"""
Hybrid Fuzzer - Combines Random Fuzzing and Symbolic Execution

This fuzzer uses:
1. Random mutation (AFL-style) for fast exploration
2. Symbolic execution (KLEE-style) for targeted path exploration
3. Coverage-guided feedback to prioritize interesting inputs
"""

import time
import random
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from toylang_ast import Program
from toylang_parser import parse_program
from interpreter import Interpreter
from symbolic_executor import SymbolicExecutor
from random_fuzzer import MutationFuzzer, FuzzInput, FuzzQueue


@dataclass
class FuzzStats:
    """Statistics about fuzzing campaign"""
    total_executions: int = 0
    assertion_failures: int = 0
    runtime_errors: int = 0
    unique_crashes: Set[str] = field(default_factory=set)
    coverage_branches: int = 0
    coverage_statements: int = 0
    time_elapsed: float = 0.0
    symbolic_inputs: int = 0
    mutated_inputs: int = 0
    
    # unique_crashes uses default_factory so no post-init needed
    def __post_init__(self):
        return
    
    def __repr__(self):
        return (f"FuzzStats(execs={self.total_executions}, "
                f"assertions={self.assertion_failures}, "
                f"errors={self.runtime_errors}, "
                f"crashes={len(self.unique_crashes)}, "
                f"coverage={self.coverage_branches} branches)")


