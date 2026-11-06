// WINDOW WATCH art (port of mochi_arcade/games/window_watch_art.py): Maru, the treasures on the windowsill,
// the sky backgrounds and every falling/flying thing. The ww_* sprites come from GeneratedData (sprites.ART).
import Foundation

let WW_SILL = 172

/// Python-style modulo for doubles (the result has the sign of the divisor).
@inline(__always) func wwMod(_ a: Double, _ m: Double) -> Double {
    let r = a.truncatingRemainder(dividingBy: m)
    return r < 0 ? r + m : r
}

/// Python-style floor division for ints.
@inline(__always) func wwDiv(_ a: Int, _ b: Int) -> Int {
    let q = a / b
    return (a % b != 0 && (a < 0) != (b < 0)) ? q - 1 : q
}

enum WWArt {
    static let capColors: [String: String] = ["N": "lime", "T": "orange", "S": "sky", "H": "pink", "$": "yellow"]
    static let kindColors: [String: [String]] = [
        "drop": ["sky", "blue", "white"], "leaf": ["orange", "yellow", "peach"], "bug": ["lime", "mint", "sky"],
        "dart": ["yellow", "red", "white"], "bubble": ["sky", "white", "lavender"], "mini": ["sky", "white", "lavender"],
        "crow": ["darkgray", "gray", "black"], "hail": ["white", "sky", "lavender"], "moth": ["lavender", "cream", "white"],
        "rocket": ["red", "yellow", "white"], "spark": ["yellow", "orange", "white"], "snow": ["white", "sky", "white"],
        "plane": ["white", "sky", "cream"], "puff": ["white", "cream", "lime"], "seed": ["white", "cream"],
        "star": ["yellow", "white", "orange"], "food": ["orange", "yellow"], "cap": ["white", "pink", "yellow"],
        "orb": ["yellow", "white", "orange"], "feather": ["darkgray", "gray"], "treat": ["orange", "yellow", "peach"],
        "gold": ["yellow", "white", "orange"], "fly": ["yellow", "lime", "white"], "rise": ["sky", "white", "pink"]]

    // ------------------------------------------------------------------ small helpers
    /// Filled circle, only the rows at or below ytop (water in a bowl).
    static func discBelow(_ s: Surface, _ cx: Int, _ cy: Int, _ r: Int, _ ytop: Int, _ color: String) {
        let c = col(color)
        for dy in -r ... r {
            let y = cy + dy
            if y < ytop { continue }
            let dx = Int(Double(r * r - dy * dy).squareRoot())
            s.fillRect(c, cx - dx, y, dx * 2 + 1, 1)
        }
    }

    static func ditherBand(_ s: Surface, _ y0: Int, _ h: Int, _ a: String, _ b: String) {
        for i in 0 ..< max(0, h) {
            let f = Double(i) / Double(max(1, h - 1))
            s.fillRect(lerpCol(a, b, f), 0, y0 + i, W, 1)
        }
    }

