"""Write-Ahead Log (WAL) implementation for GAUNTLET (Phase 2 - SPACE).

Binary framing:
[4B Magic: 'GTWL'] [8B Seq (Q)] [8B Timestamp (Q)] [1B Op (B)] [4B Length (I)] [4B CRC32 (I)] [Payload (Length bytes)]
"""

import os
import struct
import zlib
from pathlib import Path
from typing import Callable, Generator, List, Optional, Tuple
from gauntlet.models import Event

WAL_MAGIC = b"GTWL"
# Header format: Magic (4s), Seq (Q), Timestamp (Q), Op (B), Length (I), CRC32 (I)
# Total header size: 4 + 8 + 8 + 1 + 4 + 4 = 29 bytes
WAL_HEADER_FORMAT = ">4sQQBII"
WAL_HEADER_SIZE = struct.calcsize(WAL_HEADER_FORMAT)

OP_INSERT = 1
OP_FLUSH_CHECKPOINT = 2


class WALCorruptionError(Exception):
    """Raised when unrecoverable WAL corruption occurs."""
    pass


class WALRecoveryReport:
    """Detailed summary of WAL recovery status."""
    def __init__(self) -> None:
        self.total_entries: int = 0
        self.valid_entries: int = 0
        self.corrupted_entries: int = 0
        self.partial_tail_bytes: int = 0
        self.recovered_events: List[Event] = []

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "valid_entries": self.valid_entries,
            "corrupted_entries": self.corrupted_entries,
            "partial_tail_bytes": self.partial_tail_bytes,
            "recovered_count": len(self.recovered_events),
        }


class WriteAheadLog:
    """Append-only, CRC32-checked Write-Ahead Log for durable mutations."""

    def __init__(self, wal_path: Path, sync_on_write: bool = True) -> None:
        self.wal_path = Path(wal_path)
        self.sync_on_write = sync_on_write
        self._file = None
        self._last_sequence = 0
        self._open_log()

    def _open_log(self) -> None:
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        # Open in append + binary mode
        self._file = open(self.wal_path, "a+b")

    @property
    def last_sequence(self) -> int:
        return self._last_sequence

    def append_event(self, event: Event) -> int:
        """Appends an event insert record to the log."""
        payload_bytes = event.to_json().encode("utf-8")
        payload_len = len(payload_bytes)
        crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        seq = event.sequence_num

        header = struct.pack(
            WAL_HEADER_FORMAT,
            WAL_MAGIC,
            seq,
            event.timestamp,
            OP_INSERT,
            payload_len,
            crc
        )

        self._file.write(header)
        self._file.write(payload_bytes)

        if self.sync_on_write:
            self._file.flush()
            os.fsync(self._file.fileno())

        self._last_sequence = max(self._last_sequence, seq)
        return seq

    def append_checkpoint(self, checkpoint_seq: int, timestamp: int) -> None:
        """Appends a flush checkpoint marker."""
        header = struct.pack(
            WAL_HEADER_FORMAT,
            WAL_MAGIC,
            checkpoint_seq,
            timestamp,
            OP_FLUSH_CHECKPOINT,
            0,
            0
        )
        self._file.write(header)
        if self.sync_on_write:
            self._file.flush()
            os.fsync(self._file.fileno())

    def recover(self) -> WALRecoveryReport:
        """Reads WAL from start, verifies all frames, and isolates valid prefix."""
        report = WALRecoveryReport()
        if not self.wal_path.exists() or self.wal_path.stat().st_size == 0:
            return report

        # Close active append handle while recovering
        if self._file:
            self._file.close()

        valid_file_offset = 0
        with open(self.wal_path, "rb") as rf:
            while True:
                offset_before = rf.tell()
                header_bytes = rf.read(WAL_HEADER_SIZE)
                if not header_bytes:
                    break  # Clean EOF

                if len(header_bytes) < WAL_HEADER_SIZE:
                    # Incomplete header at tail (partial crash write)
                    report.partial_tail_bytes = len(header_bytes)
                    break

                magic, seq, ts, op, payload_len, expected_crc = struct.unpack(WAL_HEADER_FORMAT, header_bytes)

                if magic != WAL_MAGIC or payload_len > 10 * 1024 * 1024:
                    report.corrupted_entries += 1
                    report.partial_tail_bytes = rf.seek(0, os.SEEK_END) - offset_before
                    break

                payload_bytes = rf.read(payload_len)
                if len(payload_bytes) < payload_len:
                    # Partial payload write at tail
                    report.partial_tail_bytes = len(header_bytes) + len(payload_bytes)
                    break

                actual_crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
                if actual_crc != expected_crc:
                    report.corrupted_entries += 1
                    report.partial_tail_bytes = rf.seek(0, os.SEEK_END) - offset_before
                    break

                # Frame is completely valid
                report.total_entries += 1
                report.valid_entries += 1
                valid_file_offset = rf.tell()
                self._last_sequence = max(self._last_sequence, seq)

                if op == OP_INSERT:
                    try:
                        import json
                        d = json.loads(payload_bytes.decode("utf-8"))
                        event = Event.from_dict(d)
                        report.recovered_events.append(event)
                    except Exception:
                        report.corrupted_entries += 1
                        break

        # If there was a corrupt tail, truncate the file back to the valid prefix
        if report.partial_tail_bytes > 0:
            with open(self.wal_path, "r+b") as wf:
                wf.seek(valid_file_offset)
                wf.truncate()

        # Reopen append handle
        self._open_log()
        return report

    def truncate_log(self) -> None:
        """Clears/truncates the WAL file after successful segment flush."""
        if self._file:
            self._file.close()
        with open(self.wal_path, "wb") as f:
            f.truncate(0)
        self._open_log()

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()
