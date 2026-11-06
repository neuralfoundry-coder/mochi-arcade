// A tiny software renderer: 32-bit RGBA surfaces with the drawing primitives the games use
// (mirrors the pygame calls of the desktop version so the games port almost line by line).
import CoreGraphics
import Foundation

typealias Color = UInt32 // bytes in memory: R, G, B, A  (0xAABBGGRR)

@inline(__always) func rgba(_ r: Int, _ g: Int, _ b: Int, _ a: Int = 255) -> Color {
    UInt32(r & 255) | (UInt32(g & 255) << 8) | (UInt32(b & 255) << 16) | (UInt32(a & 255) << 24)
}

extension UInt32 {
    @inline(__always) var cr: Int { Int(self & 255) }
    @inline(__always) var cg: Int { Int((self >> 8) & 255) }
    @inline(__always) var cb: Int { Int((self >> 16) & 255) }
    @inline(__always) var ca: Int { Int(self >> 24) }
    func alpha(_ a: Int) -> Color { (self & 0x00FF_FFFF) | (UInt32(Swift.max(0, Swift.min(255, a))) << 24) }
}

struct IRect {
    var x, y, w, h: Int
    init(_ x: Int, _ y: Int, _ w: Int, _ h: Int) { self.x = x; self.y = y; self.w = w; self.h = h }
    var right: Int { x + w }
    var bottom: Int { y + h }
    var centerx: Int { x + w / 2 }
    var centery: Int { y + h / 2 }
    func intersects(_ o: IRect) -> Bool { x < o.right && o.x < right && y < o.bottom && o.y < bottom }
    func inflate(_ dx: Int, _ dy: Int) -> IRect { IRect(x - dx / 2, y - dy / 2, w + dx, h + dy) }
    func contains(_ px: Double, _ py: Double) -> Bool { px >= Double(x) && px < Double(right) && py >= Double(y) && py < Double(bottom) }
    func moved(_ dx: Int, _ dy: Int) -> IRect { IRect(x + dx, y + dy, w, h) }
}

final class Surface {
    let w: Int
    let h: Int
    var px: [UInt32]

    init(_ w: Int, _ h: Int, fill: Color = 0) {
        self.w = max(1, w)
        self.h = max(1, h)
        px = [UInt32](repeating: fill, count: self.w * self.h)
    }

    // ------------------------------------------------------------------ pixels
    @inline(__always) func put(_ x: Int, _ y: Int, _ c: Color) {
        if x < 0 || y < 0 || x >= w || y >= h { return }
        let a = c.ca
        if a == 255 { px[y * w + x] = c; return }
        if a == 0 { return }
        let i = y * w + x
        let d = px[i]
        let ia = 255 - a
        let oa = a + d.ca * ia / 255
        px[i] = rgba((c.cr * a + d.cr * ia) / 255, (c.cg * a + d.cg * ia) / 255, (c.cb * a + d.cb * ia) / 255, oa)
    }

    func fill(_ c: Color) {
        if c.ca == 255 {
            for i in 0 ..< px.count { px[i] = c }
        } else {
            fillRect(c, 0, 0, w, h)
        }
    }

    func fillRect(_ c: Color, _ x: Int, _ y: Int, _ rw: Int, _ rh: Int) {
        let x0 = max(0, x), y0 = max(0, y), x1 = min(w, x + rw), y1 = min(h, y + rh)
        if x0 >= x1 || y0 >= y1 { return }
        if c.ca == 255 {
            for yy in y0 ..< y1 {
                let base = yy * w
                for xx in x0 ..< x1 { px[base + xx] = c }
            }
        } else if c.ca > 0 {
            for yy in y0 ..< y1 { for xx in x0 ..< x1 { put(xx, yy, c) } }
        }
    }

    func fillRect(_ c: Color, _ r: IRect) { fillRect(c, r.x, r.y, r.w, r.h) }

