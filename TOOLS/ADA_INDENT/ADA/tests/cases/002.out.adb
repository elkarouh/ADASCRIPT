package Shapes is
  type Point is record
    X : Float;
    Y : Float;
  end record;
private
  Origin : constant Point := (0.0, 0.0);
end Shapes;
