import httpx
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

BRIDGE_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8765")
log = logging.getLogger("dashboard")

async def emit(
    agent: str,
    status: str,
    review_id: str,
    envelope: Dict[str, Any],
    action: str = "",
    note: str = "",
    confidence: float = 0.0,
    edge: Optional[str] = None,
    qa_result: Optional[Dict[str, Any]] = None,
    draft_text: Optional[str] = None,
    published: bool = False,
    revision_count: int = 0,
):
    """
    Fire-and-forget. Never raises — dashboard is non-critical.
    Agent pipeline continues regardless of whether the emit succeeds.
    """
    event = {
        "event_type": "agent_status",
        "agent": agent,
        "status": status,
        "review_id": review_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "envelope_snapshot": envelope,
        "trail_entry": {
            "action": action,
            "note": note,
            "confidence": confidence,
        },
        "qa_result": qa_result,
        "draft_text": draft_text,
        "meta": {
            "edge": edge,
            "revision_count": revision_count,
            "published": published,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            await client.post(f"{BRIDGE_URL}/events", json=event)
    except Exception as exc:
        log.debug("dashboard emit failed (non-fatal): %s", exc)
