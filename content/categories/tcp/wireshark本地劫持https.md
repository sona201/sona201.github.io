---
title: "Wireshark本地劫持https"
image: 
style:
    background: "#2a9d8f"
    color: "#fff"
---

[相关文章](https://www.jianshu.com/p/b3cc1299e03e)

方案: 手动启动浏览器，让浏览器把证书放到指定目录，wireshark去读取，然后解析，就可以得到解密后的包了，等同于http请求抓包

### 一、启动浏览器
> 在终端执行命令，打开新的 Chrome 浏览器
```
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --user-data-dir=/tmp/chrome --ssl-key-log-file=/tmp/.ssl-key.log
```

### 二、配置wireshark
```
打开 Wireshark ，Wireshark - Perferences - Protocols - TLS ，在 (Pre)-Master-Secret log filename 输入 /tmp/.ssl-key.log
```
![wireshrk_config](/image/wireshrk_config.png)

### 三、抓包
> 打开浏览器，发出请求，开始抓包
![start_chrome](/image/start_chrome.png)

### 四、异常情况
> 异常情况暂未遇到过，这个先记录一下

> 出现 Opening in existing browser session. \
> 解决方式：关闭掉用命令启动的 Chrome，然后重新运行 Chrome 启动命令

```
$ ps -ef | grep /tmp/.ssl | awk 'NR==1{print $2}' | xargs  kill -9
$ /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --user-data-dir=/tmp/chrome --ssl-key-log-file=/tmp/.ssl-key.log
```

### 参考文章
[使用wireshark分析https](https://blog.gfkui.com/2018/03/30/%E4%BD%BF%E7%94%A8wireshark%E5%88%86%E6%9E%90https/index.html)