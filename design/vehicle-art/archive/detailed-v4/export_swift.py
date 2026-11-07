"""Export the SVG drawing layers to cached SwiftUI paths, without an SVG runtime.

Usage: python3 -B export_swift.py /path/to/VehicleArtData.swift
Then format the output with Xcode's swift-format.
"""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from generate import svg, CARS, BIKES


def ink(value, opacity='1', stroke=False):
    if value is None or value == 'none':
        return 'nil'
    if value == 'currentColor':
        return '.paint'
    if value.startswith('url('):
        return '.shade' if '-shade' in value else '.glass'
    if stroke and value == '#263039':
        return '.outline'
    value = {'white': '#ffffff', 'black': '#000000'}.get(value, value)
    return f'.solid(0x{value[1:].upper()}, {opacity})'


def layers(key, compact):
    root = ET.fromstring(svg(key,compact))
    result=[]
    for element in root:
        tag=element.tag.rsplit('}',1)[-1]
        a=element.attrib
        if tag in ('defs','title'):
            continue
        opacity=float(a.get('opacity','1'))
        fill=ink(a.get('fill','black'), str(opacity*float(a.get('fill-opacity','1'))))
        stroke=ink(a.get('stroke'),str(opacity*float(a.get('stroke-opacity','1'))),True)
        if tag == 'path':
            shape='"'+a['d']+'"'
        elif tag in ('circle','ellipse'):
            rx=float(a.get('r',a.get('rx','0')))
            ry=float(a.get('r',a.get('ry','0')))
            x=float(a['cx'])-rx
            y=float(a['cy'])-ry
            shape=f'ellipse: CGRect(x: {x:g}, y: {y:g}, width: {2*rx:g}, height: {2*ry:g})'
        else:
            raise ValueError(tag)
        width = float(a.get('stroke-width','1'))
        result.append(f'            VehicleArtLayer({shape}, fill: {fill}, stroke: {stroke}, lineWidth: {width}),')
    return '\n'.join(result)


def main():
    output=['import SwiftUI', '', '// Generated v4 vehicle geometry. Do not hand-edit individual layers.',
            '// Paths are parsed once; paint and theme are resolved when drawing.',
            'nonisolated enum VehicleArtData {']
    for name,compact in [('regular',False),('compact',True)]:
        output.append(f'    static let {name}: [VehicleBodyStyle: [VehicleArtLayer]] = [')
        for key in (*CARS,*BIKES):
            output.extend([f'        .{key}: [',layers(key,compact),'        ],'])
        output.append('    ]')
    output.append('}')
    Path(sys.argv[1]).write_text('\n'.join(output)+'\n')


if __name__ == '__main__':
    main()
