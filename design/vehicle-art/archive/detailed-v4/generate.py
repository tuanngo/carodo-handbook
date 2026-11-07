"""Editable vector artwork source. Run with Python 3; no third-party dependencies."""

from pathlib import Path
from math import cos, sin, pi
from html import escape
import re

ROOT = Path(__file__).parent
PAINT = '#8195a6'


def arc_q(cx, cy, r, a1_deg, a2_deg, steps=4):
    """Approximate a circular arc with exact-tangent quadratic Bézier segments."""
    a1 = a1_deg * pi / 180.0
    a2 = a2_deg * pi / 180.0
    da = (a2 - a1) / steps
    half = da / 2.0
    rc = r / cos(half)
    parts = []
    for i in range(steps):
        mid = a1 + (i + 0.5) * da
        end = a1 + (i + 1) * da
        qx, qy = cx + rc * cos(mid), cy + rc * sin(mid)
        ex, ey = cx + r * cos(end), cy + r * sin(end)
        parts.append(f'Q{qx:.2f} {qy:.2f} {ex:.2f} {ey:.2f}')
    return ' '.join(parts)


def car_body_under(rear, front, r_arch=21.2, y_sill=82.5):
    """Trace the lower car body from front wheel arch back to rear wheel arch."""
    f_start_x = front + r_arch * cos(3 * pi / 180.0)
    f_start_y = 82.0 + r_arch * sin(3 * pi / 180.0)
    r_start_x = rear + r_arch * cos(3 * pi / 180.0)
    r_start_y = 82.0 + r_arch * sin(3 * pi / 180.0)
    return (
        f'L{f_start_x:.2f} {f_start_y:.2f} '
        f'{arc_q(front, 82.0, r_arch, 3, -183, 4)} '
        f'L{rear + r_arch:.2f} {y_sill:.2f} '
        f'L{r_start_x:.2f} {r_start_y:.2f} '
        f'{arc_q(rear, 82.0, r_arch, 3, -183, 4)}'
    )


def arch_flare(cx, cy=82.0, r=24.2):
    """Subtle sheetmetal fender flare arc above a wheel arch."""
    sx = cx + r * cos(-162 * pi / 180.0)
    sy = cy + r * sin(-162 * pi / 180.0)
    return f'M{sx:.2f} {sy:.2f} {arc_q(cx, cy, r, -162, -18, 3)}'


def arch_cladding(cx, cy=82.0, r=22.0):
    """Dark rugged wheel-arch cladding for SUV and Pickup."""
    sx = cx + r * cos(-176 * pi / 180.0)
    sy = cy + r * sin(-176 * pi / 180.0)
    return f'M{sx:.2f} {sy:.2f} {arc_q(cx, cy, r, -176, -4, 4)}'


