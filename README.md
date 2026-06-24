# 工作文档搭子（未完成，建设中）

工作文档搭子是一个基于 karpathy/llm-wiki.md 思路打造的 **无服务端 MCP 工具包**。

它不做飞书机器人 SaaS，不接公网 webhook，也不托管任何 LLM API key。它停留在工具层：帮助用户或 AI 客户端把飞书文档、飞书知识库、群消息、会议纪要、PDF、网页资料整理成可追溯引用的项目 wiki。

> 发资料给它，它记住。  
> 问它问题，它回答。  
> 信息变了，它自己维护。  
> 有冲突，它来问你。

## 当前形态

```text
飞书文档 / 飞书知识库 / 飞书消息
        ↓
飞书官方 MCP、Lark CLI、Docs add-on 或用户当前 AI 客户端读取内容
        ↓
工作文档搭子 MCP 工具包维护项目 wiki
        ↓
AI 客户端基于带引用的 wiki 证据回答
```

工作文档搭子本身不提供模型。用户使用的 LLM 来自自己的 AI 客户端或企业模型配置，比如 Codex、Claude Code、Cursor、Trae、OpenClaw、OpenAI、Azure OpenAI、DeepSeek、通义、火山或私有模型。

## 普通用户怎么理解

如果它以后装进飞书工作流，用户看到的是：

- 把一份会议纪要整理进 A 客户项目。
- 问“明天和 A 客户开会前我该注意什么？”
- 得到带引用的回答。
- 点引用回到对应的飞书文档或 wiki 页面。
- 如果预算、时间、承诺事项冲突，它不会自己猜，会把问题放进“待确认问题”。

底层实现不是机器人服务，而是一组 MCP 工具。AI 客户端负责读飞书内容和调用工具；工具负责维护项目 wiki 和返回可引用证据。

## 防幻觉规则

这是硬规则：**回答必须来自项目 wiki。**

- 回答任何项目问题前，必须调用 `query_project_wiki` 或 `get_cited_context`。
- 工具只返回 wiki 中可引用的证据。
- AI 客户端只能基于返回的 `citations` 回答。
- 没有 `citations`，就必须说 wiki 没有证据，不能补编。
- 发现冲突时，冲突写入 `open-questions`，由用户确认。

## MCP 工具

当前提供 11 个工具：

- `create_project_memory`：创建项目 wiki 标准页面。
- `list_project_memories`：列出项目记忆。
- `get_project_index`：获取项目 wiki 索引和回答规则。
- `ingest_text`：把已读取的飞书文档、群消息、会议纪要等文本整理进项目 wiki。
- `upsert_wiki_page`：写入或替换 wiki 页面，可传飞书文档链接作为引用地址。
- `list_wiki_pages`：列出项目 wiki 页面。
- `read_wiki_page`：读取某个 wiki 页面。
- `get_cited_context`：根据问题返回带引用的 wiki 证据。
- `query_project_wiki`：`get_cited_context` 的别名，回答问题前应调用它。
- `lint_project_wiki`：检查缺失页面、薄页面、未解决冲突。
- `detect_conflicts`：列出未解决冲突。

## 启动 MCP

```bash
python -m work_memory.mcp_server
```

安装后也可以使用：

```bash
wendang-dazi-mcp
```

MCP 客户端配置示例：

```json
{
  "mcpServers": {
    "工作文档搭子": {
      "command": "python",
      "args": ["-m", "work_memory.mcp_server"],
      "env": {
        "WORK_MEMORY_DATA_DIR": "/path/to/work-memory-data"
      }
    }
  }
}
```

## 飞书优先方案

第一阶段不做飞书机器人，也不做公网服务端。

推荐组合是：

1. 用飞书官方 MCP、Lark CLI 或 Docs add-on 读取飞书文档/知识库/消息内容。
2. 把读取到的文本传给 `ingest_text`。
3. 工作文档搭子维护项目 wiki。
4. 如果 wiki 页面已经存在飞书文档中，用 `upsert_wiki_page` 的 `external_url` 传入飞书文档链接。
5. 提问时调用 `query_project_wiki`，得到带引用上下文。
6. AI 客户端只根据引用回答。

推荐 wiki 结构：

```text
工作文档搭子/
  A客户项目/
    overview.md
    requirements.md
    risks.md
    commitments.md
    decisions.md
    open-questions.md
    sources.md
```

在本地开发时，引用会使用 `wiki://workspace/project/page#Lx`。在飞书正式工作流中，应该通过 `external_url` 映射成飞书文档/知识库链接。

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
- 平台能力使用原则：[docs/platform-capabilities.md](docs/platform-capabilities.md)

## 当前状态

已完成：

- MCP stdio server。
- 项目 wiki 创建。
- 文本 ingest。
- 自动维护 wiki 页面。
- 冲突检测。
- 带引用上下文查询。
- 无引用不回答的规则。

不再包含：

- 本地 HTTP 服务。
- 本地 Web UI。
- 飞书 webhook adapter。
- 飞书机器人 SaaS 服务端。

这些如果未来要做，也应该另开独立应用层，而不是混在 MCP 工具包核心里。