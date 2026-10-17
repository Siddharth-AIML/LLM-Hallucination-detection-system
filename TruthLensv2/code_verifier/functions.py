"""Stage 4: do the functions/attributes the code calls actually exist?

Notebook cells 28-35 (build_aliases fixed version, attr_chain, get_references,
resolve, can_inspect, check_function). build_aliases_v1 (cell 29) was the
buggy first draft and is not ported. Only stdlib or already-installed modules
are ever imported (can_inspect); nothing is installed or executed.
"""

import ast
import difflib
import importlib
import importlib.util
import sys


def build_aliases(tree):
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    top = a.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for a in node.names:
                bound = a.asname or a.name
                aliases[bound] = f"{node.module}.{a.name}"
    return aliases


def attr_chain(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return list(reversed(parts))
    return None


def get_references(tree, aliases):
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            chain = attr_chain(node)
            if chain and chain[0] in aliases:
                refs.add(".".join([aliases[chain[0]]] + chain[1:]))
    for bound, target in aliases.items():
        if "." in target:
            refs.add(target)
    return sorted(refs)


def resolve(dotted):
    parts = dotted.split(".")
    try:
        obj = importlib.import_module(parts[0])
    except Exception:
        return "cannot_import", None
    for i in range(1, len(parts)):
        name = parts[i]
        if hasattr(obj, name):
            obj = getattr(obj, name)
            continue
        try:
            obj = importlib.import_module(".".join(parts[:i + 1]))
        except Exception:
            suggestion = difflib.get_close_matches(name, dir(obj), n=1, cutoff=0.6)
            return "missing", (name, suggestion[0] if suggestion else None)
    return "exists", None


def can_inspect(dotted):
    top = dotted.split(".")[0]
    return top in sys.stdlib_module_names or importlib.util.find_spec(top) is not None


def check_function(dotted):
    if not can_inspect(dotted):
        return "INSUFFICIENT_INFORMATION", "package not installed here, cannot inspect"
    result, detail = resolve(dotted)
    if result == "exists":
        return "SUPPORTED", "exists"
    if result == "cannot_import":
        return "INSUFFICIENT_INFORMATION", "package failed to load"
    top = importlib.import_module(dotted.split(".")[0])
    version = getattr(top, "__version__", "unknown")
    missing, hint = detail
    reason = f"'{missing}' not found (installed version {version})"
    if hint:
        reason += f"; closest real name: '{hint}'"
    return "CONTRADICTED", reason
