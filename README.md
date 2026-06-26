# TruthTrace AI

**Every answer with proof.**

TruthTrace AI is an enterprise-grade fact verification and trust analysis platform. It answers questions with multi-source verification, confidence scoring, contradiction detection, and detailed trust reports.

![TruthTrace AI](https://img.shields.io/badge/TruthTrace-AI-8b5cf6?style=for-the-badge)
![Next.js 15](https://img.shields.io/badge/Next.js-15-black?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square)

## Features

- **Intelligent Chat Interface** — Ask questions and receive verified, evidence-backed answers
- **Confidence Scoring** — Every answer includes a confidence percentage and reliability level
- **Multi-Source Verification** — Cross-references Tavily, Serper, and RAG knowledge base
- **Contradiction Detection** — Identifies and displays source disagreements
- **Trust Reports** — Detailed reports with evidence quality and source reliability
- **Analytics Dashboard** — Recharts and Chart.js visualizations
- **Dark/Light Mode** — Seamless theme switching with glassmorphism UI

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js 15 Frontend                   │
│  Landing │ Chat │ Dashboard │ Theme │ Framer Motion      │
└────────────────────────┬────────────────────────────────┘
                         │ REST / SSE
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌─────────────── Agent Pipeline ───────────────────┐   │
│  │ Question Analyzer → Web Search → RAG Retrieval    │   │
│  │ → Fact Verification → Contradiction Detection   │   │
│  │ → Confidence Scoring → Trust Report             │   │
│  └──────────────────────────────────────────────────┘   │
└──────┬──────────────┬──────────────┬────────────────────┘
       │              │              │
  PostgreSQL       Redis         ChromaDB
```

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- PostgreSQL 16 (optional — app degrades gracefully)
- Redis 7 (optional — falls back to in-memory cache)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd TruthTrace
cp .env.example .env
# Edit .env with your API keys
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Docker (Full Stack)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Demo Mode

Visit `/chat?demo=true` for a fully interactive demo with sample verification data — no API keys required.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Recommended | OpenAI API key for GPT-4o |
| `ANTHROPIC_API_KEY` | Optional | Claude API key (alternative provider) |
| `TAVILY_API_KEY` | Recommended | Tavily web search API |
| `SERPER_API_KEY` | Optional | Google Serper search API |
| `DATABASE_URL` | Optional | PostgreSQL connection string |
| `REDIS_URL` | Optional | Redis connection string |
| `CLERK_SECRET_KEY` | Optional | Clerk authentication |

See `.env.example` for the complete list.

## Project Structure

```
TruthTrace/
├── frontend/                 # Next.js 15 application
│   ├── src/app/             # App router pages
│   ├── src/components/      # UI components
│   └── src/lib/             # Utilities and API client
├── backend/                  # FastAPI application
│   ├── app/agents/          # Agent-based verification pipeline
│   ├── app/api/             # Route handlers
│   ├── app/services/        # LLM, search, RAG services
│   └── tests/               # pytest test suite
├── sample-data/             # Sample verification records
├── docs/                    # API documentation
├── docker-compose.yml       # Full stack deployment
└── DEPLOYMENT.md            # Deployment guide
```

## Testing

```bash
# Backend
cd backend
pytest -v

# Frontend
cd frontend
npm test
```

## API Documentation

- Interactive docs: http://localhost:8000/docs
- Full reference: [docs/API.md](docs/API.md)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion, ShadCN UI |
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| AI | OpenAI GPT-4o, Claude, LangChain |
| RAG | ChromaDB, OpenAI Embeddings |
| Search | Tavily, Serper |
| Database | PostgreSQL, SQLAlchemy |
| Cache | Redis |
| Auth | Clerk |
| Charts | Recharts, Chart.js |
| Deploy | Docker, Vercel, AWS |

## License

MIT
