// KITTEN PILE art: kittens, pillows, grandpa cats, yarn, toy mice, the big cats (Poppy, rivals, bosses), the bed and
// the bedroom backgrounds (port of mochi_arcade/games/kitten_pile_art.py - keep the two in step).
// The pixel sprites themselves (kp_*) come from Python through GData.art.
import Foundation

enum KPArt {
    static let CELL = 12
    static let kittens: [Int: (String, [Character: Character])] = [
        1: ("kp_kit", ["o": "o", "n": "n", "c": "c", "p": "p", "u": "k"]),
        2: ("kp_kit", ["o": "g", "n": "d", "c": "w", "p": "p", "u": "k"]),
        3: ("kp_kit", ["o": "i", "n": "k", "c": "d", "p": "P", "u": "y", "k": "k"]),
        4: ("kp_kit", ["o": "w", "n": "c", "c": "w", "p": "p", "u": "b"]),
        5: ("kp_cal", ["o": "w", "n": "o", "h": "i", "c": "c", "p": "p", "u": "k"]),
    ]
    static let poppyRemap: [Character: Character] = ["o": "v", "n": "u", "c": "c", "p": "p", "u": "m"]
    static let kitNames = [1: "GINGER", 2: "TABBY", 3: "SOOTY", 4: "SNOWY", 5: "CALICO"]
    static let kitCoat = [1: "orange", 2: "gray", 3: "ink", 4: "white", 5: "peach"]
    static let kitDark = [1: "brown", 2: "darkgray", 3: "black", 4: "cream", 5: "orange"]

    @inline(__always) static func fdiv(_ a: Int, _ b: Int) -> Int { Int((Double(a) / Double(b)).rounded(.down)) }
    @inline(__always) static func pmod(_ a: Int, _ b: Int) -> Int { ((a % b) + b) % b }
    private static func pts(_ p: [(Int, Int)]) -> [(Double, Double)] { p.map { (Double($0.0), Double($0.1)) } }

    // ------------------------------------------------------------------ the bed and its kittens
    static func kitten(_ s: Surface, _ x: Int, _ y: Int, _ code: Int, _ mood: Int = 0, _ t: Double = 0) {
        let (name, remap) = kittens[code & 7] ?? kittens[1]!
        s.blit(sprite(name, mood, remap: remap), x, y)
        if code & 32 != 0 {
            s.fillRect(col("yellow"), x + 1, y, 2, 2)
            s.fillRect(col("yellow"), x + 9, y, 2, 2)
            let ph = Int(t * 10) % 14
            if ph < 10 {
                s.fillRect(col("white"), x + ph, y + 3, 2, 1)
                s.fillRect(col("yellow"), x + ph + 1, y + 4, 1, 2)
            }
        }
        if code & 16 != 0 { s.blit(sprite("kp_star"), x + 4, y - 2 + Int(sin(t * 5 + Double(x)) * 1)) }
    }

    /// Paws holding: bridge two touching kittens of one colour (right: to the east, else to the south).
    static func link(_ s: Surface, _ x: Int, _ y: Int, _ k: Int, _ right: Bool) {
        let c = col(kitCoat[k] ?? "white")
        if right {
            s.fillRect(c, x + 10, y + 5, 4, 3)
            s.fillRect(col("black"), x + 10, y + 4, 4, 1)
        } else {
            s.fillRect(c, x + 4, y + 9, 4, 5)
            s.fillRect(col(kitDark[k] ?? "gray"), x + 5, y + 10, 2, 1)
        }
    }

    static func junk(_ s: Surface, _ x: Int, _ y: Int, _ code: Int, _ t: Double = 0) {
        if code == KP.PILLOW {
            s.blit(sprite("kp_pillow"), x, y)
        } else {
            s.blit(sprite("kp_grandpa", code == KP.GRANDPA ? 0 : 1), x, y)
            if code == KP.GRANDPA && Int(t * 2 + Double(x)) % 4 == 0 { drawZ(s, x + 9, y - 3, "white") }
        }
    }

    static func special(_ s: Surface, _ x: Int, _ y: Int, _ code: Int, _ t: Double = 0) {
        if code == KP.YARN {
            s.blit(sprite("kp_yarn"), x, y)
            let a = t * 6
            s.fillRect(col("white"), x + 5 + Int(cos(a) * 3), y + 5 + Int(sin(a) * 3), 1, 1)
        } else {
            s.blit(sprite("kp_mouse", flip: Int(t * 4) % 2 == 0), x, y + Int(t * 12) % 2)
        }
    }

