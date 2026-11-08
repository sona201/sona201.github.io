---
title: "重新配置鼠须管：小鹤双拼、万象模型和候选框"
description: "记录小鹤双拼、万象模型、英文输入和候选框调整，以及 Mac 通讯录与飞书联系人姓名导入词库的过程。"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2026-11-08"
categories: ["tools"]
tags: ["RIME", "鼠须管", "小鹤双拼", "输入法", "macOS"]
slug: "rime-macos-install"
draft: false
---

最初用 RIME，主要是出于输入隐私方面的考虑。这次重新配置鼠须管，小鹤双拼还是继续用。雾凇能把双拼编码显示成完整拼音，这一点我觉得挺好，也想保留下来。接下来要调整的是选词和候选框：选词试了万象模型，候选框则希望小一点，拼音和注释能看得清楚。

配置好以后，又碰到了几个具体问题。比如输入英文缩写 `sdp`，候选框里却出现了 `sai p` 和“赛跑”；换上搜狗配色之后，也没有得到搜狗那种向下展开的候选框。这些问题涉及的配置其实不在同一个地方，正好一起记下来。

基础配置对应 **2026 年 10 月 26 日**的使用状态：鼠须管 Squirrel 1.1.2，内置 librime 1.16.0，使用雾凇词库、小鹤双拼和万象模型。**11 月 8 日**又补充了 Mac 通讯录和飞书联系人姓名的导入记录。文章沿用以前安装笔记的地址，后续有调整再接着更新。

## 先把小鹤双拼配好

Rime、鼠须管、雾凇这几个名字经常一起出现，但各自负责的事情不同。Rime 处理输入编码、词库和候选词，鼠须管把它接到 macOS 的输入系统里，并负责显示候选窗口。雾凇则提供了一套方案、词库和扩展功能。我们平时改“小鹤键位”“候选框颜色”“英文词库”，改的也就不是同一份文件。

在新电脑上，可以通过 Homebrew 安装鼠须管：

```sh
brew install --cask squirrel-app
```

安装后，到“系统设置 → 键盘 → 文字输入 → 编辑 → 添加”里添加鼠须管。如果列表中没有出现，官方建议注销再登录，让系统重新识别输入法。已经配置好的电脑不用重新安装。

雾凇可以用 Rime 的配置管理工具 plum 安装，也就是“东风破”：

```sh
git clone https://github.com/rime/plum.git "$HOME/plum"
cd "$HOME/plum"
bash rime-install iDvel/rime-ice
bash rime-install iDvel/rime-ice:others/recipes/config:schema=double_pinyin_flypy
```

