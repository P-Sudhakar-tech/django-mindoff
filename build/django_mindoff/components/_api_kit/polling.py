import uuid
import asyncio
import json
import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from ...models import MindoffPolling


# --- redis client ---
redis_client = redis.Redis.from_url("redis://localhost:6379/0")


def start_polling_task(func, request, *args, **kwargs) -> dict:
    """
    Gateway to start polling.
    Saves task in DB + Redis.
    Launches async runner that updates progress in Redis + pushes to WS.
    """
    task_id = str(uuid.uuid4())
    user_id = request.user.id if request.user.is_authenticated else None
    cookie_identifier = request.COOKIES.get("sessionid", None)

    # persist once in DB
    MindoffPolling.objects.create(
        task_id=task_id,
        user_id=user_id,
        cookie_identifier=cookie_identifier,
        status="pending",
    )

    # persist initial in Redis
    redis_client.hset(
        f"polling:{task_id}",
        mapping={
            "status": "pending",
            "percentage": "0",
            "message": "Task created",
        },
    )

    # async runner
    asyncio.create_task(_run_task(func, task_id, request, *args, **kwargs))
    return {"task_id": task_id}


async def _run_task(func, task_id, request, *args, **kwargs):
    group_name = f"task_{task_id}"

    try:
        kwargs["_progress_callback"] = lambda p, s: _update_progress(
            task_id, group_name, p, s
        )

        if asyncio.iscoroutinefunction(func):
            await func(request, *args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, func, request, *args, **kwargs)

        _finalize_task(task_id, group_name, "completed", 100)
    except Exception as e:
        _finalize_task(task_id, group_name, f"error: {str(e)}", 0)


def _update_progress(task_id: str, group_name: str, percentage: int, status: str):
    redis_client.hset(
        f"polling:{task_id}",
        mapping={"status": status, "percentage": str(percentage)},
    )
    async_to_sync(_send_ws_update)(group_name, percentage, status)


def _finalize_task(task_id: str, group_name: str, status: str, percentage: int):
    # update redis
    redis_client.hset(
        f"polling:{task_id}",
        mapping={"status": status, "percentage": str(percentage)},
    )
    redis_client.expire(f"polling:{task_id}", 60)  # auto-clean after 1min

    # persist final state in DB
    MindoffPolling.objects.filter(task_id=task_id).update(
        status=status,
        updated_at=timezone.now(),
    )

    # push final ws
    async_to_sync(_send_ws_update)(group_name, percentage, status)


async def _send_ws_update(group_name: str, percentage: int, status: str):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        group_name,
        {
            "type": "task.progress",
            "percentage": percentage,
            "status": status,
        },
    )
