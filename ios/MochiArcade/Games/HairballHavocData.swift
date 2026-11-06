// HAIRBALL HAVOC campaign tables, read from the data exported by mochi_arcade/games/hairball_havoc_data.py
// (hairball_havoc.EXPORT -> GeneratedData.swift). Both platforms play exactly the same 200 stages.
import Foundation

// robo-toy ids (same order as KINDS in hairball_havoc_data.py)
let HH_MOUSE = 0, HH_CAR = 1, HH_SOCK = 2, HH_VAC = 3, HH_DRUM = 4, HH_BALL = 5, HH_PLANE = 6, HH_POPBOX = 7
let HH_GOLEM = 8, HH_HELI = 9, HH_TOP = 10, HH_MINIBALL = 11, HH_BLOCKLET = 12, HH_GOLD = 13

let HH_TILE = 8
let HH_IX0 = 8, HH_IY0 = 24, HH_IX1 = 312, HH_IY1 = 192        // floor rectangle in screen pixels

struct HHKind { let name: String; let hp, speed, points, first, w, h: Int; let flies: Bool; let intro: String }
struct HHFurn { let name: String; let sizes: [(Int, Int)]; let style, top, front: String }
struct HHRoom {
    let name, floor, a, b, wall, stripe, accentA, accentB: String
    let kinds: [Int]
    let landmark: Int
    let quip: String
}
struct HHBossSpec { let name: String; let minion: Int; let box: (Double, Double); let parts: [(Double, Double, Int, Double)]; let intro: String }

struct HHStage {
    let n: Int
    let room: Int
    let type: String                // normal | bonus | boss
    var mode = ""                   // bonus: parade | roundup
    var doors: [(Int, Int)] = []
    var furn: [(k: Int, x: Int, y: Int, w: Int, h: Int)] = []
    var rug: [Int]? = nil
    var pets: [(kind: Int, x: Int, y: Int, coat: Int)] = []
    var spawns: [(kind: Int, door: Int, time: Double, elite: Int)] = []
    var mods: [String] = []
    var new = -1
    var spd = 1.0, hpx = 1.0, fire = 2.4, bv = 90.0
    var maxOn = 8
    var par = 30.0
    // bonus
    var lanes: [(kind: Int, door: Int, delay: Double, count: Int, gold: Int)] = []
    var dur = 20.0
    // boss
    var boss = -1, lv = 0, final = false, name = ""
    var hp = 100
    var phases: [[String]] = []
    var nphase = 2
    var rest = 1.0
    var cars = 3
}

enum HHData {
    private static let root: [String: Any] = (GameData.json("hairball_havoc") as? [String: Any]) ?? [:]

