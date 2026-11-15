#!/usr/bin/env python3
"""S1: fetch each showcase drive's road line and elevation, write routes/<id>.gpx and a preview.

    python3 showcase/fetch_routes.py [id ...]

The line comes from the public OSRM server (OpenStreetMap data, ODbL), the elevation from
Open-Meteo's elevation API (Copernicus DEM, 90 m). Requests carry only the public waypoints in
drives.json. Network goes through `curl` (the system's certificates). Standard library only.
A line the owner redraws in gpx.studio replaces routes/<id>.gpx; run with --preview-only to redraw
its preview without fetching.
"""

import json
import math
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTES = HERE / "routes"
R = 6_371_000.0


def curl_json(url: str) -> dict:
    out = subprocess.run(
        ["curl", "-sS", "-m", "60", "-A", "carodo-showcase-routes/0.1", url],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def haversine(a, b) -> float:
    (lat1, lon1), (lat2, lon2) = a, b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def osrm(waypoints):
    coords = ";".join(f"{w['lon']},{w['lat']}" for w in waypoints)
    url = (f"https://router.project-osrm.org/route/v1/driving/{coords}"
           "?overview=full&geometries=geojson&steps=true")
    data = curl_json(url)
    if data.get("code") != "Ok":
        raise SystemExit(f"OSRM: {data.get('code')} {data.get('message')}")
    route = data["routes"][0]
    line = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
    roads = []
    for leg in route["legs"]:
        for step in leg["steps"]:
            name = " ".join(x for x in (step.get("ref"), step.get("name")) if x).strip()
            if name and step["distance"] > 300:
                if roads and roads[-1][0] == name:
                    roads[-1][1] += step["distance"]
                else:
                    roads.append([name, step["distance"]])
    return line, route["distance"], route["duration"], roads


def resample(line, every_m):
    """Points every `every_m` metres along the line, with their distance from the start."""
    out = [(0.0, line[0])]
    dist, carry = 0.0, 0.0
    for a, b in zip(line, line[1:]):
        seg = haversine(a, b)
        if seg == 0:
            continue
        t = every_m - carry
        while t <= seg:
            f = t / seg
            out.append((dist + t, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)))
            t += every_m
        carry = seg - (t - every_m)
        dist += seg
    out.append((dist, line[-1]))
    return out


def elevations(points):
    result = []
    for i in range(0, len(points), 100):
        chunk = points[i:i + 100]
        q = urllib.parse.urlencode({
            "latitude": ",".join(f"{p[0]:.5f}" for p in chunk),
            "longitude": ",".join(f"{p[1]:.5f}" for p in chunk),
        })
        for attempt in range(6):
            data = curl_json(f"https://api.open-meteo.com/v1/elevation?{q}")
            if "elevation" in data:
                break
            print(f"  elevation: {data.get('reason')}; waiting 65 s", file=sys.stderr)
            time.sleep(65)
        else:
            raise SystemExit("elevation API kept refusing")
        result += data["elevation"]
        time.sleep(2)
    return result


