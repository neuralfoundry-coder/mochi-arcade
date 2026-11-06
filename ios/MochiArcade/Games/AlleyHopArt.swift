// ALLEY HOP art (port of mochi_arcade/games/alley_hop_art.py): Sushi the calico cat, kittens, traffic, canal
// floaters, laundry, boxes and props. Sprites (ah_*) come from the Python module through GeneratedData.swift.
import Foundation

private let AH_COATS: [Character] = ["o", "g", "d", "c", "w", "e"]
let AH_SHEET_COLORS = ["white", "pink", "sky", "yellow", "mint", "lavender", "peach"]

enum AHArt {
    // ------------------------------------------------------------------ heroes
    /// Sushi's ringed tail (white with an orange band and a dark tip), drawn behind the body.
    static func tail(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ face: String, _ wag: Double = 1) {
        let sway = sin(t * 5) * 2 * wag
        if face == "left" || face == "right" {
            let d = face == "right" ? -1 : 1
            let bx = x + 8 + d * 7, by = y + 9
            for i in 0 ..< 5 {
                let px = bx + d * (i / 2)
                let py = by - i - Int(sway * Double(i) / 4)
                let c = i < 2 ? "white" : (i < 4 ? "orange" : "choco")
                s.fillRect(col("black"), px - 1, py, 3, 2)
                s.fillRect(col(c), px, py, 1, 1)
            }
        } else {
            let bx = x + 12, by = y + 13
            for i in 0 ..< 5 {
                let px = bx + i / 2 + Int(sway * Double(i) / 5)
                let py = by - i
                let c = i < 2 ? "white" : (i < 4 ? "orange" : "choco")
                s.fillRect(col("black"), px - 1, py - 1, 3, 3)
                s.fillRect(col(c), px, py, 1, 1)
            }
        }
    }

    /// Sushi with her top-left at (x, y). face: up/down/left/right. mood: "" | happy | hurt.
    static func sushi(_ s: Surface, _ x: Int, _ y0: Int, _ t: Double, _ face: String = "up", _ mood: String = "",
                      _ hop: Double = 0, flash: Bool = false) {
        if flash && Int(t * 20) % 2 == 1 { return }
        let lift = hop > 0 ? Int(sin(Double.pi * hop) * 5) : 0
        if hop > 0 { s.ellipse(col("black"), x + 3, y0 + 13, 10, 3) }
        let y = y0 - lift
        var fr: Int
        if mood == "happy" { fr = 5 } else if mood == "hurt" { fr = 6 } else if face == "up" { fr = 2 } else if face == "left" || face == "right" {
            fr = (hop > 0 && hop < 0.6) ? 4 : 3
        } else {
            fr = Int(t * 1.3) % 6 == 0 ? 1 : 0
        }
        if mood == "" && face != "down" { tail(s, x, y, t, face, hop > 0 ? 2 : 1) }
        s.blit(sprite("ah_sushi", fr, flip: face == "left"), x, y)
    }

    /// A kitten centred at cx with its feet on by. mood: "" | wow | happy | sleepy
    static func kitten(_ s: Surface, _ cx: Double, _ by: Double, _ coat: Int, _ t: Double, _ mood: String = "",
                       _ hop: Double = 0, _ seed: Int = 0, flash: Bool = false) {
        if flash && Int(t * 20) % 2 == 1 { return }
        var lift = hop > 0 ? Int(sin(Double.pi * hop) * 4) : 0
        if mood == "happy" { lift = max(lift, Int(abs(sin(t * 8 + Double(seed))) * 2)) }
        let x = Int(cx) - 5, y = Int(by) - 9 - lift
        if hop > 0 { s.fillRect(col("black"), Int(cx) - 3, Int(by) - 1, 7, 1) }
        let blink = Int(t * 1.1 + Double(seed) * 0.37) % 5 == 0
        let fr = mood == "wow" ? 2 : ((mood == "sleepy" || blink) ? 1 : 0)
        s.blit(sprite("ah_kit", fr, remap: ["o": AH_COATS[ahImod(coat, 6)]]), x, y)
    }

