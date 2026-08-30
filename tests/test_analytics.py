"""Unit tests for Phase 6 - SOUL (Analytics & Correlation Engine)."""

import unittest
from gauntlet.models import Event
from gauntlet.analytics.engine import AnalyticsEngine
from gauntlet.analytics.correlations import CorrelationEngine


class TestAnalyticsEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = AnalyticsEngine()

    def test_pearson_correlation(self) -> None:
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        r = CorrelationEngine.pearson_correlation(x, y)
        self.assertAlmostEqual(r, 1.0, places=3)

        neg_y = [10.0, 8.0, 6.0, 4.0, 2.0]
        r_neg = CorrelationEngine.pearson_correlation(x, neg_y)
        self.assertAlmostEqual(r_neg, -1.0, places=3)

    def test_full_diagnostic_report(self) -> None:
        events = [
            Event(event_id=f"e{i}", entity="server-42", timestamp=1000 + i * 10, type="cpu", value=40.0 + (i % 2), sequence_num=i+1)
            for i in range(10)
        ]
        events.extend([
            Event(event_id=f"m{i}", entity="server-42", timestamp=1000 + i * 10, type="memory", value=60.0 + (i % 2), sequence_num=10+i+1)
            for i in range(10)
        ])
        events.append(Event(event_id="d1", entity="server-42", timestamp=1105, type="deployment", value="v2.8.1", sequence_num=21))
        events.append(Event(event_id="sp", entity="server-42", timestamp=1110, type="cpu", value=99.0, sequence_num=22))

        report = self.engine.full_diagnostic_report(events, "server-42")
        self.assertEqual(report["entity"], "server-42")
        self.assertTrue("profile" in report)
        self.assertTrue(report["total_anomalies_detected"] >= 1)
        self.assertTrue("correlations" in report)


if __name__ == "__main__":
    unittest.main()
