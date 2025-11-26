"""
ToyLang AST (Abstract Syntax Tree) Definitions

Grammar:
    program     ::= statement*
    statement   ::= assignment | if_stmt | assert_stmt
    assignment  ::= ID '=' expr
    if_stmt     ::= 'if' '(' condition ')' '{' statement* '}' ['else' '{' statement* '}']
    assert_stmt ::= 'assert' '(' condition ')'
    condition   ::= expr comparison_op expr
    expr        ::= term (('+' | '-') term)*
    term        ::= factor (('*' | '/') factor)*
    factor      ::= NUMBER | ID | '(' expr ')'
    comparison_op ::= '==' | '!=' | '<' | '>' | '<=' | '>='
"""

from dataclasses import dataclass
from typing import List, Union
from enum import Enum


class CompOp(Enum):
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="


class BinOp(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"


# Expression nodes
@dataclass
class Number:
    value: int
    
    def __repr__(self):
        return f"Num({self.value})"


@dataclass
class Variable:
    name: str
    
    def __repr__(self):
        return f"Var({self.name})"


@dataclass
class BinaryOp:
    left: 'Expr'
    op: BinOp
    right: 'Expr'
    
    def __repr__(self):
        return f"BinOp({self.left} {self.op.value} {self.right})"


Expr = Union[Number, Variable, BinaryOp]


# Condition nodes
@dataclass
class Comparison:
    left: Expr
    op: CompOp
    right: Expr
    
    def __repr__(self):
        return f"Comp({self.left} {self.op.value} {self.right})"


# Statement nodes
@dataclass
class Assignment:
    var_name: str
    expr: Expr
    
    def __repr__(self):
        return f"Assign({self.var_name} = {self.expr})"


@dataclass
class IfStatement:
    condition: Comparison
    then_block: List['Statement']
    else_block: List['Statement']
    
    def __repr__(self):
        return f"If({self.condition})"


@dataclass
class AssertStatement:
    condition: Comparison
    
    def __repr__(self):
        return f"Assert({self.condition})"


Statement = Union[Assignment, IfStatement, AssertStatement]


@dataclass
class Program:
    statements: List[Statement]
    
    def __repr__(self):
        return f"Program({len(self.statements)} stmts)"