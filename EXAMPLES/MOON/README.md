# MOON -- an Earth-Moon landing, translated from Python

`moon_sim.ady` is `moon_sim.py` (a 2-D, Apollo-style mission: TLI, a trans-lunar coast,
LOI-1/LOI-2, undock, DOI, then a closed-loop powered descent through
IMU -> Navigation -> Guidance -> Autopilot -> Propulsion) written in Adascript.

    ady2nim c -r moon_sim.ady --out moon_mission.png      # about 2.5 s
    make test-moon

**Nim only**: it imports `MAP_UTILS/map_base.ady` and `map_flat.ady` for its units and flat-plane geometry, and those
files are Nim only (they do `from math nimport ...`; `ady2py` cannot run it). The first version of this
example had its own `Vec2` and ran on both backends, with identical output; this one trades that for
the shared types.

The deterministic part of the mission is the original's to the digit (TLI 3133.1 m/s, LOI-1 770.6,
LOI-2 41.6, DOI 19.5, perilune 100.0 km at 2446.1 m/s, mission time 132.60 h); `make test-moon`
checks those lines. The powered descent is noisy, so its landing differs a little from the original's
(seed 1: 880 s, -0.86 m/s vertical, 533 kg of propellant left, against 868 s, -1.13 m/s, 601 kg) and
the six plots have the same shape as `moon_mission.png`. Matplotlib is needed to plot, through
`pyimport`; `make test` skips the run when it (or nimpy) is not installed, and only compiles.

## What differs from the Python

| moon_sim.py | here |
|-------------|------|
| `scipy.integrate.solve_ivp(..., method="DOP853", events=...)` | `integrate`: an adaptive Dormand-Prince 5(4) with terminal events, found by bisection. scipy cannot be called from Nim with a callback, and writing it in Adascript made the Nim build possible. Same tolerances (rtol 1e-10, atol 1e-3, max step 1800 s / 30 s); the orbit comes out the same to the printed digits |
| `scipy.optimize.brentq` | `brentq`, Brent's method, ported |
| numpy arrays | map_flat's `Position` (a point) and `Vector` (a displacement); `State_T` is a position and a velocity, `Delta_T` what it changes by per second. numpy is not imported at all |
| `np.random.default_rng(seed)` | `Rng`, L'Ecuyer's combined generator with Box-Muller, so the Python and Nim runs draw the same noise. The descent's noise therefore differs from numpy's for the same seed |
| `Stage` dataclass, `Spacecraft` | `Stage_T`, a record whose fields are `Mass_T`, `Duration_T` and `Force_T`, held by `Spacecraft`. The original shares one `Stage` object between the stack, the burn and `Propulsion`; here a stage is found by its `StageId_T`, so nothing is shared |
| `dict(...)` for orbital elements, gates, telemetry | records: `Elements_T`, `Gate_T`, `Target_T`, `Telemetry_T`, `Result_T` |
| strings for stage names, burn labels, guidance modes, phases | enums (`StageId_T`, `Burn_T`, `Mode_T`, `Phase_T`, `Event_T`) with name tables (`STAGE_NAME`, `BURN_NAME`, `MODE_NAME`) |
| event functions with `.terminal` / `.direction` attributes | `Event_T` and `EVENT_DIRECTION`; a `Dynamics` class (`EarthDynamics`, `MoonDynamics`) says what it watches |
| `lambda d: self._signed_periapsis(d) - target` | `PhaseError`, a `Scalar_Fn` with a `value` method: functions here do not close over variables |
| `float("nan")` for "no arrival" | `?float` from `signed_periapsis`, `1e30` where Brent needs a number |
| `orbital_elements` also returned `a`, `energy`, `apoapsis` | only what the program reads: radius, speed, `h`, `e`, periapsis |
| `Guidance.t_go` is `None` until set | `t_go` and `has_t_go` |
| `argparse` | a small loop over `$@` with an enum for what is expected next |

## Units

