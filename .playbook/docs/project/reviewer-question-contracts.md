---
title: Reviewer 默认命题核验契约
status: active
created: 2026-09-23
updated: 2026-09-23
source_of_truth: repo
contract_version: reviewer-questions/v1
---

# Reviewer 默认命题核验契约

本契约是默认 Reviewer 的有界核验方法，无 Jev、翻译服务或额外 API 依赖。命题结果只辅助
Reviewer 判断；不能自动生成 finding、正式 `review pass` 或新增人工审批。Reviewer 仍须开放式检查
调用链、未知缺陷及与命题相冲突的原始证据。

## 共用输入与结果

每个问题至少绑定 `question_contract_version=reviewer-questions/v1`、`question_type`、当前候选
`head_sha`、对象与阶段、待核对的原主张、已提供原始材料的可定位引用、材料范围与未检查范围。
规则或验收引用只在该依据路径适用且已提供时绑定；观察或运行记录若缺失，明确列出缺口，
不能伪造引用或把未执行写成语义结论。
实现者摘要、工具结论和旧 HEAD 的报告只能作线索，不能代替原文。规则有修订时同时记录适用版本
与生效阶段；不能用已被替代的规则裁定新阶段，也不能把新规则倒灌到旧历史。改变 HEAD、阶段、
规则或证据集合后，相关结论必须重新核对。

语义结果为 `supported`（给定原始材料直接支持该命题）、`contradicted`（给定材料直接反证）、
`insufficient_evidence`（关键材料缺失或尚不能区分）。它只回答写明的对象、阶段和材料范围；
局部 `insufficient_evidence` 不证明全仓不存在，`contradicted` 不证明别处没有更窄的真实缺陷。
另记执行状态 `completed`、`not_checked`、`timeout` 或 `source_error`；后三种没有语义结果，
不能伪装成 `insufficient_evidence`。可选辅助未配置时记录辅助未运行，Reviewer 仍直接查原始材料。
所有输出给出来源、推理边界及仍需补的证据。

## 1. 主张—证据 `claim_evidence`

输入是一句可判真假的主张、它所指的对象/版本/阶段和至少一处原始材料引用。先核对证据是否属于
该对象及阶段，再判断材料是否直接蕴含或反证原主张；引用可定位不等于内容支持。阶段错位、
压缩体与解压上限、消息与 manifest 的不同载体分别判断，不把一个载体的观察外推成全局事实。

| 合成示例与可定位材料 | 结果 | 边界 |
| --- | --- | --- |
| 主张“请求已 POSTED”；唯一日志只记录同一请求 `RECEIVED`，且日志定义明确两者为不同状态 | `insufficient_evidence` | 已收到不证明已提交，也不直接证明永未提交；需 POSTED 事件或状态读回 |
| 主张“该消息没有证据引用”；完整边界消息原文含有效的 `task://...` 引用 | `contradicted` | 撤回消息缺引用的主张；manifest 的其他缺陷须另判 |
| 主张“解压后大小超过上限”；同 HEAD 的实测显示解压后 12 MiB、适用上限 10 MiB | `supported` | 只证明这次输入违反该上限，不能推出所有压缩请求失败 |

## 2. 验收—测试 `acceptance_test`

输入是带适用阶段与来源的验收条款、测试源码的具体断言，以及已提供的当前 HEAD 运行记录；
缺运行记录时明确记 `not_checked`。分别输出
`assertion_coverage`（断言是否检查该验收）和 `run_observation`（该目标断言是否在当前候选
真实执行**且通过**），已核对的部分采用上述三态。失败记录使 `run_observation=contradicted`，
并保留失败详情；结果无法辨认时为 `insufficient_evidence`。未运行则执行状态为 `not_checked`，
没有运行语义结果，不得称验证通过。
合并前源码测试与部署后 UAT 是两个验收面；旧规则上的 PASS 不能替代现行规则的检查。

| 合成示例与可定位材料 | `assertion_coverage` / `run_observation` | 边界 |
| --- | --- | --- |
| 验收要求 viewer 不得下载财务导出；测试以 viewer 会话调用财务导出入口 `GET /finance/export` 并断言 403，当前 HEAD 测试报告该断言通过 | `supported` / `supported` | 证明该候选这条入口的测试，不能外推到其他导出路径 |
| 同一断言在当前 HEAD 已执行，却实际得到 200 而失败 | `supported` / `contradicted` | 测试覆盖目标，但本次验证失败；保留失败报告，不能写成通过 |
| 验收要求 viewer 不得下载财务导出；只看到测试片段断言响应为 403，未提供构造会话与请求路由的代码，当前 HEAD 测试报告该断言通过 | `insufficient_evidence` / `supported` | 已运行且通过该断言，但不能确认它用了 viewer 会话或财务导出入口；补齐调用与准备代码再裁定覆盖 |
| 测试以 viewer 会话调用 `GET /finance/export` 并断言 403，但当前 HEAD 没有该测试的执行记录 | `supported` / 无结果 | 源码存在不能写“验证通过”；记录 `not_checked` 并运行或取执行证据 |
| 验收要求部署后租户隔离；唯一测试只断言本地 mock 返回 200，当前 HEAD 的测试记录显示该断言通过 | `contradicted` / `supported` | 运行结果只支持这条 mock 断言；它不检查目标验收，也不是部署后 UAT |

## 3. Finding—依据 `finding_basis`

输入是原 finding 的准确主张、适用规则及版本，或可复现源码/行为与具体影响。依次判断
**原主张、缺陷事实、组件责任、影响与严重度**。缺少逐字规则不能自动否决已复现的 Bug；
原主张错了也必须检查同一材料是否证明更窄的缺陷。责任合同或定级证据不足时，分别标为未定，
不能把已证实的缺陷整体写成待核查。只有缺陷事实本身缺关键材料时才写待核查。

| 合成示例与可定位材料 | 对原主张/缺陷的结果 | 处置 |
| --- | --- | --- |
| 原称“manifest 缺字段导致证据丢失”；适用契约只要求完整边界消息带引用，实际消息有引用 | `contradicted` / 无已证缺陷 | 撤回原 finding；不能继续归责 validator 或沿用 P1 |
| 同一契约下完整边界消息实际缺引用，manifest 字段非强制，未提供 manifest 到消息的因果链 | 原归因 `insufficient_evidence` / 消息违规 `supported` | 撤回无依据的归因、保留较窄真缺陷；消息发送者有内容责任，validator 是否独自把关须另核；影响和等级按证据界定 |
| 跨租户财务导出能由普通请求重现，返回另一租户付款行，虽没有逐字定级表 | 泄露缺陷 `supported` | 保留严重真实缺陷；按敏感数据暴露证据定级，不因无逐字等级规则降成待核查 |
| 只有“上传没有限流”的旧评论，没有上传路由、入口配置或复现 | `insufficient_evidence` | 原 P1 不成立；列明需检查的入口与配置，不冒称已证缺陷 |
| 唯一依据是旧版规则，而当前阶段的有效规则已明确替代它 | `contradicted` | 撤回基于旧规则的违规主张；若另有复现 Bug，单独判断 |

三类命题和执行状态均不能代替最终 finding 裁定。输出前按
`.playbook/docs/project/reviewer-checklists.md` 核对原 finding 集合、真实缺陷、责任、严重度和总评
是否相容；正式 MR comment 仍只写一次并绑定 exact HEAD。
