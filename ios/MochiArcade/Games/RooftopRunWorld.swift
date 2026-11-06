// ROOFTOP RUN world (port of games/rooftop_run_world.py + the data half of games/rooftop_run_course.py):
// the exported stage table, course objects, Tora's physics step and the rooftop drawing helpers.
import Foundation

// ----------------------------------------------------------------------------- physics (rooftop_run_course.py)
let RR_G_UP = 560.0, RR_G_DOWN = 1150.0, RR_JUMP_V = 265.0, RR_AIR_V = 235.0, RR_KICK_V = 285.0
let RR_BOUNCE_V = 330.0, RR_PAD_V = 440.0, RR_HANG = 15.0, RR_SLIDE_H = 7.0, RR_STAND_H = 14.0
let RR_CLING_V = 40.0, RR_MAX_FALL = 430.0, RR_POUNCE_V = 380.0
let RR_GLIDE_V = [0.0, 70.0, 45.0]
let RR_SPRINT = 1.22, RR_BRAKE = 0.7
let RR_ADS = ["FISH!", "MEOW", "TUNA", "PURR", "NAPS", "MILK", "YARN", "SALE"]
let RR_CAP_NAMES = ["BELL MAGNET", "UMBRELLA", "CATNIP RUSH", "FUR SHIELD", "MILK! +1 LIFE", "GOLD BELL"]
let RR_CAP_COLORS = ["yellow", "sky", "lime", "peach", "white", "orange"]

/// Python-style modulo (never negative) for ints and doubles.
@inline(__always) func rrMod(_ a: Int, _ b: Int) -> Int { ((a % b) + b) % b }
@inline(__always) func rrFmod(_ a: Double, _ b: Double) -> Double {
    let r = a.truncatingRemainder(dividingBy: b)
    return r < 0 ? r + b : r
}
/// Python floor division for ints.
@inline(__always) func rrDiv(_ a: Int, _ b: Int) -> Int { Int((Double(a) / Double(b)).rounded(.down)) }

// deterministic noise (same as rooftop_run_world.lcg / hash2)
func rrLcg(_ s: Int) -> Int { (s &* 1103515245 &+ 12345) & 0x7FFF_FFFF }
func rrHash(_ a: Int, _ b: Int) -> Int { rrLcg(rrLcg(a &* 7919 &+ 13) ^ (b &* 104729 &+ 7)) >> 7 }

final class RRRng {
    var s: Int
    init(_ seed: Int) { s = seed & 0x7FFF_FFFF }
    func n(_ k: Int) -> Int { s = rrLcg(s); return (s >> 8) % k }
}

// ----------------------------------------------------------------------------- the exported stage table
struct RRBossSpec { let kind, name: String; let hp, lv: Int; let final: Bool; let rate: Double }

struct RRStage {
    let n, tier: Int
    let kind, name, newLine, bonus: String
    let speed: Double
    let len, loop, fish: Int
    let c: String
    let mods: [String]
    let boss: RRBossSpec?
}

/// name, sky top, sky low, far skyline, near skyline, facade, trim, ledge, windows, landmark, weather, NEW line, quip
struct RRTheme {
    let v: [String]
    var name: String { v[0] }
    var skyTop: String { v[1] }
    var skyLow: String { v[2] }
    var far: String { v[3] }
    var mid: String { v[4] }
    var face: String { v[5] }
    var trim: String { v[6] }
    var ledge: String { v[7] }
    var win: String { v[8] }
    var landmark: String { v[9] }
    var weather: String { v[10] }
    var quip: String { v[12] }
}

enum RRData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static let root: [String: Any] = (GameData.json("rooftop_run") as? [String: Any]) ?? [:]

    static let stages: [RRStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: RRBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = RRBossSpec(kind: b["kind"] as? String ?? "gully", name: b["name"] as? String ?? "", hp: Int(num(b["hp"])),
                              lv: Int(num(b["lv"])), final: b["final"] as? Bool ?? false, rate: num(b["rate"]))
        }
        return RRStage(n: Int(num(d["n"])), tier: Int(num(d["tier"])), kind: d["kind"] as? String ?? "normal",
                       name: d["name"] as? String ?? "", newLine: d["new"] as? String ?? "", bonus: d["bonus"] as? String ?? "",
                       speed: num(d["speed"]), len: Int(num(d["len"])), loop: Int(num(d["loop"])), fish: Int(num(d["fish"])),
                       c: d["c"] as? String ?? "", mods: d["mods"] as? [String] ?? [], boss: boss)
    }

    static let themes: [RRTheme] = ((root["themes"] as? [[Any]]) ?? []).map { a in RRTheme(v: a.map { "\($0)" }) }
}

/// The decoded entities of a course string ("T,f1,f2;..."): kind letter, the solid-box letter for S, int fields.
struct RREnt { let t: Character; let k: Character; let f: [Int] }

func rrDecode(_ s: String) -> [RREnt] {
    var out: [RREnt] = []
    for part in s.split(separator: ";") {
        let f = part.split(separator: ",")
        guard let t = f.first?.first else { continue }
        if t == "S" {
            out.append(RREnt(t: t, k: f[1].first ?? "X", f: f.dropFirst(2).map { Int($0) ?? 0 }))
        } else {
            out.append(RREnt(t: t, k: " ", f: f.dropFirst().map { Int($0) ?? 0 }))
        }
    }
    return out
}

/// Fish positions of an F (row) or A (arc) entity - the same integer maths as fish_points().
func rrFishPoints(_ e: RREnt) -> [(Int, Int)] {
    let x = e.f[0], y = e.f[1], n = e.f[2], dx = e.f[3]
    if e.t == "F" { return (0 ..< n).map { (x + $0 * dx, y) } }
    let h = e.f[4], m = max(1, n - 1)
    return (0 ..< n).map { k in (x + k * dx, y - (4 * h * k * (m - k)) / (m * m)) }
}

// ----------------------------------------------------------------------------- course objects
class RRSolid {
    var x, y, w, h: Double
    let solid: Character        // R roof, S box, M lift
    init(_ x: Double, _ y: Double, _ w: Double, _ h: Double, _ solid: Character) {
        self.x = x; self.y = y; self.w = w; self.h = h; self.solid = solid
    }
    var gone: Bool { false }
}

final class RRRoof: RRSolid {
    let glass: Bool
    var crack = -1.0            // seconds left before a touched skylight breaks (-1: untouched)
    var broken = false
    init(_ x0: Int, _ x1: Int, _ y: Int, _ glass: Int) {
        self.glass = glass != 0
        super.init(Double(x0), Double(y), Double(x1 - x0), 400, "R")
    }
    override var gone: Bool { broken }
}

