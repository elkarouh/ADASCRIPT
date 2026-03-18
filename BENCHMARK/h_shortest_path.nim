## Shortest-path / dynamic-programming optimiser framework.
## 
## ALL DYNAMIC PROGRAMMING PROBLEMS CAN BE TRANSFORMED INTO SHORTEST-PATH PROBLEMS
## UNDER THE CONDITION THAT for each decision there is only ONE next state.

import sets, sugar, tables
import stdlib
import math



# ---------------------------------------------------------------------------
# Core Optimizer
# ---------------------------------------------------------------------------
type Cost_T = float
type Fringe_Element_T[S, D] = tuple
    hcost: float
    new_cost: float
    new_path: seq[D]
    next_state: S
type Optimizer[S, D] = ref object of RootObj
    offset: float
    decision_path: seq[D]
    start_state: S

proc initOptimizer[S, D](self: Optimizer[S, D], offset: float = 0.0) =
    self.offset = offset

proc newOptimizer*[S, D](offset: float = 0.0): Optimizer[S, D] =
    new(result)
    initOptimizer(result, offset)
type State_T1 = string
type Cost_T1 = float
type Decision_T1 = State_T1
type MyOptimizer = ref object of Optimizer[State_T1, Decision_T1]
    G: Table[State_T1, seq[(Decision_T1, Cost_T1)]]

proc newMyOptimizer*(): MyOptimizer =
    new(result)
    result.G = {"s": @[("u", 10.0), ("x", 5.0)], "u": @[("v", 1.0), ("x", 2.0)], "v": @[("y", 4.0)], "x": @[("u", 3.0), ("v", 9.0), ("y", 2.0)], "y": @[("s", 7.0), ("v", 6.0)]}.toTable
method get_state(self: Optimizer[State_T1, Decision_T1], past_decisions: seq[Decision_T1]): State_T1 {.base.} =
    raise newException(CatchableError, "Override get_state()")

method get_next_decisions(self: Optimizer[State_T1, Decision_T1], current_state: State_T1): seq[(Decision_T1, Cost_T)] {.base.} =
    raise newException(CatchableError, "Override get_next_decisions()")

method get_heuristic_cost(self: Optimizer[State_T1, Decision_T1], current_state: State_T1): float {.base.} =
    return 0.0

proc cost_operator(self: Optimizer[State_T1, Decision_T1], accumulated: Cost_T, step_cost: Cost_T): Cost_T =
    var actual_cost: Cost_T = step_cost + self.offset
    assert actual_cost >= 0
    return accumulated + actual_cost

proc hcost_operator(self: Optimizer[State_T1, Decision_T1], past_cost: Cost_T, current_state: State_T1): Cost_T =
    return past_cost + self.get_heuristic_cost(current_state)

proc real_cost(self: Optimizer[State_T1, Decision_T1], cost: Cost_T): Cost_T =
    return cost - self.offset * float(len(self.decision_path))

iterator shortest_path(self: Optimizer[State_T1, Decision_T1], start_state: State_T1, end_state: State_T1, allsolutions: bool = true): auto =
    self.start_state = start_state
    var empty_path: seq[Decision_T1] = @[]
    var fringe: PriorityQueue[Fringe_Element_T[State_T1, Decision_T1]] = newPriorityQueueWith((0.0, 0.0, empty_path, start_state))
    var visited: HashSet[State_T1] = initHashSet[State_T1]()

    while fringe.len > 0:
        var item = fringe.pop()
        var cost: float = item[1]
        var path: seq[Decision_T1] = item[2]
        var current_state: State_T1 = item[3]

        if not allsolutions and current_state in visited:
            continue

        self.decision_path = path
        visited.incl(current_state)

        if current_state == end_state:
            yield (self.real_cost(cost), path)
            if not allsolutions:
                break

        for (new_decision, step_cost) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T1] = path & @[new_decision]
            var next_state: State_T1 = self.get_state(new_path)
            if next_state notin visited:
                var new_cost: float = self.cost_operator(cost, step_cost)
                var hcost: float = self.hcost_operator(new_cost, next_state)
                fringe.push((hcost, new_cost, new_path, next_state))

    # ------------------------------------------------------------------
    # Generic traversal (BFS / DFS / best-first)
    # ------------------------------------------------------------------

proc is_end_state(self: Optimizer[State_T1, Decision_T1], state: State_T1): bool =
    return false

proc visit_state(self: Optimizer[State_T1, Decision_T1], state: var State_T1): void =
    echo("state =", state)

