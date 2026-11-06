// JELLY STACK campaign tables (built in Python by games/jelly_stack_stages.py, exported through
// jelly_stack.EXPORT -> GData.gameData) plus the background and boss art (port of jelly_stack.py).
import Foundation

struct JSBossDef { let id: Int; let hp: Int; let atk: [String]; let every: Double; let pow: Int }

struct JSStage {
    let n: Int
    let k: String
    let goal: Int
    let lim: Int
    let g: Double
    let rise: Double
    let rows: [String]
    let seq: String
    let mods: [String]
    let par: Int
    let new: String
    let boss: JSBossDef?
    let sol: [(String, Int, Int)]     // puzzle solution: (kind, rotation, column) in order
}

struct JSTheme { let name: String; let hue: String; let acc: String; let style: Int }
struct JSBossInfo { let name: String; let attack: String; let body: String; let trim: String }
struct JSUpgradeDef { let id: String; let name: String; let desc: String; let color: String; let max: Int }

enum JSData {
    private static let root: [String: Any] = GameData.json("jelly_stack") as? [String: Any] ?? [:]

    private static func num(_ d: [String: Any], _ k: String) -> Double { (d[k] as? NSNumber)?.doubleValue ?? 0 }
    private static func int(_ d: [String: Any], _ k: String) -> Int { (d[k] as? NSNumber)?.intValue ?? 0 }

    static let stages: [JSStage] = (root["stages"] as? [[String: Any]] ?? []).map { d in
        var boss: JSBossDef?
        if let b = d["boss"] as? [String: Any] {
            boss = JSBossDef(id: int(b, "id"), hp: int(b, "hp"), atk: b["atk"] as? [String] ?? [], every: num(b, "every"),
                             pow: int(b, "pow"))
        }
        return JSStage(n: int(d, "n"), k: d["k"] as? String ?? "rows", goal: int(d, "goal"), lim: int(d, "lim"),
                       g: num(d, "g"), rise: num(d, "rise"), rows: d["rows"] as? [String] ?? [], seq: d["seq"] as? String ?? "",
                       mods: d["mods"] as? [String] ?? [], par: int(d, "par"), new: d["new"] as? String ?? "", boss: boss,
                       sol: (d["sol"] as? [[Any]] ?? []).map { ($0[0] as? String ?? "O", ($0[1] as? NSNumber)?.intValue ?? 0,
                                                                  ($0[2] as? NSNumber)?.intValue ?? 0) })
    }

    static let themes: [JSTheme] = (root["themes"] as? [[Any]] ?? []).map {
        JSTheme(name: $0[0] as? String ?? "", hue: $0[1] as? String ?? "pink", acc: $0[2] as? String ?? "yellow",
                style: ($0[3] as? NSNumber)?.intValue ?? 0)
    }

    static let bosses: [JSBossInfo] = (root["bosses"] as? [[String]] ?? []).map {
        JSBossInfo(name: $0[0], attack: $0[1], body: $0[2], trim: $0[3])
    }

    static let upgrades: [JSUpgradeDef] = (root["upgrades"] as? [[Any]] ?? []).map {
        JSUpgradeDef(id: $0[0] as? String ?? "", name: $0[1] as? String ?? "", desc: $0[2] as? String ?? "",
                     color: $0[3] as? String ?? "mint", max: ($0[4] as? NSNumber)?.intValue ?? 1)
    }

    static let attackNames: [String: String] = root["attackNames"] as? [String: String] ?? [:]
    static let mods: [String: String] = root["mods"] as? [String: String] ?? [:]

    static let iconGlyph: [String: String] = ["peek": ">", "slow": "`", "sticky": "#", "bomb": "*", "zap": "!",
                                              "shield": "=", "party": "+", "pocket": "&", "lucky": "$", "heart": "@"]

    static let pool: [Upgrade] = upgrades.map { u in
        Upgrade(id: u.id, name: u.name, desc: u.desc, color: u.color, icon: nil, draw: { s, cx, cy, t in
            Cute.jellyCell(s, cx - 6, cy - 6, 13, u.color, t, face: false)
            drawText(s, iconGlyph[u.id] ?? "?", cx, cy - 4, "black", align: .center, shadow: nil)
        }, max: u.max)
    }

    /// Jackpot well refill: blocks of 4 dusty rows, each with a one-wide shaft (same as stages.well_blocks).
    static func wellBlocks(_ blocks: Int) -> [[String?]] {
        var rows: [[String?]] = []
        var last = -1
        for _ in 0 ..< blocks {
            let c = (0 ..< 10).filter { $0 != last }.randomElement()!
            last = c
            for _ in 0 ..< 4 { rows.append((0 ..< 10).map { $0 == c ? nil : "g" }) }
        }
        return rows
    }
}

