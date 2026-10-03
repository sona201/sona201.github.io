---
title: "mysqlclient 安装记录"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["mysql"]
tags: ["mysql", "python", "mysqlclient"]
draft: false
---

#mysql #python #install #mysqlclient
# mysqlclient 安装

## 一、官方安装操作

[pypi 安装](https://pypi.org/project/mysqlclient/2.2.0rc1/)

```
# Assume you are activating Python 3 venv
$ brew install mysql-client pkg-config
$ export PKG_CONFIG_PATH="/opt/homebrew/opt/mysql-client/lib/pkgconfig"
$ pip install mysqlclient
```

## 二、安装问题解决

### 1. xcode 问题

**解决操作命令**
```
xcode-select --install
```

> xcrun error xcode error

报错内容

![msyqlclient_xcode_error](/images/mysqlclient-xcode-error.png)

```
(venv) clin:devops-api/ (master) $ pip install mysqlclient                                                                                                               [10:54:12]
Looking in indexes: https://pypi.mirrors.ustc.edu.cn/simple/
Collecting mysqlclient
  Using cached https://mirrors.bfsu.edu.cn/pypi/web/packages/37/fb/d9a8f763c84f1e789c027af0ffc7dbf94c9a38db961484f253f0552cbb47/mysqlclient-2.2.1.tar.gz (89 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Installing backend dependencies ... done
  Preparing metadata (pyproject.toml) ... done
Building wheels for collected packages: mysqlclient
  Building wheel for mysqlclient (pyproject.toml) ... error
  error: subprocess-exited-with-error
  
  × Building wheel for mysqlclient (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [41 lines of output]
      # Options for building extension module:
        extra_compile_args: ['-I/usr/local/Cellar/mysql-client/8.3.0/include/mysql', '-std=c99']
        extra_link_args: ['-L/usr/local/Cellar/mysql-client/8.3.0/lib', '-lmysqlclient']
        define_macros: [('version_info', (2, 2, 1, 'final', 0)), ('__version__', '2.2.1')]
      running bdist_wheel
      running build
      running build_py
      creating build
      creating build/lib.macosx-10.9-x86_64-cpython-39
      creating build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/release.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/cursors.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/connections.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/__init__.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/times.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/converters.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/_exceptions.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      creating build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/FLAG.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/CLIENT.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/__init__.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/ER.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/CR.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/FIELD_TYPE.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      running egg_info
      writing src/mysqlclient.egg-info/PKG-INFO
      writing dependency_links to src/mysqlclient.egg-info/dependency_links.txt
      writing top-level names to src/mysqlclient.egg-info/top_level.txt
      reading manifest file 'src/mysqlclient.egg-info/SOURCES.txt'
      reading manifest template 'MANIFEST.in'
      adding license file 'LICENSE'
      writing manifest file 'src/mysqlclient.egg-info/SOURCES.txt'
      copying src/MySQLdb/_mysql.c -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      running build_ext
      building 'MySQLdb._mysql' extension
      creating build/temp.macosx-10.9-x86_64-cpython-39
      creating build/temp.macosx-10.9-x86_64-cpython-39/src
      creating build/temp.macosx-10.9-x86_64-cpython-39/src/MySQLdb
      gcc -Wno-unused-result -Wsign-compare -Wunreachable-code -fno-common -dynamic -DNDEBUG -g -fwrapv -O3 -Wall -arch x86_64 -g "-Dversion_info=(2, 2, 1, 'final', 0)" -D__version__=2.2.1 -I/Users/clin/File/Project/shuhe/devops-api/venv/include -I/Library/Frameworks/Python.framework/Versions/3.9/include/python3.9 -c src/MySQLdb/_mysql.c -o build/temp.macosx-10.9-x86_64-cpython-39/src/MySQLdb/_mysql.o -I/usr/local/Cellar/mysql-client/8.3.0/include/mysql -std=c99
      xcrun: error: invalid active developer path (/Library/Developer/CommandLineTools), missing xcrun at: /Library/Developer/CommandLineTools/usr/bin/xcrun
      error: command '/usr/bin/gcc' failed with exit code 1
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed building wheel for mysqlclient
Failed to build mysqlclient
ERROR: Could not build wheels for mysqlclient, which is required to install pyproject.toml-based projects
```

###  1. mysql 8.0 兼容问题

**解决操作命令**
```
pip install -e git+https://github.com/etripier/mysqlclient.git@ee1882e02e3c73910b1d6df86bbdce784edbb881#egg=mysqlclient
```

![msyqlclient_8_0_install_error](/images/mysqlclient-install-error.png)

[git fix link https://github.com/PyMySQL/mysqlclient/issues/688](https://github.com/PyMySQL/mysqlclient/issues/688)
```
(venv) clin:devops-api/ (master) $ pip install mysqlclient                                                                                                               [10:54:54]
Looking in indexes: https://pypi.mirrors.ustc.edu.cn/simple/
Collecting mysqlclient
  Using cached https://mirrors.bfsu.edu.cn/pypi/web/packages/37/fb/d9a8f763c84f1e789c027af0ffc7dbf94c9a38db961484f253f0552cbb47/mysqlclient-2.2.1.tar.gz (89 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Installing backend dependencies ... done
  Preparing metadata (pyproject.toml) ... done
Building wheels for collected packages: mysqlclient
  Building wheel for mysqlclient (pyproject.toml) ... error
  error: subprocess-exited-with-error
  
  × Building wheel for mysqlclient (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [58 lines of output]
      # Options for building extension module:
        extra_compile_args: ['-I/usr/local/Cellar/mysql-client/8.3.0/include/mysql', '-std=c99']
        extra_link_args: ['-L/usr/local/Cellar/mysql-client/8.3.0/lib', '-lmysqlclient']
        define_macros: [('version_info', (2, 2, 1, 'final', 0)), ('__version__', '2.2.1')]
      running bdist_wheel
      running build
      running build_py
      creating build
      creating build/lib.macosx-10.9-x86_64-cpython-39
      creating build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/release.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/cursors.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/connections.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/__init__.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/times.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/converters.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      copying src/MySQLdb/_exceptions.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      creating build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/FLAG.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/CLIENT.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/__init__.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/ER.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/CR.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      copying src/MySQLdb/constants/FIELD_TYPE.py -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb/constants
      running egg_info
      writing src/mysqlclient.egg-info/PKG-INFO
      writing dependency_links to src/mysqlclient.egg-info/dependency_links.txt
      writing top-level names to src/mysqlclient.egg-info/top_level.txt
      reading manifest file 'src/mysqlclient.egg-info/SOURCES.txt'
      reading manifest template 'MANIFEST.in'
      adding license file 'LICENSE'
      writing manifest file 'src/mysqlclient.egg-info/SOURCES.txt'
      copying src/MySQLdb/_mysql.c -> build/lib.macosx-10.9-x86_64-cpython-39/MySQLdb
      running build_ext
      building 'MySQLdb._mysql' extension
      creating build/temp.macosx-10.9-x86_64-cpython-39
      creating build/temp.macosx-10.9-x86_64-cpython-39/src
      creating build/temp.macosx-10.9-x86_64-cpython-39/src/MySQLdb
      gcc -Wno-unused-result -Wsign-compare -Wunreachable-code -fno-common -dynamic -DNDEBUG -g -fwrapv -O3 -Wall -arch x86_64 -g "-Dversion_info=(2, 2, 1, 'final', 0)" -D__version__=2.2.1 -I/Users/clin/File/Project/shuhe/devops-api/venv/include -I/Library/Frameworks/Python.framework/Versions/3.9/include/python3.9 -c src/MySQLdb/_mysql.c -o build/temp.macosx-10.9-x86_64-cpython-39/src/MySQLdb/_mysql.o -I/usr/local/Cellar/mysql-client/8.3.0/include/mysql -std=c99
      src/MySQLdb/_mysql.c:527:9: error: call to undeclared function 'mysql_ssl_set'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
              mysql_ssl_set(&(self->connection), key, cert, ca, capath, cipher);
              ^
      src/MySQLdb/_mysql.c:527:9: note: did you mean 'mysql_close'?
      /usr/local/Cellar/mysql-client/8.3.0/include/mysql/mysql.h:797:14: note: 'mysql_close' declared here
      void STDCALL mysql_close(MYSQL *sock);
                   ^
      src/MySQLdb/_mysql.c:1795:9: error: call to undeclared function 'mysql_kill'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
          r = mysql_kill(&(self->connection), pid);
              ^
      src/MySQLdb/_mysql.c:1795:9: note: did you mean 'mysql_ping'?
      /usr/local/Cellar/mysql-client/8.3.0/include/mysql/mysql.h:525:13: note: 'mysql_ping' declared here
      int STDCALL mysql_ping(MYSQL *mysql);
                  ^
      src/MySQLdb/_mysql.c:2011:9: error: call to undeclared function 'mysql_shutdown'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
          r = mysql_shutdown(&(self->connection), SHUTDOWN_DEFAULT);
              ^
      3 errors generated.
      error: command '/usr/bin/gcc' failed with exit code 1
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed building wheel for mysqlclient
Failed to build mysqlclient
ERROR: Could not build wheels for mysqlclient, which is required to install pyproject.toml-based projects
```

### 2. arm 芯片 安装异常报错
应用启动报错
```
/Users/clin/File/Project/shuhe/devops-api/venv/bin/python3.8 /Users/clin/File/Project/shuhe/devops-api/manage.py runserver 0.0.0.0:8000 
Traceback (most recent call last):
  File "/Users/clin/File/Project/shuhe/devops-api/manage.py", line 20, in main
    django.setup()
  File "/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/django/__init__.py", line 24, in setup
    apps.populate(settings.INSTALLED_APPS)
  File "/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/django/apps/registry.py", line 91, in populate
    app_config = AppConfig.create(entry)
  File "/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/django/apps/config.py", line 224, in create
    import_module(entry)
  File "/usr/local/var/pyenv/versions/3.8.15/lib/python3.8/importlib/__init__.py", line 127, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
  File "<frozen importlib._bootstrap>", line 991, in _find_and_load
  File "<frozen importlib._bootstrap>", line 975, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 671, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 843, in exec_module
  File "<frozen importlib._bootstrap>", line 219, in _call_with_frames_removed
  File "/Users/clin/File/Project/shuhe/devops-api/apps/cmdb/__init__.py", line 6, in <module>
    from cmdb.task.sync_system_projects import sync_system_projects
  File "/Users/clin/File/Project/shuhe/devops-api/apps/cmdb/task/sync_system_projects.py", line 2, in <module>
    import MySQLdb
  File "/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/MySQLdb/__init__.py", line 17, in <module>
    from . import _mysql
ImportError: dlopen(/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/MySQLdb/_mysql.cpython-38-darwin.so, 0x0002): tried: '/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/MySQLdb/_mysql.cpython-38-darwin.so' (mach-o file, but is an incompatible architecture (have 'x86_64', need 'arm64')), '/System/Volumes/Preboot/Cryptexes/OS/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/MySQLdb/_mysql.cpython-38-darwin.so' (no such file), '/Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/MySQLdb/_mysql.cpython-38-darwin.so' (mach-o file, but is an incompatible architecture (have 'x86_64', need 'arm64'))

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/clin/File/Project/shuhe/devops-api/manage.py", line 32, in <module>
    main()
  File "/Users/clin/File/Project/shuhe/devops-api/manage.py", line 23, in main
    raise ImportError(
ImportError: Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?

Process finished with exit code 1
```

解决方案，先卸载，然后安装对应arm版本
```
(venv) clin:devops-api/ (master) $ pip uninstall mysqlclient                                                                                                                                                                                                              [17:01:12]
Found existing installation: mysqlclient 2.2.4
Uninstalling mysqlclient-2.2.4:
  Would remove:
    /Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/MySQLdb/*
    /Users/clin/File/Project/shuhe/devops-api/venv/lib/python3.8/site-packages/mysqlclient-2.2.4.dist-info/*
Proceed (Y/n)? y
  Successfully uninstalled mysqlclient-2.2.4
(venv) clin:devops-api/ (master) $ ARCHFLAGS="-arch arm64" pip install mysqlclient --compile --no-cache-dir                                                                                                                                                               [17:03:01]
Looking in indexes: https://pypi.tuna.tsinghua.edu.cn/simple/
Collecting mysqlclient
  Downloading https://pypi.tuna.tsinghua.edu.cn/packages/79/33/996dc0ba3f03e2399adc91a7de1f61cb14b57ebdb4cc6eca8a78723043cb/mysqlclient-2.2.4.tar.gz (90 kB)
     |████████████████████████████████| 90 kB 256 kB/s             
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Installing backend dependencies ... done
  Preparing metadata (pyproject.toml) ... done
Building wheels for collected packages: mysqlclient
  Building wheel for mysqlclient (pyproject.toml) ... done
  Created wheel for mysqlclient: filename=mysqlclient-2.2.4-cp38-cp38-macosx_12_0_arm64.whl size=75702 sha256=a3e9ae6f73d411a05e3af30579534c66ae3e5e1b9087b0fc89b2b84987e3bd3d
  Stored in directory: /private/var/folders/y7/s2k99dl93dz6gwl73yxjtn2c0000gn/T/pip-ephem-wheel-cache-xf7j4ax5/wheels/34/f1/30/55bf7960d0b0ff6257e4a1462e0c08c5748202e5eaeeef826c
Successfully built mysqlclient
Installing collected packages: mysqlclient
Successfully installed mysqlclient-2.2.4
WARNING: You are using pip version 21.3.1; however, version 24.0 is available.
You should consider upgrading via the '/Users/clin/File/Project/shuhe/devops-api/venv/bin/python -m pip install --upgrade pip' command.
```

### 3. 另辟蹊径，安装pymysql解决问题

pip install pymysql

在项目的`__init__`文件里配置(与`settings`同级)添加模块

```
import pymysql

pymysql.install_as_MySQLdb()

```
