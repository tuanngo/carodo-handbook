// Outlines the Carodo wordmark to SVG path data, with no dependencies beyond macOS (CoreText).
//
//   swift wordmark.swift <font.ttf> <out.json> [text] [weight] [tracking]
//
// font:     Plus Jakarta Sans variable font (OFL), e.g. PlusJakartaSans[wght].ttf from google/fonts
// text:     default "Carodo"
// weight:   wght axis value, default 600 (SemiBold)
// tracking: extra space between letters as a share of the font size, default 0
//
// Writes JSON: { d, width, capHeight, xHeight, ascent, descent, size } in a coordinate space where
// the font size is 100, the baseline is y = 0 and y grows downward (SVG convention). Kerning from the
// font is applied. mark.py reads this file to build the lockups.
import CoreText
import Foundation

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: swift wordmark.swift <font.ttf> <out.json> [text] [weight] [tracking]\n".data(using: .utf8)!)
    exit(2)
}
let fontURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])
let text = args.count > 3 ? args[3] : "Carodo"
let weight = args.count > 4 ? Double(args[4]) ?? 600 : 600
let tracking = args.count > 5 ? Double(args[5]) ?? 0 : 0
let size: CGFloat = 100

guard let descriptors = CTFontManagerCreateFontDescriptorsFromURL(fontURL as CFURL) as? [CTFontDescriptor],
      let base = descriptors.first else {
    FileHandle.standardError.write("cannot read font at \(fontURL.path)\n".data(using: .utf8)!)
    exit(1)
}
// Variable font: pin the Weight ('wght') axis. CTFontDescriptorCreateCopyWithVariation is the call that
// takes effect for a font loaded from a file (a CGFont variation or a raw attribute dictionary does not).
let wghtTag = NSNumber(value: 0x7767_6874 as UInt32)
let font = CTFontCreateWithFontDescriptor(
    CTFontDescriptorCreateCopyWithVariation(base, wghtTag, CGFloat(weight)), size, nil)

let attributed = NSAttributedString(string: text, attributes: [
    NSAttributedString.Key(kCTFontAttributeName as String): font,
    NSAttributedString.Key(kCTKernAttributeName as String): NSNumber(value: tracking * Double(size)),
])
let line = CTLineCreateWithAttributedString(attributed)

var d = ""
func fmt(_ v: CGFloat) -> String {
    var s = String(format: "%.2f", Double(v))
    while s.contains(".") && (s.hasSuffix("0") || s.hasSuffix(".")) { s.removeLast() }
    return s == "-0" ? "0" : s
}

for run in CTLineGetGlyphRuns(line) as! [CTRun] {
    let count = CTRunGetGlyphCount(run)
    var glyphs = [CGGlyph](repeating: 0, count: count)
    var positions = [CGPoint](repeating: .zero, count: count)
    CTRunGetGlyphs(run, CFRange(location: 0, length: count), &glyphs)
    CTRunGetPositions(run, CFRange(location: 0, length: count), &positions)
    for i in 0..<count {
        // flip y so the path is in SVG space (baseline at 0, y down)
        var transform = CGAffineTransform(a: 1, b: 0, c: 0, d: -1, tx: positions[i].x, ty: -positions[i].y)
        guard let path = CTFontCreatePathForGlyph(font, glyphs[i], &transform) else { continue }
        path.applyWithBlock { element in
            let p = element.pointee.points
            switch element.pointee.type {
            case .moveToPoint: d += "M\(fmt(p[0].x)) \(fmt(p[0].y))"
            case .addLineToPoint: d += "L\(fmt(p[0].x)) \(fmt(p[0].y))"
            case .addQuadCurveToPoint: d += "Q\(fmt(p[0].x)) \(fmt(p[0].y)) \(fmt(p[1].x)) \(fmt(p[1].y))"
            case .addCurveToPoint:
                d += "C\(fmt(p[0].x)) \(fmt(p[0].y)) \(fmt(p[1].x)) \(fmt(p[1].y)) \(fmt(p[2].x)) \(fmt(p[2].y))"
            case .closeSubpath: d += "Z"
            @unknown default: break
            }
        }
    }
}

// width = ink extent (no trailing tracking), so lockups align to the visible letters
let bounds = CTLineGetBoundsWithOptions(line, .useGlyphPathBounds)
let result: [String: Any] = [
    "text": text, "weight": weight, "tracking": tracking, "size": Double(size),
    "d": d,
    "inkLeft": Double(bounds.minX), "width": Double(bounds.maxX),
    "capHeight": Double(CTFontGetCapHeight(font)), "xHeight": Double(CTFontGetXHeight(font)),
    "ascent": Double(CTFontGetAscent(font)), "descent": Double(CTFontGetDescent(font)),
]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try data.write(to: outURL)
print("wrote \(outURL.path): width \(fmt(bounds.maxX)), cap height \(fmt(CTFontGetCapHeight(font)))")
