# GitHub.com 个人仓库治理兼容方案

首版面向个人 Free 公开单仓。使用 `gh` 的已登录账号，写入前确认目标 owner/repo；私有仓库
及企业版能力不从公开沙箱推断。现有 `gitlab-governance-core` pack 名称保留兼容，并提供 GitHub
适配脚本；不要求 GitHub 目标调用 glab。托管 Web 安装服务目前仍为 GitLab，不在此冒称支持 GitHub OAuth。

## 权威与入口

Issue 的目标、范围、验收、唯一 assignee、labels 和 Milestone 是工作事实；PR 承载实现与 review。
`workflow::*` 与 `backlog::*` 各且仅一个已知值。只初始化 Discovery / Delivery；不创建 Backbone、
Parent backbone、Development、Initiatives 或组织级 Issue fields。

首次实现写入之前调用 `git_workflow_guard.py --action file_mutation --issue <number>`，读取当前
origin、平台默认/受保护分支与同仓 Issue；目标仓必须先存在非默认、非受保护工作分支。
讨论中途转执行、合并后开始另一项工作同样检查。授权保留，不要求再问用户是否允许建 Issue/分支。

## 初始化与同步

```sh
python3 .playbook/scripts/github_governance.py --repo OWNER/REPO init
python3 .playbook/scripts/github_governance.py --repo OWNER/REPO --apply init
python3 .playbook/scripts/github_governance.py --repo OWNER/REPO --apply milestone --title 'Iteration 1'
python3 .playbook/scripts/github_governance.py --repo OWNER/REPO --apply transition --issue 1 --workflow doing --maturity ready-for-dev
python3 .playbook/scripts/github_governance.py --repo OWNER/REPO --apply sync --issue 1 --project 1
```

所有写命令都要求 `--apply`；缺省为读取/预览。Project 使用与仓库绑定的描述标记；同名但未标记的
对象以及字段/视图定制冲突保留并报错，不静默覆盖。API 权限失败不视为初始化成功。
如果首次创建 Project 成功但归属标记写入失败，先读取并确认本次创建的 Project number；使用
`init --recover-project <number>` 预览并显式 `--apply` 恢复。仅接受同名、无描述、无 item/关联仓库、
默认字段与默认 View 1 的空项目，任何定制都拒绝；不凭同名自动认领。
Board 使用普通 Project 单选字段作为可丢弃投影，字段不保存治理权威；手工拖动不能触发
Issue 状态、merge、Release 或 close。下次 sync 按原生 Issue labels 恢复字段。
标签变更后应立即 sync；可由可信定时/事件调用方调度同一命令。首版不安装后台服务或双向机器人，
未调度时应明确展示只是最近一次同步结果，不宣称实时。不要把个人管理 token 写入公开仓库或日志。

## 分支保护

显式使用 `protect-default --check <实际检查名称>` 预览，加 `--apply` 才建立默认分支 Ruleset。
同名已有规则不同则保留并报冲突，不覆盖。检查名称必须对应真正的验证来源，不能用占位 success
替代 CI 或独立审查；沙箱合成 status 只验证 GitHub 平台的拒绝机制。当前账号缺 workflow scope 时，
不能发布 Actions 文件，应报告此限制，不绕过权限。平台分支保护不阻止本地首次编辑，仍需首次写入准入。

## 审查与关闭

独立 reviewer 的 PR comment 包含 `Agent: reviewer`、`Instance: reviewer:<id>`、`Via: Codex`、
`head_sha: <exact SHA>` 与 `review_result: review pass|changes requested|blocked`。
`merge-preflight --pr <number> --issue <number>` 只读检查最新 exact-HEAD 记录、目标分支与平台
mergeability。它不授权合并。实际合并使用 GitHub 原生接口并传预期 SHA，遵守 Rulesets/required checks。
同一账号上的独立 Agent 审查不等于另一账号的 GitHub Review；需要原生批准时必须另配身份。
PR 用 `Refs #<number>`，不使用自动关闭关键字。workflow::done、Issue closed、PR merged 与
Release published 分开处理，Milestone 也不自动关闭。更改状态不是得到关闭/发布授权。

## 资源分发

通用资源采用 Release assets：创建 annotated tag、draft Release，上传资源文件与
`manifest.json`（`schema_version: 1, files: [{name, sha256}]`），校验后按明确授权发布。
消费端按精确 tag 下载到隔离目录，调用 `github_governance.verify_assets` 校验文件名和哈希。
不使用 latest 定位，不把短期 Actions artifacts 当作稳定分发；真实解包继续使用安全路径检查。
建议启用 Immutable releases；须在发布之前上传齐全部资产。测试只使用合成资源，不能上传真实私有资源。
