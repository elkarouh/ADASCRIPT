"""
School Timetabling — Backtracking CSP
======================================
Same data as the ILP version. The state is a single dict:
    assignment: (class, subject, occurrence) -> (teacher, room, period)
We mutate it in place and undo on backtrack.
"""

from itertools import product

# ---------------------------------------------------------------------------
# Data  (identical to ILP version)
# ---------------------------------------------------------------------------

DAYS    = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOTS   = [1, 2, 3, 4]
PERIODS = [(d, s) for d in DAYS for s in SLOTS]   # 20 periods

CLASSES  = ["9A", "9B", "10A"]
SUBJECTS = ["Math", "English", "Science", "History"]
TEACHERS = ["Alice", "Bob", "Carol", "Dan"]
ROOMS    = ["R1", "R2", "R3"]

requirements = {
    ("9A",  "Math"):    2, ("9A",  "English"): 2,
    ("9A",  "Science"): 2, ("9A",  "History"): 1,
    ("9B",  "Math"):    2, ("9B",  "English"): 2,
    ("9B",  "Science"): 1, ("9B",  "History"): 2,
    ("10A", "Math"):    3, ("10A", "English"): 2,
    ("10A", "Science"): 2, ("10A", "History"): 1,
}

can_teach = {
    ("Alice", "Math"),   ("Alice", "Science"),
    ("Bob",   "English"),("Bob",   "History"),
    ("Carol", "Math"),   ("Carol", "English"),
    ("Dan",   "Science"),("Dan",   "History"),
}

room_capacity = {"R1": 35, "R2": 30, "R3": 25}
class_size    = {"9A": 28, "9B": 25, "10A": 22}

# ---------------------------------------------------------------------------
# Build the list of lesson tokens to assign
# (class, subject, occurrence_index)
# ---------------------------------------------------------------------------

lessons = []
for (c, s), count in sorted(requirements.items()):
    for occ in range(count):
        lessons.append((c, s, occ))

# All candidate values for a lesson token: (teacher, room, period)
def candidates(c, s):
    return [
        (t, r, p)
        for t, r, p in product(TEACHERS, ROOMS, PERIODS)
        if (t, s) in can_teach
        and room_capacity[r] >= class_size[c]
    ]

# Pre-compute candidates per (class, subject) — same for all occurrences
all_candidates = {
    (c, s): candidates(c, s)
    for (c, s) in requirements
}

# ---------------------------------------------------------------------------
# Constraint checking
# ---------------------------------------------------------------------------

def is_consistent(assignment, lesson, value):
    """
    Check whether placing `lesson` at `value` is consistent with everything
    already in `assignment`.

    lesson : (class, subject, occurrence)
    value  : (teacher, room, period)
    """
    c,  s,  _  = lesson
    t,  r,  p  = value

    for (c2, s2, occ2), (t2, r2, p2) in assignment.items():
        # Teacher conflict
        if t == t2 and p == p2:
            return False
        # Class conflict  (same class, same period)
        if c == c2 and p == p2:
            return False
        # Room conflict
        if r == r2 and p == p2:
            return False

    return True

# ---------------------------------------------------------------------------
# Variable ordering heuristic — Most Constrained Variable (MCV)
#
# Among unassigned lessons, pick the one with the fewest remaining
# consistent candidates.  This fails fast and prunes the tree early.
# ---------------------------------------------------------------------------

def pick_lesson(assignment, remaining):
    def count_options(lesson):
        c, s, _ = lesson
        return sum(
            1 for v in all_candidates[(c, s)]
            if is_consistent(assignment, lesson, v)
        )
    return min(remaining, key=count_options)

# ---------------------------------------------------------------------------
# Backtracking search
# ---------------------------------------------------------------------------

def backtrack(assignment, remaining, stats):
    """
    assignment : dict  (class, subject, occ) -> (teacher, room, period)
    remaining  : list of lesson tokens not yet assigned
    stats      : dict tracking calls and backtracks
    """
    stats["calls"] += 1

    if not remaining:
        return True   # all lessons placed — success

    # Choose which lesson to assign next (MCV heuristic)
    lesson = pick_lesson(assignment, remaining)
    remaining.remove(lesson)

    c, s, _ = lesson

    for value in all_candidates[(c, s)]:
        if is_consistent(assignment, lesson, value):
            # Assign
            assignment[lesson] = value

            if backtrack(assignment, remaining, stats):
                return True

            # Undo
            del assignment[lesson]
            stats["backtracks"] += 1

    # No value worked — restore and signal failure
    remaining.append(lesson)
    return False

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

import time

assignment = {}
remaining  = list(lessons)
stats      = {"calls": 0, "backtracks": 0}

print("Solving via backtracking CSP …\n")
t0 = time.perf_counter()
solved = backtrack(assignment, remaining, stats)
elapsed = time.perf_counter() - t0

print(f"{'Solved' if solved else 'No solution found'} in {elapsed:.3f}s")
print(f"Recursive calls : {stats['calls']}")
print(f"Backtracks      : {stats['backtracks']}")

if not solved:
    raise SystemExit

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_timetable():
    for c in CLASSES:
        print(f"\n{'='*54}")
        print(f"  Timetable for class {c}")
        print(f"{'='*54}")
        print(f"{'':8}" + "".join(f"{d:>10}" for d in DAYS))
        for sl in SLOTS:
            row = f"Slot {sl}  "
            for d in DAYS:
                entry = "—"
                for (kc, ks, _), (kt, kr, (kd, ksl)) in assignment.items():
                    if kc == c and kd == d and ksl == sl:
                        entry = f"{ks[:3]}({kt[0]})"
                row += f"{entry:>10}"
            print(row)

print_timetable()

# Coverage check
print(f"\n{'='*54}")
print("  Coverage check")
print(f"{'='*54}")
print(f"{'Class':<6} {'Subject':<10} {'Required':>8} {'Scheduled':>9}")
print("-" * 36)
all_ok = True
for (c, s), req in sorted(requirements.items()):
    scheduled = sum(1 for (kc, ks, _) in assignment if kc == c and ks == s)
    ok = "✓" if scheduled == req else "✗"
    if scheduled != req:
        all_ok = False
    print(f"{c:<6} {s:<10} {req:>8} {scheduled:>8}  {ok}")

print()
print("All constraints satisfied ✓" if all_ok else "Some constraints violated ✗")
