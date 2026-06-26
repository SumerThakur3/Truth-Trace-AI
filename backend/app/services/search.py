"""Web search integration via Tavily and Serper."""

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse

import httpx
from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.verification import SourceSchema


# Track recently used domains and URLs to ensure diversity across queries
_recent_domains: dict[str, datetime] = {}
_recent_urls: dict[str, datetime] = {}
_domain_access_count: dict[str, int] = defaultdict(int)

RECENCY_WINDOW_SECONDS = 300  # 5 minutes


def _get_query_variations(question: str, key_entities: list[str]) -> list[str]:
    """Generate multiple query variations for better source coverage."""
    queries = [question]

    # Add entity-specific queries
    if key_entities:
        for entity in key_entities[:3]:
            if len(entity.split()) <= 3:
                queries.append(f"{entity} facts")
                queries.append(f"{entity} research study")

    # Add question-type specific queries
    question_lower = question.lower()
    if "health" in question_lower or "medical" in question_lower or "disease" in question_lower:
        queries.append(f"{question} peer-reviewed study")
        queries.append(f"{question} clinical trial")
    elif "climate" in question_lower or "environment" in question_lower:
        queries.append(f"{question} scientific report 2024")
        queries.append(f"{question} IPCC")
    elif "technology" in question_lower or "ai" in question_lower:
        queries.append(f"{question} news 2024")
        queries.append(f"{question} research paper")
    elif "political" in question_lower or "government" in question_lower:
        queries.append(f"{question} official source")
        queries.append(f"{question} news verification")

    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique_queries.append(q)

    return unique_queries[:5]


def _should_include_source(url: str, domain: str) -> bool:
    """Determine if a source should be included based on recency and diversity."""
    now = datetime.now()

    # Clean up old entries
    cutoff = now - timedelta(seconds=RECENCY_WINDOW_SECONDS)
    for key, timestamp in list(_recent_domains.items()):
        if timestamp < cutoff:
            del _recent_domains[key]
    for key, timestamp in list(_recent_urls.items()):
        if timestamp < cutoff:
            del _recent_urls[key]

    # Check URL recency
    if url in _recent_urls:
        return False

    # Check domain diversity - limit to 2 sources per domain in recency window
    if _domain_access_count.get(domain, 0) >= 2:
        # Allow if it's a highly trusted domain
        if domain in TRUSTED_DOMAINS and TRUSTED_DOMAINS[domain] >= 90:
            return _domain_access_count.get(domain, 0) < 4
        return False

    return True


def _record_source_use(url: str, domain: str):
    """Record that a source was used to track diversity."""
    now = datetime.now()
    _recent_urls[url] = now
    _recent_domains[domain] = now
    _domain_access_count[domain] = _domain_access_count.get(domain, 0) + 1


TRUSTED_DOMAINS = {
    "wikipedia.org": 85,
    "who.int": 96,
    "cdc.gov": 95,
    "nih.gov": 95,
    "nejm.org": 98,
    "nature.com": 95,
    "science.org": 94,
    "thelancet.com": 97,
    "reuters.com": 91,
    "apnews.com": 90,
    "bbc.com": 88,
    "arxiv.org": 88,
    "pubmed.ncbi.nlm.nih.gov": 96,
    "gov": 90,
    "edu": 88,
}


def _domain_reliability(url: str, title: str = "", snippet: str = "") -> float:
    domain = urlparse(url).netloc.replace("www.", "")
    text = f"{title} {snippet}".lower()
    if domain in TRUSTED_DOMAINS:
        base = TRUSTED_DOMAINS[domain]
    else:
        base = 72.0
        for key, score in TRUSTED_DOMAINS.items():
            if domain.endswith(key):
                base = score
                break

    if any(term in text for term in ["peer-reviewed", "systematic review", "meta-analysis", "clinical trial"]):
        base += 4
    if any(term in text for term in ["blog", "opinion", "sponsored", "advertisement"]):
        base -= 8
    if len(snippet.strip()) < 80:
        base -= 5
    if urlparse(url).scheme != "https":
        base -= 4

    return max(35.0, min(99.0, float(base)))


def _source_from_parts(title: str, url: str, snippet: str) -> SourceSchema | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    domain = parsed.netloc.replace("www.", "")
    clean_snippet = re.sub(r"\s+", " ", snippet or "").strip()[:500]
    return SourceSchema(
        id=hashlib.md5(url.encode()).hexdigest()[:12],
        title=(title or domain or "Untitled").strip()[:200],
        url=url,
        snippet=clean_snippet,
        reliability_score=_domain_reliability(url, title, clean_snippet),
        domain=domain,
        extracted_evidence=[clean_snippet[:200]] if clean_snippet else [],
    )


