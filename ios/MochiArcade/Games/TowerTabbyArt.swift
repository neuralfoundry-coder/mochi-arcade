// TOWER TABBY entities and drawing helpers (port of the classes and module-level draw functions of
// games/tower_tabby.py - keep in step). Pixel sprites (tt_*) come from tower_tabby_art.py via GeneratedData.
import Foundation

let TT_HUD_H = 11
let TT_FLOOR = 192.0
let TT_YARN_COLORS = ["pink", "sky", "lime", "lavender", "yellow", "mint", "peach"]
let TT_KITTEN_COLORS: [[Character: Character]] = [["g": "g"], ["g": "w"], ["g": "d", "p": "p"], ["g": "c"], ["g": "e"]]
let TT_GOLD_FISH: [Character: Character] = ["s": "y", "w": "w"]

// ---------------------------------------------------------------------- the cat tree
/// Something you can stand on: a shelf segment or a hammock.
class TTPlat {}

/// A run of shelf cells of one kind: plank | bed | box | belt (dir -1/1).
final class TTSeg: TTPlat {
    let x0, x1, k, slope: Int
    let kind: String
    let belt: Int
    var stand = 0.0, gone = 0.0, boing = 0.0
    init(_ x0: Int, _ x1: Int, _ k: Int, _ slope: Int, _ kind: String, _ belt: Int = 0) {
        self.x0 = x0; self.x1 = x1; self.k = k; self.slope = slope; self.kind = kind; self.belt = belt
    }
    func y(_ x: Double) -> Double { TT_LEVEL_Y[k] + Double(slope) * TT_TILT * (x - 160) / 160.0 }
}

final class TTPost {
    let x, k: Int
    let rope: Bool
    let top, bot: Double
    init(_ x: Int, _ k: Int, _ rope: Bool, _ slopes: [Int]) {
        self.x = x; self.k = k; self.rope = rope
        top = ttYAt(k + 1, slopes[k + 1], Double(x))
        let b = ttYAt(k, slopes[k], Double(x))
        bot = rope ? b - 15 : b
    }
}

/// A hammock riding back and forth over a run of '~' cells (32 px wide).
final class TTHam: TTPlat {
    let xa, xb: Double
    let k: Int
    let period, phase: Double
    var x = 0.0, dx = 0.0, y: Double
    var x0 = 0.0, x1 = 0.0
    init(_ xa: Double, _ xb: Double, _ k: Int, _ phase: Double) {
        self.xa = xa; self.xb = xb; self.k = k; self.phase = phase
        period = max(2.0, 2.0 * (xb - xa) / 34.0)
        y = TT_LEVEL_Y[k]
        super.init()
        x = pos(0)
        x0 = x; x1 = x + 32
    }
    func pos(_ t: Double) -> Double { xa + (xb - xa) * (0.5 - 0.5 * cos(2 * .pi * (t / period + phase))) }
    func update(_ t: Double) {
        let nx = pos(t)
        dx = nx - x
        x = nx
        x0 = x; x1 = x + 32
    }
}

protocol TTBody: AnyObject {
    var x: Double { get set }
    var y: Double { get set }
    var vx: Double { get set }
    var vy: Double { get set }
    var ground: TTPlat? { get set }
}

final class TTPlayer: TTBody {
    var x, y: Double                    // centre x, feet y
    var vx = 0.0, vy = 0.0
    var ground: TTPlat?
    var face = 1
    var climb: TTPost?
    var pounce = false, pounceT = 0.0
    var boost = false                   // bounced by a bed or cushion: the jump-height cut does not apply
    var pcd = 0.0
    var airPounce = true
    var coyote = 0.0, jbuf = 0.0
    var inv = 2.0
    var warpT = 0.0
    var warpTo: (Int, Int)?
    var anim = 0.0, swipe = 0.0
    var trail: [(Double, Double)] = []
    init(_ x: Double, _ y: Double) { self.x = x; self.y = y }
}

final class TTHaz: TTBody {
    let kind: String
    var x, y, r: Double
    var vx = 0.0, vy = 0.0
    var ground: TTPlat?
    var dir = Bool.random() ? 1 : -1
    var age = 0.0, life = 16.0
    var dead = false, jumped = false, batted = false
    var spin = 0.0
    var color = TT_YARN_COLORS.randomElement()!
    var t = Double.random(in: 0 ... 6.28)
    var cool = Double.random(in: 1.0 ... 2.5)
    var mode = ""
    var k = 0
    var ay: Double                      // anchor y: spider thread top, moth cruise height, cushion landing
    var stun = 0.0
    var post: TTPost?
    var cdir = 0
    var harmless = false, gold = false
    var path: [(Double, Double)] = []
    init(_ kind: String, _ x: Double, _ y: Double, _ r: Double) {
        self.kind = kind; self.x = x; self.y = y; self.r = r; ay = y
    }
}

