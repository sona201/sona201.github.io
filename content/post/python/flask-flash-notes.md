---
title: "Flask flash 消息使用笔记"
date: "2021-01-10T00:51:58+08:00"
lastmod: "2021-01-10T00:51:58+08:00"
categories: ["python"]
slug: "flask-flash-notes"
draft: false
---

![闪现](/images/%E9%97%AA%E7%8E%B0.png)



#### 闪现

```python
from flask import Flask, session, flash, get_flashed_messages

app = Flask(__name__)
import os
app.secret_key = os.environ['FLASK_SECRET_KEY']
app.config.from_object('settings.dev')


@app.route('/x1', methods=['GET', 'POST'])
def login():
    flash('hello world1', category='x1')
    flash('hello world2', category='x2')
    return 'login!'


@app.route('/x2', methods=['GET', 'POST'])
def index():
    # data1 = get_flashed_messages()
    # print('=========', data1)
    data = get_flashed_messages(category_filter=['x1'])
    print(data)
    return 'index!'


if __name__ == '__main__':
    app.run()
```