    // ------------------------------------------------------------------ traffic
    static func bike(_ s: Surface, _ X: Int, _ y0: Int, _ d: Int, _ t: Double, _ tint: String = "sky") {
        for wx in [X + 3, X + 12] {
            s.circle(col("black"), wx, y0 + 12, 3)
            s.circle(col("gray"), wx, y0 + 12, 2, width: 1)
        }
        s.line(col(tint), X + 3, y0 + 12, X + 7, y0 + 8)
        s.line(col(tint), X + 7, y0 + 8, X + 12, y0 + 12)
        s.line(col(tint), X + 7, y0 + 8, X + 9, y0 + 12)
        let hx = d > 0 ? X + 13 : X + 2
        s.fillRect(col("gray"), hx - 1, y0 + 6, 3, 1)
        s.fillRect(col("orange"), X + 6, y0 + 5, 4, 4)
        s.circle(col("peach"), X + 8 + d * 2, y0 + 3, 2)
        s.fillRect(col(tint), X + 6 + d * 2, y0, 5, 2)
        s.fillRect(col("black"), X + 8 + d * 3, y0 + 3, 1, 1)
        s.fillRect(col("yellow"), d > 0 ? X + 15 : X, y0 + 9, 1, 2)
    }

    static func scooter(_ s: Surface, _ X: Int, _ y0: Int, _ d: Int, _ t: Double, _ tint: String = "red") {
        for wx in [X + 4, X + 19] {
            s.circle(col("black"), wx, y0 + 12, 3)
            s.fillRect(col("gray"), wx, y0 + 12, 1, 1)
        }
        s.ellipse(col(tint), X + 2, y0 + 6, 20, 7)
        s.fillRect(col("white"), X + 6, y0 + 7, 10, 1)
        let bx = d > 0 ? X + 1 : X + 15
        s.fillRect(col("black"), bx - 1, y0 + 1, 10, 7)
        s.fillRect(col("yellow"), bx, y0 + 2, 8, 5)
        s.fillRect(col("red"), bx + 2, y0 + 4, 4, 1)
        let rx = X + 12 + d * 2
        s.fillRect(col("blue"), rx - 2, y0 + 3, 5, 4)
        s.circle(col("peach"), rx + d, y0 + 2, 2)
        s.fillRect(col("white"), rx - 1 + d, y0, 4, 2)
        s.fillRect(col("yellow"), d > 0 ? X + 23 : X, y0 + 7, 1, 3)
    }

    static func can(_ s: Surface, _ X: Int, _ y0: Int, _ d: Int, _ t: Double, _ tint: String = "gray") {
        let bob = Int(abs(sin(t * 9 + Double(X) * 0.1)) * 2)
        let y = y0 + 3 - bob
        s.rect(col("black"), IRect(X, y, 14, 11), radius: 3)
        s.rect(col(tint), IRect(X + 1, y + 1, 12, 9), radius: 2)
        let roll = ahImod(Int(t * 14 * Double(d)), 4)
        for i in 0 ..< 3 { s.fillRect(col("darkgray"), X + 2 + (i * 4 + roll) % 11, y + 1, 1, 9) }
        s.fillRect(col("white"), X + 3, y + 2, 6, 1)
        s.fillRect(col("darkgray"), d > 0 ? X + 13 : X, y - 1, 1, 13)
        if Int(t * 6) % 2 == 1 { s.fillRect(col("lime"), X + 6, y - 2, 1, 1) }
    }

    static func van(_ s: Surface, _ X: Int, _ y0: Int, _ d: Int, _ t: Double, _ tint: String = "cream") {
        s.rect(col("black"), IRect(X, y0 + 1, 40, 12), radius: 3)
        s.rect(col(tint), IRect(X + 1, y0 + 2, 38, 10), radius: 2)
        s.fillRect(col("orange"), X + 1, y0 + 9, 38, 2)
        let wx = d > 0 ? X + 30 : X + 3
        s.fillRect(col("sky"), wx, y0 + 3, 7, 4)
        s.fillRect(col("white"), wx + 1, y0 + 3, 2, 1)
        let bx = d > 0 ? X + 12 : X + 20
        s.ellipse(col("red"), bx, y0 + 5, 9, 4)
        s.fillRect(col("yellow"), bx + 2, y0 + 4, 5, 1)
        if Int(t * 4) % 2 == 1 { s.fillRect(col("white"), bx + 4, y0 + 2, 1, 2) }
        for wx2 in [X + 8, X + 31] {
            s.circle(col("black"), wx2, y0 + 13, 3)
            s.fillRect(col("gray"), wx2, y0 + 13, 1, 1)
        }
        s.fillRect(col("yellow"), d > 0 ? X + 39 : X, y0 + 4, 1, 3)
    }

