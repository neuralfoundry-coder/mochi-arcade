// PAW PINBALL art (port of games/paw_pinball_art.py): Kiki, her paws, cat bumpers, fish targets, the nap bed,
// the cat tower and the table backgrounds. Sprites and songs come from the Python export (GeneratedData).
import Foundation

let PP_KITTEN_COATS: [[Character: Character]] = [["g": "o"], ["g": "g"], ["g": "c"], ["g": "e"], ["g": "w"], ["g": "n"]]

enum PPArt {
    private static func ip(_ v: Double) -> Int { Int(v) }

    // ------------------------------------------------------------------ table background
    static func makeBg(_ tb: PPTable, _ theme: PPTheme) -> Surface {
        let s = Surface(W, H, fill: col("black"))
        let wall = theme.wall
        s.fillRect(col(theme.a), PP_TX0, 0, PP_TX1 - PP_TX0, H)
        let cb = col(theme.b)
        let x0 = Int(PP_LW), x1 = Int(PP_RW)
        switch theme.pat {
        case 0:
            for y in stride(from: 0, to: H, by: 10) {
                for x in stride(from: x0, to: x1, by: 10) where (x / 10 + y / 10) % 2 == 1 { s.fillRect(cb, x, y, 10, 10) }
            }
        case 1:
            for k in stride(from: -H, to: W, by: 14) {
                for i in 0 ..< 4 { s.line(cb, k + i, H, k + i + H, 0) }
            }
        case 2:
            for y in stride(from: 6, to: H, by: 12) {
                for x in stride(from: x0 + 4 + ((y / 12) % 2 == 1 ? 6 : 0), to: x1, by: 12) { s.circle(cb, x, y, 2) }
            }
        case 3:
            for y in stride(from: 4, to: H, by: 10) {
                for x in stride(from: x0, to: x1, by: 2) { s.fillRect(cb, x, y + Int(sin(Double(x) * 0.25) * 2), 2, 1) }
            }
        default:
            for y in stride(from: 8, to: H, by: 18) {
                for x in stride(from: x0 + 6 + ((y / 18) % 2 == 1 ? 9 : 0), to: x1, by: 18) {
                    s.circle(cb, x, y + 2, 2)
                    for (dx, dy) in [(-3, -2), (-1, -4), (1, -4), (3, -2)] { s.fillRect(cb, x + dx, y + dy, 1, 1) }
                }
            }
        }
        deco(s, theme.deco, theme)
        // outside the arch and the outer walls: frame colour
        let fr = col("black")
        for x in Int(PP_LW) ... Int(PP_LANE_OUT) { s.fillRect(fr, x, 0, 1, Int(ppArchY(Double(x)))) }
        s.fillRect(fr, PP_TX0, 0, Int(PP_LW) - PP_TX0, H)
        s.fillRect(fr, Int(PP_LANE_OUT) + 1, 0, PP_TX1 - Int(PP_LANE_OUT) - 1, H)
        // aprons below the inlane guides, slingshot bodies
        let g = PPData.guide, sl = PPData.sling
        for side in [1.0, -1.0] {
            func X(_ x: Double) -> Double { side == 1 ? x : PP_MIRROR - x }
            let (gx1, gy1) = g[0], (gx2, gy2) = g[1]
            s.polygon(col("black"), [(X(gx1), gy1), (X(gx2), gy2), (X(gx2), Double(H)), (X(gx1), Double(H))])
            s.polygon(col("ink"), [(X(gx1 + 3), gy1 + 6), (X(gx2 - 4), gy2 + 4), (X(gx2 - 4), Double(H)), (X(gx1 + 3), Double(H))])
            let (ax, ay) = sl[0], (bx, by) = sl[1], (qx, qy) = sl[2]
            s.polygon(col(theme.accent), [(X(ax), ay), (X(bx), by), (X(qx), qy)])
            s.polygon(col("white"), [(X(ax + 2), ay + 6), (X(bx + 2), by - 2), (X(qx - 6), qy - 7)])
        }
        drawTower(s, theme)
        for w in tb.walls where Int(w[4]) != PP_GATE {
            let k = Int(w[4])
            let c = k == PP_METAL ? wall : "white"
            s.line(col(c), ip(w[0]), ip(w[1]), ip(w[2]), ip(w[3]), width: 2)
        }
        // plunger lane
        s.fillRect(col("black"), Int(PP_RW) + 1, Int(PP_GATE_Y), Int(PP_LANE_OUT - PP_RW) - 1, H - Int(PP_GATE_Y))
        for y in stride(from: Int(PP_GATE_Y) + 4, to: Int(PP_PLUNGE_Y) - 4, by: 8) { s.fillRect(col("darkgray"), Int(PP_LANE_X), y, 1, 3) }
        for p in tb.posts {
            s.circle(col("black"), ip(p[0]), ip(p[1]), ip(p[2]) + 1)
            s.circle(col("white"), ip(p[0]), ip(p[1]), ip(p[2]))
        }
        // side panels
        s.fillRect(col("ink"), 0, 0, PP_TX0 - 2, H)
        s.fillRect(col("ink"), PP_TX1 + 2, 0, W - PP_TX1 - 2, H)
        s.fillRect(col(wall), PP_TX0 - 2, 0, 1, H)
        s.fillRect(col(wall), PP_TX1 + 1, 0, 1, H)
        return s
    }

