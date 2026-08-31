# STDLIB.md — Standard Library Usage & Zero-Dependency Architecture

GAUNTLET enforces a **strict zero-runtime-dependency architecture**. All runtime capabilities are built from first principles using only Python's standard library.

---

## 1. Direct Module Replacements & Technical Reasoning

| Standard Library Swap | Normally Used Third-Party | Technical Reasoning & Zero-Dependency Justification |
|---|---|---|
| `urllib.request` + `http.client` | `requests` / `httpx` | While `requests` offers connection pooling and HTTP/2, all our agentic crawler probes are sequential socket scans with explicit timeouts and custom header injection; nothing is lost by using native standard library sockets. |
| `struct` + `os.fsync` | `sqlite3` / `rocksdb` | Native `struct` permits byte-level precision over length-prefixed frames (`>IIQ`), binary segment headers, and atomic disk synchronization without embedding C-compiled foreign libraries. |
| `zlib.crc32` | `crcmod` / `hashlib` extensions | `zlib.crc32` executes native compiled C hardware-accelerated CRC-32 checksum computations directly in Python's standard library for fast segment integrity validation. |
| `hashlib.sha256` | `uuid` / `shortuuid` | Content-addressed deterministic SHA-256 hashing produces duplicate-proof collision-resistant 24-character event identifiers without relying on random UUID state generators. |
| `math` (mean, sqrt, stddev) | `numpy` / `scipy` | We implemented Welford's algorithm, Pearson linear correlation coefficients ($r$), and Z-Score statistical anomaly equations in native Python, avoiding hundreds of megabytes of binary dependencies. |
| `http.server` + `urllib.parse` | `FastAPI` / `Flask` / `Starlette` | Handcrafted `SimpleHTTPRequestHandler` subclass handles asynchronous routing, JSON serialization, and static asset streaming in under 400 lines of clean code. |
| `argparse` | `click` / `typer` | Full hierarchical CLI subcommand suite (`init`, `ingest`, `query`, `analyze`, `verify`, `serve`, `benchmark`) built cleanly with zero decorator-magic overhead. |
| `dataclasses` + `typing.Protocol` | `pydantic` | Strongly-typed immutable schemas and interface contracts verified statically without heavy runtime metaclass parsing overhead. |

---

## 2. Standard Library Modules Inventory

| Module | Core Purpose in GAUNTLET |
|---|---|
| `pathlib` / `os` | Platform-agnostic file paths, directory isolation, atomic file renaming (`.rename()`), and disk syncing (`os.fsync`). |
| `struct` | Binary encoding and decoding of fixed-size segment headers, records, and index offsets. |
| `zlib` | Checksum calculations (`zlib.crc32`) on WAL frames and segment footers to detect data corruption. |
| `hashlib` | Deterministic SHA-256 event ID generation and multiple hash seed generation for Bloom filter indexing. |
| `json` | Structured payload serialization/deserialization for human-inspectable event attributes. |
| `http.server` | Lightweight TCP HTTP server and REST API dispatcher. |
| `urllib.parse` | Query string parsing and request URI decomposition. |
| `threading` | Thread safety for concurrent WAL writes and segment flushes (`threading.RLock`). |
| `math` | Square root, floor, and ceiling for standard deviation and percentile calculations. |
| `dataclasses` | Strongly-typed immutable record structures (`Event`, `QueryAST`, `SegmentMetadata`). |
| `typing` | Static type annotations and protocols (`Protocol` for analytics contract). |
| `argparse` | Command-line interface definition and argument parsing. |
| `time` / `datetime` | ISO-8601 parsing, UNIX timestamps, and high-resolution execution telemetry (`perf_counter`). |
| `unittest` | Automated unit testing and chaos recovery verification. |

---

## 3. What GAUNTLET Explicitly Avoids

- ❌ **No external databases**: No SQLite, PostgreSQL, MongoDB, Redis, or Elasticsearch.
- ❌ **No data manipulation frameworks**: No Pandas, Polars, NumPy, or SciPy.
- ❌ **No web frameworks**: No FastAPI, Flask, Django, or Starlette.
- ❌ **No third-party ML/AI libraries**: No Scikit-learn, TensorFlow, or PyTorch.
