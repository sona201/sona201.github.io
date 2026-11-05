---
title: "英语学习记录：从技术话题开始练习表达"
description: "记录技术英语的翻译、半开放回答和纠错过程，先补上关于工具复用与 Agent Skills 评估的两次练习，再跟踪能否换个场景独立使用。"
date: "2026-11-05T00:00:00+08:00"
lastmod: "2026-11-05T00:00:00+08:00"
categories: ["学习"]
tags: ["英语", "学习记录", "ChatGPT"]
slug: "english-learning-log"
draft: false
---

最近，我已经在 ChatGPT 的「每日英文视频推荐」对话里开始做英语练习。材料围绕软件工程和 AI Agent 展开，练习也会用到工具复用、测试和验证这些话题。这篇先把最近两次实际写过的句子整理下来，之后继续在这里补充。

回看已经提交的句子，问题很具体：我写出了 `can reuseable`，也把“用测试用例”写成了 `by test cases`。这些错误落在词形和搭配上。这里把原句也留下来，之后再看看，同样的问题还会不会出现。

## 现在怎么练

目前做的练习分成两类。一类是固定句翻译，先给中文意思，再用英文表达；另一类是半开放回答，给一个技术问题，由我自己选择要说什么，再组织成句子。

提交时，我会请 ChatGPT 尽量保留原句结构，解释语法、拼写和搭配问题，并分别评价这两类回答。最后再给一道换场景的练习，不提前给答案。这也是为了看清楚：原句改对以后，换一个内容，我还能不能自己写出来。

对话里的材料安排通常是五分钟视频，再配词汇、例句和输出练习。不过，收到材料和完成练习是两回事。这篇先记录已经提交的回答，不把推荐过的视频都算成学完了。

## 11 月 4 日：把“复用”放进句子里

这次练的是工具和脚本复用。固定句翻译的原句是：

> we should reuse existing tools, instead of creating new Agent for every task

整理后可以写成：

> We should reuse existing tools instead of creating a new agent for every task.

`instead of creating` 已经用出来了。这里要补的是 `a new agent` 中的冠词，以及句首大写等细节。`agent` 在这个句子里指一个新的 Agent，不能把单数名词直接留在那里。

半开放回答就暴露了更多问题：

> Agent Skills can reuseable to help my development work, instead of creating existing scripts for every development work

我想表达的是，Skills 可以复用，帮助开发时减少重复编写脚本。保留这个意思，可以改成：

> Agent Skills can be reused to support my development work, so I don't have to write the same scripts for every development task.

这里最需要分清的是三种形式：

| 表达 | 意思 |
| --- | --- |
| We can reuse skills. | 我们可以复用 Skills。 |
| Skills are reusable. | Skills 是可复用的。 |
| Skills can be reused. | Skills 可以被复用。 |

我写的 `reuseable`，正确拼写是 `reusable`。但只改拼写还不够：它是形容词，不能直接接在 `can` 后面。想说“可以被复用”，这里需要 `can be reused`。[^passive]

另外，`creating existing scripts` 把动作和对象配错了。已有的脚本可以 `reuse`，想避免的重复劳动则是 `writing the same scripts again`。`every development work` 也要改：`work` 表示工作时通常不可数，这里用 `every development task` 更合适。[^work]

这次两道题放在一起，差别比较明显。中文意思已经给定时，我能沿着 `instead of + doing` 写下去；需要自己决定内容时，词形、搭配和句子之间的关系就容易乱。后面需要继续看，这个差别会不会随着练习缩小。

## 11 月 5 日：追问一次批改里的解释

这次主题换成了 Agent Skills 的评估。固定句翻译要表达的是：我们应该验证最终结果，而不是只检查 Agent 是否调用了 Skill。

我的原句：

> We should verify the finnal result, instead of checking the Skills are called by Agent

修改后的一个版本是：

> We should verify the final result instead of only checking whether the agent called the skill.

`finnal` 要改成 `final`，原句也漏掉了“只检查”里的 `only`。不过，这次让我继续追问的，是 ChatGPT 对从句的解释。它最初说，`checking` 后面不能直接接完整陈述句，所以需要加 `whether`。

