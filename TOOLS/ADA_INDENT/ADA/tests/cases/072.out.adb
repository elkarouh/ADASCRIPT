type File_Iterator_Record_T (Nr_Of_Criteria : Natural_T;
                             Nr_Of_Files    : Positive_T) is
  record
    Smallest_File : Natural_T := 0;
  end record;
procedure Free is new Unchecked_Deallocation (A, B);
