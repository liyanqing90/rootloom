"""Typed failures shared by Strict Runner and Human Review."""


class PipelineError(RuntimeError):
    """A controlled pipeline failure with a stable exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class EvidenceInvalidError(PipelineError):
    """Persisted evidence is malformed, inconsistent, or unsafe."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 9)


class BindingDriftError(PipelineError):
    """Structurally valid evidence no longer matches observed current state."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 12)


class VerificationError(PipelineError):
    """The verifier could not obtain enough current-state evidence."""

    def __init__(self, message: str) -> None:
        super().__init__(message, 13)
