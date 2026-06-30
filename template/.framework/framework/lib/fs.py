"""Filesystem helpers shared across generators."""

import os
from pathlib import Path
import tempfile


def atomic_write_text(path: Path, content: str) -> None:
    """Write text to path atomically via a temp file + os.replace.

    Avoids leaving a truncated file behind if the process is interrupted
    mid-write, since generated files live in read-only zones that callers
    trust to be complete or unchanged.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
