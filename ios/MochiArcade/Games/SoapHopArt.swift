// SOAP HOP art: the new dust critters, the six bosses, items and upgrade icons (port of games/soap_hop_art.py).
// Item sprites (sh_chest, sh_soda ...) come from the Python ART table through GeneratedData.swift.
import Foundation

private func pts(_ p: [(Int, Int)]) -> [(Double, Double)] { p.map { (Double($0.0), Double($0.1)) } }

enum SHArt {
    // ------------------------------------------------------------------ critters (16x16 boxes)
    static func fluff(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, _ body: String, _ dark: String, flip: Bool = false,
                      mood: String = "angry", trapped: Bool = false, feet: Bool = true) {
        let cx = x + 8, cy = y + 9
        let bob = trapped ? 0 : Int(sin(t * 10))
        var a = 0
        while a < 360 {
            let r = (Double(a) + t * 60) * .pi / 180
            d.circle(col(dark), Int(Double(cx) + cos(r) * 6), Int(Double(cy + bob) + sin(r) * 5), 3)
            a += 40
        }
        d.circle(col(body), cx, cy + bob, 6)
        let look = flip ? -1 : 1
        Cute.eyes(d, cx, cy - 1 + bob, 3, look: look, mood: mood, blink: Int(t * 2) % 7 == 0)
        Cute.mouth(d, cx + look, cy + 2 + bob, mood)
        if feet && !trapped {
            let step = Int(t * 8) % 2
            d.fillRect(col("black"), cx - 4 + step, y + 15, 3, 1)
            d.fillRect(col("black"), cx + 2 - step, y + 15, 3, 1)
        }
    }

    static func golden(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool, trapped: Bool) {
        fluff(d, x, y, t, "yellow", "orange", flip: flip, mood: "happy", trapped: trapped)
        if Int(t * 6) % 3 == 0 { d.fillRect(col("white"), x + 3 + Int(t * 7) % 10, y + 3, 1, 1) }
    }

    static func boing(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool, angry: Bool, trapped: Bool, squash: Int) {
        let cx = x + 8, by = y + 6 + squash
        if !trapped {
            for i in 0 ..< 3 {
                let yy = y + 11 + squash + i * (2 - squash / 2)
                d.fillRect(col(i % 2 == 1 ? "gray" : "white"), cx - 3, yy, 7, 1)
            }
            d.fillRect(col("black"), cx - 3, y + 15, 7, 1)
        }
        d.circle(col(angry ? "red" : "lime"), cx, by, 6)
        d.circle(col(angry ? "hotpink" : "teal"), cx, by, 6, width: 1)
        d.fillRect(col(angry ? "hotpink" : "teal"), cx - 1, by - 8, 1, 2)
        d.fillRect(col(angry ? "hotpink" : "teal"), cx + 1, by - 9, 1, 3)
        let look = flip ? -1 : 1
        Cute.eyes(d, cx, by - 1, 2, look: look, mood: angry ? "angry" : (trapped ? "wow" : "happy"))
        Cute.mouth(d, cx + look, by + 2, squash == 0 && !trapped ? "wow" : "happy")
    }

    static func zoomy(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool, angry: Bool, trapped: Bool, dash: Bool, rev: Bool) {
        let cx = x + 8, cy = y + 9
        let look = flip ? -1 : 1
        let jit = rev ? Int(t * 30) % 2 : 0
        if dash && !trapped {
            for (i, yy) in [cy - 3, cy, cy + 3].enumerated() {
                let ln = 4 + (i % 2) * 3
                d.fillRect(col("white"), cx - look * 8 - (look > 0 ? ln : 0), yy, ln, 1)
            }
        }
        d.polygon(col(angry ? "hotpink" : "red"), pts([(cx - look * 5, cy - 4), (cx - look * 10, cy - 7), (cx - look * 7, cy),
                                                     (cx - look * 11, cy + 2), (cx - look * 5, cy + 3)]))
        d.ellipse(col(angry ? "red" : "orange"), cx - 6 + jit, cy - 5, 13, 11)
        d.ellipse(col("brown"), cx - 6 + jit, cy - 5, 13, 11, width: 1)
        Cute.eyes(d, cx + look + jit, cy - 1, 2, look: look, mood: "angry")
        Cute.mouth(d, cx + look * 2 + jit, cy + 2, trapped ? "wow" : "angry")
        if !trapped {
            let step = Int(t * (dash ? 16 : 8)) % 2
            d.fillRect(col("black"), cx - 4 + step, y + 15, 3, 1)
            d.fillRect(col("black"), cx + 2 - step, y + 15, 3, 1)
        }
    }

