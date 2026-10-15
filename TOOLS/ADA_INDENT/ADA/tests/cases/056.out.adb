package body P is
  overriding function Image return String is
    (Compute (A));
  not overriding function Eq (L : in T;
                              R : in T) return Boolean is
    (L.Id = R.Id);
  procedure Q is
  begin
    null;
  end Q;
end P;
