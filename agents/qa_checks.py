# agents/qa_checks.py

QA_CHECKS = {
    "within_character_limit": {
        "description": "Response within platform character limit",
        "hard_fail": True,
        "weight": 1.0
    },
    "addresses_core_complaint": {
        "description": "Directly addresses the specific central issue raised by the reviewer (e.g. ignoring a reservation, cold food). Must name the specific grievance, not just apologize generically.",
        "hard_fail": False,
        "weight": 1.5
    },
    "empathetic_opening": {
        "description": "Opens with an empathetic statement or apology",
        "hard_fail": False,
        "weight": 0.8
    },
    "no_legal_liability_admission": {
        "description": "Avoids admitting legal fault or liability",
        "hard_fail": True,
        "weight": 1.0
    },
    "no_public_compensation_offer": {
        "description": "Avoids offering refunds or discounts publicly",
        "hard_fail": True,
        "weight": 1.0
    },
    "no_defensive_language": {
        "description": "Avoids blame-shifting, 'but', or negating the reviewer's experience",
        "hard_fail": False,
        "weight": 1.2
    },
    "has_action_step": {
        "description": "Includes a concrete next step or contact path for resolution",
        "hard_fail": False,
        "weight": 1.2
    },
    "appropriate_tone": {
        "description": "Tone matches review valence (empathetic for negative, warm for positive)",
        "hard_fail": False,
        "weight": 1.0
    },
    "brand_voice_consistent": {
        "description": "Tone and vocabulary match brand voice profile. Avoids corporate-speak or deflective language like 'operational issues'.",
        "hard_fail": False,
        "weight": 1.0
    },
    "not_generic": {
        "description": "Response feels personalized, not like a copy-pasted template",
        "hard_fail": False,
        "weight": 0.7
    }
}
