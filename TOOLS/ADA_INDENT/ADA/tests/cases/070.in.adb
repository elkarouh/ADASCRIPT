procedure P is
begin
if Local_Mode.Activated then
case Time.Compare (A, B) is
when Order.Smaller => return "Live";
when Order.Equal => if Time.Control.Is_Controlled then
return "Simul";
else
return "Live";
end if;
end case;
end if;
return "Live";
end P;