# All vehicles face right. Bodywork is independently paintable; glass, rubber,
# metal and lights never inherit the selected body colour.
CARS = {
    'sedan': {
        'title': 'Sedan',
        'rear': 56,
        'front': 187,
        'body': (
            'M15 70 Q14 58 20 52 L34 49 '
            'Q60 34 83 27 Q103 23 127 24 Q146 25 166 41 '
            'L174 47 Q199 49 216 54 Q224 56 225 63 L225 73 Q224 80 214 81 '
            'L209 82 ' + car_body_under(56, 187, 21.2, 82.5) + ' '
            'L25 81 Q15 80 15 70 Z'
        ),
        'dlo': 'M48 46 Q68 34 85 29 Q103 25 125 26 Q143 27 161 41 L168 47 L116 47.5 L48 46 Z',
        'glass': (
            'M51 45.5 Q69 35 85 30 Q100 27 113 27 L112 46.5 L51 45.5 Z '
            'M117 27 L125 27 Q142 28 159 41 L165 46 L116 46.5 Z'
        ),
        'seams': 'M114.5 27 L113.5 78 M68 46 L66 62 M167 47 L169 61',
        'crease': 'M20 54 Q94 51 168 52 Q196 52 214 57',
        'mirror': (159, 44.5),
        'headlamp': 'M207 55 L223 58 L224 63 L210 62 Q206 60 207 55 Z',
        'taillamp': 'M15.5 53 L26 54 Q27 58 24 60 L14.8 60 Z',
        'intake': 'M212 72 L224 72 L222 77 L210 77 Z',
        'handles': [(82, 52), (124, 52)],
        'rugged': False,
        'rails': None,
    },
    'hatchback': {
        'title': 'Hatchback',
        'rear': 55,
        'front': 181,
        'body': (
            'M22 71 Q21 59 25 49 L36 30 Q39 25 48 25 '
            'Q86 23 121 25 Q140 26 158 40 L166 47 '
            'Q191 49 208 54 Q218 57 219 64 L219 73 Q218 80 209 81 '
            'L203 82 ' + car_body_under(55, 181, 21.2, 82.5) + ' '
            'L30 81 Q22 80 22 71 Z'
        ),
        'dlo': 'M42 45 L48 31 Q50 28 58 28 L119 28 Q136 29 152 40 L160 47 L46 47 Q42 47 42 45 Z',
        'glass': (
            'M44 45 L49 32 Q51 29 58 29 L101 29 L100 46 L44 45 Z '
            'M105 29 L119 29 Q135 30 150 40 L157 46 L104 46 Z'
        ),
        'seams': 'M102.5 29 L101.5 78 M58 47 L56 61 M160 47 L162 61',
        'crease': 'M26 53 Q92 50 160 52 Q187 52 205 57',
        'mirror': (152, 44.5),
        'headlamp': 'M200 55 L217 58 L218 63 L203 62 Q199 60 200 55 Z',
        'taillamp': 'M23.5 50 L33 51 Q34 55 31 57 L22 56 Z',
        'intake': 'M206 72 L218 72 L216 77 L204 77 Z',
        'handles': [(75, 52), (114, 52)],
        'rugged': False,
        'rails': None,
    },
    'suv': {
        'title': 'SUV',
        'rear': 54,
        'front': 190,
        'body': (
            'M14 72 Q13 57 17 44 L26 23 Q29 17 39 16 '
            'Q88 14 134 16 Q150 17 163 31 L172 41 '
            'Q200 43 217 47 Q227 49 228 58 L228 73 Q228 81 218 82 '
            'L213 83 ' + car_body_under(54, 190, 21.8, 82.5) + ' '
            'L24 82 Q14 81 14 72 Z'
        ),
        'dlo': 'M29 40 L37 22 Q39 19 47 19 L133 19 Q146 20 157 31 L165 41 L34 41 Q29 41 29 40 Z',
        'glass': (
            'M31 40 L38 23 Q40 20 47 20 L72 20 L72 40 Z '
            'M76 20 L114 20 L114 40 L76 40 Z '
            'M118 20 L133 20 Q145 21 155 31 L162 40 L118 40 Z'
        ),
        'seams': 'M74 41 L74 62 M116 20 L116 78 M165 42 L167 61',
        'crease': 'M19 48 Q96 46 170 47 Q200 47 218 51',
        'mirror': (158, 39),
        'headlamp': 'M210 49 L226 51 L227 57 L213 56 Q209 54 210 49 Z',
        'taillamp': 'M15.5 46 L26 47 Q27 51 24 54 L14.5 54 Z',
        'intake': 'M215 69 L227 69 L226 75 L213 75 Z',
        'handles': [(84, 47), (126, 47)],
        'rugged': True,
        'rails': 'M46 12.5 Q90 11.5 132 12.5',
    },
    'mpv': {
        'title': 'MPV',
        'rear': 54,
        'front': 190,
        'body': (
            'M15 73 Q14 57 17 43 L24 25 Q27 19 38 19 '
            'Q88 17 136 19 Q153 20 168 34 L181 46 '
            'Q206 49 219 55 Q227 59 227 68 L227 74 Q227 81 217 82 '
            'L212 83 ' + car_body_under(54, 190, 21.2, 82.5) + ' '
            'L25 82 Q15 81 15 73 Z'
        ),
        'dlo': 'M26 44 L32 26 Q34 22 42 22 L135 22 Q150 23 164 35 L174 45 L30 45 Q26 45 26 44 Z',
        'glass': (
            'M28 44 L33 27 Q35 23 42 23 L74 23 L74 44 Z '
            'M78 23 L120 23 L120 44 L78 44 Z '
            'M124 23 L135 23 Q149 24 162 35 L171 44 L124 44 Z'
        ),
        'seams': 'M76 45 L76 66 M122 23 L122 78 M174 46 L176 62 M40 54 L74 54',
        'crease': 'M20 51 Q98 49 174 51 Q202 52 219 57',
        'mirror': (166, 43),
        'headlamp': 'M208 54 L225 57 L226 62 L211 61 Q207 59 208 54 Z',
        'taillamp': 'M16 48 L26 49 Q27 53 24 55 L15 55 Z',
        'intake': 'M214 72 L226 72 L225 77 L212 77 Z',
        'handles': [(94, 51), (132, 51)],
        'rugged': False,
        'rails': None,
    },
    'pickup': {
        'title': 'Pickup',
        'rear': 54,
        'front': 192,
        'body': (
            'M10 72 L11 46 Q11 41 17 41 L78 41 Q81 41 82 37 '
            'L87 22 Q90 16 100 16 L141 16 Q156 16 166 29 L175 41 '
            'Q203 43 220 46 Q229 48 230 57 L230 74 Q230 82 220 83 '
            'L215 84 ' + car_body_under(54, 192, 21.8, 82.5) + ' '
            'L20 83 Q10 82 10 72 Z'
        ),
        'dlo': 'M88 39 L93 23 Q95 19 101 19 L140 19 Q152 20 161 30 L168 40 L90 40 Q88 40 88 39 Z',
        'glass': (
            'M90 39 L94 24 Q96 20 101 20 L121 20 L121 39 Z '
            'M125 20 L140 20 Q151 21 159 30 L165 39 L125 39 Z'
        ),
        'seams': 'M80 41 L80 79 M123 20 L123 78 M168 42 L170 61',
        'crease': 'M15 48 L76 48 M84 48 L172 48 Q202 48 220 51',
        'mirror': (161, 38),
        'headlamp': 'M214 48 L229 50 L229 58 L216 57 Q213 54 214 48 Z',
        'taillamp': 'M10.5 47 L16.5 47 L16.5 57 L10.5 57 Z',
        'intake': 'M218 69 L229 69 L228 75 L216 75 Z',
        'handles': [(100, 47), (134, 47)],
        'rugged': True,
        'rails': None,
    },
    'coupe': {
        'title': 'Coupé',
        'rear': 55,
        'front': 188,
        'body': (
            'M14 71 Q13 59 20 53 L35 50 '
            'Q66 34 90 27.5 Q110 23 131 26 Q148 28 163 42 '
            'L171 48 Q198 50 216 55 Q226 58 227 65 L227 74 Q226 81 216 82 '
            'L210 83 ' + car_body_under(55, 188, 21.2, 82.5) + ' '
            'L24 81 Q14 80 14 71 Z'
        ),
        'dlo': 'M54 47.5 Q77 34 96 29.5 Q113 26 130 28.5 Q145 30.5 158 42 L165 48 L54 47.5 Z',
        'glass': (
            'M58 46.5 Q78 35 96 30.5 Q105 28.5 112 28.5 L110 47 Z '
            'M116 28.5 Q123 28.5 130 29.5 Q144 31.5 156 42 L162 47 L114 47 Z'
        ),
        'seams': 'M113 48 L111 78 M164 49 L166 62',
        'crease': 'M18 55 Q62 51 106 53 Q162 54 214 59',
        'mirror': (155, 45.5),
        'headlamp': 'M207 56 L225 59 L226 64 L210 63 Q206 61 207 56 Z',
        'taillamp': 'M14.5 55 L26 55 Q28 58 24 60 L14 60 Z',
        'intake': 'M212 73 L226 73 L224 77 L210 77 Z',
        'handles': [(100, 53.5)],
        'rugged': False,
        'rails': None,
    },
}

