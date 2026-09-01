#!/usr/bin/env python3"""Live E2E verification of Scheme Sahayak deployed API (Vercel)."""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("BASE_URL", "https://scheme-sahayak-1jf1pde8z-sakets-projects-260aa991.vercel.app")
PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    print(("  ok    " if cond else "  FAIL  ") + name + (" " + extra if (extra and not cond) else ""))
    if cond:
        PASS += 1
    else:
        FAIL += 1


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
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

print("BASE:", BASE)
print("== health ==")
h = get("/api/health")
check("health ok", h.get("status") == "ok", str(h)[:100])
check("13 schemes in corpus", h.get("corpus", {}).get("schemes") == 13)

print("== schemes ==")
s = get("/api/schemes")
check("catalog 13", s.get("count") == 13)

print("== match (farmer) ==")
m = post("/api/match", {"profile": FARMER, "language": "hinglish", "include_explanations": True})
res = {x["scheme_id"]: x for x in m["results"]}
check("pm-kisan full", res["pm-kisan"]["matched"] is True)
check("pmay-g full", res["pmay-g"]["matched"] is True)
check("pmay-u excluded (rural profile)", res["pmay-u-2-0"]["confidence"] == "excluded")
exps = [x for x in m["results"] if "explanation" in x]
check("explanations attached", len(exps) >= 1)
if exps:
    print("       explainer backend =", exps[0]["explanation"]["backend"])
    check("explanation cited", len(exps[0]["explanation"]["citations"]) >= 1)
    print("       sample explanation:", exps[0]["explanation"]["text"][:150].replace("\n", " "))

print("== ask ==")
a = post("/api/ask", {"question": "What is the income limit for PMAY-U 2.0?"})
check("ask answered", len(a["answer"]["text"]) > 30)
check("ask cited", len(a["answer"]["citations"]) >= 1)
print("       answer preview:", a["answer"]["text"][:120].replace("\n", " "))

print("== explain (SC student) ==")
e2 = post("/api/explain", {"profile": {"social_category": "SC", "is_student": True, "annual_income": 200000, "age": 19}, "scheme_id": "pms-sc", "language": "en"})
check("pms-sc matched", e2["match"]["matched"] is True)

print("== CORS preflight ==")
req = urllib.request.Request(BASE + "/api/match", method="OPTIONS",
    headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"})
with urllib.request.urlopen(req, timeout=30) as r:
    check("cors allow-origin present", r.headers.get("access-control-allow-origin") is not None)

print(f"\nLIVE E2E: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
