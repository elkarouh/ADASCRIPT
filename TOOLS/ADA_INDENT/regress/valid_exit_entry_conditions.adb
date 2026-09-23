-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- A condition on its own 'when' line continuing 'exit Name' or an entry
-- header: it is not a case alternative, and its 'and then' continuations
-- sit one level past the 'when'.
package body Conditions is

  function First return Report_T is
    Item : Report.T;
  begin
    Scan:
    for I in 1 .. Length (List) loop
      Item_Distance := Lower_Bound_Of (List, I);
      exit Scan
        when Towards_Side = Side.First
          and then (Item_Distance > From or else (not Inclusive and then Item_Distance = From));
      Item := Value (List, I);
    end loop Scan;
    return Result;
  end First;

  protected body Lock is
    entry Wait (X : Integer)
      when Ready
        and then not Busy is
    begin
      null;
    end Wait;
  end Lock;

  procedure Q is
  begin
    loop
      exit when A
        and then B;
      exit Outer when A;
      exit Outer
        when A or B;
    end loop;
  end Q;

end Conditions;
