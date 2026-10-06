---
title: "AI Agent 学习笔记：CrewAI 与 ReAct"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["AI"]
tags: ["AI", "Agent", "CrewAI", "ReAct"]
draft: false
---


#agent #ai #react #plantegg

# 学习笔记：使用 CrewAI 复刻 Claude Code 级的 AI Agent

## 1. 什么是 CrewAI？

**CrewAI** 是一个用于编排协同式 AI Agent 的 Python 框架。如果说 LLM（大语言模型）是一个聪明的“大脑”，那么 CrewAI 就是一个**“项目经理”**。

### 核心四元素：

- **Role (角色)**：定义 Agent 的身份（如：DBA 专家、技术作家）。
    
- **Task (任务)**：定义具体要做的事情。
    
- **Tools (工具)**：Agent 可以调用的技能（如：SSH 远程执行、数据库查询）。
    
- **Process (流程)**：规定 Agent 之间如何协作（顺序、层级等）。
    

---

## 2. 核心原理：ReAct 工作模式

文章中复刻 Claude Code 的核心逻辑是 **ReAct (Reasoning + Acting)**，这是目前 Agent 最主流的工作方式。

### ReAct 循环公式：

> **Thought (思考) → Action (行动) → Observation (观察) → Thought (再思考)**

1. **Thought**：模型根据用户问题，思考当前需要什么信息。
    
2. **Action**：模型决定调用哪一个工具（Tool）以及参数是什么。
    
3. **Observation**：Agent 执行工具并拿到结果（如 Linux 报错信息或 SQL 查询结果）。
    
4. **Next Thought**：模型根据反馈结果，决定是继续调用工具，还是输出最终答案。
    

---

## 3. Agent 开发三要素

开发一个功能强大的 Agent，本质上是在配置以下三个部分：

|**要素**|**作用**|**示例**|
|---|---|---|
|**LLM (大脑)**|提供推理和决策能力|Claude 3.5 Sonnet, GPT-4o|
|**Tools (手脚)**|让模型能与现实世界交互|`ssh_tool`, `mysql_query_tool`|
|**Prompt (指令)**|定义角色、规则和约束|"你是一个资深 DBA，只允许执行读操作"|

---

## 4. 实战：从 0 到 1 组建运维 Agent

根据参考文章，构建一个 MySQL 运维 Agent 的步骤如下：

### Step 1: 定义自定义工具

工具是 Agent 的“手脚”。每个工具必须包含 `description`，因为**模型是靠这段描述来判断何时使用该工具的**。

```python
from crewai.tools import BaseTool

class MySQLQueryTool(BaseTool):
    name: str = "mysql_query"
    description: str = "用于执行 MySQL 只读查询语句，获取数据库状态。"

    def _run(self, query: str):
        # 实际执行 SQL 的 Python 代码
        return "查询结果文本"
```

### Step 2: 配置 Agent 与 Task

```python
from crewai import Agent, Task, Crew

# 1. 定义 Agent
dba_agent = Agent(
    role="DBA 运维专家",
    goal="诊断 MySQL 性能瓶颈",
    backstory="你拥有 10 年运维经验，擅长通过慢查询日志定位问题。",
    tools=[MySQLQueryTool()], # 载入工具
    verbose=True # 开启 debug 模式，查看思考过程
)

# 3. 定义任务
task = Task(
    description="分析 10.0.0.1 机器上的慢查询并给出优化建议",
    expected_output="一份包含问题原因和优化建议的 MD 报告",
    agent=dba_agent
)

# 4. 组建团队启动
crew = Crew(agents=[dba_agent], tasks=[task])
result = crew.kickoff()
```

---

## 5. 关键洞察（踩坑总结）

- **模型没有记忆**：每一轮 ReAct 交互，Agent 都会把之前的对话历史、工具返回结果打包成一个巨大的 Prompt 重新发给模型。这意味着 Token 消耗会随轮数剧增。
    
- **模型不会执行工具**：大模型只输出“指令字符串”，真正去执行 SSH 或 Python 代码的是 **CrewAI 框架**。
    
- **工具描述至关重要**：如果 Agent 总是用错工具，通常是因为 `description` 写得不清晰。
    
- **安全边界**：在运维场景下，必须在工具的 Python 代码层做好拦截（如禁止 `DROP`, `DELETE` 等操作），不能仅靠 Prompt 约束。
    

---

## 6. 进阶方向

1. **接入更多数据源**：将 Prometheus 监控、日志平台 API 封装为 Tool。
    
2. **多 Agent 协作**：一个 Agent 负责搜集数据，另一个 Agent 负责编写最终诊断报告。
    
3. **Human-in-the-loop**：在执行高风险 Action 前，让 Agent 停下来等待人类授权。
    

---

_笔记来源：基于 [plantegg 博客](https://plantegg.github.io/2026/03/05/%E4%BB%8E0%E5%88%B01%E5%A4%8D%E5%88%BB%E4%B8%80%E4%B8%AAClaude_Code%E8%BF%99%E6%A0%B7%E7%9A%84Agent/) 与 CrewAI 官方文档整理。_
