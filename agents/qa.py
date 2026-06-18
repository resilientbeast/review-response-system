"""QA agent: evaluate drafts against quality checks."""

import asyncio
import json
import logging
from band import Agent

from shared.base_agent import ReviewAgentAdapter
from shared.schemas import ReviewEnvelope, QAData
from shared.config import MODELS, agent_handle
from shared.envelope import append_trail, update_status
from agents.qa_scorer import run_qa_checks
from agents.qa_checks import QA_CHECKS
from shared.dashboard import emit

QA_SYSTEM_PROMPT = """You are the QA Agent in a restaurant review response pipeline.

Evaluate the draft response against the specific quality checks listed below.
Output a JSON object with scores for each check.

## Checks to Evaluate
"""
for name, data in QA_CHECKS.items():
    QA_SYSTEM_PROMPT += f"- {name}: {data['description']}\n"

QA_SYSTEM_PROMPT += """
## Output
Return ONLY valid JSON with boolean values for each check.
If all checks pass and the draft is approved, set `feedback` to `null`.
If any checks fail or revision is required, provide detailed reasoning in `feedback` so the drafter knows what to fix.

{
  "checks": {
    "within_character_limit": true|false,
    "addresses_core_complaint": true|false
  },
  "feedback": null,
  "confidence": <float 0.0-1.0>
}
Ensure you include EVERY check from the 'Checks to Evaluate' section in the 'checks' dictionary.
"""

class QAAdapter(ReviewAgentAdapter):
    def __init__(self):
        cfg = MODELS["qa"]
        super().__init__(
            agent_name="qa-agent",
            llm_base_url=cfg["base_url"],
            llm_api_key=cfg["key"],
            model=cfg["model"],
        )

    async def process_message(self, content: str, tools) -> None:
        try:
            envelope = ReviewEnvelope.model_validate_json(content)
        except Exception as e:
            self.log.error(f"ReviewEnvelope parse error: {e}")
            await tools.send_event(content=f"[QA] Parse error: {e}", message_type="error")
            return

        await emit(
            agent="qa", status="processing",
            review_id=envelope.review_id, envelope=envelope.model_dump(),
            action="Checking", note="Running quality evaluation",
            edge=None,
        )

        context = {
            "review": envelope.review.model_dump(mode="json"),
            "draft": envelope.draft.model_dump(mode="json"),
            "platform_rules": envelope.research.platform_rules.model_dump(mode="json") if envelope.research.platform_rules else None,
            "brand_voice": envelope.research.brand_voice.model_dump(mode="json") if envelope.research.brand_voice else None,
        }

        result_text = await self.call_llm(
            system_prompt=QA_SYSTEM_PROMPT,
            user_content=json.dumps(context),
            json_mode=True,
        )

        try:
            llm_out = json.loads(result_text)
            qa_result = run_qa_checks(llm_out)
        except Exception as e:
            self.log.error(f"QA validation error: {e}\nRaw: {result_text}")
            await tools.send_event(content=f"[QA] Schema error: {e}", message_type="error")
            return

        revision_count = envelope.qa.revision_count if envelope.qa else 0
        
        qa_data = QAData(
            passed=qa_result["passed"],
            revision_count=revision_count,
            checks=qa_result["checks"],
            feedback_to_drafter=qa_result["feedback"],
            confidence=llm_out.get("confidence", 1.0),
            overall_score=qa_result["overall_score"],
            hard_fail_triggers=qa_result["hard_fail_triggers"],
        )

        # Routing Logic
        feedback_given = qa_result["feedback"] is not None
        if qa_result["passed"] and not feedback_given:
            route_to = "escalation" # Escalation handles publishing / final check
            status_update = "approved"
            qa_data.feedback_to_drafter = None # Clear feedback if passed
            envelope.status = "approved"
            envelope.final_response = envelope.draft.response_text
        else:
            if qa_result["hard_fail_triggers"] or revision_count >= 2:
                route_to = "escalation"
                envelope.escalation.required = True
                escalation_reason = "QA hard fail or revision cap reached."
                if feedback_given:
                    escalation_reason += " Feedback: " + str(qa_result["feedback"])
                envelope.escalation.reason = escalation_reason
                status_update = "escalated"
            else:
                route_to = "drafting"
                qa_data.revision_count += 1
                status_update = "qa_review"

        envelope.qa = qa_data
        
        envelope_dict = envelope.model_dump()
        envelope_dict = append_trail(
            envelope_dict,
            "qa",
            "qa_checked",
            f"score={qa_data.overall_score}, passed={qa_data.passed}, route={route_to}"
        )
        envelope_dict = update_status(envelope_dict, status_update)

        if qa_result["passed"]:
            emoji = "✅"
            verdict = "APPROVED"
        else:
            emoji = "❌"
            verdict = f"REVISION NEEDED ({route_to.upper()})"

        await tools.send_event(
            content=(
                f"{emoji} [QA] Evaluation complete\n"
                f"  Pipeline: {envelope.review_id}\n"
                f"  Score: {qa_data.overall_score * 100:.1f}%\n"
                f"  Verdict: {verdict}\n"
                f"  ➡️ Routing to {route_to}-agent"
            ),
            message_type="thought",
        )

        qa_res = qa_data.model_dump()
        qa_res["feedback"] = qa_res.pop("feedback_to_drafter", None)
        
        await emit(
            agent="qa",
            status="done" if qa_result["passed"] else "error",
            review_id=envelope.review_id,
            envelope=envelope_dict,
            action="Evaluated",
            note=f"Score: {qa_data.overall_score * 100:.1f}%. Passed: {qa_result['passed']}",
            confidence=qa_data.confidence,
            edge=None if qa_result["passed"] else "qa-drafter",
            qa_result=qa_res,
        )

        await tools.send_message(
            content=json.dumps(envelope_dict),
            mentions=[agent_handle(route_to)],
        )

async def run():
    adapter = QAAdapter()
    agent = Agent.from_config("qa", adapter=adapter)
    await agent.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    asyncio.run(run())
