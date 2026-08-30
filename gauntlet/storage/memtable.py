"""In-memory write structure (Memtable) for GAUNTLET (Phase 2 - SPACE)."""

import bisect
from typing import Dict, Iterator, List, Optional
from gauntlet.models import Event


class Memtable:
    """In-memory sorted event buffer with size threshold monitoring."""

    def __init__(self, max_size_bytes: int = 1024 * 1024, max_events: int = 10000) -> None:
        self.max_size_bytes = max_size_bytes
        self.max_events = max_events
        self._events: List[Event] = []
        self._keys: List[tuple] = []  # (timestamp, sequence_num) for binary search
        self._approx_size_bytes: int = 0
        self._entity_map: Dict[str, List[Event]] = {}

    def __len__(self) -> int:
        return len(self._events)

    @property
    def approx_size_bytes(self) -> int:
        return self._approx_size_bytes

    def should_flush(self) -> bool:
        """Returns True if size or count thresholds are reached."""
        return len(self._events) >= self.max_events or self._approx_size_bytes >= self.max_size_bytes

    def put(self, event: Event) -> None:
        """Inserts an event keeping chronological (timestamp, sequence) order."""
        key = (event.timestamp, event.sequence_num)
        idx = bisect.bisect_left(self._keys, key)
        self._keys.insert(idx, key)
        self._events.insert(idx, event)

        # Update entity index map
        if event.entity not in self._entity_map:
            self._entity_map[event.entity] = []
        self._entity_map[event.entity].append(event)

        # Estimate memory footprint
        self._approx_size_bytes += len(event.to_json()) + 64

    def get_all(self) -> List[Event]:
        """Returns a snapshot copy of all events in sorted order."""
        return list(self._events)

    def scan(
        self,
        entity: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> Iterator[Event]:
        """Scans in-memory records matching criteria."""
        source = self._entity_map.get(entity, []) if entity else self._events
        for e in source:
            if start_ts is not None and e.timestamp < start_ts:
                continue
            if end_ts is not None and e.timestamp > end_ts:
                continue
            if event_type is not None and e.type != event_type:
                continue
            yield e

    def clear(self) -> List[Event]:
        """Drains and resets the memtable, returning all buffered events."""
        flushed = self._events
        self._events = []
        self._keys = []
        self._approx_size_bytes = 0
        self._entity_map = {}
        return flushed
