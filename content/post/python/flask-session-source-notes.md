---
title: "Flask session 使用与源码笔记"
date: "2021-01-10T00:51:58+08:00"
lastmod: "2021-01-10T00:51:58+08:00"
categories: ["python"]
slug: "flask-session-source-notes"
draft: false
---

设置session

```python
from flask import Flask, session

app = Flask(__name__)
import os
app.secret_key = os.environ['FLASK_SECRET_KEY']
@app.route('/x1')
def index():
  session['k1'] = 123
  return "index"

@app.route('/x2')
def order():
	print(session['k1'])
  return "order"

```



```python
obj['xxxx'] = 123  # __setitem__方法
```



流程分析

![image-20201206231459996](/images/session%E6%B5%81%E7%A8%8B.png)





源码解读

![session源码1](/images/session%E6%BA%90%E7%A0%811.png)



源码解读二，分析类

![session源码2类封装](/images/session%E6%BA%90%E7%A0%812%E7%B1%BB%E5%B0%81%E8%A3%85.png)