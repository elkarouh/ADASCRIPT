-- Regression fixture for ada_indent: must be a fixpoint (re-indenting it
-- changes nothing), and must also come back unchanged from a copy with all
-- leading whitespace stripped. One-line constructs, statement labels, literals
-- holding keywords, mixed-case keywords, spaced-out closers, select/accept,
-- protected entries, extended return, named blocks and loops, handlers.
--
with Ada.Text_IO; use Ada.Text_IO;
package body Torture is

  type Rec is record X : Integer; end record;
  type Acc is access procedure (X : Integer);
  type Color is (Red, Green, Blue);
  procedure Nothing is null;
  procedure Later is separate;
  package Inst is new Gen (X => 1);
  Semi : constant Character := ';';
  Open : constant Character := '(';
  Text : constant String := "end if; begin ( is loop";

  function Qual return Character is
  begin
    return Character'('(');
  end Qual;

  procedure One_Liners is
  begin
    if A then B; elsif C then D; else E; end if;
    loop null; end loop;
    case X is when others => null; end case;
    X := 1; Y := 2;
    declare Z : Integer := 0; begin null; end;
    <<Lbl>>
    for I in 1..10 loop Put (I'Image); end loop;
  end One_Liners;

  procedure Mixed_Case is
  BEGIN
    IF A THEN
      NULL;
    End If;
    While X loop
      exit when Y;
    END LOOP;
  eNd Mixed_Case;

  procedure Spaced is
  begin
    if A then
      null;
    end if ;
    loop
      null;
    end   loop ;
  end Spaced ;

  task body Worker is
  begin
    select
      accept Start do
        null;
      exception
        when others =>
          null;
      end Start;
    or
      delay 1.0;
    else
      null;
    end select;
  end Worker;

  protected body Lock is
    entry Seize when not Busy is
    begin
      Busy := True;
    end Seize;

    entry Wait (Requests : Request_List_T;
                Index    : out Index_T)
      when True is -- the barrier on its own line, a comment after 'is'
      Oldest : Length_T := 0;
    begin
      Scan:
      for I in Index_T loop
        if Pool (I).Requests = Requests then
          Index := I;
          return;
        end if;
      end loop Scan;
      requeue Retry;
    end Wait;
  end Lock;

  function Build return Rec is
  begin
    return R : Rec do
      R.X := 1;
    exception
      when others =>
        R.X := 0;
        raise;
    end return;
  end Build;

  procedure Blocks is
  begin
    Blk : declare
      V : Integer := 0;
    begin
      null;
    end Blk;
    Outer : for I in 1 .. 3 loop
      exit Outer when I = 2;
    end loop Outer;
  exception
    when Constraint_Error =>
      null;
    when others =>
      raise;
  end Blocks;

  procedure Comments is -- then is begin loop
  begin
    if A then -- loop
      null; -- end if;
    end if; -- begin
  end Comments;

end Torture;
