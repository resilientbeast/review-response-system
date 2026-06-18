import uuid
from datetime import datetime, timezone

def append_trail(envelope: dict, agent_name: str, action: str, note: str) -> dict:
    envelope.setdefault("reasoning_trail", []).append({
        "agent": agent_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "note": note
    })
    return envelope

def update_status(envelope: dict, status: str) -> dict:
    envelope["status"] = status
    return envelope
