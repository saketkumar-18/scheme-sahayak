# Scheme Sahayak 🇮🇳

**Government Scheme Eligibility Matcher** — enter your profile (income, caste, state, occupation, household) and instantly see exactly which Indian government schemes you qualify for — PMAY-U/G, Ayushman Bharat (PM-JAY), PM-KISAN, Post-Matric Scholarships, PM Vishwakarma, PM SVANidhi, Stand-Up India, Atal Pension, Sukanya Samriddhi, PM Ujjwala 2.0 and NSAP pensions — with **application steps, documents, and official sources** for each.

**Live:** Frontend on Vercel · API on Render (links below)

---

## Why this exists

Crores of Indians miss benefits they're entitled to simply because eligibility rules are scattered across dozens of PDFs and portals. Scheme Sahayak models those rules **as code** (a deterministic rules engine — no hallucination in the verdict itself), grounds explanations in a RAG index built from official guidance, and generates friendly per-scheme explanations with an LLM **that falls back to extractive answering** if the LLM is unavailable.

## Features

- **13 schemes** modelled from official guidelines (PIB, ministry portals, NSP, NHA, PM-KISAN operational guidelines)
- **Deterministic eligibility** — every verdict is a rules-engine decision with the exact criterion that passed/failed
- **Missing-info awareness** — the engine never says "not eligible" when data is simply absent; it tells you what to add
- **Grounded explanations** — BM25-hybrid RAG over per-scheme guidance chunks with citations; LLM answers only from retrieved context, with an always-available extractive fallback
- **Apply-ready output** — numbered application steps, document checklist, and the official source link for every scheme
- **3 languages** — English / हिंदी / Hinglish explanation modes
- **Privacy-first** — profile stays in your browser; the API is stateless and stores nothing

## Architecture

```
┌──────────────┐    POST /api/match     ┌───────────────────────────────┐
│  React + Vite │ ─────────────────────▶ │        FastAPI backend        │
│  (Vercel)    │ ◀───────────────────── │  ┌─────────────────────────┐ │
└──────────────┘   JSON: matches +      │  │  Rules engine (DSL)     │ │
                   steps + sources      │  │  evaluate per scheme    │ │
                                        │  └───────────┬─────────────┘ │
                                        │  ┌───────────▼─────────────┐ │
                                        │  │  Hybrid RAG (BM25)      │ │
                                        │  │  over guidance corpus   │ │
                                        │  └───────────┬─────────────┘ │
                                        │  ┌───────────▼─────────────┐ │
                                        │  │  LLM explainer          │ │
                                        │  │  pollinations → extract │ │
                                        │  └─────────────────────────┘ │
                                        └───────────────────────────────┘
```

- `backend/data/schemes.json` — 13 schemes × rules DSL (`eq/lte/gte/in/range/any_of`) × application steps × docs × official sources
- `backend/data/guidance/*.md` — 13 guidance documents authored from official sources (each cites its sources at the bottom)
- `backend/app/rules_engine.py` — deterministic evaluation: `full` / `missing_info` / `excluded` verdicts
- `backend/app/rag.py` — chunking with provenance + BM25 (stdlib-only; optional fastembed vector layer via `RAG_USE_FASTEMBED=1`)
- `backend/app/llm.py` — keyless pollinations API first, extractive fallback always
- `backend/app/main.py` — FastAPI: `/api/health`, `/api/schemes`, `/api/schemes/{id}`, `/api/match`, `/api/explain`, `/api/ask`

## Quick start (local)

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # or uv venv
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# Frontend (new terminal)
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## Tests

```bash
cd backend && pytest tests/ -q
# 41 tests: rules engine boundaries, RAG relevance, LLM fallback contract, API integration
```

## Deployment

- **API (Render, free tier):** Docker image, `/api/health` healthcheck, BM25-only (fits 512MB)
- **Frontend (Vercel):** static build, `VITE_API_URL` baked at build time
- CI: GitHub Actions — backend tests, frontend type-check/build, server-boot smoke test

## Data freshness & disclaimer

Rules were modelled from official sources as of **September 2026**. Schemes evolve — always verify on the official portal (linked on every scheme card) before applying. See `docs/ETHICS.md` for limitations, fairness notes, and privacy stance.

## License

MIT
