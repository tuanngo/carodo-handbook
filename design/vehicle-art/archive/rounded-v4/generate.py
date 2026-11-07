"""Editable vector artwork source. Run with Python 3; no third-party dependencies."""

from pathlib import Path
from math import cos, sin, pi
from html import escape
import re

ROOT = Path(__file__).parent
PAINT = '#8195a6'

# All vehicles face right. Bodywork is independently paintable; glass, rubber,
# metal and lights never inherit the selected body colour.
CARS = {
    'sedan': (
        'Sedan',
        'M14 75 Q14 61 24 57 Q35 53 54 51 Q73 32 91 27 Q107 22 132 24 Q150 25 164 37 L184 51 Q207 52 219 59 Q228 64 228 75 Q228 82 218 83 L212 83 Q211 60 190 60 Q169 60 168 84 L79 84 Q78 60 57 60 Q36 60 35 83 L24 83 Q14 83 14 75 Z',
        'M65 50 L87 33 Q93 29 106 29 L116 29 L116 50 Z M122 29 L139 29 Q148 29 155 35 L174 50 L122 50 Z',
        'M119 54 L119 77 M177 55 L180 61 M82 55 L79 70', 57, 190),
    'hatchback': (
        'Hatchback',
        'M24 76 L24 57 Q25 42 31 31 Q35 24 50 24 L122 24 Q140 24 153 38 L173 52 Q200 53 211 62 Q218 68 218 77 Q218 83 209 84 L203 84 Q202 60 181 60 Q160 60 159 84 L77 84 Q76 60 55 60 Q34 60 33 83 Q24 83 24 76 Z',
        'M37 49 L40 33 Q41 30 47 30 L99 30 L99 50 Z M105 30 L127 30 Q138 30 146 37 L161 50 L105 50 Z',
        'M102 54 L102 78 M42 53 L40 62 M165 54 L167 62', 55, 181),
    'suv': (
        'SUV',
        'M13 75 L14 47 Q14 38 23 32 L31 22 Q37 16 49 16 L132 16 Q148 16 158 28 L173 44 L208 47 Q226 49 227 64 L227 76 Q227 84 216 84 L212 84 Q211 59 190 59 Q168 59 167 85 L77 85 Q76 59 54 59 Q32 59 31 83 L23 83 Q13 83 13 75 Z',
        'M26 40 L35 23 Q37 20 43 20 L70 20 L70 41 Z M76 20 L112 20 L112 41 L76 41 Z M118 20 L136 20 Q144 20 150 28 L160 41 L118 41 Z',
        'M73 45 L73 63 M115 45 L115 78 M164 46 L166 63', 54, 190),
    'mpv': (
        'MPV',
        'M15 75 L15 39 Q15 20 34 19 L126 19 Q145 19 159 33 L184 52 Q212 55 221 64 Q226 69 226 77 Q226 83 215 84 L211 84 Q210 60 189 60 Q168 60 167 84 L77 84 Q76 60 55 60 Q34 60 33 83 L25 83 Q15 83 15 75 Z',
        'M24 47 L24 32 Q24 25 33 24 L73 24 L73 48 Z M79 24 L118 24 L118 48 L79 48 Z M124 24 L131 24 Q144 24 153 35 L169 48 L124 48 Z',
        'M76 52 L76 65 M121 52 L121 78 M173 53 L176 63 M81 58 L114 58', 55, 189),
    'pickup': (
        'Pickup',
        'M10 75 L10 49 Q10 43 16 43 L81 43 L87 25 Q90 16 102 16 L139 16 Q154 16 162 29 L174 44 L212 47 Q229 49 230 65 L230 77 Q230 85 219 85 L215 85 Q214 59 192 59 Q169 59 168 85 L78 85 Q77 59 55 59 Q32 59 31 84 L20 84 Q10 84 10 75 Z',
        'M90 40 L94 23 Q95 20 100 20 L119 20 L119 40 Z M125 20 L143 20 Q149 20 154 28 L162 40 L125 40 Z',
        'M83 47 L83 78 M122 44 L122 78 M165 46 L168 61 M15 49 L76 49', 55, 192),
    'coupe': (
        'Coupé',
        'M13 76 Q13 63 28 58 L56 53 Q80 34 100 29 Q118 24 135 28 Q149 30 161 42 L177 52 Q205 53 220 62 Q230 68 229 77 Q229 83 218 84 L213 84 Q212 60 191 60 Q169 60 168 85 L78 85 Q77 60 56 60 Q34 60 33 83 L23 83 Q13 83 13 76 Z',
        'M68 51 L94 35 Q101 31 113 31 L118 31 L118 51 Z M124 31 L137 31 Q146 31 154 40 L164 51 L124 51 Z',
        'M122 55 L120 78 M168 56 L171 65', 56, 191),
}