    private static func d(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func i(_ v: Any?) -> Int { (v as? NSNumber)?.intValue ?? 0 }
    private static func b(_ v: Any?) -> Bool { (v as? NSNumber)?.boolValue ?? false }
    private static func s(_ v: Any?) -> String { v as? String ?? "" }
    private static func arr(_ v: Any?) -> [Any] { (v as? [Any]) ?? [] }

    static let kinds: [HHKind] = arr(root["kinds"]).map { k in
        let a = arr(k)
        return HHKind(name: s(a[0]), hp: i(a[1]), speed: i(a[2]), points: i(a[3]), first: i(a[4]), w: i(a[5]), h: i(a[6]),
                      flies: i(a[7]) != 0, intro: s(a[8]))
    }

    static let furn: [HHFurn] = arr(root["furn"]).map { f in
        let a = arr(f)
        return HHFurn(name: s(a[0]), sizes: arr(a[1]).map { let q = arr($0); return (i(q[0]), i(q[1])) },
                      style: s(a[2]), top: s(a[3]), front: s(a[4]))
    }

    static let rooms: [HHRoom] = arr(root["rooms"]).map { r in
        let a = arr(r)
        return HHRoom(name: s(a[0]), floor: s(a[1]), a: s(a[2]), b: s(a[3]), wall: s(a[4]), stripe: s(a[5]),
                      accentA: s(a[6]), accentB: s(a[7]), kinds: arr(a[8]).map { i($0) }, landmark: i(a[9]), quip: s(a[10]))
    }

    static let bosses: [HHBossSpec] = arr(root["bosses"]).map { v in
        let a = arr(v)
        let bx = arr(a[2])
        return HHBossSpec(name: s(a[0]), minion: i(a[1]), box: (d(bx[0]), d(bx[1])),
                          parts: arr(a[3]).map { let p = arr($0); return (d(p[0]), d(p[1]), i(p[2]), d(p[3])) },
                          intro: s(a[5]))
    }

    static let modText: [String: String] = (root["mod_text"] as? [String: String]) ?? [:]

    static let stages: [HHStage] = arr(root["stages"]).map { v in
        let o = v as? [String: Any] ?? [:]
        var st = HHStage(n: i(o["n"]), room: i(o["room"]), type: s(o["type"]))
        st.mode = s(o["mode"])
        st.doors = arr(o["doors"]).map { let q = arr($0); return (i(q[0]), i(q[1])) }
        st.furn = arr(o["furn"]).map { let q = arr($0); return (i(q[0]), i(q[1]), i(q[2]), i(q[3]), i(q[4])) }
        if let r = o["rug"] as? [Any] { st.rug = r.map { i($0) } }
        st.pets = arr(o["pets"]).map { let q = arr($0); return (i(q[0]), i(q[1]), i(q[2]), i(q[3])) }
        st.spawns = arr(o["spawns"]).map { let q = arr($0); return (i(q[0]), i(q[1]), d(q[2]), i(q[3])) }
        st.mods = (o["mods"] as? [String]) ?? []
        if o["new"] != nil { st.new = i(o["new"]) }
        if o["spd"] != nil { st.spd = d(o["spd"]) }
        if o["hpx"] != nil { st.hpx = d(o["hpx"]) }
        if o["fire"] != nil { st.fire = d(o["fire"]) }
        if o["bv"] != nil { st.bv = d(o["bv"]) }
        if o["max_on"] != nil { st.maxOn = i(o["max_on"]) }
        if o["par"] != nil { st.par = d(o["par"]) }
        st.lanes = arr(o["lanes"]).map { let q = arr($0); return (i(q[0]), i(q[1]), d(q[2]), i(q[3]), i(q[4])) }
        if o["dur"] != nil { st.dur = d(o["dur"]) }
        if o["boss"] != nil {
            st.boss = i(o["boss"]); st.lv = i(o["lv"]); st.final = b(o["final"]); st.name = s(o["name"])
            st.hp = i(o["hp"]); st.phases = (o["phases"] as? [[String]]) ?? [["fan"]]; st.nphase = i(o["nphase"])
            st.rest = d(o["rest"]); st.cars = i(o["cars"])
        }
        return st
    }

    static func stage(_ n: Int) -> HHStage { stages[max(1, min(STAGES, n)) - 1] }

    // ---------------------------------------------------------------- geometry (same as hairball_havoc_data.py)
    /// Screen rectangle of a doorway. side 0 = top wall, 1 = left wall, 2 = right wall.
    static func doorRect(_ side: Int, _ pos: Int) -> IRect {
        if side == 0 { return IRect(HH_IX0 + pos * HH_TILE, HH_IY0 - 14, HH_TILE * 3, 14) }
        if side == 1 { return IRect(0, HH_IY0 + pos * HH_TILE, HH_IX0, HH_TILE * 3) }
        return IRect(HH_IX1, HH_IY0 + pos * HH_TILE, W - HH_IX1, HH_TILE * 3)
    }

    /// Where a toy appears when it walks in, and the inward direction.
    static func doorSpawn(_ side: Int, _ pos: Int) -> (Double, Double, Double, Double) {
        if side == 0 { return (Double(HH_IX0 + pos * HH_TILE + 12), Double(HH_IY0 + 6), 0, 1) }
        if side == 1 { return (Double(HH_IX0 + 6), Double(HH_IY0 + pos * HH_TILE + 12), 1, 0) }
        return (Double(HH_IX1 - 6), Double(HH_IY0 + pos * HH_TILE + 12), -1, 0)
    }
}
