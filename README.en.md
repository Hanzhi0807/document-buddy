# Document Buddy（文档搭子）

<p>
  <a href="https://github.com/ivyzhi0807/document-buddy/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ivyzhi0807/document-buddy/actions/workflows/ci.yml/badge.svg"></a>
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

### 1. Install

```bash
git clone https://github.com/ivyzhi0807/document-buddy.git
cd document-buddy
pip install -e .
```

### 2. Start The MCP Server In Your AI Client

Add Document Buddy to an MCP-capable AI client:

```json
{
  "mcpServers": {
    "Document Buddy": {
      "command": "python",
      "args": ["-m", "work_memory.mcp_server"],
      "env": {
        "WORK_MEMORY_DATA_DIR": "/path/to/document-buddy-data"
      }
    }
  }
}
```

After installation you can also start it with:

```bash
document-buddy-mcp
```

### 3. Ingest Real Feishu Materials

Use the official Feishu MCP, `lark-cli`, or your internal Feishu tooling to read real Feishu content. Then let the AI client call `ingest_text`:

```json
{
  "workspace_id": "your-team-or-tenant",
  "project": "Customer A Project",
  "title": "Feishu meeting note title",
  "content": "text read from Feishu",
  "source_url": "Feishu doc or message URL"
}
```

Document Buddy creates a standard project wiki:

```text
Document Buddy Wiki/
  Customer A Project/
    Home
    Overview
    Requirements
    Risks
    Commitments
    Decisions
    People
    Open Questions
    Sources
    Maintenance Log
```

### 4. Sync To Feishu Wiki

If `lark-cli` is installed and authorized, sync the generated wiki pages back to Feishu:

```bash
python scripts/sync_to_feishu.py \
  --workspace-id "your-team-or-tenant" \
  --project "Customer A Project" \
  --root-node-token "existing Document Buddy root wiki node token"
```

The script calls your local `lark-cli`; it does not store Feishu tokens or require a backend server. Before writing Markdown to Feishu, it keeps a single H1 title so imported Docx pages do not become `Untitled`.

### 5. Ask Questions With Citations

Before answering a project question, the AI client should call:

- `query_project_wiki`
- or `get_cited_context`

Document Buddy returns only cited wiki evidence. If there are no citations, the AI client should say the wiki has no evidence instead of inventing an answer.

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