    static func pigeon(_ s: Surface, _ X: Int, _ y0: Int, _ d: Int, _ t: Double, _ tint: String = "gray") {
        let bob = Int(t * 8) % 2
        s.ellipse(col("black"), X, y0 + 5, 12, 8)
        s.ellipse(col(tint), X + 1, y0 + 6, 10, 6)
        let hx = d > 0 ? X + 9 : X + 2
        s.circle(col("lavender"), hx, y0 + 5 + bob, 2)
        s.fillRect(col("black"), hx, y0 + 4 + bob, 1, 1)
        s.fillRect(col("orange"), hx + d * 2, y0 + 5 + bob, 1, 1)
        s.fillRect(col("orange"), X + 4 + bob, y0 + 13, 1, 2)
        s.fillRect(col("orange"), X + 7 - bob, y0 + 13, 1, 2)
    }

    static let traffic: Set<String> = ["bike", "scooter", "can", "van", "pigeon"]
    static let tints: [String: [String]] = ["bike": ["sky", "lime", "pink", "mint"], "scooter": ["red", "teal", "purple", "orange"],
                                            "can": ["gray", "teal", "lavender", "gray"], "van": ["cream", "white", "peach", "pink"],
                                            "pigeon": ["gray", "gray", "lavender", "gray"]]

    static func drawTraffic(_ s: Surface, _ kind: String, _ X: Int, _ y0: Int, _ d: Int, _ t: Double, _ i: Int = 0) {
        let tint = tints[kind]![ahImod(i, 4)]
        switch kind {
        case "bike": bike(s, X, y0, d, t, tint)
        case "scooter": scooter(s, X, y0, d, t, tint)
        case "can": can(s, X, y0, d, t, tint)
        case "van": van(s, X, y0, d, t, tint)
        default: pigeon(s, X, y0, d, t, tint)
        }
    }

    /// x of the headlight (for the dark stages) of a vehicle at screen x X moving in d.
    static func headlight(_ kind: String, _ X: Double, _ d: Int) -> Double {
        let w: Double = ["bike": 16, "scooter": 24, "can": 14, "van": 40, "pigeon": 12][kind] ?? 16
        return d > 0 ? X + w + 6 : X - 6
    }

    // ------------------------------------------------------------------ floaters
    static func crate(_ s: Surface, _ X: Int, _ y0: Int, _ w: Int, _ t: Double) {
        let bob = Int(t * 2 + Double(X) * 0.05) % 2 != 0 ? 1 : 0
        for i in 0 ..< w / 16 {
            let x = X + i * 16
            s.fillRect(col("choco"), x + 1, y0 + 2 + bob, 14, 12)
            s.fillRect(col("brown"), x + 2, y0 + 3 + bob, 12, 10)
            s.line(col("choco"), x + 2, y0 + 3 + bob, x + 13, y0 + 12 + bob)
            s.line(col("choco"), x + 13, y0 + 3 + bob, x + 2, y0 + 12 + bob)
            s.fillRect(col("peach"), x + 2, y0 + 3 + bob, 12, 1)
        }
        s.fillRect(col("sky"), X, y0 + 14, w, 1)
    }

    /// A mother duck leading her ducklings; state up | tell | down (diving).
    static func ducks(_ s: Surface, _ X: Int, _ y0: Int, _ w: Int, _ d: Int, _ t: Double, _ state: String = "up") {
        let n = (w - 16) / 12
        if state == "down" {
            for i in 0 ... n {
                let cx = X + 8 + i * 12
                s.fillRect(col("sky"), cx - 4, y0 + 11, 8, 1)
                if Int(t * 6 + Double(i)) % 2 == 1 { s.fillRect(col("white"), cx, y0 + 9, 1, 1) }
            }
            return
        }
        let shake = state == "tell" ? Int(sin(t * 30) * 1) : 0
        let mx = d > 0 ? X + w - 8 : X + 8
        var order: [(Int, Bool)] = [(mx, true)]
        for i in 0 ..< n { order.append((d > 0 ? X + w - 22 - 12 * i : X + 22 + 12 * i, false)) }
        for (cx0, big) in order {
            let cx = cx0 + shake
            if big {
                s.ellipse(col("black"), cx - 7, y0 + 5, 14, 9)
                s.ellipse(col("white"), cx - 6, y0 + 6, 12, 7)
                let hx = cx + d * 4
                s.circle(col("black"), hx, y0 + 4, 3)
                s.circle(col("white"), hx, y0 + 4, 2)
                s.fillRect(col("orange"), hx + d * 2 - (d < 0 ? 1 : 0), y0 + 4, 2, 1)
                s.fillRect(col("black"), hx + d, y0 + 3, 1, 1)
            } else {
                s.ellipse(col("black"), cx - 5, y0 + 7, 10, 7)
                s.ellipse(col("yellow"), cx - 4, y0 + 8, 8, 5)
                s.circle(col("yellow"), cx + d * 3, y0 + 7, 2)
                s.fillRect(col("orange"), cx + d * 5 - (d < 0 ? 1 : 0), y0 + 7, 1, 1)
            }
            s.fillRect(col("sky"), cx - 6, y0 + 14, 12, 1)
        }
        if state == "tell" && Int(t * 8) % 2 == 1 { drawText(s, "!", mx - 2, y0 - 6, "yellow", shadow: "black") }
    }

