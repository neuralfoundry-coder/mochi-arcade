// Palette, pixel font, sprites and small effects (port of mochi_arcade/gfx.py).
import Foundation

let W = 320
let H = 200

enum Pal {
    static let colors: [String: Color] = {
        var d: [String: Color] = [:]
        for (k, v) in GData.palette { d[k] = rgba(v.0, v.1, v.2) }
        return d
    }()
}

@inline(__always) func col(_ name: String, _ alpha: Int = 255) -> Color {
    let c = Pal.colors[name] ?? rgba(255, 0, 255)
    return alpha == 255 ? c : c.alpha(alpha)
}

func lerpCol(_ a: String, _ b: String, _ t: Double) -> Color {
    let ca = col(a), cb = col(b)
    func l(_ x: Int, _ y: Int) -> Int { Int(Double(x) + Double(y - x) * t) }
    return rgba(l(ca.cr, cb.cr), l(ca.cg, cb.cg), l(ca.cb, cb.cb))
}

// ---------------------------------------------------------------------- text
func textWidth(_ s: String, _ scale: Int = 1) -> Int { s.isEmpty ? 0 : s.count * 6 * scale - scale }

private var textCache: [String: Surface] = [:]

func renderText(_ s: String, _ color: Color, _ scale: Int = 1) -> Surface {
    let key = "\(s)|\(color)|\(scale)"
    if let t = textCache[key] { return t }
    let up = s.uppercased()
    let surf = Surface(max(1, textWidth(up, scale)), 7 * scale)
    for (i, ch) in up.enumerated() {
        let g = GData.font[ch] ?? GData.font["?"]!
        for (y, row) in g.enumerated() {
            for (x, p) in row.enumerated() where p == "#" {
                surf.fillRect(color, (i * 6 + x) * scale, y * scale, scale, scale)
            }
        }
    }
    if textCache.count > 600 { textCache.removeAll() }
    textCache[key] = surf
    return surf
}

enum Align { case left, center, right }

@discardableResult
func drawText(_ dst: Surface, _ s: String, _ x: Int, _ y: Int, _ color: String = "white", scale: Int = 1,
              align: Align = .left, shadow: String? = "ink", outline: String? = nil) -> Int {
    drawTextC(dst, s, x, y, col(color), scale: scale, align: align, shadow: shadow, outline: outline)
}

@discardableResult
func drawTextC(_ dst: Surface, _ s: String, _ x0: Int, _ y: Int, _ color: Color, scale: Int = 1,
               align: Align = .left, shadow: String? = "ink", outline: String? = nil) -> Int {
    let w = textWidth(s.uppercased(), scale)
    var x = x0
    if align == .center { x -= w / 2 } else if align == .right { x -= w }
    if let o = outline {
        let os = renderText(s, col(o), scale)
        for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)] {
            dst.blit(os, x + dx * scale, y + dy * scale)
        }
    } else if let sh = shadow {
        dst.blit(renderText(s, col(sh), scale), x + scale, y + scale)
    }
    dst.blit(renderText(s, color, scale), x, y)
    return w
}

func drawWavy(_ dst: Surface, _ s: String, _ x0: Int, _ y: Int, _ t: Double, colorAt: (Int) -> String,
              scale: Int = 2, outline: String = "ink", amp: Double = 2) {
    let up = s.uppercased()
    let x = x0 - textWidth(up, scale) / 2
    for (i, ch) in up.enumerated() {
        let dy = Int(sin(t * 4 + Double(i) * 0.6) * amp)
        drawText(dst, String(ch), x + i * 6 * scale, y + dy, colorAt(i), scale: scale, shadow: nil, outline: outline)
    }
}

// ---------------------------------------------------------------------- sprites
private var spriteCache: [String: Surface] = [:]

func makeSprite(_ rows: [String], remap: [Character: Character]? = nil) -> Surface {
    let h = rows.count, w = rows.map { $0.count }.max() ?? 1
    let s = Surface(w, h)
    for (y, row) in rows.enumerated() {
        for (x, chRaw) in row.enumerated() {
            var ch = chRaw
            if let r = remap, let m = r[ch] { ch = m }
            if ch != ".", let name = GData.spriteChars[ch] { s.put(x, y, col(name)) }
        }
    }
    return s
}

func sprite(_ name: String, _ frame: Int = 0, flip: Bool = false, remap: [Character: Character]? = nil, scale: Int = 1) -> Surface {
    let rk = remap.map { $0.map { "\($0.key)\($0.value)" }.sorted().joined() } ?? ""
    let key = "\(name)|\(frame)|\(flip)|\(rk)|\(scale)"
    if let s = spriteCache[key] { return s }
    let frames = GData.art[name]!
    var s = makeSprite(frames[((frame % frames.count) + frames.count) % frames.count], remap: remap)
    if flip { s = s.flippedH() }
    if scale != 1 { s = s.scaled(scale) }
    spriteCache[key] = s
    return s
}

