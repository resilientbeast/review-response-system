"""All Pydantic v2 models for inter-agent handoff payloads."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from datetime import datetime
import uuid


class ReviewData(BaseModel):
    text: str
    rating: int
    author: str
    timestamp: str
    url: str
    language: str = "en"


class TriageData(BaseModel):
    sentiment: Optional[Literal["positive", "neutral", "negative", "mixed"]] = None
    urgency: Optional[Literal["low", "medium", "high", "critical"]] = None
    category: Optional[Literal["service", "product", "staff", "facility", "pricing", "other"]] = None
    confidence: Optional[float] = None
    escalate_flag: Optional[bool] = None
    reasoning: Optional[str] = None


class BrandVoice(BaseModel):
    tone: str
    formality: float
    keywords_to_include: list[str] = Field(default_factory=list)
    keywords_to_avoid: list[str] = Field(default_factory=list)


class PlatformRules(BaseModel):
    max_response_length: int
    allows_markdown: bool
    requires_disclosure: bool


class SimilarPastResponse(BaseModel):
    review_text: str
    response_text: str
    qa_score: Optional[float] = None
    tone_tags: Optional[str] = None


class ResearchData(BaseModel):
    business_name: Optional[str] = None
    brand_voice: Optional[BrandVoice] = None
    platform_rules: Optional[PlatformRules] = None
    similar_past_responses: list[SimilarPastResponse] = Field(default_factory=list)
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    past_context_summary: Optional[str] = None


class DraftData(BaseModel):
    response_text: Optional[str] = None
    version: int = 0
    word_count: Optional[int] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None


class QAData(BaseModel):
    passed: bool = False
    revision_count: int = 0
    checks: Dict[str, Any] = Field(default_factory=dict)
    feedback_to_drafter: Optional[str] = None
    confidence: Optional[float] = None
    overall_score: Optional[float] = None
    hard_fail_triggers: list[str] = Field(default_factory=list)


class EscalationData(BaseModel):
    required: bool = False
    reason: Optional[str] = None
    assignee: Optional[str] = None
    status: Literal["pending", "assigned", "resolved"] = "pending"
    notified_at: Optional[str] = None


class ReasoningTrailEntry(BaseModel):
    agent: str
    timestamp: str
    action: str
    note: str


class ReviewEnvelope(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "2.0"
    platform: Literal["google", "yelp", "tripadvisor"]
    business_id: str
    status: Literal["ingested", "triaged", "researching", "drafting", "qa_review", "escalated", "approved", "published"]
    
    review: ReviewData
    triage: TriageData = Field(default_factory=TriageData)
    research: ResearchData = Field(default_factory=ResearchData)
    draft: DraftData = Field(default_factory=DraftData)
    qa: QAData = Field(default_factory=QAData)
    escalation: EscalationData = Field(default_factory=EscalationData)
    
    reasoning_trail: list[ReasoningTrailEntry] = Field(default_factory=list)
    
    final_response: Optional[str] = None
    published_at: Optional[str] = None