    /// A big sleepy koi floating along (kittens nap on it). Dives when it wakes up.
    static func fish(_ s: Surface, _ X: Int, _ y0: Int, _ w: Int, _ d: Int, _ t: Double, _ state: String = "up") {
        if state == "down" {
            s.fillRect(col("orange"), X + w / 2 - 2, y0 + 10, 5, 2)
            s.fillRect(col("sky"), X + 4, y0 + 12, w - 8, 1)
            return
        }
        let shake = state == "tell" ? Int(sin(t * 30) * 1) : 0
        let x = X + shake
        s.ellipse(col("black"), x + 3, y0 + 4, w - 8, 10)
        s.ellipse(col("white"), x + 4, y0 + 5, w - 10, 8)
        for i in 0 ..< 3 { s.fillRect(col("orange"), x + 8 + i * 9, y0 + 6 + i % 2, 5, 3) }
        let tx = d > 0 ? x + 1 : x + w - 6
        let pts: [(Double, Double)] = d > 0
            ? [(Double(tx), Double(y0 + 4)), (Double(tx + 5), Double(y0 + 9)), (Double(tx), Double(y0 + 13))]
            : [(Double(tx + 5), Double(y0 + 4)), (Double(tx), Double(y0 + 9)), (Double(tx + 5), Double(y0 + 13))]
        s.polygon(col("orange"), pts)
        let ex = d > 0 ? x + w - 12 : x + 9
        s.fillRect(col("black"), ex, y0 + 7, 3, 1)
        s.fillRect(col("sky"), X + 2, y0 + 14, w - 4, 1)
        if state == "tell" {
            if Int(t * 8) % 2 == 1 { drawText(s, "!", ex - 1, y0 - 6, "yellow", shadow: "black") }
        } else if Int(t * 1.5 + Double(X) * 0.01) % 3 == 0 {
            drawText(s, "Z", ex + d * 4, y0 - 4 - Int(t * 4) % 3, "lavender", shadow: nil)
        }
    }

    static func sheet(_ s: Surface, _ X: Int, _ y0: Int, _ w: Int, _ t: Double, _ i: Int) {
        let c = AH_SHEET_COLORS[ahImod(i, AH_SHEET_COLORS.count)]
        let flap = Int(sin(t * 3 + Double(i)) * 1.5)
        s.fillRect(col("black"), X - 1, y0 + 2, w + 2, 13 + flap)
        s.fillRect(col(c), X, y0 + 3, w, 11 + flap)
        var k = 4
        while k < w {
            s.fillRect(col(c != "white" ? "white" : "sky"), X + k, y0 + 5 + (k / 8) % 2 * 3, 2, 1)
            k += 8
        }
        s.fillRect(col("brown"), X + 2, y0 + 1, 2, 3)
        s.fillRect(col("brown"), X + w - 4, y0 + 1, 2, 3)
    }

    static func tray(_ s: Surface, _ X: Int, _ y0: Int, _ t: Double, _ i: Int) {
        s.fillRect(col("black"), X, y0 + 4, 16, 9)
        s.fillRect(col("cream"), X + 1, y0 + 5, 14, 7)
        s.fillRect(col(i % 2 == 1 ? "orange" : "pink"), X + 3, y0 + 7, 10, 3)
    }

