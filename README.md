# 文档搭子（Document Buddy）

<p>
  <a href="https://github.com/ivyzhi0807/document-buddy/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ivyzhi0807/document-buddy/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="MCP" src="https://img.shields.io/badge/MCP-toolkit-4b5563.svg">
  <img alt="Feishu / Lark" src="https://img.shields.io/badge/Feishu%20%2F%20Lark-ready-00b96b.svg">
</p>

<p><strong>README 中文</strong> · <a href="README.en.md">README English</a> · <a href="LICENSE">MIT License</a></p>

文档搭子是一个面向飞书真实工作流的 **无服务端 MCP 工具包**。它把飞书文档、知识库、群消息、会议纪要、PDF 和网页资料整理成项目 wiki，再让 AI 客户端只根据带引用的 wiki 证据回答问题。

它不做 SaaS，不接公网 webhook，不托管飞书 token，也不保存 LLM API key。飞书读写交给你已经授权的飞书官方能力或 `lark-cli`；LLM 来自你自己的 AI 客户端。

> 发资料给它，它记住。  
> 问它问题，它回答。  
> 信息变了，它自己维护。  
> 有冲突，它来问你。

## 适合谁

很多白领的问题不是“没有资料”，而是资料散在太多地方：飞书文档、知识库、群消息、会议纪要、PDF、临时截图、邮件摘录。真正要用的时候，大家常常要重新翻聊天记录、找最新版文档、问同事“上次客户到底怎么说的”。

文档搭子想做的是一个很轻的项目记忆层：你把资料发给它，它把项目里的需求、决策、风险、承诺、人物、资料来源和待确认问题整理成一套飞书可见 wiki。之后你问问题，它只根据 wiki 里有引用的内容回答，并把来源链接带回来。

它不是一个新的知识库系统，也不是让大家再多维护一套表格。它更像一个会整理资料的同事，藏在你已经使用的办公平台和 AI 客户端后面。

## 普通白领怎么用

用户只需要记住两种操作：

- **发资料给它**：会议纪要、飞书文档、群消息、需求文档、PDF、网页摘录都可以。
- **问它问题**：会前准备、客户背景、风险点、待办、周报素材、邮件草稿都可以问。

它在后台做这些事：

- 自动把资料整理进对应项目 wiki。
- 在飞书知识库或飞书云文档里生成团队可见页面。
- 维护项目总览、需求、风险、承诺、决策、人物、资料来源和待确认问题。
- 回答时带引用，方便点回飞书 wiki 页面或原始资料。
- 发现预算、时间、承诺事项冲突时，不自己猜，先放进待确认问题。

## 一天里的使用方式

早上开会前，你可以问：

> 明天和 A 客户开会前，我该注意什么？

文档搭子会从项目 wiki 里找出客户需求、风险、承诺事项和待确认冲突，并带上引用。没有证据的部分不会编。

开完会后，你可以说：

> 把这份会议纪要整理进 A 客户项目。

它会更新项目总览、需求、风险、待办、决策和资料清单。如果出现“预算 10 万”和“预算 12 万”这样的冲突，它不会替你选一个，而是提醒你确认。

写周报时，你可以问：

> 帮我整理 A 客户项目这周进展，重点写风险和下周待办。

它会只用 wiki 里有证据的内容生成素材，并给出引用。你可以点回来源，不用重新翻一遍群消息。

新人接手项目时，可以问：

> 我刚接手 A 客户项目，给我一个 5 分钟能看懂的项目背景。

它会从项目总览、需求、决策、风险和待确认问题中整理出当前状态，并告诉你每个关键点来自哪里。

## 真实飞书环境怎么用

### 1. 安装

```bash
git clone https://github.com/ivyzhi0807/document-buddy.git
cd document-buddy
pip install -e .
```

### 2. 在 AI 客户端里启动 MCP

把文档搭子加到支持 MCP 的 AI 客户端里，例如：

```json
{
  "mcpServers": {
    "文档搭子": {
      "command": "python",
      "args": ["-m", "work_memory.mcp_server"],
      "env": {
        "WORK_MEMORY_DATA_DIR": "/path/to/document-buddy-data"
      }
    }
  }
}
```

安装后也可以用：

```bash
document-buddy-mcp
```

### 3. 读取飞书资料并写入项目记忆

用飞书官方 MCP、`lark-cli` 或你的企业内部飞书工具读取真实飞书内容。然后让 AI 客户端调用文档搭子的 `ingest_text`：

