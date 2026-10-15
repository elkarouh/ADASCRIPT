procedure P is
begin
if Length (L) = 0 then return; end if;
Measure.Create (X);
if A then B; elsif C then D; end if;
Measure.Create (Y);
exception
when others =>
raise;
end P;
