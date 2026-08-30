"""Unit tests for Phase 1 - POWER (Models and Ingestion Pipeline)."""

import unittest
from gauntlet.models import Event, EventValidator, ValidationError, parse_timestamp, compute_event_id
from gauntlet.ingestion.pipeline import IngestionPipeline, IngestionReport


class TestModelsAndIngestion(unittest.TestCase):

    def test_timestamp_parsing(self) -> None:
        self.assertEqual(parse_timestamp(1700000000), 1700000000)
        self.assertEqual(parse_timestamp("1700000000"), 1700000000)
        self.assertEqual(parse_timestamp("2026-08-30T14:02:00Z"), 1788098520)

        with self.assertRaises(ValidationError):
            parse_timestamp("invalid-date-string")

    def test_event_validation_success(self) -> None:
        raw = {
            "entity": "server-42",
            "timestamp": 1788098520,
            "type": "cpu",
            "value": 42.1,
            "attributes": {"region": "us-east-1"}
        }
        event = EventValidator.validate_and_normalize(raw, sequence_num=1)
        self.assertEqual(event.entity, "server-42")
        self.assertEqual(event.timestamp, 1788098520)
        self.assertEqual(event.type, "cpu")
        self.assertEqual(event.value, 42.1)
        self.assertEqual(event.attributes["region"], "us-east-1")
        self.assertEqual(event.sequence_num, 1)
        self.assertTrue(len(event.event_id) > 0)

    def test_event_validation_rejections(self) -> None:
        # Missing entity
        with self.assertRaises(ValidationError):
            EventValidator.validate_and_normalize({"timestamp": 100, "type": "cpu"})

        # Missing timestamp
        with self.assertRaises(ValidationError):
            EventValidator.validate_and_normalize({"entity": "s1", "type": "cpu"})

        # Missing type
        with self.assertRaises(ValidationError):
            EventValidator.validate_and_normalize({"entity": "s1", "timestamp": 100})

        # Invalid value type
        with self.assertRaises(ValidationError):
            EventValidator.validate_and_normalize({"entity": "s1", "timestamp": 100, "type": "cpu", "value": [1, 2, 3]})

    def test_deterministic_id(self) -> None:
        id1 = compute_event_id("server-1", 1000, "cpu", 50.0, {"env": "prod"}, sequence=1)
        id2 = compute_event_id("server-1", 1000, "cpu", 50.0, {"env": "prod"}, sequence=1)
        id3 = compute_event_id("server-1", 1000, "cpu", 50.0, {"env": "prod"}, sequence=2)
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

    def test_pipeline_batch_ingestion(self) -> None:
        pipeline = IngestionPipeline(sequence_offset=0)
        batch = [
            {"entity": "server-1", "timestamp": 1000, "type": "cpu", "value": 10.0},
            {"entity": "server-1", "timestamp": 1005, "type": "cpu", "value": 20.0},
            "invalid json payload {",
            {"entity": "server-2", "timestamp": 1010, "type": "memory", "value": 85.5},
            {"invalid": "payload"}
        ]
        events, report = pipeline.ingest_batch(batch)
        self.assertEqual(len(events), 3)
        self.assertEqual(report.total_received, 5)
        self.assertEqual(report.accepted, 3)
        self.assertEqual(report.rejected, 2)
        self.assertEqual(events[0].sequence_num, 1)
        self.assertEqual(events[1].sequence_num, 2)
        self.assertEqual(events[2].sequence_num, 3)


if __name__ == "__main__":
    unittest.main()
