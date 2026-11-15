#!/usr/bin/env python3
"""Drive a showcase route on the iOS Simulator, so the app records it through its real path.

    python3 showcase/sim_drive.py <id> --udid <SIMULATOR-UDID> [--scale 1] [--stops] [--dry-run]

Reads routes/<id>.gpx and plays it with `xcrun simctl location start` as one continuous scenario at
the drive's average moving speed (from the curvature profile, the S2 model without noise). With
--profile the speed follows the curvature, one scenario per stretch; restarting a scenario can jump
the position ahead (90-330 m on the Prenn test), and the app's filter rightly drops those jumps
from the distance, so --profile is for looking at the live panel only. Start a drive in the app first (Start Drive, or `xcrun simctl openurl <udid>
carodo://trip/start`). At the end the car slows to a stop and the Simulator stops sending fixes;
the app ends the drive by itself (StopDetector's silent stop, then the 300 s grace).

--scale N plays N times faster (the recorded speeds are N times too high: a preview only).
--stops holds at the drive's stops (capped at 4 min: past StopDetector's 300 s grace a stop ends
the drive). Standard library only.
"""

import argparse
import json
import math
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = 6_371_000.0
STEP_M = 10.0
A_LAT = {"pass": 2.0, "expressway": 1.5}
ACCEL, BRAKE = 1.2, 2.0
MAX_STOP_S = 240


def haversine(a, b):
    (lat1, lon1), (lat2, lon2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def read_line(path):
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    return [(float(p.get("lat")), float(p.get("lon"))) for p in ET.parse(path).getroot().findall(".//g:trkpt", ns)]


def resample(line, step):
    out = [line[0]]
    carry = 0.0
    for a, b in zip(line, line[1:]):
        seg = haversine(a, b)
        t = step - carry
        while t <= seg:
            f = t / seg
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            t += step
        carry = seg - (t - step) if seg else carry
    out.append(line[-1])
    return out


def radius(a, b, c):
    """Circumradius of three points (metres), on a local flat projection."""
    k = math.cos(math.radians(b[0]))
    pts = [(math.radians(p[1]) * R * k, math.radians(p[0]) * R) for p in (a, b, c)]
    (x1, y1), (x2, y2), (x3, y3) = pts
    ab, bc, ca = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2]), math.dist(pts[2], pts[0])
    area2 = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
    return float("inf") if area2 < 1e-9 else ab * bc * ca / (2 * area2)


def profile(pts, v_road, a_lat, stop_idx):
    n = len(pts)
    span = 2  # 20 m either side
    v = []
    for i in range(n):
        r = radius(pts[max(0, i - span)], pts[i], pts[min(n - 1, i + span)]) if 0 < i < n - 1 else float("inf")
        v.append(min(v_road, math.sqrt(a_lat * r)))
    v[0] = v[-1] = 0.0
    for i in stop_idx:
        v[i] = 0.0
    for i in range(1, n):  # acceleration cap
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * ACCEL * STEP_M))
    for i in range(n - 2, -1, -1):  # braking cap
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * BRAKE * STEP_M))
    return v


def nearest_index(pts, lat, lon):
    return min(range(len(pts)), key=lambda i: haversine(pts[i], (lat, lon)))


