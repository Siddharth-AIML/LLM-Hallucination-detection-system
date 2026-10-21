"""Stage 3: background checks for packages that are not installed.

Notebook cells 20-27 (near_miss, package_profile, background_check).
Reads PYPI_URL from imports.py so there is a single setting.
"""

import difflib
import json
import urllib.request
from datetime import datetime, timezone

from . import imports
from .imports import KNOWN_IMPORTS

POPULAR_IMPORTS = list(KNOWN_IMPORTS.keys())

profile_cache = {}


def near_miss(name):
    matches = difflib.get_close_matches(name, POPULAR_IMPORTS, n=1, cutoff=0.8)
    return matches[0] if matches else None


def package_profile(name):
    if name in profile_cache:
        return profile_cache[name]
    try:
        with urllib.request.urlopen(
            f"{imports.PYPI_URL}/{name}/json", timeout=imports.PYPI_TIMEOUT
        ) as r:
            data = json.load(r)
        upload_times = []
        for files in data["releases"].values():
            for f in files:
                upload_times.append(f["upload_time_iso_8601"])
        if upload_times:
            first = datetime.fromisoformat(min(upload_times).replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - first).days
        else:
            age_days = None
        releases = len(data["releases"])
    except (OSError, ValueError, KeyError, AttributeError):
        return None
    profile = {
        "releases": releases,
        "files": len(upload_times),
        "age_days": age_days,
    }
    profile_cache[name] = profile
    return profile


def background_check(name, status):
    if status in ("stdlib", "known", "installed"):
        return "SUPPORTED", status
    if status == "unreachable":
        return "INSUFFICIENT_INFORMATION", "PyPI could not be reached"
    close = near_miss(name)
    if status == "not_found":
        if close:
            return "CONTRADICTED", f"does not exist; looks like a typo of '{close}'"
        return "CONTRADICTED", "does not exist on PyPI"
    p = package_profile(name)
    if p is None:
        return "INSUFFICIENT_INFORMATION", "could not read package details"
    young = p["age_days"] is None or p["age_days"] < 90
    thin = p["files"] == 0 or p["releases"] <= 2
    if close and (young or thin):
        return "CONTRADICTED", f"likely typosquat of '{close}' {p}"
    if close:
        return "SUPPORTED", f"established package, but similar to '{close}': check intent"
    if young or thin:
        return "INSUFFICIENT_INFORMATION", f"exists but unproven {p}"
    return "SUPPORTED", f"established package {p}"
