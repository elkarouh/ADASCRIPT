declare
X : Integer;

begin
X := 1;
exception
when Constraint_Error =>
X := 0;
end;
