"""Scheme Sahayak — LLM explainer with graceful degradation.

Backends (first available wins):
1. pollinations — keyless hosted text API (https://text.pollinations.ai/openai)
2. extractive  — offline fallback: keyword-rank retrieved sentences into a
                 cited answer (never fails; used in tests and if network is down)

Contract: explain(profile_result, chunks) -> {"text": str, "backend": str, "citations": [...]}
"""
from __future__ import annotations

import re
import urllib.request
import urllib.error
import json
from typing import Any, Optional

POLLINATIONS_URL = "https://text.pollinations.ai/openai"
REQUEST_TIMEOUT = float(20)

SYSTEM_PROMPT = (
    "You are Scheme Sahayak, an assistant that explains Indian government scheme "
    "eligibility results to citizens. Use ONLY the provided eligibility context; "
    "never invent criteria or amounts. Be practical, warm, and concise (max ~180 words). "
    "Structure: 1-line verdict, then 2-4 short bullet-style lines of reasoning, "
    "then 1-2 next steps. If some information is missing, say what to add. "
    "Write in the requested language."
)


class LLMError(Exception):
    pass


def _post_pollinations(messages: list[dict], model: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 400,
    }).encode("utf-8")
    req = urllib.request.Request(
        POLLINATIONS_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(f"unexpected pollinations response shape: {e}") from e
    if not content or not str(content).strip():
        raise LLMError("empty pollinations content")
    return str(content).strip()


class Explainer:
    """Explains match results using pollinations (keyless) with extractive fallback."""

    def __init__(self, model: str = "openai", offline: bool = False):
        self.model = model
        self.offline = offline  # offline=True forces extractive (tests / no-network deploys)

    @property
    def backend(self) -> str:
        if self.offline:
            return "extractive"
        return "pollinations"

    # ---------------- prompt building ----------------
    @staticmethod
    def _build_context(match: dict[str, Any], chunks: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        lines.append(f"Scheme: {match.get('name')} (id={match.get('scheme_id')})")
        lines.append(f"Verdict: {match.get('confidence')} (matched={match.get('matched')})")
        lines.append(f"Benefit: {match.get('benefit')}")
        for c in match.get("matched_criteria", []):
            note = c.get("note")
            if note:
                lines.append(f"- Met criterion: {note}")
        for b in match.get("blockers", [])[:4]:
            lines.append(f"- Blocker/missing: {b}")
        if chunks:
            lines.append("")
            lines.append("Official guidance excerpts:")
            for i, ch in enumerate(chunks, 1):
                text = ch["chunk"]["text"][:700]
                lines.append(f"[{i}] {text}")
        return "\n".join(lines)

    def _prompt(self, match: dict[str, Any], chunks: list[dict[str, Any]], language: str) -> str:
        ctx = self._build_context(match, chunks)
        lang_line = {
            "en": "Answer in simple English.",
            "hi": "उत्तर सरल हिंदी में दें।",
            "hinglish": "Answer in friendly Hinglish (Roman-script Hindi + English mix).",
        }.get(language, "Answer in simple English.")
        return (
            f"{lang_line}\n\nExplain this eligibility result to the citizen.\n\n{ctx}\n\n"
            "End with a line: 'Verify details at the official portal before applying.'"
        )

    # ---------------- extractive fallback ----------------
    @staticmethod
    def _extractive(match: dict[str, Any], chunks: list[dict[str, Any]]) -> str:
        verdict = {
            "full": "✅ You appear ELIGIBLE",
            "missing_info": "🟡 You may be eligible, but some information is missing",
            "excluded": "❌ You are currently NOT eligible",
        }.get(match.get("confidence", ""), "Result")
        lines = [f"{verdict} — {match.get('name')}", ""]
        lines.append(f"Benefit: {match.get('benefit')}")
        if match.get("matched_criteria"):
            notes = [c.get("note") for c in match["matched_criteria"] if c.get("note")]
            if notes:
                lines.append("Why: " + "; ".join(notes[:3]))
        if match.get("blockers"):
            lines.append("Blocked/missing: " + "; ".join(match["blockers"][:3]))
        if chunks:
            first = chunks[0]["chunk"]["text"]
            first = re.sub(r"\s+", " ", first).strip()
            lines.append(f"From official guidance: {first[:350]}…")
        lines.append("Verify details at the official portal before applying.")
        return "\n".join(lines)

    # ---------------- main entry ----------------
    def explain(self, match: dict[str, Any], chunks: list[dict[str, Any]],
                language: str = "en") -> dict[str, Any]:
        citations = [
            {"n": i, "scheme_id": ch["chunk"]["scheme_id"], "source_file": ch["chunk"]["source_file"]}
            for i, ch in enumerate(chunks, 1)
        ]
        if self.offline:
            return {
                "text": self._extractive(match, chunks),
                "backend": "extractive",
                "citations": citations,
            }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._prompt(match, chunks, language)},
        ]
        try:
            text = _post_pollinations(messages, self.model)
            return {"text": text, "backend": "pollinations", "citations": citations}
        except (LLMError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return {
                "text": self._extractive(match, chunks),
                "backend": "extractive",
                "citations": citations,
            }


def answer_question(question: str, chunks: list[dict[str, Any]], model: str = "openai",
                    offline: bool = False, language: str = "en") -> dict[str, Any]:
    """Free-text Q&A over retrieved chunks with the same fallback ladder."""
    citations = [
        {"n": i, "scheme_id": ch["chunk"]["scheme_id"], "source_file": ch["chunk"]["source_file"]}
        for i, ch in enumerate(chunks, 1)
    ]
    ctx = "\n".join(f"[{i}] {ch['chunk']['text'][:700]}" for i, ch in enumerate(chunks, 1))
    lang_line = {
        "en": "Answer in simple English.",
        "hi": "उत्तर सरल हिंदी में दें।",
        "hinglish": "Answer in friendly Hinglish.",
    }.get(language, "Answer in simple English.")

    if offline or not chunks:
        if chunks:
            best = re.sub(r"\s+", " ", chunks[0]["chunk"]["text"]).strip()
            text = f"{best[:500]}…\n\nSource: {chunks[0]['chunk']['source_file']}"
        else:
            text = "No relevant guidance found for this question."
        return {"text": text, "backend": "extractive", "citations": citations}

    prompt = (
        f"{lang_line}\nAnswer the citizen's question using ONLY these numbered excerpts.\n\n"
        f"Question: {question}\n\n{ctx}\n\n"
        "Cite excerpts as [1], [2]. If the excerpts don't cover it, say so."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        text = _post_pollinations(messages, model)
        return {"text": text, "backend": "pollinations", "citations": citations}
    except (LLMError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        best = re.sub(r"\s+", " ", chunks[0]["chunk"]["text"]).strip()
        return {
            "text": f"{best[:500]}…\n\nSource: {chunks[0]['chunk']['source_file']}",
            "backend": "extractive",
            "citations": citations,
        }
