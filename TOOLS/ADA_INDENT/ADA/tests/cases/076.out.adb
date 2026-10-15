procedure P is
begin
  if Force then
    if (not Is_None (A)
          and not Is_None (B))
      and then -- no compare when either is None
      Compare (A, B) /= Order.Equal
    then
      Set_Distance (C, A);
    end if;
  end if;
end P;
