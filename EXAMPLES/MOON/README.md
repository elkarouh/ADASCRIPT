# MOON -- an Earth-Moon landing, translated from Python

`moon_sim.ady` is `moon_sim.py` (a 2-D, Apollo-style mission: TLI, a trans-lunar coast,
LOI-1/LOI-2, undock, DOI, then a closed-loop powered descent through
IMU -> Navigation -> Guidance -> Autopilot -> Propulsion) written in Adascript.

    ady2nim c -r moon_sim.ady --out moon_mission.png      # Nim, about 2 s
    ady2py -c moon_sim.ady --out moon_mission.png         # Python, about 3 s
    make test-moon                                        # both, and they must agree

Both backends print the same mission, line for line, for any `--seed`. The deterministic part
is the original's to the digit (TLI 3133.1 m/s, LOI-1 770.6, LOI-2 41.6, DOI 19.5, perilune
100.0 km at 2446.1 m/s, mission time 132.60 h); the powered descent is noisy, so its landing
differs a little from the original's (seed 1: 880 s, -0.86 m/s vertical, 533 kg of propellant
left, against 868 s, -1.13 m/s, 601 kg) and the six plots have the same shape as
`moon_mission.png`. Matplotlib is needed to plot, through `pyimport`; `make test` skips the run
when it (or nimpy, for the Nim build) is not installed, and only compiles.

## What differs from the Python

| moon_sim.py | here |
|-------------|------|
| `scipy.integrate.solve_ivp(..., method="DOP853", events=...)` | `integrate`: an adaptive Dormand-Prince 5(4) with terminal events, found by bisection. scipy cannot be called from Nim with a callback, and writing it in Adascript made the Nim build possible. Same tolerances (rtol 1e-10, atol 1e-3, max step 1800 s / 30 s); the orbit comes out the same to the printed digits |
| `scipy.optimize.brentq` | `brentq`, Brent's method, ported |
| numpy arrays | `Vec2` and `State_T`, classes with operators. numpy is not imported at all |
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

The vehicle's bookkeeping is typed with units: `Mass_T`, `Duration_T`, `Distance_T` are
`distinct float`, `Speed_T`, `Accel_T`, `Force_T` are derived from them, so the rocket equation
is `ve = isp * G0` (a `Speed_T`), `used = m0 * (1 - exp(-dv / ve))` (a `Mass_T`), and a burn's
delta-v cannot be added to a mass. The orbit kernel (`Vec2`, `State_T`, the dynamics) is plain
SI floats, and the units are put back with `Speed_T(magnitude(dv))` where a vector comes out.

## Transpiler gaps met on the way

None needed a change to the transpiler; each has a workaround in the source, marked where it is.

* **`(a, b) = f()` inside a block, onto variables declared outside it, makes new variables on
  Nim** (`var (a, b) = ...`) and leaves the outer ones as they were. Python is right, Nim silently
  wrong: guidance flew to a target of zeros and the lander hit the Moon at 300 m/s. Worked
  around by returning a record and assigning its fields (`Guidance.compute`).
* **`(self.r, self.v) = f()` is not seen as a write to `self`**: the method gets a plain `self`
  and Nim refuses to compile it (`Navigation.propagate`).
* **Methods in a `record` body are dropped without a word**, on both backends; operators on a
  record exist only as top-level procs on Nim. `Vec2` is a class for that reason.
* **Classes are values on Nim, references on Python** (chapter 13): `Rng` and `Spacecraft` are
  shared, so they are `@virtual`. Not a bug, but the first run disagreed until they were.
* **`math.atan`, `atan2`, `asin`, `acos` are not mapped to Nim** (`arctan`, `arctan2`, ...), and
  `math.log(x)` with one argument is not either (Nim's `log` wants a base). Worked around with
  an `arctan` written out and `math.log(x, E)`.
* **`{x:,.0f}` and `{x:+.0f}` in an f-string**: Nim has no `,` flag, and `+.0f` leaves a stray
  `.` (`-456396.`). Written as `thousands()` and `signed()`.
* **`\n` inside an f-string is not an escape on Nim** (`f"\nPlot saved"` printed no blank line).
* **A call on a `PyObject` variable standing alone is not discarded on Nim**
  (`ax.plot(...)`: "has to be used"); only calls on a pyimported module are. Written as
  `let _: PyObject = ax.plot(...)`.
* **`Record(a, b, None)` with a positional `None` for a `?T` field emits `nil` on Nim**; named
  (`hit=None`) is right. **`opt == value` and `opt != value` on a `?Enum` do not compile on
  Nim**, and `a + b` on two `[]T` fields reached through `self.x.y` is not seen as a list
  concatenation.
* **`min(a, b, c)` with three arguments does not compile on Nim.**
* **A literal beside `>` on a distinct type** (`force > 0.0`, in a conditional expression) came
  out as `0.0 < force` and was refused; so was a bare `0.0` in a tuple returned as
  `(Vec2, Force_T)`. Written `float(force) > 0.0` and `Force_T(0.0)`.
* **The Python backend's unit check does not know a record field's type**: `st.isp * G0` was
  taken for an `Accel_T` and refused. Bound to a typed `let` first.
* **`raise NotImplementedError()` does not compile on Nim** (`newException` needs a message).
