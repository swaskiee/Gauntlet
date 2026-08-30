"""Query Planner and Execution Engine for GAUNTLET (Phase 4 - MIND)."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from gauntlet.models import Event
from gauntlet.query.parser import QueryAST, parse_query
from gauntlet.storage.engine import StorageEngine
from gauntlet.index.engine import IndexEngine


@dataclass
class QueryTelemetry:
    scanned_rows: int = 0
    returned_rows: int = 0
    segments_touched: int = 0
    index_hits: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "scanned_rows": self.scanned_rows,
            "returned_rows": self.returned_rows,
            "segments_touched": self.segments_touched,
            "index_hits": self.index_hits,
            "execution_time_ms": round(self.execution_time_ms, 3)
        }


@dataclass
class QueryResult:
    """Structured query execution result matching the system contract."""
    columns: List[str]
    rows: List[List[Any]]
    events: List[Event]
    telemetry: QueryTelemetry

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "metadata": self.telemetry.to_dict()
        }


class QueryExecutor:
    """Plans and executes queries against StorageEngine using IndexEngine acceleration."""

    def __init__(self, storage: StorageEngine, index: Optional[IndexEngine] = None) -> None:
        self.storage = storage
        self.index = index

    def execute(self, query: str | QueryAST) -> QueryResult:
        start_time = time.perf_counter()
        telemetry = QueryTelemetry()

        if isinstance(query, str):
            ast = parse_query(query)
        else:
            ast = query

        target_type = None if ast.target == "events" else ast.target

        # 1. Determine segments to scan via Index Planner
        if self.index:
            candidate_segments = self.index.find_candidate_segments(
                entity=ast.entity,
                start_ts=ast.start_ts,
                end_ts=ast.end_ts,
                event_type=target_type
            )
            telemetry.segments_touched = len(candidate_segments)
            telemetry.index_hits = len(self.storage.segments) - len(candidate_segments)
        else:
            telemetry.segments_touched = len(self.storage.segments)

        # 2. Scan records
        scanned_events: List[Event] = []
        for event in self.storage.scan(
            entity=ast.entity,
            start_ts=ast.start_ts,
            end_ts=ast.end_ts,
            event_type=target_type
        ):
            telemetry.scanned_rows += 1

            # Evaluate filters
            if not self._evaluate_filters(event, ast.filters):
                continue

            scanned_events.append(event)

        # 3. Sort
        if ast.order_by == "timestamp":
            scanned_events.sort(key=lambda e: e.timestamp, reverse=(ast.order_dir == "DESC"))
        elif ast.order_by == "value":
            scanned_events.sort(key=lambda e: (e.value is not None, e.value), reverse=(ast.order_dir == "DESC"))

        # 4. Limit
        if ast.limit is not None:
            scanned_events = scanned_events[:ast.limit]

        telemetry.returned_rows = len(scanned_events)
        telemetry.execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        # Build table representation
        columns = ["timestamp", "entity", "type", "value", "event_id"]
        rows = [
            [e.timestamp, e.entity, e.type, e.value, e.event_id]
            for e in scanned_events
        ]

        return QueryResult(
            columns=columns,
            rows=rows,
            events=scanned_events,
            telemetry=telemetry
        )

    def _evaluate_filters(self, event: Event, filters: list) -> bool:
        for f in filters:
            val = getattr(event, f.field, None)
            if val is None:
                val = event.attributes.get(f.field)
            if val is None:
                return False

            try:
                if f.operator in ("=", "==") and val != f.value:
                    return False
                elif f.operator == "!=" and val == f.value:
                    return False
                elif f.operator == ">" and not (val > f.value):
                    return False
                elif f.operator == ">=" and not (val >= f.value):
                    return False
                elif f.operator == "<" and not (val < f.value):
                    return False
                elif f.operator == "<=" and not (val <= f.value):
                    return False
            except Exception:
                return False

        return True
