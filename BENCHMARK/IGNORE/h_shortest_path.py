from enum import Enum
from typing import NamedTuple
"""
Shortest-path / dynamic-programming optimiser framework.

ALL DYNAMIC PROGRAMMING PROBLEMS CAN BE TRANSFORMED INTO SHORTEST-PATH PROBLEMS
UNDER THE CONDITION THAT for each decision there is only ONE next state.
"""

from stdlib import ANY, PriorityQueue, FifoQueue, LifoQueue
from math import log

# nimport stdlib


# ---------------------------------------------------------------------------
# Core Optimizer
# ---------------------------------------------------------------------------
Cost_T = float
class Fringe_Element_T(NamedTuple):
    hcost: float
    new_cost: float
    new_path: list[D]
    next_state: S
class Optimizer[S, D]:
    """
        Generic shortest-path / dynamic-programming optimiser.
    
        Subclass and override:
          - get_state(past_decisions)       -> current state
          - get_next_decisions(state)       -> list of (decision, cost) pairs
          - get_heuristic_cost(state)       -> admissible heuristic (default 0)
          - cost_operator(accumulated, new) -> how costs combine (default: addition)
        """
    offset: float
    decision_path: list[D]
    start_state: S
    def __init__(self, offset: float = 0.0):
        self.offset = offset
        self.decision_path = []

    # ------------------------------------------------------------------
    # Methods to override
    # ------------------------------------------------------------------

    def get_state(self, past_decisions: list[D]) -> S:
        raise NotImplementedError("Override get_state()")

    def get_next_decisions(self, current_state: S) -> list[tuple[D, Cost_T]]:
        raise NotImplementedError("Override get_next_decisions()")

    def get_heuristic_cost(self, current_state: S) -> float:
        return 0.0

    def cost_operator(self, accumulated: Cost_T, step_cost: Cost_T) -> Cost_T:
        actual_cost: Cost_T = step_cost + self.offset
        assert actual_cost >= 0
        return accumulated + actual_cost

    def hcost_operator(self, past_cost: Cost_T, current_state: S) -> Cost_T:
        return past_cost + self.get_heuristic_cost(current_state)

    def real_cost(self, cost: Cost_T) -> Cost_T:
        return cost - self.offset * float(len(self.decision_path))

    # ------------------------------------------------------------------
    # Shortest-path (A* / Dijkstra)
    # ------------------------------------------------------------------

    def shortest_path(self, start_state: S, end_state: S, allsolutions: bool = True):
        self.start_state = start_state
        empty_path: list[D] = []
        fringe: PriorityQueue = PriorityQueue((0.0, 0.0, empty_path, start_state))
        visited: set[S] = set()

        while fringe:
            item = fringe.pop()
            cost: float = item[1]
            path: list[D] = item[2]
            current_state: S = item[3]

            if not allsolutions and current_state in visited:
                continue

            self.decision_path = path
            visited.add(current_state)

            if current_state == end_state:
                yield self.real_cost(cost), path
                if not allsolutions:
                    break

            for new_decision, step_cost in self.get_next_decisions(current_state):
                new_path: list[D] = path + [new_decision]
                next_state: S = self.get_state(new_path)
                if next_state not in visited:
                    new_cost: float = self.cost_operator(cost, step_cost)
                    hcost: float = self.hcost_operator(new_cost, next_state)
                    fringe.push((hcost, new_cost, new_path, next_state))

    # ------------------------------------------------------------------
    # Generic traversal (BFS / DFS / best-first)
    # ------------------------------------------------------------------

    def is_end_state(self, state: S) -> bool:
        return False

    def visit_state(self, state: S) -> None:
        print("state =", state)

    # ------------------------------------------------------------------
    # Longest-path helpers
    return # ------------------------------------------------------------------

    def longest_path_min(self, end_state: S, excluded_lengths: list[int] = [], offset: float = 1000.0) -> tuple[float, list[D]]:
        excluded: set[int] = set(excluded_lengths)
        empty_path: list[D] = []
        fringe = PriorityQueue((0.0, empty_path, self.start_state))
        visited: dict[S, float] = {}
        solution: tuple[float, list[D]] = (0.0, [])

        while fringe:
            item = fringe.pop()
            cost: float = item[0]
            path: list[D] = item[1]
            current_state: S = item[2]
            real_revenue: float = float(len(path)) * offset - cost

            if current_state in visited and real_revenue <= visited[current_state]:
                continue
            visited[current_state] = real_revenue

            if current_state == end_state:
                return real_revenue, path

            for new_decision, revenue in self.get_next_decisions(current_state):
                new_path: list[D] = path + [new_decision]
                next_state: S = self.get_state(new_path)
                cost_step: float = -revenue + offset
                assert cost_step > 0
                new_cost: float = cost + cost_step
                new_real: float = float(len(new_path)) * offset - new_cost

                penalty: float = 0.0
                if len(new_path) in excluded and next_state == end_state:
                    penalty = 100000.0

                if next_state not in visited or new_real > visited[next_state]:
                    fringe.push((new_cost + penalty, new_path, next_state))

        return solution

    def longest_path(self, start_state: S, end_state: S, max_path_length: int = 1000, offset: float = 1000.0) -> tuple[float, list[D]]:
        self.start_state = start_state
        (revenue, path) = self.longest_path_min(end_state, offset=offset)
        if len(path) == 0:
            return (0.0, path)

        excluded: list[int] = [len(path)]
        best_revenue: float = revenue
        best_path: list[D] = path

        while True:
            (new_revenue, new_path) = self.longest_path_min(end_state, excluded_lengths=excluded, offset=offset)
            if len(new_path) == 0 or len(new_path) <= len(best_path):
                break
            if len(new_path) > max_path_length:
                break
            excluded.append(len(new_path))
            if new_revenue > best_revenue:
                best_revenue = new_revenue
                best_path = new_path

        return best_revenue, best_path

