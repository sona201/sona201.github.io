---
title: "Vim 与 VSCodeVim 操作笔记"
date: "2024-07-06T01:17:38+08:00"
lastmod: "2024-07-06T01:17:38+08:00"
categories: ["tools"]
slug: "vim-operation"
draft: false
---

#vim/vi #linux
vim operation

[简明vim攻略](https://coolshell.cn/articles/5426.html)
[vim光标移动](https://harttle.land/2015/11/07/vim-cursor.html)
[vim笔记](https://gist.github.com/taigetco/6fbb57f71e7e58d17b41)
[Vim 学习笔记 2: 组合命令](https://einverne.github.io/post/2015/05/vim-advanced-notes.html)
[打造vim ide](https://harttle.land/2016/08/08/vim-search-in-file.html)

vim 搜索忽略大小写

```
/foo\c

# 选区，在 Visual 模式下选择区域后输入 :，Vim 即可自动补全为 :'<,'>。
:'<,'>s/foo/bar/g
```

## 光标移动
```
--NROMAL--
w         跳到一个单词开头
b         跳到本单词或上一个单词开头
e         跳到本单词或下一个单词结尾
ge        跳到上一个单词结尾
0         跳到行首
^         跳到从行首开始第一个非空字符
$         跳到行尾
g_        到本行最后一个不是blank字符的位置
gg        跳到第一行
G         跳到最后一行
/pattern  搜索 pattern 的字符串(如果搜索出多个匹配,可按n键到下一个)
u         undo 撤销
Ctrl + r  redo

f{char}  光标跳到下个{char}所在位置
F{char}  反向移动到上一个{char}所在位置
t{char}  光标跳到下个{char}的前一个字符的位置
T{char}  光标反向移动到上个{char}的后一个字符的位置
这里的f/t查询均局限于当前行操作
;        重复上次的字符查找操作
,        反向查找上次查找的命令
```

## 操作符 operator
```
--NROMAL--
d(delete)  删除
dd         删除当前行
p          粘贴剪切板
c(change)  修改(删除并进入插入模式)
C          删除当前光标至结尾，并进入insert入模式
cc         删除当前行所有内容，并进入insert模式
y(yank)    复制
v(visual)  选中并进入 VISUAL 模式
x          删除光标后一个字符
X          删除光标前一个字符
Ctrl + v   进入 VISUAL BLOCK 模式, (列模式)
Ctrl + v + I + #  批量使用 # 在行首注释
```

## 动作 motion
```
i     inner
a     around
ciw   删除当前单词并进入编辑模式
cw    从当前位置删除到单词结尾并进入编辑模式
ca<   删除一对<> 匹配的内容和<>符号,并进入编辑模式
ci{   删除一对{} 内匹配的内容,不包括符号,并进入编辑模式
```

## 切换大小写
```
~     将光标下的字母改变大小写
3~    将光标位置开始的3个字母改变其大小写
g~~   改变当前行的字母的大小写
gUU   将当前行的字母改成大写
guu   将当前行的字母改成小写
gUaw(gUiw)  将光标下的单词改成大写
guaw(guiw)  将光标下的单词改成小写
```

## 滚屏操作 前缀(N)为按下的数字
```
--NROMAL--
(N)Ctrl-E    窗口向下滚动N行, 不加(N)默认向下滚动一行(光标没有移动)
(N)Ctrl-Y    窗口向上滚动N行, 不加(N)默认向上滚动一行(光标没有移动)
(N)Ctrl-D    窗口向下滚动N行, 不加(N)默认滚动窗口行数的一半(光标没有移动)
(N)Ctrl-U    窗口向上滚动N行, 不加(N)默认滚动窗口行数的一半(光标没有移动)
(N)Ctrl-F    窗口向下滚动N页, 不加(N)默认向下滚动一屏(光标被迫移动)
(N)Ctrl-B    窗口向上滚动N页, 不加(N)默认向下滚动一屏(光标被迫移动)

zt(小写)      重新绘制窗口,光标所在行移动到屏幕的顶端(相当于        z<enter>)
zz(小写)      重新绘制窗口,光标所在行移动到屏幕的中间(相当于        z.)
zb(小写)      重新绘制窗口,光标所在行移动到屏幕的底端(相当于        zb)
H
L
```

## 打开/保存/退出/改变文件(Buffer)
```
--NROMAL--
:e <path/to/file>         打开一个文件
:w                        存盘
:saveas <path/to/file>    另存为 <path/to/file>
:x,ZZ 或 :wq              保存并退出 (:x 表示仅在需要时保存, ZZ不需要输入冒号并回车)
:q!  退出不保存 :qa!       强行退出所有的正在编辑的文件,就算别的文件有更改
:bn 和 :bp                你可以同时打开很多文件，使用这两个命令来切换下一个或上一个文件(陈皓注:我喜欢使用:n到下一个文件)
```

## 文本编辑器的换行操作

Vim 通常会对长行自动回绕(换行),以便你可以看见所有的文字。但有时想让文字在一行中显示完。那么就要关闭自动回绕功能，你需要左右移动才能看到一整行。

```
--NROMAL--
set wrap
set nowrap
```

当nowrap生效时

```
--NROMAL--
(N)zh    屏幕向右滚动N个字符
(N)zl    屏幕向左滚动N个字符
(N)zH    屏幕向右滚动半个屏幕宽度的字符
(N)zL    屏幕向左滚动半个屏幕宽度的字符
```

[vim vscode plug](https://github.com/mg979/vim-visual-multi)

https://coolshell.cn/articles/1651.html

在VIM中输入:h!试试看会发现什么。

再输入:h 42呢？又会有什么发现？


![Vim 帮助页示例](/images/vim-42.png)

查看历史命令

```
用 q: 可以查看最近的历史命令的命令行窗口。用 up and down 选定，使用 Enter 就可以执行这个命令。
:<up> and <down>, 也可查看并用 Enter 使用这个命令。
:　CTRL-P　and CTRL-N , 查看历史命令.
:history  
:history /
```

vim 边界符号(英文字符下)，可以使用`b`, 'B'来获取边界
vim 下的 `%` 使用也是很神奇，会有偶尔用错的情况。
还有就是要看下vscode 下，vim 对应的 `keymap` 
刚刚在练习使用 `f{char}` 速行定位时，用到 `.` 好像会删除行，这个不知道是不是跟我刚刚的操作有关，`.` 应该是重复上次的操作，刚好我上次操作是 '删除'
vim 使用途中发现 `u` `U` 会出现很多问题，这个确实有点头疼。


vscode vim插件使用问题汇总
- vim 批量操作行位处理，批量到行尾增加字符串(每行长度不一致，vscode可以直接command 方向键右，好像vim下也可以这么操作)
ctrl + v 列块选择模式，切换到行尾 $，然后使用 A 在行位插入需要写入的字符串，然后两次 ESC，这样确实方便，以后在 vim 模式下也能操作，这个也是我比较喜欢的功能。
[行位批量操作3中方式](https://jelly.jd.com/article/6006b1045b6c6a01506c87ce)
- 批量正则替换，好像cammand + f也可以唤出替换，这样应该也是能满足我的需求
- 批量选择某个单词，command + d, 这个是 vscode 特有的, 需要写个插件配置

ide的相关快捷操作
1. 去定义的位置 gd go to define 
2. 快速格式化

vscode vim <C-f> 无法正常翻页，只能向右移动一个字符
按住 j ，不会一直向下移动一行，只能按一次向下移动一行，这是因为 输入法控制，避免连续按键问题。
经常在vim 突然发现都变成一行了。自己也莫名其妙
J → 把所有的行连接起来（变成一行）

vim 下全选复制粘贴的快捷键。
vim 快速增加引号 ysw"，原生 vim 是不支持该操作，需要安装 [插件](https://github.com/tpope/vim-surround)
常规操作下列几种，在 vscode vim 下这个是默认支持的。
https://blog.csdn.net/Xurui_Luo/article/details/106984427

https://github.com/ahrencode/Miscellaneous/blob/master/vim-cheatsheet.pdf

vim 光标乱跳的问题，不确定当前状态是啥，是不是已经触发按键 v/i/a 之类的 -> 这个需要看 vim 操作大全

找了一篇关于 vscode vim 的使用文章 [我如何用 VSCodeVim 提升開發效率](https://blog.kalan.dev/posts/2022-01-13-vscode-vim-tips)

vim 下的 d/y 命令会把当前剪切板内容覆盖，这个比较头疼。 可能需要直接v-<action> 模式，然后粘贴。

vim  mark标记位置, 快速复制一段数据, 粘贴到当前光标下一行
vim 寄存器  剪切板
http://yyq123.blogspot.com/2011/06/vim-mark.html

vim 的复制粘贴p, 只能粘贴一次, 再次使用数据粘贴板变了; vim 寄存器问题, 关键字 vim registers

https://blog.csdn.net/weixin_43274002/article/details/120165079


vim u 命令, 回退会到哪一步, 操作错一步, 回退步步错

vim 大小写问题

shift + h 会跳到上一个空格的位置


大写的 hjkl 是什么意思，会突然变的换行

https://hackmd.io/@lunzaizai/BJX4hlPKY

https://www.cnblogs.com/yinheyi/p/6944144.html

HL 命令解释

vim yank 后 想粘贴到下一行
