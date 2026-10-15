package P is
  Name : constant String := A
    & (if C
       then "0"
       else Trim (X))
    & "_";
end P;
