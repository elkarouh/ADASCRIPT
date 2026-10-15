package P is
  Any_Concerned : constant Boolean
    := (for some Reg of All_Regs (1 .. N) =>
          not Reg.Excluded);
end P;
