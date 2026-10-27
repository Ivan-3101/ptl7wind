"""Vercel entry point. Vercel runs Python files in api/ as serverless functions.

All /api/* requests are rewritten here (see vercel.json); FastAPI does the routing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402  (import after the path is set)

__all__ = ["app"]
