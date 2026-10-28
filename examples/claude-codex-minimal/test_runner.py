"""Integration tests for the runner; no model calls or third-party packages.

Run with: python3 -m unittest discover -s examples/claude-codex-minimal -v
"""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


FAKE_CODEX = r'''
import json
import os
from pathlib import Path
import subprocess
import sys
import time

args = sys.argv[1:]
prompt = sys.stdin.read()
records = Path(os.environ["FAKE_CODEX_RECORDS"])
mode = os.environ.get("FAKE_CODEX_MODE", "happy")
sandbox = args[args.index("--sandbox") + 1]
role = "worker" if sandbox == "workspace-write" else "reviewer"
repo = Path.cwd()
for flag in ("--cd", "-C"):
    if flag in args:
        repo = Path(args[args.index(flag) + 1])
output = Path(args[args.index("-o") + 1])
record = {"args": args, "prompt": prompt, "repo": str(repo), "pid": os.getpid()}
record_path = records / (role + ".json")
record_path.write_text(json.dumps(record))
print(json.dumps({"type": "thread.started", "thread_id": "fake-" + role}), flush=True)
print("fake " + role + " diagnostic", file=sys.stderr, flush=True)

if role == "worker":
    if mode == "timeout":
        heartbeat = records / "heartbeat"
        child_code = (
            "import time\nfrom pathlib import Path\n"
            + "path = Path(" + repr(str(heartbeat)) + ")\n"
            + "while True:\n"
            + "    with path.open('a') as stream: stream.write('tick\\n')\n"
            + "    time.sleep(0.05)\n"
        )
        child = subprocess.Popen([sys.executable, "-c", child_code])
        (records / "child.pid").write_text(str(child.pid))
        while True:
            time.sleep(1)
    if mode == "nonzero":
        sys.exit(7)
    if mode == "invalid_json":
        output.write_text("{broken json")
        sys.exit(0)
    if mode == "missing_json":
        sys.exit(0)
    (repo / "src/app.py").write_text("VALUE = 2\n")
    (repo / "src/helper.py").write_text("HELPER = True\n")
    if mode == "staged_only":
        subprocess.run(["git", "-C", str(repo), "add", "src/app.py"], check=True)
        (repo / "src/app.py").write_text("VALUE = 1\n")
    if mode == "change_head":
        subprocess.run(["git", "-C", str(repo), "add", "src"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "Unexpected commit"], check=True)
    result = {
        "status": "completed",
        "summary": "Updated the value and added a helper.",
        "tests": [{"command": "test fixture validation", "outcome": "passed", "evidence": "fake evidence"}],
        "risks": [],
    }
else:
    record["tracked_contents"] = (repo / "src/app.py").read_text()
    record["new_contents"] = (repo / "src/helper.py").read_text()
    record_path.write_text(json.dumps(record))
    if mode == "review_mutates":
        (repo / "src/helper.py").write_text("HELPER = False\n")
    result = {
        "verdict": "changes_requested" if mode == "review_findings" else "approve",
        "summary": "Reviewed the actual files in a separate invocation.",
        "findings": ([{"severity": "medium", "path": "src/app.py", "line": 1, "message": "Example review finding."}]
                     if mode == "review_findings" else []),
        "unverified": [],
    }
output.write_text(json.dumps(result))
print(json.dumps({"type": "turn.completed"}), flush=True)
'''


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="claude-codex-runner-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fake = self.root / "fake_codex.py"
        self.fake.write_text(FAKE_CODEX)
        self.runner = Path(__file__).resolve().with_name("runner.py")
        self.case_number = 0

    def git(self, repo, *args):
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def make_case(self, mode="happy", timeout=10):
        self.case_number += 1
        case_root = self.root / str(self.case_number)
        repo = case_root / "repo"
        (repo / "src").mkdir(parents=True)
        (repo / "src/app.py").write_text("VALUE = 1\n")
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.name", "Runner Test")
        self.git(repo, "config", "user.email", "runner-test@example.invalid")
        self.git(repo, "config", "commit.gpgsign", "false")
        self.git(repo, "config", "core.hooksPath", str(case_root / "unused-hooks"))
        self.git(repo, "add", "src/app.py")
        self.git(repo, "commit", "-qm", "Initial test fixture")
        records = case_root / "records"
        records.mkdir()
        task = case_root / "task.json"
        task.write_text(json.dumps({
            "id": "example-task",
            "goal": "Change VALUE to 2 and add a helper.",
            "context": "A temporary repository used to verify the orchestration contract.",
            "allowed_paths": ["src/"],
            "constraints": ["Do not commit or change branches."],
            "acceptance": ["VALUE equals 2; the helper file exists."],
            "checks": ["test fixture validation"],
            "handoff": "Fresh task.",
        }))
        config = case_root / "config.json"
        config.write_text(json.dumps({
            "codex_command": [sys.executable, str(self.fake)],
            "worker": {"model": "test-worker-model", "effort": "medium", "timeout_seconds": timeout},
            "reviewer": {"model": "test-reviewer-model", "effort": "high", "timeout_seconds": timeout},
        }))
        environment = os.environ.copy()
        environment.update(FAKE_CODEX_MODE=mode, FAKE_CODEX_RECORDS=str(records))
        return {
            "repo": repo, "task": task, "config": config,
            "run_dir": case_root / "run", "records": records,
            "env": environment, "base_head": self.git(repo, "rev-parse", "HEAD"),
        }

    def run_case(self, case):
        return subprocess.run(
            [sys.executable, str(self.runner), "run", "--repo", str(case["repo"]),
             "--task", str(case["task"]), "--config", str(case["config"]),
             "--run-dir", str(case["run_dir"])],
            capture_output=True, text=True, env=case["env"], timeout=20,
        )

    def status(self, case):
        return json.loads((case["run_dir"] / "status.json").read_text())

    def assert_exit(self, result, expected):
        self.assertEqual(result.returncode, expected, result.stdout + "\n" + result.stderr)

    def test_success_reviews_tracked_and_untracked_changes_in_new_session(self):
        case = self.make_case()
        result = self.run_case(case)
        self.assert_exit(result, 0)
        state = self.status(case)
        self.assertEqual(state["status"], "ready_for_acceptance")
        self.assertEqual(state["base_head"], case["base_head"])
        changes = json.loads((case["run_dir"] / "changes.json").read_text())
        self.assertEqual(changes["base_head"], case["base_head"])
        self.assertEqual(changes["head"], case["base_head"])
        for name in ("src/app.py", "src/helper.py"):
            self.assertRegex(changes["files"][name], r"^[0-9a-f]{64}$")
        for role, sandbox, model in (
            ("worker", "workspace-write", "test-worker-model"),
            ("reviewer", "read-only", "test-reviewer-model"),
        ):
            call = json.loads((case["records"] / (role + ".json")).read_text())
            self.assertIn("--ephemeral", call["args"])
            self.assertNotIn("resume", call["args"])
            self.assertEqual(call["args"][call["args"].index("--sandbox") + 1], sandbox)
            self.assertEqual(call["args"][call["args"].index("--model") + 1], model)
            self.assertTrue(call["prompt"].strip())
        review = json.loads((case["records"] / "reviewer.json").read_text())
        self.assertEqual(review["tracked_contents"], "VALUE = 2\n")
        self.assertEqual(review["new_contents"], "HELPER = True\n")
        verify = [sys.executable, str(self.runner), "verify", "--run-dir", str(case["run_dir"])]
        self.assert_exit(subprocess.run(verify, capture_output=True, text=True), 0)
        (case["repo"] / "src/helper.py").write_text("HELPER = False\n")
        self.assert_exit(subprocess.run(verify, capture_output=True, text=True), 1)

    def test_review_findings_require_fixes(self):
        case = self.make_case("review_findings")
        self.assert_exit(self.run_case(case), 2)
        self.assertEqual(self.status(case)["status"], "needs_fixes")

    def test_worker_failure_or_invalid_result_never_starts_review(self):
        for mode in ("nonzero", "invalid_json", "missing_json"):
            with self.subTest(mode=mode):
                case = self.make_case(mode)
                self.assert_exit(self.run_case(case), 1)
                self.assertEqual(self.status(case)["status"], "failed")
                self.assertTrue((case["records"] / "worker.json").is_file())
                self.assertFalse((case["records"] / "reviewer.json").exists())
                artifacts = [p for p in case["run_dir"].rglob("*") if p.is_file()]
                self.assertTrue(any("fake worker diagnostic" in p.read_text(errors="replace") for p in artifacts))

    @unittest.skipUnless(os.environ.get("RUN_PROCESS_GROUP_TESTS") == "1", "Requires an environment permitting process-group signals; opt in explicitly")
    def test_timeout_stops_child_process_as_well_as_worker(self):
        case = self.make_case("timeout", timeout=1)
        self.addCleanup(self.stop_fake_child, case)
        self.assert_exit(self.run_case(case), 1)
        self.assertEqual(self.status(case)["status"], "timed_out")
        heartbeat = case["records"] / "heartbeat"
        self.assertTrue(heartbeat.is_file(), "Fake child did not start before timeout")
        size_after_exit = heartbeat.stat().st_size
        time.sleep(0.3)
        self.assertEqual(heartbeat.stat().st_size, size_after_exit, "Child survived runner timeout")
        self.assertFalse((case["records"] / "reviewer.json").exists())

    def stop_fake_child(self, case):
        pids = []
        for role in ("worker", "reviewer"):
            call = case["records"] / (role + ".json")
            if call.exists():
                pids.append(json.loads(call.read_text())["pid"])
        child = case["records"] / "child.pid"
        if child.exists():
            pids.append(int(child.read_text()))
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_dirty_repository_is_rejected_before_model_call(self):
        for kind in ("tracked", "untracked"):
            with self.subTest(kind=kind):
                case = self.make_case()
                target = "src/app.py" if kind == "tracked" else "src/untracked.py"
                (case["repo"] / target).write_text("User-owned change.\n")
                self.assert_exit(self.run_case(case), 1)
                self.assertFalse((case["records"] / "worker.json").exists())
                self.assertEqual((case["repo"] / target).read_text(), "User-owned change.\n")

    def test_existing_run_directory_is_not_reused_or_overwritten(self):
        case = self.make_case()
        case["run_dir"].mkdir()
        marker = case["run_dir"] / "existing-result.txt"
        marker.write_text("Keep the previous run.\n")
        self.assert_exit(self.run_case(case), 1)
        self.assertEqual(marker.read_text(), "Keep the previous run.\n")
        self.assertFalse((case["records"] / "worker.json").exists())

    def test_worker_changing_head_is_rejected_before_review(self):
        case = self.make_case("change_head")
        self.assert_exit(self.run_case(case), 1)
        self.assertNotEqual(self.git(case["repo"], "rev-parse", "HEAD"), case["base_head"])
        self.assertEqual(self.status(case)["status"], "failed")
        self.assertFalse((case["records"] / "reviewer.json").exists())

    def test_hidden_staged_change_is_rejected_before_review(self):
        case = self.make_case("staged_only")
        task = json.loads(case["task"].read_text())
        task["allowed_paths"] = ["src/helper.py"]
        case["task"].write_text(json.dumps(task))
        self.assert_exit(self.run_case(case), 1)
        self.assertEqual(self.status(case)["status"], "failed")
        self.assertIn("staged", self.status(case)["detail"])
        self.assertEqual((case["repo"] / "src/app.py").read_text(), "VALUE = 1\n")
        self.assertFalse((case["records"] / "reviewer.json").exists())

    def test_changes_during_review_invalidate_result(self):
        case = self.make_case("review_mutates")
        self.assert_exit(self.run_case(case), 1)
        self.assertEqual(self.status(case)["status"], "failed")
        self.assertIn("changed during review", self.status(case)["detail"])

    def test_repeated_cancel_is_deferred_until_group_cleanup_finishes(self):
        # No OS signals are sent: this verifies handler/control-flow order only.
        spec = importlib.util.spec_from_file_location("runner_under_test", self.runner)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        process = mock.Mock(pid=999999)
        sent = []
        before = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
        def fake_killpg(pid, sig):
            self.assertEqual(pid, process.pid)
            sent.append(sig)
            if sig == signal.SIGTERM:
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        with mock.patch.object(runner.os, "killpg", side_effect=fake_killpg), mock.patch.object(runner.time, "monotonic", side_effect=[0, 0, 3]), mock.patch.object(runner.time, "sleep"):
            with self.assertRaises(runner.Cancelled):
                runner.stop_group(process)
        self.assertIn(signal.SIGKILL, sent)
        process.wait.assert_called_once()
        self.assertEqual(before, {sig: signal.getsignal(sig) for sig in before})


if __name__ == "__main__":
    unittest.main()
