"""Carodo brand: the mark, the lockup and the app-icon sources, generated from parameters.

    python3 mark.py            # writes geometry.json; export.swift turns it into every asset

The mark was traced from the brand board (../brand-board.png) and redrawn as clean geometry on a
100x100 grid: wheel centre (50,50), outer ring radius 46. Measured values were then regularised:
the five spokes are spaced evenly at 72 degrees with one shared width profile, and the hub is
centred. The journey is the board's two strokes. The first is a copper swoosh, its edges fitted to
the traced pixels (max error 0.5). The second is a dashed lane of three dashes in perspective, which
converge on the swoosh tip. Wherever two parts cross, a gap is knocked out between them, so the mark
reads on any background, including the transparent iOS dark and tinted icons.

The wordmark is "Carodo" in Plus Jakarta Sans at weight 700, outlined to a path by wordmark.swift into
wordmark.json. Editing guide: ../brand.md.
"""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))

# Brand colours: the CarodoColor tokens in carodo-ios/Carodo/DesignSystem.
CHARCOAL, COPPER, IVORY, STONE = "#242321", "#BD8053", "#F3EEE5", "#77736D"
C = 50.0  # wheel centre

# ------------------------------------------------------------------ parameters
# All lengths are in grid units (outer ring radius = 46). "board" = value measured on brand-board.png.
FULL = dict(
    # ring
    ring_r=43.1, ring_w=5.8,                 # board: ring spans r 40.2 .. 46.0
    # hub: copper cap, dark gap, ivory hub ring
    cap_r=7.6, hub_gap_r=10.2, hub_r=13.6,   # board 7.2 / 10.5 / 13.5; tuned so the ivory ring (3.4)
                                             # outweighs the gap (2.6) and reads at 29-48 px
    # spokes: width(r) = a + k*r, from spoke_r0 to the tip at spoke_r1
    spoke_r0=12.0, spoke_r1=36.0,            # board: tips at r ~36
    spoke_w=(14.1, -0.185),                  # board: 11.6 wide at the hub, 7.4 at the tip
    tip_round=1.5,                           # board: square tips, small rounded corners
    # knock-out gap around everything the journey crosses
    gap=2.3,
    # swoosh: upper edge (left -> tip) and lower edge (tip -> left) as cubic Beziers, fitted to the board
    upper=[(24.9, 88.5), (43.55, 75.02), (67.53, 64.32), (92.4, 67.4)],
    lower=[(92.4, 68.1), (71.8, 68.76), (52.38, 75.61), (39.5, 91.7)],
    cut_r=46.2,                              # board: the swoosh's left end follows the ring's outer circle
    # lane: the road's centre line (cubic Bezier), its dashes as ranges along it (0 = near, 1 = far)
    # and its thickness from near to far. Lengths, gaps and thickness all shrink toward the tip.
    lane=[(53.77, 85.88), (59.95, 82.42), (68.67, 76.69), (77.84, 73.33)],  # board's dash line, 18 % toward the swoosh
    dashes=[(0.0, 0.40), (0.49, 0.72), (0.79, 0.93)],
    lane_w=(3.4, 1.2),
)
# <= 32 px and favicons: heavier strokes, wider gap, no lane and no hub gap (they cannot be read)
SMALL = dict(FULL, ring_r=42.25, ring_w=7.5, cap_r=8.0, hub_gap_r=0, hub_r=13.5,
             spoke_w=(16.5, -0.17), tip_round=2.0, gap=3.2, dashes=[])

# Lockup (mark + wordmark), in units of the mark's ring diameter D = 92. Board: cap height 0.364 D,
# gap 0.132 D. Weight 700 makes the letter stems (0.064 D) as heavy as the ring (0.063 D).
LOCKUP = dict(cap_height=0.364, gap=0.132)
ICON_SCALE = 8.0  # app icon: the mark spans 800 of 1024


# ------------------------------------------------------------------ helpers

def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def bez(p, t):
    u = 1 - t
    return tuple(u**3 * p[0][i] + 3 * u * u * t * p[1][i] + 3 * u * t * t * p[2][i] + t**3 * p[3][i]
                 for i in (0, 1))


