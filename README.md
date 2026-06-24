# 文档搭子（Document Buddy，未完成，建设中）

文档搭子（Document Buddy）是一个基于 karpathy/llm-wiki.md 思路打造的 **无服务端 MCP 工具包**。

它不做飞书机器人 SaaS，不接公网 webhook，也不托管任何 LLM API key。它停留在工具层：帮助用户或 AI 客户端把飞书文档、飞书知识库、群消息、会议纪要、PDF、网页资料整理成可追溯引用的项目 wiki。

> 发资料给它，它记住。  
> 问它问题，它回答。  
> 信息变了，它自己维护。  
> 有冲突，它来问你。

## 它解决什么

很多白领的问题不是“没有资料”，而是资料散在太多地方：飞书文档、知识库、群消息、会议纪要、PDF、临时截图、邮件摘录。真正要用的时候，大家常常要重新翻聊天记录、找最新版文档、问同事“上次客户到底怎么说的”。

文档搭子想做的是一个很轻的项目记忆层：你把资料发给它，它把项目里的需求、决策、风险、承诺、待确认问题整理成一套 wiki。之后你问问题，它只根据 wiki 里有引用的内容回答，并把来源链接带回来。

它不是一个新的知识库系统，也不是让大家再多维护一套表格。它更像一个会整理资料的同事，藏在你已经使用的办公平台和 AI 客户端后面。

## 普通白领怎么用

用户只需要记住两种操作：

- **发资料给它**：会议纪要、飞书文档、群消息、需求文档、PDF、网页摘录都可以。
- **问它问题**：会前准备、客户背景、风险点、待办、周报素材、邮件草稿都可以问。

它在后台做这些事：

- 自动判断资料属于哪个项目。
- 把资料整理到项目 wiki。
- 维护项目总览、需求、风险、承诺、决策、人物、资料来源和待确认问题。
- 回答时带引用，方便点回原始飞书文档或 wiki 页面。
- 发现预算、时间、承诺事项冲突时，不自己猜，先放进待确认问题。

## 一天里的使用方式

早上开会前，你可以问：

> 明天和 A 客户开会前，我该注意什么？

文档搭子会从项目 wiki 里找出客户需求、未解决风险、承诺事项和待确认冲突，并带上引用。没有证据的部分不会编。

开完会后，你可以说：

> 把这份会议纪要整理进 A 客户项目。

它会把新资料写入项目记忆，更新需求、风险、待办、决策和资料清单。如果发现“预算 10 万”和“预算 12 万”同时出现，它不会选一个看起来更像的答案，而是提醒你确认。

写周报时，你可以问：

> 帮我整理 A 客户项目这周进展，重点写风险和下周待办。

它会只用 wiki 里有证据的内容生成素材，并给出引用。你可以点回来源检查，不用重新翻一遍群消息。

跟进客户时，你可以问：

> 根据现有资料，帮我写一封给 A 客户的跟进邮件。

AI 客户端可以根据文档搭子返回的引用证据组织成邮件。文档搭子本身不负责自由发挥，它只负责把可信资料找出来。

新人接手项目时，可以问：

> 我刚接手 A 客户项目，给我一个 5 分钟能看懂的项目背景。

它会从项目总览、需求、决策、风险和待确认问题中整理出当前状态，并告诉你每个关键点来自哪里。

## 用户能期待什么

好的情况下，用户看到的是：

- 不用自己整理一堆零散会议纪要。
- 不用在群里反复搜索客户上次怎么说。
- 不用担心 AI 把没有出处的内容说得像真的。
- 可以点引用回到飞书文档、群消息或 wiki 页面。
- 信息变了以后，项目 wiki 会跟着更新。
- 出现冲突时，它把问题抛出来，让人确认。

它的目标不是替用户做决定，而是让用户更快知道：现在项目里有哪些事实、哪些承诺、哪些风险、哪些地方还没确认。

## 当前形态

```text
飞书文档 / 飞书知识库 / 飞书消息
        ↓
飞书官方 MCP、Lark CLI、Docs add-on 或用户当前 AI 客户端读取内容
        ↓
文档搭子 MCP 工具包维护项目 wiki
        ↓
AI 客户端基于带引用的 wiki 证据回答
```

文档搭子本身不提供模型。用户使用的 LLM 来自自己的 AI 客户端或企业模型配置，比如 Codex、Claude Code、Cursor、Trae、OpenClaw、OpenAI、Azure OpenAI、DeepSeek、通义、火山或私有模型。

## 防幻觉规则

这是硬规则：**回答必须来自项目 wiki。**

- 回答任何项目问题前，必须调用 `query_project_wiki` 或 `get_cited_context`。
- 工具只返回 wiki 中可引用的证据。
- AI 客户端只能基于返回的 `citations` 回答。
- 没有 `citations`，就必须说 wiki 没有证据，不能补编。
- 发现冲突时，冲突写入 `open-questions`，由用户确认。

## 无飞书账号时先验证

现在还没有连飞书，也可以先跑完整闭环：

```bash
python examples/run_offline_demo.py
```

这个演示会用模拟飞书资料调用 `ingest_text`，生成项目 wiki，查询带引用答案，并列出预算冲突。晚上接上飞书后，把模拟资料换成飞书官方 MCP / Lark CLI 读取到的真实标题、正文和链接即可。

