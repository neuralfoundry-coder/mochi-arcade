// Procedurally drawn cute critters, food and blocks (port of mochi_arcade/cute.py).
import Foundation

enum Cute {
    static func eyes(_ d: Surface, _ cx: Int, _ cy: Int, _ gap: Int, look: Int = 0, mood: String = "happy", blink: Bool = false, size: Int = 1) {
        let k = col("black")
        for side in [-1, 1] {
            let ex = cx + side * gap + look
            if blink || mood == "sleepy" { d.fillRect(k, ex - size, cy, size * 2 + 1, 1); continue }
            if mood == "wow" { d.circle(col("white"), ex, cy, size + 1); d.fillRect(k, ex, cy, 1, 1); continue }
            d.fillRect(k, ex - (size - 1), cy - size, size + (size - 1), size * 2)
            d.fillRect(col("white"), ex, cy - size, 1, 1)
            if mood == "angry" {
                for i in 0 ..< 3 {
                    let bx = side < 0 ? ex - 1 + i : ex + 1 - i
                    d.fillRect(k, bx, cy - size - 2 + i, 1, 1)
                }
            }
        }
    }

    static func mouth(_ d: Surface, _ cx: Int, _ cy: Int, _ mood: String = "happy") {
        let k = col("black")
        switch mood {
        case "happy":
            d.fillRect(k, cx - 1, cy, 1, 1); d.fillRect(k, cx, cy + 1, 1, 1); d.fillRect(k, cx + 1, cy, 1, 1)
        case "angry":
            d.fillRect(k, cx - 1, cy + 1, 3, 1); d.fillRect(k, cx - 2, cy + 2, 1, 1); d.fillRect(k, cx + 2, cy + 2, 1, 1)
        case "wow":
            d.circle(k, cx, cy + 1, 1)
        default:
            d.fillRect(k, cx - 1, cy, 3, 1)
        }
    }

    static func blush(_ d: Surface, _ cx: Int, _ cy: Int, _ gap: Int) {
        d.fillRect(col("pink"), cx - gap - 2, cy, 2, 1)
        d.fillRect(col("pink"), cx + gap + 1, cy, 2, 1)
    }

    static func grump(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool = false, angry: Bool = false, trapped: Bool = false) {
        let body = col(angry ? "red" : "gray"), dark = col(angry ? "hotpink" : "darkgray")
        let cx = x + 8, cy = y + 9
        let bob = trapped ? 0 : Int(sin(t * 10))
        var a = 0
        while a < 360 {
            let r = (Double(a) + t * 60) * .pi / 180
            d.circle(dark, Int(Double(cx) + cos(r) * 6), Int(Double(cy + bob) + sin(r) * 5), 3)
            a += 40
        }
        d.circle(body, cx, cy + bob, 6)
        let look = flip ? -1 : 1
        eyes(d, cx, cy - 1 + bob, 3, look: look, mood: "angry", blink: Int(t * 2) % 7 == 0)
        mouth(d, cx + look, cy + 2 + bob, "angry")
        if !trapped {
            let step = Int(t * 8) % 2
            d.fillRect(col("black"), cx - 4 + step, y + 15, 3, 1)
            d.fillRect(col("black"), cx + 2 - step, y + 15, 3, 1)
        }
    }

    static func flutter(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, flip: Bool = false, angry: Bool = false, trapped: Bool = false) {
        let cx = x + 8, cy = y + 8
        let flap = sin(t * 18)
        let wing = col(angry ? "hotpink" : "sky")
        for side in [-1, 1] {
            let wx = cx + side * (5 + Int(abs(flap)))
            d.ellipse(wing, wx - 3, cy - 6 + Int(flap * 2), 6, 7)
            d.ellipse(col("white"), wx - 2, cy - 5 + Int(flap * 2), 2, 2)
        }
        d.circle(col(angry ? "red" : "lavender"), cx, cy, 5)
        d.circle(col("black"), cx, cy, 5, width: 1)
        eyes(d, cx, cy - 1, 2, look: flip ? -1 : 1, mood: angry ? "angry" : (trapped ? "wow" : "happy"))
        d.fillRect(col("black"), cx - 3, cy - 7, 1, 2); d.fillRect(col("black"), cx + 3, cy - 7, 1, 2)
    }

