# TESTS

Pure regression tests: `test_*.ady` programs that pin one language or transpiler
behaviour, with the small modules they import (`mr_*.ady`, `NIMPORT_TEST/`,
`ELEMENT_FIELD/`, `hand_speeds.nim`). `make test` builds and runs them; they are not
meant to be read as examples. The programs in `EXAMPLES/` itself are the examples.

`shortest_path_demo.ady` and `state_search_demo.ady` are showcases, not tests, and live in `EXAMPLES/`;
the libraries they show are in `TO_NIM/STDLIB/`.
