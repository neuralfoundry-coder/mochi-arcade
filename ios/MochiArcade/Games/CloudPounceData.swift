// CLOUD POUNCE data, objects, upgrade cards and drawing helpers
// (port of games/cloud_pounce_data.py constants + the helpers at the bottom of games/cloud_pounce.py).
// The 200 stages themselves are built in Python and read from the exported campaign (GameData "cloud_pounce").
import Foundation

enum CP {
    static let FX0 = 48                    // the play field: x 48 ... 272 on screen
    static let FW = 224
    static let FWd = 224.0
    static let G = 480.0
    static let JUMP_V = 270.0
    static let RAIN_V = 215.0
    static let SPRING_V = 430.0
    static let POUNCE_V = 380.0
    static let POWER_V = 335.0
    static let BALLOON_LIFT = 150.0, BALLOON_T = 1.2
    static let VX_MAX = 125.0
    static let ROCKET_SPEED = 210.0
    // cloud kinds
    static let KF = 0, KT = 1, KM = 2, KR = 3, KS = 4, KZ = 5, KG = 6, KW = 7, FLOOR = 8
    // items
    static let I_STAR = 0, I_BALLOON = 1, I_ROCKET = 2, I_BELL = 3, I_PARASOL = 4, I_MAGNET = 5, I_MILK = 6, I_GOLD = 7
    // foes
    static let E_BIRD = 0, E_KITE = 1, E_DOT = 2, E_SPARK = 3
    static let LIFE_AT = [15000, 40000, 80000, 140000]          // then every 100000
    static let CAP_NAMES = [2: "CATNIP ROCKET!", 3: "LUCKY BELL!", 4: "PARASOL!", 5: "STAR MAGNET!", 6: "MILK! +1 LIFE"]
    static let BIRD_COLS = ["peach", "sky", "lime", "pink", "yellow", "mint", "lavender"]
    static let BALLOON_COLS = ["red", "hotpink", "sky", "lime", "orange", "lavender"]
    static let CLOUD_COL: [Int: (String, String, String)] = [
        0: ("white", "lavender", "cream"), 1: ("cream", "gray", "peach"), 2: ("white", "sky", "sky"),
        3: ("gray", "darkgray", "darkgray"), 4: ("white", "hotpink", "pink"), 5: ("darkgray", "ink", "ink"),
        6: ("lavender", "purple", "purple"), 7: ("mint", "teal", "teal")]
}

/// Signed horizontal distance on the wrapping field, in -FW/2 ... FW/2 (Python: (dx + FW/2) % FW - FW/2).
@inline(__always) func cpWrapd(_ dx: Double) -> Double { cpFmod(dx + CP.FWd / 2, CP.FWd) - CP.FWd / 2 }
/// Python-style float modulo (never negative for m > 0).
@inline(__always) func cpFmod(_ a: Double, _ m: Double) -> Double {
    let r = a.truncatingRemainder(dividingBy: m)
    return r < 0 ? r + m : r
}
@inline(__always) func cpMod(_ a: Int, _ m: Int) -> Int { ((a % m) + m) % m }

/// (a, b) parameters of a cloud derived from its position (same integer maths as cloud_pounce_data.cloud_ab).
func cpCloudAB(_ k: Int, _ x: Int, _ h: Int, _ w: Int, _ tier: Int) -> (Int, Int) {
    if k == CP.KM {
        let amp = min([20, 28, 36, 44][(x / 8 + h / 12) % 4], 40 + tier)
        return (amp, 70 + (x * 3 + h) % (41 + 3 * tier))
    }
    if k == CP.KZ || k == CP.KG { return ((h * 7 + x * 3) % 100, 0) }
    if k == CP.KW { return (x * 2 + w < CP.FW ? 1 : -1, 0) }
    return (0, 0)
}

// ----------------------------------------------------------------------------- campaign data (EXPORT)
struct CPBossSpec { let kind, name: String; let hp: Int; let rate, speed: Double; let extra: [String]; let tier: Int }