    static func fruit(_ d: Surface, _ kind: Int, _ x: Int, _ y: Int) {
        let k = col("black")
        switch kind {
        case 0:
            d.line(col("lime"), x + 4, y, x + 2, y + 4); d.line(col("lime"), x + 4, y, x + 6, y + 4)
            for cx in [x + 2, x + 6] { d.circle(col("red"), cx, y + 5, 2); d.fillRect(col("white"), cx - 1, y + 4, 1, 1) }
        case 1:
            d.polygon(col("red"), [(Double(x), Double(y + 2)), (Double(x + 8), Double(y + 2)), (Double(x + 4), Double(y + 8))])
            d.circle(col("red"), x + 4, y + 3, 3)
            d.fillRect(col("lime"), x + 2, y, 5, 2)
            for (px, py) in [(x + 2, y + 3), (x + 5, y + 3), (x + 4, y + 5)] { d.fillRect(col("yellow"), px, py, 1, 1) }
        case 2:
            d.polygon(col("lime"), [(Double(x), Double(y + 2)), (Double(x + 8), Double(y + 2)), (Double(x + 4), Double(y + 8))])
            d.polygon(col("pink"), [(Double(x + 1), Double(y + 2)), (Double(x + 7), Double(y + 2)), (Double(x + 4), Double(y + 6))])
            d.fillRect(k, x + 3, y + 3, 1, 1); d.fillRect(k, x + 5, y + 3, 1, 1)
        case 3:
            d.circle(col("hotpink"), x + 4, y + 4, 3)
            d.polygon(col("yellow"), [(Double(x), Double(y + 2)), (Double(x + 2), Double(y + 4)), (Double(x), Double(y + 6))])
            d.polygon(col("yellow"), [(Double(x + 8), Double(y + 2)), (Double(x + 6), Double(y + 4)), (Double(x + 8), Double(y + 6))])
            d.fillRect(col("white"), x + 3, y + 3, 1, 1)
        case 4:
            d.fillRect(col("cream"), x, y + 3, 9, 5); d.fillRect(col("pink"), x, y + 2, 9, 2)
            d.fillRect(col("red"), x + 4, y, 2, 2); d.fillRect(col("choco"), x, y + 6, 9, 1)
        case 5:
            d.circle(col("peach"), x + 4, y + 4, 4); d.circle(col("hotpink"), x + 4, y + 4, 4, width: 2); d.circle(col("night"), x + 4, y + 4, 1)
        case 6:
            d.polygon(col("orange"), [(Double(x + 1), Double(y + 4)), (Double(x + 7), Double(y + 4)), (Double(x + 4), Double(y + 9))])
            d.circle(col("mint"), x + 4, y + 3, 3); d.fillRect(col("white"), x + 3, y + 1, 1, 1)
        default:
            d.polygon(col("white"), [(Double(x + 4), Double(y)), (Double(x + 8), Double(y + 7)), (Double(x), Double(y + 7))])
            d.fillRect(col("black"), x + 2, y + 5, 5, 3)
        }
    }

    static func jellyCell(_ d: Surface, _ x: Int, _ y: Int, _ size: Int, _ color: String, _ t: Double = 0, face: Bool = true,
                          wobble: Double = 0, ghost: Bool = false) {
        let c = col(color)
        if ghost { d.rect(c, IRect(x, y, size, size), width: 1, radius: 2); return }
        let dark = rgba(max(0, c.cr - 70), max(0, c.cg - 70), max(0, c.cb - 70))
        let light = rgba(min(255, c.cr + 60), min(255, c.cg + 60), min(255, c.cb + 60))
        d.rect(dark, IRect(x, y, size, size), radius: 2)
        d.rect(c, IRect(x, y, size, size - 1), radius: 2)
        d.fillRect(light, x + 1, y + 1, size - 3, 1)
        d.fillRect(light, x + 1, y + 1, 1, 2)
        if face && size >= 8 {
            let cx = x + size / 2, cy = y + size / 2 + Int(wobble)
            let blink = Int(t * 1.7 + Double(x) * 0.13 + Double(y) * 0.07) % 9 == 0
            let k = col("black")
            if blink { d.fillRect(k, cx - 3, cy, 2, 1); d.fillRect(k, cx + 1, cy, 2, 1) } else {
                d.fillRect(k, cx - 2, cy - 1, 1, 2); d.fillRect(k, cx + 1, cy - 1, 1, 2)
            }
            d.fillRect(k, cx - 1, cy + 2, 2, 1)
        }
    }

