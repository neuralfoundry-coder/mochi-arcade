// COMET KITTY art (port of mochi_arcade/games/comet_kitty_art.py): procedurally drawn space critters,
// bosses, backdrops, capsules and upgrade icons. All original designs.
import Foundation

/// Python-style floor division (Swift `/` truncates toward zero).
@inline(__always) func ckFdiv(_ a: Int, _ b: Int) -> Int { Int((Double(a) / Double(b)).rounded(.down)) }
@inline(__always) private func P(_ x: Int, _ y: Int) -> (Double, Double) { (Double(x), Double(y)) }

enum CKArt {
    static let sizes: [(Int, Int)] = [(12, 12), (12, 12), (16, 14), (12, 14), (12, 12), (14, 12), (14, 14), (12, 12), (14, 14),
                                      (12, 12), (8, 8), (8, 8), (12, 12), (14, 10)]
    static let kindColors: [[String]] = [["sky", "white", "blue"], ["pink", "hotpink", "white"], ["purple", "yellow", "white"],
                                         ["orange", "peach", "red"], ["lime", "mint", "white"], ["mint", "teal", "white"],
                                         ["teal", "sky", "white"], ["yellow", "orange", "red"], ["purple", "lavender", "white"],
                                         ["lavender", "white", "sky"], ["pink", "white", "sky"], ["gray", "red", "yellow"],
                                         ["brown", "peach", "choco"], ["yellow", "orange", "white"]]

    static func rgb(_ c: CKRGB, _ a: Int = 255) -> Color { rgba(c.0, c.1, c.2, a) }
    static func dark(_ c: CKRGB, _ f: Double) -> CKRGB { (Int(Double(c.0) * f), Int(Double(c.1) * f), Int(Double(c.2) * f)) }

    // ------------------------------------------------------------------ backdrop
    /// Planet disc lit from the upper left: the lower-right rim falls into shade (stripe: banded giant).
    static func disc(_ s: Surface, _ x: Int, _ y: Int, _ r: Int, _ c: CKRGB, _ stripe: CKRGB? = nil) {
        for dy in -r ... r {
            let hw = Int(Double(max(0, r * r - dy * dy)).squareRoot())
            let cc = (stripe == nil || ((dy + r) / 5) % 2 == 0) ? c : stripe!
            s.fillRect(rgb(cc), x - hw, y + dy, hw * 2 + 1, 1)
            let sx = x + Int(Double(hw) * 0.35) - ckFdiv(dy, 3)
            if sx < x + hw { s.fillRect(rgb(dark(cc, 0.62)), sx, y + dy, x + hw - sx + 1, 1) }
        }
    }

    static func ring(_ s: Surface, _ x: Int, _ y: Int, _ a: Int, _ b: Int, _ c: Color, _ front: Bool) {
        for i in stride(from: 0, to: 180, by: 3) {
            let ang = Double(front ? i : i + 180) * .pi / 180
            s.fillRect(c, x + Int(cos(ang) * Double(a)), y + Int(sin(ang) * Double(b)), 2, 1)
        }
    }

