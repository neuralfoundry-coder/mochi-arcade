// WHISKER MAZE art (port of games/whisker_maze_art.py): Nori (pixel sprites from GeneratedData, drawn with her
// lavender rim), the dust bots, floor items and the bosses (drawn with primitives so they can look, wobble and flash).
import Foundation

enum WMArt {
    static let rim: [Character: Character] = ["k": "v", "d": "v", "y": "v", "w": "v", "p": "v", "r": "v", "o": "v"]
    static let flashMap: [Character: Character] = ["k": "w", "d": "w"]

    // ------------------------------------------------------------------ Nori
    /// (sprite name, frame, flip, bob) for Nori's current pose.
    static func noriPose(_ d: (Int, Int), _ t: Double, _ moving: Bool, _ mood: String) -> (String, Int, Bool, Int) {
        if mood == "hurt" { return ("wm_hurt", 0, false, 0) }
        if mood == "happy" { return ("wm_happy", 0, false, 0) }
        if !moving { return ("wm_sit", Int(t * 1.3) % 6 == 0 ? 2 : Int(t * 2) % 2, false, 0) }
        let f = Int(t * 9) % 2
        let bob = f == 1 ? -1 : 0
        if d.0 != 0 { return ("wm_side", f, d.0 < 0, bob) }
        if d.1 < 0 { return ("wm_up", f, false, bob) }
        return ("wm_down", f, false, bob)
    }

    static func nori(_ s: Surface, _ cx: Double, _ cy: Double, _ d: (Int, Int), _ t: Double, _ moving: Bool,
                     _ mood: String = "", flash: Bool = false) {
        let (name, f, flip, bob) = noriPose(d, t, moving, mood)
        let x = Int(cx) - 6, y = Int(cy) - 6 + bob
        let r = sprite(name, f, flip: flip, remap: rim)
        for (ox, oy) in [(-1, 0), (1, 0), (0, -1), (0, 1)] { s.blit(r, x + ox, y + oy) }
        s.blit(sprite(name, f, flip: flip, remap: flash ? flashMap : nil), x, y)
    }

    // ------------------------------------------------------------------ dust bots
    static let botColors: [String: (String, String, String)] = [
        "sniffy": ("peach", "brown", "pink"), "zig": ("lime", "teal", "yellow"), "fridgy": ("sky", "blue", "white"),
        "snoozy": ("lavender", "purple", "yellow"), "mopsy": ("mint", "teal", "white"), "spritz": ("pink", "hotpink", "sky"),
        "ruff": ("orange", "brown", "choco"), "bunny": ("gray", "darkgray", "white"),
    ]

    /// A dust bot centred at (cx, cy). state: "" | dizzy | sleep | alert | frozen | tired | aim.
    static func bot(_ s: Surface, _ kind: String, _ cx: Int, _ cy: Int, _ t: Double, look: (Int, Int) = (0, 0),
                    state: String = "", flash: Bool = false) {
        if state == "dizzy" {
            let wob = Int(sin(t * 18 + Double(cx)) * 1.5)
            botBody(s, kind, cx + wob, cy, t, (0, 0), "dizzy")
            if !flash {
                for i in 0 ..< 3 {
                    let a = t * 6 + Double(i) * 2.09
                    let sx = Int(Double(cx) + cos(a) * 6), sy = Int(Double(cy - 10) + sin(a) * 2)
                    s.fillRect(col("yellow"), sx - 1, sy, 3, 1)
                    s.fillRect(col("yellow"), sx, sy - 1, 1, 3)
                }
            }
            return
        }
        botBody(s, kind, cx, cy, t, look, state)
    }

