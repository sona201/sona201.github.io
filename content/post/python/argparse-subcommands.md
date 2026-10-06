---
title: "Argparse 子命令示例"
date: "2024-09-08T15:39:49+08:00"
lastmod: "2024-09-08T15:39:49+08:00"
categories: ["python"]
slug: "argparse-subcommands"
draft: false
---

#python #argparse #文件 #传参

```python
import argparse

# 创建ArgumentParser对象
parser = argparse.ArgumentParser(description='这是一个带有子命令的参数解析示例')

# 创建子命令解析器
subparsers = parser.add_subparsers(title='子命令', dest='command')

# 创建子命令1解析器
parser_command1 = subparsers.add_parser('command1', help='执行命令1')
parser_command1.add_argument('-f', '--file', type=str, help='文件名')

# 创建子命令2解析器
parser_command2 = subparsers.add_parser('command2', help='执行命令2')
parser_command2.add_argument('-d', '--directory', type=str, help='目录名')

# 解析命令行参数
args = parser.parse_args()

# 根据子命令执行相应的操作
if args.command == 'command1':
    if args.file:
        print(f'执行命令1，文件名: {args.file}')
    else:
        print('请指定文件名')
elif args.command == 'command2':
    if args.directory:
        print(f'执行命令2，目录名: {args.directory}')
    else:
        print('请指定目录名')
else:
    print('请指定子命令')
```

  
```shell
python script.py command1 -f file.txt
```
输出结果
```
执行命令1，文件名: file.txt
```


```shell
python script.py command2 -d directory
```
输出结果
```
执行命令2，目录名: directory
```

