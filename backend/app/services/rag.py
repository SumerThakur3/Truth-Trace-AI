"""Lightweight local RAG retrieval without external embedding APIs."""

import re

from app.core.logging import logger

SAMPLE_KNOWLEDGE = [
    {
        "content": (
            "The Mediterranean diet emphasizes fruits, vegetables, whole grains, legumes, "
            "olive oil, and moderate fish consumption. Multiple meta-analyses confirm "
            "30% reduction in cardiovascular disease risk."
        ),
        "metadata": {"source": "nutrition_research", "domain": "health"},
        "keywords": ["mediterranean", "diet", "health", "cardiovascular", "nutrition"],
    },
    {
        "content": (
            "Climate change acceleration: IPCC AR6 reports global surface temperature "
            "has risen 1.1°C since pre-industrial times, with accelerating ice sheet loss "
            "in Greenland and Antarctica exceeding earlier model predictions."
        ),
        "metadata": {"source": "ipcc_report", "domain": "climate"},
        "keywords": ["climate", "ipcc", "warming", "environment", "hoax", "change"],
    },
    {
        "content": (
            "mRNA vaccines demonstrate 90-95% efficacy against severe COVID-19 in clinical trials. "
            "Real-world effectiveness remains high against severe outcomes despite variant evolution."
        ),
        "metadata": {"source": "vaccine_research", "domain": "health"},
        "keywords": ["mrna", "vaccine", "covid", "efficacy", "immunization"],
    },
    {
        "content": (
            "Intermittent fasting research shows potential benefits for metabolic health, "
            "including improved insulin sensitivity and autophagy activation in animal studies. "
            "Human longevity data remains limited but promising."
        ),
        "metadata": {"source": "longevity_research", "domain": "health"},
        "keywords": ["fasting", "longevity", "metabolic", "health", "intermittent"],
    },
    {
        "content": (
            "Artificial Intelligence (AI) refers to computer systems designed to perform tasks "
            "that typically require human intelligence, including learning, reasoning, and "
            "problem-solving. Modern AI uses machine learning and neural networks."
        ),
        "metadata": {"source": "ai_overview", "domain": "technology"},
        "keywords": ["artificial", "intelligence", "ai", "machine", "learning", "neural"],
    },
    {
        "content": (
            "Fact verification best practices: cross-reference at least 3 independent sources, "
            "prioritize primary sources and peer-reviewed research, check publication dates, "
            "and assess author credentials and potential conflicts of interest."
        ),
        "metadata": {"source": "verification_guide", "domain": "methodology"},
        "keywords": ["fact", "verification", "sources", "evidence", "trust"],
    },
]


async def init_vectorstore() -> None:
    """No-op: local keyword retrieval requires no initialization."""
    logger.info("local_rag_ready", documents=len(SAMPLE_KNOWLEDGE))


def _score_document(query: str, doc: dict) -> float:
    query_lower = query.lower()
    query_words = set(re.findall(r"\w+", query_lower))
    score = 0.0

    content_lower = doc["content"].lower()
    for word in query_words:
        if len(word) < 3:
            continue
        if word in content_lower:
            score += 2.0
        for kw in doc.get("keywords", []):
            if word in kw or kw in word:
                score += 1.5

    if doc["metadata"].get("domain", "") in query_lower:
        score += 3.0

    return score


async def retrieve_context(query: str, k: int = 4) -> list[str]:
    """Retrieve relevant context using keyword scoring (no external API)."""
    scored = [(doc, _score_document(query, doc)) for doc in SAMPLE_KNOWLEDGE]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = [doc["content"] for doc, s in scored if s > 0][:k]
    if not results:
        results = [doc["content"] for doc in SAMPLE_KNOWLEDGE[:k]]
    return results