    // ------------------------------------------------------------------ the sky
    static func makeSky(_ theme: WWTheme, _ seed: Int) -> Surface {
        let s = Surface(W, H)
        let top = theme.top, bottom = theme.bottom, deco = theme.deco
        ditherBand(s, 0, WW_SILL, top, bottom)
        let night = ["black", "night", "darkgray", "purple"].contains(top)
        if deco.contains("rainbow") {
            for (i, c) in ["red", "orange", "yellow", "lime", "sky", "lavender"].enumerated() {
                s.circle(col(c), 160, 190, 120 - i * 4, width: 4)
            }
            ditherBand(s, 160, WW_SILL - 160, bottom, bottom)
        }
        if deco.contains("sun") {
            s.circle(col("yellow"), 272, 52, 14)
            s.circle(col("white"), 268, 48, 5)
            var a = 0
            while a < 360 {
                let r = Double(a) * .pi / 180
                s.fillRect(col("yellow"), Int(272 + cos(r) * 18), Int(52 + sin(r) * 18), 2, 2)
                a += 30
            }
        }
        if deco.contains("sunset") {
            s.circle(col("orange"), 200, 160, 30)
            s.circle(col("yellow"), 200, 160, 24)
            for i in 0 ..< 4 { s.fillRect(col("peach"), 150, 132 + i * 8, 100, 1) }
        }
        if deco.contains("moon") {
            s.circle(col("cream"), 58, 50, 11)
            s.circle(col(top), 64, 46, 10)
        }
        if deco.contains("bigmoon") {
            s.circle(col("orange"), 240, 70, 22)
            s.circle(col("peach"), 234, 64, 6)
            s.circle(col("peach"), 250, 80, 3)
        }
        if deco.contains("aurora") {
            for (band, c) in [(40, "mint"), (52, "teal"), (64, "lavender")] {
                var x = 0
                while x < W {
                    let y = band + Int(sin(Double(x) * 0.03 + Double(band)) * 8)
                    s.fillRect(col(c), x, y, 2, 2 + (x / 2) % 3)
                    x += 2
                }
            }
        }
        if deco.contains("stars") {
            var rnd = seed * 7 + 3
            for i in 0 ..< 46 {
                rnd = (rnd &* 1103515245 &+ 12345) & 0x7FFF_FFFF
                let x = rnd % W
                rnd = (rnd &* 1103515245 &+ 12345) & 0x7FFF_FFFF
                let y = 20 + rnd % 120
                s.fillRect(col(i % 5 == 0 ? "white" : "lavender"), x, y, 1, 1)
            }
        }
        // distant rooftops
        let roof = lerpCol(bottom, night ? "night" : "black", night ? 0.6 : 0.45)
        var x = 0, i = 0
        while x < W {
            let w = 26 + (i * 37 % 23)
            let h = 10 + (i * 53 % 17)
            s.fillRect(roof, x, WW_SILL - h, w - 2, h)
            if i % 3 == 0 {
                s.polygon(roof, [(Double(x - 2), Double(WW_SILL - h)), (Double(x + w / 2 - 1), Double(WW_SILL - h - 8)),
                                 (Double(x + w), Double(WW_SILL - h))])
            }
            if night {
                var wy = WW_SILL - h + 3
                while wy < WW_SILL - 3 {
                    var wx = x + 3
                    while wx < x + w - 5 {
                        if (wx * 7 + wy * 3 + i) % 5 == 0 { s.fillRect(col("yellow"), wx, wy, 2, 2) }
                        wx += 6
                    }
                    wy += 5
                }
            }
            x += w
            i += 1
        }
        return s
    }