BIKES = ('scooter', 'underbone', 'manual', 'sport', 'bicycle')


def rounded(d, radius=3):
    """Round straight junctions with tangent quadratic curves; preserve authored curves."""
    tokens = re.findall(r'[MLQZ]|-?\d+(?:\.\d+)?', d)
    subpaths, commands, i = [], [], 0
    while i < len(tokens):
        op = tokens[i]
        count = {'M': 2, 'L': 2, 'Q': 4, 'Z': 0}[op]
        args = [float(n) for n in tokens[i+1:i+1+count]]
        if op == 'M' and commands:
            subpaths.append(commands)
            commands = []
        commands.append((op, args))
        i += count+1
    if commands:
        subpaths.append(commands)
    output = []

    def fmt(point):
        return ' '.join(f'{v:.3f}'.rstrip('0').rstrip('.') if v else '0' for v in point)

    for commands in subpaths:
        closed = commands[-1][0] == 'Z'
        nodes = commands[:-1] if closed else commands
        corners = {}
        for j, (op, args) in enumerate(nodes):
            if op not in ('M', 'L') or (j == 0 and not closed) or (j == len(nodes)-1 and not closed):
                continue
            nxt = nodes[(j+1) % len(nodes)]
            if nxt[0] not in ('L', 'M'):
                continue
            previous = nodes[j-1][1][-2:]
            vertex = args[-2:]
            following = nxt[1][-2:]
            a = sum((previous[k]-vertex[k])**2 for k in (0, 1))**.5
            b = sum((following[k]-vertex[k])**2 for k in (0, 1))**.5
            if not a or not b:
                continue
            distance = min(radius, a*.35, b*.35)
            before = [vertex[k]+(previous[k]-vertex[k])*distance/a for k in (0, 1)]
            after = [vertex[k]+(following[k]-vertex[k])*distance/b for k in (0, 1)]
            corners[j] = (before, vertex, after)
        output.append('M'+fmt(corners[0][2] if 0 in corners else nodes[0][1]))
        for j, (op, args) in enumerate(nodes[1:], 1):
            if j in corners:
                before, vertex, after = corners[j]
                output.extend(['L'+fmt(before), 'Q'+fmt(vertex+after)])
            else:
                output.append(op+fmt(args))
        if closed:
            if 0 in corners:
                before, vertex, after = corners[0]
                output.extend(['L'+fmt(before), 'Q'+fmt(vertex+after)])
            output.append('Z')
    return ' '.join(output)


def path(d, fill='none', stroke=None, width=1, extra='', round_r=None):
    r = (3 if fill != 'none' else 2) if round_r is None else round_r
    d = rounded(d, r) if r > 0 else d
    return f'<path d="{d}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"' if stroke else '') + f' {extra}/>'


def car_wheel(x, y, r=19, compact=False):
    s = f'<circle cx="{x}" cy="{y}" r="{r+2.2:.1f}" fill="#1b2228" fill-opacity=".88"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r}" fill="#23282c" stroke="#eef1f3" stroke-opacity=".18" stroke-width=".8"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r*.68:.2f}" fill="#323b42" stroke="#ced7dc" stroke-width="1.3"/>'
    if compact:
        s += f'<circle cx="{x}" cy="{y}" r="{r*.42:.2f}" fill="#b8c4cb"/>'
        return s + f'<circle cx="{x}" cy="{y}" r="{r*.18:.2f}" fill="#323b42"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r*.46:.2f}" fill="none" stroke="#7c8992" stroke-opacity=".55" stroke-width="2"/>'
    for i in range(5):
        a = -pi / 2 + i * 2 * pi / 5
        a1, a2 = a - 0.14, a + 0.14
        s += path(
            f'M{x+cos(a1)*3.2:.2f} {y+sin(a1)*3.2:.2f} L{x+cos(a1)*r*.63:.2f} {y+sin(a1)*r*.63:.2f} '
            f'L{x+cos(a2)*r*.63:.2f} {y+sin(a2)*r*.63:.2f} L{x+cos(a2)*3.2:.2f} {y+sin(a2)*3.2:.2f} Z',
            fill='#d3dce0', round_r=0.5)
    s += f'<circle cx="{x}" cy="{y}" r="3.4" fill="#d3dce0"/>'
    return s + f'<circle cx="{x}" cy="{y}" r="1.6" fill="#323b42"/>'


def moto_wheel(x, y, r=18.5, compact=False):
    s = f'<circle cx="{x}" cy="{y}" r="{r}" fill="#23282c" stroke="#eef1f3" stroke-opacity=".18" stroke-width=".8"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r*.72:.2f}" fill="#2f383f" stroke="#c8d2d8" stroke-width="1.2"/>'
    if compact:
        s += f'<circle cx="{x}" cy="{y}" r="{r*.34:.2f}" fill="#b8c4cb"/>'
        return s + f'<circle cx="{x}" cy="{y}" r="{r*.16:.2f}" fill="#2f383f"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r*.46:.2f}" fill="none" stroke="#9aa6ae" stroke-opacity=".65" stroke-width="1.8"/>'
    for i in range(6):
        a = -pi / 2 + i * pi / 3
        s += path(
            f'M{x+cos(a)*2.8:.2f} {y+sin(a)*2.8:.2f} L{x+cos(a+0.12)*r*.67:.2f} {y+sin(a+0.12)*r*.67:.2f}',
            stroke='#ced7dc', width=1.6, round_r=0)
    s += f'<circle cx="{x}" cy="{y}" r="3.1" fill="#d3dce0"/>'
    return s + f'<circle cx="{x}" cy="{y}" r="1.4" fill="#2f383f"/>'