    /// Kiki's cat tower: a sisal scratching post with cushioned platforms in the top-left corner.
    static func drawTower(_ s: Surface, _ theme: PPTheme) {
        let tw = PPData.tower
        guard tw.count == 5 else { return }
        let poly: [(Double, Double)] = [(PP_LW, 30), (PP_LW, tw[0].1), tw[1], tw[2], tw[3], tw[4], (PP_LW, tw[4].1)]
        s.polygon(col("choco"), poly)
        for y in stride(from: 22, to: Int(tw[0].1), by: 3) {
            let yd = Double(y)
            let xr = y < 92 ? 97.0 : (y < 100 ? 96 - (yd - 92) * 0.75 : 90 - (yd - 100) * 3)
            s.line(col(y % 2 == 1 ? "peach" : "brown"), Int(PP_LW) + 2, y, Int(xr) - 2, y + 1)
        }
        for py in [34, 56] {
            s.rect(col(theme.accent), IRect(Int(PP_LW) + 1, py, 24, 5), radius: 2)
            s.fillRect(col("white"), Int(PP_LW) + 3, py + 1, 18, 1)
        }
    }

    /// A faint motif per theme, under everything.
    static func deco(_ s: Surface, _ kind: Int, _ theme: PPTheme) {
        let c = col(theme.b)
        switch kind {
        case 1:
            s.circle(c, 196, 140, 18, width: 2)
            for i in stride(from: -12, through: 12, by: 6) { s.line(c, 196 + i, 124, 196 - i, 156) }
        case 2:
            s.rect(c, IRect(128, 112, 54, 40), width: 2)
            s.fillRect(c, 154, 112, 2, 40)
            s.fillRect(c, 128, 131, 54, 2)
        case 3:
            for x0 in [120, 176] {
                s.fillRect(c, x0, 140, 20, 2)
                for i in 0 ..< 4 { s.line(c, x0 + 3 + i * 4, 136, x0 + 3 + i * 4, 146) }
                s.polygon(c, [(Double(x0 + 20), 141), (Double(x0 + 26), 136), (Double(x0 + 26), 146)])
            }
        case 4:
            s.rect(c, IRect(130, 124, 22, 18), width: 2)
            s.rect(c, IRect(160, 116, 26, 26), width: 2)
        case 5:
            s.circle(c, 200, 132, 12)
            s.circle(col(theme.a), 205, 128, 10)
            for (x, y) in [(120, 120), (140, 150), (180, 158), (112, 100)] {
                s.fillRect(c, x, y - 1, 1, 3)
                s.fillRect(c, x - 1, y, 3, 1)
            }
        default:
            s.circle(c, 155, 140, 9)
            for (dx, dy) in [(-11, -9), (-4, -15), (4, -15), (11, -9)] { s.circle(c, 155 + dx, 140 + dy, 3) }
        }
    }

