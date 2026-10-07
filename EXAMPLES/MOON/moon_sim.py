#!/usr/bin/env python3
"""
moon_sim.py - Earth -> Moon landing simulation (2-D, Apollo-style)

Consolidates moon.py (orbital mechanics / mission sequencing) and
moon2.py (Navigation -> Guidance -> Autopilot -> Propulsion layers).

Mission sequence
----------------
  LEO (200 km) -> TLI -> trans-lunar coast (Earth+Moon gravity, Moon on a
  moving ephemeris) -> lunar SOI entry -> periapsis -> LOI-1 -> LOI-2
  (100 km circular) -> LM undock -> DOI (15 km periapsis) -> PDI ->
  P63 braking -> P64 approach -> P65 terminal descent -> touchdown

Fidelity notes
--------------
  * Impulsive burns for TLI / LOI / DOI (rocket equation, per-stage mass).
  * Finite-thrust, closed-loop powered descent through the GNC chain:
        physics -> IMU -> Navigation -> Guidance -> Autopilot -> Propulsion
  * Moon phase is solved (shooting method) so the transfer really arrives
    at a 100 km periapsis; nothing is "teleported".
  * Not modelled: Moon rotation, mascons, Earth tides in lunar orbit,
    3-D plane changes, ascent/return.

Usage:  python moon_sim.py [--seed N] [--show] [--out moon_mission.png]
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import matplotlib

from scipy.integrate import solve_ivp
from scipy.optimize import brentq

# ============================================================
# CONSTANTS
# ============================================================

MU_EARTH = 3.986004418e14
MU_MOON = 4.9048695e12
M_EARTH = 5.972e24
M_MOON = 7.342e22

R_EARTH = 6.371e6
R_MOON = 1.7374e6
MOON_DISTANCE = 384.4e6
SOI_MOON = MOON_DISTANCE * (M_MOON / M_EARTH) ** 0.4

G0 = 9.80665


# ============================================================
# VECTOR / ORBIT UTILITIES
# ============================================================

def magnitude(v):
    return float(np.linalg.norm(v))


def unit(v):
    n = magnitude(v)
    return np.zeros_like(v) if n == 0 else v / n


def perp(v):
    """90 deg counter-clockwise rotation."""
    return np.array([-v[1], v[0]])


def rot(v, ang):
    c, s = np.cos(ang), np.sin(ang)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def tangent(r, v=None):
    """Unit tangent at r (in the direction of motion if v is given)."""
    t = unit(perp(r))
    if v is not None and np.dot(t, v) < 0:
        t = -t
    return t


def circular_velocity(mu, radius):
    return np.sqrt(mu / radius)


def vis_viva(mu, radius, a):
    return np.sqrt(mu * (2.0 / radius - 1.0 / a))


def orbital_elements(r, v, mu):
    rmag, vmag = magnitude(r), magnitude(v)
    h = cross2(r, v)
    energy = vmag ** 2 / 2.0 - mu / rmag
    a = np.inf if abs(energy) < 1e-12 else -mu / (2.0 * energy)
    evec = ((vmag ** 2 - mu / rmag) * r - np.dot(r, v) * v) / mu
    e = magnitude(evec)
    rp = h ** 2 / (mu * (1.0 + e))
    ra = h ** 2 / (mu * (1.0 - e)) if e < 1.0 else np.nan
    return dict(radius=rmag, speed=vmag, h=h, energy=energy, a=a, e=e,
                periapsis=rp, apoapsis=ra)


def period(mu, a):
    return 2.0 * np.pi * np.sqrt(a ** 3 / mu)


# ============================================================
# SPACECRAFT (stack of stages)
# ============================================================

@dataclass
class Stage:
    name: str
    dry: float          # kg
    prop: float         # kg
    isp: float          # s
    max_thrust: float   # N

    @property
    def mass(self):
        return self.dry + self.prop


class Spacecraft:
    def __init__(self, stages):
        self.stages = list(stages)
        self.burn_log = []

    @property
    def mass(self):
        return sum(s.mass for s in self.stages)

    def stage(self, name):
        return next(s for s in self.stages if s.name == name)

    def separate(self, name):
        st = self.stage(name)
        self.stages.remove(st)
        return st

    def burn(self, dv_vec, stage_name, label=""):
        """Impulsive burn with the rocket equation. Clips if out of propellant."""
        st = self.stage(stage_name)
        dv = magnitude(dv_vec)
        if dv <= 0:
            return dv_vec
        m0 = self.mass
        ve = st.isp * G0
        used = m0 * (1.0 - np.exp(-dv / ve))
        if used > st.prop:
            used = st.prop
            dv_act = ve * np.log(m0 / (m0 - used))
            print(f"  !! {st.name} out of propellant: wanted {dv:.1f} m/s, got {dv_act:.1f} m/s")
            dv_vec = dv_vec * dv_act / dv
            dv = dv_act
        st.prop -= used
        self.burn_log.append((label, st.name, dv, used))
        return dv_vec


# ============================================================
# EPHEMERIS + EARTH-FRAME DYNAMICS
# ============================================================

class MoonEphemeris:
    """Moon on a circular orbit about Earth, analytic in time."""

    def __init__(self, phase0=0.0):
        self.phase0 = phase0
        self.n = np.sqrt((MU_EARTH + MU_MOON) / MOON_DISTANCE ** 3)

    def state(self, t):
        th = self.phase0 + self.n * t
        c, s = np.cos(th), np.sin(th)
        r = MOON_DISTANCE * np.array([c, s])
        v = MOON_DISTANCE * self.n * np.array([-s, c])
        return r, v


def earth_rhs(t, y, moon):
    """Spacecraft in the Earth-centred frame, with Moon as a 3rd body
    (direct + indirect terms)."""
    r, v = y[:2], y[2:]
    rm, _ = moon.state(t)
    d = r - rm
    a = (-MU_EARTH * r / magnitude(r) ** 3
         - MU_MOON * (d / magnitude(d) ** 3 + rm / magnitude(rm) ** 3))
    return np.r_[v, a]


def soi_event(t, y, moon):
    return magnitude(y[:2] - moon.state(t)[0]) - SOI_MOON


soi_event.terminal = True
soi_event.direction = -1


def moon_rhs(t, y):
    r = y[:2]
    return np.r_[y[2:], -MU_MOON * r / magnitude(r) ** 3]


def ev_periapsis(t, y):
    return np.dot(y[:2], y[2:])


ev_periapsis.terminal = True
ev_periapsis.direction = 1


def ev_apoapsis(t, y):
    return np.dot(y[:2], y[2:])


ev_apoapsis.terminal = True
ev_apoapsis.direction = -1


def ev_surface(t, y):
    return magnitude(y[:2]) - R_MOON


ev_surface.terminal = True
ev_surface.direction = -1


def rk4_step(r, v, a_ext, dt):
    """One RK4 step of lunar two-body gravity + constant external accel."""
    def f(rr, vv):
        return vv, -MU_MOON * rr / magnitude(rr) ** 3 + a_ext

    k1r, k1v = f(r, v)
    k2r, k2v = f(r + 0.5 * dt * k1r, v + 0.5 * dt * k1v)
    k3r, k3v = f(r + 0.5 * dt * k2r, v + 0.5 * dt * k2v)
    k4r, k4v = f(r + dt * k3r, v + dt * k3v)
    return (r + dt / 6.0 * (k1r + 2 * k2r + 2 * k3r + k4r),
            v + dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v))


# ============================================================
# APOLLO-STYLE GNC LAYER  (from moon2.py, made self-consistent)
#
#   physics -> IMU -> Navigation -> Guidance -> Autopilot -> Propulsion
# ============================================================

class IMU:
    """Accelerometers measure specific force (thrust accel, NOT gravity)."""

    def __init__(self, rng, bias_sigma=3e-4, walk=1e-6, noise=2e-4):
        self.rng = rng
        self.bias = rng.normal(0.0, bias_sigma, 2)
        self.walk = walk
        self.noise = noise

    def measure(self, specific_force, dt):
        self.bias += self.rng.normal(0.0, self.walk, 2) * np.sqrt(dt)
        return specific_force + self.bias + self.rng.normal(0.0, self.noise, 2)


class Navigation:
    def __init__(self, rng):
        self.rng = rng
        self.r = np.zeros(2)
        self.v = np.zeros(2)

    def initialize(self, r, v, pos_sigma=100.0, vel_sigma=0.1):
        """State handed over from the pre-PDI ground/orbit solution (with error)."""
        self.r = r + self.rng.normal(0.0, pos_sigma, 2)
        self.v = v + self.rng.normal(0.0, vel_sigma, 2)

    def propagate(self, measured_specific_force, dt):
        self.r, self.v = rk4_step(self.r, self.v, measured_specific_force, dt)

    def radar_update(self, true_r, true_v):
        """Landing radar: altitude + Doppler velocity (valid below ~10 km)."""
        alt_true = magnitude(true_r) - R_MOON
        z_alt = alt_true + self.rng.normal(0.0, 2.0 + 0.005 * alt_true)
        z_vel = true_v + self.rng.normal(0.0, 0.3, 2)

        radial = unit(self.r)
        d_alt = z_alt - (magnitude(self.r) - R_MOON)
        self.r = self.r + 0.5 * d_alt * radial          # position (radial only)
        self.v = self.v + 0.3 * (z_vel - self.v)        # velocity (full vector)


class Guidance:
    """P63 braking / P64 approach / P65 terminal, in the spirit of the AGC.

    P63/P64 use the AGC-style polynomial law (linear jerk profile) that meets a
    target position + velocity at time-to-go T:
          a = 6 (rT - r)/T^2 - (4 v + 2 vT)/T
    P65 is a velocity-tracking vertical descent.
    """

    P63, P64, P65 = "P63-BRAKING", "P64-APPROACH", "P65-TERMINAL"

    # target gates (altitude [m], up-range [m], horiz vel, vertical vel [m/s])
    HIGH_GATE = dict(alt=2000.0, uprange=7000.0, vh=85.0, vv=-25.0)
    LOW_GATE = dict(alt=50.0, uprange=150.0, vh=2.0, vv=-3.0)

    def __init__(self, site_up, travel_sign):
        self.site_up = site_up
        self.s = travel_sign
        self.site = R_MOON * site_up
        self.mode = self.P63
        self.t_go = None

    def _frame(self, offset_rad):
        up = rot(self.site_up, self.s * offset_rad)
        east = self.s * perp(up)
        return up, east

    def _target(self, gate):
        up, east = self._frame(-gate["uprange"] / R_MOON)
        return (R_MOON + gate["alt"]) * up, gate["vh"] * east + gate["vv"] * up

    @staticmethod
    def _estimate_tgo(r, v, rT, vT):
        dist = magnitude(rT - r)
        return max(15.0, 2.0 * dist / (magnitude(v) + magnitude(vT) + 1e-9))

    def compute(self, r, v, elapsed):
        """Return commanded THRUST acceleration vector (m/s^2)."""
        g = -MU_MOON * r / magnitude(r) ** 3
        alt = magnitude(r) - R_MOON

        if self.t_go is not None:
            self.t_go -= elapsed

        if self.mode == self.P63:
            rT, vT = self._target(self.HIGH_GATE)
            if self.t_go is None:
                self.t_go = self._estimate_tgo(r, v, rT, vT)
            if self.t_go <= 4.0:
                self.mode, self.t_go = self.P64, None

        if self.mode == self.P64:
            rT, vT = self._target(self.LOW_GATE)
            if self.t_go is None:
                self.t_go = self._estimate_tgo(r, v, rT, vT)
            if self.t_go <= 3.0 or alt < 60.0:
                self.mode, self.t_go = self.P65, None

        if self.mode in (self.P63, self.P64):
            T = max(self.t_go, 3.0)
            a_total = 6.0 * (rT - r) / T ** 2 - (4.0 * v + 2.0 * vT) / T
        else:
            up = unit(r)
            east = self.s * perp(up)
            dx = np.dot(self.site - r, east)
            # horizontal velocity is nulled as the surface approaches
            fade = np.clip(alt / 30.0, 0.0, 1.0)
            v_des = (east * np.clip(0.1 * dx, -2.0, 2.0) * fade
                     - up * np.clip(0.1 * alt, 1.0, 3.0))
            a_total = (v_des - v) / 1.5

        return a_total - g          # thrust must cancel gravity


class Autopilot:
    """Throttle limits and attitude slew-rate limit."""

    def __init__(self, direction, max_rate_deg=10.0, min_throttle=0.10, max_throttle=1.0):
        self.dir = unit(direction)
        self.max_rate = np.radians(max_rate_deg)
        self.tmin, self.tmax = min_throttle, max_throttle
        self.saturated = False

    def command(self, a_cmd, mass, max_thrust, dt):
        mag = magnitude(a_cmd)
        if mag > 0:
            want = a_cmd / mag
            ang = np.arctan2(cross2(self.dir, want), np.dot(self.dir, want))
            self.dir = rot(self.dir, np.clip(ang, -self.max_rate * dt, self.max_rate * dt))
        raw = mag * mass / max_thrust
        self.saturated = raw > self.tmax
        return self.dir, float(np.clip(raw, self.tmin, self.tmax))


class Propulsion:
    def __init__(self, spacecraft, stage):
        self.sc, self.stage = spacecraft, stage

    def thrust(self, direction, throttle, dt):
        """Returns thrust acceleration; burns propellant."""
        if self.stage.prop <= 0:
            return np.zeros(2), 0.0
        mass = self.sc.mass
        force = throttle * self.stage.max_thrust
        used = min(force / (self.stage.isp * G0) * dt, self.stage.prop)
        self.stage.prop -= used
        return direction * force / mass, force


# ============================================================
# MISSION
# ============================================================

class Mission:
    LEO_ALT = 200e3
    LOI_PERI_ALT = 100e3
    LOI1_APO_ALT = 300e3
    DOI_PERI_ALT = 15e3
    DESCENT_ARC = 0.36          # rad of lunar arc between PDI and landing site
    DT = 0.2                    # physics step in powered descent
    GUIDANCE_CYCLE = 2.0        # AGC guidance cycle

    def __init__(self, seed=1):
        self.rng = np.random.default_rng(seed)
        self.sc = Spacecraft([
            Stage("S-IVB", 13_500.0, 70_000.0, 421.0, 1_000_000.0),
            Stage("CSM", 10_500.0, 18_500.0, 314.0, 91_000.0),
            Stage("LM", 7_000.0, 8_200.0, 311.0, 45_040.0),
        ])
        self.lander = None
        self.t = 0.0
        self.r = None
        self.v = None
        self.phase = "LEO"
        self.earth_track = []       # (t_array, xy[2,N])
        self.moon_tracks = []       # (label, xy[2,N])
        self.moon_ephem = None
        self.descent = None
        self.result = None

    # --------------------------------------------------------
    def log(self, text=""):
        print(text)

    # --------------------------------------------------------
    # TLI + phase solution
    # --------------------------------------------------------
    def plan_tli(self):
        self.log("PHASE: TLI")
        r0 = np.array([R_EARTH + self.LEO_ALT, 0.0])
        rm0 = magnitude(r0)
        a_t = (rm0 + MOON_DISTANCE) / 2.0
        v_c = circular_velocity(MU_EARTH, rm0)
        v_t = vis_viva(MU_EARTH, rm0, a_t)
        self.tli_r = r0
        self.tli_v = np.array([0.0, v_t])
        dv = v_t - v_c
        self.sc.burn(np.array([0.0, dv]), "S-IVB", "TLI")
        self.sc.separate("S-IVB")
        self.log(f"  TLI dv = {dv:.1f} m/s  (S-IVB jettisoned, stack = {self.sc.mass:,.0f} kg)")

        t_transfer = np.pi * np.sqrt(a_t ** 3 / MU_EARTH)
        n = MoonEphemeris().n
        self.phase_nominal = np.pi - n * t_transfer
        self.t_max = 1.4 * t_transfer
        self.log(f"  Nominal transfer time = {t_transfer / 86400:.2f} d")

    def _arrival(self, delta):
        moon = MoonEphemeris(self.phase_nominal + delta)
        y0 = np.r_[self.tli_r, self.tli_v]
        sol = solve_ivp(earth_rhs, (0.0, self.t_max), y0, args=(moon,),
                        events=soi_event, method="DOP853",
                        rtol=1e-10, atol=1e-3, max_step=1800.0)
        return sol if sol.status == 1 else None

    def _signed_periapsis(self, delta):
        sol = self._arrival(delta)
        if sol is None:
            return np.nan
        rm, vm = MoonEphemeris(self.phase_nominal + delta).state(sol.t[-1])
        el = orbital_elements(sol.y[:2, -1] - rm, sol.y[2:, -1] - vm, MU_MOON)
        return np.sign(el["h"]) * el["periapsis"]

    def solve_moon_phase(self):
        """Shooting method: choose the Moon's phase so that perilune = 100 km."""
        target = R_MOON + self.LOI_PERI_ALT
        self.log("  Solving Moon phasing (shooting method)...")
        grid = np.linspace(-0.45, 0.45, 31)
        vals = np.array([self._signed_periapsis(d) - target for d in grid])
        root = None
        for i in range(len(grid) - 1):
            if np.isfinite(vals[i]) and np.isfinite(vals[i + 1]) and vals[i] * vals[i + 1] < 0:
                root = brentq(lambda d: self._signed_periapsis(d) - target,
                              grid[i], grid[i + 1], xtol=1e-9)
                break
        if root is None:
            raise RuntimeError("could not find a Moon phase that gives the target periapsis")
        self.phase_delta = root
        self.moon_ephem = MoonEphemeris(self.phase_nominal + root)
        self.log(f"  Moon phase correction = {np.degrees(root):+.3f} deg")

    # --------------------------------------------------------
    # Trans-lunar coast
    # --------------------------------------------------------
    def coast_earth(self):
        self.phase = "TRANS_LUNAR"
        moon = self.moon_ephem
        y0 = np.r_[self.tli_r, self.tli_v]
        sol = solve_ivp(earth_rhs, (0.0, self.t_max), y0, args=(moon,),
                        events=soi_event, method="DOP853",
                        rtol=1e-10, atol=1e-3, max_step=1800.0)
        self.earth_track = (sol.t.copy(), sol.y[:2].copy())
        self.t = sol.t[-1]
        rm, vm = moon.state(self.t)
        self.r = sol.y[:2, -1] - rm
        self.v = sol.y[2:, -1] - vm
        self.phase = "LUNAR_APPROACH"
        self.log()
        self.log("ENTERED LUNAR SOI")
        self.log(f"  Time     = {self.t / 3600:.1f} h  ({self.t / 86400:.2f} d)")
        self.log(f"  Distance = {magnitude(self.r) / 1000:.0f} km")
        self.log(f"  Rel. vel = {magnitude(self.v):.1f} m/s")

    # --------------------------------------------------------
    # Lunar-frame propagation helper
    # --------------------------------------------------------
    def coast_moon(self, duration, events=None, label=""):
        y0 = np.r_[self.r, self.v]
        sol = solve_ivp(moon_rhs, (0.0, duration), y0, method="DOP853",
                        events=events, rtol=1e-10, atol=1e-3, max_step=30.0)
        self.moon_tracks.append((label or self.phase, sol.y[:2].copy()))
        self.t += sol.t[-1]
        self.r = sol.y[:2, -1]
        self.v = sol.y[2:, -1]
        return sol

    def coast_to_periapsis(self):
        sol = self.coast_moon(5 * 86400.0, [ev_periapsis, ev_surface], "approach")
        if len(sol.t_events[1]):
            raise RuntimeError("lunar impact during approach")
        el = orbital_elements(self.r, self.v, MU_MOON)
        self.log()
        self.log("LUNAR PERIAPSIS")
        self.log(f"  Altitude = {(el['radius'] - R_MOON) / 1000:.1f} km")
        self.log(f"  Speed    = {el['speed']:.1f} m/s")

    # --------------------------------------------------------
    # Generic tangential burn to a target speed
    # --------------------------------------------------------
    def _tangential_burn(self, stage_name, target_speed, label, sc=None):
        sc = sc or self.sc
        desired = tangent(self.r, self.v) * target_speed
        dv = desired - self.v
        dv = sc.burn(dv, stage_name, label)
        self.v = self.v + dv
        return magnitude(dv)

    # --------------------------------------------------------
    # LOI-1 / LOI-2
    # --------------------------------------------------------
    def loi1(self):
        self.phase = "LOI-1"
        rp = magnitude(self.r)
        ra = R_MOON + self.LOI1_APO_ALT
        speed = vis_viva(MU_MOON, rp, (rp + ra) / 2.0)
        dv = self._tangential_burn("CSM", speed, "LOI-1")
        self.log(f"LOI-1 dv = {dv:.1f} m/s   (-> {(rp - R_MOON) / 1e3:.0f} x "
                 f"{self.LOI1_APO_ALT / 1e3:.0f} km)")

    def coast_to_next_periapsis(self):
        self.phase = "LUNAR_ORBIT"
        self.coast_moon(3 * 86400.0, [ev_apoapsis], "lunar orbit")
        self.coast_moon(3 * 86400.0, [ev_periapsis], "lunar orbit")

    def loi2(self):
        self.phase = "LOI-2"
        speed = circular_velocity(MU_MOON, magnitude(self.r))
        dv = self._tangential_burn("CSM", speed, "LOI-2")
        el = orbital_elements(self.r, self.v, MU_MOON)
        self.log(f"LOI-2 dv = {dv:.1f} m/s   (circular, e = {el['e']:.4f}, "
                 f"alt {(el['radius'] - R_MOON) / 1e3:.1f} km)")
        self.phase = "LUNAR_CIRCULAR"

    # --------------------------------------------------------
    # Undock, coast, DOI
    # --------------------------------------------------------
    def undock_and_coast(self):
        lm = self.sc.separate("LM")
        self.lander = Spacecraft([lm])
        self.log()
        self.log(f"LM UNDOCK  (lander mass = {self.lander.mass:,.0f} kg, "
                 f"CSM stays in orbit with {self.sc.stage('CSM').prop:,.0f} kg prop)")
        T = period(MU_MOON, magnitude(self.r))
        self.coast_moon(T, None, "circular orbit")

    def doi(self):
        self.phase = "DOI"
        r = magnitude(self.r)
        rp = R_MOON + self.DOI_PERI_ALT
        speed = vis_viva(MU_MOON, r, (r + rp) / 2.0)
        dv = self._tangential_burn("LM", speed, "DOI", sc=self.lander)
        self.log(f"DOI dv = {dv:.1f} m/s   (-> periapsis {self.DOI_PERI_ALT / 1e3:.0f} km)")
        self.coast_moon(3 * 86400.0, [ev_periapsis, ev_surface], "descent orbit")
        self.phase = "PDI"

    # --------------------------------------------------------
    # Powered descent (closed-loop GNC)
    # --------------------------------------------------------
    def powered_descent(self):
        lander = self.lander
        stage = lander.stages[0]
        r, v = self.r.copy(), self.v.copy()
        s = np.sign(cross2(r, v))
        site_up = rot(unit(r), s * self.DESCENT_ARC)

        imu = IMU(self.rng)
        nav = Navigation(self.rng)
        nav.initialize(r, v)
        guid = Guidance(site_up, s)
        auto = Autopilot(-unit(v))
        prop = Propulsion(lander, stage)

        self.log()
        self.log("POWERED DESCENT INITIATION")
        self.log(f"  Altitude = {(magnitude(r) - R_MOON) / 1000:.1f} km, "
                 f"speed = {magnitude(v):.0f} m/s, mass = {lander.mass:,.0f} kg")
        self.log(f"  Landing site is {self.DESCENT_ARC * R_MOON / 1000:.0f} km downrange")

        dt = self.DT
        t = 0.0
        next_guid, next_radar, next_tm = 0.0, 0.0, 0.0
        a_cmd = np.zeros(2)
        last_cycle = 0.0
        tele = []
        outcome = "TIMEOUT"
        last_mode = None

        while t < 2400.0:
            if t >= next_guid - 1e-9:
                a_cmd = guid.compute(nav.r, nav.v, t - last_cycle if t > 0 else 0.0)
                last_cycle = t
                next_guid += self.GUIDANCE_CYCLE
                if guid.mode != last_mode:
                    self.log(f"  t+{t:6.1f}s  {guid.mode:13s} alt {(magnitude(r) - R_MOON):8.0f} m  "
                             f"v {magnitude(v):7.1f} m/s  fuel {stage.prop:6.0f} kg")
                    last_mode = guid.mode

            direction, throttle = auto.command(a_cmd, lander.mass, stage.max_thrust, dt)
            a_thrust, force = prop.thrust(direction, throttle, dt)

            if t >= next_tm - 1e-9:
                up = unit(r)
                east = s * perp(up)
                tele.append(dict(
                    t=t, alt=magnitude(r) - R_MOON,
                    vv=np.dot(v, up), vh=np.dot(v, east),
                    throttle=throttle if force > 0 else 0.0, fuel=stage.prop,
                    pos_err=magnitude(nav.r - r), vel_err=magnitude(nav.v - v),
                    mode=guid.mode, x=r[0], y=r[1]))
                next_tm += 1.0

            r_new, v_new = rk4_step(r, v, a_thrust, dt)
            nav.propagate(imu.measure(a_thrust, dt), dt)
            t += dt

            alt_new = magnitude(r_new) - R_MOON
            if alt_new <= 0.0:
                # linear interpolation to the instant of contact
                alt_old = magnitude(r) - R_MOON
                f = alt_old / max(alt_old - alt_new, 1e-9)
                r = r + f * (r_new - r)
                v = v + f * (v_new - v)
                outcome = "TOUCHDOWN"
                break
            r, v = r_new, v_new

            if (magnitude(r) - R_MOON) < 10_000.0 and t >= next_radar:
                nav.radar_update(r, v)
                next_radar += 1.0

            if stage.prop <= 0.0 and outcome != "TOUCHDOWN":
                pass

        up = unit(r)
        east = s * perp(up)
        vv, vh = float(np.dot(v, up)), float(np.dot(v, east))
        arc = np.arctan2(cross2(site_up, up), np.dot(site_up, up)) * s
        miss = arc * R_MOON               # + = overshoot (beyond site)

        good = (outcome == "TOUCHDOWN" and abs(vv) < 3.0 and abs(vh) < 1.5)
        self.phase = "LANDED" if good else ("HARD_LANDING" if outcome == "TOUCHDOWN" else outcome)
        self.r, self.v = r, v
        self.t += t
        self.descent = tele
        self.result = dict(outcome=outcome, vv=vv, vh=vh, miss=miss, t=t,
                           fuel=stage.prop, nav_pos_err=magnitude(nav.r - r),
                           nav_vel_err=magnitude(nav.v - v))

        self.log()
        self.log("==============================")
        self.log("  TOUCHDOWN" if good else f"  {self.phase}")
        self.log("==============================")
        self.log(f"  Descent time         : {t:.0f} s")
        self.log(f"  Contact velocity     : {vv:+.2f} m/s vertical, {vh:+.2f} m/s horizontal")
        self.log(f"  Landing miss         : {miss:+.0f} m (+ = long)")
        self.log(f"  Nav error at contact : {self.result['nav_pos_err']:.0f} m, "
                 f"{self.result['nav_vel_err']:.2f} m/s")
        self.log(f"  Descent prop left    : {stage.prop:.0f} kg")

    # --------------------------------------------------------
    def run(self):
        self.plan_tli()
        self.solve_moon_phase()
        self.coast_earth()
        self.coast_to_periapsis()
        self.loi1()
        self.coast_to_next_periapsis()
        self.loi2()
        self.undock_and_coast()
        self.doi()
        self.powered_descent()

    # --------------------------------------------------------
    def summary(self):
        print()
        print("==============================")
        print("MISSION SUMMARY")
        print("==============================")
        print(f"Final phase  : {self.phase}")
        print(f"Mission time : {self.t / 3600:.2f} h ({self.t / 86400:.2f} d)")
        print()
        print(f"{'burn':8s} {'stage':7s} {'dv [m/s]':>10s} {'prop [kg]':>11s}")
        total = 0.0
        for sc in (self.sc, self.lander, getattr(self, "_all", None)):
            pass
        for label, name, dv, used in self._all_burns():
            print(f"{label:8s} {name:7s} {dv:10.1f} {used:11.0f}")
            total += dv
        print(f"{'total':16s} {total:10.1f}")

    def _all_burns(self):
        # TLI was logged on the original stack object before separation, so
        # the same Spacecraft keeps it; the lander has its own log.
        return list(self.sc.burn_log) + list(self.lander.burn_log)