# ===========================================================================
# EXAMPLES / TESTS
# ===========================================================================
# -----------------------------------------------------------------------
# Example 1 -- simple weighted graph (Dijkstra / longest path)
# -----------------------------------------------------------------------
State_T1 = str
Cost_T1 = float
Decision_T1 = State_T1  # the decision is which state we will choose
class MyOptimizer(Optimizer[State_T1, Decision_T1]):
    G: dict[State_T1, list[tuple[Decision_T1, Cost_T1]]] = {
            's': [('u', 10.0), ('x', 5.0)],
            'u': [('v', 1.0), ('x', 2.0)],
            'v': [('y', 4.0)],
            'x': [('u', 3.0), ('v', 9.0), ('y', 2.0)],
            'y': [('s', 7.0), ('v', 6.0)],
        }

    def get_state(self, past_decisions: list[Decision_T1]) -> State_T1:
        return past_decisions[-1]

    def get_next_decisions(self, curr_state: State_T1) -> list[tuple[Decision_T1, Cost_T]]:
        return self.G.get(curr_state, [])

op: MyOptimizer = MyOptimizer()
solution: tuple[Cost_T1, list[Decision_T1]] = op.longest_path('s', 'v', max_path_length=4)
print("Longest path s->v:", solution)

# -----------------------------------------------------------------------
# Example 2 -- DP tutorial graph
# -----------------------------------------------------------------------
State_T2 = str
Cost_T2 = float
Decision_T2 = State_T2
class MyOptimizer2(Optimizer[State_T2, Decision_T2]):
    G: dict[State_T2, list[tuple[Decision_T2, Cost_T2]]] = {
            'a': [('b', 2.0), ('c', 4.0), ('d', 3.0)],
            'b': [('e', 7.0), ('f', 4.0), ('g', 6.0)],
            'c': [('e', 3.0), ('f', 2.0), ('g', 4.0)],
            'd': [('e', 4.0), ('f', 1.0), ('g', 5.0)],
            'e': [('h', 1.0), ('i', 4.0)],
            'f': [('h', 6.0), ('i', 3.0)],
            'g': [('h', 3.0), ('i', 3.0)],
            'h': [('j', 3.0)],
            'i': [('j', 4.0)],
        }

    def get_state(self, past_decisions: list[Decision_T2]) -> State_T2:
        return past_decisions[-1]

    def get_next_decisions(self, curr_state: State_T2) -> list[tuple[Decision_T2, Cost_T]]:
        return self.G.get(curr_state, [])

