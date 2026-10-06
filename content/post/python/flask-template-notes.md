---
title: "Flask 模板与自定义函数笔记"
date: "2021-01-10T00:51:58+08:00"
lastmod: "2021-01-10T00:51:58+08:00"
categories: ["python"]
slug: "flask-template-notes"
draft: false
---

## 模板搜索引擎

![image-20201129132854360](/images/image-20201129132854360.png)



![muban](/images/muban.png)



#### 自定义函数

![自定义函数](/images/%E8%87%AA%E5%AE%9A%E4%B9%89%E5%87%BD%E6%95%B0.png)



![input框函数](/images/input%E6%A1%86%E5%87%BD%E6%95%B0.png)



自定义函数模板

![自定义函数模板](/images/%E8%87%AA%E5%AE%9A%E4%B9%89%E5%87%BD%E6%95%B0%E6%A8%A1%E6%9D%BF.png)



```python
from flask import Markup

return Markup("<input value='%s' />" % value)
```



在每一个模板里都使用自定义函数

使用特殊的装饰器(全局)

```python
@app.template_golbal()

def sbbbbbb(a1, a2):
  "
  每个模板中可以调用的函数
  :param a1:
  :param a2:
  :return
  "
  return a1 + a2

# <h1>{{k5(99)|safe}}</h1> 这里的safe也是一个函数
```



![自定义函数模板](/images/%E8%87%AA%E5%AE%9A%E4%B9%89%E5%87%BD%E6%95%B0%E6%A8%A1%E6%9D%BF.png)



模板继承(与django相同)

![模板继承1](/images/%E6%A8%A1%E6%9D%BF%E7%BB%A7%E6%89%BF1.png)



![模板继承2](/images/%E6%A8%A1%E6%9D%BF%E7%BB%A7%E6%89%BF2.png)