    static func dumpling(_ d: Surface, _ x: Int, _ y: Int, golden: Bool = false, t: Double = 0) {
        d.ellipse(col(golden ? "yellow" : "cream"), x, y + 2, 8, 6)
        d.ellipse(col("black"), x, y + 2, 8, 6, width: 1)
        for i in 0 ..< 3 { d.fillRect(col(golden ? "orange" : "peach"), x + 2 + i * 2, y + 2 - (i % 2), 1, 2) }
        d.fillRect(col("black"), x + 2, y + 5, 1, 1); d.fillRect(col("black"), x + 5, y + 5, 1, 1)
        d.fillRect(col("pink"), x + 1, y + 6, 1, 1); d.fillRect(col("pink"), x + 6, y + 6, 1, 1)
        if golden && Int(t * 8) % 2 == 1 { d.fillRect(col("white"), x + 6, y + 1, 1, 1) }
    }

    static func spaceJelly(_ d: Surface, _ x: Int, _ y: Int, _ t: Double, _ kind: Int = 0, hit: Bool = false) {
        let k = col("black")
        if kind == 2 {
            let cx = x + 8, cy = y + 7
            d.circle(col(hit ? "white" : "purple"), cx, cy, 7)
            d.circle(k, cx, cy, 7, width: 1)
            d.polygon(col("yellow"), [(Double(cx - 4), Double(cy - 6)), (Double(cx - 2), Double(cy - 9)), (Double(cx), Double(cy - 6)),
                                      (Double(cx + 2), Double(cy - 9)), (Double(cx + 4), Double(cy - 6))])
            eyes(d, cx, cy, 3, mood: hit ? "angry" : "happy")
            mouth(d, cx, cy + 3, hit ? "angry" : "happy")
            return
        }
        if kind == 0 {
            let cx = x + 6, cy = y + 5
            d.ellipse(col(hit ? "white" : "sky"), x + 1, y, 10, 9)
            d.ellipse(k, x + 1, y, 10, 9, width: 1)
            for i in 0 ..< 4 {
                let wig = Int(sin(t * 10 + Double(i)))
                d.fillRect(col("blue"), x + 2 + i * 2 + wig, y + 9, 1, 3)
            }
            eyes(d, cx, cy - 1, 2)
            blush(d, cx, cy + 1, 2)
            return
        }
        let cx = x + 6, cy = y + 6
        let flap = Int(sin(t * 16) * 2)
        for side in [-1, 1] { d.ellipse(col("pink"), cx + side * 4 - 2, cy - 4 + flap, 5, 6) }
        d.circle(col(hit ? "white" : "hotpink"), cx, cy, 4)
        d.circle(k, cx, cy, 4, width: 1)
        eyes(d, cx, cy - 1, 2, mood: "wow")
    }

    static func brick(_ d: Surface, _ r: IRect, _ kind: String, hp: Int = 1) {
        let pal: [String: (String, String)] = ["cookie": ("peach", "brown"), "candy": ("pink", "hotpink"), "mint": ("mint", "teal"),
                                               "lemon": ("yellow", "orange"), "berry": ("lavender", "purple"),
                                               "choco": ("brown", "choco"), "tin": ("gray", "darkgray")]
        let (light, dark) = pal[kind] ?? ("white", "gray")
        d.rect(col(dark), r, radius: 2)
        d.rect(col(light), r.inflate(-2, -2), radius: 2)
        switch kind {
        case "cookie":
            for (dx, dy) in [(3, 2), (8, 4), (12, 2)] { d.fillRect(col("choco"), r.x + dx, r.y + dy, 2, 1) }
        case "candy":
            var i = 3
            while i < r.w - 2 { d.fillRect(col("white"), r.x + i, r.y + 2, 2, r.h - 4); i += 4 }
        case "choco":
            d.fillRect(col(dark), r.centerx, r.y + 1, 1, r.h - 2)
            if hp < 2 { d.line(col("black"), r.x + 3, r.y + 2, r.x + 7, r.bottom - 3) }
        case "tin":
            d.fillRect(col("white"), r.x + 2, r.y + 2, r.w - 4, 1)
        default:
            d.fillRect(col("white"), r.x + 2, r.y + 2, 3, 1)
        }
    }
}
