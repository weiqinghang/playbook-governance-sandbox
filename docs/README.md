# 项目文档入口

本文件由目标仓维护，用于组织项目的产品、架构与运行文档。Playbook 首次安装只在文件缺失时创建它；后续升级保留项目内容。

## Playbook 协作入口

- `AGENTS.md` 的受管区块提供任务路由与行动边界；项目补充规则写在标记外。
- `.playbook/docs/project/` 保存已安装的协作协议；需要时按 `AGENTS.md` 的最小入口读取。
- `.seed-lock.json` 记录当前已安装的 Playbook 版本和文件摘要；不要在本页复制版本号。
- `.playbook/scripts/audit_seed_installation.py` 可只读核对受管文件，并列出本页等项目保留文件的差异。

在此补充本项目的文档导航。项目说明可以修改；涉及 Playbook 规则变更时，核对 `AGENTS.md` 与已安装的协议文件。
