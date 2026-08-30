# STDLIB.md — Standard Library Usage & Zero-Dependency Guarantee

GAUNTLET enforces a **strict zero-runtime-dependency architecture**. All runtime capabilities are built from first principles using only Python's standard library.

## Standard Library Modules Used

| Module | Purpose in GAUNTLET | Self-Built Core Logic |
|---|---|---|
| `pathlib` / `os` | Platform-agnostic file paths, directory management, atomic filesystem renaming (`.rename()`), and disk syncing (`os.fsync`). | Persistence layout and directory lifecycle. |
| `struct` | Binary encoding and decoding of fixed-size segment headers, records, and index offsets. | Binary layout, frame packing, endianness handling (`>`). |
| `zlib` | Checksum calculations (`zlib.crc32`) on WAL frames and segment footers to detect data corruption. | Integrity verification, corruption recovery, and health check validation. |
| `hashlib` | Deterministic SHA-256 event ID generation and multiple hash seed generation for Bloom filter indexing. | Deterministic sequence hashing and multi-hash bloom filters. |
| `json` | Structured payload serialization/deserialization for human-inspectable event attributes. | Schema normalization, type parsing, and validation. |
| `http.server` | Lightweight TCP HTTP server and REST API dispatcher. | Zero-framework REST endpoint routing and static UI file serving. |
| `urllib.parse` | Query string parsing and request URI decomposition. | API request parameter decoding. |
| `threading` | Thread safety for concurrent WAL writes and segment flushes (`threading.RLock`). | Concurrency control across read/write paths. |
| `math` | Square root, floor, and ceiling for standard deviation and percentile calculations. | All statistics formulas (mean, median, stddev, percentiles, z-score). |
| `dataclasses` | Strongly-typed immutable record structures (`Event`, `QueryAST`, `SegmentMetadata`). | Domain modeling. |
| `typing` | Static type annotations and protocols (`Protocol` for analytics contract). | Architectural separation of Nitanshu's and Swati's ownership. |
| `argparse` | Command-line interface definition and argument parsing. | Full CLI suite (`init`, `ingest`, `query`, `verify`, `serve`, `benchmark`). |
| `time` / `datetime` | ISO-8601 parsing, UNIX timestamps, and high-resolution execution telemetry (`perf_counter`). | Temporal query filtering, diffing, and query performance metrics. |
| `unittest` | Automated unit testing and chaos recovery verification. | Full test pyramid and assertion suite. |

## What GAUNTLET Does NOT Use
- ❌ No external databases (No SQLite, PostgreSQL, MongoDB, Redis, Elasticsearch).
- ❌ No data manipulation frameworks (No Pandas, Polars, NumPy, SciPy).
- ❌ No web frameworks (No FastAPI, Flask, Django, Starlette).
- ❌ No third-party ML/AI libraries (No Scikit-learn, TensorFlow, PyTorch).