final class TTShot {
    let kind: String
    var x, y, vx, vy, r, warn, life: Double
    var age = 0.0
    var dead = false, batted = false
    var k = -1
    init(_ kind: String, _ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ r: Double = 2, _ warn: Double = 0,
         _ life: Double = 6) {
        self.kind = kind; self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.r = r; self.warn = warn; self.life = life
    }
}

final class TTPickup {
    let kind: String
    var x, y: Double
    let value: Int
    var vx = 0.0, vy = 0.0
    var falling = false
    var life = -1.0                     // < 0: stays until picked up
    var t = Double.random(in: 0 ... 6.28)
    init(_ kind: String, _ x: Double, _ y: Double, _ value: Int = 0) { self.kind = kind; self.x = x; self.y = y; self.value = value }
}

final class TTKitten {
    var x, y: Double
    let color: Int
    var follow = false
    var t = Double.random(in: 0 ... 6.28)
    init(_ x: Double, _ y: Double, _ color: Int) { self.x = x; self.y = y; self.color = color }
}

/// The crow on the top branch: flies about and throws things down the tree.
final class TTKaw {
    var x = 250.0, y = 22.0, tx = 160.0
    var face = -1
    var mode = "fly", modeT = 0.0
    var throwT = 2.6
    var rate: Double
    var aim = 0.0
    var nextKind: String?
    var stun = 0.0, taunt = 0.0
    var party = false
    init(_ rate: Double) { self.rate = rate }
}

