---
title: "Apple Silicon cffi 架构错误排查记录"
date: "2023-11-09T00:40:38+08:00"
lastmod: "2023-11-09T00:40:38+08:00"
categories: ["python"]
slug: "cffi-apple-silicon-error-notes"
draft: false
---

## 问题django启动异常

提示跟包 cffi 有关，甚至还和 arm 芯片有关
```
这里是相关的关键字
mach-o file, but is an incompatible architecture (have 'x86_64', need 'arm64')

from cryptography.hazmat.bindings._rust import exceptions as rust_exceptions pyo3_runtime.PanicException: Python API call failed

pyo3-0.18.3/src/err/mod.rs:790:5

No module named _cffi_backend
```



后续安装
```
pip uninstall cffi
pip install cffi==1.5.2
```