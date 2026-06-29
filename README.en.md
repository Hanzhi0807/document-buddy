# Document Buddy（文档搭子）

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="MCP" src="https://img.shields.io/badge/MCP-toolkit-4b5563.svg">
  <img alt="Feishu / Lark" src="https://img.shields.io/badge/Feishu%20%2F%20Lark-ready-00b96b.svg">
</p>

<p><a href="README.md">README 中文</a> · <strong>README English</strong> · <a href="LICENSE">MIT License</a></p>

Document Buddy is a **serverless MCP toolkit** for real Feishu/Lark workflows. It turns Feishu docs, wiki pages, chat messages, meeting notes, PDFs, and web snippets into a project wiki, then helps an AI client answer only from cited wiki evidence.

It is not a SaaS bot, does not expose a public webhook, does not host Feishu tokens, and does not store LLM API keys. Feishu read/write is handled by the official Feishu MCP, `lark-cli`, or your internal Feishu tooling. The LLM comes from your own AI client.

> Send it materials, it remembers.
> Ask it questions, it answers.
> When information changes, it maintains the wiki.
> When facts conflict, it asks you.

## Who It Helps

Office work rarely lacks documents. The real problem is that project knowledge is scattered across Feishu docs, wiki pages, group chats, meeting notes, PDFs, screenshots, and email snippets.

Document Buddy adds a lightweight project memory layer. You send it materials; it organizes requirements, decisions, risks, commitments, people, sources, and open questions into a Feishu-visible wiki. When you ask a question, it answers only from cited wiki evidence and gives you links back to the source.

It is not another knowledge-base product that asks your team to maintain more tables. It behaves more like a colleague who keeps the project memory tidy inside the tools you already use.

## How A Non-Technical User Uses It

Users only need two actions:

- **Send materials**: meeting notes, Feishu docs, chat excerpts, requirements, PDFs, or web snippets.
- **Ask questions**: meeting prep, customer background, risks, todos, weekly report material, or email drafts.

In the background, Document Buddy:

- organizes materials into the right project wiki;
- creates team-visible pages in Feishu Wiki or Feishu Docs;
- maintains overview, requirements, risks, commitments, decisions, people, sources, and open questions;
- answers with citations that point back to Feishu wiki pages or source materials;
- records conflicts instead of guessing which fact is correct.

## Real Feishu/Lark Usage

Copy the full block below into an MCP-capable or command-line-capable agent, such as Claude Code, Kimi, or Codex, and let it wire Document Buddy into your real Feishu/Lark environment. The block includes example values; ask the agent to replace them with your own workspace details.

```text
Help me use Document Buddy with my real Feishu/Lark workspace on this machine.

The repository is https://github.com/Hanzhi0807/document-buddy. First check whether the repo already exists locally. If it does not, clone it into a suitable workspace. Then enter the project directory and run pip install -e . to install it.

Configure it as an MCP server in my AI client. The startup command is python -m work_memory.mcp_server. Set WORK_MEMORY_DATA_DIR to a local data directory, for example D:\document-buddy-data or /path/to/document-buddy-data.

Use my already-authorized official Feishu MCP, lark-cli, or internal Feishu tooling to read real Feishu materials. For each source, pass its title, body text, and source URL to Document Buddy's ingest_text tool. Example parameters: workspace_id = "acme-feishu" (a team/tenant/workspace identifier), project = "Customer A Project" (one concrete project name), title = "Feishu meeting note: Customer A prep", content = "text read from Feishu", source_url = "https://example.feishu.cn/docx/xxx".

After ingestion, call get_feishu_wiki_sync_plan to generate the sync plan. If local lark-cli is authorized, run the sync script to write the generated wiki pages back to Feishu Wiki and backfill Feishu page URLs as local citation links. Example command: python scripts/sync_to_feishu.py --workspace-id "acme-feishu" --project "Customer A Project" --root-node-token "wikcnExampleRoot123". Here root-node-token means the token of an existing Document Buddy root wiki page. For example, if the Feishu Wiki page URL is https://example.feishu.cn/wiki/wikcnExampleRoot123, then root-node-token is wikcnExampleRoot123.

Before answering any project question, always call query_project_wiki or get_cited_context, and answer only from returned citations. If there are no citations, say the wiki has no evidence instead of inventing an answer. If budgets, dates, commitments, or other facts conflict, record them as open questions or review items instead of guessing.

Do not store Feishu tokens, do not host LLM API keys, and do not start a public webhook or SaaS service.
```

Field examples: `workspace_id` is a team/tenant/workspace identifier such as `acme-feishu`; `project` is a concrete project name such as `Customer A Project`; `root-node-token` is the token after `/wiki/` in the Feishu Wiki root page URL, such as `wikcnExampleRoot123`.

## Anti-Hallucination Rule

Hard rule: **answers must come from the project wiki.**

- Always call `query_project_wiki` or `get_cited_context` before answering.
- The toolkit returns only citable wiki evidence.
- Lightweight BM25 ranking finds relevant pages and lines.
- No citations means no answer.
- Conflicts are written to `open-questions` for user confirmation.

## MCP Tools

Core tools:

- `ingest_text`: ingest Feishu docs, messages, meeting notes, or extracted text into a project wiki.
- `get_feishu_wiki_sync_plan`: package wiki pages for Feishu Wiki/Docs creation or update.
- `upsert_wiki_page`: write or replace a wiki page and store an external citation URL.
- `query_project_wiki`: return cited wiki evidence for a question.
- `get_cited_context`: evidence-only query context.
- `list_review_items`: list conflicts and pages that need review.
- `resolve_conflict`: mark a user-confirmed conflict as resolved.

Additional tools cover project creation, wiki page reads, page listing, linting, conflict detection, and wiki schema retrieval.

## Architecture

```text
Feishu Docs / Feishu Wiki / Feishu Messages
        ↓
Official Feishu MCP / Lark CLI / Internal Feishu tooling
        ↓
Document Buddy MCP: project wiki, conflict detection, citations
        ↓
Feishu Wiki / Feishu Docs as the team-visible layer
        ↓
AI client answers only from cited evidence
```

`WORK_MEMORY_DATA_DIR` stores tool state, indexes, conflicts, and cache. The main user-facing wiki should live in Feishu Wiki or Feishu Docs.

## Keywords

MCP, Feishu, Lark, llm-wiki, project memory, AI knowledge base, cited answers, anti-hallucination, workplace AI, document wiki, RAG alternative.

## Status

MVP usable. Real Feishu Wiki write-back and Feishu citation-based Q&A have been validated.

Current boundaries:

- no SaaS backend;
- no Feishu token hosting;
- no LLM API key hosting;
- no Feishu bot webhook;
- no Web UI.

These can be added later as separate application layers, but they are intentionally outside the MCP toolkit core.

## More Docs

- MCP toolkit design: [docs/mcp-toolkit.md](docs/mcp-toolkit.md)
- Feishu quickstart: [docs/feishu-quickstart.md](docs/feishu-quickstart.md)
- Feishu-visible wiki design: [docs/feishu-visible-wiki.md](docs/feishu-visible-wiki.md)
- Wiki schema: [docs/wiki-schema.md](docs/wiki-schema.md)
- Platform capability principles: [docs/platform-capabilities.md](docs/platform-capabilities.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