struct CPStage {
    let n, tier: Int
    let kind, name, newLine, bonus: String
    let time: Double
    let goal, par: Int
    let c, i, f, e, riv, mods: [Int]
    let boss: CPBossSpec?
}

enum CPData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func ints(_ v: Any?) -> [Int] { ((v as? [Any]) ?? []).map { Int(num($0)) } }
    private static let root: [String: Any] = (GameData.json("cloud_pounce") as? [String: Any]) ?? [:]

    static let stages: [CPStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: CPBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = CPBossSpec(kind: b["kind"] as? String ?? "owl", name: b["name"] as? String ?? "", hp: Int(num(b["hp"])),
                              rate: num(b["rate"]), speed: num(b["speed"]), extra: b["extra"] as? [String] ?? [],
                              tier: Int(num(b["tier"])))
        }
        return CPStage(n: Int(num(d["n"])), tier: Int(num(d["tier"])), kind: d["kind"] as? String ?? "normal",
                       name: d["name"] as? String ?? "", newLine: d["new"] as? String ?? "", bonus: d["bonus"] as? String ?? "",
                       time: num(d["time"]), goal: Int(num(d["goal"])), par: Int(num(d["par"])),
                       c: ints(d["c"]), i: ints(d["i"]), f: ints(d["f"]), e: ints(d["e"]), riv: ints(d["riv"]),
                       mods: ints(d["mods"]), boss: boss)
    }
    static let themes: [[String]] = (root["themes"] as? [[String]]) ?? []
    static let quips: [String] = (root["quips"] as? [String]) ?? [""]
    static let fish: [(pts: [(Int, Int)], lines: [(Int, Int)])] = ((root["fish"] as? [[String: Any]]) ?? []).map { f in
        let pts = ((f["pts"] as? [[Any]]) ?? []).map { (Int(num($0[0])), Int(num($0[1]))) }
        let lines = ((f["lines"] as? [[Any]]) ?? []).map { (Int(num($0[0])), Int(num($0[1]))) }
        return (pts, lines)
    }
}

// ----------------------------------------------------------------------------- objects
final class CPCloud {
    let k, x0, h, w: Int
    let a, b: Int
    var x: Double
    var alive = true
    var squash = 0.0, regrow = 0.0
    var temp = 0.0              // cushion / rescue clouds fade away
    var phase: Double
    init(_ k: Int, _ x: Int, _ h: Int, _ w: Int, _ tier: Int) {
        self.k = k; x0 = x; self.h = h; self.w = w
        (a, b) = cpCloudAB(k, x, h, w, tier)
        self.x = Double(x)
        phase = Double(x + h) * 0.05
    }
    var hd: Double { Double(h) }
    func cx() -> Double { x + Double(w) / 2 }
}

final class CPItem {
    let k: Int
    var x, h: Double
    var got = false, gold = false
    var ph: Double
    init(_ k: Int, _ x: Double, _ h: Double) {
        self.k = k; self.x = x; self.h = h
        ph = Double(cpMod(Int(x) * 13 + Int(h), 7))
    }
}

final class CPFish {
    let x, h, shape: Int
    let gold: Bool
    var stars: [(x: Double, h: Double, got: Bool)]
    let lines: [(Int, Int)]
    var done = false
    var glow = 0.0
    init(_ x: Int, _ h: Int, _ shape: Int, _ mirror: Int, _ gold: Int) {
        let f = CPData.fish[shape]
        self.x = x; self.h = h; self.shape = shape; self.gold = gold != 0
        let sx = mirror != 0 ? -1 : 1
        stars = f.pts.map { (Double(cpMod(x + sx * $0.0, CP.FW)), Double(h + $0.1), false) }
        lines = f.lines
    }
}

