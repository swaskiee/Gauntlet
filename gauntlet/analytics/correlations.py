"""Statistical Correlation & Temporal Association Engine (Phase 6 - SOUL)."""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from gauntlet.models import Event


@dataclass
class CorrelationPair:
    metric_a: str
    metric_b: str
    coefficient: float  # -1.0 to 1.0 (Pearson r)
    relationship: str    # STRONG_POSITIVE, MODERATE_POSITIVE, NEGLIGIBLE, STRONG_NEGATIVE
    sample_size: int

    def to_dict(self) -> dict:
        return {
            "metric_a": self.metric_a,
            "metric_b": self.metric_b,
            "coefficient": round(self.coefficient, 3),
            "relationship": self.relationship,
            "sample_size": self.sample_size
        }


class CorrelationEngine:
    """Zero-dependency statistical correlation matrix and causal event association."""

    @staticmethod
    def pearson_correlation(x: List[float], y: List[float]) -> float:
        """Calculates Pearson correlation coefficient between two numeric series."""
        n = min(len(x), len(y))
        if n < 3:
            return 0.0

        x_slice = x[:n]
        y_slice = y[:n]

        mean_x = sum(x_slice) / n
        mean_y = sum(y_slice) / n

        numerator = sum((x_slice[i] - mean_x) * (y_slice[i] - mean_y) for i in range(n))
        denom_x = sum((x_slice[i] - mean_x) ** 2 for i in range(n))
        denom_y = sum((y_slice[i] - mean_y) ** 2 for i in range(n))

        denominator = math.sqrt(denom_x * denom_y)
        if denominator < 1e-9:
            return 0.0

        return max(-1.0, min(1.0, numerator / denominator))

    @staticmethod
    def compute_metric_correlations(events: List[Event], entity: Optional[str] = None) -> List[CorrelationPair]:
        """Aligns time series metrics on nearest timestamp and computes pairwise correlations."""
        ent_events = [e for e in events if entity is None or e.entity == entity]

        # Group timestamps by metrics
        metric_series: Dict[str, Dict[int, float]] = {}
        for e in ent_events:
            if isinstance(e.value, (int, float)):
                metric_series.setdefault(e.type, {})[e.timestamp] = float(e.value)

        metrics = list(metric_series.keys())
        results: List[CorrelationPair] = []

        for i in range(len(metrics)):
            for j in range(i + 1, len(metrics)):
                m_a = metrics[i]
                m_b = metrics[j]

                dict_a = metric_series[m_a]
                dict_b = metric_series[m_b]

                # Find timestamps aligned within +/- 60s
                matched_a: List[float] = []
                matched_b: List[float] = []

                for ts_a, val_a in sorted(dict_a.items()):
                    # Find closest ts in dict_b
                    closest_ts = min(dict_b.keys(), key=lambda ts_b: abs(ts_b - ts_a), default=None)
                    if closest_ts is not None and abs(closest_ts - ts_a) <= 120:
                        matched_a.append(val_a)
                        matched_b.append(dict_b[closest_ts])

                if len(matched_a) >= 3:
                    coeff = CorrelationEngine.pearson_correlation(matched_a, matched_b)
                    rel = "NEGLIGIBLE"
                    if coeff >= 0.7:
                        rel = "STRONG_POSITIVE"
                    elif coeff >= 0.3:
                        rel = "MODERATE_POSITIVE"
                    elif coeff <= -0.7:
                        rel = "STRONG_NEGATIVE"
                    elif coeff <= -0.3:
                        rel = "MODERATE_NEGATIVE"

                    results.append(CorrelationPair(
                        metric_a=m_a,
                        metric_b=m_b,
                        coefficient=coeff,
                        relationship=rel,
                        sample_size=len(matched_a)
                    ))

        return results
