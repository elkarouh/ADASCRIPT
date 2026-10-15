package body P is
  type A is null record;
  type B is record F : Integer; end record;
  Msg : constant String := "end record here";
  Next_Decl : Integer;
end P;
