from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import logging

log = logging.getLogger("bridge")
logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active SSE subscriber queues
_queues: list[asyncio.Queue] = []

@app.post("/events")
async def receive_event(request: Request):
    """Agents POST here. Fire-and-forget from the agent side."""
    try:
        event = await request.json()
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}, 400

    log.debug("event: agent=%s status=%s", event.get("agent"), event.get("status"))

    dead = []
    for q in _queues:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)    # subscriber too slow — drop it
    
    for q in dead:
        _queues.remove(q)

    return {"ok": True, "subscribers": len(_queues)}

@app.get("/stream")
async def event_stream():
    """Browser connects here via EventSource. One queue per connection."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _queues.append(q)

    async def generate():
        try:
            # Send a heartbeat comment immediately so the browser knows it's connected
            yield ": connected\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"   # keep connection alive through proxies
        except asyncio.CancelledError:
            pass
        finally:
            if q in _queues:
                _queues.remove(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering
        },
    )