    @inline(__always) func hline(_ c: Color, _ xa: Int, _ xb: Int, _ y: Int) {
        if y < 0 || y >= h { return }
        let x0 = max(0, min(xa, xb)), x1 = min(w - 1, max(xa, xb))
        if x0 > x1 { return }
        if c.ca == 255 {
            let base = y * w
            for xx in x0 ... x1 { px[base + xx] = c }
        } else {
            for xx in x0 ... x1 { put(xx, y, c) }
        }
    }

    // ------------------------------------------------------------------ shapes
    /// pygame.draw.circle: filled when width == 0, otherwise a ring of `width` pixels.
    func circle(_ c: Color, _ cx: Int, _ cy: Int, _ r: Int, width: Int = 0) {
        if r < 1 { put(cx, cy, c); return }
        let rr = r * r
        if width == 0 {
            for dy in -r ... r {
                let dx = Int(Double(rr - dy * dy).squareRoot())
                hline(c, cx - dx, cx + dx, cy + dy)
            }
            return
        }
        let inner = max(0, r - width)
        let ir = inner * inner
        for dy in -r ... r {
            for dx in -r ... r {
                let d = dx * dx + dy * dy
                if d <= rr && d > ir { put(cx + dx, cy + dy, c) }
            }
        }
    }

    /// pygame.draw.ellipse inside the bounding rect.
    func ellipse(_ c: Color, _ x: Int, _ y: Int, _ ew: Int, _ eh: Int, width: Int = 0) {
        if ew <= 0 || eh <= 0 { return }
        let a = Double(ew) / 2, b = Double(eh) / 2
        let cx = Double(x) + a, cy = Double(y) + b
        func span(_ yy: Int, _ aa: Double, _ bb: Double) -> (Int, Int)? {
            if aa <= 0 || bb <= 0 { return nil }
            let dy = (Double(yy) + 0.5 - cy) / bb
            if abs(dy) > 1 { return nil }
            let half = aa * (1 - dy * dy).squareRoot()
            let x0 = Int((cx - half).rounded()), x1 = Int((cx + half).rounded()) - 1
            return x1 >= x0 ? (x0, x1) : nil
        }
        for yy in y ..< (y + eh) {
            guard let (o0, o1) = span(yy, a, b) else { continue }
            if width == 0 { hline(c, o0, o1, yy); continue }
            if let (i0, i1) = span(yy, a - Double(width), b - Double(width)) {
                hline(c, o0, i0 - 1, yy)
                hline(c, i1 + 1, o1, yy)
            } else {
                hline(c, o0, o1, yy)
            }
        }
    }

    func line(_ c: Color, _ xa: Int, _ ya: Int, _ xb: Int, _ yb: Int, width: Int = 1) {
        var x0 = xa, y0 = ya
        let dx = abs(xb - xa), sx = xa < xb ? 1 : -1
        let dy = -abs(yb - ya), sy = ya < yb ? 1 : -1
        var err = dx + dy
        let half = (width - 1) / 2
        while true {
            if width <= 1 { put(x0, y0, c) } else { fillRect(c, x0 - half, y0 - half, width, width) }
            if x0 == xb && y0 == yb { break }
            let e2 = 2 * err
            if e2 >= dy { err += dy; x0 += sx }
            if e2 <= dx { err += dx; y0 += sy }
        }
    }

    func polygon(_ c: Color, _ pts: [(Double, Double)]) {
        guard pts.count >= 3 else { return }
        let ys = pts.map { $0.1 }
        let y0 = Int(ys.min()!.rounded(.down)), y1 = Int(ys.max()!.rounded(.up))
        for yy in y0 ... y1 {
            let sy = Double(yy) + 0.5
            var xs: [Double] = []
            for i in 0 ..< pts.count {
                let (ax, ay) = pts[i], (bx, by) = pts[(i + 1) % pts.count]
                if (ay <= sy && by > sy) || (by <= sy && ay > sy) {
                    xs.append(ax + (sy - ay) / (by - ay) * (bx - ax))
                }
            }
            xs.sort()
            var i = 0
            while i + 1 < xs.count {
                hline(c, Int(xs[i].rounded()), Int(xs[i + 1].rounded()) - 1, yy)
                i += 2
            }
        }
        // outline like pygame (edges are part of the shape)
        for i in 0 ..< pts.count {
            let (ax, ay) = pts[i], (bx, by) = pts[(i + 1) % pts.count]
            line(c, Int(ax), Int(ay), Int(bx), Int(by))
        }
    }

