#!/usr/bin/env python3
"""One Codex worker, one fresh read-only reviewer. Python 3.9+, macOS/Linux."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
TERMINAL = {"ready_for_acceptance", "needs_fixes", "blocked", "failed", "timed_out", "cancelled"}


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING}
WORKER_SCHEMA = obj({
    "status": {"type": "string", "enum": ["completed", "blocked"]},
    "summary": STRING,
    "tests": {"type": "array", "items": obj({
        "command": STRING, "outcome": {"type": "string", "enum": ["passed", "failed", "not_run"]},
        "evidence": STRING,
    })},
    "risks": STRINGS,
})
REVIEW_SCHEMA = obj({
    "verdict": {"type": "string", "enum": ["approve", "changes_requested", "blocked"]},
    "summary": STRING,
    "findings": {"type": "array", "items": obj({
        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
        "path": STRING, "line": {"type": "integer"}, "message": STRING,
    })},
    "unverified": STRINGS,
})


class Cancelled(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(value, schema):
    """Validate only the small JSON Schema subset emitted by this program."""
    kind = schema["type"]
    expected = {"object": dict, "array": list, "string": str, "integer": int}[kind]
    if type(value) is not expected:
        raise ValueError("result JSON type mismatch: " + kind)
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("result JSON enum mismatch")
    if kind == "object":
        if set(value) != set(schema["properties"]):
            raise ValueError("result JSON fields mismatch")
        for key, field in schema["properties"].items():
            validate(value[key], field)
    if kind == "array":
        for item in value:
            validate(item, schema["items"])


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def text_git(repo, *args):
    return git(repo, *args).decode("utf-8", errors="surrogateescape").strip()


def inside(path, parent):
    return path == parent or parent in path.parents


def snapshot(repo, base):
    changed = set(filter(None, git(repo, "diff", "--no-ext-diff", "--no-textconv", "--name-only", "--no-renames", "-z", base, "--").split(b"\0")))
    changed.update(filter(None, git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")))
    files = {}
    for raw in sorted(changed):
        name = os.fsdecode(raw)
        path = repo / name
        if path.is_symlink():
            content = b"symlink:" + os.fsencode(os.readlink(path))
        elif path.is_file():
            content = path.read_bytes()
        elif path.is_dir():
            raise ValueError("Changed directory/submodule is unsupported: " + name)
        else:
            files[name] = None
            continue
        content = str(path.lstat().st_mode).encode() + b":" + content
        files[name] = hashlib.sha256(content).hexdigest()
    result = {
        "base_head": base, "head": text_git(repo, "rev-parse", "HEAD"), "files": files,
        "index_diff_sha256": hashlib.sha256(git(repo, "diff", "--no-ext-diff", "--no-textconv", "--cached", "--binary", base, "--")).hexdigest(),
    }
    result["snapshot"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def in_scope(name, allowed):
    return any(name == p or (p.endswith("/") and name.startswith(p)) for p in allowed)


def check_inputs(task, config):
    for field in ("id", "goal", "context", "handoff"):
        if not isinstance(task.get(field), str):
            raise ValueError("task requires string: " + field)
    for field in ("allowed_paths", "constraints", "acceptance", "checks"):
        if not isinstance(task.get(field), list) or not all(isinstance(v, str) and v for v in task[field]):
            raise ValueError("task requires string array: " + field)
    if not task["goal"].strip() or not task["allowed_paths"] or not task["acceptance"] or not task["checks"]:
        raise ValueError("goal, allowed_paths, acceptance and checks must be nonempty")
    for name in task["allowed_paths"]:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or not path.parts or ".git" in path.parts or "\\" in name:
            raise ValueError("Use relative file names or directory prefixes, never .git: " + name)
    if not isinstance(config.get("codex_command"), list) or not config["codex_command"] or not all(isinstance(x, str) and x for x in config["codex_command"]):
        raise ValueError("codex_command must be a nonempty argv array")
    for role in ("worker", "reviewer"):
        settings = config[role]
        if not isinstance(settings.get("model"), str) or not settings["model"]:
            raise ValueError("Set an accessible model for " + role)
        if settings.get("effort") not in ("minimal", "low", "medium", "high", "xhigh", "max"):
            raise ValueError("Unsupported effort for " + role)
        if type(settings.get("timeout_seconds")) not in (int, float) or settings["timeout_seconds"] <= 0:
            raise ValueError("Positive timeout required for " + role)


def stop_group(process):
    # A child can outlive its direct parent; signal the group, not just the parent.
    deferred_cancel = False
    def defer_cancel(_signum, _frame):
        nonlocal deferred_cancel
        deferred_cancel = True
    previous = {sig: signal.signal(sig, defer_cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if deferred_cancel:
        raise Cancelled()


def run_codex(role, prompt, repo, job, config):
    schema = WORKER_SCHEMA if role == "worker" else REVIEW_SCHEMA
    write_json(job / (role + ".schema.json"), schema)
    prompt_path = job / (role + ".prompt.txt")
    prompt_path.write_text(prompt, encoding="utf-8")
    settings = config[role]
    command = config["codex_command"] + [
        "exec", "--cd", str(repo), "--model", settings["model"],
        "--sandbox", "workspace-write" if role == "worker" else "read-only",
        "-c", 'approval_policy="never"',
        "-c", "model_reasoning_effort=" + json.dumps(settings["effort"]),
        "--json", "--ephemeral", "--output-schema", str(job / (role + ".schema.json")),
        "-o", str(job / (role + ".result.json")), "-",
    ]
    write_json(job / (role + ".command.json"), command)
    with prompt_path.open("rb") as source, (job / (role + ".events.jsonl")).open("wb") as events, (job / (role + ".stderr.log")).open("wb") as errors:
        process = subprocess.Popen(command, cwd=repo, stdin=source, stdout=events, stderr=errors, start_new_session=True)
        try:
            code = process.wait(timeout=settings["timeout_seconds"])
        finally:
            # Also removes residual children after normal exit.
            stop_group(process)
    write_json(job / (role + ".exit.json"), {"exit_code": code})
    if code != 0:
        raise RuntimeError(role + " CLI exited with code " + str(code))
    report = read_json(job / (role + ".result.json"))
    validate(report, schema)
    return report


def publish(job, state, status, detail):
    state.update(status=status, detail=detail, updated_at=now())
    write_json(job / "status.json", state)
    next_step = "等待原生后台任务完成通知，不要重复启动。"
    if status in TERMINAL:
        next_step = "读取任务、结果、真实 diff 和测试证据；由 Claude 最终验收。" if status == "ready_for_acceptance" else "读取错误/审核报告，检查现有进程和改动，再决定下一步；不会自动重试。"
    handoff = [
        "# Codex 任务交接", "", "- ID: " + state["task_id"], "- 状态: " + status,
        "- 工作区: " + state["repo"], "- 起始 HEAD: " + state["base_head"],
        "- runner PID: " + str(state["runner_pid"]), "- 更新时间: " + state["updated_at"],
        "- 原始任务: " + str(job / "task.json"), "- 完整状态: " + str(job / "status.json"),
        "- 修改证据: " + str(job / "changes.json") + " / changes.diff（生成后可读）",
        "- 执行报告: " + str(job / "worker.result.json") + "（生成后可读）",
        "- 独立审核: " + str(job / "reviewer.result.json") + "（生成后可读）",
        "", detail, "", "下一步：" + next_step,
        "", "模型报告不是最终验收。若会话被强制关闭，遗留运行状态不证明进程仍活着。", "",
    ]
    (job / "HANDOFF.md").write_text("\n".join(handoff), encoding="utf-8")


def run(args):
    repo, job = Path(args.repo).resolve(), Path(args.run_dir).resolve()
    task, config = read_json(args.task), read_json(args.config)
    check_inputs(task, config)
    if inside(job, repo):
        raise ValueError("run-dir must be outside the target worktree")
    if inside(Path(args.task).resolve(), repo):
        raise ValueError("task card must be outside the target worktree")
    if Path(text_git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("--repo must be the Git working tree root")
    lock_path = Path(text_git(repo, "rev-parse", "--absolute-git-dir")) / "claude-codex.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This worktree already has a running job") from None
        if git(repo, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("A clean dedicated worktree is required; existing changes were not touched")
        base = text_git(repo, "rev-parse", "HEAD")
        job.mkdir(parents=True, exist_ok=False)
        write_json(job / "task.json", task)
        write_json(job / "config.json", config)
        state = {"task_id": task["id"], "repo": str(repo), "base_head": base, "runner_pid": os.getpid(), "started_at": now()}
        publish(job, state, "working", "Codex worker 正在执行；固定模型和时间上限见 config.json。")
        status, detail = "failed", "Task did not complete"
        try:
            worker_prompt = (
                "你是执行者。请在当前工作区实施任务，并运行任务卡 checks 中的每条命令。\n"
                "只修改 allowed_paths 中的文件（以 / 结尾是目录前缀）。遵守仓库指令。\n"
                "不要 git add/stage、commit、切换分支、改 Git 配置或推送。不要创建常驻/脱离进程。\n"
                "不要修改任务/配置/schema/日志。遇到权限、依赖、需求阻塞应返回 blocked。\n"
                "tests 的 command 必须使用 checks 原字符串；报告实际 outcome 与证据。不能把未执行当 passed。\n"
                "按给定 JSON Schema 返回结果；你无权最终验收。\nTASK:\n" + json.dumps(task, ensure_ascii=False, indent=2)
            )
            worker = run_codex("worker", worker_prompt, repo, job, config)
            changes = snapshot(repo, base)
            write_json(job / "changes.json", changes)
            (job / "changes.diff").write_bytes(git(repo, "diff", "--no-ext-diff", "--no-textconv", "--binary", base, "--"))
            state["reviewed_snapshot"] = changes["snapshot"]
            if changes["head"] != base:
                raise ValueError("Worker changed HEAD; inspect manually, do not review against a moved baseline")
            if git(repo, "diff", "--cached", "--name-only", base, "--"):
                raise ValueError("Worker staged changes; this MVP only reviews unstaged edits. Inspect index before continuing")
            outside = [p for p in changes["files"] if not in_scope(p, task["allowed_paths"])]
            if outside:
                raise ValueError("Changes outside allowed_paths: " + ", ".join(outside))
            if worker["status"] == "blocked":
                status, detail = "blocked", worker["summary"]
            else:
                publish(job, state, "reviewing", "执行阶段结束，启动全新 read-only Codex reviewer。")
                review_prompt = (
                    "你是独立代码审核者，不是执行者。只能读取，不能编辑、提交或修复代码。\n"
                    "根据原始任务核对实际代码、git diff 和新增文件，寻找功能错误、回归、范围越界及缺失测试。\n"
                    "不要依赖执行者的完成结论。无需读取 worker 聊天或其最终报告。\n"
                    "这是代码审查，不要求重跑可能写缓存的测试；不要声称自己运行了未运行的检查。\n"
                    "报告可定位问题；无法核实的重要行为写入 unverified。仅在无待解决问题时 approve。\n"
                    "修改基线 HEAD: " + base + "\n"
                    "运行 git diff --no-ext-diff " + base + " -- 检查已跟踪修改。\n"
                    "下面的文件清单包括新增文件，新增文件需要直接读取（git diff 不含 untracked 内容）。\n"
                    "CHANGES:\n" + json.dumps(changes, ensure_ascii=False, indent=2) + "\nTASK:\n" + json.dumps(task, ensure_ascii=False, indent=2)
                )
                reviewer = run_codex("reviewer", review_prompt, repo, job, config)
                if snapshot(repo, base) != changes:
                    raise ValueError("Worktree changed during review; review result is stale")
                test_map = {test["command"]: test for test in worker["tests"]}
                all_reported = all(command in test_map and test_map[command]["outcome"] == "passed" and test_map[command]["evidence"].strip() for command in task["checks"])
                if reviewer["verdict"] == "blocked":
                    status, detail = "blocked", reviewer["summary"]
                elif reviewer["verdict"] != "approve" or reviewer["findings"] or reviewer["unverified"] or not all_reported:
                    status, detail = "needs_fixes", "审核有问题、存在未验证项，或执行者未报告全部检查通过。请读取两份结果。"
                else:
                    status, detail = "ready_for_acceptance", "执行者报告检查通过，独立审查未报告问题。仍需 Claude 核对实际证据并最终验收。"
        except subprocess.TimeoutExpired:
            status, detail = "timed_out", "Codex 超过本阶段时间上限，已停止其进程组；保留部分修改和日志，需检查。"
        except Cancelled:
            status, detail = "cancelled", "收到取消信号，已停止当前 Codex 进程组；部分修改和日志保留。"
        except (OSError, ValueError, RuntimeError, KeyError, subprocess.CalledProcessError) as exc:
            status, detail = "failed", str(exc)
        publish(job, state, status, detail)
        print(json.dumps({"status": status, "detail": detail, "handoff": str(job / "HANDOFF.md"), "status_file": str(job / "status.json")}, ensure_ascii=False), flush=True)
        return 0 if status == "ready_for_acceptance" else 2 if status in ("needs_fixes", "blocked") else 1


def show_context(root):
    print("Codex 任务交接索引（只恢复上下文，不重启进程）:")
    records = []
    for path in Path(root).resolve().glob("*/status.json"):
        try:
            state = read_json(path)
            record = {"id": state["task_id"], "status": state["status"], "repo": state["repo"], "handoff": str(path.parent / "HANDOFF.md")}
            records.append((state["status"] in TERMINAL, -path.stat().st_mtime, record))
        except (OSError, ValueError, KeyError):
            print("Unreadable status: " + str(path))
    for _, _, record in sorted(records, key=lambda item: item[:2])[:10]:
        print(json.dumps(record, ensure_ascii=False))
    if len(records) > 10:
        print("仅显示优先运行中、其次最近更新的 10 项；完整任务在 " + str(Path(root).resolve()))
    print("运行状态可能因强制退出而过期；先确认进程与工作区，不要直接重跑。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    launch = sub.add_parser("run")
    for name in ("repo", "task", "run-dir"):
        launch.add_argument("--" + name, required=True)
    launch.add_argument("--config", default=str(HERE / "config.json"))
    status = sub.add_parser("status")
    status.add_argument("--run-dir", required=True)
    verify = sub.add_parser("verify", help="Check whether the reviewed code snapshot is still current; does not run tests")
    verify.add_argument("--run-dir", required=True)
    context = sub.add_parser("context")
    context.add_argument("--runs-dir", default=str(HERE / ".runs"))
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--config", default=str(HERE / "config.json"))
    args = parser.parse_args()
    if args.command == "status":
        print(json.dumps(read_json(Path(args.run_dir) / "status.json"), ensure_ascii=False, indent=2))
        return 0
    if args.command == "verify":
        job = Path(args.run_dir).resolve()
        state = read_json(job / "status.json")
        changes = read_json(job / "changes.json")
        current = snapshot(Path(state["repo"]), state["base_head"])
        matches = state["status"] == "ready_for_acceptance" and current == changes
        print(json.dumps({"reviewed_code_unchanged": matches, "status": state["status"], "tests_verified": False}))
        return 0 if matches else 1
    if args.command == "context":
        show_context(args.runs_dir)
        return 0
    if args.command == "doctor":
        # Read-only local checks: no authentication files and no inference request.
        config = read_json(args.config)
        result = subprocess.run(config["codex_command"] + ["--version"], capture_output=True, text=True, timeout=15)
        print(result.stdout or result.stderr)
        print("Doctor checks CLI startup only; model access and authentication still need verification before use.")
        return result.returncode
    def cancel(_signum, _frame):
        raise Cancelled()
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    return run(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print("Cannot start: " + str(error), file=sys.stderr)
        sys.exit(1)