    static func liddy(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool, angry: Bool, trapped: Bool, lid: Bool) {
        fluff(d, x, y, t, angry ? "red" : "sky", angry ? "hotpink" : "blue", flip: flip, mood: "angry", trapped: trapped)
        if lid {
            let bob = trapped ? 0 : Int(sin(t * 10))
            d.ellipse(col("gray"), x, y + 1 + bob, 16, 6)
            d.ellipse(col("darkgray"), x, y + 1 + bob, 16, 6, width: 1)
            d.fillRect(col("white"), x + 3, y + 2 + bob, 5, 1)
            d.fillRect(col("darkgray"), x + 7, y - 1 + bob, 3, 2)
        }
    }

    static func sneezy(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool, angry: Bool, trapped: Bool, swell: Double) {
        let cx = x + 8, cy = y + 9
        let look = flip ? -1 : 1
        let r = 6 + Int(swell * 2)
        let bob = trapped ? 0 : Int(sin(t * 8))
        d.circle(col(angry ? "red" : "pink"), cx, cy + bob, r)
        d.circle(col("hotpink"), cx, cy + bob, r, width: 1)
        Cute.eyes(d, cx - look, cy - 2 + bob, 2, look: look, mood: swell > 0.5 ? "sleepy" : (angry ? "angry" : "happy"))
        d.circle(col(angry ? "orange" : "hotpink"), cx + look * (r - 1), cy + 1 + bob, 2)
        d.fillRect(col("white"), cx + look * (r - 1), cy + bob, 1, 1)
        if !trapped {
            let step = Int(t * 6) % 2
            d.fillRect(col("black"), cx - 4 + step, y + 15, 3, 1)
            d.fillRect(col("black"), cx + 2 - step, y + 15, 3, 1)
        }
    }

    static func wisp(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool, angry: Bool, trapped: Bool) {
        let cx = x + 8, cy = y + 7
        let sway = Int(sin(t * 6) * 2)
        let body = angry ? "purple" : "darkgray"
        d.polygon(col(body), pts([(cx - 5, cy), (cx + 5, cy), (cx + 2 + sway, cy + 7), (cx + sway, cy + 9), (cx - 2 + sway, cy + 6)]))
        d.circle(col(body), cx, cy, 5)
        d.circle(col(angry ? "hotpink" : "black"), cx, cy, 5, width: 1)
        let look = flip ? -1 : 1
        d.fillRect(col("white"), cx - 3 + look, cy - 1, 2, 2)
        d.fillRect(col("white"), cx + 1 + look, cy - 1, 2, 2)
        if trapped { d.fillRect(col("black"), cx - 1, cy + 2, 2, 1) }
    }

    /// Draw any enemy kind at the 16x16 box (x, y). e: the enemy (per-kind state) or nil.
    static func critter(_ d: Surface, _ kind: String, _ x: Int, _ y: Int, _ t: Double, flip: Bool = false, angry: Bool = false,
                        trapped: Bool = false, _ e: SHEnemy? = nil) {
        if let e = e, e.golden { golden(d, x, y, t, flip: flip, trapped: trapped); return }
        switch kind {
        case "g": Cute.grump(d, x, y, t, flip: flip, angry: angry, trapped: trapped)
        case "f": Cute.flutter(d, x, y, t, flip: flip, angry: angry, trapped: trapped)
        case "b": boing(d, x, y, t, flip: flip, angry: angry, trapped: trapped, squash: (e?.onGround ?? false) && !trapped ? 2 : 0)
        case "z": zoomy(d, x, y, t, flip: flip, angry: angry, trapped: trapped, dash: e?.mode == "dash", rev: e?.mode == "rev")
        case "s": liddy(d, x, y, t, flip: flip, angry: angry, trapped: trapped, lid: e?.lid ?? true)
        case "p": sneezy(d, x, y, t, flip: flip, angry: angry, trapped: trapped, swell: e != nil && !trapped ? e!.swell : 0)
        default: wisp(d, x, y, t, flip: flip, angry: angry, trapped: trapped)
        }
    }

