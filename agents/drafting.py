"""Drafting agent: write and revise review responses."""

import asyncio
import json
import logging
from band import Agent

from shared.base_agent import ReviewAgentAdapter
from shared.schemas import ReviewEnvelope, DraftData
from shared.config import MODELS, agent_handle
from shared.envelope import append_trail, update_status
from shared.dashboard import emit

DRAFTING_SYSTEM_PROMPT = """You are the Drafting Agent in a restaurant review response pipeline.

Write a response to a customer review using the provided context.

## Requirements
1. Length: 3–5 sentences. NEVER exceed platform_character_limit.
2. Tone: Warm, professional, genuinely empathetic. Senior hospitality professional.
3. Structure: acknowledge specific experience → address core issue → action/resolution → close with next step
4. Prohibitions:
   - No admission of legal liability
   - No public compensation offers (no discounts/vouchers/refunds in text)
   - No defensive language ("however", "but actually", "in our defence")
   - Do not name specific staff members
   - Do not minimise safety/health complaints

## When Revising
If qa_feedback is provided in the input context, fix ONLY what is flagged. Preserve what worked.

## Output
Return ONLY valid JSON — no preamble, no markdown.
{
  "response_text": "The response text.",
  "word_count": 42,
  "confidence": 0.85,
  "reasoning": "One sentence explaining approach."
}
"""

class DraftingAdapter(ReviewAgentAdapter):
    def __init__(self):
        cfg = MODELS["drafting"]
        super().__init__(
            agent_name="drafting-agent",
            llm_base_url=cfg["base_url"],
            llm_api_key=cfg["key"],
            model=cfg["model"],
        )

    async def process_message(self, content: str, tools) -> None:
        try:
            envelope = ReviewEnvelope.model_validate_json(content)
        except Exception as e:
            self.log.error(f"ReviewEnvelope parse error: {e}")
            await tools.send_event(content=f"[DRAFTING] Parse error: {e}", message_type="error")
            return

        is_revision = envelope.qa and envelope.qa.feedback_to_drafter is not None
        
        await emit(
            agent="drafter", status="processing",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Drafting", note=f"Attempt #{envelope.qa.revision_count + 1 if is_revision else 1}",
            edge=None,
        )

        if is_revision:
            prefix = f"✏️ [DRAFTING] Revising draft (attempt #{envelope.qa.revision_count + 1})"
            self.log.info(f"Revision #{envelope.qa.revision_count + 1} for {envelope.review_id}")
        else:
            prefix = "✏️ [DRAFTING] Writing fresh draft"
            self.log.info(f"Fresh draft for {envelope.review_id}")

        context = {
            "review": envelope.review.model_dump(mode="json"),
            "research": envelope.research.model_dump(mode="json"),
        }
        if is_revision:
            context["previous_draft"] = envelope.draft.model_dump(mode="json")
            context["qa_feedback"] = envelope.qa.feedback_to_drafter
            
        # Demo hack: force a bad first draft for the QA loop scenario
        if envelope.review.author == "Sarah K." and not is_revision:
            context["special_system_instruction"] = "For this specific draft, intentionally ignore the 'No public compensation offers' and 'No defensive language' rules. You MUST offer a full refund and use defensive language like 'however, we were very busy'. This is required to trigger the QA system."


        result_text = await self.call_llm(
            system_prompt=DRAFTING_SYSTEM_PROMPT,
            user_content=json.dumps(context),
            json_mode=True,
        )

        try:
            llm_out = json.loads(result_text)
            draft_data = DraftData.model_validate(llm_out)
            # Retain or increment version
            draft_data.version = envelope.draft.version + 1 if is_revision else 1
        except Exception as e:
            self.log.error(f"Draft validation error: {e}\nRaw: {result_text}")
            await tools.send_event(content=f"[DRAFTING] Schema error: {e}", message_type="error")
            return

        envelope.draft = draft_data
        
        envelope_dict = envelope.model_dump()
        envelope_dict = append_trail(
            envelope_dict,
            "drafting",
            "drafted",
            f"version={draft_data.version}, confidence={draft_data.confidence}"
        )
        envelope_dict = update_status(envelope_dict, "drafting")

        await tools.send_event(
            content=(
                f"{prefix}\n"
                f"  Pipeline: {envelope.review_id}\n"
                f"  Length: {draft_data.word_count} words\n"
                f"  Confidence: {draft_data.confidence}\n"
                f"  Rationale: \"{draft_data.reasoning}\"\n"
                f"  Preview: \"{(draft_data.response_text or '')[:100]}...\"\n"
                f"  ➡️ Routing to qa-agent"
            ),
            message_type="thought",
        )

        await emit(
            agent="drafter", status="done",
            review_id=envelope.review_id, envelope=envelope_dict,
            action="Drafted",
            note=f"Wrote {draft_data.word_count} words",
            confidence=draft_data.confidence,
            edge="drafter-qa",
            draft_text=draft_data.response_text,
        )

        await tools.send_message(
            content=json.dumps(envelope_dict),
            mentions=[agent_handle("qa")],
        )

async def run():
    adapter = DraftingAdapter()
    agent = Agent.from_config("drafting", adapter=adapter)
    await agent.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run())
