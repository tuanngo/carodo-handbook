// Builds every brand asset from geometry.json (written by mark.py) and wordmark.json.
//
//   swift export.swift          (run from anywhere; paths are relative to this file)
//
// Uses only macOS frameworks: CoreGraphics boolean operations (macOS 13+) flatten the mark into plain
// filled paths -- no masks, no strokes, no arcs -- so the SVGs work in Icon Composer, Figma, browsers
// and any strict SVG reader; CoreGraphics + ImageIO render the PNGs.
//
// Writes:
//   ../svg/                          the mark, wordmark, lockup and app-icon sources (flattened SVG)
//   ../export/ios/AppIcon.appiconset light (no alpha), dark and tinted 1024 PNGs + Contents.json
//   ../export/icon-composer/         the icon's layers as separate SVGs, for an Icon Composer .icon later
//   ../export/web/                   favicon.ico/.svg, apple-touch-icon, PWA icons, OG image, manifest, <head> snippet
//   ../export/ios/LaunchMark.imageset, LaunchBackground.colorset   the static launch screen
//   ../export/ios/CarodoMarkGeometry.swift                         the mark as SwiftUI paths, in animatable parts
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let source = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
let root = source.deletingLastPathComponent()

// MARK: - Input

let geometry = try JSONSerialization.jsonObject(
    with: Data(contentsOf: source.appendingPathComponent("geometry.json"))) as! [String: Any]
let colors = geometry["colors"] as! [String: String]
let charcoal = colors["charcoal"]!, copper = colors["copper"]!, ivory = colors["ivory"]!
let iconScale = geometry["iconScale"] as! Double

/// Parses absolute SVG path data with M, L, Q, C and Z (what mark.py and CoreText produce).
func parsePath(_ d: String) -> CGPath {
    let path = CGMutablePath()
    var tokens: [String] = []
    var current = ""
    for ch in d {
        if "MLQCZ".contains(ch) {
            if !current.isEmpty { tokens.append(current); current = "" }
            tokens.append(String(ch))
        } else if ch == " " || ch == "," {
            if !current.isEmpty { tokens.append(current); current = "" }
        } else if ch == "-" && !current.isEmpty && !current.hasSuffix("e") {
            tokens.append(current); current = "-"
        } else {
            current.append(ch)
        }
    }
    if !current.isEmpty { tokens.append(current) }
    var i = 0
    func num() -> CGFloat { defer { i += 1 }; return CGFloat(Double(tokens[i])!) }
    func pt() -> CGPoint { let x = num(); return CGPoint(x: x, y: num()) }
    var command = "M"
    while i < tokens.count {
        if "MLQCZ".contains(tokens[i]) { command = tokens[i]; i += 1 }
        switch command {
        case "M": path.move(to: pt()); command = "L"   // implicit line-tos after a move
        case "L": path.addLine(to: pt())
        case "Q": let c = pt(); path.addQuadCurve(to: pt(), control: c)
        case "C": let c1 = pt(), c2 = pt(); path.addCurve(to: pt(), control1: c1, control2: c2)
        case "Z": path.closeSubpath()
        default: fatalError("unsupported path command \(command)")
        }
    }
    return path
}

func fmt(_ v: CGFloat) -> String {
    var s = String(format: "%.2f", Double(v))
    while s.contains(".") && (s.hasSuffix("0") || s.hasSuffix(".")) { s.removeLast() }
    return s == "-0" ? "0" : s
}

func svgData(_ path: CGPath) -> String {
    var d = ""
    path.applyWithBlock { e in
        let p = e.pointee.points
        switch e.pointee.type {
        case .moveToPoint: d += "M\(fmt(p[0].x)) \(fmt(p[0].y))"
        case .addLineToPoint: d += "L\(fmt(p[0].x)) \(fmt(p[0].y))"
        case .addQuadCurveToPoint: d += "Q\(fmt(p[0].x)) \(fmt(p[0].y)) \(fmt(p[1].x)) \(fmt(p[1].y))"
        case .addCurveToPoint:
            d += "C\(fmt(p[0].x)) \(fmt(p[0].y)) \(fmt(p[1].x)) \(fmt(p[1].y)) \(fmt(p[2].x)) \(fmt(p[2].y))"
        case .closeSubpath: d += "Z"
        @unknown default: break
        }
    }
    return d
}

