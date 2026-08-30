"""Persistent immutable segment file format (.gt) for GAUNTLET (Phase 2 - SPACE).

Segment Binary Layout:
+-------------------------------------------------------------+
| Header: Magic 'GTSG' (4B) | Version (2B) | Flags (2B)       |
+-------------------------------------------------------------+
| Meta: MinTs (8B) | MaxTs (8B) | MinSeq (8B) | MaxSeq (8B)   |
|       RecordCount (4B) | IndexOffset (8B) | IndexCount (4B) |
+-------------------------------------------------------------+
| Records Area:                                               |
|   [RecordLen (4B)][CRC32 (4B)][Payload (JSON UTF-8)] ...   |
+-------------------------------------------------------------+
| Sparse Index Area:                                          |
|   [Ts (8B)][Seq (8B)][FileOffset (8B)] ...                  |
+-------------------------------------------------------------+
| Checksum: Total Footer CRC32 (4B)                           |
+-------------------------------------------------------------+
"""

import os
import struct
import zlib
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple
from gauntlet.models import Event

SEGMENT_MAGIC = b"GTSG"
SEGMENT_VERSION = 1

# Header: Magic (4s), Version (H), Flags (H) -> 8 bytes
SEGMENT_HEADER_FMT = ">4sHH"
SEGMENT_HEADER_SIZE = struct.calcsize(SEGMENT_HEADER_FMT)

# Meta: MinTs (Q), MaxTs (Q), MinSeq (Q), MaxSeq (Q), RecordCount (I), IndexOffset (Q), IndexCount (I) -> 48 bytes
SEGMENT_META_FMT = ">QQQQIQI"
SEGMENT_META_SIZE = struct.calcsize(SEGMENT_META_FMT)

# Record entry header: Length (I), CRC32 (I) -> 8 bytes
RECORD_HEADER_FMT = ">II"
RECORD_HEADER_SIZE = struct.calcsize(RECORD_HEADER_FMT)

# Index entry: Timestamp (Q), Sequence (Q), Offset (Q) -> 24 bytes
INDEX_ENTRY_FMT = ">QQQ"
INDEX_ENTRY_SIZE = struct.calcsize(INDEX_ENTRY_FMT)


class SegmentMetadata:
    """Metadata summary of an immutable segment file."""
    def __init__(
        self,
        segment_id: str,
        path: Path,
        min_ts: int,
        max_ts: int,
        min_seq: int,
        max_seq: int,
        record_count: int,
        index_offset: int,
        index_count: int,
        entities: Set[str],
        event_types: Set[str]
    ) -> None:
        self.segment_id = segment_id
        self.path = Path(path)
        self.min_ts = min_ts
        self.max_ts = max_ts
        self.min_seq = min_seq
        self.max_seq = max_seq
        self.record_count = record_count
        self.index_offset = index_offset
        self.index_count = index_count
        self.entities = entities
        self.event_types = event_types

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "path": str(self.path),
            "min_ts": self.min_ts,
            "max_ts": self.max_ts,
            "min_seq": self.min_seq,
            "max_seq": self.max_seq,
            "record_count": self.record_count,
            "entities": list(self.entities),
            "event_types": list(self.event_types)
        }


class SegmentWriter:
    """Serializes in-memory events into a verified, immutable segment file (.gt)."""

    @staticmethod
    def write_segment(
        segment_path: Path,
        events: List[Event],
        index_interval: int = 16
    ) -> SegmentMetadata:
        if not events:
            raise ValueError("Cannot write an empty segment")

        sorted_events = sorted(events, key=lambda e: (e.timestamp, e.sequence_num))
        min_ts = sorted_events[0].timestamp
        max_ts = sorted_events[-1].timestamp
        min_seq = min(e.sequence_num for e in sorted_events)
        max_seq = max(e.sequence_num for e in sorted_events)
        record_count = len(sorted_events)

        entities: Set[str] = set()
        event_types: Set[str] = set()

        temp_path = segment_path.with_suffix(".tmp")
        index_entries: List[Tuple[int, int, int]] = []

        with open(temp_path, "w+b") as f:
            # 1. Write placeholder header and metadata
            f.write(b"\x00" * (SEGMENT_HEADER_SIZE + SEGMENT_META_SIZE))

            # 2. Write record area
            for idx, event in enumerate(sorted_events):
                entities.add(event.entity)
                event_types.add(event.type)

                record_offset = f.tell()
                if idx % index_interval == 0:
                    index_entries.append((event.timestamp, event.sequence_num, record_offset))

                payload = event.to_json().encode("utf-8")
                payload_len = len(payload)
                crc = zlib.crc32(payload) & 0xFFFFFFFF

                f.write(struct.pack(RECORD_HEADER_FMT, payload_len, crc))
                f.write(payload)

            # 3. Write sparse index area
            index_offset = f.tell()
            index_count = len(index_entries)
            for ts, seq, offset in index_entries:
                f.write(struct.pack(INDEX_ENTRY_FMT, ts, seq, offset))

            # 4. Write footer checksum
            total_size = f.tell()
            f.seek(0)
            all_content = f.read(total_size)
            footer_crc = zlib.crc32(all_content) & 0xFFFFFFFF
            f.seek(total_size)
            f.write(struct.pack(">I", footer_crc))

            # 5. Rewind and write real header and metadata
            f.seek(0)
            f.write(struct.pack(SEGMENT_HEADER_FMT, SEGMENT_MAGIC, SEGMENT_VERSION, 0))
            f.write(struct.pack(
                SEGMENT_META_FMT,
                min_ts,
                max_ts,
                min_seq,
                max_seq,
                record_count,
                index_offset,
                index_count
            ))

        # Atomic rename
        if segment_path.exists():
            segment_path.unlink()
        temp_path.rename(segment_path)

        segment_id = segment_path.stem
        return SegmentMetadata(
            segment_id=segment_id,
            path=segment_path,
            min_ts=min_ts,
            max_ts=max_ts,
            min_seq=min_seq,
            max_seq=max_seq,
            record_count=record_count,
            index_offset=index_offset,
            index_count=index_count,
            entities=entities,
            event_types=event_types
        )


