# GAUNTLET — Query Language Specification (Phase 4: MIND)

The GAUNTLET Query Engine parses and executes a domain-specific temporal query language.

---

## 1. Syntax Overview

### Data Retrieval (`FIND`)
```sql
FIND <target>
[FROM <entity_id>]
[BETWEEN <start_time> AND <end_time>]
[WHERE <field> <op> <value> [AND ...]]
[ORDER BY <field> [ASC|DESC]]
[LIMIT <count>]
```

**Examples:**
```sql
FIND events FROM server-42 BETWEEN "2026-08-30T10:00:00Z" AND "2026-08-30T14:00:00Z"
FIND cpu FROM server-42 WHERE value > 80.0 ORDER BY timestamp DESC LIMIT 10
FIND deployment FROM server-42
```

---

### Analytical Aggregation (`ANALYZE`)
```sql
ANALYZE <metric>
[FROM <entity_id>]
[WHERE <field> <op> <value>]
[GROUP BY <hour|day|minute>]
```

---

### Temporal Difference (`DIFF`)
```sql
DIFF <entity_id> FROM <timestamp_1> TO <timestamp_2>
```

---

## 2. Query Pipeline

```text
Query String
     │
     ▼
Lexer (Tokens)
     │
     ▼
Recursive Descent Parser (QueryAST)
     │
     ▼
Query Planner (Evaluates Index candidate segments & prune disk reads)
     │
     ▼
Segment & Memtable Scanner
     │
     ▼
Filter, Sort & Limit Execution
     │
     ▼
Structured QueryResult + Telemetry (scanned vs returned rows, latency)
```
