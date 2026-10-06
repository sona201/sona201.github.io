---
title: "JavaScript 模块化学习笔记"
date: "2022-11-17T00:11:17+08:00"
lastmod: "2026-10-06T18:07:31+08:00"
categories: ["tools"]
slug: "javascript-module-notes"
draft: false
---

常用的 JavaScript 模块化规范有 CommonJS、AMD、CMD 和 ES Modules。

## 闭包与模块化

### 闭包函数

```javascript
(function() {
  var flag = true;
})();
```

### 使用闭包组织模块

使用模块化作为出口，将需要对外提供的变量和方法放入对象，再返回这个对象。

```javascript
var ModuleA = (function() {
  // 1. 定义一个对象
  var obj = {};

  // 2. 在对象内部添加变量和方法
  obj.flag = true;
  obj.myFunc = function(info) {
    console.log(info);
  };

  // 3. 将对象返回
  return obj;
})();
```

## CommonJS

### 导出模块

```javascript
module.exports = {
  flag: true,
  test(a, b) {
    return a + b;
  },
  demo(a, b) {
    return a * b;
  }
};
```

### 导入模块

使用 `require()` 导入模块，并通过解构获取变量和方法：

```javascript
let { test, demo, flag } = require('moduleA');
```

也可以先获取整个模块对象，再分别读取属性：

```javascript
let _mA = require('moduleA');
let test = _mA.test;
let demo = _mA.demo;
let flag = _mA.flag;
```

## ES Modules：export / import

### 直接导出函数或类

```javascript
export function test(content) {
  console.log(content);
}

export class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }

  run() {
    console.log(this.name + '在奔跑');
  }
}
```

### 先定义，再统一导出

```javascript
function test(content) {
  console.log(content);
}

class Person {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }

  run() {
    console.log(this.name + '在奔跑');
  }
}

export { test, Person };
```

### 默认导出：export default

某些情况下，一个模块包含的功能不需要指定导出名称，而是由导入者自行命名。这时可以使用 `export default`。

在 `info.js` 中默认导出一个函数：

```javascript
// info.js
export default function () {
  console.log('default function');
}
```

在 `main.js` 中导入并调用。这里的 `myFunc` 是导入时自行指定的名称：

```javascript
// main.js
import myFunc from './info.js';
myFunc();
```

**注意：同一个模块只能有一个 `export default`。**
