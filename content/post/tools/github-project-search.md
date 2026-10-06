---
title: "GitHub 项目精准搜索笔记"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["tools"]
slug: "github-project-search"
draft: false
---

# Gihub精准搜索开源项目

## 开源项目的组成部分

源项目组成部分：

- name: 项目名
- description: 项目的简要描述
- 项目的源码
- README.md: 项目的详细情况的介绍

除了这些要素之外，项目本身的`star`数和`fork`数，也是评判一个开源项目是否火热的标准，这同时也是一个很重要的搜索标准。另外我们也要注意观察这个项目的最近更新日期，因为项目越活跃，那么它的更新日期也更加频繁。

以上要素就是我们在进行搜索的时候要注意的一些关键点。

## 方法总结

增加筛选条件精准搜索。

1. `in:name xxx  # 按照项目名搜索`
2. `in:readme xxx  # 按照README搜索`
3. `in:description xxx  # 按照description搜索`

附加增加筛选条件

1. `stars:>xxx  # stars数大于xxx`
2. `forks:>3000  # forks数大于xxx`
3. `language:xxx  # 编程语言是xxx`
4. `pushed:>YYYY-MM-DD  # 最后更新时间大于YYYY-MM-DD`

最后绝招:  官方提供精准搜索，官方搜索左下角: [advanced](https://github.com/search/advanced)
