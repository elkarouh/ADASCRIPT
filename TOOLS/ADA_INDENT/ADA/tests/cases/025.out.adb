procedure P is
begin
  if X then
    null;
  elsif not Traffic_Volume_Profile.Element_Exists
    (TV_Profiles.P (FTFM), Env_Regulation_Info.TV_Id (Reg_Info))
  then
    null;
  end if;
end P;