    private static func botBody(_ s: Surface, _ kind: String, _ cx: Int, _ cy: Int, _ t: Double, _ look: (Int, Int), _ state: String) {
        var (body, dark, acc) = botColors[kind] ?? ("gray", "darkgray", "white")
        if state == "frozen" { (body, dark, acc) = ("sky", "blue", "white") }
        let k = col("black")
        let bob = ["sleep", "frozen", "puck"].contains(state) ? 0 : Int(sin(t * 12 + Double(cx)))
        let (lx, ly) = look
        let y = cy + bob
        switch kind {
        case "fridgy":
            let r = IRect(cx - 5, y - 7, 11, 13)
            s.rect(k, r.inflate(2, 2), radius: 3)
            s.rect(col(body), r, radius: 3)
            s.fillRect(col(dark), r.x, y - 1, r.w, 1)
            s.fillRect(col(acc), r.right - 3, y - 5, 1, 3)
            s.fillRect(col(acc), r.right - 3, y + 1, 1, 3)
            eyes(s, cx - 1 + lx, y - 4 + ly, state, t)
            s.fillRect(k, cx - 4, y + 6, 3, 1)
            s.fillRect(k, cx + 2, y + 6, 3, 1)
            return
        case "spritz":
            func pt(_ a: Int, _ b: Int) -> (Double, Double) { (Double(a), Double(b)) }
            s.polygon(k, [pt(cx - 5, y + 6), pt(cx + 5, y + 6), pt(cx + 4, y - 3), pt(cx - 4, y - 3)])
            s.polygon(col(body), [pt(cx - 4, y + 5), pt(cx + 4, y + 5), pt(cx + 3, y - 2), pt(cx - 3, y - 2)])
            s.fillRect(k, cx - 3, y - 7, 7, 5)
            s.fillRect(col(dark), cx - 2, y - 6, 5, 3)
            let nx = lx >= 0 ? cx + 4 : cx - 6
            s.fillRect(col(acc), nx, y - 6, 3, 2)
            s.fillRect(col("white"), cx - 3, y + 1, 1, 3)
            eyes(s, cx + lx, y + ly, state, t, gap: 2)
            return
        case "ruff":
            s.circle(k, cx, y + 1, 7)
            s.circle(col(body), cx, y + 1, 6)
            s.circle(col(acc), cx, y + 1, 6, width: 1)
            let flop = Int(sin(t * 10))
            for side in [-1, 1] { s.ellipse(col(dark), cx + side * 6 - 2, y - 4 + flop, 4, 7) }
            let wag = Int(sin(t * 18) * 2)
            s.fillRect(col(dark), cx - lx * 7 + wag - 1, y - 6, 2, 3)
            eyes(s, cx + lx, y + ly, state, t)
            s.fillRect(k, cx - 1 + lx, y + 3, 3, 2)
            return
        case "bunny":
            var a = 0
            while a < 360 {
                let rr = (Double(a) + t * 90) * .pi / 180
                s.circle(col(dark), cx + Int(cos(rr) * 4), y + Int(sin(rr) * 3), 2)
                a += 60
            }
            s.circle(col(body), cx, y, 4)
            eyes(s, cx + lx, y - 1 + ly, state, t, gap: 1)
            return
        default: break
        }
        s.ellipse(k, cx - 7, y - 6, 15, 13)
        s.ellipse(col(body), cx - 6, y - 5, 13, 11)
        s.fillRect(col(dark), cx - 5, y + 3, 11, 1)
        switch kind {
        case "sniffy":
            s.fillRect(col(acc), cx - 1 + lx * 3, y + 1 + ly, 3, 2)
            s.fillRect(k, cx + lx * 3, y + 1 + ly, 1, 1)
            s.fillRect(col(dark), cx, y - 9, 1, 3)
            s.fillRect(col(acc), cx - 1, y - 10, 3, 2)
        case "zig":
            let pts = [(cx - 4, y - 5), (cx - 1, y - 2), (cx + 1, y - 4), (cx + 4, y - 1)]
            for i in 0 ..< 3 { s.line(col(acc), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1) }
        case "snoozy":
            s.polygon(col(acc), [(Double(cx - 5), Double(y - 4)), (Double(cx + 4), Double(y - 5)), (Double(cx + 8), Double(y - 9))])
            s.fillRect(col("white"), cx + 7, y - 10, 2, 2)
        case "mopsy":
            var i = -6
            while i <= 6 { s.fillRect(col(acc), cx + i, y + 5 + ((i / 2) % 2 + 2) % 2, 1, 3); i += 2 }
        default: break
        }
        eyes(s, cx + lx, y - 1 + ly, state, t)
    }

