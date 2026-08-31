"""Scheme Sahayak — hybrid RAG over scheme guidance corpus.

Design (free-tier friendly, per render-ml-backend recipe):
- BM25 (pure Python, stdlib only) over chunked guidance markdown — ALWAYS available.
- Optional vector layer via fastembed (only if installed & enabled via RAG_USE_FASTEMBED=1);
  default is BM25-only to stay within Render's 512MB free tier.

Chunking: guidance/*.md → ~600-char chunks, 100-char overlap, scheme_id + file + section provenance.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_TOKEN_RE = re.compile(
    r"[a-zA-Z\u0900-\u097F][a-zA-Z\u0900-\u097F\d]*"  # latin + devanagari words
    r"|\d+(?:[.,]\d+)*"                                  # numbers incl 2.5 lakh style
)

STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "to", "in", "for", "on", "is", "are",
    "be", "by", "with", "at", "from", "as", "it", "this", "that", "these",
    "under", "per", "not", "no", "any", "all", "must", "should", "will", "can",
    "ke", "ka", "ki", "mein", "me", "se", "ko", "hai", "hain", "ho", "ka", "iye",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in STOPWORDS and len(t) > 1]


@dataclass
class Chunk:
    text: str
    scheme_id: str
    source_file: str
    section: str = ""
    chunk_index: int = 0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "scheme_id": self.scheme_id,
            "source_file": self.source_file,
            "section": self.section,
        }


def chunk_markdown(md: str, scheme_id: str, source_file: str,
                   chunk_size: int = 600, overlap: int = 100) -> list[Chunk]:
    """Split markdown into chunks at paragraph/heading boundaries with provenance."""
    sections = re.split(r"\n(?=# )", md)  # split at top-level headings
    chunks: list[Chunk] = []
    idx = 0
    for section in sections:
        heading = ""
        body = section
        first_line = section.split("\n", 1)
        if first_line and first_line[0].startswith("#"):
            heading = first_line[0].lstrip("# ").strip()
        # further split long sections at paragraph boundaries
        paras = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
        buf = ""
        for para in paras:
            candidate = (buf + "\n\n" + para).strip() if buf else para
            if len(candidate) > chunk_size and buf:
                chunks.append(Chunk(buf, scheme_id, source_file, heading, idx))
                idx += 1
                buf = para[: chunk_size] if len(para) > chunk_size else para
            else:
                buf = candidate
        if buf.strip():
            chunks.append(Chunk(buf.strip(), scheme_id, source_file, heading, idx))
            idx += 1
    return chunks


class BM25:
    """Classic Okapi BM25 over pre-tokenized docs."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[list[str]] = []
        self.doc_len: list[int] = []
        self.df: dict[str, int] = {}
        self.n = 0
        self.avgdl = 0.0
        self.idf: dict[str, float] = {}

    def add(self, tokens: list[str]) -> None:
        self.docs.append(tokens)
        self.doc_len.append(len(tokens))
        self.n += 1
        seen = set()
        for t in tokens:
            if t not in seen:
                self.df[t] = self.df.get(t, 0) + 1
                seen.add(t)

    def finalize(self) -> None:
        self.avgdl = sum(self.doc_len) / max(self.n, 1)
        self.idf = {}
        for t, df in self.df.items():
            # BM25+ style smoothing to avoid negatives
            self.idf[t] = math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: list[str], doc_index: int) -> float:
        doc = self.docs[doc_index]
        dl = self.doc_len[doc_index]
        if dl == 0 or self.avgdl == 0:
            return 0.0
        tf_map: dict[str, int] = {}
        for t in doc:
            tf_map[t] = tf_map.get(t, 0) + 1
        s = 0.0
        for qt in query_tokens:
            tf = tf_map.get(qt, 0)
            if tf == 0:
                continue
            idf = self.idf.get(qt, 0.0)
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += idf * tf * (self.k1 + 1) / denom
        return s


