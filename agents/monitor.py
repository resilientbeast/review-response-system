"""Monitor agent: Passive listener for new reviews (from webhook ingestor).

It receives a ReviewEnvelope from the ingestion pipeline via a Band message,
and routes it to Triage.
"""

import asyncio
import logging
from band import Agent
from band.core.simple_adapter import SimpleAdapter
from band.core.types import PlatformMessage
from shared.schemas import ReviewEnvelope, ReviewData
from shared.config import agent_handle
from shared.dashboard import emit
from aiohttp import web
import uuid
import datetime

log = logging.getLogger("monitor-agent")

_global_tools = None

class MonitorAdapter(SimpleAdapter):
    """Monitor adapter — receives envelopes and routes to triage."""

    async def on_message(
        self,
        msg: PlatformMessage,
        tools,
        history,
        participants_msg,
        contacts_msg,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        global _global_tools
        if is_session_bootstrap:
            _global_tools = tools
            log.info("Monitor session bootstrapped in room %s", room_id)
            return
            
        if not msg.content:
            return

        try:
            content = msg.content
            if content.startswith("@monitor "):
                content = content.replace("@monitor ", "", 1)
                
            envelope = ReviewEnvelope.model_validate_json(content)
        except Exception as e:
            log.error(f"Monitor failed to parse message: {e}\nContent: {msg.content}")
            return

        # Emit an event to the room
        await tools.send_event(
            content=(
                f"[MONITOR] New review detected (via webhook)\n"
                f"  ID: {envelope.review_id} | Platform: {envelope.platform.upper()} "
                f"| Rating: {envelope.review.rating}/5 | Reviewer: {envelope.review.author}\n"
                f'  Preview: "{envelope.review.text[:80]}..."\n'
                f"  -> Routing to triage-agent"
            ),
            message_type="thought",
        )

        await emit(
            agent="monitor", status="processing",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Ingested", note="Received from webhook",
            edge=None,
        )

        await emit(
            agent="monitor", status="done",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Ingested", note="Google webhook",
            edge="monitor-triage",
        )

        # Route to triage
        await tools.send_message(
            content=envelope.model_dump_json(),
            mentions=[agent_handle("triage")],
        )
        log.info(f"Sent {envelope.review_id} to triage")

async def inject_review_handler(request):
    """Handle incoming mock reviews from the dashboard."""
    try:
        data = await request.json()
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

    envelope = ReviewEnvelope(
        review_id=f"REV-{uuid.uuid4().hex[:6].upper()}",
        platform="google",
        business_id="loc_demo",
        status="ingested",
        review=ReviewData(
            author=data.get("reviewer_name", "Demo User"),
            rating=int(data.get("rating", 3)),
            text=data.get("text", ""),
            url="http://demo.platform",
            timestamp=datetime.datetime.utcnow().isoformat()
        )
    )

    agent = request.app["agent"]
    import os
    BAND_ROOM_ID = os.environ.get("BAND_ROOM_ID")

    # We simulate what on_message does:
    await emit(
        agent="monitor", status="processing",
        review_id=envelope.review_id, envelope=envelope.model_dump(),
        action="Ingested", note="Received from dashboard inject",
        edge=None,
    )

    try:
        await agent.runtime.link.rest.agent_api_messages.create_agent_chat_message(
            chat_id=BAND_ROOM_ID,
            message={
                "content": (
                    f"[MONITOR] New review detected (via mock injection)\n"
                    f"  ID: {envelope.review_id} | Platform: {envelope.platform.upper()} "
                    f"| Rating: {envelope.review.rating}/5 | Reviewer: {envelope.review.author}\n"
                    f'  Preview: "{envelope.review.text[:80]}..."\n'
                    f"  -> Routing to triage-agent"
                )
            }
        )
    except Exception as e:
        log.warning(f"Could not send thought event: {e}")

    await emit(
        agent="monitor", status="done",
        review_id=envelope.review_id, envelope=envelope.model_dump(),
        action="Ingested", note="Dashboard injection",
        edge="monitor-triage",
    )

    try:
        await agent.runtime.link.rest.agent_api_messages.create_agent_chat_message(
            chat_id=BAND_ROOM_ID,
            message={
                "content": f"{agent_handle('triage')} {envelope.model_dump_json()}",
                "mentions": [{"handle": agent_handle('triage').lstrip('@')}]
            }
        )
    except Exception as e:
        log.error(f"Failed to hand off to triage: {e}")
        return web.json_response({"error": "Failed to route to triage"}, status=500)
        
    return web.json_response({"status": "ok", "review_id": envelope.review_id})


async def run_http_server(agent):
    app = web.Application()
    app["agent"] = agent
    app.router.add_post('/inject', inject_review_handler)
    
    import aiohttp_cors
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8002)
    await site.start()
    log.info("Monitor HTTP server running on http://localhost:8002")


async def run():
    adapter = MonitorAdapter()
    agent = Agent.from_config("monitor", adapter=adapter)
    
    # Start HTTP server concurrently
    asyncio.create_task(run_http_server(agent))

    
    await agent.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run())