    private func inRound(_ x: Int, _ y: Int, _ r: IRect, _ rad: Int) -> Bool {
        if x < r.x || y < r.y || x >= r.right || y >= r.bottom { return false }
        if rad <= 0 { return true }
        let cx = x < r.x + rad ? r.x + rad : (x >= r.right - rad ? r.right - rad - 1 : x)
        let cy = y < r.y + rad ? r.y + rad : (y >= r.bottom - rad ? r.bottom - rad - 1 : y)
        let dx = x - cx, dy = y - cy
        return dx * dx + dy * dy <= rad * rad
    }

    /// pygame.draw.rect with optional border width and border_radius.
    func rect(_ c: Color, _ r: IRect, width: Int = 0, radius: Int = 0) {
        let rad = min(radius, min(r.w, r.h) / 2)
        if rad == 0 {
            if width == 0 { fillRect(c, r); return }
            fillRect(c, r.x, r.y, r.w, width)
            fillRect(c, r.x, r.bottom - width, r.w, width)
            fillRect(c, r.x, r.y, width, r.h)
            fillRect(c, r.right - width, r.y, width, r.h)
            return
        }
        let inner = IRect(r.x + width, r.y + width, r.w - 2 * width, r.h - 2 * width)
        let irad = max(0, rad - width)
        let y0 = max(0, r.y), y1 = min(h, r.bottom), x0 = max(0, r.x), x1 = min(w, r.right)
        if y0 >= y1 || x0 >= x1 { return } // fully off-screen (Swift ranges must not be reversed)
        for yy in y0 ..< y1 {
            for xx in x0 ..< x1 where inRound(xx, yy, r, rad) {
                if width == 0 || !inRound(xx, yy, inner, irad) { put(xx, yy, c) }
            }
        }
    }

    // ------------------------------------------------------------------ surfaces
    func blit(_ s: Surface, _ x: Int, _ y: Int, alpha: Int = 255) {
        let x0 = max(0, x), y0 = max(0, y), x1 = min(w, x + s.w), y1 = min(h, y + s.h)
        if x0 >= x1 || y0 >= y1 { return }
        for yy in y0 ..< y1 {
            let srow = (yy - y) * s.w - x
            for xx in x0 ..< x1 {
                let c = s.px[srow + xx]
                let a = c.ca
                if a == 0 { continue }
                if a == 255 && alpha == 255 { px[yy * w + xx] = c } else { put(xx, yy, c.alpha(a * alpha / 255)) }
            }
        }
    }

    func scaled(_ k: Int) -> Surface {
        let s = Surface(w * k, h * k)
        for y in 0 ..< s.h { for x in 0 ..< s.w { s.px[y * s.w + x] = px[(y / k) * w + x / k] } }
        return s
    }

    func flippedH() -> Surface {
        let s = Surface(w, h)
        for y in 0 ..< h { for x in 0 ..< w { s.px[y * w + x] = px[y * w + (w - 1 - x)] } }
        return s
    }

    func copy() -> Surface {
        let s = Surface(w, h)
        s.px = px
        return s
    }

    private static let colorSpace = CGColorSpaceCreateDeviceRGB()

    /// Opaque CGImage of the surface (alpha ignored) for display.
    func cgImage() -> CGImage? {
        let data = px.withUnsafeBufferPointer { Data(buffer: $0) }
        guard let provider = CGDataProvider(data: data as CFData) else { return nil }
        return CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: w * 4,
                       space: Surface.colorSpace,
                       bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipLast.rawValue),
                       provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)
    }
}

/// Small deterministic RNG (for star fields and other seeded decorations).
struct SeededRNG: RandomNumberGenerator {
    var state: UInt64
    init(_ seed: UInt64) { state = seed &* 0x9E37_79B9_7F4A_7C15 | 1 }
    mutating func next() -> UInt64 {
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return state
    }
}
