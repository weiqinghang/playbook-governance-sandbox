---
title: 实际宿主 Skill 差异与采用
status: active
created: 2026-09-06
updated: 2026-09-06
source_of_truth: repo
---

# 实际宿主采用 BTDD

Playbook 是 BTDD 唯一维护源；项目 `.playbook/skills/btdd`、`.agents/skills/btdd` 与用户全局目录均为
安装投影。修复回到 Playbook，不在个人技能仓另建 BTDD 源码。项目安装可能在 CI、服务器或另一位
执行者的机器上完成，因此 seed 安装器只提示后续检查，默认不读取或修改安装机器的全局配置。

## 在真实工作主机检查

用户首次接手已升级仓库，或任务确需 BTDD 且项目候选发生变化时，在实际使用主机做一次有界检查。
当前会话无法确定是否为用户工作主机时，只说明可在使用主机执行下列命令，不阻塞项目任务。
没有 `.seed-lock.json` 的源仓工作树不使用此下游采用入口。

```bash
python3 .playbook/scripts/host_adoption.py check --project . \
  --global-root "$HOME/.codex/skills" --also-root "$HOME/.agents/skills" \
  --instruction "$HOME/.codex/AGENTS.md" --instruction ./AGENTS.md
```

这是 Codex 的路径示例；若设有 `CODEX_HOME` 或宿主明确提供其他路径，使用实际路径。脚本默认目标是
`${CODEX_HOME:-$HOME/.codex}/skills`，不猜测宿主加载优先级。按需用多个 `--also-root` 报告同名和旧名
入口，用多个 `--instruction` 提供本次相关指令来源。只读取指定 Skill 和文件；不扫描插件缓存、凭据、
聊天或全部配置。存在软链接时报告路径问题，先核实其维护者，不自动跟随或解链。

检查输出候选版本、source commit、完整文件哈希、全局状态、其他副本和本次 `fingerprint`。
`.seed-lock.json` 必须与项目两份 BTDD 投影的完整清单及哈希一致。它提供本地安装 provenance，
**不等于这次独立查询了远端 annotated tag / Release，也不能证明宿主已发现该 Skill**。

- `absent`：可选择初装。
- `matching` / `matching_unmanaged`：字节匹配，无需覆盖；后者不冒称已受管。
- `managed_upgrade_available`：可选择前向更新。
- `unmanaged_or_modified`：展示具体差异和维护归属，只有用户明确选择替换才使用替换参数并保留原件。
- `same_version_conflict` / `downgrade_blocked`：不写入；核对版本或选择正确来源，不用覆盖参数绕过。
- 其他副本、旧名并存或路径异常：先定位真实宿主入口和所有者，不自动删除、迁移或改链接。

## 差异不等于冲突

当前 Agent 比较与本次任务相关的规则；脚本只报告指纹，不推断语义。沿用 Dream 指令审计的
`authority_conflict / scope_conflict / workflow_conflict / acceptance_conflict` 分析维度，区分
文本风险与已在执行中表现的问题。记录来源路径/版本、宿主实际指令层级与适用范围、冲突片段的脱敏
摘要、影响和对应维护者。主机没有 Dream 也可完成这项只读判断，不强制安装或创建 Dream 记录。

个人 AGENTS 与个人 Skill 的修改回到其维护源；Playbook 规则回到 Playbook；第三方插件使用受支持
设置或上游修复。项目规则不能因安装路径自动压过宿主或用户指令，全局规则也不能自授跨仓写权限。
发现 BTDD 版本差异时按上述状态给出具体选择；同一会话的相同候选与宿主文件指纹只提示一次。
用户拒绝或暂缓就继续项目任务；不默认持久写入跨会话提示账本，不将宿主信息写进 `.seed-lock.json`。

## 用户选择后的安装

复用当前任务中仍有效、指向这个真实主机与目标 Skill 的安装授权；尚未授权时先展示差异再询问。
安装时保留 check 中所有项目、目标、额外 root 和 instruction 参数，并把返回的 fingerprint 传入：

```bash
python3 .playbook/scripts/host_adoption.py install --project . \
  --global-root "$HOME/.codex/skills" --also-root "$HOME/.agents/skills" \
  --instruction "$HOME/.codex/AGENTS.md" --instruction ./AGENTS.md \
  --user-host --expected '<check 返回的 fingerprint>'
```

仅用户明确选择替换未受管/修改过副本时追加 `--replace-unmanaged`。`--user-host` 是调用者对真实
目标的明确声明，脚本无法技术判定机器属于谁；fingerprint 是防止检查后变化，不是用户授权凭证。
命令在临时目录准备、并发锁内复查、保留原件后替换并完整回读；失败恢复原件。备份位于所选 skills
目录的相邻 `playbook-skill-backups`，不放入 Skill 发现根目录，不自动清理。外部非协作写入导致恢复
位置被占用时保留原件并报告位置，不覆盖新出现内容；遗留锁由人核实，不能机械删除。

安装只改选定全局 BTDD，不改全局 AGENTS、项目文件或其他 Skills。文件通过回读后仍须由宿主重新
加载/新会话确认发现状态；当前会话旧 Skill 不会因为磁盘更新就自动换版。普通 seed 参数
`--update-global-skill` 仍仅用于既有 Supervisor–Executor，不被此入口扩义。
