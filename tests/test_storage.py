"""Unit tests for Phase 2 - SPACE (Storage Engine, Segments, Compaction, Recovery)."""

import shutil
import tempfile
import unittest
from pathlib import Path
from gauntlet.models import Event
from gauntlet.storage.engine import StorageEngine


class TestStorageEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_write_and_scan(self) -> None:
        engine = StorageEngine(self.test_dir, memtable_max_events=10)
        events = [
            Event(event_id=f"e{i}", entity="server-1", timestamp=1000 + i * 5, type="cpu", value=40.0 + i, sequence_num=i+1)
            for i in range(5)
        ]
        for e in events:
            engine.write(e)

        scanned = list(engine.scan(entity="server-1"))
        self.assertEqual(len(scanned), 5)
        self.assertEqual(scanned[0].event_id, "e0")
        self.assertEqual(scanned[-1].event_id, "e4")
        engine.close()

    def test_memtable_flush_to_segment(self) -> None:
        # max 3 events per memtable to trigger auto-flush
        engine = StorageEngine(self.test_dir, memtable_max_events=3)
        events = [
            Event(event_id=f"e{i}", entity="server-1", timestamp=1000 + i * 5, type="cpu", value=50.0 + i, sequence_num=i+1)
            for i in range(7)
        ]
        for e in events:
            engine.write(e)

        # 7 events with threshold 3 -> 2 flushed segments (3+3) + 1 in memtable
        self.assertEqual(len(engine.segments), 2)
        self.assertEqual(len(engine.memtable), 1)

        # Scan should seamlessly yield all 7 events across segments and memtable
        all_scanned = list(engine.scan(entity="server-1"))
        self.assertEqual(len(all_scanned), 7)

        # Integrity verification
        health = engine.verify_integrity()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertEqual(health["checksums_valid"], "2/2")
        self.assertEqual(health["total_records"], 7)
        engine.close()

    def test_compaction(self) -> None:
        engine = StorageEngine(self.test_dir, memtable_max_events=2)
        for i in range(6):
            engine.write(Event(event_id=f"e{i}", entity="server-1", timestamp=1000 + i * 5, type="cpu", value=20.0 + i, sequence_num=i+1))

        self.assertEqual(len(engine.segments), 3)

        # Compact all 3 segments into 1
        compacted = engine.compact(target_segments_count=2)
        self.assertIsNotNone(compacted)
        self.assertEqual(len(engine.segments), 1)
        self.assertEqual(engine.segments[0].record_count, 6)

        scanned = list(engine.scan(entity="server-1"))
        self.assertEqual(len(scanned), 6)
        engine.close()

    def test_crash_restart_and_recovery(self) -> None:
        engine = StorageEngine(self.test_dir, memtable_max_events=100)
        e1 = Event(event_id="e1", entity="server-1", timestamp=1000, type="cpu", value=42.0, sequence_num=1)
        e2 = Event(event_id="e2", entity="server-1", timestamp=1005, type="cpu", value=44.0, sequence_num=2)
        engine.write(e1)
        engine.write(e2)
        # Process halts without flushing memtable
        engine.close()

        # Restart engine from disk
        restarted_engine = StorageEngine(self.test_dir, memtable_max_events=100)
        # Events should be replayed from WAL back into memtable
        self.assertEqual(len(restarted_engine.memtable), 2)
        scanned = list(restarted_engine.scan(entity="server-1"))
        self.assertEqual(len(scanned), 2)
        self.assertEqual(scanned[0].event_id, "e1")
        self.assertEqual(scanned[1].event_id, "e2")
        restarted_engine.close()


if __name__ == "__main__":
    unittest.main()
