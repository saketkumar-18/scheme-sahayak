# ETHICS.md — Scheme Sahayak

## 1. Purpose & intended use
Scheme Sahayak helps citizens **discover** government schemes they may qualify for and **understand how to apply**. It is a guidance tool, not a government service, and is not affiliated with any ministry.

## 2. Accuracy & honesty
- **Verdicts are deterministic.** Eligibility decisions come from a rules engine over a curated corpus — never from the LLM. The LLM only *explains* results and answers questions, and it is instructed to use only retrieved context.
- **Every fact is sourced.** Each scheme's criteria are modelled from official sources (PIB, ministry portals, NSP, NHA, PM-KISAN operational guidelines). Each guidance document cites its sources at the bottom. Scheme cards in the UI link directly to official portals.
- **Missing data is never treated as disqualification.** If a profile field is absent, the engine returns "missing_info" and names the field to provide — it does not silently exclude.
- **Limitations.** Rules are a simplification of dense guidelines: state-level variations (pension top-ups, state scholarships), survey-based gates (SECC lists, Awaas+), and discretionary verification (land records, income certificates) cannot be fully modelled. The app says "likely qualify", never "guaranteed".
- **Freshness.** Corpus dated 2026-09-01 (`backend/data/schemes.json` `updated` field). Scheme rules change; the UI carries a persistent disclaimer and links to official portals for verification.

## 3. Privacy
- **No accounts, no tracking, no storage.** The API is stateless. Profiles exist only in the caller's browser and are used for the single matching request. No logs of profiles are kept; no analytics run on page content.
- **No third-party data sharing.** The only external calls the backend makes are to the LLM text API (pollinations), which receives the match context — never the full profile — for explanation generation. The extractive fallback performs zero external calls.

## 4. Fairness & inclusion
- Coverage deliberately spans vulnerable groups the schemes target: SC/ST/OBC students, BPL households, farmers, women, artisans, street vendors, seniors, persons with disabilities.
- The UI is text-first, mobile-friendly, and offers English/हिंदी/Hinglish so language is not a barrier.
- Caste, income, and BPL status are requested **only because the schemes themselves condition benefits on them** — they are used for matching, nothing else.

## 5. LLM use policy
- The LLM never decides eligibility; it explains rules-engine output.
- Prompts enforce "use ONLY provided context; never invent criteria or amounts".
- A deterministic extractive fallback guarantees the service works without any LLM (and keeps it keyless and free); the UI labels which engine produced each answer.

## 6. Security
- Read-only API: no writes, no auth, no personal data at rest → minimal attack surface.
- Input validation on every endpoint (Pydantic); profile fields are strongly typed and bounded (e.g., age 0–120, income ≥ 0).

## 7. Accessibility
- Semantic HTML, keyboard-navigable controls, high-contrast text, no color-only signalling (✅/🟡/❌ paired with words).

## 8. If something is wrong
If you find an incorrect criterion, open a GitHub issue with the official source — the corpus is data-driven and one JSON edit fixes the app.