class SegmentReader:
    """Reads, queries, and verifies records from an immutable segment file (.gt)."""

    def __init__(self, segment_path: Path) -> None:
        self.segment_path = Path(segment_path)
        self.metadata = self._read_metadata()

    def _read_metadata(self) -> SegmentMetadata:
        with open(self.segment_path, "rb") as f:
            header_bytes = f.read(SEGMENT_HEADER_SIZE)
            if len(header_bytes) < SEGMENT_HEADER_SIZE:
                raise ValueError(f"Corrupt segment header: {self.segment_path}")

            magic, version, flags = struct.unpack(SEGMENT_HEADER_FMT, header_bytes)
            if magic != SEGMENT_MAGIC:
                raise ValueError(f"Invalid segment magic {magic} in {self.segment_path}")

            meta_bytes = f.read(SEGMENT_META_SIZE)
            min_ts, max_ts, min_seq, max_seq, rec_count, idx_offset, idx_count = struct.unpack(SEGMENT_META_FMT, meta_bytes)

            # Scan entities and event types
            entities: Set[str] = set()
            event_types: Set[str] = set()

            f.seek(SEGMENT_HEADER_SIZE + SEGMENT_META_SIZE)
            for _ in range(rec_count):
                rec_head = f.read(RECORD_HEADER_SIZE)
                if not rec_head:
                    break
                plen, _ = struct.unpack(RECORD_HEADER_FMT, rec_head)
                payload = f.read(plen)
                # Quick inspection
                import json
                d = json.loads(payload.decode("utf-8"))
                entities.add(d["entity"])
                event_types.add(d["type"])

        return SegmentMetadata(
            segment_id=self.segment_path.stem,
            path=self.segment_path,
            min_ts=min_ts,
            max_ts=max_ts,
            min_seq=min_seq,
            max_seq=max_seq,
            record_count=rec_count,
            index_offset=idx_offset,
            index_count=idx_count,
            entities=entities,
            event_types=event_types
        )

    def scan(
        self,
        entity: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> Iterator[Event]:
        # Fast prune by segment bounds
        if start_ts is not None and self.metadata.max_ts < start_ts:
            return
        if end_ts is not None and self.metadata.min_ts > end_ts:
            return
        if entity is not None and entity not in self.metadata.entities:
            return
        if event_type is not None and event_type not in self.metadata.event_types:
            return

        with open(self.segment_path, "rb") as f:
            f.seek(SEGMENT_HEADER_SIZE + SEGMENT_META_SIZE)
            for _ in range(self.metadata.record_count):
                rec_head = f.read(RECORD_HEADER_SIZE)
                if not rec_head:
                    break
                plen, expected_crc = struct.unpack(RECORD_HEADER_FMT, rec_head)
                payload = f.read(plen)
                actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
                if actual_crc != expected_crc:
                    raise ValueError(f"CRC mismatch in record of {self.segment_path}")

                import json
                d = json.loads(payload.decode("utf-8"))
                event = Event.from_dict(d)

                if start_ts is not None and event.timestamp < start_ts:
                    continue
                if end_ts is not None and event.timestamp > end_ts:
                    continue
                if entity is not None and event.entity != entity:
                    continue
                if event_type is not None and event.type != event_type:
                    continue

                yield event

    def verify_integrity(self) -> Tuple[bool, str]:
        """Validates all record checksums and header metadata."""
        try:
            with open(self.segment_path, "rb") as f:
                header_bytes = f.read(SEGMENT_HEADER_SIZE)
                magic, version, _ = struct.unpack(SEGMENT_HEADER_FMT, header_bytes)
                if magic != SEGMENT_MAGIC:
                    return False, f"Invalid magic {magic}"

                meta_bytes = f.read(SEGMENT_META_SIZE)
                _, _, _, _, rec_count, _, _ = struct.unpack(SEGMENT_META_FMT, meta_bytes)

                count = 0
                for _ in range(rec_count):
                    rec_head = f.read(RECORD_HEADER_SIZE)
                    if not rec_head:
                        break
                    plen, exp_crc = struct.unpack(RECORD_HEADER_FMT, rec_head)
                    payload = f.read(plen)
                    if (zlib.crc32(payload) & 0xFFFFFFFF) != exp_crc:
                        return False, f"Record CRC mismatch at record index {count}"
                    count += 1

                if count != rec_count:
                    return False, f"Expected {rec_count} records, found {count}"

            return True, "HEALTHY"
        except Exception as e:
            return False, str(e)
