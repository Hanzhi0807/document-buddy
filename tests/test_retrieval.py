from __future__ import annotations

import unittest

from work_memory.retrieval import SearchDocument, rank_bm25, tokenize_search_text


class RetrievalTest(unittest.TestCase):
    def test_chinese_tokenizer_keeps_searchable_chunks(self) -> None:
        tokens = tokenize_search_text("客户关注部署培训安排")
        self.assertIn("部署", tokens)
        self.assertIn("培训", tokens)
        self.assertIn("部署培", tokens)

    def test_bm25_ranks_specific_chinese_match_first(self) -> None:
        documents = [
            SearchDocument("quote", "客户需要周五前看到报价方案"),
            SearchDocument("training", "客户关注部署培训安排"),
            SearchDocument("color", "客户希望页面用蓝色"),
        ]

        ranked = rank_bm25("客户培训", documents)

        self.assertTrue(ranked)
        self.assertEqual("training", ranked[0][0].doc_id)

    def test_empty_inputs_return_no_results_unless_requested(self) -> None:
        documents = [SearchDocument("one", "客户需要报价")]

        self.assertEqual([], rank_bm25("客户", []))
        self.assertEqual([], rank_bm25("", documents))
        zero_ranked = [
            (doc.doc_id, score)
            for doc, score in rank_bm25("", documents, include_zero=True)
        ]
        self.assertEqual([("one", 0.0)], zero_ranked)

    def test_bm25_handles_single_document(self) -> None:
        documents = [SearchDocument("only", "客户关注部署培训安排")]

        ranked = rank_bm25("部署培训", documents)

        self.assertEqual(1, len(ranked))
        self.assertEqual("only", ranked[0][0].doc_id)
        self.assertGreater(ranked[0][1], 0)

    def test_bm25_handles_mixed_chinese_and_english(self) -> None:
        documents = [
            SearchDocument("pricing", "客户需要新版报价方案"),
            SearchDocument("rollout", "Need rollout training by Friday，客户要培训计划"),
            SearchDocument("legal", "DPA legal review is pending"),
        ]

        ranked = rank_bm25("training Friday 培训", documents)

        self.assertTrue(ranked)
        self.assertEqual("rollout", ranked[0][0].doc_id)

    def test_short_specific_line_beats_long_loose_match(self) -> None:
        long_text = "客户 " * 120 + "培训 " + "背景资料 " * 80
        documents = [
            SearchDocument("long", long_text),
            SearchDocument("short", "部署培训安排"),
        ]

        ranked = rank_bm25("部署培训", documents)

        self.assertEqual("short", ranked[0][0].doc_id)


if __name__ == "__main__":
    unittest.main()