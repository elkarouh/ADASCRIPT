procedure P is
  Coordination_Fix : constant Def_Location.T :=
    (if C
     then (Def_Location.GPS, X => Y)
     else (Def_Location.ICAO_Aerodrome,
           Aerodrome => Def_Aerodrome.Convert
             (Env_Location.Value (A))));
begin
  null;
end P;
