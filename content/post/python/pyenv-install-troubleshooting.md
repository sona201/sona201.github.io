---
title: "pyenv 安装与 Apple Silicon 故障排查"
date: "2023-10-23T13:40:21+08:00"
lastmod: "2023-10-23T13:40:21+08:00"
categories: ["python"]
slug: "pyenv-install-troubleshooting"
draft: false
---

pyenv install
### 官方文档
[pyenv office doc](https://github.com/pyenv/pyenv#installation)

https://github.com/pyenv/pyenv

### 默认简单方式
brew install pyenv

```
# Github
# curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
# recommand
curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
# simple
curl https://pyenv.run | bash
```


### 查看当前版本
```
pyenv versions
```

### 查看当前可安装版本
```
pyenv install -l
```

### 安装对应版本

Intel 芯片安装
```
pyenv install 3.10.6
```

Arm 芯片安装
```
export ARCHFLAGS="-arch arm64"; pyenv install 3.10.6
export ARCHFLAGS="-arch arm64";arch --arm64 pyenv install 3.7.15
```

> 一个神奇的点，使用kitty终端能安装成功，但用secretCRT却不行

查看对应的版本是否存在，可以去指定目录下看是否有对应版本号

```
echo $(pyenv root)
/usr/local/var/pyenv/versions/
```


### 设置当前使用的python版本
```
#配置当前shell的python版本，退出shell则失效
pyenv shell 3.7.17

#配置所在项目（目录）的python版本
pyenv local 3.7.17

#配置当前用户的系统使用的python版本
pyenv global 3.7.17

#查看当前版本
python -V
```

install python develop
```bash
export ARCHFLAGS="-arch arm64"; pyenv install 3.8-dev
python-build: use openssl@1.1 from homebrew
python-build: use readline from homebrew
Cloning https://github.com/python/cpython...
Installing Python-3.8-dev...
python-build: use readline from homebrew
python-build: use zlib from xcode sdk
Installed Python-3.8-dev to /usr/local/var/pyenv/versions/3.8-dev

cd /usr/local/var/pyenv/versions/3.8-dev
```

### 查看安装报错详情
```
pyenv install 3.9.15 --verbose
```

#### 安装失败

报错提示缺少lib，搜索关键字`ModuleNotFoundError: No module named '_lzma' WARNING: The Python lzma extension was not compiled. Missing the lzma lib`
```
admin@admins-MacBook-Pro ~ % export ARCHFLAGS="-arch arm64";arch --arm64 pyenv install 3.7.15
pyenv: /Users/example/.pyenv/versions/3.7.15 already exists
continue with installation? (y/N) y
python-build: use openssl from homebrew
python-build: use readline from homebrew
Downloading Python-3.7.15.tar.xz...
-> https://www.python.org/ftp/python/3.7.15/Python-3.7.15.tar.xz
Installing Python-3.7.15...
patching file 'Doc/library/ctypes.rst'
patching file 'Lib/test/test_unicode.py'
patching file 'Modules/_ctypes/_ctypes.c'
patching file 'Modules/_ctypes/callproc.c'
patching file 'Modules/_ctypes/ctypes.h'
patching file setup.py
patching file 'Misc/NEWS.d/next/Core and Builtins/2020-06-30-04-44-29.bpo-41100.PJwA6F.rst'
patching file 'Modules/_decimal/libmpdec/mpdecimal.h'
patching file setup.py
python-build: use readline from homebrew
python-build: use zlib from xcode sdk
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/Users/example/.pyenv/versions/3.7.15/lib/python3.7/lzma.py", line 27, in <module>
    from _lzma import *
ModuleNotFoundError: No module named '_lzma'
WARNING: The Python lzma extension was not compiled. Missing the lzma lib?
Installed Python-3.7.15 to /Users/example/.pyenv/versions/3.7.15
```

解决方案，安装对应的包
```
brew install readline xz
```

#### arm 芯片 3.9 版本安装问题

安装python3.9.15时，提示`readline-8.1.tar.gz`包下载失败，报错如下。

手动从网上找到一个地址下载了这个包。想能不能自己搭建个服务器提供下载。但因为是https，无法进行host写死转发下载。于是被迫看执行脚本，看看能不能搜索到执行脚本，然后更改下载源。
```
clin:Project/ $ pyenv install 3.9.15 --verbose
python-build: use openssl@1.1 from homebrew
/var/folders/y7/s2k99dl93dz6gwl73yxjtn2c0000gn/T/python-build.20240124165710.23936 ~/File/Project
Downloading readline-8.1.tar.gz...
HTTP/1.1 200 Connection established

HTTP/2 404
server: GitHub.com
content-type: text/html; charset=utf-8
permissions-policy: interest-cohort=()
access-control-allow-origin: *
etag: "64d39a40-24a3"
content-security-policy: default-src 'none'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'
x-proxy-cache: MISS
x-github-request-id: 6004:22C29E:99AB1:AFE1F:65B0CC14
accept-ranges: bytes
date: Wed, 24 Jan 2024 08:57:11 GMT
via: 1.1 varnish
age: 1235
x-served-by: cache-qpg1234-QPG
x-cache: HIT
x-cache-hits: 1
x-timer: S1706086632.903138,VS0,VE2
vary: Accept-Encoding
x-fastly-request-id: aac04c88e0b4189654405bc0e51408bad9c54033
content-length: 9379

-> https://ftpmirror.gnu.org/readline/readline-8.1.tar.gz
curl: (35) LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to mirror.ossplanet.net:443
error: failed to download readline-8.1.tar.gz

BUILD FAILED (OS X 14.2.1 using python-build 20180424)

Results logged to /var/folders/y7/s2k99dl93dz6gwl73yxjtn2c0000gn/T/python-build.20240124165710.23936.log

Last 10 log lines:
age: 1235
x-served-by: cache-qpg1234-QPG
x-cache: HIT
x-cache-hits: 1
x-timer: S1706086632.903138,VS0,VE2
vary: Accept-Encoding
x-fastly-request-id: aac04c88e0b4189654405bc0e51408bad9c54033
content-length: 9379

curl: (35) LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to mirror.ossplanet.net:443
```

通过多次关键字搜索，在git上发现脚本，https://github.com/pyenv/pyenv/blob/2374260efa9af987f2c046475dcd22804a81fb6d/plugins/python-build/share/python-build/3.9.17#L7

```bash
prefer_openssl11
export PYTHON_BUILD_CONFIGURE_WITH_OPENSSL=1
# Avoid a compilation error when linking against OpenSSL built with SSLv3 support (fixed in 3.10.0) (#2181)
export PYTHON_CFLAGS="-DOPENSSL_NO_SSL3${PYTHON_CFLAGS:+ $PYTHON_CFLAGS}"

install_package "openssl-1.1.1u" "https://www.openssl.org/source/openssl-1.1.1u.tar.gz#e2f8d84b523eecd06c7be7626830370300fbcc15386bf5142d72758f6963ebc6" mac_openssl --if has_broken_mac_openssl
install_package "readline-8.1" "https://ftpmirror.gnu.org/readline/readline-8.1.tar.gz#f8ceb4ee131e3232226a17f51b164afc46cd0b9e6cef344be87c65962cb82b02" mac_readline --if has_broken_mac_readline
if has_tar_xz_support; then
  install_package "Python-3.9.17" "https://www.python.org/ftp/python/3.9.17/Python-3.9.17.tar.xz#30ce057c44f283f8ed93606ccbdb8d51dd526bdc4c62cce5e0dc217bfa3e8cee" standard verify_py39 copy_python_gdb ensurepip
else
  install_package "Python-3.9.17" "https://www.python.org/ftp/python/3.9.17/Python-3.9.17.tgz#8ead58f669f7e19d777c3556b62fae29a81d7f06a7122ff9bc57f7dd82d7e014" standard verify_py39 copy_python_gdb ensurepip
fi
```

于是搜了下本地，发现了类似的脚本。
本地执行的时候发现执行的命令其实是`python-build`，于是开始排查这是不是执行脚本，里面有没有`readline`相关的包或关键字
```
clin:Project/ $ which python-build
/opt/homebrew/bin/python-build
clin:Project/ $ ll /opt/homebrew/bin/python-build
lrwxr-xr-x@ 1 clin  admin    38B Aug 21 10:37 /opt/homebrew/bin/python-build -> ../Cellar/pyenv/2.3.6/bin/python-build
clin:Project/ $ cd /opt/homebrew/bin/
clin:bin/ (stable) $ cd ../Cellar/pyenv/
clin:pyenv/ (stable) $ ll
total 0
drwxr-xr-x  22 clin  admin   704B Nov 14  2022 2.3.6
clin:pyenv/ (stable) $ cd 2.3.6
clin:2.3.6/ (stable) $ ll
total 440
-rw-r--r--   1 clin  admin    41K Nov  3  2022 CHANGELOG.md
-rw-r--r--   1 clin  admin    11K Nov  3  2022 COMMANDS.md
-rw-r--r--   1 clin  admin   3.3K Nov  3  2022 CONDUCT.md
-rw-r--r--   1 clin  admin   6.7K Nov  3  2022 CONTRIBUTING.md
-rw-r--r--   1 clin  admin   680B Nov  3  2022 Dockerfile
-rw-r--r--   1 clin  admin   1.6K Nov 14  2022 INSTALL_RECEIPT.json
-rw-r--r--   1 clin  admin   1.1K Nov  3  2022 LICENSE
-rw-r--r--   1 clin  admin   1.0K Nov  3  2022 MAINTENANCE.md
-rw-r--r--   1 clin  admin   928B Nov  3  2022 Makefile
-rw-r--r--   1 clin  admin    26K Nov  3  2022 README.md
drwxr-xr-x   6 clin  admin   192B Nov  3  2022 bin
drwxr-xr-x   5 clin  admin   160B Nov  3  2022 completions
drwxr-xr-x  29 clin  admin   928B Nov 14  2022 libexec
drwxr-xr-x   4 clin  admin   128B Nov  3  2022 plugins
drwxr-xr-x   5 clin  admin   160B Nov  3  2022 pyenv.d
drwxr-xr-x   3 clin  admin    96B Nov  3  2022 share
drwxr-xr-x   9 clin  admin   288B Nov  3  2022 src
-rw-r--r--   1 clin  admin   102K Nov  3  2022 terminal_output.png
drwxr-xr-x  30 clin  admin   960B Nov  3  2022 test
```

通过上面的发现执行脚本就是`pyenv`每次更新，然后去拉取对应版本的执行脚本

```
clin:python-build/ (stable) $ pwd
/opt/homebrew/Cellar/pyenv/2.3.6/plugins/python-build/share/python-build
```

在这个目录下有对应版本的执行脚本，里面就有readline包下载地址，更新后就可以正常跑了。之前不清楚这些脚本都是怎么运行的，以为都是各种特殊的逻辑进行安装。现在发现都是类似`打表`，有人维护好各种兼容脚本供大家使用。加上互联网的支持，及时更新。