// ---------------------------------------------------------------------- backgrounds and bosses
enum JSArt {
    static func background(_ s: Surface, _ th: JSTheme, _ t: Double) {
        let deco = lerpCol("black", th.hue, 0.3)
        s.fill(lerpCol("black", th.hue, 0.16))
        switch th.style {
        case 0:   // bubbles drifting up
            for i in 0 ..< 16 {
                let x = (i * 47 + 13) % W
                let y = Double(H) - (t * Double(8 + i % 4) * 2 + Double(i * 31)).truncatingRemainder(dividingBy: Double(H + 20))
                s.circle(deco, x, Int(y), 3 + i % 4)
            }
        case 1:   // rolling waves
            for i in 0 ..< 6 {
                let y0 = 20 + i * 34
                for x in stride(from: 0, to: W, by: 4) {
                    s.fillRect(deco, x, y0 + Int(sin(Double(x) * 0.05 + t * 1.5 + Double(i)) * 4), 4, 3)
                }
            }
        case 2:   // twinkles
            for i in 0 ..< 28 {
                let x = (i * 71 + 7) % W, y = (i * 37 + 11) % H
                if Int(t * 2 + Double(i)) % 5 != 0 {
                    s.fillRect(deco, x, y - 2, 1, 5)
                    s.fillRect(deco, x - 2, y, 5, 1)
                }
            }
        case 3:   // diagonal candy stripes
            let off = Int(t * 10) % 24
            for i in stride(from: -H, to: W + H, by: 24) {
                let x = Double(i + off), h = Double(H)
                s.polygon(deco, [(x, 0), (x + 8, 0), (x + 8 - h, h), (x - h, h)])
            }
        default:  // slow checker
            let off = Int(t * 6) % 32
            for y in stride(from: -32, to: H + 32, by: 16) {
                for x in stride(from: -32, to: W + 32, by: 16) where ((x + y) / 16) % 2 == 0 {
                    s.fillRect(deco, x + off, y + off / 2, 16, 16)
                }
            }
        }
    }

