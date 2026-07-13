from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "plugins" / "rootloom" / "lib" / "rootloom_lock.py"
SPEC = importlib.util.spec_from_file_location("rootloom_lock_test", MODULE)
assert SPEC and SPEC.loader
lock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lock)


class SimpleLockTests(unittest.TestCase):
    def test_lock_is_exclusive_and_removed_on_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-lock-", dir=Path.home()) as temporary:
            path = Path(temporary) / "run.lock"
            with lock.simple_lock(path, owner_bytes=b"first\n"):
                self.assertTrue(path.is_file())
                with self.assertRaises(lock.LockBusyError):
                    with lock.simple_lock(path):
                        pass
            self.assertFalse(path.exists())

    def test_owner_record_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-lock-", dir=Path.home()) as temporary:
            with self.assertRaises(lock.LockFileError):
                with lock.simple_lock(Path(temporary) / "run.lock", owner_bytes=b"x" * 4097):
                    pass


if __name__ == "__main__":
    unittest.main()
