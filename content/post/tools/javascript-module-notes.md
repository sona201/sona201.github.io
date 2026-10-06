---
title: "JavaScript 模块化学习笔记"
date: "2022-11-17T00:11:17+08:00"
lastmod: "2022-11-17T00:11:17+08:00"
categories: ["tools"]
slug: "javascript-module-notes"
draft: false
---




--------------

使用模块化作为出口

闭包函数

(function() {
  var flag = true
})()


模块化

var ModuleA = (function() {
  // 1. 定义一个对象
  var obj = {}
  // 2. 在对象内部添加变量和方法
  obj.flag = true
  obj.myFunc = function(info) {
    console.log(info);
  }
  // 3. 将对象返回
  return obj
})()


常用的模块化规范:
  CommonJS / AMD / CMD / ES6的Modules


CommonJS 导出
module.exports = {
  flag: true,
  test(a, b) {
    return a + b
  }
  demo(a, b) {
    return a * b
  }
}

CommonJS 导入
// CommonJS 模块
let { test, demo, flag } = require('moduleA')

// 等同于
let _mA = require('moduleA');
let test = _mA.test;
let demo = _mA.demo;
let flag = _mA.flag;


ES6 export/import

导出函数或类

export function test(content) {
  console.log(content);
}

export class Persion {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }

  run() {
    console.log(this.name + '在奔跑')
  }
}


另外方式

>functions test(content) {
>console.log(content);
>}

class Persion {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }

  run(){
    console.log(this.name = '在奔跑')
  }
}

export {test, Persion}
<<<<


// 自己命名 export default

>某些情况下，一个模块中包含某个功能，我们并不希望给这个功能命名，而且让导入者自己来命名
>这个时候可以使用export default

//info.js
export default function () {
  console.log('default function')
}

我们来到main.js中，这样用就可以了
这里的myFunc是我自己命名的，你可以根据需要命名它对应的名字
import myFunc from './info.js'
myFunc()

另外，需要注意：export default 在同一模块中，不允许同时存在对个.
<<<<