    /// Seven original jelly monsters, about 48x44, drawn around (cx, cy).
    static func boss(_ s: Surface, _ bid: Int, _ cx: Int, _ cy: Int, _ t: Double, hurt: Bool = false, angry: Bool = false) {
        let info = JSData.bosses[bid]
        let bc = hurt ? "white" : info.body, trim = info.trim
        let mood = angry ? "angry" : "happy"
        let wob = sin(t * 4) * 2
        let k = col("black")
        func P(_ pts: [(Int, Int)]) -> [(Double, Double)] { pts.map { (Double($0.0), Double($0.1)) } }
        switch bid {
        case 0:   // GUMMY KING: green dome jelly with a crown
            let w = Int(44 + wob)
            s.ellipse(k, cx - w / 2 - 1, cy - 19, w + 2, 40)
            s.ellipse(col(bc), cx - w / 2, cy - 18, w, 38)
            s.fillRect(col("white"), cx - 12, cy - 12, 6, 3)
            s.polygon(col(trim), P([(cx - 10, cy - 16), (cx - 12, cy - 26), (cx - 5, cy - 20), (cx, cy - 28),
                                    (cx + 5, cy - 20), (cx + 12, cy - 26), (cx + 10, cy - 16)]))
            s.fillRect(col("red"), cx - 1, cy - 22, 3, 3)
            Cute.eyes(s, cx, cy - 2, 8, mood: mood, size: 2)
            Cute.mouth(s, cx, cy + 8, mood)
        case 1:   // FROSTY FLAN: pudding with caramel top and icicles
            s.polygon(k, P([(cx - 22, cy + 20), (cx + 22, cy + 20), (cx + 15, cy - 16), (cx - 15, cy - 16)]))
            s.polygon(col(bc), P([(cx - 21, cy + 19), (cx + 21, cy + 19), (cx + 14, cy - 15), (cx - 14, cy - 15)]))
            s.ellipse(col(hurt ? "white" : "brown"), cx - 15, cy - 20, 30, 10)
            for i in 0 ..< 5 {
                let x = cx - 12 + i * 6, ln = 4 + (i * 3) % 5
                s.polygon(col(trim), P([(x, cy - 12), (x + 4, cy - 12), (x + 2, cy - 12 + ln)]))
            }
            Cute.eyes(s, cx, cy + 2, 7, mood: angry ? "angry" : "sleepy", size: 2)
            Cute.mouth(s, cx, cy + 10, mood)
            if Int(t * 3) % 2 == 1 {
                s.fillRect(col("white"), cx + 18, cy - 20, 1, 3)
                s.fillRect(col("white"), cx + 17, cy - 19, 3, 1)
            }
        case 2:   // INKY PUDDING: round purple blob with wiggly tentacles
            for i in 0 ..< 4 {
                let x = cx - 15 + i * 10
                for j in 0 ..< 4 {
                    let dx = Int(sin(t * 6 + Double(i) + Double(j) * 0.8) * 2)
                    s.circle(col(hurt ? "white" : trim), x + dx, cy + 12 + j * 4, 3)
                }
            }
            s.circle(k, cx, cy - 2, 20)
            s.circle(col(bc), cx, cy - 2, 19)
            s.fillRect(col("white"), cx - 10, cy - 14, 5, 2)
            Cute.eyes(s, cx, cy - 4, 7, look: Int(sin(t * 2) * 2), mood: mood, size: 2)
            Cute.mouth(s, cx, cy + 6, "wow")
        case 3:   // TOFU TITAN: a big square block of tofu
            let a = Int(abs(wob))
            let r = IRect(cx - 21, cy - 20 + a, 42, 40 - a)
            s.rect(k, r.inflate(2, 2), radius: 4)
            s.rect(col(bc), r, radius: 4)
            s.rect(col(trim), IRect(r.x, r.bottom - 6, r.w, 6), radius: 3)
            s.fillRect(col("cream"), r.x + 4, r.y + 3, 10, 2)
            Cute.eyes(s, cx, r.y + 14, 9, mood: "angry", size: 2)
            Cute.mouth(s, cx, r.y + 24, angry ? "angry" : "flat")
        case 4:   // TRICKY TART: round tart with a jester hat
            s.circle(k, cx, cy + 4, 19)
            s.circle(col(hurt ? "white" : "orange"), cx, cy + 4, 18)
            s.circle(col(bc), cx, cy + 4, 14)
            for a in stride(from: 0, to: 360, by: 60) {
                let ra = (Double(a) + t * 40) * .pi / 180
                s.fillRect(col("red"), cx + Int(cos(ra) * 10), cy + 4 + Int(sin(ra) * 10), 2, 2)
            }
            s.polygon(col(trim), P([(cx - 14, cy - 12), (cx - 22, cy - 26), (cx, cy - 16)]))
            s.polygon(col("yellow"), P([(cx + 14, cy - 12), (cx + 22, cy - 26), (cx, cy - 16)]))
            s.circle(col("yellow"), cx - 22, cy - 26, 2)
            s.circle(col(trim), cx + 22, cy - 26, 2)
            Cute.eyes(s, cx, cy + 2, 6, look: Int(sin(t * 5) * 2), mood: mood, size: 2)
            Cute.mouth(s, cx, cy + 10, angry ? "angry" : "happy")
        case 5:   // FIZZY FLOAT: fizzy soda bubble with a straw
            s.line(col("red"), cx + 6, cy - 18, cx + 14, cy - 30, width: 2)
            s.circle(k, cx, cy, 20)
            s.circle(col(bc), cx, cy, 19)
            s.circle(col(trim), cx, cy + 6, 13)
            for i in 0 ..< 6 {
                let by = cy + 14 - Int((t * 20 + Double(i * 7)).truncatingRemainder(dividingBy: 30))
                s.circle(col("white"), cx - 10 + i * 4, by, 1)
            }
            Cute.eyes(s, cx, cy - 4, 7, mood: mood, size: 2)
            Cute.mouth(s, cx, cy + 5, angry ? "wow" : "happy")
        default:  // JELLY EMPEROR: layered rainbow jelly with crown and cape
            s.polygon(col("red"), P([(cx - 24, cy - 6), (cx + 24, cy - 6), (cx + 28, cy + 22), (cx - 28, cy + 22)]))
            for (i, c) in ["hotpink", "orange", "yellow", "lime", "sky"].enumerated() {
                s.rect(col(hurt ? "white" : c), IRect(cx - 18 + i, cy - 16 + i * 7, 36 - i * 2, 8), radius: 3)
            }
            s.rect(k, IRect(cx - 19, cy - 17, 38, 37), width: 1, radius: 4)
            s.polygon(col(trim), P([(cx - 12, cy - 16), (cx - 14, cy - 28), (cx - 6, cy - 20), (cx, cy - 30),
                                    (cx + 6, cy - 20), (cx + 14, cy - 28), (cx + 12, cy - 16)]))
            s.fillRect(col("sky"), cx - 1, cy - 25, 3, 3)
            Cute.eyes(s, cx, cy - 3, 8, mood: "angry", size: 2)
            Cute.mouth(s, cx, cy + 7, mood)
        }
    }
}
