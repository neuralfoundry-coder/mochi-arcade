// JELLY STACK - falling-block puzzle with wobbly jellies (port of games/jelly_stack.py - keep the two in step).
// Modes: STAGES (200-stage campaign with bosses, bonus stages and upgrades) and the classic MARATHON / SPRINT 40 /
// ENDLESS. Stage tables come from Python (JellyStackData.swift reads GameData.json("jelly_stack")).
import Foundation

private let BW = 10, BH = 20, CELL = 9
private let BX = (W - BW * CELL) / 2, BY = 16
private let WELL_W = BW * CELL, WELL_H = BH * CELL
private let LINE_PTS = [1: 100, 2: 300, 3: 500, 4: 800]
private let BOSS_DMG = [1: 10, 2: 25, 3: 45, 4: 80]
private let LIFE_STEP = 100000           // extra lives at 100k, 300k, 600k, 1M ...
private let GOLD_CHANCE = 0.012
private let BOMB_CHANCE = 0.02
private let BOSS_CX = 264, BOSS_CY = 160
private let KIND_TITLE = ["rows": "POP ROWS", "score": "SCORE!", "dig": "DIG OUT!", "stars": "STAR HUNT", "survive": "HANG ON!",
                          "puzzle": "PUZZLE", "speed": "SPEED!", "mix": "POP ROWS", "rain": "CANDY RAIN", "well": "JACKPOT WELL",
                          "boss": "BOSS!"]
private let PIECE_COLORS = Set(GData.jellyColors.values)

/// Seconds per row for a (possibly fractional) speed level 1..20 (jelly_stack_core.gravity_interval).
private func gravityInterval(_ lv0: Double) -> Double {
    let lv = max(1, min(20, lv0))
    return max(0.016, pow(0.8 - (lv - 1) * 0.007, lv - 1))
}

final class JSPiece {
    let kind: String
    var rot = 0, x = 3, y: Int
    let gold: Bool
    let bomb: Int           // index of the bomb cell, -1 = none
    init(_ kind: String, gold: Bool = false, bomb: Int = -1) {
        self.kind = kind; self.gold = gold; self.bomb = bomb
        y = kind == "I" ? -2 : -1
    }
    func cells(_ x: Int? = nil, _ y: Int? = nil, _ rot: Int? = nil) -> [(Int, Int)] {
        let xx = x ?? self.x, yy = y ?? self.y, r = rot ?? self.rot
        return GData.jellyRot[kind]![r].map { (xx + $0.0, yy + $0.1) }
    }
}

final class JSBoss {
    let id: Int, max: Int, atk: [String], every: Double, pow: Int
    var hp: Int, t: Double
    var tele: (String, Double)?
    var hit = 0.0, phase = 1, col = 0, hole = 0
    init(_ d: JSBossDef, hp: Int) {
        id = d.id; max = d.hp; atk = d.atk; every = d.every; pow = d.pow
        self.hp = hp; t = d.every * 0.8
    }
}

final class JellyStack: GameScene {
    override var music: String? { stageSong() }
    // ROT R sits under the resting thumb (turning is by far the most frequent action), ROT L is its neighbour
    // (a stray tap is undone with one more turn), DROP is one deliberate reach away (a stray hard drop is the
    // costliest mistake), HOLD is the rarest. Soft drop stays on the pad.
    override var buttons: [Action: String] { [.b: "ROT R", .a: "ROT L", .y: "DROP", .x: "HOLD"] }
    override var buttonOrder: [Action] { [.b, .a, .y, .x] }
    override var fourWay: Bool { true }