final class CPFoe {
    let k: Int
    let ax, ah: Double
    let a, b: Int
    var x, h: Double
    let spd: Double
    var alive = true
    var deadT = 0.0, vh = 0.0
    let ph: Double
    init(_ k: Int, _ x: Int, _ h: Int, _ a: Int, _ b: Int, _ spd: Double) {
        self.k = k; ax = Double(x); ah = Double(h); self.a = a; self.b = b
        self.x = Double(x); self.h = Double(h); self.spd = spd
        ph = Double((x * 7 + h) % 13) * 0.5
    }
}

final class CPHail {
    var x, h: Double
    var warn = 0.8
    var alive = true
    init(_ x: Double, _ h: Double) { self.x = x; self.h = h }
}

// ----------------------------------------------------------------------------- upgrade cards
private func iconBell(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
    s.circle(col("yellow"), cx, cy, 5)
    s.fillRect(col("yellow"), cx - 6, cy + 2, 13, 3)
    s.fillRect(col("orange"), cx - 1, cy + 5, 3, 2)
    s.fillRect(col("white"), cx - 2, cy - 3, 1, 2)
}

private func iconMagnet(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) {
    s.fillRect(col("red"), cx - 6, cy - 4, 4, 9)
    s.fillRect(col("red"), cx + 3, cy - 4, 4, 9)
    s.fillRect(col("red"), cx - 6, cy + 2, 13, 3)
    s.fillRect(col("white"), cx - 6, cy - 4, 4, 2)
    s.fillRect(col("white"), cx + 3, cy - 4, 4, 2)
    s.fillRect(col("yellow"), cx, cy - 7 + Int(t * 6) % 3, 1, 1)
}

func cpIconBell(_ s: Surface, _ cx: Int, _ cy: Int, _ t: Double) { iconBell(s, cx, cy, t) }

