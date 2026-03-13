# ============================================================================
# Test 1: Basic virtual class with dynamic dispatch
# ============================================================================
echo "--- Test 1: Basic virtual class + dynamic dispatch ---"

@virtual
class Shape:
  var name: str
  def __init__(self, name: str):
    self.name = name
  def area(self) -> float:
    0.0
  def describe(self) -> str:
    f"{self.name}: area= {self.area()}"

@virtual
class Circle(Shape):
  var radius: float
  def __init__(self, radius: float):
    super().__init__("Circle")   # initialize parent fields
    self.radius = radius
  def area(self) -> float:
    3.14159 * self.radius * self.radius
