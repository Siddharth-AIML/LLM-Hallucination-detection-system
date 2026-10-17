"""Stage 2: which packages does the code import, and do they exist?

Notebook cells 8-18 (get_imports, on_pypi, KNOWN_IMPORTS, classify, VERDICT).
PYPI_URL and pypi_cache live here; tests point PYPI_URL at an invalid host
via code_verifier.imports.PYPI_URL. background.py reads the same setting.
"""

import ast
import importlib.util
import sys
import urllib.error
import urllib.request

PYPI_URL = "https://pypi.org/pypi"
PYPI_TIMEOUT = 10

pypi_cache = {}

KNOWN_IMPORTS = {
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "fitz": "pymupdf",
    "serial": "pyserial",
    "jwt": "pyjwt",
    "Crypto": "pycryptodome",
    "attr": "attrs",
    "numpy": "numpy", "pandas": "pandas", "requests": "requests",
    "matplotlib": "matplotlib", "scipy": "scipy", "torch": "torch",
    "flask": "flask", "django": "django", "fastapi": "fastapi",
}

VERDICT = {
    "stdlib": "SUPPORTED",
    "known": "SUPPORTED",
    "installed": "SUPPORTED",
    "on_pypi": "SUPPORTED (low trust)",
    "not_found": "CONTRADICTED",
    "unreachable": "INSUFFICIENT_INFORMATION",
}


def get_imports(tree):
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                continue
            names.append(node.module.split(".")[0])
    return sorted(set(names))


def on_pypi(name):
    if name in pypi_cache:
        return pypi_cache[name]
    try:
        with urllib.request.urlopen(f"{PYPI_URL}/{name}/json", timeout=PYPI_TIMEOUT) as r:
            result = (r.status == 200)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result = False
        else:
            return None
    except (urllib.error.URLError, OSError):
        return None
    pypi_cache[name] = result
    return result


def classify(name):
    if name in sys.stdlib_module_names:
        return "stdlib"
    if name in KNOWN_IMPORTS:
        return "known"
    if importlib.util.find_spec(name) is not None:
        return "installed"
    found = on_pypi(name)
    if found is None:
        return "unreachable"
    return "on_pypi" if found else "not_found"
