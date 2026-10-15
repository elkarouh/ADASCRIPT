package body P is
  function Stack_Top (S : Stack.T) return Position_T
  is (Stack.Element (S, Stack.Length (S)));
  function Stack_Base (S : Stack.T) return Position_T
  is
    (Stack.Element (S, 1));
  procedure Q is
  begin
    null;
  end Q;
end P;