print('======= SHORTEST a->j =======')
op2: MyOptimizer2 = MyOptimizer2()
for solution in op2.shortest_path('a', 'j'):
    print(solution)
print('======= LONGEST  a->j =======')
print(op2.longest_path('a', 'j'))


# -----------------------------------------------------------------------
# Example 3 -- Rod Cutting
# You are given a rod of size n >0, it can be cut into any number of pieces k (k ≤ n).
# Price for each piece of size i is represented as p(i) and maximum revenue from a rod of size i is r(i)
# (could be split into multiple pieces). Find r(n) for the rod of size n.
# -----------------------------------------------------------------------
ROD_SIZE: int = 5

State_T3 = tuple[int, int]
Revenue_T3 = float
Decision_T3 = int  # decision os what length we cut

class RodCutting(Optimizer[State_T3, Decision_T3]):
    prices: list[tuple[Decision_T3, Revenue_T3]] = [(1, 1.0), (2, 5.0), (3, 8.0), (4, 9.0), (5, 10.0), (6, 17.0), (7, 17.0), (8, 20.0), (9, 24.0), (10, 30.0)]

    def get_state(self, past_decisions: list[Decision_T3]) -> State_T3:
        stage: int = len(past_decisions)
        remaining_size: int = ROD_SIZE - sum(d for d in past_decisions)
        if remaining_size <= 0:
            return (-1, 0)
        return (stage, remaining_size)

    def get_next_decisions(self, current_state: State_T3) -> list[tuple[Decision_T3, Cost_T]]:
        (stage, remaining_size) = current_state
        return [(size, rev) for size, rev in self.prices if size <= remaining_size]

print('======= ROD CUTTING =======')
op3: RodCutting = RodCutting()
print(op3.longest_path((0, ROD_SIZE), (-1, 0)))

# -----------------------------------------------------------------------
# Example 4 -- Capital Budgeting
# -----------------------------------------------------------------------
CAPITAL: int = 5
Cost_T4 = float
Stage_T4 = int
class State_T4(NamedTuple):
    stage: Stage_T4
    budget: Cost_T4
Decision_T4 = str  # decision is which project for the plant
Revenue_T4 = float
class Choice_T4(NamedTuple):
    cost: Cost_T4
    revenue: Revenue_T4
class CapitalBudgeting(Optimizer[State_T4, Decision_T4]):
    _choices: dict[Stage_T4, dict[Decision_T4, Choice_T4]] = {
            1: {'plant1-p1': (cost:0.0, revenue:0.0), 'plant1-p2': (cost:1.0, revenue:5.0), 'plant1-p3': (cost:2.0, revenue:6.0)},
            2: {'plant2-p1': (cost:0.0, revenue:0.0), 'plant2-p2': (cost:2.0, revenue:8.0), 'plant2-p3': (cost:3.0, revenue:9.0), 'plant2-p4': (cost:4.0, revenue:12.0)},
            3: {'plant3-p1': (cost:0.0, revenue:0.0), 'plant3-p2': (cost:1.0, revenue:4.0)},
        }

    def get_state(self, past_decisions: list[Decision_T4]) -> State_T4:
        stage: int = len(past_decisions)
        spent: float = 0.0
        for d in past_decisions:
            for choices in self._choices.values():
                if d in choices:
                    spent += choices[d][0]
        return stage, float(CAPITAL) - spent

    def get_next_decisions(self, current_state: State_T4) -> list[tuple[Decision_T4, Cost_T]]:
        (stage, budget) = current_state
        if stage not in self._choices:
            return []
        choices: dict[Decision_T4, Choice_T4] = self._choices[stage]
        return [(name, choice.revenue) for name, choice in choices.items() if choice.cost <= budget]

