// YARN WEAVER campaign data: the 200-stage table exported from games/yarn_weaver_stages.py (EXPORT in
// games/yarn_weaver.py), plus the grid helpers both platforms share (base grid, furniture, open regions).
import Foundation

let YW_GW = 152, YW_GH = 88            // playfield grid (2x2 pixel cells) -> 304 x 176 pixels
let YW_FX = 8, YW_FY = 20              // where the playfield sits on the 320x200 canvas

struct YWPic {
    let name, bg, bg2: String
    let pat, pose: Int
    let fur, fur2: String
    let mark: Int
    let eye: String
    let mood, acc: Int
    let accc: String
    let prop: Int
    let propc, cush: String
    let x: Int
}

struct YWBossSpec {
    let kind, name: String
    let tier: Int
    let hp, rate, speed: Double
    let extra: [String]
    let minions: Int
}

/// Furniture: a rect (x, y, w, h) or a round pouf (centre x, y and radius r), in grid cells.
struct YWShape { let round: Bool; let x, y, w, h, r: Int; let c: String }

struct YWStage {
    let n, tier: Int
    let kind, room, layout: String
    let shapes: [YWShape]
    let target: Int
    let speed: Double
    let pic: YWPic
    let quip, newLine: String
    let fluffs, minis, zips, hunters, moths: Int
    let nose, storm: Double
    let knots: [(Int, Int)]
    let items: Double
    let time: Double
    let bonus: String
    let poms, fish: Int
    let boss: YWBossSpec?
    let fspeed, zspeed: Double
}

struct YWTheme { let name, a, b: String; let pat: Int; let yarnA, yarnB, song: String }

enum YWData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func int(_ v: Any?) -> Int { Int(num(v)) }
    private static func str(_ v: Any?) -> String { v as? String ?? "" }
    private static let root: [String: Any] = (GameData.json("yarn_weaver") as? [String: Any]) ?? [:]

    static let stages: [YWStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        let p = d["pic"] as? [String: Any] ?? [:]
        let pic = YWPic(name: str(p["name"]), bg: str(p["bg"]), bg2: str(p["bg2"]), pat: int(p["pat"]), pose: int(p["pose"]),
                        fur: str(p["fur"]), fur2: str(p["fur2"]), mark: int(p["mark"]), eye: str(p["eye"]), mood: int(p["mood"]),
                        acc: int(p["acc"]), accc: str(p["accc"]), prop: int(p["prop"]), propc: str(p["propc"]),
                        cush: str(p["cush"]), x: int(p["x"]))
        let shapes: [YWShape] = ((d["shapes"] as? [[Any]]) ?? []).map { a in
            if str(a[0]) == "r" {
                return YWShape(round: false, x: int(a[1]), y: int(a[2]), w: int(a[3]), h: int(a[4]), r: 0, c: str(a[5]))
            }
            return YWShape(round: true, x: int(a[1]), y: int(a[2]), w: 0, h: 0, r: int(a[3]), c: str(a[4]))
        }
        var boss: YWBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = YWBossSpec(kind: str(b["kind"]), name: str(b["name"]), tier: int(b["tier"]), hp: num(b["hp"]),
                              rate: num(b["rate"]), speed: num(b["speed"]), extra: b["extra"] as? [String] ?? [],
                              minions: int(b["minions"]))
        }
        let knots = ((d["knots"] as? [[Any]]) ?? []).map { (int($0[0]), int($0[1])) }
        return YWStage(n: int(d["n"]), tier: int(d["tier"]), kind: str(d["kind"]), room: str(d["room"]), layout: str(d["layout"]),
                       shapes: shapes, target: int(d["target"]), speed: num(d["speed"]), pic: pic, quip: str(d["quip"]),
                       newLine: str(d["new"]), fluffs: int(d["fluffs"]), minis: int(d["minis"]), zips: int(d["zips"]),
                       hunters: int(d["hunters"]), moths: int(d["moths"]), nose: num(d["nose"]), storm: num(d["storm"]),
                       knots: knots, items: num(d["items"]), time: num(d["time"]), bonus: str(d["bonus"]),
                       poms: int(d["poms"]), fish: int(d["fish"]), boss: boss, fspeed: num(d["fspeed"]), zspeed: num(d["zspeed"]))
    }

    static let themes: [YWTheme] = ((root["themes"] as? [[Any]]) ?? []).map { a in
        YWTheme(name: str(a[0]), a: str(a[1]), b: str(a[2]), pat: int(a[3]), yarnA: str(a[4]), yarnB: str(a[5]), song: str(a[6]))
    }

    /// Mark furniture cells in a flat GW*GH grid.
    static func applyShapes(_ g: inout [UInt8], _ shapes: [YWShape], _ value: UInt8 = 1) {
        for sh in shapes {
            if !sh.round {
                for yy in max(0, sh.y) ..< min(YW_GH, sh.y + sh.h) {
                    for xx in max(0, sh.x) ..< min(YW_GW, sh.x + sh.w) { g[yy * YW_GW + xx] = value }
                }
            } else {
                let r = sh.r
                for yy in max(0, sh.y - r) ..< min(YW_GH, sh.y + r + 1) {
                    for xx in max(0, sh.x - r) ..< min(YW_GW, sh.x + r + 1)
                    where (xx - sh.x) * (xx - sh.x) + (yy - sh.y) * (yy - sh.y) <= r * r {
                        g[yy * YW_GW + xx] = value
                    }
                }
            }
        }
    }

    /// 0 = open rug, 1 = claimed (the border ring and the furniture).
    static func baseGrid(_ shapes: [YWShape]) -> [UInt8] {
        var g = [UInt8](repeating: 0, count: YW_GW * YW_GH)
        for x in 0 ..< YW_GW { g[x] = 1; g[(YW_GH - 1) * YW_GW + x] = 1 }
        for y in 0 ..< YW_GH { g[y * YW_GW] = 1; g[y * YW_GW + YW_GW - 1] = 1 }
        applyShapes(&g, shapes)
        return g
    }

    /// 4-connected regions of open (0) cells: lists of cell indices.
    static func openRegions(_ g: [UInt8]) -> [[Int]] {
        var seen = [Bool](repeating: false, count: g.count)
        var out: [[Int]] = []
        for i in 0 ..< g.count where g[i] == 0 && !seen[i] {
            var reg = [i]
            seen[i] = true
            var k = 0
            while k < reg.count {
                let c = reg[k]
                k += 1
                let x = c % YW_GW
                for n in [x > 0 ? c - 1 : -1, x < YW_GW - 1 ? c + 1 : -1, c - YW_GW, c + YW_GW]
                where n >= 0 && n < g.count && g[n] == 0 && !seen[n] {
                    seen[n] = true
                    reg.append(n)
                }
            }
            out.append(reg)
        }
        return out
    }
}
