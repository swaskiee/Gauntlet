"""Unit tests for Phase 4 - MIND (Lexer, Parser, and Query Execution)."""

import shutil
import tempfile
import unittest
from pathlib import Path
from gauntlet.models import Event
from gauntlet.storage.engine import StorageEngine
from gauntlet.index.engine import IndexEngine
from gauntlet.query.lexer import Lexer, TokenType
from gauntlet.query.parser import parse_query, QueryAST
from gauntlet.query.executor import QueryExecutor


class TestQueryEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = StorageEngine(self.test_dir, memtable_max_events=10)
        self.index = IndexEngine()

        # Seed sample data
        events = [
            Event(event_id="e1", entity="server-42", timestamp=1000, type="cpu", value=42.0, sequence_num=1),
            Event(event_id="e2", entity="server-42", timestamp=1010, type="cpu", value=85.5, sequence_num=2),
            Event(event_id="e3", entity="server-42", timestamp=1020, type="cpu", value=94.2, sequence_num=3),
            Event(event_id="e4", entity="server-42", timestamp=1015, type="deployment", value="v2.8.1", sequence_num=4),
            Event(event_id="e5", entity="server-99", timestamp=1000, type="cpu", value=20.0, sequence_num=5),
        ]
        for e in events:
            self.storage.write(e)
        self.storage.flush()
        self.index.rebuild_from_segments(self.storage.segments)
        self.executor = QueryExecutor(self.storage, self.index)

    def tearDown(self) -> None:
        self.storage.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_lexer(self) -> None:
        query = 'FIND cpu FROM server-42 WHERE value > 80.0'
        tokens = Lexer(query).tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(types, [
            TokenType.FIND,
            TokenType.IDENTIFIER,
            TokenType.FROM,
            TokenType.IDENTIFIER,
            TokenType.WHERE,
            TokenType.IDENTIFIER,
            TokenType.GT,
            TokenType.NUMBER,
            TokenType.EOF
        ])

    def test_parser(self) -> None:
        ast = parse_query('FIND cpu FROM server-42 BETWEEN 1000 AND 1020 WHERE value >= 80 ORDER BY timestamp DESC LIMIT 5')
        self.assertEqual(ast.command, "FIND")
        self.assertEqual(ast.target, "cpu")
        self.assertEqual(ast.entity, "server-42")
        self.assertEqual(ast.start_ts, 1000)
        self.assertEqual(ast.end_ts, 1020)
        self.assertEqual(ast.order_dir, "DESC")
        self.assertEqual(ast.limit, 5)
        self.assertEqual(len(ast.filters), 1)
        self.assertEqual(ast.filters[0].field, "value")
        self.assertEqual(ast.filters[0].operator, ">=")
        self.assertEqual(ast.filters[0].value, 80)

    def test_executor(self) -> None:
        res = self.executor.execute('FIND cpu FROM server-42 WHERE value > 80 ORDER BY timestamp ASC')
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(res.rows[0][3], 85.5)
        self.assertEqual(res.rows[1][3], 94.2)
        self.assertEqual(res.telemetry.returned_rows, 2)
        self.assertTrue(res.telemetry.execution_time_ms >= 0.0)


if __name__ == "__main__":
    unittest.main()
