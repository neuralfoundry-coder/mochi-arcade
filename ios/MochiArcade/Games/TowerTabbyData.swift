// TOWER TABBY stage data (port of the parts of games/tower_tabby_data.py the game uses at run time).
// The 200 stages themselves are generated in Python and arrive through GameData.json("tower_tabby").
import Foundation

let TT_NC = 20                       // cells per level line
let TT_CW = 16                       // cell width in pixels
let TT_LEVEL_Y = [192.0, 162.0, 132.0, 102.0, 72.0, 42.0]
let TT_TILT = 4.0
let TT_SOLID: Set<Character> = ["=", "H", "R", "S", "X", "<", ">", "W", "G", "P"]

@inline(__always) func ttPmod(_ a: Int, _ b: Int) -> Int { ((a % b) + b) % b }
@inline(__always) func ttFmod(_ a: Double, _ b: Double) -> Double { a - floor(a / b) * b }

/// Shelf surface y of a level at pixel x (slope +1: the right end is lower, things roll right).
func ttYAt(_ level: Int, _ slope: Int, _ x: Double) -> Double {
    TT_LEVEL_Y[level] + Double(slope) * TT_TILT * (x - 160) / 160.0
}

struct TTStage {
    var k = "normal", nm = "", th = 0
    var lv: [[Character]] = []              // bottom (floor) to top
    var sl = [0, 0, 0, 0, 0, 0]
    var en: [(String, Int, Int)] = []        // kind, cell, level
    var fish: [(Int, Int)] = []
    var kit: [(Int, Int)] = []
    var it: [(Int, Int, String)] = []
    var mix: [String] = ["yarn"]
    var rate = 3.0, hs = 1.0, moth = 0.0
    var mods: [String] = []
    var new = "", nst = "", quip = ""
    var par = 40
    var boss = "kaw", hp = 14, lvN = 0
    var pat: [String] = []
    var spd = 1.0
    var bt = "fish", time = 20

    func solid(_ k: Int, _ c: Int) -> Bool { k >= 0 && k < 6 && c >= 0 && c < TT_NC && TT_SOLID.contains(lv[k][c]) }

    func find(_ ch: Character) -> (Int, Int)? {
        for k in 0 ..< lv.count { if let c = lv[k].firstIndex(of: ch) { return (k, c) } }
        return nil
    }

    /// Box tunnel pairs in reading order (bottom level first, left to right).
    func warpPairs() -> [((Int, Int), (Int, Int))] {
        var cells: [(Int, Int)] = []
        for k in 0 ..< lv.count { for c in 0 ..< TT_NC where lv[k][c] == "W" { cells.append((k, c)) } }
        var out: [((Int, Int), (Int, Int))] = []
        var i = 0
        while i + 1 < cells.count { out.append((cells[i], cells[i + 1])); i += 2 }
        return out
    }
}

/// name, wall top, wall bottom, carpet, carpet shade, post, post stripe, backdrop style, accent
struct TTTheme { let name, wa, wb, carpet, carpetD, post, stripe, style, accent: String }

enum TTData {
    static let root: [String: Any] = (GameData.json("tower_tabby") as? [String: Any]) ?? [:]

    private static func int(_ v: Any?) -> Int { (v as? NSNumber)?.intValue ?? 0 }
    private static func dbl(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }

    static let stages: [TTStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var s = TTStage()
        s.k = d["k"] as? String ?? "normal"
        s.nm = d["nm"] as? String ?? ""
        s.th = int(d["th"])
        s.lv = (d["lv"] as? [String] ?? []).map { Array($0) }
        s.sl = (d["sl"] as? [Any])?.map { int($0) } ?? [0, 0, 0, 0, 0, 0]
        s.en = ((d["en"] as? [[Any]]) ?? []).map { ($0[0] as? String ?? "mouse", int($0[1]), int($0[2])) }
        s.fish = ((d["fish"] as? [[Any]]) ?? []).map { (int($0[0]), int($0[1])) }
        s.kit = ((d["kit"] as? [[Any]]) ?? []).map { (int($0[0]), int($0[1])) }
        s.it = ((d["it"] as? [[Any]]) ?? []).map { (int($0[0]), int($0[1]), $0[2] as? String ?? "wand") }
        s.mix = d["mix"] as? [String] ?? []
        s.rate = dbl(d["rate"])
        s.hs = d["hs"] == nil ? 1 : dbl(d["hs"])
        s.moth = dbl(d["moth"])
        s.mods = d["mods"] as? [String] ?? []
        s.new = d["new"] as? String ?? ""
        s.nst = d["nst"] as? String ?? ""
        s.quip = d["quip"] as? String ?? ""
        s.par = d["par"] == nil ? 40 : int(d["par"])
        s.boss = d["boss"] as? String ?? "kaw"
        s.hp = max(1, int(d["hp"]))
        s.lvN = int(d["lv_n"])
        s.pat = d["pat"] as? [String] ?? ["swoop"]
        s.spd = d["spd"] == nil ? 1 : dbl(d["spd"])
        s.bt = d["bt"] as? String ?? "fish"
        s.time = d["time"] == nil ? 20 : int(d["time"])
        return s
    }

    static let themes: [TTTheme] = ((root["themes"] as? [[String]]) ?? []).map { a in
        TTTheme(name: a[0], wa: a[1], wb: a[2], carpet: a[3], carpetD: a[4], post: a[5], stripe: a[6], style: a[7],
                accent: a[8])
    }

    /// kind -> (name, intro tier, blurb)
    static let hazards: [String: (String, Int, String)] = ((root["hazards"] as? [String: [Any]]) ?? [:]).mapValues {
        ($0[0] as? String ?? "", int($0[1]), $0[2] as? String ?? "")
    }
    /// structure char -> (name, intro tier, blurb)
    static let structs: [String: (String, Int, String)] = ((root["structs"] as? [String: [Any]]) ?? [:]).mapValues {
        ($0[0] as? String ?? "", int($0[1]), $0[2] as? String ?? "")
    }
    static let mods: [String: String] = (root["mods"] as? [String: String]) ?? [:]
}