// ---------------------------------------------------------------------- drawing helpers
enum TTArt {
    static func backdrop(_ s: Surface, _ th: TTTheme, _ t: Double, _ tr: Int = 0) {
        var y = TT_HUD_H
        while y < H { s.fillRect(lerpCol(th.wa, th.wb, Double(y - TT_HUD_H) / Double(H - TT_HUD_H)), 0, y, W, 4); y += 4 }
        let shade = lerpCol(th.wa, "black", 0.3)
        let light = lerpCol(th.wa, "white", 0.18)
        let FH = Double(H - TT_HUD_H)
        switch th.style {
        case "window":
            s.fillRect(shade, 196, 26, 96, 70)
            s.fillRect(col(tr != 6 ? "sky" : "night"), 200, 30, 88, 62)
            s.circle(col("yellow"), 268, 48, 9)
            for i in 0 ..< 3 {
                let cx = Int(ttFmod(Double(i * 41) + t * 4, 110)) + 190
                s.ellipse(col("white"), cx, 62 + i * 9, 18, 6)
            }
            s.fillRect(shade, 242, 30, 4, 62)
            s.fillRect(shade, 200, 59, 88, 3)
            s.fillRect(col(th.accent), 192, 22, 104, 4)
        case "tiles":
            for x in stride(from: 0, to: W, by: 20) { s.fillRect(shade, x, TT_HUD_H, 1, H) }
            for y in stride(from: TT_HUD_H, to: H, by: 20) { s.fillRect(shade, 0, y, W, 1) }
        case "books":
            for row in 0 ..< 4 {
                let y = 30 + row * 40
                s.fillRect(shade, 0, y + 22, W, 3)
                for i in 0 ..< 24 {
                    let h = 12 + (i * 7 + row * 3) % 9
                    let c = ["red", "blue", "lime", "yellow", "lavender", "teal"][(i + row) % 6]
                    s.fillRect(lerpCol(c, th.wb, 0.55), i * 13 + row * 5, y + 22 - h, 10, h)
                }
            }
        case "bubbles":
            for i in 0 ..< 14 {
                let x = ttFmod(Double(i * 53) + t * Double(3 + i % 3), Double(W))
                let y = Double(TT_HUD_H) + ttFmod(Double(i * 37) - t * 6, FH)
                s.circle(light, Int(x), Int(y), 3 + i % 4, width: 1)
            }
        case "leaves":
            for i in 0 ..< 18 {
                let x = (i * 47 + Int(t * 5)) % W
                let y = TT_HUD_H + (i * 29 + Int(t * 9)) % (H - TT_HUD_H)
                s.ellipse(shade, x, y, 6, 3)
            }
        case "stars":
            for i in 0 ..< 36 {
                let x = (i * 67) % W, y = TT_HUD_H + (i * 31) % (H - TT_HUD_H)
                s.fillRect(Int(t * 2 + Double(i)) % 7 == 0 ? col("white") : light, x, y, 1, 1)
            }
            s.circle(col("cream"), 60, 40, 10)
            s.circle(col(th.wa), 64, 37, 9)
        case "beams":
            for x in stride(from: 10, to: W, by: 70) { s.fillRect(shade, x, TT_HUD_H, 8, H) }
            let hh = Double(TT_HUD_H)
            s.polygon(shade, [(0, hh), (Double(W / 2), hh + 30), (Double(W), hh), (Double(W), hh + 6), (Double(W / 2), hh + 36), (0, hh + 6)])
        case "rain":
            s.fillRect(shade, 30, 30, 70, 60)
            for i in 0 ..< 30 {
                let x = (i * 29 + Int(t * 8)) % W
                let y = TT_HUD_H + (i * 47 + Int(t * 90)) % (H - TT_HUD_H)
                s.fillRect(light, x, y, 1, 5)
            }
        case "stripes":
            for x in stride(from: 0, to: W, by: 16) { s.fillRect(shade, x, TT_HUD_H, 6, H) }
        case "snow":
            for i in 0 ..< 40 {
                let x = ttPmod(i * 37 + Int(sin(t + Double(i)) * 4), W)
                let y = TT_HUD_H + (i * 53 + Int(t * 14)) % (H - TT_HUD_H)
                s.fillRect(col("white"), x, y, 1 + i % 2, 1 + i % 2)
            }
        case "polka":
            for i in 0 ..< 30 {
                let x = (i * 61) % W, y = TT_HUD_H + (i * 43) % (H - TT_HUD_H)
                s.circle(light, x, y, 4)
            }
        case "notes":
            for i in 0 ..< 10 {
                let x = (i * 71 + Int(t * 6)) % W
                let y = TT_HUD_H + 10 + (i * 37) % 150 + Int(sin(t * 2 + Double(i)) * 3)
                s.fillRect(light, x, y, 1, 7)
                s.circle(light, x - 2, y + 7, 2)
            }
        case "clouds":
            for i in 0 ..< 7 {
                let x = Int(ttFmod(Double(i * 59) + t * Double(4 + i), Double(W + 60))) - 30
                let y = TT_HUD_H + 14 + (i * 27) % 150
                s.ellipse(light, x, y, 34, 10)
                s.ellipse(light, x + 8, y - 5, 18, 10)
            }
        default:
            break
        }
        s.fillRect(col(th.carpetD), 0, Int(TT_FLOOR), W, H - Int(TT_FLOOR))
        for x in stride(from: 0, to: W, by: 8) { s.fillRect(col(th.accent), x + 2, Int(TT_FLOOR) + 4, 4, 1) }
    }

    static func plank(_ f: Surface, _ sg: TTSeg, _ th: TTTheme, _ sd: TTStage) {
        let k = sg.k
        let c0 = sg.x0 / TT_CW, c1 = sg.x1 / TT_CW - 1
        let openL = c0 == 0 || !sd.solid(k, c0 - 1)
        let openR = c1 == TT_NC - 1 || !sd.solid(k, c1 + 1)
        for x in sg.x0 ..< sg.x1 {
            let inset = (x == sg.x0 && openL) || (x == sg.x1 - 1 && openR) ? 1 : 0
            let y = Int(sg.y(Double(x) + 0.5))
            let thk = k > 0 ? 5 : 3
            f.fillRect(col("black"), x, y + inset, 1, thk + 1 - inset)
            f.fillRect(col(th.carpetD), x, y + 1 + inset, 1, thk - 1 - inset)
            f.fillRect(col(th.carpet), x, y + inset, 1, 2 - inset)
            if (x * 7 + k * 3) % 11 == 0 { f.fillRect(col("white"), x, y + 1, 1, 1) }
        }
    }

