procedure P is
begin
  if A
    and then Take_Off_Time (X)
    -- a comment
      >= Take_Off_Time (Y)
  then
    null;
  end if;
end P;