No bare floats in signatures. From map_base and map_flat: `Meters_T`, `Degrees_T`, `SquareMeters_T`, `Vector`,
`Position`, `Kilometers_T` and `Radians_T` (scaled units: `Kilometers_T(m)`, `Degrees_T(r)`), `modulo`, and `rotated_by` / `angle` / `unit` / `cross` for the rotations and
signs the original did with `rot`, `arctan2` and `np.sign`. Declared here: `Mass_T`, `Duration_T`
(distinct), `Speed_T`, `Accel_T`, `Force_T`, `Mu_T` (a body's GM), `AngularRate_T` and `AngMom_T` (derived).
The rocket equation is `ve = isp * G0` (a `Speed_T`), `used = m0 * (1 - exp(-dv / ve))` (a `Mass_T`),
gravity is `MU_MOON / (r * r)` (an `Accel_T`), the Moon's phase is a `Degrees_T` advancing at an
`AngularRate_T`, and a burn's delta-v cannot be added to a mass.

Two places still go through plain floats, inside a function that has typed parameters and result:
`sqrt`, `exp`, `ln` and `**` (`vis_viva`, `half_period`, the Moon's mean motion), and the arithmetic of
the integrator and Brent's method, which is on dimensionless step fractions.

Velocities and accelerations are map_flat's `Velocity` (`Speed_T` along a bearing) and
`Acceleration` (`Accel_T` along a bearing), with `Vector / t -> Velocity`,
`Velocity * t -> Vector`, `Velocity / t -> Acceleration` and `Acceleration * t -> Velocity` (`*` and `/` are
overloaded on the type of the right-hand side: a plain number scales, a `Duration_T` changes the unit);
the integrator's state is a `Position` and a `Velocity`, and a step of it is a `Vector` and a `Velocity`.
So `r + v * dt` checks, and `r + v` does not.

## Transpiler gaps met on the way

The units items below were fixed in the transpiler (`EXAMPLES/test_units_fields.ady`); the rest have a workaround in the source, marked where it is.

* **`(a, b) = f()` inside a block, onto variables declared outside it, made new variables on
  Nim** (`var (a, b) = ...`) and left the outer ones as they were. Silent: guidance flew to a
  target of zeros and the lander hit the Moon at 300 m/s. Fixed in the transpiler; the source still
  returns a record and assigns (`Guidance.compute`'s `aim`).
* **`(self.r, self.v) = f()` was not seen as a write to `self`**: the method got a plain `self` and
  Nim refused to compile it. Fixed in the transpiler; `Navigation.propagate` still assigns one at a time.
* **Methods in a `record` body were dropped without a word**, on both backends; both now refuse
  them and say to write a function or use a class. The first version's vector had to be a class.
* **Classes are values on Nim, references on Python** (chapter 13): `Rng` and `Spacecraft` are shared,
  so they are `@virtual`.
* **Units**: `SquareMeters_T * Meters_T` has no unit (a chain is two-at-a-time), so a cube is taken
  through `float`. Three others were fixed here: a literal beside `>` on a distinct type in a
  conditional expression or on a tuple-unpacked name came out as `0.0 < force`; a bare `0.0` in a
  returned tuple `(int, Force_T)` was not converted; and the Python unit check did not know a record
  field's type (`st.isp * G0`).
* **`{x:,.0f}` and `{x:+.0f}` in an f-string**: Nim had no `,` flag, and `+.0f` left a stray `.`
  (`-456396.`). Fixed in the transpiler, with a width and alignment too (`{x:15,.1f}`); the source
  writes them as Python does. `\n` in an f-string was fixed some time before.
* **A call on a `PyObject` variable standing alone (`ax.plot(...)`) was "has to be used" on Nim**
  (only a call on a pyimported module was discarded). Fixed in the transpiler; the plots are written
  as plain calls.
* **`Record(a, b, None)` with a positional `None` for a `?T` field emitted `nil` on Nim, and
  `opt == value` / `opt != value` on a `?Enum` did not compile.** Fixed in the transpiler (the field is
  lifted to `none(T)` or `some(v)`, positional or by name; the value beside `==` is lifted to
  `some(v)`).
* **`a + b` on two `[]T` fields reached through `self.x.y`** was not seen as a list concatenation on
  Nim (`&`). Fixed in the transpiler.
* **`min(a, b, c)` with three arguments, and `raise NotImplementedError()` without a message,
  did not compile on Nim.** Fixed in the transpiler (nested two-argument calls; the exception's name
  as its message, and `except NotImplementedError` catches it).
* **`math.atan`, `atan2`, `asin`, `acos` and one-argument `math.log`** are Python's names, not Nim's
  (`arctan`, `arctan2`, `arcsin`, `arccos`, `ln`). They are now refused with what Nim calls them, and
  `math.arctan` and the others run on the Python backend too.
* **map_base and map_flat cannot be imported from a sibling directory by name**; `from MAP_UTILS/map_base import`
  works because the parent of this directory is searched.
