package P is
type Simple is
record
X : Integer;
end record;
-- after simple
type Mode is (A, B);
type Var (M : Mode := A) is
record
case M is
when A =>
X : Integer;
when B =>
Y : Float;
end case;
end record;
-- after variant
Z : Integer;
end P;
