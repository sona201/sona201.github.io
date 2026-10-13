import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.queue = self.directory / "issues.json"
        self.queue.write_text((runner.ROOT / "issues.json").read_text())
        self.args = SimpleNamespace(simulate="success", agent=None, queue=self.queue,
                                    state_dir=self.directory / "state")

    def test_success_has_evidence_and_does_not_repeat_or_edit_original(self):
        original = (runner.ROOT / "gateway.py").read_bytes()
        first = runner.tick(self.args)
        self.assertEqual(first["status"], "needs_review")
        artifact = Path(first["artifacts"])
        self.assertFalse(json.loads((artifact / "before.json").read_text())["passed"])
        self.assertTrue(json.loads((artifact / "after.json").read_text())["passed"])
        self.assertIn("a/gateway.py", (artifact / "patch.diff").read_text())
        self.assertEqual(runner.tick(self.args)["status"], "idle")
        self.assertEqual((runner.ROOT / "gateway.py").read_bytes(), original)

    def test_failures_stop_after_two_attempts(self):
        self.args.simulate = "fail"
        self.assertEqual(runner.tick(self.args)["status"], "retry")
        second = runner.tick(self.args)
        self.assertEqual(second["status"], "needs_human")
        self.assertEqual(second["attempts"], 2)
        self.assertEqual(runner.tick(self.args)["status"], "idle")

    def test_unapproved_or_out_of_scope_tasks_never_call_model(self):
        self.queue.write_text(json.dumps([
            {"id": "unapproved", "approved": False, "scope": "gateway.py"},
            {"id": "out_of_scope", "approved": True, "scope": "../runner.py"},
        ]))
        with patch.object(runner, "propose") as propose:
            self.assertEqual(runner.tick(self.args)["status"], "idle")
            propose.assert_not_called()

    def test_concurrent_tick_cannot_enter_locked_state(self):
        self.args.state_dir.mkdir()
        with (self.args.state_dir / "run.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(runner.tick(self.args)["status"], "busy")
        self.assertEqual(runner.tick(self.args)["status"], "needs_review")

    def test_interrupted_work_is_handed_to_human(self):
        self.args.state_dir.mkdir()
        runner.save_json(self.args.state_dir / "state.json", {
            "base-url-001": {"status": "running", "attempts": 1},
        })
        self.assertEqual(runner.tick(self.args)["status"], "idle")
        state = runner.read_json(self.args.state_dir / "state.json")
        self.assertEqual(state["base-url-001"]["status"], "needs_human")

    def test_boundary_rejects_paths_calls_and_statement_injection(self):
        invalid = [
            {"path": "../gateway.py", "expression": "value"},
            {"path": "gateway.py", "expression": "__import__('os').system('id')"},
            {"path": "gateway.py", "expression": "value.__class__"},
            {"path": "gateway.py", "expression": "value\nimport os"},
            {"path": "gateway.py", "expression": "value.replace(*value)"},
        ]
        for proposal in invalid:
            with self.subTest(proposal=proposal), self.assertRaises(runner.BoundaryError):
                runner.candidate_source(proposal)

    def test_boundary_failure_stops_immediately(self):
        with patch.object(runner, "propose", return_value={"path": "runner.py"}):
            result = runner.tick(self.args)
        self.assertEqual(result["status"], "needs_human")
        self.assertEqual(result["attempts"], 1)

    def test_broken_baseline_is_not_counted_as_reproduced(self):
        project = self.directory / "project"
        project.mkdir()
        shutil.copyfile(runner.ROOT / "acceptance.py", project / "acceptance.py")
        (project / "gateway.py").write_text("def broken(\n")
        with patch.object(runner, "ROOT", project), patch.object(runner, "propose") as propose:
            result = runner.tick(self.args)
        self.assertEqual(result["status"], "needs_human")
        self.assertIn("infrastructure error", result["error"])
        self.assertIn("SyntaxError", result["error"])
        propose.assert_not_called()

    def test_source_change_invalidates_candidate(self):
        project = self.directory / "project"
        project.mkdir()
        for filename in ("acceptance.py", "gateway.py"):
            shutil.copyfile(runner.ROOT / filename, project / filename)

        def changed_while_model_was_running(*_):
            with (project / "gateway.py").open("a") as source:
                source.write("\n# Concurrent human edit\n")
            return {"path": "gateway.py", "expression": "value.strip().rstrip('/')"}

        with patch.object(runner, "ROOT", project), \
                patch.object(runner, "propose", side_effect=changed_while_model_was_running):
            result = runner.tick(self.args)
        self.assertEqual(result["status"], "needs_human")
        self.assertIn("source changed", result["error"])
        self.assertFalse((Path(result["artifacts"]) / "patch.diff").exists())

    def test_cli_adapter_uses_tool_free_mode_and_structured_output(self):
        self.args.simulate = None
        proposal = {"path": "gateway.py", "expression": "value.strip().rstrip('/')", "reason": "fix"}
        reply = subprocess.CompletedProcess([], 0, json.dumps({"structured_output": proposal}), "")
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}), \
                patch.object(runner.subprocess, "run", return_value=reply) as run:
            actual = runner.propose({"description": "fix URL"}, "source", "", self.directory, self.args)
        self.assertEqual(actual, proposal)
        command = run.call_args.args[0]
        self.assertIn("--bare", command)
        self.assertEqual(command[command.index("--tools") + 1], "")
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 120)


if __name__ == "__main__":
    unittest.main()
