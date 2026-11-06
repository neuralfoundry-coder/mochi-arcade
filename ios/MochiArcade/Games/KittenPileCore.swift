// KITTEN PILE rules: the cat bed grid, groups, gravity, chains and the shared random generator
// (port of mochi_arcade/games/kitten_pile_core.py - keep the two in step), plus the stage tables exported from
// Python (kitten_pile.EXPORT -> GameData.json("kitten_pile")).
//
// Cells are small ints: 0 empty, 1...5 kittens (+16 star, +32 golden), 8 pillow, 9 grandpa (asleep),
// 10 grandpa (yawning), 11 yarn ball, 12 toy mouse.
import Foundation

enum KP {
    static let COLS = 6, ROWS = 12, SPAWN_X = 2
    static let STAR = 16, GOLD = 32
    static let PILLOW = 8, GRANDPA = 9, GRANDPA1 = 10, YARN = 11, MOUSE = 12
    static let NEED = 4
    static let DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]       // satellite offsets for rot 0..3
    static let CHAIN_MULT = [1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225, 256, 289, 324]
    static let CHAIN_POWER = [1, 2, 4, 6, 9, 12, 16, 20, 25, 30, 36, 42, 49, 56, 64, 72, 81, 90]

    typealias Grid = [[Int]]
    typealias Cell = (x: Int, y: Int)

    static func codeOf(_ ch: Character) -> Int {
        switch ch {
        case "1": return 1
        case "2": return 2
        case "3": return 3
        case "4": return 4
        case "5": return 5
        case "a": return 17
        case "b": return 18
        case "c": return 19
        case "d": return 20
        case "e": return 21
        case "P": return PILLOW
        case "G": return GRANDPA
        case "g": return GRANDPA1
        default: return 0
        }
    }

    @inline(__always) static func isKitten(_ c: Int) -> Bool { c > 0 && c & 8 == 0 }
    @inline(__always) static func kcolor(_ c: Int) -> Int { isKitten(c) ? c & 7 : 0 }
    @inline(__always) static func isJunk(_ c: Int) -> Bool { c == PILLOW || c == GRANDPA || c == GRANDPA1 }

    static func emptyGrid() -> Grid { Grid(repeating: [Int](repeating: 0, count: COLS), count: ROWS) }

    static func parseRows(_ rows: [String]) -> Grid {
        var g = emptyGrid()
        for (i, r) in rows.enumerated() {
            let y = ROWS - rows.count + i
            for (x, ch) in r.enumerated() where x < COLS && y >= 0 { g[y][x] = codeOf(ch) }
        }
        return g
    }

    static func colHeight(_ g: Grid, _ x: Int) -> Int {
        for y in 0 ..< ROWS where g[y][x] != 0 { return ROWS - y }
        return 0
    }

    static func countCells(_ g: Grid, _ f: (Int) -> Bool) -> Int {
        var n = 0
        for row in g { for c in row where f(c) { n += 1 } }
        return n
    }

    /// Let everything fall. Returns (x, fromY, toY) for the animation.
    @discardableResult
    static func applyGravity(_ g: inout Grid) -> [(Int, Int, Int)] {
        var moves: [(Int, Int, Int)] = []
        for x in 0 ..< COLS {
            var dst = ROWS - 1
            for y in stride(from: ROWS - 1, through: 0, by: -1) {
                let c = g[y][x]
                if c != 0 {
                    if y != dst { g[dst][x] = c; g[y][x] = 0; moves.append((x, y, dst)) }
                    dst -= 1
                }
            }
        }
        return moves
    }

    /// Connected same-colour kittens of size >= NEED (cells sorted by row, then column).
    static func findGroups(_ g: Grid) -> [[Cell]] {
        var seen = [[Bool]](repeating: [Bool](repeating: false, count: COLS), count: ROWS)
        var out: [[Cell]] = []
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS {
                let k = kcolor(g[y][x])
                if k == 0 || seen[y][x] { continue }
                var comp: [Cell] = []
                var stack: [Cell] = [(x, y)]
                seen[y][x] = true
                while let (cx, cy) = stack.popLast() {
                    comp.append((cx, cy))
                    for (dx, dy) in DIRS {
                        let nx = cx + dx, ny = cy + dy
                        if nx >= 0 && nx < COLS && ny >= 0 && ny < ROWS && !seen[ny][nx] && kcolor(g[ny][nx]) == k {
                            seen[ny][nx] = true
                            stack.append((nx, ny))
                        }
                    }
                }
                if comp.count >= NEED { out.append(comp.sorted { $0.y != $1.y ? $0.y < $1.y : $0.x < $1.x }) }
            }
        }
        return out
    }

    /// Pillows / grandpas next to the popping kittens (each hit once per pop).
    static func junkHits(_ g: Grid, _ cells: [Cell]) -> [Cell] {
        var hit = Set(cells.map { $0.y * COLS + $0.x })
        var out: [Cell] = []
        for (x, y) in cells {
            for (dx, dy) in DIRS {
                let nx = x + dx, ny = y + dy
                if nx >= 0 && nx < COLS && ny >= 0 && ny < ROWS && !hit.contains(ny * COLS + nx) && isJunk(g[ny][nx]) {
                    hit.insert(ny * COLS + nx)
                    out.append((nx, ny))
                }
            }
        }
        return out.sorted { $0.y != $1.y ? $0.y < $1.y : $0.x < $1.x }
    }

    /// One nap's worth of damage: pillows vanish, sound-asleep grandpas start yawning, yawning ones leave.
    @discardableResult
    static func hitJunk(_ g: inout Grid, _ x: Int, _ y: Int) -> Bool {
        if g[y][x] == GRANDPA { g[y][x] = GRANDPA1; return false }
        g[y][x] = 0
        return true
    }

    /// The colour a landed yarn ball puts to sleep: the kitten under it, else the most common one.
    static func yarnColor(_ g: Grid, _ x: Int, _ y: Int) -> Int {
        if y + 1 < ROWS && isKitten(g[y + 1][x]) { return kcolor(g[y + 1][x]) }
        var counts = [Int](repeating: 0, count: 6)
        for row in g { for c in row { counts[kcolor(c)] += 1 } }
        var best = 0, bestn = 0
        for k in 1 ... 5 where counts[k] > bestn { best = k; bestn = counts[k] }
        return best
    }

    /// Junk a landed toy mouse squeaks awake (Chebyshev radius).
    static func mouseCells(_ g: Grid, _ x: Int, _ y: Int, _ radius: Int) -> [Cell] {
        var out: [Cell] = []
        for yy in max(0, y - radius) ..< min(ROWS, y + radius + 1) {
            for xx in max(0, x - radius) ..< min(COLS, x + radius + 1) where isJunk(g[yy][xx]) { out.append((xx, yy)) }
        }
        return out
    }

    /// Score for one chain step (before upgrades / FEVER).
    static func stepPoints(_ groups: [[Cell]], _ chain: Int, _ g: Grid) -> Int {
        let n = groups.reduce(0) { $0 + $1.count }
        var colours = Set<Int>()
        for gr in groups { for (x, y) in gr { colours.insert(kcolor(g[y][x])) } }
        let mult = CHAIN_MULT[min(chain, CHAIN_MULT.count) - 1] + groups.reduce(0) { $0 + $1.count - NEED } + 3 * (colours.count - 1)
        return 10 * n * max(1, mult)
    }

    /// Naps sent at a rival for one chain step.
    static func stepPower(_ groups: [[Cell]], _ chain: Int) -> Int {
        let n = groups.reduce(0) { $0 + $1.count }
        return n * CHAIN_POWER[min(chain, CHAIN_POWER.count) - 1] + (chain >= 2 ? 3 : 0)
    }

    /// Pivot first, then the satellite.
    static func pieceCells(_ x: Int, _ y: Int, _ rot: Int, _ solo: Bool) -> [Cell] {
        if solo { return [(x, y)] }
        let (dx, dy) = DIRS[rot]
        return [(x, y), (x + dx, y + dy)]
    }

    static func fits(_ g: Grid, _ cells: [Cell]) -> Bool {
        for (x, y) in cells {
            if x < 0 || x >= COLS || y >= ROWS { return false }
            if y >= 0 && g[y][x] != 0 { return false }
        }
        return true
    }

    static func dropY(_ g: Grid, _ x: Int, _ y0: Int, _ rot: Int, _ solo: Bool) -> Int {
        var y = y0
        while fits(g, pieceCells(x, y + 1, rot, solo)) { y += 1 }
        return y
    }

    /// Put a locked piece into the bed (cells already ordered lowest first): every kitten falls on its own.
    /// Returns (x, y, code) where each landed (y < 0: it bounced out of a full column).
    static func place(_ g: inout Grid, _ ordered: [(Int, Int, Int)]) -> [(Int, Int, Int)] {
        var out: [(Int, Int, Int)] = []
        for (x, _, code) in ordered {
            let ty = ROWS - 1 - colHeight(g, x)
            if ty >= 0 { g[ty][x] = code }
            out.append((x, ty, code))
        }
        return out
    }

    static func topped(_ g: Grid) -> Bool { g[0][SPAWN_X] != 0 }

    static func stageSeed(_ n: Int, _ attempt: Int, _ salt: Int = 0) -> UInt32 {
        UInt32(truncatingIfNeeded: UInt64(n) &* 2654435761 &+ UInt64(attempt) &* 40503 &+ UInt64(salt) &* 97 &+ 12345)
    }
}

