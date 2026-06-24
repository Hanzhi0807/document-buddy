# 飞书可见 Wiki 设计

文档搭子的正式目标不是把项目 wiki 藏在本地目录里，而是把团队可见的知识库做到飞书文档或飞书知识库里。

## 目标

普通用户应该在飞书里看到一套清晰的项目记忆页面：

```text
文档搭子知识库/
  A客户项目/
    index
    overview
    requirements
    risks
    commitments
    decisions
    people
    open-questions
    sources
    log
```

用户可以在飞书里直接打开这些页面，查看项目背景、需求、风险、承诺和待确认问题。AI 回答时也应该优先引用这些飞书页面或原始飞书资料链接。

## 分工

```text
飞书官方 MCP / Lark CLI
  读取原始飞书文档、群消息、知识库页面
  创建或更新飞书云文档 / 知识库页面

文档搭子 MCP
  把资料整理成 wiki 页面内容
  管理页面结构、冲突、引用规则和本地缓存
  返回 query_project_wiki / get_cited_context 的 citations

飞书知识库 / 云文档
  承载用户可见的 wiki 页面
  管理权限、协作、分享和真实链接
```

## 本地数据的定位

本地 `WORK_MEMORY_DATA_DIR` 仍然存在，但它不是最终用户的主要阅读入口。

本地应该保存：

- `state.sqlite`：项目、来源、页面索引、冲突、事件。
- `raw/`：离线演示或调试时保存的原始资料副本。
- `extracted/`：提取出的纯文本缓存。
- `wiki/`：离线演示或没有飞书写权限时的 Markdown fallback。

正式飞书工作流里，用户可见内容应优先写入飞书文档或飞书知识库。本地 wiki 只是缓存和 fallback。

## 第一阶段落地方式

第一阶段不需要文档搭子自己实现飞书 OpenAPI，也不需要服务端。

推荐流程：

1. AI 客户端用飞书官方 MCP / Lark CLI 读取原始资料。
2. 调用文档搭子 `ingest_text`，让文档搭子整理项目 wiki。
3. 调用 `get_feishu_wiki_sync_plan`，拿到要创建或更新到飞书的页面清单。
4. AI 客户端再用飞书官方 MCP / Lark CLI 创建或更新飞书知识库页面。
5. 调用 `upsert_wiki_page`，用 `external_url` 把本地页面索引映射到对应飞书页面链接。
6. 用户提问时，`query_project_wiki` 返回的引用优先指向飞书页面。

## 页面映射

| 文档搭子页面 | 飞书可见页面 |
| --- | --- |
| `index` | 项目首页 |
| `overview` | 项目总览 |
| `requirements` | 需求与关注点 |
| `risks` | 风险点 |
| `commitments` | 承诺与待办 |
| `decisions` | 决策记录 |
| `people` | 相关人物 |
| `open-questions` | 待确认问题 |
| `sources` | 资料清单 |
| `log` | 维护日志 |

## 成功标准

- `get_feishu_wiki_sync_plan` 能给出飞书页面清单。
- 飞书里能看到“文档搭子知识库”或项目目录。
- A 客户项目下能看到标准 wiki 页面。
- 页面内容由文档搭子整理，并保留来源标题和链接。
- `query_project_wiki` 返回的 citations 能点回飞书页面或原始飞书资料。
- 本地目录只作为缓存、索引和离线 fallback，不是用户主要入口。
