# Claude Code 调度 Codex：最小可用方案

这套配置用一个 Claude Code 会话做总控，依次启动一个 Codex 执行者和一个独立 Codex 审核者。你只与总控沟通，任务约定、状态和结果保存在磁盘上。

```text
Claude / Opus：写任务卡、启动后台任务、最终验收
    ↓ Bash 工具 run_in_background=true
runner.py
    ├─ Codex worker：修改代码、执行检查、返回结构化报告
    ├─ Codex reviewer：全新会话，只读审查实际代码
    └─ 保存结果并退出 → Claude Code 原生完成通知
    ↓
Claude：核对 diff、测试证据及审核发现，交付或安排下一步
```

这里的“回调”使用 Claude Code 原生后台任务通知，不需要 HTTP 服务。后台执行期间可以继续聊天；完成通知表示包装器结束，**不表示代码已经验收通过**。[Claude Code 后台命令](https://code.claude.com/docs/en/interactive-mode#background-bash-commands)、[官方更新记录](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)

## 1. 准备环境和目标工作区

需要 macOS 或 Linux、Python 3.9+、Git，以及已安装并登录的 Claude Code 和 Codex CLI。Python 包装器仅使用标准库。两套 CLI 使用各自的登录与额度；这套方案不把一个订阅转换为另一个产品的调用额度。

从仓库根目录进入本示例目录后执行：

```bash
cd examples/claude-codex-minimal
python3 --version
claude --version
python3 runner.py doctor
```

`doctor` 只执行 `codex --version`，检查 CLI 能否启动，不会发送模型请求，也不验证登录、模型权限或剩余额度。若 Codex 不在 PATH，可以在配置的 `codex_command` 中填写其可执行文件绝对路径。

准备一个**专用、干净的 Git worktree**，安装好项目所需依赖。例如，将下列路径换成自己的实际路径：

```bash
git -C /absolute/path/to/project worktree add -b codex/pagination-001 /absolute/path/to/task-worktree HEAD
git -C /absolute/path/to/task-worktree status --short
```

第二条命令应无输出。一次只对这个 worktree 运行一个任务；执行和审核期间，总控及其他窗口都不要编辑它。任务卡与运行记录放在 worktree 外，本示例目录中的 `.runs/` 即可。

## 2. 固定模型，填写真实任务

复制一份本地配置和任务卡，保留示例原件：

```bash
cp config.json config.local.json
cp task.example.json task.local.json
```

默认分工如下，模型名是起始配置，需确认你的 Codex CLI 和账户确实可用。

| 角色 | 模型 | 推理强度 | 单次时间上限 |
| --- | --- | --- | --- |
| Claude 总控 | `opus` 别名 | `medium` | 由 Claude 会话管理 |
| Codex worker | `gpt-6.1-sol` | `medium` | 30 分钟 |
| Codex reviewer | `gpt-6.1-sol` | `high` | 15 分钟 |

`config.local.json` 的 worker/reviewer 配置直接转换成每次 `codex exec` 的 `--model` 和 `model_reasoning_effort`。**本版没有自动模型路由**；Claude 不自行升级模型，模型不可用时报告失败，不静默换模型。先保持一组固定配置，复杂任务再由你明确调整。时间上限也不是费用或 token 上限。[Codex CLI 参数](https://learn.chatgpt.com/docs/developer-commands?surface=cli)、[Claude 模型配置](https://code.claude.com/docs/en/model-config)

编辑 `task.local.json`，把分页例子换成真实需求：

| 字段 | 填什么 |
| --- | --- |
| `id` | 唯一任务标识，如 `pagination-001` |
| `goal` | 具体要改变的行为 |
| `context` | 已确认背景、相关调用方和设计依据 |
| `allowed_paths` | 相对文件路径；以 `/` 结尾表示整个目录前缀，不支持 glob |
| `constraints` | 接口、依赖、兼容性等限制 |
| `acceptance` | 可核对的验收条件 |
| `checks` | 项目中真实可运行的检查命令，至少一条 |
| `handoff` | 本次任务的已知进展、阻塞和下一步 |

不要复制全部聊天或日志。保留明确目标、必要事实、文件线索和验收方法即可。执行者会读取目标仓库指令，并自行获取相关代码上下文。

## 3. 启动 Claude，总控下发任务

仍从本示例目录启动。`--settings` 加载附带的 SessionStart hook，`--add-dir` 让总控能够核查目标代码，不需要覆盖你现有的 `.claude/settings.json`。

```bash
claude --model opus --effort medium \
  --settings ./claude-settings.example.json \
  --add-dir /absolute/path/to/task-worktree
```

把下面这段交给 Claude，替换目标路径及任务 ID：

```text
遵守当前目录的 CLAUDE.md。先读 task.local.json 和 config.local.json，
确认任务卡已换成真实目标，且目标 worktree 干净。

请用 Bash 工具运行下面命令，并设置 run_in_background=true：
python3 runner.py run --repo /absolute/path/to/task-worktree --task task.local.json --config config.local.json --run-dir .runs/pagination-001

记录后台任务 ID 和输出位置，等待原生完成通知，不高频轮询。
收到通知后读取 HANDOFF、status 和两份结果，核对实际 diff 与测试证据，
再给出验收结论。存在问题时说明原因，不自动返工、合并或部署。
```

`run_in_background` 是 **Bash 工具参数**，不是 shell 命令参数。不要在命令后加 `&`，也不要用 `nohup`。包装器必须等待 worker 和 reviewer 都结束后才退出，否则通知会过早到达。

`runner.py` 会顺序执行两次全新的 `codex exec --ephemeral`：worker 使用 `workspace-write`，reviewer 使用 `read-only`；两者均不交互申请提权。通过 stdin 输入任务，以 `--json` 保存事件，并用 `--output-schema` 与 `-o` 保存结构化报告。遇到权限或依赖阻塞应停止并报告，不添加绕过沙箱的参数。[Codex 非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)

## 4. 回调、上下文交接和独立 review 如何工作

运行记录位于 `.runs/pagination-001/`，主要文件如下：

| 文件 | 用途 |
| --- | --- |
| `task.json`、`config.json` | 本次任务与模型配置快照 |
| `status.json`、`HANDOFF.md` | 程序状态和简短交接说明 |
| `worker.result.json` | 修改摘要、检查报告、风险 |
| `reviewer.result.json` | 审核结论、定位到文件与行的问题、未验证项 |
| `changes.json`、`changes.diff` | 基线、修改文件指纹和已跟踪文件 diff |
| `*.command.json`、`*.prompt.txt` | 实际调用参数和委派内容 |
| `*.events.jsonl`、`*.stderr.log`、`*.exit.json` | 过程日志、诊断和正常获得的退出码 |

独立 reviewer 是第二个全新 Codex 会话，与 worker 可以使用同一个模型。它拿到原始任务、Git 基线和修改文件清单，读取实际代码；不 resume worker，也不依赖 worker 的聊天或完成结论。新增文件不在普通 `git diff` 中，reviewer 和总控都需按 `changes.json` 直接读取它们。

程序要求改动保持未暂存；worker 若改动 HEAD 或暂存代码会停止，避免工作区与暂存区不同造成漏审。程序在审查前后比较工作区快照，发现中途又被修改就拒绝使用旧审核结果。`allowed_paths` 是事后范围检查，并非文件访问沙箱；应保留 Codex 自身的沙箱。工作区锁用于防止本包装器同时启动两个任务，不会阻止其他编辑器或 Agent 改文件。

`SessionStart` hook 在启动、恢复、清空和压缩上下文后运行：

```bash
python3 runner.py context --runs-dir .runs
```

它仅注入简短索引，Claude 再按需读取任务与结果。无需手工复制状态板，也不把完整日志重新塞进上下文。官方支持 `startup|resume|clear|compact`，SessionStart 的 stdout 会加入上下文。[SessionStart hook](https://code.claude.com/docs/en/hooks#sessionstart)

需要查看某个任务时可运行：

```bash
python3 runner.py status --run-dir .runs/pagination-001
```

**关闭 Claude Code 不会让这套任务继续常驻。** 原生后台进程会被清理，resume 不恢复后台 Bash。正常取消会停止 Codex 进程组并保留部分改动；强制结束可能留下过期的 `working`/`reviewing` 状态，恢复后先检查进程和工作区，不要直接重复启动。[后台任务生命周期](https://code.claude.com/docs/en/interactive-mode#background-bash-commands)、[恢复限制](https://code.claude.com/docs/en/scheduled-tasks#limitations)

## 5. 谁决定任务完成

| 状态 | 含义和下一步 |
| --- | --- |
| `working` / `reviewing` | 正在执行或审核；等待原生通知 |
| `ready_for_acceptance` | 报告满足程序条件，等待 Claude 最终验收 |
| `needs_fixes` | 审核发现问题、存在未验证项，或未报告全部检查通过 |
| `blocked` | 模型报告存在阻塞 |
| `failed` | CLI、结果格式、修改范围或快照等检查失败 |
| `timed_out` / `cancelled` | 时间到或被取消；保留日志与部分代码 |

**检查命令由 worker 执行并报告，runner 不独立重跑测试。** 程序只校验报告格式及任务中的每条检查是否都有 `passed` 和非空证据；reviewer 只做代码审查，不重跑可能写缓存的测试。因此 `ready_for_acceptance` 不是自动通过，更不代表模型报告一定真实。

Claude 最终核对原始需求、实际 diff、新增文件、审核发现和测试证据。必要时查看事件日志中的命令结果，或重新执行验收检查；随后运行下面的命令，确认当前代码仍与审核时的快照对应（此命令不运行测试）：

```bash
python3 runner.py verify --run-dir .runs/pagination-001
```

MVP 不自动返工，也不提交、合并或部署。需要继续时保留原记录，检查并处理已有改动，再使用新的任务 ID、全新 run-dir 和干净工作区。不要为了重跑而直接删除残留代码或覆盖原任务目录。

## 6. 本地验证与当前限制

从本示例目录运行测试：

```bash
python3 -m unittest discover -s . -p 'test_runner.py' -v
```

测试用临时 Git 仓库和假的 Codex 进程验证编排逻辑，不调用任何模型、不消耗模型额度。它们不能证明真实模型可用，也不能代替 Claude Code 后台通知的现场联调。

交付时运行 10 项测试：**9 项通过，1 项跳过**。通过项包括成功交接、审核发现问题、异常/缺失 JSON、脏工作区、重复目录、HEAD 变化、隐藏暂存改动、审核中代码变化，以及重复取消的模拟信号顺序；成功用例还验证 `verify` 能识别后续代码变化。真实超时/子进程终止测试需要允许进程组信号的环境，本次未完成该项实测。可在满足条件的普通终端显式运行：

```bash
RUN_PROCESS_GROUP_TESTS=1 python3 -m unittest discover -s . -p 'test_runner.py' -v
```

模拟信号测试不等于真实进程终止已验证。交付前检查进程列表，未发现本次模拟 CLI 的残留进程。

本次环境检查中，`claude 2.1.283` 可以启动；PATH 中的 `codex` 报错：

```text
Error: Missing optional dependency @openai/codex-darwin-x64
```

没有修改全局安装。因此真实 Codex 调用、账户对 `gpt-6.1-sol` 的访问权限，以及 Claude → Codex → review → 通知的完整链路尚未实测。先修复或指定可用的 Codex CLI，使 `doctor` 通过，再用一个小而可验证的真实任务做首轮联调。
