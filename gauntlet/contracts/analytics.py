"""Analytics & Intelligence Contract for GAUNTLET (Phase 5 & 6 - TIME & SOUL).

This file defines the clean interface boundary between Nitanshu's core systems (65%)
and Swati's analytics & anomaly intelligence layer (35%).
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol
from gauntlet.models import Event
from gauntlet.query.executor import QueryResult


@dataclass
class MetricSummary:
    count: int = 0
    min: float = 0.0
    max: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    stddev: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "min": round(self.min, 2),
            "max": round(self.max, 2),
            "mean": round(self.mean, 2),
            "median": round(self.median, 2),
            "stddev": round(self.stddev, 2),
            "p90": round(self.p90, 2),
            "p95": round(self.p95, 2),
            "p99": round(self.p99, 2),
        }


@dataclass
class AnomalyRecord:
    metric: str
    entity: str
    timestamp: int
    observed_value: float
    expected_baseline: float
    deviation_pct: float
    z_score: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    evidence: List[str] = field(default_factory=list)
    assessment: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "entity": self.entity,
            "timestamp": self.timestamp,
            "observed_value": round(self.observed_value, 2),
            "expected_baseline": round(self.expected_baseline, 2),
            "deviation_pct": round(self.deviation_pct, 2),
            "z_score": round(self.z_score, 2),
            "severity": self.severity,
            "evidence": self.evidence,
            "assessment": self.assessment,
        }


@dataclass
class EntityProfile:
    entity: str
    total_events: int
    active_span_seconds: int
    metrics: Dict[str, MetricSummary]
    recent_anomalies: List[AnomalyRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "total_events": self.total_events,
            "active_span_seconds": self.active_span_seconds,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "recent_anomalies": [a.to_dict() for a in self.recent_anomalies],
        }


class AnalyticsContract(Protocol):
    """Formal protocol for Swati's 35% Analytics & Intelligence Engine."""

    def compute_statistics(self, values: List[float]) -> MetricSummary:
        ...

    def detect_anomalies(self, events: List[Event], target_metric: str, z_threshold: float = 3.0) -> List[AnomalyRecord]:
        ...

    def generate_entity_profile(self, events: List[Event], entity: str) -> EntityProfile:
        ...


class BuiltinAnalyticsEngine:
    """Deterministic, zero-dependency reference analytics engine satisfying AnalyticsContract."""

    def compute_statistics(self, values: List[float]) -> MetricSummary:
        if not values:
            return MetricSummary()

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        total = sum(sorted_vals)
        mean = total / n

        # Median
        if n % 2 == 1:
            median = sorted_vals[n // 2]
        else:
            median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

        # Variance & Stddev
        variance = sum((x - mean) ** 2 for x in sorted_vals) / n
        stddev = math.sqrt(variance)

        # Percentiles
        def get_p(p: float) -> float:
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_vals[int(k)]
            return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)

        return MetricSummary(
            count=n,
            min=sorted_vals[0],
            max=sorted_vals[-1],
            mean=mean,
            median=median,
            stddev=stddev,
            p90=get_p(0.90),
            p95=get_p(0.95),
            p99=get_p(0.99)
        )

    def detect_anomalies(self, events: List[Event], target_metric: str, z_threshold: float = 2.5) -> List[AnomalyRecord]:
        """Calculates historical baselines and flags statistically significant deviations."""
        metric_events = [e for e in events if e.type == target_metric and isinstance(e.value, (int, float))]
        if len(metric_events) < 5:
            return []

        vals = [float(e.value) for e in metric_events]
        stats = self.compute_statistics(vals)
        if stats.stddev < 1e-5:
            return []

        anomalies: List[AnomalyRecord] = []
        for e in metric_events:
            val = float(e.value)
            z = (val - stats.mean) / stats.stddev

            if abs(z) >= z_threshold:
                dev_pct = ((val - stats.mean) / stats.mean) * 100.0 if stats.mean != 0 else 0.0

                severity = "LOW"
                if abs(z) >= 4.0:
                    severity = "CRITICAL"
                elif abs(z) >= 3.0:
                    severity = "HIGH"
                elif abs(z) >= 2.0:
                    severity = "MEDIUM"

                # Find surrounding events (within +/- 300 seconds, prioritized by closest time delta)
                nearby_events = [
                    ne for ne in events
                    if abs(ne.timestamp - e.timestamp) <= 300 and ne.event_id != e.event_id
                ]
                nearby_events.sort(key=lambda ne: abs(ne.timestamp - e.timestamp))
                nearby = [
                    f"{ne.type} (seq {ne.sequence_num}, val={ne.value})"
                    for ne in nearby_events
                ]

                anomalies.append(AnomalyRecord(
                    metric=target_metric,
                    entity=e.entity,
                    timestamp=e.timestamp,
                    observed_value=val,
                    expected_baseline=stats.mean,
                    deviation_pct=dev_pct,
                    z_score=z,
                    severity=severity,
                    evidence=nearby[:5],
                    assessment=f"Significant {target_metric} deviation (+{round(dev_pct, 1)}%) detected relative to baseline {round(stats.mean, 1)}."
                ))

        return anomalies

    def generate_entity_profile(self, events: List[Event], entity: str) -> EntityProfile:
        ent_events = [e for e in events if e.entity == entity]
        if not ent_events:
            return EntityProfile(entity=entity, total_events=0, active_span_seconds=0, metrics={})

        min_ts = min(e.timestamp for e in ent_events)
        max_ts = max(e.timestamp for e in ent_events)
        span = max_ts - min_ts

        # Group by numeric metrics
        metric_groups: Dict[str, List[float]] = {}
        for e in ent_events:
            if isinstance(e.value, (int, float)):
                metric_groups.setdefault(e.type, []).append(float(e.value))

        metrics_summary = {
            m: self.compute_statistics(vals)
            for m, vals in metric_groups.items()
        }

        # Check anomalies across metrics
        anomalies = []
        for m in metric_groups:
            anomalies.extend(self.detect_anomalies(ent_events, m))

        return EntityProfile(
            entity=entity,
            total_events=len(ent_events),
            active_span_seconds=span,
            metrics=metrics_summary,
            recent_anomalies=anomalies[:10]
        )
