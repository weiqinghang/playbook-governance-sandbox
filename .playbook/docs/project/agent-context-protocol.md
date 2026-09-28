---
title: Agent 上下文供给协议
status: active
created: 2026-08-01
updated: 2026-08-28
source_of_truth: repo
---

# Agent 上下文供给协议

本文是项目内 Focus Contract 与事实确认先于行动门的 canonical owner。普通 single-owner、显式
Supervisor–Executor、AGENTS 入口和受管 seed 都复用本文，不另行复制一套事实门或状态机。

## Focus Contract

新任务、目标实质变化或用户纠偏后，先建立最多四行的 Focus Contract：

```text
目标结果：<用户真正要得到的结果>
主验收面：<什么事实或产物决定成功>
模式：discussion | decision | execution
明确排除项：<本轮不做什么>
```

目标、授权和验收已经清晰时可内部维护，不要求用户重复确认。只有发生用户纠偏、与旧目标冲突、
阻塞性未知或会改变行动的重要推断时才显式读回；Focus Contract 不是问卷。新 Contract 与当前控制
冲突时，先替换冲突的旧目标或计划，再继续；旧计划、Issue、里程碑或技术代理目标不得静默覆盖新的
主验收面。

## 事实确认先于行动

进入实现前，确认权威事实源，以及会改变范围、授权或实现路径的关键事实。用户明确要求“先核实”，
或诊断结论会改变范围、授权或实现路径时，先给出事实结论、支持证据和行动影响。事实结论只使用
`成立 | 不成立 | 暂不确定`；不得把假设、旧快照或技术便利写成已确认。

当目标、主验收面、范围或授权存在阻塞性未知时，只暂停依赖该未知的动作，继续已授权的独立工作。
`暂不确定` 须指出缺失证据。只读核实，以及已授权范围内、隔离可逆、不触碰真实数据/权限/外部系统的
最小复现和技术实验，均可用于消除实现未知；技术未知本身不要求用户代为诊断。
目标、范围或授权实质变化后，仅相关旧 dispatch 失效，先修正其边界再恢复副作用。

本门是窄触发的行动门，不是重型流程。discussion 模式不得创建 Issue 或代码；清晰、局部、低风险的
execution 直接采用最小必要事实，不强制完整事实矩阵、Spec 或 Plan，也不新增第二套 workflow。
Micro Direct 仍先按其既有准入条件判定并保持紧凑路径；本门不会把它自动升级为 Standard / Heavy。

显式 Supervisor–Executor 中，Supervisor 必须在 topology/DAG 选择、Executor 创建与任何 Executor
side effects 前执行同一门；Executor 只消费仍有效的 dispatch。普通 single-owner 在自己的第一项实现
副作用前复用同一规则，不增加 handoff 或第二 owner。

默认只读取完成当前动作所需的最小信息：GitLab Issue description/note 中的 goal、scope、
acceptance、唯一 assignee 与 `workflow::*`，以及关联 MR 的当前 HEAD、diff、测试和 review。
先搜索和缩小范围，再读取直接依赖的局部内容；只有依赖不清、测试失败或多次尝试失败时才扩展。

上下文升级顺序为：Issue/MR 摘要 -> 相关结构 -> 局部实现 -> 必要的完整文件。每次升级简短说明
触发原因与新增范围即可。不要默认 full dump，也不要读取或更新 `now.md`。

复杂且长期的产品或架构决定可在 Issue/MR 中确认，并按需沉淀为一份紧凑 ADR。普通工作不得默认
创建或要求 Spec、Plan、Intent/Worker/Goal-Loop packet、projection、activation、receipt、claim、
lease 或 runtime JSONL。Issue/MR 是执行事实，note 是可追溯沟通，不产生平行状态机。

## 授权继承与连续推进

一次明确请求可以授权一个明确动作集合，授权随本任务及有效委派继承。每次行动仍核对对象、范围、
当前事实、风险和适用前置门；这些 action-specific 检查不是重新询问。已有明确授权时，普通参数、
内部顺序、方法选择、隔离实验、验证修复和等待继续均由当前控制器处理。
只有授权缺失/被撤回、目标变化、风险或外部副作用扩张、真实业务选择时才提出决定；完成所有不依赖该
决定的工作后，提供具体候选、证据和解除条件。merge/tag/Release 等不可由普通 commit/push 推断授权。
内部 DAG 重排在产出、验收、边界及并行预算不扩张时可复用原授权，更新结构和引用仍必须一致。

连续两轮没有新增证据、缩小不确定性或验收进展时，先诊断并改变方法、上下文或模型投入，再继续。
次数是干预信号，不是机械第三次换型号、第四次必停。权限和目标问题先修边界，模型不能替代授权。
Reviewer pending 与观察窗口结束不等于 timeout/blocked；继续等待同一实例，使用现有 Reviewer Wait Policy。
