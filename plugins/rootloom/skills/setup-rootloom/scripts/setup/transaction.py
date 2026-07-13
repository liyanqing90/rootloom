"""Atomic filesystem writes used by setup transactions and recovery."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def atomic_write(path: Path, value: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to write symlink: {path}")
    file_descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
