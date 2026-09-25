---
title: 产品开发 XP 与可执行 BDD 契约
status: active
created: 2026-08-04
updated: 2026-08-25
source_of_truth: repo
---

# 产品开发 XP 与可执行 BDD 契约

本契约是产品开发任务的唯一 XP/BDD 规则源。它是 v0.13 Lean Core 下的可选能力，
不创建第二套 workflow，也不恢复旧 delivery lifecycle。

## `micro_direct` 预路由

先于 Goal-driven Delivery 和主要验收面分类判断 `micro_direct`。只有以下条件全部满足才准入：

- 单仓、局部、可逆，用户已明确授权，目标、范围与最小验证方式没有阻塞性歧义；
- 仅修改 CSS、布局、截断、格式或不改变业务含义的纯展示，例如日期区间输入框文字截断，只调整
  局部宽度并保持响应式；
- 不改变业务语义、API、数据、权限、安全、migration 或跨仓契约；
- 不修改跨页面或跨应用广泛复用的共享组件；
- 可用 lint、build、已有测试、组件检查或 browser smoke 的最小充分组合验证。

准入后使用 `bounded inspection → smallest edit → focused verification → concise report`。不新增 `.feature`，
也不强制 Goal Contract、Spec/Plan、Specification/Behavior RED、多 Agent 编排或独立 Reviewer。
如果已有测试或 `.feature` 自然覆盖该行为，可以复跑；不得为了 Micro 展示修复新增锁定 CSS 源码文本、
选择器写法或具体像素实现细节的 BDD steps。

任一条件不满足，或出现共享组件广泛影响、语义/API/数据/权限/安全/migration/跨仓信号、范围不清、
验证入口不充分时，必须升级到 Standard / Heavy，再按下面的主要验收面分类。
普通可修的 lint/build/test 验证失败先诊断；范围、风险及验收不变时在 Micro 路径内修复并复验。失败本身不触发重流程。
`micro_direct` 只降低实现方法的流程强度：目标仓已有 protected branch、MR、CODEOWNERS、merge、release
与生产发布规则仍然生效，不能由本预路由绕过。

## 非 Micro 任务路由

未命中 `micro_direct` 后，按主要验收面只选择一个类别：

- `product_behavior`：功能、用户可见 Bugfix 或业务行为变化。必须使用标准 `.feature`
  和 `btdd` Skill 的 BDD-led TDD+ 路径。
- `product_technical`：支撑产品的内部算法、适配器、重构或基础技术行为。使用批量 TDD，
  不强制 Gherkin。
- `non_product`：研究、文档、治理、普通运维等。不得加载完整编程实践；只保留聚焦、
  简单、及时反馈和诚实暴露问题。

分类按本次任务的主要验收面，而不是仓库类型。产品开发之外不得为了形式统一强行套用本契约。

## XP 的可观察行为

- **沟通**：Issue 保存目标、范围和不做什么；产品行为由 `.feature` 表达。语义、可行性或
  验收面冲突必须提出，不能由实现者猜测。
- **简单**：开工前只确认当前场景批次、最小设计、明确不做。额外基础设施必须指出它服务的
  当前场景；否则删除或延期。GREEN 后才做有直接收益的有限重构。
- **反馈**：使用 `Gherkin parse → Specification RED → Behavior RED → GREEN → regression/CI
  → 业务验收`。一个批次可以包含多个内聚场景和多个测试。
- **勇气**：需求不可执行、设计膨胀或代码现实与业务语义冲突时停止并返回 shaping；如实保留
  失败、未覆盖项和残余风险，不用 workaround 制造假 GREEN。

采用 Planning Game、小发布、简单设计、测试优先、持续集成、GREEN 后重构、仓库编码规范、
持续客户反馈和可持续节奏。Pair Programming、Metaphor 与强制 Collective Ownership 不作通用要求。

## `.feature` 唯一真源

- 产品行为正文只存在于目标实现仓库的标准 `.feature` 文件。Issue 只记录文件链接、AC 清单
  和当前 commit，不复制场景正文。
- 使用英文 Gherkin 关键字和中文业务文本；以合法 tags 表达 `@AC-123-01 @must @surface_api`。
- 优先使用项目已有目录；没有惯例时使用 `features/<capability>.feature`。
- Python + pytest 项目没有既有选择时使用 `pytest-bdd`；已有 `behave` 的项目保持 `behave`。
- `pytest-bdd` 项目用 `pytest_bdd_apply_tag` 消费 AC/优先级/Surface 元数据，避免把每个 AC
  注册成全局 pytest mark。
- 不使用 Markdown fenced block，也不使用 `Acceptance:`、`Priority:`、`Surface:` 等自造头部。

