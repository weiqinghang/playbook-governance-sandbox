---
name: btdd
description: Use for approved non-Micro product implementation or takeover verification. Route product_behavior through executable Gherkin and BDD-led TDD+; route product_technical through coherent batch TDD. Exclude micro_direct, non_product research, docs, governance, ordinary operations and throwaway exploration; use characterization for untrusted legacy behavior.
---

# BDD-led TDD+

以一个内聚业务批次取得真实反馈，不按文件或测试数量机械切循环。本 Skill 只约束实现与验证方法，
不选择 workflow、owner 或扩大交付终点。先读取项目的
`.playbook/docs/project/product-development-xp-contract.md`；不存在时使用下面的最小规则，
说明项目契约未安装并继续，不把缺失本身当阻塞。

## 选择路径

- `micro_direct`：停止加载本 Skill。入口必须已确认全部准入条件满足；日期区间文字截断等局部
  展示修复使用最小修改和 lint/build/已有测试/browser smoke，不新增 `.feature` 或锁定源码文本、
  选择器、像素的 steps。风险或验收发生变化才升级；普通可修的验证失败原路修复。
- `product_behavior`：功能、用户可见 Bugfix 或业务行为变化。标准 `.feature` 是业务正文。
- `product_technical`：内部技术行为，以多个相关测试组成批量 TDD，不强制 Gherkin。
- `non_product`：停止加载本 Skill。文档、治理规则的文本检查只证明工件一致性，不能声称验证了 Agent 行为。

不可信的遗留行为先做 characterization；有 `legacy-characterization-testing` 时使用它。
一条龙由同一个 owner 完成场景、实现与验收，不创建 handoff。只有已显式选择两条龙时读取
[角色接力](references/role-relay.md)，消费既有输入，不在普通开发中引入 dogfood 分类或观测字段。

## 开工前

明确当前场景或测试批次、最小设计、明确不做的范围即可。额外基础设施必须服务当前场景，
否则删除或延期。只有突破已授权范围或引入未决定的业务语义才返回 shaping；范围内设计与普通修复继续。

先确定验收的 **使用者、触发入口、可观察结果**。MCP-only 任务须从 MCP 入口完成要求的操作与读取；
REST、内部函数、mock 或日志只能证明各自覆盖的层。对当前风险补齐拒绝后的无副作用、跨对象隔离、
幂等重试或持久化回读；不为无关风险套完整矩阵，不以返回码或测试数代替业务结果。
生命周期敏感 Given 必须经既有受控产品路径或复用该路径的 fixture builder 真实建立并读取；
不得直接改数据库状态或只写上下文变量制造 published/draft/permission 证据。

## 新增或修改行为

1. `product_behavior` 找到项目标准 `.feature` 和真实 BDD runner；从项目配置、脚本或 CI 取得
   runner proof，在目标 runtime 预检、collect。Python + pytest 无既有 BDD 框架时用 `pytest-bdd`；
   已有 `behave` 时保留。`product_technical` 直接选择内聚技术测试批次。
2. 为本批目标行为加入最小 steps/fixtures 或技术测试并运行。**Behavior RED** 必须因目标行为缺失
   而失败；语法、导入、fixture、plugin、环境或 internal error 都不是行为 RED。先诊断并修复范围内
   问题，再重跑；只有真实外部依赖阻止恢复时报告阻塞。
3. **Specification RED** 仅指规格可解析且仅因 undefined steps 失败，可用于显式产品→全栈交接；
   接手者独立重放后绑定 steps，再取 Behavior RED。一条龙无需停在交接点。
4. 一次实现使本批 GREEN 的最小代码，运行相关回归。GREEN 后只做有当前收益的重构，改后复跑。
   普通预检、RED、GREEN 不要求分别发起一次用户确认。

## 接手已有实现或已有 GREEN

先复跑既有测试并检查断言、业务入口和覆盖范围。有效历史 RED 可引用其来源；没有则如实写
“historical RED unavailable”，不把当前 GREEN 回填为先前 RED，不删除实现或故意破坏工作树补仪式。
新增或修复的行为仍对增量执行上面的 RED→GREEN。

如果需要证明测试确实能检出目标缺陷，且旧基线可运行、成本与风险合适，在隔离临时目录/工作树将
当前测试应用于未修复基线，验证失败来自目标行为。记录为 **counterfactual RED**，不冒称历史测试优先。
旧依赖、导入或 fixture 失败不是反事实成功。不可比或不可行时记录限制，用当前入口验证与独立审阅
补强；高风险验收仍有缺口时明确未通过，不能用缺少历史证据豁免当前正确性要求。

## 证据与完成

在现有 Issue/MR 或任务结果给出：测试/feature 与代码来源、批次及验收入口、执行命令、观察结果、
失败原因、GREEN 与相关回归、未覆盖项。接手时区分 historical / counterfactual / unavailable RED。
有必要时用结构化证据；不默认新建 YAML、日志或逐测试记录。引用既有输出，不复制原始敏感数据。

GREEN 只证明 `implementation_candidate_green`。继续完成用户约定的业务验收与适用仓库门，包括
所要求的 exact-HEAD 独立 Reviewer；角色接力按其已解析模式处理。测试、审阅、merge、发布、health
与业务 UAT 各自证明不同层，按当前交付契约判定完成，不自动增加未请求阶段。
