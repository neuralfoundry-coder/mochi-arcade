// WHISKER MAZE campaign data (exported from games/whisker_maze_maze.py via EXPORT) and the upgrade cards.
// Mazes are mirror-symmetric, so only the left 16 columns travel; the right half is rebuilt here.
import Foundation

let WM_COLS = 31, WM_ROWS = 17

struct WD: Equatable {
    var x: Int, y: Int
    init(_ x: Int, _ y: Int) { self.x = x; self.y = y }
    static let zero = WD(0, 0)
    var isZero: Bool { x == 0 && y == 0 }
    var rev: WD { WD(-x, -y) }
}

let WM_D4 = [WD(1, 0), WD(-1, 0), WD(0, 1), WD(0, -1)]

struct WMBossSpec { let kind, name: String; let hp: Int; let rate, speed: Double; let patterns: [String]; let extra: String; let tier: Int }

struct WMStage {
    let n: Int, kind: String, tier: Int, name: String
    let rows: [[Character]]
    let bots: [(String, Int, Int)]
    let feats: [String]
    let speed, nip, release, doorT: Double
    let dark, bell: Bool
    let newLine, quip: String
    let spots: [(Int, Int)]
    let bonus: String
    let time: Double
    let boss: WMBossSpec?
    let nips: [(Int, Int)]
}

struct WMTheme { let name, fa, fb, wall, top, side: String; let pat: Int }

enum WMData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func pairs(_ v: Any?) -> [(Int, Int)] {
        ((v as? [[Any]]) ?? []).map { (Int(num($0[0])), Int(num($0[1]))) }
    }
    private static let root: [String: Any] = (GameData.json("whisker_maze") as? [String: Any]) ?? [:]

    private static func theme(_ a: [Any]) -> WMTheme {
        WMTheme(name: a[0] as? String ?? "", fa: a[1] as? String ?? "ink", fb: a[2] as? String ?? "deep",
                wall: a[3] as? String ?? "peach", top: a[4] as? String ?? "cream", side: a[5] as? String ?? "brown",
                pat: Int(num(a[6])))
    }

    static let stages: [WMStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: WMBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = WMBossSpec(kind: b["kind"] as? String ?? "queen", name: b["name"] as? String ?? "", hp: Int(num(b["hp"])),
                              rate: num(b["rate"]), speed: num(b["speed"]), patterns: b["patterns"] as? [String] ?? [],
                              extra: b["extra"] as? String ?? "", tier: Int(num(b["tier"])))
        }
        let rows: [[Character]] = (d["rows"] as? [String] ?? []).map { half in
            let h = Array(half)
            return h + h.dropLast().reversed()
        }
        let bots = ((d["bots"] as? [[Any]]) ?? []).map { ($0[0] as? String ?? "sniffy", Int(num($0[1])), Int(num($0[2]))) }
        return WMStage(n: Int(num(d["n"])), kind: d["kind"] as? String ?? "normal", tier: Int(num(d["tier"])),
                       name: d["name"] as? String ?? "", rows: rows, bots: bots, feats: d["feats"] as? [String] ?? [],
                       speed: num(d["speed"]), nip: num(d["nip"]), release: num(d["release"]), doorT: num(d["door_t"]),
                       dark: d["dark"] as? Bool ?? false, bell: d["bell"] as? Bool ?? false,
                       newLine: d["new"] as? String ?? "", quip: d["quip"] as? String ?? "", spots: pairs(d["spots"]),
                       bonus: d["bonus"] as? String ?? "", time: num(d["time"]), boss: boss, nips: pairs(d["nips"]))
    }

    static let themes: [WMTheme] = ((root["themes"] as? [[Any]]) ?? []).map(theme)
    static let bonusThemes: [String: WMTheme] = ((root["bonus_themes"] as? [String: [Any]]) ?? [:]).mapValues(theme)
}

