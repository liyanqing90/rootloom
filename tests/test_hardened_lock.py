from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "plugins" / "rootloom" / "lib" / "rootloom_lock.py"
SPEC = importlib.util.spec_from_file_location("rootloom_lock_direct_test", MODULE)
assert SPEC and SPEC.loader
lock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lock)


class HardenedLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="rootloom-lock-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_regular_lock_is_private_non_inheritable_and_nonblocking(self) -> None:
        path = self.root / "regular.lock"
        with lock.hardened_lock(path, owner_bytes=b"owner\n") as descriptor:
            self.assertFalse(os.get_inheritable(descriptor))
            os.lseek(descriptor, 0, os.SEEK_SET)
            self.assertEqual(os.read(descriptor, 4096), b"owner\n")
            with self.assertRaises(lock.LockBusyError):
                with lock.hardened_lock(path):
                    self.fail("competing lock acquired")
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_symlink_lock_never_mutates_victim(self) -> None:
        victim = self.root / "victim.txt"
        victim.write_bytes(b"preserve-victim")
        if os.name != "nt":
            victim.chmod(0o644)
        before_mode = stat.S_IMODE(victim.stat().st_mode)
        path = self.root / "linked.lock"
        try:
            path.symlink_to(victim)
        except OSError as exc:  # pragma: no cover - depends on Windows symlink policy
            self.skipTest(f"platform cannot create a test symlink: {exc}")
        with self.assertRaises(lock.LockFileError):
            with lock.hardened_lock(path, owner_bytes=b"attacker-wins\n"):
                self.fail("symlinked lock acquired")
        self.assertEqual(victim.read_bytes(), b"preserve-victim")
        self.assertEqual(stat.S_IMODE(victim.stat().st_mode), before_mode)

    def test_hardlinked_lock_never_mutates_victim(self) -> None:
        victim = self.root / "hardlink-victim.txt"
        victim.write_bytes(b"preserve-hardlink-victim")
        if os.name != "nt":
            victim.chmod(0o644)
        before_mode = stat.S_IMODE(victim.stat().st_mode)
        path = self.root / "hardlinked.lock"
        os.link(victim, path)
        with self.assertRaises(lock.LockFileError):
            with lock.hardened_lock(path, owner_bytes=b"attacker-wins\n"):
                self.fail("hardlinked lock acquired")
        self.assertEqual(victim.read_bytes(), b"preserve-hardlink-victim")
        self.assertEqual(stat.S_IMODE(victim.stat().st_mode), before_mode)

    def test_symlinked_parent_never_mutates_external_lock(self) -> None:
        external = self.root / "external"
        external.mkdir()
        victim = external / "setup.lock"
        victim.write_bytes(b"preserve-parent-victim")
        linked_parent = self.root / "linked-parent"
        try:
            linked_parent.symlink_to(external, target_is_directory=True)
        except OSError as exc:  # pragma: no cover - depends on Windows symlink policy
            self.skipTest(f"platform cannot create a test directory symlink: {exc}")
        with self.assertRaises(lock.LockFileError):
            with lock.hardened_lock(
                linked_parent / "setup.lock",
                owner_bytes=b"attacker-wins\n",
            ):
                self.fail("lock below symlinked parent acquired")
        self.assertEqual(victim.read_bytes(), b"preserve-parent-victim")
