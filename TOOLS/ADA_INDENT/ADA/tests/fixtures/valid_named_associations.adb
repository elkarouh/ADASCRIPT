-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Named associations whose value spills past '=>' onto the next line, where
-- that value is itself a parenthesised case expression: the item after it
-- must return to the item column. Also a choice list wrapped inside an
-- aggregate, whose '|' lines go one level past the item column.
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

  -- A choice list wrapped inside an aggregate: the '|' lines continue the
  -- association one level past its item column (a decision, not an accident).
  Validate_Of_Type : constant array (Measure_Type.T) of Boolean
    := (Regulation_Measure | Regulation_Subperiod | Flow_Measure
          | Address_Measure | CDM_Measure
          | FAAS_Updates_T => False,
        Capacity_Updates_T | Sector_Update => True);

  -- Comments among the items of an enumeration, including after the last
  -- item (no comma): they stay at the item column, like the ');' below.
  type Segment_CDR_T is
    (None,
     --%   <li> None available
     Gap,
     CDR_2, -- No longer used operationally
     CDR_3,
     --%   <li> CDR3
     Arrival_Band
     --%   <li> Arrival_Band
     -- Terminal procedure categories
     );

  procedure Call is
  begin
    Put (Item  =>
           (if Flag then "yes" else "no"),
         Width => 10);
  end Call;

end Associations;
