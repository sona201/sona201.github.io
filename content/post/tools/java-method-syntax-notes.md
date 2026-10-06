---
title: "从 Python 看 Java 方法语法"
date: "2023-08-17T00:04:13+08:00"
lastmod: "2023-08-17T00:04:13+08:00"
categories: ["tools"]
slug: "java-method-syntax-notes"
draft: false
---

## java 自问自答

### java 函数语法吐槽
java 的 "方法" 真的好想吐槽。与 python go c 等不一样，它没有类似 func def 等关键字来区别。 \

```java
public class ApiController {

    @Autowired
    private ApiServices apiServices;

    @RequestMapping(value = "/api01", method = RequestMethod.GET)
    public String api01() {
        return apiServices.api01();
    }

    @RequestMapping(value = "/api02", method = RequestMethod.GET)
    public String api02() {
        return apiServices.api01();
    }

    @RequestMapping(value = "/apiparam", method = RequestMethod.GET)
    public String api() {
        return apiServices.api_param("api param");
    }

}
```
只能通过 括号、花括号 识别，虽然在 python 里也是这个逻辑，但少了关键字多少有点怪怪的


### java 的引入
spring 怎么知道 control 里的类，是有引用还是会自动搜索