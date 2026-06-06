-- ada_indent_sample_test.adb  --  exercises the ada_indent requirements
--
-- Feed this file to ada_indent; the output must be byte-for-byte identical.
-- The subunit (§2.7) appears at the end as a separate compilation unit.

------------------------------------------------------------------------
--  PACKAGE SPEC
------------------------------------------------------------------------

package Regression_Tests is

  -- ── §2.3 inline record type ───────────────────────────────────────────────
  type Point is record
    X : Float;
    Y : Float;
  end record;

  -- ── §2.3 'type T is' on its own line (simple record) ─────────────────────
  type Simple is
    record
      X : Integer;
    end record;

  -- ── §3 subtype declaration split across lines ──────────────────────────────
  subtype Small_Int is
    Integer range 1 .. 10;
  Next_Field : Integer;

  type Mode_T is (A, B);

  -- ── §2.3 variant record on two lines ─────────────────────────────────────
  type Var_T (M : Mode_T := A) is
    record
      case M is
        when A =>
          X : Integer;
        when B =>
          Y : Float;
      end case;
    end record;

  -- ── §2.4 task type with aspect-clause; standalone 'is' ───────────────────
  task type Worker_T (Flag : Boolean) with
    Storage_Size => 64 * 1024
  is
    entry Start;
    entry Stop;
  end Worker_T;

  -- ── §3 declaration continuation ──────────────────────────────────────────
  Curtains : constant Alternatives_Profiles_T
    := Whatever_But_Very_Long;
  Long_Sum : Integer := A
    + B
    + C;

  -- ── §3, §4.2 ':= call' then '(args)' on next line ───────────────────────
  Set_Info : constant T
    := Get
      (Query => Q,
       Object => O);

  -- ── §3 operator-led term continuation ────────────────────────────────────
  Delta_X : constant Duration_T
    := Take_Off_Time (Curtains (Normal) (RTFM))
      - Take_Off_Time (Flight, FTFM);

  -- ── §3 'and not'/'or not' as value operators ─────────────────────────────
  Clean_Mask : constant Mask_T
    := (Base_Mask or Initially_Flagged)
      and not Initially_Not_Interesting
      and not Clear_Aspects;

  -- ── §3 'or else' continuation in value expression ────────────────────────
  Flag_A : constant Boolean
    := True
      or else False;

  -- ── §3 'and (' continuation ───────────────────────────────────────────────
  Both : constant Boolean
    := (A = B)
      and (C = D);

  -- ── §3, §7.1 multi-line boolean expression with interleaved comments ──────
  Complex : constant Boolean
    := (A
          and then B)
      -- comment one
      -- comment two
      or else (C
                 and then D)
      -- comment three
      or else not E;

  -- ── §3 quantified expression ──────────────────────────────────────────────
  Any_Concerned : constant Boolean
    := (for some Reg of All_Regs (1 .. N) =>
          not Reg.Excluded);

  -- ── §3, §4.4 ':= (if A then (agg) else (agg))' ──────────────────────────
  Derived : T
    := (if A
        then (others => True)
        else (K1
                => V1,
              K2
                => V2));

  -- ── §4.4 if-expr 'else …)' continues the surrounding statement ───────────
  Full_Name : constant String := A
    & (if C
       then "0"
       else Trim (X))
    & "_";

  -- ── §4.3 '(' continuing unfinished expression inside outer paren ──────────
  Coord_Fix : constant Def_Location.T :=
    (if C
     then (Def_Location.GPS, X => Y)
     else (Def_Location.ICAO_Aerodrome,
           Aerodrome => Def_Aerodrome.Convert
             (Env_Location.Value (A))));

  -- ── §7.3 comment between branches of parenthesised if-expression ──────────
  Curtains_Val : constant T
    := (if E
        then (A => P,
              B => Q)
        -- note one
        -- note two
        else (A => R,
              B => S));

private

  -- ── §2.3 private part ─────────────────────────────────────────────────────
  Origin : constant Point := (0.0, 0.0);

end Regression_Tests;

------------------------------------------------------------------------
--  PACKAGE BODY
------------------------------------------------------------------------

