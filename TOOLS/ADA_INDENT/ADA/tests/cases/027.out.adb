procedure P is
begin
  Mask (K)
    := (Mask (K) or Initially_Flagged)
      and not Initially_Not_Interesting
      and not Clear_Aspects;
end P;
