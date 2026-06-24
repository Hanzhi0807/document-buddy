from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from work_memory.toolkit import WorkMemoryToolkit


class ToolkitEdgeCasesTest(unittest.TestCase):
    def test_duplicate_source_ingest_reuses_source_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            first = toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书会议纪要",
                content="客户需要周五前收到报价方案。",
                source_url="https://feishu.example/doc/meeting-1",
            )
            second = toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书会议纪要",
                content="客户需要周五前收到报价方案。",
                source_url="https://feishu.example/doc/meeting-1",
            )

            sources = toolkit.db.list_sources("tenant-a", first["project_id"])

            self.assertEqual(first["source_id"], second["source_id"])
            self.assertEqual(1, len(sources))

    def test_empty_content_ingest_does_not_hallucinate_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.ingest_text(
                workspace_id="tenant-a",
                project="空资料项目",
                title="空资料",
                content="",
                source_url="https://feishu.example/doc/empty",
            )

            answer = toolkit.query_project_wiki("tenant-a", "空资料项目", "预算是多少？")

            self.assertEqual([], answer["citations"])
            self.assertIn("没有可引用内容", answer["context"])

    def test_query_no_match_returns_no_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.upsert_wiki_page(
                workspace_id="tenant-a",
                project="A客户项目",
                page_key="overview",
                markdown="客户需要周五前收到报价方案。",
            )

            answer = toolkit.query_project_wiki("tenant-a", "A客户项目", "法务合同状态？")

            self.assertEqual([], answer["citations"])
            self.assertIn("没有可引用内容", answer["context"])

    def test_unicode_and_mixed_language_ingest_stays_searchable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.ingest_text(
                workspace_id="tenant-a",
                project="混合语言项目",
                title="Mixed update",
                content="Need rollout training by Friday。客户需要培训计划 😊。日本語メモ。",
                source_url="https://feishu.example/doc/mixed",
            )

            answer = toolkit.query_project_wiki("tenant-a", "混合语言项目", "rollout training 培训")

            self.assertTrue(answer["citations"])
            self.assertIn("training", answer["context"].lower())

    def test_large_source_ingest_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            filler = "背景资料。" * 6000
            content = filler + "\n客户需要周五提供上线培训计划。\n" + filler
            toolkit.ingest_text(
                workspace_id="tenant-a",
                project="大资料项目",
                title="长会议纪要",
                content=content,
                source_url="https://feishu.example/doc/large",
            )

            answer = toolkit.query_project_wiki("tenant-a", "大资料项目", "上线培训计划")

            self.assertTrue(answer["citations"])
            self.assertIn("上线培训", answer["context"])

    def test_missing_extracted_source_file_becomes_review_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            result = toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书会议纪要",
                content="客户需要周五前收到报价方案。",
                source_url="https://feishu.example/doc/meeting-1",
            )
            source = toolkit.db.list_sources("tenant-a", result["project_id"])[0]
            Path(source["text_path"]).unlink()

            toolkit.engine.maintain_project("tenant-a", result["project_id"])
            lint = toolkit.lint_project_wiki("tenant-a", "A客户项目")
            review = toolkit.list_review_items("tenant-a", "A客户项目")

            self.assertFalse(lint["ok"])
            self.assertEqual(1, len(lint["source_read_errors"]))
            self.assertTrue(any(item["type"] == "source_read_error" for item in review["items"]))

    def test_reingest_restored_source_clears_read_error_review_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            result = toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书会议纪要",
                content="客户需要周五前收到报价方案。",
                source_url="https://feishu.example/doc/meeting-1",
            )
            source = toolkit.db.list_sources("tenant-a", result["project_id"])[0]
            Path(source["text_path"]).unlink()
            toolkit.engine.maintain_project("tenant-a", result["project_id"])
            self.assertTrue(
                any(
                    item["type"] == "source_read_error"
                    for item in toolkit.list_review_items("tenant-a", "A客户项目")["items"]
                )
            )

            toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书会议纪要",
                content="客户需要周五前收到报价方案。",
                source_url="https://feishu.example/doc/meeting-1",
            )

            review = toolkit.list_review_items("tenant-a", "A客户项目")
            self.assertFalse(any(item["type"] == "source_read_error" for item in review["items"]))


if __name__ == "__main__":
    unittest.main()