    static func post(_ f: Surface, _ po: TTPost, _ th: TTTheme) {
        let top = Int(po.top), bot = Int(po.bot)
        if po.rope {
            for y in top ..< max(top, bot) { f.fillRect(col((y / 2) % 2 == 1 ? th.stripe : th.post), po.x - 1, y, 2, 1) }
            f.circle(col(th.stripe), po.x, bot, 2)
            f.fillRect(col(th.post), po.x - 1, bot + 1, 2, 3)
            return
        }
        f.fillRect(col("black"), po.x - 4, top, 8, bot - top)
        for y in top ..< max(top, bot) {
            for x in (po.x - 3) ..< (po.x + 3) {
                f.fillRect(col(((y + x) / 2) % 3 == 0 ? th.stripe : th.post), x, y, 1, 1)
            }
        }
    }

    static func tunnel(_ f: Surface, _ x0: Double, _ y0: Double) {
        let x = Int(x0), y = Int(y0)
        f.fillRect(col("black"), x - 8, y - 11, 16, 11)
        f.fillRect(col("peach"), x - 7, y - 10, 14, 10)
        f.fillRect(col("brown"), x - 7, y - 10, 14, 2)
        f.ellipse(col("black"), x - 4, y - 7, 8, 7)
        f.fillRect(col("brown"), x - 1, y - 10, 2, 2)
    }

    static func cushion(_ f: Surface, _ x0: Double, _ y0: Double) {
        let x = Int(x0), y = Int(y0)
        f.ellipse(col("black"), x - 12, y - 9, 24, 10)
        f.ellipse(col("purple"), x - 11, y - 8, 22, 8)
        f.ellipse(col("lavender"), x - 10, y - 8, 20, 5)
        f.fillRect(col("yellow"), x - 1, y - 6, 2, 2)
        for dx in [-12, 11] { f.fillRect(col("yellow"), x + dx, y - 3, 1, 3) }
    }

    static func hammock(_ s: Surface, _ hm: TTHam, _ th: TTTheme) {
        let x = Int(hm.x), y = Int(hm.y)
        for dx in [1, 30] { s.fillRect(col(th.stripe), x + dx, y - 14, 1, 14) }
        let X = Double(x), Y = Double(y)
        s.polygon(col("black"), [(X, Y - 1), (X + 32, Y - 1), (X + 28, Y + 5), (X + 4, Y + 5)])
        s.polygon(col(th.accent), [(X + 1, Y), (X + 31, Y), (X + 27, Y + 4), (X + 5, Y + 4)])
        for i in stride(from: 4, to: 28, by: 6) { s.fillRect(col("white"), x + i, y + 1, 2, 1) }
    }

    static func special(_ s: Surface, _ sg: TTSeg, _ th: TTTheme, _ t: Double, _ oy: Double = 0) {
        if sg.kind == "bed" {
            for c in stride(from: sg.x0, to: sg.x1, by: TT_CW) {
                let x = c + 8
                let y = Int(sg.y(Double(x)) + oy)
                let sq = sg.boing > 0 ? 2 : 0
                s.ellipse(col("black"), x - 8, y - 4 + sq, 16, 9 - sq)
                s.ellipse(col("hotpink"), x - 7, y - 3 + sq, 14, 7 - sq)
                s.ellipse(col("pink"), x - 5, y - 2 + sq, 10, 3)
                s.fillRect(col("white"), x - 3, y - 2 + sq, 2, 1)
            }
        } else if sg.kind == "box" {
            if sg.gone > 0 {
                if sg.gone < 0.6 && Int(t * 12) % 2 == 1 {
                    for c in stride(from: sg.x0, to: sg.x1, by: 4) { s.fillRect(col("peach"), c, Int(sg.y(Double(c)) + oy), 2, 1) }
                }
                return
            }
            let shake = sg.stand > 0.05 ? Int(sin(t * 60) * 1.5) : 0
            for c in stride(from: sg.x0, to: sg.x1, by: TT_CW) {
                let y = Int(sg.y(Double(c + 8)) + oy)
                s.fillRect(col("black"), c + shake, y - 1, 16, 8)
                s.fillRect(col("peach"), c + 1 + shake, y, 14, 6)
                s.fillRect(col("brown"), c + 1 + shake, y, 14, 1)
                s.fillRect(col("orange"), c + 7 + shake, y, 2, 6)
                if sg.stand > 0.2 { s.line(col("black"), c + 3 + shake, y + 1, c + 6 + shake, y + 4) }
            }
        } else if sg.kind == "belt" {
            for x in sg.x0 ..< sg.x1 {
                let y = Int(sg.y(Double(x) + 0.5) + oy)
                s.fillRect(col("black"), x, y, 1, 6)
                s.fillRect(col("darkgray"), x, y + 1, 1, 4)
                let ph = ttPmod(Int(Double(x) - Double(sg.belt) * t * 32), 8)
                if ph < 2 { s.fillRect(col("yellow"), x, y + 2, 1, 2) }
            }
            for x in [sg.x0, sg.x1 - 1] { s.circle(col("gray"), x, Int(sg.y(Double(x)) + oy) + 3, 3) }
        }
    }

