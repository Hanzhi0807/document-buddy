# 文档搭子 Wiki 规则

这份规则是给 MCP host 里的 AI 看，也是给普通用户和管理员看的。它刻意保持轻量：不要求新服务、不要求专门 UI，也不要求文档搭子保存任何 LLM API key。

## 核心原则

- 原始资料不改写：飞书文档、会议纪要、聊天摘录、PDF 文本等作为来源保存或保留链接。
- wiki 是工作副本：AI 可以维护 wiki 页面，但回答时只能引用 wiki 里已经确认的内容。
- 引用必须可追溯：wiki 条目应尽量保留来源标题、原始链接和行号提示。
- 冲突不硬猜：预算、时间、承诺对象等冲突进入 `open-questions.md`。
- 页面要短：优先服务白领日常查询、会前准备、周报、跟进邮件。

## 标准页面

- `index.md`：项目入口、页面目录、回答规则、资料数量、冲突数量。
- `overview.md`：当前对项目的简短理解。
- `requirements.md`：需求、目标、关注点、偏好。
- `risks.md`：风险、阻塞、不确定事项、预算/法务/排期问题。
- `commitments.md`：承诺、待办、负责人、时间点。
- `decisions.md`：已经确认的决定。
- `people.md`：相关人物、团队、客户角色。
- `sources.md`：资料清单，优先保存飞书文档或知识库链接。
- `open-questions.md`：需要用户确认的问题和冲突。
- `log.md`：维护日志，新记录在前。

## AI 维护方式

1. 读取新资料。
2. 调用 `ingest_text` 先做轻量自动整理。
3. 如需更精细整理，调用 `get_wiki_maintenance_contract` 查看页面契约。
4. 读取相关 wiki 页面。
5. 只在有证据时调用 `upsert_wiki_page` 更新页面。
6. 如发现冲突，保留在 `open-questions.md`，不要自行裁决。

## 回答方式

回答任何项目问题前，必须调用 `query_project_wiki` 或 `get_cited_context`。工具会用轻量 BM25 从 wiki 页面和行里找证据，但回答仍然只能使用返回的 citations。

- 有 citations：只基于 citations 回答，并保留引用链接。
- 没有 citations：说明 wiki 没有证据，不要补编。
- 用户追问细节：继续从 wiki 取证据，而不是凭上下文猜。
