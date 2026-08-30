"""Lexer / Tokenizer for GAUNTLET Query Language (Phase 4 - MIND)."""

import re
from enum import Enum, auto
from typing import List, Optional


class TokenType(Enum):
    # Keywords
    FIND = auto()
    ANALYZE = auto()
    FROM = auto()
    WHERE = auto()
    BETWEEN = auto()
    AND = auto()
    ORDER = auto()
    BY = auto()
    ASC = auto()
    DESC = auto()
    LIMIT = auto()
    LAST = auto()
    GROUP = auto()
    DIFF = auto()
    STATE = auto()
    AS = auto()
    OF = auto()

    # Literals & Identifiers
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Operators
    EQ = auto()          # = or ==
    NEQ = auto()         # !=
    GT = auto()          # >
    GTE = auto()         # >=
    LT = auto()          # <
    LTE = auto()         # <=
    COMMA = auto()

    EOF = auto()


class Token:
    def __init__(self, type_: TokenType, value: any, line: int = 1, col: int = 1) -> None:
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)})"


class LexerError(Exception):
    pass


class Lexer:
    """Tokenizes GAUNTLET DSL queries."""

    KEYWORDS = {
        "FIND": TokenType.FIND,
        "SELECT": TokenType.FIND,
        "ANALYZE": TokenType.ANALYZE,
        "FROM": TokenType.FROM,
        "WHERE": TokenType.WHERE,
        "BETWEEN": TokenType.BETWEEN,
        "AND": TokenType.AND,
        "ORDER": TokenType.ORDER,
        "BY": TokenType.BY,
        "ASC": TokenType.ASC,
        "DESC": TokenType.DESC,
        "LIMIT": TokenType.LIMIT,
        "LAST": TokenType.LAST,
        "GROUP": TokenType.GROUP,
        "DIFF": TokenType.DIFF,
        "STATE": TokenType.STATE,
        "AS": TokenType.AS,
        "OF": TokenType.OF,
    }

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]

            if ch in " \t\r\n":
                if ch == "\n":
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.pos += 1
                continue

            if ch == ",":
                tokens.append(Token(TokenType.COMMA, ",", self.line, self.col))
                self.pos += 1
                self.col += 1
                continue

            # Multi-char operators
            if ch == "!" and self.pos + 1 < len(self.text) and self.text[self.pos + 1] == "=":
                tokens.append(Token(TokenType.NEQ, "!=", self.line, self.col))
                self.pos += 2
                self.col += 2
                continue

            if ch == "=":
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == "=":
                    self.pos += 1
                tokens.append(Token(TokenType.EQ, "=", self.line, self.col))
                self.pos += 1
                self.col += 1
                continue

            if ch == ">":
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == "=":
                    tokens.append(Token(TokenType.GTE, ">=", self.line, self.col))
                    self.pos += 2
                    self.col += 2
                else:
                    tokens.append(Token(TokenType.GT, ">", self.line, self.col))
                    self.pos += 1
                    self.col += 1
                continue

            if ch == "<":
                if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == "=":
                    tokens.append(Token(TokenType.LTE, "<=", self.line, self.col))
                    self.pos += 2
                    self.col += 2
                else:
                    tokens.append(Token(TokenType.LT, "<", self.line, self.col))
                    self.pos += 1
                    self.col += 1
                continue

            if ch == "*":
                tokens.append(Token(TokenType.IDENTIFIER, "*", self.line, self.col))
                self.pos += 1
                self.col += 1
                continue

            # Strings: "string" or 'string'
            if ch in ('"', "'"):
                quote_char = ch
                start_col = self.col
                self.pos += 1
                self.col += 1
                str_buf = []
                while self.pos < len(self.text) and self.text[self.pos] != quote_char:
                    str_buf.append(self.text[self.pos])
                    self.pos += 1
                    self.col += 1
                if self.pos >= len(self.text):
                    raise LexerError(f"Unterminated string literal at line {self.line}, col {start_col}")
                self.pos += 1  # closing quote
                self.col += 1
                tokens.append(Token(TokenType.STRING, "".join(str_buf), self.line, start_col))
                continue

            # Numbers
            if ch.isdigit() or (ch == "-" and self.pos + 1 < len(self.text) and self.text[self.pos + 1].isdigit()):
                start_col = self.col
                num_buf = [ch]
                self.pos += 1
                self.col += 1
                is_float = False
                while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == "."):
                    if self.text[self.pos] == ".":
                        is_float = True
                    num_buf.append(self.text[self.pos])
                    self.pos += 1
                    self.col += 1
                raw_num = "".join(num_buf)
                val = float(raw_num) if is_float else int(raw_num)
                tokens.append(Token(TokenType.NUMBER, val, self.line, start_col))
                continue

            # Identifiers / Keywords (including hyphenated identifiers like server-42)
            if ch.isalnum() or ch in ("_", "-"):
                start_col = self.col
                id_buf = [ch]
                self.pos += 1
                self.col += 1
                while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] in ("_", "-", ".")):
                    id_buf.append(self.text[self.pos])
                    self.pos += 1
                    self.col += 1
                raw_id = "".join(id_buf)
                upper_id = raw_id.upper()
                if upper_id in self.KEYWORDS:
                    tokens.append(Token(self.KEYWORDS[upper_id], upper_id, self.line, start_col))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, raw_id, self.line, start_col))
                continue

            raise LexerError(f"Unexpected character '{ch}' at line {self.line}, col {self.col}")

        tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return tokens
