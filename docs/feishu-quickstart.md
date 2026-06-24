# 飞书接入 Quickstart

这份文档先解决“不连飞书也能准备什么”。晚上连上飞书以后，只需要把示例里的假飞书内容换成真实读取到的文档内容和链接。

## 当前分工

```text
AI 客户端
  ↓
飞书官方 MCP / Lark CLI：读取飞书文档、知识库、群消息，返回文本和链接
  ↓
文档搭子 MCP：ingest_text、维护 wiki、同步飞书可见层、检测冲突、返回 citations
  ↓
AI 客户端：只根据 citations 回答用户
```

文档搭子不保存飞书 token，不保存 LLM API key，也不直接封装飞书 OpenAPI。

## 现在可以先做

1. 确认文档搭子 MCP 能启动。
2. 跑一遍离线演示，确认 wiki、引用、冲突检测都正常。
3. 在 AI 客户端里准备两个 MCP 配置位：一个给飞书能力，一个给文档搭子。
4. 晚上连飞书时，把真实飞书文档内容传给 `ingest_text`，再用 `get_feishu_wiki_sync_plan` 把生成的 wiki 页面同步到飞书知识库或云文档。

## 本地离线演示

```bash
python examples/run_offline_demo.py
```

这个脚本会读取 `examples/offline_feishu_sources/` 里的模拟飞书资料，写入一个临时项目 wiki，打印飞书可见层同步清单，然后问三个问题：

- 明天和 A 客户开会前要注意什么？
- 客户需要什么？
- 有哪些待确认冲突？

演示里的链接是假的飞书链接，只用于验证 citation 链路。

如果想保留生成出来的 wiki 文件：

```bash
python examples/run_offline_demo.py --data-dir .demo-data
```

生成内容会在 `.demo-data/demo-tenant/a客户项目/wiki/`。

## AI 客户端 MCP 配置

文档搭子这一段可以先配好：

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

晚上接飞书时，再把飞书官方 MCP 或 Lark CLI 的配置加到同一个 `mcpServers` 里。具体命令和凭证以飞书开放平台当前文档为准，文档搭子这边只要求飞书工具最终能返回：

- 文档标题
- 文档纯文本内容
- 原始飞书链接

## 晚上真实接入时怎么做

拿到飞书文档内容以后，让 AI 客户端按这个顺序调用：

1. 飞书工具读取文档内容。
2. 调用文档搭子 `ingest_text`：

```json
{
  "workspace_id": "你的飞书 tenant / 团队 / 群标识",
  "project": "A客户项目",
  "title": "飞书会议纪要标题",
  "content": "飞书工具读取到的正文",
  "source_url": "飞书文档或消息链接"
}
```

3. 调用 `get_feishu_wiki_sync_plan`，拿到准备写入飞书的页面清单：

```json
{
  "workspace_id": "你的飞书 tenant / 团队 / 群标识",
  "project": "A客户项目",
  "root_title": "文档搭子知识库"
}
```

4. AI 客户端用飞书官方 MCP / Lark CLI 创建或更新飞书知识库、云文档里的项目页面。
5. 对已经同步到飞书的 wiki 页面，调用 `upsert_wiki_page` 时传入 `external_url`，让引用优先指向飞书页面。
6. 用户提问时，先调用 `query_project_wiki`：

```json
{
  "workspace_id": "你的飞书 tenant / 团队 / 群标识",
  "project": "A客户项目",
  "question": "明天开会前我该注意什么？"
}
```

7. AI 客户端只根据返回的 `citations` 回答。

## 接入成功的判断标准

- `list_wiki_pages` 能看到 `index`、`overview`、`requirements`、`risks`、`commitments`、`sources`、`log` 等页面。
- 飞书知识库或云文档里能看到同一套项目 wiki 页面。
- `read_wiki_page` 能看到来源标题和飞书链接。
- `get_feishu_wiki_sync_plan` 能返回要写入飞书的页面清单。
- `query_project_wiki` 返回非空 `citations`。
- 如果资料里出现预算、时间或承诺冲突，`list_review_items` 能看到待确认项。

## 常见问题

### 没有 citations 怎么办？

不要让 AI 自己补答案。先补充资料，或读取相关 wiki 页面检查是否真的没有证据。

### 飞书链接怎么进入引用？

调用 `ingest_text` 时传 `source_url`。如果 wiki 页面本身已经同步到飞书文档，调用 `upsert_wiki_page` 时可以用 `external_url` 传飞书文档链接。后续再次整理资料时，文档搭子会保留这个外部链接，让引用继续指向飞书。

### 需要服务端吗？

第一阶段不需要。飞书读取由飞书官方 MCP / Lark CLI 负责，文档搭子只是本地或企业内的 MCP 工具包。
