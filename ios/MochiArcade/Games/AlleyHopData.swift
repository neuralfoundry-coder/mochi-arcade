// ALLEY HOP stage table (exported from mochi_arcade/games/alley_hop_stages.py via alley_hop.EXPORT) and the lane
// maths shared with the desktop version: every lane is a pure function of 'lane time'.
import Foundation

let AH_TOP = 12, AH_CELL = 16, AH_ROWS = 11, AH_COLS = 20, AH_START_COL = 9
let AH_CARRIERS: Set<String> = ["water", "gap", "belt"]

struct AHItem { let kind: String; let x: Double; let w: Double }

struct AHLane {
    let t: String
    let v, ph, sw, om: Double
    let p: Int
    let it: [AHItem]
    let dv: [Double]       // cycle, down, stagger (diving ducks / fish)
    let tr: [Double]       // cycle, warn, length, speed, phase, dir (trains)
    let gt: [Double]       // cycle, open, phase (gates)
    let gc: [Int], bl: [Int], pd: [Int]
    let soft: Bool
    var carrier: Bool { AH_CARRIERS.contains(t) }
}

struct AHBossSpec {
    let kind, name, title, hint: String
    let hp: Int
    let sp, rest, tell: Double
    let atk: [String]
    let n: Int
    let rk, ck: String
    let cyc: Int
}

struct AHStage {
    let n, tier, theme: Int
    let kind, name, newLine, line, bonus, layout: String
    let lanes: [AHLane]
    let kittens: [(r: Int, x: Double, coat: Int)]
    let items: [(kind: String, r: Int, x: Double)]
    let boxes: [Int]
    let lids: [Double]
    let manholes: [[Int]]
    let lamps: [[Double]]        // x, y, radius, flicker phase
    let clock: Double
    let dark, rain: Bool
    let boss: AHBossSpec?
}

enum AHData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func nums(_ v: Any?) -> [Double] { ((v as? [Any]) ?? []).map { num($0) } }
    private static func ints(_ v: Any?) -> [Int] { ((v as? [Any]) ?? []).map { Int(num($0)) } }
    private static let root: [String: Any] = (GameData.json("alley_hop") as? [String: Any]) ?? [:]

    static func lane(_ d: [String: Any]) -> AHLane {
        let items = ((d["it"] as? [[Any]]) ?? []).map { a in
            AHItem(kind: a[0] as? String ?? "crate", x: num(a[1]), w: num(a[2]))
        }
        return AHLane(t: d["t"] as? String ?? "safe", v: num(d["v"]), ph: num(d["ph"]), sw: num(d["sw"]), om: num(d["om"]),
                      p: Int(num(d["p"])), it: items, dv: nums(d["dv"]), tr: nums(d["tr"]), gt: nums(d["gt"]),
                      gc: ints(d["gc"]), bl: ints(d["bl"]), pd: ints(d["pd"]), soft: num(d["soft"]) != 0)
    }

    static let stages: [AHStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: AHBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = AHBossSpec(kind: b["kind"] as? String ?? "bruno", name: b["name"] as? String ?? "",
                              title: b["title"] as? String ?? "", hint: b["hint"] as? String ?? "",
                              hp: Int(num(b["hp"])), sp: num(b["sp"]), rest: num(b["rest"]), tell: num(b["tell"]),
                              atk: b["atk"] as? [String] ?? [], n: Int(num(b["n"])), rk: b["rk"] as? String ?? "ball",
                              ck: b["ck"] as? String ?? "can", cyc: Int(num(b["cyc"])))
        }
        let kittens = ((d["kittens"] as? [[Any]]) ?? []).map { a in (r: Int(num(a[0])), x: num(a[1]), coat: Int(num(a[2]))) }
        let items = ((d["items"] as? [[Any]]) ?? []).map { a in (kind: a[0] as? String ?? "fish", r: Int(num(a[1])), x: num(a[2])) }
        return AHStage(n: Int(num(d["n"])), tier: Int(num(d["tier"])), theme: Int(num(d["theme"])),
                       kind: d["kind"] as? String ?? "normal", name: d["name"] as? String ?? "",
                       newLine: d["new"] as? String ?? "", line: d["line"] as? String ?? "",
                       bonus: d["bonus"] as? String ?? "", layout: d["layout"] as? String ?? "",
                       lanes: ((d["lanes"] as? [[String: Any]]) ?? []).map { lane($0) },
                       kittens: kittens, items: items, boxes: ints(d["boxes"]), lids: nums(d["lids"]),
                       manholes: ((d["manholes"] as? [Any]) ?? []).map { ints($0) },
                       lamps: ((d["lamps"] as? [Any]) ?? []).map { nums($0) },
                       clock: num(d["clock"]), dark: num(d["dark"]) != 0, rain: num(d["rain"]) != 0, boss: boss)
    }

    /// name, ground, ground2, road, paint, water, water2, void, wall, accent, focus lane code
    static let themes: [[String]] = ((root["themes"] as? [[Any]]) ?? []).map { $0.map { $0 as? String ?? "" } }
}

