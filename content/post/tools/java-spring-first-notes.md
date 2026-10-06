---
title: "Java 与 Spring Boot 入门学习记录"
date: "2023-08-10T00:14:00+08:00"
lastmod: "2023-08-10T00:14:00+08:00"
categories: ["tools"]
slug: "java-spring-first-notes"
draft: false
---

网上找了一个教程 https://www.jianshu.com/p/56e600280ad1 快速入门 spring, spring 从入门到安装各个组件 

一直听说 java 的思想很牛, 跟 python 形成鲜明的对比.

想快速学习, 但感觉落下很多基础知识, 亡羊补牢却不知道从何学起. 只能强迫自己静下心来慢慢看(心里还是有点做不到)

### 缘起
无奈之下想起之前看的廖雪峰, 文字版可以快速跳过一些不重要的知识(还是浮躁) \
廖雪峰的教程会感觉有点详细, 更适合做一个词典用来查阅怎么用, 目前的方法论是快速学习, 也算是培养成就感.

### java 基础知识

`hello world!` 入门教学里的知识点

- java 每个文件只能有一个 pulic class 类, 对应的类名要与文件名一致
- java 有入口函数 main
- java 必须都被类包着

java 的方法函数, 这个[廖雪峰](https://www.liaoxuefeng.com/wiki/1252599548343744/1260454185794944)几乎没讲, 看到 [w3schools](https://www.w3schools.com/java/java_methods.asp) 讲了一点点

```java
public class Main {
    static int plusMethodInt(int x, int y) {
        return x + y;
    }

    static double plusMethodDouble(double x, double y) {
        return x + y;
    }

    public static void main(String[] args) {
        int myNum1 = plusMethodInt(8, 5);
        double myNum2 = plusMethodDouble(4.3, 6.26);
        System.out.println("int: " + myNum1);
        System.out.println("double: " + myNum2);
    }
}
```

### 学习疑惑:
1. 所有的 java 必须有个 main 函数，只能写这么写 public static void main
2. 不能写成 public static main，然后 return 一个函数么？

网上搜到很多文章, 摘要两篇感觉通俗易懂的:
1. [Java之主函数——main函数](https://blog.csdn.net/qiaoquan3/article/details/53325915)
2. [探秘Java：从main函数启动开始](https://juejin.cn/post/6976678093024919560)

#### 答疑

main函数特殊之处：
1. 格式是固定的。
2. 被jvm所识别和调用。

main函数关键字分析 `public static void main(String[] args)`
- public: 是权限修饰词，表明任何类或对象都可以访问这个方法
- static: 表明main() 是一个静态方法，即方法中的代码是存储在静态存储区的，只要类被加载就可以使用该方法而不需要通过实例化对象来访问，可以直接通过 类名.main() 来自直接访问
- void: 主函数没有具体的返回值。
- main: 函数名，不是关键字，只是一个jvm识别的固定的名字。
- String[] arg: 这是主函数的参数列表，是一个数组类型的参数，而且元素都是字符串类型的。

在web 应用中，一个程序只能有一个入口(main 函数)，要是写多个 main 入口也可以，但启动只能指定一个。\

> `java -classpath /home/ds/import/dc x-1.5.2.jar`

JAVA虚拟机不管有几个main方法， 一个JVM只可以运行一个main方法。它只管运行的哪一个main方法，如果想同时运行多个main方法就得用多个JVM

#### spring 启动

https://start.spring.io/

配置项

- project: maven
- language: java
- spring-boot version: 2.7.14
- package: java
- java version: 8
- dependencies: spring web
- dependencies: lombok

![spring_initializr_demo](/images/spring_initializr_demo.png)