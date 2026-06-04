with Ada.Text_IO; use Ada.Text_IO;

procedure Sample is

   type Color is (Red, Green, Blue);

   function Name (C : Color) return String is
   begin
      case C is
         when Red =>
            return "red";
         when Green =>
            return "green";
         when others =>
            return "blue";
      end case;
   end Name;

   type Point is record
      X : Float;
      Y : Float;
   end record;

   Origin : constant Point := (X => 0.0,
      Y => 0.0);

begin
   Main_Loop : for I in 1 .. 3 loop
      if I mod 2 = 0 then
         Put_Line ("even");
      else
         Put_Line ("odd:" & Name (Blue));
      end if;
   end loop Main_Loop;

   declare
      Total : Integer := 0;
   begin
      Total := Total + 1;
   exception
      when Constraint_Error =>
         Put_Line ("overflow");
   end;
end Sample;