BIKES = {
    'scooter': (
        'Scooter',
        'M39 66 Q38 52 55 47 Q74 43 93 47 Q103 48 104 59 L107 69 Q108 74 115 74 L134 74 Q146 74 146 62 L144 43 Q142 32 153 30 Q161 28 164 33 L172 55 Q174 60 165 65 Q159 69 158 77 Q157 83 146 83 L108 84 Q96 84 92 71 Q88 64 78 65 L44 70 Q39 70 39 66 Z M168 70 Q185 55 202 71 L202 75 Q185 68 169 76 Z',
        'M48 45 Q48 40 56 40 L94 40 Q103 40 105 47 L49 49 Z',
        'M156 32 L166 20 L178 20 M164 20 L160 10 L166 7',
        'M153 44 L163 64 M97 56 L101 75 L138 75',
        'M53 80 L93 80 L99 87 L55 88 Z'),
    'underbone': (
        'Underbone',
        'M37 53 L53 46 L98 48 L115 63 L145 38 L157 32 L169 35 L158 57 L136 72 L121 78 L96 68 L59 64 Z M169 70 Q185 57 203 70 L204 74 L169 75 Z',
        'M44 44 Q45 39 54 39 L91 42 Q100 42 104 48 L53 49 Z',
        'M158 34 L166 21 L178 20 M165 21 L160 11 L167 8',
        'M151 47 L127 72 M58 58 L78 76 L110 73',
        'M52 82 L102 77 L112 81 L110 87 L55 89 Z'),
    'manual': (
        'Naked bike',
        'M35 46 Q36 40 44 40 L83 44 Q94 45 103 38 Q113 27 129 30 Q145 32 151 40 L156 48 Q158 52 149 55 L135 59 Q125 61 114 56 Q105 52 94 55 Q85 58 73 55 L45 51 Q35 50 35 46 Z M168 68 Q185 57 203 69 L203 74 Q187 66 169 74 Z',
        'M43 38 L72 38 L91 43 L100 43 L95 49 L70 47 L44 43 Z',
        'M150 38 L163 22 L178 23 M166 23 L161 13 L169 11',
        'M84 54 L106 72 L132 62 L147 47 M107 39 L130 38',
        'M46 82 L95 73 L110 78 L107 85 L49 89 Z'),
    'sport': (
        'Sport bike',
        'M32 43 L39 34 L83 42 L102 39 Q110 29 126 31 L146 35 L157 25 L173 31 L183 49 L165 55 L148 79 L115 82 L99 59 L77 53 L53 49 Z M170 68 Q188 57 205 70 L203 74 Q187 66 170 74 Z',
        'M40 35 L65 36 L83 41 L101 40 L99 46 L76 46 L45 40 Z M158 24 L163 17 L172 21 L177 31 Z',
        'M155 36 L164 28 L175 29',
        'M112 44 L145 48 L130 70 L116 74 M151 53 L162 47',
        'M47 84 L91 75 L105 78 L102 86 L51 90 Z'),
}


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
        commands.append((op,args))
        i += count+1
    if commands:
        subpaths.append(commands)
    output=[]
    def fmt(point):
        return ' '.join(f'{v:.3f}'.rstrip('0').rstrip('.') if v else '0' for v in point)
    for commands in subpaths:
        closed = commands[-1][0] == 'Z'
        nodes = commands[:-1] if closed else commands
        corners = {}
        for j,(op,args) in enumerate(nodes):
            if op not in ('M','L') or (j == 0 and not closed) or (j == len(nodes)-1 and not closed):
                continue
            nxt = nodes[(j+1)%len(nodes)]
            if nxt[0] not in ('L','M'):
                continue
            previous = nodes[j-1][1][-2:]
            vertex = args[-2:]
            following = nxt[1][-2:]
            a = sum((previous[k]-vertex[k])**2 for k in (0,1))**.5
            b = sum((following[k]-vertex[k])**2 for k in (0,1))**.5
            if not a or not b:
                continue
            distance = min(radius,a*.35,b*.35)
            before = [vertex[k]+(previous[k]-vertex[k])*distance/a for k in (0,1)]
            after = [vertex[k]+(following[k]-vertex[k])*distance/b for k in (0,1)]
            corners[j]=(before,vertex,after)
        output.append('M'+fmt(corners[0][2] if 0 in corners else nodes[0][1]))
        for j,(op,args) in enumerate(nodes[1:],1):
            if j in corners:
                before,vertex,after=corners[j]
                output.extend(['L'+fmt(before),'Q'+fmt(vertex+after)])
            else:
                output.append(op+fmt(args))
        if closed:
            if 0 in corners:
                before,vertex,after=corners[0]
                output.extend(['L'+fmt(before),'Q'+fmt(vertex+after)])
            output.append('Z')
    return ' '.join(output)


