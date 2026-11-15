#!/usr/bin/env python3
"""S2: turn each showcase road line into a drive of realistic raw GPS fixes.

    python3 showcase/generate.py [id ...] [--noise showcase|measured]
    python3 showcase/generate.py --check        # the model's self-test and determinism

Inputs: drives.json (start, seed, stops, road speed), routes/<id>.gpx (the road and its elevation),
noise.json (S0: noise measured on real drives). Outputs in out/:

- <id>.json      every fix with every `trip_points` field (carodo-ios TripPointRecord), at 1 Hz
- <id>.sim.gpx   the same fixes, timed, for Xcode's location playback
- summary.md     length, duration, speeds, stops, climb, noise figures per drive
- shapes.json    each route simplified (~100 points) and normalised to a unit box, no coordinate

The model (plans/showcase-drives.md, "The drive model"): speed from the road's curvature under a
lateral-acceleration limit, capped by the road speed and by acceleration and braking; stops at the
planned places; GPS error as an AR(1) process whose size follows a two-state accuracy chain (good /
degraded), gaps, drift while stopped, noisy speed and course, altitude and barometric pressure.
`--noise showcase` (default) keeps the measured figures but halves the degraded share and shortens
gaps, so a Replay never jumps; `--noise measured` uses them as measured, for tests.

Deterministic: one seed per drive; the same inputs give byte-identical outputs. Standard library only.
"""

import argparse
import hashlib
import json
import math
import random
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
R = 6_371_000.0
STEP_M = 5.0  # the road is resampled every 5 m
A_LAT = {"pass": 2.0, "expressway": 1.5}  # m/s², lateral acceleration a driver accepts
ACCEL, BRAKE = 1.2, 2.0  # m/s²
START_IDLE_S, END_IDLE_S = 12, 20  # stationary fixes before setting off and after arriving
FIELDS = ["recorded_at", "latitude", "longitude", "altitude_m", "speed_mps", "course_deg",
          "horizontal_accuracy_m", "vertical_accuracy_m", "speed_accuracy_mps", "course_accuracy_deg",
          "pressure_kpa"]
ZONES = {"Asia/Ho_Chi_Minh": 7}


# ---------------------------------------------------------------------------------------- geometry

