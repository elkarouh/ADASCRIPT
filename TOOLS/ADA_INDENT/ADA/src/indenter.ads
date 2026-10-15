--  indenter.ads - the stack machine that re-indents Ada source.
--
--  Counterpart of the Indenter class of ada_indent.ady; see that file (and
--  ../README.md) for the model.  Each open construct pushes a frame; the
--  display indent of a line is the stack depth (times the indent width),
--  with small adjustments for the keywords that align with their opener
--  rather than the block body.

with Ada.Containers.Vectors;
with Ada_Scan;  use Ada_Scan;
with Strscan;   use Strscan;

package Indenter is

   package Block_Vectors is new Ada.Containers.Vectors (Natural, Block_T);

   type Indenter_T is record
      Stack          : Block_Vectors.Vector;
      Frame_Names    : Str_Vector;  --  name of each open frame, "" when it has none;
                                    --  kept in step with Stack by Push_Frame/Pop_Frame
      Closed_Names   : Str_Vector;  --  "name:depth" of named frames closed by a nameless
                                    --  'end' (most recent last)
      Unopened_Heads : Str_Vector;  --  declaration heads that have neither opened a frame
                                    --  nor ended in ';' (a spec)
      Pending_Label  : Ustr := +""; --  a bare 'Outer :' label line awaiting its block
      Frame_Name     : Ustr := +""; --  the name declared by the logical line being read
      Spec_Name      : Ustr := +""; --  name of the deferred 'function ... is' header
      Lnum           : Integer := 0;       --  physical line number, for diagnostics
      Warn           : Boolean := True;    --  report 'end' lines that contradict the stack
      Paren_Depth    : Integer := 0;
      Pending_Spec   : Boolean := False;   --  a 'function ... is' header whose body kind is unknown
      Cont_Kw        : Ustr := +"";        --  the keyword that opened the declaration being continued
      Pending_Inst   : Boolean := False;   --  an 'X is\nnew Y' PKG frame to pop when done
      Cond_State     : Integer := 0;       --  1 = inside multi-line 'if' condition, 2 = 'elsif'
      Cond_Base      : Integer := 0;       --  display depth of the opening if/elsif
      Cond_Value_Base : Integer := 0;      --  display level of the line holding the current term
      In_Cont        : Boolean := False;   --  previous line was an unterminated statement
      Value_Base     : Integer := 0;       --  display level where the value expression starts
      Last_Lead      : Integer := 0;       --  indent column of the last code line
      Kept_Comment   : Boolean := False;   --  the last line was a comment kept at its hand-placed column
      Keep_States    : Boolean := False;   --  Indent_Lines records Dump_State after every line
      States         : Str_Vector;         --  ...here, for --emit-state
      Ref_Orig       : Int_Vector;         --  per paren depth: the input column of the last code
      Ref_New        : Int_Vector;         --  line that started at that depth, and its output column
      Last_Ends_Name : Boolean := False;   --  the last code line ended in a name
      Spill_Col      : Integer := -1;      --  column for continuation lines of a spilled sub-expression
      Paren_Stack    : Paren_Vector;       --  every open '('
      Paren_Cont     : Boolean := False;   --  prev line within plain paren ended without ','
      Arrow_Level    : Integer := 0;       --  innermost paren level with a '=>' value spill (0 = none)
      Paren_Next_Lead       : Integer := 0;   --  column where the next code line in this paren lands
      Paren_Next_Lead_Depth : Integer := -1;  --  paren depth that applies to (-1 = none)
      Paren_Prev_Lead       : Integer := 0;   --  actual lead column of the previous code line
   end record;

   function Dump_State (Self : Indenter_T) return String;
   --  Serialize the full indenter state to a compact, opaque string.

   procedure Load_State (Self : in out Indenter_T; S : String);
   --  Restore indenter state from a string produced by Dump_State.

   function Indent_Line (Self : in out Indenter_T; Line : String) return String;
   --  Process one raw line and return it re-indented.

   function Indent_Lines
     (Self : in out Indenter_T; Lines : Str_Vector) return Str_Vector;
   --  Re-indent a sequence of lines, with one code line of lookahead.

end Indenter;
