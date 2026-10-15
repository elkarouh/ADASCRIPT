-- Regression fixture for ada_indent's recovery from INVALID code (fixpoint,
-- also from flattened input). Each procedure below holds one error: a stray
-- 'end if', an unclosed '(', an 'if' without 'then', a stray 'end;' and a
-- mangled header. Lines inside a broken procedure may be off; the point is
-- that every After_N procedure following one is indented as if nothing had
-- happened - the damage stays inside the construct that holds the error.
package body Broken is
  procedure Stray_End_If is
  begin
    null;
    end if;
  end Stray_End_If;
  procedure After_1 is
  begin
    null;
  end After_1;
  procedure Unclosed_Paren is
    X : Integer := F (1,
  begin
    null;
  end Unclosed_Paren;
  procedure After_2 is
  begin
    null;
  end After_2;
  procedure Missing_Then is
  begin
    if X > 0
      Y := 1;
    end if;
  end Missing_Then;
  procedure After_3 is
  begin
    null;
  end After_3;
  procedure Stray_End is
  begin
  end;
  null;
  end Stray_End;
  procedure After_4 is
  begin
    null;
  end After_4;
  procedure Mangled_Header (X : Integer) is (
begin
  null;
  end Mangled_Header;
  procedure After_5 is
  begin
    null;
  end After_5;
end Broken;
