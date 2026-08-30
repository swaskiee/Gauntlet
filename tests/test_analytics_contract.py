"""Unit tests for Phase 5 & 6 Contract (Analytics & Anomaly Baseline Detection)."""

import unittest
from gauntlet.models import Event
from gauntlet.contracts.analytics import BuiltinAnalyticsEngine


class TestAnalyticsContract(unittest.TestCase):

    def setUp(self) -> None:
        self.analytics = BuiltinAnalyticsEngine()

    def test_statistics(self) -> None:
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = self.analytics.compute_statistics(vals)
        self.assertEqual(stats.count, 5)
        self.assertEqual(stats.min, 10.0)
        self.assertEqual(stats.max, 50.0)
        self.assertEqual(stats.mean, 30.0)
        self.assertEqual(stats.median, 30.0)
        self.assertAlmostEqual(stats.stddev, 14.14, places=2)

    def test_anomaly_detection(self) -> None:
        # 10 baseline events around 40% CPU, then 1 spike to 95%
        events = [
            Event(event_id=f"e{i}", entity="server-42", timestamp=1000 + i * 10, type="cpu", value=40.0 + (i % 3), sequence_num=i+1)
            for i in range(10)
        ]
        # Insert a deployment event nearby
        events.append(Event(event_id="d1", entity="server-42", timestamp=1105, type="deployment", value="v2.8.1", sequence_num=11))
        # Insert anomaly spike
        events.append(Event(event_id="spike", entity="server-42", timestamp=1110, type="cpu", value=95.0, sequence_num=12))

        anomalies = self.analytics.detect_anomalies(events, target_metric="cpu", z_threshold=2.5)
        self.assertEqual(len(anomalies), 1)
        anom = anomalies[0]
        self.assertEqual(anom.metric, "cpu")
        self.assertEqual(anom.entity, "server-42")
        self.assertEqual(anom.observed_value, 95.0)
        self.assertTrue(anom.z_score > 2.5)
        self.assertTrue(any("deployment" in ev for ev in anom.evidence))


if __name__ == "__main__":
    unittest.main()
