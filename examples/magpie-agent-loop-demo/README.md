# 最小 AI 自动维护流程

这是博客的**教学示例**，不是 Magpie 的代码或真实缺陷复刻。我们借用一个常见网关配置问题：用户配置的 API 地址是 `https://api.example.com/team/v1/`，规范化函数却误删了 `/v1`，请求因此发往错误路径。

完整过程只有一条：读取人工批准的本地 issue → 复现问题 → 请求候选修复 → 固定验收 → 保存补丁和证据 → 等待人工审查。它不连接 GitHub，不发消息，不自动合并或发布。

## 先运行，不需要模型帐号

需要 Python 3.9+，支持 macOS/Linux（锁使用标准库 `fcntl`），不需要 `pip install`。

```bash
cd examples/magpie-agent-loop-demo
python3 -m unittest -v
python3 runner.py --simulate success
python3 runner.py --simulate success
```

第一次应输出 `needs_review`，第二次为 `idle`。查看成果：

```bash
cat .runs/simulate-success/base-url-001/1/patch.diff
cat .runs/simulate-success/base-url-001/1/report.json
cat .runs/simulate-success/base-url-001/1/before.json
cat .runs/simulate-success/base-url-001/1/after.json
```

补丁的核心变化是：

```diff
-    return value.strip().rstrip("/").replace("/v1", "")
+    return value.strip().rstrip('/')
```

`before.json` 证明原实现违反约定；`after.json` 证明候选通过同一组验收。验收报告区分断言失败与基础设施错误：只有测试实际执行并报告 `assertion_failure` 才算复现；语法错误、导入失败、测试超时和没有执行测试会转交人工。源目录的 `gateway.py` 始终保留原样。这个练习将“已生成补丁”和“允许修改主代码”分成两个状态。

`--simulate` 使用预先写好的候选，只验证编排流程；**它不是 AI 修复能力的实测，也没有调用模型**。

## 观察自动化失败

```bash
python3 runner.py --simulate fail
python3 runner.py --simulate fail
python3 runner.py --simulate fail
```

依次得到 `retry`、`needs_human`、`idle`。模拟器返回 `value`，没有去除空格和末尾斜杠，因此固定验收失败；失败证据保存在本次尝试目录，并会传入下一次真实模型请求。尝试两次仍不合格就停下，不无限烧钱。

不同模式有独立状态目录，模拟结果不会阻止真实模型任务。需要重新做一次实验时指定新的目录即可，无需删除旧证据：

```bash
python3 runner.py --simulate success --state-dir .runs/another-experiment
```

## 接入真实 Claude

先安装支持下述参数的 Claude Code，并通过环境变量配置自己的 `ANTHROPIC_API_KEY`，然后运行：

```bash
claude --version
python3 runner.py --agent claude
```

此命令会请求真实模型、发送示例 issue 与源码并消耗 API 额度。**本示例交付时没有执行这一步**；只核对了官方参数与本机帮助，测试了模拟模式及 CLI 适配器。

runner 实际调用的是下列参数组合，提示词通过标准输入传入，API key 不写入代码：

```text
claude --bare -p --tools "" --permission-mode default
  --strict-mcp-config --no-session-persistence --disable-slash-commands
  --output-format json --json-schema <schema>
  --max-turns 3 --max-budget-usd 0.50
```

