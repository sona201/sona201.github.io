---
title: "Nginx location 匹配"
description: "nginx的location匹配逻辑"
date: "2024-11-20T00:19:55+08:00"
lastmod: "2024-11-20T00:19:55+08:00"
categories: ["nginx"]
slug: "nginx-location"
draft: false
tags: ["nginx", "location"]
---

[原文作者：挖坑的张师傅](https://juejin.cn/post/6844903849166110733)

# 彻底弄懂 Nginx location 匹配

Nginx 的 location 实现了对请求的细分处理，有些 URI 返回静态内容，有些分发到后端服务器等，今天来彻底弄懂它的匹配规则

一个最简单的 location 的例子如下


```
server {
    server_name website.com;
    location /admin/ {
    # The configuration you place here only applies to
    # http://website.com/admin/
    }
}
```

location 支持的语法 `location [=|~|~*|^~|@] pattern { ... }`，乍一看还挺复杂的，来逐个看一下。

# location修饰符类型

## 「=」 修饰符：要求路径完全匹配

```
server {
    server_name website.com;
    location = /abcd {
    […]
    }
}
```

- `http://website.com/abcd`**匹配**
- `http://website.com/ABCD`**可能会匹配** ，也可以不匹配，取决于操作系统的文件系统是否大小写敏感（case-sensitive）。ps: Mac 默认是大小写不敏感的，git 使用会有大坑。
- `http://website.com/abcd?param1&param2`**匹配**，忽略 querystring
- `http://website.com/abcd/`**不匹配**，带有结尾的`/`
- `http://website.com/abcde`**不匹配**

## 「~」修饰符：区分大小写的正则匹配

```
server {
    server_name website.com;
    location ~ ^/abcd$ {
    […]
    }
}
```

`^/abcd$`这个正则表达式表示字符串必须以`/`开始，以`$`结束，中间必须是`abcd`

- `http://website.com/abcd`**匹配**（完全匹配）
- `http://website.com/ABCD`**不匹配**，大小写敏感
- `http://website.com/abcd?param1&param2`**匹配**
- `http://website.com/abcd/`**不匹配**，不能匹配正则表达式
- `http://website.com/abcde`**不匹配**，不能匹配正则表达式

## 「~*」不区分大小写的正则匹配

```
server {
    server_name website.com;
    location ~* ^/abcd$ {
    […]
    }
}
```

- `http://website.com/abcd`**匹配** (完全匹配)
- `http://website.com/ABCD`**匹配** (大小写不敏感)
- `http://website.com/abcd?param1&param2`**匹配**
- `http://website.com/abcd/` `不匹配`，不能匹配正则表达式
- `http://website.com/abcde` `不匹配`，不能匹配正则表达式

##「^~」修饰符：前缀匹配 如果该 location 是最佳的匹配，那么对于匹配这个 location 的字符串， 该修饰符不再进行正则表达式检测。注意，这不是一个正则表达式匹配，它的目的是优先于正则表达式的匹配

# 查找的顺序及优先级

当有多条 location 规则时，nginx 有一套比较复杂的规则，优先级如下：

- 精确匹配 `=`
- 前缀匹配 `^~`（立刻停止后续的正则搜索）
- 按文件中顺序的正则匹配 `~`或`~*`
- 匹配不带任何修饰的前缀匹配。

这个规则大体的思路是

> 先精确匹配，没有则查找带有 `^~`的前缀匹配，没有则进行正则匹配，最后才返回前缀匹配的结果（如果有的话）

> 如果上述规则不好理解，可以看下面的伪代码（非常重要）

```
function match(uri):
  rv = NULL
  
  if uri in exact_match:
    return exact_match[uri]
  
  if uri in prefix_match:
    if prefix_match[uri] is '^~':
      return prefix_match[uri]
    else:
      rv = prefix_match[uri] // 注意这里没有 return，且这里是最长匹配
   
  if uri in regex_match:
    return regex_match[uri] // 按文件中顺序，找到即返回
  return rv
```

一个简化过的`Node.js`写的代码如下

```
function ngx_http_core_find_location(uri, static_locations, regex_locations, named_locations, track) {
  let rc = null;
  let l = ngx_http_find_static_location(uri, static_locations, track);
  if (l) {
    if (l.exact_match) {
      return l;
    }
    if (l.noregex) {
      return l;
    }
    rc = l;
  }
  if (regex_locations) {
    for (let i = 0 ; i < regex_locations.length; i ++) {
      if (track) track(regex_locations[i].id);
      let n = null;
      if (regex_locations[i].rcaseless) {
        n = uri.match(new RegExp(regex_locations[i].name));
      } else {
        n = uri.match(new RegExp(regex_locations[i].name), "i");
      }
      if (n) {
        return regex_locations[i];
      }
    }
  }

  return rc;
}
```

# 案例分析

## 案例 1

```
server {
    server_name website.com;
    location /doc {
        return 701; # 用这样的方式，可以方便的知道请求到了哪里
    }
    location ~* ^/document$ {
        return 702; # 用这样的方式，可以方便的知道请求到了哪里

    }
}

curl -I  website.com:8080/document
HTTP/1.1 702
```

按照上述的规则，第二个会有更高的优先级

## 案例2

```
server {
    server_name website.com;
    location /document {
        return 701;
    }
    location ~* ^/document$ {
        return 702;
    }
}
curl -I  website.com:8080/document

```

第二个匹配了正则表达式，优先级高于第一个普通前缀匹配

## 案例 3

```
server {
    server_name website.com;
    location ^~ /doc {
        return 701;
    }
    location ~* ^/document$ {
        return 702;
    }
}
curl http://website.com/document
HTTP/1.1 701
```

第一个前缀匹配`^~`命中以后不会再搜寻正则匹配，所以会第一个命中

## 案例 4

```
server {
    server_name website.com;
    location /docu {
        return 701;
    }
    location /doc {
        return 702;
    }
}
```

`curl -I website.com:8080/document` 返回 `HTTP/1.1 701`，

```
server {
    server_name website.com;
    location /doc {
        return 702;
    }
    location /docu {
        return 701;
    }
}
```

`curl -I website.com:8080/document` 依然返回 `HTTP/1.1 701`

**前缀匹配下，返回最长匹配的 location，与 location 所在位置顺序无关**

## 案例 5

```
server {
	listen 8080;
	server_name website.com;

    location ~ ^/doc[a-z]+ {
        return 701;
    }

    location ~ ^/docu[a-z]+ {
        return 702;
    }
}
```

`curl -I website.com:8080/document` 返回 `HTTP/1.1 701`

把顺序换一下

```
server {
	listen 8080;
	server_name website.com;

    location ~ ^/docu[a-z]+ {
        return 702;
    }
    
    location ~ ^/doc[a-z]+ {
        return 701;
    }
}
```

`curl -I website.com:8080/document` 返回 `HTTP/1.1 702`

**正则匹配是使用文件中的顺序，找到返回**

