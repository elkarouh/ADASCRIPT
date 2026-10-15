procedure P is
begin
  Call
    (V => Make (X => 1,
                Y => 2),
                 -- about Make: stays under its arguments
     B => 2);
end P;
