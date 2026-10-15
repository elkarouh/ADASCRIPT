--  ada_scan.ads - the lexical helpers of the indenter: everything that looks
--  at a single physical line and knows nothing of the block stack.
--
--  Indices are 0-based, as in Strscan.  The line-level functions expect
--  comments to be removed already (see Strscan.Strip_Line_Comment).

with Ada.Containers.Vectors;
with Strscan;  use Strscan;

package Ada_Scan is

   Indent_Width : constant := 2;

   --  The indentation-significant constructs.  A frame is pushed for each
   --  open block; the kind is only consulted where it changes behaviour.
   --  (The B_ prefix keeps the names clear of Ada's reserved words.)
   type Block_T is
     (B_PKG,          --  package / subprogram / task / protected / type spec opened by trailing 'is'
      B_TYPE_HEADER,  --  'type T is' on its own line - pairs with RECORD below it
      B_DECLARE,      --  a declare block (block label or bare 'declare')
      B_BLOCK,        --  a begin ... end region (statement part)
      B_IF,           --  if ... then
      B_LOOP,         --  [while/for] ... loop
      B_CASE,         --  case ... is
      B_WHEN,         --  when ... =>   (case alternative or exception handler)
      B_RECORD,       --  record  ... end record
      B_SELECT,       --  select ... end select
      B_DO,           --  accept ... do  /  return ... do  (extended return)
      B_GENERIC);     --  'generic' - its formal part, closed by the unit it introduces

   function Block_Image (B : Block_T) return String;
   --  "PKG", "TYPE_HEADER", ... as the saved state spells them.

   function Block_From_Image (S : String; Found : out Boolean) return Block_T;

   --  Kind of a parenthesised expression, for indentation purposes.
   type Paren_Kind_T is
     (P_OUTSIDE,    --  sentinel: entry_top_kind when the paren stack is empty
      P_PLAIN,      --  plain parenthesis
      P_IF_EXPR,    --  (if ... then ... else ...)
      P_CASE_EXPR,  --  (case ... is when ...)
      P_FOR_EXPR);  --  (for ... => ...)  quantified or iterated expression

   function Paren_Kind_Image (K : Paren_Kind_T) return String;
   function Paren_Kind_From_Image
     (S : String; Found : out Boolean) return Paren_Kind_T;

   --  One open '(' : the depth just inside it, the output column its
   --  continuations align to, and its kind.
   type Paren_Entry is record
      Level : Integer;
      Col   : Integer;
      Kind  : Paren_Kind_T;
   end record;

   package Paren_Vectors is new Ada.Containers.Vectors (Natural, Paren_Entry);
   subtype Paren_Vector is Paren_Vectors.Vector;

   ----------------------------------------------------------------------
   --  Lexical helpers - all work on a single physical line.
   ----------------------------------------------------------------------

   function Code_Mask (S : String) return Mask_Array;
   --  True at each index of S that is outside a string or character literal
   --  (the characters code_positions yields).

   function Paren_Delta (Line : String) return Integer;
   --  Net '(' minus ')' on the line.

   function Last_Word (Code : String) return String;
   --  Lowercased final token, after dropping a trailing ';'.  "" if empty.

   function Ends_With_Condition_Then (Code_S : String) return Boolean;
   function Code_Words (Code_S : String) return Str_Vector;
   function Record_Delta (Code_S : String) return Integer;
   function Has_Condition_Then (Code_S : String) return Boolean;
   function Loop_Delta (Code_S : String) return Integer;
   function If_Delta (Code_S : String) return Integer;
   function Unmatched_Ends (Code_S : String) return Natural;
   function Is_Then_Abort (Code_S : String) return Boolean;
   function Stmt_Incomplete (Code_S : String) return Boolean;
   function Ends_With_Operator (Code_S : String) return Boolean;
   function Starts_With_Operator (Code_S : String) return Boolean;
   function Is_Term_Continuation (Code_S : String) return Boolean;
   function Body_Follows_Arrow (Text : String) return Boolean;

   function Scan_Parens
     (Text : String; Base_Depth : Integer; Base_Col : Integer)
     return Paren_Vector;

   ----------------------------------------------------------------------
   --  Construct names - the anchors an 'end' line is checked against.
   ----------------------------------------------------------------------

   function Is_End_Keyword (W : String) return Boolean;
   --  'end <kw>' names a construct KIND, not an instance.

   function Is_Resync_Word (W : String) return Boolean;
   --  Words that can never appear inside an expression or a condition.

   function Input_Column (Line : String) return Integer;
   function Lead_Words (Code_S : String) return Str_Vector;
   function Declared_Name (Code_S : String) return String;
   function Lead_Keyword (Code_S : String) return String;
   function End_Name (Code_S : String) return String;

end Ada_Scan;
