# GAUNTLET — Analytics Interface Contract (Swati's 35% Ownership)

This document specifies the exact contract between **Nitanshu's Core Systems (65%)** and **Swati's Analytics Subsystem (35%)**.

---

## 1. Boundary & Responsibilities

```text
Nitanshu's Systems (65%)
  - Storage (WAL, Memtable, Segments)
  - Indexing (Bloom Filter, Time Index, Entity Index)
  - Query Engine (Lexer, Parser, Executor)
  - API & UI Server
             │
             │ Provides Structured QueryResult & List[Event]
             ▼
Swati's Analytics (35%)
  - Descriptive Statistics (Mean, Median, Stddev, Percentiles)
  - Temporal Aggregations & Rolling Windows
  - Baselines & Expected Behavior Estimation
  - Z-Score Anomaly Detection
  - Correlating Surrounding Evidence
  - Entity Behavioral Profiles
             │
             │ Returns MetricSummary, AnomalyRecord, EntityProfile
             ▼
Nitanshu's UI / API Layer
  - Renders visual console, tables, and timeline alerts
```

---

## 2. Python Protocol Contract (`gauntlet.contracts.analytics`)

```python
class AnalyticsContract(Protocol):
    def compute_statistics(self, values: List[float]) -> MetricSummary:
        ...

    def detect_anomalies(self, events: List[Event], target_metric: str, z_threshold: float = 3.0) -> List[AnomalyRecord]:
        ...

    def generate_entity_profile(self, events: List[Event], entity: str) -> EntityProfile:
        ...
```

---

## 3. Data Transfer Objects

### `MetricSummary`
```json
{
  "count": 100,
  "min": 38.2,
  "max": 94.2,
  "mean": 42.1,
  "median": 41.0,
  "stddev": 4.8,
  "p90": 46.5,
  "p95": 58.2,
  "p99": 89.1
}
```

### `AnomalyRecord`
```json
{
  "metric": "cpu",
  "entity": "server-42",
  "timestamp": 1788098660,
  "observed_value": 94.2,
  "expected_baseline": 41.2,
  "deviation_pct": 128.6,
  "z_score": 5.21,
  "severity": "HIGH",
  "evidence": ["deployment (seq 8, val=v2.8.1)", "latency (seq 10, val=84.0)"],
  "assessment": "Significant cpu deviation (+128.6%) detected relative to baseline 41.2."
}
```
