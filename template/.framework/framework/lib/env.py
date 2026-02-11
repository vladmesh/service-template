"""Environment helpers for script tooling."""

from __future__ import annotations

import os
from pathlib import Path


def get_repo_root() -> Path:
    """Return the repository root, honoring SERVICE_TEMPLATE_ROOT overrides."""

    override = os.environ.get("SERVICE_TEMPLATE_ROOT")
    if override:
        return Path(override).resolve()
    current = Path(__file__).resolve()
    # Try parents[2] (Framework repo structure)
    candidate = current.parents[2]
    if (candidate / "services.yml").exists() or (candidate / "copier.yml").exists():
        return candidate

    # Try parents[3] (Generated project structure: .framework/framework/lib/env.py)
    candidate = current.parents[3]
    if (candidate / "services.yml").exists() or (candidate / ".copier-answers.yml").exists():
        return candidate

    return current.parents[2]


def get_framework_dir() -> Path:
    """Return the ``framework/`` directory containing templates and lib.

    In the framework repo this is ``ROOT/framework/``.
    In a generated project this is ``ROOT/.framework/framework/``.
    Uses ``__file__`` so the result is always correct regardless of ROOT.
    Honors SERVICE_TEMPLATE_ROOT for test overrides.
    """

    override = os.environ.get("SERVICE_TEMPLATE_ROOT")
    if override:
        return Path(override).resolve() / "framework"
    return Path(__file__).resolve().parent.parent
