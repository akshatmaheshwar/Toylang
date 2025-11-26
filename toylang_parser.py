"""
ToyLang parser for the small example language used in the repo.

This is a lightweight, resilient parser intended to parse the example
programs in `programs.py` and produce AST nodes defined in `toylang_ast.py`.
It supports assignments, if/else blocks, assertions, integer literals,
variables, binary expressions (+,-,*,/), and comparisons (==, !=, <, >, <=, >=).
"""
import re
from typing import List, Tuple
from toylang_ast import *


_TOKEN_RE = re.compile(r"\s*(?:(\d+)|([A-Za-z_][A-Za-z0-9_]*)|(==|!=|<=|>=|[+\-*/<>=(){}=,])|(.))")


class ParseError(Exception):
    pass


def tokenize(src: str) -> List[Tuple[str, str]]:
    tokens = []
    pos = 0
    while pos < len(src):
        m = _TOKEN_RE.match(src, pos)
        if not m:
            break
        num, ident, op, bad = m.groups()
        if bad:
            raise ParseError(f"Unexpected character: {bad!r}")
        if num:
            tokens.append(("NUMBER", num))
        elif ident:
            tokens.append(("IDENT", ident))
        elif op:
            tokens.append((op, op))
        pos = m.end()
    tokens.append(("EOF", ""))
    return tokens


class Parser:
    def __init__(self, tokens: List[Tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos][0]

    def peek_val(self):
        return self.tokens[self.pos][1]

    def consume(self, expected=None):
        tok = self.tokens[self.pos]
        if expected and tok[0] != expected:
            raise ParseError(f"Expected {expected} but got {tok}")
        self.pos += 1
        return tok

    def accept(self, expected) -> bool:
        if self.peek() == expected:
            self.consume()
            return True
        return False

    def parse_program(self) -> Program:
        stmts = self.parse_statements()
        return Program(stmts)

    def parse_statements(self, stop_tokens=None) -> List[Statement]:
        if stop_tokens is None:
            stop_tokens = {"EOF"}
        stmts = []
        while self.peek() not in stop_tokens:
            stmt = self.parse_statement()
            stmts.append(stmt)
        return stmts

    def parse_statement(self) -> Statement:
        tok = self.peek()
        if tok == 'IDENT' and self.peek_val() == 'if':
            # parse if
            self.consume('IDENT')
            if self.peek() == '(':
                self.consume('(')
            cond = self.parse_comparison()
            if self.peek() == ')':
                self.consume(')')
            # expect '{'
            if self.peek() == '{':
                self.consume('{')
            then_block = self.parse_statements(stop_tokens={'}'})
            if self.peek() == '}':
                self.consume('}')

            else_block = []
            if self.peek() == 'IDENT' and self.peek_val() == 'else':
                self.consume('IDENT')
                if self.peek() == '{':
                    self.consume('{')
                else_block = self.parse_statements(stop_tokens={'}'})
                if self.peek() == '}':
                    self.consume('}')

            return IfStatement(cond, then_block, else_block)

        if tok == 'IDENT' and self.peek_val() == 'assert':
            self.consume('IDENT')
            if self.peek() == '(':
                self.consume('(')
            cond = self.parse_comparison()
            if self.peek() == ')':
                self.consume(')')
            return AssertStatement(cond)

        if tok == 'IDENT':
            # assignment
            name = self.consume('IDENT')[1]
            if self.peek() == '=':
                self.consume('=')
            expr = self.parse_expr()
            return Assignment(name, expr)

        raise ParseError(f"Unexpected token in statement: {self.tokens[self.pos]}")

    def parse_comparison(self) -> Comparison:
        left = self.parse_expr()
        op_tok = self.peek()
        op_val = self.peek_val()
        if op_tok in ('==', '!=', '<', '>', '<=', '>='):
            self.consume()
            right = self.parse_expr()
            mapping = {
                '==': CompOp.EQ,
                '!=': CompOp.NE,
                '<': CompOp.LT,
                '>': CompOp.GT,
                '<=': CompOp.LE,
                '>=': CompOp.GE,
            }
            return Comparison(left, mapping[op_val], right)
        else:
            raise ParseError(f"Expected comparison operator, got {op_tok}")

    def parse_expr(self) -> Expr:
        node = self.parse_term()
        while self.peek() in ('+', '-'):
            op = self.consume()[0]
            right = self.parse_term()
            binop = BinOp.ADD if op == '+' else BinOp.SUB
            node = BinaryOp(node, binop, right)
        return node

    def parse_term(self) -> Expr:
        node = self.parse_factor()
        while self.peek() in ('*', '/'):
            op = self.consume()[0]
            right = self.parse_factor()
            binop = BinOp.MUL if op == '*' else BinOp.DIV
            node = BinaryOp(node, binop, right)
        return node

    def parse_factor(self) -> Expr:
        tok = self.peek()
        # Handle negative numbers
        if tok == '-':
            self.consume('-')
            # Parse the number or sub-expression after the minus
            factor = self.parse_factor()
            # Return as subtraction from zero
            return BinaryOp(Number(0), BinOp.SUB, factor)
        if tok == 'NUMBER':
            val = int(self.consume('NUMBER')[1])
            return Number(val)
        if tok == 'IDENT':
            name = self.consume('IDENT')[1]
            return Variable(name)
        if tok == '(':
            self.consume('(')
            expr = self.parse_expr()
            if self.peek() == ')':
                self.consume(')')
            return expr
        raise ParseError(f"Unexpected token in factor: {self.tokens[self.pos]}")


def parse_program(src: str) -> Program:
    tokens = tokenize(src)
    p = Parser(tokens)
    prog = p.parse_program()
    return prog
