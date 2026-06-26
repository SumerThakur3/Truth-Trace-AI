"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    session_id: str | None = None


class SourceSchema(BaseModel):
    id: str
    title: str
    url: str
    snippet: str
    reliability_score: float
    domain: str
    extracted_evidence: list[str] = []


class ContradictionSchema(BaseModel):
    claim: str
    source_a: str
    source_b: str
    evidence_a: str
    evidence_b: str
    severity: Literal["high", "medium", "low"]


class VerificationStepSchema(BaseModel):
    step: str
    status: Literal["pending", "running", "completed", "error"]
    message: str
    timestamp: str | None = None


class TrustReportSchema(BaseModel):
    sources_checked: int
    verification_status: Literal["verified", "partial", "unverified"]
    confidence_score: float
    evidence_quality: float
    source_reliability: float
    contradictions_found: int
    final_trust_rating: str
    reasoning: str
    timeline: list[VerificationStepSchema] = []


class VerificationResultSchema(BaseModel):
    id: str
    question: str
    answer: str
    confidence_score: float
    reliability_level: str
    verification_status: str
    sources: list[SourceSchema]
    contradictions: list[ContradictionSchema]
    trust_report: TrustReportSchema
    claims: list[str]
    created_at: str


class QuestionAnalysis(BaseModel):
    intent: str
    domain: str
    complexity: Literal["low", "medium", "high"]
    key_entities: list[str] = []
    requires_recent_data: bool = False


class DashboardStatsSchema(BaseModel):
    total_queries: int
    verification_rate: float
    average_confidence: float
    sources_used: int
    confidence_trend: list[dict]
    verification_history: list[dict]
    source_reliability: list[dict]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
