# Examples

这里放的是不依赖真实飞书账号的演示资料。它们模拟“飞书官方 MCP / Lark CLI 已经读取出的文档文本和来源链接”。

运行：

```bash
python examples/run_offline_demo.py
```

它会演示：

- 把模拟飞书资料传给 `ingest_text`。
- 自动生成项目 wiki。
- 生成可写入飞书知识库/云文档的同步清单。
- 查询项目问题并返回 citations。
- 发现预算冲突并生成 review item。

晚上连上飞书以后，把 `examples/offline_feishu_sources/` 里的文本换成飞书工具实际读取到的内容，再用 `get_feishu_wiki_sync_plan` 把 wiki 页面同步到飞书知识库或云文档。

## 同步到真实飞书

离线演示跑通后，如果本机已经授权 `lark-cli`，可以回到仓库根目录运行：

```bash
python scripts/sync_to_feishu.py \
  --workspace-id "你的团队或工作区标识" \
  --project "A客户项目" \
  --root-node-token "已有的文档搭子知识库节点 token" \
  --dry-run
```

确认清单没问题后去掉 `--dry-run`。脚本会把 wiki 页面写入飞书知识库，并把飞书页面 URL 回填成本地 citation 链接。
