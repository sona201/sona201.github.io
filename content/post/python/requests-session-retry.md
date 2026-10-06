---
title: "Requests Session 重试配置笔记"
date: "2024-01-08T00:14:04+08:00"
lastmod: "2024-01-08T00:14:04+08:00"
categories: ["python"]
slug: "requests-session-retry"
draft: false
---

[https://gist.github.com/laixintao/e9eae48a835e741969ae06af3ad45f71](https://gist.github.com/laixintao/e9eae48a835e741969ae06af3ad45f71)


```python
from requests.adapters import HTTPAdapter, Retry
from requests import Session

retries = Retry(
  total=5, backoff_factor=1, status_forcelist=[502, 503, 504]
)
session = Session()  # reuse tcp connection
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))

session.get("https://example.com", timeout=5)  # seconds
```