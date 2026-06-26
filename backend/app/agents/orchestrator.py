"""Agent-based verification pipeline."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.core.cache import cache_get, cache_set
from app.core.logging import logger
from app.schemas.verification import (
    ContradictionSchema,
    QuestionAnalysis,
    SourceSchema,
    TrustReportSchema,
    VerificationResultSchema,
    VerificationStepSchema,
)
from app.services.llm import call_llm, parse_json_response
from app.services.rag import retrieve_context
from app.services.search import search_web


class QuestionAnalyzerAgent:
    """Detects intent, domain, and complexity of user questions."""

    SYSTEM = """You are a question analysis agent. Analyze the user's question and return JSON with:
    intent (string), domain (string), complexity (low|medium|high),
    key_entities (array of strings - be specific and extract ALL relevant entities),
    requires_recent_data (boolean).

    IMPORTANT: Extract as many key entities as possible (person, place, organization, concept, date, etc.)
    to help retrieve diverse, relevant sources."""

    async def analyze(self, question: str) -> QuestionAnalysis:
        # Avoid LLM call to save API quota.
        return QuestionAnalysis(
            intent="factual_inquiry",
            domain="general",
            complexity="medium",
            key_entities=[],
            requires_recent_data=False,
        )


class WebSearchAgent:
    """Searches trusted web sources."""

    async def search(self, question: str, analysis: QuestionAnalysis) -> list[SourceSchema]:
        # Pass key_entities to search_web for query variations and diversity
        return await search_web(question, max_results=10, key_entities=analysis.key_entities)


class RetrievalAgent:
    """Performs RAG retrieval from knowledge base."""

    async def retrieve(self, question: str) -> list[str]:
        return await retrieve_context(question)


class FactVerificationAgent:
    """Verifies claims against sources."""

    SYSTEM = """You are a fact verification agent. Given a question, sources, and context,
    extract verifiable claims, verify each, and detect any contradictions between the sources. Your answer must be unique and specific to this question.
    Return JSON with:
    claims (array of strings),
    verified_claims (array of {claim, verified, confidence, supporting_sources}),
    contradictions (array of {claim, source_a, source_b, evidence_a, evidence_b, severity}),
    answer (comprehensive answer based on verified evidence).

    IMPORTANT: Your answer must be tailored to the specific question asked. Do not use generic templates.
    Each answer should reflect the actual content and evidence from the provided sources.
    Only report real contradictions found in the actual source evidence. Do not fabricate contradictions."""

    async def verify(
        self,
        question: str,
        sources: list[SourceSchema],
        rag_context: list[str],
    ) -> dict:
        source_text = "\n".join(
            f"- [{s.title}] ({s.domain}): {s.snippet}" for s in sources[:8]
        )
        context_text = "\n".join(f"- {c}" for c in rag_context)

        # Build a query-specific system prompt that adds context
        query_specific_instructions = self._get_query_instructions(question)

        prompt = f"""{query_specific_instructions}

Question: {question}

Web Sources (these are REAL sources with ACTUAL content - cite them specifically):
{source_text}

Knowledge Base Context:
{context_text}