    static func drawSkyFx(_ s: Surface, _ theme: WWTheme, _ t: Double, _ flash: Double) {
        let deco = theme.deco
        if deco.contains("clouds") {
            for i in 0 ..< 4 {
                let x = Int(wwMod(Double(i * 97) + t * Double(5 + i * 2), Double(W + 80)) - 40)
                let y = 34 + (i * 29) % 70
                s.ellipse(col("white"), x - 16, y - 4, 32, 9)
                s.ellipse(col("white"), x - 8, y - 9, 18, 11)
            }
        }
        if deco.contains("bubbles") {
            for i in 0 ..< 6 {
                let y = Double(WW_SILL) - wwMod(t * 10 + Double(i * 31), 150)
                let x = Double(20 + (i * 53) % 280) + sin(t + Double(i)) * 6
                s.circle(col("white"), Int(x), Int(y), 3 + i % 3, width: 1)
            }
        }
        if deco.contains("storm") {
            for i in 0 ..< 5 {
                let x = Int(wwMod(Double(i * 71) + t * 6, Double(W + 60)) - 30)
                s.ellipse(col("darkgray"), x - 30, 14, 60, 18)
                s.ellipse(col("ink"), x - 20, 22, 44, 12)
            }
        }
        if deco.contains("rain") {
            let c = col("lavender")
            for i in 0 ..< 40 {
                let x = (i * 41 + Int(t * 40)) % W
                let y = (i * 67 + Int(t * 220)) % (WW_SILL - 20) + 20
                s.fillRect(c, x, y, 1, 4)
            }
        }
        if deco.contains("leaves") {
            for i in 0 ..< 10 {
                let y = wwMod(Double(i * 37) + t * 18, Double(WW_SILL - 20)) + 20
                let x = wwMod(Double(i * 61) + t * 30 + sin(t * 2 + Double(i)) * 10, Double(W))
                s.fillRect(col(i % 2 == 1 ? "orange" : "brown"), Int(x), Int(y), 2, 1)
            }
        }
        if deco.contains("petals") {
            for i in 0 ..< 14 {
                let y = wwMod(Double(i * 29) + t * 16, Double(WW_SILL - 20)) + 20
                let x = wwMod(Double(i * 47) + t * 12 + sin(t * 2 + Double(i)) * 8, Double(W))
                s.fillRect(col(i % 3 != 0 ? "pink" : "white"), Int(x), Int(y), 2, 1)
            }
        }
        if deco.contains("snow") {
            for i in 0 ..< 36 {
                let y = wwMod(Double(i * 23) + t * Double(14 + i % 4 * 4), Double(WW_SILL - 20)) + 20
                let x = wwMod(Double(i * 53) + sin(t + Double(i)) * 6, Double(W))
                s.fillRect(col("white"), Int(x), Int(y), 1 + i % 2, 1 + i % 2)
            }
        }
        if deco.contains("stars") {
            for i in 0 ..< 6 where Int(t * 3 + Double(i) * 1.7) % 4 == 0 {
                let x = (i * 131 + 17) % W, y = 24 + (i * 47) % 100
                s.fillRect(col("white"), x - 1, y, 3, 1)
                s.fillRect(col("white"), x, y - 1, 1, 3)
            }
        }
        if deco.contains("lanterns") {
            var x = 10
            while x < W {
                let y = 28 + Int(sin(Double(x) * 0.05) * 4)
                s.fillRect(col("darkgray"), x, y - 3, 1, 3)
                s.ellipse(col((x / 28) % 2 == 1 ? "red" : "orange"), x - 3, y, 7, 8)
                s.fillRect(col("yellow"), x - 1, y + 3, 3, 2)
                x += 28
            }
        }
        if deco.contains("fireworks") {
            for i in 0 ..< 2 {
                let cyc = wwMod(t + Double(i) * 1.7, 3.4)
                if cyc < 1.2 {
                    let cx = 60 + ((Int((t + Double(i) * 1.7) / 3.4) * 97 + i * 120) % 200), cy = 50 + i * 24
                    let rr = Int(cyc * 22)
                    let c = col(["hotpink", "yellow", "mint", "sky"][(Int((t + Double(i)) / 3.4) + i) % 4])
                    var a = 0
                    while a < 360 {
                        let r = Double(a) * .pi / 180
                        s.fillRect(c, Int(Double(cx) + cos(r) * Double(rr)), Int(Double(cy) + sin(r) * Double(rr)), 1, 1)
                        a += 30
                    }
                }
            }
        }
        if deco.contains("kites") {
            for i in 0 ..< 2 {
                let x = Double(70 + i * 170) + sin(t * 0.8 + Double(i)) * 12
                let y = Double(50 + i * 16) + sin(t * 1.3 + Double(i)) * 6
                s.polygon(col(i == 1 ? "red" : "yellow"), [(x, y - 6), (x + 5, y), (x, y + 7), (x - 5, y)])
                for j in 1 ..< 6 {
                    s.fillRect(col(j % 2 == 1 ? "white" : "pink"), Int(x + sin(t * 4 + Double(j)) * 2), Int(y + 7 + Double(j * 4)), 2, 1)
                }
            }
        }
        if flash > 0 {
            s.fillRect(col("white", Int(120 * min(1, flash * 4))), 0, 0, W, WW_SILL)
        }
    }

    /// Window frame: tied-back curtains on the sides and a scalloped valance under the HUD band.
    static func drawFrame(_ s: Surface, _ theme: WWTheme, _ t: Double) {
        let cur = theme.curtain
        let dark = cur == "white" ? "darkgray" : "ink"
        for i in 0 ..< 9 {
            let yb = 150 - i * 7 + Int(sin(t * 1.2 + Double(i) * 0.5))
            let c = col(i % 3 == 2 ? dark : cur)
            s.fillRect(c, i, 17, 1, yb - 17)
            s.fillRect(c, W - 1 - i, 17, 1, yb - 17)
        }
        s.fillRect(col("yellow"), 0, 98, 6, 2)
        s.fillRect(col("yellow"), W - 6, 98, 6, 2)
        var x = 0
        while x < W {
            s.circle(col(cur), x + 6, 21, 5)
            s.fillRect(col(dark), x + 6, 25, 1, 1)
            x += 12
        }
        s.fillRect(col(cur), 0, 17, W, 4)
        s.fillRect(col("brown"), 0, 16, W, 2)
    }

