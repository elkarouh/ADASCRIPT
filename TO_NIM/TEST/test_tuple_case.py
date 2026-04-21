# Test file for tuple pattern case/when desugaring
# Syntax: case (a, b): when (val, _): ...
# Desugars to if/elif chains in Nim (Nim does not support tuple case selectors)
# Run with: python3 TO_NIM/py2nim.py TO_NIM/TEST/test_tuple_case.py

# ============================================================================
# Test 1: Basic tuple pattern — two-element tuple
# ============================================================================
print("--- Test 1: Two-element tuple pattern ---")

def classify_pair(x: int, y: int) -> int:
    case (x, y):
        when (0, 0):
            return 0
        when (0, _):
            return 1
        when (_, 0):
            return 2
        when others:
            return 3

assert classify_pair(0, 0) == 0
assert classify_pair(0, 5) == 1
assert classify_pair(3, 0) == 2
assert classify_pair(3, 4) == 3
print("  Two-element tuple pattern: OK")

# ============================================================================
# Test 2: Both elements constrained
# ============================================================================
print("--- Test 2: Both elements constrained ---")

def both_constrained(a: int, b: int) -> int:
    case (a, b):
        when (1, 2):
            return 12
        when (3, 4):
            return 34
        when (_, _):
            return -1

assert both_constrained(1, 2) == 12
assert both_constrained(3, 4) == 34
assert both_constrained(0, 0) == -1
print("  Both elements constrained: OK")

# ============================================================================
# Test 3: Four-branch pattern matching specific combinations
# ============================================================================
print("--- Test 3: Four-branch specificity ---")

def specificity(a: int, b: int) -> int:
    case (a, b):
        when (1, 1):
            return 11
        when (1, _):
            return 10
        when (_, 1):
            return 1
        when others:
            return 0

assert specificity(1, 1) == 11
assert specificity(1, 5) == 10
assert specificity(7, 1) == 1
assert specificity(7, 5) == 0
print("  Four-branch specificity: OK")

# ============================================================================
# Test 4: Tuple case inside a method (simulates shortest_path example6 pattern)
# ============================================================================
print("--- Test 4: Range subtypes in tuple patterns ---")

type Year_T is 0..10
type Age_T  is 0..5

def boundary_decision(year: Year_T, age: Age_T) -> int:
    case (year, age):
        when (0, _):
            return 0
        when (10, _):
            return 10
        when (_, 5):
            return 5
        when others:
            return -1

assert boundary_decision(Year_T(0), Age_T(2)) == 0
assert boundary_decision(Year_T(10), Age_T(1)) == 10
assert boundary_decision(Year_T(5), Age_T(5)) == 5
assert boundary_decision(Year_T(3), Age_T(2)) == -1
print("  Range subtypes in tuple patterns: OK")

print("All tuple case/when tests passed.")
