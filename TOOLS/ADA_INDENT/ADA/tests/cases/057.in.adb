package body P is
overriding function F return Integer is
R : Integer := 0;
begin
return R;
end F;
overriding procedure Set (X : in T) is
begin
null;
end Set;
end P;
