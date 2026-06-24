# 文档搭子（Document Buddy）MCP 工具包方案

这个版本不假设有服务端，也不托管用户的 LLM API。

文档搭子的定位是：

```text
飞书里的文档记忆结构
+
AI 可调用的 MCP 工具层
+
强制引用的 wiki 工作流
```

## 谁来提供 LLM

MCP 工具包不提供模型。用户在哪个 AI 客户端里使用，就由那个客户端里的模型来推理。

常见形态：

- Cursor / Claude Code / Codex / Trae / OpenClaw 调用本 MCP。
- 企业自己配置 OpenAI、Azure OpenAI、DeepSeek、通义、火山或私有模型。
- 飞书官方 MCP / Lark CLI 负责读取飞书文档，本工具负责维护项目 wiki 和引用规则。

普通用户不需要在文档搭子里填 API key；企业管理员也不需要把 key 给这个工具包。

## 飞书操作层

文档搭子不直接封装飞书 OpenAPI。推荐把飞书操作交给更靠近平台的一层：

- 飞书官方 MCP：优先用于云文档、知识库等正式接入。
- Lark CLI / 本地 OpenAPI MCP：适合本地开发、调试和企业内网验证。
- 飞书 Docs add-on：如果以后做插件 UI，也复用同一组文档搭子 MCP 工具。

文档搭子只接收已经读取出的文本、来源标题和 `source_url`，然后维护 wiki、冲突和引用证据。

## 飞书优先工作流

第一阶段不做飞书机器人 SaaS，也不需要公网 webhook；旧的本地服务和飞书 webhook 已从最终版核心中移除。

推荐流程：

1. 用户或 AI 客户端通过飞书官方 MCP / Lark CLI 读取当前飞书文档、消息或文件内容。
2. 调用 `ingest_text` 把内容整理进某个项目记忆，并把飞书链接作为 `source_url` 传入。
3. 文档搭子维护本地或飞书文档形式的 wiki，默认生成 `index.md` 和 `log.md`。
4. 如果 host LLM 需要做更细的整理，先调用 `get_wiki_maintenance_contract`，再用 `read_wiki_page` / `upsert_wiki_page` 做小范围页面更新。
5. 用户提问时，AI 客户端必须先调用 `get_cited_context` 或 `query_project_wiki`。
6. AI 只能基于工具返回的引用回答；没有引用就说 wiki 没有证据。

后续如果做飞书 Docs add-on，插件 UI 也应该调用同一组工具。

## 推荐 wiki 结构

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

在飞书正式形态里，这些页面可以映射到飞书文档或知识库页面。工具返回的引用链接应优先指向飞书文档链接；未映射飞书文档时使用 `wiki://...`。

## MCP 工具

### create_project_memory

创建标准项目记忆页面。

### list_project_memories

列出工作区里的项目记忆。

### get_project_index

返回项目 wiki 页索引、页面契约，并提醒模型：回答前必须调用引用上下文工具。

### get_wiki_maintenance_contract

返回轻量 wiki schema。MCP host 里的 LLM 可以据此维护页面，不需要本工具包保存模型 API key。

### ingest_text

接收已经从飞书文档、群消息、文件或其他工具读取出来的文本，整理进项目记忆。

### upsert_wiki_page

写入或替换 wiki 页面。`external_url` 可以传飞书文档链接，用作后续引用链接。

### list_wiki_pages

列出某个项目的 wiki 页面。

### read_wiki_page

读取某个 wiki 页面。

### get_cited_context

根据问题返回带引用的 wiki 证据。这个工具不负责自由发挥，只返回可引用上下文。

### query_project_wiki

`get_cited_context` 的别名。建议 AI 客户端在回答任何项目问题前都调用它。

### lint_project_wiki

检查缺失页面、薄页面和未解决冲突。

### detect_conflicts

列出未解决冲突。

### list_review_items

列出需要用户或 AI 复核的轻量事项，例如冲突和内容过薄的页面。

### resolve_conflict

用户确认哪个版本正确后，把对应冲突标记为已解决。

## MCP 客户端配置示例

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

## 回答规则

AI 客户端应该把下面这条规则写进 system/developer prompt：

> 回答任何项目问题前，必须调用 `query_project_wiki`。只能使用工具返回的 citations 作答；没有 citations 时，直接说明 wiki 没有证据，不要补编。