// ----------------------------------------------------------------------------- lane maths (pure functions of time)
@inline(__always) func ahPmod(_ a: Double, _ b: Double) -> Double { a - b * floor(a / b) }
@inline(__always) func ahImod(_ a: Int, _ b: Int) -> Int { ((a % b) + b) % b }
@inline(__always) func ahCY(_ r: Int) -> Int { AH_TOP + r * AH_CELL + 8 }
/// Python's `int(x // 16)` (floor, also for negative x).
@inline(__always) func ahCol(_ x: Double) -> Int { Int(floor(x / Double(AH_CELL))) }

func ahShift(_ ln: AHLane, _ lt: Double) -> Double {
    if ln.sw != 0 { return ln.sw * sin(ln.om * lt + ln.ph) }
    return ln.ph + ln.v * lt
}

func ahPad(_ ln: AHLane) -> Double { Double((ln.p - W) / 2) }

/// Screen x of a pattern item's left edge.
func ahItemSX(_ ln: AHLane, _ ix: Double, _ sh: Double) -> Double { ahPmod(ix + sh, Double(ln.p)) - ahPad(ln) }

/// 0 afloat, 1 about to dive (telegraph), 2 under water.
func ahDive(_ ln: AHLane, _ i: Int, _ lt: Double) -> Int {
    if ln.dv.count < 3 { return 0 }
    let cyc = ln.dv[0], down = ln.dv[1], stag = ln.dv[2]
    let c = ahPmod(lt + Double(i) * stag, cyc)
    if c < cyc - down - 0.9 { return 0 }
    return c < cyc - down ? 1 : 2
}

/// (warning, x0, x1): the train's extent on screen (nil when no train is passing).
func ahTrain(_ ln: AHLane, _ lt: Double) -> (warn: Bool, x0: Double?, x1: Double?) {
    let cyc = ln.tr[0], warn = ln.tr[1], length = ln.tr[2], speed = ln.tr[3], ph = ln.tr[4], d = ln.tr[5]
    let c = ahPmod(lt + ph, cyc)
    if c < warn { return (true, nil, nil) }
    let dist = (c - warn) * speed
    if dist > Double(W) + length + 80 { return (false, nil, nil) }
    if d > 0 {
        let front = -40 + dist
        return (true, front - length, front)
    }
    let front = Double(W) + 40 - dist
    return (true, front, front + length)
}

func ahGateOpen(_ ln: AHLane, _ lt: Double) -> Bool { ahPmod(lt + ln.gt[2], ln.gt[0]) < ln.gt[1] }

func ahGateWarn(_ ln: AHLane, _ lt: Double) -> Bool {
    let c = ahPmod(lt + ln.gt[2], ln.gt[0])
    return ln.gt[1] - 0.8 < c && c < ln.gt[1]
}
