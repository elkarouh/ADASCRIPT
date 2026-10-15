package P is
  Curtains : constant T
    := (if E
        then (A => P,
              B => Q)
        -- note one
        -- note two
        else (A => R,
              B => S));
end P;
