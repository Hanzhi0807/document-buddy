from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import Database
from .engine import WorkMemoryEngine
from .storage import LocalStorageProvider
from .utils import slugify


DEFAULT_PAGES = {
    "overview": "# {project} 项目总览\n\n暂无资料。\n",
    "requirements": "# {project} 需求与关注点\n\n- 暂无资料。\n",
    "risks": "# {project} 风险点\n\n- 暂无资料。\n",
    "commitments": "# {project} 承诺与待办\n\n- 暂无资料。\n",
    "decisions": "# {project} 决策记录\n\n- 暂无资料。\n",
    "open-questions": "# {project} 待确认问题\n\n- 暂无资料。\n",
    "sources": "# {project} 资料清单\n\n- 暂无资料。\n",
}


class WorkMemoryToolkit:
    """Tool-level API for MCP hosts.

    This toolkit owns no LLM. The MCP host's model calls these tools, then
    composes answers only from the cited context returned by the tools.
    """

    def __init__(self, data_dir: Path, citation_base_url: str = ""):
        self.data_dir = data_dir
        self.db = Database(data_dir / "state.sqlite")
        self.storage = LocalStorageProvider(data_dir)
        self.engine = WorkMemoryEngine(self.db, self.storage, citation_base_url=citation_base_url)

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
        }

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
        if source_url:
            content = f"{content}\n\n来源链接：{source_url}"
        result = self.engine.upload_content(
            workspace_id=workspace_id,
            project=project,
            title=title,
            content=content,
            filename=f"{slugify(title, 'source')}.txt",
            source_type="mcp_text",
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
        return {
            "project_id": project_id,
            "ok": not missing,
            "missing_pages": missing,
            "thin_pages": thin_pages,
            "open_conflicts": conflicts["conflicts"],
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


def create_default_toolkit() -> WorkMemoryToolkit:
    import os

    data_dir = Path(os.getenv("WORK_MEMORY_DATA_DIR", "data")).expanduser().resolve()
    citation_base_url = os.getenv("WORK_MEMORY_PUBLIC_BASE_URL", "")
    return WorkMemoryToolkit(data_dir=data_dir, citation_base_url=citation_base_url)
