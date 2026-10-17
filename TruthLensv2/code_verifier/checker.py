"""Stage 5: the public entry point.

Notebook cell 36 (analyze_code, summarize).
"""

from .background import background_check
from .extract import extract_code_blocks, safe_parse
from .functions import build_aliases, check_function, get_references
from .imports import classify, get_imports


def analyze_code(llm_answer):
    blocks = extract_code_blocks(llm_answer)
    findings = []
    for i, code in enumerate(blocks):
        tree, err = safe_parse(code)
        if err:
            findings.append({"block": i, "kind": "parse", "item": "code block",
                             "verdict": "INSUFFICIENT_INFORMATION",
                             "reason": f"code does not parse: {err}"})
            continue
        package_verdict = {}
        for name in get_imports(tree):
            verdict, reason = background_check(name, classify(name))
            package_verdict[name] = verdict
            findings.append({"block": i, "kind": "package", "item": name,
                             "verdict": verdict, "reason": reason})
        for ref in get_references(tree, build_aliases(tree)):
            top = ref.split(".")[0]
            if package_verdict.get(top) != "SUPPORTED":
                continue
            verdict, reason = check_function(ref)
            findings.append({"block": i, "kind": "function", "item": ref,
                             "verdict": verdict, "reason": reason})
    return findings


def summarize(findings):
    counts = {}
    for f in findings:
        counts[f["verdict"]] = counts.get(f["verdict"], 0) + 1
    return counts
