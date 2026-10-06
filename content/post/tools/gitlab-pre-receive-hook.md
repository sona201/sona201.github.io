---
title: "GitLab pre-receive 提交检查笔记"
date: "2023-07-05T01:05:24+08:00"
lastmod: "2023-07-05T01:05:24+08:00"
categories: ["tools"]
slug: "gitlab-pre-receive-hook"
draft: false
---

# Gitlab commit hook

### 1 hook概念
git 提供了一些hook，可以在提交代码时进行相关的检测，这些hook可以在客户端，也可以在服务端。目前主流都是在服务端进行检测。

#### 1.1 客户端钩子

客户端钩子分为很多种。 下面把它们分为：提交工作流钩子、电子邮件工作流钩子和其它钩子。

#### 1.2 服务器端钩子

除了客户端钩子，作为系统管理员，你还可以使用若干服务器端的钩子对项目强制执行各种类型的策略。 这些钩子脚本在推送到服务器之前和之后运行。 推送到服务器前运行的钩子可以在任何时候以非零值退出，拒绝推送并给客户端返回错误消息，还可以依你所想设置足够复杂的推送策略。

- `pre-receive`
处理来自客户端的推送操作时，最先被调用的脚本是 pre-receive。 它从标准输入获取一系列被推送的引用。如果它以非零值退出，所有的推送内容都不会被接受。 你可以用这个钩子阻止对引用进行非快进（non-fast-forward）的更新，或者对该推送所修改的所有引用和文件进行访问控制。

- `update`
`update` 脚本和 pre-receive 脚本十分类似，不同之处在于它会为每一个准备更新的分支各运行一次。 假如推送者同时向多个分支推送内容，pre-receive 只运行一次，相比之下 update 则会为每一个被推送的分支各运行一次。 它不会从标准输入读取内容，而是接受三个参数：引用的名字（分支），推送前的引用指向的内容的 SHA-1 值，以及用户准备推送的内容的 SHA-1 值。 如果 update 脚本以非零值退出，只有相应的那一个引用会被拒绝；其余的依然会被更新。

- `post-receive`
`post-receive` 挂钩在整个过程完结以后运行，可以用来更新其他系统服务或者通知用户。 它接受与 pre-receive 相同的标准输入数据。 它的用途包括给某个邮件列表发信，通知持续集成（continous integration）的服务器， 或者更新问题追踪系统（ticket-tracking system） —— 甚至可以通过分析提交信息来决定某个问题（ticket）是否应该被开启，修改或者关闭。 该脚本无法终止推送进程，不过客户端在它结束运行之前将保持连接状态， 所以如果你想做其他操作需谨慎使用它，因为它将耗费你很长的一段时间。

