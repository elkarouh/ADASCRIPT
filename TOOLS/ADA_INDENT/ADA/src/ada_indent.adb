--  ada_indent - a simplified Ada source re-indenter.
--
--  This is NOT a full Ada parser.  It implements only the slice of Ada
--  grammar that matters for indentation: the keywords that open, close, or
--  split an indented block.  Everything else is treated as an ordinary
--  statement line.  See ../docs/INDENTATION.md for the grammar.

with Ada.Command_Line;
with Ada.Streams;       use Ada.Streams;
with Ada.Streams.Stream_IO;
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Text_IO.Text_Streams;
with Indenter;
with Ada.Strings.Unbounded;
with Strscan;           use Strscan;

procedure Ada_Indent is

   --  Split a stream into lines at LF, CR LF or a lone CR.  A final line
   --  terminator does not start another line, but a blank line before the end
   --  of the file is a line (Text_IO.End_Of_File would drop it).
   procedure Read_Lines
     (Stream : not null access Root_Stream_Type'Class; Lines : in out Str_Vector)
   is
      Buffer   : Stream_Element_Array (1 .. 65_536);
      Last     : Stream_Element_Offset;
      Current  : Ustr := +"";
      Pending  : Boolean := False;   --  Current holds the start of a line
      After_CR : Boolean := False;
   begin
      loop
         Read (Stream.all, Buffer, Last);
         exit when Last < Buffer'First;
         for I in Buffer'First .. Last loop
            declare
               C : constant Character := Character'Val (Buffer (I));
            begin
               if After_CR and then C = ASCII.LF then
                  After_CR := False;          --  the LF of a CR LF
               else
                  After_CR := False;
                  if C = ASCII.LF or else C = ASCII.CR then
                     Lines.Append (Current);
                     Current := +"";
                     Pending := False;
                     After_CR := C = ASCII.CR;
                  else
                     Ada.Strings.Unbounded.Append (Current, C);
                     Pending := True;
                  end if;
               end if;
            end;
         end loop;
      end loop;
      if Pending then
         Lines.Append (Current);
      end if;
   end Read_Lines;

   procedure Usage is
   begin
      Put_Line ("Usage: ada_indent [OPTIONS] [FILE]");
      New_Line;
      Put_Line ("Indent Ada source code.  Reads FILE, or stdin when FILE is omitted.");
      Put_Line ("Output is written to stdout; each source line is replaced by its");
      Put_Line ("correctly-indented form (indentation step: 2 spaces, spaces only).");
      New_Line;
      Put_Line ("Options:");
      Put_Line ("  -h, --help          Show this help and exit.");
      Put_Line ("  --emit-state        After each output line emit a state snapshot on a separate line of the");
      Put_Line ("                      form  ##STATE:<data>  that captures the indenter's full parse state.");
      Put_Line ("                      Consumed by emacs integration to enable incremental re-indentation.");
      Put_Line ("  --state <data>      Restore the indenter from a previously-emitted state snapshot before processing");
      Put_Line ("                      the first input line.  Must  precede the lines the snapshot refers to.");
      Put_Line ("  -q, --quiet         Suppress the stderr diagnostics reported when an 'end' line contradicts");
      Put_Line ("                      the block structure seen so far.  The indenting is unaffected: the same");
      Put_Line ("                      resynchronisation happens either way, it is just not reported.");
      New_Line;
   end Usage;

   Ind           : Indenter.Indenter_T;
   Do_Emit_State : Boolean := False;
   File_Arg      : Ustr := +"";   --  empty until a non-option argument names one
   Lines         : Str_Vector;
   Input         : Ada.Streams.Stream_IO.File_Type;
   Argc          : constant Natural := Ada.Command_Line.Argument_Count;
   Ai            : Natural := 1;

begin
   while Ai <= Argc loop
      declare
         A : constant String := Ada.Command_Line.Argument (Ai);
      begin
         if A = "-h" or else A = "--help" then
            Usage;
            return;
         elsif A = "--emit-state" then
            Do_Emit_State := True;
         elsif A = "-q" or else A = "--quiet" then
            Ind.Warn := False;
         elsif A = "--state" then
            if Ai + 1 <= Argc then
               Ai := Ai + 1;
               Indenter.Load_State (Ind, Ada.Command_Line.Argument (Ai));
            end if;
         else
            File_Arg := +A;
         end if;
      end;
      Ai := Ai + 1;
   end loop;

   if -File_Arg /= "" then
      begin
         Ada.Streams.Stream_IO.Open
           (Input, Ada.Streams.Stream_IO.In_File, -File_Arg);
      exception
         when Name_Error | Use_Error =>
            Put_Line (Standard_Error, "ada_indent: cannot open " & (-File_Arg));
            Ada.Command_Line.Set_Exit_Status (Ada.Command_Line.Failure);
            return;
      end;
      Read_Lines (Ada.Streams.Stream_IO.Stream (Input), Lines);
      Ada.Streams.Stream_IO.Close (Input);
   else
      Read_Lines (Ada.Text_IO.Text_Streams.Stream (Current_Input), Lines);
   end if;

   --  Whole input first: a comment opening a paragraph takes the column of
   --  the code line after it (see Indent_Lines), so it cannot be printed
   --  before that line has been read.
   Ind.Keep_States := Do_Emit_State;
   declare
      Outs : constant Str_Vector := Indenter.Indent_Lines (Ind, Lines);
   begin
      for I in 0 .. Natural (Outs.Length) - 1 loop
         Put_Line (-Outs (I));
         if Do_Emit_State then
            Put_Line ("##STATE:" & (-Ind.States (I)));
         end if;
      end loop;
   end;
end Ada_Indent;
