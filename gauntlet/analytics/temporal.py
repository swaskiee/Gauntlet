"""Temporal Analytics & Historical State Reconstruction (Phase 5 - TIME).

First-principles temporal calculations including time-window aggregations,
state reconstruction as-of timestamps, temporal rate-of-change, and period diffing.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from gauntlet.models import Event


@dataclass
class TimeBucket:
    start_ts: int
    end_ts: int
    event_count: int
    values: List[float]
    mean: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0

    def to_dict(self) -> dict:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "event_count": self.event_count,
            "mean": round(self.mean, 2),
            "min_val": round(self.min_val, 2),
            "max_val": round(self.max_val, 2)
        }


@dataclass
class TemporalDiffReport:
    entity: str
    metric: str
    t1: int
    t2: int
    val1: Optional[float]
    val2: Optional[float]
    absolute_change: float
    percentage_change: float
    intervening_events: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "metric": self.metric,
            "t1": self.t1,
            "t2": self.t2,
            "val1": self.val1,
            "val2": self.val2,
            "absolute_change": round(self.absolute_change, 2),
            "percentage_change": round(self.percentage_change, 2),
            "intervening_events": self.intervening_events
        }


class TemporalEngine:
    """Zero-dependency temporal intelligence and historical reconstruction engine."""

    @staticmethod
    def bucket_by_time_window(events: List[Event], window_seconds: int = 3600) -> List[TimeBucket]:
        """Groups events into discrete temporal windows (tumbling windows)."""
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        min_ts = sorted_events[0].timestamp
        max_ts = sorted_events[-1].timestamp

        buckets_map: Dict[int, List[float]] = {}
        counts_map: Dict[int, int] = {}

        for e in sorted_events:
            bucket_idx = (e.timestamp - min_ts) // window_seconds
            bucket_start = min_ts + bucket_idx * window_seconds

            counts_map[bucket_start] = counts_map.get(bucket_start, 0) + 1
            if isinstance(e.value, (int, float)):
                buckets_map.setdefault(bucket_start, []).append(float(e.value))

        results: List[TimeBucket] = []
        cur_ts = min_ts
        while cur_ts <= max_ts:
            vals = buckets_map.get(cur_ts, [])
            count = counts_map.get(cur_ts, 0)
            mean_val = (sum(vals) / len(vals)) if vals else 0.0
            min_val = min(vals) if vals else 0.0
            max_val = max(vals) if vals else 0.0

            results.append(TimeBucket(
                start_ts=cur_ts,
                end_ts=cur_ts + window_seconds,
                event_count=count,
                values=vals,
                mean=mean_val,
                min_val=min_val,
                max_val=max_val
            ))
            cur_ts += window_seconds

        return results

    @staticmethod
    def reconstruct_state_as_of(events: List[Event], as_of_ts: int, entity: Optional[str] = None) -> Dict[str, Any]:
        """Reconstructs the latest known state of all metrics/attributes for an entity at a given timestamp."""
        filtered = [
            e for e in events
            if e.timestamp <= as_of_ts and (entity is None or e.entity == entity)
        ]
        filtered.sort(key=lambda e: (e.timestamp, e.sequence_num))

        state: Dict[str, Any] = {
            "entity": entity,
            "as_of_timestamp": as_of_ts,
            "metrics": {},
            "last_event_type": None,
            "last_event_time": None
        }

        for e in filtered:
            state["metrics"][e.type] = e.value
            state["last_event_type"] = e.type
            state["last_event_time"] = e.timestamp

        return state

    @staticmethod
    def calculate_temporal_diff(
        events: List[Event],
        entity: str,
        metric: str,
        t1: int,
        t2: int
    ) -> TemporalDiffReport:
        """Compares historical metric states between t1 and t2, isolating intervening causal events."""
        state1 = TemporalEngine.reconstruct_state_as_of(events, t1, entity=entity)
        state2 = TemporalEngine.reconstruct_state_as_of(events, t2, entity=entity)

        v1 = state1["metrics"].get(metric)
        v2 = state2["metrics"].get(metric)

        v1_num = float(v1) if isinstance(v1, (int, float)) else 0.0
        v2_num = float(v2) if isinstance(v2, (int, float)) else 0.0

        abs_diff = v2_num - v1_num
        pct_diff = ((v2_num - v1_num) / v1_num * 100.0) if v1_num != 0 else 0.0

        # Discover intervening state-changing events (e.g. deployments, errors, config changes)
        intervening = [
            f"{e.type} (val={e.value} at t={e.timestamp})"
            for e in events
            if e.entity == entity and t1 < e.timestamp <= t2 and e.type != metric
        ]

        return TemporalDiffReport(
            entity=entity,
            metric=metric,
            t1=t1,
            t2=t2,
            val1=v1_num if v1 is not None else None,
            val2=v2_num if v2 is not None else None,
            absolute_change=abs_diff,
            percentage_change=pct_diff,
            intervening_events=intervening
        )