    /// Small picture of a tree part for the NEW! line of the stage card (y = top of the line).
    static func structIcon(_ s: Surface, _ ch: String, _ x: Int, _ y: Int, _ th: TTTheme, _ t: Double) {
        let floor = TT_LEVEL_Y[0]
        switch ch {
        case "R":
            for yy in (y - 2) ..< (y + 14) { s.fillRect(col(ttPmod(yy / 2, 2) == 1 ? th.stripe : th.post), x + 8, yy, 2, 1) }
        case "~":
            let hm = TTHam(Double(x - 6), Double(x - 6), 0, 0)
            hm.x = Double(x - 6); hm.y = Double(y + 12)
            hammock(s, hm, th)
        case "S": special(s, TTSeg(x, x + 16, 0, 0, "bed"), th, t, Double(y + 10) - floor)
        case "X": special(s, TTSeg(x, x + 16, 0, 0, "box"), th, t, Double(y + 8) - floor)
        case "<", ">": special(s, TTSeg(x - 2, x + 20, 0, 0, "belt", 1), th, t, Double(y + 6) - floor)
        case "W": tunnel(s, Double(x + 8), Double(y + 14))
        default: break
        }
    }

    static func item(_ s: Surface, _ it: TTPickup, _ t: Double) {
        let x = Int(it.x), y = Int(it.y)
        let bob = it.falling ? 0 : Int(sin(it.t * 4) * 1.5)
        switch it.kind {
        case "fish":
            s.blit(sprite("tt_fish"), x - 5, y - 3 + bob)
        case "gfish":
            s.blit(sprite("tt_fish", 0, remap: TT_GOLD_FISH), x - 5, y - 3 + bob)
            if Int(t * 8) % 2 == 1 { s.fillRect(col("white"), x + 2, y - 4 + bob, 1, 1) }
        case "coin":
            s.blit(sprite("tt_coin"), x - 3, y - 3)
            if Int(t * 10) % 2 == 1 { s.fillRect(col("white"), x - 5, y - 5, 1, 1) }
        case "heart":
            s.blit(sprite("heart"), x - 3, y - 3 + bob)
        default:
            let name = ["wand": "tt_wand", "bell": "tt_bell", "milk": "tt_milk", "nip": "tt_nip"][it.kind] ?? "tt_wand"
            let img = sprite(name)
            s.circle(col(Int(t * 6) % 2 == 1 ? "white" : "lavender"), x, y + bob, 7, width: 1)
            s.blit(img, x - img.w / 2, y - img.h / 2 + bob)
        }
    }

    static func kitten(_ s: Surface, _ kt: TTKitten, _ t: Double) {
        let x = Int(kt.x), y = Int(kt.y)
        let fr = Int(kt.t * (kt.follow ? 6 : 2)) % 2
        let hop = kt.follow ? -Int(abs(sin(kt.t * 8)) * 2) : 0
        s.blit(sprite("tt_kitten", fr, remap: TT_KITTEN_COLORS[kt.color]), x - 4, y - 7 + hop)
        if !kt.follow && Int(kt.t * 1.5) % 3 == 0 { drawText(s, "MEW", x, y - 16, "pink", align: .center, shadow: "ink") }
    }

