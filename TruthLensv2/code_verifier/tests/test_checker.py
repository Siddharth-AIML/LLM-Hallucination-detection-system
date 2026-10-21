"""Tests ported from the checks in CodeHallucinations.ipynb.

Tests marked `internet` hit the real pypi.org and are skipped when it is
unreachable (or deselect them with: pytest -m "not internet"). Their
offline twins pre-fill the caches so the same logic is still exercised.
"""

import pytest
from fastapi.testclient import TestClient

from code_verifier import analyze_code, background, imports, summarize
from code_verifier.server import app

FENCE = "`" * 3

ROUND_1_ANSWER = f"""Sure! Here is how to fetch a web page and count the words:

{FENCE}python
import requests
import os
from collections import Counter
import fastjson_turbo

resp = requests.fetch("https://example.com")
words = resp.text.split()
print(Counter(words).most_common(5))
{FENCE}

This uses the requests library to download the page.
"""


def wrap(code):
    return "Here is the code:\n\n" + FENCE + "python\n" + code + FENCE + "\n"


TEST_CASES = [
    {"id": "real-01", "code": "import os\nfiles = os.listdir('.')\n", "hallucinated": []},
    {"id": "real-02", "code": "import json\ntext = json.dumps({'a': 1})\n", "hallucinated": []},
    {"id": "real-03", "code": "import math\nr = math.isqrt(17)\n", "hallucinated": []},
    {"id": "real-04", "code": "from datetime import datetime\nnow = datetime.now()\n", "hallucinated": []},
    {"id": "real-05", "code": "import itertools\nflat = list(itertools.chain.from_iterable([[1], [2]]))\n", "hallucinated": []},
    {"id": "real-06", "code": "import os.path as osp\np = osp.join('a', 'b')\n", "hallucinated": []},
    {"id": "fakepkg-01", "code": "import fastjson_turbo\nfastjson_turbo.load('x')\n", "hallucinated": ["fastjson_turbo"]},
    {"id": "fakepkg-02", "code": "import reqeusts\nr = reqeusts.get('https://example.com')\n", "hallucinated": ["reqeusts"]},
    {"id": "fakefn-01", "code": "import random\nn = random.randomint(1, 6)\n", "hallucinated": ["random.randomint"]},
    {"id": "fakefn-02", "code": "import statistics\nm = statistics.average([1, 2, 3])\n", "hallucinated": ["statistics.average"]},
    {"id": "fakefn-03", "code": "import datetime\nnow = datetime.now()\n", "hallucinated": ["datetime.now"]},
    {"id": "fakefn-04", "code": "import itertools\nflat = itertools.flatten([[1], [2]])\n", "hallucinated": ["itertools.flatten"]},
]

# Not one of the notebook's 12 cases: a method on a variable. The checker
# only follows names bound by import statements, so this is a known miss.
FAKEFN_06 = {"id": "fakefn-06", "code": "d = {}\nd.append_key('x')\n", "hallucinated": ["d.append_key"]}


def flagged_items(llm_answer):
    return {f["item"] for f in analyze_code(llm_answer) if f["verdict"] == "CONTRADICTED"}


def evaluate(cases):
    tp = fp = fn = 0
    for case in cases:
        predicted = flagged_items(wrap(case["code"]))
        expected = set(case["hallucinated"])
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"TP": tp, "FP": fp, "FN": fn, "precision": precision, "recall": recall}


def prefill_unknown_packages():
    """Stand in for PyPI answering 404 for the invented packages."""
    for name in ("fastjson_turbo", "reqeusts"):
        imports.pypi_cache[name] = False


# --- Round 1 example answer -------------------------------------------------

def check_round_1():
    findings = analyze_code(ROUND_1_ANSWER)
    assert flagged_items(ROUND_1_ANSWER) == {"fastjson_turbo", "requests.fetch"}
    real = [f for f in findings if f["item"] in ("os", "requests", "collections", "collections.Counter")]
    assert real and all(f["verdict"] == "SUPPORTED" for f in real)


@pytest.mark.internet
def test_round_1_example_live():
    check_round_1()


def test_round_1_example_offline_cache():
    prefill_unknown_packages()
    check_round_1()


# --- 12 notebook test cases -------------------------------------------------

@pytest.mark.internet
def test_twelve_cases_precision_recall_live():
    assert len(TEST_CASES) == 12
    m = evaluate(TEST_CASES)
    assert m["precision"] == 1.0 and m["recall"] == 1.0, m


