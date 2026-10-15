-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Several openers or closers on one line: 'end if; end loop;', 'null; end
-- loop; end if;', 'if A then if B then', whole subprograms on one line, and
-- case alternatives with their body beside the arrow.
--
package body Dense is

  procedure Closers is
  begin
    for I in 1 .. 3 loop
      if A then
        null;
      end if; end loop;
    Next;
    loop
      if B then null; end if;
      exit;
    end loop;
    if C then
      loop
        null; end loop; end if;
    Done;
  end Closers;

  procedure Openers is
  begin
    if A then if B then
        null;
      end if;
    end if;
    Next;
  end Openers;

  procedure Short is begin null; end Short;

  function Expr return Boolean is (True);

  procedure Case_Stmt is
  begin
    case K is
      when A => null;
      when B | C =>
        Do_It;
      when others => raise Program_Error;
    end case;
  end Case_Stmt;

end Dense;
