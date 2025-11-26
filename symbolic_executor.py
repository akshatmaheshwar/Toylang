"""
Symbolic Executor for ToyLang using Z3

This module performs symbolic execution to explore program paths
and generate inputs that satisfy specific path conditions.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
try:
    import z3  # type: ignore[import]  # pylint: disable=import-error
except Exception as e:
    raise ImportError("The 'z3-solver' package is required; install it with 'pip install z3-solver'") from e
from toylang_ast import *

@dataclass
class PathConstraint:
    """Represents a constraint along an execution path"""
    condition: Comparison
    taken: bool  # True if then-branch, False if else-branch
    
    def __repr__(self):
        branch = "then" if self.taken else "else"
        return f"PathConstraint({self.condition}, {branch})"


@dataclass
class SymbolicPath:
    """Represents a symbolic execution path"""
    constraints: List[PathConstraint]
    coverage: Set[str]
    assignments: Dict[str, Expr]  # Track variable assignments along this path
    
    def __repr__(self):
        return f"Path({len(self.constraints)} constraints, {len(self.coverage)} branches)"


class SymbolicExecutor:
    """Symbolic execution engine for ToyLang"""
    
    def __init__(self, max_depth: int = 50):
        self.max_depth = max_depth
        self.explored_paths: List[SymbolicPath] = []
        self.used_path_signatures: Set[str] = set()  # Track paths already used for input generation
    
    def explore_paths(self, program: Program, input_vars: Optional[List[str]] = None) -> List[SymbolicPath]:
        """
        Explore all possible execution paths in the program
        Returns list of symbolic paths with their constraints
        
        Args:
            program: Program to explore
            input_vars: List of input variable names (treat as symbolic)
        """
        self.explored_paths = []
        self.input_vars = set(input_vars or [])
        
        # Reset for fresh exploration
        self._explore_recursive(program.statements, [], set(), 0, {})
        
        # Remove duplicate paths and sort by coverage size
        unique_paths = []
        seen_constraints = set()
        
        for path in self.explored_paths:
            # Create a unique signature for the path constraints
            constraint_sig = tuple((str(pc.condition), pc.taken) for pc in path.constraints)
            
            if constraint_sig not in seen_constraints:
                seen_constraints.add(constraint_sig)
                unique_paths.append(path)
        
        # Sort by number of constraints (more specific paths first)
        unique_paths.sort(key=lambda p: len(p.constraints), reverse=True)
        
        # Debug: print found paths
        print(f"  Found {len(unique_paths)} unique paths with coverage:")
        for i, path in enumerate(unique_paths):
            print(f"    Path {i}: {len(path.coverage)} branches - {path.coverage}")
        
        return unique_paths
    
    def _explore_recursive(
        self, 
        statements: List[Statement], 
        constraints: List[PathConstraint],
        coverage: Set[str],
        depth: int,
        assignments: Optional[Dict[str, Expr]] = None
    ):
        """Recursively explore execution paths"""
        if assignments is None:
            assignments = {}
        
        if depth > self.max_depth:
            # Record path even if we hit depth limit
            if constraints:
                self.explored_paths.append(SymbolicPath(constraints, coverage, assignments.copy()))
            return
        
        if not statements:
            # End of statements - record this path
            # Always record paths, even with no constraints (for straight-line code)
            self.explored_paths.append(SymbolicPath(constraints, coverage, assignments.copy()))
            return
        
        stmt = statements[0]
        remaining = statements[1:]
        
        if isinstance(stmt, IfStatement):
            # Use hash of condition string for consistent branch IDs
            branch_id = f"if_{hash(str(stmt.condition))}"
            
            # Explore then-branch
            then_constraints = constraints + [PathConstraint(stmt.condition, True)]
            then_coverage = coverage | {f"{branch_id}_then"}
            self._explore_recursive(stmt.then_block + remaining, then_constraints, then_coverage, depth + 1, assignments)
            
            # Explore else-branch  
            else_constraints = constraints + [PathConstraint(stmt.condition, False)]
            else_coverage = coverage | {f"{branch_id}_else"}
            self._explore_recursive(stmt.else_block + remaining, else_constraints, else_coverage, depth + 1, assignments)
        
        elif isinstance(stmt, Assignment):
            # Track this assignment
            new_assignments = assignments.copy()
            new_assignments[stmt.var_name] = stmt.expr
            # Continue with remaining statements
            self._explore_recursive(remaining, constraints, coverage, depth + 1, new_assignments)
        
        elif isinstance(stmt, AssertStatement):
            # Continue with remaining statements
            self._explore_recursive(remaining, constraints, coverage, depth + 1, assignments)
    
    def generate_input(self, path: SymbolicPath, input_vars: List[str]) -> Optional[Dict[str, int]]:
        """
        Generate concrete input values that satisfy the path constraints
        using Z3 SMT solver
        """
        solver = z3.Solver()
        
        # Create symbolic variables - only for the specified input variables
        z3_vars = {var: z3.Int(var) for var in input_vars}
        
        # Track assignments to build proper substitutions
        self._assignments = path.assignments

        # Reset per-call non-zero/divisor constraints collector
        self._nonzero_constraints = []

        # Add path constraints to solver
        for path_constraint in path.constraints:
            z3_cond = self._condition_to_z3(path_constraint.condition, z3_vars)

            if path_constraint.taken:
                solver.add(z3_cond)
            else:
                solver.add(z3.Not(z3_cond))

        # Add any non-zero/divisor constraints collected while building expressions
        for c in getattr(self, '_nonzero_constraints', []):
            solver.add(c)
        
        # Check if constraints are satisfiable
        if solver.check() == z3.sat:
            model = solver.model()
            
            # Extract concrete values (robust to different Z3 Ref types)
            result: Dict[str, int] = {}
            for var_name, z3_var in z3_vars.items():
                val = model.eval(z3_var, model_completion=True)
                # Prefer numeric extraction via as_long when available
                try:
                    result[var_name] = int(val.as_long())  # type: ignore[attr-defined]
                except Exception:
                    # Fallback: try boolean or string conversion
                    try:
                        if z3.is_true(val):
                            result[var_name] = 1
                        elif z3.is_false(val):
                            result[var_name] = 0
                        else:
                            result[var_name] = int(str(val))
                    except Exception:
                        result[var_name] = 0
            
            return result
        
        return None
    
    def _expr_to_z3(self, expr: Expr, z3_vars: Dict[str, Any]) -> Any:
        """Convert ToyLang expression to Z3 expression"""
        if isinstance(expr, Number):
            return z3.IntVal(expr.value)
        
        elif isinstance(expr, Variable):
            if expr.name in z3_vars:
                return z3_vars[expr.name]
            else:
                # Check if this variable has an assignment we should substitute
                assignments = getattr(self, '_assignments', {})
                if expr.name in assignments:
                    # Recursively convert the assigned expression
                    return self._expr_to_z3(assignments[expr.name], z3_vars)
                else:
                    # Unknown variable - create a new Z3 variable for it
                    z3_vars[expr.name] = z3.Int(expr.name)
                    return z3_vars[expr.name]
        
        elif isinstance(expr, BinaryOp):
            left_z3 = self._expr_to_z3(expr.left, z3_vars)
            right_z3 = self._expr_to_z3(expr.right, z3_vars)
            
            if expr.op == BinOp.ADD:
                return left_z3 + right_z3
            elif expr.op == BinOp.SUB:
                return left_z3 - right_z3
            elif expr.op == BinOp.MUL:
                return left_z3 * right_z3
            elif expr.op == BinOp.DIV:
                # Add constraint that divisor is non-zero so solver avoids division-by-zero models
                try:
                    # record a constraint to be added by caller
                    self._nonzero_constraints.append(right_z3 != 0)
                except Exception:
                    # defensive: if _nonzero_constraints not present, create it
                    self._nonzero_constraints = [right_z3 != 0]
                # Use Python-backed Z3 division (handles Int/Real appropriately)
                return left_z3 / right_z3
        
        raise ValueError(f"Unknown expression type: {type(expr)}")
    
    def _condition_to_z3(self, cond: Comparison, z3_vars: Dict[str, Any]) -> Any:
        """Convert ToyLang comparison to Z3 boolean expression"""
        left_z3 = self._expr_to_z3(cond.left, z3_vars)
        right_z3 = self._expr_to_z3(cond.right, z3_vars)
        
        if cond.op == CompOp.EQ:
            return left_z3 == right_z3
        elif cond.op == CompOp.NE:
            return left_z3 != right_z3
        elif cond.op == CompOp.LT:
            return left_z3 < right_z3
        elif cond.op == CompOp.GT:
            return left_z3 > right_z3
        elif cond.op == CompOp.LE:
            return left_z3 <= right_z3
        elif cond.op == CompOp.GE:
            return left_z3 >= right_z3
        
        raise ValueError(f"Unknown comparison operator: {cond.op}")
    
    def find_new_coverage(
        self, 
        program: Program, 
        input_vars: List[str],
        current_coverage: Set[str]
    ) -> Optional[Tuple[Dict[str, int], Set[str]]]:
        """
        Find an input that achieves new coverage
        Returns: (input_dict, new_branches) or None
        """
        paths = self.explore_paths(program, input_vars)
        
        for i, path in enumerate(paths):
            # Check if this path has any new coverage
            new_branches = path.coverage - current_coverage
            
            if new_branches:
                # Create a signature for this path to avoid reusing it
                path_sig = f"{path.constraints}_{path.coverage}"
                
                # Skip if we've already used this path
                if path_sig in self.used_path_signatures:
                    continue
                
                print(f"  Path {i}: has {len(new_branches)} new branches: {new_branches}")
                
                # Try to generate input for this path
                input_dict = self.generate_input(path, input_vars)
                
                if input_dict is not None:
                    # Filter to only include the specified input variables
                    filtered_input = {var: input_dict[var] for var in input_vars if var in input_dict}
                    
                    if filtered_input:
                        print(f"  Generated input: {filtered_input}")
                        # Mark this path as used
                        self.used_path_signatures.add(path_sig)
                        return (filtered_input, path.coverage)
                    else:
                        print(f"  Could not generate valid input for path {i}")
                else:
                    print(f"  Could not solve constraints for path {i}")
        
        print("  No paths with new coverage found")
        return None