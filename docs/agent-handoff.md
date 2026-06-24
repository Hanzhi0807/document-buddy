# Agent 交接文档

这份文档是文档搭子项目的接力记录。每个 agent 做完工作以后，都必须更新本文件，不需要用户再次提示。

## 给下一位 agent 的一句话

当前核心方向已经明确：文档搭子不是单纯本地 wiki，而是一个无服务端 MCP 工具包，负责把资料整理成可引用的项目 wiki，并把用户可见层同步到飞书知识库或飞书云文档。

晚上继续时，优先做真实飞书接入验证：用飞书官方 MCP / Lark CLI 读取真实飞书资料，调用文档搭子 `ingest_text`，再用 `get_feishu_wiki_sync_plan` 把 wiki 页面写回飞书知识库或云文档。

## 当前产品判断

- 中文名：文档搭子。
- 英文名：Document Buddy。
- GitHub repo：`ivyzhi0807/document-buddy`。
- 形态：无服务端 MCP 工具包。
- 不是：飞书机器人 SaaS、本地 Web UI、公网 webhook 服务、LLM API 托管服务。
- LLM 来源：用户自己的 AI 客户端或企业模型配置。
- 飞书读写：优先交给飞书官方 MCP、Lark CLI 或未来 Docs add-on。
- 文档搭子职责：整理 wiki、维护页面结构、用轻量 BM25 检索 citations、检测冲突、生成飞书可见层同步清单。

## 必须遵守的回答规则

- 回答任何项目问题前，必须调用 `query_project_wiki` 或 `get_cited_context`。
- 只能使用工具返回的 `citations` 作答。
- 没有 `citations` 时，必须说 wiki 没有证据，不能补编。
- 发现预算、时间、承诺事项等冲突时，写入 `open-questions` 或 review item，让用户确认。

## 数据位置判断

正式目标：

```text
飞书知识库 / 飞书云文档 = 用户和团队看见的 wiki
```

本地目录：

```text
WORK_MEMORY_DATA_DIR = 工具运行状态、缓存、索引、冲突、离线 fallback
```

本地不应该被描述成正式用户入口。正式接飞书后，wiki 页面应优先写入飞书知识库或云文档。

## 当前 MCP 工具

当前有 15 个工具：

- `create_project_memory`
- `list_project_memories`
- `get_project_index`
- `get_wiki_maintenance_contract`
- `ingest_text`
- `upsert_wiki_page`
- `list_wiki_pages`
- `read_wiki_page`
- `get_feishu_wiki_sync_plan`
- `get_cited_context`
- `query_project_wiki`
- `lint_project_wiki`
- `detect_conflicts`
- `list_review_items`
- `resolve_conflict`

其中 `get_feishu_wiki_sync_plan` 是飞书可见层的关键工具：它不直接调用飞书 API，而是把当前 wiki 页面打包成飞书知识库/云文档的创建或更新清单。AI 客户端拿到清单后，再用飞书官方 MCP / Lark CLI 写入飞书。

## 晚上真实飞书接入的建议顺序

1. 确认飞书官方 MCP / Lark CLI 能读取真实飞书文档、知识库页面或消息。
2. 把读取到的标题、正文、原始飞书链接传给文档搭子 `ingest_text`。
3. 调用 `get_feishu_wiki_sync_plan`，拿到标准 wiki 页面清单。
4. 用飞书官方 MCP / Lark CLI 在飞书知识库或云文档中创建项目目录和页面。
5. 每创建或更新一个飞书 wiki 页面后，调用 `upsert_wiki_page`，用 `external_url` 写回飞书页面链接。
6. 调用 `query_project_wiki` 提问，确认 citations 能指向飞书页面或原始飞书资料。
7. 跑 `list_review_items`，确认冲突和待确认事项能被看见。

## 当前已验证

最近一次验证命令：

```bash
python -m unittest discover -s tests
python -m compileall work_memory tests examples
python examples\run_offline_demo.py
git diff --check
python -c "from work_memory.mcp_server import MCPServer; s=MCPServer(); print(len(s.tools)); print('get_feishu_wiki_sync_plan' in s.tools)"
```