async def search_tavily(query: str, max_results: int = 8) -> list[SourceSchema]:
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
        )
        sources = []
        for i, result in enumerate(response.get("results", [])):
            url = result.get("url", "")
            sources.append(
                SourceSchema(
                    id=hashlib.md5(url.encode()).hexdigest()[:12],
                    title=result.get("title", "Untitled"),
                    url=url,
                    snippet=result.get("content", "")[:500],
                    reliability_score=_domain_reliability(
                        url, result.get("title", ""), result.get("content", "")
                    ),
                    domain=urlparse(url).netloc.replace("www.", ""),
                    extracted_evidence=[result.get("content", "")[:200]],
                )
            )
        return sources
    except Exception as e:
        logger.error("tavily_search_failed", error=str(e))
        return []


async def search_serper(query: str, max_results: int = 8) -> list[SourceSchema]:
    settings = get_settings()
    if not settings.serper_api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=settings.search_timeout, verify=False) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.serper_api_key},
                json={"q": query, "num": max_results},
            )
            response.raise_for_status()
            data = response.json()

        sources = []
        for i, result in enumerate(data.get("organic", [])[:max_results]):
            url = result.get("link", "")
            sources.append(
                SourceSchema(
                    id=hashlib.md5(url.encode()).hexdigest()[:12],
                    title=result.get("title", "Untitled"),
                    url=url,
                    snippet=result.get("snippet", "")[:500],
                    reliability_score=_domain_reliability(
                        url, result.get("title", ""), result.get("snippet", "")
                    ),
                    domain=urlparse(url).netloc.replace("www.", ""),
                    extracted_evidence=[result.get("snippet", "")[:200]],
                )
            )
        return sources
    except Exception as e:
        logger.error("serper_search_failed", error=str(e))
        return []


async def search_web(query: str, max_results: int = 10, key_entities: list[str] = None) -> list[SourceSchema]:
    """Search multiple providers with query variations and deduplicate by URL.

    Args:
        query: The main search query
        max_results: Maximum number of results to return
        key_entities: Optional list of key entities for generating query variations
    """
    # Generate query variations for better coverage
    query_variations = _get_query_variations(query, key_entities or [])

    seen: set[str] = set()
    merged: list[SourceSchema] = []

    # Search with different query variations
    for q in query_variations:
        tavily_results = await search_tavily(q, max_results // 2)
        serper_results = await search_serper(q, max_results // 2)

        for source in tavily_results + serper_results:
            if source.url not in seen:
                domain = source.domain

                # Apply diversity filtering
                if _should_include_source(source.url, domain):
                    seen.add(source.url)
                    merged.append(source)
                    _record_source_use(source.url, domain)

        if len(merged) >= max_results:
            break

    # If we don't have enough results from variations, do a final broad search
    if len(merged) < max_results:
        remaining = max_results - len(merged)
        tavily_results = await search_tavily(query, remaining)
        serper_results = await search_serper(query, remaining)

        for source in tavily_results + serper_results:
            if source.url not in seen and len(merged) < max_results:
                domain = source.domain
                if _should_include_source(source.url, domain):
                    seen.add(source.url)
                    merged.append(source)
                    _record_source_use(source.url, domain)

    if not merged:
        merged = await _free_http_search_async(query)

    # Sort by reliability score (highest first) to prioritize trusted sources
    merged.sort(key=lambda s: s.reliability_score, reverse=True)
    return merged[:max_results]


async def _free_http_search_async(query: str) -> list[SourceSchema]:
    """Best-effort search through DDGS, Wikipedia, and DuckDuckGo HTML."""
    sources: list[SourceSchema] = []

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        results = DDGS().text(query, max_results=8)
        for r in results:
            url = r.get("href", r.get("url", ""))
            source = _source_from_parts(
                r.get("title", "Untitled"),
                url,
                r.get("body", r.get("snippet", "")),
            )
            if source:
                sources.append(source)
        if sources:
            logger.info("ddgs_search_success", query=query[:50], count=len(sources))
            return sources
    except Exception as e:
        logger.warning("ddgs_search_failed", error=str(e))

    headers = {"User-Agent": "TruthTraceAI/1.0 (+https://localhost)"}

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers, verify=False) as client:
            wiki = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": 3,
                    "namespace": 0,
                    "format": "json",
                },
            )
            wiki.raise_for_status()
            data = wiki.json()
            for title, snippet, url in zip(data[1], data[2], data[3]):
                source = _source_from_parts(title, url, snippet)
                if source:
                    sources.append(source)

            ddg = await client.get(f"https://duckduckgo.com/html/?q={quote_plus(query)}")
            if ddg.status_code < 400:
                html = ddg.text
                matches = re.findall(
                    r'class="result__a" href="([^"]+)".*?>(.*?)</a>.*?class="result__snippet">(.*?)</a>',
                    html,
                    flags=re.DOTALL,
                )
                for url, title_html, snippet_html in matches[:8]:
                    title = re.sub("<.*?>", "", title_html)
                    snippet = re.sub("<.*?>", "", snippet_html)
                    source = _source_from_parts(title, url, snippet)
                    if source:
                        sources.append(source)
    except Exception as e:
        logger.warning("free_http_search_failed", error=str(e))

    seen: set[str] = set()
    unique: list[SourceSchema] = []
    for source in sources:
        if source.url not in seen:
            seen.add(source.url)
            unique.append(source)
    return unique