产品 Ready 要求 runner 能解析并收集文件；每个场景是真实用例；Given 可构造、When 是一个业务触发、
Then 是业务可观察结果；没有 TBD、占位、虚构 Examples 或实现细节。`@manual` 不是自动化豁免，
必须在 Issue 记录原因、风险和复核条件。交接前须从项目配置或 CI 找到真实 runner，在目标 runtime 和
依赖中执行预检与 collect；语法、导入、fixture、环境、plugin 或 internal error 都是 Product Ready
blocker，不能称为 RED。若 Given 声称数据已发布、存在 draft、权限已生效或其他生命周期状态，必须经
项目既有的受控产品路径（或复用该路径的项目 fixture builder）真实建立并读取；不得以直接改数据库
payload/状态或仅写上下文变量代替。没有受控路径是 blocker，不为测试临时造旁路。

产品可交付“规格完整但 steps 尚未绑定”的 `.feature`。runner 因 undefined steps 产生的
`Specification RED` 只允许停留在两条龙交接点。新开发时，全栈绑定最小 steps/fixtures 后，必须取得因
目标行为缺失产生的 `Behavior RED`，再实现 GREEN。GREEN 只表示当前实现批次的
`implementation_candidate_green`，不能称 Issue 或交付已完成。

## 接手已有实现与证据充分性

接手已有实现先复跑并审查当前测试、业务入口和断言。没有历史 RED 时明确记录
`historical RED unavailable`，不得删除实现、制造失败或冒称历史测试优先。增量变化仍按 RED→GREEN；
需要验证测试检出能力时，可在隔离、可比的未修复基线上重放当前测试，注明 `counterfactual RED`。
基线无法运行或失败仅来自环境时，不构成行为证据。根据当前风险补足验收，真实缺口不能被豁免。
此接手路径也适用于显式角色交接已有 GREEN，不要求回造 undefined steps；全新规格交接仍复核下文的
runner proof、collect 与 Specification RED。

验收以使用者、真实触发入口与可观察结果为准。mock、内部函数、REST、MCP、browser 与运行时
证据只能证明对应层，不能互相替代任务指定的入口。按风险验证失败无副作用、对象隔离、幂等及持久化
回读，不以测试数量或返回码代替业务正确性。治理文本检查只证明工件一致性，不证明 Agent 实际行为。
语法、导入、fixture、环境等失败先诊断并修复已授权范围内问题；它们不是 RED，也不自动成为停止点。
只有真实外部依赖、授权或未决业务选择阻止继续时报告相应阻塞，继续无依赖工作。

## 交付状态用语

不新增表单或生命周期，只约束结论用语：

- `implementation_candidate_green`：当前工作树的场景批次和回归通过；此状态仅证明当前实现批次，不替代本轮终点。
- `committed`：变更已提交，可报告准确 commit；仍不是交付完成。
- `mr_reviewed`：MR 的 exact HEAD 已获得独立 Reviewer PASS；仍须由主流程处理 merge/close scope。
- `delivery_complete`：本轮约定的 acceptance 已有 fresh evidence，且适用的仓库门已满足；按 delivery-verification 的 applicability 区分本地、reviewed candidate 与完整仓库交付，不强制未请求阶段。

不得用“测试通过”“GREEN”或“实现完成”替代更高一级状态；缺少条件时如实报告当前状态与下一门。

## 一条龙

同一个 owner 从业务场景、实现到验收直接驾驶完成：新开发写 `.feature`、取得 RED（已有实现按接手路径）、确认最小设计与
明确不做、实现 GREEN、运行回归并提交同一个 MR。不得生成 handoff、双签、owner 切换或额外
receipt；最终仍接受 exact-HEAD 独立 Reviewer。

## 两条龙

两条龙必须显式选择，仍只使用一个 Issue、一个 accountable assignee 和一个主 MR。产品验收角色
先写并校验 `.feature`，然后只交付以下轻量信息：

### Discovery 激活与跨仓传递

`product_behavior + role-relay` 在离开 Discovery 前必须由 governing Issue 显式记录二选一：

- `acceptance_continuity: opt_in_dogfood`：申请进入 #278 受控观测；
- `acceptance_continuity: standard_product_return`：保持 GREEN 后返回产品验收。

缺省由编排者在当前 governing Issue/note 归一为 `standard_product_return` 后继续，不等待产品确认，
不得计入 dogfood，也不得把未询问或未记录解释为产品已拒绝。
`standard_product_return` 不要求 `acceptance_authorization`，不得因 AC 分类缺失返回 Discovery；
`opt_in_dogfood` 则必须在
进入 `workflow::ready` 前完成以下交接字段及既有 AC 闭集约束。选择动作只使用当前 governing Issue/note，
不创建 receipt 或第二状态机。

跨仓交付时，governing Issue 是 continuity 决定的唯一事实源。发送给每个实现仓 Session/MR 的轻量输入
始终携带 `governing_issue`、`implementation_repositories`、已解析 continuity mode、feature/source、
AC inventory 与 `explicit_exclusions`；仅 `opt_in_dogfood` 额外要求 AC 分类、
`acceptance_authorization` 与 `return_triggers`。子仓不得根据自己的流程重新选择、猜测或扩大授权；
通用输入缺失、与 governing Issue 不一致或无法 fresh-read 时，必须返回 governing Issue 的 Discovery，
不能继续实现后再同步寻找产品补齐。标准返回缺少 opt-in 专属字段不是 blocker。