def cubic(p):
    return f"C{f(p[1][0])} {f(p[1][1])} {f(p[2][0])} {f(p[2][1])} {f(p[3][0])} {f(p[3][1])}"


def poly(pts):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + " Z"


def circle_hit(p0, d, r):
    """Point where the ray p0 + s*d (s >= 0) reaches radius r around the centre."""
    px, py = p0[0] - C, p0[1] - C
    a = d[0] ** 2 + d[1] ** 2
    b = 2 * (px * d[0] + py * d[1])
    c = px * px + py * py - r * r
    s = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
    return p0[0] + d[0] * s, p0[1] + d[1] * s


# ------------------------------------------------------------------ wheel

def spokes(p):
    """Five tapered spokes with square, slightly rounded tips; the top one points up."""
    r0, r1, rr = p["spoke_r0"], p["spoke_r1"], p["tip_round"]
    a0, k = p["spoke_w"]
    hw = lambda r: (a0 + k * r) / 2
    out = []
    for i in range(5):
        a = math.radians(-90 + 72 * i)
        ux, uy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
        P = lambda r, s: (C + ux * r + nx * s, C + uy * r + ny * s)
        h1 = hw(r1)
        start, side = P(r0, -hw(r0)), P(r1 - rr, -hw(r1 - rr))
        c1, e1 = P(r1, -h1), P(r1, -h1 + rr)
        s2 = P(r1, h1 - rr)
        c2, e2 = P(r1, h1), P(r1 - rr, hw(r1 - rr))
        end = P(r0, hw(r0))
        out.append(f"M{f(start[0])} {f(start[1])} L{f(side[0])} {f(side[1])} "
                   f"Q{f(c1[0])} {f(c1[1])} {f(e1[0])} {f(e1[1])} L{f(s2[0])} {f(s2[1])} "
                   f"Q{f(c2[0])} {f(c2[1])} {f(e2[0])} {f(e2[1])} L{f(end[0])} {f(end[1])} Z")
    return " ".join(out)


# ------------------------------------------------------------------ journey

def arc(r, p_from, p_to):
    """Cubic Beziers along the circle of radius r around the centre, from p_from to p_to with the angle
    increasing (clockwise on screen). Kept as cubics so every consumer can read the path (no SVG arcs)."""
    a0 = math.atan2(p_from[1] - C, p_from[0] - C)
    a1 = math.atan2(p_to[1] - C, p_to[0] - C)
    while a1 <= a0:
        a1 += 2 * math.pi
    n = max(1, math.ceil((a1 - a0) / (math.pi / 2)))
    step = (a1 - a0) / n
    k = 4 / 3 * math.tan(step / 4) * r
    out = []
    for i in range(n):
        s0, s1 = a0 + i * step, a0 + (i + 1) * step
        c1 = (C + r * math.cos(s0) - k * math.sin(s0), C + r * math.sin(s0) + k * math.cos(s0))
        c2 = (C + r * math.cos(s1) + k * math.sin(s1), C + r * math.sin(s1) - k * math.cos(s1))
        e = (C + r * math.cos(s1), C + r * math.sin(s1))
        out.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(e[0])} {f(e[1])}")
    return " ".join(out)


def circle(r):
    top, bottom = (C, C - r), (C, C + r)
    return f"M{f(top[0])} {f(top[1])} {arc(r, top, bottom)} {arc(r, bottom, top)} Z"


def swoosh(p):
    u, l, r = p["upper"], p["lower"], p["cut_r"]
    corner = circle_hit(l[3], (l[3][0] - l[2][0], l[3][1] - l[2][1]), r)  # lower edge meets the cut circle
    return (f"M{f(u[0][0])} {f(u[0][1])} {cubic(u)} L{f(l[0][0])} {f(l[0][1])} {cubic(l)} "
            f"L{f(corner[0])} {f(corner[1])} {arc(r, corner, u[0])} Z")


def swoosh_cut(p):
    """The swoosh extended outward past its left end, so the ring is cut straight along its edges."""
    u, l = p["upper"], p["lower"]
    a = u[0]
    ta = (a[0] - u[1][0], a[1] - u[1][1]); na = math.hypot(*ta)
    tb = (l[3][0] - l[2][0], l[3][1] - l[2][1]); nb = math.hypot(*tb)
    b = circle_hit(l[3], tb, p["cut_r"])
    return swoosh(p) + " " + poly([a, (a[0] + ta[0] / na * 10, a[1] + ta[1] / na * 10),
                                   (b[0] + tb[0] / nb * 10, b[1] + tb[1] / nb * 10), b])


