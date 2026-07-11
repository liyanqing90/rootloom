from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "rootloom"
    / "hooks"
    / "subagent_budget.py"
)
SPEC = importlib.util.spec_from_file_location("subagent_budget", SCRIPT)
assert SPEC and SPEC.loader
budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(budget)


class SubagentBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="subagent-budget-test-", dir=Path.home())
        self.addCleanup(self.temp_dir.cleanup)
        self.plugin_data = Path(self.temp_dir.name)

    def event(self, index: int, **overrides: str) -> dict[str, str]:
        event = {
            "session_id": "session-1",
            "agent_id": f"agent-{index}",
            "agent_type": "explorer",
            "model": "gpt-5.6-terra",
        }
        event.update(overrides)
        return event

    def test_fifth_unique_child_receives_advisory_stop_context(self) -> None:
        for index in range(1, 5):
            self.assertIsNone(budget.audit_event(self.event(index), self.plugin_data))
        output = budget.audit_event(self.event(5), self.plugin_data)
        self.assertIsNotNone(output)
        assert output is not None
        self.assertIn("started 5", output["systemMessage"])
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("cannot cancel", context)
        self.assertIn("Do not modify files", context)

    def test_duplicate_agent_id_does_not_consume_another_slot(self) -> None:
        event = self.event(1)
        self.assertIsNone(budget.audit_event(event, self.plugin_data, max_children=1))
        self.assertIsNone(budget.audit_event(event, self.plugin_data, max_children=1))

    def test_named_role_model_mismatch_is_reported(self) -> None:
        output = budget.audit_event(
            self.event(
                1,
                agent_type="root_cause_reviewer",
                model="gpt-5.6-terra",
            ),
            self.plugin_data,
        )
        self.assertIsNotNone(output)
        assert output is not None
        self.assertIn("model mismatch", output["systemMessage"])

    def test_symlinked_plugin_data_is_rejected_without_writing_outside(self) -> None:
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        redirected = Path(self.temp_dir.name) / "redirected"
        redirected.symlink_to(outside, target_is_directory=True)

        output = budget.audit_event(self.event(1), redirected)

        self.assertIsNotNone(output)
        assert output is not None
        self.assertIn("symbolic link", output["systemMessage"])
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_state_directory_is_rejected_without_writing_outside(self) -> None:
        outside = Path(self.temp_dir.name) / "outside-state"
        outside.mkdir()
        state_dir = self.plugin_data / "subagent-budget"
        state_dir.symlink_to(outside, target_is_directory=True)

        output = budget.audit_event(self.event(1), self.plugin_data)

        self.assertIsNotNone(output)
        assert output is not None
        self.assertIn("symbolic link", output["systemMessage"])
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
