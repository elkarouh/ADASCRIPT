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
    i32.const 5
    i32.sub
    global.set $__stack_pointer
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 97
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 10
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 92
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 39
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 65
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 65
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 0
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    call $__dup_i32
    i32.const 63
    i32.store8
    i32.load8_s
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load s
    i32.const 1
    i32.add
    call $__dup_i32
    i32.const 65536
    i32.store
    i32.load
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load s
    i32.const 1
    i32.add
    call $__dup_i32
    i32.const 65572
    i32.store
    i32.load
    drop ;; discard statement expr result
    global.get $__stack_pointer ;; load c
    i32.const 0
    i32.add
    i32.load8_s
    global.get $__stack_pointer ;; fixup stack pointer before return
    i32.const 5
    i32.add
    global.set $__stack_pointer
    return
    unreachable
  )
  (export "main" (func $main))
  (data $.rodata (i32.const 65536) "plain\09tab\0anl A\04 A\07 \22q\22 \5c ? \07\08\0c\0b end\00joined strings\00")
)
exit 0