final class RRBox: RRSolid {
    let k: Character
    var alive = true
    var flash = 0.0
    init(_ k: Character, _ f: [Int]) {
        self.k = k
        super.init(Double(f[0]), Double(f[1]), Double(f[2]), Double(f[3]), "S")
    }
    override var gone: Bool { !alive }
}

final class RRLift: RRSolid {
    let y0, amp, ph: Double
    init(_ f: [Int]) {
        y0 = Double(f[1]); amp = Double(f[3]); ph = Double(f[4]) / 100
        super.init(Double(f[0]), Double(f[1]), Double(f[2]), 6, "M")
    }
    func at(_ t: Double) -> Double { y0 + amp * sin(t * 1.5 + ph) }
}

final class RRLine {
    let x0, x1, base, sway: Double
    var y: Double
    init(_ f: [Int]) { x0 = Double(f[0]); x1 = Double(f[1]); base = Double(f[2]); sway = Double(f[3]); y = base }
    func at(_ t: Double) -> Double { base + sway * sin(t * 2.2 + x0 * 0.01) }
}

final class RRWire {
    let x0, x1, y: Double
    let spark: Bool
    init(_ f: [Int]) { x0 = Double(f[0]); x1 = Double(f[1]); y = Double(f[2]); spark = f[3] != 0 }
    /// Zaps run from the far end towards Tora.
    func sparkX(_ t: Double) -> Double { x1 - rrFmod(t * 70 + x0 * 0.37, x1 - x0 + 80) }
}

final class RRPad { let x, y: Double; var cd = 0.0; init(_ x: Double, _ y: Double) { self.x = x; self.y = y } }

final class RRFish {
    var x, y: Double
    var got = false
    var rainbow = false
    init(_ x: Double, _ y: Double) { self.x = x; self.y = y }
}

final class RRCap {
    let x, y: Double
    var k: Int
    var got = false
    init(_ x: Double, _ y: Double, _ k: Int) { self.x = x; self.y = y; self.k = k }
}

final class RRHaz {
    let k: Character
    var x, y: Double
    let x0, y0: Double
    let a: Int
    var b: Int
    var t = 0.0
    var state = 0               // kind specific: 0 idle / waiting, 1 active, 2 done
    var alive = true
    var dir = -1
    var vy = 0.0

    init(_ e: RREnt) {
        k = e.t
        x = Double(e.f[0]); y = Double(e.f[1]); x0 = x; y0 = y
        a = e.f.count > 2 ? e.f[2] : 0
        b = e.f.count > 3 ? e.f[3] : 0
    }

    /// Hurt box or nil.
    func rect(_ stime: Double) -> RRRect? {
        if !alive { return nil }
        switch k {
        case "p": return RRRect(x - 5, y - 9, 10, 9)
        case "q": return RRRect(x - 5, y - 3, 10, 6)
        case "s": return rrSprinklerPhase(self, stime) == 2 ? RRRect(x - 5, y - 30, 10, 30) : nil
        case "a": return RRRect(x - 2, y - Double(a), 5, Double(a))
        case "i":
            if state == 2 { return RRRect(x - 3, y - 6, 7, 6) }
            return state == 1 ? RRRect(x - 3, y - 9, 7, 9) : nil
        case "d": return state == 2 ? RRRect(x - 7, y - 4, 14, 8) : nil
        case "z": return state == 2 ? RRRect(x - 12, y - 8, 25, 8) : nil
        default: return nil
        }
    }
}

/// 0 off, 1 dripping (about to spray), 2 spraying.
func rrSprinklerPhase(_ h: RRHaz, _ stime: Double) -> Int {
    let p = rrFmod(stime + Double(h.a) / 100, 2.4)
    return p >= 1.4 ? 2 : (p >= 1.0 ? 1 : 0)
}

struct RRRect {
    var x, y, w, h: Double
    init(_ x: Double, _ y: Double, _ w: Double, _ h: Double) { self.x = x; self.y = y; self.w = w; self.h = h }
    func hits(_ o: RRRect) -> Bool { x < o.x + o.w && o.x < x + w && y < o.y + o.h && o.y < y + h }
}

/// A stage's objects, sorted along x.
final class RRCourse {
    var roofs: [RRRoof] = []
    var boxes: [RRBox] = []
    var lifts: [RRLift] = []
    var lines: [RRLine] = []
    var wires: [RRWire] = []
    var winds: [(Double, Double, Int)] = []
    var vents: [(Double, Double)] = []
    var pads: [RRPad] = []
    var fish: [RRFish] = []
    var gold: [RRFish] = []
    var caps: [RRCap] = []
    var haz: [RRHaz] = []
    var finish = 0.0

    init(_ st: RRStage) {
        for e in rrDecode(st.c) {
            switch e.t {
            case "R": roofs.append(RRRoof(e.f[0], e.f[1], e.f[2], e.f[3]))
            case "S": boxes.append(RRBox(e.k, e.f))
            case "M": lifts.append(RRLift(e.f))
            case "L": lines.append(RRLine(e.f))
            case "W": wires.append(RRWire(e.f))
            case "N": winds.append((Double(e.f[0]), Double(e.f[1]), e.f[2]))
            case "V": vents.append((Double(e.f[0]), Double(e.f[1])))
            case "J": pads.append(RRPad(Double(e.f[0]), Double(e.f[1])))
            case "F", "A": for (fx, fy) in rrFishPoints(e) { fish.append(RRFish(Double(fx), Double(fy))) }
            case "G": gold.append(RRFish(Double(e.f[0]), Double(e.f[1])))
            case "P": caps.append(RRCap(Double(e.f[0]), Double(e.f[1]), e.f[2]))
            case "E": finish = Double(e.f[0])
            case "p", "q", "s", "a", "i", "d", "z": haz.append(RRHaz(e))
            default: break
            }
        }
        roofs.sort { $0.x < $1.x }
        boxes.sort { $0.x < $1.x }
        sortFish()
    }

    func sortFish() { fish.sort { $0.x < $1.x } }

    /// First fish index with x >= v (binary search; fish are kept sorted along x).
    func fishFrom(_ v: Double) -> Int {
        var lo = 0, hi = fish.count
        while lo < hi { let m = (lo + hi) / 2; if fish[m].x < v { lo = m + 1 } else { hi = m } }
        return lo
    }

    /// Boss arenas loop: everything outside [keepX0, keepX1] comes back fresh.
    func resetConsumables(_ keepX0: Double, _ keepX1: Double) {
        for f in fish where !(keepX0 <= f.x && f.x <= keepX1) { f.got = false }
        for r in roofs where !(keepX0 <= r.x && r.x <= keepX1) { r.crack = -1; r.broken = false }
        for b in boxes where !(keepX0 <= b.x && b.x <= keepX1) { b.alive = true }
    }
}