// MARK: - Flattening

/// A filled shape in one colour role.
struct Layer { let role: Role; let path: CGPath }
enum Role { case wheel, road, hub, word }

/// The shape grown by `gap` on every side (the knock-out around anything the journey crosses).
func grown(_ p: CGPath, by gap: Double) -> CGPath {
    p.union(p.copy(strokingWithWidth: 2 * gap, lineCap: .round, lineJoin: .round, miterLimit: 10))
}

/// The mark as flat, non-overlapping filled paths on the 100x100 grid.
func markLayers(_ name: String, mono: Bool = false) -> [Layer] {
    let v = geometry[name] as! [String: Any]
    let gap = v["gap"] as! Double
    let ring = parsePath(v["ring"] as! String)
        .copy(strokingWithWidth: v["ringWidth"] as! Double, lineCap: .butt, lineJoin: .miter, miterLimit: 10)
        .subtracting(grown(parsePath(v["swooshCut"] as! String), by: gap))
    var wheel = parsePath(v["wheel"] as! String).normalized()
        .subtracting(grown(parsePath(v["underSwoosh"] as! String), by: gap))
    let hubGap = mono ? v["monoHubGap"] as! String : v["hubGap"] as! String
    if !hubGap.isEmpty { wheel = wheel.subtracting(parsePath(hubGap)) }
    var layers = [Layer(role: .wheel, path: ring.union(wheel)),
                  Layer(role: .hub, path: parsePath(v["cap"] as! String)),
                  Layer(role: .road, path: parsePath(v["swoosh"] as! String))]
    let lane = v["lane"] as! String
    if !lane.isEmpty { layers.append(Layer(role: .road, path: parsePath(lane))) }
    return layers
}

let wordmarkInfo = geometry["wordmark"] as! [String: Any]
let wordmarkPath = parsePath(wordmarkInfo["d"] as! String).normalized()   // removes overlapping contours

func lockupLayers() -> [Layer] {
    let l = geometry["lockup"] as! [String: Any]
    var t = CGAffineTransform(translationX: l["textX"] as! Double, y: l["baseline"] as! Double)
        .scaledBy(x: l["textScale"] as! Double, y: l["textScale"] as! Double)
    return markLayers("full") + [Layer(role: .word, path: wordmarkPath.copy(using: &t)!)]
}

func transformed(_ layers: [Layer], _ t: CGAffineTransform) -> [Layer] {
    var t = t
    return layers.map { Layer(role: $0.role, path: $0.path.copy(using: &t)!) }
}

/// The mark placed on the 1024 icon canvas.
func iconLayers(_ name: String = "full") -> [Layer] {
    let offset = (1024 - 100 * iconScale) / 2
    return transformed(markLayers(name), CGAffineTransform(translationX: offset, y: offset).scaledBy(x: iconScale, y: iconScale))
}

// MARK: - Output

struct Palette { let wheel, road, hub, word: String }
let onDark = Palette(wheel: ivory, road: copper, hub: copper, word: ivory)
let onLight = Palette(wheel: charcoal, road: copper, hub: copper, word: charcoal)
let mono = Palette(wheel: "currentColor", road: "currentColor", hub: "currentColor", word: "currentColor")
let tinted = Palette(wheel: "#FFFFFF", road: "#B4B4B4", hub: "#B4B4B4", word: "#FFFFFF")

func color(_ role: Role, _ p: Palette) -> String {
    switch role { case .wheel: p.wheel; case .road: p.road; case .hub: p.hub; case .word: p.word }
}