    // ------------------------------------------------------------------ bosses (centre x, y)
    private static func c(_ name: String, _ flash: Bool) -> Color { col(flash ? "white" : name) }

    static func king(_ d: Surface, _ cx: Int, _ cy: Int, _ t: Double, squash: Double, flash: Bool, phase: Int) {
        let rw = Int(14 + squash * 5), rh = Int(13 - squash * 5)
        for i in 0 ..< 12 {
            let a = Double(i) * 2 * .pi / 12 + t * 0.8
            d.circle(c(phase < 3 ? "darkgray" : "hotpink", flash), Int(Double(cx) + cos(a) * Double(rw)), Int(Double(cy) + sin(a) * Double(rh)), 5)
        }
        d.ellipse(c(phase < 3 ? "gray" : "red", flash), cx - rw, cy - rh, rw * 2, rh * 2)
        for side in [-1, 1] {
            d.ellipse(c("gray", flash), cx + side * 7 - 3, cy - rh - 12, 6, 13)
            d.ellipse(c("pink", flash), cx + side * 7 - 1, cy - rh - 9, 2, 8)
        }
        let top = cy - rh - 2
        d.polygon(c("yellow", flash), pts([(cx - 8, top + 4), (cx - 8, top - 4), (cx - 4, top), (cx, top - 6), (cx + 4, top),
                                           (cx + 8, top - 4), (cx + 8, top + 4)]))
        d.fillRect(c("red", flash), cx - 1, top - 1, 3, 3)
        Cute.eyes(d, cx, cy - 2, 6, look: 0, mood: "angry", size: 2)
        Cute.mouth(d, cx, cy + 4, "angry")
        Cute.blush(d, cx, cy + 2, 8)
    }

    static func mop(_ d: Surface, _ cx: Int, _ cy: Int, _ t: Double, lift: Double, flash: Bool, walk: Double, phase: Int) {
        let step = Int(walk * 6) % 2
        d.fillRect(c("darkgray", flash), cx - 9, cy + 13 - step, 6, 5)
        d.fillRect(c("darkgray", flash), cx + 3, cy + 13 - (1 - step), 6, 5)
        d.polygon(c(phase < 3 ? "sky" : "lavender", flash), pts([(cx - 14, cy - 10), (cx + 14, cy - 10), (cx + 10, cy + 14), (cx - 10, cy + 14)]))
        d.fillRect(c("blue", flash), cx - 12, cy + 2, 24, 3)
        d.fillRect(c("white", flash), cx - 15, cy - 12, 30, 3)
        d.fillRect(c("gray", flash), cx - 15, cy - 9, 30, 1)
        Cute.eyes(d, cx, cy - 4, 5, look: 0, mood: "angry", size: 2)
        Cute.mouth(d, cx, cy + 6, "angry")
        let hx = cx + 15, hy = cy - 2
        let tx: Int, ty: Int
        if lift >= 0 { tx = hx + Int(8 - lift * 8); ty = hy - 22 - Int(lift * 8) } else { tx = hx + 22; ty = hy + 14 }
        d.line(c("brown", flash), hx, hy, tx, ty, width: 2)
        for i in -3 ... 3 {
            let ex = tx + i * 2 + (lift < 0.5 ? Int(sin(t * 9 + Double(i))) : 0)
            let ey = lift >= 0 ? ty - 7 : ty + 6
            d.line(c("cream", flash), tx, ty, ex, ey)
        }
        d.circle(c("cream", flash), tx, ty, 3)
    }

