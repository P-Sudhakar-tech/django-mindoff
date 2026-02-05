import json
import redis
from .constants import REDIS_QUEUE_TTL

r = redis.Redis(decode_responses=True)


def redis_key(queue_id):
    return f"mo:queue:{queue_id}"


def init_queue(queue_id):
    r.setex(
        redis_key(queue_id),
        REDIS_QUEUE_TTL,
        json.dumps(
            {
                "status": "queue",
                "progress": 0,
                "msg": "In Queue",
                "cancelled": False,
                "steps": [],
            }
        ),
    )


def update(queue_id, **fields):
    key = redis_key(queue_id)
    data = json.loads(r.get(key) or "{}")
    data.update(fields)
    r.setex(key, REDIS_QUEUE_TTL, json.dumps(data))


def get(queue_id):
    val = r.get(redis_key(queue_id))
    return json.loads(val) if val else None
