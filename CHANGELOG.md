# Changelog

## 0.2.0 - 2026-06-24

- Added GitHub Actions CI for tests, compile checks, offline demo, and mypy.
- Fixed editable package installation by scoping setuptools package discovery to `work_memory*`.
- Surfaced source read failures through events, lint output, and review items.
- Added lightweight BM25 wiki retrieval and broader retrieval edge-case tests.
- Added Feishu-visible wiki sync planning via `get_feishu_wiki_sync_plan`.
- Added multi-agent handoff docs and update rules.

## 0.1.0 - 2026-06-24

- Initial no-server MCP toolkit for Document Buddy.
- Added project wiki creation, text ingestion, citation-only querying, conflict detection, and offline Feishu demo.
