"""Query Parser and AST for GAUNTLET (Phase 4 - MIND)."""

from dataclasses import dataclass, field
from typing import Any, List, Optional
from gauntlet.query.lexer import Lexer, LexerError, Token, TokenType
from gauntlet.models import parse_timestamp


class ParserError(Exception):
    pass


@dataclass
class FilterCondition:
    field: str
    operator: str
    value: Any


@dataclass
class QueryAST:
    command: str  # FIND, ANALYZE, DIFF, STATE
    target: str   # events, cpu, memory, etc.
    entity: Optional[str] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None
    filters: List[FilterCondition] = field(default_factory=list)
    order_by: Optional[str] = "timestamp"
    order_dir: str = "ASC"
    limit: Optional[int] = None
    group_by: Optional[str] = None
    diff_from_ts: Optional[int] = None
    diff_to_ts: Optional[int] = None


class QueryParser:
    """Recursive descent parser translating tokens into structured QueryAST."""

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _curr(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Optional[Token]:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def _advance(self) -> Token:
        tok = self._curr()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _match(self, *types: TokenType) -> bool:
        if self._curr().type in types:
            self._advance()
            return True
        return False

    def _expect(self, type_: TokenType, error_msg: str) -> Token:
        if self._curr().type != type_:
            raise ParserError(f"{error_msg}. Got {self._curr().type.name} ('{self._curr().value}') at line {self._curr().line}, col {self._curr().col}")
        return self._advance()

    def parse(self) -> QueryAST:
        first = self._curr()

        if first.type == TokenType.FIND:
            self._advance()
            return self._parse_find_query()
        elif first.type == TokenType.ANALYZE:
            self._advance()
            return self._parse_analyze_query()
        elif first.type == TokenType.DIFF:
            self._advance()
            return self._parse_diff_query()
        else:
            raise ParserError(f"Unsupported query command '{first.value}' at line {first.line}, col {first.col}")

    def _parse_find_query(self) -> QueryAST:
        # Target: events, cpu, memory, etc. or wildcard *
        target = "events"
        if self._curr().type in (TokenType.IDENTIFIER, TokenType.STRING) or self._curr().value == "*":
            target = str(self._advance().value)
            if target == "*":
                target = "events"

        ast = QueryAST(command="FIND", target=target)

        # Optional FROM clause
        if self._match(TokenType.FROM):
            ent_tok = self._expect(TokenType.IDENTIFIER, "Expected entity identifier after FROM")
            ast.entity = str(ent_tok.value)

        # Optional clauses in any order: WHERE, BETWEEN, LAST, ORDER BY, LIMIT
        while self._curr().type != TokenType.EOF:
            if self._match(TokenType.WHERE):
                self._parse_where_clause(ast)
            elif self._match(TokenType.BETWEEN):
                self._parse_between_clause(ast)
            elif self._match(TokenType.ORDER):
                self._expect(TokenType.BY, "Expected BY after ORDER")
                ord_tok = self._expect(TokenType.IDENTIFIER, "Expected column name after ORDER BY")
                ast.order_by = str(ord_tok.value)
                if self._match(TokenType.DESC):
                    ast.order_dir = "DESC"
                elif self._match(TokenType.ASC):
                    ast.order_dir = "ASC"
            elif self._match(TokenType.LIMIT):
                lim_tok = self._expect(TokenType.NUMBER, "Expected integer limit number")
                ast.limit = int(lim_tok.value)
            else:
                break

        return ast

    def _parse_analyze_query(self) -> QueryAST:
        target = str(self._expect(TokenType.IDENTIFIER, "Expected metric identifier after ANALYZE").value)
        ast = QueryAST(command="ANALYZE", target=target)

        if self._match(TokenType.FROM):
            ast.entity = str(self._expect(TokenType.IDENTIFIER, "Expected entity after FROM").value)

        while self._curr().type != TokenType.EOF:
            if self._match(TokenType.WHERE):
                self._parse_where_clause(ast)
            elif self._match(TokenType.BETWEEN):
                self._parse_between_clause(ast)
            elif self._match(TokenType.GROUP):
                self._expect(TokenType.BY, "Expected BY after GROUP")
                grp = self._expect(TokenType.IDENTIFIER, "Expected bucket name (e.g. hour, minute)").value
                ast.group_by = str(grp)
            else:
                break

        return ast

    def _parse_diff_query(self) -> QueryAST:
        # DIFF server-42 FROM 1000 TO 2000
        target = "events"
        entity = None
        if self._curr().type == TokenType.IDENTIFIER:
            entity = str(self._advance().value)

        ast = QueryAST(command="DIFF", target=target, entity=entity)
        if self._match(TokenType.FROM):
            t1 = self._parse_value()
            ast.diff_from_ts = parse_timestamp(t1)
        if self._match(TokenType.IDENTIFIER) and str(self.tokens[self.pos-1].value).upper() == "TO":
            t2 = self._parse_value()
            ast.diff_to_ts = parse_timestamp(t2)
        return ast

    def _parse_where_clause(self, ast: QueryAST) -> None:
        while True:
            field_tok = self._expect(TokenType.IDENTIFIER, "Expected field name in WHERE clause")
            field_name = str(field_tok.value)

            op_tok = self._curr()
            if op_tok.type not in (TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.GTE, TokenType.LT, TokenType.LTE):
                raise ParserError(f"Expected comparison operator in WHERE, got '{op_tok.value}'")
            self._advance()
            op = op_tok.value

            val = self._parse_value()

            # Special field mappings for fast AST slots
            if field_name.lower() == "entity" and op == "=":
                ast.entity = str(val)
            elif field_name.lower() == "type" and op == "=" and ast.target == "events":
                ast.target = str(val)
            else:
                ast.filters.append(FilterCondition(field=field_name, operator=op, value=val))

            if not self._match(TokenType.AND):
                break

    def _parse_between_clause(self, ast: QueryAST) -> None:
        start_val = self._parse_value()
        self._expect(TokenType.AND, "Expected AND in BETWEEN clause")
        end_val = self._parse_value()

        ast.start_ts = parse_timestamp(start_val)
        ast.end_ts = parse_timestamp(end_val)

    def _parse_value(self) -> Any:
        tok = self._curr()
        if tok.type in (TokenType.STRING, TokenType.NUMBER, TokenType.IDENTIFIER):
            self._advance()
            return tok.value
        raise ParserError(f"Expected literal value (string/number), got {tok.type.name} at line {tok.line}")


def parse_query(query_text: str) -> QueryAST:
    """Convenience helper: Tokenize and parse query text into QueryAST."""
    lexer = Lexer(query_text)
    tokens = lexer.tokenize()
    parser = QueryParser(tokens)
    return parser.parse()