proc longest_path_min(self: Optimizer[State_T1, Decision_T1], end_state: State_T1, excluded_lengths: seq[int] = @[], offset: float = 1000.0): (float, seq[Decision_T1]) =
    var excluded: HashSet[int] = excluded_lengths.toHashSet()
    var empty_path: seq[Decision_T1] = @[]
    var fringe = newPriorityQueueWith((0.0, empty_path, self.start_state))
    var visited: Table[State_T1, float] = initTable[State_T1, float]()
    var solution: (float, seq[Decision_T1]) = (0.0, @[])

    while fringe:
        var item = fringe.pop()
        var cost: float = item[0]
        var path: seq[Decision_T1] = item[1]
        var current_state: State_T1 = item[2]
        var real_revenue: float = float(len(path)) * offset - cost

        if current_state in visited and real_revenue <= visited[current_state]:
            continue
        visited[current_state] = real_revenue

        if current_state == end_state:
            return (real_revenue, path)

        for (new_decision, revenue) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T1] = path & @[new_decision]
            var next_state: State_T1 = self.get_state(new_path)
            var cost_step: float = -revenue + offset
            assert cost_step > 0
            var new_cost: float = cost + cost_step
            var new_real: float = float(len(new_path)) * offset - new_cost

            var penalty: float = 0.0
            if len(new_path) in excluded and next_state == end_state:
                penalty = 100000.0

            if next_state notin visited or new_real > visited[next_state]:
                fringe.push((new_cost + penalty, new_path, next_state))

    return solution

proc longest_path(self: Optimizer[State_T1, Decision_T1], start_state: State_T1, end_state: State_T1, max_path_length: int = 1000, offset: float = 1000.0): (float, seq[Decision_T1]) =
    self.start_state = start_state
    let (revenue, path) = self.longest_path_min(end_state, offset = offset)
    if len(path) == 0:
        return (0.0, path)

    var excluded: seq[int] = @[len(path)]
    var best_revenue: float = revenue
    var best_path: seq[Decision_T1] = path

    while true:
        let (new_revenue, new_path) = self.longest_path_min(end_state, excluded_lengths = excluded, offset = offset)
        if len(new_path) == 0 or len(new_path) <= len(best_path):
            break
        if len(new_path) > max_path_length:
            break
        excluded.add(len(new_path))
        if new_revenue > best_revenue:
            best_revenue = new_revenue
            best_path = new_path

    return (best_revenue, best_path)

method get_state(self: MyOptimizer, past_decisions: seq[Decision_T1]): State_T1 =
    return past_decisions[^1]

method get_next_decisions(self: MyOptimizer, curr_state: State_T1): seq[(Decision_T1, Cost_T)] =
    return (self.G.getOrDefault(curr_state, @[]))

var op: MyOptimizer = newMyOptimizer()
var solution: (Cost_T1, seq[Decision_T1]) = op.longest_path("s", "v", max_path_length = 4)
echo("Longest path s->v:", solution)

# -----------------------------------------------------------------------
# Example 2 -- DP tutorial graph
# -----------------------------------------------------------------------
type State_T2 = string
type Cost_T2 = float
type Decision_T2 = State_T2
type MyOptimizer2 = ref object of Optimizer[State_T2, Decision_T2]
    G: Table[State_T2, seq[(Decision_T2, Cost_T2)]]

proc newMyOptimizer2*(): MyOptimizer2 =
    new(result)
    result.G = {"a": @[("b", 2.0), ("c", 4.0), ("d", 3.0)], "b": @[("e", 7.0), ("f", 4.0), ("g", 6.0)], "c": @[("e", 3.0), ("f", 2.0), ("g", 4.0)], "d": @[("e", 4.0), ("f", 1.0), ("g", 5.0)], "e": @[("h", 1.0), ("i", 4.0)], "f": @[("h", 6.0), ("i", 3.0)], "g": @[("h", 3.0), ("i", 3.0)], "h": @[("j", 3.0)], "i": @[("j", 4.0)]}.toTable
method get_state(self: MyOptimizer2, past_decisions: seq[Decision_T2]): State_T2 =
    return past_decisions[^1]

method get_next_decisions(self: MyOptimizer2, curr_state: State_T2): seq[(Decision_T2, Cost_T)] =
    return (self.G.getOrDefault(curr_state, @[]))

echo("======= SHORTEST a->j =======")
var op2: MyOptimizer2 = newMyOptimizer2()
for solution in op2.shortest_path("a", "j"):
    echo(solution)
echo("======= LONGEST  a->j =======")
echo(op2.longest_path("a", "j"))


# -----------------------------------------------------------------------
# Example 3 -- Rod Cutting
# You are given a rod of size n >0, it can be cut into any number of pieces k (k ≤ n).
# Price for each piece of size i is represented as p(i) and maximum revenue from a rod of size i is r(i)
# (could be split into multiple pieces). Find r(n) for the rod of size n.
# -----------------------------------------------------------------------
var ROD_SIZE: int = 5

type State_T3 = (int, int)
type Revenue_T3 = float
type Decision_T3 = int

type RodCutting = ref object of Optimizer[State_T3, Decision_T3]
    prices: seq[(Decision_T3, Revenue_T3)]

proc newRodCutting*(): RodCutting =
    new(result)
    result.prices = @[(1, 1.0), (2, 5.0), (3, 8.0), (4, 9.0), (5, 10.0), (6, 17.0), (7, 17.0), (8, 20.0), (9, 24.0), (10, 30.0)]
method get_state(self: Optimizer[State_T3, Decision_T3], past_decisions: seq[Decision_T3]): State_T3 {.base.} =
    raise newException(CatchableError, "Override get_state()")

method get_next_decisions(self: Optimizer[State_T3, Decision_T3], current_state: State_T3): seq[(Decision_T3, Cost_T)] {.base.} =
    raise newException(CatchableError, "Override get_next_decisions()")

