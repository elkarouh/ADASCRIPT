# DB_REMEDIATION: remediation as graph search

Demo of the idea in Stripe's article
[How Stripe uses graph search and state machines to auto-remediate a global
database fleet](https://stripe.dev/blog/how-stripe-uses-graph-search-and-state-machines-to-auto-remediate-a-global-database-fleet).

## The article in short

- **Problem.** About 2,000 MongoDB shards. V1 was a fixed-order chain of
  plugins ("fix votes", "fix priority", "rebuild node"). Plugins had circular
  dependencies, multi-failure shards matched no ordering and paged a human,
  safety checks were duplicated per layout (a week to onboard a layout), and
  cancelled workflows left shards in states no plugin handled. 124 pages for
  misconfigured shards and 32 for complicated node-down cases in six months.
- **Reframing.** State = per-node attributes (votes, priority, hidden) plus
  shard properties (quorum, oplog sizes, regions). Edges = atomic operations
  (add/remove vote or priority, hide, rebuild, resize oplog). Goal = the
  shard's source of truth. Invalid states (even votes, no healthy voting
  majority, priority without a vote) are pruned, so quorum holds at every step.
- **BFS first**, shortest valid operation sequence. It discovers orderings no
  hand-written runbook had ("fix vote and priority first, then rebuild").
- **Simulation = execution.** A `CommonContext` hides Temporal and real I/O
  behind one interface, so the planner simulates thousands of paths in
  memory with the same business logic that runs in production.
- **Dijkstra second.** Edge weight = misconfiguration(state) x estimated
  time(op) (config 3, oplog 19, rebuild 101), so cheap exposure-reducing
  fixes go before slow ones. If the goal is unreachable, return a path to the
  least misconfigured state (partial remediation) and page for the rest.
  Misconfiguration is a sum of named, composable rules.
- **Results.** About 30% fewer pages, about 12 shard-degraded days per year
  removed, zero code per new layout, cancelled workflows resume from wherever
  they stopped. "Runbooks encode known recovery procedures; a state machine
  discovers novel ones."

## The demo

`db_remediation.ady` models a 3-node replica set and reuses what the repo has:

| Article | Demo | Reused code |
|---|---|---|
| BFS planner | `BreadthPlanner` | `EXAMPLES/state_search.ady` `StateSearcher.search` |
| Dijkstra with weights | `WeightedPlanner` | `EXAMPLES/shortest_path.ady` `Minimizer.shortest_path` |
| Least-misconfigured state | `Sweeper` (a `StateSearcher` that records scores) | `state_search.ady` |
| Shared simulate/execute | one `apply()` used by planners and `execute()` | |
| Composable scoring | `rule_scores()`: node down, vote mismatch, priority mismatch | |

Scenarios: (1) a lost vote plus a down node, planned with BFS and with
Dijkstra; (2) the same shard with an unrebuildable node, giving a partial
plan that stops at the least misconfigured reachable state; (3) two faults on
different nodes.

Run it:

    python3 TO_NIM/ady2nim.py c -r EXAMPLES/DB_REMEDIATION/db_remediation.ady

Simplifications: three fixed nodes, no hidden flag, oplog or regions; one
cost per operation kind.
