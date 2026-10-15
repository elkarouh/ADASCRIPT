package body Parent.Child is
procedure P is
X : Integer := 0;
begin
Outer :
for I in 1 .. 10 loop
Inner : while X > 0 loop
X := X - 1;
end loop Inner;
end loop Outer;
case X is
when 1 =>
null;
end case;
end P;
end Parent.Child;
