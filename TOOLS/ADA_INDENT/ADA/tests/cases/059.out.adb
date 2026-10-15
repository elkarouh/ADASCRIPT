package body P is
  function F return Integer
  is
    R : Integer := 0;
  begin
    return R;
  end F;
  task type W (Flag : Boolean) with
    Storage_Size => 64
  is
    entry E;
  end W;
end P;