def bike_wheel(x, y, r=20.0, compact=False):
    s = f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#23282c" stroke-width="2.6"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r-1.9:.2f}" fill="none" stroke="#627079" stroke-width="1.1"/>'
    if not compact:
        s += f'<circle cx="{x}" cy="{y}" r="4.8" fill="none" stroke="#94a0a8" stroke-opacity=".75" stroke-width="1"/>'
        for i in range(6):
            a = i * pi / 6
            dx, dy = cos(a) * (r - 2.5), sin(a) * (r - 2.5)
            s += path(f'M{x-dx:.2f} {y-dy:.2f} L{x+dx:.2f} {y+dy:.2f}', stroke='#95a2aa', width=0.65, extra='stroke-opacity=".55"', round_r=0)
    return s + f'<circle cx="{x}" cy="{y}" r="2.4" fill="#323b42" stroke="#d3dce0" stroke-width=".8"/>'


def mudguard(cx, cy, r=20.2, a1=-142, a2=-32, thickness=3.6):
    """Curved front fender hugging the front wheel."""
    outer = arc_q(cx, cy, r + thickness, a1, a2, 3)
    inner = arc_q(cx, cy, r, a2, a1, 3)
    sx = cx + (r + thickness) * cos(a1 * pi / 180.0)
    sy = cy + (r + thickness) * sin(a1 * pi / 180.0)
    ix = cx + r * cos(a2 * pi / 180.0)
    iy = cy + r * sin(a2 * pi / 180.0)
    return f'M{sx:.2f} {sy:.2f} {outer} L{ix:.2f} {iy:.2f} {inner} Z'