    static func cell(_ s: Surface, _ x: Int, _ y: Int, _ code: Int, _ mood: Int = 0, _ t: Double = 0) {
        if code == 0 { return }
        if code & 8 != 0 {
            if code <= 10 { junk(s, x, y, code, t) } else { special(s, x, y, code, t) }
        } else {
            kitten(s, x, y, code, mood, t)
        }
    }

    /// A kitten curling up to sleep (f: 0 -> 1): eyes close, it shrinks into a ball, then a puff.
    static func curl(_ s: Surface, _ x: Int, _ y: Int, _ code: Int, _ f: Double) {
        if f < 0.45 {
            kitten(s, x, y, code, f > 0.12 ? 2 : 1)
            if f > 0.2 { drawZ(s, x + 9, y - 2 - Int((f - 0.2) * 20), "white") }
        } else {
            let r = max(1, Int(6 * (1 - (f - 0.45) / 0.55)))
            s.circle(col("black"), x + 6, y + 7, r + 1)
            s.circle(col(kitCoat[code & 7] ?? "white"), x + 6, y + 7, r)
            drawZ(s, x + 8, y - 6 - Int(f * 10), "lavender")
        }
    }

    static func drawZ(_ s: Surface, _ x: Int, _ y: Int, _ c: String = "white") {
        s.fillRect(col(c), x, y, 3, 1)
        s.fillRect(col(c), x + 1, y + 1, 1, 1)
        s.fillRect(col(c), x, y + 2, 3, 1)
    }

    /// The wicker cat bed around the play field, with a dotted cushion inside.
    static func bed(_ s: Surface, _ bx: Int, _ by: Int, _ w: Int, _ h: Int, _ th: KPTheme) {
        s.rect(col("black"), IRect(bx - 7, by - 3, w + 14, h + 12), radius: 6)
        s.rect(col("brown"), IRect(bx - 6, by - 2, w + 12, h + 10), radius: 6)
        var yy = by
        while yy < by + h + 6 {
            for xx in [bx - 5, bx + w + 1] { s.fillRect(col("choco"), xx + (yy / 4) % 2 * 2, yy, 2, 2) }
            yy += 4
        }
        s.fillRect(col("peach"), bx - 5, by - 2, w + 10, 2)
        s.fillRect(lerpCol("night", th.hue, 0.22), bx, by, w, h)
        let dot = lerpCol("night", th.hue, 0.3)
        yy = by + 6
        while yy < by + h {
            var xx = bx + 6 + (yy - by) / 18 % 2 * 9
            while xx < bx + w { s.fillRect(dot, xx, yy, 2, 2); xx += 18 }
            yy += 18
        }
        s.rect(col("brown"), IRect(bx - 6, by + h + 1, w + 12, 7), radius: 3)
        s.fillRect(col("choco"), bx - 4, by + h + 4, w + 8, 1)
        s.fillRect(col(th.acc), bx + w / 2 - 6, by + h + 3, 12, 3)
    }

    static func drawBg(_ s: Surface, _ th: KPTheme, _ t: Double) {
        s.fill(lerpCol("black", th.hue, 0.16))
        let deco = lerpCol("black", th.hue, 0.28)
        switch th.style {
        case 0:
            for i in 0 ..< 40 { s.circle(deco, (i * 53 + 11) % W, (i * 29 + Int(t * 4)) % (H + 8) - 4, 2 + i % 2) }
        case 1:
            let off = Int(t * 5) % 20
            var x = -20
            while x < W + 20 { s.fillRect(deco, x + off, 0, 6, H); x += 20 }
        case 2:
            for i in 0 ..< 30 {
                let x = (i * 71 + 7) % W, y = (i * 37 + 11) % H
                if (Int(t * 2) + i) % 6 != 0 {
                    s.fillRect(deco, x, y - 2, 1, 5)
                    s.fillRect(deco, x - 2, y, 5, 1)
                }
            }
        case 3:
            let off = Int(t * 4) % 32
            var y = -32
            while y < H + 32 {
                var x = -32
                while x < W + 32 {
                    if pmod(fdiv(x + y, 16), 2) == 0 { s.fillRect(deco, x + off, y + off / 2, 16, 16) }
                    x += 16
                }
                y += 16
            }
        default:
            for i in 0 ..< 24 {
                let x = (i * 61 + 23) % W, y = (i * 43 + Int(t * 6)) % (H + 10) - 5
                s.circle(deco, x - 2, y, 2)
                s.circle(deco, x + 2, y, 2)
                s.polygon(deco, pts([(x - 4, y + 1), (x + 4, y + 1), (x, y + 5)]))
            }
        }
    }