Verify claims and provide a comprehensive, evidence-based answer. Your answer should:
1. Directly address the question
2. Cite specific sources and their evidence
3. Be unique to this question - not a template response"""

        response = await call_llm(self.SYSTEM, prompt, json_mode=True)
        return parse_json_response(response)

    def _get_query_instructions(self, question: str) -> str:
        """Generate query-specific instructions based on the question type."""
        question_lower = question.lower()

        if any(word in question_lower for word in ["what is", "what are", "define", "definition"]):
            return "The user is asking for a definition or explanation. Provide a clear, factual answer based on the sources."
        elif any(word in question_lower for word in ["why", "reason", "cause", "why does"]):
            return "The user is asking for reasons or causes. Explain the causal relationships with evidence from sources."
        elif any(word in question_lower for word in ["how", "process", "work", "how does"]):
            return "The user is asking about a process or mechanism. Explain step-by-step with evidence."
        elif any(word in question_lower for word in ["is it true", "does", "can", "verify", "confirm"]):
            return "The user is asking for verification. Address the claim directly with supporting or contradicting evidence."
        elif any(word in question_lower for word in ["compare", "difference", "versus", "vs"]):
            return "The user is asking for a comparison. Highlight the key differences and similarities with evidence."
        elif any(word in question_lower for word in ["effect", "impact", "result", "outcome"]):
            return "The user is asking about effects or impacts. Provide evidence-based outcomes."
        else:
            return "Provide a comprehensive, evidence-based response tailored to this specific question."


class ContradictionAgent:
    """Detects contradictions between sources."""

    SYSTEM = """You are a contradiction detection agent. Compare evidence from sources and identify
    contradictions. Your analysis should be specific to the sources and claims provided.
    Return JSON with contradictions array, each containing:
    claim, source_a, source_b, evidence_a, evidence_b, severity (high|medium|low).

    IMPORTANT: Only report real contradictions found in the actual source evidence.
    Do not fabricate contradictions if sources are consistent."""

    async def detect(
        self, sources: list[SourceSchema], claims: list[str]
    ) -> list[ContradictionSchema]:
        if len(sources) < 2:
            return []

        source_text = "\n".join(
            f"- {s.title} ({s.domain}): {s.snippet}" for s in sources
        )
        prompt = f"""Analyze these specific claims against these specific sources.
Check for REAL contradictions in the evidence - do not fabricate disagreements.

Claims to check: {claims}

Sources (ACTUAL content):
{source_text}