package body Regression_Tests is

  -- ── §7.4 comment before begin; comment after deferred function header ──────

  procedure P_Empty is
    -- before begin
  begin
    null;
  end P_Empty;

  function F_Deferred return T is
    -- doc one
    -- doc two
    X_Loc : T := 0;
  begin
    null;
  end F_Deferred;

  -- ── §2.5 expression function; no block frame pushed ──────────────────────

  function Image return String is
    (Compute (A, B'Image));
  procedure After_Image is
  begin
    null;
  end After_Image;

  -- ── §2.1, §2.2 basic statements; declare block; labeled constructs ────────

  procedure Hello is
    X : Integer := 0;
  begin
    -- §2.2 declare block with exception handler
    declare
      Y : Integer;

    begin
      Y := 1;
    exception
      when Constraint_Error =>
        Y := 0;
    end;

    -- §2.1 if/elsif/else
    if X = 0 then
      Put_Line ("zero");
    elsif X > 0 then
      Put_Line ("pos");
    else
      Put_Line ("neg");
    end if;

    -- §2.2 labeled declare block and labeled for loop
    Log_Changes:
    declare
      Z : Integer;
    begin
      Find_Model : -- pick the model
      for M in reverse T loop
        null;
      end loop Find_Model;
    end Log_Changes;

    -- §2.1 for loop and case
    for I in 1 .. 10 loop
      X := X + I;
    end loop;
    case X is
      when 0 =>
        null;
      when others =>
        Put_Line ("other");
    end case;
  end Hello;

  -- ── §4.1 paren-continuation aligns under first item ──────────────────────

  procedure Test_4 is
  begin
    Set (A => 1,
         B => 2);
  end Test_4;

  -- ── §5 multi-line if/elsif conditions ────────────────────────────────────

  procedure Test_6 is
  begin
    if A = 1
      and then B = 2
      and then C = 3
    then
      null;
    elsif D = 4
      and then E = 5
    then
      null;
    end if;
  end Test_6;

  -- ── §4.4 if-expression inside parentheses ────────────────────────────────

  procedure Test_8 is
  begin
    R := (if Cycle_Of (X)
            /= Cycle_Of (Y)
          then Empty
          else Full);
    Next_Statement;
  end Test_8;

  -- ── §2.5, §6 case-expression as expression-function body ─────────────────

  function F_10 return T is
    (case X is
       when A | B
         => R1,
       when others => R2);

  -- ── §4.3 'and' outside paren; 'or else' takes extra indent inside paren ──

  function F_12 return Boolean is
  begin
    return A
      and (B = C
             or else D = E);
  end F_12;

  -- ── §4.3 nested parens inside multi-line if condition ─────────────────────

  procedure Test_13 is
  begin
    if A
      and then (B
                  or else (C
                             and then D))
    then
      null;
    end if;
  end Test_13;

  -- ── §7.1 comments between continuation lines are transparent ─────────────

  function F_14 return Boolean is
  begin
    return New_OBT > Old_OBT
      -- comment one
      -- comment two
      and (Departure.Earliest_TTOT = None
             -- inner comment
             or else New_OBT > X);
  end F_14;

  -- ── §2.5 ':= (case X is …)' inside paren; must NOT push block frame ───────

  procedure G_15 is
    Orig : constant T := (case E is
                            when A => X,
                            when others => Y);
    function F return T is
      (if C
       then P
       else Q);
    Id : constant T := Z;
  begin
    null;
  end G_15;

  -- ── §6 multi-line case-expression arm body with operator continuation ──────

  function F_16 return Boolean is
    (case S is
       when A | B
         => P,
       when others =>
         X
           or else Y
           or else (Z
                      and then W));

  -- ── §4.2 call name on own line; '(' one level deeper ─────────────────────

  procedure Test_17b is
  begin
    Foo
      (A,
       B);
  end Test_17b;

  -- ── §5 term continuation in condition ('>=' past 'and then') ─────────────

  procedure Test_19 is
  begin
    if A
      and then Take_Off_Time (X)
      -- a comment
        >= Take_Off_Time (Y)
    then
      null;
    end if;
  end Test_19;

  -- ── §6 '|' choice continuation at arm-body level ─────────────────────────

  procedure Test_21 is
  begin
    case X is
      when Action_1 | Action_15
        | Action_16 | Action_43 =>
        Do_It;
    end case;
  end Test_21;

  -- ── §5 '(' argument list in multi-line if condition ──────────────────────

  procedure Test_23 is
  begin
    if A
      and then Curtain_Index_May_Differ
        (Left (Normal) (FTFM),
         Right (FTFM),
         Skip => True)
    then
      null;
    end if;
  end Test_23;

  -- ── §5 call on 'elsif' opener; argument list one level in ────────────────

  procedure Test_23b is
  begin
    if X then
      null;
    elsif not Traffic_Volume_Profile.Element_Exists
      (TV_Profiles.P (FTFM), Env_Regulation_Info.TV_Id (Reg_Info))
    then
      null;
    end if;
  end Test_23b;

  -- ── §4.5 ')' in character literal must not affect paren depth ────────────

  procedure Test_24 is
  begin
    X := (A
            & (if C
               then B & ')'
               else ""));
  end Test_24;

  -- ── §4.3 '(' continuing first item of outer paren ────────────────────────

  procedure Test_32 is
  begin
    Id := F (G.Image
               (H (X),
                Width => W));
  end Test_32;

  -- ── §8 named association with value on next line + operator continuation ──

  procedure Test_33 is
  begin
    Call (A => 1,
          B =>
            X
              and Y
              -- comment
              and Z,
          C => 3);
  end Test_33;

  -- ── §4.4 lone ')' closing if-expression aligns under opening '(' ──────────

  procedure Test_34 is
  begin
    X := (if C
          then A
          else B
          -- a trailing note
         );
  end Test_34;

  -- ── §7.1 comment block in elsif condition before 'then' ──────────────────

  procedure Test_38 is
  begin
    if X then
      null;
    elsif not A (M)
      or else not B
      -- note one
      -- note two
    then
      null;
    end if;
  end Test_38;

  -- ── §7.2 comment inside paren ────────────────────────────────────────────

  procedure Test_39 is
  begin
    if A
      and then (B
                  -- note
                  or else C)
    then
      null;
    end if;
  end Test_39;

  -- ── §7.2 comment in paren must not inherit stale paren alignment ──────────

  procedure Test_40 is
  begin
    if First
      and then (Ready
                  or else (Sent (Data)))
      or else (Status = No_Deviation
                 -- a note
                 and then Has_Message (Info))
    then
      null;
    end if;
  end Test_40;

  -- ── §6, §7.1 comment after HEAD line of multi-line case-expression arm ────

  function F_41 return Boolean is
    (case Y is
       when A | B =>
         First_Cond
           -- head note
           or else Second_Cond
           -- middle note
           or else Third_Cond,
       when others => False);

  -- ── §7.2 trailing comment after last argument ────────────────────────────

  procedure Test_42 is
  begin
    Write (Bin_File => F,
           Query => Q,
           Validate => False
           -- the file stays open for an hour
           -- no need to validate now
           );
  end Test_42;

  -- ── §7.2 comment between arguments ───────────────────────────────────────

  procedure Test_43 is
  begin
    Make (M => M,
          Differ => A
            or else B = U,
          -- a note
          -- a second note
          Ctrl => C);
  end Test_43;

  -- ── §9 identifier starting with keyword (Case_Sensitive, …) ─────────────

  procedure R is
    A : Boolean := (Case_Sensitive
                      or Other);
    B : Integer := (If_Valid
                      + Count);
    C : Boolean := (For_Each
                      and Flag);
  begin
    null;
  end R;

  -- ── §2.4 select with guarded alternatives; 'or' aligns with 'select' ──────

  task body Worker_T is
  begin
    select
      when G1 =>
        accept Start;
    or
      when G2 =>
        accept Stop;
    end select;
  end Worker_T;

  -- ── §4.6 standalone 'loop' snaps back after '..' continuation ────────────

  procedure Test_48 is
  begin
    for C in Foo (A)
      .. Bar (B)
    loop
      null;
    end loop;
  end Test_48;

  -- ── §2.4, §2.6 'is new' stays continuation; standalone 'is' snaps back ───

  procedure Inst
    is new Gen (Param);

  task type T_49 (X : Boolean) with
    Storage_Size => 64
  is
    entry E;
  end T_49;

  -- ── §4.2, §8 named-association opening paren; value on next line ──────────

  procedure Test_50 is
  begin
    Error_Report
      (Title =>
         "Long value",
       Desc => Short,
       Sev => High);
  end Test_50;

  -- ── §2.6 'package Q is new Gen(…)' inside declarative region ────────────

  procedure Transfer (Stream : Buffer.T;
                      Object : in out Info_Request_List_T) is
    use type Buffer.Mode_T;
    procedure Transfer_Constrained (Request_Array : in out Info_Request_Array_T) is
      subtype Index_T is Info_Request_Index_T range Request_Array'Range;
      subtype Array_T is Info_Request_Array_T (Index_T);
      package Info_Request_Array_Buffer is
        new Buffer.Constrained_G (Index_T => Index_T,
                                  Component_T => Info_Request_T,
                                  Item_T => Array_T,
                                  Unchecked_Raw_Transfer => True);
    begin
      Info_Request_Array_Buffer.Transfer (Stream, Request_Array);
    end;
  begin
    Buffer.Text.Composite_Begin (Stream);
  end Transfer;

end Regression_Tests;

------------------------------------------------------------------------
--  §2.7 SUBUNIT (separate compilation unit)
------------------------------------------------------------------------

separate (Regression_Tests)
procedure P_Subunit (A : Integer;
                     B : Integer) is
  X : Integer;
begin
  null;
end P_Subunit;
