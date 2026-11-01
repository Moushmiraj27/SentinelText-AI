"""Vercel ASGI entry point for the canonical SentinelText FastAPI app."""
import sys
from pathlib import Path


PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from backend.main import app  # noqa: E402

application = app
handler = app

__all__ = ["app", "application", "handler"]
