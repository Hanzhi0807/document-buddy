from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from work_memory.toolkit import WorkMemoryToolkit


class ToolkitSmokeTest(unittest.TestCase):
    def test_ingest_creates_cited_wiki_and_review_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书会议纪要",
                content="\n".join(
                    [
                        "参会人：张经理、李法务。",
                        "客户需要下周提供报价方案。",
                        "预算为10万。",
                        "预算为12万，需要确认。",
                    ]
                ),
                source_url="https://feishu.example/doc/meeting-1",
            )

            pages = toolkit.list_wiki_pages("tenant-a", "A客户项目")["pages"]
            page_keys = {page["page_key"] for page in pages}
            self.assertIn("index", page_keys)
            self.assertIn("log", page_keys)

            requirements = toolkit.read_wiki_page("tenant-a", "A客户项目", "requirements")
            self.assertIn("来源：飞书会议纪要 L2", requirements["content"])
            self.assertIn("https://feishu.example/doc/meeting-1", requirements["content"])

            answer = toolkit.query_project_wiki("tenant-a", "A客户项目", "客户需要什么？")
            self.assertTrue(answer["citations"])
            self.assertIn("requirements", answer["sources"])

            conflicts = toolkit.detect_conflicts("tenant-a", "A客户项目")["conflicts"]
            self.assertEqual(1, len(conflicts))
            review = toolkit.list_review_items("tenant-a", "A客户项目")
            self.assertTrue(any(item["type"] == "conflict" for item in review["items"]))

            resolved = toolkit.resolve_conflict(
                "tenant-a",
                "A客户项目",
                conflicts[0]["id"],
                "以12万预算为准。",
            )
            self.assertTrue(resolved["resolved"])
            self.assertEqual([], toolkit.detect_conflicts("tenant-a", "A客户项目")["conflicts"])


if __name__ == "__main__":
    unittest.main()
