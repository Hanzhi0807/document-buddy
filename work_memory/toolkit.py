from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import Database
from .engine import WorkMemoryEngine
from .storage import LocalStorageProvider
from .utils import slugify


DEFAULT_PAGES = {
    "index": "# {project} Wiki Index\n\n暂无资料。\n",
    "overview": "# {project} 项目总览\n\n暂无资料。\n",
    "requirements": "# {project} 需求与关注点\n\n- 暂无资料。\n",
    "risks": "# {project} 风险点\n\n- 暂无资料。\n",
    "commitments": "# {project} 承诺与待办\n\n- 暂无资料。\n",
    "decisions": "# {project} 决策记录\n\n- 暂无资料。\n",
    "people": "# {project} 相关人物\n\n- 暂无资料。\n",
    "open-questions": "# {project} 待确认问题\n\n- 暂无资料。\n",
    "sources": "# {project} 资料清单\n\n- 暂无资料。\n",
    "log": "# {project} 维护日志\n\n- 暂无记录。\n",
}

WIKI_PAGE_TITLES = {
    "index": "项目首页",
    "overview": "项目总览",
    "requirements": "需求与关注点",
    "risks": "风险点",
    "commitments": "承诺与待办",
    "decisions": "决策记录",
    "people": "相关人物",
    "open-questions": "待确认问题",
    "sources": "资料清单",
    "log": "维护日志",
}

WIKI_CONTRACT = {
    "goal": "Maintain a small project wiki from immutable source material; answer only from cited wiki evidence.",
    "pages": {
        "index": "Entry point, page map, answer rules, project status.",
        "overview": "Short current understanding of the project.",
        "requirements": "Needs, goals, preferences, scope, acceptance hints.",
        "risks": "Risks, blockers, unknowns, budget/legal/timeline concerns.",
        "commitments": "Promised actions, owners, dates, follow-ups.",
        "decisions": "Confirmed decisions and their source evidence.",
        "people": "People, teams, customers, roles.",
        "sources": "Source list with original links or local raw paths.",
        "open-questions": "Conflicts and questions that need user confirmation.",
        "log": "Small maintenance log, newest first.",
    },
    "rules": [
        "Keep pages short and useful for office work.",
        "Do not invent facts; preserve source title, source link, and line hint when available.",
        "If two facts conflict, write the conflict to open-questions instead of choosing silently.",
        "Use upsert_wiki_page for model-reviewed page patches; do not require a backend LLM key.",
    ],
}

def prepare_feishu_markdown(markdown: str) -> str:
    """Keep one top-level title for Feishu Docs Markdown import.

    Feishu derives the Docx title from the first H1. Extra H1 lines in body
    content can make imported pages show up as Untitled or with an unexpected
    title, so downgrade later H1 lines while leaving code fences untouched.
    """

    lines = markdown.splitlines(keepends=True)
    in_fence = False
    fence_marker = ""
    seen_h1 = False
    prepared: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""

        if not in_fence and line.startswith("# "):
            if seen_h1:
                prepared.append("### " + line[2:])
            else:
                prepared.append(line)
                seen_h1 = True
            continue
        prepared.append(line)
    return "".join(prepared)


