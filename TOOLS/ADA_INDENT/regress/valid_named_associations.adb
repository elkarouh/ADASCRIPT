-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Named associations whose value spills past '=>' onto the next line, where
-- that value is itself a parenthesised case expression: the item after it
-- must return to the item column.
package body Associations is

  function Optimal return Distance.T is
    (Performance.Optimal_Distance
     (Obj      => Obj.Data,
      Phase    => Phase_Of (Start_Side),
      Start_FL =>
        (case Start_Side is
           when Side.First =>
             Obj.Bound (Start_Side).Level_At (Info_Kind.Restriction_FL),
           when Side.Last => Level_Cap),
      End_FL   =>
        (case Start_Side is
           when Side.First => Level_Cap,
           when Side.Last  =>
             Obj.Bound (Start_Side).Level_At (Info_Kind.Restriction_FL))));

  procedure Call is
  begin
    Put (Item  =>
           (if Flag then "yes" else "no"),
         Width => 10);
  end Call;

end Associations;
