import os
import sys
from pathlib import Path
import pytest

# Run pytest from TruthLensv2 root, or set TRUTHLENS_ROOT to that directory.
PROJECT_ROOT = Path(os.getenv("TRUTHLENS_ROOT", Path.cwd())).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture(scope="session")
def api_module():
    """
    Import the real FastAPI app. Import may initialize configured services,
    so run tests inside the project's normal virtual environment.
    """
    import api
    return api

@pytest.fixture()
def client(api_module):
    from fastapi.testclient import TestClient
    return TestClient(api_module.app)
