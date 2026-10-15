package body P is
subtype Small_T is
Integer range 1 .. 10;
function Area (Shape : in T;
Scale : in Float) return Float is
(Shape.W * Shape.H * Scale);
procedure Q is
begin
case K is
when A => null;
end case;
end Q;
end P;
