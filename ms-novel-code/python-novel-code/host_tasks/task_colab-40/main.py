
"""This program simulates a priority queue system using redis db."""

import json
import redis
from typing import Optional, Dict

EVENT_TYPE_RANK = {
    "alert": 0,
    "transaction": 1,
    "log": 2
}

PRIORITY_QUEUE_KEY = "priority_event_queue"
COUNTER_KEY = "priority_event_counter"


def enqueue_event(redis_conn: redis.Redis, event: Dict) -> None:
    """Enqueue an event into a Redis priority queue based on priority."""
    event_id = event.get("event_id")
    event_type = event.get("event_type")
    urgency = event.get("urgency")
    payload = event.get("payload")

    if not event_id:
        raise ValueError("Missing 'event_id' in event")
    if event_type not in EVENT_TYPE_RANK:
        raise ValueError(f"Unknown event_type '{event_type}'")
    if not isinstance(urgency, int) or not (1 <= urgency <= 5):
        raise ValueError("Urgency must be an integer from 1 to 5")
    if not isinstance(payload, str):
        raise ValueError("Missing or invalid 'payload' field")

    if redis_conn.zscore(PRIORITY_QUEUE_KEY, event_id) is not None:
        return

    type_rank = EVENT_TYPE_RANK[event_type]
    urgency_factor = 5 - urgency
    insert_index = redis_conn.incr(COUNTER_KEY)
    score = (urgency_factor * 1_000_000) + (type_rank * 1_000) + insert_index

    redis_conn.set(f"event:{event_id}", json.dumps(event))
    redis_conn.zadd(PRIORITY_QUEUE_KEY, {event_id: score})


def dequeue_event(redis_conn: redis.Redis) -> Optional[dict]:
    """Dequeue the highest priority event from Redis."""
    popped = redis_conn.zpopmin(PRIORITY_QUEUE_KEY, 1)
    if not popped:
        return []

    event_id, _ = popped[0]
    if isinstance(event_id, bytes):  # redis-py returns bytes
        event_id = event_id.decode()

    event_data_key = f"event:{event_id}"
    event_json = redis_conn.get(event_data_key)
    if not event_json:
        return None

    event_dict = json.loads(event_json)
    redis_conn.delete(event_data_key)
    return event_dict