```json
{
  "workspace_id": "your-team-or-tenant",
  "project": "A客户项目",
  "title": "飞书会议纪要标题",
  "content": "飞书工具读取到的正文",
  "source_url": "飞书文档或消息链接"
}
```

文档搭子会生成标准项目 wiki：

```text
文档搭子知识库/
  A客户项目/
    项目首页
    项目总览
    需求与关注点
    风险点
    承诺与待办
    决策记录
    相关人物
    待确认问题
    资料清单
    维护日志
```

### 4. 同步到飞书知识库

如果你已经装好并授权 `lark-cli`，可以用同步脚本把 wiki 页面写入飞书知识库，并把飞书页面 URL 回填成本地 citation 链接：

```bash
python scripts/sync_to_feishu.py \
  --workspace-id "your-team-or-tenant" \
  --project "A客户项目" \
  --root-node-token "已有的文档搭子知识库节点 token"
```

这个脚本只调用你本机已经登录的 `lark-cli`，不保存飞书 token，也不需要服务端。写入飞书前，它会自动处理 Markdown 里多余的一级标题，避免页面标题变成 `Untitled`。

### 5. 提问并获得带引用回答

问题进来时，AI 客户端应该先调用：

- `query_project_wiki`
- 或 `get_cited_context`

文档搭子只返回 wiki 中可引用的证据。AI 客户端再基于这些证据回答。

如果资料里没有证据，答案应该是：wiki 没有证据，而不是自由发挥。

## 防幻觉规则

这是硬规则：**回答必须来自项目 wiki。**

- 回答任何项目问题前，必须调用 `query_project_wiki` 或 `get_cited_context`。
- 工具只返回 wiki 中可引用的证据。
- 查询证据时使用轻量 BM25 排序，优先返回更贴近问题的页面和行。
- AI 客户端只能基于返回的 `citations` 回答。
- 没有 `citations`，就必须说 wiki 没有证据，不能补编。
- 发现冲突时，冲突写入 `open-questions`，由用户确认。

## MCP 工具

核心工具：

- `ingest_text`：把已读取的飞书文档、群消息、会议纪要等文本整理进项目 wiki。
- `get_feishu_wiki_sync_plan`：把当前 wiki 打包成飞书知识库或云文档的创建/更新清单。
- `upsert_wiki_page`：写入或替换 wiki 页面，可传飞书页面链接作为 citation 地址。
- `query_project_wiki`：根据问题返回带引用的 wiki 证据。
- `get_cited_context`：`query_project_wiki` 的 evidence-only 版本。
- `list_review_items`：列出需要用户复核的冲突、薄页面和来源读取问题。
- `resolve_conflict`：用户确认后，把冲突标记为已解决。

其他工具包括：项目创建、页面读取、页面列表、lint、冲突检测和 wiki schema 获取。

## 架构

```text
飞书文档 / 飞书知识库 / 飞书消息
        ↓
飞书官方 MCP / Lark CLI / 企业内部飞书工具
        ↓
文档搭子 MCP：整理项目 wiki、检测冲突、生成 citation
        ↓
飞书知识库 / 飞书云文档作为团队可见层
        ↓
AI 客户端只根据带引用证据回答
```

本地 `WORK_MEMORY_DATA_DIR` 只保存工具状态、索引、冲突和缓存。用户主要阅读入口应该是飞书知识库或飞书云文档。

## 关键词

MCP, Feishu, Lark, llm-wiki, project memory, AI knowledge base, cited answers, anti-hallucination, workplace AI, document wiki, RAG alternative.

## 项目状态

MVP 可用。已经跑通真实飞书知识库写回与带飞书 citation 的问答链路。

当前边界：

- 不提供 SaaS 服务端。
- 不保存飞书 token。
- 不保存 LLM API key。
- 不实现飞书机器人 webhook。
- 不提供 Web UI。

这些能力未来可以作为独立应用层扩展，但不会混进 MCP 工具包核心。

## 更多文档

- MCP 工具包方案：[docs/mcp-toolkit.md](docs/mcp-toolkit.md)
- 飞书接入 Quickstart：[docs/feishu-quickstart.md](docs/feishu-quickstart.md)
- 飞书可见 Wiki 设计：[docs/feishu-visible-wiki.md](docs/feishu-visible-wiki.md)
- Wiki 轻量规则：[docs/wiki-schema.md](docs/wiki-schema.md)
- 平台能力使用原则：[docs/platform-capabilities.md](docs/platform-capabilities.md)
- Changelog：[CHANGELOG.md](CHANGELOG.md)