/// What the physics needs around Tora: solids (roofs, boxes, lifts), lines, wires, winds, vents, pads.
final class RRView {
    let speed, t: Double
    var solids: [RRSolid] = []
    var lines: [RRLine] = []
    var wires: [RRWire] = []
    var winds: [(Double, Double, Int)] = []
    var vents: [(Double, Double)] = []
    var pads: [RRPad] = []

    init(_ c: RRCourse, _ x0: Double, _ x1: Double, _ speed: Double, _ t: Double) {
        self.speed = speed; self.t = t
        for r in c.roofs where r.x < x1 && r.x + r.w > x0 && !r.broken { solids.append(r) }
        for b in c.boxes where b.alive && b.x < x1 && b.x + b.w > x0 { solids.append(b) }
        for m in c.lifts where m.x < x1 && m.x + m.w > x0 { solids.append(m) }
        lines = c.lines.filter { $0.x0 < x1 && $0.x1 > x0 }
        wires = c.wires.filter { $0.x0 < x1 && $0.x1 > x0 }
        winds = c.winds.filter { $0.0 < x1 && $0.1 > x0 }
        vents = c.vents.filter { x0 - 20 < $0.0 && $0.0 < x1 + 20 }
        pads = c.pads.filter { x0 - 20 < $0.x && $0.x < x1 + 20 }
    }
}

// ----------------------------------------------------------------------------- Tora's body + physics
final class RRBody {
    var x, y: Double
    var vy = 0.0
    var ground: RRSolid?        // the solid under the paws
    var wire: RRWire?           // the tram wire she hangs on
    var slide = false, pounce = false, pad = false, hold = false, cling = false
    var blocked: RRSolid?
    var jumps = 0               // mid-air jumps left
    var airMax = 0
    var jv = 1.0                // jump power (SPRING PAWS)
    var glide = 0               // TAIL GLIDE level (or 1 while the umbrella is open)
    var boost = 1.0             // speed factor from catnip
    var coyote = 0.0, buffer = 0.0, wireCd = 0.0, airT = 0.0

    init(_ x: Double, _ y: Double) { self.x = x; self.y = y }
    var height: Double { slide ? RR_SLIDE_H : RR_STAND_H }
    var half: Double { slide ? 7 : 5 }
    var box: RRRect { RRRect(x - half, y - height, half * 2, height) }
}

struct RRCtrl {
    var jumpHit = false, jump = false, downHit = false, down = false
    var lr = 0
}

struct RREvent {
    let k: String
    var solid: RRSolid? = nil
    var line: RRLine? = nil
    var wire: RRWire? = nil
    var pad: RRPad? = nil
    var impact = 0.0
    var pounced = false
}

func rrRunSpeed(_ b: RRBody, _ c: RRCtrl, _ v: RRView) -> Double {
    var spd = v.speed * b.boost * (c.lr > 0 ? RR_SPRINT : (c.lr < 0 ? RR_BRAKE : 1.0))
    for z in v.winds where z.0 <= b.x && b.x <= z.1 { spd *= z.2 == 0 ? 0.6 : 1.35 }
    return spd
}

