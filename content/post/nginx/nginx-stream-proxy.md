---
title: "Nginx Stream 四层代理配置笔记"
date: "2024-01-14T20:30:47+08:00"
lastmod: "2024-01-14T20:30:47+08:00"
categories: ["nginx"]
slug: "nginx-stream-proxy"
draft: false
---

nginx 4层代理(初级版)

> Nginx从1.9.0版本开始，新增加了一个stream模块，用来实现四层协议的转发、代理或者负载均衡

> 本笔记使用的 Nginx 1.16.1 软件包动态加载了 stream 模块。不同安装包的模块配置需要分别检查。

http://nginx.org/en/docs/stream/ngx_stream_core_module.html

暂不需要编译源码
http://nginx.org/en/download.html


遇到问题：以下都是环境上缺少相关的依赖，安装即可
```
./configure: error: the HTTP XSLT module requires the libxml2/libxslt
yum install libxslt-devel -y

./configure: error: the HTTP image filter module requires the GD library.
 yum install gd-devel -y
 
 ./configure: error: perl module ExtUtils::Embed is required
 yum -y install perl-devel perl-ExtUtils-Embed
 
./configure: error: the GeoIP module requires the GeoIP library.
 yum -y install GeoIP GeoIP-devel GeoIP-data
 
./configure: error: the Google perftools module requires the Google perftools
yum install gperftools -y

./configure: error: SSL modules require the OpenSSL library.
yum -y install openssl openssl-devel

checking for --with-ld-opt="-Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld -Wl,-E" ... not found
./configure: error: the invalid value in --with-ld-opt="-Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld -Wl,-E"
yum install redhat-rpm-config -y

./configure: error: perl module ExtUtils::Embed is required
yum -y install perl-devel perl-ExtUtils-Embed

在执行make时候的报错：
/root/nginx-auth-ldap/ngx_http_auth_ldap_module.c:33:18: fatal error: ldap.h: No such file or directory
 #include <ldap.h>
yum install -y openldap-devel
```

### 配置文件样例
```
# For more information on configuration, see:
#   * Official English Documentation: http://nginx.org/en/docs/
#   * Official Russian Documentation: http://nginx.org/ru/docs/

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

stream {
    upstream tcp_proxy {
        hash $remote_addr consistent;
        server 192.0.2.10:30400  max_fails=3 fail_timeout=30s;
        #server 192.0.2.11:30400  max_fails=3 fail_timeout=30s;
    }
    server {
        listen 443;
        proxy_connect_timeout 1s;
        proxy_timeout 3s;
        proxy_pass tcp_proxy;
    }
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;

    server {
        listen       80 default_server;
        server_name  _;
        root         /usr/share/nginx/html;

        # Load configuration files for the default server block.
        include /etc/nginx/default.d/*.conf;

        location / {
        }

        error_page 404 /404.html;
            location = /40x.html {
        }

        error_page 500 502 503 504 /50x.html;
            location = /50x.html {
        }
    }


}
```


### nginx yum安装1.16 配置参数
```bash
nginx version: nginx/1.16.1
built by gcc 4.8.5 20150623 (Red Hat 4.8.5-39) (GCC) 
built with OpenSSL 1.0.2k-fips  26 Jan 2017
TLS SNI support enabled
configure arguments: --prefix=/usr/share/nginx --sbin-path=/usr/sbin/nginx --modules-path=/usr/lib64/nginx/modules --conf-path=/etc/nginx/nginx.conf --error-log-path=/var/log/nginx/error.log --http-log-path=/var/log/nginx/access.log --http-client-body-temp-path=/var/lib/nginx/tmp/client_body --http-proxy-temp-path=/var/lib/nginx/tmp/proxy --http-fastcgi-temp-path=/var/lib/nginx/tmp/fastcgi --http-uwsgi-temp-path=/var/lib/nginx/tmp/uwsgi --http-scgi-temp-path=/var/lib/nginx/tmp/scgi --pid-path=/run/nginx.pid --lock-path=/run/lock/subsys/nginx --user=nginx --group=nginx --with-file-aio --with-ipv6 --with-http_ssl_module --with-http_v2_module --with-http_realip_module --with-stream_ssl_preread_module --with-http_addition_module --with-http_xslt_module=dynamic --with-http_image_filter_module=dynamic --with-http_sub_module --with-http_dav_module --with-http_flv_module --with-http_mp4_module --with-http_gunzip_module --with-http_gzip_static_module --with-http_random_index_module --with-http_secure_link_module --with-http_degradation_module --with-http_slice_module --with-http_stub_status_module --with-http_perl_module=dynamic --with-http_auth_request_module --with-mail=dynamic --with-mail_ssl_module --with-pcre --with-pcre-jit --with-stream=dynamic --with-stream_ssl_module --with-google_perftools_module --with-debug --with-cc-opt='-O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic' --with-ld-opt='-Wl,-z,relro -specs=/usr/lib/rpm/redhat/redhat-hardened-ld -Wl,-E'
```

有两个模块能达到效果:

- ngx_stream_proxy_module
- ngx_stream_core_module