    static func backdrop(_ th: CKTheme) -> Surface {
        let s = Surface(W, H)
        for i in 0 ..< 25 {
            let f = Double(i) / 24
            func m(_ a: Int, _ b: Int) -> Int { Int(Double(a) + Double(b - a) * f) }
            s.fillRect(rgba(m(th.top.0, th.bot.0), m(th.top.1, th.bot.1), m(th.top.2, th.bot.2)), 0, i * 8, W, 8)
        }
        for (x, y, r, c, a) in th.neb {
            for i in 0 ..< 5 { s.circle(rgb(c, a / 3), x, y, r * (5 - i) / 5) }   // soft glow: stacked faint discs
        }
        let p = th.planet
        let x = p.x, y = p.y, r = p.r, c1 = p.c1, c2 = p.c2
        for (rx, ry, rr) in th.rocks {
            s.circle(rgb(dark(c1, 0.8)), rx, ry, rr)
            s.fillRect(rgb(c2), rx - 1, ry - rr, 1, 1)
        }
        switch p.kind {
        case 1:
            s.circle(rgb(c1, 30), x, y, r + 5)
            disc(s, x, y, r, c1)
            for (dx, dy, rr) in [(ckFdiv(-r, 3), ckFdiv(-r, 4), r / 4), (r / 4, r / 5, r / 5), (ckFdiv(-r, 6), r / 2, r / 6),
                                 (r / 5, ckFdiv(-r, 2), r / 7 + 1)] {
                s.circle(rgb(dark(c1, 0.8)), x + dx, y + dy, max(1, rr))
            }
        case 2:
            ring(s, x, y, r * 19 / 10, r * 9 / 20, rgb(c2), false)
            disc(s, x, y, r, c1)
            ring(s, x, y, r * 19 / 10, r * 9 / 20, rgb(c2), true)
        case 3:
            disc(s, x, y, r, c1, c2)
        case 4:
            disc(s, x, y, r, c1)
            disc(s, x + r + 10, y + r / 2 + 6, r / 2, c2)
        case 5:
            s.circle(rgb(c1, 26), x, y, r * 12 / 5)
            s.circle(rgb(c1, 40), x, y, r * 8 / 5)
            s.circle(rgb(c1), x, y, r)
            s.circle(rgb(c2), x, y, r * 7 / 10)
        default: break
        }
        return s
    }