// ----------------------------------------------------------------------------- upgrade cards
let WM_UPGRADES: [Upgrade] = [
    Upgrade(id: "speed", name: "QUICK PAWS", desc: "NORI RUNS|FASTER", color: "lime", draw: { s, cx, cy, t in
        for (i, (dx, dy)) in [(-5, 3), (-1, -1), (3, 3), (6, -2)].enumerated() where Int(t * 6) % 4 >= i {
            s.fillRect(col("white"), cx + dx, cy + dy, 2, 2)
        }
    }, max: 3),
    Upgrade(id: "nip", name: "LONG ZOOMIES", desc: "CATNIP|LASTS LONGER", color: "mint", draw: { s, cx, cy, t in
        s.blit(sprite("wm_nip"), cx - 4, cy - 4 + Int(sin(t * 5)))
    }, max: 3),
    Upgrade(id: "dash", name: "ZOOM DASH", desc: "DASH MORE|OFTEN AND|LONGER", color: "sky", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.fillRect(col("sky"), cx - 7 + i * 2 - Int(t * 20) % 3, cy - 3 + i * 3, 6, 1) }
        s.blit(sprite("wm_side", Int(t * 9) % 2), cx - 2, cy - 6)
    }, max: 3),
    Upgrade(id: "collar", name: "LUCKY COLLAR", desc: "SHRUGS OFF|ONE HIT|EVERY STAGE", color: "red", draw: { s, cx, cy, _ in
        s.circle(col("red"), cx, cy, 6, width: 2)
        s.blit(sprite("wm_bell"), cx - 4, cy + 1)
    }, max: 2),
    Upgrade(id: "whisker", name: "LONG WHISKERS", desc: "EAT CRUMBS|BESIDE YOU|TOO", color: "white", draw: { s, cx, cy, t in
        for dy in [-2, 0, 2] {
            let w = 6 + Int(sin(t * 6 + Double(dy)) * 2)
            s.fillRect(col("white"), cx - w - 2, cy + dy, w, 1)
            s.fillRect(col("white"), cx + 3, cy + dy, w, 1)
        }
        s.fillRect(col("pink"), cx - 1, cy - 1, 3, 2)
    }, max: 2),
    Upgrade(id: "bell", name: "SILENT BELL", desc: "BOTS SNIFF,|SEE AND HEAR|YOU LESS", color: "yellow", draw: { s, cx, cy, _ in
        s.blit(sprite("wm_bell"), cx - 4, cy - 4)
        s.line(col("red"), cx - 7, cy - 6, cx + 7, cy + 6)
    }, max: 3),
    Upgrade(id: "power", name: "POWER POUNCE", desc: "BOSSES TAKE|MORE DAMAGE", color: "hotpink", draw: { s, cx, cy, t in
        s.circle(col("hotpink"), cx, cy + 1, 4 + Int(abs(sin(t * 4)) * 2))
        for dx in [-4, -1, 2, 5] { s.fillRect(col("pink"), cx + dx - 1, cy - 6, 2, 2) }
    }, max: 3),
    Upgrade(id: "tuna", name: "TUNA LOVER", desc: "TUNA IS|WORTH MORE,|STAYS LONGER", color: "sky", draw: { s, cx, cy, _ in
        s.blit(sprite("wm_tuna"), cx - 5, cy - 4)
    }, max: 3),
    Upgrade(id: "life", name: "EXTRA LIFE", desc: "+1 LIFE|RIGHT NOW", color: "pink", icon: "heart", max: 5),
    Upgrade(id: "fever", name: "FEVER PURR", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "orange", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
    Upgrade(id: "luck", name: "LUCKY PAW", desc: "MORE GOLD|FISH, BELLS|AND MILK", color: "yellow", draw: { s, cx, cy, t in
        s.blit(sprite("wm_gold"), cx - 5, cy - 3 + Int(sin(t * 4)))
    }, max: 3),
]
