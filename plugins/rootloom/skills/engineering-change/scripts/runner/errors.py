"""Stable failures for the personal engineering helper."""


class ChangeError(RuntimeError):
    """A controlled engineering-change failure."""


class DangerousDeletionError(ChangeError):
    """A sensitive deletion needs exact operator confirmation."""


class VerificationError(ChangeError):
    """A requested verification command failed or could not run."""
