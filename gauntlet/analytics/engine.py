"""Complete Analytics & Intelligence Engine (Phase 6 - SOUL)."""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from gauntlet.models import Event
from gauntlet.contracts.analytics import MetricSummary, AnomalyRecord, EntityProfile
from gauntlet.analytics.temporal import TemporalEngine, TimeBucket, TemporalDiffReport
from gauntlet.analytics.correlations import CorrelationEngine, CorrelationPair


class AnalyticsEngine:
    """Full-featured temporal intelligence, baseline estimation, and explainable anomaly detection engine."""

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

        # Percentiles (interpolated)
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

    def detect_anomalies(
        self,
        events: List[Event],
        target_metric: str,
        z_threshold: float = 1.5
    ) -> List[AnomalyRecord]:
        """Detects anomalies using dynamic baseline estimation and extracts temporal context."""
        metric_events = [e for e in events if e.type == target_metric and isinstance(e.value, (int, float))]
        if len(metric_events) < 4:
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
                if abs(z) >= 3.5:
                    severity = "CRITICAL"
                elif abs(z) >= 2.5:
                    severity = "HIGH"
                elif abs(z) >= 1.5:
                    severity = "MEDIUM"

                # Find surrounding events (within +/- 300 seconds)
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

        # Discover all metric anomalies
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

    def full_diagnostic_report(self, events: List[Event], entity: str) -> Dict[str, Any]:
        """Comprehensive intelligence report combining profiles, correlations, and anomalies."""
        profile = self.generate_entity_profile(events, entity)
        correlations = CorrelationEngine.compute_metric_correlations(events, entity=entity)

        return {
            "entity": entity,
            "profile": profile.to_dict(),
            "correlations": [c.to_dict() for c in correlations],
            "total_anomalies_detected": len(profile.recent_anomalies)
        }