method get_heuristic_cost(self: Optimizer[State_T3, Decision_T3], current_state: State_T3): float {.base.} =
    return 0.0

proc cost_operator(self: Optimizer[State_T3, Decision_T3], accumulated: Cost_T, step_cost: Cost_T): Cost_T =
    var actual_cost: Cost_T = step_cost + self.offset
    assert actual_cost >= 0
    return accumulated + actual_cost

proc hcost_operator(self: Optimizer[State_T3, Decision_T3], past_cost: Cost_T, current_state: State_T3): Cost_T =
    return past_cost + self.get_heuristic_cost(current_state)

proc real_cost(self: Optimizer[State_T3, Decision_T3], cost: Cost_T): Cost_T =
    return cost - self.offset * float(len(self.decision_path))

iterator shortest_path(self: Optimizer[State_T3, Decision_T3], start_state: State_T3, end_state: State_T3, allsolutions: bool = true): auto =
    self.start_state = start_state
    var empty_path: seq[Decision_T3] = @[]
    var fringe: PriorityQueue[Fringe_Element_T[State_T3, Decision_T3]] = newPriorityQueueWith((0.0, 0.0, empty_path, start_state))
    var visited: HashSet[State_T3] = initHashSet[State_T3]()

    while fringe.len > 0:
        var item = fringe.pop()
        var cost: float = item[1]
        var path: seq[Decision_T3] = item[2]
        var current_state: State_T3 = item[3]

        if not allsolutions and current_state in visited:
            continue

        self.decision_path = path
        visited.incl(current_state)

        if current_state == end_state:
            yield (self.real_cost(cost), path)
            if not allsolutions:
                break

        for (new_decision, step_cost) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T3] = path & @[new_decision]
            var next_state: State_T3 = self.get_state(new_path)
            if next_state notin visited:
                var new_cost: float = self.cost_operator(cost, step_cost)
                var hcost: float = self.hcost_operator(new_cost, next_state)
                fringe.push((hcost, new_cost, new_path, next_state))

    # ------------------------------------------------------------------
    # Generic traversal (BFS / DFS / best-first)
    # ------------------------------------------------------------------

proc is_end_state(self: Optimizer[State_T3, Decision_T3], state: State_T3): bool =
    return false

proc visit_state(self: Optimizer[State_T3, Decision_T3], state: var State_T3): void =
    echo("state =", state)

proc longest_path_min(self: Optimizer[State_T3, Decision_T3], end_state: State_T3, excluded_lengths: seq[int] = @[], offset: float = 1000.0): (float, seq[Decision_T3]) =
    var excluded: HashSet[int] = excluded_lengths.toHashSet()
    var empty_path: seq[Decision_T3] = @[]
    var fringe = newPriorityQueueWith((0.0, empty_path, self.start_state))
    var visited: Table[State_T3, float] = initTable[State_T3, float]()
    var solution: (float, seq[Decision_T3]) = (0.0, @[])

    while fringe:
        var item = fringe.pop()
        var cost: float = item[0]
        var path: seq[Decision_T3] = item[1]
        var current_state: State_T3 = item[2]
        var real_revenue: float = float(len(path)) * offset - cost

        if current_state in visited and real_revenue <= visited[current_state]:
            continue
        visited[current_state] = real_revenue

        if current_state == end_state:
            return (real_revenue, path)

        for (new_decision, revenue) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T3] = path & @[new_decision]
            var next_state: State_T3 = self.get_state(new_path)
            var cost_step: float = -revenue + offset
            assert cost_step > 0
            var new_cost: float = cost + cost_step
            var new_real: float = float(len(new_path)) * offset - new_cost

            var penalty: float = 0.0
            if len(new_path) in excluded and next_state == end_state:
                penalty = 100000.0

            if next_state notin visited or new_real > visited[next_state]:
                fringe.push((new_cost + penalty, new_path, next_state))

    return solution

proc longest_path(self: Optimizer[State_T3, Decision_T3], start_state: State_T3, end_state: State_T3, max_path_length: int = 1000, offset: float = 1000.0): (float, seq[Decision_T3]) =
    self.start_state = start_state
    let (revenue, path) = self.longest_path_min(end_state, offset = offset)
    if len(path) == 0:
        return (0.0, path)

    var excluded: seq[int] = @[len(path)]
    var best_revenue: float = revenue
    var best_path: seq[Decision_T3] = path

    while true:
        let (new_revenue, new_path) = self.longest_path_min(end_state, excluded_lengths = excluded, offset = offset)
        if len(new_path) == 0 or len(new_path) <= len(best_path):
            break
        if len(new_path) > max_path_length:
            break
        excluded.add(len(new_path))
        if new_revenue > best_revenue:
            best_revenue = new_revenue
            best_path = new_path

    return (best_revenue, best_path)

method get_state(self: RodCutting, past_decisions: seq[Decision_T3]): State_T3 =
    var stage: int = len(past_decisions)
    var remaining_size: int = ROD_SIZE - sum(collect(for d in past_decisions: d))
    if remaining_size <= 0:
        return (-1, 0)
    return (stage, remaining_size)

method get_next_decisions(self: RodCutting, current_state: State_T3): seq[(Decision_T3, Cost_T)] =
    let (stage, remaining_size) = current_state
    return (collect(for (size, rev) in self.prices: (if size <= remaining_size: (size, rev))))