    // ------------------------------------------------------------------ enemies
    /// Draw an enemy centred at (x, y). glow: about to fire, faded: wisp out of phase, d: gold comet heading.
    static func enemy(_ s: Surface, _ kind: Int, _ x: Int, _ y: Int, _ t: Double, hit: Bool = false, glow: Bool = false,
                      faded: Bool = false, hp: Int = 1, d: Int = 1) {
        let k = col("black")
        switch kind {
        case CK_JELLY, CK_MOTH, CK_PUFF:
            let (w, h) = sizes[kind]
            Cute.spaceJelly(s, x - w / 2, y - h / 2, t, kind, hit: hit)
        case CK_DART:
            let body = col(hit ? "white" : "orange")
            s.polygon(col("peach"), [P(x - 6, y - 2), P(x - 2, y - 7), P(x - 2, y)])
            s.polygon(col("peach"), [P(x + 6, y - 2), P(x + 2, y - 7), P(x + 2, y)])
            s.polygon(body, [P(x - 3, y - 5), P(x, y - 9), P(x + 3, y - 5)])
            s.ellipse(body, x - 4, y - 7, 9, 11)
            s.ellipse(k, x - 4, y - 7, 9, 11, width: 1)
            for i in 0 ..< 3 {
                let wig = Int(sin(t * 12 + Double(i)) * 1)
                s.fillRect(col("red"), x - 3 + i * 3 + wig, y + 3, 1, 4)
            }
            Cute.eyes(s, x, y - 2, 2, mood: "angry")
            if glow && Int(t * 14) % 2 == 1 { s.circle(col("yellow"), x, y, 9, width: 1) }
        case CK_SPORE:
            if glow { s.circle(col(Int(t * 16) % 2 == 1 ? "yellow" : "white"), x, y, 8, width: 1) }
            s.fillRect(col("mint"), x, y - 7, 1, 2)
            s.fillRect(col("mint"), x - 7, y, 2, 1)
            s.fillRect(col("mint"), x + 6, y, 2, 1)
            s.circle(col(hit ? "white" : "lime"), x, y, 5)
            s.circle(k, x, y, 5, width: 1)
            s.fillRect(col("teal"), x - 3, y - 3, 2, 1)
            s.fillRect(col("teal"), x + 2, y - 3, 1, 2)
            Cute.eyes(s, x, y, 2, mood: glow ? "wow" : "happy")
        case CK_BLOB:
            let wob = Int(sin(t * 6) * 1)
            let r = IRect(x - 7 - wob, y - 5 + wob, 14 + 2 * wob, 11 - wob)
            s.ellipse(col(hit ? "white" : "mint"), r.x, r.y, r.w, r.h)
            s.ellipse(k, r.x, r.y, r.w, r.h, width: 1)
            s.fillRect(col("white"), x - 4, y - 3, 2, 1)
            Cute.eyes(s, x, y, 3)
            Cute.blush(s, x, y + 2, 3)
        case CK_SHELL:
            s.fillRect(col("mint"), x - 5, y + 3, 2, 2)
            s.fillRect(col("mint"), x + 4, y + 3, 2, 2)
            s.circle(col(hit ? "white" : "teal"), x, y, 4)
            s.circle(k, x, y, 4, width: 1)
            Cute.eyes(s, x, y - 1, 2, mood: hp <= 1 ? "angry" : "happy")
            if hp > 1 { bubble(s, Double(x), Double(y), 7, t, tint: "sky") }
        case CK_COMET:
            let fl = Int(t * 20) % 2
            s.polygon(col("red"), [P(x - 4, y), P(x, y - 9 - fl * 2), P(x + 4, y)])
            s.polygon(col("orange"), [P(x - 3, y), P(x, y - 6 - fl), P(x + 3, y)])
            s.circle(col(hit ? "white" : "yellow"), x, y + 1, 4)
            s.circle(k, x, y + 1, 4, width: 1)
            Cute.eyes(s, x, y + 1, 2, mood: "angry")
        case CK_URCHIN:
            for i in 0 ..< 8 {
                let a = t * 2 + Double(i) * .pi / 4
                s.line(col("lavender"), x, y, x + Int(cos(a) * 7), y + Int(sin(a) * 7))
            }
            s.circle(col(hit ? "white" : "purple"), x, y, 5)
            s.circle(k, x, y, 5, width: 1)
            Cute.eyes(s, x, y, 2, mood: "angry")
        case CK_WISP:
            let c = col(hit ? "white" : "lavender")
            if faded {
                s.circle(c, x, y - 1, 5, width: 1)
                for i in 0 ..< 3 { s.fillRect(c, x - 5 + i * 4, y + 4, 2, 1) }
                Cute.eyes(s, x, y - 1, 2, mood: "sleepy")
            } else {
                s.circle(c, x, y - 1, 5)
                s.fillRect(c, x - 5, y - 1, 11, 5)
                for i in 0 ..< 3 { s.fillRect(c, x - 5 + i * 4 + (Int(t * 8) + i) % 2, y + 4, 3, 2) }
                Cute.eyes(s, x, y - 1, 2)
                Cute.mouth(s, x, y + 2, "wow")
            }
        case CK_MINI:
            s.circle(col(hit ? "white" : "pink"), x, y, 3)
            s.fillRect(k, x - 2, y - 1, 1, 2)
            s.fillRect(k, x + 1, y - 1, 1, 2)
        case CK_MINE:
            s.fillRect(col("gray"), x - 1, y - 5, 2, 10)
            s.fillRect(col("gray"), x - 5, y - 1, 10, 2)
            s.circle(col("darkgray"), x, y, 3)
            s.fillRect(col(glow ? "red" : "yellow"), x - 1, y - 1, 2, 2)
        case CK_METEOR:
            s.circle(col(hit ? "white" : "brown"), x, y, 6)
            s.circle(col("choco"), x, y, 6, width: 1)
            s.circle(col("choco"), x - 2, y - 1, 2)
            s.circle(col("choco"), x + 2, y + 3, 1)
            s.fillRect(col("peach"), x - 3, y - 4, 2, 1)
        case CK_GOLD:
            for i in 0 ..< 6 { s.fillRect(col(rainbow(i, t)), x - d * (6 + i * 3) - 1, y - 2 + i % 2, 3, 3) }
            s.circle(col("orange"), x, y, 6)
            s.circle(col(hit ? "white" : "yellow"), x, y, 5)
            s.fillRect(col("white"), x - 2, y - 3, 2, 2)
            Cute.eyes(s, x, y, 2)
            if Int(t * 10) % 2 == 1 {
                s.fillRect(col("white"), x + d * 7, y - 6, 1, 3)
                s.fillRect(col("white"), x + d * 7 - 1, y - 5, 3, 1)
            }
        default: break
        }
    }

