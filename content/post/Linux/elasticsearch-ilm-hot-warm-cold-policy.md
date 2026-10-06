---
title: "Elasticsearch ILM 冷热分层与定时删除策略"
date: "2024-01-19T15:22:43+08:00"
lastmod: "2024-01-19T15:22:43+08:00"
categories: ["Linux"]
slug: "elasticsearch-ilm-hot-warm-cold-policy"
draft: false
---

更新策略

```
PUT _ilm/policy/hot-warm-cold-delete-30days
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "5gb",
            "max_age": "30d"
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          },
          "set_priority": {
            "priority": 25
          }
        }
      },
      "cold": {
        "min_age": "14d",
        "actions": {
          "freeze": {},
          "set_priority": {
            "priority": 0
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {
            "delete_searchable_snapshot": true
          }
        }
      }
    }
  }
}


```


```
PUT _ilm/policy/hot-warm-cold-delete-30days
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size":"5gb",
            "max_age":"30d"
          },
          "set_priority": {
            "priority":50
          }
        }
      },
      "warm": {
        "min_age":"7d",
        "actions": {
          "forcemerge": {
            "max_num_segments":1
          },
          "shrink": {
            "number_of_shards":1
          },
          "allocate": {
            "require": {
              "data": "warm"
            }
          },
          "set_priority": {
            "priority":25
          }
        }
      },
      "cold": {
        "min_age":"14d",
        "actions": {
          "set_priority": {
            "priority":0
          },
          "freeze": {},
          "allocate": {
            "require": {
              "data": "cold"
            }
          }
        }
      },
      "delete": {
        "min_age":"30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}


PUT _template/hot-warm-cold-delete-30days-template
{
  "order":10,
  "index_patterns": ["logstash-*", "metricbeat-*", "filebeat-*"],
  "settings": {
    "index.routing.allocation.require.data": "hot",
    "index.lifecycle.name": "hot-warm-cold-delete-30days"
  }
}

PUT _template/hot-warm-cold-delete-30days-template
{
  "order":10,
  "index_patterns": ["logstash-sysjson-*"],
  "settings": {
    "index.routing.allocation.require.data": "hot",
    "index.lifecycle.name": "hot-warm-cold-delete-30days"
  }
}


{
  "index.blocks.read_only_allow_delete": "false",
  "index.priority": "1",
  "index.query.default_field": [
    "*"
  ],
  "index.write.wait_for_active_shards": "1",
  "index.routing.allocation.include._tier_preference": "data_content",
  "index.refresh_interval": "5s",
  "index.number_of_replicas": "1"
}

{
  "index.blocks.read_only_allow_delete": "false",
  "index.query.default_field": [
    "*"
  ],
  "index.write.wait_for_active_shards": "1",
  "index.lifecycle.name": "hot-warm-cold-delete-30days",
  "index.routing.allocation.include._tier_preference": "data_content",
  "index.routing.allocation.require.data": "hot",
  "index.refresh_interval": "5s",
  "index.priority": "50",
  "index.number_of_replicas": "1"
}


PUT _ilm/policy/hot-warm-cold-delete-7days
{
  "policy": {
    "phases": {
      "delete": {
        "min_age":"7d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```