func svg(_ layers: [Layer], _ palette: Palette, viewBox: [Double], background: String? = nil) -> String {
    let vb = viewBox.map { fmt(CGFloat($0)) }.joined(separator: " ")
    var body = background.map { "<rect x=\"\(fmt(viewBox[0]))\" y=\"\(fmt(viewBox[1]))\" width=\"\(fmt(viewBox[2]))\" height=\"\(fmt(viewBox[3]))\" fill=\"\($0)\"/>" } ?? ""
    for l in layers { body += "<path fill=\"\(color(l.role, palette))\" fill-rule=\"evenodd\" d=\"\(svgData(l.path))\"/>" }
    return "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"\(vb)\" width=\"\(fmt(viewBox[2]))\" height=\"\(fmt(viewBox[3]))\">\(body)</svg>\n"
}

func cgColor(_ hex: String) -> CGColor {
    let v = UInt32(hex.dropFirst(), radix: 16)!
    return CGColor(srgbRed: CGFloat((v >> 16) & 0xff) / 255, green: CGFloat((v >> 8) & 0xff) / 255,
                   blue: CGFloat(v & 0xff) / 255, alpha: 1)
}

/// Renders layers (in their own coordinates, y down) into a PNG of `size`, after `transform`.
/// `opaque` writes an image without an alpha channel (required for the App Store icon).
func png(_ layers: [Layer], _ palette: Palette, size: CGSize, transform: CGAffineTransform = .identity,
         background: String? = nil, opaque: Bool = false) -> Data {
    let info = opaque ? CGImageAlphaInfo.noneSkipLast.rawValue : CGImageAlphaInfo.premultipliedLast.rawValue
    let ctx = CGContext(data: nil, width: Int(size.width), height: Int(size.height), bitsPerComponent: 8,
                        bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: info)!
    ctx.translateBy(x: 0, y: size.height)
    ctx.scaleBy(x: 1, y: -1)
    if let background { ctx.setFillColor(cgColor(background)); ctx.fill(CGRect(origin: .zero, size: size)) }
    ctx.concatenate(transform)
    for l in layers {
        ctx.addPath(l.path)
        ctx.setFillColor(cgColor(color(l.role, palette)))
        ctx.fillPath(using: .evenOdd)
    }
    let data = NSMutableData()
    let dest = CGImageDestinationCreateWithData(data, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    CGImageDestinationFinalize(dest)
    return data as Data
}

/// A square PNG of the mark: `markShare` of the edge is the mark's 100-unit grid.
func markPNG(_ name: String, _ palette: Palette, edge: Int, markShare: Double = 1, background: String? = nil,
             badge: String? = nil, opaque: Bool = false) -> Data {
    var layers = markLayers(name)
    var p = palette
    if let badge {   // a disc behind the mark (drawn in the .word role) so it reads on any tab colour
        layers.insert(Layer(role: .word, path: CGPath(ellipseIn: CGRect(x: 2, y: 2, width: 96, height: 96), transform: nil)), at: 0)
        p = Palette(wheel: palette.wheel, road: palette.road, hub: palette.hub, word: badge)
    }
    let s = Double(edge) * markShare / 100
    let o = (Double(edge) - 100 * s) / 2
    return png(layers, p, size: CGSize(width: edge, height: edge),
               transform: CGAffineTransform(translationX: o, y: o).scaledBy(x: s, y: s), background: background, opaque: opaque)
}

/// .ico with PNG-encoded images (supported by every current browser and Windows Vista+).
func ico(_ images: [(Int, Data)]) -> Data {
    var out = Data([0, 0, 1, 0, UInt8(images.count), 0])
    var offset = 6 + 16 * images.count
    func le16(_ v: Int) -> [UInt8] { [UInt8(v & 0xff), UInt8(v >> 8 & 0xff)] }
    func le32(_ v: Int) -> [UInt8] { le16(v & 0xffff) + le16(v >> 16) }
    for (edge, data) in images {
        out += [UInt8(edge >= 256 ? 0 : edge), UInt8(edge >= 256 ? 0 : edge), 0, 0] + le16(1) + le16(32)
            + le32(data.count) + le32(offset)
        offset += data.count
    }
    for (_, data) in images { out += data }
    return out
}

func write(_ data: Data, _ relative: String) throws {
    let url = root.appendingPathComponent(relative)
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try data.write(to: url)
}
func write(_ text: String, _ relative: String) throws { try write(Data(text.utf8), relative) }

// MARK: - Assets

let markBox: [Double] = [0, 0, 100, 100]
let wordBox = ["x", "y", "width", "height"].map { wordmarkInfo[$0] as! Double }
let lockupBox = (geometry["lockup"] as! [String: Any])["viewBox"] as! [Double]
let iconBox: [Double] = [0, 0, 1024, 1024]
var count = 0
func out(_ text: String, _ path: String) throws { try write(text, path); count += 1 }
func out(_ data: Data, _ path: String) throws { try write(data, path); count += 1 }

// svg/
try out(svg(markLayers("full"), onDark, viewBox: markBox), "svg/carodo-mark-on-dark.svg")
try out(svg(markLayers("full"), onLight, viewBox: markBox), "svg/carodo-mark-on-light.svg")
try out(svg(markLayers("full", mono: true), mono, viewBox: markBox), "svg/carodo-mark-mono.svg")
try out(svg(markLayers("small"), onDark, viewBox: markBox), "svg/carodo-mark-small-on-dark.svg")
try out(svg(markLayers("small"), onLight, viewBox: markBox), "svg/carodo-mark-small-on-light.svg")
try out(svg(markLayers("small", mono: true), mono, viewBox: markBox), "svg/carodo-mark-small-mono.svg")
let word = [Layer(role: .word, path: wordmarkPath)]
try out(svg(word, onDark, viewBox: wordBox), "svg/carodo-wordmark-on-dark.svg")
try out(svg(word, onLight, viewBox: wordBox), "svg/carodo-wordmark-on-light.svg")
try out(svg(word, mono, viewBox: wordBox), "svg/carodo-wordmark-mono.svg")
try out(svg(lockupLayers(), onDark, viewBox: lockupBox), "svg/carodo-lockup-on-dark.svg")
try out(svg(lockupLayers(), onLight, viewBox: lockupBox), "svg/carodo-lockup-on-light.svg")
try out(svg(iconLayers(), onLight, viewBox: iconBox, background: ivory), "svg/appicon-light.svg")
try out(svg(iconLayers(), onDark, viewBox: iconBox), "svg/appicon-dark.svg")
try out(svg(iconLayers(), tinted, viewBox: iconBox), "svg/appicon-tinted.svg")

// export/ios/AppIcon.appiconset -- one 1024 image per appearance (Xcode 14+ single size).
// Light is opaque (the App Store rejects an icon with alpha). Dark sits on a transparent background
// so iOS supplies its dark gradient. Tinted is greyscale; iOS colours it.
let full = CGSize(width: 1024, height: 1024)
try out(png(iconLayers(), onLight, size: full, background: ivory, opaque: true), "export/ios/AppIcon.appiconset/AppIcon.png")
try out(png(iconLayers(), onDark, size: full), "export/ios/AppIcon.appiconset/AppIcon-Dark.png")
try out(png(iconLayers(), tinted, size: full), "export/ios/AppIcon.appiconset/AppIcon-Tinted.png")
try out("""
{
  "images" : [
    {
      "filename" : "AppIcon.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    },
    {
      "appearances" : [ { "appearance" : "luminosity", "value" : "dark" } ],
      "filename" : "AppIcon-Dark.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    },
    {
      "appearances" : [ { "appearance" : "luminosity", "value" : "tinted" } ],
      "filename" : "AppIcon-Tinted.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}

""", "export/ios/AppIcon.appiconset/Contents.json")

// export/icon-composer -- layers for an Icon Composer .icon (iOS 26 Liquid Glass): background colour
// is set in Icon Composer (ivory), these are the foreground layers, back to front.
let layers = iconLayers()
try out(svg(layers.filter { $0.role == .wheel }, onLight, viewBox: iconBox), "export/icon-composer/1-wheel.svg")
try out(svg(layers.filter { $0.role == .hub }, onLight, viewBox: iconBox), "export/icon-composer/2-hub.svg")
try out(svg(layers.filter { $0.role == .road }, onLight, viewBox: iconBox), "export/icon-composer/3-journey.svg")

// export/web
// favicon.ico: the small mark on a charcoal disc, so it reads on light and dark browser tabs.
try out(ico([16, 32, 48].map { ($0, markPNG("small", onDark, edge: $0, badge: charcoal)) }), "export/web/favicon.ico")
// favicon.svg: the small mark that follows the browser's colour scheme.
let small = markLayers("small")
var faviconBody = ""
for l in small {
    let cls = l.role == .wheel ? " class=\"w\"" : ""
    faviconBody += "<path\(cls) fill=\"\(color(l.role, onLight))\" fill-rule=\"evenodd\" d=\"\(svgData(l.path))\"/>"
}
try out("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><style>@media (prefers-color-scheme: dark){.w{fill:\(ivory)}}</style>\(faviconBody)</svg>\n",
        "export/web/favicon.svg")
// apple-touch-icon: the light app icon (opaque; iOS rounds the corners).
try out(png(iconLayers(), onLight, size: CGSize(width: 180, height: 180), transform: CGAffineTransform(scaleX: 180 / 1024, y: 180 / 1024), background: ivory, opaque: true),
        "export/web/apple-touch-icon.png")
for edge in [192, 512] {
    let s = Double(edge) / 1024
    try out(png(iconLayers(), onLight, size: CGSize(width: edge, height: edge), transform: CGAffineTransform(scaleX: s, y: s), background: ivory, opaque: true),
            "export/web/icon-\(edge).png")
}
// maskable: the ring stays inside the 80 % safe circle (ring diameter 92 units -> 72 % of the edge)
try out(markPNG("full", onLight, edge: 512, markShare: 0.72 * 100 / 92, background: ivory, opaque: true), "export/web/icon-maskable-512.png")
// Open Graph / social share image: the lockup centred on charcoal.
let og = CGSize(width: 1200, height: 630)
let lockupWidth = 640.0, ls = lockupWidth / lockupBox[2]
try out(png(lockupLayers(), onDark, size: og,
            transform: CGAffineTransform(translationX: (og.width - lockupWidth) / 2 - lockupBox[0] * ls,
                                         y: (og.height - lockupBox[3] * ls) / 2 - lockupBox[1] * ls).scaledBy(x: ls, y: ls),
            background: charcoal, opaque: true), "export/web/og-image.png")
try out("""
{
  "name": "Carodo",
  "short_name": "Carodo",
  "icons": [
    { "src": "/icon-192.png", "type": "image/png", "sizes": "192x192" },
    { "src": "/icon-512.png", "type": "image/png", "sizes": "512x512" },
    { "src": "/icon-maskable-512.png", "type": "image/png", "sizes": "512x512", "purpose": "maskable" }
  ],
  "theme_color": "\(charcoal)",
  "background_color": "\(charcoal)",
  "display": "standalone"
}

""", "export/web/site.webmanifest")
try out("""
<!-- Carodo icons: copy the files in export/web/ to the site root, then add to <head>. -->
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="\(charcoal)">
<meta property="og:image" content="https://carodo.app/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">

""", "export/web/head.html")

// MARK: - iOS launch screen + animatable mark

/// SwiftUI `Path` source for a CGPath on the 100-unit grid.
func swiftPath(_ path: CGPath) -> String {
    var lines: [String] = []
    func pt(_ p: CGPoint) -> String { "CGPoint(x: \(fmt(p.x)), y: \(fmt(p.y)))" }
    path.applyWithBlock { e in
        let p = e.pointee.points
        switch e.pointee.type {
        case .moveToPoint: lines.append("p.move(to: \(pt(p[0])))")
        case .addLineToPoint: lines.append("p.addLine(to: \(pt(p[0])))")
        case .addQuadCurveToPoint: lines.append("p.addQuadCurve(to: \(pt(p[1])), control: \(pt(p[0])))")
        case .addCurveToPoint: lines.append("p.addCurve(to: \(pt(p[2])), control1: \(pt(p[0])), control2: \(pt(p[1])))")
        case .closeSubpath: lines.append("p.closeSubpath()")
        @unknown default: break
        }
    }
    return "Path { p in\n" + lines.map { "        " + $0 }.joined(separator: "\n") + "\n    }"
}

/// Splits a path into its subpaths (one per move-to).
func subpaths(_ path: CGPath) -> [CGPath] {
    var parts: [CGMutablePath] = []
    path.applyWithBlock { e in
        let p = e.pointee.points
        switch e.pointee.type {
        case .moveToPoint: let m = CGMutablePath(); m.move(to: p[0]); parts.append(m)
        case .addLineToPoint: parts.last?.addLine(to: p[0])
        case .addQuadCurveToPoint: parts.last?.addQuadCurve(to: p[1], control: p[0])
        case .addCurveToPoint: parts.last?.addCurve(to: p[2], control1: p[0], control2: p[1])
        case .closeSubpath: parts.last?.closeSubpath()
        @unknown default: break
        }
    }
    return parts
}

/// The wheel alone, whole: the ring and spokes with no knock-outs (nothing crosses them yet) and the
/// copper cap. The launch screen and the onboarding's first scene show it; the journey joins it in
/// the onboarding's last scene (../../onboarding.md).
func wheelLayers(_ name: String) -> [Layer] {
    let v = geometry[name] as! [String: Any]
    let ring = parsePath(v["ring"] as! String)
        .copy(strokingWithWidth: v["ringWidth"] as! Double, lineCap: .butt, lineJoin: .miter, miterLimit: 10)
    var wheel = parsePath(v["wheel"] as! String).normalized()
    let hubGap = v["hubGap"] as! String
    if !hubGap.isEmpty { wheel = wheel.subtracting(parsePath(hubGap)) }
    return [Layer(role: .wheel, path: ring.union(wheel)), Layer(role: .hub, path: parsePath(v["cap"] as! String))]
}

// LaunchMark: the whole wheel (no journey) at the mark's 120 pt box, charcoal wheel (any) and ivory
// wheel (dark), @2x and @3x.
let launchPoints = 120
for (suffix, palette) in [("light", onLight), ("dark", onDark)] {
    for scale in [2, 3] {
        let edge = launchPoints * scale, s = Double(edge) / 100
        try out(png(wheelLayers("full"), palette, size: CGSize(width: edge, height: edge),
                    transform: CGAffineTransform(scaleX: s, y: s)),
                "export/ios/LaunchMark.imageset/LaunchMark-\(suffix)@\(scale)x.png")
    }
}
try out("""
{
  "images" : [
    { "filename" : "LaunchMark-light@2x.png", "idiom" : "universal", "scale" : "2x" },
    { "filename" : "LaunchMark-light@3x.png", "idiom" : "universal", "scale" : "3x" },
    { "appearances" : [ { "appearance" : "luminosity", "value" : "dark" } ],
      "filename" : "LaunchMark-dark@2x.png", "idiom" : "universal", "scale" : "2x" },
    { "appearances" : [ { "appearance" : "luminosity", "value" : "dark" } ],
      "filename" : "LaunchMark-dark@3x.png", "idiom" : "universal", "scale" : "3x" }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}

""", "export/ios/LaunchMark.imageset/Contents.json")

func colorJSON(_ hex: String) -> String {
    let v = UInt32(hex.dropFirst(), radix: 16)!
    let c = [(v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff].map { String(format: "0x%02X", $0) }
    return "\"color\" : { \"color-space\" : \"srgb\", \"components\" : { \"alpha\" : \"1.000\", \"red\" : \"\(c[0])\", \"green\" : \"\(c[1])\", \"blue\" : \"\(c[2])\" } }"
}
try out("""
{
  "colors" : [
    { "idiom" : "universal", \(colorJSON(ivory)) },
    { "appearances" : [ { "appearance" : "luminosity", "value" : "dark" } ],
      "idiom" : "universal", \(colorJSON(charcoal)) }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}

""", "export/ios/LaunchBackground.colorset/Contents.json")

// CarodoMarkGeometry.swift: the full mark split into the parts the welcome animation moves.
// At rest (spokes at a multiple of 72 degrees, everything visible) it draws exactly markLayers("full").
let fullGeometry = geometry["full"] as! [String: Any]
let fullGap = fullGeometry["gap"] as! Double
let ringPart = markLayers("full")[0].path.subtracting(
    parsePath(fullGeometry["wheel"] as! String).normalized())   // ring only (the wheel layer is ring + spokes)
let spokesPart = parsePath(fullGeometry["wheel"] as! String).normalized()
    .subtracting(parsePath(fullGeometry["hubGap"] as! String))
let spokesKnockout = grown(parsePath(fullGeometry["underSwoosh"] as! String), by: fullGap)
// What the journey's knock-out removes from the ring: drawn back in while the wheel stands alone.
let ringGapPart = wheelLayers("full")[0].path.subtracting(markLayers("full")[0].path)
    .subtracting(parsePath(fullGeometry["wheel"] as! String).normalized())
let laneParts = subpaths(parsePath(fullGeometry["lane"] as! String))
let wb = wordBox
try out("""
// Generated by carodo-handbook/design/brand/source/export.swift -- do not edit.
// Regenerate with `sh source/build.sh`, then copy export/ios/CarodoMarkGeometry.swift here.
import SwiftUI

/// The Carodo mark on its 100 x 100 grid, split into parts so they can move separately.
/// `spokes` rotates about (50, 50); `spokesKnockout` is fixed and is cut out of the spokes,
/// so at any multiple of 72 degrees the drawing equals the flattened brand mark.
enum CarodoMarkGeometry {
    static let grid: CGFloat = 100
    static let center = CGPoint(x: 50, y: 50)

    static let ring = \(swiftPath(ringPart))

    static let spokes = \(swiftPath(spokesPart))

    static let spokesKnockout = \(swiftPath(spokesKnockout))

    /// The ring's knock-out under the journey; filled in, the ring is whole (the wheel alone).
    static let ringGap = \(swiftPath(ringGapPart))

    static let cap = \(swiftPath(parsePath(fullGeometry["cap"] as! String)))

    static let swoosh = \(swiftPath(parsePath(fullGeometry["swoosh"] as! String)))

    /// The three lane dashes, nearest first.
    static let lane: [Path] = [
\(laneParts.map { "        " + swiftPath($0).replacingOccurrences(of: "\n", with: "\n    ") }.joined(separator: ",\n"))
    ]

    /// "Carodo" in its own coordinates (baseline at y = 0); `wordmarkBounds` is tight to the ink.
    static let wordmark = \(swiftPath(wordmarkPath))

    static let wordmarkBounds = CGRect(x: \(fmt(wb[0])), y: \(fmt(wb[1])), width: \(fmt(wb[2])), height: \(fmt(wb[3])))
}

""", "export/ios/CarodoMarkGeometry.swift")

print("wrote \(count) files under \(root.path)")