    /// Power capsules (P F B S $), the lucky star (L) and score medals (M).
    static func capsule(_ s: Surface, _ kind: String, _ x: Int, _ y: Int, _ t: Double) {
        if kind == "M" {
            let w = max(1, Int(abs(cos(t * 6)) * 4))
            s.fillRect(col("orange"), x - w, y - 4, w * 2 + 1, 9)
            s.fillRect(col("yellow"), x - w + 1, y - 3, max(1, w * 2 - 1), 7)
            if w >= 3 { s.fillRect(col("white"), x, y - 2, 1, 5) }
            return
        }
        if kind == "L" {
            for i in 0 ..< 5 {
                let a = t * 4 + Double(i) * 2 * .pi / 5
                s.fillRect(col(rainbow(i, t)), x + Int(cos(a) * 7), y + Int(sin(a) * 7), 2, 2)
            }
            s.blit(sprite("star"), x - 3, y - 3)
            return
        }
        let c = ["P": "yellow", "F": "pink", "B": "red", "S": "mint", "$": "orange"][kind] ?? "white"
        s.rect(col("black"), IRect(x - 6, y - 4, 13, 10), radius: 3)
        s.rect(col(c), IRect(x - 6, y - 5, 13, 10), radius: 3)
        s.rect(col(Int(t * 6) % 2 == 1 ? "white" : c), IRect(x - 6, y - 5, 13, 10), width: 1, radius: 3)
        drawText(s, kind, x - 2, y - 3, "ink", shadow: nil)
    }

    // ------------------------------------------------------------------ bosses
    /// Weak-spot marker: four blinking corner ticks.
    static func reticle(_ s: Surface, _ x: Int, _ y: Int, _ r: Int, _ t: Double) {
        let c = col(Int(t * 4) % 2 == 1 ? "yellow" : "white")
        for sx in [-1, 1] {
            for sy in [-1, 1] {
                let px = x + sx * r, py = y + sy * r
                s.fillRect(c, px - (sx > 0 ? 1 : 0), py, 2, 1)
                s.fillRect(c, px, py - (sy > 0 ? 1 : 0), 1, 2)
            }
        }
    }

    struct PartView { let x, y, r: Int; let alive: Bool; let flash: Double; let front: Bool }

