-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- An argument list opening a continuation line nests one level past the line
-- that holds the call's name - also when that line is itself a continuation
-- ('and then not F' / 'or else not F' above '(Args)').
package body Calls is

  procedure Q is
    Freeze_Present : constant Boolean
      := not Debug.Trace (Disable_Freeze)
        and then not Constraints_Pkg.Elements_Present
          (Constraints,
           What => Constraints_Pkg.Freeze_Outside_Only);
    V : Integer
      := Compute
        (A,
         B);
  begin
    Foo
      (A,
       B);
    X := Bar
      (C);
  end Q;

  function Created_Before return Boolean is
  begin
    return Local_Ancestor = Baseline
      or else not Env_Baseline.Is_Ancestor_Same_Cycle
        (Ancestor => Local_Ancestor, Offspring => Baseline);
  end Created_Before;

end Calls;