    static func drawSill(_ s: Surface) {
        s.fillRect(col("brown"), 0, WW_SILL, W, 5)
        s.fillRect(col("peach"), 0, WW_SILL, W, 1)
        s.fillRect(col("choco"), 0, WW_SILL + 5, W, H - WW_SILL - 5)
        s.fillRect(col("black"), 0, WW_SILL + 5, W, 1)
        for y in [WW_SILL + 11, WW_SILL + 19] {
            var x = 4 + (y % 3) * 9
            while x < W { s.fillRect(col("brown"), x, y, 18, 1); x += 47 }
        }
    }

    // ------------------------------------------------------------------ treasures
    static func drawTreasure(_ s: Surface, _ tr: WWTreasure, _ t: Double) {
        let hp = tr.hp, mx = tr.maxhp
        let wob = tr.wobble > 0 ? Int(sin(tr.wobble * 30) * 2) : 0
        let x = Int(tr.x) + wob
        if tr.kind == "bowl" {
            let cx = x, cy = 161, r = 11
            s.fillRect(col("choco"), cx - 6, WW_SILL - 2, 13, 2)
            let level = hp > 0 ? cy + r - Int(Double(2 * r - 4) * Double(hp) / Double(mx)) : cy + r + 1
            s.circle(col("black"), cx, cy, r + 1)
            s.circle(col(hp > 0 ? "sky" : "darkgray"), cx, cy, r)
            s.circle(col("ink"), cx, cy, r - 1)
            if hp > 0 {
                discBelow(s, cx, cy, r - 1, level, "blue")
                s.fillRect(col("sky"), cx - Int(Double(max(0, (r - 1) * (r - 1) - (level - cy) * (level - cy))).squareRoot()), level, 1, 1)
                let fx = cx - 4 + Int(sin(t * 1.3 + tr.x) * 4)
                let fy = max(level + 2, cy + 1) + Int(sin(t * 3 + tr.x))
                s.blit(sprite("ww_fish", flip: cos(t * 1.3 + tr.x) < 0), fx, fy)
            } else {
                s.blit(sprite("ww_fish"), cx - 2, cy + 6)
                s.fillRect(col("black"), cx - 1, cy + 7, 1, 1)
            }
            s.fillRect(col("white"), cx - 7, cy - 6, 2, 3)
            s.fillRect(col("white"), cx - 8, cy - 2, 1, 2)
            s.ellipse(col("black"), cx - 7, cy - r - 2, 15, 5)
            s.ellipse(col("sky"), cx - 6, cy - r - 1, 13, 3)
        } else if tr.kind == "pond" {
            let x0 = x - 22, y0 = 158, w = 45
            s.rect(col("black"), IRect(x0 - 1, y0 - 1, w + 2, WW_SILL - y0 + 1), radius: 3)
            s.rect(col(hp > 0 ? "gray" : "darkgray"), IRect(x0, y0, w, WW_SILL - y0), radius: 3)
            s.fillRect(col("ink"), x0 + 2, y0 + 2, w - 4, WW_SILL - y0 - 3)
            if hp > 0 {
                let lv = Int(Double(WW_SILL - y0 - 4) * Double(hp) / Double(mx))
                s.fillRect(col("teal"), x0 + 2, WW_SILL - 1 - lv, w - 4, lv)
                s.fillRect(col("mint"), x0 + 2, WW_SILL - 1 - lv, w - 4, 1)
                for i in 0 ..< 2 {
                    let ph = t * (1.1 + Double(i) * 0.4) + Double(i)
                    s.blit(sprite("ww_fish", flip: cos(ph) < 0), x0 + 8 + i * 18 + Int(sin(ph) * 6), WW_SILL - 7)
                }
                s.ellipse(col("lime"), x0 + 28, WW_SILL - 2 - lv, 9, 3)
            }
            s.fillRect(col("white"), x0 + 3, y0 + 3, 4, 1)
        } else {    // bird feeder: a little house on a post with two chicks
            s.fillRect(col("brown"), x - 1, 160, 3, WW_SILL - 160)
            s.fillRect(col("choco"), x - 9, 158, 19, 3)
            s.polygon(col(hp > 0 ? "red" : "darkgray"), [(Double(x - 11), 150), (Double(x), 143), (Double(x + 11), 150)])
            s.fillRect(col("black"), x - 11, 150, 23, 1)
            s.fillRect(col("cream"), x - 8, 151, 17, 7)
            if hp > 0 {
                for i in 0 ..< min(2, hp) {
                    let bob = Int(abs(sin(t * 4 + Double(i) * 1.3)))
                    s.blit(sprite("ww_chick", flip: i == 1), x - 7 + i * 9, 152 - bob)
                }
                for i in 0 ..< hp { s.fillRect(col("yellow"), x - 6 + i * 4, 157, 2, 1) }
            } else {
                s.fillRect(col("darkgray"), x - 6, 155, 13, 1)
            }
        }
        if tr.shield > 0 {
            let cy = tr.kind != "pond" ? 158 : 164, rr = tr.kind != "pond" ? 15 : 26
            s.circle(col(Int(t * 6) % 2 == 1 ? "mint" : "sky"), x, cy, rr, width: 1)
        }
        if tr.flash > 0 && Int(t * 20) % 2 == 1 { s.circle(col("white"), x, 160, 14, width: 1) }
    }

