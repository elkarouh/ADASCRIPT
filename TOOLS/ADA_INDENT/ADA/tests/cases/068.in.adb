package body P is
type Base_Obj_T is abstract tagged null record;
package Base_Tree is new Tree_Element_G (Base_Obj_T);
procedure Q is
begin
for I in 1 .. 3 loop Put (I); end loop;
type R is record F : Integer; end record;
for J in F (X) loop Put (J); end loop;
Next_Statement;
end Q;
end P;
