"""Scheme Sahayak — Vercel serverless entry (ASGI bridge to the FastAPI app).

@vercel/python detects the ASGI `app` object exported here and serves every
/api/* request through it (see root vercel.json rewrites).
"""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Serverless-friendly settings (must be set BEFORE importing the app, which
# reads env at import time): short LLM timeout keeps worst-case request well
# inside function duration; open CORS for this public, stateless, zero-auth API.
os.environ.setdefault("LLM_TIMEOUT", "6")
os.environ.setdefault("ALLOWED_ORIGINS", "*")

from backend.app.main import app  # noqa: E402,F401  (Vercel serves this ASGI app)
