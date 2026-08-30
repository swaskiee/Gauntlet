"""Ingestion pipeline for GAUNTLET (Phase 1 - POWER)."""

import json
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from gauntlet.models import Event, EventValidator, ValidationError


class IngestionReport:
    """Summary report of an ingestion job."""

    def __init__(self) -> None:
        self.total_received: int = 0
        self.accepted: int = 0
        self.rejected: int = 0
        self.errors: List[Dict[str, Any]] = []

    def record_success(self) -> None:
        self.total_received += 1
        self.accepted += 1

    def record_error(self, index: int, raw_payload: Any, error_msg: str) -> None:
        self.total_received += 1
        self.rejected += 1
        self.errors.append({
            "index": index,
            "payload": str(raw_payload)[:100],
            "error": error_msg,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_received": self.total_received,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "error_count": len(self.errors),
            "errors": self.errors[:50],
        }


class IngestionPipeline:
    """Validates, normalizes, and sequences event batches."""

    def __init__(self, sequence_offset: int = 0) -> None:
        self._current_sequence: int = sequence_offset

    @property
    def current_sequence(self) -> int:
        return self._current_sequence

    def ingest_single(self, raw_data: Dict[str, Any]) -> Event:
        self._current_sequence += 1
        return EventValidator.validate_and_normalize(raw_data, sequence_num=self._current_sequence)

    def ingest_batch(self, items: Iterable[Any]) -> Tuple[List[Event], IngestionReport]:
        events: List[Event] = []
        report = IngestionReport()

        for idx, item in enumerate(items):
            try:
                if isinstance(item, str):
                    raw_dict = json.loads(item)
                elif isinstance(item, dict):
                    raw_dict = item
                else:
                    raise ValidationError(f"Unsupported item type: {type(item).__name__}")

                self._current_sequence += 1
                event = EventValidator.validate_and_normalize(raw_dict, sequence_num=self._current_sequence)
                events.append(event)
                report.record_success()
            except Exception as e:
                report.record_error(idx, item, str(e))

        return events, report

    def ingest_jsonl_stream(self, stream: Iterable[str]) -> Generator[Tuple[Optional[Event], Optional[str]], None, None]:
        """Yields (Event, None) or (None, error_str) line-by-line."""
        for line in stream:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            try:
                raw_dict = json.loads(line_str)
                self._current_sequence += 1
                event = EventValidator.validate_and_normalize(raw_dict, sequence_num=self._current_sequence)
                yield (event, None)
            except Exception as e:
                yield (None, str(e))
