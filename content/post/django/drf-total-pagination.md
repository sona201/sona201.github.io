---
title: "DRF 返回全部数据并保留 count 字段"
date: "2025-08-19T17:54:03+08:00"
lastmod: "2025-08-19T17:54:03+08:00"
categories: ["django"]
slug: "drf-total-pagination"
draft: false
---

django restful 风格返回所有数据
并且有相应的字段

```python
from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from collections import OrderedDict


class TotalPagination(BasePagination):  
    """  
    不分页，显示总数  
    """  
    def paginate_queryset(self, queryset, request, view=None):  
        """  
        返回所有  
        """
        return list(queryset[:])  
  
    def get_paginated_response(self, data):  
        return Response(OrderedDict([  
            ('count', len(data)),  
            ('results', data)  
        ]))
```

pagination 的 page_size_query_param 参数是怎么获取的？
drf 的 get_paginated_responseresponse 格式是怎么来的？