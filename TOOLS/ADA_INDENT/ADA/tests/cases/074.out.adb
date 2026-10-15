function Outer (Args : Reader.T) return Boolean is
  procedure Report (Message : String) is begin
    IO.Report_Error
      (Trace,
       "Response: " & Message);
  end Report;
begin
  return True;
end Outer;
