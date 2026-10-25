---
title: "macOS 鼠须管使用记录：小鹤双拼、万象模型与 ms_sogou 主题"
description: "记录鼠须管搭配雾凇拼音、小鹤双拼、万象语法模型和 ms_sogou 主题的实际配置，包括日常快捷键、配置维护、更新和恢复方法。"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2026-10-25"
categories: ["tools"]
tags: ["RIME", "鼠须管", "小鹤双拼", "输入法", "macOS"]
slug: "rime-macos-install"
draft: false
---

最初使用 RIME，主要是出于输入隐私方面的考虑。这次重新配置鼠须管，我保留了熟悉的小鹤双拼。雾凇把双拼编码显示成完整拼音，这一点用起来不错；随后叠加万象语法模型改善整句选词，再把候选框换成字号较小的 `ms_sogou` 主题。

下面按 **2026 年 10 月 25 日的实际配置**记录，方便日常查阅，也便于以后换电脑时恢复。本文更新原来的安装笔记，保留原地址。

## 当前用的是哪几部分

| 部分 | 本次配置 | 作用 |
| --- | --- | --- |
| 输入法引擎 | librime 1.16.0 | 处理编码、词典、候选和输入方案 |
| macOS 客户端 | 鼠须管 Squirrel 1.1.2 | 接入系统输入源、显示候选窗口 |
| 方案与词库 | 雾凇拼音 | 简体词库、中英混输及常用扩展功能 |
| 主输入方案 | 小鹤双拼 `double_pinyin_flypy` | 使用小鹤键位，显示完整拼音 |
| 备用方案 | 雾凇全拼 `rime_ice` | 需要时从方案选单切换 |
| 语法模型 | `wanxiang-lts-zh-hans.gram` | 在本机改善整句选词；只挂到小鹤方案 |
| 候选框 | `ms_sogou` | 白底蓝字、橙红首选，横排 5 个候选 |

候选文字和顶部拼音是 **14 pt**，注释 **12 pt**，序号 **11 pt**。完整拼音放在候选框顶部独立一行。明暗主题目前都指定为 `ms_sogou`，因此系统切到深色模式时，候选框仍然是白底。

万象模型离线运行，不需要云端 API。它主要调整已有拼音对应的选词结果；本次没有开启“一个词上屏后，自动弹出下一词”的预测功能，也没有添加 AI 续写功能。

## 日常怎么用

在 macOS 菜单栏选择“鼠须管”，再按 **Control + 反引号**打开方案选单，选择“小鹤双拼”。`F4` 也可以打开选单，是否需要配合 `Fn` 取决于 Mac 的功能键设置。

### 常用按键

| 按键 | 当前行为 |
| --- | --- |
| 空格 | 确认当前候选并上屏 |
| 数字 `1`–`5` | 选择本页对应候选 |
| 左 Shift / 右 Shift | 切换中英文；有未确认的输入时，先输出原始编码 |
| Enter | 输出原始双拼编码，例如 `nihc` |
| Control + Enter | 输出转换后的完整拼音，例如 `ni hao` |
| Esc | 取消尚未上屏的输入 |
| `-` / `=` | 候选框出现时，上一页 / 下一页 |
| Tab / Shift + Tab | 编辑拼音时，移动到下一个 / 上一个音节 |
| Option + 左右方向键 | 编辑拼音时，按音节移动光标 |
| Control + Shift + 3 | 切换中文 / 英文标点 |
| Control + Shift + 4 | 切换简体 / 繁体 |

这里最容易混淆的是 **空格和 Enter**：要把候选“你好”输入到文稿中，应按空格；按 Enter 得到的是原始编码 `nihc`。同样，当前 Tab 用来移动音节，不是翻页或 AI 补全。

Shift 使用的是 `commit_code`。例如输入 `nihc` 后还没有选词，直接按 Shift，会输出 `nihc` 并切到英文。如果想保留中文，先按空格确认，再按 Shift。

Terminal、iTerm2、kitty 和 SecureCRT 配成了默认英文，在这些应用中需要中文时再切换。VS Code 没有加这项默认英文配置。

### 试打样例

下面是本次使用 RIME 引擎、在不带个人用户词频的临时目录中得到的测试结果。日常候选还会受个人词频影响。

| 小鹤编码 | 完整拼音提示 | 本次首选 |
| --- | --- | --- |
| `nihc` | `ni hao` | 你好 |
| `uurufa` | `shu ru fa` | 输入法 |
| `jbtmtmqihfhc` | `jin tian tian qi hen hao` | 今天天气很好 |
| `vuzdliwu` | `zhu zai li wu` | 住在里屋 |

