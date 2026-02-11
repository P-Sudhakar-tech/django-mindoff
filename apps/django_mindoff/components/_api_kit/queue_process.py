import json
import hashlib
import base64
import gzip
import redis
import dramatiq
import uuid
from django.utils import timezone
from django.urls import resolve
from django.test.client import RequestFactory
from ..helper_kit import get_api_class_from_url_name
from ...models import MOQueue
import traceback

from django.apps import apps
from django.utils.module_loading import import_string
from ...models import MOQueue
from .redis import init_queue, mark_running, mark_completed, mark_failed
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import Retries
from django.conf import settings

redis_broker = RedisBroker(
    url=settings.REDIS_URL,
    middleware=[
        Retries(max_retries=0),
    ],
)
dramatiq.set_broker(redis_broker)

_COMPRESSED_RESPONSE_FLAG = "__compressed__"


class QueueRequest:
    def __init__(
        self,
        *,
        method: str,
        data=None,
        query_params=None,
        headers=None,
        user=None,
        auth=None,
        files=None,
    ):
        # HTTP method
        self.method = method.upper()

        # Payload sources
        self.data = data or {}
        self.query_params = query_params or {}
        self.FILES = files or {}

        # Metadata
        self.headers = headers or {}
        self.user = user
        self.auth = auth

    def __repr__(self):
        return f"<QueueRequest method={self.method}>"


def enqueue_process(*, request, api_instance, args, kwargs):
    # 1. Resolve user identity (stable + traceable)
    user_id = getattr(request.user, "id", None)

    if user_id is None:
        user_id = getattr(request, "session", None)
        user_id = getattr(user_id, "session_key", None)

    # 2. Build request snapshot (queue-safe)
    request_snapshot = {
        "method": request.method,
        "data": request.data if request.method in ("POST", "PUT") else {},
        "query_params": request.query_params,
        "headers": dict(request.headers),
        "args": args,
        "kwargs": kwargs,
    }

    # 3. (Optional) idempotency handling
    idempotency_key = None

    if not getattr(api_instance, "allow_duplicate_queue", False):
        raw = json.dumps(
            {
                "user_id": user_id,
                "api_url_name": api_instance.api_url_name,
                "request": request_snapshot,
            },
            sort_keys=True,
            default=str,
        )
        idempotency_key = hashlib.sha256(raw.encode()).hexdigest()
        existing = (
            MOQueue.objects.filter(idempotency_key=idempotency_key)
            .exclude(status__in=("failed", "completed"))
            .first()
        )

        if existing:
            return str(existing.queue_task_uuid)

    # 4. Create queue task (SQL)
    queue_task_uuid = uuid.uuid4()
    created_at = timezone.now()

    _ = MOQueue.objects.create(
        queue_task_uuid=queue_task_uuid,
        idempotency_key=idempotency_key,
        user_id=user_id,
        api_url_name=api_instance.api_url_name,
        status="queued",
        request_snapshot=request_snapshot,
        created_at=created_at,
    )

    # 5. Initialize Redis state
    init_queue(
        queue_task_uuid=str(queue_task_uuid),
        created_at=created_at,
    )

    # 6. Assign to worker
    execute_queue.send(str(queue_task_uuid))
    return str(queue_task_uuid)


@dramatiq.actor(max_retries=0)
def execute_queue(queue_task_uuid: str):
    # 1. Load queue task (SQL is source of truth)
    try:
        obj = MOQueue.objects.get(queue_task_uuid=queue_task_uuid)
    except MOQueue.DoesNotExist:
        return  # Task vanished or was purged
    snapshot = obj.request_snapshot or {}

    # 2. Mark running
    obj.status = "running"
    obj.save(update_fields=["status"])
    mark_running(queue_task_uuid)

    try:
        # 3. Resolve API class
        api_cls = get_api_class_from_url_name(obj.api_url_name)
        api = api_cls()

        # 4. Rehydrate request, args and kwargs
        request = QueueRequest(
            method=snapshot.get("method"),
            data=snapshot.get("data"),
            query_params=snapshot.get("query_params"),
            headers=snapshot.get("headers"),
            user=obj.get_user(),  # helper on model (recommended)
            auth=None,
            files={},
        )
        args = snapshot.get("args", [])
        kwargs = snapshot.get("kwargs", {})

        # 5. Execute API logic (THIS IS THE CORE)
        result = api.run(request, *args, **kwargs)
        result = _ensure_json_result(result)
        compressed_result = _compress_json_result(result)

        # 7. Mark completed
        obj.status = "completed"
        obj.response = compressed_result
        obj.save(update_fields=["status", "response"])

        mark_completed(queue_task_uuid)

    except Exception as exc:
        tb = traceback.format_exc()
        obj.status = "failed"
        obj.error = str(exc)
        obj.traceback = tb
        obj.save(update_fields=["status", "error", "traceback"])
        mark_failed(queue_task_uuid, error=str(exc))


# Implement rehydrate request for missing redis state
# Implement cancel and retry request for failed sql state


# ---------- Helper Functions ---------
def _ensure_json_result(result):
    try:
        json.dumps(result, default=str)
    except (TypeError, ValueError) as exc:
        raise ValueError("API result must be JSON-serializable") from exc
    return result


def _compress_json_result(result):
    payload = json.dumps(result, separators=(",", ":"), ensure_ascii=True)
    compressed = gzip.compress(payload.encode("utf-8"))
    b64 = base64.b64encode(compressed).decode("ascii")
    return {
        _COMPRESSED_RESPONSE_FLAG: True,
        "codec": "gzip+base64",
        "data": b64,
    }
