package body Strscan is

   function Is_Digit_Ch (C : Character) return Boolean is
     (C in '0' .. '9');

   function Is_Alpha_Ch (C : Character) return Boolean is
     (C in 'a' .. 'z' or else C in 'A' .. 'Z');

   function Is_Alnum_Ch (C : Character) return Boolean is
     (Is_Alpha_Ch (C) or else Is_Digit_Ch (C));

   function Is_Ident_Ch (C : Character) return Boolean is
     (Is_Alnum_Ch (C) or else C = '_');

   function Is_Space_Ch (C : Character) return Boolean is
     (Character'Pos (C) in 32 | 9 | 10 | 13);

   function Is_Blank_Ch (C : Character) return Boolean is
     (Character'Pos (C) in 32 | 9 | 10 | 11 | 12 | 13);

   ----------------------------------------------------------------------

   function Slice (S : String; Lo, Hi : Integer) return String is
      L : constant Integer := Integer'Max (0, Lo);
      H : constant Integer := Integer'Min (S'Length, Hi);
   begin
      if H <= L then
         return "";
      end if;
      declare
         R : constant String (1 .. H - L) :=
           S (S'First + L .. S'First + H - 1);
      begin
         return R;
      end;
   end Slice;

   function Tail (S : String; Lo : Integer) return String is
   begin
      return Slice (S, Lo, S'Length);
   end Tail;

   function LStrip (S : String) return String is
      I : Natural := 0;
   begin
      while I < S'Length and then Is_Blank_Ch (Ch (S, I)) loop
         I := I + 1;
      end loop;
      return Tail (S, I);
   end LStrip;

   function RStrip (S : String) return String is
      N : Natural := S'Length;
   begin
      while N > 0 and then Is_Blank_Ch (Ch (S, N - 1)) loop
         N := N - 1;
      end loop;
      return Slice (S, 0, N);
   end RStrip;

   function Strip (S : String) return String is
   begin
      return LStrip (RStrip (S));
   end Strip;

   function RStrip_Char (S : String; C : Character) return String is
      N : Natural := S'Length;
   begin
      while N > 0 and then Ch (S, N - 1) = C loop
         N := N - 1;
      end loop;
      return Slice (S, 0, N);
   end RStrip_Char;

   function Lower (S : String) return String is
      R : String (1 .. S'Length);
   begin
      for I in R'Range loop
         declare
            C : constant Character := S (S'First + I - 1);
         begin
            if C in 'A' .. 'Z' then
               R (I) := Character'Val (Character'Pos (C) + 32);
            else
               R (I) := C;
            end if;
         end;
      end loop;
      return R;
   end Lower;

   function Starts_With (S, Prefix : String) return Boolean is
   begin
      return S'Length >= Prefix'Length
        and then Slice (S, 0, Prefix'Length) = Prefix;
   end Starts_With;

   function Ends_With (S, Suffix : String) return Boolean is
   begin
      return S'Length >= Suffix'Length
        and then Tail (S, S'Length - Suffix'Length) = Suffix;
   end Ends_With;

   function Find_Char (S : String; C : Character) return Integer is
   begin
      for I in 0 .. S'Length - 1 loop
         if Ch (S, I) = C then
            return I;
         end if;
      end loop;
      return -1;
   end Find_Char;

   function Repeat_Space (N : Integer) return String is
   begin
      if N <= 0 then
         return "";
      end if;
      return (1 .. N => ' ');
   end Repeat_Space;

   function Split_Ws (S : String) return Str_Vector is
      R : Str_Vector;
      I : Natural := 0;
      N : constant Natural := S'Length;
   begin
      while I < N loop
         while I < N and then Is_Blank_Ch (Ch (S, I)) loop
            I := I + 1;
         end loop;
         exit when I >= N;
         declare
            J : Natural := I;
         begin
            while J < N and then not Is_Blank_Ch (Ch (S, J)) loop
               J := J + 1;
            end loop;
            R.Append (+Slice (S, I, J));
            I := J;
         end;
      end loop;
      return R;
   end Split_Ws;

   function Split_On (S : String; Sep : Character) return Str_Vector is
      R     : Str_Vector;
      Start : Natural := 0;
   begin
      for I in 0 .. S'Length - 1 loop
         if Ch (S, I) = Sep then
            R.Append (+Slice (S, Start, I));
            Start := I + 1;
         end if;
      end loop;
      R.Append (+Tail (S, Start));
      return R;
   end Split_On;

   function Join (V : Str_Vector; Sep : String) return String is
      R : Ustr;
      First : Boolean := True;
   begin
      for E of V loop
         if not First then
            Append (R, Sep);
         end if;
         Append (R, E);
         First := False;
      end loop;
      return -R;
   end Join;

   function Img (N : Integer) return String is
      Raw : constant String := Integer'Image (N);
   begin
      if Raw (Raw'First) = ' ' then
         return Tail (Raw, 1);
      end if;
      return Slice (Raw, 0, Raw'Length);
   end Img;

   ----------------------------------------------------------------------

   function Skip_Ch (S : String; I : Natural; C : Character) return Natural is
      J : Natural := I;
   begin
      while J < S'Length and then Ch (S, J) = C loop
         J := J + 1;
      end loop;
      return J;
   end Skip_Ch;

   function Skip_Space (S : String; I : Natural) return Natural is
      J : Natural := I;
   begin
      while J < S'Length and then Is_Space_Ch (Ch (S, J)) loop
         J := J + 1;
      end loop;
      return J;
   end Skip_Space;

   function Skip_Quoted (S : String; I : Natural; Quote : Character)
     return Natural
   is
      J : Natural := I + 1;
   begin
      while J < S'Length and then Ch (S, J) /= Quote loop
         J := J + 1;
      end loop;
      return J + 1;
   end Skip_Quoted;

   ----------------------------------------------------------------------

   function Lead_Ident (S : String) return String is
      T : constant String := Strip (S);
      N : Natural := 0;
   begin
      while N < T'Length and then Is_Ident_Ch (Ch (T, N)) loop
         N := N + 1;
      end loop;
      return Slice (T, 0, N);
   end Lead_Ident;

   function Strip_Line_Comment
     (Line : String; Marker : String; Quote : Character) return String
   is
      N      : constant Natural := Line'Length;
      M      : constant Natural := Marker'Length;
      I      : Natural := 0;
      In_Str : Boolean := False;
   begin
      while I < N loop
         if not In_Str and then M > 0 and then I + M <= N
           and then Slice (Line, I, I + M) = Marker
         then
            exit;
         end if;
         if Ch (Line, I) = Quote then
            In_Str := not In_Str;
         end if;
         I := I + 1;
      end loop;
      return Slice (Line, 0, I);
   end Strip_Line_Comment;

end Strscan;
