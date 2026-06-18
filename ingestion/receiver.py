import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

load_dotenv()

from shared.schemas import ReviewEnvelope, ReviewData

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BAND_ROOM_ID = os.environ.get("BAND_ROOM_ID")
BAND_API_KEY = os.environ.get("BAND_API_KEY")

def normalize_review(platform: str, raw: dict) -> dict:
    """Normalize platform-specific payloads into the standard envelope schema."""
    normalizers = {
        "google": normalize_google,
        "yelp": normalize_yelp,
        "tripadvisor": normalize_tripadvisor,
        "demo": normalize_demo
    }
    return normalizers[platform](raw)

def normalize_demo(raw: dict) -> dict:
    envelope = ReviewEnvelope(
        review_id=raw.get("review_id", str(uuid.uuid4())),
        platform=raw.get("platform", "google"),
        business_id=raw.get("business_id", "demo_business"),
        status="ingested",
        review=ReviewData(
            text=raw.get("text", ""),
            rating=raw.get("rating", 5),
            author=raw.get("reviewer_name", "Anonymous"),
            timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
            url=raw.get("url", "https://demo.com"),
            language="en"
        ),
        reasoning_trail=[{
            "agent": "monitor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ingested",
            "note": "Demo/Manual injection"
        }]
    )
    return envelope.model_dump()

def normalize_google(raw: dict) -> dict:
    review = raw.get("review", {})
    star_mapping = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    star_rating = review.get("starRating", "THREE")
    rating = star_mapping.get(star_rating, int(star_rating.split("_")[0]) if "_" in star_rating else 3)
    
    business_id = raw.get("name", "").split("/")[1] if "/" in raw.get("name", "") else "unknown"
    review_id = review.get("name", "").split("/")[-1] if "/" in review.get("name", "") else str(uuid.uuid4())
    
    envelope = ReviewEnvelope(
        review_id=review_id,
        platform="google",
        business_id=business_id,
        status="ingested",
        review=ReviewData(
            text=review.get("comment", ""),
            rating=rating,
            author=review.get("reviewer", {}).get("displayName", "Anonymous"),
            timestamp=review.get("createTime", datetime.now(timezone.utc).isoformat()),
            url=f"https://maps.google.com/?cid={business_id}",
            language="en"
        ),
        reasoning_trail=[{
            "agent": "monitor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ingested",
            "note": "Google Business Profile webhook"
        }]
    )
    return envelope.model_dump()

def normalize_yelp(raw: dict) -> dict:
    envelope = ReviewEnvelope(
        review_id=raw.get("id", str(uuid.uuid4())),
        platform="yelp",
        business_id=raw.get("business_id", "unknown"),
        status="ingested",
        review=ReviewData(
            text=raw.get("text", ""),
            rating=raw.get("rating", 3),
            author=raw.get("user", {}).get("name", "Anonymous"),
            timestamp=raw.get("time_created", datetime.now(timezone.utc).isoformat()),
            url=raw.get("url", ""),
            language="en"
        ),
        reasoning_trail=[{
            "agent": "monitor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ingested",
            "note": "Yelp polling"
        }]
    )
    return envelope.model_dump()

def normalize_tripadvisor(raw: dict) -> dict:
    envelope = ReviewEnvelope(
        review_id=str(raw.get("id", uuid.uuid4())),
        platform="tripadvisor",
        business_id=str(raw.get("location_id", "unknown")),
        status="ingested",
        review=ReviewData(
            text=raw.get("text", ""),
            rating=raw.get("rating", 3),
            author=raw.get("user", {}).get("username", "Anonymous"),
            timestamp=raw.get("published_date", datetime.now(timezone.utc).isoformat()),
            url=raw.get("url", ""),
            language="en"
        ),
        reasoning_trail=[{
            "agent": "monitor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ingested",
            "note": "TripAdvisor webhook"
        }]
    )
    return envelope.model_dump()

async def forward_to_monitor(envelope: dict):
    if not BAND_API_KEY or not BAND_ROOM_ID:
        print("Missing BAND_API_KEY or BAND_ROOM_ID in env")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.band.ai/v1/rooms/{BAND_ROOM_ID}/messages",
            headers={"Authorization": f"Bearer {BAND_API_KEY}"},
            json={"content": f"@arkadiusz/monitor-agent {json.dumps(envelope)}"}
        )
        print(f"Band API Response: {resp.status_code} {resp.text}")

@app.post("/webhook/google")
async def google_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    envelope = normalize_review("google", payload)
    background_tasks.add_task(forward_to_monitor, envelope)
    return {"status": "accepted"}

@app.get("/webhook/yelp/poll")
async def yelp_poll(background_tasks: BackgroundTasks):
    """Triggered by cron (e.g. every 15 min via GitHub Actions or cron job)."""
    yelp_api_key = os.environ.get('YELP_API_KEY')
    if not yelp_api_key:
        return {"error": "Missing YELP_API_KEY"}
        
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.yelp.com/v3/businesses/{id}/reviews", # Need actual ID config here in real life
            headers={"Authorization": f"Bearer {yelp_api_key}"}
        )
    if resp.status_code == 200:
        for raw_review in resp.json().get("reviews", []):
            envelope = normalize_review("yelp", raw_review)
            background_tasks.add_task(forward_to_monitor, envelope)
        return {"polled": len(resp.json().get("reviews", []))}
    return {"error": resp.text}

@app.post("/webhook/tripadvisor")
async def tripadvisor_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    envelope = normalize_review("tripadvisor", payload)
    background_tasks.add_task(forward_to_monitor, envelope)
    return {"status": "accepted"}

@app.post("/demo/inject")
async def demo_inject(request: Request, background_tasks: BackgroundTasks):
    """Inject a manual payload directly to trigger the pipeline."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    envelope = normalize_review("demo", payload)
    background_tasks.add_task(forward_to_monitor, envelope)
    return {"status": "accepted", "review_id": envelope["review_id"]}
