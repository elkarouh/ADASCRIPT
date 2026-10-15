with Ada.Strings.Unbounded;  use Ada.Strings.Unbounded;
with Ada.Text_IO;

package body Indenter is

   ----------------------------------------------------------------------
   --  Small accessors - the Python `self.stack[-1]` and `if self.stack`
   ----------------------------------------------------------------------

   function Depth_Of (Self : Indenter_T) return Integer is
     (Integer (Self.Stack.Length));

   function Top_Is (Self : Indenter_T; K : Block_T) return Boolean is
     (not Self.Stack.Is_Empty and then Self.Stack.Last_Element = K);

   function Top_Name (Self : Indenter_T) return String is
     (if Self.Stack.Is_Empty then "" else -Self.Frame_Names.Last_Element);

   function Name_At (Self : Indenter_T; I : Integer) return String is
     (-Self.Frame_Names (I));

   function TF (B : Boolean) return String is (if B then "T" else "F");

   function Sp (N : Integer) return String renames Repeat_Space;

   function Lead_Of (Res : String) return Integer is
     (Res'Length - LStrip (Res)'Length);

   function Find_Substring (S, Pat : String) return Boolean is
   begin
      for I in 0 .. S'Length - Pat'Length loop
         if Slice (S, I, I + Pat'Length) = Pat then
            return True;
         end if;
      end loop;
      return False;
   end Find_Substring;

   function Has_Word (Code_S, Word : String) return Boolean is
   begin
      for W of Code_Words (Code_S) loop
         if -W = Word then
            return True;
         end if;
      end loop;
      return False;
   end Has_Word;

   function Contains (V : Str_Vector; S : String) return Boolean is
   begin
      for E of V loop
         if -E = S then
            return True;
         end if;
      end loop;
      return False;
   end Contains;

   ----------------------------------------------------------------------
   --  Frame management
   ----------------------------------------------------------------------

   procedure Forget_Head (Self : in out Indenter_T; Name : String) is
      Kept : Str_Vector;
      Low  : constant String := Lower (Name);
   begin
      for H of Self.Unopened_Heads loop
         if -H /= Low then
            Kept.Append (H);
         end if;
      end loop;
      Self.Unopened_Heads := Kept;
   end Forget_Head;

   procedure Push_Frame
     (Self : in out Indenter_T; Kind : Block_T; Name : String := "") is
   begin
      Self.Stack.Append (Kind);
      Self.Frame_Names.Append (+Name);
      if Name /= "" then
         Forget_Head (Self, Name);
      end if;
   end Push_Frame;

   procedure Pop_Frame (Self : in out Indenter_T) is
   begin
      if not Self.Stack.Is_Empty then
         Self.Stack.Delete_Last;
         Self.Frame_Names.Delete_Last;
      end if;
   end Pop_Frame;

   procedure Warn (Self : Indenter_T; Msg : String) is
   begin
      if Self.Warn then
         Ada.Text_IO.Put_Line
           (Ada.Text_IO.Standard_Error,
            "ada_indent: line " & Img (Self.Lnum) & ": " & Msg);
      end if;
   end Warn;

   function Close_Named (Self : in out Indenter_T; Name : String) return Boolean
   is
      I : Integer := Depth_Of (Self) - 1;
   begin
      while I >= 0 loop
         if Lower (Name_At (Self, I)) = Lower (Name) then
            while Depth_Of (Self) > I loop
               Pop_Frame (Self);
            end loop;
            return True;
         end if;
         I := I - 1;
      end loop;
      return False;
   end Close_Named;

   function Closed_Depth (Self : Indenter_T; Name : String) return Integer is
      I : Integer := Natural (Self.Closed_Names.Length) - 1;
   begin
      while I >= 0 loop
         declare
            Nd : constant Str_Vector := Split_On (-Self.Closed_Names (I), ':');
         begin
            if -Nd (0) = Lower (Name) then
               return Integer'Value (-Nd (1));
            end if;
         end;
         I := I - 1;
      end loop;
      return -1;
   end Closed_Depth;

   procedure Close_Kind (Self : in out Indenter_T; Kind : Block_T; Word : String)
   is
      I : Integer := Depth_Of (Self) - 1;
   begin
      while I >= 0 loop
         if Self.Stack (I) = Kind then
            declare
               Dropped : Natural := 0;
            begin
               for J in I + 1 .. Depth_Of (Self) - 1 loop
                  if Self.Stack (J) /= B_WHEN then
                     Dropped := Dropped + 1;
                  end if;
               end loop;
               while Depth_Of (Self) > I loop
                  Pop_Frame (Self);
               end loop;
               if Dropped > 0 then
                  Warn (Self, "'end " & Word & "' closes an outer '" & Word
                        & "': dropped " & Img (Dropped)
                        & " unclosed frame(s) to resynchronise");
               end if;
            end;
            return;
         end if;
         if Self.Stack (I) = B_PKG or else Self.Stack (I) = B_TYPE_HEADER
           or else ((Self.Stack (I) = B_BLOCK or else Self.Stack (I) = B_DECLARE)
                    and then Name_At (Self, I) /= "")
         then
            exit;
         end if;
         I := I - 1;
      end loop;
      Warn (Self, "'end " & Word & "' has no open '" & Word & "' to close: ignored");
   end Close_Kind;

   procedure Resync_Expression (Self : in out Indenter_T; Why : String) is
   begin
      Warn (Self, Why);
      if Self.Cond_State = 1 then
         Push_Frame (Self, B_IF);
      end if;
      Self.Cond_State := 0;
      Self.Paren_Depth := 0;
      Self.Paren_Stack.Clear;
      Self.Paren_Cont := False;
      Self.Arrow_Level := 0;
      Self.Paren_Next_Lead_Depth := -1;
      Self.In_Cont := False;
   end Resync_Expression;

   ----------------------------------------------------------------------
   --  State snapshots
   ----------------------------------------------------------------------

   function Ints_Join (V : Int_Vector) return String is
      R : Ustr;
   begin
      for I in 0 .. Natural (V.Length) - 1 loop
         if I > 0 then
            Append (R, ",");   --  from Ada.Strings.Unbounded, visible via Ustr
         end if;
         Append (R, Img (V (I)));
      end loop;
      return -R;
   end Ints_Join;

   function Dump_State (Self : Indenter_T) return String is
      Stack_Names : Str_Vector;
      Ps_Parts    : Str_Vector;
   begin
      for I in 0 .. Depth_Of (Self) - 1 loop
         Stack_Names.Append
           (+(Block_Image (Self.Stack (I)) & ":" & Name_At (Self, I)));
      end loop;
      for T of Self.Paren_Stack loop
         Ps_Parts.Append
           (+(Img (T.Level) & ":" & Img (T.Col) & ":" & Paren_Kind_Image (T.Kind)));
      end loop;
      return "stack=" & Join (Stack_Names, ",")
        & "|cn="   & Join (Self.Closed_Names, ",")
        & "|uh="   & Join (Self.Unopened_Heads, ",")
        & "|pd="   & Img (Self.Paren_Depth)
        & "|ps="   & TF (Self.Pending_Spec)
        & "|ck="   & (-Self.Cont_Kw)
        & "|pl="   & (-Self.Pending_Label)
        & "|fn="   & (-Self.Frame_Name)
        & "|sn="   & (-Self.Spec_Name)
        & "|ln="   & Img (Self.Lnum)
        & "|pi="   & TF (Self.Pending_Inst)
        & "|cs="   & Img (Self.Cond_State)
        & "|cb="   & Img (Self.Cond_Base)
        & "|cvb="  & Img (Self.Cond_Value_Base)
        & "|ic="   & TF (Self.In_Cont)
        & "|vb="   & Img (Self.Value_Base)
        & "|sc="   & Img (Self.Spill_Col)
        & "|ll="   & Img (Self.Last_Lead)
        & "|ro="   & Ints_Join (Self.Ref_Orig)
        & "|rn="   & Ints_Join (Self.Ref_New)
        & "|len="  & TF (Self.Last_Ends_Name)
        & "|psk="  & Join (Ps_Parts, ";")
        & "|pc="   & TF (Self.Paren_Cont)
        & "|al="   & Img (Self.Arrow_Level)
        & "|pnl="  & Img (Self.Paren_Next_Lead)
        & "|pnld=" & Img (Self.Paren_Next_Lead_Depth)
        & "|ppl="  & Img (Self.Paren_Prev_Lead);
   end Dump_State;

   procedure Load_State (Self : in out Indenter_T; S : String) is

      function To_Int (V : String) return Integer is
      begin
         return Integer'Value (V);
      exception
         when Constraint_Error =>
            return 0;
      end To_Int;

      procedure Load_Ints (V : String; Into : in out Int_Vector) is
      begin
         for X of Split_On (V, ',') loop
            Into.Append (To_Int (-X));
         end loop;
      end Load_Ints;

   begin
      Self.Stack.Clear;
      Self.Frame_Names.Clear;
      Self.Closed_Names.Clear;
      Self.Unopened_Heads.Clear;
      Self.Pending_Label := +"";
      Self.Frame_Name := +"";
      Self.Spec_Name := +"";
      Self.Lnum := 0;
      Self.Paren_Depth := 0;
      Self.Pending_Spec := False;
      Self.Cont_Kw := +"";
      Self.Pending_Inst := False;
      Self.Cond_State := 0;
      Self.Cond_Base := 0;
      Self.Cond_Value_Base := 0;
      Self.In_Cont := False;
      Self.Value_Base := 0;
      Self.Spill_Col := -1;
      Self.Last_Lead := 0;
      Self.Ref_Orig.Clear;
      Self.Ref_New.Clear;
      Self.Last_Ends_Name := False;
      Self.Paren_Stack.Clear;
      Self.Paren_Cont := False;
      Self.Arrow_Level := 0;
      Self.Paren_Next_Lead := 0;
      Self.Paren_Next_Lead_Depth := -1;
      Self.Paren_Prev_Lead := 0;
      for PartU of Split_On (S, '|') loop
         declare
            Part : constant String := -PartU;
            Eq   : constant Integer := Find_Char (Part, '=');
         begin
            if Eq >= 0 then
               declare
                  Key : constant String := Slice (Part, 0, Eq);
                  Val : constant String := Tail (Part, Eq + 1);
               begin
                  if Key = "stack" then
                     if Val /= "" then
                        for EntryU of Split_On (Val, ',') loop
                           declare
                              Ent   : constant String := -EntryU;
                              C     : constant Integer := Find_Char (Ent, ':');
                              Found : Boolean;
                           begin
                              if C < 0 then
                                 declare
                                    K : constant Block_T :=
                                      Block_From_Image (Ent, Found);
                                 begin
                                    if Found then
                                       Push_Frame (Self, K);
                                    end if;
                                 end;
                              else
                                 declare
                                    K : constant Block_T :=
                                      Block_From_Image (Slice (Ent, 0, C), Found);
                                 begin
                                    if Found then
                                       Push_Frame (Self, K, Tail (Ent, C + 1));
                                    end if;
                                 end;
                              end if;
                           end;
                        end loop;
                     end if;
                  elsif Key = "pd" then Self.Paren_Depth := To_Int (Val);
                  elsif Key = "ps" then Self.Pending_Spec := Val = "T";
                  elsif Key = "ck" then Self.Cont_Kw := +Val;
                  elsif Key = "pl" then Self.Pending_Label := +Val;
                  elsif Key = "fn" then Self.Frame_Name := +Val;
                  elsif Key = "sn" then Self.Spec_Name := +Val;
                  elsif Key = "ln" then Self.Lnum := To_Int (Val);
                  elsif Key = "pi" then Self.Pending_Inst := Val = "T";
                  elsif Key = "cs" then Self.Cond_State := To_Int (Val);
                  elsif Key = "cb" then Self.Cond_Base := To_Int (Val);
                  elsif Key = "cvb" then Self.Cond_Value_Base := To_Int (Val);
                  elsif Key = "ic" then Self.In_Cont := Val = "T";
                  elsif Key = "vb" then Self.Value_Base := To_Int (Val);
                  elsif Key = "sc" then Self.Spill_Col := To_Int (Val);
                  elsif Key = "ll" then Self.Last_Lead := To_Int (Val);
                  elsif Key = "ro" then
                     if Val /= "" then
                        Load_Ints (Val, Self.Ref_Orig);
                     end if;
                  elsif Key = "rn" then
                     if Val /= "" then
                        Load_Ints (Val, Self.Ref_New);
                     end if;
                  elsif Key = "len" then Self.Last_Ends_Name := Val = "T";
                  elsif Key = "psk" then
                     if Val /= "" then
                        for EntryU of Split_On (Val, ';') loop
                           declare
                              Ep    : constant Str_Vector :=
                                Split_On (-EntryU, ':');
                              Found : Boolean;
                           begin
                              if Natural (Ep.Length) = 3 then
                                 declare
                                    K : constant Paren_Kind_T :=
                                      Paren_Kind_From_Image (-Ep (2), Found);
                                 begin
                                    if Found then
                                       Self.Paren_Stack.Append
                                         ((Level => To_Int (-Ep (0)),
                                           Col   => To_Int (-Ep (1)),
                                           Kind  => K));
                                    end if;
                                 end;
                              end if;
                           end;
                        end loop;
                     end if;
                  elsif Key = "pc" then Self.Paren_Cont := Val = "T";
                  elsif Key = "al" then Self.Arrow_Level := To_Int (Val);
                  elsif Key = "pnl" then Self.Paren_Next_Lead := To_Int (Val);
                  elsif Key = "pnld" then Self.Paren_Next_Lead_Depth := To_Int (Val);
                  elsif Key = "ppl" then Self.Paren_Prev_Lead := To_Int (Val);
                  elsif Key = "cn" then
                     if Val /= "" then
                        Self.Closed_Names := Split_On (Val, ',');
                     end if;
                  elsif Key = "uh" then
                     if Val /= "" then
                        Self.Unopened_Heads := Split_On (Val, ',');
                     end if;
                  end if;
               end;
            end if;
         end;
      end loop;
   end Load_State;

   ----------------------------------------------------------------------
   --  Opening frames
   ----------------------------------------------------------------------

   procedure Open_Trailing (Self : in out Indenter_T; Code_S : String; LW : String)
   is
   begin
      if Ends_With (Code_S, ";") then
         return;
      end if;
      declare
         Last : constant String := Last_Word (Code_S);
         CK   : constant String := -Self.Cont_Kw;
      begin
         if Last = "is" then
            if CK = "function" then
               Self.Pending_Spec := True;
               Self.Spec_Name := Self.Frame_Name;
            elsif CK = "type" then
               Push_Frame (Self, B_TYPE_HEADER, -Self.Frame_Name);
            elsif CK /= "subtype" then
               if CK = "case" or else CK = "when" then
                  Push_Frame (Self, B_CASE);
               else
                  Push_Frame (Self, B_PKG, -Self.Frame_Name);
               end if;
            end if;
         elsif Last = "then" and then Ends_With_Condition_Then (Code_S) then
            Push_Frame (Self, B_IF);
         elsif Last = "loop" then
            Push_Frame (Self, B_LOOP, -Self.Frame_Name);
         elsif Last = "record" and then LW /= "null" then
            Push_Frame (Self, B_RECORD);
         elsif Last = "select" then
            Push_Frame (Self, B_SELECT);
         elsif Last = "do" then
            Push_Frame (Self, B_DO);
         elsif Last = "declare" then
            Push_Frame (Self, B_DECLARE, -Self.Frame_Name);
         elsif Last = "begin" then
            Push_Frame (Self, B_BLOCK, -Self.Frame_Name);
         end if;
      end;
   end Open_Trailing;

   procedure Open_Midline
     (Self : in out Indenter_T; Code, Code_S : String; LW : String)
   is
      Last : constant String := Last_Word (Code_S);
   begin
      if Last /= "record" and then Record_Delta (Code) > 0 then
         Push_Frame (Self, B_RECORD);
      end if;
      if Last /= "loop" then
         declare
            Extra_Loops : Integer := Loop_Delta (Code);
         begin
            while Extra_Loops > 0 loop
               Push_Frame (Self, B_LOOP);
               Extra_Loops := Extra_Loops - 1;
            end loop;
         end;
      end if;
      if Has_Condition_Then (Code) then
         declare
            Tracked : constant Boolean :=
              LW = "if" and then not Ends_With_Condition_Then (Code_S)
              and then Stmt_Incomplete (Code_S);
            Extra_Ifs : Integer :=
              If_Delta (Code)
              - (if Ends_With_Condition_Then (Code_S) then 1 else 0)
              - (if Tracked then 1 else 0);
         begin
            while Extra_Ifs > 0 loop
               Push_Frame (Self, B_IF);
               Extra_Ifs := Extra_Ifs - 1;
            end loop;
         end;
      end if;
   end Open_Midline;

   procedure Push_Parens
     (Self : in out Indenter_T; Text : String;
      Base_Col, Base_Depth, New_Depth : Integer) is
   begin
      for Opener of Scan_Parens (Text, Base_Depth, Base_Col) loop
         Self.Paren_Stack.Append (Opener);
      end loop;
      while not Self.Paren_Stack.Is_Empty
        and then Self.Paren_Stack.Last_Element.Level > New_Depth
      loop
         Self.Paren_Stack.Delete_Last;
      end loop;
   end Push_Parens;

   ----------------------------------------------------------------------
   --  Indent_Raw - re-indent one raw line
   ----------------------------------------------------------------------

   function Indent_Raw (Self : in out Indenter_T; Line : String) return String is
      Raw2      : constant String := RStrip (Line);
      Code      : constant String := Strip_Line_Comment (Raw2, "--", '"');
      Code_S    : constant String := Strip (Code);
      Emit_Text : constant String := Strip (Raw2);
      Lead_Id   : constant String := Lead_Ident (Code_S);
      LW        : constant String := Lower (Lead_Id);

      Entry_Depth : Integer;
      Cont        : Integer;
      Disp        : Integer;
      Popped_Type_Header : Boolean := False;
      Lead_N      : Integer;
      Extra_Ends  : Integer;
   begin
      Self.Lnum := Self.Lnum + 1;

      if Emit_Text = "" then
         return "";
      end if;

      -----------------------------------------------------------------
      --  A comment-only line is transparent to the parser: it is indented
      --  to the current context and leaves ALL state untouched.
      -----------------------------------------------------------------
      if Code_S = "" then
         if Self.Paren_Depth > 0 and then not Self.Paren_Stack.Is_Empty then
            declare
               PTop  : constant Paren_Entry := Self.Paren_Stack.Last_Element;
               PFall : Integer := PTop.Col;
            begin
               if Self.Paren_Next_Lead_Depth = Self.Paren_Depth then
                  return Sp (Self.Paren_Next_Lead) & Emit_Text;
               end if;
               case PTop.Kind is
                  when P_CASE_EXPR | P_FOR_EXPR =>
                     PFall := PFall + Indent_Width;
                  when P_PLAIN =>
                     if Self.Paren_Cont then
                        PFall := PFall + Indent_Width;
                     end if;
                  when others =>
                     null;
               end case;
               return Sp (PFall) & Emit_Text;
            end;
         end if;
         if Self.Cond_State > 0 then
            declare
               CLvl : constant Integer :=
                 Integer'Max (Self.Cond_Value_Base, Self.Cond_Base + 1);
            begin
               return Sp (Integer'Max (0, CLvl) * Indent_Width) & Emit_Text;
            end;
         end if;
         if Self.In_Cont and then Self.Spill_Col >= 0 then
            return Sp (Self.Spill_Col) & Emit_Text;
         end if;
         if Self.In_Cont then
            return Sp (Integer'Max (0, Self.Value_Base + 1) * Indent_Width)
              & Emit_Text;
         end if;
         declare
            BLvl : constant Integer :=
              Depth_Of (Self) + (if Self.Pending_Spec then 1 else 0);
         begin
            return Sp (Integer'Max (0, BLvl) * Indent_Width) & Emit_Text;
         end;
      end if;

      -----------------------------------------------------------------
      --  A line that cannot be part of an expression ends whatever
      --  expression or condition the previous lines left open.
      -----------------------------------------------------------------
      if (Self.Paren_Depth > 0 or else Self.Cond_State > 0)
        and then Is_Resync_Word (LW)
      then
         Resync_Expression
           (Self,
            "'" & Lead_Id & "' inside an unfinished "
            & (if Self.Paren_Depth > 0 then "parenthesis" else "'if' condition")
            & ": state reset");
      elsif Self.In_Cont and then Is_Resync_Word (LW) then
         Self.In_Cont := False;   --  the previous line lacked its ';'
      elsif Self.Cond_State > 0 and then Self.Paren_Depth = 0
        and then Ends_With (Code_S, ";") and then LW /= "then"
        and then not Has_Condition_Then (Code)
      then
         Resync_Expression (Self, "'if' condition ended without 'then'");
      end if;

      Entry_Depth := Self.Paren_Depth;
      if Entry_Depth = 0 then
         Self.Paren_Cont := False;
         Self.Arrow_Level := 0;
      end if;
      Cont := (if Self.Paren_Depth > 0 or else Self.In_Cont then 1 else 0);

      if Cont = 0 then
         Self.Cont_Kw := +Lead_Keyword (Code_S);
         declare
            DN : constant String := Declared_Name (Code_S);
            CK : constant String := -Self.Cont_Kw;
         begin
            if DN /= "" and then CK /= "type" and then CK /= "subtype" then
               Forget_Head (Self, DN);
               Self.Unopened_Heads.Append (+Lower (DN));
               if Natural (Self.Unopened_Heads.Length) > 8 then
                  Self.Unopened_Heads.Delete_First;
               end if;
            end if;
            if DN /= "" and then Ends_With (Code_S, ":") then
               Self.Pending_Label := +DN;
               Self.Frame_Name := +"";
            else
               Self.Frame_Name := (if DN /= "" then +DN else Self.Pending_Label);
               Self.Pending_Label := +"";
            end if;
         end;
      end if;
      Disp := Depth_Of (Self);

      --  A 'type T is' that turned out to be an enum, derived, or other
      --  non-record type pushed TYPE_HEADER waiting for 'record'.
      if not Self.In_Cont and then Self.Paren_Depth = 0
        and then Top_Is (Self, B_TYPE_HEADER) and then LW /= "record"
        and then not Starts_With (Code_S, "(")
      then
         Pop_Frame (Self);
         Disp := Depth_Of (Self);
         Popped_Type_Header := True;
      end if;

      --  The formal part of a generic ends where the unit it parameterises
      --  begins.
      if Cont = 0 and then Top_Is (Self, B_GENERIC)
        and then LW in "package" | "procedure" | "function"
      then
         Pop_Frame (Self);
         Disp := Depth_Of (Self);
      end if;

      --  An 'X is\nnew Y;' generic instantiation pushed a PKG for 'X is'.
      if Self.Pending_Inst and then not Self.In_Cont and then Self.Paren_Depth = 0
      then
         Self.Pending_Inst := False;
         if Top_Is (Self, B_PKG) then
            Pop_Frame (Self);
            Disp := Depth_Of (Self);
         end if;
      end if;

      --  Resolve a deferred 'function ... is' header (set on the previous line).
      if Self.Pending_Spec then
         Self.Pending_Spec := False;
         if Starts_With (Code_S, "(") then
            Self.In_Cont := False;
            declare
               Lead_E : constant Integer :=
                 Integer'Max (0, Depth_Of (Self) + 1 + Cont) * Indent_Width;
            begin
               Self.Paren_Depth :=
                 Integer'Max (0, Self.Paren_Depth + Paren_Delta (Code));
               Self.Paren_Next_Lead_Depth := -1;
               Push_Parens (Self, Emit_Text, Lead_E, Entry_Depth, Self.Paren_Depth);
               return Sp (Lead_E) & Emit_Text;
            end;
         else
            Push_Frame (Self, B_PKG, -Self.Spec_Name);
            Disp := Depth_Of (Self);
         end if;
      end if;

      -----------------------------------------------------------------
      --  Inside an unclosed parenthesis the line is a continuation of an
      --  expression / list, aligned by absolute column to the innermost
      --  open parenthesis.
      -----------------------------------------------------------------
      if Self.Paren_Depth > 0 then
         while not Self.Paren_Stack.Is_Empty
           and then Self.Paren_Stack.Last_Element.Level > Entry_Depth
         loop
            Self.Paren_Stack.Delete_Last;
         end loop;
         declare
            Lead            : Integer :=
              Integer'Max (0, Depth_Of (Self) + Cont) * Indent_Width;
            Entry_Top_Level : Integer := 0;
            Entry_Top_Kind  : Paren_Kind_T := P_OUTSIDE;
            Was_Cont        : Boolean := False;
            ACol            : Integer := 0;
            New_Depth       : Integer;
         begin
            if not Self.Paren_Stack.Is_Empty then
               declare
                  Top : constant Paren_Entry := Self.Paren_Stack.Last_Element;
               begin
                  ACol := Top.Col;
                  Entry_Top_Level := Top.Level;
                  Entry_Top_Kind := Top.Kind;
                  if Entry_Top_Kind /= P_PLAIN and then Starts_With (Code_S, ")")
                  then
                     --  A line that begins by closing an '(if'/'(case'/'(for'
                     --  expression aligns the ')' under the opening '('.
                     Lead := Integer'Max (0, ACol - 1);
                  else
                     case Entry_Top_Kind is
                        when P_IF_EXPR =>
                           if LW in "then" | "else" | "elsif" then
                              Lead := ACol;
                           else
                              Lead := ACol + Indent_Width;
                           end if;
                        when P_CASE_EXPR =>
                           if LW = "when" then
                              Lead := ACol + Indent_Width;
                           else
                              Lead := ACol + 2 * Indent_Width;
                              if Starts_With_Operator (Code_S)
                                and then not Starts_With (Code_S, "=>")
                              then
                                 Lead := Lead + Indent_Width;
                                 Was_Cont := True;
                              end if;
                           end if;
                        when P_FOR_EXPR =>
                           Lead := ACol + Indent_Width;
                           if Starts_With_Operator (Code_S)
                             and then not Starts_With (Code_S, "=>")
                           then
                              Lead := Lead + Indent_Width;
                              Was_Cont := True;
                           end if;
                        when others =>
                           declare
                              VBase : constant Integer :=
                                ACol + (if Self.Arrow_Level = Top.Level
                                        then Indent_Width else 0);
                           begin
                              Lead := VBase;
                              if Starts_With_Operator (Code_S) then
                                 Lead := VBase + Indent_Width;
                                 Was_Cont := True;
                              elsif Starts_With (Code_S, "(") and then Self.Paren_Cont
                              then
                                 Lead := VBase + Indent_Width;
                                 if Self.Paren_Next_Lead_Depth = Entry_Depth then
                                    Lead := Integer'Max
                                      (Lead, Self.Paren_Prev_Lead + Indent_Width);
                                 end if;
                                 Was_Cont := True;
                              end if;
                           end;
                     end case;
                  end if;
               end;
            end if;
            New_Depth := Self.Paren_Depth + Paren_Delta (Code);
            Self.In_Cont := Stmt_Incomplete (Code_S);
            Self.Paren_Cont := Self.In_Cont and then not Ends_With (Code_S, ",");
            Self.Paren_Depth := Integer'Max (0, New_Depth);
            if Entry_Top_Kind = P_PLAIN then
               if Ends_With (Code_S, "=>") then
                  Self.Arrow_Level := Entry_Top_Level;
               elsif Self.Arrow_Level = Entry_Top_Level
                 and then Ends_With (Code_S, ",")
               then
                  Self.Arrow_Level := 0;
               end if;
            end if;
            if Self.Arrow_Level > 0 and then Self.Paren_Depth < Self.Arrow_Level then
               Self.Arrow_Level := 0;
            end if;
            if Self.Arrow_Level > 0 and then Self.Paren_Depth = Self.Arrow_Level
              and then Ends_With (Code_S, ",")
            then
               Self.Arrow_Level := 0;
            end if;
            declare
               Complete_Assoc : constant Boolean :=
                 Find_Substring (Code_S, "=>") and then not Ends_With (Code_S, "=>");
            begin
               if Entry_Top_Kind /= P_OUTSIDE and then Ends_With (Code_S, ",") then
                  declare
                     PNext : Integer := ACol;
                  begin
                     if Entry_Top_Kind in P_CASE_EXPR | P_FOR_EXPR then
                        PNext := PNext + Indent_Width;
                     end if;
                     Self.Paren_Next_Lead := PNext;
                  end;
               elsif Entry_Top_Kind = P_PLAIN and then Complete_Assoc then
                  Self.Paren_Next_Lead := ACol;
               elsif Entry_Top_Kind /= P_IF_EXPR and then Self.Paren_Cont
                 and then not Was_Cont
                 and then (Entry_Top_Kind /= P_PLAIN or else Ends_With_Operator (Code_S))
               then
                  Self.Paren_Next_Lead := Lead + Indent_Width;
               else
                  Self.Paren_Next_Lead := Lead;
               end if;
            end;
            Self.Paren_Prev_Lead := Lead;
            Self.Paren_Next_Lead_Depth := Entry_Depth;
            Push_Parens (Self, Emit_Text, Lead, Entry_Depth, Self.Paren_Depth);
            if New_Depth <= 0
              and then (Ends_With (Code_S, ",") or else not Self.In_Cont)
            then
               Self.Spill_Col := -1;   --  the aspect's value ends here
            end if;
            if New_Depth <= 0 then
               if Self.Cond_State > 0 and then Ends_With_Condition_Then (Code_S) then
                  if Self.Cond_State = 1 then
                     Push_Frame (Self, B_IF);
                  end if;
                  Self.Cond_State := 0;
               else
                  Open_Trailing (Self, Code_S, LW);
               end if;
            end if;
            return Sp (Lead) & Emit_Text;
         end;
      end if;

      -----------------------------------------------------------------
      --  Multi-line if/elsif condition (outside any parenthesis)
      -----------------------------------------------------------------
      if Self.Cond_State > 0 then
         if Ends_With_Condition_Then (Code_S) or else LW = "then" then
            Disp := Self.Cond_Base;
            if Self.Cond_State = 1 then
               Push_Frame (Self, B_IF);
            end if;
            Self.Cond_State := 0;
         elsif Is_Term_Continuation (Code_S) and then LW /= "and" and then LW /= "or"
         then
            Disp := Self.Cond_Value_Base + 1;
         else
            Disp := Self.Cond_Base + 1;
            Self.Cond_Value_Base := Self.Cond_Base + 1;
         end if;
         Self.In_Cont := False;
         declare
            Lead_C : constant Integer := Integer'Max (0, Disp) * Indent_Width;
         begin
            Self.Paren_Depth := Integer'Max (0, Self.Paren_Depth + Paren_Delta (Code));
            Self.Paren_Cont := Self.Paren_Depth > 0 and then not Ends_With (Code_S, ",");
            Self.Paren_Next_Lead_Depth := -1;
            Push_Parens (Self, Emit_Text, Lead_C, Entry_Depth, Self.Paren_Depth);
            return Sp (Lead_C) & Emit_Text;
         end;
      end if;

      -----------------------------------------------------------------
      --  Keyword dispatch
      -----------------------------------------------------------------
      if LW = "end" then
         while Top_Is (Self, B_WHEN) loop
            Pop_Frame (Self);
         end loop;
         declare
            En     : constant String := End_Name (Code_S);
            Ews    : constant Str_Vector := Lead_Words (Code_S);
            EKw    : constant String :=
              (if Natural (Ews.Length) > 1
                 and then Is_End_Keyword (Lower (-Ews (1)))
               then Lower (-Ews (1)) else "");
            Top_N  : constant String := Top_Name (Self);
            Before : constant Integer := Depth_Of (Self);
         begin
            if EKw /= "" then
               --  'end if', 'end loop', ...: the kind is stated, so match on it.
               if EKw = "if" then
                  Close_Kind (Self, B_IF, EKw);
               elsif EKw = "loop" then
                  Close_Kind (Self, B_LOOP, EKw);
               elsif EKw = "case" then
                  Close_Kind (Self, B_CASE, EKw);
               elsif EKw = "record" then
                  Close_Kind (Self, B_RECORD, EKw);
               elsif EKw = "select" then
                  Close_Kind (Self, B_SELECT, EKw);
               else
                  Close_Kind (Self, B_DO, EKw);   --  'end return'
               end if;
            elsif En = "" or else Lower (Top_N) = Lower (En) then
               --  The ordinary, matching case.  A nameless 'end' closing a named
               --  frame is remembered: if it was stray, the frame's own 'end X;'
               --  arrives later and must not close another.
               if En = "" and then Top_N /= "" then
                  Self.Closed_Names.Append
                    (+(Lower (Top_N) & ":" & Img (Depth_Of (Self) - 1)));
                  if Natural (Self.Closed_Names.Length) > 8 then
                     Self.Closed_Names.Delete_First;
                  end if;
               end if;
               Pop_Frame (Self);
            elsif Close_Named (Self, En) then
               declare
                  Stale : constant Integer := Before - Depth_Of (Self) - 1;
               begin
                  Warn (Self, "'end " & En & "' closes an outer construct: dropped "
                        & Img (Stale) & " unclosed frame(s) to resynchronise");
               end;
            elsif Closed_Depth (Self, En) >= 0 then
               declare
                  Depth : constant Integer := Closed_Depth (Self, En);
               begin
                  while Depth_Of (Self) > Depth loop
                     Pop_Frame (Self);
                  end loop;
                  Warn (Self, "'end " & En
                        & "' closes a construct an earlier 'end' already closed");
               end;
            elsif Top_N = "" then
               Pop_Frame (Self);   --  unnamed frame: nothing to contradict
            elsif Contains (Self.Unopened_Heads, Lower (En)) then
               Warn (Self, "'end " & En & "' closes '" & En
                     & "', whose header opened no block: ignored");
            else
               Warn (Self, "'end " & En & "' does not match the open '" & Top_N & "'");
               Pop_Frame (Self);
            end if;
         end;
         Disp := Depth_Of (Self);
         --  'end record' closes only RECORD; pop the paired TYPE_HEADER so
         --  that the lines AFTER this one resume at the enclosing scope.
         if Last_Word (Code_S) = "record" and then Top_Is (Self, B_TYPE_HEADER) then
            Pop_Frame (Self);
         end if;

      elsif LW = "begin" then
         if Top_Is (Self, B_PKG) or else Top_Is (Self, B_DECLARE) then
            Disp := Depth_Of (Self) - 1;
            Self.Stack.Replace_Element (Depth_Of (Self) - 1, B_BLOCK);
         else
            Disp := Depth_Of (Self);
            Push_Frame (Self, B_BLOCK, -Self.Frame_Name);
         end if;

      elsif LW = "when"
        and then (Cont = 0 or else (-Self.Cont_Kw /= "entry" and then -Self.Cont_Kw /= "exit"))
      then
         --  (A 'when' continuing an 'exit Name' or an entry header is a
         --  condition, not an alternative.)
         if Top_Is (Self, B_WHEN) then
            Pop_Frame (Self);
         end if;
         Disp := Depth_Of (Self);
         if Top_Is (Self, B_CASE) or else Top_Is (Self, B_SELECT)
           or else Top_Is (Self, B_BLOCK) or else Top_Is (Self, B_DO)
         then
            Push_Frame (Self, B_WHEN);
            if Paren_Delta (Code) <= 0 then
               Open_Trailing (Self, Code_S, LW);
               Open_Midline (Self, Code, Code_S, LW);
            end if;
         else
            Warn (Self, "'when' outside a case, select or exception handler: "
                  & "no alternative opened");
         end if;

      elsif LW = "elsif" then
         Disp := Depth_Of (Self) - 1;
         if not Ends_With_Condition_Then (Code_S) and then Stmt_Incomplete (Code_S)
         then
            Self.Cond_State := 2;
            Self.Cond_Base := Integer'Max (0, Disp);
            Self.Cond_Value_Base := Integer'Max (0, Disp);
         end if;

      elsif LW = "generic" and then Lower (Code_S) = "generic" then
         Push_Frame (Self, B_GENERIC);

      elsif LW in "else" | "exception" | "or" | "private" | "then"
        and then (LW /= "private" or else Lower (Code_S) = "private")
        and then (LW /= "then" or else Is_Then_Abort (Code_S))
      then
         --  A select alternative ends without popping the WHEN frame (only
         --  'end' and 'when' pop it): 'or'/'else' splitting the select must
         --  clear it first so they align with 'select'.
         while Top_Is (Self, B_WHEN) loop
            Pop_Frame (Self);
         end loop;
         if Cont = 0 then
            Disp := Depth_Of (Self) - 1;
         end if;

      else
         --  'package/procedure X is\nnew Y' is a generic instantiation.
         if LW = "new" and then Cont = 0 and then not Popped_Type_Header
           and then Top_Is (Self, B_PKG)
         then
            Self.Pending_Inst := True;
         end if;
         Disp := Depth_Of (Self);
         --  A trailing block keyword opens a block only when it sits at the
         --  top level of the line.
         if Paren_Delta (Code) <= 0 then
            if Cont > 0 and then Last_Word (Code_S) = "record"
              and then LW in "record" | "with" | "limited" | "tagged" | "abstract"
              and then not Ends_With (Code_S, ";")
              and then not Top_Is (Self, B_TYPE_HEADER)
            then
               Push_Frame (Self, B_TYPE_HEADER, -Self.Frame_Name);
            end if;
            Open_Trailing (Self, Code_S, LW);
         end if;
         Open_Midline (Self, Code, Code_S, LW);
         if LW = "if" and then not Ends_With_Condition_Then (Code_S)
           and then Stmt_Incomplete (Code_S)
         then
            Self.Cond_State := 1;
            Self.Cond_Base := Disp;
            Self.Cond_Value_Base := Disp;
         end if;
      end if;

      --  'end's the line reaches part-way along, after something the
      --  dispatch above has already claimed.
      Extra_Ends := Unmatched_Ends (Code_S) - (if LW = "end" then 1 else 0);
      while Extra_Ends > 0 loop
         while Top_Is (Self, B_WHEN) loop
            Pop_Frame (Self);
         end loop;
         Pop_Frame (Self);
         Extra_Ends := Extra_Ends - 1;
      end loop;

      Self.In_Cont := (if Self.Cond_State > 0 then False else Stmt_Incomplete (Code_S));
      Self.Paren_Depth := Integer'Max (0, Self.Paren_Depth + Paren_Delta (Code));
      Self.Paren_Cont := Self.In_Cont and then not Ends_With (Code_S, ",");
      if Self.Paren_Depth > 0 and then Ends_With (Code_S, "=>") then
         Self.Arrow_Level := Self.Paren_Depth;
      end if;

      if Cont = 0 then
         Self.Value_Base := Integer'Max (0, Disp);
      elsif Starts_With (Code_S, ":=") then
         Self.Value_Base := Disp + Cont;
      end if;

      Lead_N := Integer'Max (0, Disp + Cont) * Indent_Width;
      if Cont > 0 and then Is_Term_Continuation (Code_S) then
         Lead_N := Integer'Max (0, Self.Value_Base + 1) * Indent_Width;
         if Starts_With (Code_S, "(") and then Self.Last_Ends_Name then
            Lead_N := Integer'Max (Lead_N, Self.Last_Lead + Indent_Width);
         end if;
      end if;
      if Cont > 0 and then Starts_With (Code_S, "|") then
         Lead_N := Integer'Max
           (0, Disp + (if -Self.Cont_Kw = "when" then 1 else 0)) * Indent_Width;
      end if;
      if LW in "loop" | "do" and then Cont > 0 then
         Lead_N := Integer'Max (0, Disp) * Indent_Width;
      end if;
      if LW = "is" and then Cont > 0
        and then Lower (Lead_Ident (Tail (Code_S, 2))) /= "new"
      then
         Lead_N := Integer'Max (0, Disp) * Indent_Width;
      end if;
      if Self.Spill_Col >= 0 and then Cont > 0 then
         Lead_N := Self.Spill_Col;
         if Is_Term_Continuation (Code_S) or else Starts_With (Code_S, "|") then
            Lead_N := Lead_N + Indent_Width;
         end if;
      end if;
      if Cont = 0 or else Ends_With (Code_S, ",") or else not Self.In_Cont then
         Self.Spill_Col := -1;
      end if;
      if Cont > 0 and then LW = "when" and then Self.In_Cont then
         Self.Spill_Col := Lead_N;
      end if;
      if Self.Paren_Depth = 0 and then Ends_With (Code_S, "=>")
        and then -Self.Cont_Kw /= "when" and then not Has_Word (Code_S, "when")
      then
         Self.Spill_Col := Lead_N + Indent_Width;
         Self.In_Cont := True;
      end if;
      Self.Paren_Next_Lead_Depth := -1;
      Push_Parens (Self, Emit_Text, Lead_N, Entry_Depth, Self.Paren_Depth);
      return Sp (Lead_N) & Emit_Text;
   end Indent_Raw;

   ----------------------------------------------------------------------

   function Indent_Line (Self : in out Indenter_T; Line : String) return String is
      Depth  : constant Integer := Self.Paren_Depth;   --  the depth the line starts at
      Res    : Ustr;
      Code_S : constant String := Strip (Strip_Line_Comment (Line, "--", '"'));
      Orig   : constant Integer := Input_Column (Line);
   begin
      Self.Kept_Comment := False;
      Res := +Indent_Raw (Self, Line);
      if Code_S /= "" then
         declare
            R : constant String := -Res;
         begin
            Self.Last_Lead := Lead_Of (R);
            Self.Last_Ends_Name := Is_Ident_Ch (Ch (Code_S, Code_S'Length - 1));
            --  Remember where this line was and where it went, as the
            --  reference for comments at its depth; deeper references are
            --  stale now.
            while Natural (Self.Ref_Orig.Length) > Depth loop
               Self.Ref_Orig.Delete_Last;
               Self.Ref_New.Delete_Last;
            end loop;
            while Natural (Self.Ref_Orig.Length) < Depth loop
               Self.Ref_Orig.Append (-1);
               Self.Ref_New.Append (-1);
            end loop;
            Self.Ref_Orig.Append (Orig);
            Self.Ref_New.Append (Self.Last_Lead);
            --  A line that opens parentheses holds their first items too.
            while Natural (Self.Ref_Orig.Length) <= Self.Paren_Depth loop
               Self.Ref_Orig.Append (Orig);
               Self.Ref_New.Append (Self.Last_Lead);
            end loop;
         end;
      elsif Strip (Line) /= "" and then Depth < Natural (Self.Ref_Orig.Length)
        and then Self.Ref_Orig (Depth) >= 0
      then
         --  A comment placed deliberately deeper than the indenter would put
         --  it keeps its place relative to the code line above it at its depth.
         declare
            R    : constant String := -Res;
            Dflt : constant Integer := Lead_Of (R);
            Rel  : constant Integer := Orig - Self.Ref_Orig (Depth);
         begin
            if Rel > 0 and then Rel > Dflt - Self.Ref_New (Depth) + Indent_Width then
               declare
                  Kept : constant Integer :=
                    Integer'Max (0, Self.Ref_New (Depth) + Rel);
               begin
                  Res := +(Sp (Kept) & LStrip (R));
                  Self.Kept_Comment := True;
               end;
            end if;
         end;
      end if;
      --  A declaration that ends in ';' at the outer level is complete
      --  without a body, so its head is not one waiting for a frame.
      if Self.Paren_Depth = 0 and then -Self.Frame_Name /= ""
        and then Ends_With (RStrip (Strip_Line_Comment (Line, "--", '"')), ";")
      then
         Forget_Head (Self, -Self.Frame_Name);
      end if;
      return -Res;
   end Indent_Line;

   function Indent_Lines
     (Self : in out Indenter_T; Lines : Str_Vector) return Str_Vector
   is
      Out_Lines   : Str_Vector;
      Pending     : Int_Vector;   --  comment lines waiting for their code line
      After_Blank : Boolean := True;   --  the file's first comments open a paragraph too
   begin
      for LineU of Lines loop
         declare
            Line : constant String := -LineU;
            Res  : constant String := Indent_Line (Self, Line);
            Text : constant String := Strip (Line);
         begin
            if Self.Keep_States then
               Self.States.Append (+Dump_State (Self));
            end if;
            if Text = "" then
               Pending.Clear;   --  a blank line: the run stands alone
               After_Blank := True;
            elsif Strip (Strip_Line_Comment (Line, "--", '"')) = "" then
               if After_Blank and then not Self.Kept_Comment then
                  Pending.Append (Natural (Out_Lines.Length));
               else
                  Pending.Clear;
                  After_Blank := False;
               end if;
            else
               if Lower (Lead_Ident (Text)) not in "end" | "begin"
                 and then not Starts_With (Text, ")")
               then
                  declare
                     Col : constant Integer := Lead_Of (Res);
                  begin
                     for K of Pending loop
                        declare
                           Body_Text : constant String := LStrip (-Out_Lines (K));
                        begin
                           Out_Lines.Replace_Element (K, +(Sp (Col) & Body_Text));
                        end;
                     end loop;
                  end;
               end if;
               Pending.Clear;
               After_Blank := False;
            end if;
            Out_Lines.Append (+Res);
         end;
      end loop;
      return Out_Lines;
   end Indent_Lines;

end Indenter;