def under_swoosh(p):
    """The swoosh and everything below it: the spokes stop here, they never peek out under the road."""
    u = p["upper"]
    return f"M{f(u[0][0])} {f(u[0][1])} {cubic(u)} L110 {f(u[3][1])} L110 120 L-10 120 L-10 {f(u[0][1])} Z"


def lane(p):
    """Dashes along the lane curve, shorter and thinner toward the swoosh tip, cut square to the lane."""
    if not p["dashes"]:
        return ""
    n = 400
    pts = [bez(p["lane"], i / n) for i in range(n + 1)]
    acc = [0.0]
    for q0, q1 in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.dist(q0, q1))

    def at(s):  # point and unit tangent at arc-length fraction s
        target = s * acc[-1]
        k = next((k for k in range(1, len(acc)) if acc[k] >= target), len(acc) - 1)
        (x0, y0), (x1, y1) = pts[k - 1], pts[k]
        r = (target - acc[k - 1]) / ((acc[k] - acc[k - 1]) or 1)
        tx, ty = x1 - x0, y1 - y0
        m = math.hypot(tx, ty)
        return x0 + tx * r, y0 + ty * r, tx / m, ty / m

    w0, w1 = p["lane_w"]
    out = []
    for a, b in p["dashes"]:
        side1, side2 = [], []
        for i in range(25):
            s = a + (b - a) * i / 24
            x, y, tx, ty = at(s)
            h = (w0 + (w1 - w0) * s) / 2
            side1.append((x - ty * h, y + tx * h))
            side2.append((x + ty * h, y - tx * h))
        out.append(poly(side1 + side2[::-1]))
    return " ".join(out)


# ------------------------------------------------------------------ export

def wordmark():
    with open(os.path.join(HERE, "wordmark.json")) as fh:
        return json.load(fh)


def variant(p):
    """The primitive shapes of one variant. export.swift combines them (stroke, union, subtract)."""
    mono_gap = p["hub_gap_r"] or p["cap_r"] + 2.0          # mono: the hub becomes a ring
    return {
        "ring": circle(p["ring_r"]), "ringWidth": p["ring_w"],
        "wheel": circle(p["hub_r"]) + " " + spokes(p),       # hub ring + spokes (they overlap; union)
        "cap": circle(p["cap_r"]),
        "hubGap": circle(p["hub_gap_r"]) if p["hub_gap_r"] else "",
        "monoHubGap": circle(mono_gap),
        "swoosh": swoosh(p), "swooshCut": swoosh_cut(p), "underSwoosh": under_swoosh(p),
        "lane": lane(p),
        "gap": p["gap"],
    }


def geometry():
    w = wordmark()
    D = 92.0
    scale = LOCKUP["cap_height"] * D / w["capHeight"]
    x0 = 96 + LOCKUP["gap"] * D - w["inkLeft"] * scale     # the ring's right edge is at x = 96
    baseline = C + w["capHeight"] * scale / 2               # cap height centred on the wheel
    ys = [float(v) for v in re.findall(r"-?[\d.]+", w["d"])][1::2]
    return {
        "generatedBy": "mark.py; do not edit",
        "colors": {"charcoal": CHARCOAL, "copper": COPPER, "ivory": IVORY, "stone": STONE},
        "full": variant(FULL), "small": variant(SMALL),
        "iconScale": ICON_SCALE,
        "wordmark": {"d": w["d"], "x": w["inkLeft"], "y": min(ys),
                     "width": w["width"] - w["inkLeft"], "height": max(ys) - min(ys)},
        "lockup": {"textX": x0, "baseline": baseline, "textScale": scale,
                   "viewBox": [4, 4, x0 + w["width"] * scale - 4, 92]},
    }


if __name__ == "__main__":
    path = os.path.join(HERE, "geometry.json")
    with open(path, "w") as fh:
        json.dump(geometry(), fh, indent=1)
    print(f"wrote {os.path.relpath(path)}")