echo("======= ROD CUTTING =======")
var op3: RodCutting = newRodCutting()
echo(op3.longest_path((0, ROD_SIZE), (-1, 0)))

# -----------------------------------------------------------------------
# Example 4 -- Capital Budgeting
# -----------------------------------------------------------------------
const CAPITAL: int = 5
type Cost_T4 = float
type Stage_T4 = int
type State_T4 = tuple
    stage: Stage_T4
    budget: Cost_T4
type Decision_T4 = string
type Revenue_T4 = float
type Choice_T4 = tuple
    cost: Cost_T4
    revenue: Revenue_T4
type CapitalBudgeting = ref object of Optimizer[State_T4, Decision_T4]
    choices: Table[Stage_T4, Table[Decision_T4, Choice_T4]]

proc newCapitalBudgeting*(): CapitalBudgeting =
    new(result)
    result.choices = {1: {"plant1-p1": (cost: 0.0, revenue: 0.0), "plant1-p2": (cost: 1.0, revenue: 5.0), "plant1-p3": (cost: 2.0, revenue: 6.0)}.toTable, 2: {"plant2-p1": (cost: 0.0, revenue: 0.0), "plant2-p2": (cost: 2.0, revenue: 8.0), "plant2-p3": (cost: 3.0, revenue: 9.0), "plant2-p4": (cost: 4.0, revenue: 12.0)}.toTable, 3: {"plant3-p1": (cost: 0.0, revenue: 0.0), "plant3-p2": (cost: 1.0, revenue: 4.0)}.toTable}.toTable
method get_state(self: Optimizer[State_T4, Decision_T4], past_decisions: seq[Decision_T4]): State_T4 {.base.} =
    raise newException(CatchableError, "Override get_state()")

method get_next_decisions(self: Optimizer[State_T4, Decision_T4], current_state: State_T4): seq[(Decision_T4, Cost_T)] {.base.} =
    raise newException(CatchableError, "Override get_next_decisions()")

method get_heuristic_cost(self: Optimizer[State_T4, Decision_T4], current_state: State_T4): float {.base.} =
    return 0.0

proc cost_operator(self: Optimizer[State_T4, Decision_T4], accumulated: Cost_T, step_cost: Cost_T): Cost_T =
    var actual_cost: Cost_T = step_cost + self.offset
    assert actual_cost >= 0
    return accumulated + actual_cost

proc hcost_operator(self: Optimizer[State_T4, Decision_T4], past_cost: Cost_T, current_state: State_T4): Cost_T =
    return past_cost + self.get_heuristic_cost(current_state)

proc real_cost(self: Optimizer[State_T4, Decision_T4], cost: Cost_T): Cost_T =
    return cost - self.offset * float(len(self.decision_path))

iterator shortest_path(self: Optimizer[State_T4, Decision_T4], start_state: State_T4, end_state: State_T4, allsolutions: bool = true): auto =
    self.start_state = start_state
    var empty_path: seq[Decision_T4] = @[]
    var fringe: PriorityQueue[Fringe_Element_T[State_T4, Decision_T4]] = newPriorityQueueWith((0.0, 0.0, empty_path, start_state))
    var visited: HashSet[State_T4] = initHashSet[State_T4]()

    while fringe.len > 0:
        var item = fringe.pop()
        var cost: float = item[1]
        var path: seq[Decision_T4] = item[2]
        var current_state: State_T4 = item[3]

        if not allsolutions and current_state in visited:
            continue

        self.decision_path = path
        visited.incl(current_state)

        if current_state == end_state:
            yield (self.real_cost(cost), path)
            if not allsolutions:
                break

        for (new_decision, step_cost) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T4] = path & @[new_decision]
            var next_state: State_T4 = self.get_state(new_path)
            if next_state notin visited:
                var new_cost: float = self.cost_operator(cost, step_cost)
                var hcost: float = self.hcost_operator(new_cost, next_state)
                fringe.push((hcost, new_cost, new_path, next_state))

    # ------------------------------------------------------------------
    # Generic traversal (BFS / DFS / best-first)
    # ------------------------------------------------------------------

proc is_end_state(self: Optimizer[State_T4, Decision_T4], state: State_T4): bool =
    return false

proc visit_state(self: Optimizer[State_T4, Decision_T4], state: var State_T4): void =
    echo("state =", state)

proc longest_path_min(self: Optimizer[State_T4, Decision_T4], end_state: State_T4, excluded_lengths: seq[int] = @[], offset: float = 1000.0): (float, seq[Decision_T4]) =
    var excluded: HashSet[int] = excluded_lengths.toHashSet()
    var empty_path: seq[Decision_T4] = @[]
    var fringe = newPriorityQueueWith((0.0, empty_path, self.start_state))
    var visited: Table[State_T4, float] = initTable[State_T4, float]()
    var solution: (float, seq[Decision_T4]) = (0.0, @[])

    while fringe:
        var item = fringe.pop()
        var cost: float = item[0]
        var path: seq[Decision_T4] = item[1]
        var current_state: State_T4 = item[2]
        var real_revenue: float = float(len(path)) * offset - cost

        if current_state in visited and real_revenue <= visited[current_state]:
            continue
        visited[current_state] = real_revenue

        if current_state == end_state:
            return (real_revenue, path)

        for (new_decision, revenue) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T4] = path & @[new_decision]
            var next_state: State_T4 = self.get_state(new_path)
            var cost_step: float = -revenue + offset
            assert cost_step > 0
            var new_cost: float = cost + cost_step
            var new_real: float = float(len(new_path)) * offset - new_cost

            var penalty: float = 0.0
            if len(new_path) in excluded and next_state == end_state:
                penalty = 100000.0

            if next_state notin visited or new_real > visited[next_state]:
                fringe.push((new_cost + penalty, new_path, next_state))

    return solution