最后一组在未挂模型时，首选是“住在礼物”；挂上万象后变成“住在里屋”。这说明模型在这组样例中起了作用，不代表所有句子都会更准确。

### 几个方便的小功能

以下触发词对应当前的小鹤双拼方案，在中文状态输入后从候选中选择：

| 输入 | 功能 |
| --- | --- |
| `date` | 当前日期 |
| `time` | 当前时间 |
| `week` | 星期 |
| `lunar` | 农历 |
| `cC1+2` | 计算器示例 |
| `Vhelp` | 符号输入帮助 |

自定义短语使用 `custom_phrase_double.txt`。全拼的 `custom_phrase.txt` 是另一个文件，不要改错。

## 安装与配置文件

新电脑先安装鼠须管，下面的命令不需要在已经配置好的电脑上重做：

```sh
brew install --cask squirrel-app
```

然后进入“系统设置 → 键盘 → 文字输入 → 编辑 → 添加”，在简体中文输入源中添加“鼠须管”。安装后若列表中没有出现，按官方说明注销再登录；有未保存的工作时，先保存再注销。

雾凇可通过 RIME 的配置管理工具“东风破 / plum”安装：

```sh
# 首次获取 plum；已有这个目录时直接进入，不要重复 clone。
git clone https://github.com/rime/plum.git "$HOME/plum"
cd "$HOME/plum"

# 安装雾凇完整方案和词库。
bash rime-install iDvel/rime-ice

# 适配小鹤双拼，以及英文派生和部件反查规则。
bash rime-install iDvel/rime-ice:others/recipes/config:schema=double_pinyin_flypy
```

已有 RIME 配置时，先备份再执行安装或更新。随后将下面的个人补丁合并进去，重新部署。

### 文件各管什么

用户目录是 `~/Library/Rime/`，也可以从鼠须管菜单的“用户设定”打开。

| 文件 | 用途 |
| --- | --- |
| `default.custom.yaml` | 启用的方案、候选数量、Shift 切换 |
| `squirrel.custom.yaml` | 主题、字体、排版和应用默认中英文 |
| `double_pinyin_flypy.custom.yaml` | 当前只放万象模型补丁 |
| `melt_eng.custom.yaml` | 英文派生规则适配小鹤 |
| `radical_pinyin.custom.yaml` | 部件反查规则适配小鹤 |
| `custom_phrase_double.txt` | 小鹤方案的自定义短语 |
| `wanxiang-lts-zh-hans.gram` | 万象简体语法模型文件 |
| `build/` | 部署生成的文件，用于核对生效结果，不直接编辑 |

个人修改放在 `.custom.yaml` 中，上游的 `default.yaml`、`squirrel.yaml` 和方案文件尽量保留原样。一个文件只有一个顶层 `patch:`；已有配置时，把新条目合并到它下面，不要再追加一个同名 `patch:`。

改完配置后，在鼠须管菜单选择“重新部署”，或在鼠须管进程运行时执行：

```sh
"/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel" --reload
```

### 全局习惯

`default.custom.yaml`：

```yaml
patch:
  schema_list:
    - schema: double_pinyin_flypy
    - schema: rime_ice
  menu/page_size: 5
  ascii_composer/switch_key/Shift_L: commit_code
  ascii_composer/switch_key/Shift_R: commit_code
```

本机已在方案选单中选定“小鹤双拼”，选择状态保存在 `user.yaml`。以后切换备用全拼也用方案选单，不必手工编辑这个运行状态文件。

双拼配套补丁分别是：

```yaml
# melt_eng.custom.yaml
patch:
  speller/algebra:
    __include: melt_eng.schema.yaml:/algebra_double_pinyin_flypy
```

```yaml
# radical_pinyin.custom.yaml
patch:
  speller/algebra:
    __include: radical_pinyin.schema.yaml:/algebra_double_pinyin_flypy
```

## 万象模型

鼠须管 1.1.2 的安装包已经带有 `librime-octagram` 插件，本次是在它之上添加模型文件和方案补丁，没有更换输入引擎。

在已安装 plum 的情况下，雾凇提供了现成配方：

```sh
cd "$HOME/plum"
bash rime-install iDvel/rime-ice:others/recipes/grammar:schema=double_pinyin_flypy
```

