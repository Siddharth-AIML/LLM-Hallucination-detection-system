"""Stage 1: pull fenced code blocks out of an LLM answer and parse them.

Notebook cells 2-7 (extraction pattern, ast.parse, safe_parse).
"""

import ast
import re

FENCE = "`" * 3
BLOCK_PATTERN = FENCE + r"(?:python|py)?\s*\n(.*?)" + FENCE


def extract_code_blocks(llm_answer):
    return re.findall(BLOCK_PATTERN, llm_answer, flags=re.DOTALL)


def safe_parse(code):
    try:
        return ast.parse(code), None
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e:
        return None, str(e)