def artwork(key, compact=False):
    defs = f'''<defs>
      <linearGradient id="{key}-shade" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="white" stop-opacity=".24"/><stop offset=".48" stop-color="white" stop-opacity=".06"/><stop offset="1" stop-color="black" stop-opacity=".14"/></linearGradient>
      <linearGradient id="{key}-glass" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#53616c"/><stop offset="1" stop-color="#26333e"/></linearGradient>
    </defs>'''
    if key in CARS:
        c = CARS[key]
        title, rear, front = c['title'], c['rear'], c['front']
        s = car_wheel(rear, 82, 19, compact) + car_wheel(front, 82, 19, compact)
        if c['rails']:
            s += path('M50 12.5 L50 16 M126 12.5 L126 16', stroke='#38424a', width=1.8, round_r=0)
            s += path(c['rails'], stroke='#38424a', width=1.8, round_r=0)
        if key == 'pickup':
            s += path('M14 41 L78 41', stroke='#252f37', width=2.2, round_r=0)
        s += path(c['body'], 'currentColor', '#263039', .75, 'stroke-opacity=".45"')
        s += path(c['body'], f'url(#{key}-shade)')
        s += path(c['dlo'], '#1e272f', '#d6e1e6', .6, 'stroke-opacity=".48"', round_r=2)
        s += path(c['glass'], f'url(#{key}-glass)', round_r=1.5)
        if not compact:
            s += path(c['seams'], stroke='#1f2c36', width=.7, extra='opacity=".22"', round_r=0)
            s += path(c['crease'], stroke='white', width=1.1, extra='opacity=".22"', round_r=0)
            s += path(arch_flare(rear) + ' ' + arch_flare(front), stroke='white', width=0.9, extra='opacity=".18"', round_r=0)
            s += path(
                f'M{rear+25} 73.5 L{front-25} 73.5 L{front-29} 77.5 L{rear+29} 77.5 Z',
                fill='#1c262e', extra='fill-opacity=".13"', round_r=1.5)
            for hx, hy in c['handles']:
                s += path(f'M{hx} {hy} L{hx+7} {hy}', stroke='#1f2c36', width=1.5, extra='opacity=".40"', round_r=0)
        if c['rugged']:
            s += path(arch_cladding(rear) + ' ' + arch_cladding(front), stroke='#232c33', width=2.4, extra='opacity=".80"', round_r=0)
            s += path(f'M{rear+21} 82 L{front-21} 82', stroke='#232c33', width=2.8, extra='opacity=".80"', round_r=0)
        else:
            s += path(f'M{rear+23} 80.5 L{front-23} 80.5', stroke='#202c34', width=1.8, extra='opacity=".45"', round_r=0)
        mx, my = c['mirror']
        s += path(f'M{mx} {my} L{mx+8} {my} Q{mx+11} {my+1} {mx+10} {my+5} L{mx+1} {my+5} Z', 'currentColor', '#2a343d', .75, round_r=1.5)
        s += path(c['headlamp'], '#eef4f6', '#3a4752', .6, round_r=1)
        s += path(c['taillamp'], '#b54038', '#6e231e', .5, round_r=1)
        s += path(c['intake'], '#222c34', round_r=1)
        return title, defs + s

    if key == 'scooter':
        title = 'Scooter'
        rear, front, wy, wr = 68, 170, 84.0, 17.0
        s = moto_wheel(rear, wy, wr, compact) + moto_wheel(front, wy, wr, compact)
        # Rear mudflap, shock, CVT drivetrain case & sculpted muffler with heat shield.
        s += path('M46 53 L40 65', stroke='#2b343c', width=2.2, round_r=0)
        s += path('M68 79 L78 58', stroke='#7c8890', width=2.4, round_r=0)
        s += path('M58 81 L96 77 Q102 77 102 83 L96 88 L60 87 Z', '#323c44', '#1d252c', .8, round_r=2)
        s += path('M52 75 L88 76 L90 83 L54 83 Z', '#2b343c', '#1b2228', .8, round_r=2)
        s += path('M57 76.5 L84 77.2 L85 81.2 L58 81 Z', '#a7b2b9', round_r=1.2)
        # Telescopic front fork & sculpted front fender.
        s += path(f'M149 41 L{front} {wy}', stroke='#9aa6ae', width=3.6, round_r=0)
        s += path(f'M146 43 L{front-3} {wy-1}', stroke='#3f4952', width=1.8, round_r=0)
        fender = mudguard(front, wy, wr + 1.0, -145, -28, 4.2)
        s += path(fender, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=0)
        s += path(fender, f'url(#{key}-shade)', round_r=0)
        # Dark inner legshield & floorboard mat.
        s += path('M104 72 L138 72 Q142 72 141 65 L137 36 L143 29 L147 40 L145 70 Q144 77 136 77 L104 77 Z', '#263038', round_r=2)
        # Main scooter bodywork: almond wasp-tail rear + low floorboard + proud S-curve front apron.
        body = (
            'M44 58 Q43 45 58 42 Q78 39 102 44 Q109 46 110 55 '
            'L111 68 Q112 73 118 73 L134 73 Q140 73 140 65 '
            'L137 40 Q136 30 144 26 L154 27 '
            'Q165 39 166 53 Q166 62 157 68 Q149 74 146 80 '
            'Q143 83 134 83 L105 83 Q96 83 92 74 Q88 66 76 66 '
            'L52 65 Q44 64 44 58 Z'
        )
        s += path(body, 'currentColor', '#263039', .8, 'stroke-opacity=".55"')
        s += path(body, f'url(#{key}-shade)')
        if not compact:
            s += path('M54 51 Q78 49 95 60 M146 35 Q156 47 154 62', stroke='#1f2d36', width=.8, extra='opacity=".24"', round_r=0)
            s += path('M52 42 L40 41 Q38 42 41 44 L48 45', stroke='#8e9aa2', width=1.8, round_r=0)
        # Plush contoured two-up saddle.
        s += path('M51 43 Q51 35 62 35 L90 36 Q101 37 107 43 L108 46 L52 45 Z', '#242d34', '#141c22', .8, round_r=2)
        # Integrated handlebar cowling (headset) seated on the steering neck, headlamp & mirror.
        s += path('M143 27 L146 21 L136 22', stroke='#3d474f', width=2.4, round_r=1)
        if not compact:
            s += path('M146 20 L143 10', stroke='#48535a', width=1.6, round_r=0)
            s += '<ellipse cx="142" cy="8.5" rx="4.2" ry="2.2" fill="#48535a"/>'
        headset = 'M140 26 Q143 18 155 18 L161 21 L159 27 L142 27 Z'
        s += path(headset, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=1.5)
        s += path('M156 19 L161 21 L159 26 L155 26 Z', '#eef4f6', '#4a5760', .6, round_r=1)
        s += path('M44 50 L50 51 L48 56 L44 55 Z', '#b54038', round_r=1)
        return title, defs + s

    if key == 'underbone':
        title = 'Underbone'
        rear, front, wy, wr = 64, 174, 82.0, 19.0
        s = moto_wheel(rear, wy, wr, compact) + moto_wheel(front, wy, wr, compact)
        # Rear mudflap, horizontal swingarm/chain case, shock & horizontal engine.
        s += path('M46 48 L38 61', stroke='#2b343c', width=2.2, round_r=0)
        s += path('M62 80 L98 78 L98 83 L62 84 Z', '#434e56', '#232b32', .7, round_r=1.5)
        s += path('M68 79 L80 54', stroke='#7c8890', width=2.4, round_r=0)
        s += path('M94 58 L134 56 L146 64 L138 79 L96 79 Z', '#2e3840', '#1b2329', .9, round_r=2)
        if not compact:
            s += path('M127 62 L140 64 M126 67 L139 69', stroke='#95a1a9', width=1.3, round_r=0)
            s += '<circle cx="108" cy="69" r="5.2" fill="#59656e" stroke="#222a30" stroke-width=".8"/>'
        # Exhaust header under engine + gently upswept muffler above the rear axle.
        s += path('M130 79 L94 80', stroke='#59656e', width=2.6, round_r=0)
        s += path('M54 73 L95 77 L95 82 L55 79 Z', '#a7b2b9', '#39434b', .9, round_r=1.8)
        # Front telescopic fork & painted fender.
        s += path(f'M148 35 L{front} {wy}', stroke='#a5b0b7', width=3.6, round_r=0)
        s += path(f'M145 37 L{front-3} {wy-1}', stroke='#3f4952', width=1.8, round_r=0)
        fender = mudguard(front, wy, wr + 1.0, -142, -32, 3.8)
        s += path(fender, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=0)
        s += path(fender, f'url(#{key}-shade)', round_r=0)
        # Dark inner legshield panel & under-seat frame cover.
        s += path('M72 52 L117 59 L136 36 L142 30 L146 42 L124 66 L94 62 Z', '#242e36', round_r=2)
        # Sculpted U-bone fairing with athletic front legshield & fuller rear body cowling.
        body = (
            'M42 45 Q48 40 65 42 L102 45 Q110 46 115 54 Q120 60 125 54 '
            'L140 35 Q146 28 154 28 L163 33 Q167 40 159 50 '
            'L147 65 Q141 71 131 70 L116 64 L96 58 '
            'Q82 57 66 56 L46 52 Q41 50 42 45 Z'
        )
        s += path(body, 'currentColor', '#263039', .8, 'stroke-opacity=".55"')
        s += path(body, f'url(#{key}-shade)')
        if not compact:
            s += path('M149 35 Q154 46 141 60 M52 46 L94 51', stroke='#1f2d36', width=.8, extra='opacity=".24"', round_r=0)
            s += path('M50 41 L40 40 Q38 41 41 43 L47 44', stroke='#8e9aa2', width=1.8, round_r=0)
        # Contoured seat, handlebar cowl & headlight.
        s += path('M48 42 Q50 35 61 35 L92 38 Q101 39 105 45 L49 44 Z', '#242d34', '#141c22', .8, round_r=2)
        s += path('M145 28 L148 21 L138 22', stroke='#3d474f', width=2.4, round_r=1)
        if not compact:
            s += path('M148 20 L145 10', stroke='#48535a', width=1.6, round_r=0)
            s += '<ellipse cx="144" cy="8.5" rx="4.2" ry="2.2" fill="#48535a"/>'
        headset = 'M142 27 Q146 19 157 20 L163 24 L160 29 L144 29 Z'
        s += path(headset, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=1.5)
        s += path('M158 21 L163 24 L160 28 L156 28 Z', '#eef4f6', '#4a5760', .6, round_r=1)
        s += path('M42 45 L47 46 L46 50 L42 49 Z', '#b54038', round_r=1)
        return title, defs + s

    if key == 'manual':
        title = 'Naked bike'
        rear, front, wy, wr = 64, 174, 82.0, 19.0
        s = moto_wheel(rear, wy, wr, compact) + moto_wheel(front, wy, wr, compact)
        # Tail tidy, subframe cover, horizontal swingarm, monoshock & muscular roadster engine.
        s += path('M47 42 L38 54', stroke='#2b343c', width=2.0, round_r=0)
        s += path('M66 44 L98 46 L100 62 L82 58 Z', '#232c33', round_r=2)
        s += path(f'M{rear} {wy} L98 79', stroke='#3d474f', width=4.4, round_r=0)
        s += path('M82 78 L93 55', stroke='#b87b52', width=2.6, round_r=0)
        s += path('M94 47 L138 45 L146 61 L135 79 L98 79 L91 61 Z', '#283138', '#182026', .9, round_r=2.5)
        if not compact:
            s += path('M94 48 L120 41 L144 36 M102 62 L120 41', stroke='#6c7982', width=2.2, round_r=1)
            s += '<circle cx="113" cy="68" r="6" fill="#59656e" stroke="#222a30" stroke-width=".9"/>'
            s += path('M124 53 L140 54 M125 58 L141 59', stroke='#8d99a1', width=1.3, round_r=0)
        # Exhaust collector under engine + sleek megaphone muffler above the swingarm.
        s += path('M128 79 L92 79', stroke='#59656e', width=2.8, round_r=0)
        s += path('M62 72 L94 76 L94 81 L63 78 Z', '#a7b2b9', '#39434b', .9, round_r=1.8)
        s += path('M58 72 L63 72 L63 78 L58 77 Z', '#283138', round_r=1)
        # USD front forks & painted mudguard.
        s += path('M144 29 L166 66', stroke='#b4bec5', width=3.8, round_r=0)
        s += path(f'M162 60 L{front} {wy}', stroke='#3a444c', width=2.6, round_r=0)
        fender = mudguard(front, wy, wr + 1.0, -140, -34, 3.8)
        s += path(fender, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=0)
        s += path(fender, f'url(#{key}-shade)', round_r=0)
        # Sculpted roadster spine: upswept tail cowl + muscular flat-top tank + sharp radiator shroud.
        body = (
            'M43 39 Q47 35 57 37 L80 43 L98 45 '
            'Q103 31 116 28 L134 27 Q143 28 148 36 '
            'L154 43 L141 54 L131 53 L124 46 L96 48 '
            'L86 52 L66 47 L47 43 Q43 42 43 39 Z'
        )
        s += path(body, 'currentColor', '#263039', .8, 'stroke-opacity=".55"')
        s += path(body, f'url(#{key}-shade)')
        if not compact:
            s += path('M106 38 Q122 33 142 38', stroke='white', width=1.0, extra='opacity=".22"', round_r=0)
        # Deeply contoured roadster saddle.
        s += path('M55 37 Q65 35 78 39 L88 44 Q95 46 101 44 L98 50 L76 47 L55 41 Z', '#242d34', '#141c22', .8, round_r=2)
        # Fork-mounted streetfighter headlight, wide flat bars & mirror.
        s += path('M142 29 L147 20 L138 21', stroke='#3d474f', width=2.4, round_r=1)
        if not compact:
            s += path('M147 19 L145 10', stroke='#48535a', width=1.6, round_r=0)
            s += '<ellipse cx="144" cy="8.5" rx="4.2" ry="2.2" fill="#48535a"/>'
        s += path('M146 31 L155 29 Q161 29 164 34 L162 42 Q155 43 149 38 Z', '#2b353e', '#1a2228', .7, round_r=1.5)
        s += path('M160 31 L164 34 L162 41 L159 41 Z', '#eef4f6', round_r=.8)
        s += path('M43 38 L48 39 L47 42 L43 41 Z', '#b54038', round_r=.8)
        return title, defs + s

    if key == 'sport':
        title = 'Sport bike'
        rear, front, wy, wr = 64, 174, 82.0, 19.0
        s = moto_wheel(rear, wy, wr, compact) + moto_wheel(front, wy, wr, compact)
        # Tail tidy, horizontal swingarm, subframe, dark lower belly pan & compact race muffler.
        s += path('M46 36 L38 48', stroke='#2b343c', width=1.8, round_r=0)
        s += path('M56 38 L96 45 L96 57 L74 49 Z', '#222b33', round_r=2)
        s += path(f'M{rear} {wy} L98 79', stroke='#39434b', width=4.4, round_r=0)
        s += path('M96 54 L148 54 L154 74 L138 80 L100 80 L94 66 Z', '#222b33', '#161e24', .8, round_r=2)
        s += path('M64 72 L96 76 L96 81 L65 78 Z', '#a7b2b9', '#39434b', .9, round_r=1.8)
        s += path('M60 72 L65 72 L65 78 L60 77 Z', '#283138', round_r=1)
        # USD front forks & painted aero mudguard.
        s += path('M147 34 L166 66', stroke='#b4bec5', width=3.8, round_r=0)
        s += path(f'M162 60 L{front} {wy}', stroke='#3a444c', width=2.6, round_r=0)
        fender = mudguard(front, wy, wr + 1.0, -140, -34, 3.8)
        s += path(fender, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=0)
        s += path(fender, f'url(#{key}-shade)', round_r=0)
        # Raked aerodynamic bubble windscreen.
        s += path('M142 29 L154 19 Q162 19 172 28 L175 33 L151 25 Z', f'url(#{key}-glass)', '#d6e1e6', .6, 'stroke-opacity=".50"', round_r=1.5)
        # Full supersport fairing + sculpted fuel tank + razor-sharp upswept tail.
        body = (
            'M41 32 Q46 28 57 31 L78 39 L98 43 '
            'Q102 29 116 26 L133 26 Q141 27 145 31 '
            'L152 24 Q164 25 175 33 L180 41 Q181 45 173 48 L159 52 '
            'L149 71 Q144 76 132 75 L108 73 Q101 71 98 60 '
            'L94 49 L72 44 L48 37 Q41 35 41 32 Z'
        )
        s += path(body, 'currentColor', '#263039', .8, 'stroke-opacity=".55"')
        s += path(body, f'url(#{key}-shade)')
        # Fairing shark-gill vent & solo race seat pad.
        s += path('M118 48 L142 44 L134 62 L112 58 Z', '#1e272f', round_r=2)
        if not compact:
            s += path('M105 36 Q121 31 138 35 M143 49 L156 45', stroke='#1f2d36', width=.8, extra='opacity=".26"', round_r=0)
        s += path('M73 37 L86 41 Q93 43 99 41 L97 47 L74 43 Z', '#242d34', '#141c22', .8, round_r=2)
        s += path('M167 35 L179 40 L177 44 L165 40 Z', '#eef4f6', '#4a5760', .6, round_r=1)
        s += path('M41 31 L46 32 L45 35 L41 34 Z', '#b54038', round_r=.8)
        return title, defs + s

    # bicycle
    title = 'Bicycle'
    rear, front, wy, wr = 64, 176, 80.5, 20.0
    s = bike_wheel(rear, wy, wr, compact) + bike_wheel(front, wy, wr, compact)
    # Drivetrain: chain loop & rear cassette.
    if not compact:
        s += path('M64 77.8 L112 75.2 L112 85.8 L64 83.2 Z', stroke='#64717a', width=1.0, extra='stroke-opacity=".75"', round_r=1)
    s += '<circle cx="64" cy="80.5" r="3.8" fill="#46525a" stroke="#9aa6ae" stroke-width=".8"/>'
    # Collinear seatpost (along 72° seat tube), racing saddle, stem & drop handlebars.
    s += path('M98.5 39 L93 22', stroke='#2b343c', width=2.5, round_r=0)
    s += path('M80 20 Q88 18 101 21 Q105 22 103 24 L88 24 Q81 24 80 20 Z', '#222b32', '#141c22', .7, round_r=1.5)
    s += path('M152.5 35 L149.5 23 L161 23 Q168.5 23 168.5 29.5 Q168.5 35.5 161 35.5', stroke='#2b343c', width=2.4, round_r=1.5)
    if not compact:
        s += path('M165 21 L169 24', stroke='#49545d', width=1.8, round_r=0)
        s += path('M124 60 L133 52 L136.5 55.5 L127.5 63.5 Z', '#46525a', round_r=1.2)
    # Slender, uniform-gauge road frame + aero fork (CW outer + 2 CCW cutouts).
    frame = (
        'M62 79.5 L95.5 42 L96.5 38 L100 38 L151 34.5 L154.5 34.5 L158.5 44.5 '
        'L177.5 80 L174.5 81.5 L155 45.5 L114.5 82 L109.5 82 L62 82 Z '
        'M100.8 41.4 L111.5 75.5 L152.8 42.8 L151.2 38.0 Z '
        'M66.8 78.2 L107.2 77.8 L96.8 44.8 L66.8 78.2 Z'
    )
    s += path(frame, 'currentColor', '#263039', .75, 'stroke-opacity=".55"', round_r=0.8)
    s += path(frame, f'url(#{key}-shade)', round_r=0.8)
    # Crankset spider & pedal arm over bottom bracket.
    s += '<circle cx="112" cy="80.5" r="5.5" fill="#2c353d" stroke="#9aa6ae" stroke-width="1.1"/>'
    s += path('M112 80.5 L116 89 M113 89 L119 89', stroke='#38424a', width=1.8, round_r=0)
    return title, defs + s