/// Advance Tora by dt (port of rooftop_run_world.step): returns events - jump airjump kick bounce grab land bonk
/// pad pounce updraft leave.
func rrStep(_ b: RRBody, _ c: RRCtrl, _ dt: Double, _ v: RRView) -> [RREvent] {
    var ev: [RREvent] = []
    b.wireCd -= dt
    b.coyote -= dt
    b.buffer -= dt
    if c.jumpHit { b.buffer = 0.12 }
    if !c.jump { b.hold = false }
    let spd = rrRunSpeed(b, c, v)
    // ---- hanging on a tram wire
    if let wr = b.wire {
        b.x += spd * 1.3 * dt
        b.y = wr.y + RR_HANG
        b.slide = false
        if b.buffer > 0 {
            b.buffer = 0
            b.wire = nil
            b.vy = -RR_JUMP_V * 0.92 * b.jv
            b.hold = true
            b.wireCd = 0.25
            b.jumps = b.airMax
            ev.append(RREvent(k: "jump", wire: wr))
        } else if c.downHit || b.x > wr.x1 {
            let hop = b.x > wr.x1
            b.wire = nil
            b.vy = hop ? -90 : 0
            b.wireCd = hop ? 0.12 : 0.3
            b.jumps = b.airMax
            ev.append(RREvent(k: "leave", wire: wr))
        }
        return ev
    }
    // ---- run (horizontal)
    let h = b.height, hw = b.half
    var nx = b.x + spd * dt
    b.blocked = nil
    for r in v.solids where r.y < b.y - 0.5 && r.y + r.h > b.y - h && b.x + hw <= r.x + 0.01 && nx + hw > r.x {
        nx = r.x - hw
        b.blocked = r
    }
    b.x = nx
    // ---- on the ground
    if let g = b.ground {
        if g.gone || b.x + hw <= g.x || b.x - hw >= g.x + g.w {
            b.ground = nil
            b.coyote = 0.09
            b.vy = 0
            ev.append(RREvent(k: "leave", solid: g))
        } else {
            b.y = g.y
            if c.down {
                b.slide = true
            } else if b.slide {
                // a solid overhead keeps her sliding (billboards)
                let covered = v.solids.contains { r in
                    r.y + r.h > b.y - RR_STAND_H && r.y + r.h <= b.y - RR_SLIDE_H + 0.5 && r.x < b.x + 5 && r.x + r.w > b.x - 5
                }
                if !covered { b.slide = false }
            }
            for p in v.pads where abs(p.x - b.x) < 8 && abs(p.y - b.y) < 1 && p.cd <= 0 {
                b.ground = nil
                b.vy = -RR_PAD_V
                b.pad = true
                b.slide = false
                ev.append(RREvent(k: "pad", pad: p))
                return ev
            }
            if b.buffer > 0 {
                b.buffer = 0
                b.ground = nil
                b.slide = false
                b.vy = -RR_JUMP_V * b.jv
                b.hold = true
                b.jumps = b.airMax
                ev.append(RREvent(k: "jump"))
            } else {
                for (vx, vy0) in v.vents where abs(vx - b.x) < 12 && abs(vy0 - b.y) < 1 {
                    b.ground = nil
                    b.slide = false
                    b.vy = -120
                    ev.append(RREvent(k: "updraft"))
                    break
                }
            }
            if b.ground != nil { return ev }
        }
    }
    // ---- in the air
    b.slide = false
    b.airT += dt
    if b.buffer > 0 {
        if b.blocked != nil || b.cling {
            b.buffer = 0
            b.vy = -RR_KICK_V * b.jv
            b.hold = true
            b.pounce = false; b.pad = false
            ev.append(RREvent(k: "kick", solid: b.blocked))
        } else if b.coyote > 0 {
            b.buffer = 0
            b.vy = -RR_JUMP_V * b.jv
            b.hold = true
            b.jumps = b.airMax
            ev.append(RREvent(k: "jump"))
        } else if b.jumps > 0 && c.jumpHit {
            b.buffer = 0
            b.jumps -= 1
            b.vy = -RR_AIR_V * b.jv
            b.hold = true
            b.pounce = false; b.pad = false
            ev.append(RREvent(k: "airjump"))
        }
    }
    if c.downHit && !b.pounce {
        b.pounce = true
        b.pad = false
        b.vy = max(b.vy, RR_POUNCE_V)
        ev.append(RREvent(k: "pounce"))
    }
    let g = (b.vy < 0 && b.hold && !b.pad) ? RR_G_UP : RR_G_DOWN
    b.vy += g * dt
    for (vx, vy0) in v.vents where abs(vx - b.x) < 12 && vy0 - 130 < b.y && b.y <= vy0 + 1 && !b.pounce {
        b.vy = max(b.vy - 2600 * dt, -300)
    }
    if b.glide > 0 && c.jump && b.vy > 0 && !b.pounce { b.vy = min(b.vy, RR_GLIDE_V[min(2, b.glide)]) }
    b.cling = b.blocked != nil && !b.pounce
    if b.cling && b.vy > RR_CLING_V { b.vy = RR_CLING_V }
    b.vy = min(b.vy, RR_MAX_FALL)
    var ny = b.y + b.vy * dt
    if b.vy >= 0 {
        var best: RRSolid?
        for r in v.solids where b.x + hw > r.x && b.x - hw < r.x + r.w && b.y <= r.y + 0.5 && ny >= r.y {
            if best == nil || r.y < best!.y { best = r }
        }
        var line: RRLine?
        for ln in v.lines where ln.x0 <= b.x && b.x <= ln.x1 && b.y <= ln.y + 0.5 && ny >= ln.y {
            if (best == nil || ln.y < best!.y) && (line == nil || ln.y < line!.y) { line = ln }
        }
        if let ln = line {
            b.y = ln.y
            b.vy = -RR_BOUNCE_V * (c.jump ? 1.15 : 1.0)
            b.hold = c.jump
            b.pounce = false; b.pad = false
            b.jumps = b.airMax
            ev.append(RREvent(k: "bounce", line: ln))
            return ev
        }
        if let r = best {
            ev.append(RREvent(k: "land", solid: r, impact: b.vy, pounced: b.pounce))
            b.y = r.y
            b.vy = 0
            b.ground = r
            b.pounce = false; b.pad = false; b.cling = false
            b.jumps = b.airMax
            b.airT = 0
            if b.buffer > 0 {           // a jump pressed just before touching down
                b.buffer = 0
                b.ground = nil
                b.vy = -RR_JUMP_V * b.jv
                b.hold = true
                ev.append(RREvent(k: "jump"))
            }
            return ev
        }
    } else {
        for r in v.solids where b.x + hw > r.x && b.x - hw < r.x + r.w && b.y - h >= r.y + r.h - 0.5 && ny - h < r.y + r.h {
            ny = r.y + r.h + h
            b.vy = 0
            ev.append(RREvent(k: "bonk", solid: r))
            break
        }
    }
    b.y = ny
    if b.wireCd <= 0 {
        for wr in v.wires where wr.x0 + 2 <= b.x && b.x <= wr.x1 - 8 && abs(b.y - RR_STAND_H - wr.y) <= 7 {
            b.wire = wr
            b.y = wr.y + RR_HANG
            b.vy = 0
            b.pounce = false; b.pad = false; b.cling = false
            ev.append(RREvent(k: "grab", wire: wr))
            break
        }
    }
    return ev
}

// ----------------------------------------------------------------------------- drawing: background
private let RR_SKY_LANDMARK_MOON: Set<String> = ["moon", "sea", "domes", "hills", "lanterns", "fireworks", "lighthouse"]

/// Static sky: gradient, stars, moon and the district's landmark.
func rrMakeSky(_ tier: Int) -> Surface {
    let th = RRData.themes[tier]
    let s = Surface(W, H, fill: col("night"))
    for i in 0 ..< 16 { s.fillRect(lerpCol(th.skyTop, th.skyLow, Double(i) / 15), 0, i * 10, W, i < 15 ? 10 : H - 150) }
    let rnd = RRRng(tier * 31 + 5)
    if !["rain", "storm", "fog"].contains(th.weather) {
        for _ in 0 ..< 46 {
            let x = rnd.n(W), y = rnd.n(120)
            let c = ["white", "lavender", "yellow"][rnd.n(3)]
            s.fillRect(col(c), x, y, 1, 1)
        }
    }
    let lm = th.landmark
    if RR_SKY_LANDMARK_MOON.contains(lm) {
        let (mx, my, mr) = lm != "moon" ? (248, 46, 16) : (236, 50, 24)
        s.circle(col("cream"), mx, my, mr)
        s.circle(col("white"), mx - 2, my - 2, mr - 4)
        for (dx, dy, r) in [(-5, 3, 3), (4, -4, 2), (6, 6, 2)] { s.circle(col("cream"), mx + dx, my + dy, r) }
    }
    switch lm {
    case "sea":
        s.fillRect(col("ink"), 0, 150, W, H - 150)
        var y = 152
        while y < H {
            var x = rnd.n(20)
            let step = 26 + rnd.n(20)
            while x < W { s.fillRect(col(y > 170 ? "deep" : "lavender"), x, y, 6 + rnd.n(8), 1); x += step }
            y += 5
        }
        var x = 242
        while x < 256 { s.fillRect(col("yellow"), x, 158 + x % 6, 1, 2); x += 2 }
    case "clock":
        s.fillRect(col("ink"), 52, 34, 34, 130)
        s.polygon(col("ink"), [(48, 36), (69, 10), (90, 36)])
        s.circle(col("cream"), 69, 56, 12)
        s.circle(col("ink"), 69, 56, 12, width: 1)
        s.line(col("ink"), 69, 56, 69, 47)
        s.line(col("ink"), 69, 56, 75, 59)
    case "tram":
        for k in 0 ..< 3 { s.line(col("darkgray"), 0, 60 + k * 6, W, 46 + k * 6) }
    case "towers":
        for (x, w, h) in [(30, 26, 140), (84, 18, 170), (190, 30, 150), (268, 22, 176)] {
            s.fillRect(col("ink"), x, H - h, w, h)
            s.fillRect(col("red"), x + w / 2, H - h - 3, 1, 3)
        }
    case "lanterns":
        for k in 0 ..< 3 {
            let y0 = 40 + k * 22
            var x = 0
            while x < W {
                let y = y0 + Int(8 * sin(Double(x) / Double(W) * .pi + Double(k)))
                s.fillRect(col("darkgray"), x, y, 6, 1)
                if x % 24 == 0 { s.circle(col(["red", "orange", "yellow"][(x / 24 + k) % 3]), x + 3, y + 4, 3) }
                x += 6
            }
        }
    case "cranes":
        for (x0, h) in [(40, 120), (210, 140)] {
            s.fillRect(col("ink"), x0, H - h, 4, h)
            s.fillRect(col("ink"), x0 - 30, H - h, 90, 3)
            s.line(col("ink"), x0 + 50, H - h + 3, x0 + 50, H - h + 50)
            s.fillRect(col("orange"), x0 + 1, H - h - 2, 2, 2)
        }
    default: break
    }
    return s
}