proc longest_path(self: Optimizer[State_T4, Decision_T4], start_state: State_T4, end_state: State_T4, max_path_length: int = 1000, offset: float = 1000.0): (float, seq[Decision_T4]) =
    self.start_state = start_state
    let (revenue, path) = self.longest_path_min(end_state, offset = offset)
    if len(path) == 0:
        return (0.0, path)

    var excluded: seq[int] = @[len(path)]
    var best_revenue: float = revenue
    var best_path: seq[Decision_T4] = path

    while true:
        let (new_revenue, new_path) = self.longest_path_min(end_state, excluded_lengths = excluded, offset = offset)
        if len(new_path) == 0 or len(new_path) <= len(best_path):
            break
        if len(new_path) > max_path_length:
            break
        excluded.add(len(new_path))
        if new_revenue > best_revenue:
            best_revenue = new_revenue
            best_path = new_path

    return (best_revenue, best_path)

method get_state(self: CapitalBudgeting, past_decisions: seq[Decision_T4]): State_T4 =
    var stage: int = len(past_decisions)
    var spent: float = 0.0
    for d in past_decisions:
        for choices in self.choices.values():
            if d in choices:
                spent += choices[d][0]
    return (stage, float(CAPITAL) - spent)

method get_next_decisions(self: CapitalBudgeting, current_state: State_T4): seq[(Decision_T4, Cost_T)] =
    let (stage, budget) = current_state
    if stage notin self.choices:
        return @[]
    var choices: Table[Decision_T4, Choice_T4] = self.choices[stage]
    return (collect(for (name, choice) in choices.pairs(): (if choice.cost <= budget: (name, choice.revenue))))

echo("======= CAPITAL BUDGETING =======")
var op4: CapitalBudgeting = newCapitalBudgeting()
echo(op4.longest_path((stage: 1, budget: float(CAPITAL)), (stage: 3, budget: 0.0)))

# -----------------------------------------------------------------------
# Example 5 -- Knapsack
# -----------------------------------------------------------------------
const MAX_WEIGHT: int = 5
type Stage_T5 = enum STAGE1, STAGE2, STAGE3, END
type State_T5 = tuple
    stage: Stage_T5
    remaining: int
type Decision_T5 = tuple
    stage: Stage_T5
    quantity: int
type Choice_T5 = tuple
    weight: int
    benefit: int
type Knapsack = ref object of Optimizer[State_T5, Decision_T5]
    items: Table[Stage_T5, Choice_T5]

proc newKnapsack*(): Knapsack =
    new(result)
    result.items = {Stage1: (weight: 2, benefit: 65), Stage2: (weight: 3, benefit: 80), Stage3: (weight: 1, benefit: 30)}.toTable
method get_state(self: Optimizer[State_T5, Decision_T5], past_decisions: seq[Decision_T5]): State_T5 {.base.} =
    raise newException(CatchableError, "Override get_state()")

method get_next_decisions(self: Optimizer[State_T5, Decision_T5], current_state: State_T5): seq[(Decision_T5, Cost_T)] {.base.} =
    raise newException(CatchableError, "Override get_next_decisions()")

method get_heuristic_cost(self: Optimizer[State_T5, Decision_T5], current_state: State_T5): float {.base.} =
    return 0.0

proc cost_operator(self: Optimizer[State_T5, Decision_T5], accumulated: Cost_T, step_cost: Cost_T): Cost_T =
    var actual_cost: Cost_T = step_cost + self.offset
    assert actual_cost >= 0
    return accumulated + actual_cost

proc hcost_operator(self: Optimizer[State_T5, Decision_T5], past_cost: Cost_T, current_state: State_T5): Cost_T =
    return past_cost + self.get_heuristic_cost(current_state)

proc real_cost(self: Optimizer[State_T5, Decision_T5], cost: Cost_T): Cost_T =
    return cost - self.offset * float(len(self.decision_path))