    // ------------------------------------------------------------------ big cats
    /// A round cat head (radius r) - Poppy, the rivals and the bosses all share it.
    /// mood: open | angry | smug | happy | sleep | wow | hurt
    static func bigCat(_ s: Surface, _ cx: Int, _ cy: Int, _ r: Int, _ coat: String, _ mark: String, _ eye: String,
                       _ mood: String = "open", _ t: Double = 0, look: Int = 0, pattern: String = "tabby", ear: Int = 0,
                       muzzle: String = "cream") {
        let k = col("black")
        if pattern == "fluff" {          // scalloped fur edge behind the head
            for pass in 0 ..< 2 {
                for i in 0 ..< 12 {
                    let a = Double(i) * 0.5236 + 0.26
                    let fx = cx + Int(cos(a) * Double(r)), fy = cy + Int(sin(a) * Double(r) * 0.9) + 1
                    s.circle(pass == 0 ? k : col(coat), fx, fy, r / 4 + 2 - pass)
                }
            }
        }
        for side in [-1, 1] {            // ears
            let tw = side < 0 ? ear : 0
            let ax = cx + side * r, ay = cy - r / 3
            let bx = cx + side * (r * 3 / 4), by = cy - r - r / 2 + tw
            let qx = cx + side * (r / 4), qy = cy - r + 1
            s.polygon(k, pts([(ax + side, ay + 1), (bx + side, by - 1), (qx - side, qy - 1)]))
            s.polygon(col(coat), pts([(ax, ay), (bx, by), (qx, qy)]))
            s.polygon(col("pink"), pts([(ax - side * 3, ay - 2), (bx, by + 4), (qx + side * 2, qy + 1)]))
        }
        if pattern != "fluff" {
            s.circle(k, cx, cy, r + 1)
            s.ellipse(k, cx - r - 2, cy - r / 4 - 1, 2 * r + 4, r + 3)
        }
        s.circle(col(coat), cx, cy, r)
        s.ellipse(col(coat), cx - r - 1, cy - r / 4, 2 * r + 2, r + 1)
        let m = col(mark)
        switch pattern {
        case "tabby":
            s.fillRect(m, cx - 1, cy - r + 1, 3, r / 3)
            s.fillRect(m, cx - r / 3 - 2, cy - r + 3, 2, r / 4)
            s.fillRect(m, cx + r / 3 + 1, cy - r + 3, 2, r / 4)
            for side in [-1, 1] {
                for i in 0 ..< 2 { s.fillRect(m, cx + side * (r - 1) - (side > 0 ? 3 : 0), cy + i * 3, 4, 1) }
            }
        case "tux":
            s.ellipse(m, cx - r / 2 - 1, cy - 1, r + 2, r / 2 + 4)
            s.polygon(m, pts([(cx - 2, cy - r / 2), (cx + 2, cy - r / 2), (cx + r / 3, cy + 2), (cx - r / 3, cy + 2)]))
        case "patch":
            s.circle(m, cx + r / 2, cy - r / 4, r / 2)
        case "fluff":
            s.ellipse(m, cx - r / 2, cy + r / 6, r, r / 2 + 2)
        case "cosmic":
            for i in 0 ..< 7 {
                s.fillRect(m, cx + Int(cos(Double(i) * 1.1 + t) * Double(r) * 0.6),
                           cy - r / 2 + Int(sin(Double(i) * 1.7) * Double(r) * 0.3), 1, 1)
            }
        default: break
        }
        let es = max(2, r / 5)
        let ey = cy - r / 8
        if pattern == "mask" { s.fillRect(m, cx - r, ey - es - 2, 2 * r + 1, 2 * es + 5) }
        for side in [-1, 1] {
            let ex = cx + side * (r * 2 / 5) + look
            switch mood {
            case "open", "angry", "smug":
                s.ellipse(col(eye), ex - es, ey - es - 1, 2 * es + 1, 2 * es + 3)
                s.ellipse(k, ex - es / 2, ey - es, es + 1, 2 * es + 1)
                s.fillRect(col("white"), ex - es + 1, ey - es, 2, 2)
                if mood == "smug" {
                    s.fillRect(col(coat), ex - es, ey - es - 1, 2 * es + 1, es + 1)
                    s.fillRect(k, ex - es, ey, 2 * es + 1, 1)
                }
                if mood == "angry" { s.line(k, ex - side * es * 2, ey - es - 3, ex + side, ey - es, width: 2) }
            case "happy":
                s.line(k, ex - es, ey + 1, ex, ey - es + 1, width: 2)
                s.line(k, ex, ey - es + 1, ex + es, ey + 1, width: 2)
            case "sleep":
                s.line(k, ex - es, ey - 1, ex, ey + es - 1, width: 2)
                s.line(k, ex, ey + es - 1, ex + es, ey - 1, width: 2)
            case "wow":
                s.circle(col("white"), ex, ey, es + 1)
                s.circle(k, ex, ey, es + 1, width: 1)
                s.fillRect(k, ex - 1, ey - 1, 2, 2)
            default:            // hurt: > <
                s.line(k, ex - side * es, ey - es, ex + side * es, ey, width: 2)
                s.line(k, ex + side * es, ey, ex - side * es, ey + es, width: 2)
            }
        }
        let mz = col(muzzle)
        let my = cy + r / 3
        s.circle(mz, cx - es + 1, my, es)
        s.circle(mz, cx + es - 1, my, es)
        s.polygon(col("hotpink"), pts([(cx - 2, my - es), (cx + 2, my - es), (cx, my - es + 2)]))
        switch mood {
        case "wow", "hurt":
            s.ellipse(k, cx - 2, my + 1, 5, 5)
        case "happy":
            s.ellipse(k, cx - 3, my, 7, 5)
            s.fillRect(col("hotpink"), cx - 1, my + 2, 3, 2)
        case "angry":
            s.fillRect(k, cx - 2, my + 2, 5, 1)
        default:
            s.fillRect(k, cx - 2, my + 1, 2, 1)
            s.fillRect(k, cx + 1, my + 1, 2, 1)
            s.fillRect(k, cx, my, 1, 1)
        }
        for side in [-1, 1] {
            let x0 = cx + side * (es + 3)
            s.line(col("white"), x0, my - 1, x0 + side * (r / 2 + 3), my - 3)
            s.line(col("white"), x0, my + 1, x0 + side * (r / 2 + 3), my + 2)
            if mood != "angry" { s.fillRect(col("pink"), cx + side * (r / 2 + 2) - 2, my - es + 1, 4, 2) }
        }
    }

