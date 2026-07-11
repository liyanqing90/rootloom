#!/usr/bin/env python3
"""Validate the installed high-assurance Codex agent setup."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tomllib


REQUIRED_AGENTS = {
    "evidence_explorer": "read-only",
    "root_cause_reviewer": "read-only",
    "implementation_worker": "workspace-write",
    "verification_reviewer": "read-only",
}

def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def main() -> int:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    runner_failures: list[str] = []
    profile_failures: list[str] = []
    native_blockers: list[str] = []
    warnings: list[str] = []
    routes: list[str] = []

    config_path = codex_home / "config.toml"
    if not config_path.is_file():
        native_blockers.append(f"missing default config: {config_path}")
        config: dict = {}
    else:
        try:
            config = load_toml(config_path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            native_blockers.append(f"invalid config {config_path}: {exc}")
            config = {}

    agents_config = config.get("agents", {})
    if agents_config.get("max_threads") != 4:
        warnings.append("global agents.max_threads differs from the recommended value 4")
    if agents_config.get("max_depth") != 1:
        native_blockers.append("default config agents.max_depth must be 1")
    if agents_config.get("interrupt_message") is not True:
        warnings.append("global agents.interrupt_message is not true")
    if not config.get("review_model"):
        warnings.append("global review_model is not pinned")
    if config.get("model_reasoning_effort") == "ultra":
        native_blockers.append("default session uses Ultra, which may add uncontrolled delegation")
    if config.get("sandbox_mode") == "danger-full-access":
        native_blockers.append("default session uses danger-full-access")
    if any(
        server.get("enabled", True)
        for server in config.get("mcp_servers", {}).values()
    ):
        warnings.append(
            "read-only roles inherit enabled MCP/plugin tools; external read-only is a "
            "behavioral rule in native sessions"
        )

    profile_path = codex_home / "high-assurance.config.toml"
    if not profile_path.is_file():
        profile_failures.append(f"missing profile: {profile_path}")
        profile: dict = {}
    else:
        try:
            profile = load_toml(profile_path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            profile_failures.append(f"invalid profile {profile_path}: {exc}")
            profile = {}

    if profile.get("model_reasoning_effort") != "high":
        profile_failures.append("profile model_reasoning_effort must be high")
    if not profile.get("review_model"):
        profile_failures.append("profile review_model is not pinned")
    if profile.get("approval_policy") != "on-request":
        profile_failures.append("profile approval_policy must be on-request")
    if profile.get("sandbox_mode") != "workspace-write":
        profile_failures.append("profile sandbox_mode must be workspace-write")
    profile_agents = profile.get("agents", {})
    if profile_agents.get("max_threads") != 4:
        warnings.append("profile agents.max_threads differs from the recommended value 4")
    if profile_agents.get("max_depth") != 1:
        profile_failures.append("profile agents.max_depth must be 1")

    catalog: dict[str, set[str]] = {}
    catalog_path = codex_home / "models_cache.json"
    if catalog_path.is_file():
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            for model in payload.get("models", []):
                slug = model.get("slug")
                efforts = {
                    item.get("effort")
                    for item in model.get("supported_reasoning_levels", [])
                    if item.get("effort")
                }
                if slug:
                    catalog[slug] = efforts
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"could not read model catalog: {exc}")
    else:
        warnings.append("models_cache.json is absent; model availability was not checked")

    if catalog:
        profile_model = profile.get("model")
        profile_effort = profile.get("model_reasoning_effort")
        if profile_model not in catalog:
            profile_failures.append(
                f"profile model {profile_model!r} is not in the local catalog"
            )
        elif profile_effort not in catalog[profile_model]:
            profile_failures.append(
                f"profile effort {profile_effort!r} is not supported by {profile_model!r}"
            )

    agents_dir = codex_home / "agents"
    for role, expected_sandbox in REQUIRED_AGENTS.items():
        path = agents_dir / f"{role}.toml"
        if not path.is_file():
            runner_failures.append(f"missing agent: {path}")
            continue
        try:
            agent = load_toml(path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            runner_failures.append(f"invalid agent {path}: {exc}")
            continue

        for field in ("name", "description", "developer_instructions", "model", "model_reasoning_effort"):
            if not agent.get(field):
                runner_failures.append(f"{role}: missing {field}")
        if agent.get("name") != role:
            runner_failures.append(f"{role}: name must match the role")
        if agent.get("sandbox_mode") != expected_sandbox:
            runner_failures.append(f"{role}: sandbox_mode must be {expected_sandbox}")
        if expected_sandbox == "read-only":
            apps_default = agent.get("apps", {}).get("_default", {})
            if apps_default.get("enabled") is not False:
                runner_failures.append(f"{role}: apps._default.enabled must be false")

        model = agent.get("model")
        effort = agent.get("model_reasoning_effort")
        routes.append(f"{role}: {model} / {effort} / {agent.get('sandbox_mode')}")
        if catalog:
            if model not in catalog:
                runner_failures.append(f"{role}: model {model!r} is not in the local catalog")
            elif effort not in catalog[model]:
                runner_failures.append(
                    f"{role}: effort {effort!r} is not supported by {model!r}"
                )

    runner_path = Path(__file__).resolve().with_name("run_pipeline.py")
    if not runner_path.is_file():
        runner_failures.append(f"missing deterministic runner: {runner_path}")
    native_blockers.append(
        "live agent_type role/model attestation is unavailable on the locally verified "
        "multi-agent v2 surface"
    )

    print("High-assurance Codex routing")
    for route in routes:
        print(f"  {route}")
    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in runner_failures:
        print(f"RUNNER FAIL: {failure}")
    for failure in profile_failures:
        print(f"PROFILE FAIL: {failure}")
    for blocker in native_blockers:
        print(f"NATIVE NOT_READY: {blocker}")

    if runner_failures:
        print(f"Runner readiness: FAIL ({len(runner_failures)} issue(s))")
        return 1
    print("Runner readiness: PASS")
    if profile_failures:
        print(f"Native profile readiness: FAIL ({len(profile_failures)} issue(s))")
    else:
        print("Native profile readiness: PASS (configuration only)")
    print("Default/live native routing readiness: NOT_READY")
    print("Result: PASS (deterministic runner ready; native route remains disabled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