print('======= CAPITAL BUDGETING =======')
op4: CapitalBudgeting = CapitalBudgeting()
print(op4.longest_path((1, float(CAPITAL)), (3, 0.0)))

# -----------------------------------------------------------------------
# Example 5 -- Knapsack
# -----------------------------------------------------------------------
MAX_WEIGHT: int = 5
class Stage_T5(Enum):
    STAGE1 = 0
    STAGE2 = 1
    STAGE3 = 2
    END = 3
STAGE1 = Stage_T5.STAGE1
STAGE2 = Stage_T5.STAGE2
STAGE3 = Stage_T5.STAGE3
END = Stage_T5.END
class State_T5(NamedTuple):
    stage: Stage_T5
    remaining: int
class Decision_T5(NamedTuple):
    stage: Stage_T5
    quantity: int  # the quantity of items to choose
class Choice_T5(NamedTuple):
    weight: int
    benefit: int
class Knapsack(Optimizer[State_T5, Decision_T5]):
    items: dict[Stage_T5, Choice_T5] = {
          Stage1: (weight:2, benefit:65),
          Stage2: (weight:3, benefit:80),
          Stage3: (weight:1, benefit:30)
        }

    def get_state(self, past_decisions: list[Decision_T5]) -> State_T5:
        stage: Stage_T5 = past_decisions[-1].stage__tick__Next
        remaining: int = MAX_WEIGHT
        for decision in past_decisions:
            prev_stage: Stage_T5 = decision.stage
            qty: int = decision.quantity
            remaining -= qty * self.items[prev_stage].weight
        return stage, remaining

    def get_next_decisions(self, current_state: State_T5) -> list[tuple[Decision_T5, Cost_T]]:
        (stage, remaining) = current_state
        if stage == END:
            return []
        (weight, benefit) = self.items[stage]
        decisions: list[tuple[Decision_T5, Cost_T]] = []
        qty: int = 0
        while qty * weight <= remaining:
            decisions.append(((stage, qty), float(benefit * qty)))
            qty += 1
        return decisions

print('======= KNAPSACK =======')
op5: Knapsack = Knapsack()
print(op5.longest_path((STAGE1, MAX_WEIGHT), (END, 0)))

# -----------------------------------------------------------------------
# Example 6 -- Equipment Replacement
# -----------------------------------------------------------------------
class Decision_T6(Enum):
    BUY = 0
    SELL = 1
    KEEP = 2
    TRADE = 3
BUY = Decision_T6.BUY
SELL = Decision_T6.SELL
KEEP = Decision_T6.KEEP
TRADE = Decision_T6.TRADE
Cost_T6 = float
IRRELEVANT: int = -1
State_T6 = tuple[int, int]

class EquipmentReplacement(Optimizer[State_T6, Decision_T6]):
    maintenance_cost: dict[int, Cost_T6] = {0: 60.0, 1: 80.0, 2: 120.0}
    market_value: dict[int, Cost_T6] = {0: 1000.0, 1: 800.0, 2: 600.0, 3: 500.0}

    def __init__(self, offset: float = 0.0):
        super().__init__(offset)

    def get_state(self, past_decisions: list[Decision_T6]) -> State_T6:
        year: int = len(past_decisions)
        if year == 6:
            return (6, IRRELEVANT)
        age: int = 0
        for decision in past_decisions:
            if decision == KEEP:
                age = age + 1
            else:
                age = 1
        return (year, age)

    def get_next_decisions(self, current_state: State_T6) -> list[tuple[Decision_T6, Cost_T]]:
        (year, age) = current_state
        if age == IRRELEVANT:
            return []
        if year == 0:
            return [(BUY, self.maintenance_cost[0] + 1000.0)]
        if year == 5:
            return [(SELL, -self.market_value[age])]
        if age == 3:
            return [(TRADE, -self.market_value[age] + 1000.0 + self.maintenance_cost[0])]
        return [
                    (KEEP, self.maintenance_cost[age]),
                    (TRADE, -self.market_value[age] + 1000.0 + self.maintenance_cost[0]),
                ]

