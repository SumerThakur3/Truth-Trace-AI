# TruthTrace AI — Deployment Guide

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Vercel (Frontend)](#vercel-frontend)
4. [AWS (Backend)](#aws-backend)
5. [Production Checklist](#production-checklist)

---

## Local Development

### Backend Only

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Only

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## Docker Deployment

### Full Stack

```bash
# Configure environment
cp .env.example .env
# Add your API keys to .env

# Build and start all services
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Services:
| Service | Port | Description |
|---------|------|-------------|
| frontend | 3000 | Next.js application |
| backend | 8000 | FastAPI API server |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |

### Backend Only (Docker)

```bash
cd backend
docker build -t truthtrace-backend .
docker run -p 8000:8000 --env-file ../.env truthtrace-backend
```

---

## Vercel (Frontend)

1. Push code to GitHub
2. Import project in [Vercel Dashboard](https://vercel.com)
3. Set root directory to `frontend`
4. Configure environment variables:

```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
```

5. Deploy

### vercel.json (optional)

Create `frontend/vercel.json`:

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next"
}
```

---

## Render (Backend) + Aiven (MySQL)

### Render environment variables

Set these on your Render Web Service:

```
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=mysql+aiomysql://avnadmin:PASSWORD@HOST:PORT/defaultdb
DATABASE_SSL_REQUIRED=true
TAVILY_API_KEY=your-tavily-key
```

**Important:** Use `mysql+aiomysql://` (not plain `mysql://`). SSL is auto-detected for `aivencloud.com` hosts.

### Verify persistence after deploy

After Render wakes from idle sleep, check:

```
GET https://your-render-app.onrender.com/api/v1/health
```

Response should show:

```json
{
  "database": "connected",
  "stored_verifications": 12
}
```

If `stored_verifications` is 0 after you have asked questions, check Render logs for `save_verification_failed` or `database_unavailable`.

### Why stats reset on free tier (fixed)

Render free tier spins down after ~15 minutes idle. Previously, dashboard data lived only in server memory and was lost on restart. Analytics now **always load from Aiven MySQL** with automatic reconnect after wake-up.

---

## AWS (Backend)

### Option A: ECS Fargate

1. Push backend Docker image to ECR
2. Create ECS task definition with environment variables
3. Configure Application Load Balancer on port 8000
4. Set up RDS PostgreSQL and ElastiCache Redis

### Option B: EC2

```bash
# On EC2 instance
sudo apt update && sudo apt install -y docker.io docker-compose
git clone <repo> && cd TruthTrace
cp .env.example .env
# Configure .env with production values
docker compose up -d backend postgres redis
```

### RDS PostgreSQL

```
DATABASE_URL=postgresql+asyncpg://user:pass@your-rds-endpoint:5432/truthtrace
```

### ElastiCache Redis

```
REDIS_URL=redis://your-elasticache-endpoint:6379/0
```

---

## Production Checklist

### Security
- [ ] Set strong PostgreSQL credentials
- [ ] Enable HTTPS/TLS on all endpoints
- [ ] Configure CORS to allow only your frontend domain
- [ ] Set up Clerk authentication with production keys
- [ ] Rotate API keys regularly
- [ ] Enable rate limiting (default: 30/minute)

### Performance
- [ ] Enable Redis caching
- [ ] Configure CDN for frontend static assets
- [ ] Set appropriate `CACHE_TTL` (default: 3600s)
- [ ] Monitor API response times

### Monitoring
- [ ] Set up health check endpoint: `GET /api/v1/health`
- [ ] Configure CloudWatch / Datadog logging
- [ ] Set up alerts for 5xx errors

### Database
- [ ] Run migrations: tables auto-create on startup
- [ ] Set up automated backups for PostgreSQL
- [ ] Monitor connection pool usage

### Environment Variables (Production)

```env
DEBUG=false
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
CLERK_SECRET_KEY=sk_live_...
RATE_LIMIT=30/minute
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | Check DATABASE_URL and API keys in .env |
| No search results | Configure TAVILY_API_KEY or SERPER_API_KEY |
| Frontend can't reach API | Verify NEXT_PUBLIC_API_URL and CORS settings |
| Low confidence scores | Ensure OpenAI/Anthropic keys are valid |
| Redis connection failed | App falls back to in-memory cache automatically |
| Database connection failed | App runs without persistence; check PostgreSQL |

---

## Health Checks

```bash
# Backend health
curl http://localhost:8000/api/v1/health

# Verify endpoint
curl -X POST http://localhost:8000/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the speed of light?"}'
```
