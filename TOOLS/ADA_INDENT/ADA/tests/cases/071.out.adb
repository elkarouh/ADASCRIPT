procedure P is
begin
  case K is
    when A => Foo (X);
    when B => for I in 1 .. 3 loop
        Put (I);
      end loop;
    when others => null;
  end case;
end P;