    // ------------------------------------------------------------------ props
    /// Static obstacles on sidewalks: 0 chimney, 1 trash bin, 2 flower pot, 3 hydrant.
    static func block(_ s: Surface, _ x: Int, _ y0: Int, _ kind: Int, _ t: Double) {
        switch kind {
        case 0:
            s.fillRect(col("black"), x + 2, y0, 12, 15)
            s.fillRect(col("red"), x + 3, y0 + 3, 10, 11)
            for yy in [y0 + 6, y0 + 10] { s.fillRect(col("choco"), x + 3, yy, 10, 1) }
            s.fillRect(col("darkgray"), x + 1, y0, 14, 3)
            if Int(t * 2 + Double(x)) % 4 == 0 { s.fillRect(col("gray"), x + 7, y0 - 3, 2, 2) }
        case 1:
            s.rect(col("black"), IRect(x + 2, y0 + 2, 12, 13), radius: 2)
            s.fillRect(col("teal"), x + 3, y0 + 4, 10, 10)
            s.fillRect(col("gray"), x + 2, y0 + 2, 12, 2)
            s.fillRect(col("mint"), x + 5, y0 + 6, 1, 6)
        case 2:
            s.fillRect(col("black"), x + 3, y0 + 8, 10, 7)
            s.fillRect(col("orange"), x + 4, y0 + 9, 8, 5)
            s.circle(col("lime"), x + 8, y0 + 6, 4)
            for (fx, fy, c) in [(x + 6, y0 + 4, "pink"), (x + 10, y0 + 6, "yellow"), (x + 7, y0 + 7, "hotpink")] {
                s.fillRect(col(c), fx, fy, 2, 2)
            }
        default:
            s.fillRect(col("black"), x + 4, y0 + 3, 8, 12)
            s.fillRect(col("red"), x + 5, y0 + 4, 6, 10)
            s.fillRect(col("black"), x + 2, y0 + 7, 12, 3)
            s.fillRect(col("red"), x + 3, y0 + 8, 10, 1)
            s.fillRect(col("pink"), x + 6, y0 + 5, 1, 4)
        }
    }

    /// A cozy cardboard box in the home row (x = cell left). nIn kittens peek out.
    static func box(_ s: Surface, _ x: Int, _ y0: Int, _ nIn: Int, _ t: Double, closed: Bool = false, warn: Bool = false,
                    glow: Bool = false) {
        if glow { s.rect(col("yellow"), IRect(x - 1, y0 + 1, 18, 15), width: 1) }
        s.fillRect(col("black"), x + 1, y0 + 5, 14, 11)
        s.fillRect(col("brown"), x + 2, y0 + 6, 12, 9)
        s.fillRect(col("choco"), x + 2, y0 + 12, 12, 1)
        if closed {
            s.fillRect(col("black"), x, y0 + 3, 16, 3)
            s.fillRect(col("peach"), x + 1, y0 + 4, 14, 1)
            s.fillRect(col("yellow"), x + 7, y0 + 3, 2, 4)
            if warn && Int(t * 8) % 2 == 1 { s.fillRect(col("red"), x + 6, y0, 4, 2) }
            return
        }
        let flap = Int(sin(t * 3 + Double(x)) * 1)
        s.fillRect(col("peach"), x - 1, y0 + 4 + flap, 4, 2)
        s.fillRect(col("peach"), x + 13, y0 + 4 - flap, 4, 2)
        for i in 0 ..< min(nIn, 3) {
            let hx = x + 4 + i * 4
            s.circle(col(["orange", "gray", "cream"][i]), hx, y0 + 5, 2)
            s.fillRect(col("black"), hx - 1, y0 + 4, 1, 1)
            s.fillRect(col("black"), hx + 1, y0 + 4, 1, 1)
        }
        if nIn > 3 { drawText(s, "\(nIn)", x + 8, y0 + 7, "yellow", align: .center, shadow: "black") }
        if warn && Int(t * 8) % 2 == 1 { s.fillRect(col("red"), x + 6, y0, 4, 2) }
    }

    static func puddle(_ s: Surface, _ x: Int, _ y0: Int, _ t: Double) {
        s.ellipse(col("blue"), x + 1, y0 + 5, 14, 8)
        s.ellipse(col("sky"), x + 3, y0 + 7, 9, 4, width: 1)
        let k = Int(t * 3 + Double(x)) % 5
        if k < 2 { s.fillRect(col("white"), x + 5 + k * 3, y0 + 8, 1, 1) }
    }

    static func manhole(_ s: Surface, _ x: Int, _ y0: Int, _ t: Double) {
        s.ellipse(col("black"), x + 1, y0 + 4, 14, 10)
        s.ellipse(col("gray"), x + 2, y0 + 5, 12, 8)
        s.ellipse(col("darkgray"), x + 4, y0 + 7, 8, 4, width: 1)
        if Int(t * 2 + Double(x)) % 3 == 0 { s.fillRect(col("lime"), x + 7, y0 + 2, 2, 1) }
    }

