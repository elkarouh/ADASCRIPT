--  strscan.ads - character classification, the small scanners a hand-written
--  lexer keeps needing, and the few Python/Nim string idioms the indenter
--  leans on (strip, split, slice).
--
--  Counterpart of TO_NIM/STDLIB/strscan.ady.  Every classifier is defined by
--  ASCII range, and every index in this package is 0-BASED, exactly as in the
--  Adascript source: S (S'First + I) is character I, and a slice is
--  Slice (S, Lo, Hi) = S[Lo:Hi] (half open, clamped like Python's).  Strings
--  that come back from this package always have bounds 1 .. N.

with Ada.Containers.Vectors;
with Ada.Strings.Unbounded;

package Strscan is

   use Ada.Strings.Unbounded;

   subtype Ustr is Unbounded_String;

   function "+" (S : String) return Ustr renames To_Unbounded_String;
   function "-" (U : Ustr) return String renames To_String;

   package Str_Vectors is new Ada.Containers.Vectors (Natural, Ustr);
   subtype Str_Vector is Str_Vectors.Vector;

   package Int_Vectors is new Ada.Containers.Vectors (Natural, Integer);
   subtype Int_Vector is Int_Vectors.Vector;

   --  A mask over the characters of a string (index 0 .. Length - 1).
   type Mask_Array is array (Integer range <>) of Boolean;

   ----------------------------------------------------------------------
   --  Character classification
   ----------------------------------------------------------------------

   function Is_Digit_Ch (C : Character) return Boolean;
   function Is_Alpha_Ch (C : Character) return Boolean;
   function Is_Alnum_Ch (C : Character) return Boolean;
   function Is_Ident_Ch (C : Character) return Boolean;
   function Is_Space_Ch (C : Character) return Boolean;
   --  The set str.strip() removes: blank, HT, LF, VT, FF, CR.
   function Is_Blank_Ch (C : Character) return Boolean;

   ----------------------------------------------------------------------
   --  Python-style string idioms
   ----------------------------------------------------------------------

   function Ch (S : String; I : Natural) return Character is (S (S'First + I));

   function Slice (S : String; Lo, Hi : Integer) return String;
   --  S[Lo:Hi] for non-negative Lo and Hi.

   function Tail (S : String; Lo : Integer) return String;
   --  S[Lo:]

   function Strip (S : String) return String;
   function LStrip (S : String) return String;
   function RStrip (S : String) return String;
   function RStrip_Char (S : String; C : Character) return String;
   --  S.rstrip (C): every trailing C goes.

   function Lower (S : String) return String;

   function Starts_With (S, Prefix : String) return Boolean;
   function Ends_With (S, Suffix : String) return Boolean;

   function Find_Char (S : String; C : Character) return Integer;
   --  Index of the first C, or -1.

   function Repeat_Space (N : Integer) return String;
   --  " " * N, empty for N <= 0.

   function Split_Ws (S : String) return Str_Vector;
   --  S.split ()

   function Split_On (S : String; Sep : Character) return Str_Vector;
   --  S.split (Sep), with Python's behaviour on empty fields.

   function Join (V : Str_Vector; Sep : String) return String;

   function Img (N : Integer) return String;
   --  str (N), without Ada's leading blank.

   ----------------------------------------------------------------------
   --  Scanners - each takes the index to start at and returns the one to
   --  go on at.
   ----------------------------------------------------------------------

   function Skip_Ch (S : String; I : Natural; C : Character) return Natural;
   function Skip_Space (S : String; I : Natural) return Natural;
   function Skip_Quoted (S : String; I : Natural; Quote : Character)
     return Natural;

   ----------------------------------------------------------------------
   --  Whole-token and whole-line helpers
   ----------------------------------------------------------------------

   function Lead_Ident (S : String) return String;
   --  The identifier S begins with, after leading blanks, or "".

   function Strip_Line_Comment
     (Line : String; Marker : String; Quote : Character) return String;
   --  The line with any trailing comment removed, string literals kept.

end Strscan;