    // ------------------------------------------------------------------ live pieces
    /// Cat-face pop bumper (radius 9).
    static func bumper(_ s: Surface, _ xd: Double, _ yd: Double, _ color: String, _ flash: Double, _ t: Double, _ i: Int = 0) {
        let x = Int(xd), y = Int(yd)
        let lit = flash > 0
        let body = col(lit ? "white" : color)
        s.circle(col("black"), x, y + 1, 10)
        for side in [-1, 1] {
            let sd = Double(side), xx = Double(x), yy = Double(y)
            s.polygon(col("black"), [(xx + sd * 9, yy - 2), (xx + sd * 8, yy - 13), (xx + sd * 1, yy - 7)])
            s.polygon(body, [(xx + sd * 7, yy - 3), (xx + sd * 7, yy - 10), (xx + sd * 2, yy - 7)])
            s.polygon(col("pink"), [(xx + sd * 6, yy - 5), (xx + sd * 6, yy - 8), (xx + sd * 4, yy - 7)])
        }
        s.circle(body, x, y, 9)
        s.circle(col(lit ? "yellow" : "cream"), x, y + 3, 5)
        let k = col("black")
        if lit {
            for side in [-1, 1] {
                let ex = x + side * 4
                s.fillRect(k, ex + side, y - 3, 1, 1)
                s.fillRect(k, ex, y - 2, 1, 1)
                s.fillRect(k, ex + side, y - 1, 1, 1)
            }
        } else {
            let blink = Int(t * 1.3 + Double(i) * 1.7) % 6 == 0
            for side in [-1, 1] {
                let ex = x + side * 4
                if blink {
                    s.fillRect(k, ex - 1, y - 2, 3, 1)
                } else {
                    s.fillRect(k, ex - 1, y - 3, 2, 3)
                    s.fillRect(col("white"), ex - 1, y - 3, 1, 1)
                }
            }
        }
        s.fillRect(col("hotpink"), x - 1, y + 1, 3, 1)
        s.fillRect(k, x - 1, y + 3, 1, 1)
        s.fillRect(k, x + 1, y + 3, 1, 1)
        s.fillRect(k, x, y + 2, 1, 1)
        for side in [-1, 1] { s.fillRect(k, x + side * 6 - (side < 0 ? 2 : 0), y + 2, 3, 1) }
    }

    /// Drop target.
    static func fish(_ s: Surface, _ f: PPFish, _ t: Double) {
        if f.down > 0 {
            if f.x1 == f.x2 {
                s.fillRect(col("black"), Int(f.x1) - 1, Int(f.y1), 3, Int(f.y2 - f.y1) + 1)
            } else {
                s.fillRect(col("black"), Int(f.x1), Int(f.y1) - 1, Int(f.x2 - f.x1) + 1, 3)
            }
            return
        }
        if f.x1 == f.x2 {
            s.blit(sprite("pp_fish_v"), Int(f.x1) - 2, Int((f.y1 + f.y2) / 2) - 5)
        } else {
            s.blit(sprite("pp_fish"), Int((f.x1 + f.x2) / 2) - 5, Int(f.y1) - 2)
        }
    }

    /// Kiki's nap bed: a round cushion.
    static func saucer(_ s: Surface, _ xd: Double, _ yd: Double, _ t: Double, busy: Bool, lit: Bool) {
        let x = Int(xd), y = Int(yd)
        s.ellipse(col("black"), x - 9, y - 5, 18, 11)
        s.ellipse(col(lit && Int(t * 6) % 2 == 1 ? "hotpink" : "lavender"), x - 8, y - 4, 16, 9)
        s.ellipse(col("purple"), x - 5, y - 2, 10, 5)
        s.fillRect(col("white"), x - 6, y - 3, 3, 1)
        if busy {
            for i in 0 ..< 2 {
                let zz = (t * 0.8 + Double(i) * 0.5).truncatingRemainder(dividingBy: 1)
                drawText(s, "Z", x + 4 + Int(zz * 6), y - 8 - Int(zz * 10), i == 1 ? "white" : "sky", shadow: nil)
            }
        }
    }

    /// Yarn spool across a lane: the wool rolls round while it spins.
    static func spinner(_ s: Surface, _ sp: [Double], _ angle: Double, _ t: Double) {
        let x1 = Int(sp[0]), y = Int(sp[1]), x2 = Int(sp[2])
        let w = x2 - x1 + 1
        s.fillRect(col("black"), x1 - 3, y - 5, w + 6, 11)
        for j in 0 ..< 7 {
            let c = ["hotpink", "pink", "white"][(j + Int(angle * 6)) % 3]
            s.fillRect(col(c), x1, y - 3 + j, w, 1)
        }
        for fx in [x1 - 2, x2 + 1] {
            s.fillRect(col("brown"), fx, y - 4, 2, 9)
            s.fillRect(col("peach"), fx, y - 4, 1, 9)
        }
    }