    static func vac(_ d: Surface, _ cx: Int, _ cy: Int, _ t: Double, inhale: Double, flash: Bool, phase: Int) {
        let shade = phase < 3 ? "gray" : "purple"
        for (dx, dy, r) in [(-11, 3, 9), (11, 3, 9), (0, 5, 10)] { d.circle(c(shade, flash), cx + dx, cy + dy, r) }
        for (dx, dy, r) in [(-11, 0, 9), (11, 0, 9), (0, -6, 11), (0, 2, 10)] { d.circle(c("lavender", flash), cx + dx, cy + dy, r) }
        Cute.eyes(d, cx, cy - 4, 5, look: 0, mood: "angry", size: 2)
        let mr = 3 + Int(inhale * 3)
        d.circle(col("night"), cx, cy + 6, mr)
        d.circle(c("darkgray", flash), cx, cy + 6, mr, width: 1)
        if inhale > 0 {
            for i in 0 ..< 6 {
                let a = Double(i) * 2 * .pi / 6 - t * 7
                let r1 = 14 + (t * 40 + Double(i * 5)).truncatingRemainder(dividingBy: 12)
                let x1 = Double(cx) + cos(a) * r1, y1 = Double(cy + 6) + sin(a) * r1
                d.line(col("white"), Int(x1), Int(y1), Int(x1 + cos(a + 1.2) * 3), Int(y1 + sin(a + 1.2) * 3))
            }
        }
    }

    static func sockSeg(_ d: Surface, _ x: Int, _ y: Int, _ i: Int, flash: Bool) {
        d.circle(c(i % 2 == 0 ? "hotpink" : "white", flash), x, y, 6)
        d.circle(c("purple", flash), x, y, 6, width: 1)
    }

    static func sockHead(_ d: Surface, _ cx: Int, _ cy: Int, _ t: Double, face: Int, lunge: Bool, flash: Bool) {
        d.circle(c("hotpink", flash), cx, cy, 8)
        d.fillRect(c("white", flash), cx - 7, cy - 3, 15, 2)
        d.circle(c("purple", flash), cx, cy, 8, width: 1)
        Cute.eyes(d, cx + face, cy - 2, 3, look: face, mood: lunge ? "wow" : "angry", size: 1)
        if lunge {
            d.line(col("red"), cx + face * 4, cy + 4, cx + face * 9, cy + 5 + Int(sin(t * 30) * 2))
        } else {
            Cute.mouth(d, cx + face, cy + 3, "angry")
        }
    }

    static func soot(_ d: Surface, _ cx: Int, _ cy: Int, _ t: Double, charge: Double, flash: Bool, phase: Int) {
        for (dx, dy, r) in [(-12, 2, 9), (12, 2, 9), (0, -5, 12), (-5, 4, 9), (6, 4, 9)] {
            d.circle(c(phase < 3 ? "darkgray" : "purple", flash), cx + dx, cy + dy, r)
        }
        for (dx, dy, r) in [(-12, 0, 7), (0, -7, 9), (12, 0, 7)] { d.circle(c("gray", flash), cx + dx, cy + dy, r) }
        for side in [-1, 1] {
            d.fillRect(col("yellow"), cx + side * 5 - 1, cy - 3, 3, 3)
            d.fillRect(col("black"), cx + side * 5 - 2 + (side < 0 ? 1 : 0), cy - 5, 3, 1)
        }
        d.fillRect(col("black"), cx - 3, cy + 4, 7, 1)
        if charge > 0 && Int(t * 12) % 2 == 1 {
            d.polygon(col("yellow"), pts([(cx - 2, cy - 18), (cx + 4, cy - 18), (cx, cy - 13), (cx + 3, cy - 13), (cx - 4, cy - 6),
                                          (cx - 1, cy - 12), (cx - 4, cy - 12)]))
        }
    }

