procedure P is
begin
if C then X; end if;
Y := (if A then B else C);
if Is_Set (A)
and then Is_Set (B)
then
Z;
end if;
end P;
