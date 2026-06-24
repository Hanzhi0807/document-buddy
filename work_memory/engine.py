from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from urllib.parse import quote

from .compiler import compile_project_memory
from .db import Database
from .extractors import extract_text
from .storage import StorageProvider
from .utils import compact_text, sha256_bytes, slugify


@dataclass(frozen=True)
class UploadResult:
    project_id: str
    source_id: int
    message: str
    conflicts: list[str]


@dataclass(frozen=True)
class Evidence:
    page_key: str
    line_no: int
    text: str
    link: str


@dataclass(frozen=True)
class AnswerResult:
    project_id: str
    answer: str
    sources: list[str]
    citations: list[str]


class WorkMemoryEngine:
    def __init__(self, db: Database, storage: StorageProvider):
        self.db = db
        self.storage = storage

    def upload_content(
        self,
        workspace_id: str,
        project: str,
        title: str,
        content: str,
        filename: str = "note.txt",
        source_type: str = "text",
        source_uri: str = "",
    ) -> UploadResult:
        project_id = slugify(project, "default")
        data = content.encode("utf-8")
        source_hash = sha256_bytes(data)
        raw = self.storage.save_raw(workspace_id, project_id, source_hash, filename, data)
        extracted = extract_text(filename, data)
        text_obj = self.storage.save_extracted_text(workspace_id, project_id, source_hash, extracted)
        source_id = self.db.upsert_source(
            workspace_id=workspace_id,
            project_id=project_id,
            title=title or filename,
            source_type=source_type,
            source_hash=source_hash,
            uri=source_uri or raw.uri,
            text_path=text_obj.uri,
        )
        self.db.add_event(
            workspace_id,
            project_id,
            "content_submitted",
            json.dumps({"title": title, "raw_uri": raw.uri, "source_uri": source_uri}, ensure_ascii=False),
        )
        maintain_message, conflicts = self.maintain_project(workspace_id, project_id)
        return UploadResult(
            project_id=project_id,
            source_id=source_id,
            message=f"已收到并整理到「{project}」。{maintain_message}",
            conflicts=conflicts,
        )

    def upload_file_base64(
        self,
        workspace_id: str,
        project: str,
        title: str,
        filename: str,
        data_base64: str,
    ) -> UploadResult:
        data = base64.b64decode(data_base64)
        project_id = slugify(project, "default")
        source_hash = sha256_bytes(data)
        raw = self.storage.save_raw(workspace_id, project_id, source_hash, filename, data)
        extracted = extract_text(filename, data)
        text_obj = self.storage.save_extracted_text(workspace_id, project_id, source_hash, extracted)
        source_id = self.db.upsert_source(
            workspace_id=workspace_id,
            project_id=project_id,
            title=title or filename,
            source_type="file",
            source_hash=source_hash,
            uri=raw.uri,
            text_path=text_obj.uri,
        )
        self.db.add_event(
            workspace_id,
            project_id,
            "file_submitted",
            json.dumps({"filename": filename, "uri": raw.uri}, ensure_ascii=False),
        )
        maintain_message, conflicts = self.maintain_project(workspace_id, project_id)
        return UploadResult(
            project_id=project_id,
            source_id=source_id,
            message=f"已收到文件「{filename}」，并整理到「{project}」。{maintain_message}",
            conflicts=conflicts,
        )

    def maintain_project(self, workspace_id: str, project_id: str) -> tuple[str, list[str]]:
        source_rows = self.db.list_sources(workspace_id, project_id)
        sources: list[dict[str, str]] = []
        for row in source_rows:
            try:
                with open(row["text_path"], encoding="utf-8") as source_file:
                    text = source_file.read()
            except OSError:
                text = ""
            sources.append(
                {
                    "title": row["title"],
                    "uri": row["uri"],
                    "text": text,
                    "created_at": row["created_at"],
                }
            )
        existing = self.storage.list_wiki_pages(workspace_id, project_id)
        page_links = {row["page_key"]: row["uri"] for row in self.db.list_pages(workspace_id, project_id)}
        compiled = compile_project_memory(project_id, sources, existing)
        for page_key, content in compiled.pages.items():
            obj = self.storage.write_wiki_page(workspace_id, project_id, page_key, content)
            existing_uri = page_links.get(page_key, "")
            uri = existing_uri if existing_uri.startswith(("http://", "https://")) else obj.uri
            self.db.upsert_page(workspace_id, project_id, page_key, page_key, uri)
        self.db.upsert_conflicts(workspace_id, project_id, compiled.conflicts)
        self.db.add_event(
            workspace_id,
            project_id,
            "maintenance_completed",
            json.dumps({"summary": compiled.summary}, ensure_ascii=False),
        )
        return compiled.summary, [description for _, description in compiled.conflicts]

    def ask(self, workspace_id: str, project: str, question: str) -> AnswerResult:
        project_id = slugify(project, "default")
        pages = self.storage.list_wiki_pages(workspace_id, project_id)
        if not pages:
            answer = "文档搭子还没有这个项目的 wiki 资料。先把会议纪要、文档、链接或聊天摘录发给我。"
            return AnswerResult(project_id=project_id, answer=answer, sources=[], citations=[])

        page_links = {row["page_key"]: row["uri"] for row in self.db.list_pages(workspace_id, project_id)}
        ranked = self._rank_pages(question, pages)
        evidence = self._collect_evidence(workspace_id, project_id, question, ranked, page_links)
        if not evidence:
            answer = self._no_evidence_answer(project_id)
            self.db.add_conversation(workspace_id, project_id, question, answer)
            return AnswerResult(project_id=project_id, answer=answer, sources=[], citations=[])

        answer = self._compose_cited_answer(project_id, question, evidence)
        sources = self._unique([item.page_key for item in evidence])
        citations = self._unique([self._citation(item) for item in evidence])
        self.db.add_conversation(workspace_id, project_id, question, answer)
        self.db.add_event(
            workspace_id,
            project_id,
            "question_answered",
            json.dumps({"question": question, "sources": sources, "citations": citations}, ensure_ascii=False),
        )
        return AnswerResult(project_id=project_id, answer=answer, sources=sources, citations=citations)

    def list_projects(self, workspace_id: str) -> list[str]:
        return self.db.list_projects(workspace_id)

    def read_wiki_page(self, workspace_id: str, project: str, page_key: str) -> str:
        return self.storage.read_wiki_page(workspace_id, slugify(project, "default"), page_key)

    def _rank_pages(self, question: str, pages: dict[str, str]) -> list[tuple[str, int, str]]:
        terms = self._question_terms(question)
        ranked: list[tuple[str, int, str]] = []
        for key, text in pages.items():
            lowered = text.lower()
            score = sum(lowered.count(term.lower()) for term in terms)
            if key in question.lower():
                score += 5
            ranked.append((key, score, text))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _collect_evidence(
        self,
        workspace_id: str,
        project_id: str,
        question: str,
        ranked: list[tuple[str, int, str]],
        page_links: dict[str, str],
    ) -> list[Evidence]:
        preferred_pages = self._preferred_pages(question)
        ranked_by_key = {page_key: (score, text) for page_key, score, text in ranked}
        ordered: list[tuple[str, int, str]] = []
        for page_key in preferred_pages:
            if page_key in ranked_by_key:
                score, text = ranked_by_key[page_key]
                ordered.append((page_key, score + 10, text))
        for page_key, score, text in ranked:
            if page_key not in preferred_pages:
                ordered.append((page_key, score, text))

        terms = self._question_terms(question)
        evidence: list[Evidence] = []
        for page_key, score, text in ordered:
            allow_general = page_key in preferred_pages or score > 0
            if not allow_general:
                continue
            for line_no, raw_line in enumerate(text.splitlines(), start=1):
                clean = self._clean_wiki_line(raw_line)
                if not clean:
                    continue
                if page_key not in preferred_pages and terms:
                    lowered = clean.lower()
                    if not any(term.lower() in lowered for term in terms):
                        continue
                evidence.append(
                    Evidence(
                        page_key=page_key,
                        line_no=line_no,
                        text=compact_text(clean, 240),
                        link=self._page_link(workspace_id, project_id, page_key, page_links),
                    )
                )
                if len([item for item in evidence if item.page_key == page_key]) >= 2:
                    break
            if len(evidence) >= 8:
                break
        return evidence[:8]

    def _preferred_pages(self, question: str) -> list[str]:
        if any(word in question for word in ["周报", "汇报", "进展", "复盘"]):
            return ["overview", "decisions", "commitments", "risks", "open-questions"]
        if any(word in question for word in ["会议", "开会", "准备", "会前"]):
            return ["commitments", "risks", "requirements", "open-questions", "decisions"]
        if any(word in question for word in ["风险", "卡", "问题", "冲突"]):
            return ["risks", "open-questions", "commitments"]
        if any(word in question for word in ["邮件", "email", "跟进"]):
            return ["requirements", "commitments", "risks", "decisions"]
        return []

    def _compose_cited_answer(self, project_id: str, question: str, evidence: list[Evidence]) -> str:
        if any(word in question for word in ["周报", "汇报", "进展", "复盘"]):
            heading = "可确认的周报素材"
        elif any(word in question for word in ["会议", "开会", "准备", "会前"]):
            heading = "开会前可确认的要点"
        elif any(word in question for word in ["风险", "卡", "问题", "冲突"]):
            heading = "wiki 中可确认的风险/问题"
        elif any(word in question for word in ["邮件", "email", "跟进"]):
            heading = "可用于邮件的确认信息"
        else:
            heading = "wiki 中可确认的信息"

        lines = [
            f"我只根据「{project_id}」wiki 里能确认的信息回答；wiki 没有的内容不补编。",
            "",
            f"{heading}：",
        ]
        for item in evidence:
            lines.append(f"- {item.text} {self._citation(item)}")
        lines.append("")
        lines.append("引用页：" + "、".join(self._unique([self._page_reference(item) for item in evidence])))
        return "\n".join(lines)

    def _no_evidence_answer(self, project_id: str) -> str:
        return (
            f"我只能根据「{project_id}」wiki 回答。当前 wiki 没有可引用内容支持这个问题，"
            "所以我不编造答案。请补充会议纪要、文档、聊天摘录或网页链接后再问。"
        )

    def _clean_wiki_line(self, line: str) -> str:
        clean = line.strip()
        clean = clean.removeprefix("- ").strip()
        if not clean:
            return ""
        if clean.startswith("#") or clean.startswith("更新时间"):
            return ""
        if clean.startswith("暂无") or "还没有明确提取" in clean:
            return ""
        return clean

    def _question_terms(self, question: str) -> list[str]:
        terms = [term for term in re.split(r"\W+", question.lower()) if len(term) > 1]
        cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", question)
        for term in cjk_terms:
            if term not in terms:
                terms.append(term)
            for size in (2, 3):
                for idx in range(0, max(len(term) - size + 1, 0)):
                    chunk = term[idx : idx + size]
                    if chunk not in terms:
                        terms.append(chunk)
        return terms

    def _page_link(
        self,
        workspace_id: str,
        project_id: str,
        page_key: str,
        page_links: dict[str, str],
    ) -> str:
        uri = page_links.get(page_key, "")
        if uri.startswith("http://") or uri.startswith("https://"):
            return uri
        return f"wiki://{quote(workspace_id)}/{quote(project_id)}/{quote(page_key)}"

    def _citation(self, evidence: Evidence) -> str:
        return f"[{evidence.page_key}:L{evidence.line_no}]({evidence.link}#L{evidence.line_no})"

    def _page_reference(self, evidence: Evidence) -> str:
        return f"[{evidence.page_key}]({evidence.link})"

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        unique_items: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)
        return unique_items
