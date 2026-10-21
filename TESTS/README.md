# TESTS

Pure regression tests: `test_*.ady` programs that pin one language or transpiler
behaviour, with the small modules they import (`mr_*.ady`, `NIMPORT_TEST/`,
`ELEMENT_FIELD/`, `hand_speeds.nim`). `make test` builds and runs them; they are not
meant to be read as examples. The programs in `EXAMPLES/` itself are the examples.

`test_shortest_path.ady` and `test_state_search.ady` stay in `EXAMPLES/`, beside the
library programs they exercise.
