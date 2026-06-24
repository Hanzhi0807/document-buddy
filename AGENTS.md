# Agent 接力规则

这个仓库会被多个 agent 轮流继续开发。每个 agent 开始工作前必须先阅读：

- `README.md`
- `docs/agent-handoff.md`
- 与当前任务相关的 `docs/*.md`

每个 agent 完成工作后，必须在最终回复前更新 `docs/agent-handoff.md`，不需要等待用户再次提醒。

更新交接文档时至少写清楚：

- 本轮做了什么。
- 改了哪些关键文件。
- 跑了哪些验证命令，结果如何。
- 当前还没做什么。
- 下一位 agent 应该从哪里继续。
- 如果相关 commit 已经生成，写上 commit hash；如果当前提交尚未生成，最终回复里必须补充最新 hash。

项目方向提醒：

- 产品名：文档搭子 / Document Buddy。
- 正式目标：把团队可见的 wiki 做到飞书知识库或飞书云文档里。
- 当前形态：无服务端 MCP 工具包，不做 SaaS、不做 webhook、不保存飞书 token、不保存 LLM API key。
- 本地 `WORK_MEMORY_DATA_DIR` 只作为缓存、索引、冲突状态和离线 fallback。
- 回答项目问题前必须调用 `query_project_wiki` 或 `get_cited_context`，没有 citations 就不能编答案。