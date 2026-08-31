"""LLM explainer tests — offline extractive path + citation contract (no network)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.llm import Explainer, answer_question  # noqa: E402

FAKE_MATCH = {
    "scheme_id": "pm-kisan",
    "name": "PM Kisan Samman Nidhi (PM-KISAN)",
    "category": "agriculture",
    "benefit": "₹6,000 per year in 3 installments.",
    "matched": True,
    "confidence": "full",
    "matched_criteria": [
        {"field": "is_landholding_farmer", "note": "Cultivable landholding is primary eligibility"},
    ],
    "missing_info": [],
    "blockers": [],
}

FAKE_CHUNKS = [
    {"chunk": {"text": "PM-KISAN provides ₹6,000 per year to landholding farmer families via DBT.",
               "scheme_id": "pm-kisan", "source_file": "pm-kisan.md", "section": "Overview"}, "score": 0.9},
]


def test_offline_explain_returns_extractive_with_verdict():
    ex = Explainer(offline=True)
    out = ex.explain(FAKE_MATCH, FAKE_CHUNKS, language="hinglish")
    assert out["backend"] == "extractive"
    assert "ELIGIBLE" in out["text"]
    assert "₹6,000" in out["text"] or "PM-KISAN" in out["text"]
    assert "official portal" in out["text"]


def test_offline_explain_missing_info_and_excluded_variants():
    ex = Explainer(offline=True)
    missing = dict(FAKE_MATCH, confidence="missing_info", matched=False,
                   blockers=["Please provide: is_landholding_farmer"])
    out = ex.explain(missing, FAKE_CHUNKS)
    assert "information is missing" in out["text"]
    excluded = dict(FAKE_MATCH, confidence="excluded", matched=False,
                    blockers=["Exclusion: income tax payers in the last assessment year"])
    out2 = ex.explain(excluded, FAKE_CHUNKS)
    assert "NOT eligible" in out2["text"]


def test_citations_numbered_with_provenance():
    ex = Explainer(offline=True)
    out = ex.explain(FAKE_MATCH, FAKE_CHUNKS * 2)
    assert out["citations"][0]["n"] == 1
    assert out["citations"][0]["scheme_id"] == "pm-kisan"
    assert out["citations"][0]["source_file"] == "pm-kisan.md"


def test_answer_question_offline():
    out = answer_question("Who gets PM-KISAN?", FAKE_CHUNKS, offline=True)
    assert out["backend"] == "extractive"
    assert "₹6,000" in out["text"]
    assert "pm-kisan.md" in out["text"]


def test_answer_question_no_chunks():
    out = answer_question("random", [], offline=True)
    assert "No relevant" in out["text"]
    assert out["citations"] == []


def test_backend_property_reflects_mode():
    assert Explainer(offline=True).backend == "extractive"
    assert Explainer(offline=False).backend == "pollinations"
