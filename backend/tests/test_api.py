"""API integration tests via FastAPI TestClient — offline LLM mode."""
import os
import sys
from pathlib import Path

os.environ["LLM_OFFLINE"] = "1"  # force extractive backend before app import

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


FARMER = {
    "age": 35, "gender": "male", "state": "Uttar Pradesh",
    "annual_income": 90000, "social_category": "General",
    "rural_or_urban": "rural", "occupation": "farmer",
    "is_landholding_farmer": True, "is_govt_employee": False,
    "pays_income_tax": False, "family_member_govt_employee": False,
    "owns_pucca_house": False, "has_kutcha_or_homeless": True,
    "bank_account": True,
}

SENIOR = {
    "age": 72, "gender": "female", "state": "Bihar",
    "annual_income": 60000, "social_category": "General",
    "senior_70_plus_in_family": True, "is_bpl": True,
    "rural_or_urban": "rural", "bank_account": True,
}


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["corpus"]["schemes"] == 13


def test_schemes_catalog():
    r = client.get("/api/schemes")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 13
    ids = {s["id"] for s in body["schemes"]}
    assert {"pm-kisan", "ab-pmjay", "pmay-u-2-0", "pmay-g", "pms-sc"} <= ids
    assert all(s.get("sources") for s in body["schemes"])


def test_scheme_detail_and_404():
    r = client.get("/api/schemes/pm-kisan")
    assert r.status_code == 200
    d = r.json()
    assert d["application_steps"] and d["rules"] and d["docs"]
    r404 = client.get("/api/schemes/nope")
    assert r404.status_code == 404


def test_match_farmer_matches_pm_kisan_and_pmay_g():
    r = client.post("/api/match", json={"profile": FARMER})
    assert r.status_code == 200
    body = r.json()
    assert body["matched_count"] >= 2
    results = {x["scheme_id"]: x for x in body["results"]}
    assert results["pm-kisan"]["matched"] is True
    assert results["pm-kisan"]["confidence"] == "full"
    assert results["pmay-g"]["matched"] is True
    # excluded example: urban-only scheme for rural farmer
    assert results["pmay-u-2-0"]["confidence"] == "excluded"


def test_match_senior_matches_abpmjay_and_nsap():
    r = client.post("/api/match", json={"profile": SENIOR})
    assert r.status_code == 200
    results = {x["scheme_id"]: x for x in r.json()["results"]}
    assert results["ab-pmjay"]["matched"] is True
    assert results["nsap-old-age"]["matched"] is True


def test_match_empty_profile_rejected():
    r = client.post("/api/match", json={"profile": {}})
    assert r.status_code == 422


def test_match_with_explanations_offline():
    r = client.post("/api/match", json={"profile": FARMER, "include_explanations": True, "language": "hinglish"})
    assert r.status_code == 200
    body = r.json()
    with_exp = [x for x in body["results"] if "explanation" in x]
    assert with_exp, "explanations missing on top results"
    assert with_exp[0]["explanation"]["backend"] == "extractive"
    assert with_exp[0]["explanation"]["citations"]


def test_explain_endpoint():
    r = client.post("/api/explain", json={"profile": FARMER, "scheme_id": "pm-kisan", "language": "hinglish"})
    assert r.status_code == 200
    body = r.json()
    assert body["match"]["matched"] is True
    assert body["explanation"]["backend"] == "extractive"
    assert body["explanation"]["text"]


def test_explain_404():
    r = client.post("/api/explain", json={"profile": FARMER, "scheme_id": "nope"})
    assert r.status_code == 404


def test_ask_endpoint_relevance():
    r = client.post("/api/ask", json={"question": "What is the income limit for PM Awas Yojana urban?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]["backend"] == "extractive"
    assert "pmay-u-2-0.md" in body["answer"]["text"] or body["answer"]["citations"]


def test_ask_with_scheme_filter():
    r = client.post("/api/ask", json={"question": "income limit", "scheme_id": "pms-sc"})
    assert r.status_code == 200
    for c in r.json()["answer"]["citations"]:
        assert c["scheme_id"] == "pms-sc"


def test_ask_accepts_hindi_language():
    """RED test: language='hi' must be a valid option (guards the Literal typo)."""
    r = client.post("/api/ask", json={"question": "income limit for scholarship", "language": "hi"})
    assert r.status_code == 200, f"language='hi' rejected: {r.text}"


def test_profile_validation_rejects_bad_values():
    r = client.post("/api/match", json={"profile": {"age": 200}})
    assert r.status_code == 422
    r2 = client.post("/api/match", json={"profile": {"social_category": "XYZ"}})
    assert r2.status_code == 422
