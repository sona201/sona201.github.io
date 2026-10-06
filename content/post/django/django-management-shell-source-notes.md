---
title: "Django 4.0 命令管理与 shell 启动流程"
date: "2023-02-01T00:29:29+08:00"
lastmod: "2023-02-01T00:29:29+08:00"
categories: ["django"]
slug: "django-management-shell-source-notes"
draft: false
---

python manage.py help shell

```python
from django.core.management import ManagementUtility
ManagementUtility().main_help_text()
"\nType 'pydevconsole.py help <subcommand>' for help on a specific subcommand.\n\nAvailable subcommands:\n\n[auth]\n    changepassword\n    createsuperuser\n\n[channels]\n    runworker\n\n[contenttypes]\n    remove_stale_contenttypes\n\n[django]\n    check\n    compilemessages\n    createcachetable\n    dbshell\n    diffsettings\n    dumpdata\n    flush\n    inspectdb\n    loaddata\n    makemessages\n    makemigrations\n    migrate\n    sendtestemail\n    shell\n    showmigrations\n    sqlflush\n    sqlmigrate\n    sqlsequencereset\n    squashmigrations\n    startapp\n    startproject\n    test\n    testserver\n\n[sessions]\n    clearsessions\n\n[staticfiles]\n    collectstatic\n    findstatic\n    runserver"
print(ManagementUtility().main_help_text())
```

判断继承类有没有该方法
```text
    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        raise NotImplementedError(
            "subclasses of BaseCommand must provide a handle() method"
        )
```

执行find方法

每个命令都是对应一个py文件，文件都有Command类，本质是执行excuse方法，最终调用handle方法

1.6 Django中startproject命令追踪


for root, dirs, files in os.walk(template_dir)
    for dirname in dirs[:]:
        if "exclude" not in options:
            if dirname.startswith(".") or dirname == "__pycache__":
                dirs.remove(dirname)
        elif dirname in excluded_directories:
            dirs.remove(dirname)
def walkFile(file):
    for root, dirs, files in os.walk(file):

        # root 表示当前正在访问的文件夹路径
        # dirs 表示该文件夹下的子目录名list
        # files 表示该文件夹下的文件list

        # 遍历文件
        for f in files:
            print(os.path.join(root, f))

        # 遍历所有的文件夹
        for d in dirs:
            print(os.path.join(root, d))

for root, dirs, files in os.walk("/Users/example/File/Project/firstDjango/web", topdown=False):
    for name in files:
        print(os.path.join(root, name))
    for name in dirs:
        print(os.path.join(root, name))


shutil.copymode(old_path, new_path)

                if new_path.endswith(extensions) or filename in extra_files:
                    with open(old_path, encoding="utf-8") as template_file:
                        content = template_file.read()
                    template = Engine().from_string(content)
                    content = template.render(context)
                    with open(new_path, "w", encoding="utf-8") as new_file:
                        new_file.write(content)
                else:
                    shutil.copyfile(old_path, new_path)

#### django 自定义模板引擎 Engine()
```python
>>> content_tp = "hello, {{ name }}"
>>> from django.template import Context, Engine
>>> template = Engine().from_string(content_tp)
>>> context = Context({'name': 'clin'})
>>> template.render(context)
'hello, clin'
```

1.7 

`python3 manage.py shell`进入交互模式会做什么

可以增加参数-c参数指定使用哪个交互python \
可选项有三个，需要提前安装 \
shells = ['ipython', 'bpython', 'python'] \
若没有指定，则默认按照顺序导入，报错则执行下一个 \
```python
        for shell in available_shells:
            try:
                return getattr(self, shell)(options)
            except ImportError:
                pass
        raise CommandError("Couldn't import {} interface.".format(shell))
```

`getattr(self, shell)(options)` 这也算是一个常用方法，getattr判断是否有该属性，然后加括号执行


python进入交互模式
```
import traceback
import os
import sys
from django.utils.datastructures import OrderedSet


def python():
    import code

    # Set up a dictionary to serve as the environment for the shell.
    imported_objects = {}

    # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
    # conventions and get $PYTHONSTARTUP first then .pythonrc.py.
    """
    机器翻译:
    # 我们要尊重 $PYTHONSTARTUP 和 .pythonrc.py，所以遵循系统
    # 约定并首先获取 $PYTHONSTARTUP，然后获取 .pythonrc.py。
    对代码逻辑没有影响，可以去掉
    """
    for pythonrc in OrderedSet(
            [os.environ.get("PYTHONSTARTUP"), os.path.expanduser("~/.pythonrc.py")]
    ):
        if not pythonrc:
            continue
        if not os.path.isfile(pythonrc):
            continue
        with open(pythonrc) as handle:
            pythonrc_code = handle.read()
        # Match the behavior of the cpython shell where an error in
        # PYTHONSTARTUP prints an exception and continues.
        """
        机器翻译:
        # 匹配出现错误的 cpython shell 的行为
        # PYTHONSTARTUP 打印异常并继续。
        对代码逻辑没有影响，可以去掉
        """
        try:
            exec(compile(pythonrc_code, pythonrc, "exec"), imported_objects)
        except Exception:
            traceback.print_exc()

    # By default, this will set up readline to do tab completion and to read and
    # write history to the .python_history file, but this can be overridden by
    # $PYTHONSTARTUP or ~/.pythonrc.py.
    try:
        hook = sys.__interactivehook__
    except AttributeError:
        # Match the behavior of the cpython shell where a missing
        # sys.__interactivehook__ is ignored.
        pass
    else:
        try:
            hook()
        except Exception:
            # Match the behavior of the cpython shell where an error in
            # sys.__interactivehook__ prints a warning and the exception
            # and continues.
            print("Failed calling sys.__interactivehook__")
            traceback.print_exc()

    # Set up tab completion for objects imported by $PYTHONSTARTUP or
    # ~/.pythonrc.py.
    try:
        import readline
        import rlcompleter

        readline.set_completer(rlcompleter.Completer(imported_objects).complete)
    except ImportError:
        pass

    # Start the interactive interpreter.
    code.interact(local=imported_objects)


python()
```