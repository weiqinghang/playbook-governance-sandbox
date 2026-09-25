---
title: 项目内 Agent 字典
status: active
created: 2026-08-01
updated: 2026-08-01
source_of_truth: repo
---

# 项目内 Agent 字典

Codex 直接完成 ordinary single-owner 实现。仅在独立信息价值高于协调成本时调度：

- `architect`：结构迁移、边界或 rollback 不清时，只读给出 adopted/rejected/deferred。
- `reviewer`：MR/PR 已有 fresh verification 时，对 exact HEAD 做 formal pass/changes requested/
  blocked 结论；必须独立于 implementer。
- `qa-engineer`：需要独立运行或回归证据时；不替代 reviewer gate。
- `investigator`：重复失败且根因未知时；不直接扩展范围。

Agent 输出默认中文，明确 evidence、remaining risk 与下一步。没有可审对象、独立性或
必要输入时必须 blocked，不能靠主线程角色扮演补足。任何正式平台 note/comment 均署名。
