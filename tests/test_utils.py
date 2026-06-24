from __future__ import annotations

import unittest

from work_memory.utils import money_mentions


class UtilsTest(unittest.TestCase):
    def test_money_mentions_ignore_dates_and_times(self) -> None:
        text = "会议时间：2026-06-24 10:00。预算暂按 10 万元，可能改成 12 万元。"
        self.assertEqual(["预算暂按10万元", "可能改成12万元"], money_mentions(text))


if __name__ == "__main__":
    unittest.main()
