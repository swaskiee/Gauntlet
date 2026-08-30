<p align="center">
  <img src="Logo.png" alt="GAUNTLET Logo" width="320"/>
</p>
<p align="center">
  <strong>High-Density Temporal Telemetry & Analytics Engine</strong><br/>
  <em>Authoritative Storage &bull; 6-Phase Agentic Pipeline &bull; Statistical Diagnostics &bull; Zero Dependencies</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/runtime-Python%203.11+-blue?style=flat-square" alt="Runtime"/>
  <img src="https://img.shields.io/badge/dependencies-zero%20external-emerald?style=flat-square" alt="Zero Dependencies"/>
  <img src="https://img.shields.io/badge/storage-binary%20WAL%20%2B%20segments-cyan?style=flat-square" alt="Storage"/>
  <img src="https://img.shields.io/badge/integrity-CRC--32%20validated-purple?style=flat-square" alt="Integrity"/>
  <img src="https://img.shields.io/badge/tests-26%20passed-success?style=flat-square" alt="Tests"/>
</p>

---

## 1. System Architecture & Core Capabilities

GAUNTLET is an enterprise-grade temporal data engine, agentic web telemetry crawler, and observability analytics platform built from first principles with zero third-party runtime dependencies.

```text
RAW PROBES & STREAMS
        │
        ▼
[PHASE I: POWER] ──> Real Socket Probing, Jitter & Latency Benchmarks
        │
        ▼
[PHASE II: SPACE] ──> Binary Append-Only WAL (wal.gtwl) & Immutable Segments (.gt)
        │
        ▼
[PHASE III: REALITY] ──> Bloom Filter Manifestation & Entity Index Pruning
        │
        ▼
[PHASE IV: MIND] ──> AST Query Engine, Schema Normalization & DSL Planner
        │
        ▼
[PHASE V: TIME] ──> Temporal Sliding-Window Analysis & Historical Delta Diff
        │
        ▼
[PHASE VI: SOUL] ──> Z-Score Anomaly Detection (|z| >= 2.0) & Pearson Correlations
        │
        ▼
EXPLAINABLE ANALYTICS & DASHBOARD
Interactive Web IDE / Multi-Metric Canvases / SLA Reports / CLI Dispatch
```

---

## 2. Technical Feature Highlights

### 1. Authoritative Binary Storage & Zero Data Loss
- **Append-Only Write-Ahead Log (`wal.gtwl`)**: Length-prefixed binary structs with CRC-32 checksums written on every ingestion before memory commitment.
- **Immutable Segments (`.gt`)**: In-memory memtable flushes to sorted disk segment files with binary headers and payload offsets.
- **Deterministic Event Hashing**: Content-addressed SHA-256 event IDs preventing duplicate telemetry entries.
- **Automatic Crash Recovery**: Replays valid WAL frames upon process restart and safely truncates partial uncommitted tails.

### 2. 6-Phase Agentic Live Web & Socket Crawler
- **Live HTTP Socket Probing**: Performs multi-socket probing on any local server or internet URL.
- **DOM & Network Metadata Extraction**: Extracts page title, meta description, primary H1 heading, script/link/image/form counts, server technology header, payload MIME type, and HSTS security status.
- **Time-Series Metric Synthesis**: Emits authoritative records (`latency`, `size_kb`, `cpu_factor`, `memory_heap`, `errors`) into the WAL and Bloom index in real time.

### 3. Analytics & Statistical Anomaly Engine
- **Z-Score Anomaly Detection**: Calculates dynamic mean ($\mu$) and standard deviation ($\sigma$) baselines per entity and flags statistical anomalies ($|z| \ge 2.0$).
- **Pearson Linear Correlation Matrix**: Computes pairwise correlation coefficients ($r \in [-1, 1]$) across multiple telemetry dimensions.
- **Quantile Engine**: Computes exact P95, Median, Min, and Max metrics.
- **Temporal Delta Diff Engine**: Quantifies baseline shifts and absolute drift between two distinct timestamps.

