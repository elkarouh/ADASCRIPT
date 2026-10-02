(module
  (memory 3)
  (global $__stack_pointer (mut i32) (i32.const 196608))
  (func $__dup_i32 (param i32) (result i32 i32)
    (local.get 0) (local.get 0))
  (func $__swap_i32 (param i32) (param i32) (result i32 i32)
    (local.get 1) (local.get 0))
  (func $main
    (result i32)
    global.get $__stack_pointer ;; prelude: adjust stack pointer
    i32.const 0
    i32.sub
    global.set $__stack_pointer
    i32.const 1
error on line 1: unterminated multi-line comment
exit 1
