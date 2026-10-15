procedure P is
begin
  if First
    and then (Ready
                or else (Sent (Data)))
    or else (Status = No_Deviation
               -- a note
               and then Has_Message (Info))
  then
    null;
  end if;
end P;
