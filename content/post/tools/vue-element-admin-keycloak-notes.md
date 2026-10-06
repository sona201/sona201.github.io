---
title: "vue-element-admin 接入 Keycloak 的学习记录"
date: "2023-08-31T01:01:32+08:00"
lastmod: "2023-08-31T01:01:32+08:00"
categories: ["tools"]
slug: "vue-element-admin-keycloak-notes"
draft: false
---

# vue-element-admin集成Keycloak实现统一身份验证、权限控制

[vue-element-admin集成Keycloak实现统一身份验证、权限控制](https://juejin.cn/post/6844904152590450702)

## vue-element-admin

[vue-element-admin github link](https://github.com/PanJiaChen/vue-element-admin)

我的前端使用 vue-element-admin，接入 Keycloak 后希望共享登录会话，减少重复登录。

既然是要将vue-element-admin与Keycloak进行集成，那么有必要先来对vue-element-admin本身的登录、身份验证、权限控制相关的功能是如何实现的进行一个了解。核心代码主要位于如下几个文件中：

- src/permission.js：针对vue-router进行的全局导航守卫配置，身份验证、权限控制最为核心的逻辑都在这个文件中
- src/router/index.js：vue-router相关的路由配置，其中asyncRoutes是与roles相关的动态路由配置
- src/modules/permission.js：根据roles进行权限控制、生成动态路由的vuex相关操作
- src/modules/user.js：登录登出、用户信息、Token等的vuex相关操作
- src/api/user.js：登录登出、用户信息的API操作
- src/views/login/index.vue：登录页面
- src/layout/components/Navbar.vue：登出入口所在组件

## 接入思路

前提概要，系统原本有一套权限系统，暂时不想完全使用 keycloak 的角色，仅使用登录方案，免去重复登录。

去公共 keycloak 地址访问 session，如果没有则跳转到登录页，获取 token 后发送给后端，后端拿到 token 后去校验，
然后返回系统原来的 token 方案，保存，后续请求使用。

### 前端接入配置

使用 keycloak 组件对接，配置好访问地址;



这里有个 URL 要跟当前域名使用的协议一致，如果一个是 https 另一个是 http，这会出现跨域问题。


在 src/modules/permission.js 拦截器里执行登录，因为请求参数变化，后端也需要更新。

需要将登录、用户认证信息获取、登出部分进行改动，交给Keycloak处理。我们将对如下文件进行修改：

- src/store/modules/user.js：将vuex中登录、获取用户信息、登出相关的action改为通过Keycloak进行管理
- src/main.js：添加Keycloak初始化集成，将身份验证及登录部分交给Keycloak接管
- src/permission.js：获取roles部分改为从Keycloak获取
- src/layout/components/Navbar.vue：登出逻辑改为调用Keycloak的登出

### 文件更新

1. 安装 keycloak-js vuejs-logger
```
    "keycloak-js": "^22.0.1",
    "vuejs-logger": "^1.5.5",
```

2. env 配置
```
VUE_APP_KEYCLOAK_OPTIONS_URL = 'http://keycloak.domain.net/auth'
VUE_APP_KEYCLOAK_OPTIONS_REALM = 'realm'
VUE_APP_KEYCLOAK_OPTIONS_CLIENTID = 'client-demo'
VUE_APP_KEYCLOAK_OPTIONS_ONLOAD = 'login-required'
```

3. src/layout/components/Navbar.vue

```
 <script>
-import { mapGetters } from 'vuex'
 import Breadcrumb from '@/components/Breadcrumb'
 import Hamburger from '@/components/Hamburger'
+import { mapGetters } from 'vuex'
 // import ErrorLog from '@/components/ErrorLog'
 // import Screenfull from '@/components/Screenfull'
 // import SizeSelect from '@/components/SizeSelect'
 
 ...
     },
     async logout() {
       await this.$store.dispatch('user/logout')
-      this.$router.push(`/login?redirect=${this.$route.fullPath}`)
+      // this.$router.push(`/login?redirect=${this.$route.fullPath}`)
+      this.$router.push(`/?redirect=${this.$route.fullPath}`)
     }
   }
 }
```

4. src/permission.js
```
-import { getToken } from '@/utils/auth' // get token from cookie
+// get token from cookie
+import { getToken } from '@/utils/auth'
 import getPageTitle from '@/utils/get-page-title'
 import { Message } from 'element-ui'
-import NProgress from 'nprogress' // progress bar
-import 'nprogress/nprogress.css' // progress bar style
+import Keycloak from 'keycloak-js'
+// progress bar
+import NProgress from 'nprogress'
+// progress bar style
+import 'nprogress/nprogress.css'
 import router from './router'
 import store from './store'
...

const whiteList = ['/login', '/auth-redirect'] // no redirect whitelist
 
+const initOptions = {
+  url: process.env.VUE_APP_KEYCLOAK_OPTIONS_URL,
+  realm: process.env.VUE_APP_KEYCLOAK_OPTIONS_REALM,
+  clientId: process.env.VUE_APP_KEYCLOAK_OPTIONS_CLIENTID,
+  onLoad: process.env.VUE_APP_KEYCLOAK_OPTIONS_ONLOAD
+}
+
+const keycloak = new Keycloak(initOptions)
+
 router.beforeEach(async(to, from, next) => {
   // start progress bar
   NProgress.start()
           // remove token and go to login page to re-login
           await store.dispatch('user/resetToken')
           Message.error(error || 'Has Error')
-          next(`/login?redirect=${to.path}`)
+          // next(`/login?redirect=${to.path}`)
+          next(`/?redirect=${to.path}`)
           NProgress.done()
         }
       }
       next()
     } else {
       // other pages that do not have permission to access are redirected to the login page.
-      next(`/login?redirect=${to.path}`)
-      NProgress.done()
+      keycloak.init({ onLoad: initOptions.onLoad, checkLoginIframe: false }).then(async authenticated => {
+        if (!authenticated) {
+          console.log('not auth')
+          window.location.reload()
+          return
+        } else {
+          // await store.dispatch('user/keycloakLogin', keycloak.idToken)
+          await store.dispatch('user/keycloakLogin', keycloak)
+          next(`/?redirect=${to.path}`)
+          NProgress.done()
+        }
+      }).catch(error => {
+        console.log('Authenticated Failed', error)
+      })
+      // next(`/login?redirect=${to.path}`)
+      // NProgress.done()
     }
   }
 })

```


6. src/store/getters.js
```
   department: state => state.user.department,
   roles: state => state.user.roles,
   permission_routes: state => state.permission.routes,
-  errorLogs: state => state.errorLog.logs
+  errorLogs: state => state.errorLog.logs,
+  keycloak: state => state.user.keycloak
 }
 export default getters
```

7. src/store/modules/user.js
```
   nickname: '',
   introduction: '',
   department: '',
-  roles: []
+  roles: [],
+  keycloak: null
 }
 
 const mutations = {
   },
   SET_ROLES: (state, roles) => {
     state.roles = roles
+  },
+  SET_KEYCLOAK: (state, keycloak) => {
+    state.keycloak = keycloak
   }
 }
 ... 
       })
     })
   },
+  // keycloak login
+  keycloakLogin({ commit }, keycloak) {
+    return new Promise((resolve, reject) => {
+      login({ token: keycloak.idToken.trim() }).then(response => {
+        const data = response.data
+        const { token } = data
+        // const userinfo = jwtDecode(token)
+        // const { username, roles } = userinfo
+        commit('SET_TOKEN', token)
+        setToken(token)
+        commit('SET_KEYCLOAK', keycloak)
+        resolve()
+      }).catch(error => {
+        reject(error)
+      })
+    })
+  },
 
   // get user info
   getInfo({ commit, state }) {
         commit('SET_ROLES', [])
         removeToken()
         resetRouter()
+        state.keycloak.logout()
 
         // reset visited views and cached views
         // to fixed https://github.com/PanJiaChen/vue-element-admin/issues/2485
```


## 最后还留了一个问题，就是登录不能跳转到默认页面，需要解析下