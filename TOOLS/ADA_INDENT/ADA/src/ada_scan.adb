package body Ada_Scan is

   Apos : constant Character := Character'Val (39);

   ----------------------------------------------------------------------
   --  Enumerations <-> the names the saved state uses
   ----------------------------------------------------------------------

   function Block_Image (B : Block_T) return String is
      Raw : constant String := Block_T'Image (B);
   begin
      return Tail (Raw, 2);   --  drop the "B_"
   end Block_Image;

   function Block_From_Image (S : String; Found : out Boolean) return Block_T is
   begin
      for B in Block_T loop
         if Block_Image (B) = S then
            Found := True;
            return B;
         end if;
      end loop;
      Found := False;
      return B_PKG;
   end Block_From_Image;

   function Paren_Kind_Image (K : Paren_Kind_T) return String is
      Raw : constant String := Paren_Kind_T'Image (K);
   begin
      return Tail (Raw, 2);   --  drop the "P_"
   end Paren_Kind_Image;

   function Paren_Kind_From_Image
     (S : String; Found : out Boolean) return Paren_Kind_T is
   begin
      for K in Paren_Kind_T loop
         if Paren_Kind_Image (K) = S then
            Found := True;
            return K;
         end if;
      end loop;
      Found := False;
      return P_PLAIN;
   end Paren_Kind_From_Image;

   ----------------------------------------------------------------------
   --  Lexical helpers
   ----------------------------------------------------------------------

   function Code_Mask (S : String) return Mask_Array is
      N    : constant Natural := S'Length;
      Mask : Mask_Array (0 .. N - 1) := (others => False);
      I    : Natural := 0;
   begin
      while I < N loop
         if Ch (S, I) = '"' then
            I := Skip_Quoted (S, I, '"');
         elsif Ch (S, I) = Apos and then I + 2 < N and then Ch (S, I + 2) = Apos
         then
            I := I + 3;                   --  character literal: skip 'x' whole
         else
            Mask (I) := True;
            I := I + 1;
         end if;
      end loop;
      return Mask;
   end Code_Mask;

   function Paren_Delta (Line : String) return Integer is
      Mask  : constant Mask_Array := Code_Mask (Line);
      Depth : Integer := 0;
   begin
      for I in Mask'Range loop
         if Mask (I) then
            if Ch (Line, I) = '(' then
               Depth := Depth + 1;
            elsif Ch (Line, I) = ')' then
               Depth := Depth - 1;
            end if;
         end if;
      end loop;
      return Depth;
   end Paren_Delta;

   function Last_Word (Code : String) return String is
      Parts : constant Str_Vector :=
        Split_Ws (RStrip_Char (Strip (Code), ';'));
   begin
      if Parts.Is_Empty then
         return "";
      end if;
      declare
         Tok : constant String := -Parts.Last_Element;
         I   : Natural := Tok'Length;
      begin
         if not Is_Ident_Ch (Ch (Tok, Tok'Length - 1)) then
            return Lower (Tok);
         end if;
         while I > 0 and then Is_Ident_Ch (Ch (Tok, I - 1)) loop
            I := I - 1;
         end loop;
         return Lower (Tail (Tok, I));
      end;
   end Last_Word;

   function Ends_With_Condition_Then (Code_S : String) return Boolean is
   begin
      if Last_Word (Code_S) /= "then" then
         return False;
      end if;
      declare
         Head : constant String := Strip (RStrip_Char (Strip (Code_S), ';'));
      begin
         return Last_Word (Slice (Head, 0, Head'Length - 4)) /= "and";
      end;
   end Ends_With_Condition_Then;

   function Code_Words (Code_S : String) return Str_Vector is
      R     : Str_Vector;
      I     : Natural := 0;
      Depth : Integer := 0;
      N     : constant Natural := Code_S'Length;
   begin
      while I < N loop
         if Ch (Code_S, I) = '"' then
            I := Skip_Quoted (Code_S, I, '"');
         elsif Ch (Code_S, I) = Apos and then I + 2 < N
           and then Ch (Code_S, I + 2) = Apos
         then
            I := I + 3;
         elsif Ch (Code_S, I) = '(' then
            Depth := Depth + 1;
            I := I + 1;
         elsif Ch (Code_S, I) = ')' then
            Depth := Integer'Max (0, Depth - 1);
            I := I + 1;
         elsif Is_Ident_Ch (Ch (Code_S, I)) then
            declare
               J : Natural := I;
            begin
               while J < N and then Is_Ident_Ch (Ch (Code_S, J)) loop
                  J := J + 1;
               end loop;
               if Depth = 0 then
                  R.Append (+Lower (Slice (Code_S, I, J)));
               end if;
               I := J;
            end;
         else
            I := I + 1;
         end if;
      end loop;
      return R;
   end Code_Words;

   function Record_Delta (Code_S : String) return Integer is
      Delta_N : Integer := 0;
      Prev    : Ustr := +"";
   begin
      for Wu of Code_Words (Code_S) loop
         if -Wu = "record" then
            if -Prev = "end" then
               Delta_N := Delta_N - 1;
            elsif -Prev /= "null" then
               Delta_N := Delta_N + 1;
            end if;
         end if;
         Prev := Wu;
      end loop;
      return Delta_N;
   end Record_Delta;

   function Has_Condition_Then (Code_S : String) return Boolean is
      Prev : Ustr := +"";
   begin
      for Wu of Code_Words (Code_S) loop
         if -Wu = "then" and then -Prev /= "and" then
            return True;
         end if;
         Prev := Wu;
      end loop;
      return False;
   end Has_Condition_Then;

   function Loop_Delta (Code_S : String) return Integer is
      Delta_N : Integer := 0;
      Prev    : Ustr := +"";
   begin
      for Wu of Code_Words (Code_S) loop
         if -Wu = "loop" then
            if -Prev = "end" then
               Delta_N := Delta_N - 1;
            else
               Delta_N := Delta_N + 1;
            end if;
         end if;
         Prev := Wu;
      end loop;
      return Delta_N;
   end Loop_Delta;

   function If_Delta (Code_S : String) return Integer is
      Delta_N : Integer := 0;
      Prev    : Ustr := +"";
   begin
      for Wu of Code_Words (Code_S) loop
         if -Wu = "if" then
            if -Prev = "end" then
               Delta_N := Delta_N - 1;
            else
               Delta_N := Delta_N + 1;
            end if;
         end if;
         Prev := Wu;
      end loop;
      return Delta_N;
   end If_Delta;

   function Unmatched_Ends (Code_S : String) return Natural is
      Open_N  : Natural := 0;
      Result : Natural := 0;
      Prev   : Ustr := +"";
      Head   : constant Boolean :=
        Lead_Keyword (Code_S) in
          "package" | "procedure" | "function" | "task" | "protected" | "entry";
   begin
      for Wu of Code_Words (Code_S) loop
         declare
            W : constant String := -Wu;
            P : constant String := -Prev;
         begin
            if W = "end" then
               if Open_N > 0 then
                  Open_N := Open_N - 1;
               else
                  Result := Result + 1;
               end if;
            elsif P /= "end"
              and then W in "if" | "loop" | "case" | "select" | "begin" | "do"
            then
               Open_N := Open_N + 1;
            elsif W = "record" and then P /= "end" and then P /= "null" then
               Open_N := Open_N + 1;
            elsif W = "is" and then Head and then Open_N = 0 then
               Open_N := Open_N + 1;
            end if;
         end;
         Prev := Wu;
      end loop;
      return Result;
   end Unmatched_Ends;

   function Is_Then_Abort (Code_S : String) return Boolean is
   begin
      return Join (Split_Ws (Lower (Code_S)), " ") = "then abort";
   end Is_Then_Abort;

   function Stmt_Incomplete (Code_S : String) return Boolean is
   begin
      if Code_S = "" or else Ends_With (Code_S, ";")
        or else Ends_With (Code_S, "=>") or else Ends_With (Code_S, ":")
        or else Ends_With (Code_S, ">>")
      then
         return False;
      end if;
      declare
         LW : constant String := Lower (Lead_Ident (Code_S));
      begin
         --  'separate (Parent)' is a complete compilation-unit prefix.
         if LW = "separate" then
            return False;
         end if;
         --  A *bare* splitter/opener keyword line is complete.
         if Lower (Code_S) = LW
           and then LW in "begin" | "declare" | "else" | "exception"
                        | "or" | "private" | "select" | "generic"
         then
            return False;
         end if;
         if Is_Then_Abort (Code_S) then
            return False;
         end if;
         declare
            LT : constant String := Last_Word (Code_S);
         begin
            --  'subtype T is' is not a block opener.
            if LT = "is" and then LW = "subtype" then
               return True;
            end if;
            return LT not in "is" | "then" | "loop" | "record" | "select"
                           | "do" | "overriding" | "begin" | "declare";
         end;
      end;
   end Stmt_Incomplete;

   function Ends_With_Operator (Code_S : String) return Boolean is
      T : constant String := RStrip (Code_S);
   begin
      if T = "" then
         return False;
      end if;
      if Ch (T, T'Length - 1) in '&' | '+' | '-' | '*' | '/' | '=' | '<' | '>' | '|'
      then
         return True;
      end if;
      return Last_Word (T) in "and" | "or" | "xor" | "then" | "else" | "in"
                            | "mod" | "rem" | "not";
   end Ends_With_Operator;

   function Starts_With_Operator (Code_S : String) return Boolean is
   begin
      if Code_S = "" then
         return False;
      end if;
      case Ch (Code_S, 0) is
         when ':' =>
            return Code_S'Length > 1 and then Ch (Code_S, 1) = '=';
         when '.' =>
            return Code_S'Length > 1 and then Ch (Code_S, 1) = '.';
         when '=' | '&' | '+' | '-' | '*' | '/' | '<' | '>' | '|' =>
            return True;
         when others =>
            return Lower (Lead_Ident (Code_S)) in
              "and" | "or" | "xor" | "mod" | "rem";
      end case;
   end Starts_With_Operator;

   function Is_Term_Continuation (Code_S : String) return Boolean is
   begin
      if Code_S = "" then
         return False;
      end if;
      if Starts_With (Code_S, "(") then
         return True;
      end if;
      if not Starts_With_Operator (Code_S)
        or else Starts_With (Code_S, ":=") or else Starts_With (Code_S, "=>")
        or else Starts_With (Code_S, "|")
      then
         return False;
      end if;
      declare
         W : constant String := Lower (Lead_Ident (Code_S));
      begin
         if W in "and" | "or" then
            return True;
         end if;
         return W /= "xor";
      end;
   end Is_Term_Continuation;

   function Body_Follows_Arrow (Text : String) return Boolean is
      Mask  : constant Mask_Array := Code_Mask (Text);
      Depth : Integer := 0;
   begin
      for K in Mask'Range loop
         if Mask (K) then
            case Ch (Text, K) is
               when '(' =>
                  Depth := Depth + 1;
               when ')' =>
                  if Depth = 0 then
                     return False;
                  end if;
                  Depth := Depth - 1;
               when '=' =>
                  if Depth = 0 and then K + 1 < Text'Length
                    and then Ch (Text, K + 1) = '>'
                  then
                     declare
                        Rest : constant String := Strip (Tail (Text, K + 2));
                     begin
                        return Rest /= "" and then not Starts_With (Rest, "--");
                     end;
                  end if;
               when others =>
                  null;
            end case;
         end if;
      end loop;
      return False;
   end Body_Follows_Arrow;

   function Scan_Parens
     (Text : String; Base_Depth : Integer; Base_Col : Integer)
     return Paren_Vector
   is
      Openers : Paren_Vector;
      Depth   : Integer := Base_Depth;
      N       : constant Natural := Text'Length;
      Mask    : constant Mask_Array := Code_Mask (Text);
   begin
      for I in Mask'Range loop
         if Mask (I) then
            if Ch (Text, I) = ')' then
               Depth := Depth - 1;
            elsif Ch (Text, I) = '(' then
               Depth := Depth + 1;
               declare
                  J    : constant Natural := Skip_Ch (Text, I + 1, ' ');
                  KW   : constant String := Lower (Lead_Ident (Tail (Text, J)));
                  Kind : Paren_Kind_T := P_PLAIN;
               begin
                  if KW = "if" then
                     Kind := P_IF_EXPR;
                  elsif KW = "case" then
                     Kind := P_CASE_EXPR;
                  elsif KW = "for" then
                     Kind := P_FOR_EXPR;
                  end if;
                  --  A '(for' whose predicate starts beside its arrow is
                  --  continued like a plain parenthesis.
                  if Kind = P_FOR_EXPR
                    and then Body_Follows_Arrow (Tail (Text, I + 1))
                  then
                     Kind := P_PLAIN;
                  end if;
                  Openers.Append
                    ((Level => Depth,
                      Col   => Base_Col + (if J < N then J else Indent_Width),
                      Kind  => Kind));
               end;
            end if;
         end if;
      end loop;
      return Openers;
   end Scan_Parens;

   ----------------------------------------------------------------------
   --  Construct names
   ----------------------------------------------------------------------

   function Is_Name_Qualifier (W : String) return Boolean is
     (W in "package" | "procedure" | "function" | "task" | "protected"
         | "entry" | "type" | "subtype" | "generic" | "overriding"
         | "not" | "separate" | "body");

   function Is_Name_Opener (W : String) return Boolean is
     (W in "package" | "procedure" | "function" | "task" | "protected"
         | "entry" | "type" | "subtype" | "generic" | "overriding"
         | "not" | "separate");

   function Is_End_Keyword (W : String) return Boolean is
     (W in "if" | "loop" | "case" | "record" | "select" | "return");

   function Is_Resync_Word (W : String) return Boolean is
     (W in "begin" | "end" | "declare" | "exception" | "package"
         | "procedure" | "function" | "pragma" | "type" | "subtype" | "use"
         | "loop" | "while" | "exit" | "goto" | "delay" | "accept" | "entry"
         | "task" | "protected" | "generic" | "separate" | "select");

   function Input_Column (Line : String) return Integer is
      Col : Integer := 0;
   begin
      for I in 0 .. Line'Length - 1 loop
         case Ch (Line, I) is
            when ' '        => Col := Col + 1;
            when ASCII.HT   => Col := Col + 8 - Col mod 8;
            when others     => return Col;
         end case;
      end loop;
      return Col;
   end Input_Column;

   function Lead_Words (Code_S : String) return Str_Vector is
      R : Str_Vector;
      I : Natural := 0;
      N : constant Natural := Code_S'Length;
   begin
      while I < N loop
         I := Skip_Space (Code_S, I);
         exit when I >= N;
         exit when not Is_Ident_Ch (Ch (Code_S, I)) and then Ch (Code_S, I) /= '.';
         declare
            J : Natural := I;
         begin
            while J < N and then (Is_Ident_Ch (Ch (Code_S, J))
                                  or else Ch (Code_S, J) = '.')
            loop
               J := J + 1;
            end loop;
            R.Append (+Slice (Code_S, I, J));
            I := J;
         end;
      end loop;
      return R;
   end Lead_Words;

   function Declared_Name (Code_S : String) return String is
      Ws : constant Str_Vector := Lead_Words (Code_S);
   begin
      if Ws.Is_Empty then
         return "";
      end if;
      if Is_Name_Opener (Lower (-Ws.First_Element)) then
         declare
            I : Natural := 0;
         begin
            while I < Natural (Ws.Length)
              and then Is_Name_Qualifier (Lower (-Ws (I)))
            loop
               I := I + 1;
            end loop;
            return (if I < Natural (Ws.Length) then -Ws (I) else "");
         end;
      end if;
      --  A label: one identifier, a ':', then either nothing or the
      --  construct it labels.  'X : Integer := 0;' has the same shape and is
      --  a variable, so the word after the colon has to open a block.
      declare
         First : constant String := -Ws.First_Element;
         After : constant Natural := Skip_Space (Code_S, First'Length);
      begin
         if After >= Code_S'Length or else Ch (Code_S, After) /= ':' then
            return "";
         end if;
         if After + 1 < Code_S'Length and then Ch (Code_S, After + 1) = '='
         then
            return "";
         end if;
         declare
            Rest : constant String := Strip (Tail (Code_S, After + 1));
         begin
            if Rest = "" or else Lower (Lead_Ident (Rest)) in
              "declare" | "begin" | "for" | "while" | "loop"
            then
               return First;
            end if;
            return "";
         end;
      end;
   end Declared_Name;

   function Lead_Keyword (Code_S : String) return String is
      Ws : constant Str_Vector := Lead_Words (Code_S);
      I  : Natural := 0;
   begin
      while I < Natural (Ws.Length)
        and then Lower (-Ws (I)) in "not" | "overriding" | "private"
      loop
         I := I + 1;
      end loop;
      return (if I < Natural (Ws.Length) then Lower (-Ws (I)) else "");
   end Lead_Keyword;

   function End_Name (Code_S : String) return String is
      Ws : constant Str_Vector := Lead_Words (Code_S);
      I  : Natural := 1;
   begin
      if Ws.Is_Empty or else Lower (-Ws.First_Element) /= "end" then
         return "";
      end if;
      if I < Natural (Ws.Length) and then Is_End_Keyword (Lower (-Ws (I))) then
         I := I + 1;
      end if;
      return (if I < Natural (Ws.Length) then -Ws (I) else "");
   end End_Name;

end Ada_Scan;
