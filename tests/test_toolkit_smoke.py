from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from work_memory.toolkit import WorkMemoryToolkit, prepare_feishu_markdown


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

            sync_plan = toolkit.get_feishu_wiki_sync_plan("tenant-a", "A客户项目")
            self.assertEqual("feishu_docs_or_wiki", sync_plan["target"]["type"])
            self.assertEqual("文档搭子知识库", sync_plan["target"]["root_title"])
            requirements_task = next(
                page for page in sync_plan["pages"] if page["page_key"] == "requirements"
            )
            self.assertEqual(
                ["文档搭子知识库", "A客户项目", "需求与关注点"],
                requirements_task["suggested_path"],
            )
            self.assertIn("客户需要下周提供报价方案", requirements_task["markdown"])

            toolkit.upsert_wiki_page(
                "tenant-a",
                "A客户项目",
                "requirements",
                requirements["content"],
                external_url="https://feishu.example/wiki/a-client/requirements",
            )
            toolkit.ingest_text(
                workspace_id="tenant-a",
                project="A客户项目",
                title="飞书跟进消息",
                content="客户需要周五确认联系人。",
                source_url="https://feishu.example/message/follow-up",
            )
            page_map = {
                page["page_key"]: page
                for page in toolkit.list_wiki_pages("tenant-a", "A客户项目")["pages"]
            }
            self.assertEqual(
                "https://feishu.example/wiki/a-client/requirements",
                page_map["requirements"]["uri"],
            )

            answer = toolkit.query_project_wiki("tenant-a", "A客户项目", "客户需要什么？")
            self.assertTrue(answer["citations"])
            self.assertIn("requirements", answer["sources"])
            self.assertTrue(
                any(
                    "https://feishu.example/wiki/a-client/requirements" in citation
                    for citation in answer["citations"]
                )
            )

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

    def test_prepare_feishu_markdown_keeps_one_h1(self) -> None:
        markdown = "\n".join(
            [
                "# 项目总览",
                "",
                "## 当前理解",
                "",
                "```md",
                "# code fence heading stays literal",
                "```",
                "# 来源文档标题",
            ]
        )

        prepared = prepare_feishu_markdown(markdown)

        self.assertIn("# 项目总览", prepared)
        self.assertIn("# code fence heading stays literal", prepared)
        self.assertIn("### 来源文档标题", prepared)
        body_h1_lines = [line for line in prepared.splitlines() if line == "# 来源文档标题"]
        self.assertEqual([], body_h1_lines)

    def test_feishu_sync_plan_uses_safe_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.upsert_wiki_page(
                workspace_id="tenant-a",
                project="A客户项目",
                page_key="overview",
                markdown="# A客户项目 项目总览\n\n# 飞书原文标题\n\n客户需要报价方案。\n",
            )

            sync_plan = toolkit.get_feishu_wiki_sync_plan("tenant-a", "A客户项目")
            overview = next(page for page in sync_plan["pages"] if page["page_key"] == "overview")

            self.assertIn("### 飞书原文标题", overview["markdown"])
            self.assertNotIn("\n# 飞书原文标题", overview["markdown"])

    def test_query_uses_bm25_line_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.upsert_wiki_page(
                workspace_id="tenant-a",
                project="A客户项目",
                page_key="requirements",
                markdown="\n".join(
                    [
                        "# A客户项目 需求与关注点",
                        "",
                        "- 客户需要周五前看到报价方案。",
                        "- 客户关注部署培训安排。",
                        "- 客户希望页面用蓝色。",
                    ]
                ),
            )

            answer = toolkit.query_project_wiki("tenant-a", "A客户项目", "客户培训")
            bullet_lines = [
                line for line in answer["context"].splitlines() if line.startswith("- ")
            ]

            self.assertTrue(bullet_lines)
            self.assertIn("部署培训", bullet_lines[0])
            self.assertTrue(answer["citations"])

    def test_query_empty_wiki_returns_no_citations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))

            answer = toolkit.query_project_wiki("tenant-a", "空项目", "客户需要什么？")

            self.assertEqual([], answer["citations"])
            self.assertIn("还没有这个项目", answer["context"])

    def test_query_single_page_wiki_returns_citation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit = WorkMemoryToolkit(Path(tmp))
            toolkit.upsert_wiki_page(
                workspace_id="tenant-a",
                project="单页项目",
                page_key="overview",
                markdown="\n".join(
                    [
                        "# 单页项目 项目总览",
                        "",
                        "客户需要周五前收到报价方案。",
                    ]
                ),
            )

            answer = toolkit.query_project_wiki("tenant-a", "单页项目", "报价方案")

            self.assertTrue(answer["citations"])
            self.assertIn("报价方案", answer["context"])


if __name__ == "__main__":
    unittest.main()
