"""Command-Line Interface for GAUNTLET."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List
from gauntlet.models import Event, EventValidator
from gauntlet.storage.engine import StorageEngine
from gauntlet.index.engine import IndexEngine
from gauntlet.query.executor import QueryExecutor
from gauntlet.analytics.engine import AnalyticsEngine
from gauntlet.api.server import create_server


def cmd_init(args: argparse.Namespace) -> None:
    db_dir = Path(args.dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    engine = StorageEngine(db_dir)
    engine.close()
    print(f"[OK] Initialized clean GAUNTLET database at '{db_dir}'")


def cmd_ingest(args: argparse.Namespace) -> None:
    db_dir = Path(args.dir)
    engine = StorageEngine(db_dir)
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    accepted = 0
    errors = 0
    t0 = time.perf_counter()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            try:
                d = json.loads(line_str)
                event = EventValidator.validate_and_normalize(d)
                engine.write(event)
                accepted += 1
            except Exception as e:
                errors += 1

    dur = time.perf_counter() - t0
    rate = accepted / dur if dur > 0 else 0
    print(f"[OK] Ingested {accepted} events in {round(dur*1000, 2)} ms ({round(rate, 1)} events/sec). Rejected {errors} errors.")
    engine.close()


def cmd_query(args: argparse.Namespace) -> None:
    db_dir = Path(args.dir)
    storage = StorageEngine(db_dir)
    index = IndexEngine()
    index.rebuild_from_segments(storage.segments)
    executor = QueryExecutor(storage, index)

    res = executor.execute(args.query)

    print(f"\n--- GAUNTLET QUERY RESULTS ({res.telemetry.returned_rows} rows, {res.telemetry.execution_time_ms} ms, {res.telemetry.scanned_rows} scanned, {res.telemetry.index_hits} index hits) ---")
    headers = res.columns
    row_fmts = ["{:<22}", "{:<15}", "{:<12}", "{:<15}", "{:<24}"]
    header_str = " ".join(fmt.format(h) for fmt, h in zip(row_fmts, headers))
    print(header_str)
    print("-" * len(header_str))
    for row in res.rows:
        print(" ".join(fmt.format(str(val)) for fmt, val in zip(row_fmts, row)))
    print("-" * len(header_str) + "\n")
    storage.close()


def cmd_analyze(args: argparse.Namespace) -> None:
    db_dir = Path(args.dir)
    storage = StorageEngine(db_dir)
    analytics = AnalyticsEngine()
    events = list(storage.scan(entity=args.entity))

    if args.metric:
        anomalies = analytics.detect_anomalies(events, args.metric)
        print(f"\n--- ANOMALIES DETECTED FOR ENTITY '{args.entity}' (Metric: {args.metric}) ---")
        if not anomalies:
            print("No anomalies detected above statistical threshold.")
        for a in anomalies:
            print(f"[{a.severity}] Ts: {a.timestamp} | Observed: {a.observed_value} | Baseline: {a.expected_baseline} | Dev: +{a.deviation_pct}% | Z-Score: {a.z_score}")
            print(f"   Assessment: {a.assessment}")
            if a.evidence:
                print(f"   Correlated Evidence: {', '.join(a.evidence)}")
    else:
        profile = analytics.generate_entity_profile(events, args.entity)
        print(f"\n--- BEHAVIORAL PROFILE FOR '{args.entity}' ---")
        print(f"Total Events: {profile.total_events} | Active Span: {profile.active_span_seconds}s")
        for m, stats in profile.metrics.items():
            print(f"Metric '{m}': Mean={stats.mean}, Median={stats.median}, Stddev={stats.stddev}, P95={stats.p95}")

    storage.close()


def cmd_verify(args: argparse.Namespace) -> None:
    db_dir = Path(args.dir)
    storage = StorageEngine(db_dir)
    info = storage.verify_integrity()
    print("\nGAUNTLET INTEGRITY REPORT")
    print("-------------------------")
    print(f"Database Status:     {info['status']}")
    print(f"Segments Checked:    {info['segments_checked']}")
    print(f"Checksums Valid:     {info['checksums_valid']}")
    print(f"Total Records:       {info['total_records']}")
    print(f"Memtable Records:    {info['memtable_records']}")
    if info["issues"]:
        print("Issues found:")
        for iss in info["issues"]:
            print(f"  - {iss}")
    print("-------------------------\n")
    storage.close()


def cmd_serve(args: argparse.Namespace) -> None:
    db_dir = Path(args.dir)
    storage = StorageEngine(db_dir)
    index = IndexEngine()
    index.rebuild_from_segments(storage.segments)
    executor = QueryExecutor(storage, index)
    analytics = AnalyticsEngine()

    server = create_server(storage, index, executor, analytics, host=args.host, port=args.port)
    print(f"[OK] GAUNTLET Server running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GAUNTLET server...")
    finally:
        server.server_close()
        storage.close()


def cmd_benchmark(args: argparse.Namespace) -> None:
    print("\nStarting GAUNTLET Performance Benchmark Harness...")
    import tempfile, shutil
    bench_dir = Path(tempfile.mkdtemp())
    storage = StorageEngine(bench_dir, memtable_max_events=1000)
    index = IndexEngine()

    count = 10000
    events = [
        Event(event_id=f"b_{i}", entity=f"server-{i%10}", timestamp=10000+i, type="cpu", value=40.0 + (i%50), sequence_num=i+1)
        for i in range(count)
    ]

    t0 = time.perf_counter()
    storage.write_batch(events)
    storage.flush()
    ingest_time = time.perf_counter() - t0
    rate = count / ingest_time

    index.rebuild_from_segments(storage.segments)
    executor = QueryExecutor(storage, index)

    t1 = time.perf_counter()
    qres = executor.execute("FIND cpu FROM server-1 WHERE value > 80")
    q_time = (time.perf_counter() - t1) * 1000.0

    print("--------------------------------------------------")
    print(f"Events Ingested:    {count}")
    print(f"Ingestion Time:     {round(ingest_time*1000, 2)} ms")
    print(f"Throughput:         {round(rate, 1)} events/sec")
    print(f"Segment Count:      {len(storage.segments)}")
    print(f"Query Latency:      {round(q_time, 2)} ms (Matched {qres.telemetry.returned_rows} rows)")
    print(f"Scanned vs Total:   {qres.telemetry.scanned_rows} / {count}")
    print("--------------------------------------------------\n")

    storage.close()
    shutil.rmtree(bench_dir, ignore_errors=True)


def main() -> None:
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--dir", default="database", help="Path to database directory (default: 'database')")

    parser = argparse.ArgumentParser(description="GAUNTLET Temporal Data & Analytics Engine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", parents=[parent_parser], help="Initialize a new GAUNTLET database")

    # ingest
    p_ingest = subparsers.add_parser("ingest", parents=[parent_parser], help="Ingest a JSONL event file")
    p_ingest.add_argument("file", help="Path to events.jsonl")

    # query
    p_query = subparsers.add_parser("query", parents=[parent_parser], help="Execute a query")
    p_query.add_argument("query", help="Query string, e.g. 'FIND cpu FROM server-42'")

    # analyze
    p_analyze = subparsers.add_parser("analyze", parents=[parent_parser], help="Run temporal analytics / anomaly detection")
    p_analyze.add_argument("entity", help="Entity ID (e.g. server-42)")
    p_analyze.add_argument("--metric", help="Optional specific metric to analyze")

    # verify
    p_verify = subparsers.add_parser("verify", parents=[parent_parser], help="Verify database integrity and checksums")

    # serve
    p_serve = subparsers.add_parser("serve", parents=[parent_parser], help="Launch HTTP server & web UI")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host binding (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")

    # benchmark
    p_bench = subparsers.add_parser("benchmark", parents=[parent_parser], help="Run performance benchmarks")

    args = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "ingest": cmd_ingest,
        "query": cmd_query,
        "analyze": cmd_analyze,
        "verify": cmd_verify,
        "serve": cmd_serve,
        "benchmark": cmd_benchmark
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
