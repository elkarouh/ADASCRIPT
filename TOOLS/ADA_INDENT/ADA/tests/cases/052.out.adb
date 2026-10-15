package body P is
  function Is_Valid_Char (The_Char         : in Character;
                          Allow_Underscore : in Boolean) return Boolean is
    (Is_Upper (The_Char) or else (Allow_Underscore and The_Char = '_'));
  procedure Q is
  begin
    null;
  end Q;
end P;
