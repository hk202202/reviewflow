# ReviewFlow — AI-Powered Review Management SaaS

Multi-tenant SaaS platform for managing e-commerce reviews across Amazon, Flipkart, Myntra, Google Business, and more.

## Stack

- **Frontend**: Next.js 14, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, SQLAlchemy, Celery
- **Database**: PostgreSQL
- **Cache/Queue**: Redis
- **AI**: OpenAI GPT-4o
- **Extension**: Chrome MV3

## Quick Start

```bash
# Copy env file
cp .env.example .env

# Start infrastructure
docker-compose up -d postgres redis

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Celery (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info

# Frontend
cd frontend
npm install
npm run dev

# Landing page
cd landing
npm install
npm run dev
```

## Services

| Service | URL |
|---------|-----|
| Frontend App | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Landing Page | http://localhost:3001 |

## Chrome Extension

Load `extension/` as unpacked extension in Chrome DevTools.
