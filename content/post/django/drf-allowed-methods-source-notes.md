---
title: "Django 与 DRF allowed_methods 源码笔记"
date: "2023-10-25T00:42:03+08:00"
lastmod: "2023-10-25T00:42:03+08:00"
categories: ["django"]
slug: "drf-allowed-methods-source-notes"
draft: false
---

## allowed_methods

```python
class APIView(View):
  ...
    @property
    def allowed_methods(self):
        """
        Wrap Django's private `_allowed_methods` interface in a public property.
        """
        return self._allowed_methods()
```


```python
    def _allowed_methods(self):
        return [m.upper() for m in self.http_method_names if hasattr(self, m)]
```

```python
class View:
    """
    Intentionally simple parent class for all views. Only implements
    dispatch-by-method and simple sanity checking.
    """

    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
    ]
```
