package body P is
  package Inst is
    new Gen (A => B);
  procedure R is
  begin
    null;
  end R;
end P;
