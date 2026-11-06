// PAW PINBALL tables and missions, read from the Python export (games/paw_pinball_tables.py via EXPORT):
// both platforms collide against exactly the same walls and play exactly the same 200 missions.
import Foundation

// shared shell (mirrors games/paw_pinball_tables.py)
let PP_BALL_R = 3.0
let PP_TX0 = 68, PP_TX1 = 252
let PP_LW = 72.0, PP_RW = 238.0
let PP_LANE_X = 243.0, PP_LANE_OUT = 248.0
let PP_CX = 155.0, PP_MIRROR = 310.0
let PP_ARCH = (cx: 160.0, cy: 62.0, rx: 88.0, ry: 56.0)
let PP_PLUNGE_Y = 189.0, PP_GATE_Y = 74.0
let PP_FLIP_Y = 169.0
let PP_FLIP_X = [128.0, 182.0]
let PP_METAL = 0, PP_RUBBER = 1, PP_SLING = 2, PP_GATE = 3

func ppArchY(_ x: Double) -> Double {
    let u = max(-1, min(1, (x - PP_ARCH.cx) / PP_ARCH.rx))
    return PP_ARCH.cy - PP_ARCH.ry * (1 - u * u).squareRoot()
}

struct PPRamp {
    let kind: String
    let gate: [Double]
    let dir: (Double, Double)
    let path: [(Double, Double)]
    let out: (Double, Double)
}

struct PPTheme { let a, b: String; let pat: Int; let wall, accent, bump: String; let deco: Int }

struct PPTable {
    let name: String
    let walls: [[Double]]          // x1, y1, x2, y2, kind
    let posts: [[Double]]          // x, y, r
    let bumpers: [(Double, Double)]
    let fish: [[Double]]           // x1, y1, x2, y2, face, bank
    let saucer: (Double, Double)?
    let ramps: [PPRamp]
    let spinner: [Double]          // x1, y, x2, y (empty: none)
    let spots: [(Double, Double)]
    let lanes: [(Double, Double)]
    let theme: PPTheme
}

struct PPBossSpec { let kind, name, title: String; let hp: Int; let speed, rate: Double; let extra: [String]; let round: Int }

struct PPStage {
    let n: Int, kind: String, tier: Int, name: String
    let goals: [(String, Int)]
    let time: Double, grav: Double, save: Double
    let boss: PPBossSpec?
    let bonus: String, newLine: String
}

enum PPData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func nums(_ v: Any?) -> [Double] { ((v as? [Any]) ?? []).map { num($0) } }
    private static func pts(_ v: Any?) -> [(Double, Double)] { ((v as? [[Any]]) ?? []).map { (num($0[0]), num($0[1])) } }
    private static let root: [String: Any] = (GameData.json("paw_pinball") as? [String: Any]) ?? [:]

    private static func table(_ d: [String: Any]) -> PPTable {
        let th = d["theme"] as? [String: Any] ?? [:]
        let theme = PPTheme(a: th["a"] as? String ?? "choco", b: th["b"] as? String ?? "brown", pat: Int(num(th["pat"])),
                            wall: th["wall"] as? String ?? "cream", accent: th["accent"] as? String ?? "peach",
                            bump: th["bump"] as? String ?? "orange", deco: Int(num(th["deco"])))
        let ramps: [PPRamp] = ((d["ramps"] as? [[String: Any]]) ?? []).map { r in
            let dir = nums(r["dir"]), out = nums(r["out"])
            return PPRamp(kind: r["kind"] as? String ?? "tower", gate: nums(r["gate"]), dir: (dir[0], dir[1]),
                          path: pts(r["path"]), out: (out[0], out[1]))
        }
        let sa = nums(d["saucer"])
        return PPTable(name: d["name"] as? String ?? "", walls: ((d["walls"] as? [Any]) ?? []).map { nums($0) },
                       posts: ((d["posts"] as? [Any]) ?? []).map { nums($0) }, bumpers: pts(d["bumpers"]),
                       fish: ((d["fish"] as? [Any]) ?? []).map { nums($0) }, saucer: sa.count == 2 ? (sa[0], sa[1]) : nil,
                       ramps: ramps, spinner: nums(d["spinner"]), spots: pts(d["spots"]), lanes: pts(d["lanes"]), theme: theme)
    }

    static let tables: [PPTable] = ((root["tables"] as? [[String: Any]]) ?? []).map { table($0) }
    static let arena: PPTable = table((root["arena"] as? [String: Any]) ?? [:])
    static let tower: [(Double, Double)] = pts(root["tower"])
    static let guide: [(Double, Double)] = pts(root["guide"])
    static let sling: [(Double, Double)] = pts(root["sling"])
    /// goal type -> (HUD word, intro text with {n})
    static let goals: [String: (String, String)] = {
        var d: [String: (String, String)] = [:]
        for (k, v) in (root["goals"] as? [String: [String]]) ?? [:] { d[k] = (v[0], v[1]) }
        return d
    }()

    static let stages: [PPStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: PPBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = PPBossSpec(kind: b["kind"] as? String ?? "buster", name: b["name"] as? String ?? "",
                              title: b["title"] as? String ?? "", hp: Int(num(b["hp"])), speed: num(b["speed"]),
                              rate: num(b["rate"]), extra: b["extra"] as? [String] ?? [], round: Int(num(b["round"])))
        }
        let goals: [(String, Int)] = ((d["goals"] as? [[Any]]) ?? []).map { ($0[0] as? String ?? "bump", Int(num($0[1]))) }
        return PPStage(n: Int(num(d["n"])), kind: d["kind"] as? String ?? "normal", tier: Int(num(d["tier"])),
                       name: d["name"] as? String ?? "", goals: goals, time: num(d["time"]), grav: num(d["grav"]),
                       save: num(d["save"]), boss: boss, bonus: d["bonus"] as? String ?? "", newLine: d["new"] as? String ?? "")
    }
}
