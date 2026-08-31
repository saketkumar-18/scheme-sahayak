#!/usr/bin/env python3"""Live E2E verification of Scheme Sahayak API against a running uvicorn server."""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {extra}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode())


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


FARMER = {
    "age": 35, "gender": "male", "state": "Uttar Pradesh",
    "annual_income": 90000, "social_category": "General",
    "rural_or_urban": "rural", "occupation": "farmer",
    "is_landholding_farmer": True, "is_govt_employee": False,
    "pays_income_tax": False, "family_member_govt_employee": False,
    "owns_pucca_house": False, "has_kutcha_or_homeless": True,
    "bank_account": True,
}

print("== health ==")
h = get("/api/health")
check("health ok", h.get("status") == "ok")
check("13 schemes", h.get("corpus", {}).get("schemes") == 13)

print("== schemes ==")
s = get("/api/schemes")
check("catalog count 13", s.get("count") == 13)

print("== match (farmer, LLM explanations ON) ==")
m = post("/api/match", {"profile": FARMER, "language": "hinglish", "include_explanations": True})
res = {x["scheme_id"]: x for x in m["results"]}
check("pm-kisan full match", res["pm-kisan"]["matched"] is True and res["pm-kisan"]["confidence"] == "full")
check("pmay-g full match", res["pmay-g"]["matched"] is True)
check("pmay-u excluded (rural)", res["pmay-u-2-0"]["confidence"] == "excluded")
check("matched_count >= 2", m["matched_count"] >= 2)
exps = [x for x in m["results"] if "explanation" in x]
check("explanations present", len(exps) >= 1)
if exps:
    e = exps[0]["explanation"]
    check("explanation text non-trivial", len(e.get("text", "")) > 40, f"backend={e.get('backend')}")
    print(f"       explainer backend = {e['backend']}")
    check("explanation has citations", len(e.get("citations", [])) >= 1)

print("== explain (SC student) ==")
SC_STUDENT = {"social_category": "SC", "is_student": True, "annual_income": 200000, "age": 19}
e2 = post("/api/explain", {"profile": SC_STUDENT, "scheme_id": "pms-sc", "language": "en"})
check("pms-sc matches SC student", e2["match"]["matched"] is True)
check("explain backend responds", len(e2["explanation"]["text"]) > 30)
print(f"       explainer backend = {e2['explanation']['backend']}")

print("== ask (grounded QA) ==")
a = post("/api/ask", {"question": "What is the income limit for PMAY-U 2.0?"})
check("ask returns answer", len(a["answer"]["text"]) > 30)
check("ask cites guidance", len(a["answer"]["citations"]) >= 1)

print("== validation ==")
import urllib.error
try:
    post("/api/match", {"profile": {"age": 200}})
    check("age 200 rejected", False)
except urllib.error.HTTPError as ex:
    check("age 200 rejected", ex.code == 422)

print(f"\nE2E RESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
