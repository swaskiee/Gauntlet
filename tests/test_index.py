"""Unit tests for Phase 3 - REALITY (Bloom filter & Index Engine)."""

import unittest
from pathlib import Path
from gauntlet.index.engine import BloomFilter, IndexEngine
from gauntlet.storage.segment import SegmentMetadata


class TestIndexEngine(unittest.TestCase):

    def test_bloom_filter(self) -> None:
        bloom = BloomFilter(size_bits=256, hash_count=3)
        bloom.add("server-42")
        bloom.add("server-88")

        self.assertTrue(bloom.contains("server-42"))
        self.assertTrue(bloom.contains("server-88"))
        self.assertFalse(bloom.contains("server-999_not_present"))

    def test_index_candidate_pruning(self) -> None:
        idx = IndexEngine()
        meta1 = SegmentMetadata(
            segment_id="seg-1",
            path=Path("seg-1.gt"),
            min_ts=1000,
            max_ts=2000,
            min_seq=1,
            max_seq=10,
            record_count=10,
            index_offset=100,
            index_count=1,
            entities={"server-1", "server-2"},
            event_types={"cpu"}
        )
        meta2 = SegmentMetadata(
            segment_id="seg-2",
            path=Path("seg-2.gt"),
            min_ts=3000,
            max_ts=4000,
            min_seq=11,
            max_seq=20,
            record_count=10,
            index_offset=100,
            index_count=1,
            entities={"server-3"},
            event_types={"memory"}
        )
        idx.register_segment(meta1)
        idx.register_segment(meta2)

        # Lookup server-1 -> only seg-1
        res1 = idx.find_candidate_segments(entity="server-1")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0].segment_id, "seg-1")

        # Lookup time range 3500-3600 -> only seg-2
        res2 = idx.find_candidate_segments(start_ts=3500, end_ts=3600)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0].segment_id, "seg-2")

        # Lookup non-existent entity
        res3 = idx.find_candidate_segments(entity="server-99")
        self.assertEqual(len(res3), 0)


if __name__ == "__main__":
    unittest.main()
