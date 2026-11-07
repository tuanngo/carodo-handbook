"""Proposed paint palette; design-only, no changes to stored vehicle colours."""
from pathlib import Path
import json
from generate import artwork

ROOT = Path(__file__).parent
COLORS = [
    ('Silver', '#B8BDC2', 'Trung tính'),
    ('Slate', '#8195A6', 'Mặc định'),
    ('Pearl', '#E5E2DC', 'Trắng ngọc'),
    ('Graphite', '#41474C', 'Đen than'),
    ('Crimson', '#AE5450', 'Đỏ trầm'),
    ('Ocean', '#567FA3', 'Xanh biển'),
    ('Forest', '#648272', 'Xanh rêu'),
    ('Champagne', '#C6AA68', 'Vàng cát'),
    ('Terracotta', '#BE805E', 'Cam đất'),
    ('Cocoa', '#8E7262', 'Nâu'),
]


def vehicle(key, paint, identity, dark=False, compact=False):
    _, art = artwork(key, compact)
    art = art.replace(f'{key}-', f'{identity}-{key}-')
    if dark:
        # Only the outline changes; selected paint remains identical in both themes.
        art = art.replace('stroke="#263039"', 'stroke="#F3EEE5"')
        art = art.replace('stroke-opacity=".45"', 'stroke-opacity=".25"')
        art = art.replace('stroke-opacity=".55"', 'stroke-opacity=".25"')
    return f'<g color="{paint}">{art}</g>'


def label(x, y, text, color, size=12, weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" font-weight="{weight}">{text}</text>'


def main():
    sheet = ''
    for dark in (False, True):
        x = 600 if dark else 0
        bg, fg, secondary, border = ('#242321', '#F3EEE5', '#B5B0A7', '#605C56') if dark else ('#F3EEE5', '#242321', '#77736D', '#CCC6BD')
        sheet += f'<rect x="{x}" width="600" height="1200" fill="{bg}"/>'
        sheet += label(x+28, 42, 'CARODO · Sơn xe', fg, 24, 600)
        sheet += label(x+28, 69, f'{"Dark · Charcoal" if dark else "Light · Ivory"} {bg}', secondary, 13)
        sheet += label(x+28, 93, 'Màu sơn giữ nguyên · Viền theo nền', secondary, 12)
        for i, (name, paint, role) in enumerate(COLORS):
            y = 115+i*100
            sheet += f'<path d="M{x+28} {y+97} H{x+572}" stroke="{border}" stroke-opacity=".45"/>'
            sheet += f'<circle cx="{x+46}" cy="{y+36}" r="15" fill="{paint}" stroke="{border}" stroke-width="1"/>'
            if name == 'Slate':
                sheet += f'<circle cx="{x+46}" cy="{y+36}" r="20" fill="none" stroke="#BD8053" stroke-width="2"/>'
                sheet += f'<path d="M{x+39} {y+36} l5 5 9 -10" fill="none" stroke="#242321" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            sheet += label(x+76, y+28, name, fg, 14, 600)
            sheet += label(x+76, y+47, paint, secondary, 11)
            sheet += label(x+76, y+66, role, secondary, 11)
            for j, key in enumerate(('sedan', 'manual')):
                art = vehicle(key, paint, f'{dark}-{i}-{j}', dark)
                sheet += f'<g transform="translate({x+185+j*168},{y+13}) scale(.67)">{art}</g>'
            # A square selection tile demonstrates the compact asset at 48 CSS px.
            sheet += f'<rect x="{x+528}" y="{y+12}" width="52" height="52" rx="14" fill="none" stroke="{border}"/>'
            art = vehicle('sedan', paint, f'{dark}-{i}-badge', dark, True)
            sheet += f'<g transform="translate({x+530},{y+27}) scale(.2)">{art}</g>'
        sheet += label(x+28, 1158, 'Vòng chọn Copper #BD8053 + dấu chọn', secondary, 12)
        sheet += label(x+28, 1180, 'Bản thử thiết kế · Chưa áp dụng vào app', secondary, 12)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200">{sheet}</svg>'
    (ROOT/'palette-proposal.svg').write_text(svg)
    (ROOT/'palette-proposal.json').write_text(json.dumps({
        'status': 'design proposal, not persisted values',
        'default': 'Slate', 'neutral': 'Silver',
        'backgrounds': {'light': '#F3EEE5', 'dark': '#242321'},
        'selection': '#BD8053',
        'colors': [{'name': n, 'hex': h, 'role': r} for n,h,r in COLORS]
    }, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
