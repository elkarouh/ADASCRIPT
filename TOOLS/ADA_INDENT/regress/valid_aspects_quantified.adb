-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Aspect specifications whose value spills past its '=>' onto the next line,
-- told apart from case alternatives and handlers that also end in '=>'; and
-- quantified expressions whose predicate starts beside the arrow or below it.
package body Aspects is

  subtype Reason_Subset_T is Reason_T
    with Static_Predicate =>
      Reason_Subset_T in Base_Reason_T | Violates_Availability;

  function F (X : Integer) return Boolean
    with Pre =>
      X > 0
        and then X < 10,
    Post =>
      -- the result
      F'Result = (X > 1);

  procedure Q
    with Inline;

  type Even is new Integer
    with Dynamic_Predicate =>
      Even mod 2 = 0;

  function Has_Orphan return Boolean is
    (for some S in Side.T => Pair (S).Kind = Location_Kind.Point
       and then Orphan_Point (Info_Pair (S)));

  Any : constant Boolean
    := (for some Reg of All_Regs (1 .. N) =>
          not Reg.Excluded
            and then Reg.Active);

  Sum : constant Integer := (for I in 1 .. 3 => I * 2);

  procedure R is
  begin
    case X is
      when 1
          | 2 =>
        null;
      when others =>
        null;
    end case;
  exception
    when Constraint_Error
        | Program_Error =>
      null;
    when E : others =>
      null;
  end R;

end Aspects;
