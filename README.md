# ToyLang

A custom programming language built from scratch in Python, complete with a parser, AST, interpreter, and a **hybrid fuzzer** that combines coverage-guided random fuzzing with symbolic execution to automatically discover bugs.

## What This Is

ToyLang is a small but complete language implementation that demonstrates core compiler and program analysis concepts:

- **Lexer & Parser** — tokenises source code and builds an Abstract Syntax Tree (AST)
- **Interpreter** — executes ToyLang programs with branch and statement coverage tracking
- **Symbolic Executor** — uses Z3 (SMT solver) to reason about all possible execution paths
- **Random Fuzzer** — AFL-style mutation fuzzer that generates and mutates inputs
- **Hybrid Fuzzer** — combines both approaches: random mutation for fast exploration, symbolic execution for targeted path coverage

## Language Features

ToyLang supports:
- Integer variables and arithmetic (`+`, `-`, `*`, `/`)
- Comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`)
- `if / else` blocks with nested branching
- `assert` statements (used as bug oracles)

Example ToyLang program:
```
x = 10
y = 20
z = x + y
if (z > 25) {
    result = z * 2
    assert(result != 60)
}
```

## Architecture

```
toylang_ast.py        # AST node definitions (Program, Assignment, IfStatement, etc.)
toylang_parser.py     # Lexer + recursive descent parser → AST
interpreter.py        # Tree-walking interpreter with coverage instrumentation
symbolic_executor.py  # Symbolic execution engine using Z3 SMT solver
random_fuzzer.py      # Coverage-guided mutation fuzzer (AFL-style)
hybrid_fuzzer.py      # Combines random + symbolic fuzzing (KLEE-style)
programs.py           # Example programs with embedded bugs
demo.py               # Demo of individual components
demo_end_to_end.py    # End-to-end fuzzing demo
```

## How the Hybrid Fuzzer Works

1. **Random phase** — mutates integer inputs quickly to explore shallow paths and build a coverage corpus
2. **Symbolic phase** — when random fuzzing gets stuck, the symbolic executor takes over, solving path constraints with Z3 to generate inputs that reach previously uncovered branches
3. **Feedback loop** — any input that increases coverage gets added to the queue, prioritising interesting paths

This mirrors the approach used by real-world fuzzers like AFL and KLEE.

## Setup

```bash
pip install z3-solver
```

## Usage

```bash
# Run the end-to-end demo
python demo_end_to_end.py

# Run individual component demo
python demo.py
```

## Example Bugs Found

The `programs.py` file contains programs with intentional bugs the fuzzer is designed to find, including:

- Division by zero (`z = x / (x - 100)` when `x = 100`)
- Assertion violations in hard-to-reach branches (`if (secret == 12345)`)
- Arithmetic edge cases requiring symbolic reasoning to trigger

## Concepts Demonstrated

- Recursive descent parsing
- Abstract Syntax Tree design
- Tree-walking interpretation
- Branch coverage instrumentation
- SMT solving with Z3
- Concolic / hybrid fuzzing
- Path constraint collection and solving