    /// Draw boss b centred at (x, y). look: -2..2 eye direction.
    static func boss(_ s: Surface, _ b: CKBoss, _ x: Int, _ y: Int, _ t: Double, _ parts: [PartView], _ look: Int) {
        let k = col("black")
        let hit = b.flash > 0 && Int(t * 30) % 3 == 0
        let angry = b.phase >= 1
        let mood = angry ? "angry" : "happy"
        let blink = Int(t * 1.3) % 6 == 0 && !angry
        let attacking = b.atk != nil && b.atk != "teleport"
        switch b.kind {
        case 0:     // MOCHI MOON
            s.circle(col("ink"), x, y + 1, 24)
            s.circle(col("peach"), x, y + 1, 22)
            s.circle(col(hit ? "white" : "cream"), x, y, 21)
            for (dx, dy, r) in [(-12, -9, 4), (12, -6, 3), (7, -15, 2), (-15, 5, 2)] { s.circle(col("peach"), x + dx, y + dy, r) }
            s.circle(col("white"), x - 8, y - 13, 2)
            s.polygon(col("lime"), [P(x, y - 20), P(x + 9, y - 28), P(x + 3, y - 19)])
            s.fillRect(col("teal"), x, y - 23, 1, 4)
            Cute.eyes(s, x, y - 2, 8, look: look, mood: mood, blink: blink, size: 2)
            s.fillRect(col("pink"), x - 17, y + 3, 4, 2)
            s.fillRect(col("pink"), x + 14, y + 3, 4, 2)
            if attacking {
                s.ellipse(k, x - 6, y + 6, 12, 9)
                s.ellipse(col("hotpink"), x - 3, y + 10, 6, 4)
            } else {
                Cute.mouth(s, x, y + 8, mood)
            }
        case 1:     // STAR SQUID
            for p in parts {
                let ex = p.alive ? p.x : x + ckFdiv(p.x - x, 2), ey = p.alive ? p.y : y + 10
                s.line(col("purple"), x + ckFdiv(p.x - x, 3), y + 8, ex, ey, width: 2)
                if p.alive {
                    s.circle(col(p.flash > 0 ? "white" : "lavender"), p.x, p.y, p.r)
                    s.circle(k, p.x, p.y, p.r, width: 1)
                    s.fillRect(col("pink"), p.x - 1, p.y + 1, 2, 2)
                }
            }
            s.polygon(col("purple"), [P(x - 11, y - 10), P(x, y - 26), P(x + 11, y - 10)])
            s.ellipse(col("lavender"), x - 24, y - 16, 10, 12)
            s.ellipse(col("lavender"), x + 14, y - 16, 10, 12)
            s.ellipse(col(hit ? "white" : "purple"), x - 16, y - 16, 32, 32)
            s.ellipse(k, x - 16, y - 16, 32, 32, width: 1)
            for (dx, dy) in [(-8, -8), (6, -11), (9, -2), (-11, 1), (0, -18)] { s.fillRect(col("yellow"), x + dx, y + dy, 1, 1) }
            s.circle(col("white"), x, y + 6, 7)
            s.circle(k, x, y + 6, 7, width: 1)
            s.circle(col(angry ? "red" : "black"), x + look, y + 7, 3)
            s.fillRect(col("white"), x + look - 1, y + 5, 1, 1)
            if angry {
                s.line(k, x - 7, y - 3, x - 2, y - 1)
                s.line(k, x + 7, y - 3, x + 2, y - 1)
            }
        case 2:     // COMET WHALE
            let f = b.face
            s.polygon(col("blue"), [P(x - f * 26, y - 2), P(x - f * 40, y - 13), P(x - f * 35, y), P(x - f * 40, y + 10)])
            s.ellipse(col(hit ? "white" : "blue"), x - 30, y - 14, 60, 28)
            s.ellipse(col("sky"), x - 24, y - 1, 46, 14)
            s.ellipse(k, x - 30, y - 14, 60, 28, width: 1)
            for i in 0 ..< 4 { s.fillRect(col("white"), x - 12 + i * 7, y + 3, 4, 1) }
            s.fillRect(k, x + f * 17 - 1, y - 5, 2, 3)
            s.fillRect(col("white"), x + f * 17 - (f > 0 ? 1 : 0), y - 5, 1, 1)
            s.fillRect(col("pink"), x + f * 20 - 1, y + 1, 3, 1)
            if angry { s.line(k, x + f * 14, y - 9, x + f * 20, y - 7) }
            let sx = x + f * 4
            if b.atk == "rain" || Int(t * 3) % 3 == 0 {
                for i in 0 ..< 5 {
                    let a = -Double.pi / 2 + Double(i - 2) * 0.35
                    let rr = 6 + Int(t * 30 + Double(i * 3)) % 8
                    s.fillRect(col(i % 2 == 1 ? "sky" : "white"), sx + Int(cos(a) * Double(rr)), y - 14 + Int(sin(a) * Double(rr)), 2, 2)
                }
            }
            let wx = x + Int(b.weak.0) * f
            s.polygon(col("yellow"), [P(wx, y + 3), P(wx + 2, y + 7), P(wx + 6, y + 7), P(wx + 3, y + 10), P(wx + 4, y + 14),
                                      P(wx, y + 11), P(wx - 4, y + 14), P(wx - 3, y + 10), P(wx - 6, y + 7), P(wx - 2, y + 7)])
        case 3:     // NEBULA CRAB
            for side in [-1, 1] {
                for i in 0 ..< 3 {
                    let wig = Int(sin(t * 8 + Double(i + side)) * 2)
                    s.line(col("red"), x + side * (8 + i * 5), y + 8, x + side * (14 + i * 6), y + 18 + wig, width: 2)
                }
            }
            for p in parts {
                s.line(col("red"), x + (p.x > x ? 8 : -8), y, p.alive ? p.x : ckFdiv(x + p.x, 2), p.y, width: 3)
                if p.alive {
                    s.circle(col(p.flash > 0 ? "white" : "red"), p.x, p.y, p.r)
                    s.circle(k, p.x, p.y, p.r, width: 1)
                    s.polygon(col("ink"), [P(p.x - 3, p.y - p.r - 1), P(p.x, p.y - 1), P(p.x + 3, p.y - p.r - 1)])
                    s.fillRect(col("peach"), p.x - 5, p.y + 1, 2, 2)
                }
            }
            s.line(k, x - 6, y - 10, x - 9, y - 19)
            s.line(k, x + 6, y - 10, x + 9, y - 19)
            s.ellipse(col(hit ? "white" : "red"), x - 20, y - 12, 40, 26)
            s.ellipse(k, x - 20, y - 12, 40, 26, width: 1)
            for dx in [-10, 0, 10] { s.fillRect(col("peach"), x + dx - 1, y - 8, 3, 2) }
            for side in [-1, 1] {
                s.circle(col("white"), x + side * 9, y - 20, 3)
                s.fillRect(k, x + side * 9 + ckFdiv(look, 2), y - 21, 1, 2)
            }
            Cute.mouth(s, x, y + 6, angry ? "angry" : "wow")
        case 4:     // RING GRUMP
            for p in parts where p.alive && !p.front { s.circle(col("gray"), p.x, p.y, p.r - 1) }
            ring(s, x, y + 4, 36, 11, col("yellow"), false)
            disc(s, x, y, 18, hit ? (255, 247, 240) : (255, 138, 61), (255, 179, 138))
            s.circle(k, x, y, 18, width: 1)
            Cute.eyes(s, x, y - 1, 6, look: look, mood: "angry", blink: blink, size: 2)
            Cute.mouth(s, x, y + 9, "angry")
            ring(s, x, y + 4, 36, 11, col("yellow"), true)
            for p in parts where p.alive && p.front {
                s.circle(col(p.flash > 0 ? "white" : "lavender"), p.x, p.y, p.r)
                s.circle(k, p.x, p.y, p.r, width: 1)
                Cute.eyes(s, p.x, p.y, 2, mood: "sleepy")
            }
        default:    // VOID PUFF / ABYSS PUFF
            let body = col(hit ? "white" : (b.final ? "night" : "ink"))
            let rim = col(b.final ? "red" : "purple")
            let puffs = [(0, -6, 18), (-17, 1, 12), (17, 1, 12), (-10, 10, 11), (10, 10, 11)]
            for (i, (dx, dy, r)) in puffs.enumerated() { s.circle(rim, x + dx, y + dy + Int(sin(t * 3 + Double(i)) * 1), r + 1) }
            for (i, (dx, dy, r)) in puffs.enumerated() { s.circle(body, x + dx, y + dy + Int(sin(t * 3 + Double(i)) * 1), r) }
            for (i, (dx, dy)) in [(-10, -12), (8, -14), (-20, 0), (18, -2), (-4, -2), (12, 6), (-14, 8)].enumerated()
                where Int(t * 2 + Double(i) * 1.7) % 5 != 0 {
                s.fillRect(col("white"), x + dx, y + dy, 3, 2)
                s.fillRect(k, x + dx + 1 + (look > 0 ? 1 : 0) - (look < 0 ? 1 : 0), y + dy, 1, 2)
            }
            let pulse = Int(sin(t * 6) * 1.5)
            s.circle(col("black"), x, y + 10, 8 + pulse)
            s.circle(col("hotpink"), x, y + 10, 6 + pulse)
            s.circle(col("white"), x, y + 10, 2)
            if b.final {
                s.polygon(col("yellow"), [P(x - 10, y - 22), P(x - 7, y - 31), P(x - 3, y - 24), P(x, y - 33), P(x + 3, y - 24),
                                          P(x + 7, y - 31), P(x + 10, y - 22)])
                s.fillRect(col("red"), x - 1, y - 28, 2, 2)
            }
        }
        if b.state == "fight" {
            let (wx, wy, wr) = b.weakPos()
            reticle(s, Int(wx), Int(wy), wr + 2, t)
        }
    }

