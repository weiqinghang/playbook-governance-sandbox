---
title: GitLab CLI / API 操作手册
status: active
created: 2026-08-01
updated: 2026-08-01
source_of_truth: repo
---

# GitLab CLI / API 操作手册

GitLab 是 Issue/MR/review/release 的事实源。先运行 `glab auth status`，再从当前仓库的 Git remote 解析目标 GitLab 项目，并通过 API 回读确认项目路径与 ID。不得复用 Playbook 源仓或其他项目的 ID。
普通 MR 不自动关闭 governing Issue，除非其全部 acceptance 已覆盖。protected merge 使用
`python3 scripts/git_traceability.py merge-mr --mr <iid> --governing-issue <iid> --dry-run`
先 readback；只有 exact-head reviewer PASS 后才能实际合并。tag/Release、permissions、
migrations、cross-repo write 不从普通 MR 推断授权。

面向 GitLab 的 Markdown 正文必须走 `.playbook/scripts/gitlab_markdown.py managed-write`：例如更新 Issue/MR
description 使用 `--method PUT --field description --write-endpoint <endpoint> --read-endpoint <endpoint> --input <body.md>`；
新增 note 使用 `--method POST --field body --write-endpoint <notes-endpoint> --read-endpoint <created-note-endpoint> --input <body.md>`。
命令先拒绝非代码区域的字面量 `\\n`，再经 `glab api` 写入并 GET authoritative readback；任一步失败或正文不一致即 fail closed。
只需生成待交给其他受管调用方的 payload 时，使用 `prepare --input <body.md> --field description|body --output <payload.json>`；独立回读
文件可用 `verify-readback --expected <body.md> --actual <readback.md>` 比对。
协作语言从
`.playbook/config/collaboration-language-v1.json` 解析；配置不存在时先询问用户。

single-owner 的普通维护不要求第二个 GitLab 人类账号：独立 reviewer 子 Agent 的 exact-HEAD 审计
与 controller 的明确 merge 授权即可。只有 action-specific policy 明确要求时（例如安全、权限、生产
破坏性操作或数据/schema migration），才在 preflight 增加 `--require-distinct-native-approval`，要求
不同于 MR 作者的 GitLab 原生 approval；它不是所有 protected merge 的默认门槛。
