// COMET KITTY campaign tables, read from the data exported by mochi_arcade/games/comet_kitty_data.py
// (comet_kitty.EXPORT -> GeneratedData.swift). Both platforms fly exactly the same 200 stages.
import Foundation

struct CKSlot { let col, row, kind, path, mirror: Int; let delay: Double; let group, cap: Int }
struct CKWave { let path, mirror: Int; let delay: Double; let count, gold, kind: Int }
typealias CKRGB = (Int, Int, Int)

struct CKStage {
    let n: Int
    let type: String            // normal | bonus | boss
    let theme: Int
    // normal
    var slots: [CKSlot] = []
    var groups = 0
    var mods: [String] = []
    var new = -1
    var speed = 140.0
    var diveGap = 2.0, diveMax = 1, shots = 1
    var efire = 0.0, burst = 1, amb = 0.0, volley = 0.0
    var bv = 80.0, fireGap = 3.0
    var hpb = 0, hpj = 0
    var par = 30.0
    // bonus
    var waves: [CKWave] = []
    // boss
    var boss = 0, lv = 0, final = false, name = ""
    var phases: [[String]] = []
    var nphase = 2, hp = 100, rest = 1.0
}

struct CKTheme {
    let name: String
    let top: CKRGB, bot: CKRGB
    let neb: [(Int, Int, Int, CKRGB, Int)]
    let rocks: [(Int, Int, Int)]
    let planet: (kind: Int, x: Int, y: Int, r: Int, c1: CKRGB, c2: CKRGB)
}

struct CKBossSpec {
    let name: String
    let box: (Double, Double)
    let parts: [(Double, Double, Int, Double)]   // dx dy r share-of-hp
    let weak: (Double, Double, Int)
    let intro: String
}

struct CKKind { let name: String; let hp, ptsForm, ptsDive, unlock: Int; let desc: String }

// foe ids (same order as KINDS in comet_kitty_data.py)
let CK_JELLY = 0, CK_MOTH = 1, CK_PUFF = 2, CK_DART = 3, CK_SPORE = 4, CK_BLOB = 5, CK_SHELL = 6, CK_COMET = 7
let CK_URCHIN = 8, CK_WISP = 9, CK_MINI = 10, CK_MINE = 11, CK_METEOR = 12, CK_GOLD = 13

enum CKData {
    private static let root: [String: Any] = (GameData.json("comet_kitty") as? [String: Any]) ?? [:]

    private static func d(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func i(_ v: Any?) -> Int { (v as? NSNumber)?.intValue ?? 0 }
    private static func b(_ v: Any?) -> Bool { (v as? NSNumber)?.boolValue ?? false }
    private static func arr(_ v: Any?) -> [Any] { (v as? [Any]) ?? [] }
    private static func rgb(_ v: Any?) -> CKRGB { let a = arr(v); return (i(a[0]), i(a[1]), i(a[2])) }

    static let consts: [String: Any] = (root["consts"] as? [String: Any]) ?? [:]
    static let step = d(consts["step"])
    static let colDX = d(consts["col_dx"]), rowDY = d(consts["row_dy"]), rowY0 = d(consts["row_y0"])
    static let capsules: [String] = (root["capsules"] as? [String]) ?? []

    static let paths: [[(Double, Double)]] = arr(root["paths"]).map { p in arr(p).map { let q = arr($0); return (d(q[0]), d(q[1])) } }

    static let kinds: [CKKind] = arr(root["kinds"]).map { k in
        let a = arr(k)
        return CKKind(name: a[0] as? String ?? "", hp: i(a[1]), ptsForm: i(a[2]), ptsDive: i(a[3]), unlock: i(a[4]),
                      desc: a[5] as? String ?? "")
    }

    static let bosses: [CKBossSpec] = arr(root["bosses"]).map { v in
        let o = v as? [String: Any] ?? [:]
        let bx = arr(o["box"]), wk = arr(o["weak"])
        return CKBossSpec(name: o["name"] as? String ?? "", box: (d(bx[0]), d(bx[1])),
                          parts: arr(o["parts"]).map { let p = arr($0); return (d(p[0]), d(p[1]), i(p[2]), d(p[3])) },
                          weak: (d(wk[0]), d(wk[1]), i(wk[2])), intro: o["intro"] as? String ?? "")
    }

    static let themes: [CKTheme] = arr(root["themes"]).map { v in
        let o = v as? [String: Any] ?? [:]
        let p = arr(o["planet"])
        return CKTheme(name: o["name"] as? String ?? "", top: rgb(o["top"]), bot: rgb(o["bot"]),
                       neb: arr(o["neb"]).map { let q = arr($0); return (i(q[0]), i(q[1]), i(q[2]), rgb(q[3]), i(q[4])) },
                       rocks: arr(o["rocks"]).map { let q = arr($0); return (i(q[0]), i(q[1]), i(q[2])) },
                       planet: (kind: i(p[0]), x: i(p[1]), y: i(p[2]), r: i(p[3]), c1: rgb(p[4]), c2: rgb(p[5])))
    }

    static let stages: [CKStage] = arr(root["stages"]).map { v in
        let o = v as? [String: Any] ?? [:]
        var s = CKStage(n: i(o["n"]), type: o["type"] as? String ?? "normal", theme: i(o["theme"]))
        switch s.type {
        case "normal":
            s.slots = arr(o["slots"]).map { let a = arr($0)
                return CKSlot(col: i(a[0]), row: i(a[1]), kind: i(a[2]), path: i(a[3]), mirror: i(a[4]), delay: d(a[5]),
                              group: i(a[6]), cap: i(a[7])) }
            s.groups = i(o["groups"]); s.mods = (o["mods"] as? [String]) ?? []; s.new = i(o["new"])
            s.speed = d(o["speed"]); s.diveGap = d(o["dive_gap"]); s.diveMax = i(o["dive_max"]); s.shots = i(o["shots"])
            s.efire = d(o["efire"]); s.burst = i(o["burst"]); s.amb = d(o["amb"]); s.volley = d(o["volley"])
            s.bv = d(o["bv"]); s.fireGap = d(o["fire_gap"]); s.hpb = i(o["hpb"]); s.hpj = i(o["hpj"]); s.par = d(o["par"])
        case "bonus":
            s.waves = arr(o["waves"]).map { let a = arr($0)
                return CKWave(path: i(a[0]), mirror: i(a[1]), delay: d(a[2]), count: i(a[3]), gold: i(a[4]), kind: i(a[5])) }
            s.speed = d(o["speed"]); s.par = d(o["par"])
        default:
            s.boss = i(o["boss"]); s.lv = i(o["lv"]); s.final = b(o["final"]); s.name = o["name"] as? String ?? ""
            s.phases = (o["phases"] as? [[String]]) ?? [["fan"]]; s.nphase = i(o["nphase"])
            s.hp = i(o["hp"]); s.bv = d(o["bv"]); s.rest = d(o["rest"]); s.par = d(o["par"])
        }
        return s
    }

    static func stage(_ n: Int) -> CKStage { stages[max(1, min(STAGES, n)) - 1] }
}