    static func star(_ s: Surface, _ x: Int, _ y: Int, _ r: Int, _ c: String) {
        s.polygon(col(c), pts([(x, y - r), (x + r / 2 + 1, y), (x, y + r), (x - r / 2 - 1, y)]))
        s.polygon(col(c), pts([(x - r, y), (x, y - r / 2 - 1), (x + r, y), (x, y + r / 2 + 1)]))
    }

    static func accessory(_ s: Surface, _ kind: String, _ cx: Int, _ cy: Int, _ r: Int, _ t: Double, _ c2: String = "red") {
        let k = col("black")
        switch kind {
        case "tophat":
            let hx = cx - r / 2 - 1
            s.fillRect(k, hx - 4, cy - r - 2, r + 10, 3)
            s.fillRect(k, hx, cy - r - 16, r + 2, 14)
            s.fillRect(col("red"), hx, cy - r - 6, r + 2, 3)
            s.circle(col("yellow"), cx + r * 2 / 5, cy - r / 8, max(3, r / 4), width: 1)
            s.line(col("yellow"), cx + r * 2 / 5 + 2, cy, cx + r - 2, cy + r / 2)
        case "bow":
            let bx = cx - r + 2, by = cy - r + 1
            s.polygon(col("hotpink"), pts([(bx, by), (bx - 7, by - 5), (bx - 7, by + 5)]))
            s.polygon(col("hotpink"), pts([(bx, by), (bx + 7, by - 5), (bx + 7, by + 5)]))
            s.circle(col("pink"), bx, by, 2)
        case "mask":
            let tail = Int(sin(t * 8) * 3)
            s.polygon(col("red"), pts([(cx + r, cy - r / 3), (cx + r + 10, cy - r / 3 - 4 + tail), (cx + r + 9, cy - r / 3 + 3 + tail)]))
            s.fillRect(col("red"), cx - r + 1, cy - r / 2 - 2, 2 * r - 1, 2)
        case "phones":
            s.circle(col("hotpink"), cx, cy - 2, r + 3, width: 2)
            s.fillRect(col("sky"), cx - r - 4, cy - 4, 5, 9)
            s.fillRect(col("sky"), cx + r, cy - 4, 5, 9)
            if Int(t * 4) % 2 == 1 {
                s.fillRect(col("yellow"), cx + r + 7, cy - 10, 2, 2)
                s.fillRect(col("yellow"), cx - r - 9, cy - 12, 2, 2)
            }
        case "crown":
            let y0 = cy - r - 3
            s.polygon(col("yellow"), pts([(cx - r / 2 - 2, y0 + 4), (cx - r / 2 - 2, y0 - 6), (cx - r / 4, y0 - 1), (cx, y0 - 8),
                                          (cx + r / 4, y0 - 1), (cx + r / 2 + 2, y0 - 6), (cx + r / 2 + 2, y0 + 4)]))
            s.fillRect(col("red"), cx - 1, y0 - 2, 3, 3)
            s.ellipse(col("white"), cx - r / 2, cy + r / 3 + 2, r, r / 2)
        case "moon":
            let mx = cx - r - 2, my = cy - r - 4
            s.circle(col("yellow"), mx, my, 6)
            s.circle(col("purple"), mx + 3, my - 2, 5)
            for i in 0 ..< 5 {
                let a = t * 1.5 + Double(i) * 1.26
                s.fillRect(col(i % 2 == 1 ? "white" : "yellow"), cx + Int(cos(a) * Double(r + 8)), cy + Int(sin(a) * Double(r + 6)), 1, 1)
            }
        case "nightcap":
            let tip = Int(sin(t * 2) * 2)
            let y0 = cy - r + 1
            let p = [(cx - r + 1, y0), (cx - r / 2, y0 - 7), (cx + r / 3, y0 - 9), (cx + r + 7, y0 + 3 + tip), (cx + r - 1, y0 - 1)]
            s.polygon(k, pts(p.map { ($0.0, $0.1 - 1) }))
            s.polygon(col("purple"), pts(p))
            for i in 0 ..< 3 {
                let x = cx - r / 2 + i * (r / 2 + 1)
                s.line(col("lavender"), x, y0 - 7 + i, x + 3, y0 - 2)
            }
            s.fillRect(col("white"), cx - r + 2, y0 - 1, 2 * r - 3, 3)
            star(s, cx + r + 7, y0 + 3 + tip, 3, "yellow")
        case "collar":
            s.fillRect(col(c2), cx - r / 2, cy + r - 1, r, 3)
            s.circle(col("yellow"), cx, cy + r + 3, 2)
        default: break
        }
    }