我问了一句：“为什么不能直接接完整的陈述语句？”

接着它修正了前面的说法：`check` 可以接 `that` 从句，`that` 有时也可以省略。因此，不能简单记成“没有 `whether` 就一定错”。整理这篇记录时，又核对了 Cambridge Dictionary，`check` 词条确实标了 `+ (that)`，例句也把 `that` 放在括号里。[^check]

这几种表达可以放在一起看：

| 表达 | 这里想表达的意思 |
| --- | --- |
| Check the result. | 检查结果。 |
| Check that the API works. | 确认 API 正常工作。 |
| Check whether the API works. | 检查 API 是否正常工作。 |

回到我的句子，使用 `whether` 能更明确地表达“是否调用了”。这是根据意思选择表达方式，和“`check` 后绝对不能直接接一个从句”不是同一回事。这一处先记下来，之后碰到类似句子时还可以对照。

同一天的半开放问题是：怎样验证一个 Agent Skill 是否有用？我的回答是：

> I would test the skills by test cases, beause test cases are reliable, they can verify code logic

整理后的版本：

> I would test the skills using test cases because well-designed test cases can help verify whether the skills work as expected.

这里除了 `beause` 的拼写，还有两个值得留下的问题。一个是怎样表达手段：这里可以用 `using test cases`，也可以写 `by running tests`。另一个是把想说的内容说准：测试用例是否可靠还要看具体设计，不能只因为有了测试，就默认它能证明结果正确。

修改后的句子把意思收到了“设计良好的测试用例可以帮助检查 Skills 是否按预期工作”。它也把原来用逗号接在后面的 `they can...` 收进原因从句，读起来更完整。

## 要不要开始背句子

11 月 5 日，我还问了一个新的问题：要不要尝试背英文句子或者段落，尚雯婕的方法有没有参考性？

对话里的建议是先选短句，理解后跟读、脱稿回忆，再换成自己的场景表达；也提出了“每天两句，先试两周”的做法。这次整理的记录里，只有提问和建议，还没有采用之后的练习结果。

这个问题可以和前面的练习接起来。比如 `instead of + doing` 已经在两次回答里出现了，`can be reused` 却还需要纠正。之后如果开始背句子，可以观察的不只是当天能不能背出原句，还包括隔几天能否想起来，换成模板、会议纪要等内容时能否用对。

## 接下来在这里跟踪什么

先把截至 11 月 5 日的状态留在这里，后续有新的回答，再追加原句、修改和实际结果。

| 跟踪项 | 目前记录 | 后续要看什么 |
| --- | --- | --- |
| `instead of + doing` | 两次提交中都已使用 | 换个话题、不看例句时能否继续用对 |
| `reuse / reusable / be reused` | 已整理区别，原句里出过错 | 能否根据主语选择主动、形容词或被动形式 |
| 冠词、可数名词和搭配 | 出现过 `new Agent`、`every work`、`by test cases` | 下一次独立回答里是否仍会出现 |
| 背句子或短段落 | 已记录提问和建议，尚未收录实践结果 | 实际采用什么做法，之后能否换场景使用 |

对话里还留下了两组换场景练习：用模板整理会议纪要，以及发布新版本前验证 API 兼容性。这篇还没有收录对应的回答，先留在这里。后续补进来，再和上面的句子一起看。

[^passive]: [Cambridge English Grammar Today：Passive: forms](https://dictionary.cambridge.org/grammar/british-grammar/passive-forms)，说明被动结构由 `be` 与过去分词构成，并列出情态动词后的被动形式。

[^work]: [Cambridge English Grammar Today：Nouns: countable and uncountable](https://dictionary.cambridge.org/grammar/british-grammar/countable-uncountable)，将 `work` 列为不可数名词，并给出 `a job`、`a task` 这类具体表达。

[^check]: [Cambridge Dictionary：check](https://dictionary.cambridge.org/us/dictionary/english/check)，词条中的 `+ (that)` 及例句支持此处对省略 `that` 的说明。