// ---------------------------------------------------------------------- helpers
func panel(_ dst: Surface, _ r: IRect, fill: String = "ink", border: String = "lavender", radius: Int = 4, shadow: Bool = true) {
    if shadow { dst.rect(col("black"), r.moved(2, 2), radius: radius) }
    dst.rect(col(fill), r, radius: radius)
    dst.rect(col(border), r, width: 1, radius: radius)
}

func bubble(_ dst: Surface, _ cx: Double, _ cy: Double, _ r: Int, _ t: Double, tint: String = "sky") {
    let x = Int(cx), y = Int(cy)
    dst.circle(col(tint, 60), x, y, r)
    dst.circle(col(tint, 230), x, y, r, width: 1)
    let hx = x - Int(Double(r) * 0.45) + Int(sin(t * 3))
    let hy = y - Int(Double(r) * 0.45)
    dst.circle(col("white", 230), hx, hy, max(1, r / 4))
    dst.circle(col("white", 140), x + r / 3, y + r / 3, max(1, r / 7))
}

func checkerBg(_ dst: Surface, _ t: Double, _ a: String = "night", _ b: String = "ink", size: Int = 16, speed: Double = 8) {
    dst.fill(col(a))
    let off = Int(t * speed) % (size * 2)
    let cb = col(b)
    var y = -size * 2
    while y < H + size * 2 {
        var x = -size * 2
        while x < W + size * 2 {
            if ((x + y) / size) % 2 == 0 { dst.fillRect(cb, x + off, y + off / 2, size, size) }
            x += size
        }
        y += size
    }
}

func scanlines(_ dst: Surface) {
    let c = rgba(0, 0, 0, 40)
    var y = 0
    while y < H { dst.fillRect(c, 0, y, W, 1); y += 2 }
}

final class Stars {
    var s: [(Double, Double, Int)] = []
    init(_ n: Int = 70, seed: UInt64 = 3) {
        var rng = SeededRNG(seed)
        for _ in 0 ..< n {
            s.append((Double.random(in: 0 ..< Double(W), using: &rng), Double.random(in: 0 ..< Double(H), using: &rng),
                      [1, 1, 1, 2, 3].randomElement(using: &rng)!))
        }
    }

    func update(_ dt: Double, _ speed: Double = 20) {
        for i in s.indices {
            s[i].1 += speed * Double(s[i].2) * dt
            if s[i].1 > Double(H) { s[i].1 -= Double(H); s[i].0 = Double.random(in: 0 ..< Double(W)) }
        }
    }

    func draw(_ dst: Surface, _ t: Double = 0) {
        for (x, y, z) in s {
            var c = ["darkgray", "lavender", "white"][z - 1]
            if z == 3 && Int(t * 6 + x) % 7 == 0 { c = "yellow" }
            dst.fillRect(col(c), Int(x), Int(y), 1, z < 3 ? 1 : 2)
        }
    }
}

final class Particles {
    struct P { var x, y, vx, vy, life, full: Double; var c: String; var grav: Double; var size: Int }
    var p: [P] = []

    func burst(_ x: Double, _ y: Double, _ n: Int = 10, _ colors: [String] = ["white", "pink", "yellow"],
               _ speed: Double = 60, _ life: Double = 0.6, grav: Double = 80, size: Int = 1) {
        for _ in 0 ..< n {
            let a = Double.random(in: 0 ..< 2 * .pi), v = Double.random(in: speed * 0.4 ... speed)
            p.append(P(x: x, y: y, vx: cos(a) * v, vy: sin(a) * v - speed * 0.3, life: life, full: life,
                       c: colors.randomElement()!, grav: grav, size: size))
        }
    }

    func sparkle(_ x: Double, _ y: Double, _ c: String = "yellow") {
        p.append(P(x: x, y: y, vx: Double.random(in: -10 ... 10), vy: Double.random(in: -30 ... -10), life: 0.5, full: 0.5,
                   c: c, grav: 0, size: 1))
    }

    func update(_ dt: Double) {
        for i in p.indices {
            p[i].x += p[i].vx * dt; p[i].y += p[i].vy * dt; p[i].vy += p[i].grav * dt; p[i].life -= dt
        }
        p.removeAll { $0.life <= 0 }
    }

    func draw(_ dst: Surface) {
        for q in p {
            if q.life < q.full * 0.3 && Int(q.life * 30) % 2 == 1 { continue }
            dst.fillRect(col(q.c), Int(q.x), Int(q.y), q.size, q.size)
        }
    }
}

final class FloatText {
    struct Item { var x, y: Double; var s: String; var c: String; var life: Double }
    var items: [Item] = []
    func add(_ x: Double, _ y: Double, _ s: String, _ c: String = "yellow") { items.append(Item(x: x, y: y, s: s, c: c, life: 0.9)) }
    func update(_ dt: Double) {
        for i in items.indices { items[i].y -= 18 * dt; items[i].life -= dt }
        items.removeAll { $0.life <= 0 }
    }
    func draw(_ dst: Surface) { for it in items { drawText(dst, it.s, Int(it.x), Int(it.y), it.c, align: .center) } }
}
