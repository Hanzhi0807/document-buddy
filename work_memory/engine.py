from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

from .compiler import compile_project_memory
from .db import Database
from .extractors import extract_text
from .storage import StorageProvider
from .utils import compact_text, sha256_bytes, slugify, utc_now


@dataclass(frozen=True)
class UploadResult:
    project_id: str
    source_id: int
    message: str
    conflicts: list[str]


@dataclass(frozen=True)
class AnswerResult:
    project_id: str
    answer: str
    sources: list[str]


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
            uri=raw.uri,
            text_path=text_obj.uri,
        )
        self.db.add_event(
            workspace_id,
            project_id,
            "content_submitted",
            json.dumps({"title": title, "uri": raw.uri}, ensure_ascii=False),
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
                text = open(row["text_path"], encoding="utf-8").read()
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
        compiled = compile_project_memory(project_id, sources, existing)
        for page_key, content in compiled.pages.items():
            obj = self.storage.write_wiki_page(workspace_id, project_id, page_key, content)
            self.db.upsert_page(workspace_id, project_id, page_key, page_key, obj.uri)
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
            answer = "我还没有这个项目的资料。先把会议纪要、文档、链接或聊天摘录发给我。"
            return AnswerResult(project_id=project_id, answer=answer, sources=[])

        ranked = self._rank_pages(question, pages)
        conflicts = self.db.open_conflicts(workspace_id, project_id)
        answer = self._compose_answer(project_id, question, ranked, [row["description"] for row in conflicts])
        sources = [page for page, _score, _text in ranked[:4]]
        self.db.add_conversation(workspace_id, project_id, question, answer)
        self.db.add_event(
            workspace_id,
            project_id,
            "question_answered",
            json.dumps({"question": question, "sources": sources}, ensure_ascii=False),
        )
        return AnswerResult(project_id=project_id, answer=answer, sources=sources)

    def list_projects(self, workspace_id: str) -> list[str]:
        return self.db.list_projects(workspace_id)

    def _rank_pages(self, question: str, pages: dict[str, str]) -> list[tuple[str, int, str]]:
        terms = [term for term in re.split(r"\W+", question.lower()) if term]
        ranked: list[tuple[str, int, str]] = []
        for key, text in pages.items():
            lowered = text.lower()
            score = sum(lowered.count(term) for term in terms)
            if key in question.lower():
                score += 5
            ranked.append((key, score, text))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _compose_answer(
        self,
        project_id: str,
        question: str,
        ranked: list[tuple[str, int, str]],
        conflicts: list[str],
    ) -> str:
        joined = "\n\n".join(text for _key, _score, text in ranked[:4])
        q = question.lower()
        if any(word in question for word in ["周报", "汇报", "进展"]):
            opening = f"「{project_id}」本周可以这样汇报："
            focus = self._section_answer(joined, ["需求", "风险", "承诺", "决策"])
        elif any(word in question for word in ["会议", "开会", "准备"]):
            opening = f"和「{project_id}」开会前，建议先看这几件事："
            focus = self._section_answer(joined, ["需求", "风险", "承诺"])
        elif any(word in question for word in ["风险", "卡", "问题"]):
            opening = f"「{project_id}」当前风险主要是："
            focus = self._section_answer(joined, ["风险", "预算", "延期", "法务"])
        elif "邮件" in question or "email" in q:
            opening = f"可以基于「{project_id}」当前记忆写这封邮件："
            focus = "您好，\n\n根据我们最近沟通的信息，我整理了当前重点、待确认事项和下一步建议。请您确认是否准确。\n\n"
            focus += self._section_answer(joined, ["需求", "承诺", "风险"])
        else:
            opening = f"根据「{project_id}」目前的项目记忆，我的回答是："
            focus = self._section_answer(joined, [])

        conflict_text = ""
        if conflicts:
            conflict_text = "\n\n需要你确认：\n" + "\n".join(f"- {item}" for item in conflicts[:3])

        citation_text = "\n\n参考的项目记忆页：" + "、".join(page for page, _score, _text in ranked[:4])
        return opening + "\n\n" + focus + conflict_text + citation_text

    def _section_answer(self, text: str, hints: list[str]) -> str:
        lines = []
        for line in text.splitlines():
            clean = line.strip(" -")
            if not clean or clean.startswith("#") or clean.startswith("更新时间"):
                continue
            if hints and not any(hint in clean for hint in hints):
                continue
            lines.append(compact_text(clean, 220))
            if len(lines) >= 6:
                break
        if not lines:
            for line in text.splitlines():
                clean = line.strip(" -")
                if clean and not clean.startswith("#") and not clean.startswith("更新时间"):
                    lines.append(compact_text(clean, 220))
                if len(lines) >= 6:
                    break
        if not lines:
            return "目前资料还不够，我没有找到可靠答案。你可以继续发会议纪要、文档或聊天摘录给我。"
        return "\n".join(f"- {line}" for line in lines)
