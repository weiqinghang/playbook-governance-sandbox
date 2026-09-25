# 显式角色接力

仅在当前控制器已选择 role-relay 时读取；项目产品开发契约仍是规则源。

一条龙由同一个 owner 直接完成全循环，不生成角色 handoff。只有已显式选择两条龙时，才消费
产品验收角色提供的 `feature_path + source_commit + acceptance_ids + explicit_exclusions + runner_proof`；
全新规格额外提供 `specification_red`，已有实现则独立复验当前行为，不要求回造规格失败。
选择 `opt_in_dogfood` 连续推进时还必须消费 `acceptance_continuity + acceptance_authorization`；
标准返回只要求已解析的 continuity mode。
`product_behavior + role-relay` 必须在离开 Discovery 前由 governing Issue 记录
`acceptance_continuity: opt_in_dogfood|standard_product_return`；缺省等价于
`standard_product_return`，由编排者在 governing Issue/note 归一为 `standard_product_return` 后继续，
不等待产品确认；未显式 opt-in 时保持 GREEN 后返回产品验收且不得计入 dogfood，不能从聊天或角色可用性推断授权。
`standard_product_return` 不要求 `acceptance_authorization`，不得因 AC 分类缺失返回 Discovery；只有选择
`opt_in_dogfood` 但授权输入不完整时不得进入 `workflow::ready`。
接手时从 exact `source_commit` 解析并复核 feature 与 AC inventory，并保持 `explicit_exclusions` 不变。
只有 `opt_in_dogfood` 才要求两类授权 AC 的并集必须恰好等于 inventory，内部和跨类不得重复、不得出现额外 ID。
跨仓交付还必须 fresh-read `governing_issue`，确认 `implementation_repositories` 包含当前仓，且已解析
mode、feature/source、AC inventory 和排除项一致；只有 opt-in 额外核对 AC 分类和 return triggers。
通用输入缺失或不一致时返回 governing Issue 的 Discovery，标准返回不因 opt-in 专属字段缺失而阻塞。


交接全新规格时，独立重放 runner proof、collect 和 Specification RED；普通环境问题先修复 Product Ready，
不能冒充行为 RED。已有实现或已有 GREEN 的接手按 SKILL.md 的接手路径验证，不能要求回造 undefined steps。

GREEN 后默认返回产品验收。只有显式 `opt_in_dogfood`、exact feature/AC inventory 与排除项未变化、
全部 AC 均为 `objective_evidence`、业务语义未变化、fresh evidence 符合预期且未触发 return triggers，
才连续完成业务验收证据。`product_judgment`、新业务选择、语义变化、范围扩张、证据歧义或验收充分性
不清时，GREEN 后返回产品验收。人工操作不等于产品裁量；客观可判断的浏览器或运行时操作也可属于
`objective_evidence`。这不授权 merge 或发布，也不能替代 exact-HEAD 独立 Reviewer。

opt-in 观测沿用 governing Issue/MR，不创建额外工件：

```yaml
acceptance_continuity_observation:
  observed_at:
  continuous_completion: true | false
  unexpected_product_returns: 0
  context_resume_count: 0
  return_trigger:
  evidence_refs: []
```

只填写可回读事实；没有观测不能把默认值当结果。