验证结果：

- 单元测试通过。
- compileall 通过。
- 离线飞书演示通过。
- `git diff --check` 通过，仅有 Windows 换行提示。
- MCP server 工具数为 15，包含 `get_feishu_wiki_sync_plan`。

## 重要文件

- `README.md`：面向普通白领的产品说明和小白上手。
- `docs/feishu-quickstart.md`：晚上接飞书时的操作顺序。
- `docs/feishu-visible-wiki.md`：飞书可见 wiki 的设计。
- `docs/mcp-toolkit.md`：MCP 工具包方案。
- `work_memory/toolkit.py`：工具层 API。
- `work_memory/mcp_server.py`：MCP 工具暴露。
- `work_memory/engine.py`：ingest、维护、引用查询逻辑。
- `work_memory/retrieval.py`：无依赖 BM25 检索与中英文分词。
- `examples/run_offline_demo.py`：离线飞书模拟演示。
- `tests/test_toolkit_smoke.py`：核心 smoke test。

## 本轮开始前最近提交

- `5a29c1a Add agent handoff docs`

## 本轮交接记录

### 2026-06-24：补轻量 BM25 检索

本轮目标：

- 接受外部评价里“检索层太弱”的问题，先补一个无外部依赖、中文可用的轻量 BM25 检索。
- 保持项目边界：不引入 embedding 服务、不保存 API key、不新增服务端。

本轮改动：

- 新增 `work_memory/retrieval.py`：提供 `SearchDocument`、`tokenize_search_text`、`rank_bm25`。
- 更新 `work_memory/engine.py`：`query_project_wiki` / `get_cited_context` 的证据选择改为页面级 + 行级 BM25 排序，并保留会前、周报、风险等场景页偏好。
- 降低 `index`、`sources`、`log` 这类导航页在普通问题中的证据权重，减少无关来源清单被排到前面。
- 修复 wiki 列表项被回答成 `- - 内容` 的显示问题。
- 新增 `tests/test_retrieval.py`，并在 smoke test 中验证“客户培训”能优先命中“部署培训安排”这类更具体的行。
- 更新 README、`docs/mcp-toolkit.md`、`docs/wiki-schema.md`，说明检索层已经使用轻量 BM25。

本轮验证：

- `python -m unittest discover -s tests`：通过，5 个测试通过。
- `python -m compileall work_memory tests examples`：通过。
- `python examples\run_offline_demo.py`：通过，离线飞书演示仍能 ingest、生成飞书同步清单、返回 citations、列出 review items。
- `git diff --check`：通过，仅有 Windows LF/CRLF 提示。

下一位 agent 应该继续：

- 晚上真实接入飞书后，优先验证 citations 是否能从 BM25 结果指向飞书 wiki 页面或原始飞书资料。
- 如果继续补检索层，可以考虑 SQLite FTS5 或本地 embedding，但要保持无服务端、不持有 API key 的边界。
- 另一个重要方向是把“host LLM 按 `get_wiki_maintenance_contract` 精修 wiki 页面”的流程做成更清晰的可测试链路。

### 2026-06-24：新增交接机制

本轮目标：

- 准备一份交接文档，要求每个 agent 做完之后主动更新，不需要用户再次提示。

本轮改动：

- 新增 `AGENTS.md`：给所有 agent 的根目录接力规则。
- 新增 `docs/agent-handoff.md`：当前项目状态、晚上飞书接入步骤、验证记录、下一步建议。

本轮验证：

- `git diff --check`：通过，仅有 Windows LF/CRLF 提示。
- `python -m unittest discover -s tests`：通过，2 个测试通过。

下一位 agent 应该继续：

- 晚上接入真实飞书能力后，从 `docs/feishu-quickstart.md` 和本文件的“晚上真实飞书接入的建议顺序”开始。
- 做完后更新本文件的“本轮交接记录”，写明验证命令和结果；最终回复里补充最新 commit hash。