print('======= EQUIPMENT REPLACEMENT =======')
op6: EquipmentReplacement = EquipmentReplacement(offset=10000.0)
start_state: State_T6 = (0, 0)
end_state: State_T6 = (6, IRRELEVANT)
for solution in op6.shortest_path(start_state, end_state):
    print(solution)

# -----------------------------------------------------------------------
# Example 7 -- Romania map (A* with heuristic)
# -----------------------------------------------------------------------
State_T7 = str
Distance_T7 = float
Decision_T7 = str
class BookMap(Optimizer[State_T7, Decision_T7]):
    G: dict[State_T7, list[tuple[Decision_T7, Distance_T7]]] = {
            'arad':      [('sibiu', 140.0), ('timisoara', 118.0), ('zerind', 75.0)],
            'bucharest': [('giurgiu', 90.0), ('urzineci', 85.0), ('fagaras', 211.0), ('pitesti', 101.0)],
            'craiova':   [('rimnicu', 146.0), ('pitesti', 138.0), ('drobeta', 120.0)],
            'drobeta':   [('craiova', 120.0), ('mehadia', 75.0)],
            'eforie':    [('hirsova', 86.0)],
            'fagaras':   [('sibiu', 99.0), ('bucharest', 211.0)],
            'giurgiu':   [('bucharest', 90.0)],
            'hirsova':   [('eforie', 86.0), ('urzineci', 98.0)],
            'lasi':      [('neamt', 87.0), ('vaslui', 92.0)],
            'lugoj':     [('mehadia', 70.0), ('timisoara', 111.0)],
            'mehadia':   [('drobeta', 75.0), ('lugoj', 70.0)],
            'neamt':     [('lasi', 87.0)],
            'oradea':    [('zerind', 71.0), ('sibiu', 151.0)],
            'pitesti':   [('bucharest', 101.0), ('rimnicu', 97.0), ('craiova', 138.0)],
            'rimnicu':   [('pitesti', 97.0), ('sibiu', 80.0), ('craiova', 146.0)],
            'sibiu':     [('rimnicu', 80.0), ('arad', 140.0), ('oradea', 151.0), ('fagaras', 99.0)],
            'timisoara': [('lugoj', 111.0), ('arad', 118.0)],
            'urzineci':  [('bucharest', 85.0), ('vaslui', 142.0), ('hirsova', 98.0)],
            'vaslui':    [('urzineci', 142.0), ('lasi', 92.0)],
            'zerind':    [('arad', 75.0), ('oradea', 71.0)],
        }
    _heuristic: dict[State_T7, Distance_T7] = {
            'arad': 366.0, 'bucharest': 0.0, 'craiova': 160.0, 'drobeta': 242.0,
            'eforie': 161.0, 'fagaras': 176.0, 'giurgiu': 77.0, 'hirsova': 151.0,
            'lasi': 226.0, 'lugoj': 244.0, 'mehadia': 241.0, 'neamt': 234.0,
            'oradea': 380.0, 'pitesti': 100.0, 'rimnicu': 193.0, 'sibiu': 253.0,
            'timisoara': 329.0, 'urzineci': 80.0, 'vaslui': 199.0, 'zerind': 374.0,
        }

    def get_state(self, past_decisions: list[State_T7]) -> State_T7:
        return past_decisions[-1]

    def get_next_decisions(self, current_state: State_T7) -> list[tuple[Decision_T7, Cost_T]]:
        return self.G.get(current_state, [])

    def get_heuristic_cost(self, city: State_T7) -> float:
        return self._heuristic.get(city, 0)

op7: BookMap = BookMap()
print('======= ROMANIA MAP: oradea -> bucharest =======')
for solution in op7.shortest_path('oradea', 'bucharest'):
    print(solution)
