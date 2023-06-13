---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: true

title:       "{{ with slicestr .Name 10 }}{{replace . "-" " "  | strings.TrimLeft " " | title }}{{end}}"
subtitle:    ""
description: ""
date:        {{ slicestr .Name 0 10 }}
author:      ""
image:       ""
tags:        ["tag1", "tag2"]
categories:  ["Tech"]
archives:    "{{ slicestr .Name 0 4 }}"
---

