---
title: "JumpServer 手动下载与解压笔记"
date: "2024-01-25T01:40:54+08:00"
lastmod: "2024-01-25T01:40:54+08:00"
categories: ["tools"]
slug: "jumpserver-manual-download-notes"
draft: false
---

https://docs.jumpserver.org/zh/v2/install/setup_by_fast/

https://docs.jumpserver.org/zh/v2/dev/build/#_3

cd /opt
mkdir /opt/jumpserver-v2.28.8
wget -O /opt/jumpserver-v2.28.8.tar.gz https://github.com/jumpserver/jumpserver/archive/refs/tags/v2.28.8.tar.gz
tar -xf jumpserver-v2.28.8.tar.gz -C /opt/jumpserver-v2.28.8 --strip-components 1
cd jumpserver-v2.28.8
rm -f apps/common/utils/ip/geoip/GeoLite2-City.mmdb apps/common/utils/ip/ipip/ipipfree.ipdb
wget https://download.jumpserver.org/files/ip/GeoLite2-City.mmdb -O apps/common/utils/ip/geoip/GeoLite2-City.mmdb
wget https://download.jumpserver.org/files/ip/ipipfree.ipdb -O apps/common/utils/ip/ipip/ipipfree.ipdb