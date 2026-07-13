"""Verifier-only Git environment that disables optional repository writes."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterator


READ_ONLY_GIT_ENVIRONMENT = {
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "core.fsmonitor",
    "GIT_CONFIG_VALUE_0": "false",
    "GIT_CONFIG_KEY_1": "core.untrackedCache",
    "GIT_CONFIG_VALUE_1": "false",
}


@contextmanager
def read_only_git_environment() -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in READ_ONLY_GIT_ENVIRONMENT}
    os.environ.update(READ_ONLY_GIT_ENVIRONMENT)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
