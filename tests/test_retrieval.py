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


if __name__ == "__main__":
    unittest.main()