class HybridFuzzer:
    """
    Hybrid fuzzer combining mutation-based and symbolic execution
    """
    
    def __init__(
        self,
        mutation_ratio: float = 0.8,  # 80% mutations, 20% symbolic
        seed: Optional[int] = None
    ):
        self.mutation_ratio = mutation_ratio
        self.mutation_fuzzer = MutationFuzzer(seed=seed)
        self.symbolic_executor = SymbolicExecutor()
        self.interpreter = Interpreter()
        self.fuzz_queue = FuzzQueue()
    
    def fuzz(
        self,
        program: Program,
        input_vars: List[str],
        iterations: int = 1000,
        verbose: bool = False
    ) -> FuzzStats:
        """
        Main fuzzing loop
        
        Args:
            program: ToyLang program to fuzz
            input_vars: List of input variable names
            iterations: Number of fuzzing iterations
            verbose: Print progress information
        
        Returns:
            FuzzStats object with results
        """
        stats = FuzzStats()
        start_time = time.time()
        
        # Generate initial seed inputs with more variety
        initial_inputs = self.mutation_fuzzer.generate_initial_inputs(input_vars, count=20)
        
        # Execute and queue initial inputs
        for inp in initial_inputs:
            self._execute_and_track(program, inp, stats)
        
        if verbose:
            print(f"Initial coverage: {len(self.fuzz_queue.get_total_coverage())} branches")
            print(f"Current coverage set: {self.fuzz_queue.get_total_coverage()}")
        
        # Main fuzzing loop
        for iteration in range(iterations):
            # Use symbolic execution more strategically
            use_symbolic = (
                (iteration % 20 == 0) and  # Every 20 iterations
                (self.mutation_ratio < 1.0) and  # Only if hybrid mode
                (stats.coverage_branches < 10)  # Only if we haven't reached high coverage
            )
            
            if use_symbolic:
                if verbose:
                    print(f"\n  Attempting symbolic execution at iteration {iteration}")
                
                # Symbolic execution for new coverage
                result = self.symbolic_executor.find_new_coverage(
                    program, 
                    input_vars, 
                    self.fuzz_queue.get_total_coverage()
                )
                
                if result is not None:
                    input_dict, new_coverage = result
                    # Filter input_dict to only contain the actual input variables
                    filtered_input = {var: input_dict[var] for var in input_vars if var in input_dict}
                    if filtered_input:  # Only use if we have valid inputs
                        symbolic_input = FuzzInput(filtered_input)
                        self._execute_and_track(program, symbolic_input, stats)
                        stats.symbolic_inputs += 1
                        
                        if verbose:
                            actual_coverage = self.fuzz_queue.get_total_coverage()
                            new_branches = new_coverage - actual_coverage
                            print(f"  Symbolic execution result:")
                            print(f"    Input: {filtered_input}")
                            print(f"    Expected coverage: {len(new_coverage)} branches")
                            print(f"    Actual new branches: {len(new_branches)}")
            
            # Always try mutation
            if self.fuzz_queue.size() > 0:
                base_input = self.fuzz_queue.get_random()
                assert base_input is not None
                
                # Use more aggressive mutation for diversity
                if random.random() < 0.3:  # 30% chance for havoc
                    mutated = self.mutation_fuzzer.havoc(base_input, input_vars, rounds=3)
                else:
                    mutated = self.mutation_fuzzer.mutate(base_input, input_vars)
                    
                self._execute_and_track(program, mutated, stats)
                stats.mutated_inputs += 1
            else:
                # If queue is empty, generate a random input
                random_input = self.mutation_fuzzer.generate_initial_inputs(input_vars, count=1)[0]
                self._execute_and_track(program, random_input, stats)
                stats.mutated_inputs += 1
            
            # Print progress
            if verbose and (iteration + 1) % 100 == 0:
                elapsed = time.time() - start_time
                print(f"[{iteration + 1}/{iterations}] "
                      f"Execs: {stats.total_executions}, "
                      f"Coverage: {stats.coverage_branches} branches, "
                      f"Crashes: {len(stats.unique_crashes)}, "
                      f"Symbolic: {stats.symbolic_inputs}, "
                      f"Time: {elapsed:.2f}s")
        
        stats.time_elapsed = time.time() - start_time
        return stats
    
    def _execute_and_track(self, program: Program, inp: FuzzInput, stats: FuzzStats):
        """Execute input and update statistics"""
        # Set input variables in interpreter
        self.interpreter.reset()
        self.interpreter.variables = inp.values.copy()
        
        # Execute program
        result = self.interpreter.execute(program)
        stats.total_executions += 1
        
        # Track results
        if result['status'] == 'assertion_failed':
            stats.assertion_failures += 1
            crash_sig = f"assert:{result.get('error', 'unknown')}"
            stats.unique_crashes.add(crash_sig)
        elif result['status'] == 'runtime_error':
            stats.runtime_errors += 1
            crash_sig = f"runtime:{result.get('error', 'unknown')}"
            stats.unique_crashes.add(crash_sig)
        
        # Update coverage
        coverage_info = result['coverage']
        stats.coverage_branches = max(stats.coverage_branches, coverage_info['branches'])
        stats.coverage_statements = max(stats.coverage_statements, coverage_info['statements'])
        
        # Add to queue if new coverage
        self.fuzz_queue.add(inp, coverage_info['branch_set'])


def compare_fuzzers(
    program_code: str,
    input_vars: List[str],
    iterations: int = 1000,
    trials: int = 3
) -> Dict[str, Any]:
    """
    Compare hybrid fuzzer vs pure random fuzzing
    
    Returns dictionary with comparison results
    """
    program = parse_program(program_code)
    
    results = {
        'hybrid': [],
        'random_only': []
    }
    
    for trial in range(trials):
        print(f"\n=== Trial {trial + 1}/{trials} ===")
        
        # Test hybrid fuzzer
        print("\nRunning hybrid fuzzer...")
        hybrid = HybridFuzzer(mutation_ratio=0.7, seed=trial)
        hybrid_stats = hybrid.fuzz(program, input_vars, iterations, verbose=True)
        results['hybrid'].append(hybrid_stats)
        
        # Test random-only fuzzer (100% mutation, no symbolic)
        print("\nRunning random-only fuzzer...")
        random_only = HybridFuzzer(mutation_ratio=1.0, seed=trial)
        random_stats = random_only.fuzz(program, input_vars, iterations, verbose=True)
        results['random_only'].append(random_stats)
    
    return results