也可以从[万象 LTS 发布页](https://github.com/amzxyz/rime-wanxiang-data/releases/tag/LTS)下载 `wanxiang-lts-zh-hans.gram`，放入 `~/Library/Rime/`，再添加以下补丁。

本次安装文件更新于 **2026-10-19**，大小为 **398,497,836 字节，约 380 MiB**，SHA-256 为：

```text
9eedac1d836f3fdafb61b162035c8937253aedc106be40b2b957d9ab64e9ed89
```

LTS 地址上的文件仍可能更新。以后下载时以发布页当时的校验值为准，上面的值只对应本次安装文件。

`double_pinyin_flypy.custom.yaml`：

```yaml
patch:
  grammar:
    language: wanxiang-lts-zh-hans
    collocation_max_length: 6
    collocation_min_length: 3
    collocation_penalty: -14
    non_collocation_penalty: -6
    weak_collocation_penalty: -100
    rear_penalty: -20
  translator/contextual_suggestions: false
  translator/max_homophones: 8
```

这些参数沿用[雾凇的模型配方](https://github.com/iDvel/rime-ice/blob/da1fbe602e38f26db846fa10120ee64c2b0324c0/others/recipes/grammar.recipe.yaml)。其中 `contextual_suggestions: false` 是该配方的配置，不需要为了“启用模型”把它改成 `true`。

重新部署后，`build/double_pinyin_flypy.schema.yaml` 中应出现 `grammar/language: wanxiang-lts-zh-hans`。运行时日志中的 `use grammar: wanxiang-lts-zh-hans` 和 `loading gram db:` 可以进一步确认实际加载；本次安装已核对过这些记录。

完整拼音提示来自小鹤方案中的 `translator/preedit_format`。添加模型或换主题时不需要修改它。原来的词库引用 `dictionary: rime_ice`、拼写规则和拼音注释配置也都保留。

## ms_sogou 主题

主题来自这份[现成鼠须管配置](https://github.com/epoweripione/dotfiles/blob/f09f90ad77012c2e0645e86318571b15046fe375/conf/rime/squirrel.custom.yaml#L3)，配色名为 `ms_sogou`，作者标注为 Mark24Code。

我保留了它的白底、蓝色候选和橙红色首选。原主题的注释是白色，在白底上看不清，这里改成深灰；候选和拼音从之前的 16 pt 缩到 14 pt。

以下是 `squirrel.custom.yaml` 中与当前效果有关的配置。旧主题定义可以留着；合并时保留已有的应用配置和其他个人设置。

```yaml
patch:
  style/color_scheme: ms_sogou
  style/color_scheme_dark: ms_sogou
  style/candidate_list_layout: linear
  style/text_orientation: horizontal
  style/inline_preedit: false
  style/inline_candidate: false

  style/font_face: PingFangSC-Regular
  style/font_point: 14
  style/label_font_face: Helvetica
  style/label_font_point: 11
  style/comment_font_face: PingFangSC-Regular
  style/comment_font_point: 12

  style/candidate_format: '[label] [candidate] [comment]'
  style/corner_radius: 6
  style/hilited_corner_radius: 4
  style/border_width: 0
  style/border_height: -2
  style/line_spacing: 4
  style/spacing: 5
  style/translucency: false
  style/mutual_exclusive: false
  style/shadow_size: 0
  style/memorize_size: true
  style/show_paging: true

  app_options/com.apple.Terminal:
    ascii_mode: true
    no_inline: true
  app_options/com.googlecode.iterm2:
    ascii_mode: true
    no_inline: true
  app_options/net.kovidgoyal.kitty:
    ascii_mode: true
    no_inline: true
  app_options/com.vandyke.SecureCRT:
    ascii_mode: true
    no_inline: true

  preset_color_schemes/ms_sogou:
    author: Mark24Code
    name: 搜狗／Sogou
    color_space: srgb
    back_color: '0xFFFFFF'
    border_color: '0xFFFFFF'
    candidate_text_color: '0xD67F42'
    comment_text_color: '0x6C6560'
    hilited_comment_text_color: '0x6C6560'
    label_color: '0x6C6560'
    hilited_candidate_label_color: '0x0D4FE9'
    hilited_back_color: '0xFFFFFF'
    hilited_candidate_back_color: '0xFFFFFF'
    hilited_candidate_text_color: '0x0D4FE9'
    hilited_text_color: '0xD9884F'
    text_color: '0xD9884F'
```

`inline_preedit: false` 把完整拼音放到候选框顶部。若以后想让拼音回到文稿光标处，把这一项改为 `true`，重新部署即可；显示的拼音内容仍由原方案处理。

鼠须管 1.1.2 中，顶部拼音与候选共用 `font_point`，没有独立的 `preedit_font_point`。序号和注释则有各自的字号设置。

颜色使用 **BGR / ABGR**，不是常见的 RGB。配置中应保留带 `0x` 的字符串，例如 `'0xD67F42'`。用 YAML 工具生成文件时，不要把它转换成十进制数字，否则鼠须管可能无法解析，退回默认颜色。

`show_paging: true` 只显示翻页箭头。当前鼠须管不能仅靠主题实现搜狗那种“点击下拉，展开成多行多列网格”的交互。横排内容过长时可以自然换行，但不能把它当成固定列数的展开面板。

## 更新、备份和恢复

### 改配置前先备份

只修改主题或方案补丁时，可以先备份这些个人配置：

```sh
rime_backup="$HOME/Library/Rime-backups/manual-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$rime_backup"
cp "$HOME/Library/Rime/"*.custom.yaml "$rime_backup/"
```

这份备份只覆盖 `.custom.yaml`。自定义短语、用户词库和同步数据需要另外保存，不能把配置备份当成全部输入数据的备份。

本次操作留下了三份配置备份，均位于 `~/Library/Rime-backups/`：

| 目录名 | 对应状态 |
| --- | --- |
| `before-wanxiang-20261024-202313` | 添加万象前的小鹤配置 |
| `before-theme-20261024-203612` | 调整主题前，已添加万象 |
| `before-ms-sogou-20261024-205613` | 切换 ms_sogou 前的紧凑主题，已添加万象 |

### 只恢复主题

例如，想恢复到切换 `ms_sogou` 之前的紧凑主题：

```sh
cp "$HOME/Library/Rime-backups/before-ms-sogou-20261024-205613/squirrel.custom.yaml" \
   "$HOME/Library/Rime/squirrel.custom.yaml"

"/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel" --reload
```

这里只恢复 `squirrel.custom.yaml`，不会改动小鹤键位和万象模型。不需要用整份旧目录覆盖当前用户词库。

### 暂时关闭万象模型

当前的 `double_pinyin_flypy.custom.yaml` 只包含万象补丁。需要对比原来的输入效果时，可把它改名为 `double_pinyin_flypy.custom.yaml.disabled`，然后重新部署；恢复原文件名后再部署，就能重新启用。

改名前确认目标备份名没有被占用。模型文件可以继续保留。如果以后在这个补丁里加入了其他个性化设置，就只移除 `grammar` 和本次添加的两个 `translator` 参数，不要停用整个文件。

### 更新雾凇方案和词库

备份后，在 plum 目录再次执行：

```sh
cd "$HOME/plum"
bash rime-install iDvel/rime-ice
```

这个命令执行完整配方，会更新雾凇的词库、方案、Lua 和基础配置，不只是下载词库。完成后重新部署，检查小鹤方案仍在、完整拼音提示正常、万象模型仍加载。个人设置放在 `.custom.yaml` 中，可以减少更新上游配置时相互覆盖的情况。

更新模型时单独使用万象配方或官方 LTS 下载页，不必为更新模型更换整套输入方案。`releases/latest` 可能指向词库或工具发布，不一定是语法模型。

## 遇到问题先看哪里

| 现象 | 检查项 |
| --- | --- |
| 输入的是英文字母，没有中文候选 | 确认系统选中“鼠须管”，并检查是否处于英文模式；终端默认英文是当前配置 |
| 按 Enter 没有输出候选中文 | 当前 Enter 输出原始编码，空格才确认候选 |
| 主题修改后没变化 | 检查 YAML 缩进、是否只有一个 `patch:`，并执行重新部署；不要直接改 `build/` |
| 颜色变灰或高亮不见了 | 检查是否保留了 `0x` 十六进制字符串，而不是生成了十进制数字 |
| 拼音提示位置不习惯 | 调整 `squirrel.custom.yaml` 的 `style/inline_preedit`，不用改小鹤键位或万象补丁 |
| 怀疑模型没有生效 | 核对 `.gram` 文件名、`grammar/language`、重新部署结果及运行时模型加载日志 |
| 只想回退外观 | 恢复对应备份的 `squirrel.custom.yaml`，不覆盖整个 Rime 用户目录 |

## 参考

- [RIME 官方下载与安装](https://rime.im/download/)
- [雾凇拼音：安装、双拼及语法模型说明](https://github.com/iDvel/rime-ice)
- [雾凇的小鹤双拼方案](https://github.com/iDvel/rime-ice/blob/da1fbe602e38f26db846fa10120ee64c2b0324c0/double_pinyin_flypy.schema.yaml)
- [万象语法模型与数据项目](https://github.com/amzxyz/rime-wanxiang-data)
- [鼠须管 1.1.2 的界面配置](https://github.com/rime/squirrel/blob/1.1.2/data/squirrel.yaml)
- [ms_sogou 主题来源](https://github.com/epoweripione/dotfiles/blob/f09f90ad77012c2e0645e86318571b15046fe375/conf/rime/squirrel.custom.yaml#L3)