def svg(key, compact=False):
    title, content = artwork(key, compact)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 110" role="img" aria-labelledby="title" style="color:var(--vehicle-paint,{PAINT})">
    <title id="title">{escape(title)}</title>
    {content}
    </svg>'''


def main():
    all_keys = (*CARS, *BIKES)
    for key in all_keys:
        (ROOT / f'{key}.svg').write_text(svg(key))
        (ROOT / f'{key}-compact.svg').write_text(svg(key, True))
    # Static contact sheet: all 11 assets at card size, in light and dark contexts.
    content = '<rect width="1120" height="1220" fill="#f1ede5"/><rect x="560" width="560" height="1220" fill="#252522"/>'
    for col, fg in [(0, '#292d2e'), (560, '#f3eee5')]:
        content += f'<text x="{col+34}" y="44" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="22" font-weight="600">CARODO · Vehicle art</text>'
        content += f'<text x="{col+34}" y="70" fill="{fg}" opacity=".65" font-family="Helvetica,Arial,sans-serif" font-size="13">Refined proportions · unified greenhouse · 11 silhouettes</text>'
        for i, key in enumerate(all_keys):
            x = col + 30 + (i % 2) * 260
            y = 96 + (i // 2) * 150
            title, art = artwork(key)
            art = art.replace(f'{key}-', f'{col}-{key}-')
            if col == 560:
                art = art.replace('stroke="#263039"', 'stroke="#f3eee5"').replace('stroke-opacity=".45"', 'stroke-opacity=".25"').replace('stroke-opacity=".55"', 'stroke-opacity=".25"')
            content += f'<g transform="translate({x},{y})" color="{PAINT}">{art}<text x="120" y="130" text-anchor="middle" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="14">{title}</text></g>'
        content += f'<text x="{col+34}" y="1186" fill="{fg}" opacity=".6" font-family="Helvetica,Arial,sans-serif" font-size="12">Vector proposal v4 · side profile · no brand marks</text>'
    (ROOT / 'overview.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1220" viewBox="0 0 1120 1220">{content}</svg>')
    colors = [('White', '#e5e2dc'), ('Black', '#41474c'), ('Silver', '#b8bdc2'), ('Grey', '#8195a6'), ('Red', '#ae5450'), ('Blue', '#567fa3'), ('Green', '#648272'), ('Yellow', '#c6aa68'), ('Orange', '#be805e'), ('Brown', '#8e7262')]
    content = '<rect width="1120" height="1120" fill="#f1ede5"/><rect x="560" width="560" height="1120" fill="#252522"/>'
    for col, fg in [(0, '#292d2e'), (560, '#f3eee5')]:
        content += f'<text x="{col+24}" y="40" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="22" font-weight="600">One drawing · ten paint colours</text>'
        for i, (name, paint) in enumerate(colors):
            y = 65 + i * 99
            for j, key in enumerate(('sedan', 'scooter')):
                _, art = artwork(key)
                art = art.replace(f'{key}-', f'{col}-{i}-{key}-')
                if col == 560:
                    art = art.replace('stroke="#263039"', 'stroke="#f3eee5"').replace('stroke-opacity=".45"', 'stroke-opacity=".25"').replace('stroke-opacity=".55"', 'stroke-opacity=".25"')
                content += f'<g transform="translate({col+22+j*245},{y}) scale(.85)" color="{paint}">{art}</g>'
            content += f'<text x="{col+516}" y="{y+65}" text-anchor="end" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="11">{name}</text>'
    (ROOT / 'colors.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1120" viewBox="0 0 1120 1120">{content}</svg>')
    previews()


def previews():
    all_keys = (*CARS, *BIKES)

    def instance(key, identity, compact=False):
        return svg(key, compact).replace(f'{key}-', f'{identity}-{key}-').replace('id="title"', f'id="{identity}-title"').replace('aria-labelledby="title"', f'aria-labelledby="{identity}-title"')

    cards = []
    for key in all_keys:
        title = artwork(key)[0]
        cards.append(f'<article><h2>{title}</h2><div class="hero">{instance(key, key+"-large")}</div><footer><div class="badge">{instance(key, key+"-small", True)}</div><span>Compact · 88 px<br>Card · up to 280 px</span></footer></article>')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CARODO · Vehicle art v4</title>
    <style>
    *{box-sizing:border-box}body{margin:0;background:#f1ede5;color:#272e32;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:40px 20px}main{max-width:1080px;margin:auto}header{margin:0 0 32px}h1{font-size:28px;letter-spacing:-1px;margin:4px 0}p{color:#6e777b;margin:6px 0}.eyebrow{font-size:11px;letter-spacing:2px;font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}article{background:#fbf9f5;border:1px solid #deded7;border-radius:24px;padding:20px;overflow:hidden}h2{font-size:14px;font-weight:550;margin:0}.hero{height:158px;display:flex;align-items:center;justify-content:center;--vehicle-paint:#8195a6}.hero svg{width:100%;max-width:280px;display:block}footer{border-top:1px solid #e5e5df;padding-top:16px;display:flex;gap:16px;align-items:center;color:#768085;font-size:11px}.badge{width:108px;height:66px;border:1px solid #deded7;border-radius:16px;display:grid;place-items:center;flex-shrink:0;--vehicle-paint:#8195a6}.badge svg{width:88px;display:block}.note{margin:24px 0;font-size:12px}@media(prefers-color-scheme:dark){body{background:#222421;color:#f3eee5}article{background:#2b2e2b;border-color:#41453f}p,footer{color:#aab2ad}footer{border-color:#41453f}.badge{border-color:#51564e}}@media(max-width:420px){body{padding:24px 16px}.grid{grid-template-columns:1fr}h1{font-size:25px}}
    </style><main><header><div class="eyebrow">CARODO / VECTOR ART 04</div><h1>Familiar shapes. Softer lines.</h1><p>Eleven paintable silhouettes, with a simpler version for small screens.</p></header><div class="grid">'''+''.join(cards)+'''</div><p class="note">Artwork review only · SVG scales without raster blur · Light and dark follow your device theme.</p></main></html>'''
    (ROOT / 'preview.html').write_text(html)
    # Dimensions below are CSS pixel targets, not a claim about screenshot display scaling.
    content = '<rect width="1000" height="1180" fill="#f1ede5"/>'
    content += '<text x="40" y="48" font-family="Helvetica,Arial,sans-serif" font-size="24" fill="#283238">V4 · Mobile and web size check</text>'
    for i, key in enumerate(('sedan', 'scooter', 'manual', 'bicycle', 'suv')):
        y = 80 + i * 212
        content += f'<rect x="30" y="{y}" width="940" height="194" rx="24" fill="#fbf9f5"/>'
        for j, (width, compact, label) in enumerate(((88, True, '88 px · compact'), (144, True, '144 px · compact'), (280, False, '280 px · card'))):
            x = (64, 272, 570)[j]
            _, art = artwork(key, compact)
            art = art.replace(f'{key}-', f'size-{i}-{j}-{key}-')
            content += f'<g transform="translate({x},{y+28}) scale({width/240})" color="#8195a6">{art}</g>'
            content += f'<text x="{x}" y="{y+170}" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#68767c">{label}</text>'
    (ROOT / 'sizes.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1180" viewBox="0 0 1000 1180">{content}</svg>')


if __name__ == '__main__':
    main()