def path(d, fill='none', stroke=None, width=1, extra=''):
    d = rounded(d, 3 if fill != 'none' else 2)
    return f'<path d="{d}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"' if stroke else '') + f' {extra}/>'


def wheel(x, y, r, compact=False):
    s = f'<circle cx="{x}" cy="{y}" r="{r}" fill="#272c30" stroke="#eef1f3" stroke-opacity=".18" stroke-width=".8"/>'
    s += f'<circle cx="{x}" cy="{y}" r="{r*.65}" fill="#505d65" stroke="#cdd6da" stroke-width="1.4"/>'
    if compact:
        return s + f'<circle cx="{x}" cy="{y}" r="{r*.32}" fill="#cdd6da"/>'
    for i in range(5):
        a = -pi / 2 + i * 2 * pi / 5
        s += path(f'M{x+cos(a)*3:.2f} {y+sin(a)*3:.2f} L{x+cos(a)*r*.56:.2f} {y+sin(a)*r*.56:.2f}',stroke='#d3dce0',width=2.8)
    return s + f'<circle cx="{x}" cy="{y}" r="3.4" fill="#d3dce0"/>'


def artwork(key, compact=False):
    defs = f'''<defs>
      <linearGradient id="{key}-shade" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="white" stop-opacity=".24"/><stop offset=".48" stop-color="white" stop-opacity=".06"/><stop offset="1" stop-color="black" stop-opacity=".14"/></linearGradient>
      <linearGradient id="{key}-glass" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#53616c"/><stop offset="1" stop-color="#26333e"/></linearGradient>
    </defs>'''
    if key in CARS:
        title, body, glass, seams, rear, front = CARS[key]
        s = wheel(rear,82,19,compact) + wheel(front,82,19,compact)
        s += path(body,'currentColor','#263039',.7, 'stroke-opacity=".45"')
        s += path(body,f'url(#{key}-shade)')
        s += path(glass,f'url(#{key}-glass)','#d6e1e6',.6, 'stroke-opacity=".50"')
        if not compact:
            s += path(seams,stroke='#23303a',width=.7,extra='opacity=".20"')
        s += path(f'M{rear+24} 79 L{front-24} 79',stroke='#202c34',width=2,extra='opacity=".42"')
        s += path(f'M{rear+27} 57 L{front-20} 57',stroke='white',width=1.2,extra='opacity=".20"')
        # Door handles and compact mirror. Small enough to disappear cleanly at badge size.
        if not compact:
            s += path('M130 55 L137 55',stroke='#23303a',width=1.5,extra='opacity=".38"')
        if not compact and key not in ('coupe','pickup'):
            s += path('M87 55 L94 55',stroke='#23303a',width=1.5,extra='opacity=".38"')
        s += path(f'M{front-23} 49 L{front-15} 49 Q{front-12} 50 {front-13} 54 L{front-22} 54 Z','currentColor','#303a42',.8)
        s += path(f'M{front+14} 58 L{front+29} 61 L{front+29} 65 L{front+16} 64 Z','#e5eced')
        tail = {'sedan': 16, 'hatchback': 25, 'suv': 15, 'mpv': 16, 'pickup': 11, 'coupe': 19}[key]
        s += path(f'M{tail} 59 L{tail+10} 59 L{tail+8} 64 L{tail} 64 Z','#a8453d')
        s += path(f'M{front+23} 73 L{front+32} 73',stroke='#263039',width=3)
        if key == 'suv':
            s += path('M43 12 L128 12',stroke='#3d474d',width=2)
    else:
        title,body,seat,bars,seams,exhaust = BIKES[key]
        frame = 'M58 82 L88 56 L104 79 M156 43 L186 82' if key == 'scooter' else 'M58 82 L94 56 L126 77 L58 82 M126 77 L155 43 L186 82'
        s = path(frame,stroke='#414b53',width=4)
        s += wheel(58,82,19,compact) + wheel(186,82,19,compact)
        s += path('M166 47 L186 82',stroke='#bdc5c8',width=4)
        s += path('M161 47 L181 81',stroke='#525c62',width=2)
        if key in ('manual','sport','underbone'):
            s += path('M103 56 L126 57 L136 70 L126 81 L103 78 L96 66 Z','#414b50','#222c32',1)
            if not compact:
                s += path('M105 63 L125 64 M106 69 L127 70',stroke='#9eabb2',width=1.5)
        s += path(body,'currentColor','#263039',.8, 'stroke-opacity=".55"')
        s += path(body,f'url(#{key}-shade)')
        s += path(seat,'#28323a','#131d24',.8)
        s += path(bars,stroke='#48535a',width=2.8)
        if not compact:
            s += path(seams,stroke='#293a44',width=.8,extra='opacity=".26"')
        s += path(exhaust,'#9fa9af','#434e56',1)
        s += path('M58 82 L91 79',stroke='#cbd1d4',width=2)
        if key == 'scooter':
            s += path('M160 22 Q165 19 174 21 L178 25 L176 31 L163 31 Z','currentColor','#48535a',.8)
            s += path('M174 22 L178 24 L177 29 L174 30 Z','#e8edeb','#53616a',.7)
        elif key == 'sport':
            s += path('M176 37 L181 40 L183 46 L177 44 Z','#e8edeb','#53616a',.7)
        else:
            s += path('M154 40 L169 37',stroke='#53616a',width=4)
            s += path('M163 31 L172 32 L174 36 L173 43 L166 43 Z','#53616a')
            s += path('M171 33 L174 35 L173 41 L171 42 Z','#e8edeb')
        if key != 'sport':
            s += '<ellipse cx="167" cy="9" rx="5" ry="2.5" fill="#48535a"/>'
        s += path('M40 49 L45 50',stroke='#ad4a40',width=2.5)
    return title, defs+s


