task body T is
begin
  select
    when G1 =>
      accept E1;
  or
    when G2 =>
      accept E2;
  end select;
end T;