    static func laneLetter(_ s: Surface, _ i: Int, _ x: Double, _ lit: Bool, _ t: Double, skill: Bool) {
        let ch = String(Array("MEOW")[i])
        var c = lit ? "yellow" : (skill && Int(t * 8) % 2 == 1 ? "orange" : "darkgray")
        if lit && Int(t * 3 + Double(i)) % 4 == 0 { c = "white" }
        drawText(s, ch, Int(x) - 2, 29, c, shadow: "black")
    }

    static func ball(_ s: Surface, _ b: PPBall, _ t: Double, fever: Bool) {
        let x = Int(b.x.rounded()), y = Int(b.y.rounded())
        if fever {
            for (i, p) in b.trail.suffix(4).enumerated() { s.circle(col(rainbow(i, t)), Int(p.0), Int(p.1), 2) }
        } else if b.trail.count > 2 && abs(b.vx) + abs(b.vy) > 330 {
            let n = b.trail.count
            for p in b.trail[max(0, n - 3) ..< n - 1] { s.fillRect(col("gray"), Int(p.0), Int(p.1), 1, 1) }
        }
        let sp = b.kind == "kitten" ? sprite("pp_kball", remap: PP_KITTEN_COATS[b.coat % PP_KITTEN_COATS.count]) : sprite("pp_bell")
        s.blit(sp, x - 3, y - 3)
    }

    /// Elevated ramp: two rails with ties along the path, a glowing mouth.
    static func ramp(_ s: Surface, _ r: PPRamp, _ lens: [Double], _ t: Double, _ color: String, lit: Bool) {
        let path = r.path
        for i in 0 ..< path.count - 1 {
            let (x1, y1) = path[i], (x2, y2) = path[i + 1]
            let dx = x2 - x1, dy = y2 - y1
            var L = hypot(dx, dy)
            if L == 0 { L = 1 }
            let nx = -dy / L * 4, ny = dx / L * 4
            for sgn in [-1.0, 1.0] {
                s.line(col("black"), ip(x1 + nx * sgn), ip(y1 + ny * sgn + 1), ip(x2 + nx * sgn), ip(y2 + ny * sgn + 1))
                s.line(col(color), ip(x1 + nx * sgn), ip(y1 + ny * sgn), ip(x2 + nx * sgn), ip(y2 + ny * sgn))
            }
        }
        var d = 0.0
        let total = lens[lens.count - 1]
        while d < total {
            var i = 0
            while i < lens.count - 2 && lens[i + 1] < d { i += 1 }
            let (x1, y1) = path[i], (x2, y2) = path[i + 1]
            let L = max(0.001, lens[i + 1] - lens[i])
            let u = (d - lens[i]) / L
            let x = x1 + (x2 - x1) * u, y = y1 + (y2 - y1) * u
            let nx = -(y2 - y1) / L * 3, ny = (x2 - x1) / L * 3
            s.line(col("white"), ip(x - nx), ip(y - ny), ip(x + nx), ip(y + ny))
            d += 7
        }
        let g = r.gate
        let c = lit && Int(t * 6) % 2 == 1 ? "yellow" : color
        s.line(col(c), ip(g[0]), ip(g[1]), ip(g[2]), ip(g[3]), width: 2)
        if lit {
            let mx = (g[0] + g[2]) / 2, my = (g[1] + g[3]) / 2
            let (dx, dy) = r.dir
            let k = 6 + Double(Int(abs(sin(t * 6)) * 3))
            let tipx = mx - dx * k, tipy = my - dy * k
            s.polygon(col("yellow"), [(tipx, tipy), (tipx - dx * 5 - dy * 3, tipy - dy * 5 + dx * 3),
                                      (tipx - dx * 5 + dy * 3, tipy - dy * 5 - dx * 3)])
        }
    }