def chunks(pts, v, stops):
    """Stretches of near-constant speed (1 m/s bins), split at the stops."""
    out, cur, cur_bin = [], [0], None
    for i in range(1, len(pts)):
        b = max(1.5, round(v[i]))
        if i in stops or (cur_bin is not None and b != cur_bin and len(cur) >= 3):
            cur.append(i)
            out.append((cur, cur_bin or b))
            cur, cur_bin = [i], None
            if i in stops:
                out.append(("stop", stops[i]))
            continue
        cur.append(i)
        cur_bin = b if cur_bin is None else cur_bin
    if len(cur) > 1:
        out.append((cur, cur_bin or 1.5))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--udid", required=True)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--stops", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--profile", action="store_true",
                    help="vary the speed by curvature, one scenario per stretch; known to jump 90-330 m "
                         "at some restarts (2026-11-15, Prenn: 17 jumps, the app kept 12.1 of 14.0 km)")
    a = ap.parse_args()

    drive = next(d for d in json.loads((HERE / "drives.json").read_text())["drives"] if d["id"] == a.id)
    pts = resample(read_line(HERE / "routes" / f"{a.id}.gpx"), STEP_M)
    stops = {}
    if a.stops:
        for s in drive.get("stops", []):
            if "at_waypoint" in s:
                w = drive["waypoints"][s["at_waypoint"]]
                i = nearest_index(pts, w["lat"], w["lon"])
            else:
                i = int(s["at_fraction"] * (len(pts) - 1))
            stops[i] = min(MAX_STOP_S, s["minutes"] * 60)
    kind = "expressway" if drive["road_speed_kmh"] >= 90 else "pass"
    v = profile(pts, drive["road_speed_kmh"] / 3.6, A_LAT[kind], set(stops))
    plan = chunks(pts, v, stops)

    dist = (len(pts) - 1) * STEP_M
    secs = sum((len(c) - 1) * STEP_M / s for c, s in plan if c != "stop") + sum(s for c, s in plan if c == "stop")
    vmax = max(v) * 3.6
    print(f"{a.id}: {dist / 1000:.1f} km, {len(plan)} stretches, drive {secs / 60:.0f} min at real speed "
          f"(avg {dist / secs * 3.6:.0f} km/h incl. stops, top {vmax:.0f} km/h); plays in "
          f"{secs / a.scale / 60:.1f} min at ×{a.scale:g}")
    if a.dry_run:
        return

    if not a.profile:
        # One continuous scenario at the drive's average moving speed: no restart, no jump.
        moving_s = sum((len(c) - 1) * STEP_M / sp for c, sp in plan if c != "stop")
        speed = dist / moving_s * a.scale
        print(f"  one scenario at {speed * 3.6:.0f} km/h, about {dist / speed / 60:.0f} min", flush=True)
        wp = "\n".join(f"{lat:.6f},{lon:.6f}" for lat, lon in pts[::2] + [pts[-1]]) + "\n"
        subprocess.run(["xcrun", "simctl", "location", a.udid, "start", f"--speed={speed:.2f}", "--interval=1", "-"],
                       input=wp, text=True, check=True)
        time.sleep(dist / speed + 2)
        tail = [f"{lat:.6f},{lon:.6f}" for lat, lon in pts[-3:]]
        subprocess.run(["xcrun", "simctl", "location", a.udid, "start", "--speed=0.4", "--interval=1", *tail], check=True)
        print("arrived; the app ends the drive by itself after its stop grace (about 5 min)", flush=True)
        return

    for c, speed in plan:
        if c == "stop":
            print(f"  stop {speed / 60:.1f} min", flush=True)
            time.sleep(speed / a.scale)
            continue
        wp = [pts[i] for i in c[:: max(1, len(c) // 40)]] + [pts[c[-1]]]
        args = ["xcrun", "simctl", "location", a.udid, "start", f"--speed={speed * a.scale:.2f}", "--interval=1"]
        args += [f"{lat:.6f},{lon:.6f}" for lat, lon in wp]
        subprocess.run(args, check=True)
        time.sleep((len(c) - 1) * STEP_M / (speed * a.scale))
    # Crawl the last metres: the app needs slow fixes to see a stop. Without them its last fix
    # reads as moving and only the 12 min no-signal timeout ends the drive (tracking.md, Auto-finish).
    tail = [f"{lat:.6f},{lon:.6f}" for lat, lon in pts[-3:]]
    subprocess.run(["xcrun", "simctl", "location", a.udid, "start", "--speed=0.4", "--interval=1", *tail], check=True)
    print("arrived; the app ends the drive by itself after its stop grace (about 5 min)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
