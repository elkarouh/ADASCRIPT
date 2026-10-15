package body P is
overriding function Impact_Is_Editable (A : in T) return Boolean is
(A.Operation in Create_Slot | Force_CTO);
not overriding function Eq (L : in T;
R : in T) return Boolean is
(L.Id = R.Id);
procedure Q is
begin
null;
end Q;
end P;