    // ------------------------------------------------------------------ Maru
    /// Maru, the very round silver tabby.
    static func drawMaru(_ s: Surface, _ m: WindowWatch, _ t: Double) {
        let cx = Int(m.mx)
        let base = WW_SILL + 2
        let walk = m.walking
        let breath = sin(t * 2.6)
        var hop = walk ? Int(abs(sin(t * 10)) * 2) : 0
        if m.happyT > 0 { hop = Int(abs(sin(m.happyT * 14)) * 3) }
        var bw = 30 + Int(breath)
        var bh = 24 - Int(breath)
        if m.meowT > 0 { bh += 2; bw -= 1 }
        let top = base - bh - hop
        let lx = max(-2, min(2, Int((m.cx - m.mx) / 40)))
        let ly = max(-1, min(1, Int((m.cy - 120) / 30)))
        // tail (behind the body)
        let sway = sin(t * 3.2 + (m.hurtT > 0 ? 2 : 0)) * (m.hurtT <= 0 ? 4 : 7)
        for i in 0 ..< 7 {
            let a = Double(i) / 6
            s.circle(col("black"), cx + 13 + Int(a * 6) + Int(sway * a * a), base - 4 - Int(a * 14) - hop, 3)
        }
        for i in 0 ..< 7 {
            let a = Double(i) / 6
            s.circle(col(i % 2 == 0 ? "gray" : "darkgray"), cx + 13 + Int(a * 6) + Int(sway * a * a), base - 4 - Int(a * 14) - hop, 2)
        }
        // ears
        for side in [-1, 1] {
            let ex = Double(cx + side * 9), tp = Double(top), sd = Double(side)
            s.polygon(col("black"), [(ex - 5, tp + 6), (ex + sd * 2, tp - 6), (ex + 6, tp + 6)])
            s.polygon(col("gray"), [(ex - 3, tp + 5), (ex + sd * 2, tp - 3), (ex + 4, tp + 5)])
            s.polygon(col("pink"), [(ex - 1, tp + 4), (ex + sd, tp), (ex + 2, tp + 4)])
        }
        // body
        s.ellipse(col("black"), cx - bw / 2 - 1, top - 1, bw + 2, bh + 2)
        s.ellipse(col("gray"), cx - bw / 2, top, bw, bh)
        s.fillRect(col("lavender"), cx - bw / 2 + 5, top + 3, 4, 1)
        // tabby stripes: forehead M and the sides
        for dx in [-3, 0, 3] { s.fillRect(col("darkgray"), cx + dx, top + 2, 1, dx != 0 ? 3 : 4) }
        for side in [-1, 1] {
            for k in 0 ..< 2 {
                s.fillRect(col("darkgray"), cx + side * (bw / 2 - 4) - (side > 0 ? 2 : 0), top + 12 + k * 4, 3, 1)
            }
        }
        // white muzzle + bib
        s.ellipse(col("white"), cx - 8, top + 11, 17, 9)
        s.ellipse(col("white"), cx - 6, top + 17, 13, bh - 17)
        // face
        let ey = top + 8 + ly
        var mood = "happy"
        if m.hurtT > 0 { mood = "wow" } else if m.tiredT > 0 { mood = "sleepy" }
        if m.happyT > 0 || m.meowT > 0 {
            for side in [-1, 1] {      // ^ ^ eyes
                let ex = cx + side * 6 + lx
                let k = col("black")
                s.fillRect(k, ex - 2, ey + 1, 1, 1); s.fillRect(k, ex - 1, ey, 1, 1); s.fillRect(k, ex, ey - 1, 1, 1)
                s.fillRect(k, ex + 1, ey, 1, 1); s.fillRect(k, ex + 2, ey + 1, 1, 1)
            }
        } else {
            let blink = Int(t * 1.3) % 6 == 0 && (t * 1.3).truncatingRemainder(dividingBy: 1) < 0.15
            Cute.eyes(s, cx + lx, ey, 6, look: 0, mood: mood, blink: blink, size: 2)
        }
        Cute.blush(s, cx + lx, ey + 4, 7)
        s.fillRect(col("pink"), cx - 1 + lx, top + 13, 3, 2)
        if m.meowT > 0 {
            s.ellipse(col("black"), cx - 3 + lx, top + 15, 7, 6)
            s.fillRect(col("pink"), cx - 1 + lx, top + 18, 3, 2)
        } else if m.hurtT > 0 {
            Cute.mouth(s, cx + lx, top + 16, "wow")
            s.fillRect(col("sky"), cx + 12, top + 3 + Int(wwMod(m.hurtT * 10, 3)), 2, 3)
        } else {
            Cute.mouth(s, cx + lx, top + 15, "happy")
        }
        // whiskers
        for side in [-1, 1] {
            for k in [0, 2] {
                let x0 = cx + side * 9
                s.fillRect(col("white"), side > 0 ? x0 : x0 - 5, top + 13 + k, 5, 1)
            }
        }
        // paws: one goes up to swat
        for side in [-1, 1] {
            let px = cx + side * 6
            if m.swatT > 0 && side == m.swatSide {
                let f = m.swatT / 0.25
                let ax = px + side * Int(4 * f), ay = top + 8 - Int(10 * f)
                s.circle(col("black"), ax, ay, 4)
                s.circle(col("white"), ax, ay, 3)
                s.fillRect(col("pink"), ax - 1, ay, 2, 1)
            } else if m.meowT > 0 {
                s.circle(col("black"), px + side * 10, top + 10, 4)
                s.circle(col("white"), px + side * 10, top + 10, 3)
            } else {
                let step = walk ? Int(sin(t * 10 + Double(side))) : 0
                s.ellipse(col("black"), px - 4, base - 5 - step, 9, 6)
                s.ellipse(col("white"), px - 3, base - 4 - step, 7, 4)
            }
        }
        if m.tiredT > 0 && Int(t * 4) % 2 == 1 { drawText(s, "Z", cx + 14, top - 4, "lavender", shadow: nil) }
    }

