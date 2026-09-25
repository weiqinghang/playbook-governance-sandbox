---
name: delivery-verification
description: Use before claiming an implementation, fix, QA slice, or delivery item complete when acceptance criteria must be mapped to fresh, locatable evidence such as tests, builds, queries, runtime checks, screenshots, or diffs. Structure evidence for deterministic checking, but never replace QA judgment, the Formal Reviewer, or final-HEAD confirmation.
---

# Delivery Verification

把每个 acceptance item 映射到 fresh evidence。本文是 Playbook 唯一权威的交付证据语义；其它
workflow、角色或 Skill 只能引用它，不得复制 completion taxonomy 或建立第二套状态机。该 Skill
只组织和核对证据，不是第二个 Reviewer，也不保存 per-task evidence 文件或 runtime ledger。

## 九层闭集

层级名称和顺序固定，但输出长度不固定：

1. `artifact_implementation`：实现或产物；
2. `automated_tests`：自动化测试；
3. `independent_reviewer`：独立 Reviewer；
4. `commit_mr_exact_head`：commit、MR 与 exact HEAD；
5. `merge_closeout`：merge 与 Issue closeout；
6. `migration_deploy`：migration 或 deploy；
7. `health_smoke`：health 或 smoke；
8. `logs_runtime_observation`：ELK、日志或运行观察；
9. `acceptance`：`business_uat | product_acceptance | operational_acceptance`。

每层状态只能是 `proven | not_proven | failed | blocked | not_applicable`。`proven` 必须有可定位
evidence 与带时区的 `observed_at`；`not_proven`、`failed`、`blocked` 必须有当前 owner 与下一动作；
`not_applicable` 必须有可审查理由，且不得虚构 owner、下一动作或 proof。测试、Reviewer、MR、merge、
deploy、health、logs 与 acceptance 只证明自己的层，永不互相替代。MR 层与 merge 层始终分离。

## 先选 applicability，再稀疏展示

从目标选择最小 profile，而不是从模板倒推工作：

- `micro_local`：只展开产物与适用验证；其余上层用一个可审查的 profile-level scope summary 合并说明；
- `reviewed_candidate`：展开实现、测试、Reviewer、commit/MR exact HEAD，本轮约定终点为可审查候选；
- `ordinary_repository`：在上述证据之外要求 merge/closeout，适用于本轮约定完整仓库交付；
- `full_runtime`：再展开 deploy、health、logs 与有明确 subtype 的 acceptance。

只渲染适用层，以及用户可能误认为已经完成、因此必须显式显示为未证明的上层。不要为简单本地修改
输出固定九行，不要要求逐层填写同义的 `not_applicable`。profile summary 可一次覆盖确定不适用的上层，
但必须给出理由，不能隐藏失败、阻塞或跳过的适用工作。

## 建立稀疏 evidence report

1. 读取本轮已明确约定的目标和验收；受管交付以当前 Issue 为记录面，纯本地任务可使用用户请求，并选择 profile。
2. 只展开适用层和容易被误判的上层，为每层选择最直接的事实源。
3. 运行 fresh command 或重新获取结果；不要复用无法确认 HEAD、版本、环境或 acceptance object 的输出。
4. 每个 proof 记录 `kind`、可定位 `ref`、`observed_at` 和相关 fact `bindings`。
5. 用一个 profile scope summary 覆盖剩余不适用层，并明确 unfinished、blockers 与 residual risks。

```yaml
evidence_report:
  objective: "Update one local document without publishing it"
  applicability_profile: micro_local
  layers:
    - layer: artifact_implementation
      status: proven
      evidence:
        - kind: file
          ref: path/to/document.md
          observed_at: 2026-08-28T10:00:00+08:00
          bindings: {head: "<40-char SHA>"}
    - layer: automated_tests
      status: not_proven
      owner: executor
      next_action: Run the focused document validator
  profile_scope:
    not_applicable_layers: [independent_reviewer, commit_mr_exact_head, merge_closeout, migration_deploy, health_smoke, logs_runtime_observation, acceptance]
    reason: The objective ends at a verified local artifact; publishing and runtime actions were not requested.
  completion_claim:
    status: incomplete
    fresh_readback: {source: local_git_and_filesystem, observed_at: 2026-08-28T10:01:00+08:00}
    unfinished_items: [automated_tests]
    blockers: []
    residual_risks: []
```