    static func haz(_ s: Surface, _ h: TTHaz, _ t: Double, _ frozen: Bool, icon: Bool = false) {
        let x = Int(h.x), y = Int(h.y), r = Int(h.r.rounded())
        switch h.kind {
        case "yarn":
            let c = h.color
            for i in 1 ..< max(1, h.path.count) where i % 2 == 1 {
                s.fillRect(col(c), Int(h.path[i].0), Int(h.path[i].1), 1, 1)
            }
            s.circle(col("black"), x, y, r + 1)
            s.circle(col(c), x, y, r)
            for j in 0 ..< 2 {
                let a = h.spin + Double(j) * 1.6
                let dx = cos(a) * Double(r), dy = sin(a) * Double(r)
                s.line(lerpCol(c, "black", 0.35), Int(Double(x) - dx * 0.8), Int(Double(y) - dy * 0.8),
                       Int(Double(x) + dx * 0.8), Int(Double(y) + dy * 0.8))
            }
            s.fillRect(col("white"), x - 2, y - 2, 1, 1)
            if h.gold && Int(t * 10) % 2 == 1 { s.fillRect(col("white"), x + 2, y - 4, 1, 1) }
        case "marble":
            s.circle(col("black"), x, y, r + 1)
            s.circle(col("sky"), x, y, r)
            s.fillRect(col("white"), x - 1, y - 1, 1, 1)
        case "dust":
            for a in stride(from: 0, to: 360, by: 60) {
                let rr = (Double(a) + h.spin * 40) * .pi / 180
                s.circle(col("darkgray"), Int(Double(x) + cos(rr) * 3), Int(Double(y) + sin(rr) * 3), 2)
            }
            s.circle(col("gray"), x, y, 3)
            s.fillRect(col("black"), x - 2, y - 1, 1, 1)
            s.fillRect(col("black"), x + 1, y - 1, 1, 1)
        case "cone":
            s.ellipse(col("black"), x - 4, y - 5, 9, 11)
            s.ellipse(col("brown"), x - 3, y - 4, 7, 9)
            for j in 0 ..< 3 { s.fillRect(col("choco"), x - 2 + (j % 2) * 2, y - 2 + j * 2, 2, 1) }
            s.fillRect(col("lime"), x - 1, y - 6, 2, 2)
        case "cushion":
            s.rect(col("black"), IRect(x - 9, y - 6, 18, 12), radius: 4)
            s.rect(col("lavender"), IRect(x - 8, y - 5, 16, 10), radius: 4)
            s.rect(col("purple"), IRect(x - 8, y + 2, 16, 3), radius: 2)
            s.fillRect(col("yellow"), x - 1, y - 1, 2, 2)
        case "ball":
            let sq = h.spin > 0.2 ? 1 : 0
            h.spin = max(0, h.spin - 0.02)
            s.ellipse(col("black"), x - r - 1, y - r - 1 + sq, 2 * r + 3, 2 * r + 3 - sq)
            s.ellipse(col("red"), x - r, y - r + sq, 2 * r + 1, 2 * r + 1 - sq)
            s.fillRect(col("yellow"), x - r, y, 2 * r + 1, 1)
            s.fillRect(col("white"), x - 2, y - 2, 1, 1)
        case "mouse":
            let d = h.dir < 0 ? -1 : 1
            s.ellipse(col("black"), x - 7, y - 4, 14, 9)
            s.ellipse(col("gray"), x - 6, y - 3, 12, 7)
            s.circle(col("pink"), x + d * 3, y - 4, 2)
            s.fillRect(col("black"), x + d * 4, y - 1, 1, 1)
            s.fillRect(col("pink"), x + d * 7, y, 1, 1)
            s.line(col("pink"), x - d * 6, y + 1, x - d * 10, y - 2)
            let kw = 1 + Int(abs(sin(t * 8)) * 2)
            s.fillRect(col("yellow"), x - kw, y - 7, kw * 2 + 1, 1)
            s.fillRect(col("yellow"), x, y - 6, 1, 2)
        case "spider":
            if !icon { s.fillRect(col("white"), x, Int(h.ay) - 2, 1, max(0, y - Int(h.ay) + 2)) } else { s.fillRect(col("white"), x, y - 8, 1, 6) }
            s.circle(col("black"), x, y, 4)
            for side in [-1, 1] {
                for j in 0 ..< 3 {
                    let leg = Int(sin(t * 10 + Double(j)) * 1)
                    s.fillRect(col("black"), x + side * (4 + j % 2), y - 2 + j * 2 + leg, 3, 1)
                }
            }
            s.fillRect(col("red"), x - 2, y - 1, 1, 1)
            s.fillRect(col("red"), x + 1, y - 1, 1, 1)
        case "spritz":
            let d = h.dir
            let bx = x - 4
            s.rect(col("black"), IRect(bx - 1, y - 6, 10, 16), radius: 2)
            s.rect(col("sky"), IRect(bx, y - 5, 8, 14), radius: 2)
            s.fillRect(col("white"), bx + 1, y - 2, 6, 4)
            s.fillRect(col("blue"), bx + 2, y - 9, 4, 4)
            s.fillRect(col("blue"), x + d * 4 - (d > 0 ? 0 : 2), y - 9, 3, 2)
            if h.cool < 0.6 && Int(t * 16) % 2 == 1 { s.fillRect(col("white"), x + d * 7, y - 9, 1, 1) }
        case "bot":
            let w = 7
            s.ellipse(col("black"), x - w - 1, y - 4, 2 * w + 3, 9)
            s.ellipse(col("darkgray"), x - w, y - 3, 2 * w + 1, 7)
            s.fillRect(col("gray"), x - 4, y - 3, 9, 2)
            s.fillRect(h.stun <= 0 ? col(Int(t * 4) % 2 == 1 ? "red" : "lime") : col("yellow"), x - 1, y - 2, 3, 1)
            if h.stun > 0 {
                for i in 0 ..< 2 {
                    let a = t * 8 + Double(i) * 3.1
                    s.fillRect(col("yellow"), Int(Double(x) + cos(a) * 6), Int(Double(y) - 7 + sin(a) * 2), 1, 1)
                }
            }
        case "moth":
            let fl = Int(abs(sin(t * 16)) * 3)
            s.ellipse(col("lavender"), x - 6, y - 2 - fl, 5, 4 + fl)
            s.ellipse(col("lavender"), x + 2, y - 2 - fl, 5, 4 + fl)
            s.fillRect(col("black"), x - 1, y - 2, 3, 5)
            s.fillRect(col("white"), x - 4, y - 1, 1, 1)
        default:
            break
        }
        if frozen && h.kind != "spritz" && !icon { drawText(s, "Z", x + 4, y - 10 - Int(t * 6) % 4, "sky", shadow: nil) }
    }

