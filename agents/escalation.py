"""Escalation agent: terminal stage, formats human-readable output."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from band import Agent

from shared.base_agent import ReviewAgentAdapter
from shared.schemas import ReviewEnvelope
from shared.config import MODELS
from shared.envelope import append_trail, update_status
from agents.research_memory import save_approved_response
from shared.dashboard import emit

DB_PATH = os.environ.get("DB_PATH", "./data/reviews.db")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def format_escalation_brief(envelope: ReviewEnvelope) -> str:
    r = envelope.review.model_dump()
    t = envelope.triage.model_dump() if envelope.triage else {}
    d = envelope.draft.model_dump() if envelope.draft else {}
    qa = envelope.qa.model_dump() if envelope.qa else {}
    reason = envelope.escalation.reason if envelope.escalation and envelope.escalation.reason else "Critical rating/keywords or confidence threshold."

    return f"""
🚨 ESCALATION BRIEF — {envelope.review_id}
Platform: {envelope.platform.upper()} | Rating: {r.get('rating')}/5
Urgency: {str(t.get('urgency')).upper()} | Sentiment: {str(t.get('sentiment')).upper()}
Reason for escalation: {reason}

Review text:
"{r.get('text')}"

Triage reasoning: {t.get('reasoning', 'N/A')}

Draft response (v{d.get('version', 0)}):
"{d.get('response_text', 'None')}"

QA feedback: {qa.get('feedback_to_drafter', 'N/A')}

To approve: @escalation approve {envelope.review_id}
To reject and re-draft: @escalation redraft {envelope.review_id} [your notes]
"""

async def mock_send_slack_alert(text: str):
    """Mock implementation for sending a Slack alert."""
    if SLACK_WEBHOOK_URL:
        # Here we would normally use httpx to post to Slack
        logging.info(f"[SLACK ALERT TRIGGERED] Sent to {SLACK_WEBHOOK_URL}")
    else:
        logging.info(f"[SLACK ALERT TRIGGERED] (No webhook configured)\n{text}")


class EscalationAdapter(ReviewAgentAdapter):
    def __init__(self):
        cfg = MODELS["escalation"]
        super().__init__(
            agent_name="escalation-agent",
            llm_base_url=cfg["base_url"],
            llm_api_key=cfg["key"],
            model=cfg["model"],
        )

    async def process_message(self, content: str, tools) -> None:
        try:
            envelope = ReviewEnvelope.model_validate_json(content)
        except Exception as e:
            self.log.error(f"ReviewEnvelope parse error: {e}")
            return

        envelope.escalation.status = "pending"
        envelope.escalation.notified_at = datetime.now(timezone.utc).isoformat()
        
        await emit(
            agent="escalation", status="processing",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Reviewing", note="Checking escalation rules",
            edge=None,
        )
        
        brief = format_escalation_brief(envelope)
        
        # If this is QA approved, we can consider saving it immediately or wait for human. 
        # The spec indicates wait for human, but if qa_passed and not required escalation, we auto-approve.
        if envelope.qa and envelope.qa.passed and not envelope.escalation.required:
            envelope.final_response = envelope.draft.response_text
            envelope.published_at = datetime.now(timezone.utc).isoformat()
            envelope_dict = envelope.model_dump()
            envelope_dict = update_status(envelope_dict, "published")
            save_approved_response(DB_PATH, envelope_dict)
            
            await tools.send_event(
                content=f"✅ [ESCALATION] AUTO-PUBLISHED REVIEW {envelope.review_id}\n\nResponse:\n{envelope.final_response}",
                message_type="task"
            )
            
            await emit(
                agent="system", status="published",
                review_id=envelope.review_id, envelope=envelope_dict,
                action="Published", note="Auto-approved",
                edge=None,
                published=True,
                draft_text=envelope.final_response
            )
            return

        # It's an escalation
        envelope_dict = envelope.model_dump()
        envelope_dict = append_trail(envelope_dict, "escalation", "pending_human", "Awaiting human decision via Slack/Band.")
        
        self.log.warning(f"ESCALATION for {envelope.review_id}")

        await tools.send_event(
            content=brief,
            message_type="task",
        )
        
        # Trigger Mock Slack Webhook
        await mock_send_slack_alert(brief)

        await emit(
            agent="escalation", status="waiting",
            review_id=envelope.review_id, envelope=envelope_dict,
            action="Escalated", note="Awaiting human decision via Slack",
            edge=None,
        )


async def run():
    adapter = EscalationAdapter()
    agent = Agent.from_config("escalation", adapter=adapter)
    await agent.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run())