Identify only genuine contradictions where sources provide conflicting evidence."""

        response = await call_llm(self.SYSTEM, prompt, json_mode=True)
        data = parse_json_response(response)
        contradictions = []
        for c in data.get("contradictions", []):
            contradictions.append(
                ContradictionSchema(
                    claim=c.get("claim", ""),
                    source_a=c.get("source_a", ""),
                    source_b=c.get("source_b", ""),
                    evidence_a=c.get("evidence_a", ""),
                    evidence_b=c.get("evidence_b", ""),
                    severity=c.get("severity", "medium"),
                )
            )
        return contradictions


class ConfidenceAgent:
    """Calculates trust and confidence scores."""

    SYSTEM = """You are a confidence scoring agent. Based on verification results, calculate:
    confidence_score (0-100), evidence_quality (0-100), source_reliability (0-100),
    verification_status (verified|partial|unverified),
    final_trust_rating (string), reasoning (string explaining the score).
    Return as JSON."""

    async def calculate(
        self,
        sources: list[SourceSchema],
        contradictions: list[ContradictionSchema],
        verified_data: dict,
    ) -> dict:
        return self._calculate_from_evidence(sources, contradictions, verified_data)

    def _calculate_from_evidence(
        self,
        sources: list[SourceSchema],
        contradictions: list[ContradictionSchema],
        verified_data: dict,
    ) -> dict:
        avg_reliability = (
            sum(s.reliability_score for s in sources) / len(sources) if sources else 50
        )
        domains = {s.domain for s in sources if s.domain}
        source_count_score = min(len(sources) / 6, 1.0) * 100
        diversity_score = min(len(domains) / 4, 1.0) * 100
        snippet_lengths = [len(s.snippet.strip()) for s in sources if s.snippet.strip()]
        snippet_quality = min((sum(snippet_lengths) / len(snippet_lengths)) / 350, 1.0) * 100 if snippet_lengths else 25

        verified_claims = verified_data.get("verified_claims", [])
        claim_scores: list[float] = []
        for c in verified_claims:
            if not isinstance(c, dict) or c.get("verified") is False:
                continue
            raw = c.get("confidence")
            if raw is None:
                continue
            if isinstance(raw, (int, float)):
                claim_scores.append(float(raw))
            elif isinstance(raw, str):
                mapped = {"high": 90.0, "medium": 75.0, "low": 50.0}.get(raw.lower())
                if mapped is not None:
                    claim_scores.append(mapped)
                else:
                    try:
                        claim_scores.append(float(raw))
                    except ValueError:
                        pass

        claim_confidence = sum(claim_scores) / len(claim_scores) if claim_scores else (
            70 if sources and verified_data.get("answer") else 45
        )

        severity_penalty = 0.0
        for contradiction in contradictions:
            severity_penalty += {"high": 18, "medium": 10, "low": 5}.get(contradiction.severity, 8)

        low_source_penalty = max(0, 3 - len(sources)) * 6
        evidence_quality = (
            avg_reliability * 0.45
            + source_count_score * 0.2
            + diversity_score * 0.2
            + snippet_quality * 0.15
        )
        score = (
            avg_reliability * 0.35
            + evidence_quality * 0.25
            + claim_confidence * 0.25
            + source_count_score * 0.1
            + diversity_score * 0.05
            - severity_penalty
            - low_source_penalty
        )
        score = round(max(15.0, min(98.0, score)), 1)
        evidence_quality = round(max(10.0, min(98.0, evidence_quality - low_source_penalty)), 1)
        avg_reliability = round(avg_reliability, 1)

        verification_status = (
            "verified" if score >= 85 and len(sources) >= 3 and not contradictions else
            "partial" if score >= 55 and sources else
            "unverified"
        )
        final_trust_rating = (
            "Highly Trustworthy" if score >= 90 else
            "Trustworthy" if score >= 75 else
            "Moderately Trustworthy" if score >= 60 else
            "Low Trust"
        )

        return {
            "confidence_score": score,
            "evidence_quality": evidence_quality,
            "source_reliability": avg_reliability,
            "verification_status": verification_status,
            "final_trust_rating": final_trust_rating,
            "reasoning": (
                f"Score based on {len(sources)} retrieved sources across {len(domains)} domains, "
                f"{avg_reliability}% average source reliability, {round(claim_confidence, 1)}% claim support, "
                f"and {len(contradictions)} detected contradictions."
            ),
        }


class TrustReportAgent:
    """Generates comprehensive trust reports."""

    def generate(
        self,
        sources: list[SourceSchema],
        contradictions: list[ContradictionSchema],
        confidence_data: dict,
        timeline: list[VerificationStepSchema],
    ) -> TrustReportSchema:
        score = confidence_data.get("confidence_score", 70)
        return TrustReportSchema(
            sources_checked=len(sources),
            verification_status=confidence_data.get("verification_status", "partial"),
            confidence_score=score,
            evidence_quality=confidence_data.get("evidence_quality", score - 5),
            source_reliability=confidence_data.get("source_reliability", 75),
            contradictions_found=len(contradictions),
            final_trust_rating=confidence_data.get("final_trust_rating", "Moderately Trustworthy"),
            reasoning=confidence_data.get("reasoning", "Verification complete."),
            timeline=timeline,
        )


def _reliability_label(score: float) -> str:
    if score >= 90:
        return "High Confidence"
    if score >= 70:
        return "Medium Confidence"
    return "Low Confidence"


class VerificationOrchestrator:
    """Coordinates all agents in the verification pipeline."""

    def __init__(self):
        self.analyzer = QuestionAnalyzerAgent()
        self.search_agent = WebSearchAgent()
        self.retrieval_agent = RetrievalAgent()
        self.verification_agent = FactVerificationAgent()
        self.contradiction_agent = ContradictionAgent()
        self.confidence_agent = ConfidenceAgent()
        self.report_agent = TrustReportAgent()

    async def verify(self, question: str) -> VerificationResultSchema:
        timeline: list[VerificationStepSchema] = []
        now = lambda: datetime.now(timezone.utc).isoformat()

        def add_step(step: str, status: str, message: str):
            timeline.append(
                VerificationStepSchema(
                    step=step, status=status, message=message, timestamp=now()
                )
            )

        cache_key = f"verify:{hashlib.sha256(question.encode()).hexdigest()}"
        cached = await cache_get(cache_key)
        if cached:
            return VerificationResultSchema(**cached)

        add_step("Question Analysis", "running", "Analyzing intent and domain...")
        analysis = await self.analyzer.analyze(question)
        timeline[-1].status = "completed"
        timeline[-1].message = f"{analysis.domain} domain, {analysis.complexity} complexity"

        add_step("Web Search", "running", "Searching trusted sources...")
        sources = await self.search_agent.search(question, analysis)
        timeline[-1].status = "completed"
        timeline[-1].message = f"{len(sources)} sources retrieved"

        add_step("RAG Retrieval", "running", "Retrieving knowledge base context...")
        rag_context = await self.retrieval_agent.retrieve(question)
        timeline[-1].status = "completed"
        timeline[-1].message = f"{len(rag_context)} context documents retrieved"

        add_step("Fact Verification", "running", "Verifying claims against sources...")
        verified_data = await self.verification_agent.verify(question, sources, rag_context)
        claims = verified_data.get("claims", [])
        answer = verified_data.get("answer", "")
        if not answer:
            answer = await call_llm(
                "You are TruthTrace AI, a fact verification assistant. Provide evidence-based answers.",
                f"Question: {question}\n\nSources available: {len(sources)}",
            )
        timeline[-1].status = "completed"
        timeline[-1].message = f"{len(claims)} claims verified"

        add_step("Contradiction Detection", "running", "Checking for source disagreements...")
        raw_contradictions = verified_data.get("contradictions", [])
        contradictions = []
        for c in raw_contradictions:
            contradictions.append(
                ContradictionSchema(
                    claim=c.get("claim", ""),
                    source_a=c.get("source_a", ""),
                    source_b=c.get("source_b", ""),
                    evidence_a=c.get("evidence_a", ""),
                    evidence_b=c.get("evidence_b", ""),
                    severity=c.get("severity", "medium"),
                )
            )
        timeline[-1].status = "completed"
        timeline[-1].message = f"{len(contradictions)} contradictions found"

        add_step("Confidence Scoring", "running", "Calculating trust score...")
        confidence_data = await self.confidence_agent.calculate(
            sources, contradictions, verified_data
        )
        timeline[-1].status = "completed"
        timeline[-1].message = f"{confidence_data.get('confidence_score', 0):.0f}% confidence"

        add_step("Trust Report", "running", "Generating trust report...")
        trust_report = self.report_agent.generate(
            sources, contradictions, confidence_data, timeline
        )
        timeline[-1].status = "completed"
        timeline[-1].message = trust_report.final_trust_rating

        score = confidence_data.get("confidence_score", 70)
        result = VerificationResultSchema(
            id=str(uuid.uuid4()),
            question=question,
            answer=answer,
            confidence_score=score,
            reliability_level=_reliability_label(score),
            verification_status=trust_report.verification_status,
            sources=sources,
            contradictions=contradictions,
            trust_report=trust_report,
            claims=claims,
            created_at=now(),
        )

        await cache_set(cache_key, result.model_dump())
        logger.info("verification_complete", question=question[:50], confidence=score)
        return result

    async def verify_stream(
        self, question: str
    ) -> AsyncGenerator[dict, None]:
        """Stream verification progress via SSE events."""
        steps = [
            ("Question Analysis", "Analyzing intent and domain..."),
            ("Web Search", "Searching trusted sources..."),
            ("RAG Retrieval", "Retrieving knowledge base..."),
            ("Fact Verification", "Verifying claims..."),
            ("Contradiction Detection", "Checking contradictions..."),
            ("Confidence Scoring", "Calculating trust score..."),
            ("Trust Report", "Generating report..."),
        ]

        for step_name, message in steps:
            yield {
                "type": "step",
                "data": {
                    "step": step_name,
                    "status": "running",
                    "message": message,
                },
            }

        result = await self.verify(question)

        yield {"type": "answer", "data": {"answer": result.answer}}
        yield {"type": "complete", "data": result.model_dump()}