    // ------------------------------------------------------------------ things
    static func drawThing(_ s: Surface, _ th: WWThing, _ t: Double, _ deco: [String]) {
        let k = th.k
        let x = Int(th.x), y = Int(th.y)
        if th.flash > 0 && Int(t * 30) % 2 == 1 {
            s.circle(col("white"), x, y, th.r + 1)
            return
        }
        switch k {
        case "drop":
            s.blit(sprite("ww_drop"), x - 3, y - 5)
        case "leaf":
            s.blit(sprite("ww_leaf", Int(th.age * 3) % 2, flip: sin(th.age * 2.2 + th.q) > 0), x - 4, y - 3)
        case "bug":
            s.blit(sprite("ww_bug", Int(t * 16) % 2, flip: th.vx < 0), x - 4, y - 3)
        case "dart":
            s.blit(sprite("ww_dart", flip: th.vx < 0), x - 6, y - 2)
        case "bubble":
            s.circle(col("blue"), x, y, 7, width: 1)
            bubble(s, Double(x), Double(y), 6, t + th.q, tint: "sky")
        case "mini":
            s.circle(col("purple"), x, y, 4, width: 1)
            bubble(s, Double(x), Double(y), 3, t, tint: "lavender")
        case "crow":
            if th.mode == 2 {
                s.blit(sprite("ww_dive"), x - 6, y - 4)
            } else {
                s.blit(sprite("ww_crow", th.mode == 0 ? Int(t * 8) % 2 : 0, flip: th.side < 0), x - 8, y - 5)
                if th.mode == 1 { drawText(s, "!", x - 2, y - 15, Int(t * 10) % 2 == 1 ? "red" : "yellow", shadow: "black") }
            }
        case "hail":
            if deco.contains("leaves") {
                s.blit(sprite("ww_acorn", remap: th.hp < 2 ? ["n": "d"] : nil), x - 3, y - 4)
            } else {
                s.blit(sprite("ww_hail", remap: th.hp < 2 ? ["w": "s"] : nil), x - 3, y - 3)
            }
        case "moth":
            s.blit(sprite("ww_moth", Int(t * 12) % 2), x - 5, y - 3)
        case "rocket":
            s.blit(sprite("ww_rocket"), x - 2, y - 5)
            for i in 0 ..< 3 {
                s.fillRect(col(["yellow", "orange", "red"][i]), x - 1 + (i % 2), y + 5 + i * 2 + Int(t * 30) % 2, 1, 2)
            }
        case "spark":
            let c = ["yellow", "white", "orange", "hotpink"][(th.id + Int(t * 12)) % 4]
            s.fillRect(col(c), x - 1, y - 1, 3, 3)
            s.fillRect(col("white"), x, y, 1, 1)
        case "snow":
            s.blit(sprite("ww_snow"), x - 4, y - 4)
            if th.hp < 2 { s.fillRect(col("sky"), x - 1, y - 3, 1, 5) }
        case "plane":
            let a = atan2(th.vy, th.vx)
            let ca = cos(a), sa = sin(a), fx = Double(x), fy = Double(y)
            let nose = (fx + ca * 6, fy + sa * 6)
            let backL = (fx - ca * 5 - sa * 4, fy - sa * 5 + ca * 4)
            let backR = (fx - ca * 5 + sa * 4, fy - sa * 5 - ca * 4)
            let mid = (fx - ca * 3, fy - sa * 3)
            s.polygon(col("black"), [(fx + ca * 8, fy + sa * 8), (fx - ca * 7 - sa * 6, fy - sa * 7 + ca * 6),
                                     (fx - ca * 4, fy - sa * 4), (fx - ca * 7 + sa * 6, fy - sa * 7 - ca * 6)])
            s.polygon(col("white"), [nose, backL, mid])
            s.polygon(col("sky"), [nose, mid, backR])
        case "puff":
            s.line(col("lime"), x, y + 2, x, y + 7)
            for i in 0 ..< 10 {
                let a = Double(i) * 0.628 + t * 0.6
                s.fillRect(col("white"), x + Int(cos(a) * 5), y + Int(sin(a) * 5), 1, 1)
                s.fillRect(col("cream"), x + Int(cos(a) * 3), y + Int(sin(a) * 3), 1, 1)
            }
            s.fillRect(col("yellow"), x - 1, y - 1, 2, 2)
        case "seed":
            s.fillRect(col("darkgray"), x - 2, y - 1, 5, 1)
            s.fillRect(col("white"), x - 2, y - 2, 5, 1)
            s.fillRect(col("white"), x, y - 3, 1, 3)
            s.fillRect(col("brown"), x, y, 1, 2)
        case "star":
            for i in 1 ... 4 {
                s.fillRect(col(["white", "yellow", "orange", "pink"][i - 1]), Int(th.x - th.vx * 0.018 * Double(i)),
                           Int(th.y - th.vy * 0.018 * Double(i)), 2, 2)
            }
            s.blit(sprite("star"), x - 3, y - 3)
        case "food":
            for (i, d) in [(-2, 0), (1, -1), (0, 2), (2, 1)].enumerated() {
                s.fillRect(col(i % 2 == 1 ? "orange" : "yellow"), x + d.0, y + d.1, 2, 1)
            }
            if Int(t * 4) % 2 == 1 { drawText(s, "FOOD", x, y - 11, "lime", align: .center, shadow: "black") }
        case "cap":
            let c = capColors[th.letter] ?? "pink"
            s.circle(col("ink"), x, y, 8, width: 1)
            bubble(s, Double(x), Double(y), 7, t, tint: c)
            drawText(s, th.letter, x - 2, y - 3, c, shadow: "black")
        case "orb":
            let r = 4 + Int(t * 12) % 2
            s.circle(col("orange"), x, y, r + 1)
            s.circle(col("yellow"), x, y, r)
            s.circle(col("white"), x - 1, y - 1, 2)
            for i in 1 ... 3 {
                s.fillRect(col("yellow"), Int(th.x - th.vx * 0.03 * Double(i)), Int(th.y - th.vy * 0.03 * Double(i)), 2, 2)
            }
        case "feather":
            s.blit(sprite("ww_feather", flip: th.vx < 0), x - 3, y - 2)
        case "treat":
            s.blit(sprite("ww_treat", flip: th.id % 2 == 0), x - 5, y - 3)
        case "gold":
            s.blit(sprite("ww_gold", flip: th.side < 0), x - 6, y - 3)
            if Int(t * 8) % 2 == 1 { s.fillRect(col("white"), x + 3 * th.side, y - 5, 1, 1) }
        case "fly":
            let glow = Int(t * 6 + Double(th.id)) % 3
            if glow != 0 {
                s.fillRect(col("lime"), x - 3, y, 7, 1)
                s.fillRect(col("lime"), x, y - 3, 1, 7)
                s.fillRect(col("yellow"), x - 1, y - 1, 3, 3)
            }
            s.fillRect(col(glow != 0 ? "lime" : "yellow"), x, y, 1, 1)
            s.fillRect(col("ink"), x, y - 2, 1, 1)
        case "rise":
            s.circle(col(th.id % 3 != 0 ? "blue" : "hotpink"), x, y, 6, width: 1)
            bubble(s, Double(x), Double(y), 5, t + th.q, tint: th.id % 3 == 0 ? "pink" : "sky")
        default:
            break
        }
    }

