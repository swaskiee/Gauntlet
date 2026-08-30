"""Unit tests for Phase 2 - SPACE (Write-Ahead Log & Crash Recovery)."""

import shutil
import tempfile
import unittest
from pathlib import Path
from gauntlet.models import Event
from gauntlet.storage.wal import WriteAheadLog, OP_INSERT, OP_FLUSH_CHECKPOINT


class TestWriteAheadLog(unittest.TestCase):

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())
        self.wal_path = self.test_dir / "wal.gt"

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_wal_append_and_recover(self) -> None:
        wal = WriteAheadLog(self.wal_path)
        events = [
            Event(event_id="e1", entity="server-1", timestamp=1000, type="cpu", value=45.0, sequence_num=1),
            Event(event_id="e2", entity="server-1", timestamp=1005, type="memory", value=80.0, sequence_num=2),
            Event(event_id="e3", entity="server-2", timestamp=1010, type="cpu", value=99.0, sequence_num=3),
        ]
        for e in events:
            wal.append_event(e)
        wal.close()

        # Restart WAL and recover
        recovery_wal = WriteAheadLog(self.wal_path)
        report = recovery_wal.recover()
        self.assertEqual(report.valid_entries, 3)
        self.assertEqual(report.corrupted_entries, 0)
        self.assertEqual(report.partial_tail_bytes, 0)
        self.assertEqual(len(report.recovered_events), 3)
        self.assertEqual(report.recovered_events[0].event_id, "e1")
        self.assertEqual(report.recovered_events[2].event_id, "e3")
        self.assertEqual(recovery_wal.last_sequence, 3)
        recovery_wal.close()

    def test_wal_crash_partial_tail_recovery(self) -> None:
        wal = WriteAheadLog(self.wal_path)
        e1 = Event(event_id="e1", entity="server-1", timestamp=1000, type="cpu", value=45.0, sequence_num=1)
        e2 = Event(event_id="e2", entity="server-1", timestamp=1005, type="cpu", value=50.0, sequence_num=2)
        wal.append_event(e1)
        wal.append_event(e2)
        wal.close()

        # Simulate incomplete crash write (corrupted garbage tail appended)
        with open(self.wal_path, "ab") as f:
            f.write(b"GTWL\x00\x00\x00\x03CORRUPTED_GARBAGE_BYTES_FROM_POWER_FAILURE")

        # Recover from crash
        recovery_wal = WriteAheadLog(self.wal_path)
        report = recovery_wal.recover()
        self.assertEqual(report.valid_entries, 2)
        self.assertTrue(report.partial_tail_bytes > 0)
        self.assertEqual(len(report.recovered_events), 2)
        self.assertEqual(report.recovered_events[1].event_id, "e2")
        recovery_wal.close()

        # Second recovery should now be completely clean because the corrupt tail was truncated
        clean_wal = WriteAheadLog(self.wal_path)
        clean_report = clean_wal.recover()
        self.assertEqual(clean_report.valid_entries, 2)
        self.assertEqual(clean_report.partial_tail_bytes, 0)
        clean_wal.close()

    def test_wal_truncate(self) -> None:
        wal = WriteAheadLog(self.wal_path)
        e1 = Event(event_id="e1", entity="server-1", timestamp=1000, type="cpu", value=45.0, sequence_num=1)
        wal.append_event(e1)
        wal.close()

        trunc_wal = WriteAheadLog(self.wal_path)
        trunc_wal.truncate_log()
        report = trunc_wal.recover()
        self.assertEqual(report.valid_entries, 0)
        self.assertEqual(len(report.recovered_events), 0)
        trunc_wal.close()


if __name__ == "__main__":
    unittest.main()