class SchemeCorpus:
    """Loads schemes.json + guidance markdown; builds BM25 index; optional vector layer."""

    def __init__(self, data_dir: str | Path, use_fastembed: bool | None = None):
        self.data_dir = Path(data_dir)
        self.schemes: list[dict] = []
        self.chunks: list[Chunk] = []
        self.bm25 = BM25()
        self.embedder = None
        self.embeddings = None
        self._use_fastembed = (
            os.getenv("RAG_USE_FASTEMBED", "0") == "1" if use_fastembed is None else use_fastembed
        )
        self.load()

    # ---------- loading ----------
    def load(self) -> None:
        schemes_path = self.data_dir / "schemes.json"
        with open(schemes_path, encoding="utf-8") as f:
            data = json.load(f)
        self.schemes = data.get("schemes", [])

        guidance_dir = self.data_dir / "guidance"
        all_chunks: list[Chunk] = []
        if guidance_dir.exists():
            for md in sorted(guidance_dir.glob("*.md")):
                scheme_id = md.stem
                text = md.read_text(encoding="utf-8")
                all_chunks.extend(chunk_markdown(text, scheme_id, md.name))
        self.chunks = all_chunks

        for c in self.chunks:
            self.bm25.add(tokenize(c.text))
        self.bm25.finalize()

        if self._use_fastembed:
            self._try_init_fastembed()

    def _try_init_fastembed(self) -> None:
        try:
            from fastembed import TextEmbedding  # type: ignore
        except Exception:
            return
        try:
            self.embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
            texts = [c.text for c in self.chunks]
            self.embeddings = list(self.embedder.embed(texts))
        except Exception:
            self.embedder = None
            self.embeddings = None

    # ---------- search ----------
    def search(self, query: str, k: int = 5, scheme_id: Optional[str] = None) -> list[dict]:
        """Hybrid: cosine (if available) + BM25; returns [{'chunk':..., 'score':...}]."""
        if not self.chunks:
            return []
        q_tokens = tokenize(query)

        bm25_scores = [self.bm25.score(q_tokens, i) for i in range(len(self.chunks))]
        max_bm25 = max(bm25_scores) or 1.0
        bm25_norm = [s / max_bm25 for s in bm25_scores]

        vec_scores: list[float] = [0.0] * len(self.chunks)
        if self.embedder is not None and self.embeddings is not None:
            try:
                import numpy as np  # type: ignore
                q_vec = list(self.embedder.embed([query]))[0]
                q_arr = np.asarray(q_vec)
                mat = np.asarray(self.embeddings)
                denom = np.linalg.norm(mat, axis=1) * (np.linalg.norm(q_arr) or 1.0)
                sims = (mat @ q_arr) / np.where(denom == 0, 1e-9, denom)
                vec_scores = [float(s) for s in sims]
            except Exception:
                vec_scores = [0.0] * len(self.chunks)

        combined = [(0.5 * b + 0.5 * v) if self.embedder is not None else b
                    for b, v in zip(bm25_norm, vec_scores)]

        order = sorted(range(len(self.chunks)), key=lambda i: combined[i], reverse=True)
        out: list[dict] = []
        for i in order:
            if k and len(out) >= k:
                break
            if scheme_id and self.chunks[i].scheme_id != scheme_id:
                continue
            out.append({
                "chunk": self.chunks[i].to_dict(),
                "score": round(combined[i], 4),
                "bm25": round(bm25_norm[i], 4),
            })
        return out

    # ---------- metadata ----------
    def scheme_ids(self) -> list[str]:
        return [s["id"] for s in self.schemes]

    def get_scheme(self, scheme_id: str) -> Optional[dict]:
        for s in self.schemes:
            if s["id"] == scheme_id:
                return s
        return None

    def stats(self) -> dict:
        return {
            "schemes": len(self.schemes),
            "chunks": len(self.chunks),
            "vector_layer": self.embedder is not None,
        }
