procedure P is
begin
  if Debug.Trace (FRA_Visited_Trace)then
    Report (A);
  end if;
  for I in Each (List)loop
    Report (I);
  end loop;
  while Check (X)loop
    Step;
  end loop;
end P;
