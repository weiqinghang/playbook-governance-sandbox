---
title: Agent 编排协议
status: active
created: 2026-08-01
updated: 2026-08-01
source_of_truth: repo
---

# Agent 编排协议

Codex 是默认编排者。普通 single-owner delivery 不需要 Worker、Runner、claim、lease、
receipt 或 runtime log。需要独立输入时，主编排者可 dispatch 一个 bounded read-only
architect 或 reviewer；结果必须被消费。

## 调度包

每个子 Agent 只接收：目标、范围、非目标、验收、当前 Issue/MR、必要文件、验证证据与
期望输出。不得传递 secrets，不得将 Issue/MR 状态复制进 repo JSONL。

## Reviewer

MR/PR 合并前必须有独立 reviewer 对 exact HEAD 的 `review pass`。Reviewer 不实现、
不 merge/tag/release、不改标签；其共享证据是带 `Agent: reviewer`、`Instance:`、
`Via: Codex` 的原生平台 MR/PR comment。若 reviewer 无法独立完成，merge blocked。
在已安装 `gitlab-governance-core` 的项目派发正式 Reviewer 时，把
`.playbook/docs/project/reviewer-checklists.md` 和
`.playbook/docs/project/reviewer-question-contracts.md` 作为必读默认方法；Reviewer 对每条 finding
分开判断原主张、真实缺陷、组件责任、影响与严重度，不能因缺少可选 `expert-reviewer` pack 跳过。
该治理 pack 已安装却缺受管文件才属于安装漂移；Reviewer 只读并报告缺口，由有权限的执行者
按既有任务授权和目标仓写入门修复，不能从审查任务推导出跨仓写入授权。合法的
`agent-orchestration-core` 单 pack 安装不因此受阻。

## Formal Reviewer Wait Policy

正式 Reviewer 的单次观察窗口由 `.playbook/scripts/reviewer_wait_policy.py` 解析，默认且最小为
`600` 秒。窗口到达时若同一 reviewer 仍为 `pending`，继续等待同一实例；这不是 timeout，也不消耗
retry，更不得写 `review blocked`。只有 launch failed、incomplete 或明确 blocked 才进入有界重试/阻塞
处理。项目或用户 override 只能延长正式窗口；30/60/120 秒仅可用于 fake-clock 测试。

## 高风险边界

dispatch、普通 file/comment/commit/push 不是 release authorization。protected merge、
annotated tag/Release、permission/security/credential、data/schema migration、cross-repo
write 各自使用 fresh action guard。旧 delivery context 或 ActionAuthorizer 不能继续授权。

## GitHub 兼容

GitHub 目标使用 PR 承载上述 MR 职责，独立 reviewer 在 PR comment 留下相同署名及 exact HEAD。
labels 为状态权威；平台差异入口见 `.playbook/docs/project/github-governance.md`，不能在 GitHub
项目调用 GitLab MR API。首次持久化写入准入与高风险授权不因平台变化而省略。
