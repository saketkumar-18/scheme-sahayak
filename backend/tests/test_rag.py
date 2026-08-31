"""RAG pipeline tests — chunking, BM25 relevance, filters."""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.rag import SchemeCorpus, chunk_markdown, tokenize  # noqa: E402

DATA = BACKEND / "data"
corpus = SchemeCorpus(DATA)


# ---------- tokenization ----------
def test_tokenize_mixed_language_and_numbers():
    toks = tokenize("PM-KISAN gives ₹6,000 per year to farmers किसान")
    assert "pm" in toks and "6,000" in toks and "farmers" in toks
    assert "किसान" in toks


def test_tokenize_drops_stopwords():
    toks = tokenize("the scheme of the government")
    assert "the" not in toks and "scheme" in toks


# ---------- chunking ----------
def test_chunk_markdown_provenance():
    md = "# Title\n\nPara one content here.\n\n## Sub\n\nPara two content here with more words to pack."
    chunks = chunk_markdown(md, scheme_id="x", source_file="x.md", chunk_size=80)
    assert all(c.scheme_id == "x" and c.source_file == "x.md" for c in chunks)
    assert all(len(c.text) <= 160 for c in chunks)  # overlap tolerance
    joined = " ".join(c.text for c in chunks)
    assert "Para one" in joined and "Para two" in joined


def test_corpus_chunks_nonempty_with_provenance():
    assert len(corpus.chunks) > 20
    for c in corpus.chunks:
        assert c.scheme_id and c.source_file and c.text.strip()


# ---------- BM25 relevance ----------
def test_search_pm_kisan_query_ranks_pm_kisan_first():
    hits = corpus.search("PM KISAN income support farmer family installments", k=5)
    assert hits, "no results"
    assert hits[0]["chunk"]["scheme_id"] == "pm-kisan"


def test_search_ayushman_query():
    hits = corpus.search("5 lakh health cover hospitalisation cashless senior citizen", k=5)
    assert hits[0]["chunk"]["scheme_id"] == "ab-pmjay"


def test_search_scheme_filter():
    hits = corpus.search("eligibility income", k=10, scheme_id="pms-sc")
    assert hits and all(h["chunk"]["scheme_id"] == "pms-sc" for h in hits)


def test_search_scores_sorted_desc():
    hits = corpus.search("housing pucca house rural", k=8)
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_stats_shape():
    st = corpus.stats()
    assert st["schemes"] == 13
    assert st["chunks"] > 20
    assert st["vector_layer"] in (True, False)