    /// Poppy's lantern (lx, ly = left / middle) with a soft warm glow.
    static func lantern(_ s: Surface, _ lx: Int, _ ly: Int, _ t: Double) {
        let glow = 7 + Int(sin(t * 6) * 1)
        s.circle(col("yellow", 70), lx + 2, ly, glow)
        s.fillRect(col("black"), lx - 1, ly - 5, 7, 9)
        s.fillRect(col("yellow"), lx, ly - 4, 5, 7)
        s.fillRect(col("white"), lx + 1, ly - 3, 2, 3)
        s.fillRect(col("brown"), lx - 1, ly - 6, 7, 2)
    }

    static let poppyFace = ["idle": "open", "move": "open", "happy": "happy", "cheer": "happy", "hurt": "wow", "sleepy": "sleep"]

    /// Poppy, the night-shift nanny cat: lilac fur, a striped nightcap and a lantern. (cx, by) = feet.
    /// mood: idle | move | happy | cheer | hurt | sleepy
    static func poppy(_ s: Surface, _ cx: Int, _ by: Int, _ t: Double, _ mood: String = "idle", look: Int = 0) {
        var bob = Int(sin(t * 3) * 1)
        let jump = (mood == "happy" || mood == "cheer") ? -Int(abs(sin(t * 9)) * 5) : 0
        if mood == "hurt" { bob = Int(sin(t * 40) * 1) }
        let y = by + jump
        for pass in 0 ..< 2 {            // tail: outline pass, then fur
            for i in 0 ..< 8 {
                let a = Double(i) / 7
                let tx = cx + 8 + Int(a * 8)
                let ty = y - 6 - Int(a * 12) + Int(sin(t * 4 + a * 3) * 2)
                if pass == 0 { s.circle(col("black"), tx, ty, 3) } else { s.circle(col(i < 6 ? "lavender" : "purple"), tx, ty, 2) }
            }
        }
        s.ellipse(col("black"), cx - 10, y - 19 + bob, 20, 18)
        s.ellipse(col("lavender"), cx - 9, y - 18 + bob, 18, 16)
        s.ellipse(col("cream"), cx - 5, y - 14 + bob, 10, 10)
        for side in [-1, 1] {
            let step = mood == "move" ? Int(sin(t * 10) * 2) * side : 0
            s.ellipse(col("black"), cx + side * 6 - 4 + step, y - 4, 9, 5)
            s.ellipse(col("white"), cx + side * 6 - 3 + step, y - 3, 7, 3)
        }
        var lx = cx - 13 + Int(sin(t * 2.4) * 3), ly = y - 9 + bob
        if mood == "happy" || mood == "cheer" { lx = cx - 14; ly = y - 26 + bob }
        s.line(col("black"), cx - 7, y - 14 + bob, lx + 2, ly - 6, width: 3)
        s.line(col("lavender"), cx - 7, y - 14 + bob, lx + 2, ly - 6)
        lantern(s, lx, ly, t)
        var face = poppyFace[mood] ?? "open"
        if face == "open" && Int(t * 10) % 37 == 0 { face = "sleep" }
        let hy = y - 27 + bob
        bigCat(s, cx, hy, 10, "lavender", "purple", "mint", face, t, look: look, pattern: "tabby", ear: sin(t * 7) > 0.95 ? 2 : 0)
        accessory(s, "nightcap", cx, hy, 10, t)
        if mood == "hurt" {
            s.fillRect(col("sky"), cx + 11, hy - 6, 2, 4)
            s.fillRect(col("white"), cx + 11, hy - 6, 1, 1)
        }
        if mood == "sleepy" { drawZ(s, cx + 12, hy - 14 - Int(t * 6) % 6, "white") }
    }

