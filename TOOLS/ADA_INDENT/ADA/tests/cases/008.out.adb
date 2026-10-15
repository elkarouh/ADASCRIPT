procedure P is
begin
  R := (if Cycle_Of (X)
          /= Cycle_Of (Y)
        then Empty
        else Full);
  Next_Statement;
end P;
