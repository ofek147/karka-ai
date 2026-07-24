# karka.ai 🏗️

> פלטפורמת AI לחינוך וחיפוש קרקעות ישראלית

AI-powered platform for understanding Israeli real estate land — education, zoning data, and lead generation.

## Status
🚧 In development — Phase 1: Knowledge Base + API integrations

## Stack
- **Frontend:** Next.js (RTL Hebrew)
- **Backend:** Python FastAPI + LangChain
- **LLM:** Claude (Anthropic)
- **Vector DB:** pgvector (PostgreSQL)
- **Cache:** Redis
- **Data Sources:** ags.iplan.gov.il, govmap.gov.il, data.gov.il

## Project Structure
```
karka-ai/
├── backend/          # Python FastAPI + RAG engine
├── frontend/         # Next.js app
├── knowledge-base/   # Chunked docs, Q&A, scrapers
├── scripts/          # IPLAN wrapper, govmap client
└── .env.example      # Required env vars
```

## Setup
```bash
cp .env.example .env
# Fill in your API keys
```