iterator shortest_path(self: Optimizer[State_T5, Decision_T5], start_state: State_T5, end_state: State_T5, allsolutions: bool = true): auto =
    self.start_state = start_state
    var empty_path: seq[Decision_T5] = @[]
    var fringe: PriorityQueue[Fringe_Element_T[State_T5, Decision_T5]] = newPriorityQueueWith((0.0, 0.0, empty_path, start_state))
    var visited: HashSet[State_T5] = initHashSet[State_T5]()

    while fringe.len > 0:
        var item = fringe.pop()
        var cost: float = item[1]
        var path: seq[Decision_T5] = item[2]
        var current_state: State_T5 = item[3]

        if not allsolutions and current_state in visited:
            continue

        self.decision_path = path
        visited.incl(current_state)

        if current_state == end_state:
            yield (self.real_cost(cost), path)
            if not allsolutions:
                break

        for (new_decision, step_cost) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T5] = path & @[new_decision]
            var next_state: State_T5 = self.get_state(new_path)
            if next_state notin visited:
                var new_cost: float = self.cost_operator(cost, step_cost)
                var hcost: float = self.hcost_operator(new_cost, next_state)
                fringe.push((hcost, new_cost, new_path, next_state))

    # ------------------------------------------------------------------
    # Generic traversal (BFS / DFS / best-first)
    # ------------------------------------------------------------------

proc is_end_state(self: Optimizer[State_T5, Decision_T5], state: State_T5): bool =
    return false

proc visit_state(self: Optimizer[State_T5, Decision_T5], state: var State_T5): void =
    echo("state =", state)

proc longest_path_min(self: Optimizer[State_T5, Decision_T5], end_state: State_T5, excluded_lengths: seq[int] = @[], offset: float = 1000.0): (float, seq[Decision_T5]) =
    var excluded: HashSet[int] = excluded_lengths.toHashSet()
    var empty_path: seq[Decision_T5] = @[]
    var fringe = newPriorityQueueWith((0.0, empty_path, self.start_state))
    var visited: Table[State_T5, float] = initTable[State_T5, float]()
    var solution: (float, seq[Decision_T5]) = (0.0, @[])

    while fringe:
        var item = fringe.pop()
        var cost: float = item[0]
        var path: seq[Decision_T5] = item[1]
        var current_state: State_T5 = item[2]
        var real_revenue: float = float(len(path)) * offset - cost

        if current_state in visited and real_revenue <= visited[current_state]:
            continue
        visited[current_state] = real_revenue

        if current_state == end_state:
            return (real_revenue, path)

        for (new_decision, revenue) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T5] = path & @[new_decision]
            var next_state: State_T5 = self.get_state(new_path)
            var cost_step: float = -revenue + offset
            assert cost_step > 0
            var new_cost: float = cost + cost_step
            var new_real: float = float(len(new_path)) * offset - new_cost

            var penalty: float = 0.0
            if len(new_path) in excluded and next_state == end_state:
                penalty = 100000.0

            if next_state notin visited or new_real > visited[next_state]:
                fringe.push((new_cost + penalty, new_path, next_state))

    return solution

proc longest_path(self: Optimizer[State_T5, Decision_T5], start_state: State_T5, end_state: State_T5, max_path_length: int = 1000, offset: float = 1000.0): (float, seq[Decision_T5]) =
    self.start_state = start_state
    let (revenue, path) = self.longest_path_min(end_state, offset = offset)
    if len(path) == 0:
        return (0.0, path)

    var excluded: seq[int] = @[len(path)]
    var best_revenue: float = revenue
    var best_path: seq[Decision_T5] = path

    while true:
        let (new_revenue, new_path) = self.longest_path_min(end_state, excluded_lengths = excluded, offset = offset)
        if len(new_path) == 0 or len(new_path) <= len(best_path):
            break
        if len(new_path) > max_path_length:
            break
        excluded.add(len(new_path))
        if new_revenue > best_revenue:
            best_revenue = new_revenue
            best_path = new_path

    return (best_revenue, best_path)

method get_state(self: Knapsack, past_decisions: seq[Decision_T5]): State_T5 =
    var stage: Stage_T5 = past_decisions[^1].stage.succ
    var remaining: int = MAX_WEIGHT
    for decision in past_decisions:
        var prev_stage: Stage_T5 = decision.stage
        var qty: int = decision.quantity
        remaining -= qty * self.items[prev_stage].weight
    return (stage, remaining)

method get_next_decisions(self: Knapsack, current_state: State_T5): seq[(Decision_T5, Cost_T)] =
    let (stage, remaining) = current_state
    if stage == END:
        return @[]
    let (weight, benefit) = self.items[stage]
    var decisions: seq[(Decision_T5, Cost_T)] = @[]
    var qty: int = 0
    while qty * weight <= remaining:
        decisions.add(((stage: stage, quantity: qty), float(benefit * qty)))
        qty += 1
    return decisions

echo("======= KNAPSACK =======")
var op5: Knapsack = newKnapsack()
echo(op5.longest_path((stage: STAGE1, remaining: MAX_WEIGHT), (stage: END, remaining: 0)))

# -----------------------------------------------------------------------
# Example 6 -- Equipment Replacement
# -----------------------------------------------------------------------
type Decision_T6 = enum BUY, SELL, KEEP, TRADE
type Cost_T6 = float
const IRRELEVANT: int = -1
type State_T6 = (int, int)

type EquipmentReplacement = ref object of Optimizer[State_T6, Decision_T6]
    maintenance_cost: Table[int, Cost_T6]
    market_value: Table[int, Cost_T6]

method get_state(self: Optimizer[State_T6, Decision_T6], past_decisions: seq[Decision_T6]): State_T6 {.base.} =
    raise newException(CatchableError, "Override get_state()")

method get_next_decisions(self: Optimizer[State_T6, Decision_T6], current_state: State_T6): seq[(Decision_T6, Cost_T)] {.base.} =
    raise newException(CatchableError, "Override get_next_decisions()")

