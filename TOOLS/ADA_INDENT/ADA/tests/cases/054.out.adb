package body P is
  procedure Outer is
    procedure Leaked is
    begin
      null;
  end Outer;
  procedure After is
  begin
    null;
  end After;
end P;
