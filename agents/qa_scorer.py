# agents/qa_scorer.py

from agents.qa_checks import QA_CHECKS

def run_qa_checks(llm_out: dict) -> dict:
    """
    llm_out: {"checks": {"within_character_limit": True, ...}, "feedback": "...", "confidence": 0.95}
    Returns: {"passed": bool, "overall_score": float, "hard_fail_triggers": list, "feedback": str, "checks": dict}
    """
    if "checks" in llm_out and isinstance(llm_out["checks"], dict):
        checks = llm_out["checks"]
        feedback = llm_out.get("feedback")
    else:
        checks = llm_out
        feedback = None

    # Handle old object schema gracefully just in case
    normalized_checks = {}
    for name, value in checks.items():
        if isinstance(value, dict):
            normalized_checks[name] = value.get("passed", False)
        else:
            normalized_checks[name] = bool(value)
            
    hard_fails = [
        name for name, passed in normalized_checks.items()
        if not passed and QA_CHECKS.get(name, {}).get("hard_fail", False)
    ]
    
    if hard_fails:
        fail_msg = f"Hard fail on: {', '.join(hard_fails)}. Do not revise — escalate."
        if feedback:
            feedback = f"{fail_msg} Feedback: {feedback}"
        else:
            feedback = fail_msg
            
        return {
            "passed": False,
            "overall_score": 0.0,
            "hard_fail_triggers": hard_fails,
            "feedback": feedback,
            "checks": normalized_checks
        }

    soft_checks = {k: v for k, v in QA_CHECKS.items() if not v.get("hard_fail", False)}
    total_weight = sum(c.get("weight", 1.0) for c in soft_checks.values())
    
    weighted_score = sum(
        soft_checks[name].get("weight", 1.0)
        for name, passed in normalized_checks.items()
        if passed and name in soft_checks
    )

    final_score = weighted_score / total_weight if total_weight > 0 else 0
    passed = len(hard_fails) == 0 and final_score >= 0.75

    if not passed:
        failed_checks = [name for name, passed_chk in normalized_checks.items() if not passed_chk]
        failed_str = f"Failed checks: {', '.join(failed_checks)}." if failed_checks else "Score below threshold."
        if feedback:
            feedback = f"{failed_str} Feedback: {feedback}"
        else:
            feedback = f"Revision required. {failed_str}"

    return {
        "passed": passed,
        "overall_score": round(final_score, 3),
        "hard_fail_triggers": hard_fails,
        "feedback": feedback,
        "checks": normalized_checks
    }