    static func drawPawCursor(_ s: Surface, _ fx: Double, _ fy: Double, _ t: Double, _ ready: Bool, _ color: String) {
        let x = Int(fx), y = Int(fy)
        var remap: [Character: Character]? = ready ? nil : ["w": "g"]
        if color != "white" && ready {
            remap = ["w": (["lime": "l", "yellow": "y", "pink": "p", "sky": "s"] as [String: Character])[color] ?? "w"]
        }
        s.blit(sprite("ww_paw", remap: remap), x - 4, y - 4)
        if ready && Int(t * 4) % 2 == 1 {
            for (dx, dy) in [(-9, 0), (8, 0), (0, -9), (0, 8)] { s.fillRect(col("white"), x + dx, y + dy, 1, 1) }
        }
    }

    // ------------------------------------------------------------------ preview (game carousel)
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        for i in 0 ..< h { s.fillRect(lerpCol("sky", "cream", Double(i) / Double(h)), 0, i, w, 1) }
        s.circle(col("yellow"), w - 16, 14, 7)
        let names = ["ww_drop", "ww_leaf", "ww_bug", "ww_drop", "ww_leaf"]
        for i in 0 ..< 5 {
            let x = 10 + (i * 23) % (w - 20)
            let y = Int(wwMod(t * 22 + Double(i * 17), Double(h - 20)))
            s.blit(sprite(names[i], Int(t * 4) % 2), x, y)
        }
        let cyc = wwMod(t * 1.2, 1.0)
        let rx = w / 2 + Int(sin(t * 0.7) * 26), ry = 26
        s.circle(col("white"), rx, ry, 2 + Int(cyc * 12), width: 1)
        s.blit(sprite("ww_paw"), rx - 4, ry - 4)
        s.fillRect(col("brown"), 0, h - 12, w, 12)
        s.fillRect(col("peach"), 0, h - 12, w, 1)
        for bx in [18, w - 18] {
            s.circle(col("black"), bx, h - 20, 8)
            s.circle(col("sky"), bx, h - 20, 7)
            discBelow(s, bx, h - 20, 6, h - 21, "blue")
            s.blit(sprite("ww_fish"), bx - 2, h - 18)
        }
        let cx = w / 2
        let top = h - 12 - 20 + Int(abs(sin(t * 3)))
        for side in [-1, 1] {
            let ex = Double(cx + side * 7), tp = Double(top), sd = Double(side)
            s.polygon(col("black"), [(ex - 4, tp + 5), (ex + sd * 2, tp - 5), (ex + 5, tp + 5)])
            s.polygon(col("pink"), [(ex - 2, tp + 4), (ex + sd * 2, tp - 1), (ex + 3, tp + 4)])
        }
        s.ellipse(col("black"), cx - 13, top - 1, 26, 22)
        s.ellipse(col("gray"), cx - 12, top, 24, 20)
        s.ellipse(col("white"), cx - 6, top + 9, 13, 8)
        for dx in [-2, 0, 2] { s.fillRect(col("darkgray"), cx + dx, top + 2, 1, 3) }
        Cute.eyes(s, cx, top + 7, 5, look: Int(sin(t * 0.7) * 1.5), mood: "happy", size: 2)
        s.fillRect(col("pink"), cx - 1, top + 10, 3, 1)
    }
}
