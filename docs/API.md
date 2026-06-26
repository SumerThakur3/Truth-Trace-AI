# TruthTrace AI — API Documentation

Base URL: `http://localhost:8000/api/v1`

Interactive documentation: `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## Authentication

When Clerk is configured, include the session token:

```
Authorization: Bearer <clerk_session_token>
```

Currently optional for development.

---

## Endpoints

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-06-13T12:00:00Z"
}
```

---

### Verify Question

```
POST /verify
```

**Request Body:**
```json
{
  "question": "What are the health benefits of Mediterranean diet?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "id": "uuid",
  "question": "...",
  "answer": "Evidence-based answer...",
  "confidence_score": 94.0,
  "reliability_level": "High Confidence",
  "verification_status": "verified",
  "sources": [
    {
      "id": "abc123",
      "title": "Source Title",
      "url": "https://...",
      "snippet": "Extracted content...",
      "reliability_score": 96.0,
      "domain": "who.int",
      "extracted_evidence": ["Evidence point 1"]
    }
  ],
  "contradictions": [],
  "trust_report": {
    "sources_checked": 12,
    "verification_status": "verified",
    "confidence_score": 94.0,
    "evidence_quality": 91.0,
    "source_reliability": 95.0,
    "contradictions_found": 0,
    "final_trust_rating": "Highly Trustworthy",
    "reasoning": "All claims corroborated...",
    "timeline": [...]
  },
  "claims": ["Claim 1", "Claim 2"],
  "created_at": "2026-06-13T12:00:00Z"
}
```

**Validation:**
- `question`: 3–2000 characters (required)

---

### Verify Question (Streaming)

```
POST /verify/stream
```

Server-Sent Events stream with progress updates.

**Event Types:**

| Type | Description |
|------|-------------|
| `step` | Pipeline step progress |
| `answer` | Partial answer text |
| `complete` | Full verification result |
| `error` | Error message |

**Example SSE Data:**
```
data: {"type": "step", "data": {"step": "Web Search", "status": "running", "message": "Searching..."}}

data: {"type": "complete", "data": { ...full result... }}
```

---

### Dashboard Statistics

```
GET /dashboard/stats
```

**Response:**
```json
{
  "total_queries": 12847,
  "verification_rate": 94.2,
  "average_confidence": 87.5,
  "sources_used": 523891,
  "confidence_trend": [{"date": "Mon", "score": 82}],
  "verification_history": [{"date": "Mon", "verified": 145, "partial": 12, "unverified": 3}],
  "source_reliability": [{"domain": "nejm.org", "score": 98, "count": 1240}]
}
```

---

### Verification History

```
GET /history?limit=20
```

Returns past verification records (requires database connection).

---

## Confidence Levels

| Score | Level | Status |
|-------|-------|--------|
| 90–100% | High Confidence | Verified |
| 70–89% | Medium Confidence | Partial |
| Below 70% | Low Confidence | Unverified |

---

## Agent Pipeline

1. **Question Analyzer** — Intent, domain, complexity detection
2. **Web Search Agent** — Tavily + Serper multi-source search
3. **Retrieval Agent** — ChromaDB RAG context retrieval
4. **Fact Verification Agent** — Claim extraction and verification
5. **Contradiction Agent** — Cross-source disagreement detection
6. **Confidence Agent** — Trust score calculation
7. **Trust Report Agent** — Comprehensive report generation

---

## Error Responses

```json
{
  "detail": "Error message"
}
```

| Status | Description |
|--------|-------------|
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limiting

Default: 30 requests per minute per IP address.

Configure via `RATE_LIMIT` environment variable.
