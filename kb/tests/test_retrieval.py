import unittest

from kb.retrieval import build_chunk_index, load_records, search_kb


class RetrievalTests(unittest.TestCase):
    def test_load_records(self):
        records = load_records()
        self.assertGreater(len(records), 0)
        self.assertIn("record_id", records[0])

    def test_chunk_index_build(self):
        index = build_chunk_index()
        self.assertGreater(len(index["chunks"]), 0)
        self.assertIn("chunk_id", index["chunks"][0])

    def test_search_for_policy(self):
        result = search_kb("late fee due date", category="policy")
        self.assertTrue(result["found"])
        self.assertGreater(len(result["results"]), 0)
        self.assertIn("record_id", result["results"][0])

    def test_search_for_negative_query(self):
        result = search_kb("solar panel refinancing guarantees", category="policy")
        self.assertFalse(result["found"])


if __name__ == "__main__":
    unittest.main()
