import shutil

import pytest


@pytest.fixture(scope="session")
def copier_available():
    """Check if copier is available."""
    if shutil.which("copier") is None:
        pytest.skip("copier not installed (pip install copier)")