def svg(key, compact=False):
    title, content = artwork(key,compact)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 110" role="img" aria-labelledby="title" style="color:var(--vehicle-paint,{PAINT})">
    <title id="title">{escape(title)}</title>
    {content}
    </svg>'''


def main():
    for key in (*CARS, *BIKES):
        (ROOT / f'{key}.svg').write_text(svg(key))
        (ROOT / f'{key}-compact.svg').write_text(svg(key,True))
    # Static contact sheet: same assets at card size, in light and dark contexts.
    content = '<rect width="1120" height="1120" fill="#f1ede5"/><rect x="560" width="560" height="1120" fill="#252522"/>'
    for col, fg in [(0,'#292d2e'),(560,'#f3eee5')]:
        content += f'<text x="{col+34}" y="44" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="22" font-weight="600">CARODO · Vehicle art</text>'
        content += f'<text x="{col+34}" y="70" fill="{fg}" opacity=".65" font-family="Helvetica,Arial,sans-serif" font-size="13">Softer curves · cleaner details · adaptive sizes</text>'
        for i,key in enumerate((*CARS,*BIKES)):
            x = col+30+(i%2)*260
            y = 100+(i//2)*160
            title, art = artwork(key)
            # Prefix gradient ids to avoid duplicate document IDs across backgrounds.
            art = art.replace(f'{key}-',f'{col}-{key}-')
            content += f'<g transform="translate({x},{y})" color="{PAINT}">{art}<text x="120" y="135" text-anchor="middle" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="15">{title}</text></g>'
        content += f'<text x="{col+34}" y="946" fill="{fg}" opacity=".6" font-family="Helvetica,Arial,sans-serif" font-size="12">Vector proposal v4 · side profile · no brand marks</text>'
    (ROOT/'overview.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1120" viewBox="0 0 1120 1120">{content}</svg>')
    colors = [('White','#edeae6'),('Black','#29292b'),('Silver','#bfc2c7'),('Grey','#6e7378'),('Red','#b2332b'),('Blue','#2e5c99'),('Green','#3d6b4d'),('Yellow','#e0b53b'),('Orange','#d6783b'),('Brown','#7a5740')]
    content = '<rect width="1120" height="1120" fill="#f1ede5"/><rect x="560" width="560" height="1120" fill="#252522"/>'
    for col,fg in [(0,'#292d2e'),(560,'#f3eee5')]:
        content += f'<text x="{col+24}" y="40" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="22" font-weight="600">One drawing · ten paint colours</text>'
        for i,(name,paint) in enumerate(colors):
            y=65+i*99
            for j,key in enumerate(('sedan','manual')):
                _,art=artwork(key)
                art=art.replace(f'{key}-',f'{col}-{i}-{key}-')
                content += f'<g transform="translate({col+22+j*245},{y}) scale(.85)" color="{paint}">{art}</g>'
            content += f'<text x="{col+516}" y="{y+65}" text-anchor="end" fill="{fg}" font-family="Helvetica,Arial,sans-serif" font-size="11">{name}</text>'
    (ROOT/'colors.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1120" viewBox="0 0 1120 1120">{content}</svg>')
    previews()


def previews():
    def instance(key, identity, compact=False):
        return svg(key,compact).replace(f'{key}-',f'{identity}-{key}-').replace('id="title"',f'id="{identity}-title"').replace('aria-labelledby="title"',f'aria-labelledby="{identity}-title"')
    cards=[]
    for key in (*CARS,*BIKES):
        title=artwork(key)[0]
        cards.append(f'<article><h2>{title}</h2><div class="hero">{instance(key,key+"-large")}</div><footer><div class="badge">{instance(key,key+"-small",True)}</div><span>Compact · 88 px<br>Card · up to 280 px</span></footer></article>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CARODO · Vehicle art v4</title>
    <style>
    *{box-sizing:border-box}body{margin:0;background:#f1ede5;color:#272e32;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:40px 20px}main{max-width:1080px;margin:auto}header{margin:0 0 32px}h1{font-size:28px;letter-spacing:-1px;margin:4px 0}p{color:#6e777b;margin:6px 0}.eyebrow{font-size:11px;letter-spacing:2px;font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}article{background:#fbf9f5;border:1px solid #deded7;border-radius:24px;padding:20px;overflow:hidden}h2{font-size:14px;font-weight:550;margin:0}.hero{height:158px;display:flex;align-items:center;justify-content:center;--vehicle-paint:#8195a6}.hero svg{width:100%;max-width:280px;display:block}footer{border-top:1px solid #e5e5df;padding-top:16px;display:flex;gap:16px;align-items:center;color:#768085;font-size:11px}.badge{width:108px;height:66px;border:1px solid #deded7;border-radius:16px;display:grid;place-items:center;flex-shrink:0;--vehicle-paint:#8195a6}.badge svg{width:88px;display:block}.note{margin:24px 0;font-size:12px}@media(prefers-color-scheme:dark){body{background:#222421;color:#f3eee5}article{background:#2b2e2b;border-color:#41453f}p,footer{color:#aab2ad}footer{border-color:#41453f}.badge{border-color:#51564e}}@media(max-width:420px){body{padding:24px 16px}.grid{grid-template-columns:1fr}h1{font-size:25px}}
    </style><main><header><div class="eyebrow">CARODO / VECTOR ART 04</div><h1>Familiar shapes. Softer lines.</h1><p>Ten paintable silhouettes, with a simpler version for small screens.</p></header><div class="grid">'''+''.join(cards)+'''</div><p class="note">Artwork review only · SVG scales without raster blur · Light and dark follow your device theme.</p></main></html>'''
    (ROOT/'preview.html').write_text(html)
    # Dimensions below are CSS pixel targets, not a claim about screenshot display scaling.
    content='<rect width="1000" height="1000" fill="#f1ede5"/>'
    content+='<text x="40" y="48" font-family="Helvetica,Arial,sans-serif" font-size="24" fill="#283238">V4 · Mobile and web size check</text>'
    for i,key in enumerate(('sedan','manual','scooter','suv')):
        y=88+i*218
        content+=f'<rect x="30" y="{y}" width="940" height="200" rx="24" fill="#fbf9f5"/>'
        for j,(width,compact,label) in enumerate(((88,True,'88 px · compact'),(144,True,'144 px · compact'),(280,False,'280 px · card'))):
            x=(64,272,570)[j]
            _,art=artwork(key,compact)
            art=art.replace(f'{key}-',f'size-{i}-{j}-{key}-')
            content+=f'<g transform="translate({x},{y+32}) scale({width/240})" color="#8195a6">{art}</g>'
            content+=f'<text x="{x}" y="{y+174}" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#68767c">{label}</text>'
    (ROOT/'sizes.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">{content}</svg>')


if __name__ == '__main__':
    main()