## 飞书操作由谁完成

文档搭子不直接操作飞书 API，也不自己保存飞书 token。飞书侧的读写交给飞书官方能力完成：

- **飞书官方 MCP**：优先用于让 AI 客户端读取或写入飞书云文档、知识库等内容。
- **Lark CLI / 本地 OpenAPI MCP**：更适合本地开发、调试或企业内部验证。
- **未来 Docs add-on**：如果要做成更贴近飞书用户的插件，也应该调用同一组 MCP 工具。

因此完整链路是：

```text
AI 客户端
  ↓
飞书官方 MCP / Lark CLI：读写飞书文档、消息、知识库，处理飞书权限和链接
  ↓
文档搭子 MCP：整理项目 wiki、检测冲突、返回带 citations 的证据
  ↓
AI 客户端：只根据引用回答用户
```

这样文档搭子不重复造飞书连接层，也不需要用户把 LLM API key 或飞书凭证交给它。

## 飞书优先方案

第一阶段不做飞书机器人，也不做公网服务端。

推荐组合是：

1. 用飞书官方 MCP、Lark CLI 或 Docs add-on 读取飞书文档/知识库/消息内容。
2. 把读取到的文本传给 `ingest_text`，同时传入飞书文档或消息链接作为 `source_url`。
3. 文档搭子维护项目 wiki，并自动生成 `index.md` 和 `log.md`。
4. 如果 wiki 页面已经存在飞书文档中，用 `upsert_wiki_page` 的 `external_url` 传入飞书文档链接。
5. 提问时调用 `query_project_wiki`，得到带引用上下文。
6. AI 客户端只根据引用回答。

推荐 wiki 结构：

```text
文档搭子/
  A客户项目/
    index.md
    overview.md
    requirements.md
    risks.md
    commitments.md
    decisions.md
    people.md
    open-questions.md
    sources.md
    log.md
```

在本地开发时，引用会使用 `wiki://workspace/project/page#Lx`。在飞书正式工作流中，应该通过 `external_url` 映射成飞书文档/知识库链接。

## MCP 工具

当前提供 14 个工具：

- `create_project_memory`：创建项目 wiki 标准页面。
- `list_project_memories`：列出项目记忆。
- `get_project_index`：获取项目 wiki 索引、页面契约和回答规则。
- `get_wiki_maintenance_contract`：返回轻量 wiki schema，供 MCP host 里的 LLM 做页面维护。
- `ingest_text`：把已读取的飞书文档、群消息、会议纪要等文本整理进项目 wiki。
- `upsert_wiki_page`：写入或替换 wiki 页面，可传飞书文档链接作为引用地址。
- `list_wiki_pages`：列出项目 wiki 页面。
- `read_wiki_page`：读取某个 wiki 页面。
- `get_cited_context`：根据问题返回带引用的 wiki 证据。
- `query_project_wiki`：`get_cited_context` 的别名，回答问题前应调用它。
- `lint_project_wiki`：检查缺失页面、薄页面、未解决冲突。
- `detect_conflicts`：列出未解决冲突。
- `list_review_items`：列出需要用户或 AI 复核的轻量事项。
- `resolve_conflict`：用户确认后，将某个冲突标记为已解决。

## 启动 MCP

```bash
python -m work_memory.mcp_server
```

安装后也可以使用：

```bash
document-buddy-mcp
```

MCP 客户端配置示例：

```json
{
  "mcpServers": {
    "文档搭子": {
      "command": "python",
      "args": ["-m", "work_memory.mcp_server"],
      "env": {
        "WORK_MEMORY_DATA_DIR": "/path/to/work-memory-data"
      }
    }
  }
}
```

## 本地数据

默认数据目录：

```text
data/
  state.sqlite
  <workspace>/<project>/
    raw/
    extracted/
    wiki/
```

可以通过环境变量修改：

```bash
WORK_MEMORY_DATA_DIR=/path/to/work-memory-data
```

这些本地文件只是工具层状态和开发验证。最终用户可见的 wiki 应优先映射到飞书文档或知识库。

## 更多说明

- MCP 工具包方案：[docs/mcp-toolkit.md](docs/mcp-toolkit.md)
- 飞书接入 Quickstart：[docs/feishu-quickstart.md](docs/feishu-quickstart.md)
- 离线演示样例：[examples/README.md](examples/README.md)
- Wiki 轻量规则：[docs/wiki-schema.md](docs/wiki-schema.md)
- 平台能力使用原则：[docs/platform-capabilities.md](docs/platform-capabilities.md)

## 当前状态

已完成：

- MCP stdio server。
- 项目 wiki 创建。
- 文本 ingest。
- 自动维护 wiki 页面、`index.md` 和 `log.md`。
- 来源链接和来源行号提示。
- 冲突检测与轻量 review 列表。
- 带引用上下文查询。
- 无引用不回答的规则。
- 离线飞书接入演示。

不再包含：

- 本地 HTTP 服务。
- 本地 Web UI。
- 飞书 webhook adapter。
- 飞书机器人 SaaS 服务端。

这些如果未来要做，也应该另开独立应用层，而不是混在 MCP 工具包核心里。