def haversine(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def read_gpx(path):
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    line, eles = [], []
    for p in ET.parse(path).getroot().findall(".//g:trkpt", ns):
        line.append((float(p.get("lat")), float(p.get("lon"))))
        e = p.find("g:ele", ns)
        eles.append(float(e.text) if e is not None else 0.0)
    return line, eles


def resample(line, eles, step):
    """Points every `step` metres along the line, with interpolated elevation."""
    pts, ele = [line[0]], [eles[0]]
    carry = 0.0
    for (a, ea), (b, eb) in zip(zip(line, eles), zip(line[1:], eles[1:])):
        seg = haversine(a, b)
        if seg == 0:
            continue
        t = step - carry
        while t <= seg:
            f = t / seg
            pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            ele.append(ea + (eb - ea) * f)
            t += step
        carry = seg - (t - step)
    pts.append(line[-1])
    ele.append(eles[-1])
    return pts, ele


def to_xy(p, origin):
    k = math.cos(math.radians(origin[0]))
    return (math.radians(p[1] - origin[1]) * R * k, math.radians(p[0] - origin[0]) * R)


def from_xy(x, y, origin):
    k = math.cos(math.radians(origin[0]))
    return (origin[0] + math.degrees(y / R), origin[1] + math.degrees(x / (R * k)))


def circumradius(a, b, c):
    ab, bc, ca = math.dist(a, b), math.dist(b, c), math.dist(c, a)
    area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
    return math.inf if area2 < 1e-9 else ab * bc * ca / (2 * area2)


def heading(a, b):
    """Degrees clockwise from north, from xy point a to b."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360


# ----------------------------------------------------------------------------------- speed model

def speed_profile(xy, v_road, a_lat, stop_idx, rng):
    """Target speed at each resampled point (m/s)."""
    n = len(xy)
    span = 4  # ±20 m
    # The driver's own pace drifts slowly around the road speed (0.9-1.03).
    pace, pace_v = [], 0.0
    for _ in range(n):
        pace_v = 0.995 * pace_v + 0.1 * rng.gauss(0, 0.02)
        pace.append(min(1.03, max(0.9, 0.97 + pace_v)))
    v = []
    for i in range(n):
        if 0 < i < n - 1:
            r = circumradius(xy[max(0, i - span)], xy[i], xy[min(n - 1, i + span)])
        else:
            r = math.inf
        v.append(min(v_road * pace[i], math.sqrt(a_lat * r)))
    v[0] = v[-1] = 0.0
    for i in stop_idx:
        v[i] = 0.0
    for i in range(1, n):
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * ACCEL * STEP_M))
    for i in range(n - 2, -1, -1):
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * BRAKE * STEP_M))
    return v


def drive_timeline(v, stops):
    """Integrate the speed profile at 1 Hz. Returns [(distance_m, speed_mps, stopped)] per second."""
    total = (len(v) - 1) * STEP_M
    stop_at = sorted((i * STEP_M, secs) for i, secs in stops.items())
    out = [(0.0, 0.0, True)] * START_IDLE_S
    s = 0.0

    def v_at(dist):
        i = min(len(v) - 2, int(dist / STEP_M))
        f = dist / STEP_M - i
        return v[i] + (v[i + 1] - v[i]) * f

    while s < total:
        speed = max(v_at(s), 0.4)  # never stall between stops
        nxt = s + speed
        if stop_at and nxt >= stop_at[0][0] > s:
            s = stop_at[0][0]
            out.append((s, 0.0, True))
            out += [(s, 0.0, True)] * int(stop_at[0][1])
            stop_at.pop(0)
            continue
        s = min(total, nxt)
        out.append((s, v_at(s), False))
    out += [(total, 0.0, True)] * END_IDLE_S
    return out


# ----------------------------------------------------------------------------------- noise model

def from_percentiles(rng, pct):
    """A value drawn from a piecewise-linear distribution given by p10..p90 style keys."""
    keys = sorted((int(k[1:]), v) for k, v in pct.items() if k.startswith("p"))
    u = rng.uniform(keys[0][0], keys[-1][0])
    for (p0, v0), (p1, v1) in zip(keys, keys[1:]):
        if u <= p1:
            return v0 + (v1 - v0) * (u - p0) / (p1 - p0)
    return keys[-1][1]


class Noise:
    def __init__(self, params, mode, rng):
        self.rng = rng
        h = params["horizontal_accuracy_m"]["while_moving"]
        self.good = h["good"]
        self.bad = h["degraded"]
        self.stopped_acc = params["horizontal_accuracy_m"]["while_stopped"]
        good_mean, bad_mean = h["good_run_s"]["mean"], h["degraded_run_s"]["mean"]
        if mode == "showcase":
            bad_mean /= 2
        self.p_leave_good = 1 / good_mean
        self.p_leave_bad = 1 / bad_mean
        # The showcase starts with a clear sky; measured noise starts where the chain usually is.
        self.degraded = mode == "measured" and rng.random() < bad_mean / (good_mean + bad_mean)
        # The error is a smooth second-order process (iOS filters its fixes, so they drift rather
        # than jitter): a slow AR(1) driven by another AR(1). Its size follows the reported
        # accuracy (about the 68 % radius, so ~0.7 of it per axis). S0's cross-track figure is not
        # used for the size: on real streets it measures the road's turns as much as the GPS.
        self.phi, self.psi = 0.93, 0.9
        self.sd = {False: 0.75 * self.good["p50"], True: 0.7 * self.bad["p50"]}
        self.ex = self.ey = self.wx = self.wy = 0.0
        self.unit = math.sqrt((1 + self.phi * self.psi) / ((1 - self.phi * self.psi)))  # AR(2) variance gain
        g = params["gaps"]
        self.gap_rate = g["over_3s_per_moving_hour"] / 3600 * (0.5 if mode == "showcase" else 1.0)
        self.gap_len = g["length_s"] if mode == "measured" else {"p10": 4.0, "p50": 6.0, "p90": 9.0}
        self.drift = params["stopped"]["drift_rms_m"]["p50"]
        self.vacc = params["vertical_accuracy_m"]
        self.sacc = params["speed"]["accuracy_mps"]
        self.speed_sd = params["speed"]["error_vs_positions_mps"]["sd"]
        self.cacc = params["course"]["accuracy_deg"]
        self.alt_e = 0.0
        self.press_drift = 0.0
        self.press_step = params["pressure"]["drift_pa_per_min_at_stops"]["p50"] / 60 / 1000  # kPa/s
        self.lapse = params["pressure"]["lapse_pa_per_m"]

    def step_state(self):
        r = self.rng.random()
        if self.degraded and r < self.p_leave_bad:
            self.degraded = False
        elif not self.degraded and r < self.p_leave_good:
            self.degraded = True

    def position_error(self, stopped):
        sd = self.drift if stopped else self.sd[self.degraded]
        phi, psi = (0.98, 0.9) if stopped else (self.phi, self.psi)
        k = math.sqrt(1 - psi * psi)
        self.wx = psi * self.wx + k * self.rng.gauss(0, 1)
        self.wy = psi * self.wy + k * self.rng.gauss(0, 1)
        gain = math.sqrt(1 - phi * phi) * sd / self.unit
        self.ex = phi * self.ex + gain * self.wx
        self.ey = phi * self.ey + gain * self.wy
        return self.ex, self.ey

    def horizontal_accuracy(self, stopped):
        if stopped:
            return from_percentiles(self.rng, self.stopped_acc)
        return from_percentiles(self.rng, self.bad if self.degraded else self.good)


def barometric_kpa(alt_m):
    return 101.325 * (1 - 2.25577e-5 * alt_m) ** 5.25588


# -------------------------------------------------------------------------------------- one drive

def generate(drive, params, mode):
    rng = random.Random(drive["seed"])
    line, eles = read_gpx(HERE / "routes" / f"{drive['id']}.gpx")
    pts, ele = resample(line, eles, STEP_M)
    origin = pts[0]
    xy = [to_xy(p, origin) for p in pts]

    stops = {}
    for s in drive.get("stops", []):
        if "at_waypoint" in s:
            w = drive["waypoints"][s["at_waypoint"]]
            i = min(range(len(pts)), key=lambda k: haversine(pts[k], (w["lat"], w["lon"])))
        else:
            i = int(s["at_fraction"] * (len(pts) - 1))
        stops[i] = min(240, int(s["minutes"] * 60))

    kind = "expressway" if drive["road_speed_kmh"] >= 90 else "pass"
    v = speed_profile(xy, drive["road_speed_kmh"] / 3.6, A_LAT[kind], set(stops), rng)
    timeline = drive_timeline(v, stops)

    offset = ZONES[drive["time_zone"]]
    start_local = datetime.fromisoformat(drive["start"])
    t0 = (start_local - timedelta(hours=offset)).replace(tzinfo=timezone.utc).timestamp()

    noise = Noise(params, mode, rng)
    weather = rng.uniform(-0.4, 0.4)  # kPa: the day's pressure against the standard atmosphere
    fixes, gaps, gap_left, degraded_moving, moving = [], 0, 0, 0, 0
    prev_xy = None
    for sec, (dist, speed, stopped) in enumerate(timeline):
        noise.step_state()
        i = min(len(xy) - 2, int(dist / STEP_M))
        f = dist / STEP_M - i
        x = xy[i][0] + (xy[i + 1][0] - xy[i][0]) * f
        y = xy[i][1] + (xy[i + 1][1] - xy[i][1]) * f
        alt_true = ele[i] + (ele[i + 1] - ele[i]) * f
        ex, ey = noise.position_error(stopped)

        if not stopped:
            moving += 1
            degraded_moving += noise.degraded
            if gap_left == 0 and rng.random() < noise.gap_rate:
                gap_left = max(4, round(from_percentiles(rng, noise.gap_len)))
                gaps += 1
        if gap_left > 0:
            gap_left -= 1
            continue

        lat, lon = from_xy(x + ex, y + ey, origin)
        hacc = noise.horizontal_accuracy(stopped)
        vacc = from_percentiles(rng, noise.vacc)
        noise.alt_e = 0.95 * noise.alt_e + math.sqrt(1 - 0.95 ** 2) * 0.6 * vacc * rng.gauss(0, 1)
        if stopped:
            spd, crs, cacc = max(0.0, abs(rng.gauss(0, 0.08))), None, None
            sacc = from_percentiles(rng, {"p10": 0.4, "p50": 0.7, "p90": 1.2})
        else:
            spd = max(0.0, speed + rng.gauss(0, noise.speed_sd * (0.5 if not noise.degraded else 1.0)))
            ahead = xy[min(len(xy) - 1, i + 3)]
            crs = (heading((x, y), ahead) + rng.gauss(0, 3 if not noise.degraded else 8)) % 360
            cacc = from_percentiles(rng, {"p10": 9.5, "p50": 14.5, "p90": 25.1} if not noise.degraded
                                    else {"p10": 25.1, "p50": 45.0, "p90": 65.9})
            sacc = from_percentiles(rng, {"p10": 0.72, "p50": 0.96, "p90": 1.52} if not noise.degraded
                                    else {"p10": 1.52, "p50": 2.69, "p90": 3.67})
        noise.press_drift += rng.gauss(0, noise.press_step * 3)
        pressure = barometric_kpa(alt_true) + weather + noise.press_drift + rng.gauss(0, 0.002)
        t = t0 + sec + rng.uniform(-0.004, 0.004)
        fixes.append([
            round(t, 3), round(lat, 7), round(lon, 7), round(alt_true + noise.alt_e, 2), round(spd, 2),
            None if crs is None else round(crs, 2), round(hacc, 2), round(vacc, 2), round(sacc, 2),
            None if cacc is None else round(cacc, 2), round(pressure, 3),
        ])
        prev_xy = (x, y)

    length = (len(pts) - 1) * STEP_M
    duration = timeline and len(timeline)
    moving_s = sum(1 for _, _, s in timeline if not s)
    up = sum(max(0.0, b - a) for a, b in zip(ele[::20], ele[20::20]))
    summary = {
        "km": round(length / 1000, 1),
        "fixes": len(fixes),
        "duration_min": round(duration / 60, 1),
        "moving_min": round(moving_s / 60, 1),
        "avg_moving_kmh": round(length / moving_s * 3.6, 1) if moving_s else 0,
        "top_kmh": round(max(v) * 3.6, 1),
        "stops": [round(s / 60, 1) for s in stops.values()],
        "climb_m": round(up),
        "elevation_m": [round(min(ele)), round(max(ele))],
        "degraded_share": round(degraded_moving / moving, 3) if moving else 0,
        "gaps": gaps,
    }
    started = datetime.fromtimestamp(fixes[0][0], timezone.utc)
    ended = datetime.fromtimestamp(fixes[-1][0], timezone.utc)
    doc = {
        "about": "Synthetic drive on a public road (carodo-handbook showcase). Not a recorded drive. "
                 "Times UTC; units SI; null = not reported (as CoreLocation's -1).",
        "id": drive["id"], "title": drive["title"], "time_zone": drive["time_zone"],
        "noise": mode, "seed": drive["seed"],
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "ended_at": ended.isoformat().replace("+00:00", "Z"),
        "summary": summary, "fields": FIELDS, "fixes": fixes,
    }
    return doc, pts


def write_sim_gpx(doc, path):
    rows = []
    for f in doc["fixes"]:
        t = datetime.fromtimestamp(f[0], timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        rows.append(f'      <trkpt lat="{f[1]:.7f}" lon="{f[2]:.7f}"><ele>{f[3]:.1f}</ele><time>{t}</time></trkpt>')
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="carodo-handbook showcase/generate.py" xmlns="http://www.topografix.com/GPX/1/1">\n'
        f'  <metadata><name>{doc["title"]}</name><desc>Synthetic drive, not recorded. Road © OpenStreetMap contributors.</desc></metadata>\n'
        f'  <trk><name>{doc["id"]}</name><trkseg>\n' + "\n".join(rows) + "\n  </trkseg></trk>\n</gpx>\n")


def simplify(xy, eps):
    """Douglas-Peucker."""
    if len(xy) < 3:
        return xy
    a, b = xy[0], xy[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-9
    far, idx = -1.0, 0
    for i in range(1, len(xy) - 1):
        d = abs(dy * xy[i][0] - dx * xy[i][1] + b[0] * a[1] - b[1] * a[0]) / L
        if d > far:
            far, idx = d, i
    if far <= eps:
        return [a, b]
    return simplify(xy[:idx + 1], eps)[:-1] + simplify(xy[idx:], eps)


def shape(pts, target=100):
    origin = pts[0]
    xy = [to_xy(p, origin) for p in pts]
    lo, hi = 0.1, 5000.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if len(simplify(xy, mid)) > target:
            lo = mid
        else:
            hi = mid
    s = simplify(xy, hi)
    xs, ys = [p[0] for p in s], [p[1] for p in s]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1
    # North up, y downwards as in SVG; the box is 1 on its longer side.
    return {
        "aspect": round((max(xs) - min(xs)) / ((max(ys) - min(ys)) or 1), 3),
        "points": [[round((x - min(xs)) / span, 4), round((max(ys) - y) / span, 4)] for x, y in s],
    }


def write_summary(docs, path):
    lines = [
        "# Generated showcase drives", "",
        "Synthetic, not recorded. `python3 showcase/generate.py` writes this file; do not edit it.", "",
        "| id | Length | Duration | Moving | Avg moving | Top | Stops | Climb | Elevation | Fixes | Degraded | Gaps |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for d in docs:
        s = d["summary"]
        stops = ", ".join(f"{m:g} min" for m in s["stops"]) or "none"
        lines.append(
            f"| `{d['id']}` | {s['km']} km | {s['duration_min']} min | {s['moving_min']} min | "
            f"{s['avg_moving_kmh']} km/h | {s['top_kmh']} km/h | {stops} | +{s['climb_m']} m | "
            f"{s['elevation_m'][0]}–{s['elevation_m'][1]} m | {s['fixes']} | {s['degraded_share']:.0%} | {s['gaps']} |")
    lines += ["", f"Noise: `{docs[0]['noise']}` (see the generator's docstring)."]
    path.write_text("\n".join(lines) + "\n")


def dump(doc):
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))


# ------------------------------------------------------------------------------------- self-test

def check(params):
    ok = True

    def expect(cond, what):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + what)
        ok &= cond

    # Speed on a circle of known radius: sqrt(a_lat × R), within the profile's sampling.
    radius_m = 100.0
    xy = [(radius_m * math.cos(a), radius_m * math.sin(a)) for a in [k * STEP_M / radius_m for k in range(120)]]
    v = speed_profile(xy, 50, 2.0, set(), random.Random(1))
    mid = v[60]
    expect(abs(mid - math.sqrt(2.0 * radius_m)) < 0.3, f"curve speed {mid:.2f} ≈ {math.sqrt(200):.2f} m/s on R=100 m")
    # Acceleration and braking caps.
    straight = [(k * STEP_M, 0.0) for k in range(400)]
    v = speed_profile(straight, 30, 2.0, set(), random.Random(1))
    acc = max((v[i + 1] ** 2 - v[i] ** 2) / (2 * STEP_M) for i in range(len(v) - 1))
    brk = max((v[i] ** 2 - v[i + 1] ** 2) / (2 * STEP_M) for i in range(len(v) - 1))
    expect(acc <= ACCEL + 1e-6 and brk <= BRAKE + 1e-6, f"accel {acc:.2f} ≤ {ACCEL}, brake {brk:.2f} ≤ {BRAKE} m/s²")
    # Determinism, stops and gaps on a real drive.
    drives = {d["id"]: d for d in json.loads((HERE / "drives.json").read_text())["drives"]}
    a, _ = generate(drives["hai-van"], params, "measured")
    b, _ = generate(drives["hai-van"], params, "measured")
    ha, hb = hashlib.sha256(dump(a).encode()).hexdigest(), hashlib.sha256(dump(b).encode()).hexdigest()
    expect(ha == hb, f"deterministic ({ha[:12]})")
    still = 0
    run = best = 0
    for f in a["fixes"]:
        run = run + 1 if f[4] < 0.5 else 0
        best = max(best, run)
    expect(best >= 200, f"the planned stop is there ({best} s still)")
    dts = [y[0] - x[0] for x, y in zip(a["fixes"], a["fixes"][1:])]
    expect(max(dts) >= 4, f"gaps present (longest {max(dts):.0f} s)")
    expect(all(d > 0 for d in dts), "time always moves forward")
    expect(all(len(f) == len(FIELDS) for f in a["fixes"]), "every fix has every field")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--noise", choices=["showcase", "measured"], default="showcase")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    params = json.loads((HERE / "noise.json").read_text())
    if args.check:
        return 0 if check(params) else 1

    drives = json.loads((HERE / "drives.json").read_text())["drives"]
    OUT.mkdir(exist_ok=True)
    docs, shapes = [], {}
    for drive in drives:
        if args.ids and drive["id"] not in args.ids:
            continue
        doc, pts = generate(drive, params, args.noise)
        (OUT / f"{drive['id']}.json").write_text(dump(doc) + "\n")
        write_sim_gpx(doc, OUT / f"{drive['id']}.sim.gpx")
        shapes[drive["id"]] = shape(pts)
        docs.append(doc)
        s = doc["summary"]
        print(f"{drive['id']:11} {s['km']:6} km {s['duration_min']:6} min  avg {s['avg_moving_kmh']} km/h  "
              f"top {s['top_kmh']}  fixes {s['fixes']}  degraded {s['degraded_share']:.0%}  gaps {s['gaps']}")
    if not args.ids:
        write_summary(docs, OUT / "summary.md")
        (OUT / "shapes.json").write_text(json.dumps(
            {"about": "Route shapes simplified and normalised to a unit box (x right, y down, north up). "
                      "No coordinate. Roads © OpenStreetMap contributors.", "shapes": shapes},
            ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