# ============================================================
# PLOTS
# ============================================================

def make_plots(m: Mission, path, show):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(2, 3, figsize=(17, 9.5))

    # 1 - Earth frame
    a = ax[0, 0]
    t, xy = m.earth_track
    a.plot(xy[0] / 1e6, xy[1] / 1e6, lw=1.2, label="spacecraft")
    th = np.linspace(0, 2 * np.pi, 400)
    a.plot(MOON_DISTANCE / 1e6 * np.cos(th), MOON_DISTANCE / 1e6 * np.sin(th),
           "k:", lw=0.6, label="Moon orbit")
    tm = np.linspace(0, t[-1], 200)
    mp = np.array([m.moon_ephem.state(x)[0] for x in tm]).T
    a.plot(mp[0] / 1e6, mp[1] / 1e6, "gray", lw=2, label="Moon path")
    mr = m.moon_ephem.state(t[-1])[0]
    a.add_patch(plt.Circle((mr[0] / 1e6, mr[1] / 1e6), SOI_MOON / 1e6, fill=False, ls="--", color="gray"))
    a.add_patch(plt.Circle((0, 0), R_EARTH / 1e6, color="tab:blue", alpha=0.5))
    a.set_aspect("equal")
    a.set_title("Trans-lunar trajectory (Earth-centred, inertial)")
    a.set_xlabel("x [10^3 km]"); a.set_ylabel("y [10^3 km]")
    a.legend(fontsize=7)

    # 2 - Moon frame orbits
    a = ax[0, 1]
    for label, xy in m.moon_tracks:
        a.plot(xy[0] / 1e3, xy[1] / 1e3, lw=1, label=label)
    a.add_patch(plt.Circle((0, 0), R_MOON / 1e3, color="lightgray"))
    a.set_aspect("equal")
    a.set_title("Lunar approach, orbit and descent (Moon-centred)")
    a.set_xlabel("x [km]"); a.set_ylabel("y [km]")
    a.legend(fontsize=7)

    d = m.descent
    T = np.array([x["t"] for x in d])
    alt = np.array([x["alt"] for x in d]) / 1e3
    vv = np.array([x["vv"] for x in d])
    vh = np.array([x["vh"] for x in d])
    thr = np.array([x["throttle"] for x in d]) * 100
    fuel = np.array([x["fuel"] for x in d])
    pe = np.array([x["pos_err"] for x in d])
    ve = np.array([x["vel_err"] for x in d])

    # 3 - altitude
    a = ax[0, 2]
    a.plot(T, alt)
    for i in range(1, len(d)):
        if d[i]["mode"] != d[i - 1]["mode"]:
            a.axvline(T[i], color="k", ls=":", lw=0.8)
            a.text(T[i], alt.max() * 0.9, d[i]["mode"][:3], rotation=90, fontsize=8)
    a.set_title("Powered descent: altitude")
    a.set_xlabel("time since PDI [s]"); a.set_ylabel("altitude [km]")

    # 4 - velocities
    a = ax[1, 0]
    a.plot(T, vh, label="horizontal")
    a.plot(T, vv, label="vertical")
    a.set_title("Powered descent: velocity")
    a.set_xlabel("time since PDI [s]"); a.set_ylabel("m/s")
    a.legend()

    # 5 - throttle / fuel
    a = ax[1, 1]
    a.plot(T, thr, color="tab:red", label="throttle [%]")
    a.set_ylabel("throttle [%]"); a.set_xlabel("time since PDI [s]")
    b = a.twinx()
    b.plot(T, fuel, color="tab:green", label="descent prop")
    b.set_ylabel("propellant [kg]")
    a.set_title("Throttle and propellant")

    # 6 - nav error
    a = ax[1, 2]
    a.plot(T, pe, label="position error [m]")
    a.plot(T, ve * 100, label="velocity error [cm/s]")
    a.set_title("Navigation error (estimate vs truth)")
    a.set_xlabel("time since PDI [s]")
    a.legend()

    plt.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"\nPlot saved to {path}")
    if show:
        plt.show()


# ============================================================
# MAIN
# ============================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--out", default="moon_mission.png")
    args = ap.parse_args()

    if not args.show:
        matplotlib.use("Agg")

    m = Mission(seed=args.seed)
    m.run()
    m.summary()
    make_plots(m, args.out, args.show)


if __name__ == "__main__":
    main()
