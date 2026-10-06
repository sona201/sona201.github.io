---
title: "macOS 更换 Kitty 图标"
date: "2025-05-29T00:18:11+08:00"
lastmod: "2025-05-29T00:18:11+08:00"
categories: ["tools"]
slug: "kitty-icon"
draft: false
---

## 更换icon

https://sw.kovidgoyal.net/kitty/faq/#i-do-not-like-the-kitty-icon

在家目录下
```
clin:kitty/ $ ll                                                                                                   [0:14:09]
total 192
-rw-r--r--@ 1 clin  staff    11K Apr  7  2024 kitty.app.png
-rw-------@ 1 clin  staff    83K Feb 20  2024 kitty.conf
```

将文件放到配置目录下，重启更新 icon

```bash
rm /var/folders/*/*/*/com.apple.dock.iconcache; killall Dock
```

在notedoc 的笔记里也有对应的配置文档