    /// Kiki's paw: a black furry arm with a white sock and pink toe beans at the tip.
    static func flipper(_ s: Surface, _ f: PPFlipper, _ t: Double, fever: Bool) {
        let (tx, ty) = f.tip()
        let px = f.px, py = f.py
        let stun = f.stun > 0
        let arm = col(stun ? "darkgray" : "black"), sock = col(stun ? "gray" : "white")
        for i in 0 ..< 7 {
            let u = Double(i) / 6
            let x = px + (tx - px) * u, y = py + (ty - py) * u
            let r = 3.6 + (2.2 - 3.6) * u
            s.circle(col("black"), Int(x.rounded()), Int(y.rounded()), Int(r.rounded()) + 1)
        }
        for i in 0 ..< 7 {
            let u = Double(i) / 6
            let x = px + (tx - px) * u, y = py + (ty - py) * u
            let r = 3.6 + (2.2 - 3.6) * u
            var c = u < 0.45 ? arm : sock
            if fever && u >= 0.45 { c = col(rainbow(i, t)) }
            s.circle(c, Int(x.rounded()), Int(y.rounded()), max(1, Int(r.rounded())))
        }
        let dx = (tx - px) / f.len, dy = (ty - py) / f.len
        let nx = -dy * f.side, ny = dx * f.side
        for k in [0.72, 0.86] {
            let bx = px + (tx - px) * k + nx * 1.5, by = py + (ty - py) * k + ny * 1.5
            s.fillRect(col("pink"), Int(bx.rounded()), Int(by.rounded()), 1, 1)
        }
        s.fillRect(col("hotpink"), Int((tx - dx + nx).rounded()), Int((ty - dy + ny).rounded()), 1, 1)
        s.circle(col("darkgray"), Int(px), Int(py), 1)
        if stun {
            for i in 0 ..< 3 {
                let a = t * 8 + Double(i) * 2.1
                s.fillRect(col("yellow"), Int((px + tx) / 2 + cos(a) * 6), Int((py + ty) / 2 - 5 + sin(a) * 2), 1, 1)
            }
        }
    }

    /// A lost kitten waiting to be rescued (centre x, y).
    static func kitten(_ s: Surface, _ x: Double, _ y: Double, _ coat: Int, _ t: Double, golden: Bool = false) {
        let remap: [Character: Character] = golden ? ["g": "y", "k": "o"] : PP_KITTEN_COATS[coat % PP_KITTEN_COATS.count]
        let fr = Int(t * 1.5 + Double(coat)) % 7 == 0 ? 1 : 0
        let bob = Int(abs(sin(t * 3 + Double(coat))) * 1.5)
        s.blit(sprite("pp_kitten", fr, remap: remap), Int(x) - 4, Int(y) - 5 - bob)
        if golden && Int(t * 8) % 2 == 1 { s.fillRect(col("white"), Int(x) + 4, Int(y) - 6, 1, 1) }
    }

    static func coinFish(_ s: Surface, _ x: Double, _ y: Double, _ t: Double, rainbowFish: Bool) {
        let w = max(1, Int(abs(cos(t * 4 + x * 0.1)) * 5))
        let xi = Int(x), yi = Int(y)
        if rainbowFish {
            s.ellipse(col(rainbow(0, t)), xi - w, yi - 3, w * 2 + 1, 7)
            s.ellipse(col(rainbow(3, t)), xi - max(1, w - 1), yi - 2, max(1, w * 2 - 1), 5)
            return
        }
        s.ellipse(col("orange"), xi - w, yi - 3, w * 2 + 1, 7)
        s.ellipse(col("yellow"), xi - w + 1, yi - 2, max(1, w * 2 - 1), 5)
        if w > 2 { s.fillRect(col("black"), xi - w + 2, yi - 1, 1, 1) }
    }

