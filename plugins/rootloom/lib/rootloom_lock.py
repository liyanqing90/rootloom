"""No-follow, single-link, nonblocking lock files shared by Rootloom components."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat
from typing import Any, Iterator


class LockFileError(RuntimeError):
    """A lock path or descriptor violated the hardened file contract."""


class LockBusyError(RuntimeError):
    """The validated lock file is already held by another process."""

    def __init__(self, path: Path, owner: str = "") -> None:
        super().__init__(f"lock is busy: {path}")
        self.path = path
        self.owner = owner


def _bounded_owner(descriptor: int) -> str:
    try:
        offset = os.lseek(descriptor, 0, os.SEEK_CUR)
        os.lseek(descriptor, 0, os.SEEK_SET)
        payload = os.read(descriptor, 4096)
        os.lseek(descriptor, offset, os.SEEK_SET)
    except OSError:
        return ""
    return payload.decode("utf-8", errors="backslashreplace").strip()


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise LockFileError("lock owner write made no forward progress")
        offset += written


def _open_posix(path: Path, mode: int) -> int:
    if not hasattr(os, "O_NOFOLLOW"):
        raise LockFileError("platform lacks O_NOFOLLOW for lock files")
    flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        parent_flags |= os.O_CLOEXEC
    try:
        parent_descriptor = os.open(path.parent, parent_flags)
    except OSError as exc:
        raise LockFileError(f"could not safely open lock parent {path.parent}: {exc}") from exc
    try:
        os.set_inheritable(parent_descriptor, False)
        parent_opened = os.fstat(parent_descriptor)
        parent_current = path.parent.lstat()
        if (
            not stat.S_ISDIR(parent_opened.st_mode)
            or stat.S_ISLNK(parent_current.st_mode)
            or (parent_opened.st_dev, parent_opened.st_ino)
            != (parent_current.st_dev, parent_current.st_ino)
        ):
            raise LockFileError(f"lock parent is not a stable direct directory: {path.parent}")
        try:
            descriptor = os.open(path.name, flags, mode, dir_fd=parent_descriptor)
        except OSError as exc:
            raise LockFileError(f"could not safely open lock file {path}: {exc}") from exc
        try:
            os.set_inheritable(descriptor, False)
            _validate_posix_identity(path, descriptor)
        except BaseException:
            os.close(descriptor)
            raise
    finally:
        os.close(parent_descriptor)
    return descriptor


def _validate_posix_identity(path: Path, descriptor: int) -> None:
    descriptor_info = os.fstat(descriptor)
    if not stat.S_ISREG(descriptor_info.st_mode):
        raise LockFileError(f"lock target is not a regular file: {path}")
    if descriptor_info.st_nlink != 1:
        raise LockFileError(f"lock target must have exactly one link: {path}")
    try:
        path_info = path.lstat()
    except FileNotFoundError as exc:
        raise LockFileError(f"lock path disappeared after open: {path}") from exc
    if not stat.S_ISREG(path_info.st_mode) or path.is_symlink():
        raise LockFileError(f"lock path is not a direct regular file: {path}")
    if path_info.st_nlink != 1:
        raise LockFileError(f"lock path must have exactly one link: {path}")
    if (path_info.st_dev, path_info.st_ino) != (
        descriptor_info.st_dev,
        descriptor_info.st_ino,
    ):
        raise LockFileError(f"lock path identity changed after open: {path}")


if os.name == "nt":  # pragma: no cover - exercised by native Windows CI
    import ctypes
    from ctypes import wintypes
    import msvcrt

    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _OPEN_ALWAYS = 4
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_READ_ATTRIBUTES = 0x00000080
    _LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
    _LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
    _ERROR_LOCK_VIOLATION = 33
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = (
            ("Internal", ctypes.c_size_t),
            ("InternalHigh", ctypes.c_size_t),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        )

    class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = (
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        )

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _CreateFileW = _kernel32.CreateFileW
    _CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _CreateFileW.restype = wintypes.HANDLE
    _GetFileInformationByHandle = _kernel32.GetFileInformationByHandle
    _GetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
    )
    _GetFileInformationByHandle.restype = wintypes.BOOL
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.argtypes = (wintypes.HANDLE,)
    _CloseHandle.restype = wintypes.BOOL
    _LockFileEx = _kernel32.LockFileEx
    _LockFileEx.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_OVERLAPPED),
    )
    _LockFileEx.restype = wintypes.BOOL
    _UnlockFileEx = _kernel32.UnlockFileEx
    _UnlockFileEx.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_OVERLAPPED),
    )
    _UnlockFileEx.restype = wintypes.BOOL


def _windows_raw_information(handle: Any, path: Path) -> Any:
    information = _BY_HANDLE_FILE_INFORMATION()
    if not _GetFileInformationByHandle(handle, ctypes.byref(information)):
        error = ctypes.get_last_error()
        raise LockFileError(f"could not inspect Windows lock {path}: error {error}")
    return information


def _windows_information(handle: Any, path: Path) -> Any:
    information = _windows_raw_information(handle, path)
    if information.dwFileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise LockFileError(f"Windows lock path is a reparse point: {path}")
    if information.dwFileAttributes & _FILE_ATTRIBUTE_DIRECTORY:
        raise LockFileError(f"Windows lock target is a directory: {path}")
    if information.nNumberOfLinks != 1:
        raise LockFileError(f"Windows lock target must have exactly one link: {path}")
    return information


def _windows_identity(information: Any) -> tuple[int, int, int]:
    return (
        int(information.dwVolumeSerialNumber),
        int(information.nFileIndexHigh),
        int(information.nFileIndexLow),
    )


def _open_windows_handle(path: Path, disposition: int) -> Any:
    handle = _CreateFileW(
        str(path),
        _GENERIC_READ | _GENERIC_WRITE,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        disposition,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        raise LockFileError(f"could not safely open Windows lock {path}: error {error}")
    return handle


def _open_windows_parent(path: Path) -> Any:
    handle = _CreateFileW(
        str(path),
        _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        raise LockFileError(f"could not safely open Windows lock parent {path}: error {error}")
    try:
        information = _windows_raw_information(handle, path)
        if information.dwFileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise LockFileError(f"Windows lock parent is a reparse point: {path}")
        if not information.dwFileAttributes & _FILE_ATTRIBUTE_DIRECTORY:
            raise LockFileError(f"Windows lock parent is not a directory: {path}")
        return handle
    except BaseException:
        _CloseHandle(handle)
        raise


def _open_windows(path: Path, _mode: int) -> int:  # pragma: no cover - Windows CI
    parent = _open_windows_parent(path.parent)
    handle = None
    try:
        parent_identity = _windows_identity(_windows_raw_information(parent, path.parent))
        handle = _open_windows_handle(path, _OPEN_ALWAYS)
        _windows_information(handle, path)
        current_parent = _open_windows_parent(path.parent)
        try:
            if _windows_identity(_windows_raw_information(current_parent, path.parent)) != parent_identity:
                raise LockFileError(
                    f"Windows lock parent identity changed after open: {path.parent}"
                )
        finally:
            _CloseHandle(current_parent)
        flags = os.O_RDWR | getattr(os, "O_NOINHERIT", 0)
        descriptor = msvcrt.open_osfhandle(int(handle), flags)
        handle = None
        os.set_inheritable(descriptor, False)
        return descriptor
    finally:
        if handle not in (None, _INVALID_HANDLE_VALUE):
            _CloseHandle(handle)
        _CloseHandle(parent)


def _validate_windows_identity(path: Path, descriptor: int) -> None:
    handle = msvcrt.get_osfhandle(descriptor)
    opened = _windows_information(handle, path)
    comparison = _open_windows_handle(path, _OPEN_EXISTING)
    try:
        current = _windows_information(comparison, path)
        if _windows_identity(current) != _windows_identity(opened):
            raise LockFileError(f"Windows lock path identity changed after open: {path}")
    finally:
        _CloseHandle(comparison)


def _acquire_windows(descriptor: int, path: Path) -> Any:  # pragma: no cover
    overlapped = _OVERLAPPED()
    handle = msvcrt.get_osfhandle(descriptor)
    flags = _LOCKFILE_EXCLUSIVE_LOCK | _LOCKFILE_FAIL_IMMEDIATELY
    if not _LockFileEx(handle, flags, 0, 1, 0, ctypes.byref(overlapped)):
        error = ctypes.get_last_error()
        if error == _ERROR_LOCK_VIOLATION:
            raise LockBusyError(path, _bounded_owner(descriptor))
        raise LockFileError(f"could not acquire Windows lock {path}: error {error}")
    return overlapped


def _release_windows(descriptor: int, state: Any, path: Path) -> None:  # pragma: no cover
    handle = msvcrt.get_osfhandle(descriptor)
    if not _UnlockFileEx(handle, 0, 1, 0, ctypes.byref(state)):
        error = ctypes.get_last_error()
        raise LockFileError(f"could not release Windows lock {path}: error {error}")


@contextmanager
def hardened_lock(
    path: Path,
    *,
    mode: int = 0o600,
    owner_bytes: bytes | None = None,
) -> Iterator[int]:
    """Open and acquire one direct regular single-link lock without pre-lock writes."""

    path = Path(path)
    descriptor = _open_windows(path, mode) if os.name == "nt" else _open_posix(path, mode)
    acquired = False
    platform_state: Any = None
    try:
        if os.name == "nt":  # pragma: no cover - Windows CI
            platform_state = _acquire_windows(descriptor, path)
        else:
            import fcntl

            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LockBusyError(path, _bounded_owner(descriptor)) from exc
        acquired = True
        if os.name == "nt":  # pragma: no cover - Windows CI
            _validate_windows_identity(path, descriptor)
        else:
            _validate_posix_identity(path, descriptor)
            os.fchmod(descriptor, mode)
            _validate_posix_identity(path, descriptor)
        if owner_bytes is not None:
            if len(owner_bytes) > 4096:
                raise LockFileError("lock owner record exceeds 4096 bytes")
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            _write_all(descriptor, owner_bytes)
            os.fsync(descriptor)
        yield descriptor
    finally:
        try:
            if acquired:
                if os.name == "nt":  # pragma: no cover - Windows CI
                    _release_windows(descriptor, platform_state, path)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
