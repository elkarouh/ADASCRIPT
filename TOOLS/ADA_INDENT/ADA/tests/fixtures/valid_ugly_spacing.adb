-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Valid but ugly spacing: glued punctuation (')is', ')then', ';end'), tabs
-- between tokens, trailing comments full of keywords, and keywords inside
-- string and character literals. None of it may move a line.
package body Ugly is

  procedure P(X:Integer;Y:Integer)is
    S : constant String := "if then loop begin end;";
    C : constant Character := '(';
  begin
    if(X>Y)then
      Put_Line("end if;");
    elsif X=Y then Put_Line(")is"); -- then begin loop
    else
      null;
    end if;
    for	I	in	1..X	loop
      Put(I'Image);end loop;
    case X is
      when 1=>null;
      when others=>
        declare
          Z:Integer:=0;
        begin
          Z:=Z+1;
        end;
    end case; -- end case; end if; end loop;
  end P;

  function F(A:Integer)return Integer is(A+1);

  function G(A:Integer)return Boolean
  is
  begin
    return A>0
      and then A<10;
  end G;

end Ugly;
