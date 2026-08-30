"""Event data models and validation for GAUNTLET Ingestion (Phase 1 - POWER)."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union


class ValidationError(Exception):
    """Raised when an event fails schema or integrity validation."""
    pass


@dataclass(frozen=True)
class Event:
    """Normalized, immutable temporal event record in GAUNTLET."""
    event_id: str
    entity: str
    timestamp: int  # Unix timestamp in seconds
    type: str
    value: Optional[Union[float, int, str, bool]] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    sequence_num: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "entity": self.entity,
            "timestamp": self.timestamp,
            "type": self.type,
            "value": self.value,
            "attributes": self.attributes,
            "sequence_num": self.sequence_num,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        return cls(
            event_id=str(d["event_id"]),
            entity=str(d["entity"]),
            timestamp=int(d["timestamp"]),
            type=str(d["type"]),
            value=d.get("value"),
            attributes=d.get("attributes", {}),
            sequence_num=int(d.get("sequence_num", 0)),
        )


def parse_timestamp(ts: Any) -> int:
    """Parses timestamp from integer, float, or ISO 8601 string."""
    if isinstance(ts, (int, float)):
        return int(ts)
    if isinstance(ts, str):
        ts_str = ts.strip()
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(ts_str)
            return int(dt.timestamp())
        except Exception:
            try:
                return int(float(ts_str))
            except Exception:
                raise ValidationError(f"Invalid timestamp format: '{ts}'")
    raise ValidationError(f"Unsupported timestamp type: {type(ts)}")


def compute_event_id(entity: str, timestamp: int, event_type: str, value: Any, attributes: Dict[str, Any], sequence: int = 0) -> str:
    """Computes a deterministic SHA-256 event ID."""
    raw_str = f"{sequence}:{entity}:{timestamp}:{event_type}:{value}:{json.dumps(attributes, sort_keys=True)}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:24]


class EventValidator:
    """Validates and normalizes raw inputs into structured Event instances."""

    @staticmethod
    def validate_and_normalize(raw_data: Dict[str, Any], sequence_num: int = 0) -> Event:
        if not isinstance(raw_data, dict):
            raise ValidationError(f"Event payload must be a JSON object/dict, got {type(raw_data).__name__}")

        entity = raw_data.get("entity")
        if not entity or not isinstance(entity, str) or not entity.strip():
            raise ValidationError("Missing or empty required field: 'entity'")
        entity = entity.strip()

        raw_ts = raw_data.get("timestamp")
        if raw_ts is None:
            raise ValidationError("Missing required field: 'timestamp'")
        timestamp = parse_timestamp(raw_ts)

        event_type = raw_data.get("type")
        if not event_type or not isinstance(event_type, str) or not event_type.strip():
            raise ValidationError("Missing or empty required field: 'type'")
        event_type = event_type.strip().lower()

        value = raw_data.get("value")
        if value is not None:
            if not isinstance(value, (int, float, str, bool)):
                raise ValidationError(f"Field 'value' must be a primitive (number, string, boolean), got {type(value).__name__}")

        attributes = raw_data.get("attributes", {})
        if not isinstance(attributes, dict):
            raise ValidationError(f"Field 'attributes' must be an object/dict, got {type(attributes).__name__}")

        event_id = raw_data.get("event_id")
        if not event_id:
            event_id = compute_event_id(entity, timestamp, event_type, value, attributes, sequence_num)

        return Event(
            event_id=str(event_id),
            entity=entity,
            timestamp=timestamp,
            type=event_type,
            value=value,
            attributes=attributes,
            sequence_num=sequence_num,
        )