    static func item(_ s: Surface, _ kind: String, _ cx: Double, _ cy: Double, _ t: Double) {
        let bob = Int(sin(t * 4 + cx * 0.3) * 1.5)
        let name = ["fish": "ah_fish", "gold": "ah_goldfish", "yarn": "ah_yarn", "clock": "ah_clock", "nip": "ah_nip",
                    "bell": "ah_bell", "box": "ah_boxitem", "heart": "heart"][kind] ?? "ah_fish"
        let sp = sprite(name)
        if ["gold", "nip", "bell", "box", "heart"].contains(kind) && Int(t * 6) % 2 == 1 {
            s.fillRect(col("white"), Int(cx) + 5, Int(cy) - 7 + bob, 1, 1)
        }
        s.blit(sp, Int(cx) - sp.w / 2, Int(cy) - sp.h / 2 + bob)
    }

    /// A night express: engine + lit carriages. front = x of the leading edge.
    static func train(_ s: Surface, _ front: Double, _ y0: Int, _ length: Double, _ d: Int, _ t: Double) {
        let ncar = (Int(length) - 40) / 48
        for i in 0 ... ncar {
            var cx: Double, cw: Int
            if i == 0 {
                cx = d > 0 ? front - 40 : front
                cw = 40
            } else {
                cx = d > 0 ? front - 40 - 48 * Double(i) : front + 40 + 48 * Double(i - 1)
                cw = 46
            }
            let ix = Int(cx)
            s.fillRect(col("black"), ix, y0, cw, 16)
            s.fillRect(col(i == 0 ? "red" : "teal"), ix + 1, y0 + 1, cw - 2, 13)
            s.fillRect(col("white"), ix + 1, y0 + 10, cw - 2, 1)
            if i == 0 {
                let wx = ix + (d > 0 ? 26 : 6)
                s.fillRect(col("sky"), wx, y0 + 3, 8, 5)
                s.fillRect(col("yellow"), ix + (d > 0 ? 38 : 1), y0 + 6, 1, 3)
            } else {
                for k in 0 ..< 4 { s.fillRect(col((k + i) % 3 != 0 ? "yellow" : "cream"), ix + 4 + k * 11, y0 + 3, 7, 5) }
            }
        }
    }

    static func signal(_ s: Surface, _ x: Int, _ y0: Int, _ t: Double, _ on: Bool) {
        s.fillRect(col("black"), x, y0 + 2, 6, 13)
        s.fillRect(col("darkgray"), x + 1, y0 + 3, 4, 11)
        let a = on && Int(t * 6) % 2 == 0
        let b = on && Int(t * 6) % 2 == 1
        s.fillRect(col(a ? "red" : "choco"), x + 1, y0 + 4, 2, 2)
        s.fillRect(col(b ? "red" : "choco"), x + 3, y0 + 4, 2, 2)
        s.fillRect(col("white"), x + 2, y0 + 8, 2, 1)
    }

    static func gate(_ s: Surface, _ x: Int, _ y0: Int, _ t: Double, _ opn: Bool, _ warn: Bool) {
        if opn {
            s.fillRect(col("brown"), x, y0 + 2, 2, 13)
            s.fillRect(col("brown"), x + 14, y0 + 2, 2, 13)
            if warn && Int(t * 8) % 2 == 1 { s.fillRect(col("red"), x + 6, y0 + 1, 4, 2) }
            return
        }
        s.fillRect(col("black"), x, y0 + 1, 16, 15)
        s.fillRect(col("orange"), x + 1, y0 + 2, 14, 13)
        var k = 3
        while k < 15 { s.fillRect(col("brown"), x + k, y0 + 2, 1, 13); k += 4 }
        s.fillRect(col("yellow"), x + 7, y0 + 7, 2, 2)
    }

    /// Nearest-neighbour resize (pygame.transform.scale) for the falling animation.
    static func scaled(_ src: Surface, _ w: Int, _ h: Int) -> Surface {
        let out = Surface(w, h)
        for y in 0 ..< out.h {
            for x in 0 ..< out.w { out.px[y * out.w + x] = src.px[(y * src.h / out.h) * src.w + x * src.w / out.w] }
        }
        return out
    }
}