    // ------------------------------------------------------------------ Kiki
    /// Kiki the tuxedo cat, head and bib. mood: idle happy wow worried sad sleepy angry hurt.
    static func kiki(_ s: Surface, _ cx: Int, _ cy: Int, _ mood: String, _ t: Double, _ lx: Double = 0, _ ly: Double = 0,
                     blink: Bool = false) {
        let k = col("black"), w = col("white")
        let earDrop = mood == "sad" || mood == "hurt" ? 3 : 0
        let twitch = mood == "idle" && Int(t * 2) % 9 == 0 ? 1 : 0
        let X = Double(cx), Y = Double(cy)
        s.ellipse(k, cx - 17, cy + 8, 34, 18)
        s.ellipse(w, cx - 9, cy + 9, 18, 16)
        for side in [-1, 1] {
            let sd = Double(side)
            let tip = (X + sd * 13, Y - 19 + Double(earDrop + (side > 0 ? twitch : 0)))
            s.polygon(col("darkgray"), [(X + sd * 16, Y - 4), tip, (X + sd * 4, Y - 13)])
            s.polygon(k, [(X + sd * 15, Y - 5), (tip.0, tip.1 + 1), (X + sd * 5, Y - 12)])
            s.polygon(col("pink"), [(X + sd * 13, Y - 8), (tip.0, tip.1 + 5), (X + sd * 7, Y - 11)])
        }
        s.ellipse(col("darkgray"), cx - 17, cy - 15, 34, 28)
        s.ellipse(k, cx - 16, cy - 14, 32, 26)
        s.polygon(w, [(X - 1, Y - 12), (X + 1, Y - 12), (X + 4, Y), (X - 4, Y)])
        s.ellipse(w, cx - 9, cy - 1, 18, 12)
        for side in [-1, 1] {
            let ex = cx + side * 7, ey = cy - 4
            if mood == "happy" {
                for i in 0 ..< 5 { s.fillRect(w, ex - 2 + i, ey - ([1, 2, 3].contains(i) ? 1 : 0) + (i == 2 ? 1 : 0) - 1, 1, 1) }
                continue
            }
            if mood == "sleepy" || blink { s.fillRect(col("lime"), ex - 3, ey, 7, 1); continue }
            if mood == "hurt" {
                for i in 0 ..< 5 {
                    s.fillRect(w, ex - 2 + i, ey - 2 + i, 1, 1)
                    s.fillRect(w, ex + 2 - i, ey - 2 + i, 1, 1)
                }
                continue
            }
            s.ellipse(col("lime"), ex - 3, ey - 3, 7, 7)
            s.ellipse(col("yellow"), ex - 2, ey - 1, 5, 4)
            let px = ex + Int((lx * 1.5).rounded()), py = ey + Int((ly * 1.5).rounded())
            if mood == "wow" || mood == "worried" {
                s.circle(k, px, py, 2)
            } else {
                s.fillRect(k, px, py - 2, 1, 5)
                s.fillRect(k, px - 1, py - 1, 3, 3)
            }
            s.fillRect(w, px + 1, py - 2, 1, 1)
            if mood == "sad" {
                s.fillRect(k, ex - 3, ey - 3, 7, 3)
                s.fillRect(col("sky"), ex + side, ey + 4 + Int(t * 6) % 3, 1, 2)
            }
            if mood == "angry" {
                let inner = Double(ex - side * 4), outer = Double(ex + side * 4), eyd = Double(ey)
                s.polygon(k, [(outer, eyd - 4), (inner, eyd - 4), (inner, eyd - 1)])
                s.line(w, Int(outer), ey - 4, Int(inner), ey - 1)
            }
        }
        s.polygon(col("hotpink"), [(X - 2, Y + 2), (X + 2, Y + 2), (X, Y + 4)])
        if mood == "happy" || mood == "wow" {
            s.ellipse(col("hotpink"), cx - 2, cy + 5, 5, 4)
            s.fillRect(k, cx - 1, cy + 5, 3, 1)
        } else if mood == "worried" || mood == "hurt" {
            s.circle(k, cx, cy + 7, 1)
        } else {
            s.fillRect(k, cx - 3, cy + 6, 2, 1)
            s.fillRect(k, cx, cy + 5, 1, 1)
            s.fillRect(k, cx + 2, cy + 6, 2, 1)
        }
        for side in [-1, 1] {
            for (dy, dy2) in [(3, 1), (5, 6)] { s.line(col("white"), cx + side * 9, cy + dy, cx + side * 19, cy + dy2) }
        }
        if mood == "happy" || mood == "wow" { Cute.blush(s, cx, cy + 2, 8) }
        if mood == "worried" {
            s.fillRect(col("sky"), cx + 15, cy - 9, 2, 3)
            s.fillRect(col("sky"), cx + 16, cy - 10, 1, 1)
        }
        if mood == "sleepy" {
            for i in 0 ..< 2 {
                let zz = (t * 0.7 + Double(i) * 0.5).truncatingRemainder(dividingBy: 1)
                drawText(s, "Z", cx + 12 + Int(zz * 6), cy - 14 - Int(zz * 10), "white", shadow: nil)
            }
        }
    }
}
