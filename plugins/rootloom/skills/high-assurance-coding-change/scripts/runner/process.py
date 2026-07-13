"""Stable executable identity capture for managed process boundaries."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any


def executable_identity(executable: Path) -> dict[str, Any]:
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("platform lacks no-follow executable support")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(executable, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not (
            before.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        ):
            raise ValueError("executable must be an executable regular file")
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise ValueError("executable changed while it was hashed")
    return {
        "device": after.st_dev,
        "inode": after.st_ino,
        "mode": after.st_mode,
        "size": after.st_size,
        "mtime_ns": after.st_mtime_ns,
        "ctime_ns": after.st_ctime_ns,
        "sha256": digest.hexdigest(),
    }
