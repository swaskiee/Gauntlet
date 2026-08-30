# GAUNTLET — Storage Engine Architecture (Phase 2: SPACE)

The GAUNTLET Storage Engine provides durable, crash-resilient temporal persistence built from first principles on top of the filesystem.

---

## 1. Write Path Overview

```text
Incoming Event
     │
     ▼
Write-Ahead Log (wal.gt) ── [fsync] ──► Durability Guarantee
     │
     ▼
Memtable (In-Memory Sorted Buffer)
     │ (Threshold: Size or Record Count reached)
     ▼
Flush to Immutable Segment (.gt)
     │
     ▼
Update Manifest & Truncate WAL
```

---

## 2. Write-Ahead Log (WAL) Binary Framing

Every mutation is immediately appended to `wal.gt` and synced to disk.

```text
+---------------+---------------+---------------+--------------+---------------+---------------+-----------------------+
| Magic (4B)    | Seq (8B)      | Ts (8B)       | Op (1B)      | Length (4B)   | CRC32 (4B)    | Payload (Length bytes)|
| 'GTWL'        | uint64        | uint64        | uint8        | uint32        | uint32        | JSON UTF-8            |
+---------------+---------------+---------------+--------------+---------------+---------------+-----------------------+
```

### Crash Recovery & Tail Repair
When GAUNTLET boots:
1. Replays valid records sequentially.
2. Validates frame CRC32 against stored checksums.
3. If an incomplete or corrupt tail write is detected (e.g. from an abrupt power failure), the engine identifies the last valid frame offset and truncates the corrupted tail, safely recovering 100% of verified data.

---

## 3. Persistent Segment File Format (.gt)

Segments are immutable files containing sorted batches of events.

```text
+-------------------------------------------------------------+
| Header: Magic 'GTSG' (4B) | Version (2B) | Flags (2B)       |
+-------------------------------------------------------------+
| Metadata:                                                   |
|   MinTimestamp (8B)   | MaxTimestamp (8B)                   |
|   MinSequence (8B)    | MaxSequence (8B)                    |
|   RecordCount (4B)    | IndexOffset (8B)  | IndexCount (4B) |
+-------------------------------------------------------------+
| Records Area:                                               |
|   [PayloadLength (4B)][CRC32 (4B)][Payload (JSON)] ...      |
+-------------------------------------------------------------+
| Sparse Index Area:                                          |
|   [Timestamp (8B)][Sequence (8B)][FileByteOffset (8B)] ...  |
+-------------------------------------------------------------+
| Total File CRC32 Footer (4B)                                |
+-------------------------------------------------------------+
```

---

## 4. Compaction
Multiple small segments are merged into consolidated segments to reduce read amplification, reclaim redundant disk metadata, and preserve monotonic ordering.
