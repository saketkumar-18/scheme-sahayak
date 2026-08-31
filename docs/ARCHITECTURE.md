# ARCHITECTURE.md — Scheme Sahayak

## System overview

```
 Browser (Vercel: React+Vite+Tailwind SPA)
   │  fetch JSON over HTTPS
   ▼
 FastAPI on Render (Docker, uvicorn, port $PORT/8000)
   ├── /api/health      → corpus stats
   ├── /api/schemes      → 13-scheme catalog + official sources
   ├── /api/schemes/{id} → full detail (rules, steps, docs, sources)
   ├── /api/match        → Profile → per-scheme verdicts (+optional explanations)
   ├── /api/explain      → one scheme deep-dive: rules verdict + RAG + LLM
   └── /api/ask          → free-text Q&A grounded in guidance chunks
```

## Modules

### `backend/app/rules_engine.py`
Pure-Python deterministic engine. Scheme rules live in data, not code:
```json
{"field": "annual_income", "op": "lte", "value": 250000, "note": "…"}
{"any_of": [ {"field": "is_bpl", "op": "eq", "value": true},
             {"field": "senior_70_plus_in_family", "op": "eq", "value": true} ]}
```
Ops: `eq, ne, lt, lte, gt, gte, in, range`. Verdicts: `full` (all pass) / `missing_info` (no fails, some fields absent) / `excluded` (≥1 hard fail). Each rule outcome carries the `note` from the corpus → UI shows the exact reason.

### `backend/app/rag.py`
- `chunk_markdown()` — paragraph packer (~600 chars), provenance: `scheme_id`, `source_file`, section heading.
- `BM25` — Okapi BM25, stdlib only (no numpy needed at runtime); devanagari + numeric tokens; small stopword set.
- `SchemeCorpus` — loads `schemes.json` + `guidance/*.md`, builds the index at import time (<100ms for this corpus). Optional fastembed vector layer (`RAG_USE_FASTEMBED=1`) fuses 0.5·BM25 + 0.5·cosine.
- `search(query, k, scheme_id)` — per-scheme filtering for citations on the explain/match paths.

### `backend/app/llm.py`
- **pollinations** keyless OpenAI-compatible endpoint first choice (works from datacenter IPs where anonymous tier is allowed).
- **extractive** fallback: composes verdict + matched criteria + top guidance passage into a cited, honest answer. Never fails, zero network.
- Both return the same contract `{text, backend, citations}`; the UI displays which backend answered.

### `backend/app/main.py`
Pydantic `Profile` (28 optional fields, validated types/ranges) → `model_dump(exclude_none=True)` → engine. CORS from `ALLOWED_ORIGINS` env (`*` supported for this public zero-auth read-only API; localhost defaults for dev).

## Data pipeline

```
official guidelines (PDFs/portals)  →  curated guidance/*.md (13 files, each cites sources)
                                   →  schemes.json (rules DSL + steps + docs + source URLs)
                                   →  in-memory BM25 index at boot (import-time, no cold-start DB)
```

## Testing strategy

| Layer | File | What it proves |
|---|---|---|
| Rules engine | `tests/test_rules_engine.py` | income boundaries (≤₹2.5L, ≤₹9L), any_of groups, age ranges, rural/urban split, sort order |
| RAG | `tests/test_rag.py` | chunk provenance, PM-KISAN/Ayushman queries rank first, scheme filter, sorted scores |
| LLM | `tests/test_llm.py` | extractive contract, verdict wording, citation numbering, no-chunk path |
| API | `tests/test_api.py` | all 6 endpoints, validation 422s, offline explanations |
| E2E | `scripts/e2e_verify.py` | live server: real match for farmer + senior profiles, grounded ask, CORS-checked |

LLM tests run offline (`LLM_OFFLINE=1`) → CI never depends on an external LLM.

## Deployment topology

- **Render (free 512MB):** Dockerfile installs backend deps only (fastapi/uvicorn/pydantic ≈ 60MB) — BM25-only retrieval keeps RSS ~90MB. Health `/api/health`.
- **Vercel:** static `frontend/dist`; `VITE_API_URL` baked at build → change requires rebuild (standard Vite behavior).
- **CI (GitHub Actions):** pytest → frontend `tsc -b && vite build` → uvicorn boot smoke test.

## Trade-offs made

1. **BM25 over vector embeddings** — the corpus is 13 small documents; BM25 wins on memory, cold-start, determinism, and zero model download. The vector layer is a flag, not a dependency.
2. **Curated corpus over live scraping** — official portals are slow/JS-heavy; a reviewed, dated, sourced corpus is more trustworthy for eligibility decisions. Freshness documented in ETHICS.md.
3. **Keyless LLM with fallback** — no API key management, no cost, still fully functional when the LLM is unreachable (extractive answers with citations).
4. **Rules-as-data (JSON DSL)** — non-engineers can fix a criterion with a JSON edit; tests pin the semantics.
