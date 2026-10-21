"""Code hallucination checker: imports, packages and function references.

Ported from CodeHallucinations.ipynb. The detector uses only the standard
library; FastAPI/uvicorn are confined to server.py. Submitted code is only
ever parsed with ast.parse, never executed.
"""

from .checker import analyze_code, summarize

__all__ = ["analyze_code", "summarize"]