def smooth_along_road(values, median_n=7, mean_n=5):
    """A terrain model at 90 m catches the slope beside a mountain road (the cliff above, the drop
    below). A running median over ~7 samples, then a running mean, keeps the road's own climb."""
    def run(xs, n, f):
        h = n // 2
        return [f(xs[max(0, i - h):i + h + 1]) for i in range(len(xs))]
    med = run(values, median_n, lambda w: sorted(w)[len(w) // 2])
    return run(med, mean_n, lambda w: sum(w) / len(w))


def write_gpx(drive, line, eles, path):
    pts = "\n".join(
        f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{ele:.1f}</ele></trkpt>'
        for (lat, lon), ele in zip(line, eles))
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="carodo-handbook showcase/fetch_routes.py" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n'
        f'  <metadata><name>{drive["title"]}</name>'
        '<copyright author="OpenStreetMap contributors"><license>'
        'https://opendatacommons.org/licenses/odbl/</license></copyright>'
        '<desc>Road line from OSRM (OpenStreetMap), elevation from Open-Meteo (Copernicus DEM), smoothed along the road. '
        'A road, not a recorded drive.</desc></metadata>\n'
        f'  <trk><name>{drive["id"]}</name><trkseg>\n{pts}\n  </trkseg></trk>\n</gpx>\n')


def read_gpx(path):
    import xml.etree.ElementTree as ET
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    root = ET.parse(path).getroot()
    pts = root.findall(".//g:trkpt", ns) or root.findall(".//g:rtept", ns)
    line, eles = [], []
    for p in pts:
        line.append((float(p.get("lat")), float(p.get("lon"))))
        e = p.find("g:ele", ns)
        eles.append(float(e.text) if e is not None else 0.0)
    return line, eles


def climb(eles):
    up = down = 0.0
    smooth = [sum(eles[max(0, i - 2):i + 3]) / len(eles[max(0, i - 2):i + 3]) for i in range(len(eles))]
    for a, b in zip(smooth, smooth[1:]):
        if b > a:
            up += b - a
        else:
            down += a - b
    return up, down


def write_preview(drive, line, eles, path, summary):
    """A plain SVG: the line (north up) with its waypoints, and the elevation profile."""
    lat0 = sum(p[0] for p in line) / len(line)
    k = math.cos(math.radians(lat0))
    xs = [p[1] * k for p in line]
    ys = [-p[0] for p in line]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) or 1
    W, M = 520, 20
    sx = lambda x: M + (x - minx) / span * (W - 2 * M)
    sy = lambda y: M + (y - miny) / span * (W - 2 * M)
    path_d = "M" + " L".join(f"{sx(x):.1f} {sy(y):.1f}" for x, y in zip(xs, ys))
    wps = "".join(
        f'<circle cx="{sx(w["lon"] * k):.1f}" cy="{sy(-w["lat"]):.1f}" r="5" fill="#242321"/>'
        f'<text x="{sx(w["lon"] * k) + 8:.1f}" y="{sy(-w["lat"]) + 4:.1f}" font-size="12">{w["name"]}</text>'
        for w in drive["waypoints"])
    # Elevation profile by distance.
    dists = [0.0]
    for a, b in zip(line, line[1:]):
        dists.append(dists[-1] + haversine(a, b))
    total = dists[-1] or 1
    emin, emax = min(eles), max(eles)
    erange = (emax - emin) or 1
    PH, PY = 140, W + 30
    prof = "M" + " L".join(
        f"{M + d / total * (W - 2 * M):.1f} {PY + PH - (e - emin) / erange * PH:.1f}"
        for d, e in zip(dists, eles))
    H = PY + PH + 50
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="-apple-system, sans-serif">'
        f'<rect width="{W}" height="{H}" fill="#faf7f1"/>'
        f'<path d="{path_d}" fill="none" stroke="#bd8053" stroke-width="3" stroke-linejoin="round"/>{wps}'
        f'<path d="{prof}" fill="none" stroke="#965e36" stroke-width="2"/>'
        f'<text x="{M}" y="{PY - 8}" font-size="12">{emax:.0f} m max · {emin:.0f} m min</text>'
        f'<text x="{M}" y="{H - 18}" font-size="13" font-weight="600">{drive["title"]}: {summary}</text>'
        f'<text x="{W - M}" y="{H - 4}" font-size="9" text-anchor="end">© OpenStreetMap contributors</text>'
        '</svg>\n')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    preview_only = "--preview-only" in sys.argv
    drives = json.loads((HERE / "drives.json").read_text())["drives"]
    ROUTES.mkdir(exist_ok=True)
    report = []
    for drive in drives:
        if args and drive["id"] not in args:
            continue
        gpx = ROUTES / f"{drive['id']}.gpx"
        if preview_only:
            line, eles = read_gpx(gpx)
            roads = []
            osrm_s = None
        else:
            line, dist, osrm_s, roads = osrm([w for w in drive["waypoints"] if w.get("via", True)])
            # About 400 elevation samples a drive at most (the API's per-minute limit), 100 m apart at least.
            samples = resample(line, max(100.0, dist / 400))
            ele_at = smooth_along_road(elevations([p for _, p in samples]))
            # Each line vertex takes the elevation of the nearest sample.
            dists = [0.0]
            for a, b in zip(line, line[1:]):
                dists.append(dists[-1] + haversine(a, b))
            sd = [d for d, _ in samples]
            eles, j = [], 0
            for d in dists:
                while j + 1 < len(sd) and abs(sd[j + 1] - d) <= abs(sd[j] - d):
                    j += 1
                eles.append(float(ele_at[j]))
            write_gpx(drive, line, eles, gpx)
        length = sum(haversine(a, b) for a, b in zip(line, line[1:]))
        up, down = climb(eles)
        summary = f"{length / 1000:.1f} km, +{up:.0f} m / −{down:.0f} m"
        write_preview(drive, line, eles, ROUTES / f"{drive['id']}.svg", summary)
        report.append({
            "id": drive["id"], "km": round(length / 1000, 1), "points": len(line),
            "osrm_minutes": None if osrm_s is None else round(osrm_s / 60),
            "elevation_m": [round(min(eles)), round(max(eles))], "climb_m": round(up), "descent_m": round(down),
            "roads": [f"{n} ({d / 1000:.1f} km)" for n, d in roads],
        })
        time.sleep(1)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
