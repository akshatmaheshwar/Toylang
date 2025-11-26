#!/usr/bin/env python3
"""
Hybrid Fuzzer Demo and Evaluation

This script demonstrates the effectiveness of hybrid fuzzing
by comparing it against pure random fuzzing.
"""

import sys
import os
import json
# Defer importing matplotlib until it's actually needed to avoid import errors
plt = None
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples'))

from toylang_parser import parse_program
from hybrid_fuzzer import HybridFuzzer, compare_fuzzers
from programs import EXAMPLES, list_examples


def demo_single_program(program_name: str, program_code: str, input_vars: list):
    """Demo fuzzing on a single program"""
    print(f"\n{'='*60}")
    print(f"Fuzzing Program: {program_name}")
    print(f"{'='*60}")
    print("\nProgram code:")
    print(program_code)
    print(f"\nInput variables: {input_vars}")
    
    # Parse program
    try:
        program = parse_program(program_code)
        print(f"✓ Program parsed successfully")
    except Exception as e:
        print(f"✗ Parse error: {e}")
        return None, None
    
    # Run hybrid fuzzer
    print("\n--- Running Hybrid Fuzzer ---")
    hybrid = HybridFuzzer(mutation_ratio=0.7, seed=42)
    hybrid_stats = hybrid.fuzz(program, input_vars, iterations=500, verbose=True)
    
    print("\n--- Hybrid Fuzzer Results ---")
    print(f"Total executions: {hybrid_stats.total_executions}")
    print(f"Assertion failures: {hybrid_stats.assertion_failures}")
    print(f"Runtime errors: {hybrid_stats.runtime_errors}")
    print(f"Unique crashes: {len(hybrid_stats.unique_crashes)}")
    print(f"Coverage (branches): {hybrid_stats.coverage_branches}")
    print(f"Coverage (statements): {hybrid_stats.coverage_statements}")
    print(f"Symbolic inputs used: {hybrid_stats.symbolic_inputs}")
    print(f"Mutated inputs used: {hybrid_stats.mutated_inputs}")
    print(f"Time elapsed: {hybrid_stats.time_elapsed:.2f}s")
    
    if hybrid_stats.unique_crashes:
        print(f"\nCrash signatures found:")
        for crash in hybrid_stats.unique_crashes:
            print(f"  - {crash}")
    
    # Run random-only fuzzer for comparison
    print("\n--- Running Random-Only Fuzzer ---")
    random_fuzzer = HybridFuzzer(mutation_ratio=1.0, seed=42)
    random_stats = random_fuzzer.fuzz(program, input_vars, iterations=500, verbose=True)
    
    print("\n--- Random-Only Fuzzer Results ---")
    print(f"Total executions: {random_stats.total_executions}")
    print(f"Assertion failures: {random_stats.assertion_failures}")
    print(f"Runtime errors: {random_stats.runtime_errors}")
    print(f"Unique crashes: {len(random_stats.unique_crashes)}")
    print(f"Coverage (branches): {random_stats.coverage_branches}")
    print(f"Coverage (statements): {random_stats.coverage_statements}")
    print(f"Time elapsed: {random_stats.time_elapsed:.2f}s")
    
    # Comparison
    print("\n--- Comparison ---")
    print(f"Coverage improvement: {hybrid_stats.coverage_branches - random_stats.coverage_branches} branches")
    print(f"Crash detection improvement: {len(hybrid_stats.unique_crashes) - len(random_stats.unique_crashes)} crashes")
    
    return hybrid_stats, random_stats