    static func grime(_ d: Surface, _ cx: Int, _ cy: Int, _ t: Double, squash: Double, flash: Bool, phase: Int) {
        let rw = Int(19 + squash * 6), rh = Int(17 - squash * 6)
        for i in 0 ..< 14 {
            let a = Double(i) * 2 * .pi / 14 - t * 0.6
            d.circle(c(phase < 3 ? "choco" : "purple", flash), Int(Double(cx) + cos(a) * Double(rw)), Int(Double(cy) + sin(a) * Double(rh)), 6)
        }
        d.ellipse(c("brown", flash), cx - rw, cy - rh, rw * 2, rh * 2)
        for (dx, dy) in [(-10, 6), (9, 8), (-4, 11), (12, -2)] { d.circle(c("choco", flash), cx + dx, cy + dy, 2) }
        let top = cy - rh - 3
        d.ellipse(c("gray", flash), cx - 11, top - 4, 22, 8)
        d.ellipse(c("darkgray", flash), cx - 11, top - 4, 22, 8, width: 1)
        for i in 0 ..< 4 { d.fillRect(col("darkgray"), cx - 6 + i * 4, top - 1, 2, 2) }
        Cute.eyes(d, cx, cy - 3, 7, look: 0, mood: "angry", size: 2)
        d.fillRect(col("black"), cx - 6, cy + 5, 13, 3)
        for i in 0 ..< 3 { d.fillRect(col("white"), cx - 5 + i * 4, cy + 5, 2, 2) }
    }

    // ------------------------------------------------------------------ items / letters
    static func item(_ d: Surface, _ kind: String, _ sub: Int, _ x: Int, _ y: Int, _ t: Double) {
        switch kind {
        case "snack": Cute.fruit(d, sub, x, y)
        case "heart": d.blit(sprite("heart"), x, y + 1)
        case "shield":
            bubble(d, Double(x + 4), Double(y + 4), 5, t, tint: "mint")
            d.fillRect(col("white"), x + 3, y + 3, 2, 2)
        default:
            let sp = sprite("sh_" + kind)
            d.blit(sp, x + 4 - sp.w / 2, y + 8 - sp.h)
        }
    }

    static func letterBubble(_ d: Surface, _ x: Double, _ y: Double, _ ch: String, _ t: Double) {
        bubble(d, x, y, 9, t, tint: "yellow")
        drawText(d, ch, Int(x) - 2, Int(y) - 3, "yellow", outline: "ink")
    }

    // ------------------------------------------------------------------ upgrade icons
    static func iconRange(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        bubble(s, Double(cx - 4), Double(cy), 5, t)
        drawText(s, "}", cx + 2, cy - 3, "white", shadow: nil)
    }

    static func iconRate(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        for i in 0 ..< 3 { bubble(s, Double(cx - 6 + i * 6), Double(cy + (i % 2) * 2 - 1), 3, t) }
    }

    static func iconTrap(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        Cute.grump(s, cx - 8, cy - 9, t, trapped: true)
        bubble(s, Double(cx), Double(cy), 9, t, tint: "lavender")
    }

    static func iconSpeed(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        let sp = sprite("sh_shoe")
        s.blit(sp, cx - sp.w / 2, cy - sp.h / 2)
        s.fillRect(col("white"), cx - 9, cy - 1, 3, 1)
        s.fillRect(col("white"), cx - 10, cy + 2, 4, 1)
    }

    static func iconJump(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        drawText(s, "|", cx - 6, cy - 3, "yellow", shadow: nil)
        drawText(s, "|", cx + 1, cy - 5 + Int(sin(t * 6)), "yellow", shadow: nil)
    }

    static func iconHeart(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) { s.blit(sprite("heart"), cx - 3, cy - 3) }

    static func iconChain(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        for (dx, dy) in [(-5, 3), (5, 3), (0, -5)] { bubble(s, Double(cx + dx), Double(cy + dy), 4, t, tint: "orange") }
    }

    static func iconMagnet(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        s.fillRect(col("red"), cx - 6, cy - 5, 4, 9)
        s.fillRect(col("red"), cx + 2, cy - 5, 4, 9)
        s.fillRect(col("red"), cx - 6, cy + 2, 12, 4)
        s.fillRect(col("white"), cx - 6, cy - 6, 4, 2)
        s.fillRect(col("white"), cx + 2, cy - 6, 4, 2)
    }

    static func iconShield(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        s.blit(sprite("momo_idle", 0), cx - 8, cy - 8)
        bubble(s, Double(cx), Double(cy), 10, t, tint: "mint")
    }

    static func iconTwin(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        bubble(s, Double(cx - 3), Double(cy + 3), 4, t)
        bubble(s, Double(cx + 4), Double(cy - 4), 4, t)
    }
}
