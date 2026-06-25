# Changelog

## Unreleased

- Split English README into `README.en.md` and added top navigation for Chinese README, English README, and MIT License.
- Reworked README into bilingual Chinese-first and English sections focused on real Feishu usage.
- Added package keywords for MCP, Feishu/Lark, llm-wiki, cited answers, and anti-hallucination discoverability.
- Added Feishu-safe Markdown export for sync plans so imported Docx pages keep a single H1 title.
- Added `scripts/sync_to_feishu.py` to sync generated wiki pages to Feishu via the user's local `lark-cli` and backfill citation URLs.
- Updated README to describe the project as MVP usable after real Feishu write-back validation.

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