/// A 320 px wide band of rooftops (alpha) that tiles horizontally.
func rrMakeSkyline(_ tier: Int, _ far: Bool) -> Surface {
    let th = RRData.themes[tier]
    let s = Surface(W, H)
    let c = col(far ? th.far : th.mid)
    let win = col(far ? "darkgray" : th.win)
    let rnd = RRRng(tier * 97 + (far ? 1 : 2))
    var x = 0
    let lm = th.landmark
    while x < W {
        var w = 18 + rnd.n(26)
        let top = (far ? 88 : 112) + rnd.n(far ? 40 : 46)
        if x + w > W { w = W - x }
        let style = rnd.n(5)
        if style == 1 && lm == "domes" && w > 14 {      // a glass dome, drawn before the walls cover its base
            s.circle(col(far ? "teal" : "mint"), x + w / 2, top, w / 2 - 1)
            s.circle(c, x + w / 2, top, w / 2 - 2)
            s.fillRect(col("teal"), x + w / 2 - 1, top - w / 2 + 3, 1, w / 2 - 3)
        }
        s.fillRect(c, x, top, w, H - top)
        if style == 0 && w > 12 {
            s.polygon(c, [(Double(x), Double(top)), (Double(x + w / 2), Double(top - 10)), (Double(x + w - 1), Double(top))])
        } else if style == 2 {
            s.fillRect(c, x + w / 3, top - 9, 2, 9)
            if lm == "antennas" || !far { s.fillRect(c, x + w / 3 - 3, top - 7, 8, 1) }
        } else if style == 3 && !far {
            s.rect(c, IRect(x + 3, top - 12, 9, 8), radius: 2)
            s.fillRect(c, x + 4, top - 4, 1, 4)
            s.fillRect(c, x + 10, top - 4, 1, 4)
        }
        if lm == "neon" && !far && w > 16 && rnd.n(2) != 0 {
            s.rect(col(["hotpink", "sky", "lime"][rnd.n(3)]), IRect(x + 3, top + 6, w - 6, 7), width: 1)
        }
        var wy = top + 6
        while wy < H {
            var wx = x + 3
            while wx < x + w - 3 {
                if rnd.n(far ? 5 : 3) == 0 { s.fillRect(win, wx, wy, 2, far ? 3 : 4) }
                wx += far ? 6 : 7
            }
            wy += far ? 9 : 10
        }
        x += w + rnd.n(4)
    }
    return s
}

func rrDrawWeather(_ s: Surface, _ kind: String, _ t: Double, _ cam: Double) {
    switch kind {
    case "rain", "storm":
        let c = col("sky")
        for i in 0 ..< 70 {
            let x = rrMod(i * 53 + Int(t * 60) - Int(cam * 0.6), W + 40) - 20
            let y = rrMod(i * 37 + Int(t * 260), H + 20) - 10
            s.line(c, x, y, x - 3, y + 6)
        }
    case "snow":
        for i in 0 ..< 60 {
            let x = rrMod(i * 61 + Int(sin(t + Double(i)) * 8) - Int(cam * 0.5), W)
            let y = rrMod(i * 29 + Int(t * Double(24 + i % 5 * 6)), H)
            let big = i % 3 == 0 ? 2 : 1
            s.fillRect(col("white"), x, y, big, big)
        }
    case "wind":
        for i in 0 ..< 14 {
            let x = W - rrMod(i * 83 + Int(t * 300), W + 60)
            let y = 30 + (i * 47) % 150
            s.fillRect(col("lavender"), x, y, 10 + i % 3 * 6, 1)
        }
    case "fog":
        for i in 0 ..< 6 {
            let y = 70 + i * 22 + Int(sin(t * 0.7 + Double(i)) * 4)
            s.fillRect(rgba(139, 134, 168, 34), 0, y, W, 14)
        }
        var x = 170
        while x < W { s.fillRect(rgba(139, 134, 168, min(150, x - 170)), x, 24, 10, H - 24); x += 10 }  // thick fog ahead
    default: break
    }
}

// ----------------------------------------------------------------------------- drawing: rooftops
func rrDrawRoof(_ s: Surface, _ r: RRRoof, _ cam: Int, _ th: RRTheme, _ t: Double) {
    let x = Int(r.x) - cam, w = Int(r.w)
    if x > W || x + w < 0 { return }
    let y = Int(r.y)
    if r.glass { rrDrawSkylight(s, r, x, t); return }
    let face = col(th.face), trim = col(th.trim), ledge = col(th.ledge), win = col(th.win)
    s.fillRect(face, x, y, w, H - y)
    s.fillRect(trim, x, y + 3, 2, H - y)
    s.fillRect(trim, x + w - 2, y + 3, 2, H - y)
    s.fillRect(ledge, x - 1, y, w + 2, 3)
    s.fillRect(col("black"), x - 1, y + 3, w + 2, 1)
    // windows: a grid anchored to the world so they scroll with the building
    let rx = Int(r.x)
    var wy = y + 12
    while wy < H {
        var wx = rx + 8
        while wx < rx + w - 10 {
            let sx = wx - cam
            if sx >= -8 && sx <= W {
                let hv = rrHash(wx, wy)
                if hv % 3 == 0 {
                    s.fillRect(trim, sx, wy, 6, 8)
                } else {
                    s.fillRect(col("black"), sx - 1, wy - 1, 8, 10)
                    s.fillRect(hv % 5 != 0 ? win : col("orange"), sx, wy, 6, 8)
                    s.fillRect(face, sx + 3, wy, 1, 8)
                    if hv % 7 == 0 {         // a cat silhouette in the window, now and then
                        s.fillRect(col("black"), sx + 1, wy + 4, 4, 4)
                        s.fillRect(col("black"), sx + 1, wy + 3, 1, 1)
                        s.fillRect(col("black"), sx + 4, wy + 3, 1, 1)
                    }
                }
            }
            wx += 14
        }
        wy += 16
    }
}