/// xorshift32 - identical sequences in Python and Swift (piece queues, rival moves, pillow columns).
struct KRand {
    var s: UInt32
    init(_ seed: UInt32) { s = seed == 0 ? 0x9E37_79B9 : seed }
    mutating func next() -> UInt32 {
        var x = s
        x ^= x << 13
        x ^= x >> 17
        x ^= x << 5
        s = x
        return x
    }
    mutating func below(_ n: Int) -> Int { n > 0 ? Int(next() % UInt32(n)) : 0 }
}

// ---------------------------------------------------------------------- stage tables (from Python)
struct KPFoeDef { let id: Int; let hp: Int; let every: Double; let pow: Int; let atk: [String] }
struct KPSetup { let rows: [String]; let c: Int; let x: Int; let len: Int }

struct KPStage {
    let n: Int
    let k: String
    let goal: Int
    let ncol: Int
    let g: Double
    let rows: [String]
    let mods: [String]
    let lim: Int
    let par: Int
    let yarn: Double
    let mouse: Double
    let rival: KPFoeDef?
    let boss: KPFoeDef?
    let setups: [KPSetup]
    let tip: [String]
    let rain: Double
    let rainN: Int
    let rise: Double
    let twins: Bool
}

struct KPTheme { let name: String; let hue: String; let acc: String; let style: Int }
/// A big cat: bosses (extra = accessory) and duel rivals (extra = collar colour, pattern = fur pattern).
struct KPCatDef {
    let name: String, coat: String, mark: String, eye: String, extra: String
    let atk: [String], taunt: String
    var pattern = ""
}
struct KPUpgradeDef { let id: String; let name: String; let desc: String; let color: String; let max: Int }

