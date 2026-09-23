-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Generic formal parts, private parts, abstract/with-private declarations,
-- asynchronous select ('then abort'), and headers whose 'is', 'return',
-- 'loop' or 'then' sits alone on the next line.
--
generic
  type T is private;
  with procedure Visit (X : T);
package G is
  procedure Run;
  function F return T is abstract;
  type D is new Base with private;
  type E is new Base with null record;
  type Lim is limited private;
private
  type D is new Base with record
    Y : Integer;
  end record;
end G;

package body G is

  procedure Run
  is
  begin
    select
      delay 5.0;
    then abort
      Long_Computation;
    end select;
  end Run;

  procedure Swap (A, B : in out T)
  is
    Tmp : T := A;
  begin
    A := B;
    B := Tmp;
  end Swap;

  function Max (A, B : T)
    return T
  is
  begin
    return (if A > B then A else B);
  end Max;

  procedure Loops is
  begin
    for I in reverse 1 .. 10
    loop
      null;
    end loop;
    while Cond
    loop
      null;
    end loop;
    if A
    then
      null;
    end if;
  end Loops;

end G;
