"""The container installs only `azure/requirements.txt`.

Every third-party package the app imports at start-up must be declared there.
The test suite cannot catch an omission on its own: the developer machine has
packages installed from other projects, so an undeclared import still resolves
locally and fails only inside the image.

That is not hypothetical. `python-multipart` was missing from this file while
every test passed; the deployed backend crashed on import with
"Form data requires python-multipart to be installed" because the file upload
endpoint needs it.
"""

import re
from pathlib import Path

import pytest

_REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"

# Packages FastAPI needs for features this app uses but never imports by name,
# so no import scan would find them.
_IMPLICIT_RUNTIME_DEPENDENCIES = [
    # Multipart parsing for POST /api/documents/upload.
    "python-multipart",
]


def _declared_packages() -> set[str]:
    """Distribution names in requirements.txt, normalised and lowercased."""
    names = set()
    for line in _REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # "uvicorn[standard]==0.34.0" -> "uvicorn"
        name = re.split(r"[\[=<>!~;]", line, maxsplit=1)[0].strip()
        if name:
            names.add(name.lower().replace("_", "-"))
    return names


@pytest.mark.parametrize("package", _IMPLICIT_RUNTIME_DEPENDENCIES)
def test_implicit_runtime_dependency_is_declared(package):
    assert package in _declared_packages(), (
        f"{package} is imported at runtime but not declared in "
        f"azure/requirements.txt — the container will crash on start-up"
    )


def test_the_upload_endpoint_can_parse_multipart():
    """Importing the app is what actually fails when the parser is absent.

    FastAPI raises at decoration time, so a missing parser takes down the
    whole module, not just the one endpoint.
    """
    pytest.importorskip("multipart", reason="python-multipart is not installed")

    from azure.rag.api import app

    paths = {route.path for route in app.routes}
    assert "/api/documents/upload" in paths