    static let bossPattern = ["tophat": "tux", "bow": "fluff", "mask": "mask", "phones": "tabby", "crown": "fluff", "moon": "cosmic"]

    /// A boss or a duel rival: head and shoulders.
    static func foe(_ s: Surface, _ boss: Bool, _ d: KPCatDef, _ cx: Int, _ cy: Int, _ t: Double, _ mood: String = "open", hit: Bool = false) {
        let acc = boss ? d.extra : "collar"
        let r = boss ? 17 : 13
        let pattern = boss ? (bossPattern[d.extra] ?? "plain") : d.pattern
        let bob = Int(sin(t * 2.5) * 1)
        var coat = d.coat
        if hit && Int(t * 30) % 2 == 1 { coat = "white" }
        s.ellipse(col("black"), cx - r - 3, cy + r - 6 + bob, 2 * r + 6, r + 10)
        s.ellipse(col(coat), cx - r - 2, cy + r - 5 + bob, 2 * r + 4, r + 8)
        if pattern == "tux" || pattern == "fluff" {
            s.ellipse(col(pattern == "tux" ? d.mark : "white"), cx - r / 2, cy + r - 2 + bob, r, r / 2 + 4)
        }
        if acc == "moon" { accessory(s, acc, cx, cy + bob, r, t) }
        let darkCoat = ["black", "darkgray", "ink", "choco"].contains(d.coat)
        bigCat(s, cx, cy + bob, r, coat, d.mark, d.eye, mood, t, look: 0, pattern: pattern, muzzle: darkCoat ? "white" : "cream")
        if acc != "moon" { accessory(s, acc, cx, cy + bob, r, t, boss ? "red" : d.extra) }
    }

    /// Greedy word wrap to lines of at most n characters.
    static func wrap(_ text: String, _ n: Int) -> [String] {
        var lines: [String] = [], cur = ""
        for word in text.split(separator: " ", omittingEmptySubsequences: false).map(String.init) {
            if !cur.isEmpty && cur.count + 1 + word.count > n {
                lines.append(cur)
                cur = word
            } else {
                cur = cur.isEmpty ? word : cur + " " + word
            }
        }
        if !cur.isEmpty { lines.append(cur) }
        return lines
    }
}
