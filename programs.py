"""
Example ToyLang Programs for Fuzzing

These programs contain various types of bugs:
1. Assertion failures
2. Division by zero
3. Complex conditions requiring symbolic execution
"""

EXAMPLES = {
    "simple_assert": """
x = 10
y = 20
z = x + y
assert(z == 30)
""",
    
    "buggy_division": """
x = 100
y = x - 100
z = x / y
assert(z > 0)
""",
    
    "complex_condition": """
a = 5
b = 10
c = a + b
if (c == 15) {
    d = c * 2
    if (d == 30) {
        e = d - 10
        assert(e != 20)
    }
}
""",
    
    "nested_branches": """
x = 0
if (x > 5) {
    y = x * 2
    if (y > 15) {
        assert(y < 10)
    }
} else {
    y = x + 10
    if (y == 10) {
        z = 100 / y
        assert(z == 10)
    }
}
""",
    
    "arithmetic_bug": """
a = 10
b = 20
c = a - b
if (c < 0) {
    d = c * c
    if (d == 100) {
        e = d / (c + 10)
        assert(e > 50)
    }
}
""",
    
    "multiple_paths": """
x = 0
y = 0
if (x == 42) {
    if (y == 13) {
        z = x + y
        assert(z != 55)
    }
} else {
    if (x == 100) {
        if (y == 200) {
            assert(x + y != 300)
        }
    }
}
""",
    
    "overflow_test": """
x = 1000
y = 2000
z = x + y
if (z > 2500) {
    a = z * 10
    if (a > 25000) {
        b = a / (z - 3000)
        assert(b > 0)
    }
}
""",
    
    "edge_case_bug": """
value = 0
if (value == 0) {
    result = 100 / value
    assert(result > 0)
} else {
    result = value + 10
    assert(result > value)
}
""",
    
    "symbolic_needed": """
secret1 = 0
secret2 = 0
if (secret1 == 12345) {
    if (secret2 == 67890) {
        combined = secret1 + secret2
        if (combined == 80235) {
            flag = combined / (secret1 - 12345)
            assert(flag > 0)
        }
    }
}
""",
    
    "complex_arithmetic": """
a = 10
b = 5
c = a * b
d = c - 30
if (d == 20) {
    e = d / (a - 10)
    assert(e < 100)
} else {
    e = d + 50
    if (e == 70) {
        f = e / (b - 5)
        assert(f > 0)
    }
}
""",
    
    "hard_to_reach": """
x = 0
y = 0
if (x == 42) {
    if (y == 100) {
        z = x + y
        assert(z == 142)
    } else {
        w = x - y
        assert(w == -58)
    }
} else {
    if (x == 100) {
        if (y == 200) {
            result = x * y
            assert(result == 20000)
        }
    }
}
""",
    
    "easy_symbolic": """
x = 0
if (x == 42) {
    result = 100
    assert(result == 100)
} else {
    result = 200
    assert(result == 200)
}
""",
    
    "nested_symbolic": """
a = 0
b = 0
if (a == 10) {
    if (b == 20) {
        c = a + b
        assert(c == 30)
    } else {
        c = a - b  
        assert(c == -10)
    }
} else {
    if (a == 30) {
        if (b == 40) {
            c = a * b
            assert(c == 1200)
        }
    }
}
"""
}


def get_example(name: str) -> str:
    """Get example program by name"""
    if name not in EXAMPLES:
        available = ", ".join(EXAMPLES.keys())
        raise ValueError(f"Unknown example '{name}'. Available: {available}")
    return EXAMPLES[name]


def list_examples():
    """List all available examples"""
    print("Available example programs:")
    for i, name in enumerate(EXAMPLES.keys(), 1):
        print(f"{i}. {name}")