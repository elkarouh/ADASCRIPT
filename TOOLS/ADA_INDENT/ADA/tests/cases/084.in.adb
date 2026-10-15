function Code (Name : String) return String is
begin
if    Name = "XCD Airport" then return "X";
elsif Name = "FL Scenario" then return "F";
else return "";
end if;
end Code;