    let mode: String, campaign: Bool, ghostOpt: Bool
    var level = 1
    var grid = [[String?]](repeating: [String?](repeating: nil, count: BW), count: BH)
    var wob = [[Double]](repeating: [Double](repeating: 0, count: BW), count: BH)
    var bag: [String] = []
    var queue: [String] = []
    var holds: [String?] = [nil]
    var holdUsed = false
    var lines = 0, chain = -1
    var b2b = false
    var clearing: ([Int], Double)?
    var clearGold = false
    var dasDir = 0, dasT = 0.0, arrT = 0.0
    var time = 0.0
    var cur = JSPiece("T")
    var fallT = 0.0, lockT = 0.0, lockResets = 0
    var lastRot = false
    var pieces = 0
    var feverWas = false
    var zapFx: (Int, Double)?
    // campaign
    var ups: [String: Int] = [:]
    var lives = 3, lifeK = 1
    var stageN = 1
    var st: JSStage?
    var state = "play", stateT = 0.0
    var boss: JSBoss?
    var tally: [(String, Int, Int)] = []
    var tallyI = 0, tallyT = 0.0
    var shield = 0, zap = 0, coins = 0, perfects = 0
    var srows = 0, used = 0, sscore0 = 0
    var stime = 0.0
    var missed = false
    var riseT = 0.0, inkT = 0.0, hideT = 0.0, rushT = 0.0, revealT = 0.0
    var ink: [(Int, Int, Int)] = []
    var tierN = 0
    var theme: JSTheme
    var hint: [(Int, Int)]?
    var hintOk = false

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        mode = opt["mode"] ?? "stages"
        campaign = mode == "stages"
        ghostOpt = (opt["ghost"] ?? "true") == "true"
        theme = JSData.themes[0]
        super.init(app, info, opt)
        if campaign {
            stageN = Swift.max(1, Swift.min(STAGES, optInt("start", 1)))
            beginStage(stageN)
        } else {
            level = optInt("level", 1)
            queue = (0 ..< 6).map { _ in nextKind() }
            spawn()
        }
    }

    // ================================================================ helpers
    var kind: String { st?.k ?? mode }
    func mod(_ m: String) -> Bool { st?.mods.contains(m) ?? false }
    func up(_ id: String) -> Int { ups[id] ?? 0 }

    func nextKind() -> String {
        if st?.k == "well" { return "I" }
        if bag.isEmpty { bag = GData.jellyKinds.shuffled() }
        return bag.removeLast()
    }

    func nNext() -> Int { 3 + up("peek") }

    func gravity() -> Double {
        guard campaign, let st = st else { return gravityInterval(Double(Swift.min(level, 20))) }
        var g = gravityInterval(st.g) * (1 + 0.15 * Double(up("slow")))
        if rushT > 0 { g = Swift.max(0.016, g / 4) }
        return g
    }

    func lockDelay() -> Double { campaign ? 0.5 + 0.15 * Double(up("sticky")) : 0.5 }

    func fits(_ cells: [(Int, Int)]) -> Bool {
        for (x, y) in cells {
            if x < 0 || x >= BW || y >= BH { return false }
            if y >= 0 && grid[y][x] != nil { return false }
        }
        return true
    }

    func grounded() -> Bool { !fits(cur.cells(nil, cur.y + 1)) }
    func count(_ code: String) -> Int { grid.reduce(0) { $0 + $1.filter { $0 == code }.count } }
    func junkRows() -> Int { grid.filter { r in r.contains { $0 == "g" || $0 == "i" || $0 == "b" } }.count }
    func filled() -> Int { grid.reduce(0) { $0 + $1.filter { $0 != nil }.count } }
    func stackTop() -> Int { grid.firstIndex { r in r.contains { $0 != nil } } ?? BH }
    func wowOn() -> Bool { mode != "sprint" }
    private func rowEmpty(_ y: Int) -> Bool { !grid[y].contains { $0 != nil } }

    // ================================================================ pieces
    func spawn(_ k: String? = nil) {
        var kind = k
        if kind == nil {
            kind = queue.removeFirst()
            if st?.k != "puzzle" { queue.append(nextKind()) }
        }
        pieces += 1
        var gold = false
        if wowOn() && st?.k != "puzzle" {
            gold = Double.random(in: 0 ..< 1) < GOLD_CHANCE + 0.012 * Double(up("lucky")) + (self.kind == "rain" ? 0.04 : 0)
        }
        var bomb = -1
        if up("bomb") > 0 && pieces % (15 - 3 * up("bomb")) == 0 {
            bomb = 1
        } else if let st = st, st.k != "puzzle" && st.k != "well" && !gold && Double.random(in: 0 ..< 1) < BOMB_CHANCE {
            bomb = 1                                   // a free bomb jelly now and then
        }
        cur = JSPiece(kind!, gold: gold, bomb: bomb)
        fallT = 0; lockT = 0; lockResets = 0
        lastRot = false
        hint = findHint()
        if !fits(cur.cells()) { topOut() }
    }

    /// Puzzle retry: where the stored solution puts this piece (only while the player follows it).
    func findHint() -> [(Int, Int)]? {
        guard let st = st, st.k == "puzzle", missed, hintOk, used < st.sol.count, st.sol[used].0 == cur.kind else { return nil }
        let (kind, rot, x) = st.sol[used]
        return dropPlace(kind, rot, x)
    }

    /// Spawn, turn right until `rot`, slide to column `tx`, hard drop (jelly_stack_core.drop_place).
    func dropPlace(_ kind: String, _ rot: Int, _ tx: Int) -> [(Int, Int)]? {
        let p = JSPiece(kind)
        if !fits(p.cells()) { return nil }
        let table = kind == "I" ? GData.jellyKicksI : GData.jellyKicks
        while p.rot != rot {
            let b = (p.rot + 1) % 4
            guard let (kx, ky) = (table[p.rot * 10 + b] ?? [(0, 0)]).first(where: { fits(p.cells(p.x + $0.0, p.y - $0.1, b)) }) else { return nil }
            p.x += kx; p.y -= ky; p.rot = b
        }
        while p.x != tx {
            let step = tx > p.x ? 1 : -1
            if !fits(p.cells(p.x + step, p.y)) { return nil }
            p.x += step
        }
        while fits(p.cells(nil, p.y + 1)) { p.y += 1 }
        return p.cells()
    }

    @discardableResult
    func tryMove(_ dx: Int, _ dy: Int) -> Bool {
        if fits(cur.cells(cur.x + dx, cur.y + dy)) {
            cur.x += dx; cur.y += dy
            lastRot = false
            if dx != 0 && grounded() && lockResets < 15 { lockT = 0; lockResets += 1 }
            return true
        }
        return false
    }

    @discardableResult
    func rotate(_ d: Int) -> Bool {
        let a = cur.rot, b = (cur.rot + d + 4) % 4
        let table = cur.kind == "I" ? GData.jellyKicksI : GData.jellyKicks
        for (kx, ky) in table[a * 10 + b] ?? [(0, 0)] where fits(cur.cells(cur.x + kx, cur.y - ky, b)) {
            cur.x += kx; cur.y -= ky; cur.rot = b
            lastRot = true
            if grounded() && lockResets < 15 { lockT = 0; lockResets += 1 }
            app.audio.play("rotate")
            return true
        }
        return false
    }

    func doHold() {
        if holdUsed || mod("nohold") { return }
        if holds.contains(where: { $0 == nil }) && st?.k == "puzzle" && queue.isEmpty { return }
        app.audio.play("hold")
        let k = cur.kind
        if let i = holds.firstIndex(where: { $0 == nil }) {
            holds[i] = k
            spawn()
        } else {
            let out = holds.removeFirst()!
            holds.append(k)
            spawn(out)
        }
        holdUsed = true
    }

    func hardDrop() {
        var n = 0
        while tryMove(0, 1) { n += 1 }
        if n > 0 { add(n * 2) }
        parts.burst(Double(BX) + (Double(cur.x) + 1.5) * Double(CELL), Double(BY + (cur.y + 2) * CELL), 6, ["white", "lavender"], 40, 0.3)
        lock()
    }

    func immobile() -> Bool {
        !(fits(cur.cells(cur.x - 1, cur.y)) || fits(cur.cells(cur.x + 1, cur.y)) || fits(cur.cells(cur.x, cur.y - 1)))
    }

    // ================================================================ locking and clearing
    func lock() {
        let p = cur
        let cells = p.cells()
        let twist = lastRot && p.kind != "O" && immobile()
        if hintOk {   // left the solution path: no more hints this try
            let key = { (c: [(Int, Int)]) in c.map { $0.0 * 100 + $0.1 }.sorted() }
            if hint == nil || key(cells) != key(hint!) { hintOk = false }
        }
        if cells.contains(where: { $0.1 < 0 }) { topOut(); return }
        let code = p.gold ? "$" : GData.jellyColors[p.kind]!
        for (x, y) in cells { grid[y][x] = code; wob[y][x] = 1 }
        app.audio.play("lock")
        holdUsed = false
        if let st = st {
            used += 1
            revealT = Swift.max(revealT, 0.35)
            if st.k == "rain" { coins += 1; app.audio.play("coin") }   // candy rain: every jelly that lands drops a coin
        }
        if p.bomb >= 0 {
            let (bx, by) = cells[p.bomb]
            let n = explode(bx, by)
            app.audio.play("explode")
            app.shake(3, 0.3)
            hype.flash("orange", 0.15)
            floats.add(Double(BX + bx * CELL + 4), Double(BY + by * CELL), "BOMB!", "orange")
            if boss != nil { hitBoss(10 + 2 * n) }
        }
        let full = (0 ..< BH).filter { y in grid[y].allSatisfy { $0 != nil } }
        if full.isEmpty {
            if twist {
                add(100 * level, Double(BX + p.x * CELL + 12), Double(BY + p.y * CELL), "pink")
                floats.add(Double(BX + p.x * CELL + 12), Double(BY + p.y * CELL - 9), "TWIST", "pink")
            }
            chain = -1
            hype.breakCombo()
            afterPiece()
            return
        }
        clearing = (full, 0.32)
        clearGold = full.contains { y in grid[y].contains { $0 == "$" } }
        scoreClear(full.count, twist, full)
    }

    func scoreClear(_ n: Int, _ twist: Bool, _ full: [Int]) {
        let L = level
        var pts = LINE_PTS[n]! * L
        let big = n == 4 || twist
        let back = big && b2b
        if twist { pts *= 2 }
        if back { pts = pts * 3 / 2 }
        b2b = big
        chain += 1
        if chain > 0 { pts += 50 * chain * L }
        if n >= 2 && up("party") > 0 { pts = Int(Double(pts) * (1 + 0.25 * Double(up("party")))) }
        let cx = Double(BX + WELL_W / 2)
        add(pts, cx, Double(BY + full[0] * CELL - 4), "mint")
        if wowOn() {
            hype.hit(1, fever: 0)
            hype.feverAdd(0.035 * Double(n) + (big ? 0.12 : 0) + (back ? 0.08 : 0))
        }
        if twist {
            hype.banner("JELLY TWIST!", ["", "SINGLE", "DOUBLE", "TRIPLE", "PARTY"][n] + (back ? " B2B" : ""), color: "pink", dur: 1.2)
        } else if n == 4 {
            hype.banner("JELLY PARTY!", back ? "BACK-TO-BACK!" : nil, dur: 1.4, rainbow: true)
        } else if n == 3 {
            floats.add(cx, Double(BY + full[0] * CELL - 12), "TRIPLE!", "yellow")
        }
        if n == 4 || twist {
            app.audio.play("quad"); app.shake(3, 0.3); hype.hitstop(0.05)
        } else {
            app.audio.play("line")
        }
        if chain > 0 { floats.add(cx, Double(BY + full[0] * CELL + 6), "COMBO x\(chain + 1)", "peach") }
        for y in full {
            for x in 0 ..< BW {
                parts.burst(Double(BX + x * CELL + 4), Double(BY + y * CELL + 4), 3, [cellColor(grid[y][x]), "white"], 60, 0.6)
            }
        }
        lines += n
        if let st = st {
            srows += n
            zap += n
            if st.k == "rain" {
                let candies = full.reduce(0) { a, y in a + grid[y].filter { $0 == "c" }.count }
                coins += 3 * n + 3 * candies
                hype.shower(8 * n + 6 * candies, "coins")
                app.audio.play("coin")
            } else if st.k == "well" && n == 4 {
                coins += 5
                hype.shower(30, "coins")
            }
            if boss != nil {
                var dmg = BOSS_DMG[n]! * (twist ? 2 : 1)
                if back { dmg = dmg * 3 / 2 }
                dmg += 5 * Swift.max(0, chain)
                if hype.feverOn { dmg = dmg * 5 / 4 }
                hitBoss(dmg)
            }
        }
    }

    func cellColor(_ c: String?) -> String {
        guard let c = c else { return "white" }
        if PIECE_COLORS.contains(c) { return c }
        return ["g": "gray", "*": "yellow", "i": "sky", "b": "red", "c": "yellow", "$": "yellow", "s": "cream"][c] ?? "white"
    }

    /// 3x3 blast (bomb jelly). Returns how many jellies it popped.
    @discardableResult
    func explode(_ cx: Int, _ cy: Int) -> Int {
        var n = 0
        for y in (cy - 1) ... (cy + 1) {
            for x in (cx - 1) ... (cx + 1) where x >= 0 && x < BW && y >= 0 && y < BH {
                guard let c = grid[y][x] else { continue }
                if c == "$" { goldJackpot() }
                if c == "*" { starPop(x, y) }
                parts.burst(Double(BX + x * CELL + 4), Double(BY + y * CELL + 4), 4, [cellColor(c), "orange", "yellow"], 80, 0.6)
                grid[y][x] = nil
                n += 1
            }
        }
        return n
    }

    func starPop(_ x: Int, _ y: Int) {
        parts.burst(Double(BX + x * CELL + 4), Double(BY + y * CELL + 4), 12, ["yellow", "white", "orange"], 90, 0.8)
        add(500 * level, Double(BX + x * CELL + 4), Double(BY + y * CELL - 4), "yellow")
        app.audio.play("bonus")
    }

    private func removeRow(_ y: Int) {
        grid.remove(at: y); wob.remove(at: y)
        grid.insert([String?](repeating: nil, count: BW), at: 0)
        wob.insert([Double](repeating: 0, count: BW), at: 0)
    }

    func finishClear() {
        guard let (rows, _) = clearing else { return }
        for y in rows { for x in 0 ..< BW where grid[y][x] == "*" { starPop(x, y) } }   // star jellies in the popped rows
        for y in rows {                                                                  // pop-bombs blast the rows next to them
            for x in 0 ..< BW where grid[y][x] == "b" {
                app.audio.play("explode")
                app.shake(3, 0.25)
                for yy in [y - 1, y + 1] where yy >= 0 && yy < BH && !rows.contains(yy) {
                    for xx in [x - 1, x, x + 1] where xx >= 0 && xx < BW {
                        guard let c = grid[yy][xx] else { continue }
                        if c == "*" { starPop(xx, yy) }
                        parts.burst(Double(BX + xx * CELL + 4), Double(BY + yy * CELL + 4), 4, ["orange", "red", "yellow"], 80, 0.5)
                        grid[yy][xx] = nil
                    }
                }
            }
        }
        for y in rows.sorted() {
            if grid[y].contains(where: { $0 == "i" }) {      // ice survives one pop and thaws into a dusty jelly
                grid[y] = grid[y].map { $0 == "i" ? "g" : nil }
                wob[y] = [Double](repeating: 1, count: BW)
                parts.burst(Double(BX + WELL_W / 2), Double(BY + y * CELL + 4), 10, ["sky", "white"], 70, 0.5)
                continue
            }
            removeRow(y)
        }
        for y in 0 ..< BH { for x in 0 ..< BW where grid[y][x] != nil { wob[y][x] = Swift.max(wob[y][x], 0.6) } }
        clearing = nil
        if clearGold { clearGold = false; goldJackpot() }
        if wowOn() && filled() == 0 { perfect() }
        if st != nil {
            revealT = 1.2
            let need = 12 - 2 * up("zap")
            if up("zap") > 0 && zap >= need && stackTop() < BH { zap -= need; zapRow() }
        }
        if !campaign { classicAfterClear(); return }
        afterPiece()
    }

    func goldJackpot() { hype.jackpot(3000 * level, sub: "GOLDEN JELLY!") }

    func perfect() {
        let well = st?.k == "well"
        let pts = add((well ? 1000 : 10000) * level)
        hype.banner("PERFECT!!", "+\(pts)", dur: 2.2, rainbow: true, scale: 3, sound: "win")
        hype.flash("white", 0.3)
        hype.shower(120, "confetti")
        hype.feverAdd(0.5)
        app.shake(5, 0.5)
        if st != nil {
            perfects += 1
            if well {
                coins += 10
                if perfects % 3 == 0 { hype.jackpot(2000 * level) }   // every third empty well in the jackpot bonus
            }
        }
    }

    func zapRow() {
        var y = BH - 1
        while y >= 0 && rowEmpty(y) { y -= 1 }
        if y < 0 { return }
        for x in 0 ..< BW {
            if grid[y][x] == "*" { starPop(x, y) }
            if grid[y][x] != nil { parts.burst(Double(BX + x * CELL + 4), Double(BY + y * CELL + 4), 3, ["yellow", "white"], 70, 0.5) }
        }
        removeRow(y)
        zapFx = (y, 0.45)
        srows += 1
        app.audio.play("shoot")
        floats.add(Double(BX + WELL_W / 2), Double(BY + y * CELL - 6), "ZAP!", "yellow")
        if boss != nil { hitBoss(15) }
    }

    func classicAfterClear() {
        let newLevel = Swift.max(level, optInt("level", 1) + lines / 10)
        if newLevel > level && mode != "sprint" {
            level = newLevel
            app.audio.play("levelup")
            hype.banner("LEVEL \(level)", color: "mint", dur: 1.0, scale: 1)
        }
        if mode == "sprint" && lines >= 40 {
            score = Swift.max(1, Int(100000 - time * 300))
            endGame(true, String(format: "%.1f SEC", time)); return
        }
        if mode == "marathon" && lines >= 150 { endGame(true, "150 LINES!"); return }
        spawn()
    }

    /// A piece has settled (and its rows popped): check the stage goal, then bring the next piece.
    func afterPiece() {
        guard campaign, let st = st else { spawn(); return }
        checkLife()
        if state != "play" { return }
        if goalDone() { stageClear(); return }
        if st.k == "puzzle" && queue.isEmpty {
            if let i = holds.firstIndex(where: { $0 != nil }) {
                let h = holds[i]!
                holds[i] = nil
                spawn(h)
                return
            }
            failStage("OUT OF PIECES!")
            return
        }
        if st.k == "well" && junkRows() == 0 {
            pushRows(12, well: true)
            if state != "play" { return }
        }
        spawn()
    }

    // ================================================================ garbage, attacks
    func pushRows(_ n0: Int, hole: Int? = nil, well: Bool = false, shieldable: Bool = true) {
        var n = n0
        if shieldable && shield > 0 && !well {
            let blocked = Swift.min(shield, n)
            shield -= blocked
            n -= blocked
            floats.add(Double(BX + WELL_W / 2), Double(BY + WELL_H - 20), "SHIELD!", "lavender")
            parts.burst(Double(BX + WELL_W / 2), Double(BY + WELL_H - 4), 14, ["lavender", "white"], 80, 0.5)
            app.audio.play("tin")
        }
        if n <= 0 { return }
        var over = false
        let rows = well ? JSData.wellBlocks(n / 4) : []
        for i in 0 ..< n {
            if !rowEmpty(0) { over = true }
            grid.removeFirst(); wob.removeFirst()
            var row: [String?]
            if well {
                row = rows[i]
            } else {
                row = [String?](repeating: "g", count: BW)
                row[hole ?? Int.random(in: 0 ..< BW)] = nil
            }
            grid.append(row)
            wob.append([Double](repeating: 0.8, count: BW))
        }
        app.audio.play(well ? "bonus" : "hurt")
        if !fits(cur.cells()) {
            var moved = false
            for k in 1 ... n where fits(cur.cells(nil, cur.y - k)) { cur.y -= k; moved = true; break }
            if !moved { over = true }
        }
        if over { topOut() }
    }

    func dropHeavy(_ c: Int) {
        if shield > 0 {
            shield -= 1
            floats.add(Double(BX + c * CELL + 9), Double(BY + 30), "SHIELD!", "lavender")
            parts.burst(Double(BX + c * CELL + 9), Double(BY + 20), 14, ["cream", "white"], 80, 0.5)
            app.audio.play("tin")
            return
        }
        var y = -2
        while fits([(c, y + 1), (c + 1, y + 1), (c, y + 2), (c + 1, y + 2)]) { y += 1 }
        if y < 0 { topOut(); return }
        for yy in [y, y + 1] { for xx in [c, c + 1] { grid[yy][xx] = "s"; wob[yy][xx] = 1 } }
        app.audio.play("boom")
        app.shake(5, 0.35)
        parts.burst(Double(BX + c * CELL + 9), Double(BY + (y + 2) * CELL), 14, ["cream", "white", "gray"], 90, 0.6)
        if !fits(cur.cells()) {
            for k in 1 ... 4 where fits(cur.cells(nil, cur.y - k)) { cur.y -= k; return }
            topOut()
        }
    }

    @discardableResult
    func freeze(_ n: Int) -> Int {
        let top = stackTop()
        var spots: [(Int, Int)] = []
        for y in top ..< Swift.min(BH, top + 5) {
            for x in 0 ..< BW {
                if let c = grid[y][x], !["i", "*", "$", "b"].contains(c) { spots.append((x, y)) }
            }
        }
        spots.shuffle()
        let pick = spots.prefix(n)
        for (x, y) in pick {
            grid[y][x] = "i"
            parts.burst(Double(BX + x * CELL + 4), Double(BY + y * CELL + 4), 5, ["sky", "white"], 50, 0.5)
        }
        return pick.count
    }

    func bossAttack(_ atk: String) {
        guard let b = boss else { return }
        let p = b.pow + (b.phase >= 3 ? 1 : 0)
        hype.banner((JSData.attackNames[atk] ?? atk) + "!", color: "red", dur: 0.9, scale: 1)
        switch atk {
        case "garbage":
            pushRows(Swift.min(4, 1 + p / 3), hole: b.hole)
            app.shake(4, 0.3)
        case "freeze":
            if freeze(2 + p) < 2 { pushRows(1, hole: b.hole) }
            app.audio.play("trap")
            hype.flash("sky", 0.2)
        case "ink":
            inkT = 5.0 + Double(p)
            let top = Swift.max(4, stackTop() - 2)
            ink = (0 ..< (4 + p * 2)).map { _ in (Int.random(in: top ... (BH - 1)), Int.random(in: 0 ... (BW - 1)), Int.random(in: 9 ... 16)) }
            app.audio.play("pop")
        case "heavy":
            dropHeavy(b.col)
            if p >= 4 && state == "play" { dropHeavy((b.col + 4) % (BW - 1)) }
        case "flip":
            hideT = 4.0 + Double(p)
            let n = Swift.min(nNext(), queue.count)
            queue.replaceSubrange(0 ..< n, with: queue[0 ..< n].reversed())
            app.audio.play("powerup")
        default:   // rush
            rushT = 4.0 + Double(p) * 0.5
            app.audio.play("powerup")
        }
    }

    func hitBoss(_ dmg: Int) {
        guard let b = boss, b.hp > 0, state == "play" else { return }
        b.hp = Swift.max(0, b.hp - dmg)
        b.hit = 0.3
        floats.add(Double(BOSS_CX + Int.random(in: -10 ... 10)), Double(BOSS_CY - 26), "-\(dmg)", "red")
        parts.burst(Double(BOSS_CX), Double(BOSS_CY), 6 + dmg / 8, ["white", JSData.bosses[b.id].body, "yellow"], 90, 0.6)
        hype.hitstop(0.04 + Swift.min(0.1, Double(dmg) / 800))
        if dmg >= 60 { hype.flash("white", 0.12); app.shake(3, 0.25) }
        if b.hp <= 0 { bossDown(); return }
        let frac = Double(b.hp) / Double(b.max)
        if b.phase == 1 && frac <= 0.5 {
            b.phase = 2
            hype.banner("GRRR!", "THE BOSS IS ANGRY", color: "red", dur: 1.2)
        }
        if b.phase == 2 && frac <= 0.2 && stageN >= 40 {
            b.phase = 3
            hype.banner("LAST STAND!", color: "red", dur: 1.2)
        }
    }

    func bossDown() {
        guard let b = boss else { return }
        state = "bossdown"
        stateT = 0
        app.audio.stopMusic()
        app.audio.play("bossdown")
        hype.slowmo(0.3, 1.4)
        hype.flash("white", 0.4)
        hype.shower(120, "stars")
        app.shake(6, 0.8)
        hype.banners = []
        hype.banner("BOSS DOWN!", JSData.bosses[b.id].name, dur: 2.4, rainbow: true)
        b.tele = nil
    }

    func topOut() {
        guard campaign, let st = st else {
            app.audio.play("die")
            endGame(false, "\(lines) LINES")
            return
        }
        if state != "play" { return }
        if st.k == "rain" || st.k == "well" {
            hype.banner("STACKED!", color: "peach", dur: 1.0)
            stageClear()
            return
        }
        failStage("STACKED UP!")
    }

    // ================================================================ campaign flow
    func beginStage(_ n: Int, retry: Bool = false) {
        let s = JSData.stages[n - 1]
        st = s
        stageN = n
        tierN = tier(n)
        theme = JSData.themes[tierN]
        level = tierN + 1
        grid = [[String?]](repeating: [String?](repeating: nil, count: BW), count: BH)
        wob = [[Double]](repeating: [Double](repeating: 0, count: BW), count: BH)
        for (i, r) in s.rows.enumerated() {
            let y = BH - s.rows.count + i
            for (x, ch) in r.enumerated() where ch != "." { grid[y][x] = String(ch) }
        }
        bag = []
        queue = s.k == "puzzle" ? s.seq.map { String($0) } : (0 ..< 6).map { _ in nextKind() }
        holds = up("pocket") > 0 ? [nil, nil] : [nil]
        holdUsed = false
        clearing = nil
        chain = -1
        b2b = false
        srows = 0; used = 0; coins = 0; perfects = 0
        sscore0 = score
        stime = 0
        missed = retry
        shield = 2 * up("shield")
        riseT = 0; inkT = 0; hideT = 0; rushT = 0; revealT = 0
        ink = []
        zapFx = nil
        hintOk = s.k == "puzzle"
        if s.k == "boss", let bd = s.boss {
            var keep = retry ? (boss?.hp ?? bd.hp) : bd.hp
            if retry { keep = Swift.min(bd.hp, keep + bd.hp * 15 / 100) }
            let b = JSBoss(bd, hp: keep)
            if keep <= bd.hp / 2 { b.phase = 2 }
            boss = b
        } else {
            boss = nil
        }
        spawn()
        reached(n)
        state = (s.k == "boss" && !retry) ? "warning" : "intro"
        stateT = 0
        app.audio.music(stageSong())
        app.audio.play(state == "warning" ? "warning" : "stage")
    }

    func startPlay() {
        state = "play"
        stateT = 0
        if kind == "rain" || kind == "well" {
            hype.banner("GO GO GO!", dur: 1.0, rainbow: true)
        } else {
            hype.banner("GO!", color: "lime", dur: 0.8)
        }
    }

    func goalDone() -> Bool {
        guard let st = st else { return false }
        switch st.k {
        case "rows", "mix", "speed": return srows >= st.goal
        case "score": return score - sscore0 >= st.goal
        case "dig", "puzzle": return junkRows() == 0
        case "stars": return count("*") == 0
        case "survive": return stime >= Double(st.goal)
        case "rain", "well": return stime >= Double(st.lim)
        case "boss": return (boss?.hp ?? 0) <= 0
        default: return false
        }
    }

    /// (label, fraction done) for the goal bar.
    func progress() -> (String, Double) {
        guard let st = st else { return ("", 0) }
        let goal = st.goal
        switch st.k {
        case "rows", "mix", "speed":
            return ("ROWS \(Swift.min(srows, goal))/\(goal)", Swift.min(1, Double(srows) / Double(goal)))
        case "score":
            let got = score - sscore0
            return ("SCORE \(Swift.min(got, goal))", Swift.min(1, Double(got) / Double(goal)))
        case "dig", "puzzle":
            let left = junkRows(), tot = Swift.max(1, st.rows.count)
            return ("DUSTY ROWS \(left)", 1 - Swift.min(1, Double(left) / Double(tot)))
        case "stars":
            let left = count("*")
            return ("STARS \(goal - left)/\(goal)", Double(goal - left) / Double(goal))
        case "survive":
            return ("HANG ON \(Swift.max(0, Int(Double(goal) - stime + 0.99)))", Swift.min(1, stime / Double(goal)))
        case "rain", "well":
            return ("COINS \(coins)", Swift.min(1, stime / Double(st.lim)))
        default:
            return ("", 0)
        }
    }

    func failStage(_ why: String) {
        if state != "play" { return }
        state = "fail"
        stateT = 0
        lives -= 1
        chain = -1
        hype.breakCombo()
        app.audio.play("die")
        app.shake(4, 0.4)
        hype.banner("OOPS!", why, color: "red", dur: 1.6)
        boss?.tele = nil
    }

    func stageClear() {
        guard let st = st, state == "play" || state == "bossdown" else { return }
        let k = st.k, L = level
        state = "clear"
        stateT = 0
        app.audio.play("win")
        if k != "boss" { hype.banners = [] }
        var rows: [(String, Int)]
        if k == "rain" || k == "well" {
            hype.banner("BONUS END!", "\(coins) COINS", color: "yellow", dur: 1.4)
            rows = [("COINS", coins * 100 * L)]
        } else {
            if k != "boss" { hype.banner("STAGE CLEAR!", dur: 1.4, rainbow: true) }
            hype.shower(40, "confetti")
            rows = [(k == "boss" ? "BOSS BONUS" : "CLEAR", (k == "boss" ? 5000 : 1000) * L)]
            if k == "speed" {
                rows.append(("TIME", Int(Swift.max(0, Double(st.lim) - stime)) * 50 * L))
            } else if k == "survive" {
                rows.append(("SURVIVED", 1500 * L))
            } else if k == "puzzle" {
                rows.append(("PIECES LEFT", Swift.max(0, st.lim - used) * 1000 * L))
            } else if st.par > 0 {
                rows.append(("TIME", Int(Swift.max(0, Double(st.par) - stime)) * 20 * L))
            }
            rows.append(("NO MISS", missed ? 0 : 2000 * L))
            let cells = filled()
            if cells == 0 { rows.append(("PERFECT WELL", 5000 * L)) } else if cells <= 12 { rows.append(("CLEAN WELL", 1500 * L)) }
        }
        tally = rows.map { ($0.0, $0.1, 0) }
        tallyI = 0
        tallyT = 0
    }

    func nextStage() {
        let n = stageN
        if n >= STAGES {
            hype.jackpot(1000000, sub: "ALL 200 STAGES!")
            endGame(true, "ALL 200 STAGES!", delay: 3.5)
            return
        }
        if isBoss(n) || isBonus(n) {
            state = "upgrade"
            pickUpgrade(JSData.pool, ups, title: isBoss(n) ? "BOSS REWARD!" : "POWER UP!") { [unowned self] id in self.tookUpgrade(id) }
        } else {
            beginStage(n + 1)
        }
    }

    func tookUpgrade(_ id: String?) {
        if let id = id {
            ups[id, default: 0] += 1
            if id == "heart" { lives += 1; app.audio.play("extra") }
        } else {
            lives += 1
            hype.banner("1UP!", "EVERYTHING IS MAXED", color: "pink", dur: 1.4, sound: "extra")
        }
        beginStage(stageN + 1)
    }

    func checkLife() {
        while score >= LIFE_STEP * lifeK * (lifeK + 1) / 2 {
            lifeK += 1
            lives += 1
            hype.banner("1UP!", "EXTRA LIFE", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(20, "hearts")
        }
    }

    // ================================================================ update
    override func tick(_ dt: Double) {
        time += dt
        for y in 0 ..< BH { for x in 0 ..< BW where wob[y][x] > 0 { wob[y][x] = Swift.max(0, wob[y][x] - dt * 2.5) } }
        if let z = zapFx { zapFx = z.1 - dt > 0 ? (z.0, z.1 - dt) : nil }
        if wowOn() && hype.feverOn != feverWas {
            feverWas = hype.feverOn
            if state == "play" || !campaign { app.audio.music(feverWas ? "fever" : stageSong()) }
        }
        if chain >= 0 && hype.combo > 0 { hype.comboT = Hype.comboTime }     // the chain lives until a piece pops nothing
        if campaign && state == "play" && ending == nil { stime += dt }       // the stage clock also runs while rows pop
        if var c = clearing {
            c.1 -= dt
            clearing = c
            if c.1 <= 0 { finishClear() }
            return
        }
        if ending != nil { return }
        if campaign && !tickCampaign(dt) { return }
        playInput(dt)
    }

    func stageSong() -> String {
        guard let st = st else { return "jelly" }
        return st.k == "boss" ? "boss" : (st.k == "rain" || st.k == "well") ? "bonus" : "jelly"
    }

    /// Stage flow. Returns true when the player controls the piece this frame.
    func tickCampaign(_ dt: Double) -> Bool {
        guard let st = st else { return true }
        let inp = app.input
        stateT += dt
        switch state {
        case "warning":
            if stateT > 2.4 { state = "intro"; stateT = 0 }
            return false
        case "intro":
            if stateT > 2.6 || (stateT > 0.5 && inp.hit(.a, .b, .y)) { startPlay() }
            return false
        case "fail":
            if stateT > 1.8 {
                if lives <= 0 { endGame(false, "STAGE \(stageN)") } else { beginStage(stageN, retry: true) }
            }
            return false
        case "bossdown":
            if stateT > 0.5 && Int(stateT * 10) % 2 == 0, let b = boss {
                parts.burst(Double(BOSS_CX + Int.random(in: -16 ... 16)), Double(BOSS_CY + Int.random(in: -14 ... 14)), 10,
                            [JSData.bosses[b.id].body, "white", "yellow"], 100, 0.7)
            }
            if stateT > 2.2 { stageClear() }
            return false
        case "clear":
            if stateT > 1.2 { state = "tally"; stateT = 0 }
            return false
        case "tally":
            tickTally(dt)
            return false
        case "play":
            break
        default:
            return false
        }
        inkT = Swift.max(0, inkT - dt)
        hideT = Swift.max(0, hideT - dt)
        rushT = Swift.max(0, rushT - dt)
        revealT = Swift.max(0, revealT - dt)
        if st.rise > 0 {
            riseT += dt
            if riseT >= st.rise {
                riseT = 0
                pushRows(1)
                if state != "play" { return false }
            }
        }
        if boss != nil {
            tickBoss(dt)
            if state != "play" { return false }
        }
        if st.k == "speed" && stime >= Double(st.lim) { failStage("TIME UP!"); return false }
        if ["survive", "rain", "well", "score"].contains(st.k) && goalDone() { stageClear(); return false }
        return true
    }

    func tickTally(_ dt: Double) {
        tallyT += dt
        if tallyI < tally.count {
            var line = tally[tallyI]
            let step = Swift.max(1, line.1 / 24)
            let a = Swift.min(step, line.1 - line.2)
            line.2 += a
            tally[tallyI] = line
            score += a
            if tallyT > 0.06 && a > 0 { tallyT = 0; app.audio.play("move") }
            if line.2 >= line.1 {
                tallyI += 1
                tallyT = 0
                app.audio.play(line.1 > 0 ? "coin" : "move")
            }
            checkLife()
            return
        }
        if (tallyT > 0.6 && app.input.hit(.a, .b, .y)) || tallyT > 3.0 { nextStage() }
    }

    func tickBoss(_ dt: Double) {
        guard let b = boss else { return }
        b.hit = Swift.max(0, b.hit - dt)
        if var tele = b.tele {
            tele.1 -= dt
            b.tele = tele
            if tele.1 <= 0 {
                b.tele = nil
                bossAttack(tele.0)
                if b.phase >= 3 && state == "play" && Double.random(in: 0 ..< 1) < 0.5 { b.t = 1.2 }
            }
            return
        }
        b.t -= dt
        if b.t <= 0 {
            b.t = b.every * (b.phase >= 2 ? 0.75 : 1.0)
            let atk = Double.random(in: 0 ..< 1) < 0.45 ? b.atk[0] : b.atk.randomElement()!
            b.tele = (atk, Swift.max(1.2, 2.2 - Double(tierN) * 0.05))
            b.col = Int.random(in: 0 ..< BW - 1)
            b.hole = Int.random(in: 0 ..< BW)
            app.audio.play("trap")
        }
    }

    func playInput(_ dt: Double) {
        let inp = app.input
        if inp.hit(.x) { doHold(); return }
        if inp.hit(.y) || inp.spaceKey { hardDrop(); return }
        if inp.hit(.up, .b) { rotate(1) } else if inp.hit(.a) && !inp.spaceKey { rotate(-1) }
        // horizontal with DAS
        let d = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        if d != dasDir {
            dasDir = d; dasT = 0; arrT = 0
            if d != 0 && tryMove(d, 0) { app.audio.play("move") }
        } else if d != 0 {
            dasT += dt
            if dasT > 0.167 {                // delayed auto shift, then auto repeat every 33 ms
                arrT += dt
                while arrT >= 0.033 { arrT -= 0.033; if !tryMove(d, 0) { break } }
            }
        }
        // gravity / soft drop
        var g = gravity()
        if inp.down(.down) { g = Swift.min(g, 0.03) }
        fallT += dt
        while fallT >= g {
            fallT -= g
            if tryMove(0, 1) { if inp.down(.down) { add(1) } } else { fallT = 0; break }
        }
        if grounded() { lockT += dt; if lockT >= lockDelay() { lock() } } else { lockT = 0 }
    }

    // ================================================================ drawing
    override func render(_ s: Surface) {
        JSArt.background(s, theme, t)
        drawWell(s)
        drawHud(s)
        parts.draw(s)
        floats.draw(s)
        if campaign {
            switch state {
            case "warning": drawWarning(s)
            case "intro": drawIntro(s)
            case "tally": drawTally(s)
            default: break
            }
        }
    }

    func drawCell(_ s: Surface, _ x: Int, _ y: Int, _ c: String, _ wobble: Double = 0, rb: Int = -1) {
        let px = BX + x * CELL, py = BY + y * CELL, size = CELL
        if PIECE_COLORS.contains(c) {
            Cute.jellyCell(s, px, py, size, rb >= 0 ? rainbow(rb, t) : c, t, wobble: wobble)
            return
        }
        switch c {
        case "g":
            Cute.jellyCell(s, px, py, size, "gray", face: false)
            s.fillRect(col("darkgray"), px + 2, py + 4, 2, 1)
            s.fillRect(col("darkgray"), px + 5, py + 4, 2, 1)
        case "*":
            let tw = Int(t * 4 + Double(x + y)) % 4 == 0
            Cute.jellyCell(s, px, py, size, tw ? "orange" : "yellow", face: false)
            drawText(s, "$", px + 2, py + 1, "white", shadow: nil)
        case "i":
            Cute.jellyCell(s, px, py, size, "sky", face: false)
            s.rect(col("white"), IRect(px, py, size, size), width: 1, radius: 2)
            s.fillRect(col("white"), px + 2, py + 5, 1, 1)
            s.fillRect(col("white"), px + 3, py + 4, 1, 1)
            s.fillRect(col("white"), px + 4, py + 3, 1, 1)
        case "b":
            Cute.jellyCell(s, px, py, size, "red", face: false)
            s.circle(col("black"), px + 4, py + 5, 2)
            s.fillRect(col(Int(t * 8) % 2 == 1 ? "yellow" : "orange"), px + 5, py + 1, 2, 2)
        case "c":
            Cute.jellyCell(s, px, py, size, "peach", face: false)
            s.circle(col("yellow"), px + 4, py + 4, 3)
            s.circle(col("orange"), px + 4, py + 4, 3, width: 1)
        case "$":
            Cute.jellyCell(s, px, py, size, "yellow", t, wobble: wobble)
            if Int(t * 6 + Double(x * 3 + y)) % 5 == 0 { s.fillRect(col("white"), px + 6, py + 1, 2, 2) }
        case "s":
            s.rect(col("gray"), IRect(px, py, size, size), radius: 1)
            s.rect(col("cream"), IRect(px, py, size, size - 1), radius: 1)
            s.fillRect(col("white"), px + 1, py + 1, size - 3, 1)
        default:
            break
        }
    }

    func drawWell(_ s: Surface) {
        let hue = theme.hue
        let top = stackTop()
        let danger = top < 5 && (state == "play" || !campaign)
        let red = danger && Int(t * 6) % 2 == 1
        let r = IRect(BX - 3, BY - 3, WELL_W + 6, WELL_H + 6)
        s.rect(col("black"), r.moved(2, 2), radius: 3)
        s.rect(campaign ? lerpCol("black", hue, 0.06) : col("black"), r, radius: 3)
        s.rect(red ? col("red") : (campaign ? col(hue) : col("lavender")), r, width: 1, radius: 3)
        let chk = campaign ? lerpCol("black", hue, 0.14) : col("night")
        for y in 0 ..< BH { for x in 0 ..< BW where (x + y) % 2 == 0 { s.fillRect(chk, BX + x * CELL, BY + y * CELL, CELL, CELL) } }
        let clearingRows = Set(clearing?.0 ?? [])
        let fever = hype.feverOn
        let vanish = mod("vanish") && state == "play" && revealT <= 0
        for y in 0 ..< BH {
            for x in 0 ..< BW {
                guard let c = grid[y][x] else { continue }
                if clearingRows.contains(y) {
                    if Int(clearing!.1 * 20) % 2 == 1 { s.fillRect(col("white"), BX + x * CELL, BY + y * CELL, CELL, CELL) } else { drawCell(s, x, y, c) }
                    continue
                }
                if vanish {
                    s.rect(lerpCol("black", hue, 0.35), IRect(BX + x * CELL, BY + y * CELL, CELL, CELL), width: 1)
                    continue
                }
                let w = sin(t * 30 + Double(x)) * wob[y][x] * 1.5
                drawCell(s, x, y, c, w, rb: fever && PIECE_COLORS.contains(c) ? x + y : -1)
            }
        }
        if mod("fog") && state == "play" {
            s.fillRect(col("gray", 205), BX, BY + 12 * CELL, WELL_W, 8 * CELL)
            for i in 0 ..< 6 {
                let fx = BX + 4 + Int((t * Double(6 + i) * 3 + Double(i * 23)).truncatingRemainder(dividingBy: Double(WELL_W - 8)))
                s.circle(col("white"), fx, BY + 12 * CELL + 2, 4)
            }
        }
        if let z = zapFx {
            let y = BY + z.0 * CELL + 4, w = Int(z.1 * 10)
            s.fillRect(col("yellow"), BX, y - w / 2, WELL_W, Swift.max(1, w))
            s.fillRect(col("white"), BX, y, WELL_W, 1)
        }
        let playing = !campaign || state == "play" || state == "intro"
        if clearing == nil && ending == nil && playing && ghostOpt && !mod("noghost") {
            var gy = cur.y
            while fits(cur.cells(nil, gy + 1)) { gy += 1 }
            for (x, y) in cur.cells(nil, gy) where y >= 0 {
                Cute.jellyCell(s, BX + x * CELL, BY + y * CELL, CELL, pieceColor(), ghost: true)
            }
        }
        if inkT > 0 { drawInk(s) }
        if let h = hint, state == "play", clearing == nil, Int(t * 4) % 2 == 1 {
            for (x, y) in h where y >= 0 { Cute.jellyCell(s, BX + x * CELL, BY + y * CELL, CELL, "white", ghost: true) }
        }
        if clearing == nil && ending == nil && playing {
            for (i, (x, y)) in cur.cells().enumerated() where y >= 0 {
                Cute.jellyCell(s, BX + x * CELL, BY + y * CELL, CELL, pieceColor(), t)
                if i == cur.bomb {
                    let px = BX + x * CELL, py = BY + y * CELL
                    s.circle(col("black"), px + 4, py + 5, 3)
                    s.fillRect(col(Int(t * 10) % 2 == 1 ? "yellow" : "red"), px + 6, py + 1, 2, 2)
                }
            }
        }
        if let b = boss, b.tele != nil, state == "play" { drawTeleWell(s, b) }
        if let st = st, st.rise > 0, state == "play" {
            let f = riseT / st.rise
            let c = f > 0.8 && Int(t * 10) % 2 == 1 ? "red" : "orange"
            s.fillRect(col(c), BX, BY + WELL_H + 1, Int(Double(WELL_W) * f), 2)
        }
        if campaign && state == "fail" {
            s.fillRect(rgba(12, 8, 24, Swift.min(170, Int(stateT * 200))), BX, BY, WELL_W, WELL_H)
        }
    }

    func pieceColor() -> String {
        if cur.gold { return Int(t * 8) % 2 == 1 ? "yellow" : "orange" }
        if hype.feverOn { return rainbow(0, t) }
        return GData.jellyColors[cur.kind]!
    }

    func drawInk(_ s: Surface) {
        let fade = Swift.min(1, inkT / 0.6)
        for (y, x, r) in ink {             // ink blobs, clipped to the well
            let rr = Swift.max(1, Int(Double(r) * fade))
            let cx = BX + x * CELL + 4, cy = BY + y * CELL + 4
            for dy in -rr ... rr {
                let yy = cy + dy
                if yy >= BY && yy < BY + WELL_H {
                    let half = Int(Double(rr * rr - dy * dy).squareRoot())
                    let a = Swift.max(BX, cx - half), b = Swift.min(BX + WELL_W, cx + half + 1)
                    if b > a { s.fillRect(col("night"), a, yy, b - a, 1) }
                }
            }
            if rr > 4 { s.circle(col("purple"), cx - rr / 3, cy - rr / 3, 2) }
        }
    }

    func drawTeleWell(_ s: Surface, _ b: JSBoss) {
        guard let (atk, _) = b.tele else { return }
        let blink = Int(t * 8) % 2 == 1
        if atk == "heavy" {
            let x = BX + b.col * CELL
            s.fillRect(col("red", blink ? 60 : 30), x, BY, CELL * 2, WELL_H)
            drawText(s, "`", x + 6, BY + 2, blink ? "red" : "white", shadow: nil)
        } else if atk == "garbage" {
            let n = Swift.min(4, 1 + (b.pow + (b.phase >= 3 ? 1 : 0)) / 3)
            for x in 0 ..< BW where x != b.hole {
                s.fillRect(col(blink ? "red" : "orange"), BX + x * CELL, BY + WELL_H + 1, CELL - 1, 2)
            }
            drawText(s, "+\(n)", BX - 6, BY + WELL_H - 8, "red", align: .right)
        }
    }

    // ---------------------------------------------------------------- HUD
    func drawHud(_ s: Surface) {
        let hue = campaign ? theme.hue : "lavender", acc = campaign ? theme.acc : "yellow"
        // header: score | goal or boss bar | lives
        drawText(s, "\(score)", 4, 4, "yellow")
        if campaign {
            s.blit(sprite("heart"), W - 30, 3)
            drawText(s, "x\(lives)", W - 21, 4, "white")
            if let b = boss {
                bossBar(s, JSData.bosses[b.id].name, Double(b.hp), Double(b.max), t, y: 1)
            } else {
                let (label, frac) = progress()
                goalBar(s, label, frac, hue)
            }
        } else {
            let label = ["marathon": "MARATHON  \(lines)/150", "sprint": "SPRINT  \(lines)/40"][mode] ?? "ENDLESS  \(lines) LINES"
            let frac = mode == "marathon" ? Double(lines) / 150 : mode == "sprint" ? Double(lines) / 40 : 0
            goalBar(s, label, Swift.min(1, frac), "lavender")
            drawText(s, "LV \(level)", W - 4, 4, "mint", align: .right)
        }
        // left column: hold
        let noHold = mod("nohold")
        for (i, h) in holds.enumerated() {
            let x = 6 + i * 52
            panel(s, IRect(x, 18, 48, 34), fill: "ink", border: noHold ? "darkgray" : "pink")
            drawText(s, i == 0 ? "HOLD" : "HOLD 2", x + 24, 21, noHold ? "darkgray" : "pink", align: .center, shadow: nil)
            if noHold { drawText(s, "X", x + 24, 36, "darkgray", align: .center) } else if let h = h { mini(s, h, x + 24, 39, 7) }
        }
        // stage / mode panel
        panel(s, IRect(6, 56, 100, 44), fill: "ink", border: hue)
        if campaign {
            let n = stageN
            let title = "STAGE \(n)" + (isBoss(n) ? " BOSS" : isBonus(n) ? " BONUS" : "")
            drawText(s, title, 56, 60, isBoss(n) ? "red" : "yellow", align: .center)
            drawText(s, theme.name, 56, 70, acc, align: .center, shadow: nil)
        } else {
            drawText(s, ["marathon": "MARATHON", "sprint": "SPRINT 40"][mode] ?? "ENDLESS", 56, 60, "yellow", align: .center)
            drawText(s, mode == "sprint" ? String(format: "TIME %.1f", time) : "LINES \(lines)", 56, 70, "white", align: .center, shadow: nil)
        }
        drawText(s, "HI \(Swift.max(best, score))", 56, 84, "lavender", align: .center, shadow: nil)
        // goal / info panel
        panel(s, IRect(6, 104, 100, 56), fill: "ink", border: hue)
        if campaign {
            drawGoalPanel(s, acc)
        } else {
            drawText(s, "COMBO", 12, 110, "lavender", shadow: nil)
            drawText(s, "\(Swift.max(0, chain + 1))", 100, 110, "white", align: .right)
            drawText(s, "LEVEL", 12, 124, "lavender", shadow: nil)
            drawText(s, "\(level)", 100, 124, "white", align: .right)
            drawText(s, b2b ? "B2B" : "", 56, 142, "pink", align: .center)
        }
        // upgrades
        if campaign {
            panel(s, IRect(6, 164, 100, 32), fill: "ink", border: "darkgray")
            let owned = JSData.upgrades.filter { (ups[$0.id] ?? 0) > 0 }
            if owned.isEmpty {
                drawText(s, "NO UPGRADES", 56, 169, "darkgray", align: .center, shadow: nil)
                drawText(s, "BEAT BOSSES!", 56, 180, "darkgray", align: .center, shadow: nil)
            }
            for (i, u) in owned.prefix(10).enumerated() {
                let x = 10 + (i % 5) * 19, y = 167 + (i / 5) * 14
                Cute.jellyCell(s, x, y, 9, u.color, face: false)
                drawText(s, JSData.iconGlyph[u.id] ?? "?", x + 2, y + 1, "black", shadow: nil)
                drawText(s, "\(ups[u.id] ?? 0)", x + 10, y + 3, "white", shadow: nil)
            }
        }
        // right column: next
        let nn = nNext()
        let ph = 26 + (nn - 1) * 18
        panel(s, IRect(214, 18, 50, ph), fill: "ink", border: "mint")
        drawText(s, "NEXT", 239, 21, "mint", align: .center, shadow: nil)
        for i in 0 ..< nn {
            let cy = i > 0 ? 38 + i * 18 : 37
            if hideT > 0 {
                drawText(s, "?", 239, cy - 3, Int(t * 6 + Double(i)) % 2 == 1 ? "hotpink" : "lavender", align: .center)
            } else if i < queue.count {
                mini(s, queue[i], 239, cy + (i > 0 ? 1 : 0), i == 0 ? 7 : 5)
            }
        }
        if campaign && st?.k == "puzzle" { drawText(s, "\(queue.count) LEFT", 239, 20 + ph, "white", align: .center, shadow: nil) }
        drawMeters(s)
        // boss or buddy
        if campaign {
            panel(s, IRect(214, 116, 100, 80), fill: "ink", border: boss != nil ? "red" : hue)
            if let b = boss { drawBossArea(s, b) } else { drawBuddy(s, hue) }
        }
    }

    func goalBar(_ s: Surface, _ label: String, _ frac: Double, _ hue: String) {
        panel(s, IRect(60, 1, 200, 12), fill: "black", border: hue, radius: 3, shadow: false)
        drawText(s, label, 64, 4, "white", shadow: nil)
        let x0 = 68 + textWidth(label), bw = 256 - x0
        if bw > 4 {
            s.fillRect(col("darkgray"), x0, 5, bw, 4)
            s.fillRect(col(frac >= 1 ? "lime" : hue), x0, 5, Int(Double(bw) * frac), 4)
            s.fillRect(col("white"), x0, 5, Int(Double(bw) * frac), 1)
        }
    }

    func drawGoalPanel(_ s: Surface, _ acc: String) {
        guard let st = st else { return }
        let k = st.k
        drawText(s, KIND_TITLE[k] ?? "", 56, 108, acc, align: .center)
        var big = "", sub = ""
        switch k {
        case "rows", "mix", "speed": big = "\(Swift.max(0, st.goal - srows))"; sub = "ROWS TO GO"
        case "score": big = "\(Swift.max(0, st.goal - (score - sscore0)))"; sub = "POINTS TO GO"
        case "dig", "puzzle": big = "\(junkRows())"; sub = "DUSTY ROWS"
        case "stars": big = "\(count("*"))"; sub = "STARS LEFT"
        case "survive": big = "\(Swift.max(0, Int(Double(st.goal) - stime + 0.99)))"; sub = "SECONDS"
        case "rain", "well": big = "\(Swift.max(0, Int(Double(st.lim) - stime + 0.99)))"; sub = "\(coins) COINS"
        case "boss":
            if let b = boss { big = "\(Int((100 * Double(b.hp) / Double(b.max)).rounded(.up)))%" }
            sub = "BOSS HP"
        default: break
        }
        let sc = textWidth(big, 2) <= 92 ? 2 : 1
        drawText(s, big, 56, sc == 2 ? 119 : 122, "white", scale: sc, align: .center)
        drawText(s, sub, 56, 136, "lavender", align: .center, shadow: nil)
        var extra = ""
        if k == "speed" {
            let left = Swift.max(0, Double(st.lim) - stime)
            extra = String(format: "TIME %.0f", left)
            if left < 10 && Int(t * 4) % 2 == 1 { extra = "" }
        } else if k == "puzzle" {
            extra = "PIECES \(queue.count + (state == "play" ? 1 : 0))"
        } else if !st.mods.isEmpty {
            extra = st.mods.map { JSData.mods[$0] ?? $0 }.joined(separator: " ")
        }
        if !extra.isEmpty {
            drawText(s, extra, 56, 148, (k == "speed" || k == "puzzle") ? "orange" : "pink", align: .center, shadow: nil)
        }
    }

    func drawMeters(_ s: Surface) {
        let x = 270, h = 60
        drawText(s, "FVR", x, 21, "hotpink", shadow: nil)          // fever gauge (vertical)
        s.fillRect(col("black"), x + 4, 31, 9, h + 2)
        let f = hype.feverOn ? 1.0 : hype.fever
        let fh = Int(Double(h) * f)
        s.fillRect(col(hype.feverOn ? rainbow(0, t) : "hotpink"), x + 5, 32 + h - fh, 7, fh)
        s.rect(col("pink"), IRect(x + 4, 31, 9, h + 2), width: 1)
        guard campaign, let st = st else { return }
        let yy = 96
        if up("zap") > 0 {
            let need = 12 - 2 * up("zap")
            drawText(s, "ZAP", 292, 21, "yellow", shadow: nil)
            s.fillRect(col("black"), 296, 31, 9, h + 2)
            let zh = Int(Double(h) * Swift.min(1, Double(zap) / Double(need)))
            s.fillRect(col("yellow"), 297, 32 + h - zh, 7, zh)
            s.rect(col("yellow"), IRect(296, 31, 9, h + 2), width: 1)
        }
        if up("shield") > 0 {
            Cute.jellyCell(s, 270, yy + 4, 9, "lavender", face: false)
            drawText(s, "=", 272, yy + 5, "black", shadow: nil)
            drawText(s, "x\(shield)", 281, yy + 6, "lavender", shadow: nil)
        }
        if st.rise > 0 && boss == nil { drawText(s, "RISE", 312, yy + 6, "orange", align: .right, shadow: nil) }
    }

    func mini(_ s: Surface, _ kind: String, _ cx: Int, _ cy: Int, _ size: Int) {
        let cells = GData.jellyRot[kind]![0]
        let xs = cells.map { $0.0 }, ys = cells.map { $0.1 }
        let w = (xs.max()! - xs.min()! + 1) * size, h = (ys.max()! - ys.min()! + 1) * size
        for (x, y) in cells {
            Cute.jellyCell(s, cx - w / 2 + (x - xs.min()!) * size, cy - h / 2 + (y - ys.min()!) * size, size, GData.jellyColors[kind]!, face: false)
        }
    }

    /// A big jelly pal beside the well that cheers you on.
    func drawBuddy(_ s: Surface, _ hue: String) {
        let cx = 264, cy = 160
        let happy = chain > 0 || state == "clear" || state == "tally"
        let worried = stackTop() < 7
        let bob = Int(sin(t * (happy ? 8 : 3)) * (happy ? 3 : 1))
        let w = 40 + Int(sin(t * 5) * 2)
        let body = IRect(cx - w / 2, cy - 18 + bob, w, 36 - bob)
        s.rect(lerpCol("black", hue, 0.55), body.moved(0, 2), radius: 10)
        s.rect(col(hue), body, radius: 10)
        s.fillRect(col("white"), body.x + 6, body.y + 4, 8, 2)
        Cute.eyes(s, cx, cy - 4 + bob, 7, mood: worried ? "wow" : "happy", blink: Int(t * 1.3) % 6 == 0, size: 2)
        Cute.mouth(s, cx, cy + 5 + bob, worried ? "wow" : "happy")
        Cute.blush(s, cx, cy + 2 + bob, 10)
        let msg = happy ? "YAY!" : worried ? "EEK!" : ""
        if !msg.isEmpty { drawText(s, msg, cx, 124, happy ? "yellow" : "red", align: .center) }
    }

    func drawBossArea(_ s: Surface, _ b: JSBoss) {
        let down = ["bossdown", "clear", "tally", "upgrade"].contains(state)
        if (state == "bossdown" && stateT > 1.0) || ["clear", "tally", "upgrade"].contains(state) {
            drawText(s, "DEFEATED!", BOSS_CX, BOSS_CY - 4, "yellow", align: .center)
            return
        }
        let shake = (b.hit > 0 || down) ? Int.random(in: -2 ... 2) : 0
        JSArt.boss(s, b.id, BOSS_CX + shake, BOSS_CY, t, hurt: b.hit > 0 && Int(t * 20) % 2 == 0, angry: b.phase >= 2)
        if let (atk, _) = b.tele, state == "play" {
            let blink = Int(t * 8) % 2 == 1
            drawText(s, (JSData.attackNames[atk] ?? atk) + "!", BOSS_CX, 185, blink ? "red" : "yellow", align: .center, shadow: "black")
            s.circle(col("white"), BOSS_CX + 22, BOSS_CY - 24, 6)
            drawText(s, "!", BOSS_CX + 20, BOSS_CY - 27, "red", shadow: nil)
        } else if state == "play" {
            let w = Int(80 * Swift.min(1, Swift.max(0, b.t) / b.every))
            s.fillRect(col("darkgray"), 224, 190, 80, 2)
            s.fillRect(col("red"), 224, 190, w, 2)
        }
        if inkT > 0 { drawText(s, "INK!", 222, 124, "purple", shadow: nil) }
        if rushT > 0 { drawText(s, "RUSH!", 306, 124, "orange", align: .right, shadow: nil) }
    }

    func drawWarning(_ s: Surface) {
        let tt = stateT
        if Int(tt * 6) % 2 == 0 {
            for i in stride(from: 0, to: W, by: 16) {
                let x = Double((i + Int(tt * 60)) % (W + 16) - 16)
                s.polygon(col("red"), [(x, 70), (x + 8, 70), (x + 16, 62), (x + 8, 62)])
                s.polygon(col("red"), [(x, 138), (x + 8, 138), (x + 16, 130), (x + 8, 130)])
            }
        }
        s.fillRect(rgba(12, 8, 24, 200), 0, 74, W, 56)
        drawText(s, "WARNING!!", W / 2, 82, Int(tt * 8) % 2 == 1 ? "red" : "yellow", scale: 3, align: .center, outline: "black")
        if let bd = st?.boss { drawText(s, "\(JSData.bosses[bd.id].name) APPROACHES", W / 2, 110, "white", align: .center) }
    }

    func drawIntro(_ s: Surface) {
        guard let st = st else { return }
        let appear = Swift.min(1, stateT * 5)
        let y = 46 + Int((1 - appear) * 40)
        let bonus = st.k == "rain" || st.k == "well"
        panel(s, IRect(44, y, 232, 104), fill: "night", border: st.k == "boss" ? "red" : bonus ? "yellow" : theme.hue)
        drawText(s, "STAGE \(stageN)", W / 2, y + 8, "yellow", scale: 2, align: .center, outline: "ink")
        drawText(s, theme.name, W / 2, y + 28, theme.acc, align: .center)
        drawText(s, goalText(), W / 2, y + 44, "white", align: .center)
        if !st.mods.isEmpty { drawText(s, st.mods.map { JSData.mods[$0] ?? $0 }.joined(separator: " + "), W / 2, y + 58, "pink", align: .center) }
        if !st.new.isEmpty { drawText(s, "NEW! " + st.new, W / 2, y + 72, Int(t * 4) % 2 == 1 ? "lime" : "mint", align: .center) }
        if missed {
            drawText(s, st.k == "puzzle" ? "TRY AGAIN! HINTS ON" : "TRY AGAIN!", W / 2, y + 86, "peach", align: .center)
        } else if stateT > 0.5 {
            drawText(s, "DROP: GO!", W / 2, y + 88, "lavender", align: .center, shadow: nil)
        }
    }

    func goalText() -> String {
        guard let st = st else { return "" }
        let g = st.goal
        switch st.k {
        case "rows": return "POP \(g) ROWS"
        case "mix": return "POP \(g) ROWS - ROWS RISE!"
        case "score": return "SCORE \(g) POINTS"
        case "dig": return "CLEAR ALL THE DUSTY JELLY"
        case "stars": return "POP ALL \(g) STAR JELLIES"
        case "survive": return "SURVIVE \(g) SECONDS"
        case "puzzle": return "CLEAR IT WITH \(st.lim) PIECES"
        case "speed": return "POP \(g) ROWS IN \(st.lim) SEC"
        case "rain": return "30 SEC: EVERY POP RAINS COINS"
        case "well": return "30 SEC: LONG JELLIES ONLY!"
        case "boss": return "BEAT \(JSData.bosses[st.boss?.id ?? 0].name)!"
        default: return ""
        }
    }

    func drawTally(_ s: Surface) {
        guard let st = st else { return }
        let appear = Swift.min(1, stateT * 6)
        let y = 40 + Int((1 - appear) * 30)
        panel(s, IRect(52, y, 216, 26 + 12 * tally.count + 26), fill: "night", border: "yellow")
        let title = st.k == "boss" ? "BOSS DEFEATED!" : (st.k == "rain" || st.k == "well") ? "BONUS RESULTS" : "STAGE \(stageN) CLEAR!"
        drawText(s, title, W / 2, y + 8, "yellow", align: .center)
        var total = 0
        for (i, line) in tally.enumerated() where i <= tallyI {
            let yy = y + 24 + i * 12
            drawText(s, line.0, 64, yy, line.1 > 0 ? "lavender" : "darkgray", shadow: nil)
            drawText(s, line.1 > 0 ? "\(line.2)" : "-", 256, yy, line.1 > 0 ? "white" : "darkgray", align: .right)
            total += line.2
        }
        let yy = y + 28 + 12 * tally.count
        s.fillRect(col("lavender"), 64, yy - 2, 192, 1)
        drawText(s, "TOTAL", 64, yy + 2, "yellow")
        drawText(s, "\(total)", 256, yy + 2, "yellow", align: .right)
        if tallyI >= tally.count && tallyT > 0.6 {
            drawText(s, "DROP: NEXT", W / 2, yy + 16, Int(t * 3) % 2 == 1 ? "white" : "lavender", align: .center, shadow: nil)
        }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("ink"))
        let h = s.h
        let kinds = ["mint", "pink", "yellow", "sky", "lavender", "lime", "peach"]
        for y in 0 ..< 4 {
            for x in 0 ..< 10 where (x * 7 + y * 3) % 5 != 0 {
                let c = (x + y * 3) % 11 == 0 ? "gray" : kinds[(x + y) % 7]
                Cute.jellyCell(s, 2 + x * 9, h - 9 - y * 9, 9, c, t, wobble: sin(t * 6 + Double(x)))
            }
        }
        Cute.jellyCell(s, 2 + 3 * 9, h - 9 - 3 * 9, 9, "yellow", face: false)
        drawText(s, "$", 2 + 3 * 9 + 2, h - 9 - 3 * 9 + 1, "white", shadow: nil)
        let py = Int((t * 20).truncatingRemainder(dividingBy: 30))
        for (cx, cy) in [(4, 0), (5, 0), (6, 0), (5, 1)] { Cute.jellyCell(s, 2 + cx * 9, py + cy * 9, 9, "pink", t) }
    }
}