func rrDrawSkylight(_ s: Surface, _ r: RRRoof, _ x: Int, _ t: Double) {
    let y = Int(r.y), w = Int(r.w)
    if r.broken {
        s.fillRect(col("black"), x, y, w, H - y)
        s.fillRect(col("ink"), x, y, w, 2)
        var i = 0
        while i < w { s.fillRect(col("sky"), x + i, y + 1 + (i / 5) % 2 * 2, 2, 1); i += 5 }
        return
    }
    s.fillRect(col("darkgray"), x, y + 4, w, H - y - 4)
    s.fillRect(col("gray"), x, y, w, 4)
    s.fillRect(col("teal"), x + 1, y + 1, w - 2, 2)
    let shine = rrMod(Int(t * 30 + r.x), w + 20) - 10
    if shine >= 0 && shine < w - 2 { s.fillRect(col("white"), x + 1 + shine, y + 1, 2, 2) }
    s.fillRect(col("black"), x, y, 1, 4)
    s.fillRect(col("black"), x + w - 1, y, 1, 4)
    if r.crack >= 0 {
        let k = 1 + Int((0.7 - min(0.7, r.crack)) * 8)
        for i in 0 ..< min(k, 5) {
            let cx = x + 3 + (i * 7) % max(4, w - 6)
            s.line(col("white"), cx, y + 1, cx + 3, y + 3)
        }
    }
}

func rrDrawBox(_ s: Surface, _ b: RRBox, _ cam: Int, _ t: Double) {
    let x = Int(b.x) - cam, y = Int(b.y), w = Int(b.w), h = Int(b.h)
    if x > W + 4 || x + w < -4 || !b.alive { return }
    let k = col("black")
    switch b.k {
    case "X", "C":
        s.fillRect(k, x - 1, y - 1, w + 2, h + 2)
        s.fillRect(col("brown"), x, y, w, h)
        s.fillRect(col("peach"), x, y, w, 1)
        s.line(col("choco"), x + 1, y + 1, x + w - 2, y + h - 2)
        s.line(col("choco"), x + w - 2, y + 1, x + 1, y + h - 2)
        s.fillRect(col("choco"), x, y + h / 2, w, 1)
        if b.k == "C" {
            s.fillRect(col("ink"), x + 2, y + 4, w - 4, 6)
            s.blit(sprite("rr_fish"), x + w / 2 - 4, y + 4)
        }
    case "U":
        s.fillRect(k, x - 1, y - 1, w + 2, h + 1)
        s.fillRect(col("gray"), x, y, w, h)
        s.fillRect(col("white"), x, y, w, 1)
        s.fillRect(col("darkgray"), x, y + h - 2, w, 2)
        let cx = x + w / 2, cy = y + h / 2
        let r = min(w, h) / 2 - 2
        s.circle(col("darkgray"), cx, cy, r)
        let a = t * 12
        for i in 0 ..< 3 {
            let ai = a + Double(i) * 2.1
            s.line(col("white"), cx, cy, cx + Int(cos(ai) * Double(r - 1)), cy + Int(sin(ai) * Double(r - 1)))
        }
    case "K":
        s.fillRect(k, x - 1, y + 3, w + 2, h - 3)
        s.fillRect(col("choco"), x, y + 4, w, h - 4)
        var by = y + 6
        while by < y + h {
            let off = (by / 5) % 2 == 1 ? 0 : 4
            var bx = x + off
            while bx < x + w { s.fillRect(col("brown"), bx, by, min(6, x + w - bx), 3); bx += 8 }
            by += 5
        }
        s.fillRect(k, x - 3, y - 1, w + 6, 6)
        s.fillRect(col("darkgray"), x - 2, y, w + 4, 4)
        s.fillRect(col("gray"), x - 2, y, w + 4, 1)
        for i in 0 ..< 3 {          // smoke puffs drifting up-left
            let p = rrFmod(t * 0.6 + Double(i) / 3 + b.x * 0.01, 1)
            s.circle(col(p > 0.5 ? "darkgray" : "gray"), x + w / 2 - Int(p * 14), y - 4 - Int(p * 26), 2 + Int(p * 3))
        }
    case "B":
        for lx in [x + 4, x + w - 6] { s.fillRect(col("darkgray"), lx, y + h, 2, 12) }
        s.fillRect(k, x - 1, y - 1, w + 2, h + 2)
        let hue = ["hotpink", "sky", "lime", "yellow", "orange"][rrHash(Int(b.x), 3) % 5]
        s.fillRect(col("ink"), x, y, w, h)
        let glow = rrMod(Int(t * 3 + b.x), 7) != 0
        s.rect(col(glow ? hue : "darkgray"), IRect(x + 1, y + 1, w - 2, h - 2), width: 1)
        let ad = RR_ADS[rrHash(Int(b.x), 7) % RR_ADS.count]
        drawText(s, ad, x + w / 2, y + h / 2 - 3, glow ? hue : "gray", align: .center, shadow: nil)
    default:
        s.fillRect(col("brown"), x, y, w, h)
    }
}

func rrDrawLift(_ s: Surface, _ m: RRLift, _ cam: Double) {
    let x = Int(m.x - cam), y = Int(m.y), w = Int(m.w), h = Int(m.h)
    if x > W || x + w < 0 { return }
    s.fillRect(col("darkgray"), x + 4, 0, 1, y)
    s.fillRect(col("darkgray"), x + w - 5, 0, 1, y)
    s.fillRect(col("black"), x - 1, y - 1, w + 2, h + 2)
    s.fillRect(col("gray"), x, y, w, h)
    var i = 0
    while i < w { s.fillRect(col("yellow"), x + i, y + h - 2, 3, 2); i += 6 }
    s.fillRect(col("white"), x, y, w, 1)
}