[原文链接 https://git-scm.com/book/zh/v2/%E8%87%AA%E5%AE%9A%E4%B9%89-Git-Git-%E9%92%A9%E5%AD%90](https://git-scm.com/book/zh/v2/%E8%87%AA%E5%AE%9A%E4%B9%89-Git-Git-%E9%92%A9%E5%AD%90)

## 2 配置hook

### 2.1 查看仓库id

`gitlab` 使用`hash`id来作为目录名字，在服务器上找目录不是那么容易，甚至不知道怎么找。有两种方式，一个最简单，管理员可以直接看到对应仓库的`hash`id，这种暂不过多描述。

另外一种是查看gitlab服务端的仓库的 `Settings` -> `General` 页面有个 `Project ID`，拿到这个值，执行`shell`命令

```bash
# 以 Project ID 123 为示例计算仓库目录的哈希
echo -n 123 | sha256sum
```

对应仓库位于 `/var/opt/gitlab/git-data/repositories/@hashed/` 下，通常按哈希的前四位分为两级目录，再进入完整哈希命名的仓库目录。

### 2.2 添加hook配置
创建hook目录，custom_hooks

```bash
# 将 <project-repository> 替换为对应仓库目录
cd /var/opt/gitlab/git-data/repositories/@hashed/<project-repository>.git
mkdir -p custom_hooks/pre-receive.d
```

### 2.3 添加hook文件，文件名为`pre-receive`

`gitlab-hook` 可执行文件 `pre-receive`
```bash
#!/bin/bash
# @author example@example.com
# @date 2023-03-15
# @description
# 在代码push时预检查备注信息是否符合规范，如不符合规范会被退回
# 该脚本安装在gitlab服务器的/opt/bcds-gitlab-hooks/hooks/install/custom_hooks/pre-receive.d/目录
# 安装时，脚本需要重命名为pre-receive，并通过命令 chmod +x pre-receive 设置权限

# 错误信息模版
ERROR_FORAMT="| %-40s| %-26s| %-15s| %-30s| %s\n"
# 错误信息头标题
ERROR_HRADER=$(printf "${ERROR_FORAMT}" "COMMIT ID" "ERROR" "AUTHOR" "DATE" "MESSAGE")
# 错误信息数组
declare -a errorArray=()

# 零COMMIT ID
ZERO_COMMIT_ID='0000000000000000000000000000000000000000'
# Merge操作的正则表达式
MERGE_REGEX='^Merge (remote-tracking )?branch(es)? (.+) into (.+)$'
# 提交规范的正则表达式
REGEX='^(feat|fix|docs|style|build|refactor|revert|test|perf|ci|chore|hotfix)(\(([A-Za-z0-9]+-[0-9]+)?\))?!?: (.+)$'

echo "【pre-receive】开始检查提交信息..."
while read oldrev newrev refname; do
  echo "【pre-receive】您提交的 branch : ${refname}"
  echo "【pre-receive】您提交的 oldrev : ${oldrev}"
  echo "【pre-receive】您提交的 newrev : ${newrev}"

  # Branch or tag got deleted, ignore the push
  [[ "${newrev}" == "${ZERO_COMMIT_ID}" ]] && continue

  # Calculate range for new branch/updated branch
  [[ "${oldrev}" == "${ZERO_COMMIT_ID}" ]] && range="${newrev}" || range="${oldrev}..${newrev}"

  # 获取代码提交的信息
  for commitId in $(git rev-list "${range}" --not --all); do
    # 获取提交者
    user=$(git log --pretty=format:"%an" "${commitId}" -1)
    # 获取提交日期
    commitDate=$(git log --pretty=format:"%cd" "${commitId}" -1)
    # 获取提交日志
    msg=$(git log --pretty=format:"%s" "${commitId}" -1)

    # 忽略Merge操作
    [[ ${msg} =~ ${MERGE_REGEX} ]] && continue

    # 找到匹配说明是符合规范的
    if [[ ${msg} =~ ${REGEX} ]]; then
      # 代码提交的类型
      type=${BASH_REMATCH[1]}
      # 关联的STORY或REQ编号
      code=${BASH_REMATCH[3]}
      # 只有hotfix类型可以不关联STORY或REQ
      if [[ -z ${code} && ${type} != "hotfix" ]]; then
        item=$(printf "${ERROR_FORAMT}" "${commitId}" "No STORY or REQ associated" "${user}" "${commitDate}" "${msg}")
        errorArray+=("${item}")
      fi
    else
      item=$(printf "${ERROR_FORAMT}" "${commitId}" "Invalid format" "${user}" "${commitDate}" "${msg}")
      errorArray+=("${item}")
    fi
  done
done

# 判断是否有异常信息
if [[ ${#errorArray[@]} > 0 ]]; then
  echo -e "【pre-receive】[error]代码提交信息不符合规范，模板：<type>(<STORY/REQ>): <description>，详情请看: http://wiki.company.org/pages/viewpage.action?pageId=12345678"
  echo -e "【pre-receive】[error]代码提交信息详情请看下表："
  echo "${ERROR_HRADER}"
  for item in "${errorArray[@]}"; do
    echo "${item}"
  done
  exit 1
else
  echo "【pre-receive】代码提交信息校验通过"
  exit 0
fi

```