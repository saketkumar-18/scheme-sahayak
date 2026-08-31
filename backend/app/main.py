"""Scheme Sahayak — FastAPI application.

Endpoints:
  GET  /api/health          — service + corpus stats
  GET  /api/schemes         — catalog (id, name, category, benefit, sources)
  GET  /api/schemes/{id}    — full scheme detail incl. rules + steps + sources
  POST /api/match           — profile → rules-engine matches (+ optional per-scheme RAG citations)
  POST /api/explain         — one match result + scheme → LLM explanation (pollinations → extractive)
  POST /api/ask             — free-text question → RAG chunks → grounded answer
CORS: allow Vercel frontend origin (env FRONTEND_ORIGIN) + localhost dev.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .rag import SchemeCorpus
from .rules_engine import evaluate_scheme, match_all, result_to_dict
from .llm import Explainer, answer_question

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

app = FastAPI(
    title="Scheme Sahayak API",
    description="Government Scheme Eligibility Matcher — rules engine + RAG + LLM explanations",
    version="1.0.0",
)

_allowed_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if _allowed_env == "*":
    # Public, zero-auth, no-storage API: open CORS is intentional (see ETHICS.md)
    _origins = ["*"]
else:
    _origins = [o.strip() for o in _allowed_env.split(",") if o.strip()] if _allowed_env else []
_origins += [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

corpus = SchemeCorpus(DATA_DIR)
explainer = Explainer(
    model=os.getenv("LLM_MODEL", "openai"),
    offline=os.getenv("LLM_OFFLINE", "0") == "1",
)


# ---------------- models ----------------
class Profile(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Literal["male", "female", "other"]] = None
    annual_income: Optional[float] = Field(None, ge=0)
    social_category: Optional[Literal["SC", "ST", "OBC", "General", "EWS"]] = None
    state: Optional[str] = Field(None, max_length=60)
    occupation: Optional[str] = None
    is_landholding_farmer: Optional[bool] = None
    owns_pucca_house: Optional[bool] = None
    has_kutcha_or_homeless: Optional[bool] = None
    is_bpl: Optional[bool] = None
    is_student: Optional[bool] = None
    education_level: Optional[str] = None
    is_govt_employee: Optional[bool] = None
    pays_income_tax: Optional[bool] = None
    family_member_govt_employee: Optional[bool] = None
    is_married: Optional[bool] = None
    girl_below_10_in_family: Optional[bool] = None
    family_size: Optional[int] = Field(None, ge=1, le=20)
    is_street_vendor: Optional[bool] = None
    has_vending_certificate: Optional[bool] = None
    is_artisan_or_tradeworker: Optional[bool] = None
    wants_business_loan: Optional[bool] = None
    senior_70_plus_in_family: Optional[bool] = None
    rural_or_urban: Optional[Literal["rural", "urban"]] = None
    disability: Optional[bool] = None
    widow: Optional[bool] = None
    bank_account: Optional[bool] = None
    aadhaar_linked_bank: Optional[bool] = None


class MatchRequest(BaseModel):
    profile: Profile
    language: Literal["en", "hi", "hinglish"] = "en"
    include_explanations: bool = False
    max_explanations: int = Field(3, ge=1, le=5)


class ExplainRequest(BaseModel):
    profile: Profile
    scheme_id: str
    language: Literal["en", "hi", "hinglish"] = "en"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    scheme_id: Optional[str] = None
    language: Literal["en", "hi", "hinglish"] = "en"


# ---------------- helpers ----------------
def _scheme_public(s: dict) -> dict:
    return {
        "id": s["id"],
        "name": s["name"],
        "ministry": s.get("ministry"),
        "category": s.get("category"),
        "benefit": s.get("benefit"),
        "summary": s.get("summary"),
        "sources": s.get("sources", []),
    }


def _scheme_detail(s: dict) -> dict:
    d = _scheme_public(s)
    d.update({
        "rules": s.get("rules", []),
        "application_steps": s.get("application_steps", []),
        "docs": s.get("docs", []),
    })
    return d


# ---------------- endpoints ----------------
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "scheme-sahayak",
        "version": "1.0.0",
        "corpus": corpus.stats(),
    }


@app.get("/api/schemes")
def list_schemes() -> dict:
    return {"count": len(corpus.schemes), "schemes": [_scheme_public(s) for s in corpus.schemes]}


@app.get("/api/schemes/{scheme_id}")
def scheme_detail(scheme_id: str) -> dict:
    s = corpus.get_scheme(scheme_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"scheme '{scheme_id}' not found")
    return _scheme_detail(s)


@app.post("/api/match")
def match(req: MatchRequest) -> dict:
    profile = req.profile.model_dump(exclude_none=True)
    if not profile:
        raise HTTPException(status_code=422, detail="profile must have at least one field")
    results = match_all(profile, corpus.schemes)
    out = [result_to_dict(r) for r in results]
    if req.include_explanations:
        top = [r for r in results if r.matched or r.confidence == "missing_info"][: req.max_explanations]
        for r in top:
            chunks = corpus.search(f"{r.name} eligibility criteria benefits", k=2, scheme_id=r.scheme_id)
            exp = explainer.explain(result_to_dict(r), chunks, req.language)
            for item in out:
                if item["scheme_id"] == r.scheme_id:
                    item["explanation"] = exp
    return {
        "profile": profile,
        "matched_count": sum(1 for r in results if r.matched),
        "results": out,
    }


@app.post("/api/explain")
def explain(req: ExplainRequest) -> dict:
    s = corpus.get_scheme(req.scheme_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"scheme '{req.scheme_id}' not found")
    profile = req.profile.model_dump(exclude_none=True)
    result = evaluate_scheme(profile, s)
    rd = result_to_dict(result)
    chunks = corpus.search(f"{s['name']} eligibility criteria documents", k=3, scheme_id=req.scheme_id)
    exp = explainer.explain(rd, chunks, req.language)
    return {"match": rd, "explanation": exp, "scheme": _scheme_public(s)}


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    chunks = corpus.search(req.question, k=4, scheme_id=req.scheme_id)
    if not chunks:
        return {
            "answer": {"text": "No relevant scheme guidance found. Try naming a scheme or benefit.",
                       "backend": "extractive", "citations": []},
            "question": req.question,
        }
    ans = answer_question(req.question, chunks, language=req.language)
    return {"answer": ans, "question": req.question}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
