---
title: Reviewer Checklist
status: active
created: 2026-08-01
updated: 2026-08-30
source_of_truth: repo
---

# Reviewer Checklist

对 MR 的 independent final-head review 至少验证：Issue/MR goal、scope、acceptance 一致；
面向团队的结论遵从 `collaboration-language-v1.json` 的主语言（缺失时先确认用户），技术标识保持原文；
正式 Reviewer 在 600 秒观察窗口后仍为 pending 时必须继续等待同一实例，不能以短等待写 `review blocked`；
任何 GitLab Markdown writeback 应有实际换行与读回一致性证据。
Issue 恰有一个 assignee 和一个 `workflow::*`；普通路径没有 profile/context/readiness/
receipt/claim/runtime JSONL/lifecycle manifest；legacy importer 只读；seed payload、installer、
version、release note 一致，且 release note 的状态文案在发布前后均成立，不会在正式 Release 中继续
声称“未发布”；五类 high-risk action 缺 identity/fresh observation/permission/
revision-or-head/rollback 任一即 deny；fresh verification 覆盖 exact HEAD，且无 secret、
下游写入或无关差异。

结论只能是 `review pass`、`review changes requested` 或 `review blocked`，在 GitLab MR
comment 写明 exact `head_sha`、证据、残余风险和 `Agent:`/`Instance:`/`Via: Codex`。

## 默认命题核验

按 `.playbook/docs/project/reviewer-question-contracts.md` 的 `reviewer-questions/v1` 版本、
输入边界、三态及样例执行；无可选辅助也须核对原始材料。

先独立审阅，再消费辅助输出；所有命题绑定 `question_contract_version`、candidate HEAD、阶段、来源引用
和材料摘要。命题结果只表示 `supported`、`contradicted` 或 `insufficient_evidence`；工具执行状态另报。

| 命题 | 必须核对 | 不能外推 |
| --- | --- | --- |
| 主张—证据 | 主张、对象/版本、阶段和给定证据是否相符 | 局部材料不足不是全仓不存在；RECEIVED 不是 POSTED |
| 验收—测试 | 测试是否检查验收，以及当前 candidate 的实际运行结果 | 源码存在不等于验证执行；合并前 review 不等于部署后 UAT |
| Finding—依据 | 适用规则，或可复现缺陷与真实影响 | 没有逐字规则不能自动否定真实 Bug；实现者摘要不是可信规则 |

阶段错位、被替代规则、压缩体与解压上限、未检查范围和来源冲突必须明确交还 Reviewer。辅助工具和
confidence 都不是正式门禁；关键歧义、服务失败或 HEAD/规则/证据变化使相应辅助结论无效。

## Finding 闭环检查（默认基础审查）

分别核对原 finding 主张、真实缺陷、组件责任与影响/严重度；无辅助也适用。安装了 `expert-reviewer`
时，完整方法见 Reviewer 角色的“逐条 Finding 裁定”；本检查不依赖该可选 pack。原主张错误须撤回，
同一材料证明的更窄真实缺陷仍须保留；责任不明或严重度未定不能把已证实缺陷整体写成“待核查”。
局部违规不能自动归咎某 validator 或升为 P1；有证据的跨租户敏感数据暴露不能仅因没有逐字定级规则
而降级。检查原 finding 是否遗漏或重复，命题判断与最终 finding、责任、严重度、总评是否相容。
分歧回原文或复现；材料不足不能推成全局不存在。待核查只用于事实本身仍未证实的风险，不充当
已证缺陷或 PASS。只检查格式不能证明完成了这个闭环。