    private static func eyes(_ s: Surface, _ x: Int, _ y: Int, _ state: String, _ t: Double, gap: Int = 3) {
        let k = col("black")
        if state == "sleep" {
            s.fillRect(k, x - gap - 1, y, 3, 1)
            s.fillRect(k, x + gap - 1, y, 3, 1)
            return
        }
        if state == "dizzy" {
            for side in [-1, 1] {
                let a = t * 14 * Double(side)
                let ex = x + side * gap
                s.fillRect(col("white"), ex - 1, y - 1, 3, 3)
                s.fillRect(k, ex + Int(cos(a) * 1.5), y + Int(sin(a) * 1.5), 1, 1)
            }
            return
        }
        if state == "tired" || state == "frozen" {
            for side in [-1, 1] {
                s.fillRect(k, x + side * gap - 1, y, 3, 1)
                s.fillRect(k, x + side * gap, y + 1, 1, 1)
            }
            return
        }
        let red = state == "alert" || state == "aim"
        for side in [-1, 1] {
            let ex = x + side * gap
            s.fillRect(col("white"), ex - 1, y - 1, 3, 3)
            if red {
                s.fillRect(col("red"), ex - 1, y - 1, 3, 3)
                s.fillRect(col("white"), ex - 1, y - 1, 1, 1)
            } else {
                s.fillRect(k, ex, y, 1, 1)
            }
        }
    }

    /// Lights-out stages: bots' red eyes glow in the dark.
    static func led(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        let c = col(Int(t * 4) % 2 == 1 ? "red" : "hotpink")
        s.fillRect(c, cx - 4, cy - 1, 2, 2)
        s.fillRect(c, cx + 2, cy - 1, 2, 2)
    }

    /// A batted bot flying home to its dock: a spinning shell with sparks.
    static func reboot(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
        s.circle(col("darkgray"), cx, cy, 4)
        s.circle(col("gray"), cx, cy, 4, width: 1)
        let a = t * 20
        s.fillRect(col("yellow"), cx + Int(cos(a) * 6), cy + Int(sin(a) * 6), 1, 1)
        s.fillRect(col("sky"), cx - Int(cos(a) * 6), cy - Int(sin(a) * 6), 1, 1)
    }

    // ------------------------------------------------------------------ floor items
    static func crumb(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, fever: Bool, _ i: Int) {
        if fever { s.fillRect(col(rainbow(i, t)), x - 1, y - 1, 2, 2); return }
        s.fillRect(col("cream"), x - 1, y - 1, 2, 2)
        s.fillRect(col("peach"), x, y, 1, 1)
    }

    /// A fish-bone treat on a paw-print passage.
    static func secret(_ s: Surface, _ x: Int, _ y: Int, _ t: Double) {
        let c = col("white")
        s.fillRect(c, x - 3, y, 6, 1)
        s.fillRect(c, x - 2, y - 1, 1, 3)
        s.fillRect(c, x, y - 1, 1, 3)
        s.fillRect(col(Int(t * 4) % 2 == 1 ? "yellow" : "white"), x + 3, y - 1, 1, 3)
    }

