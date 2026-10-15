procedure P is
begin
  if Outer then Z;
    if C then X; end if;
    Msg := "end if";
    Y := (if A then B else C);
    Next_Statement;
  end if;
end P;
