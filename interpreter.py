"""
ToyLang Interpreter with Coverage Instrumentation
"""

from typing import Dict, Set, Any
from toylang_ast import *


class Interpreter:
    """Interpreter for ToyLang with coverage tracking"""
    
    def __init__(self):
        self.variables: Dict[str, int] = {}
        self.covered_branches: Set[str] = set()
        self.covered_statements: Set[int] = set()
        self.statement_counter = 0
    
    def reset(self):
        """Reset interpreter state"""
        self.variables = {}
        self.covered_branches = set()
        self.covered_statements = set()
        self.statement_counter = 0
    
    def get_coverage(self) -> Dict[str, Any]:
        """Return coverage information"""
        return {
            'branches': len(self.covered_branches),
            'statements': len(self.covered_statements),
            'branch_set': self.covered_branches.copy(),
            'statement_set': self.covered_statements.copy()
        }
    
    def execute(self, program: Program) -> Dict[str, Any]:
        """Execute a program and return results"""
        self.reset()
        
        try:
            # Initialize all variables that might be used to avoid undefined errors
            # This helps when symbolic execution generates inputs with computed variables
            for stmt in program.statements:
                if isinstance(stmt, Assignment):
                    # Pre-initialize the variable
                    if stmt.var_name not in self.variables:
                        self.variables[stmt.var_name] = 0
            
            for stmt in program.statements:
                self.execute_statement(stmt)
            
            return {
                'status': 'success',
                'variables': self.variables.copy(),
                'coverage': self.get_coverage()
            }
        except AssertionError as e:
            # Assertion failures are still interesting - they provide coverage
            return {
                'status': 'assertion_failed',
                'error': str(e),
                'variables': self.variables.copy(),
                'coverage': self.get_coverage()
            }
        except (RuntimeError, ZeroDivisionError) as e:
            # Runtime errors still provide coverage information
            return {
                'status': 'runtime_error',
                'error': str(e),
                'variables': self.variables.copy(),
                'coverage': self.get_coverage()
            }
        except Exception as e:
            # Catch any other exceptions and still return coverage
            return {
                'status': 'error',
                'error': str(e),
                'variables': self.variables.copy(),
                'coverage': self.get_coverage()
            }
    
    def execute_statement(self, stmt: Statement):
        """Execute a single statement"""
        stmt_id = id(stmt)
        self.covered_statements.add(stmt_id)
        self.statement_counter += 1
        
        if isinstance(stmt, Assignment):
            value = self.eval_expr(stmt.expr)
            self.variables[stmt.var_name] = value
        
        elif isinstance(stmt, IfStatement):
            condition_result = self.eval_condition(stmt.condition)
            
            # Track branch coverage - use hash for consistency
            branch_id = f"if_{hash(str(stmt.condition))}"
            
            if condition_result:
                self.covered_branches.add(f"{branch_id}_then")
                for s in stmt.then_block:
                    self.execute_statement(s)
            else:
                self.covered_branches.add(f"{branch_id}_else") 
                for s in stmt.else_block:
                    self.execute_statement(s)
        
        elif isinstance(stmt, AssertStatement):
            condition_result = self.eval_condition(stmt.condition)
            if not condition_result:
                raise AssertionError(f"Assertion failed: {stmt.condition}")
    
    def eval_expr(self, expr: Expr) -> int:
        """Evaluate an expression to an integer"""
        if isinstance(expr, Number):
            return expr.value
        
        elif isinstance(expr, Variable):
            if expr.name not in self.variables:
                raise RuntimeError(f"Undefined variable: {expr.name}")
            return self.variables[expr.name]
        
        elif isinstance(expr, BinaryOp):
            left_val = self.eval_expr(expr.left)
            right_val = self.eval_expr(expr.right)
            
            if expr.op == BinOp.ADD:
                return left_val + right_val
            elif expr.op == BinOp.SUB:
                return left_val - right_val
            elif expr.op == BinOp.MUL:
                return left_val * right_val
            elif expr.op == BinOp.DIV:
                if right_val == 0:
                    raise ZeroDivisionError("Division by zero")
                return left_val // right_val  # Integer division
        
        raise RuntimeError(f"Unknown expression type: {type(expr)}")
    
    def eval_condition(self, cond: Comparison) -> bool:
        """Evaluate a comparison condition"""
        left_val = self.eval_expr(cond.left)
        right_val = self.eval_expr(cond.right)
        
        if cond.op == CompOp.EQ:
            return left_val == right_val
        elif cond.op == CompOp.NE:
            return left_val != right_val
        elif cond.op == CompOp.LT:
            return left_val < right_val
        elif cond.op == CompOp.GT:
            return left_val > right_val
        elif cond.op == CompOp.LE:
            return left_val <= right_val
        elif cond.op == CompOp.GE:
            return left_val >= right_val
        
        raise RuntimeError(f"Unknown comparison operator: {cond.op}")