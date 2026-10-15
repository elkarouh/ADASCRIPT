function Get_Minimum_Delay
  (Office : T;
   Clock_Shift_Conditions : Departure.Clock_Shift_Conditions_T)
  return Time.Duration_T is
  (Minimum_Take_Off_Time (Office)
     - Office.ETOT);
procedure Force_Inform is
begin
  Print;
end Force_Inform;