let CP_UPGRADES: [Upgrade] = [
    Upgrade(id: "spring", name: "SPRING PAWS", desc: "HIGHER|BOUNCES", color: "yellow", draw: { s, cx, cy, t in
        let y = cy + 2 - abs(Int(sin(t * 5) * 4))
        for i in 0 ..< 3 { s.fillRect(col("yellow"), cx - 4, cy + 5 - i * 2, 9, 1) }
        s.circle(col("white"), cx, y - 3, 3)
    }, max: 3),
    Upgrade(id: "steer", name: "SWIFT TAIL", desc: "FASTER|AIR STEERING", color: "sky", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.fillRect(col("sky"), cx - 6 + i * 5 + Int(t * 12) % 5, cy - 3 + i * 3, 4, 1) }
        s.fillRect(col("white"), cx + 5, cy - 1, 3, 3)
    }, max: 3),
    Upgrade(id: "heavy", name: "HEAVY POUNCE", desc: "POUNCES HIT|BOSSES HARDER|+ BIGGER BOUNCE", color: "orange", draw: { s, cx, cy, t in
        s.circle(col("white"), cx, cy - 6 + Int(t * 14) % 8, 3)
        s.fillRect(col("orange"), cx - 6, cy + 5, 13, 2)
        s.fillRect(col("yellow"), cx - 4, cy + 3, 1, 2)
        s.fillRect(col("yellow"), cx + 4, cy + 3, 1, 2)
    }, max: 3),
    Upgrade(id: "double", name: "DOUBLE POUNCE", desc: "+1 POUNCE|PER JUMP", color: "hotpink", draw: { s, cx, cy, t in
        for dx in [-3, 3] {
            let yy = cy + (dx / 3) * Int(sin(t * 6) * 2)
            s.circle(col("hotpink"), cx + dx, yy, 3)
            s.fillRect(col("white"), cx + dx - 1, yy - 1, 1, 1)
        }
    }, max: 2),
    Upgrade(id: "magnet", name: "STAR MAGNET", desc: "PULLS STARS|AND TREATS|TO SORA", color: "red", draw: iconMagnet, max: 3),
    Upgrade(id: "bell", name: "LUCKY BELL", desc: "A SHIELD BELL|AT EVERY|STAGE START", color: "yellow", draw: iconBell, max: 1),
    Upgrade(id: "cushion", name: "CLOUD CUSHION", desc: "SAVES ONE|FALL EVERY|STAGE", color: "white", draw: { s, cx, cy, t in
        cpDrawCloud(s, cx - 9, cy - 1 + Int(sin(t * 4) * 1), 18, CP.KF, t, 0, face: false)
    }, max: 2),
    Upgrade(id: "rocket", name: "ROCKET FUEL", desc: "LONGER|CATNIP|ROCKETS", color: "orange", draw: { s, cx, cy, t in
        cpDrawRocket(s, cx, cy + 3, t)
    }, max: 3),
    Upgrade(id: "life", name: "NINE LIVES", desc: "+1 LIFE|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
    Upgrade(id: "luck", name: "LUCKY WHISKERS", desc: "MORE GOLD|BALLOONS AND|JACKPOTS", color: "orange", draw: { s, cx, cy, t in
        let w = max(1, Int(abs(cos(t * 3)) * 5))
        s.ellipse(col("orange"), cx - w, cy - 5, w * 2 + 1, 11)
        s.ellipse(col("yellow"), cx - w + 1, cy - 4, max(1, w * 2 - 1), 9)
    }, max: 3),
    Upgrade(id: "fever", name: "FEVER PURR", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "lime", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
]

// ----------------------------------------------------------------------------- drawing helpers
/// A round cloud tuft (an ellipse in a (2r+1) box: smooth, and identical to the desktop).
@inline(__always) func cpPuff(_ s: Surface, _ c: String, _ cx: Int, _ cy: Int, _ r: Int) {
    s.ellipse(col(c), cx - r, cy - r, 2 * r + 1, 2 * r + 1)
}

/// A puffy cloud whose walkable top is at y (x = left edge).
func cpDrawCloud(_ s: Surface, _ x: Int, _ y0: Int, _ w: Int, _ k: Int, _ t: Double, _ sq: Double = 0, face: Bool = true,
                 state: Int = 0, wind: Int = 0) {
    let y = y0 + Int(sq * 10)
    var (body, rim, shade) = CP.CLOUD_COL[k] ?? ("white", "lavender", "cream")
    if k == CP.KZ { body = ["darkgray", Int(t * 12) % 2 != 0 ? "purple" : "yellow", "white"][state] }
    if k == CP.KT {          // a puff cloud: little separate tufts that pop
        let n = max(2, w / 8)
        for i in 0 ..< n { cpPuff(s, "sky", x + 4 + (w - 8) * i / (n - 1), y + 5, 4) }
        for i in 0 ..< n {
            let cx = x + 4 + (w - 8) * i / (n - 1)
            cpPuff(s, "white", cx, y + 5, 3)
            s.fillRect(col("cream"), cx - 1, y + 7, 3, 1)
            s.fillRect(col("lavender"), cx + 1, y + 3, 1, 1)
        }
        return
    }
    let n = max(2, w / 10)
    let top = y + 4
    s.rect(col(rim), IRect(x - 1, y + 2, w + 2, 9), radius: 4)
    for i in 0 ..< n { cpPuff(s, rim, x + 4 + (w - 8) * i / (n - 1), top, 5 + (i % 2)) }
    s.rect(col(body), IRect(x, y + 3, w, 7), radius: 3)
    for i in 0 ..< n { cpPuff(s, body, x + 4 + (w - 8) * i / (n - 1), top, 4 + (i % 2)) }
    if k == CP.KS {          // rainbow stripes
        for (i, c) in ["hotpink", "orange", "yellow", "lime", "sky"].enumerated() { s.fillRect(col(c), x + 2, y + 3 + i, w - 4, 1) }
    }
    s.fillRect(col(shade), x + 2, y + 9, w - 4, 1)
    s.fillRect(col("white"), x + 3, top - 3, 2, 1)
    if k == CP.KM {
        for sx in [-1, 1] {
            let ax = sx < 0 ? x - 4 : x + w + 2
            s.fillRect(col("sky"), ax, y + 5, 2, 1)
            s.fillRect(col("sky"), ax + (sx < 0 ? 1 : 0), y + 4, 1, 3)
        }
    } else if k == CP.KR {
        for i in 0 ..< max(1, w / 8) {
            s.fillRect(col("sky"), x + 3 + i * 8 + (i % 2) * 3, y + 11 + Int(t * 30 + Double(i * 5)) % 9, 1, 2)
        }
    } else if k == CP.KZ {
        let bx = x + w / 2
        let c = col(state != 1 ? "yellow" : "white")
        s.line(c, bx - 2, y + 2, bx + 1, y + 5); s.line(c, bx + 1, y + 5, bx - 1, y + 6); s.line(c, bx - 1, y + 6, bx + 2, y + 9)
    } else if k == CP.KW {
        let a = t * 6
        for i in 0 ..< 3 {
            s.fillRect(col("white"), x + w / 2 + Int(cos(a + Double(i) * 2.1) * 4), y + 5 + Int(sin(a + Double(i) * 2.1) * 2), 1, 1)
        }
        if wind > 0 {
            s.polygon(col("teal"), [(Double(x + w + 2), Double(y + 3)), (Double(x + w + 2), Double(y + 9)), (Double(x + w + 5), Double(y + 6))])
        } else {
            s.polygon(col("teal"), [(Double(x - 2), Double(y + 3)), (Double(x - 2), Double(y + 9)), (Double(x - 5), Double(y + 6))])
        }
    }
    if face && w >= 32 && [CP.KF, CP.KM, CP.KG, CP.KW, CP.KR].contains(k) {
        let cx = x + w / 2
        let k0 = col("black")
        if sq > 0 {
            s.fillRect(k0, cx - 4, y + 5, 2, 1)
            s.fillRect(k0, cx + 3, y + 5, 2, 1)
            s.fillRect(k0, cx - 1, y + 7, 3, 1)
        } else {
            let blink = Int(t * 0.8 + Double(x) * 0.1) % 6 == 0
            s.fillRect(k0, cx - 4, y + 5, 1, blink ? 1 : 2)
            s.fillRect(k0, cx + 4, y + 5, 1, blink ? 1 : 2)
            s.fillRect(col("pink"), cx - 6, y + 7, 2, 1)
            s.fillRect(col("pink"), cx + 5, y + 7, 2, 1)
            if k == CP.KG {
                s.circle(k0, cx, y + 8, 1)
            } else {
                s.fillRect(k0, cx - 1, y + 7, 1, 1)
                s.fillRect(k0, cx + 1, y + 7, 1, 1)
                s.fillRect(k0, cx, y + 8, 1, 1)
            }
        }
    }
}

func cpDrawBalloon(_ s: Surface, _ x: Int, _ y0: Int, _ c: String, _ t: Double) {
    let y = y0 + Int(sin(t * 3 + Double(x)) * 1)
    s.ellipse(col("black"), x - 5, y - 6, 11, 13)
    s.ellipse(col(c), x - 4, y - 5, 9, 11)
    s.fillRect(col("white"), x - 2, y - 3, 2, 2)
    s.fillRect(col(c), x - 1, y + 6, 3, 2)
}

/// A catnip rocket (x, y = its nose under SORA).
func cpDrawRocket(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, flame: Bool = false) {
    s.rect(col("black"), IRect(x - 4, y - 1, 9, 12), radius: 3)
    s.rect(col("mint"), IRect(x - 3, y, 7, 10), radius: 3)
    s.fillRect(col("lime"), x - 1, y + 2, 3, 3)
    s.fillRect(col("white"), x - 2, y + 1, 1, 3)
    s.fillRect(col("red"), x - 5, y + 7, 2, 4)
    s.fillRect(col("red"), x + 4, y + 7, 2, 4)
    if flame {
        let fl = 4 + Int(t * 30) % 4
        s.polygon(col("orange"), [(Double(x - 3), Double(y + 11)), (Double(x + 3), Double(y + 11)), (Double(x), Double(y + 11 + fl + 3))])
        s.polygon(col("yellow"), [(Double(x - 1), Double(y + 11)), (Double(x + 1), Double(y + 11)), (Double(x), Double(y + 11 + fl))])
    }
}

func cpDrawParasol(_ s: Surface, _ x: Int, _ y: Int, _ t: Double) {
    s.polygon(col("black"), [(Double(x - 11), Double(y + 5)), (Double(x), Double(y - 4)), (Double(x + 11), Double(y + 5))])
    s.polygon(col("pink"), [(Double(x - 9), Double(y + 4)), (Double(x), Double(y - 2)), (Double(x + 9), Double(y + 4))])
    s.fillRect(col("white"), x - 3, y + 1, 2, 3)
    s.fillRect(col("white"), x + 3, y + 1, 2, 3)
    s.fillRect(col("brown"), x, y + 4, 1, 8)
}

func cpDrawFishIcon(_ s: Surface, _ x: Int, _ y: Int, _ c: String) {
    s.ellipse(col(c), x - 4, y - 2, 8, 5)
    s.polygon(col(c), [(Double(x + 3), Double(y)), (Double(x + 7), Double(y - 3)), (Double(x + 7), Double(y + 3))])
    s.fillRect(col("black"), x - 2, y - 1, 1, 1)
}

func cpDrawItem(_ s: Surface, _ it: CPItem, _ x: Int, _ y0: Int, _ t: Double) {
    let k = it.k
    let bob = Int(sin(t * 4 + it.ph) * 1.5)
    if k == CP.I_STAR {
        s.blit(sprite("star"), x - 3, y0 - 3 + bob)
        if Int(t * 5 + it.ph) % 6 == 0 { s.fillRect(col("white"), x + 3, y0 - 4 + bob, 1, 1) }
        return
    }
    if k == CP.I_BALLOON {
        let c = it.gold ? "yellow" : CP.BALLOON_COLS[Int(it.ph) % CP.BALLOON_COLS.count]
        cpDrawBalloon(s, x, y0 + bob, c, t)
        s.line(col("white"), x, y0 + 8 + bob, x + 1, y0 + 14 + bob)
        if it.gold && Int(t * 8) % 2 != 0 { s.fillRect(col("white"), x + 4, y0 - 7 + bob, 1, 1) }
        return
    }
    let y = y0 + bob
    if k == CP.I_GOLD {
        s.ellipse(col("orange"), x - 6, y - 4, 11, 8)
        s.ellipse(col("yellow"), x - 5, y - 3, 9, 6)
        s.polygon(col("orange"), [(Double(x + 4), Double(y)), (Double(x + 8), Double(y - 4)), (Double(x + 8), Double(y + 4))])
        s.fillRect(col("black"), x - 3, y - 1, 1, 1)
        if Int(t * 10) % 2 != 0 { s.fillRect(col("white"), x - 6, y - 6, 1, 1) }
        return
    }
    let tint = [CP.I_ROCKET: "orange", CP.I_BELL: "yellow", CP.I_PARASOL: "pink", CP.I_MAGNET: "red", CP.I_MILK: "white"][k] ?? "sky"
    bubble(s, Double(x), Double(y), 7, t, tint: tint)
    if k == CP.I_ROCKET {
        cpDrawRocket(s, x, y - 4, t)
    } else if k == CP.I_BELL {
        iconBell(s, x, y - 1, t)
    } else if k == CP.I_PARASOL {
        cpDrawParasol(s, x, y - 2, t)
    } else if k == CP.I_MAGNET {
        iconMagnet(s, x, y, t)
    } else {
        s.fillRect(col("white"), x - 2, y - 3, 5, 7)
        s.fillRect(col("sky"), x - 1, y - 5, 3, 2)
        s.fillRect(col("pink"), x - 2, y, 5, 2)
    }
}

func cpDrawFoe(_ s: Surface, _ f: CPFoe, _ x: Int, _ y: Int, _ t: Double, _ tier: Int) {
    let k = f.k
    let dead = !f.alive
    for xd in [0, -CP.FW, CP.FW] {
        let xx = x + xd
        if !(-16 < xx && xx < CP.FW + 16) { continue }
        if k == CP.E_BIRD {
            let c = CP.BIRD_COLS[(tier + Int(f.ph)) % CP.BIRD_COLS.count]
            let flap = Int(sin(t * 16 + f.ph) * 3)
            let d = f.a
            s.circle(col("black"), xx, y, 6)
            s.circle(col(c), xx, y, 5)
            s.fillRect(col("white"), xx - 2 * d - 1, y + 1, 3, 2)
            s.polygon(col("orange"), [(Double(xx + d * 5), Double(y - 1)), (Double(xx + d * 9), Double(y + 1)), (Double(xx + d * 5), Double(y + 2))])
            s.ellipse(col("black"), xx - d * 3 - 3, y - 4 - flap, 7, 5)
            s.ellipse(col("white"), xx - d * 3 - 2, y - 3 - flap, 5, 3)
            if dead {
                s.fillRect(col("black"), xx + d * 2 - 1, y - 3, 3, 1)
                s.fillRect(col("black"), xx + d * 2, y - 4, 1, 3)
            } else {
                s.fillRect(col("black"), xx + d * 2, y - 2, 1, 2)
                s.fillRect(col("black"), xx + d * 1, y - 4, 2, 1)
            }
        } else if k == CP.E_KITE {
            if !dead {
                for i in stride(from: 0, to: 40, by: 3) {
                    s.fillRect(col("white"), xx + Int(sin(Double(i) * 0.2 + t) * 2), y + 9 + i, 1, 1)
                }
            }
            let pal = [("red", "yellow"), ("sky", "white"), ("hotpink", "lavender"), ("lime", "teal")][Int(f.ph) % 4]
            let X = Double(xx), Y = Double(y)
            s.polygon(col("black"), [(X, Y - 10), (X + 8, Y), (X, Y + 10), (X - 8, Y)])
            s.polygon(col(pal.0), [(X, Y - 9), (X + 7, Y), (X, Y + 9), (X - 7, Y)])
            s.polygon(col(pal.1), [(X, Y - 9), (X + 7, Y), (X, Y)])
            s.polygon(col(pal.1), [(X, Y), (X - 7, Y), (X, Y + 9)])
            Cute.eyes(s, xx, y - 1, 2, look: 0, mood: dead ? "wow" : "angry")
            for i in 0 ..< 4 {      // ribbon bows
                let bx = xx + Int(sin(t * 5 + Double(i) + f.ph) * 3) - 2
                let by = y + 10 + i * 5
                s.fillRect(col(rainbow(i, 0)), bx, by, 2, 2)
                s.fillRect(col(rainbow(i, 0)), bx + 3, by, 2, 2)
            }
        } else if k == CP.E_DOT {
            let r = 4 + Int(t * 8) % 3
            s.circle(col("hotpink"), xx, y, r, width: 1)
            s.circle(col("red"), xx, y, 2)
            s.fillRect(col("white"), xx, y - 1, 1, 1)
        } else {
            for i in 0 ..< 4 {
                let a = t * 9 + Double(i) * 1.57
                s.line(col("yellow"), xx, y, xx + Int(cos(a) * 6), y + Int(sin(a) * 6))
            }
            s.circle(col("orange"), xx, y, 4)
            s.circle(col("yellow"), xx, y, 3)
            s.fillRect(col("white"), xx - 1, y - 1, 2, 2)
        }
    }
}
