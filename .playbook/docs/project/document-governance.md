---
title: 文档治理
status: active
created: 2026-08-01
updated: 2026-08-01
source_of_truth: repo
---

# 文档治理

GitLab Issue/MR 是任务、负责人、流程状态、review 与 release 的事实源。repo 文档只保存可复用
规则、实现说明和长期决定。

Standard / Heavy single-owner delivery 的必需 durable artifacts 是 Issue + MR。全部准入条件均满足的
低风险 `micro_direct` 不由 Playbook 强制新增 Issue/MR；若目标仓规则要求它们，仍以 GitLab 为事实源。
只有长期、跨版本的决定才按需
增加一份紧凑 ADR。不得为了普通工作创建或要求 Spec、Plan、profile/context/readiness、receipt、
claim/lease、runtime JSONL 或第二状态表。

文档链接必须指向当前安装 payload 或 GitLab 原生对象。历史材料可以保留在 archive，但不得作为
默认入口或执行 gate。人类协作文本使用 `.playbook/config/collaboration-language-v1.json` 的
`primary_language`；配置缺失或无效时，首次面向人类的沟通或写入前必须询问用户，不能猜测。代码、命令、
路径、字段和错误原文保持原文；语言例外说明受众或外部约束。MR reviewer comment 必须有 `Agent:`，独立
reviewer 另有 `Instance:`。