## Fresh evidence 与失效规则

- 证据必须对应当前 acceptance，而不是泛化的“测试通过”。
- 代码相关证据必须能关联当前 HEAD；HEAD 移动后重新验证受影响项。
- 截图、查询和 runtime evidence 必须能定位环境、时间和入口。
- `blocked` 不是 `pass`；环境缺失时写明解除条件。
- 没有适用证据的 acceptance 必须写理由，并交给 Reviewer 判断是否接受。
- freshness 由事实变化触发，不使用固定 TTL。HEAD、MR exact HEAD、部署版本、环境或 acceptance object
  变化时，只把依赖该事实的层降为 `not_proven` 或 `blocked`；不相关层保留原结论。
- completion claim 必须有外部 fresh readback，并明确 unfinished items、blockers 与 residual risks。

## 结论状态门

先报告真实终态，不能由 GREEN 推断更高状态：

- `implementation_candidate_green`：当前批次测试与回归通过；此状态只描述实现验证，不能代替本轮验收结论。
- `committed`：可指向当前 commit，但不能替代 MR / review。
- `mr_reviewed`：MR exact HEAD 有独立 exact-HEAD Reviewer PASS；不替代 merge/closeout。
- `delivery_complete`：仅当本轮约定的全部 acceptance 已有 fresh evidence，且适用的仓库门禁均已满足时使用；micro_local 可在验证本地产物后完成，reviewed candidate 可在 exact-HEAD PASS 后完成本轮委派。未请求的 merge/发布不是强制终点，真实 required gate 不得标为不适用。

涉及 published、draft、权限或其他生命周期 acceptance 时，证据必须显示该状态由既有受控产品路径建立；
直接数据库注入、伪造 status 或只写测试上下文只能是测试设定，不能证明该 lifecycle acceptance。

## 使用 checker

项目提供 deterministic checker 时，先让 checker 校验字段、证据缺失、stale timestamp 和 HEAD mismatch。checker 通过只表示结构满足 contract，不表示实现正确。

本 Skill 的 checker 只处理调用方提供的内存/JSON 输入，不写 repo 或目标状态：

```bash
python3 .playbook/skills/delivery-verification/scripts/evidence_contract.py validate report.json
python3 .playbook/skills/delivery-verification/scripts/evidence_contract.py render report.json
python3 .playbook/skills/delivery-verification/scripts/evidence_contract.py aggregate group.json
```

`aggregate` 的 one-to-many 结论必须消费每个 required Executor return、每个 required Reviewer 和每个
分支自己的适用证据。一个成功分支不得覆盖 missing、blocked、failed 或未消费的另一个分支。
`return_consumed` / `reviewer_consumed` 只表达消费动作，不能单独证明消费结果；值为 true 时还必须分别
提供 `return_evidence`（`result: accepted`）和 `reviewer_evidence`（`result: pass`），两者都包含可定位
`ref`、带时区的 `observed_at` 与 exact-head binding。return 使用 `bindings.head`；Reviewer 使用
`bindings.mr_exact_head`，或在没有 MR 的适用场景使用 `bindings.head`，且必须与 return 的 head 一致。

## 边界

- 不替代 QA 的探索性判断。
- 不替代独立 Formal Reviewer 的 scope、设计和风险判断。
- 不替代 final-HEAD confirmation、目标平台 close scope 或 merge gate。
- 不为了填满矩阵制造无价值命令；每条 evidence 必须支撑一个 acceptance item。
- 不自动 merge、deploy、查日志或执行 UAT；各层分别从 目标平台/pipeline、部署系统、health、ELK/logs
  和业务验收对象 fresh-read。