func rrDrawLine(_ s: Surface, _ ln: RRLine, _ cam: Double, _ t: Double, lantern: Bool) {
    let x0 = Int(ln.x0 - cam), x1 = Int(ln.x1 - cam)
    if x0 > W || x1 < 0 { return }
    let y = Int(ln.y)
    for px in [x0, x1] {
        s.fillRect(col("choco"), px - 1, y - 6, 3, H - y + 6)
        s.fillRect(col("brown"), px, y - 6, 1, H - y + 6)
    }
    let span = max(1, x1 - x0)
    var prev: (Int, Int)?
    var i = 0
    while i <= span {
        let p = (x0 + i, y + Int(3 * sin(Double.pi * Double(i) / Double(span))))
        if let q = prev { s.line(col("cream"), q.0, q.1, p.0, p.1) }
        prev = p
        i += 4
    }
    var k = 0
    i = 8
    while i < span - 6 {
        let sag = Int(3 * sin(Double.pi * Double(i) / Double(span)))
        let cx = x0 + i, cy = y + sag
        let sw = Int(sin(t * 3 + Double(i)) * 1.5)
        if lantern {
            let c = ["red", "orange", "yellow", "hotpink"][(k + Int(ln.x0)) % 4]
            s.circle(col("black"), cx + sw, cy + 5, 4)
            s.circle(col(c), cx + sw, cy + 5, 3)
            s.fillRect(col("white"), cx + sw - 1, cy + 3, 1, 1)
        } else {
            let c = col(["pink", "sky", "lime", "yellow", "white", "lavender"][(k + Int(ln.x0)) % 6])
            let kind = (k + Int(ln.x0) / 7) % 3
            if kind == 0 {          // a little shirt
                s.fillRect(c, cx - 3 + sw, cy + 1, 7, 6)
                s.fillRect(c, cx - 5 + sw, cy + 1, 2, 3)
                s.fillRect(c, cx + 4 + sw, cy + 1, 2, 3)
            } else if kind == 1 {   // a sock
                s.fillRect(c, cx - 1 + sw, cy + 1, 3, 7)
                s.fillRect(c, cx - 1 + sw, cy + 6, 5, 2)
            } else {                // a towel
                s.fillRect(c, cx - 3 + sw, cy + 1, 6, 9)
                s.fillRect(col("white"), cx - 3 + sw, cy + 7, 6, 1)
            }
            s.fillRect(col("black"), cx + sw, cy, 1, 2)
        }
        k += 1
        i += 14
    }
}

func rrDrawWire(_ s: Surface, _ wr: RRWire, _ cam: Double, _ t: Double) {
    let x0 = Int(wr.x0 - cam), x1 = Int(wr.x1 - cam), y = Int(wr.y)
    if x0 > W || x1 < 0 { return }
    for px in [x0, x1] {
        s.fillRect(col("darkgray"), px - 1, y - 8, 3, H - y + 8)
        s.fillRect(col("gray"), px - 4, y - 8, 9, 2)
    }
    s.line(col("black"), x0, y + 1, x1, y + 1)
    s.line(col("gray"), x0, y, x1, y)
    if wr.spark {
        let sx = Int(wr.sparkX(t) - cam)
        if x0 <= sx && sx <= x1 {
            for i in 0 ..< 4 {
                let a = t * 30 + Double(i) * 1.6
                s.fillRect(col(i % 2 == 1 ? "yellow" : "white"), sx + Int(cos(a) * 3), y + Int(sin(a) * 3), 2, 2)
            }
        }
    }
}

func rrDrawFish(_ s: Surface, _ f: RRFish, _ cam: Double, _ t: Double, gold: Bool = false) {
    let x = Int(f.x - cam), y = Int(f.y)
    if x < -10 || x > W + 10 { return }
    let bob = Int(sin(t * 5 + f.x * 0.05) * 1.5)
    if gold {
        let sp: Surface
        if f.rainbow {
            sp = sprite("rr_goldfish", remap: Int(t * 8) % 2 == 1 ? ["y": "p", "o": "u"] : ["y": "m", "o": "b"])
        } else {
            sp = sprite("rr_goldfish")
        }
        s.blit(sp, x - 5, y - 3 + bob)
        if rrMod(Int(t * 6 + f.x), 4) == 0 { s.fillRect(col("white"), x + 4, y - 4 + bob, 1, 1) }
    } else {
        s.blit(sprite("rr_fish"), x - 4, y - 2 + bob)
    }
}

func rrDrawCap(_ s: Surface, _ c: RRCap, _ cam: Double, _ t: Double) {
    let x = Int(c.x - cam), y = Int(c.y + sin(t * 4 + c.x) * 2)
    if x < -12 || x > W + 12 { return }
    s.circle(col("black"), x, y, 8)
    s.circle(col(RR_CAP_COLORS[c.k]), x, y, 7)
    s.circle(col("ink"), x, y, 5)
    rrDrawCapIcon(s, c.k, x, y, t)
    s.fillRect(col("white"), x - 4, y - 5, 2, 1)
}

func rrDrawCapIcon(_ s: Surface, _ k: Int, _ x: Int, _ y: Int, _ t: Double) {
    switch k {
    case 0, 5:              // bell
        let c = k == 0 ? "yellow" : (Int(t * 10) % 2 == 1 ? "yellow" : "orange")
        s.circle(col(c), x, y, 3)
        s.fillRect(col(c), x - 4, y + 1, 9, 2)
        s.fillRect(col("black"), x, y + 3, 1, 1)
    case 1:                 // umbrella
        s.polygon(col("sky"), [(Double(x - 4), Double(y)), (Double(x), Double(y - 4)), (Double(x + 4), Double(y))])
        s.fillRect(col("white"), x, y, 1, 4)
        s.fillRect(col("white"), x - 1, y + 3, 1, 1)
    case 2:                 // catnip leaf
        s.ellipse(col("lime"), x - 3, y - 3, 6, 7)
        s.fillRect(col("mint"), x, y - 3, 1, 7)
    case 3:                 // yarn shield
        s.circle(col("peach"), x, y, 3)
        s.line(col("hotpink"), x - 2, y - 2, x + 2, y + 2)
    case 4:                 // milk carton
        s.fillRect(col("white"), x - 2, y - 2, 5, 6)
        s.fillRect(col("sky"), x - 2, y, 5, 2)
        s.fillRect(col("white"), x - 1, y - 4, 3, 2)
    default: break
    }
}

