function F (Field : Column_T) return String is
begin
  case Field is
    when Activation_Column =>
      if Measure.Data.Activation then return Activated;
      else return Deactivated; end if;
    when Source_Column =>
      return "Config";
  end case;
end F;
