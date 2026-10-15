procedure Hello is
  X : Integer := 0;
begin
  if X = 0 then
    Put_Line ("zero");
  elsif X > 0 then
    Put_Line ("pos");
  else
    Put_Line ("neg");
  end if;
  for I in 1 .. 10 loop
    X := X + I;
  end loop;
  case X is
    when 0 =>
      null;
    when others =>
      Put_Line ("other");
  end case;
end Hello;
