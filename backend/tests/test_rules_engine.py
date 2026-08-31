"""Rules engine tests — the deterministic core of Scheme Sahayak."""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.rag import SchemeCorpus  # noqa: E402
from app.rules_engine import evaluate_scheme, match_all, result_to_dict  # noqa: E402

DATA = BACKEND / "data"
corpus = SchemeCorpus(DATA)


def by_id(results):
    return {r.scheme_id: r for r in results}


# ---------- corpus sanity ----------
def test_corpus_loads_13_schemes():
    assert len(corpus.schemes) == 13


def test_corpus_has_guidance_chunks_for_all_schemes():
    ids_with_chunks = {c.scheme_id for c in corpus.chunks}
    for s in corpus.schemes:
        assert s["id"] in ids_with_chunks, f"no guidance chunks for {s['id']}"


# ---------- PM-KISAN ----------
def test_pm_kisan_eligible_farmer():
    profile = {
        "is_landholding_farmer": True,
        "is_govt_employee": False,
        "pays_income_tax": False,
        "family_member_govt_employee": False,
    }
    r = evaluate_scheme(profile, corpus.get_scheme("pm-kisan"))
    assert r.matched and r.confidence == "full"
    assert "₹6,000" in r.benefit


def test_pm_kisan_excluded_income_tax_payer():
    profile = {
        "is_landholding_farmer": True,
        "is_govt_employee": False,
        "pays_income_tax": True,
        "family_member_govt_employee": False,
    }
    r = evaluate_scheme(profile, corpus.get_scheme("pm-kisan"))
    assert not r.matched and r.confidence == "excluded"
    assert any("income tax" in b.lower() for b in r.blockers)


def test_pm_kisan_missing_info_when_land_unknown():
    r = evaluate_scheme({}, corpus.get_scheme("pm-kisan"))
    assert r.confidence == "missing_info"
    assert not r.matched


# ---------- income boundaries ----------
def test_pms_sc_income_boundary_250000():
    base = {"social_category": "SC", "is_student": True}
    r_at = evaluate_scheme(base | {"annual_income": 250000}, corpus.get_scheme("pms-sc"))
    assert r_at.matched, "₹2,50,000 exactly must pass (lte)"
    r_over = evaluate_scheme(base | {"annual_income": 250001}, corpus.get_scheme("pms-sc"))
    assert r_over.confidence == "excluded" and not r_over.matched


def test_pmay_u_income_ceiling_9l():
    base = {"rural_or_urban": "urban", "owns_pucca_house": False}
    r = evaluate_scheme(base | {"annual_income": 900000}, corpus.get_scheme("pmay-u-2-0"))
    assert r.matched, "₹9,00,000 (MIG ceiling) must pass"
    r2 = evaluate_scheme(base | {"annual_income": 900001}, corpus.get_scheme("pmay-u-2-0"))
    assert r2.confidence == "excluded"


# ---------- any_of groups ----------
def test_abpmjay_bpl_or_70plus_group():
    s = corpus.get_scheme("ab-pmjay")
    r1 = evaluate_scheme({"is_bpl": True}, s)
    assert r1.matched, "BPL alone must satisfy the any_of group"
    r2 = evaluate_scheme({"senior_70_plus_in_family": True}, s)
    assert r2.matched, "70+ senior alone must satisfy the any_of group (Vay Vandana)"
    r3 = evaluate_scheme({"is_bpl": False, "senior_70_plus_in_family": False}, s)
    assert r3.confidence == "excluded" and not r3.matched


def test_standup_india_sc_or_woman():
    s = corpus.get_scheme("stand-up-india")
    sc_man = {"social_category": "SC", "age": 30, "wants_business_loan": True}
    assert evaluate_scheme(sc_man, s).matched
    gen_woman = {"social_category": "General", "gender": "female", "age": 30, "wants_business_loan": True}
    assert evaluate_scheme(gen_woman, s).matched
    gen_man = {"social_category": "General", "gender": "male", "age": 30, "wants_business_loan": True}
    r = evaluate_scheme(gen_man, s)
    assert r.confidence == "excluded" and not r.matched


# ---------- age range ----------
def test_atal_pension_age_range():
    s = corpus.get_scheme("atal-pension-yojana")
    assert evaluate_scheme({"age": 18, "bank_account": True, "is_govt_employee": False}, s).matched
    assert evaluate_scheme({"age": 40, "bank_account": True, "is_govt_employee": False}, s).matched
    r = evaluate_scheme({"age": 41, "bank_account": True, "is_govt_employee": False}, s)
    assert r.confidence == "excluded"
    r = evaluate_scheme({"age": 17, "bank_account": True, "is_govt_employee": False}, s)
    assert r.confidence == "excluded"


# ---------- urban/rural split ----------
def test_pmay_g_rural_only_and_kutcha():
    s = corpus.get_scheme("pmay-g")
    r = evaluate_scheme({"rural_or_urban": "rural", "has_kutcha_or_homeless": True, "owns_pucca_house": False}, s)
    assert r.matched
    r_urban = evaluate_scheme({"rural_or_urban": "urban", "has_kutcha_or_homeless": True, "owns_pucca_house": False}, s)
    assert r_urban.confidence == "excluded"


# ---------- sorting ----------
def test_match_all_sorts_matched_first():
    profile = {
        "is_landholding_farmer": True, "is_govt_employee": False,
        "pays_income_tax": False, "family_member_govt_employee": False,
        "rural_or_urban": "rural", "has_kutcha_or_homeless": True, "owns_pucca_house": False,
        "age": 35,
    }
    results = match_all(profile, corpus.schemes)
    confidences = [r.confidence for r in results]
    assert "full" in confidences
    # all 'full' before any 'excluded'
    first_excluded = confidences.index("excluded")
    assert all(c in ("full", "missing_info") for c in confidences[:first_excluded])


def test_result_to_dict_shape():
    profile = {"is_landholding_farmer": True, "is_govt_employee": False,
               "pays_income_tax": False, "family_member_govt_employee": False}
    r = evaluate_scheme(profile, corpus.get_scheme("pm-kisan"))
    d = result_to_dict(r)
    assert set(d) >= {"scheme_id", "name", "category", "benefit", "matched",
                      "confidence", "score", "matched_criteria", "missing_info", "blockers"}
    assert d["matched"] is True and d["confidence"] == "full"