第一条 `rime-install` 安装雾凇，第二条选择小鹤双拼，并适配相关规则。已经有 plum 目录时，进入原目录即可，不用重复 clone。已有自己的 Rime 配置，也应该先留一份备份再执行，因为这会安装整套方案和词库。[雾凇的说明](https://github.com/iDvel/rime-ice)里有各个配方的用途。

鼠须管的用户配置放在 `~/Library/Rime/`。我把个人修改写进 `.custom.yaml`，这样更新雾凇时，可以继续保留自己的习惯。例如 `default.custom.yaml` 里现在是：

```yaml
patch:
  schema_list:
    - schema: double_pinyin_flypy
    - schema: rime_ice
  menu/page_size: 5
  ascii_composer/switch_key/Shift_L: commit_code
  ascii_composer/switch_key/Shift_R: commit_code
```

这里启用了小鹤双拼和雾凇全拼。全拼留作备用，平时在方案选单里选择小鹤。`menu/page_size: 5` 表示每页五个候选，后面两个设置则让左右 Shift 都可以切换中英文。

选择方案可以按 **Control + 反引号**，也可以按 F4；Mac 上是否要配合 Fn，取决于功能键设置。选择结果会保存在 `user.yaml` 中，不需要手工修改它。

小鹤还有两份配套补丁，分别适配英文派生和部件反查：

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

这两个代码块对应两个文件。合并其他配置时，每个文件只保留一个顶层 `patch:`，把条目放到它下面即可。

配好后，输入 `nihc`，候选框上面显示的是 `ni hao`，下面可以选择“你好”。把双拼转换成完整拼音显示，是小鹤方案里 `translator/preedit_format` 做的事情。以后换模型或者换颜色，都不用动这部分。实际词库仍然是 `dictionary: rime_ice`。

改完配置，需要让鼠须管重新部署。在菜单中选择“重新部署”，或者在鼠须管运行时执行：

```sh
"/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel" --reload
```

`build/` 里的文件是部署结果，可以用来检查配置有没有生效，但不要直接在那里修改。下一次部署会重新生成它们。

## 输入英文时，空格和回车不一样

这次碰到的例子是 `sdp`。我想输入这三个英文字母，候选框却显示了 `sai p`，首选是“赛跑”。

原因并不复杂：英文词库没有收录 `sdp`，而它又能按小鹤双拼解析。`sd` 对应 `sai`，后面接着 `p`，于是候选框里就出现了 `sai p` 和“赛跑”。完整拼音提示改变了显示内容，原始输入仍然是 `sdp`。

这里最有用的按键其实是 **Enter**。用当前配置在独立目录里测试，得到的是下面这些结果：

| 输入后的操作 | 输出 | 接下来是什么状态 |
| --- | --- | --- |
| `sdp` 后按 Enter | `sdp` | 仍然是中文 |
| `sdp` 后轻按 Shift | `sdp` | 切到英文 |
| `sdp` 后按空格 | 赛跑 | 仍然是中文 |

所以，中文里临时穿插一个缩写，打完后按回车就可以了，下一段中文接着输入。如果接下来要写一段英文，再按 Shift 切过去，写完后按 Shift 切回来。

这是因为当前方案把 Enter 绑定为 `commit_raw_input`，也就是输出原始输入；空格则确认当前候选。Shift 用的是前面配置的 `commit_code`，会先输出原始输入，再切换输入状态。它们处理的是不同的东西。

这也解释了为什么输入 `nihc` 后按 Enter，得到的是 `nihc`，而不是“你好”。要输入中文候选，按空格；要输出 `ni hao` 这样的完整拼音，才用 **Control + Enter**。

中英混输本身已经启用了，方案里挂载了 `melt_eng` 英文翻译器和 `cn_en` 中英混合词汇。例如输入 `hello`，首选就是 `hello`，按空格后仍留在中文状态，不用来回切换。陌生缩写和已有英文单词的区别，主要在于词库能不能找到对应候选，以及它和拼音是否重码。雾凇作者也专门写过[英文输入体验的说明](https://dvel.me/posts/make-rime-en-better/)。

如果一个缩写经常用，可以把它加进英文词库，或者写进小鹤的 `custom_phrase_double.txt`。全拼使用的是另一个文件 `custom_phrase.txt`，不要改错。10 月那次没有添加 `sdp` 词条，也没有调整中英文权重。

另外几个日常操作也顺手记在这里：数字 `1`–`5` 选本页候选，`-` 和 `=` 翻页，Esc 取消输入。Tab 和 Shift + Tab 用来移动到下一个、上一个音节，不是补全；Option + 左右方向键也可以按音节移动。Control + Shift + 3 切换中英文标点，Control + Shift + 4 切换简繁体。

雾凇还带了一些小功能，在中文状态输入 `date`、`time`、`week`、`lunar` 可以得到日期、时间、星期和农历；`cC1+2` 可以计算，`Vhelp` 可以查看符号输入帮助。这些触发词对应本文的小鹤方案。

## 把 Mac 通讯录和飞书联系人加入词库

**2026 年 11 月 8 日**，又给这套配置补了联系人姓名。先读 Mac 通讯录，再取飞书里和我有过单聊的工作联系人，把姓名整理成 Rime 词库。这样平时输入拼音时，就可以直接选择联系人姓名。

Mac 这一批通过系统通讯录读取，只提取姓名。157 条联系人记录去重后，得到 156 个不同的显示名；加上多音字读音和英文别名，最终写入 159 条中文词条、6 条英文词条。

飞书选择的是单聊联系人，用已经登录的 `lark-cli` 分页读取：

```sh
lark-cli im +chat-list --as user --types p2p \
  --page-size 100 --page-all --page-limit 100 --format json
```

这一步取的是会话列表和对方显示名，不需要读取聊天正文。本次共读完 4 页、324 个单聊会话，再按 `p2p_target_type=user` 筛选，留下 256 位用户，排除 68 个机器人。取完后还核对了分页结果，确认没有剩余页面。这个范围对应我当前可见的单聊联系人，不代表整个公司的通讯录。

飞书的显示名常把中文姓名和英文昵称写在一起，所以整理时把两者拆开，各自作为候选。去重后得到 253 个中文姓名、193 个英文名，其中 1 个中文姓名已经在 Mac 联系人词库里，最终新增的是 **252 个中文姓名、193 个英文名**。部分中文姓名保留了两种读音，因此新中文词库有 256 条词条。

两批姓名分别保存成四个文件，都放在 `~/Library/Rime/`：

| 来源 | 中文词库 | 英文词库 |
| --- | --- | --- |
| Mac 通讯录 | `contacts.dict.yaml` | `contacts_en.dict.yaml` |
| 飞书单聊联系人 | `feishu_contacts.dict.yaml` | `feishu_contacts_en.dict.yaml` |

中文词条写无声调的完整拼音，音节之间用空格分开，不需要另写一套小鹤双拼编码。前面的小鹤和备用全拼共用 `rime_ice` 词典，部署时会按方案处理编码。[Rime 的词典说明](https://github.com/rime/home/wiki/RimeWithSchemata#碼表與詞典)也说明了这种共用方式和词条格式。

下面用虚构姓名演示 `feishu_contacts.dict.yaml` 的格式：

```text
# Rime dictionary
# encoding: utf-8

---
name: feishu_contacts
version: "2026-11-08"
sort: by_weight
...
张三	zhang san	100
```

词条的三列分别是文字、编码和权重，列与列之间必须用真正的 **Tab** 分隔。网页复制或编辑器设置可能把 Tab 换成空格，写入前要检查。英文词库的表头同理，`name` 改为对应的文件名，例如 `feishu_contacts_en`；本次英文编码统一取小写字母，候选文字保留原来的大小写，虚构条目可以写成：

```text
ExampleName	examplename	100
```

中文读音先由 macOS 的转写功能生成，再补上姓氏和常见多音字的读音规则。这里不能把自动转写当成人名读音的最终确认；有歧义的姓名先保留备选读音，日后再按本人读法修正。另一个细节是 `ü`，去掉声调时仍要保留它和 `u` 的区别，再转成词库使用的 `v`，例如“吕”是 `lv`。

词库文件放好以后，还要挂到入口词库里。本次在 `rime_ice.dict.yaml` 的 `import_tables` 中加入两份中文词库，保留原有条目：

```yaml
import_tables:
  - cn_dicts/8105
  - contacts
  - feishu_contacts
  - cn_dicts/base
  - cn_dicts/ext
  - cn_dicts/tencent
  - cn_dicts/others
```

英文则挂到 `melt_eng.dict.yaml`：

```yaml
import_tables:
  - contacts_en
  - feishu_contacts_en
  - en_dicts/en_ext
  - en_dicts/en
```

这里记录的是这台电脑当时的列表；合并时还要保留自己额外启用的词库。挂载方法可以对照雾凇的[中文入口词库](https://github.com/iDvel/rime-ice/blob/main/rime_ice.dict.yaml)和[英文入口词库](https://github.com/iDvel/rime-ice/blob/main/melt_eng.dict.yaml)。这次直接改了这两个入口文件，它们属于上游配置，之后更新雾凇要检查这四个挂载项是否仍在，不能只保存 `.custom.yaml`。

修改前先备份入口文件，再写入联系人词库，最后执行前面的 `--reload` 重新部署。两批操作的备份另外放在 `~/Library/Rime/backups/`，对应 `contacts-20261108-230202` 和 `feishu-contacts-20261108-231928`。

部署后，用本机 librime 在独立的用户目录里逐条检查候选，避免测试写入日常使用的用户词频。四份词库合计 614 条词条，在小鹤和全拼下各测一遍，共 1,228 项，最终都能找到对应候选。不过“能找到”不等于首选：三个很短的英文昵称，在全拼下输入小写时排到了 300 名之后，首字母改成大写后才进入前两个候选。这次验证的是词条已经可用，实际排序还要看输入和使用习惯。

目前这是一次性导入的姓名快照。以后新增联系人或有人改名，需要重新提取、去重并生成对应词库，再重新部署；还没有设置定时同步。实际姓名词库留在本机，博客里只记录方法和统计结果。

## 给整句选词加一个模型

万象模型改善的是整句选词。比如小鹤编码 `vuzdliwu` 对应 `zhu zai li wu`，可以组成“住在礼物”，也可以组成“住在里屋”。10 月 24 日首次挂上模型时，在不带个人词频的测试目录中，首选就从前者变成了后者。

这组例子比较容易看出模型的作用，但不能因此认定每句话都会更准确。模型是在本机参与选词，不需要云端 API。这次也没有开启“一个词输入完，自动弹出下一个词”的预测，更没有接入 AI 续写。

鼠须管 1.1.2 已经带有 `librime-octagram` 插件，因此可以直接使用万象的 `.gram` 模型。雾凇提供了现成配方：

```sh
cd "$HOME/plum"
bash rime-install iDvel/rime-ice:others/recipes/grammar:schema=double_pinyin_flypy
```

也可以从[万象 LTS 发布页](https://github.com/amzxyz/rime-wanxiang-data/releases/tag/LTS)下载 `wanxiang-lts-zh-hans.gram`，放到 `~/Library/Rime/`，再配置 `double_pinyin_flypy.custom.yaml`：

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

这些参数直接沿用[雾凇的官方配方](https://github.com/iDvel/rime-ice/blob/da1fbe602e38f26db846fa10120ee64c2b0324c0/others/recipes/grammar.recipe.yaml)。其中 `contextual_suggestions: false` 也是配方原来的值，不需要为了“启用模型”把它改成 `true`。这份补丁只挂到小鹤方案，备用全拼没有同时加模型。

10 月 26 日又更新了一次模型。原来用的是 10 月 19 日的文件，约 380 MiB；新版文件更新于 **10 月 26 日 09:12（北京时间）**，大小是 **418,078,764 字节，约 398.7 MiB**。这一版的 SHA-256 是：

```text
e34500ab44626dc039a0641792ecba98ab63307646eb3d29186be56608ffe094
```

这里要留意，LTS 发布地址上的文件名不变，内容却会继续更新。所以以后再下载，应该核对发布页当时的校验值，不能一直拿上面这串值比较。`releases/latest` 也不一定指向模型，有可能是词库或工具的发布，找模型时直接看 LTS。

更新过程没有重新安装整套雾凇。先把旧模型和补丁备份，再把新文件下载到临时目录，核对大小和校验值。测试通过后，将它复制到 Rime 目录里的临时文件，再替换正式的 `.gram`，最后执行一次 `--reload`。这样不会在下载过程中写坏正在使用的模型，也没有改动小鹤键位、词库和主题。

更新前后，用同样的四组输入做了检查：

| 小鹤编码 | 拼音提示 | 首选 |
| --- | --- | --- |
| `nihc` | `ni hao` | 你好 |
| `uurufa` | `shu ru fa` | 输入法 |
| `jbtmtmqihfhc` | `jin tian tian qi hen hao` | 今天天气很好 |
| `vuzdliwu` | `zhu zai li wu` | 住在里屋 |

新版和旧版在这四组测试上的结果一致。这里验证的是更新后还能正常输入、拼音提示也没有变化，不是拿四句话就判断新版准确率提高了多少。“住在礼物”变成“住在里屋”，是前面首次启用模型时的对照，不能算作这次升级的效果。

模型文件换好了，还要确认正在运行的鼠须管已经重新打开它。可以先检查 `build/double_pinyin_flypy.schema.yaml` 里是否有 `grammar` 和 `language: wanxiang-lts-zh-hans`，再看部署结果和运行日志。如果日志里有 `use grammar:` 或 `loading gram db:`，就能继续核对加载路径。

这次正式进程的检查还用到了 `lsof`：

```sh
lsof -a -c Squirrel "$HOME/Library/Rime/wanxiang-lts-zh-hans.gram"
stat -f 'size=%z inode=%i' "$HOME/Library/Rime/wanxiang-lts-zh-hans.gram"
```

`lsof` 可以看到鼠须管打开了哪个文件，`stat` 则查看磁盘上文件的大小和 inode。两边对应的是同一个新版模型，并且进程已经建立了映射，才能确认正在使用新文件。独立测试目录里的加载日志，只能说明测试环境加载成功，不能代替这一步。

最后，四个方案都部署成功，没有失败项，配置和词库的校验值也与更新前一致。更新期间还打开过一个临时 TXT 文稿，目的是试打和检查候选框，并不是安装模型需要打开文本文件。那次界面自动化因工具超时没有完成，最终采用的是上面的后台验证；临时文稿已经清空、保存并关闭。

## 候选框小一点，拼音和注释清楚一点

我觉得搜狗那种比较小的候选框更合适，之前配置的显示区域偏大。因此先找了现成的配色，换成 `ms_sogou`，再把字号缩小。

主题来自[这份配置](https://github.com/epoweripione/dotfiles/blob/f09f90ad77012c2e0645e86318571b15046fe375/conf/rime/squirrel.custom.yaml#L3)，作者标注为 Mark24Code。我保留了白底、蓝色候选和橙红色首选。原配色里的注释是白色，放在白底上看不清，就改成了深灰。

主要的排版设置是下面这些，放在 `squirrel.custom.yaml` 的 `patch:` 下：

```yaml
style/candidate_list_layout: linear
style/text_orientation: horizontal
style/inline_preedit: false
style/inline_candidate: false
style/font_face: PingFangSC-Regular
style/font_point: 14
style/label_font_point: 11
style/comment_font_point: 12
```

`linear` 把候选横着排，候选文字和顶部拼音从之前的 16 pt 缩到 14 pt，注释用 12 pt，序号用 11 pt。`inline_preedit: false` 把拼音放到候选框里，单独占一行；如果改成 `true`，拼音会回到文稿光标处。这个开关调整的是位置，显示什么拼音仍然由小鹤方案决定。

在鼠须管 1.1.2 里，顶部拼音和候选共用 `font_point`，没有独立的 `preedit_font_point`，所以不能只靠增加这个字段单独调顶部字号。序号和注释有各自的设置。

配色还有一个容易漏掉的细节：鼠须管使用 BGR / ABGR，而不是常见的 RGB。颜色要保留成带 `0x` 的字符串，例如 `'0xD67F42'`。如果用 YAML 工具读写配置，留意它是否把颜色变成了十进制数字，否则可能无法解析，退回默认配色。

目前明暗主题都指定为 `ms_sogou`，所以系统切到深色模式时，候选框也还是白底。完整配置放在文末，里面也保留了 Terminal、iTerm2、kitty 和 SecureCRT 默认英文的设置；VS Code 没有加这项设置。

## 下拉展开不是换个颜色就能做到的

换好主题以后，还有一个想要的效果：平时只有一条较小的候选栏，需要时点击向下箭头，展开成多行多列。

这就需要客户端支持了。皮肤能改字体、颜色和间距，但展开、折叠、滚动和候选导航，要由显示窗口的程序实现。`show_paging: true` 只是显示翻页箭头，不能让鼠须管多出一个下拉面板。横排候选太长时自然换行，也不是同一种交互。

截至这次查询，官方鼠须管 1.1.2 没有这个功能，[多行网格候选的请求](https://github.com/rime/squirrel/issues/1173)还没有关闭。已经实现的方案是 **Fcitx5 macOS + Rime + WebPanel 卷轴模式**。它的[文档](https://fcitx-contrib.github.io/docs/theme/css.html#翻页按钮结构)明确区分了普通翻页按钮和向下展开按钮，展开后可以多行显示、纵向滚动。

Fcitx5 中文叫“小企鹅”，它是能搭配多种输入引擎的框架，Rime 就是其中一种。所以换到 Fcitx5 + Rime，还是可以继续使用小鹤、雾凇和相关配置，只是负责系统接入和候选窗口的前端变了。

我也关心这个项目是不是有人在持续维护。这里需要分开看：Fcitx5 在 Linux 上已有成熟生态，[KDE Linux 也预装了它](https://linux.kde.org/docs/cjkv-input/)，但 macOS 移植项目到 2023 年底才创建，不能把 Linux 的规模直接算到 Mac 上。

2026 年 10 月 26 日查询时，[鼠须管](https://github.com/rime/squirrel)有 6,479 个 Stars，[Fcitx5 macOS](https://github.com/fcitx/fcitx5-macos)有 533 个。近 90 天，前者合并了 [8 个 PR](https://github.com/rime/squirrel/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-07-28..2026-10-26)，后者合并了 [42 个](https://github.com/fcitx/fcitx5-macos/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-07-28..2026-10-26)，两边在 10 月都有主分支提交。鼠须管的最新稳定版还是 1 月发布的 1.1.2，小企鹅则在 10 月 19 日发布了 0.4.1。只看稳定版日期，会漏掉鼠须管还在维护这件事；只看 Stars，也看不出小企鹅最近的开发节奏。

下载数更不好直接比较。鼠须管 [1.1.2 安装包](https://github.com/rime/squirrel/releases/tag/1.1.2)从 1 月以来累计约 93,732 次下载，小企鹅 [0.4.1 的两个普通运行包](https://github.com/fcitx/fcitx5-macos/releases/tag/0.4.1)发布约一周，合计 126 次。而小企鹅常用的 `latest` 滚动构建会替换资产，下载计数也会重置。这些是查询当天的公开数据，不能拿来计算实际用户数的差距。

如果以后试用，可以安装小企鹅的中州韵版，导入现有方案和模型，再打开卷轴模式。版式需要设成水平布局、从上到下书写；关闭自动展开后，可以先试 3 行、5 列和小字号，让候选框平时保持紧凑。[主题设置文档](https://fcitx-contrib.github.io/docs/theme/adjust.html#卷轴模式)里有这些选项。

迁移时有两处需要重新处理。第一，`squirrel.custom.yaml` 不能直接控制小企鹅的外观，需要在 WebPanel 里重配颜色和字号。第二，小企鹅使用 `~/.local/share/fcitx5/rime`，鼠须管使用 `~/Library/Rime`，两份数据要分开。官方明确不建议把它们软链接到同一个目录，因为用户词库使用的 LevelDB 不支持并发访问。[Rime 导入说明](https://fcitx-contrib.github.io/docs/im/rime.html)

这一部分目前只是调研，还没有安装或迁移。电脑上继续用的是鼠须管，暂时没有小企鹅的实际使用体验可以记录。

## 以后怎么更新和恢复

模型、词库和主题可以分别更新，没有必要每次都重装一遍。尤其是已经调好的小鹤键位和拼音提示，更新模型时不需要碰它们。

修改补丁前，可以先备份 `.custom.yaml`：

```sh
rime_backup="$HOME/Library/Rime-backups/manual-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$rime_backup"
cp "$HOME/Library/Rime/"*.custom.yaml "$rime_backup/"
```

这个命令只保存个人补丁。如果要改模型，还要备份 `.gram`；自定义短语、用户词库和同步数据也需要另外保存，不能以为备份几个 YAML 就包含了全部输入数据。

前面几次模型和主题操作的备份在 `~/Library/Rime-backups/`：

- `before-wanxiang-20261024-202313`：首次加万象之前的小鹤配置。
- `before-theme-20261024-203612`：加好万象、还没调整主题时的配置。
- `before-ms-sogou-20261024-205613`：切到 `ms_sogou` 之前的紧凑主题。
- `before-model-update-20261026-154715`：这次更新前的旧模型、补丁和更新记录。

例如，只想退回之前的主题，就恢复对应的 `squirrel.custom.yaml`：

```sh
cp "$HOME/Library/Rime-backups/before-ms-sogou-20261024-205613/squirrel.custom.yaml" \
   "$HOME/Library/Rime/squirrel.custom.yaml"
"/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel" --reload
```

这样不会改到词库和模型。只退回模型时，也只取出旧 `.gram`，先复制到 Rime 目录内的临时文件，再替换正式文件并重新部署，避免直接覆盖正在被进程映射的内容。模型更新备份中的 `manifest.json` 保存升级前状态，`update-result.json` 保存这次更新的校验值和验证结果。

如果只是想比较有无万象的效果，现在的 `double_pinyin_flypy.custom.yaml` 只包含模型补丁，可以临时改名为 `double_pinyin_flypy.custom.yaml.disabled` 后重新部署。恢复原文件名再部署，就重新启用了。改名前确认目标名称没有被占用；以后如果这个文件还加入了别的设置，就只移除 `grammar` 和本次添加的两个 `translator` 参数，不能再把整个文件停用。

更新雾凇则可以在备份后重新运行：

```sh
cd "$HOME/plum"
bash rime-install iDvel/rime-ice
```

这个配方会更新词库、方案、Lua 和基础配置，不只是词库文件。更新后先检查联系人词库的挂载项，再部署，试一下小鹤、完整拼音提示和模型是否正常。个人设置留在 `.custom.yaml` 里，就是为了减少这类更新相互覆盖的情况。

## 留一份完整的候选框配置

下面是目前使用的 `squirrel.custom.yaml` 相关内容。前面正文只挑了影响字号和排版的几项，这里把配色、间距和应用设置放在一起，方便以后恢复。已有其他个人设置时，把条目合并到同一个 `patch:` 下，不要直接覆盖掉原来的配置。

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
