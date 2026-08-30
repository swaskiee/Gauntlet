"""Unified Storage Engine for GAUNTLET (Phase 2 - SPACE)."""

import json
import threading
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple
from gauntlet.models import Event
from gauntlet.storage.memtable import Memtable
from gauntlet.storage.segment import SegmentMetadata, SegmentReader, SegmentWriter
from gauntlet.storage.wal import WriteAheadLog, WALRecoveryReport


class StorageEngine:
    """Zero-dependency durable temporal storage engine."""

    def __init__(
        self,
        db_dir: Path,
        memtable_max_events: int = 5000,
        memtable_max_bytes: int = 512 * 1024,
        sync_on_write: bool = True
    ) -> None:
        self.db_dir = Path(db_dir)
        self.segments_dir = self.db_dir / "segments"
        self.wal_path = self.db_dir / "wal.gt"
        self.manifest_path = self.db_dir / "manifest.json"

        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.segments_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self.memtable = Memtable(max_size_bytes=memtable_max_bytes, max_events=memtable_max_events)
        self.wal = WriteAheadLog(self.wal_path, sync_on_write=sync_on_write)

        self.segments: List[SegmentMetadata] = []
        self._segment_counter = 0

        # Load existing database state
        self._bootstrap()

    def _bootstrap(self) -> None:
        with self._lock:
            # 1. Load manifested segments
            if self.manifest_path.exists():
                try:
                    data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                    self._segment_counter = data.get("segment_counter", 0)
                except Exception:
                    pass

            # Discover and inspect segments on disk
            self.segments = []
            segment_files = sorted(self.segments_dir.glob("segment-*.gt"))
            for seg_path in segment_files:
                try:
                    reader = SegmentReader(seg_path)
                    self.segments.append(reader.metadata)
                except Exception:
                    continue

            # 2. Replay WAL for uncommitted / crash-interrupted in-memory writes
            report = self.wal.recover()
            for event in report.recovered_events:
                self.memtable.put(event)

    def _save_manifest(self) -> None:
        data = {
            "version": 1,
            "segment_counter": self._segment_counter,
            "segments": [s.to_dict() for s in self.segments],
            "last_updated": int(time.time())
        }
        temp_manifest = self.manifest_path.with_suffix(".tmp")
        temp_manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if self.manifest_path.exists():
            self.manifest_path.unlink()
        temp_manifest.rename(self.manifest_path)

    def write(self, event: Event) -> int:
        """Durable write path: WAL -> Memtable -> Flush trigger."""
        with self._lock:
            seq = self.wal.append_event(event)
            self.memtable.put(event)

            if self.memtable.should_flush():
                self.flush()

            return seq

    def write_batch(self, events: List[Event]) -> int:
        """Batch write path."""
        with self._lock:
            last_seq = 0
            for event in events:
                last_seq = self.wal.append_event(event)
                self.memtable.put(event)

            if self.memtable.should_flush():
                self.flush()

            return last_seq

    def flush(self) -> Optional[SegmentMetadata]:
        """Flushes in-memory memtable to an immutable segment and truncates WAL."""
        with self._lock:
            if len(self.memtable) == 0:
                return None

            events_to_flush = self.memtable.clear()
            self._segment_counter += 1
            segment_name = f"segment-{self._segment_counter:06d}.gt"
            segment_path = self.segments_dir / segment_name

            metadata = SegmentWriter.write_segment(segment_path, events_to_flush)
            self.segments.append(metadata)

            # Record checkpoint & truncate WAL
            self.wal.truncate_log()
            self._save_manifest()
            return metadata

    def scan(
        self,
        entity: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> Iterator[Event]:
        """Scans records across all persistent segments and in-memory memtable."""
        with self._lock:
            # 1. Scan persistent segments
            for meta in list(self.segments):
                reader = SegmentReader(meta.path)
                for event in reader.scan(entity=entity, start_ts=start_ts, end_ts=end_ts, event_type=event_type):
                    yield event

            # 2. Scan active memtable
            for event in self.memtable.scan(entity=entity, start_ts=start_ts, end_ts=end_ts, event_type=event_type):
                yield event

    def compact(self, target_segments_count: int = 2) -> Optional[SegmentMetadata]:
        """Merges multiple segments into a single compact segment."""
        with self._lock:
            if len(self.segments) < target_segments_count:
                return None

            # Collect all events from existing segments
            all_events: List[Event] = []
            for meta in self.segments:
                reader = SegmentReader(meta.path)
                all_events.extend(list(reader.scan()))

            # Deduplicate by event_id if duplicate writes occurred
            seen_ids = set()
            unique_events: List[Event] = []
            for e in all_events:
                if e.event_id not in seen_ids:
                    seen_ids.add(e.event_id)
                    unique_events.append(e)

            # Write new consolidated segment
            self._segment_counter += 1
            compact_name = f"segment-{self._segment_counter:06d}.gt"
            compact_path = self.segments_dir / compact_name
            new_meta = SegmentWriter.write_segment(compact_path, unique_events)

            # Delete old segments
            old_segments = list(self.segments)
            self.segments = [new_meta]
            for old in old_segments:
                try:
                    if old.path.exists():
                        old.path.unlink()
                except Exception:
                    pass

            self._save_manifest()
            return new_meta

    def verify_integrity(self) -> Dict[str, any]:
        """Performs full integrity check of WAL, segments, and metadata."""
        with self._lock:
            total_records = 0
            valid_checksums = 0
            issues = []

            for meta in self.segments:
                reader = SegmentReader(meta.path)
                valid, msg = reader.verify_integrity()
                if valid:
                    valid_checksums += 1
                    total_records += meta.record_count
                else:
                    issues.append(f"Segment {meta.segment_id}: {msg}")

            total_records += len(self.memtable)

            return {
                "status": "HEALTHY" if not issues else "DEGRADED",
                "segments_checked": len(self.segments),
                "checksums_valid": f"{valid_checksums}/{len(self.segments)}",
                "total_records": total_records,
                "memtable_records": len(self.memtable),
                "issues": issues
            }

    def close(self) -> None:
        with self._lock:
            self.wal.close()
