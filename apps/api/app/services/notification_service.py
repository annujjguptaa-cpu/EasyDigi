"""
In-memory SSE notification bus for bank staff.
Falls back to 5-second polling via REST endpoint.
"""
import asyncio
import json
import time
from typing import Dict, List, Any
from collections import defaultdict

# {staff_id: [asyncio.Queue]} — multiple browser tabs supported
_SUBSCRIBER_QUEUES: Dict[str, List[asyncio.Queue]] = defaultdict(list)


async def subscribe(staff_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _SUBSCRIBER_QUEUES[staff_id].append(q)
    return q


def unsubscribe(staff_id: str, q: asyncio.Queue):
    try:
        if staff_id in _SUBSCRIBER_QUEUES and q in _SUBSCRIBER_QUEUES[staff_id]:
            _SUBSCRIBER_QUEUES[staff_id].remove(q)
    except (ValueError, KeyError):
        pass


async def emit_event(staff_id: str, event_type: str, payload: dict):
    """Push an event to all queues for a staff member."""
    data = json.dumps({"event": event_type, "payload": payload, "ts": time.time()})
    dead = []
    for q in _SUBSCRIBER_QUEUES.get(staff_id, []):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        unsubscribe(staff_id, q)


async def broadcast_event(event_type: str, payload: dict):
    """Broadcast to ALL connected staff (e.g. admin events)."""
    for staff_id in list(_SUBSCRIBER_QUEUES.keys()):
        await emit_event(staff_id, event_type, payload)
