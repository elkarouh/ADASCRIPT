package P is
  X : constant Boolean
    := (A
          and then B)
      -- comment one
      -- comment two
      or else (C
                 and then D)
      -- comment three
      or else not E;
end P;
