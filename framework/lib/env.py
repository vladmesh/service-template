"""Environment helpers for script tooling."""

from __future__ import annotations

import os
from pathlib import Path


def get_repo_root() -> Path:
    """Return the repository root, honoring SERVICE_TEMPLATE_ROOT overrides."""

    override = os.environ.get("SERVICE_TEMPLATE_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2]
