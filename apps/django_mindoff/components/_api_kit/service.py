import hashlib
import json
from django.urls import resolve
from ...models import MOQueue
from .redis import init_queue
from .worker import execute_queue


def enqueue_process(request, api_instance):
    user_id = getattr(request.user, "id", None) or request.session.session_key
    payload = request.data if request.method in ("POST", "PUT") else {}

    raw = f"{user_id}:{api_instance.api_url_name}:{json.dumps(payload, sort_keys=True)}"
    idempotency_key = hashlib.sha256(raw.encode()).hexdigest()

    obj, created = MOQueue.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "user_id": user_id,
            "status": "queue",
            "api_url": api_instance.api_url_name,
            "request": payload,
        },
    )

    if not created:
        return str(obj.mo_queue_id)

    init_queue(obj.mo_queue_id)
    execute_queue.send(str(obj.mo_queue_id))

    return str(obj.mo_queue_id)
