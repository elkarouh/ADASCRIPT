procedure P is
begin
  Call
    (A => 1,
     V => Make (X => 1,
                Y => 2),
                 -- about Make: stays under its arguments
     -- about B
     B => 2);
end P;
