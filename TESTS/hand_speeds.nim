## A Nim module written by hand, for test_nim_module.ady: a distinct type and
## a routine that takes it.
type Speed_T* = distinct float

proc double*(s: Speed_T): Speed_T = Speed_T(float(s) * 2.0)
proc faster*(s: Speed_T, by: Speed_T = Speed_T(1.0)): Speed_T = Speed_T(float(s) + float(by))
