"""Demo data: mock reviews and brand context."""

from datetime import datetime

MOCK_REVIEWS: list[dict] = [
    {
        "review_id": "rev-001",
        "platform": "google",
        "rating": 1,
        "text": "I got food poisoning after eating here on Saturday. I've been sick for 3 days and I'm consulting a lawyer. The health department will be notified.",
        "reviewer_name": "James Thorton",
        "timestamp": datetime(2026, 6, 15, 14, 23, 0),
    },
    {
        "review_id": "rev-002",
        "platform": "yelp",
        "rating": 2,
        "text": "Waited 45 minutes for food that arrived cold. Waiter was rude when we complained. Never coming back.",
        "reviewer_name": "Sarah K.",
        "timestamp": datetime(2026, 6, 15, 19, 5, 0),
    },
    {
        "review_id": "rev-003",
        "platform": "tripadvisor",
        "rating": 3,
        "text": "Mixed experience. The pasta was excellent but service was slow. Nice ambiance. Might give it another shot.",
        "reviewer_name": "Marco B.",
        "timestamp": datetime(2026, 6, 15, 20, 0, 0),
    },
    {
        "review_id": "rev-004",
        "platform": "google",
        "rating": 5,
        "text": "Absolutely wonderful evening! The risotto was the best I've had in London. Staff were incredibly attentive. Already booked for next month.",
        "reviewer_name": "Emily Watson",
        "timestamp": datetime(2026, 6, 16, 12, 30, 0),
    },
    {
        "review_id": "rev-005",
        "platform": "yelp",
        "rating": 1,
        "text": "Found a piece of glass in my soup. Serious safety hazard. My child was eating this. I want a full refund and explanation.",
        "reviewer_name": "David Chen",
        "timestamp": datetime(2026, 6, 16, 13, 45, 0),
    },
]

SIMILAR_REVIEWS_DB: list[dict] = [
    {
        "review_text": "Got sick after dining here. Very disappointed.",
        "response_text": "We take all food safety concerns extremely seriously. Please contact our team at guestrelations@restaurant.com so we can investigate this thoroughly.",
        "platform": "google", "rating": 1, "outcome": "resolved",
        "keywords": ["sick", "food", "ill"],
    },
    {
        "review_text": "Service was incredibly slow, waited over an hour.",
        "response_text": "We're truly sorry your visit didn't meet expectations. We've reviewed our kitchen workflow and would love to welcome you back with a complimentary starter on your next visit.",
        "platform": "yelp", "rating": 2, "outcome": "resolved",
        "keywords": ["wait", "slow", "service"],
    },
    {
        "review_text": "Staff were rude and dismissive when we had a problem.",
        "response_text": "This is not the standard of hospitality we hold ourselves to and we sincerely apologise. We've shared your feedback with our leadership. Please reach out directly so we can make this right.",
        "platform": "tripadvisor", "rating": 2, "outcome": "resolved",
        "keywords": ["rude", "staff", "dismissive"],
    },
]

BRAND_GUIDELINES: list[str] = [
    "Always begin with genuine empathy and acknowledgement of the specific experience.",
    "Never be defensive, dismissive, or argumentative in any public response.",
    "Do not offer specific compensation (discounts, refunds) in public responses — handle privately.",
    "Do not admit legal liability or use language that could be construed as an admission of fault.",
    "Use warm, professional language. Avoid corporate jargon.",
    "Always sign off with a specific action step — contact invitation or return invitation.",
    "Contact for escalations: guestrelations@restaurant.com",
    "Refer to management as 'our management team' — never name specific individuals.",
    "For safety/health complaints: prioritise urgency, never minimise, always invite direct contact.",
    "For positive reviews: warm but brief. Thank specifically, not generically.",
    "Response length: 3–5 sentences for most reviews. Never exceed platform character limit.",
    "Tone: think 'senior hospitality professional who genuinely cares' — not 'corporate PR'.",
]

PLATFORM_NOTES: dict[str, str] = {
    "google": "Responses appear publicly next to your listing. Professional tone essential. Char limit: 4096.",
    "yelp": "Plain text only. Cannot edit after 30 days. Char limit: 5000.",
    "tripadvisor": "Responses are permanent and cannot be deleted. Visible to millions. Char limit: 3000.",
}
