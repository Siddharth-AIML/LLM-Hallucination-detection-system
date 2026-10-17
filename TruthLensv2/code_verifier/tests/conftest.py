import urllib.request

import pytest

from code_verifier import background, imports


def _pypi_reachable():
    try:
        urllib.request.urlopen("https://pypi.org/pypi/requests/json", timeout=5).close()
        return True
    except OSError:
        return False


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "internet: needs live access to pypi.org (deselect with -m 'not internet')"
    )


def pytest_collection_modifyitems(config, items):
    if not any(item.get_closest_marker("internet") for item in items):
        return
    if _pypi_reachable():
        return
    skip = pytest.mark.skip(reason="pypi.org is not reachable")
    for item in items:
        if item.get_closest_marker("internet"):
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Every test starts with empty caches and the real PyPI URL."""
    monkeypatch.setattr(imports, "PYPI_URL", "https://pypi.org/pypi")
    imports.pypi_cache.clear()
    background.profile_cache.clear()
    yield
    imports.pypi_cache.clear()
    background.profile_cache.clear()
