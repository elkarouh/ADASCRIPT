procedure P is
begin
  Write (Bin_File => F,
         Query => Q,
         Validate => False
         -- the file stays open for an hour
         -- no need to validate now
         );
end P;