def run_comprehensive_evaluation():
    """Run evaluation on multiple programs"""
    print("\n" + "="*60)
    print("COMPREHENSIVE EVALUATION")
    print("="*60)
    
    # Use programs where symbolic execution should have clear advantage
    test_cases = [
        ("easy_symbolic", ["x"]),
        ("buggy_division", ["x"]),
        ("nested_symbolic", ["a", "b"]),
        ("symbolic_needed", ["secret1", "secret2"]),
        ("multiple_paths", ["x", "y"]),
    ]
    
    results = {}
    
    for program_name, input_vars in test_cases:
        if program_name in EXAMPLES:
            program_code = EXAMPLES[program_name]
            print(f"\n{'='*60}")
            print(f"Testing: {program_name}")
            print(f"{'='*60}")
            
            hybrid_stats, random_stats = demo_single_program(
                program_name, 
                program_code, 
                input_vars
            )
            
            if hybrid_stats and random_stats:
                results[program_name] = {
                    'hybrid': hybrid_stats,
                    'random': random_stats
                }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print(f"\n{'Program':<20} {'Hybrid Cov':<12} {'Random Cov':<12} {'Improvement':<12}")
    print("-" * 60)
    
    for program_name, stats in results.items():
        hybrid_cov = stats['hybrid'].coverage_branches
        random_cov = stats['random'].coverage_branches
        improvement = hybrid_cov - random_cov
        improvement_str = f"+{improvement}" if improvement > 0 else str(improvement)
        print(f"{program_name:<20} {hybrid_cov:<12} {random_cov:<12} {improvement_str:<12}")
    
    return results

def create_visualizations(results):
    """Create comparison visualizations"""
    # Import matplotlib lazily to avoid import errors at module import time
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("\nNote: matplotlib is not installed; skipping visualization.")
        print("Install matplotlib with: pip install matplotlib")
        return

    programs = list(results.keys())
    hybrid_coverage = [results[p]['hybrid'].coverage_branches for p in programs]
    random_coverage = [results[p]['random'].coverage_branches for p in programs]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Coverage comparison
    x = range(len(programs))
    width = 0.35
    
    ax1.bar([i - width/2 for i in x], hybrid_coverage, width, label='Hybrid', color='#2ecc71')
    ax1.bar([i + width/2 for i in x], random_coverage, width, label='Random', color='#e74c3c')
    ax1.set_xlabel('Program')
    ax1.set_ylabel('Branch Coverage')
    ax1.set_title('Coverage Comparison: Hybrid vs Random Fuzzing')
    ax1.set_xticks(x)
    ax1.set_xticklabels(programs, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Improvement chart
    improvements = [h - r for h, r in zip(hybrid_coverage, random_coverage)]
    colors = ['#2ecc71' if i > 0 else '#e74c3c' for i in improvements]
    
    ax2.bar(x, improvements, color=colors)
    ax2.set_xlabel('Program')
    ax2.set_ylabel('Coverage Improvement (branches)')
    ax2.set_title('Hybrid Fuzzer Coverage Improvement')
    ax2.set_xticks(x)
    ax2.set_xticklabels(programs, rotation=45, ha='right')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_dir = Path(__file__).parent / 'results'
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'fuzzer_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualization saved to {output_dir / 'fuzzer_comparison.png'}")
    
    plt.close()

def main():
    """Main entry point"""
    print("="*60)
    print("HYBRID FUZZER + SYMBOLIC EXECUTOR")
    print("Demonstration of Advanced Program Testing")
    print("="*60)
    
    if len(sys.argv) > 1:
        # Demo specific program
        program_name = sys.argv[1]
        
        if program_name == "list":
            list_examples()
            return
        
        if program_name not in EXAMPLES:
            print(f"Unknown program: {program_name}")
            list_examples()
            return
        
        program_code = EXAMPLES[program_name]
        
        # Determine input variables (simple heuristic)
        if program_name == "buggy_division":
            input_vars = ["x"]
        elif program_name == "symbolic_needed":
            input_vars = ["secret1", "secret2"]
        elif program_name in ["complex_condition", "arithmetic_bug", "nested_branches", "nested_symbolic"]:
            input_vars = ["a", "b"]
        elif program_name == "easy_symbolic":
            input_vars = ["x"]
        else:
            input_vars = ["x", "y"]
        
        demo_single_program(program_name, program_code, input_vars)
    else:
        # Run comprehensive evaluation
        results = run_comprehensive_evaluation()
        
        # Create visualizations
        try:
            create_visualizations(results)
        except Exception as e:
            print(f"\nNote: Could not create visualizations: {e}")
            print("Install matplotlib with: pip install matplotlib")


if __name__ == "__main__":
    main()