package P is
  X : T
    := (if A
        then (others => True)
        else (K1
                => V1,
              K2
                => V2));
end P;