def test_twelve_cases_precision_recall_offline_cache():
    prefill_unknown_packages()
    m = evaluate(TEST_CASES)
    assert m["precision"] == 1.0 and m["recall"] == 1.0, m


# --- known limitation -------------------------------------------------------

def test_method_on_variable_is_not_caught_known_limitation():
    """fakefn-06: d.append_key is hallucinated but the checker has no type
    inference, so it is a false negative. Documented, not fixed."""
    assert flagged_items(wrap(FAKEFN_06["code"])) == set()
    assert evaluate([FAKEFN_06])["recall"] == 0.0


# --- parse failures ---------------------------------------------------------

def test_broken_code_gives_parse_finding_and_does_not_raise():
    broken = wrap("import numpy as np\nfor i in range(10)\n    print(np.sqrt(i))\n")
    findings = analyze_code(broken)
    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "parse"
    assert f["verdict"] == "INSUFFICIENT_INFORMATION"
    assert f["block"] == 0


def test_null_bytes_do_not_raise():
    findings = analyze_code(wrap("import os\x00\n"))
    assert [f["kind"] for f in findings] == ["parse"]


# --- offline behaviour ------------------------------------------------------

def test_unreachable_pypi_is_insufficient_and_not_cached(monkeypatch):
    monkeypatch.setattr(imports, "PYPI_URL", "https://pypi.invalid/pypi")
    name = "zz_unlikely_package_name"
    assert imports.classify(name) == "unreachable"
    findings = analyze_code(wrap(f"import {name}\n"))
    assert [(f["kind"], f["verdict"]) for f in findings] == [("package", "INSUFFICIENT_INFORMATION")]
    assert findings[0]["reason"] == "PyPI could not be reached"
    assert name not in imports.pypi_cache


def test_unreachable_profile_is_not_cached(monkeypatch):
    monkeypatch.setattr(imports, "PYPI_URL", "https://pypi.invalid/pypi")
    assert background.package_profile("zz_unlikely_package_name") is None
    assert "zz_unlikely_package_name" not in background.profile_cache


# --- typosquat --------------------------------------------------------------

def test_simulated_typosquat_is_contradicted(monkeypatch):
    monkeypatch.setattr(imports, "PYPI_URL", "https://pypi.invalid/pypi")
    imports.pypi_cache["reqeusts"] = True
    background.profile_cache["reqeusts"] = {"releases": 1, "files": 1, "age_days": 3}
    status = imports.classify("reqeusts")
    assert status == "on_pypi"
    verdict, reason = background.background_check("reqeusts", status)
    assert verdict == "CONTRADICTED"
    assert "typosquat of 'requests'" in reason


# --- API --------------------------------------------------------------------

client = TestClient(app)


def check_shape(body):
    assert set(body) == {"findings", "summary", "blocks_found"}
    assert isinstance(body["blocks_found"], int)
    assert isinstance(body["summary"], dict)
    for f in body["findings"]:
        assert set(f) == {"block", "kind", "item", "verdict", "reason"}
        assert f["kind"] in ("parse", "package", "function")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_check_code_shape_offline():
    r = client.post("/check-code", json={"text": wrap("import os\nos.listdir('.')\nos.nope()\n")})
    assert r.status_code == 200
    body = r.json()
    check_shape(body)
    assert body["blocks_found"] == 1
    assert body["summary"] == {"SUPPORTED": 2, "CONTRADICTED": 1}
    assert {f["item"] for f in body["findings"] if f["verdict"] == "CONTRADICTED"} == {"os.nope"}


def test_check_code_without_code_blocks():
    r = client.post("/check-code", json={"text": "No code here."})
    assert r.json() == {"findings": [], "summary": {}, "blocks_found": 0}


def test_check_code_rejects_missing_text():
    assert client.post("/check-code", json={}).status_code == 422


def test_cors_allows_main_frontend_origins():
    for origin in ("http://127.0.0.1:8000", "http://localhost:8000"):
        r = client.options(
            "/check-code",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        assert r.headers.get("access-control-allow-origin") == origin
    r = client.options(
        "/check-code",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers


@pytest.mark.internet
def test_check_code_round_1_live():
    r = client.post("/check-code", json={"text": ROUND_1_ANSWER})
    body = r.json()
    check_shape(body)
    contradicted = {f["item"] for f in body["findings"] if f["verdict"] == "CONTRADICTED"}
    assert contradicted == {"fastjson_turbo", "requests.fetch"}
    assert body["summary"] == summarize(body["findings"])
