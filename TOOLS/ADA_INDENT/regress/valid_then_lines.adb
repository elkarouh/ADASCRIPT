-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- A multi-line if/elsif condition whose 'then' starts a line and is followed
-- by a statement on that same line ('then return X;'): the 'then' aligns with
-- its 'if'/'elsif', and the ';' after it does not end the condition early.
package body Then_Lines is
  function Image (Value : T) return String is
  begin
    if Base_Image (Base_Image'First) = '(' then
      return Base_Image;
    elsif Value.Seg_Kind not in Matching_Route_T
    then return Base_Image; -- keep segment image, there is no associated route info
    else
      null;
    end if;
    if A
      and then B
    then
      null;
    elsif C
    then
      null;
    end if;
    if A
    then return X;
    end if;
    return Y;
  end Image;
end Then_Lines;
