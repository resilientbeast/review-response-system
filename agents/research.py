"""Research agent: enrich context for drafting."""

import asyncio
import json
import logging
import os
from band import Agent

from shared.base_agent import ReviewAgentAdapter
from shared.schemas import ReviewEnvelope, ResearchData
from shared.config import MODELS, PLATFORM_LIMITS, agent_handle
from shared.mock_data import BRAND_GUIDELINES, PLATFORM_NOTES
from shared.envelope import append_trail, update_status
from agents.research_memory import get_similar_past_responses
from shared.dashboard import emit

DB_PATH = os.environ.get("DB_PATH", "./data/reviews.db")

RESEARCH_SYSTEM_PROMPT = """You are the Research Agent in a restaurant review response pipeline.

You receive a ReviewEnvelope JSON plus supporting context. Focus on the 'review' and 'triage' fields.
Enrich the context and output a JSON object containing research data.

## Tasks
1. business_name: Infer from the review or context if possible, otherwise use a placeholder.
2. brand_voice: select appropriate tone and formality, plus keywords to include/avoid based on guidelines.
3. platform_rules: include limits and rules for this platform.
4. similar_past_responses: leave empty in output, we will inject this.
5. confidence: how confident you are in the brand voice application (0.0 - 1.0).
6. reasoning: one sentence explaining your brand voice logic.
7. past_context_summary: leave empty.

## Output
Return ONLY valid JSON — no preamble, no markdown, no explanation.
{
  "business_name": "...",
  "brand_voice": {
    "tone": "professional|warm|casual",
    "formality": 0.8,
    "keywords_to_include": [],
    "keywords_to_avoid": []
  },
  "platform_rules": {
    "max_response_length": 4096,
    "allows_markdown": false,
    "requires_disclosure": false
  },
  "confidence": 0.95,
  "reasoning": "..."
}
"""

class ResearchAdapter(ReviewAgentAdapter):
    def __init__(self):
        cfg = MODELS["research"]
        super().__init__(
            agent_name="research-agent",
            llm_base_url=cfg["base_url"],
            llm_api_key=cfg["key"],
            model=cfg["model"],
        )

    async def process_message(self, content: str, tools) -> None:
        try:
            envelope = ReviewEnvelope.model_validate_json(content)
        except Exception as e:
            self.log.error(f"ReviewEnvelope parse error: {e}")
            await tools.send_event(content=f"[RESEARCH] Parse error: {e}", message_type="error")
            return

        await emit(
            agent="research", status="processing",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Researching", note="Fetching past responses and guidelines",
            edge=None,
        )

        # Fetch memory
        past_responses = get_similar_past_responses(DB_PATH, envelope.business_id, envelope.review.rating)
        past_context = "\n\n".join([
            f"Past review ({r.get('qa_score', 'N/A')}★): {r['review_text'][:100]}...\n"
            f"Past response: {r['response_text']}\n"
            f"Tone tags: {r.get('tone_tags') or 'none'}"
            for r in past_responses
        ]) or "No past responses found for this business."

        context = {
            "review": envelope.review.model_dump(mode="json"),
            "triage": envelope.triage.model_dump(mode="json"),
            "brand_guidelines": BRAND_GUIDELINES,
            "platform_character_limits": PLATFORM_LIMITS,
            "platform_notes": PLATFORM_NOTES,
            "past_context_summary": past_context
        }

        result_text = await self.call_llm(
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            user_content=json.dumps(context),
            json_mode=True,
        )

        try:
            llm_out = json.loads(result_text)
            research_data = ResearchData.model_validate(llm_out)
            research_data.similar_past_responses = past_responses
            research_data.past_context_summary = past_context
        except Exception as e:
            self.log.error(f"Research validation error: {e}\nRaw: {result_text}")
            await tools.send_event(content=f"[RESEARCH] Schema error: {e}", message_type="error")
            return

        envelope.research = research_data
        
        # Confidence-Gated Escalation
        route_to = "drafting"
        if research_data.confidence is not None and research_data.confidence < 0.55:
            route_to = "escalation"

        envelope_dict = envelope.model_dump()
        envelope_dict = append_trail(
            envelope_dict,
            "research",
            "researched",
            f"confidence={research_data.confidence}, route={route_to}"
        )
        envelope_dict = update_status(envelope_dict, "researching")

        await tools.send_event(
            content=(
                f"📚 [RESEARCH] Context enriched\n"
                f"  Pipeline: {envelope.review_id}\n"
                f"  Tone: {research_data.brand_voice.tone if research_data.brand_voice else 'unknown'}\n"
                f"  Similar reviews matched: {len(research_data.similar_past_responses)}\n"
                f"  Confidence: {research_data.confidence}\n"
                f"  ➡️ Routing to {route_to}-agent"
            ),
            message_type="thought",
        )

        await emit(
            agent="research", status="done",
            review_id=envelope.review_id, envelope=envelope_dict,
            action="Researched",
            note=f"Matched {len(research_data.similar_past_responses)} similar past responses",
            confidence=research_data.confidence,
            edge=f"research-{route_to}",
        )

        await tools.send_message(
            content=json.dumps(envelope_dict),
            mentions=[agent_handle(route_to)],
        )

async def run():
    adapter = ResearchAdapter()
    agent = Agent.from_config("research", adapter=adapter)
    await agent.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run())