method get_heuristic_cost(self: Optimizer[State_T6, Decision_T6], current_state: State_T6): float {.base.} =
    return 0.0

proc cost_operator(self: Optimizer[State_T6, Decision_T6], accumulated: Cost_T, step_cost: Cost_T): Cost_T =
    var actual_cost: Cost_T = step_cost + self.offset
    assert actual_cost >= 0
    return accumulated + actual_cost

proc hcost_operator(self: Optimizer[State_T6, Decision_T6], past_cost: Cost_T, current_state: State_T6): Cost_T =
    return past_cost + self.get_heuristic_cost(current_state)

proc real_cost(self: Optimizer[State_T6, Decision_T6], cost: Cost_T): Cost_T =
    return cost - self.offset * float(len(self.decision_path))

iterator shortest_path(self: Optimizer[State_T6, Decision_T6], start_state: State_T6, end_state: State_T6, allsolutions: bool = true): auto =
    self.start_state = start_state
    var empty_path: seq[Decision_T6] = @[]
    var fringe: PriorityQueue[Fringe_Element_T[State_T6, Decision_T6]] = newPriorityQueueWith((0.0, 0.0, empty_path, start_state))
    var visited: HashSet[State_T6] = initHashSet[State_T6]()

    while fringe.len > 0:
        var item = fringe.pop()
        var cost: float = item[1]
        var path: seq[Decision_T6] = item[2]
        var current_state: State_T6 = item[3]

        if not allsolutions and current_state in visited:
            continue

        self.decision_path = path
        visited.incl(current_state)

        if current_state == end_state:
            yield (self.real_cost(cost), path)
            if not allsolutions:
                break

        for (new_decision, step_cost) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T6] = path & @[new_decision]
            var next_state: State_T6 = self.get_state(new_path)
            if next_state notin visited:
                var new_cost: float = self.cost_operator(cost, step_cost)
                var hcost: float = self.hcost_operator(new_cost, next_state)
                fringe.push((hcost, new_cost, new_path, next_state))

    # ------------------------------------------------------------------
    # Generic traversal (BFS / DFS / best-first)
    # ------------------------------------------------------------------

proc is_end_state(self: Optimizer[State_T6, Decision_T6], state: State_T6): bool =
    return false

proc visit_state(self: Optimizer[State_T6, Decision_T6], state: var State_T6): void =
    echo("state =", state)

proc longest_path_min(self: Optimizer[State_T6, Decision_T6], end_state: State_T6, excluded_lengths: seq[int] = @[], offset: float = 1000.0): (float, seq[Decision_T6]) =
    var excluded: HashSet[int] = excluded_lengths.toHashSet()
    var empty_path: seq[Decision_T6] = @[]
    var fringe = newPriorityQueueWith((0.0, empty_path, self.start_state))
    var visited: Table[State_T6, float] = initTable[State_T6, float]()
    var solution: (float, seq[Decision_T6]) = (0.0, @[])

    while fringe:
        var item = fringe.pop()
        var cost: float = item[0]
        var path: seq[Decision_T6] = item[1]
        var current_state: State_T6 = item[2]
        var real_revenue: float = float(len(path)) * offset - cost

        if current_state in visited and real_revenue <= visited[current_state]:
            continue
        visited[current_state] = real_revenue

        if current_state == end_state:
            return (real_revenue, path)

        for (new_decision, revenue) in self.get_next_decisions(current_state):
            var new_path: seq[Decision_T6] = path & @[new_decision]
            var next_state: State_T6 = self.get_state(new_path)
            var cost_step: float = -revenue + offset
            assert cost_step > 0
            var new_cost: float = cost + cost_step
            var new_real: float = float(len(new_path)) * offset - new_cost

            var penalty: float = 0.0
            if len(new_path) in excluded and next_state == end_state:
                penalty = 100000.0

            if next_state notin visited or new_real > visited[next_state]:
                fringe.push((new_cost + penalty, new_path, next_state))

    return solution

proc longest_path(self: Optimizer[State_T6, Decision_T6], start_state: State_T6, end_state: State_T6, max_path_length: int = 1000, offset: float = 1000.0): (float, seq[Decision_T6]) =
    self.start_state = start_state
    let (revenue, path) = self.longest_path_min(end_state, offset = offset)
    if len(path) == 0:
        return (0.0, path)

    var excluded: seq[int] = @[len(path)]
    var best_revenue: float = revenue
    var best_path: seq[Decision_T6] = path

    while true:
        let (new_revenue, new_path) = self.longest_path_min(end_state, excluded_lengths = excluded, offset = offset)
        if len(new_path) == 0 or len(new_path) <= len(best_path):
            break
        if len(new_path) > max_path_length:
            break
        excluded.add(len(new_path))
        if new_revenue > best_revenue:
            best_revenue = new_revenue
            best_path = new_path

    return (best_revenue, best_path)