    // ------------------------------------------------------------------ upgrade card icons
    static func icon(_ uid: String) -> (Surface, Int, Int, Double) -> Void {
        return { s, cx, cy, t in
            switch uid {
            case "spread":
                for dx in [-6, 0, 6] { s.line(col("yellow"), cx, cy + 6, cx + dx, cy - 6, width: 2) }
            case "rapid":
                for i in 0 ..< 3 { s.fillRect(col("yellow"), cx - 1, cy - 8 + i * 6 + Int(t * 12) % 6, 3, 4) }
            case "lance":
                s.fillRect(col("sky"), cx - 2, cy - 9, 5, 18)
                s.fillRect(col("white"), cx - 1, cy - 9, 3, 18)
            case "seeker":
                s.line(col("lime"), cx - 7, cy + 7, cx - 5, cy)
                s.line(col("lime"), cx - 5, cy, cx - 1, cy - 4)
                s.line(col("lime"), cx - 1, cy - 4, cx + 3, cy - 5)
                s.blit(sprite("star"), cx + 1, cy - 9)
            case "pals":
                s.blit(sprite("star"), cx - 9, cy - 3)
                s.blit(sprite("star"), cx + 3, cy - 3)
                s.blit(sprite("heart"), cx - 3, cy - 9)
            case "shield":
                bubble(s, Double(cx), Double(cy), 8, t, tint: "mint")
            case "zoom":
                s.blit(sprite("kitty"), cx - 8, cy - 8)
                for i in 0 ..< 3 { s.fillRect(col("white"), cx - 11 + Int(t * 20 + Double(i * 4)) % 6, cy - 4 + i * 4, 3, 1) }
            case "focus":
                s.fillRect(col("lavender"), cx - 9, cy, 18, 1)
                s.fillRect(col("lavender"), cx, cy - 9, 1, 18)
                s.blit(sprite("heart"), cx - 3, cy - 3)
            case "bombs":
                s.circle(col("red"), cx - 1, cy + 2, 6)
                s.fillRect(col("white"), cx - 4, cy - 1, 2, 2)
                s.line(col("peach"), cx + 3, cy - 3, cx + 6, cy - 7)
                if Int(t * 8) % 2 == 1 { s.fillRect(col("yellow"), cx + 5, cy - 9, 3, 3) }
            case "magnet":
                s.circle(col("red"), cx, cy - 1, 7, width: 3)
                s.fillRect(col("ink"), cx - 8, cy, 17, 8)
                s.fillRect(col("red"), cx - 7, cy - 1, 3, 6)
                s.fillRect(col("red"), cx + 5, cy - 1, 3, 6)
                s.fillRect(col("white"), cx - 7, cy + 4, 3, 2)
                s.fillRect(col("white"), cx + 5, cy + 4, 3, 2)
            default: break
            }
        }
    }
}
