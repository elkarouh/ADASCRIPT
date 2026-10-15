package body P is
  procedure Inst
    is new Gen (Param);
  task type T (X : Boolean) with
    Storage_Size => 64
  is
    entry E;
  end T;
end P;
