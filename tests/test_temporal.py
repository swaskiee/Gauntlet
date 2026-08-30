"""Unit tests for Phase 5 - TIME (Temporal Engine)."""

import unittest
from gauntlet.models import Event
from gauntlet.analytics.temporal import TemporalEngine


class TestTemporalEngine(unittest.TestCase):

    def test_time_window_bucketing(self) -> None:
        events = [
            Event(event_id="1", entity="s1", timestamp=1000, type="cpu", value=10.0),
            Event(event_id="2", entity="s1", timestamp=1050, type="cpu", value=20.0),
            Event(event_id="3", entity="s1", timestamp=2000, type="cpu", value=50.0),
        ]
        buckets = TemporalEngine.bucket_by_time_window(events, window_seconds=500)
        self.assertEqual(len(buckets), 3)
        self.assertEqual(buckets[0].start_ts, 1000)
        self.assertEqual(buckets[0].event_count, 2)
        self.assertEqual(buckets[0].mean, 15.0)

    def test_reconstruct_state_as_of(self) -> None:
        events = [
            Event(event_id="1", entity="server-42", timestamp=1000, type="cpu", value=40.0),
            Event(event_id="2", entity="server-42", timestamp=1005, type="memory", value=70.0),
            Event(event_id="3", entity="server-42", timestamp=1010, type="cpu", value=90.0),
            Event(event_id="4", entity="server-42", timestamp=1020, type="cpu", value=99.0),
        ]
        state = TemporalEngine.reconstruct_state_as_of(events, as_of_ts=1008, entity="server-42")
        self.assertEqual(state["metrics"]["cpu"], 40.0)
        self.assertEqual(state["metrics"]["memory"], 70.0)
        self.assertEqual(state["last_event_time"], 1005)

    def test_temporal_diff_calculation(self) -> None:
        events = [
            Event(event_id="1", entity="server-42", timestamp=1000, type="cpu", value=40.0),
            Event(event_id="2", entity="server-42", timestamp=1005, type="deployment", value="v2.0"),
            Event(event_id="3", entity="server-42", timestamp=1010, type="cpu", value=80.0),
        ]
        diff = TemporalEngine.calculate_temporal_diff(events, "server-42", "cpu", t1=1000, t2=1010)
        self.assertEqual(diff.val1, 40.0)
        self.assertEqual(diff.val2, 80.0)
        self.assertEqual(diff.absolute_change, 40.0)
        self.assertEqual(diff.percentage_change, 100.0)
        self.assertTrue(any("deployment" in e for e in diff.intervening_events))


if __name__ == "__main__":
    unittest.main()