func rrDrawHazard(_ s: Surface, _ hz: RRHaz, _ cam: Double, _ t: Double, _ stime: Double) {
    if !hz.alive && hz.k != "p" && hz.k != "q" { return }
    let x = Int(hz.x - cam), y = Int(hz.y)
    if x < -30 || x > W + 30 { return }
    switch hz.k {
    case "p", "q":
        if !hz.alive {      // knocked away: tumbles off
            if hz.t < 1.2 { s.blit(sprite("rr_pigeon_fly", Int(t * 10), flip: true), x - 6, y - 10) }
            return
        }
        if hz.k == "p" {
            s.blit(sprite("rr_pigeon", Int(t * 6) % 2, flip: hz.dir > 0), x - 6, y - 10 + (Int(t * 6) % 2 == 0 ? 1 : 0))
        } else {
            s.blit(sprite("rr_pigeon_fly", Int(t * 10) % 2), x - 6, y - 6)
        }
    case "s":
        let ph = rrSprinklerPhase(hz, stime)
        s.fillRect(col("darkgray"), x - 3, y - 4, 7, 4)
        s.fillRect(col("gray"), x - 1, y - 7, 3, 3)
        if ph == 1 && Int(t * 10) % 2 == 1 {
            s.fillRect(col("sky"), x, y - 10, 1, 2)
        } else if ph == 2 {
            for i in 0 ..< 14 {
                let yy = y - 8 - rrMod(i * 2 + Int(t * 60), 24)
                let dx = Int(sin(Double(i) * 1.7 + t * 9) * 3)
                s.fillRect(col(i % 3 != 0 ? "sky" : "white"), x + dx, yy, 1 + i % 2, 2)
            }
            s.ellipse(col("sky"), x - 7, y - 33, 15, 6)
        }
    case "a":
        let h = hz.a
        s.fillRect(col("gray"), x - 1, y - h, 2, h)
        for i in 0 ..< 2 {
            let yy = y - h + 2 + i * 5, w = 9 - i * 3
            s.fillRect(col("white"), x - w / 2, yy, w, 1)
            s.fillRect(col("red"), x - w / 2, yy - 1, 1, 2)
            s.fillRect(col("red"), x + w / 2, yy - 1, 1, 2)
        }
        s.fillRect(col(Int(t * 4) % 2 == 1 ? "red" : "orange"), x - 1, y - h - 2, 2, 2)
    case "i":
        let top = hz.a
        let ax = Int(hz.x0 - cam)
        s.fillRect(col("white"), ax - 8, top - 3, 17, 3)
        s.fillRect(col("gray"), ax - 8, top, 17, 1)
        if hz.state == 0 || hz.state == 3 {
            let shake = hz.state == 3 ? Int(sin(t * 60)) : 0
            s.polygon(col("sky"), [(Double(x - 3 + shake), Double(top + 1)), (Double(x + 3 + shake), Double(top + 1)),
                                   (Double(x + shake), Double(top + 11))])
            s.fillRect(col("white"), x - 1 + shake, top + 2, 1, 4)
        } else if hz.state == 1 {
            let yy = Int(hz.y)
            s.polygon(col("sky"), [(Double(x - 3), Double(yy - 10)), (Double(x + 3), Double(yy - 10)), (Double(x), Double(yy))])
            s.fillRect(col("white"), x - 1, yy - 9, 1, 4)
        } else if hz.state == 2 {
            var i = -3
            while i < 4 { s.fillRect(col("sky"), x + i, y - 4 - abs(i), 2, 4 + abs(i) / 2); i += 2 }
        }
    case "d":
        if hz.state == 1 {          // warning
            if Int(t * 8) % 2 == 1 { drawText(s, "!", W - 10, y - 4, "red", scale: 2, outline: "ink") }
            var xx = 80
            while xx < W - 20 { s.fillRect(col("red"), xx, y, 5, 1); xx += 10 }
        } else if hz.state == 2 {
            s.blit(sprite("rr_gully_nofish", Int(t * 10) % 2, remap: ["w": "c", "g": "d"]), x - 9, y - 9)
        }
    case "z":
        s.fillRect(col("gray"), x, y - 26, 1, 26)
        s.circle(col(hz.state == 1 && Int(t * 12) % 2 == 1 ? "yellow" : "gray"), x, y - 27, 2)
        if hz.state == 1 {
            var xx = x - 12
            while xx < x + 13 { s.fillRect(col("yellow"), xx, y - 1, 2, 1); xx += 4 }
        } else if hz.state == 2 {
            var px = x
            var yy = 0
            while yy < y - 27 {
                let nx = x + rrHash(yy, Int(t * 30)) % 9 - 4
                s.line(col("white"), px, yy, nx, yy + 6, width: 2)
                px = nx
                yy += 6
            }
            for i in 0 ..< 8 {
                let xx = x - 12 + rrHash(i, Int(t * 40)) % 25
                s.fillRect(col(i % 2 == 1 ? "yellow" : "white"), xx, y - 2 - rrHash(i, Int(t * 30)) % 7, 2, 2)
            }
        }
    default: break
    }
}

func rrDrawPad(_ s: Surface, _ p: RRPad, _ cam: Double, _ t: Double) {
    let x = Int(p.x - cam), y = Int(p.y)
    if x < -10 || x > W + 10 { return }
    s.fillRect(col("black"), x - 7, y - 6, 15, 7)
    s.fillRect(col("red"), x - 6, y - 5, 13, 5)
    s.fillRect(col("yellow"), x - 6, y - 5, 13, 1)
    for i in 0 ..< 3 { s.fillRect(col("white"), x - 4 + i * 4, y - 3, 1, 2) }
    if Int(t * 6) % 2 == 1 { s.fillRect(col("yellow"), x, y - 9, 1, 2) }
}

func rrDrawVent(_ s: Surface, _ v: (Double, Double), _ cam: Double, _ t: Double) {
    let x = Int(v.0 - cam), y = Int(v.1)
    if x < -20 || x > W + 20 { return }
    s.fillRect(col("black"), x - 10, y - 6, 21, 7)
    s.fillRect(col("gray"), x - 9, y - 5, 19, 5)
    var i = -8
    while i < 9 { s.fillRect(col("darkgray"), x + i, y - 5, 1, 5); i += 3 }
    for j in 0 ..< 6 {
        let yy = y - 10 - (Int(t * 90) + j * 22) % 120
        s.fillRect(col(j % 2 == 1 ? "lavender" : "white"), x - 8 + (j * 7) % 16, yy, 1, 5)
    }
}

func rrDrawWind(_ s: Surface, _ z: (Double, Double, Int), _ cam: Double, _ t: Double) {
    let x0 = Int(z.0 - cam), x1 = Int(z.1 - cam)
    if x0 > W || x1 < 0 { return }
    let head = z.2 == 0
    for i in 0 ..< 10 {
        let span = Double(max(1, x1 - x0))
        let p = rrFmod(t * (head ? 160 : 200) + Double(i * 37), span)
        let x = head ? x1 - Int(p) : x0 + Int(p)
        let y = 40 + (i * 29) % 120
        s.fillRect(col(head ? "lavender" : "mint"), x, y, 8, 1)
        s.fillRect(col("white"), x + (head ? 0 : 6), y, 2, 1)
    }
}