method get_state(self: EquipmentReplacement, past_decisions: seq[Decision_T6]): State_T6
method get_next_decisions(self: EquipmentReplacement, current_state: State_T6): seq[(Decision_T6, Cost_T)]
proc initEquipmentReplacement(self: EquipmentReplacement, offset: float = 0.0) =
    self.maintenance_cost = {0: 60.0, 1: 80.0, 2: 120.0}.toTable
    self.market_value = {0: 1000.0, 1: 800.0, 2: 600.0, 3: 500.0}.toTable
    initOptimizer[State_T6, Decision_T6](self, offset)

proc newEquipmentReplacement*(offset: float = 0.0): EquipmentReplacement =
    new(result)
    initEquipmentReplacement(result, offset)
method get_state(self: EquipmentReplacement, past_decisions: seq[Decision_T6]): State_T6 =
    var year: int = len(past_decisions)
    if year == 6:
        return (6, IRRELEVANT)
    var age: int = 0
    for decision in past_decisions:
        if decision == KEEP:
            age = age + 1
        else:
            age = 1
    return (year, age)

method get_next_decisions(self: EquipmentReplacement, current_state: State_T6): seq[(Decision_T6, Cost_T)] =
    let (year, age) = current_state
    if age == IRRELEVANT:
        return @[]
    if year == 0:
        return (@[(BUY, self.maintenance_cost[0] + 1000.0)])
    if year == 5:
        return (@[(SELL, -self.market_value[age])])
    if age == 3:
        return (@[(TRADE, -self.market_value[age] + 1000.0 + self.maintenance_cost[0])])
    return (@[(KEEP, self.maintenance_cost[age]), (TRADE, -self.market_value[age] + 1000.0 + self.maintenance_cost[0])])

echo("======= EQUIPMENT REPLACEMENT =======")
var op6: EquipmentReplacement = newEquipmentReplacement(offset = 10000.0)
var start_state: State_T6 = (0, 0)
var end_state: State_T6 = (6, IRRELEVANT)
for solution in op6.shortest_path(start_state, end_state):
    echo(solution)

# -----------------------------------------------------------------------
# Example 7 -- Romania map (A* with heuristic)
# -----------------------------------------------------------------------
type State_T7 = string
type Distance_T7 = float
type Decision_T7 = string
type BookMap = ref object of Optimizer[State_T7, Decision_T7]
    G: Table[State_T7, seq[(Decision_T7, Distance_T7)]]
    heuristic: Table[State_T7, Distance_T7]

proc newBookMap*(): BookMap =
    new(result)
    result.G = {"arad": @[("sibiu", 140.0), ("timisoara", 118.0), ("zerind", 75.0)], "bucharest": @[("giurgiu", 90.0), ("urzineci", 85.0), ("fagaras", 211.0), ("pitesti", 101.0)], "craiova": @[("rimnicu", 146.0), ("pitesti", 138.0), ("drobeta", 120.0)], "drobeta": @[("craiova", 120.0), ("mehadia", 75.0)], "eforie": @[("hirsova", 86.0)], "fagaras": @[("sibiu", 99.0), ("bucharest", 211.0)], "giurgiu": @[("bucharest", 90.0)], "hirsova": @[("eforie", 86.0), ("urzineci", 98.0)], "lasi": @[("neamt", 87.0), ("vaslui", 92.0)], "lugoj": @[("mehadia", 70.0), ("timisoara", 111.0)], "mehadia": @[("drobeta", 75.0), ("lugoj", 70.0)], "neamt": @[("lasi", 87.0)], "oradea": @[("zerind", 71.0), ("sibiu", 151.0)], "pitesti": @[("bucharest", 101.0), ("rimnicu", 97.0), ("craiova", 138.0)], "rimnicu": @[("pitesti", 97.0), ("sibiu", 80.0), ("craiova", 146.0)], "sibiu": @[("rimnicu", 80.0), ("arad", 140.0), ("oradea", 151.0), ("fagaras", 99.0)], "timisoara": @[("lugoj", 111.0), ("arad", 118.0)], "urzineci": @[("bucharest", 85.0), ("vaslui", 142.0), ("hirsova", 98.0)], "vaslui": @[("urzineci", 142.0), ("lasi", 92.0)], "zerind": @[("arad", 75.0), ("oradea", 71.0)]}.toTable
    result.heuristic = {"arad": 366.0, "bucharest": 0.0, "craiova": 160.0, "drobeta": 242.0, "eforie": 161.0, "fagaras": 176.0, "giurgiu": 77.0, "hirsova": 151.0, "lasi": 226.0, "lugoj": 244.0, "mehadia": 241.0, "neamt": 234.0, "oradea": 380.0, "pitesti": 100.0, "rimnicu": 193.0, "sibiu": 253.0, "timisoara": 329.0, "urzineci": 80.0, "vaslui": 199.0, "zerind": 374.0}.toTable
method get_state(self: BookMap, past_decisions: seq[State_T7]): State_T7 =
    return past_decisions[^1]

method get_next_decisions(self: BookMap, current_state: State_T7): seq[(Decision_T7, Cost_T)] =
    return (self.G.getOrDefault(current_state, @[]))

method get_heuristic_cost(self: BookMap, city: State_T7): float =
    return (self.heuristic.getOrDefault(city, 0))

var op7: BookMap = newBookMap()
echo("======= ROMANIA MAP: oradea -> bucharest =======")
for solution in op7.shortest_path("oradea", "bucharest"):
    echo(solution)
