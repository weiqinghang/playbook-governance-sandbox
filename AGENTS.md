# Playbook entrypoint

<!-- PLAYBOOK-MANAGED:START -->
## Playbook router

GitLab Issue 与 MR 是工作项、唯一当前负责人、流程状态、review 与 release 的事实源；repo 承载业务
代码与已采纳的长期决策。先读取 `AGENTS.md`、`docs/README.md`、
`.playbook/docs/project/agent-context-protocol.md`、`.playbook/docs/project/document-governance.md`、
`.playbook/docs/project/charter.md`、`.playbook/docs/project/agent-registry.md` 和
`.playbook/docs/project/agent-orchestration.md`。不得默认读取或更新 `now.md`；当前阶段由 GitLab
Issue 与 milestone 表达。

`docs/README.md` 是目标仓可维护的文档导航，不承载 Playbook 版本事实或替代本受管区块的规则；
`.playbook/docs/project/charter.md` 可补充项目宪章。已安装版本以 `.seed-lock.json` 为准。

首次在真实用户主机接手更新后的下游，或需要 BTDD 且候选变化时，按
`.playbook/docs/project/host-skill-adoption.md` 做有界只读差异检查；同一会话同一指纹不重复提示。
全局采用由用户选择，拒绝或主机不明不阻塞项目任务；项目安装不自动写全局配置。

Standard / Heavy single-owner 只需一个 Issue 和一个 MR；不得创建或要求 profile/context/readiness、receipt、
claim/lease、runtime JSONL、lifecycle manifest 或默认成套 Spec/Plan。高风险动作必须 action-specific
fail closed，并需明确授权和 fresh readback；merge、tag、Release 与 Issue/milestone closeout 不由普通
mutation 自动授权。

每次普通 commit 的主题都必须包含当前 governing GitLab Issue IID，采用
`type[(scope)]: summary (#<iid>)`；代码、测试、Spec/Plan 与文档均适用。先从当前 Issue 回读
IID，再将完整提交信息写入文件，运行 `python3 scripts/git_workflow_guard.py --action commit
--issue <iid> --message-file <提交信息文件>`，最后以 `git commit -F <提交信息文件>` 提交。
push 前运行 `python3 scripts/git_workflow_guard.py --action push --issue <iid>`；MR 的 Issue 链接
不能代替 commit 自身的 Issue 引用。`--branch-only` 只供只读诊断。

普通修复、实验和未合并候选只进入 `CHANGELOG.md` 的 `未发布` 区，不得消耗 SemVer 或修改
`seed/version.json`、release registry、release note、推荐版本和下游升级矩阵。只有用户明确授权
“准备 vX.Y.Z release”且 exact candidate/review 已就绪时，才可在单独 release change 中推进这些
metadata；tag、GitLab Release 与下游升级须在明确授权动作集合内，一次明确请求可覆盖多项；逐动作验证不等于逐动作询问。

`micro_direct` 必须先于 Goal-driven Delivery 和 `product_behavior|product_technical|non_product` 分类判断。
仅限 CSS、布局、截断、格式或不改变业务含义的纯展示修改；还须单仓、局部、可逆、用户已授权、
目标与验证清晰，且不改变业务语义、跨页面广泛复用的共享组件、API、数据、权限、安全、migration
或跨仓契约。完整准入条件见 `.playbook/docs/project/product-development-xp-contract.md`，必须全部满足。
准入后只做 bounded inspection、最小修改、
聚焦 lint/build/已有测试/browser smoke 和简洁回报，不强制 Goal Contract、Spec/Plan、`.feature`、RED 链、
多 Agent、Issue/MR 或独立 Reviewer。Issue/MR 是否需要由目标仓规则决定；范围不清、共享组件广泛影响、
新增风险信号时必须升级；普通可修验证失败在范围、风险和验收不变时原路修复。不得绕过 protected branch、merge、release 或生产门禁。

无论 single-owner（一条龙）还是显式 Supervisor–Executor（两条龙），需求澄清与打磨都以
`Discovery` 为主要观察面，并保持 `workflow::backlog +` 唯一真实 `backlog::*`；打磨完成且获准实现后，
同一 Issue 以 `backlog::ready-for-dev + workflow::ready` 进入交付，从实现到完成以 `Delivery` 为主要
观察面并推进唯一 `workflow::*`。Board 只是同一 Issue 标签事实的阶段视图；聊天结论、Goal Contract、
Pair receipt 或本地任务状态不得替代标签迁移。`sizing::micro` 可压缩打磨，但不得带着阻塞性需求未决项
绕过 `Discovery`。

`product_behavior + role-relay` 必须在离开 `Discovery` 前由 governing Issue 显式记录
`acceptance_continuity: opt_in_dogfood|standard_product_return`。缺省等价于
`standard_product_return`，由编排者在当前 Issue/note 归一记录后即可继续，不等待产品确认；GREEN 后
返回产品验收且不得计入 dogfood。只有选择 `opt_in_dogfood` 时，exact
feature/source、AC 闭集分类、排除项、产品裁量 owner/window 与 return triggers 未完整前不得进入
`workflow::ready`。跨仓实现必须携带 governing Issue 中已解析的同一 mode，不能由子仓 Session 猜测或
重建；标准返回不得因缺少 opt-in 专属 AC 分类而被阻塞。

`.seed-lock.json` 是下游已安装 Playbook 版本的唯一事实；不要在本文件复制版本、tag 或 install 状态。
未命中 `micro_direct` 后再按主要验收面分类：`product_behavior` 加载 BDD-led TDD+ 和 `.feature`，`product_technical` 加载批量
TDD，`non_product` 不加载完整编程实践，只保留聚焦、简单、及时反馈和诚实暴露问题。Skill 与完整契约
常驻可发现但仅在前两类任务按需读取；不得因仓库类型或 Skill 已安装而强行触发。此段由 Playbook升级器
维护；仓库业务信息与本地规则只写在标记外。
<!-- PLAYBOOK-MANAGED:END -->

## Repository-local conventions

在此记录本仓的业务目标、开发基线、交付边界、运行环境和其他只属于本仓的约束。