    static func shot(_ s: Surface, _ sh: TTShot, _ t: Double) {
        let x = Int(sh.x), y = Int(sh.y)
        let floor = Int(TT_FLOOR)
        switch sh.kind {
        case "drop", "spray":
            s.circle(col("blue"), x, y, Int(sh.r) + 1)
            s.circle(col("sky"), x, y, Int(sh.r))
            s.fillRect(col("white"), x - 1, y - 1, 1, 1)
        case "feather":
            let a = atan2(sh.vy, sh.vx)
            let dx = cos(a) * 4, dy = sin(a) * 4
            s.line(col("black"), Int(Double(x) - dx), Int(Double(y) - dy), Int(Double(x) + dx), Int(Double(y) + dy), width: 3)
            s.line(col("darkgray"), Int(Double(x) - dx), Int(Double(y) - dy), Int(Double(x) + dx), Int(Double(y) + dy))
            s.fillRect(col("white"), Int(Double(x) + dx), Int(Double(y) + dy), 1, 1)
        case "spark":
            s.circle(col(Int(t * 16) % 2 == 1 ? "red" : "hotpink"), x, y, 3)
            s.fillRect(col("white"), x - 1, y - 1, 2, 2)
        case "wave":
            for i in 0 ..< 3 {
                let hh = 9 - i * 2
                s.fillRect(col(["white", "lavender", "purple"][i]), x - 2 + i * (sh.vx > 0 ? -2 : 2), floor - hh, 3, hh)
            }
        case "beam":
            if sh.age < sh.warn {
                if Int(sh.age * 16) % 2 == 0 {
                    for yy in stride(from: TT_HUD_H + 4, to: floor, by: 6) { s.fillRect(col("red"), x, yy, 1, 3) }
                }
            } else {
                let w = Int(sh.r) * 2 + 4
                s.fillRect(col("red"), x - w / 2, TT_HUD_H, w, floor - TT_HUD_H)
                s.fillRect(col("white"), x - 1, TT_HUD_H, 3, floor - TT_HUD_H)
            }
        case "jet":
            if sh.age < sh.warn {
                if Int(sh.age * 16) % 2 == 0 { for xx in stride(from: 0, to: W, by: 8) { s.fillRect(col("sky"), xx, y, 4, 1) } }
            } else {
                s.fillRect(col("blue"), 0, y - 3, W, 7)
                s.fillRect(col("sky"), 0, y - 2, W, 5)
                for xx in stride(from: Int(t * 200) % 12, to: W, by: 12) { s.fillRect(col("white"), xx, y - 1, 5, 1) }
            }
        default:
            break
        }
        if sh.batted { s.fillRect(col("lavender"), x - 1, y - 4, 2, 1) }
    }
}