```yaml
product_to_fullstack:
  governing_issue:
  implementation_repositories: []
  feature_path:
  source_commit:
  acceptance_ids: []
  explicit_exclusions: []
  acceptance_continuity: opt_in_dogfood | standard_product_return
  acceptance_authorization:
    objective_evidence:                   # 自动或人工执行均可，但结果可由既定标准唯一判断
      - acceptance_id:
        evidence_entry:
    product_judgment:                     # 主观体验、业务取舍或客户承诺等产品裁量
      - acceptance_id:
        decision_owner:
        availability_window:
    return_triggers:
      - feature_or_acceptance_changed
      - evidence_does_not_match_expectation
      - new_business_choice_or_scope
      - acceptance_sufficiency_unclear
  runner_proof:
    discovered_from:   # 项目配置、测试脚本或 CI
    executable:
    runtime:
    preflight:
      command:
      observed_result:
  specification_red:
    collect_command:
    collected_scenarios:
    command:
    expected_failure: undefined_steps_only
    observed_result:
```

只有 `.feature` 已被真实 runner 解析/收集，且运行失败仅为 undefined steps 时，上述
`Specification RED` 才成立。全栈接手前必须从 exact `source_commit` 解析并复核 `feature_path` 与
`acceptance_ids`，不能只检查 SHA 字段非空；全新规格交接随后独立重放 `runner_proof`、collect
和 Specification RED；已有实现按接手路径独立复验。任一项不成立即 fail closed，先修复 Product Ready，而不是进入实现。全栈不得
自行改变业务语义；需要改 `.feature` 时退回产品确认。使用 Supervisor–Executor 时，Supervisor 在派发
Executor 前完成同一只读准入检查。

`acceptance_continuity` 只在显式 `opt_in_dogfood` 时启用连续推进。`standard_product_return` 或
未显式 opt-in、已归一后的缺省 mode 保持现行路径：GREEN 后返回产品验收且不要求授权分类。只有 opt-in 出现未知 mode、AC 未恰好
分类一次或必要授权字段不完整时才阻塞 Ready；不得从上下文推断授权，并明确记录未进入 dogfood。
仅 opt-in 的精确分类是闭集约束：两类 AC ID 的并集必须恰好等于 `acceptance_ids`；两个列表之间和各自内部
均不得重复，也不得包含未声明 AC；任一不满足即授权无效。
`explicit_exclusions` 是必填范围边界，接手与 GREEN 后连续推进前都必须对照 exact `source_commit`
复核并保持不变；字段缺失、内容无法判断或实现越界时返回产品确认。
AC 分类按“结果是否能由既定标准唯一判断”，不按“是否自动化”；人工操作不等于产品裁量：人工浏览器
或运行时操作如果有唯一可判断的预期，仍属于 `objective_evidence`。`product_judgment` 必须在开工前
给出 `decision_owner` 与 `availability_window`，缺失即为 Product Ready blocker。

显式 opt-in 后，只有所有本批 AC 均为 `objective_evidence`、`.feature` / AC / 业务语义未变化、fresh
evidence 与预期一致且未命中任一 `return_triggers` 时，全栈才可在 GREEN 后连续完成业务验收证据并
进入现行 exact-HEAD 独立 Reviewer gate，不再同步寻找产品人员。任一 AC 为 `product_judgment`，或
发生语义变化、证据歧义、新业务选择、范围扩张、验收充分性不清时，仍须 GREEN 后返回产品验收。
产品预授权、验收证据执行、独立 Reviewer 与 merge 执行是四项独立责任，任何一项都不能替代其它项。

opt-in dogfood 在当前 Issue/MR 留下最小观测证据，不创建新状态机：

```yaml
acceptance_continuity_observation:
  observed_at:
  continuous_completion: true | false
  unexpected_product_returns: 0
  context_resume_count: 0
  return_trigger:
  evidence_refs: []
```

这些字段只记录可回读事实，不授权 merge、Release 或 cross-repo upgrade。发布后的真实下游案例、异步
产品抽查和延迟回读由源仓 `bigital/ai-engineering/bigital-agent-playbook#278` 观测；本地 fixture、测试
或 installer smoke 不得冒充真实 dogfood。首版保持 opt-in，未获得后续推广结论前不得写成默认路径。

最终仍由独立 Reviewer 审查 exact MR HEAD。不得恢复双 owner、claim、lease、readiness receipt、
Runner 或 runtime JSONL。

跨仓功能由协调 Issue 维护 AC 索引；每个实现仓拥有自己可运行的 `.feature` 切片、runner 和证据。
