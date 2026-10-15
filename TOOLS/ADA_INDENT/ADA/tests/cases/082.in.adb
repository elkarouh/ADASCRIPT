package P is
type Ref_Count_T is
new Integer range -1 .. 9;
type T is private;
Offset : constant Storage_Offset := 8;
end P;