    /// Paw prints on a cat-only wall tile.
    static func paws(_ s: Surface, _ x: Int, _ y: Int, _ glow: Bool, _ t: Double) {
        let c = col(glow && Int(t * 6) % 2 == 1 ? "yellow" : glow ? "lavender" : "gray")
        for (px, py) in [(x + 2, y + 5), (x + 6, y + 2)] {
            s.fillRect(c, px, py, 2, 2)
            s.fillRect(c, px - 1, py - 2, 1, 1)
            s.fillRect(c, px + 1, py - 2, 1, 1)
            s.fillRect(c, px + 2, py - 1, 1, 1)
        }
    }

    // ------------------------------------------------------------------ bosses
    static let bossLook: [String: (String, String, String)] = [
        "queen": ("pink", "hotpink", "yellow"), "slipper": ("pink", "peach", "white"), "snap": ("brown", "choco", "yellow"),
        "toaster": ("gray", "darkgray", "orange"), "bucket": ("sky", "blue", "white"), "empress": ("yellow", "orange", "white"),
    ]

    /// Big boss centred at (cx, cy) (about 32x26). mood: "" | angry | stun. wind: 0..1 attack wind-up.
    static func boss(_ s: Surface, _ kind: String, _ cx0: Int, _ cy: Int, _ t: Double, mood: String = "", flash: Bool = false,
                     wind: Double = 0) {
        var (body, dark, acc) = bossLook[kind] ?? ("pink", "hotpink", "yellow")
        if flash { body = "white"; dark = "white" }
        let k = col("black")
        let cx = Int(Double(cx0) + (wind > 0.5 ? sin(t * 50) * 2 : 0))
        let em = mood == "angry" || wind > 0 ? "angry" : (mood == "stun" ? "wow" : "happy")
        func p(_ a: Int, _ b: Int) -> (Double, Double) { (Double(a), Double(b)) }
        switch kind {
        case "queen", "empress":
            s.ellipse(k, cx - 17, cy - 8, 35, 20)
            s.ellipse(col(dark), cx - 16, cy - 6, 33, 17)
            s.ellipse(col(body), cx - 16, cy - 8, 33, 15)
            s.ellipse(col("white"), cx - 10, cy - 6, 8, 3)
            var i = -12
            while i <= 12 {
                let a = t * 16 + Double(i)
                s.fillRect(col("gray"), cx + i + Int(cos(a)), cy + 10, 1, 2)
                i += 4
            }
            let cc = col(kind == "queen" ? "yellow" : "white")
            s.polygon(cc, [p(cx - 7, cy - 8), p(cx - 7, cy - 14), p(cx - 4, cy - 10), p(cx, cy - 16), p(cx + 4, cy - 10),
                           p(cx + 7, cy - 14), p(cx + 7, cy - 8)])
            s.fillRect(col("red"), cx - 1, cy - 12, 2, 2)
            if kind == "empress" {
                s.fillRect(col("sky"), cx - 6, cy - 11, 1, 1)
                s.fillRect(col("sky"), cx + 6, cy - 11, 1, 1)
            }
            Cute.eyes(s, cx, cy - 2, 5, look: 0, mood: em, size: 2)
            Cute.mouth(s, cx, cy + 3, em == "angry" ? "angry" : "happy")
        case "slipper":
            s.ellipse(k, cx - 17, cy - 8, 35, 20)
            s.ellipse(col(body), cx - 16, cy - 7, 33, 18)
            s.ellipse(col(dark), cx - 16, cy + 4, 33, 7)
            s.ellipse(col("hotpink"), cx + 2, cy - 7, 14, 12)
            var a = 0
            while a < 360 {
                let rr = (Double(a) + t * 40) * .pi / 180
                s.circle(col(acc), cx + 9 + Int(cos(rr) * 3), cy - 9 + Int(sin(rr) * 3), 2)
                a += 45
            }
            s.circle(col(acc), cx + 9, cy - 9, 3)
            Cute.eyes(s, cx - 6, cy - 1, 4, look: 0, mood: em, size: 2)
            Cute.mouth(s, cx - 6, cy + 4, em != "happy" ? "angry" : "flat")
            for i in 0 ..< 3 { s.fillRect(col("white"), cx - 14 + i * 3, cy + 7, 1, 1) }
        case "snap":
            let r = IRect(cx - 16, cy - 4, 32, 14)
            s.rect(k, r.inflate(2, 2), radius: 2)
            s.rect(col(body), r, radius: 2)
            var i = r.x + 2
            while i < r.right - 2 { s.fillRect(col(dark), i, r.y + 2, 3, 1); i += 5 }
            let openA = wind == 0 ? 0.5 + 0.5 * sin(t * 4) : 1.0 - wind
            let barY = cy - 4 - Int(10 * openA)
            s.line(col("gray"), cx - 14, cy - 4, cx - 14, barY, width: 2)
            s.line(col("gray"), cx + 14, cy - 4, cx + 14, barY, width: 2)
            s.line(col("white"), cx - 14, barY, cx + 14, barY, width: 2)
            s.polygon(col(acc), [p(cx + 6, cy - 4), p(cx + 13, cy - 4), p(cx + 13, cy - 9)])
            s.fillRect(col("orange"), cx + 10, cy - 6, 1, 1)
            var j = -14
            while j <= 14 { s.fillRect(col("darkgray"), cx + j + Int(t * 20) % 4, cy + 11, 2, 2); j += 4 }
            Cute.eyes(s, cx - 3, cy + 3, 4, look: 0, mood: em, size: 2)
        case "toaster":
            let r = IRect(cx - 15, cy - 8, 30, 20)
            s.rect(k, r.inflate(2, 2), radius: 5)
            s.rect(col(body), r, radius: 5)
            s.fillRect(col("white"), r.x + 3, r.y + 2, 3, 12)
            for sx in [cx - 8, cx + 2] {
                let pop = Int(abs(sin(t * 3 + Double(sx))) * 3) + Int(wind * 4)
                s.rect(col("peach"), IRect(sx, cy - 13 - pop, 7, 7), radius: 2)
                s.fillRect(col("brown"), sx, cy - 13 - pop, 7, 1)
            }
            s.fillRect(col(dark), r.x, r.bottom - 4, r.w, 2)
            s.fillRect(col(acc), r.right - 4, cy - 2, 2, 5)
            Cute.eyes(s, cx - 2, cy + 1, 5, look: 0, mood: em, size: 2)
            Cute.mouth(s, cx - 2, cy + 6, em != "happy" ? "angry" : "happy")
        default:    // bucket
            s.polygon(k, [p(cx - 15, cy - 7), p(cx + 15, cy - 7), p(cx + 12, cy + 13), p(cx - 12, cy + 13)])
            s.polygon(col(body), [p(cx - 14, cy - 6), p(cx + 14, cy - 6), p(cx + 11, cy + 12), p(cx - 11, cy + 12)])
            s.fillRect(col(dark), cx - 13, cy - 3, 26, 2)
            s.line(col("gray"), cx - 13, cy - 7, cx - 8, cy - 14)
            s.line(col("gray"), cx - 8, cy - 14, cx + 8, cy - 14)
            s.line(col("gray"), cx + 8, cy - 14, cx + 13, cy - 7)
            var i = -8
            while i <= 8 {
                let sway = Int(sin(t * 6 + Double(i)) * 2)
                s.line(col(acc), cx + i, cy - 7, cx + i + sway, cy - 14)
                i += 3
            }
            Cute.eyes(s, cx, cy + 3, 5, look: 0, mood: em, size: 2)
            Cute.mouth(s, cx, cy + 8, em != "happy" ? "angry" : "happy")
        }
        if mood == "stun" {
            for i in 0 ..< 3 {
                let a = t * 6 + Double(i) * 2.1
                s.fillRect(col("yellow"), cx + Int(cos(a) * 14), cy - 16 + Int(sin(a) * 3), 2, 2)
            }
        }
    }
}
