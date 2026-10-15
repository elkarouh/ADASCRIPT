procedure G is
Origin : constant T := (case E is
when A => X,
when others => Y);
function F return T is
(if C
then P
else Q);
Id : constant T := Z;
begin
null;
end G;
