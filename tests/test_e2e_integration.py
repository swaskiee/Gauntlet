"""End-to-End integration & Chaos Recovery tests for GAUNTLET."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from gauntlet.models import Event, EventValidator
from gauntlet.storage.engine import StorageEngine
from gauntlet.index.engine import IndexEngine
from gauntlet.query.executor import QueryExecutor
from gauntlet.contracts.analytics import BuiltinAnalyticsEngine


class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = StorageEngine(self.test_dir, memtable_max_events=4)
        self.index = IndexEngine()
        self.analytics = BuiltinAnalyticsEngine()

    def tearDown(self) -> None:
        self.storage.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_flagship_pipeline(self) -> None:
        # 1. 🟣 POWER: Ingest stream of events
        raw_events = [
            {"entity": "server-42", "timestamp": 1788098000, "type": "cpu", "value": 41.2},
            {"entity": "server-42", "timestamp": 1788098060, "type": "memory", "value": 48.5},
            {"entity": "server-42", "timestamp": 1788098120, "type": "cpu", "value": 40.8},
            {"entity": "server-42", "timestamp": 1788098180, "type": "memory", "value": 49.1},
            {"entity": "server-42", "timestamp": 1788098240, "type": "cpu", "value": 42.5},
            {"entity": "server-42", "timestamp": 1788098300, "type": "errors", "value": 2},
            {"entity": "server-42", "timestamp": 1788098360, "type": "cpu", "value": 39.9},
            {"entity": "server-42", "timestamp": 1788098420, "type": "deployment", "value": "v2.8.1"},
            {"entity": "server-42", "timestamp": 1788098480, "type": "cpu", "value": 61.4},
            {"entity": "server-42", "timestamp": 1788098540, "type": "latency", "value": 84.0},
            {"entity": "server-42", "timestamp": 1788098600, "type": "errors", "value": 17},
            {"entity": "server-42", "timestamp": 1788098660, "type": "cpu", "value": 94.2},
            {"entity": "server-42", "timestamp": 1788098720, "type": "errors", "value": 41}
        ]
        for d in raw_events:
            event = EventValidator.validate_and_normalize(d)
            self.storage.write(event)

        # 2. 🔵 SPACE & 🔴 REALITY: Flush and index
        self.storage.flush()
        self.assertTrue(len(self.storage.segments) >= 3)
        self.index.rebuild_from_segments(self.storage.segments)

        # 3. 🟡 MIND: Execute Query
        executor = QueryExecutor(self.storage, self.index)
        qres = executor.execute("FIND cpu FROM server-42 WHERE value > 50 ORDER BY timestamp ASC")
        self.assertEqual(len(qres.rows), 2)
        self.assertEqual(qres.rows[0][3], 61.4)
        self.assertEqual(qres.rows[1][3], 94.2)
        self.assertEqual(qres.telemetry.returned_rows, 2)

        # 4. 🟢 TIME & 🟠 SOUL: Run Analytics Contract
        all_events = list(self.storage.scan(entity="server-42"))
        profile = self.analytics.generate_entity_profile(all_events, "server-42")
        self.assertEqual(profile.total_events, 13)
        self.assertTrue("cpu" in profile.metrics)

        # Check anomalies
        cpu_anomalies = self.analytics.detect_anomalies(all_events, "cpu", z_threshold=2.0)
        self.assertTrue(len(cpu_anomalies) >= 1)
        anom = cpu_anomalies[0]
        self.assertEqual(anom.observed_value, 94.2)
        self.assertTrue(any("deployment" in ev for ev in anom.evidence))

    def test_chaos_crash_durability_and_restart(self) -> None:
        # Ingest events without manual flush (unflushed records in memtable + WAL)
        e1 = Event(event_id="c1", entity="server-chaos", timestamp=1000, type="cpu", value=50.0, sequence_num=1)
        e2 = Event(event_id="c2", entity="server-chaos", timestamp=1005, type="cpu", value=55.0, sequence_num=2)
        self.storage.write(e1)
        self.storage.write(e2)

        # Abrupt close (simulating sudden power failure)
        self.storage.close()

        # Restart system
        rebooted_storage = StorageEngine(self.test_dir)
        rebooted_index = IndexEngine()
        rebooted_index.rebuild_from_segments(rebooted_storage.segments)
        rebooted_executor = QueryExecutor(rebooted_storage, rebooted_index)

        # Recovered events must be queryable
        res = rebooted_executor.execute("FIND cpu FROM server-chaos")
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(res.rows[0][3], 50.0)
        self.assertEqual(res.rows[1][3], 55.0)

        # Database must report healthy
        health = rebooted_storage.verify_integrity()
        self.assertEqual(health["status"], "HEALTHY")
        rebooted_storage.close()


if __name__ == "__main__":
    unittest.main()