`-p` 让命令完成一次请求后退出；JSON Schema 约定回复结构。`--bare` 避免自动加载项目与用户的 hooks、插件、记忆和 MCP 服务，且只采用显式 API 凭据，**不使用已有订阅登录**。`--tools ""` 关闭模型的内置操作工具，未提供任何 MCP 服务；模型只能建议一个表达式。Python 进程限制请求 120 秒，CLI 设置最多 3 个 agentic turns 和估算费用上限。费用上限可能有超出量，不能当作精确账单硬上限。[官方 CLI 参数](https://code.claude.com/docs/en/cli-reference)、[官方程序化调用与 bare mode](https://code.claude.com/docs/en/headless)

我们没有使用 `--dangerously-skip-permissions`。本例选择“模型提出修改，普通程序应用修改”，是为了用少量代码讲清控制边界。要让 Agent 自由阅读整个项目、编辑多个文件和运行命令，需要另外设计工作区、工具权限和执行隔离。

## 为什么不能只说“只改这个文件”

模型返回的数据被当作不可信候选。它只能返回：

```json
{
  "path": "gateway.py",
  "expression": "value.strip().rstrip('/')",
  "reason": "只移除边界字符，保留完整路径"
}
```

runner 检查目标必须精确为 `gateway.py`，表达式仅允许对字符串 `value` 进行至多 4 次 `strip`、`lstrip`、`rstrip` 或 `replace` 调用，参数仅能为短字符串字面量。其他函数、导入、属性访问和附加语句都会被拒绝。再由 runner 渲染固定函数模板，写入临时工作副本；固定的 `acceptance.py` 在副本外运行，模型不能修改验收条件。

这是一种刻意缩小问题范围的做法，不是通用 Python 沙箱，也不适合直接扩展为执行任意模型生成代码。真实项目若开放 `Bash` 和任意代码修改，应在容器或虚拟机内运行，并控制凭据、网络与可写路径。

## 每个小机制解决什么问题

| 机制 | 本例如何处理 |
| --- | --- |
| 人工批准 | 只读取本地 `issues.json` 中 `approved: true` 且 `scope: gateway.py` 的条目；这个文件由操作者维护，不能让外部 issue 的正文设置授权 |
| 去重 | 每个 issue ID 对应持久化状态，`needs_review`/`needs_human` 不会自动重做；ID 代表一个不可变的任务版本，内容有实质变化时人工分配新 ID |
| 防止并发冲突 | 同一状态目录使用非阻塞文件锁，第二个进程得到 `busy`；进程退出后 OS 释放锁 |
| 崩溃恢复 | 启动前先记录 `running`；下一次发现遗留 `running` 则转为 `needs_human`，避免盲目重复不确定的操作 |
| 控制返工 | 普通失败可再尝试一次，越过范围立即停下；测试输出成为下一次请求的上下文 |
| 防止“自称成功” | 模型的 reason 不决定结果；是否通过由外部固定验收的退出码决定 |
| 证据保留 | 每次独立保存修复前后测试输出、候选、补丁、源码 SHA-256 和状态报告；模型调用失败时保留错误 |
| 人工出口 | 验收通过只进入 `needs_review`；人工看 diff、需求和证据后，自行应用补丁并重新验证 |

人工还需要处理凭据或 CLI 版本问题、无法复现的需求、验收条件不充分、范围外修改、崩溃与两次失败。这个示例有意不自动修改验收规则，不把一次失败自动升格为长期规则。

补丁只针对报告中 `source_sha256` 对应的源文件。runner 在产出补丁前再次检查源文件，若执行期间有其他人修改则转交人工；补丁产出后源代码仍可能变化，应用前也需要核对。源代码有变化时，旧补丁与旧验收结果都需要重新评估。本例没有实现真实仓库的 Git revision 绑定、PR 门禁和多任务依赖协调。

## 怎么变成“自动流”

`runner.py` **一次只处理一个任务，不自带定时器**。先把单次执行跑通，再让一种外部调度器定期调用它；不要同时安排多个独立调度器。

- 教学演练：手动重复执行，观察状态如何变化。
- 系统自动运行：由你使用的任务调度器定期调用 `python3 runner.py --agent claude`，确保它能取得显式配置的 API 凭据。本文没有安装或创建定时任务。
- Claude 会话中的 `/loop`：它是另一种调度方式。常见用法是让该会话直接执行限定的维护流程，而不是在“一个 AI 循环”里面再套一个新的 `claude -p` 模型调用。外层调度、内层单次执行的边界要清楚。

`/loop` 的运行条件和生命周期随版本变化，使用前查看[官方定时任务文档](https://code.claude.com/docs/en/scheduled-tasks)。本 demo 的去重、锁和停止条件由 Python 负责，不能仅靠自然语言提醒替代。