enum KPData {
    private static let root: [String: Any] = GameData.json("kitten_pile") as? [String: Any] ?? [:]
    private static func num(_ d: [String: Any], _ k: String) -> Double { (d[k] as? NSNumber)?.doubleValue ?? 0 }
    private static func int(_ d: [String: Any], _ k: String) -> Int { (d[k] as? NSNumber)?.intValue ?? 0 }
    private static func foe(_ v: Any?) -> KPFoeDef? {
        guard let b = v as? [String: Any] else { return nil }
        return KPFoeDef(id: int(b, "id"), hp: int(b, "hp"), every: num(b, "every"), pow: int(b, "pow"), atk: b["atk"] as? [String] ?? [])
    }

    static let stages: [KPStage] = (root["stages"] as? [[String: Any]] ?? []).map { d in
        KPStage(n: int(d, "n"), k: d["k"] as? String ?? "clear", goal: int(d, "goal"), ncol: max(3, int(d, "ncol")), g: num(d, "g"),
                rows: d["rows"] as? [String] ?? [], mods: d["mods"] as? [String] ?? [], lim: int(d, "lim"), par: int(d, "par"),
                yarn: num(d, "yarn"), mouse: num(d, "mouse"), rival: foe(d["rival"]), boss: foe(d["boss"]),
                setups: (d["setups"] as? [[String: Any]] ?? []).map {
                    KPSetup(rows: $0["rows"] as? [String] ?? [], c: int($0, "c"), x: int($0, "x"), len: int($0, "len"))
                },
                tip: d["tip"] as? [String] ?? [], rain: num(d, "rain"), rainN: int(d, "rainN"), rise: num(d, "rise"),
                twins: d["twins"] as? Bool ?? false)
    }

    static let themes: [KPTheme] = (root["themes"] as? [[Any]] ?? []).map {
        KPTheme(name: $0[0] as? String ?? "", hue: $0[1] as? String ?? "lavender", acc: $0[2] as? String ?? "pink",
                style: ($0[3] as? NSNumber)?.intValue ?? 0)
    }

    static let bosses: [KPCatDef] = (root["bosses"] as? [[Any]] ?? []).map {
        KPCatDef(name: $0[0] as? String ?? "", coat: $0[1] as? String ?? "gray", mark: $0[2] as? String ?? "white",
                 eye: $0[3] as? String ?? "yellow", extra: $0[4] as? String ?? "crown", atk: $0[5] as? [String] ?? ["toss"],
                 taunt: $0[6] as? String ?? "")
    }

    static let rivals: [KPCatDef] = (root["rivals"] as? [[String]] ?? []).map {
        KPCatDef(name: $0[0], coat: $0[1], mark: $0[2], eye: $0[3], extra: $0[4], atk: [], taunt: "PILLOW FIGHT!",
                 pattern: $0.count > 5 ? $0[5] : "tabby")
    }

    static let upgrades: [KPUpgradeDef] = (root["upgrades"] as? [[Any]] ?? []).map {
        KPUpgradeDef(id: $0[0] as? String ?? "", name: $0[1] as? String ?? "", desc: $0[2] as? String ?? "",
                     color: $0[3] as? String ?? "mint", max: ($0[4] as? NSNumber)?.intValue ?? 1)
    }

    static let attackNames: [String: String] = root["attackNames"] as? [String: String] ?? [:]
    static let mods: [String: String] = root["mods"] as? [String: String] ?? [:]
    static let kindTitle: [String: String] = root["kindTitle"] as? [String: String] ?? [:]
    static let talk: [String: [String]] = root["talk"] as? [String: [String]] ?? [:]
    static let cheers: [String] = root["cheers"] as? [String] ?? ["GOOD NIGHT!"]
}