class WorkMemoryToolkit:
    """Tool-level API for MCP hosts.

    This toolkit owns no LLM. The MCP host's model calls these tools, then
    composes answers only from the cited context returned by the tools.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.db = Database(data_dir / "state.sqlite")
        self.storage = LocalStorageProvider(data_dir)
        self.engine = WorkMemoryEngine(self.db, self.storage)

    def create_project_memory(self, workspace_id: str, project: str) -> dict[str, Any]:
        project_id = slugify(project, "default")
        for page_key, template in DEFAULT_PAGES.items():
            content = template.format(project=project)
            obj = self.storage.write_wiki_page(workspace_id, project_id, page_key, content)
            self.db.upsert_page(workspace_id, project_id, page_key, page_key, obj.uri)
        self.db.add_event(
            workspace_id,
            project_id,
            "project_memory_created",
            json.dumps({"project": project, "pages": list(DEFAULT_PAGES)}, ensure_ascii=False),
        )
        return {"project_id": project_id, "pages": list(DEFAULT_PAGES)}

    def list_project_memories(self, workspace_id: str) -> dict[str, Any]:
        return {"projects": self.engine.list_projects(workspace_id)}

    def get_project_index(self, workspace_id: str, project: str) -> dict[str, Any]:
        project_id = slugify(project, "default")
        pages = self.list_wiki_pages(workspace_id, project)["pages"]
        conflicts = self.detect_conflicts(workspace_id, project)["conflicts"]
        return {
            "project_id": project_id,
            "pages": pages,
            "open_conflict_count": len(conflicts),
            "rule": "Answer questions only after calling get_cited_context or query_project_wiki.",
            "schema": WIKI_CONTRACT,
        }

    def get_wiki_maintenance_contract(self) -> dict[str, Any]:
        return WIKI_CONTRACT

    def upsert_wiki_page(
        self,
        workspace_id: str,
        project: str,
        page_key: str,
        markdown: str,
        external_url: str = "",
    ) -> dict[str, Any]:
        project_id = slugify(project, "default")
        obj = self.storage.write_wiki_page(workspace_id, project_id, page_key, markdown)
        uri = external_url or obj.uri
        self.db.upsert_page(workspace_id, project_id, page_key, page_key, uri)
        self.db.add_event(
            workspace_id,
            project_id,
            "wiki_page_upserted",
            json.dumps({"page_key": page_key, "uri": uri}, ensure_ascii=False),
        )
        return {"project_id": project_id, "page_key": page_key, "uri": uri, "updated": True}

    def ingest_text(
        self,
        workspace_id: str,
        project: str,
        title: str,
        content: str,
        source_url: str = "",
    ) -> dict[str, Any]:
        title = title or "资料"
        result = self.engine.upload_content(
            workspace_id=workspace_id,
            project=project,
            title=title,
            content=content,
            filename=f"{slugify(title, 'source')}.txt",
            source_type="mcp_text",
            source_uri=source_url,
        )
        return {
            "project_id": result.project_id,
            "source_id": result.source_id,
            "message": result.message,
            "conflicts": result.conflicts,
        }

    def list_wiki_pages(self, workspace_id: str, project: str) -> dict[str, Any]:
        project_id = slugify(project, "default")
        rows = self.db.list_pages(workspace_id, project_id)
        return {
            "project_id": project_id,
            "pages": [
                {"page_key": row["page_key"], "title": row["title"], "uri": row["uri"]}
                for row in rows
            ],
        }

    def read_wiki_page(self, workspace_id: str, project: str, page_key: str) -> dict[str, Any]:
        content = self.engine.read_wiki_page(workspace_id, project, page_key)
        return {
            "project_id": slugify(project, "default"),
            "page_key": page_key,
            "content": content,
            "found": bool(content),
        }

    def get_feishu_wiki_sync_plan(
        self,
        workspace_id: str,
        project: str,
        root_title: str = "文档搭子知识库",
    ) -> dict[str, Any]:
        """Return wiki pages as Feishu-visible page write tasks.

        This does not call Feishu. A host AI should pass each page to the
        official Feishu MCP, Lark CLI, or future Docs add-on, then call
        upsert_wiki_page with the Feishu page URL as external_url.
        """

        project_id = slugify(project, "default")
        pages = self.storage.list_wiki_pages(workspace_id, project_id)
        page_rows = {
            row["page_key"]: row["uri"] for row in self.db.list_pages(workspace_id, project_id)
        }
        ordered_keys = [key for key in DEFAULT_PAGES if key in pages]
        ordered_keys.extend(sorted(key for key in pages if key not in DEFAULT_PAGES))
        return {
            "project_id": project_id,
            "target": {
                "type": "feishu_docs_or_wiki",
                "root_title": root_title,
                "project_title": project,
            },
            "instruction": (
                "Create or update these pages in Feishu Docs/Knowledge Base. "
                "After Feishu returns each page URL, call upsert_wiki_page with "
                "the same page_key, markdown, and external_url."
            ),
            "pages": [
                {
                    "page_key": page_key,
                    "title": WIKI_PAGE_TITLES.get(page_key, page_key),
                    "suggested_path": [
                        root_title,
                        project,
                        WIKI_PAGE_TITLES.get(page_key, page_key),
                    ],
                    "markdown": prepare_feishu_markdown(pages[page_key]),
                    "current_uri": page_rows.get(page_key, ""),
                    "has_external_url": page_rows.get(page_key, "").startswith(
                        ("http://", "https://")
                    ),
                    "action": "create_or_update",
                }
                for page_key in ordered_keys
            ],
            "after_sync": [
                "Keep Feishu page URLs in external_url so future citations point to Feishu.",
                "Keep WORK_MEMORY_DATA_DIR as cache, index, conflict state, and offline fallback.",
            ],
        }

    def get_cited_context(self, workspace_id: str, project: str, question: str) -> dict[str, Any]:
        answer = self.engine.ask(workspace_id=workspace_id, project=project, question=question)
        return {
            "project_id": answer.project_id,
            "evidence_only": True,
            "instruction": "Only answer from these citations. If citations is empty, say the wiki has no evidence.",
            "context": answer.answer,
            "sources": answer.sources,
            "citations": answer.citations,
        }

    def query_project_wiki(self, workspace_id: str, project: str, question: str) -> dict[str, Any]:
        return self.get_cited_context(workspace_id, project, question)

    def lint_project_wiki(self, workspace_id: str, project: str) -> dict[str, Any]:
        project_id = slugify(project, "default")
        pages = self.storage.list_wiki_pages(workspace_id, project_id)
        missing = [page for page in DEFAULT_PAGES if page not in pages]
        thin_pages = []
        for page_key, content in pages.items():
            meaningful = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#") and "暂无资料" not in line
            ]
            if not meaningful:
                thin_pages.append(page_key)
        conflicts = self.detect_conflicts(workspace_id, project)
        source_read_errors = self._source_read_errors(workspace_id, project_id)
        return {
            "project_id": project_id,
            "ok": not missing and not conflicts["conflicts"] and not source_read_errors,
            "missing_pages": missing,
            "thin_pages": thin_pages,
            "open_conflicts": conflicts["conflicts"],
            "source_read_errors": source_read_errors,
        }

    def detect_conflicts(self, workspace_id: str, project: str) -> dict[str, Any]:
        project_id = slugify(project, "default")
        rows = self.db.open_conflicts(workspace_id, project_id)
        return {
            "project_id": project_id,
            "conflicts": [
                {
                    "id": row["id"],
                    "key": row["conflict_key"],
                    "description": row["description"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        }

    def list_review_items(self, workspace_id: str, project: str) -> dict[str, Any]:
        lint = self.lint_project_wiki(workspace_id, project)
        items: list[dict[str, Any]] = []
        for conflict in lint["open_conflicts"]:
            items.append(
                {
                    "type": "conflict",
                    "id": conflict["id"],
                    "title": conflict["key"],
                    "description": conflict["description"],
                    "suggested_action": "Ask the user which version is correct, then call resolve_conflict.",
                }
            )
        for error in lint["source_read_errors"]:
            title = error.get("title") or "未知资料"
            items.append(
                {
                    "type": "source_read_error",
                    "id": error.get("id"),
                    "title": title,
                    "description": f"资料「{title}」的本地提取文本读取失败：{error.get('error') or 'unknown error'}",
                    "suggested_action": "Re-ingest the source material or restore the cached extracted text file.",
                    "source_id": error.get("source_id"),
                    "uri": error.get("uri"),
                    "text_path": error.get("text_path"),
                }
            )
        for page_key in lint["thin_pages"]:
            items.append(
                {
                    "type": "thin_page",
                    "page_key": page_key,
                    "description": f"{page_key} 还缺少有用内容。",
                    "suggested_action": "Add more source material or use upsert_wiki_page after reviewing evidence.",
                }
            )
        return {"project_id": lint["project_id"], "items": items}

    def _source_read_errors(self, workspace_id: str, project_id: str) -> list[dict[str, Any]]:
        rows = self.db.list_events(workspace_id, project_id, "source_text_read_failed", limit=20)
        errors: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            text_path = str(payload.get("text_path") or "")
            if text_path and Path(text_path).exists():
                continue
            key = str(payload.get("source_id") or text_path or row["id"])
            if key in seen:
                continue
            seen.add(key)
            errors.append(
                {
                    "id": row["id"],
                    "source_id": payload.get("source_id"),
                    "title": payload.get("title", "未知资料"),
                    "uri": payload.get("uri", ""),
                    "text_path": text_path,
                    "error": payload.get("error", ""),
                    "created_at": row["created_at"],
                }
            )
        return errors

    def resolve_conflict(
        self, workspace_id: str, project: str, conflict_id: int, resolution: str
    ) -> dict[str, Any]:
        project_id = slugify(project, "default")
        resolved = self.db.resolve_conflict(workspace_id, project_id, conflict_id, resolution)
        if resolved:
            self.db.add_event(
                workspace_id,
                project_id,
                "conflict_resolved",
                json.dumps({"conflict_id": conflict_id, "resolution": resolution}, ensure_ascii=False),
            )
        return {"project_id": project_id, "conflict_id": conflict_id, "resolved": resolved}


def create_default_toolkit() -> WorkMemoryToolkit:
    import os

    data_dir = Path(os.getenv("WORK_MEMORY_DATA_DIR", "data")).expanduser().resolve()
    return WorkMemoryToolkit(data_dir=data_dir)
