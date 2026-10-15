function F return Boolean is
begin
  return New_OBT > Old_OBT
    -- comment one
    -- comment two
    and (Departure.Earliest_TTOT = None
           -- inner comment
           or else New_OBT > X);
end F;