### 4. Interactive Single-Page Dashboard (`/index.html`)
- **Drawer Navigation**: Hardware-accelerated sidebar drawer toggled directly by the transparent GAUNTLET brand logo.
- **Vector Iconography**: High-contrast, theme-matched SVG vector icons with zero unicode emojis.
- **Multi-Metric Graphs**: Real-time canvas waveform charts, quantile cards, and CSV export.
- **Authentication & User Profiles**: Local-storage-persisted sessions, profile editing, and local avatar photo uploads.
- **Query Planner IDE**: Interactive DSL console with AST syntax parsing and execution telemetry metrics.

---

## 3. Directory Layout

```text
Gauntlet/
├── gauntlet/
│   ├── analytics/       # Z-score anomalies, Pearson correlations, temporal engine
│   ├── api/             # Zero-dependency HTTP server, crawler handler, and REST API
│   ├── cli/             # Command-line interface subcommands
│   ├── index/           # Multi-hash Bloom filter index and segment pruner
│   ├── query/           # DSL lexer, parser, AST compiler, and query executor
│   ├── storage/         # Binary WAL, segment reader/writer, and compaction engine
│   └── models.py        # Event schema validation, CRC-32, and hashing
├── web/
│   └── static/
│       ├── index.html   # Single-page observability dashboard
│       └── logo.png     # Transparent official brand asset
├── tests/               # 26 unit, contract, and end-to-end integration tests
├── gauntlet.py          # Unified CLI entry point
├── Logo.png             # Master brand logo
└── README.md            # Technical documentation
```

---

## 4. Getting Started & CLI Usage

### Prerequisites
- Python 3.11 or higher
- Standard Python standard library (no `pip install` required)

### Initialize Storage Database
```bash
python gauntlet.py init --dir database
```

### Ingest Event Datasets
```bash
python gauntlet.py ingest datasets/demo_events.jsonl --dir database
```

### Launch High-Density Dashboard & API Server
```bash
python gauntlet.py serve --port 8080 --dir database
```
Open **http://127.0.0.1:8080** in your browser to access the dashboard.

### Execute DSL Query via CLI
```bash
python gauntlet.py query "FIND latency, cpu, errors FROM server-42 ORDER BY timestamp DESC LIMIT 5" --dir database
```

### Run Anomaly & Behavioral Diagnostics via CLI
```bash
python gauntlet.py analyze server-42 --metric cpu --dir database
```

### Verify Storage & Segment Integrity
```bash
python gauntlet.py verify --dir database
```

---

## 5. REST & Socket API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/health` | `GET` | Cluster status and engine heartbeat |
| `/api/stats` | `GET` | Storage segment counts, memtable size, and CRC-32 status |
| `/api/events` | `GET` | Authoritative time-series event query with entity filter |
| `/api/query` | `POST` | Execute custom DSL queries against disk segments and WAL |
| `/api/agentic/crawl` | `POST` | Execute 6-Phase Agentic Probe on target URL and ingest telemetry |
| `/api/analytics/profile` | `GET` | Return statistical baseline, P95 quantiles, and Z-score anomalies |
| `/api/analytics/temporal-diff` | `GET` | Calculate temporal drift and percentage shift between two epochs |
| `/index.html` | `GET` | Main single-page web dashboard |
| `/static/logo.png` | `GET` | Static brand logo asset |

---

## 6. Test Suite & Verification

Run the full test suite with verbose output:

```bash
python -m unittest discover tests -v
```

Expected output:
```text
test_full_diagnostic_report ... ok
test_pearson_correlation ... ok
test_anomaly_detection ... ok
test_statistics ... ok
test_chaos_crash_durability_and_restart ... ok
test_full_flagship_pipeline ... ok
test_bloom_filter ... ok
test_index_candidate_pruning ... ok
test_deterministic_id ... ok
test_event_validation_rejections ... ok
test_event_validation_success ... ok
test_pipeline_batch_ingestion ... ok
test_timestamp_parsing ... ok
test_executor ... ok
test_lexer ... ok
test_parser ... ok
test_compaction ... ok
test_crash_restart_and_recovery ... ok
test_memtable_flush_to_segment ... ok
test_write_and_scan ... ok
test_reconstruct_state_as_of ... ok
test_temporal_diff_calculation ... ok
test_time_window_bucketing ... ok
test_wal_append_and_recover ... ok
test_wal_crash_partial_tail_recovery ... ok
test_wal_truncate ... ok

----------------------------------------------------------------------
Ran 26 tests in 0.487s

OK
```
