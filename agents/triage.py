"""Triage agent: classify reviews and route accordingly."""

import asyncio
import json
import logging
from band import Agent

from shared.base_agent import ReviewAgentAdapter
from shared.schemas import ReviewEnvelope, TriageData
from shared.config import MODELS, agent_handle
from shared.envelope import append_trail, update_status
from shared.dashboard import emit

TRIAGE_SYSTEM_PROMPT = """You are the Triage Agent in a restaurant review response pipeline.

Analyse the incoming ReviewEnvelope JSON (focusing on the "review" section) and output a JSON object containing the triage classification.

## Urgency Rules
- critical: rating 1-2 AND any of: food poisoning, illness, lawyer, legal, glass/foreign object,
  injury, discrimination, health department. Route to escalation.
- high: rating 1 or 2, no critical keywords.
- medium: rating 3, or rating 2 with mild complaints.
- low: rating 4 or 5, or overwhelmingly positive.

## Sentiment Rules
- negative: majority of review is dissatisfied, angry, or disappointed.
- neutral: mixed or ambivalent.
- positive: majority is satisfied, pleased, or praising.
- mixed: equal parts positive and negative.

## Output
Return ONLY valid JSON — no preamble, no markdown, no explanation.
{
  "sentiment": "positive"|"neutral"|"negative"|"mixed",
  "urgency": "low"|"medium"|"high"|"critical",
  "category": "service"|"product"|"staff"|"facility"|"pricing"|"other",
  "confidence": <float 0.0-1.0 — how certain you are in this classification>,
  "escalate_flag": <true if this requires human attention regardless of confidence>,
  "reasoning": "<one sentence explanation>"
}
"""

URGENCY_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}

class TriageAdapter(ReviewAgentAdapter):
    def __init__(self):
        cfg = MODELS["triage"]
        super().__init__(
            agent_name="triage-agent",
            llm_base_url=cfg["base_url"],
            llm_api_key=cfg["key"],
            model=cfg["model"],
        )

    async def process_message(self, content: str, tools) -> None:
        try:
            envelope = ReviewEnvelope.model_validate_json(content)
        except Exception as e:
            self.log.error(f"ReviewEnvelope parse error: {e}")
            await tools.send_event(content=f"[TRIAGE] Parse error: {e}", message_type="error")
            return

        await emit(
            agent="triage", status="processing",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Classifying", note="running sentiment + urgency model",
            edge=None,
        )

        result_text = await self.call_llm(
            system_prompt=TRIAGE_SYSTEM_PROMPT,
            user_content=envelope.model_dump_json(include={'review': True}),
            json_mode=True,
        )

        try:
            llm_out = json.loads(result_text)
            triage_data = TriageData.model_validate(llm_out)
        except Exception as e:
            self.log.error(f"Triage validation error: {e}\nRaw: {result_text}")
            await tools.send_event(content=f"[TRIAGE] Schema error: {e}", message_type="error")
            return

        envelope.triage = triage_data
        
        # Confidence-Gated Escalation Logic
        route_to = "research"
        if triage_data.confidence is not None and triage_data.confidence < 0.60:
            route_to = "escalation"
        elif triage_data.urgency == "critical" or triage_data.escalate_flag:
            route_to = "escalation"

        envelope_dict = envelope.model_dump()
        envelope_dict = append_trail(
            envelope_dict, 
            "triage", 
            "classified", 
            f"sentiment={triage_data.sentiment}, urgency={triage_data.urgency}, route={route_to}"
        )
        envelope_dict = update_status(envelope_dict, "triaged")

        emoji = URGENCY_EMOJI.get(triage_data.urgency, "⚪")
        await tools.send_event(
            content=(
                f"{emoji} [TRIAGE] Review classified\n"
                f"  Pipeline: {envelope.review_id}\n"
                f"  Sentiment: {str(triage_data.sentiment).upper()} | Urgency: {str(triage_data.urgency).upper()} | Confidence: {triage_data.confidence}\n"
                f"  Reason: \"{triage_data.reasoning}\"\n"
                f"  ➡️ Routing to @{route_to}-agent"
            ),
            message_type="thought",
        )

        await emit(
            agent="triage", status="done",
            review_id=envelope.review_id, envelope=envelope_dict,
            action="Classified",
            note=f"{triage_data.sentiment} · {triage_data.urgency} · conf {triage_data.confidence:.2f}",
            confidence=triage_data.confidence,
            edge=f"triage-{route_to}",
        )

        await tools.send_message(
            content=json.dumps(envelope_dict),
            mentions=[agent_handle(route_to)],
        )

async def run():
    adapter = TriageAdapter()
    agent = Agent.from_config("triage", adapter=adapter)
    await agent.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run())
