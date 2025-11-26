
"""
Mutation-Based Fuzzer (AFL-style)

Implements various mutation strategies to generate test inputs:
- Bit flips
- Byte flips
- Arithmetic mutations
- Random insertions/deletions
- Dictionary-based mutations
"""

import random
import copy
from typing import Dict, List, Set, Optional
from dataclasses import dataclass


@dataclass
class FuzzInput:
    """Represents a fuzz test input"""
    values: Dict[str, int]
    
    def copy(self):
        return FuzzInput(self.values.copy())
    
    def __repr__(self):
        return f"Input({self.values})"


class MutationFuzzer:
    """AFL-style mutation-based fuzzer"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        # Interesting values that often trigger edge cases
        self.interesting_values = [
            -1, 0, 1,
            -128, 127,  # 8-bit boundaries
            -32768, 32767,  # 16-bit boundaries
            -2147483648, 2147483647,  # 32-bit boundaries
            100, 1000, 10000,
        ]
    
    def generate_initial_inputs(
        self, 
        input_vars: List[str], 
        count: int = 10
    ) -> List[FuzzInput]:
        """Generate initial seed inputs"""
        inputs = []
        
        # Start with some structured initial values
        for _ in range(count):
            values = {}
            for var in input_vars:
                values[var] = random.choice([
                    random.randint(-100, 100),
                    random.choice(self.interesting_values)
                ])
            inputs.append(FuzzInput(values))
        
        return inputs
    
    def mutate(self, input: FuzzInput, input_vars: List[str]) -> FuzzInput:
        """
        Apply random mutation to input
        Returns a new mutated input
        """
        mutated = input.copy()
        
        # Choose random mutation strategy
        strategy = random.choice([
            self._mutate_bit_flip,
            self._mutate_arithmetic,
            self._mutate_interesting,
            self._mutate_random_value,
            self._mutate_swap,
        ])
        
        strategy(mutated, input_vars)
        return mutated
    
    def _mutate_bit_flip(self, input: FuzzInput, input_vars: List[str]):
        """Flip random bits in a value"""
        if not input.values:
            return
        
        var = random.choice(list(input.values.keys()))
        value = input.values[var]
        
        # Flip 1-4 random bits
        num_flips = random.randint(1, 4)
        for _ in range(num_flips):
            bit_pos = random.randint(0, 31)  # Assuming 32-bit integers
            value ^= (1 << bit_pos)
        
        input.values[var] = value
    
    def _mutate_arithmetic(self, input: FuzzInput, input_vars: List[str]):
        """Apply arithmetic mutation (add/subtract small values)"""
        if not input.values:
            return
        
        var = random.choice(list(input.values.keys()))
        delta = random.choice([-1, 1, -10, 10, -100, 100])
        input.values[var] += delta
    
    def _mutate_interesting(self, input: FuzzInput, input_vars: List[str]):
        """Replace with an interesting value"""
        if not input.values:
            return
        
        var = random.choice(list(input.values.keys()))
        input.values[var] = random.choice(self.interesting_values)
    
    def _mutate_random_value(self, input: FuzzInput, input_vars: List[str]):
        """Set completely random value"""
        if not input.values:
            return
        
        var = random.choice(list(input.values.keys()))
        input.values[var] = random.randint(-10000, 10000)
    
    def _mutate_swap(self, input: FuzzInput, input_vars: List[str]):
        """Swap values between two variables"""
        if len(input.values) < 2:
            return
        
        vars = random.sample(list(input.values.keys()), 2)
        input.values[vars[0]], input.values[vars[1]] = \
            input.values[vars[1]], input.values[vars[0]]
    
    def havoc(self, input: FuzzInput, input_vars: List[str], rounds: int = 5) -> FuzzInput:
        """
        Apply multiple random mutations (havoc mode)
        This is more aggressive than single mutations
        """
        result = input.copy()
        for _ in range(rounds):
            result = self.mutate(result, input_vars)
        return result


class FuzzQueue:
    """Queue of inputs for fuzzing with coverage tracking"""
    
    def __init__(self):
        self.queue: List[FuzzInput] = []
        self.coverage_map: Dict[int, Set[str]] = {}  # input_id -> branches covered
        self.total_coverage: Set[str] = set()
    
    def add(self, input: FuzzInput, coverage: Set[str]):
        """Add input to queue if it provides new coverage"""
        new_coverage = coverage - self.total_coverage
        
        if new_coverage or len(self.queue) < 10:  # Always keep first 10
            input_id = len(self.queue)
            self.queue.append(input)
            self.coverage_map[input_id] = coverage
            self.total_coverage.update(coverage)
            return True
        
        return False
    
    def get_random(self) -> Optional[FuzzInput]:
        """Get random input from queue for mutation"""
        if not self.queue:
            return None
        return random.choice(self.queue).copy()
    
    def get_total_coverage(self) -> Set[str]:
        """Get total coverage achieved so far"""
        return self.total_coverage.copy()
    
    def size(self) -> int:
        return len(self.queue)