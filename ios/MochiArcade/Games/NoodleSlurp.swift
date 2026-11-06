// NOODLE SLURP - a hungry noodle slurps dumplings through a 200-stage kitchen campaign
// (port of games/noodle_slurp.py; the stage tables come from noodle_slurp_stages.py via GameData).
import Foundation

private let GW = 32, GH = 20, C = 8
private let NCELLS = GW * GH
private let OX = (W - GW * C) / 2, OY = 22
private let DIRS: [(Action, (Int, Int))] = [(.up, (0, -1)), (.down, (0, 1)), (.left, (-1, 0)), (.right, (1, 0))]
private let D4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
private let STEP = ["slow": 0.16, "normal": 0.115, "fast": 0.08]          // endless modes
private let SPEED_MULT = ["slow": 1.25, "normal": 1.0, "fast": 0.8]      // campaign
private let MILESTONES = [20, 30, 40, 50, 75, 100, 150, 200]
private let ARROWS: [Character: (Int, Int)] = [">": (1, 0), "<": (-1, 0), "v": (0, 1), "^": (0, -1)]
private let PORTALS: Set<Character> = ["1", "2", "3", "4"]
private let PORTAL_COLORS: [Character: [String]] = ["1": ["lavender", "purple"], "2": ["mint", "teal"],
                                                    "3": ["pink", "hotpink"], "4": ["yellow", "orange"]]
private let WEAK_LOOK = ["crab": "chili", "teapot": "sugar", "golem": "bean", "bao": "bun", "sushi": "chili", "ghost": "chili"]
private let WEAK_ATTACK = ["crab": "toss", "teapot": "beam", "sushi": "plates", "golem": "drop", "bao": "toss"]

private func cxy(_ c: Int) -> (Int, Int) { (c % GW, c / GW) }
/// Top-left pixel of a cell.
private func cpx(_ c: Int) -> (Int, Int) { (OX + (c % GW) * C, OY + (c / GW) * C) }
private func ringOf(_ c: Int) -> Int { let (x, y) = cxy(c); return min(x, y, GW - 1 - x, GH - 1 - y) }
private func ndPmod(_ a: Double, _ b: Double) -> Double { let r = a.truncatingRemainder(dividingBy: b); return r < 0 ? r + b : r }
private func ndImod(_ a: Int, _ b: Int) -> Int { ((a % b) + b) % b }
private func ndNum(_ a: Any?) -> Double { (a as? NSNumber)?.doubleValue ?? 0 }
private func ndInt(_ a: Any?) -> Int { (a as? NSNumber)?.intValue ?? 0 }

// ---------------------------------------------------------------------- exported stage data
private struct NdBossData { let kind: String; let hp: Int; let lvl: Int; let pool: [String]; let cool, tele, move: Double }

private struct NdStage {
    let n: Int, kind: String, theme: Int, map: [Character], sp: (Int, Int), len: Int
    let goal: String, target: Int, foods: Int, step: Double, par: Double, gate: Int
    let rollers: [[Double]], vents: [[Double]], squeeze: [Double], new: String
    let boss: NdBossData?
}

private enum NdData {
    static let root: [String: Any] = (GameData.json("noodle_slurp") as? [String: Any]) ?? [:]
    static let stages: [NdStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        let sp = (d["sp"] as? [Any]) ?? [8, 10]
        var boss: NdBossData?
        if let b = d["boss"] as? [String: Any] {
            boss = NdBossData(kind: b["kind"] as? String ?? "crab", hp: ndInt(b["hp"]), lvl: ndInt(b["lvl"]),
                         pool: b["pool"] as? [String] ?? ["sweep"], cool: ndNum(b["cool"]), tele: ndNum(b["tele"]), move: ndNum(b["move"]))
        }
        return NdStage(n: ndInt(d["n"]), kind: d["kind"] as? String ?? "stage", theme: ndInt(d["theme"]),
                      map: Array(d["map"] as? String ?? String(repeating: ".", count: NCELLS)),
                      sp: (ndInt(sp[0]), ndInt(sp[1])), len: ndInt(d["len"]), goal: d["goal"] as? String ?? "eat",
                      target: ndInt(d["target"]), foods: ndInt(d["foods"]), step: ndNum(d["step"]), par: ndNum(d["par"]),
                      gate: ndInt(d["gate"]), rollers: ((d["rollers"] as? [[Any]]) ?? []).map { $0.map { ndNum($0) } },
                      vents: ((d["vents"] as? [[Any]]) ?? []).map { $0.map { ndNum($0) } },
                      squeeze: ((d["squeeze"] as? [Any]) ?? []).map { ndNum($0) }, new: d["new"] as? String ?? "", boss: boss)
    }
    static let themes: [[String]] = (root["themes"] as? [[String]]) ?? [["KITCHEN", "choco", "brown", "cream", "peach", "brown", "choco", "lime"]]
    static let bosses: [String: [String: Any]] = (root["bosses"] as? [String: [String: Any]]) ?? [:]
    static let pool: [Upgrade] = ((root["upgrades"] as? [[Any]]) ?? []).map {
        Upgrade(id: $0[0] as? String ?? "", name: $0[1] as? String ?? "", desc: $0[2] as? String ?? "",
                color: $0[3] as? String ?? "mint", icon: $0[4] as? String, max: ndInt($0[5]))
    }
}

private func endlessStage(_ speed: String) -> NdStage {
    NdStage(n: 0, kind: "endless", theme: 0, map: Array(repeating: ".", count: NCELLS), sp: (8, 10), len: 4, goal: "endless",
           target: 0, foods: 1, step: STEP[speed] ?? 0.115, par: 0, gate: 0, rollers: [], vents: [], squeeze: [], new: "", boss: nil)
}

private func portalMap(_ g: [Character]) -> [Int: Int] {
    var pos: [Character: [Int]] = [:]
    for (c, ch) in g.enumerated() where PORTALS.contains(ch) { pos[ch, default: []].append(c) }
    var link: [Int: Int] = [:]
    for cells in pos.values where cells.count == 2 { link[cells[0]] = cells[1]; link[cells[1]] = cells[0] }
    return link
}

// ---------------------------------------------------------------------- moving parts
/// Rolling meatball (bounces), sushi plate / gold plate / fortune slip (fly straight, break on contact).
private final class NdRoller {
    var x, y, dx, dy: Int
    let period: Double
    let kind: String
    var acc = 0.0, spin = 0.0
    var alive = true
    init(_ x: Int, _ y: Int, _ dx: Int, _ dy: Int, _ period: Double, _ kind: String = "ball") {
        self.x = x; self.y = y; self.dx = dx; self.dy = dy; self.period = period; self.kind = kind
    }
    var cell: Int { y * GW + x }
}

private final class NdVent {
    static let warn = 0.7, on = 1.0
    let x, y, dx, dy: Int
    let period, phase: Double
    var life: Double
    let beam: [Int]
    init(_ x: Int, _ y: Int, _ dx: Int, _ dy: Int, _ ln: Int, _ period: Double, _ phase: Double, _ life: Double = -1) {
        self.x = x; self.y = y; self.dx = dx; self.dy = dy; self.period = period; self.phase = phase; self.life = life
        beam = (0 ... ln).map { (y + dy * $0) * GW + x + dx * $0 }
    }
    func state(_ t: Double) -> Int {
        let u = ndPmod(t + phase, period)
        if u >= period - NdVent.on { return 2 }
        if u >= period - NdVent.on - NdVent.warn { return 1 }
        return 0
    }
}

private final class NdItem {
    let kind: String
    let cell: Int
    var life: Double
    let look: String
    var t = 0.0
    init(_ kind: String, _ cell: Int, _ life: Double = -1, _ look: String = "") {
        self.kind = kind; self.cell = cell; self.life = life; self.look = look
    }
}

private final class NdAttack {
    let kind: String
    let cells: [Int]
    let tele, act: Double
    let style: String
    let dx, dy, gold: Int
    let src: (Int, Int)
    var t = 0.0
    var fired = false
    init(_ kind: String, _ cells: [Int], _ tele: Double, _ act: Double = 0, _ style: String = "", dx: Int = 0, dy: Int = 0,
         gold: Int = -1, src: (Int, Int)? = nil) {
        self.kind = kind; self.cells = cells; self.tele = tele; self.act = act; self.style = style
        self.dx = dx; self.dy = dy; self.gold = gold; self.src = src ?? (W / 2, OY)
    }
    var live: Bool { tele <= t && t < tele + act }
}

private final class NdBoss {
    let kind, name, hint: String
    let w, h: Int
    var hp: Int
    let maxhp, lvl: Int
    let pool: [String]
    let cool, tele, move: Double
    var x, y: Int
    var cd = 2.2, moveT = 0.0
    var mdir = 1
    var flash = 0.0, stun = 0.0, inv = 0.0, anim = 0.0, lid = 0.0
    var angry = false
    var last = ""
    var dead = false
    var dash = 0, ddx = 0, ddy = 0
    var weakWait = 0.0, t = 0.0

    init(_ d: NdBossData) {
        let info = NdData.bosses[d.kind] ?? [:]
        kind = d.kind; name = info["name"] as? String ?? "BOSS"; hint = info["hint"] as? String ?? ""
        w = ndInt(info["w"]); h = ndInt(info["h"])
        hp = d.hp; maxhp = d.hp; lvl = d.lvl; pool = d.pool; cool = d.cool; tele = d.tele; move = d.move
        x = (GW - w) / 2; y = 0
        if kind == "ghost" { x = 15; y = 3 }
    }

    func cells() -> [Int] { (0 ..< h).flatMap { j in (0 ..< w).map { i in (y + j) * GW + x + i } } }
    func center() -> (Int, Int) { (OX + x * C + w * C / 2, OY + y * C + h * C / 2) }
}

// ---------------------------------------------------------------------- the game
final class NoodleSlurp: GameScene {
    override var music: String? { song }
    override var fourWay: Bool { true }
    override var buttonOrder: [Action] { [.a] }
    override var buttons: [Action: String] {
        if overlay != nil { return [.a: "OK"] }
        switch state {
        case "intro", "tally": return [.a: "OK"]
        case "play", "ready": return lv("dash") > 0 ? [.a: "DASH"] : [:]
        default: return [:]
        }
    }

    let mode: String
    let speed: String
    let campaign: Bool
    var song = "noodle"
    var lives: Int
    var up: [String: Int] = [:]
    var nextLife = 30000
    var stageN: Int
    var totalEaten = 0, bestLen = 0
    var feverBoosted = false
    private var cache: Surface?

    private var st: NdStage
    private var kind = "stage", goal = "eat"
    private var target = 0, tier = 0
    private var theme: [String] = []
    private var tiles: [Character] = []
    private var stars: [Int] = []
    private var foods: [Int] = []
    private var feastTotal = 0, starsTotal = 0
    private var link: [Int: Int] = [:]
    private var rollers: [NdRoller] = []
    private var vents: [NdVent] = []
    private var blocks: [Int: Double] = [:]
    private var attacks: [NdAttack] = []
    private var items: [NdItem] = []
    private var boss: NdBoss?
    private var bossSet = Set<Int>()
    private var gatesOpen = true
    private var eatenStage = 0
    private var stageTime = 0.0
    private var deaths = 0, goldSeen = 0, goldMissed = 0, goldEaten = 0, sinceGold = 0
    private var dashCharges = 0, snips = 0
    private var squeezed = 0
    private var pending = Set<Int>()
    private var warnRing = -1
    private var bonusLeft = 20.0
    private var tally: [(String, Int, Int)] = []
    private var tallyI = 0
    private var tallyT = 0.0
    private var lucky = false
    private var victoryT = 0.0
    private var milestone = 0
    private var state = "intro"
    private var stateT = 0.0
    // the noodle
    private var body: [Int] = []
    private var dir = (1, 0)
    private var queue: [(Int, Int)] = []
    private var grow = 0
    private var stepT = 0.0, slurp = 0.0
    private var ghostT = 0.0, dashT = 0.0, magnetT = 0.0, invuln = 0.0
    private var dead = false

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        var m = opt["mode"] ?? "campaign"
        if !["campaign", "classic", "wrap"].contains(m) { m = "campaign" }
        mode = m
        var sp = opt["speed"] ?? "normal"
        if STEP[sp] == nil { sp = "normal" }
        speed = sp
        campaign = m == "campaign"
        lives = campaign ? 3 : 1
        stageN = campaign ? max(1, min(STAGES, Int(opt["start"] ?? "1") ?? 1)) : 0
        st = endlessStage(sp)
        super.init(app, info, opt)
        beginStage()
    }

    func lv(_ id: String) -> Int { up[id] ?? 0 }

    // ---------------------------------------------------------------- stage setup
    private func beginStage() {
        if campaign && stageN - 1 < NdData.stages.count {
            st = NdData.stages[stageN - 1]
            reached(stageN)
        } else {
            st = endlessStage(speed)
        }
        kind = st.kind
        goal = st.goal; target = st.target
        tier = max(0, (stageN - 1) / 10)
        theme = NdData.themes[min(st.theme, NdData.themes.count - 1)]
        tiles = st.map
        stars = tiles.indices.filter { tiles[$0] == "*" }
        foods = tiles.indices.filter { tiles[$0] == "d" }
        feastTotal = foods.count
        for c in stars + foods { tiles[c] = "." }
        starsTotal = stars.count
        link = portalMap(tiles)
        rollers = st.rollers.map { NdRoller(Int($0[0]), Int($0[1]), Int($0[2]), Int($0[3]), $0[4]) }
        vents = st.vents.map { NdVent(Int($0[0]), Int($0[1]), Int($0[2]), Int($0[3]), Int($0[4]), $0[5], $0[6]) }
        blocks = [:]
        attacks = []
        items = []
        boss = (kind == "boss" && st.boss != nil) ? NdBoss(st.boss!) : nil
        bossSet = (boss != nil && boss!.kind != "ghost") ? Set(boss!.cells()) : []
        gatesOpen = !tiles.contains("G")
        eatenStage = 0
        stageTime = 0
        deaths = 0
        goldSeen = 0; goldMissed = 0; goldEaten = 0
        sinceGold = 0
        dashCharges = lv("dash")
        snips = lv("snip")
        squeezed = 0
        pending = []
        warnRing = -1
        bonusLeft = 20
        tally = []
        tallyI = 0
        tallyT = 0
        lucky = false
        victoryT = 0
        milestone = 0
        spawnNoodle()
        fillFoods()
        state = "intro"
        stateT = 0
        cache = nil
        if kind == "boss" {
            song = "boss"
            app.audio.music("boss")
            app.audio.play("warning")
        } else {
            song = kind == "bonus" ? "bonus" : "noodle"
            app.audio.music(song)
            app.audio.play("stage")
        }
    }

    private func spawnNoodle() {
        let (x, y) = st.sp
        body = (0 ..< st.len).map { y * GW + x - $0 }
        for c in body { blocks[c] = nil }
        dir = (1, 0)
        queue = []
        grow = 0
        stepT = 0; slurp = 0
        ghostT = 0; dashT = 0; magnetT = 0
        invuln = 0
        dead = false
    }

    // ---------------------------------------------------------------- queries
    private var head: Int { body[0] }

    private func solid(_ c: Int) -> Bool {
        let ch = tiles[c]
        return ch == "#" || ch == "G" || blocks[c] != nil || bossSet.contains(c)
    }

    private func safe() -> Bool {
        invuln > 0 || ghostT > 0 || dashT > 0 || state == "bossdown" || state == "victory"
    }

    private func rollerAt(_ c: Int) -> NdRoller? { rollers.first { $0.alive && $0.cell == c } }

    /// Something that hurts the head on this cell right now (besides walls and the body).
    private func deadly(_ c: Int) -> Bool {
        if let r = rollerAt(c), r.kind != "gold" { return true }
        for v in vents where v.beam.contains(c) && v.state(stageTime) == 2 { return true }
        for a in attacks where (a.kind == "row" || a.kind == "col") && a.live && a.cells.contains(c) { return true }
        if let b = boss, b.kind == "ghost", !b.dead, b.cells().contains(c) { return true }
        return false
    }

    private func magnetR() -> Int {
        var r = lv("magnet") + (magnetT > 0 ? 2 : 0)
        if hype.feverOn { r += 2 }
        return r
    }

    private func stepTime() -> Double {
        var s: Double
        if campaign {
            s = st.step * (SPEED_MULT[speed] ?? 1) - min(0.012, Double(eatenStage) * 0.0006)
        } else {
            s = (STEP[speed] ?? 0.115) - min(0.06, Double(totalEaten) * 0.0015)
        }
        s *= 1 - 0.07 * Double(lv("calm"))
        if dashT > 0 { s /= 3 }
        return max(0.045, s)
    }

    /// Cells the noodle can currently get to (for spawning food it can actually eat).
    private func reachCells() -> Set<Int> {
        var seen: Set<Int> = [head]
        var stack = [head]
        let wrap = mode == "wrap"
        while let c = stack.popLast() {
            let (x, y) = cxy(c)
            for (dx, dy) in D4 {
                var nx = x + dx, ny = y + dy
                if wrap { nx = ndImod(nx, GW); ny = ndImod(ny, GH) } else if !(0 ..< GW).contains(nx) || !(0 ..< GH).contains(ny) { continue }
                let n = ny * GW + nx
                if seen.contains(n) || solid(n) || pending.contains(n) { continue }
                seen.insert(n)
                stack.append(n)
                if let l = link[n], !seen.contains(l) { seen.insert(l); stack.append(l) }
            }
        }
        return seen
    }

    private func freeCell(near: (Int, Int, Int)? = nil, far: Int = 3, region: Set<Int>? = nil) -> Int? {
        let reg = region ?? reachCells()
        var taken = Set(body).union(foods).union(stars).union(items.map { $0.cell })
        taken.formUnion(rollers.map { $0.cell })
        for v in vents { taken.formUnion(v.beam) }
        for a in attacks where a.kind == "drop" || a.kind == "toss" { taken.formUnion(a.cells) }
        let (hx, hy) = cxy(head)
        var cand: [Int] = []
        for c in reg {
            if taken.contains(c) || (tiles[c] != "." && tiles[c] != "~") || pending.contains(c) || ringOf(c) <= warnRing { continue }
            let (x, y) = cxy(c)
            if abs(x - hx) + abs(y - hy) < far { continue }
            if let n = near, abs(x - n.0) + abs(y - n.1) > n.2 { continue }
            cand.append(c)
        }
        return cand.randomElement()
    }

    private func fillFoods() {
        if kind == "bonus" { return }
        let want = st.foods + (hype.feverOn ? 2 : 0)
        var region: Set<Int>?
        while foods.count < want {
            if region == nil { region = reachCells() }
            guard let c = freeCell(region: region) else { break }
            foods.append(c)
        }
    }

    @discardableResult
    private func addItem(_ kind: String, _ life: Double = -1, _ look: String = "", cell: Int? = nil) -> NdItem? {
        guard let c = cell ?? freeCell() else { return nil }
        let it = NdItem(kind, c, life, look)
        items.append(it)
        return it
    }

    // ---------------------------------------------------------------- frame
    override func tick(_ dt: Double) {
        let inp = app.input
        stateT += dt
        slurp = max(0, slurp - dt)
        if ["intro", "ready", "play", "bossdown", "victory"].contains(state) {
            for (a, d) in DIRS where inp.hit(a) && queue.count < 3 {
                let last = queue.last ?? dir
                if d != last && d != (-last.0, -last.1) { queue.append(d) }
            }
        }
        updateFever()
        if score >= nextLife {
            lives += 1
            nextLife = nextLife < 80000 ? 80000 : nextLife + 100000
            hype.banner("BONUS LIFE!", "+1 NOODLE", color: "pink", dur: 1.6, sound: "extra")
            hype.shower(24, "hearts")
        }
        switch state {
        case "intro":
            let dur = kind == "boss" ? 4.2 : 2.2
            if stateT >= dur || (stateT > 0.6 && inp.hit(.a, .start)) { goPlay() }
        case "ready":
            if stateT >= 0.9 { state = "play" }
        case "play", "bossdown", "victory":
            play(dt, inp)
        case "dead":
            if stateT >= 1.5 {
                if lives > 0 {
                    spawnNoodle()
                    invuln = 2.2
                    state = "ready"; stateT = 0
                } else {
                    state = "over"
                    hype.banner("GAME OVER", "THANKS FOR SLURPING!", color: "pink", dur: 1.6)
                    endGame(false, campaign ? "STAGE \(stageN)" : "LENGTH \(bestLen)", delay: 1.4)
                }
            }
        case "clear":
            if stateT >= 1.6 { state = "tally"; stateT = 0 }
        case "tally":
            updateTally(dt, inp)
        default:
            break
        }
    }

    private func goPlay() {
        state = "play"; stateT = 0
        if kind == "boss" { hype.banner("FIGHT!", color: "red", dur: 0.9, scale: 2) } else { hype.banner("GO!", color: "lime", dur: 0.7, scale: 2) }
    }

    private func updateFever() {
        if hype.feverOn && !feverBoosted {
            feverBoosted = true
            hype.feverT += 2.0 * Double(lv("fever"))
            fillFoods()
        } else if !hype.feverOn {
            feverBoosted = false
        }
    }

    private func play(_ dt: Double, _ inp: Input) {
        stageTime += dt
        ghostT = max(0, ghostT - dt); dashT = max(0, dashT - dt); magnetT = max(0, magnetT - dt); invuln = max(0, invuln - dt)
        if inp.hit(.a) && state == "play" && dashCharges > 0 && dashT <= 0 {
            dashCharges -= 1
            dashT = 0.6
            app.audio.play("jump")
            hype.banner("DASH!", color: "yellow", dur: 0.5, scale: 1)
        }
        // timed things
        for it in items {
            it.t += dt
            if it.life > 0 {
                it.life -= dt
                if it.life <= 0 {
                    if it.kind == "gold" || it.kind == "fortune" { goldMissed += 1 }
                    let (x, y) = cpx(it.cell)
                    parts.burst(Double(x + 4), Double(y + 4), 5, ["white", "gray"], 30, 0.4)
                }
            }
        }
        items.removeAll { !($0.life == -1 || $0.life > 0) }
        for c in Array(blocks.keys) {
            blocks[c]! -= dt
            if blocks[c]! <= 0 {
                blocks[c] = nil
                let (x, y) = cpx(c)
                parts.burst(Double(x + 4), Double(y + 4), 4, ["white", "cream"], 30, 0.4)
            }
        }
        for v in vents where v.life > 0 { v.life -= dt }
        vents.removeAll { !($0.life == -1 || $0.life > 0) }
        updateRollers(dt)
        updateAttacks(dt)
        if boss != nil { updateBoss(dt) }
        if !st.squeeze.isEmpty { updateSqueeze() }
        if state == "victory" {
            victoryT -= dt
            if victoryT <= 0 { stageClear(); return }
        }
        if state == "bossdown" && stateT >= 1.6 { bossFeast() }
        if kind == "bonus" && state == "play" {
            bonusLeft -= dt
            if goal == "rush" {
                let golds = items.filter { $0.kind == "gold" || $0.kind == "fortune" }.count
                if golds < 3 && Int(stageTime * 10) % 4 == 0 {
                    addItem(hype.lucky(0.06) ? "fortune" : "gold", 3.2)
                }
            }
            if bonusLeft <= 0 {
                bonusLeft = 0
                hype.banner("TIME UP!", color: "yellow", dur: 1.2)
                stageClear()
                return
            }
        }
        stepT += dt
        var guardN = 0
        while stepT >= stepTime() && ["play", "bossdown", "victory"].contains(state) && guardN < 4 && !dead {
            stepT -= stepTime()
            guardN += 1
            advance()
        }
        if ["play", "bossdown", "victory"].contains(state) && !safe() && deadly(head) { crash() }
        if state == "play" {
            fillFoods()
            checkGoal()
        }
    }

    // ---------------------------------------------------------------- movement
    private func advance() {
        let au = app.audio
        let h = head
        let on = tiles[h]
        if let d = ARROWS[on] {
            if d != (-dir.0, -dir.1) { dir = d }
        } else if on != "~" && !queue.isEmpty {
            dir = queue.removeFirst()
        }
        let (hx, hy) = cxy(h)
        var nx = hx + dir.0, ny = hy + dir.1
        if mode == "wrap" { nx = ndImod(nx, GW); ny = ndImod(ny, GH) }
        if !(0 ..< GW).contains(nx) || !(0 ..< GH).contains(ny) { crash(); return }
        var c = ny * GW + nx
        if let l = link[c] {
            c = l
            let (x, y) = cpx(c)
            parts.burst(Double(x + 4), Double(y + 4), 8, PORTAL_COLORS[tiles[c]] ?? ["white"], 40, 0.4)
            au.play("bubble")
        }
        if solid(c) { crash(); return }
        let check = grow == 0 ? Array(body.dropLast()) : body
        if check.contains(c) {
            let i = body.firstIndex(of: c)!
            let ghostN = 4 * lv("ghost")
            if ghostT > 0 || (ghostN > 0 && i >= body.count - ghostN) {
                // ghost noodle: slip through
            } else if snips > 0 && i >= 2 {
                snips -= 1
                let cut = body[i...]
                body = Array(body[..<i])
                for k in cut {
                    let (x, y) = cpx(k)
                    parts.burst(Double(x + 4), Double(y + 4), 2, ["cream", "white", "pink"], 40, 0.5)
                }
                au.play("pop")
                hype.banner("SNIP!", color: "pink", dur: 0.6, scale: 1)
            } else {
                crash(); return
            }
        }
        if let gp = rollerAt(c), gp.kind == "gold" {
            gp.alive = false
            bossHit(c)
        } else if !safe() && deadly(c) {
            crash(); return
        }
        body.insert(c, at: 0)
        if grow > 0 { grow -= 1 } else { body.removeLast() }
        bestLen = max(bestLen, body.count)
        if dashT > 0 {
            let (x, y) = cpx(c)
            parts.burst(Double(x + 4), Double(y + 4), 2, ["yellow", "white"], 20, 0.3, grav: 0)
        }
        eatAt(c, false)
        let r = magnetR()
        if r > 0 {
            let (hx2, hy2) = cxy(c)
            for k in foods + items.filter({ ["gold", "fortune", "weak"].contains($0.kind) }).map({ $0.cell }) {
                let (x, y) = cxy(k)
                let d = abs(x - hx2) + abs(y - hy2)
                if d > 0 && d <= r { eatAt(k, true) }
            }
        }
        checkLength()
        if let b = boss, b.kind == "ghost" { checkTrap() }
    }

    private func eatAt(_ c: Int, _ pulled: Bool) {
        let au = app.audio
        let (x, y) = cpx(c)
        let fx = Double(x + 4), fy = Double(y - 4)
        if pulled {
            let (hx, hy) = cpx(head)
            for k in 0 ..< 4 {
                let u = Double(k) / 4
                parts.sparkle(Double(x + 4) + Double(hx - x) * u, Double(y + 4) + Double(hy - y) * u, "pink")
            }
        }
        if let i = foods.firstIndex(of: c) {
            foods.remove(at: i)
            eatDumpling(c)
        }
        for it in items.filter({ $0.cell == c }) {
            items.removeAll { $0 === it }
            switch it.kind {
            case "gold":
                goldEaten += 1
                grow += 3
                slurp = 0.4
                hype.hit(2, fever: 0.15 * (1 + 0.35 * Double(lv("fever"))))
                hype.comboT += 0.6 * Double(lv("combo"))
                let base = goal == "rush" ? 150 + hype.comboBonus(5) : 200 + 30 * tier
                add(base, fx, fy, "mint")
                au.play("bonus")
                parts.burst(Double(x + 4), Double(y + 4), 14, ["yellow", "white", "orange"], 60, 0.7)
                if goal == "rush" { eatenStage += 1 }
            case "fortune":
                goldEaten += 1
                grow += 3
                hype.hit(3)
                hype.jackpot(1500 + 300 * tier, sub: "FORTUNE DUMPLING!")
                if goal == "rush" { eatenStage += 1 }
            case "tea":
                ghostT = 5
                au.play("powerup")
                add(50, fx, fy, "lavender")
                hype.banner("GHOST TEA!", "PASS THROUGH ANYTHING", color: "lavender", dur: 1.1, scale: 1)
            case "chili":
                au.play("powerup")
                add(50, fx, fy, "orange")
                hype.banner("HOT CHILI!", "FEVER UP", color: "orange", dur: 1.0, scale: 1)
                hype.feverAdd(0.5)
            case "magnet":
                magnetT = 8
                au.play("powerup")
                add(50, fx, fy, "red")
                hype.banner("MAGNET!", color: "red", dur: 1.0, scale: 1)
            case "weak":
                bossHit(c)
            default:
                break
            }
        }
        if let i = stars.firstIndex(of: c) {
            stars.remove(at: i)
            hype.hit(1, fever: 0.08 * (1 + 0.35 * Double(lv("fever"))))
            hype.comboT += 0.6 * Double(lv("combo"))
            add(100 + 20 * tier, fx, fy, "orange")
            au.play("fruit")
            parts.burst(Double(x + 4), Double(y + 4), 12, ["red", "orange", "yellow"], 60, 0.6)
            let left = stars.count
            if left > 0 && left <= 2 { floats.add(Double(W / 2), Double(OY + 70), "\(left) MORE!", "orange") }
        }
    }

    private func eatDumpling(_ c: Int) {
        let au = app.audio
        let (x, y) = cpx(c)
        eatenStage += 1
        totalEaten += 1
        slurp = 0.25
        hype.hit(1, fever: 0.06 * (1 + 0.35 * Double(lv("fever"))))
        hype.comboT += 0.6 * Double(lv("combo"))
        var pts: Int
        if kind == "bonus" {
            grow += eatenStage % 2 == 0 ? 1 : 0
            pts = 30 + hype.comboBonus(3)
            if foods.isEmpty {
                hype.jackpot(10000, sub: "ALL SLURPED!")
                stageClear()
            }
        } else {
            grow += 2
            pts = (campaign ? 10 + 5 * tier : 10 + totalEaten / 5) + hype.comboBonus(2)
        }
        add(pts, Double(x + 4), Double(y - 4))
        au.play("eat")
        parts.burst(Double(x + 4), Double(y + 4), 5, ["cream", "peach", "white"], 40, 0.4)
        if kind == "bonus" { return }
        // golden / fortune / power-up drops
        sinceGold += 1
        let hasGold = items.contains { $0.kind == "gold" || $0.kind == "fortune" }
        if !hasGold && (sinceGold >= 6 - lv("gold") || Double.random(in: 0 ..< 1) < 0.10 + 0.06 * Double(lv("gold"))) {
            sinceGold = 0
            let it = hype.lucky(0.03) ? addItem("fortune", 5) : addItem("gold", 6 + 2 * Double(lv("goldtime")))
            if it != nil {
                goldSeen += 1
                au.play("bonus")
            }
        }
        if !items.contains(where: { ["tea", "chili", "magnet"].contains($0.kind) }) && Double.random(in: 0 ..< 1) < 0.07 {
            addItem(["tea", "chili", "magnet"].randomElement()!, 8)
        }
        if !gatesOpen && eatenStage >= st.gate { openGates() }
        if !campaign && totalEaten % 25 == 0 {
            pickUpgrade(NdData.pool, up, title: "SNACK BREAK!") { [unowned self] id in self.onPick(id) }
        }
    }

    private func checkLength() {
        let n = body.count
        for m in MILESTONES where n >= m && m > milestone {
            milestone = m
            if m >= 30 || !campaign {
                let pts = add(50 * m)
                hype.banner("LENGTH \(m)!", "+\(pts)", color: "mint", dur: 1.3, sound: "levelup")
                hype.shower(10 + m / 3, "stars")
            }
        }
    }

    private func openGates() {
        gatesOpen = true
        for c in tiles.indices where tiles[c] == "G" {
            tiles[c] = "."
            let (x, y) = cpx(c)
            parts.burst(Double(x + 4), Double(y + 4), 4, ["brown", "yellow", "white"], 50, 0.6)
        }
        cache = nil
        hype.banner("DOORS OPEN!", color: "yellow", dur: 1.2, sound: "levelup")
        app.shake(2, 0.2)
    }

    private func crash() {
        if !["play", "bossdown", "victory"].contains(state) { return }
        let au = app.audio
        if state == "bossdown" || state == "victory" {   // no life lost once the boss is down
            dead = true
            victoryT = min(victoryT, 0.8)
            au.play("hurt")
            return
        }
        dead = true
        au.play("hurt")
        app.shake(3, 0.3)
        hype.breakCombo()
        hype.flash("red", 0.15)
        for c in body {
            let (x, y) = cpx(c)
            parts.burst(Double(x + 4), Double(y + 4), 2, ["cream", "peach", "white"], 50, 0.8)
        }
        if kind == "bonus" {
            hype.banner("OOPS!", "BONUS OVER", color: "pink", dur: 1.2)
            stageClear()
            return
        }
        deaths += 1
        lives -= 1
        state = "dead"; stateT = 0
        attacks.removeAll { $0.kind == "row" || $0.kind == "col" }
    }

    private func checkGoal() {
        var done = false
        switch goal {
        case "eat": done = eatenStage >= target
        case "stars": done = stars.isEmpty
        case "length": done = body.count >= target
        case "survive": done = stageTime >= Double(target)
        default: break
        }
        if done { stageClear() }
    }

    // ---------------------------------------------------------------- hazards
    private func rollerBlocked(_ c: Int, _ me: NdRoller) -> Bool {
        if solid(c) { return true }
        return rollers.contains { $0 !== me && $0.alive && $0.cell == c }
    }

    private func updateRollers(_ dt: Double) {
        let bodyRest = Set(body.dropFirst())
        for r in rollers where r.alive {
            r.spin += dt * 10
            r.acc += dt
            if r.acc < r.period { continue }
            r.acc -= r.period
            let nx = r.x + r.dx, ny = r.y + r.dy
            let ball = r.kind == "ball"
            if !(0 ..< GW).contains(nx) || !(0 ..< GH).contains(ny) {
                if ball { r.dx = -r.dx; r.dy = -r.dy } else { r.alive = false }
                continue
            }
            let c = ny * GW + nx
            if c == head {
                if r.kind == "gold" { r.alive = false; bossHit(c); continue }
                if !safe() { r.x = nx; r.y = ny; crash(); continue }
            }
            if rollerBlocked(c, r) || bodyRest.contains(c) || c == head {
                if ball {
                    r.dx = -r.dx; r.dy = -r.dy
                    let bx = r.x + r.dx, by = r.y + r.dy
                    if (0 ..< GW).contains(bx) && (0 ..< GH).contains(by) && !rollerBlocked(by * GW + bx, r) &&
                        !bodyRest.contains(by * GW + bx) && by * GW + bx != head {
                        r.x = bx; r.y = by
                    }
                } else {
                    r.alive = false
                    let (x, y) = cpx(c)
                    parts.burst(Double(x + 4), Double(y + 4), 8, r.kind != "slip" ? ["white", "red", "yellow"] : ["white", "cream"], 50, 0.5)
                    if bodyRest.contains(c) {
                        add(50, Double(x + 4), Double(y - 4), "white")
                        app.audio.play("brick")
                    }
                }
                continue
            }
            r.x = nx; r.y = ny
        }
        rollers.removeAll { !$0.alive }
    }

    private func updateSqueeze() {
        let t0 = st.squeeze[0], iv = st.squeeze[1]
        let k = squeezed
        if k < 3 {
            let close = t0 + Double(k) * iv
            if stageTime >= close - 2 { warnRing = k }
            if stageTime >= close {
                squeezed += 1
                for c in 0 ..< NCELLS where ringOf(c) == k && tiles[c] != "#" { pending.insert(c) }
                hype.banner("SQUEEZE!", color: "orange", dur: 0.9, scale: 1)
                app.audio.play("lock")
                app.shake(2, 0.2)
            }
        }
        if !pending.isEmpty {
            let bodySet = Set(body)
            let done = pending.filter { !bodySet.contains($0) }
            for c in done {
                pending.remove(c)
                tiles[c] = "#"
                foods.removeAll { $0 == c }
            }
            if !done.isEmpty {
                items.removeAll { done.contains($0.cell) }
                for r in rollers where done.contains(r.cell) { r.alive = false }
                cache = nil
            }
        }
    }

    // ---------------------------------------------------------------- boss
    private func updateBoss(_ dt: Double) {
        guard let b = boss else { return }
        b.t += dt
        b.flash = max(0, b.flash - dt); b.stun = max(0, b.stun - dt); b.inv = max(0, b.inv - dt)
        b.anim = max(0, b.anim - dt); b.lid = max(0, b.lid - dt)
        if b.dead || state != "play" { return }
        if b.kind == "crab" {
            b.moveT += dt
            if b.moveT >= b.move * 1.6 {
                b.moveT = 0
                var nx = b.x + b.mdir
                if nx < 1 || nx + b.w > GW - 1 {
                    b.mdir = -b.mdir
                    nx = b.x + b.mdir
                }
                b.x = nx
                bossSet = Set(b.cells())
                if bossSet.contains(head) && !safe() { crash() }
            }
        } else if b.kind == "ghost" {
            ghostMove(dt)
        }
        let weak = items.contains { $0.kind == "weak" } || attacks.contains { $0.gold >= 0 || $0.kind == "toss" } ||
            rollers.contains { $0.kind == "gold" }
        b.weakWait = weak ? 0 : b.weakWait + dt
        b.cd -= dt * (b.angry ? 1.3 : 1.0)
        if b.cd > 0 || b.stun > 0 { return }
        b.cd = b.cool * (b.angry ? 0.75 : 1.0)
        var name: String
        if b.kind != "ghost" && !weak && (b.weakWait > 3.5 || Double.random(in: 0 ..< 1) < 0.5) {
            name = WEAK_ATTACK[b.kind] ?? "toss"
        } else {
            let opts = b.pool.filter { $0 != b.last }
            name = (opts.isEmpty ? b.pool : opts).randomElement()!
        }
        b.last = name
        b.anim = 0.6
        bossAttack(name)
    }

    private func linesNear(_ n: Int, _ rows: Bool, _ lo: Int, _ hi: Int) -> [Int] {
        let (hx, hy) = cxy(head)
        let target = rows ? hy : hx
        guard lo < hi else { return [] }
        let pool = (lo ..< hi).filter { $0 != target }.shuffled()
        var out: [Int] = []
        if lo <= target && target < hi && Double.random(in: 0 ..< 1) < 0.6 { out.append(target) }
        for k in pool {
            if out.count >= n { break }
            if out.allSatisfy({ abs(k - $0) > 1 }) { out.append(k) }
        }
        return out
    }

    private func bossAttack(_ name: String) {
        guard let b = boss else { return }
        let au = app.audio
        let tele = b.tele
        let top = b.kind != "ghost" ? b.y + b.h : 0
        let style = ["crab": "ladle", "teapot": "steam", "golem": "quake", "bao": "ladle"][b.kind] ?? "ladle"
        let (bx, by) = b.center()
        switch name {
        case "sweep", "quake":
            let n = 1 + (b.angry ? 1 : 0) + (b.lvl >= 2 ? 1 : 0)
            for y in linesNear(n, true, top + 1, GH) {
                attacks.append(NdAttack("row", (0 ..< GW).map { y * GW + $0 }, tele, 0.45, name == "quake" ? "quake" : style))
            }
        case "csweep":
            let n = 1 + (b.angry ? 1 : 0)
            for x in linesNear(n, false, 0, GW) {
                attacks.append(NdAttack("col", (top ..< GH).map { $0 * GW + x }, tele, 0.45, style))
            }
        case "beam":
            let (hx, _) = cxy(head)
            let x0 = max(0, min(GW - 2, hx - (Double.random(in: 0 ..< 1) < 0.5 ? 1 : 0)))
            let cells = (top ..< GH).flatMap { y in [y * GW + x0, y * GW + x0 + 1] }
            attacks.append(NdAttack("col", cells, tele, 1.0, "steam", gold: b.kind == "teapot" ? 1 : -1))
        case "toss":
            let k = 2 + (b.angry ? 1 : 0)
            for _ in 0 ..< k {
                if let c = freeCell(far: 3) { attacks.append(NdAttack("toss", [c], 0.8, src: (bx, by))) }
            }
            au.play("jump")
        case "drop":
            let k = 4 + 2 * b.lvl + (b.angry ? 2 : 0)
            let (hx, hy) = cxy(head)
            var cells: [Int] = []
            for i in 0 ..< k {
                if let c = freeCell(near: i % 2 == 0 ? (hx, hy, 5) : nil, far: 2), !cells.contains(c) { cells.append(c) }
            }
            if !cells.isEmpty {
                let gold = b.kind == "golem" ? Int.random(in: 0 ..< cells.count) : -1
                attacks.append(NdAttack("drop", cells, tele + 0.25, gold: gold))
            }
        case "plates":
            let k = 2 + b.lvl + (b.angry ? 1 : 0)
            let rows = linesNear(k, true, top + 1, GH)
            let golds = (b.kind == "sushi" || b.kind == "bao") ? 1 : 0
            for (i, y) in rows.enumerated() {
                var cell: Int, dx: Int, dy: Int
                if b.kind == "sushi" && b.lvl >= 1 && i % 2 == 1 {
                    let x = Int.random(in: 0 ..< GW)
                    cell = (GH - 1) * GW + x; dx = 0; dy = -1
                } else {
                    let left = Double.random(in: 0 ..< 1) < 0.5
                    cell = y * GW + (left ? 0 : GW - 1); dx = left ? 1 : -1; dy = 0
                }
                attacks.append(NdAttack("plate", [cell], 0.9 + Double(i) * 0.35, dx: dx, dy: dy, gold: i < golds ? 1 : -1))
            }
        case "vents":
            let k = 2 + (b.angry ? 1 : 0)
            for _ in 0 ..< k {
                guard let c = freeCell(far: 4) else { continue }
                let (x, y) = cxy(c)
                let (dx, dy) = D4.randomElement()!
                var ln = 0
                while ln < 3 && (0 ..< GW).contains(x + dx * (ln + 1)) && (0 ..< GH).contains(y + dy * (ln + 1)) &&
                    !solid((y + dy * (ln + 1)) * GW + x + dx * (ln + 1)) { ln += 1 }
                if ln >= 1 { vents.append(NdVent(x, y, dx, dy, ln, 2.4, 0.4 - ndPmod(stageTime, 2.4), 7.5)) }
            }
        case "dash":
            let (hx, hy) = cxy(head)
            let dx = abs(hx - b.x) >= abs(hy - b.y) ? (hx > b.x ? 1 : -1) : 0
            let dy = dx != 0 ? 0 : (hy > b.y ? 1 : -1)
            var cells: [Int] = []
            var x = b.x, y = b.y
            for _ in 0 ..< 6 {
                x += dx; y += dy
                if !(0 ... GW - b.w).contains(x) || !(0 ... GH - b.h).contains(y) { break }
                for j in 0 ..< b.h { for i in 0 ..< b.w { cells.append((y + j) * GW + x + i) } }
            }
            attacks.append(NdAttack("dash", cells, 0.75, dx: dx, dy: dy))
        case "slips":
            for (dx, dy) in D4 {
                let x = b.x + (dx > 0 ? b.w : dx < 0 ? -1 : 0)
                let y = b.y + (dy > 0 ? b.h : dy < 0 ? -1 : 0)
                if (0 ..< GW).contains(x) && (0 ..< GH).contains(y) {
                    attacks.append(NdAttack("plate", [y * GW + x], 0.5, dx: dx, dy: dy, gold: -2))
                }
            }
        default:
            break
        }
    }

    private func updateAttacks(_ dt: Double) {
        let au = app.audio
        var keep: [NdAttack] = []
        for a in attacks {
            a.t += dt
            if a.kind == "row" || a.kind == "col" {
                if a.t >= a.tele && !a.fired {
                    a.fired = true
                    au.play(a.style == "ladle" ? "shoot" : a.style == "quake" ? "explode" : "bubble")
                    if a.style == "quake" { app.shake(2, 0.2) }
                }
                if a.t >= a.tele + a.act {
                    if a.gold >= 0, let b = boss, !b.dead { spawnSugar() }
                    continue
                }
            } else if a.kind == "toss" && a.t >= a.tele {
                let c = a.cells[0]
                if c == head && !safe() { crash() }
                items.append(NdItem("weak", c, 9, WEAK_LOOK[boss?.kind ?? "crab"] ?? "chili"))
                foods.removeAll { $0 == c }
                continue
            } else if a.kind == "drop" && a.t >= a.tele {
                let bodyRest = Set(body.dropFirst())
                for (i, c) in a.cells.enumerated() {
                    let (x, y) = cpx(c)
                    if i == a.gold { items.append(NdItem("weak", c, 7, "bean")); continue }
                    if c == head && !safe() { crash() }
                    if bodyRest.contains(c) || c == head {
                        parts.burst(Double(x + 4), Double(y + 4), 6, ["white", "cream"], 40, 0.4)
                        continue
                    }
                    blocks[c] = 6
                    foods.removeAll { $0 == c }
                    items.removeAll { $0.cell == c }
                    parts.burst(Double(x + 4), Double(y + 7), 4, ["white", "gray"], 30, 0.3)
                }
                au.play("lock")
                app.shake(2, 0.15)
                continue
            } else if a.kind == "plate" && a.t >= a.tele {
                let (x, y) = cxy(a.cells[0])
                let k = a.gold == 1 ? "gold" : a.gold == -2 ? "slip" : "plate"
                let r = NdRoller(x, y, a.dx, a.dy, k != "slip" ? max(0.07, 0.12 - 0.002 * Double(tier)) : 0.13, k)
                if a.cells[0] == head {
                    if k == "gold" { bossHit(a.cells[0]); continue }
                    if !safe() { crash() }
                }
                rollers.append(r)
                au.play("shoot")
                continue
            } else if a.kind == "dash" && a.t >= a.tele {
                if let b = boss { b.dash = 6; b.ddx = a.dx; b.ddy = a.dy; b.moveT = 0 }
                continue
            }
            keep.append(a)
        }
        attacks = keep
    }

    private func spawnSugar() {
        guard let b = boss else { return }
        let cx = b.x + b.w / 2
        guard let c = freeCell(near: (cx, b.y + b.h + 2, 4), far: 2) ?? freeCell(far: 2) else { return }
        items.append(NdItem("weak", c, 4.5 + Double(b.lvl) * 0.5, "sugar"))
        b.lid = 4.5
        let (x, y) = cpx(c)
        parts.burst(Double(x + 4), Double(y + 4), 10, ["white", "sky"], 40, 0.5)
        app.audio.play("pop")
    }

    private func ghostMove(_ dt: Double) {
        guard let b = boss, b.stun <= 0 else { return }
        b.moveT += dt
        let period = b.dash > 0 ? 0.05 : b.move * (b.angry ? 0.75 : 1.0)
        if b.moveT < period { return }
        b.moveT = 0
        let bodyRest = Set(body.dropFirst())
        let (hx, hy) = cxy(head)
        func fits(_ x: Int, _ y: Int) -> Bool {
            if !(0 ... GW - b.w).contains(x) || !(0 ... GH - b.h).contains(y) { return false }
            for j in 0 ..< b.h { for i in 0 ..< b.w where bodyRest.contains((y + j) * GW + x + i) { return false } }
            return true
        }
        var nx: Int, ny: Int
        if b.dash > 0 {
            b.dash -= 1
            nx = b.x + b.ddx; ny = b.y + b.ddy
            if !fits(nx, ny) { b.dash = 0; return }
        } else {
            var best: (Double, Int, Int)?
            for (dx, dy) in D4 where fits(b.x + dx, b.y + dy) {
                let cx = Double(b.x + dx) + 0.5, cy = Double(b.y + dy) + 0.5
                let score = abs(cx - Double(hx)) + abs(cy - Double(hy)) + Double.random(in: 0 ..< 1.5)
                if best == nil || score < best!.0 { best = (score, dx, dy) }
            }
            guard let m = best else { return }
            nx = b.x + m.1; ny = b.y + m.2
        }
        b.x = nx; b.y = ny
        if b.cells().contains(head) && !safe() { crash(); return }
        checkTrap()
    }

    /// FORTUNE SPOOK: hurt it by sealing it in with the noodle (board edges count as walls).
    private func checkTrap() {
        guard let b = boss, !b.dead, b.inv <= 0, b.stun <= 0 else { return }
        let bodySet = Set(body)
        let start = b.cells().filter { !bodySet.contains($0) }
        var seen = Set(start)
        var stack = start
        while seen.count <= 70, let c = stack.popLast() {
            let (x, y) = cxy(c)
            for (dx, dy) in D4 {
                let nx = x + dx, ny = y + dy
                if (0 ..< GW).contains(nx) && (0 ..< GH).contains(ny) {
                    let n = ny * GW + nx
                    if !seen.contains(n) && !bodySet.contains(n) { seen.insert(n); stack.append(n) }
                }
            }
        }
        if seen.count <= 70 {
            b.stun = 1.2
            b.inv = 2.6
            bossHit(b.y * GW + b.x)
            hype.banner("TRAPPED!", color: "lavender", dur: 0.9, scale: 1)
        }
    }

    private func ghostWarp() {
        guard let b = boss else { return }
        let bodySet = Set(body)
        let (hx, hy) = cxy(head)
        var best: (Int, Int, Int)?
        for _ in 0 ..< 40 {
            let x = Int.random(in: 0 ..< GW - 1), y = Int.random(in: 0 ..< GH - 1)
            var hit = false
            for j in 0 ..< 2 { for i in 0 ..< 2 where bodySet.contains((y + j) * GW + x + i) { hit = true } }
            if hit { continue }
            let d = abs(x - hx) + abs(y - hy)
            if best == nil || d > best!.0 { best = (d, x, y) }
        }
        if let m = best {
            let (px, py) = b.center()
            parts.burst(Double(px), Double(py), 16, ["white", "lavender", "yellow"], 60, 0.6)
            b.x = m.1; b.y = m.2
        }
    }

    private func bossHit(_ c: Int) {
        guard let b = boss, !b.dead else { return }
        b.hp -= 1
        b.flash = 0.25
        let (x, y) = cpx(c)
        add(500, Double(x + 4), Double(y - 4), "red")
        hype.hit(2)
        hype.flash("white", 0.12)
        hype.hitstop(0.08)
        app.shake(3, 0.25)
        app.audio.play("explode")
        let (bx, by) = b.center()
        parts.burst(Double(bx), Double(by), 18, ["white", "yellow", "red", "orange"], 80, 0.7)
        if b.kind == "ghost" && b.hp > 0 { ghostWarp() }
        if b.hp <= b.maxhp / 2 && !b.angry && b.hp > 0 {
            b.angry = true
            hype.banner("IT'S ANGRY!", color: "red", dur: 1.0, scale: 1)
        }
        if b.hp <= 0 { bossDefeat() }
    }

    private func bossDefeat() {
        guard let b = boss else { return }
        b.dead = true
        b.hp = 0
        attacks = []
        rollers = []
        vents = []
        blocks = [:]
        items.removeAll { $0.kind == "weak" }
        app.audio.play("bossdown")
        hype.slowmo(0.3, 1.4)
        hype.flash("white", 0.4)
        hype.shower(70, "stars")
        hype.banner("BOSS DOWN!!", b.name, dur: 2.2, rainbow: true)
        app.shake(6, 0.9)
        state = "bossdown"; stateT = 0
        cache = nil
    }

    /// The defeated boss bursts into golden dumplings - slurp as many as you can!
    private func bossFeast() {
        guard let b = boss else { return }
        let (bx, by) = b.center()
        parts.burst(Double(bx), Double(by), 40, ["yellow", "white", "orange", "pink"], 110, 1.0)
        bossSet = []
        let region = reachCells()
        for _ in 0 ..< 12 {
            guard let c = freeCell(near: (b.x + b.w / 2, b.y + b.h / 2, 8), far: 2, region: region) else { break }
            items.append(NdItem("gold", c, 5))
        }
        state = "victory"; stateT = 0
        victoryT = dead ? 0.8 : 5.0
        hype.banner("GOLDEN FEAST!", "SLURP THEM UP!", color: "yellow", dur: 1.4, scale: 1)
        app.audio.play("coin")
    }

    // ---------------------------------------------------------------- clear / tally
    private func stageClear() {
        if ["clear", "tally", "pick", "over"].contains(state) { return }
        state = "clear"; stateT = 0
        let t = tier
        var lines: [(String, Int)] = []
        if kind == "stage" {
            lines.append(("CLEAR BONUS", 500 + 100 * t))
            if goal == "survive" {
                lines.append(("DUMPLINGS", 50 * eatenStage))
            } else {
                lines.append(("TIME BONUS", max(0, Int(st.par - stageTime)) * (20 + 5 * t)))
            }
            lines.append(("NO MISS", deaths == 0 ? 1000 + 200 * t : 0))
            let perfect = deaths == 0 && goldMissed == 0 && goldSeen > 0
            lines.append(("PERFECT!", perfect ? 3000 + 500 * t : 0))
            hype.banner("STAGE CLEAR!", dur: 1.5, rainbow: true, sound: "win")
            hype.shower(40, "confetti")
        } else if kind == "boss" {
            lines.append(("BOSS BONUS", 10000 * (1 + (boss?.lvl ?? 0))))
            lines.append(("TIME BONUS", max(0, Int(st.par - stageTime)) * 50))
            lines.append(("NO MISS", deaths == 0 ? 5000 + 1000 * t : 0))
            lines.append(("GOLD SLURPED", 300 * goldEaten))
            app.audio.play("win")
        } else if kind == "bonus" {
            if goal == "feast" {
                let got = feastTotal - foods.count
                lines.append(("SLURPED \(got)/\(feastTotal)", 100 * got))
                lines.append(("ALL SLURPED!", foods.isEmpty ? 10000 : 0))
            } else {
                lines.append(("GOLDEN X\(eatenStage)", 300 * eatenStage))
            }
            lines.append(("BEST COMBO", 50 * hype.bestCombo))
            if !dead { app.audio.play("win") }
        } else {
            endGame(false, "LENGTH \(bestLen)")
            return
        }
        lucky = campaign && hype.lucky(0.03)
        if lucky { lines = lines.map { ($0.0, $0.1 * 3) } }
        tally = lines.map { ($0.0, $0.1, 0) }
        tallyI = 0
        tallyT = 0
        attacks = []
    }

    private func updateTally(_ dt: Double, _ inp: Input) {
        let fast = inp.hit(.a, .start)
        if stateT < 0.3 { return }
        if lucky && tallyI == 0 && tallyT == 0 { hype.jackpot(0, sub: "LUCKY BOWL! X3") }
        tallyT += dt
        if tallyI < tally.count {
            var ln = tally[tallyI]
            var step = max(1, ln.1 / 25)
            if fast { step = ln.1 }
            if ln.2 < ln.1 {
                let d = min(step, ln.1 - ln.2)
                ln.2 += d
                score += d
                if Int(tallyT * 30) % 3 == 0 { app.audio.play("move") }
            }
            tally[tallyI] = ln
            if ln.2 >= ln.1 {
                tallyI += 1
                tallyT = 0
                if ln.1 > 0 { app.audio.play("coin") }
            }
            return
        }
        if tallyT > 1.2 || (fast && tallyT > 0.2) { afterTally() }
    }

    private func afterTally() {
        if (kind == "boss" || kind == "bonus") && stageN < STAGES {
            state = "pick"
            pickUpgrade(NdData.pool, up, title: kind == "boss" ? "POWER UP!" : "BONUS PRIZE!") { [unowned self] id in self.onPick(id) }
        } else {
            nextStage()
        }
    }

    private func onPick(_ id: String?) {
        if let id = id {
            up[id, default: 0] += 1
            if id == "life" { lives += 1 }
            if id == "dash" { dashCharges += 1 }
            if id == "snip" { snips += 1 }
        }
        if campaign && state == "pick" { nextStage() }
    }

    private func nextStage() {
        if stageN >= STAGES {
            state = "over"
            hype.jackpot(100000, sub: "ALL 200 STAGES!")
            endGame(true, "ALL 200 STAGES CLEAR!", delay: 4.0)
            return
        }
        stageN += 1
        beginStage()
    }

    // ---------------------------------------------------------------- drawing
    override func render(_ s: Surface) {
        if cache == nil { cache = buildCache() }
        s.blit(cache!, 0, 0)
        let t = self.t
        drawTiles(s, t)
        drawAttacks(s, t, false)
        let shade = col(theme[6])
        for c in foods {
            let (x, y) = cpx(c)
            s.fillRect(shade, x + 1, y + 7, 6, 1)
            Cute.dumpling(s, x, y - Int(abs(sin(t * 5 + Double(c)))), t: t)
        }
        for c in stars {
            let (x, y) = cpx(c)
            let bob = Int(sin(t * 4 + Double(c) * 0.7))
            s.fillRect(shade, x + 1, y + 7, 6, 1)
            s.blit(sprite("star", remap: ["y": Int(t * 4 + Double(c)) % 4 != 0 ? "r" : "o"]), x, y + bob)
            if Int(t * 3 + Double(c)) % 5 == 0 { s.fillRect(col("white"), x + 6, y + bob, 1, 1) }
        }
        for it in items { drawItem(s, it, t) }
        for r in rollers { drawRoller(s, r, t) }
        drawNoodle(s)
        if boss != nil { drawBoss(s, t) }
        drawAttacks(s, t, true)
        parts.draw(s)
        floats.draw(s)
        drawHud(s, t)
        if state == "intro" {
            drawIntro(s, t)
        } else if state == "ready" && Int(t * 6) % 2 == 0 {
            drawText(s, "READY?", W / 2, OY + 64, "yellow", scale: 2, align: .center, outline: "ink")
        } else if state == "tally" {
            drawTally(s, t)
        }
    }

    private func buildCache() -> Surface {
        let th = theme
        let surf = Surface(W, H)
        surf.fill(col(th[1]))
        var rng = SeededRNG(UInt64(stageN * 31 + 7))
        let deco = col(th[2])
        for i in 0 ..< 70 {
            let x = Int.random(in: 0 ..< W, using: &rng), y = Int.random(in: 0 ..< H, using: &rng)
            if OX - 6 < x && x < OX + GW * C + 6 && OY - 6 < y && y < OY + GH * C + 6 { continue }
            switch i % 3 {
            case 0: surf.fillRect(deco, x, y, 2, 2)
            case 1: surf.fillRect(deco, x, y, 1, 1)
            default: surf.fillRect(deco, x - 1, y, 3, 1); surf.fillRect(deco, x, y - 1, 1, 3)
            }
        }
        // dark HUD bands keep the score row and the goal row readable on every theme
        surf.fillRect(col("black"), 0, 0, W, 13)
        surf.fillRect(deco, 0, 13, W, 1)
        surf.fillRect(col("black"), 0, OY + GH * C + 4, W, H - (OY + GH * C + 4))
        surf.fillRect(deco, 0, OY + GH * C + 4, W, 1)
        panel(surf, IRect(OX - 3, OY - 3, GW * C + 6, GH * C + 6), fill: th[3], border: th[5], radius: 3)
        let fb = col(th[4])
        for y in 0 ..< GH { for x in 0 ..< GW where (x / 2 + y / 2) % 2 == 0 { surf.fillRect(fb, OX + x * C, OY + y * C, C, C) } }
        let wall = col(th[5]), shade = col(th[6]), acc = col(th[7])
        for (c, ch) in tiles.enumerated() {
            let (x, y) = cpx(c)
            let (gx, gy) = cxy(c)
            switch ch {
            case "#":
                surf.fillRect(wall, x, y, C, C)
                if gy + 1 >= GH || tiles[c + GW] != "#" { surf.fillRect(shade, x, y + C - 2, C, 2) }
                if gy == 0 || tiles[c - GW] != "#" { surf.fillRect(acc, x, y, C, 1) }
                if (gx + gy) % 3 == 0 { surf.fillRect(shade, x + 2, y + 3, 1, 1) }
            case "G":
                surf.fillRect(col("brown"), x, y, C, C)
                surf.fillRect(col("choco"), x, y + 2, C, 1)
                surf.fillRect(col("choco"), x, y + 5, C, 1)
                surf.fillRect(col("yellow"), x + 3, y + 3, 2, 2)
            case "~":
                surf.fillRect(col("sky"), x, y, C, C)
                var k = 0
                while k < C { surf.line(col("white"), x + k, y + C - 1, x + min(C - 1, k + 3), y + C - 4); k += 4 }
                let ice = col("blue")
                if gx == 0 || tiles[c - 1] != "~" { surf.fillRect(ice, x, y, 1, C) }
                if gx == GW - 1 || tiles[c + 1] != "~" { surf.fillRect(ice, x + C - 1, y, 1, C) }
                if gy == 0 || tiles[c - GW] != "~" { surf.fillRect(ice, x, y, C, 1) }
                if gy == GH - 1 || tiles[c + GW] != "~" { surf.fillRect(ice, x, y + C - 1, C, 1) }
            case ">", "<", "^", "v":
                surf.fillRect(col("darkgray"), x, y, C, C)
                surf.fillRect(col("gray"), x, y, C, 1)
            default:
                break
            }
        }
        for v in vents where v.life == -1 {
            let x = OX + v.x * C, y = OY + v.y * C
            surf.fillRect(col("darkgray"), x, y, C, C)
            for k in stride(from: 1, to: 7, by: 2) { surf.fillRect(col("black"), x + 1, y + k, C - 2, 1) }
        }
        return surf
    }

    private func drawTiles(_ s: Surface, _ t: Double) {
        for (c, ch) in tiles.enumerated() {
            if let (dx, dy) = ARROWS[ch] {
                let (x, y) = cpx(c)
                let k = Int(t * 8) % 4
                for i in 0 ..< 2 {
                    let o = (k + i * 4) % 8 - 4
                    let cx = x + 4 + dx * o / 2, cy = y + 4 + dy * o / 2
                    let c2 = col(i == 0 ? "yellow" : "orange")
                    s.line(c2, cx - dy * 2 - dx * 2, cy - dx * 2 - dy * 2, cx, cy)
                    s.line(c2, cx + dy * 2 - dx * 2, cy + dx * 2 - dy * 2, cx, cy)
                }
            } else if PORTALS.contains(ch) {
                let (x, y) = cpx(c)
                let pc = PORTAL_COLORS[ch]!
                let r = 4 + Int(sin(t * 6 + Double(c)))
                s.circle(col("black"), x + 4, y + 4, r + 1)
                s.circle(col(pc[0]), x + 4, y + 4, r)
                s.circle(col(pc[1]), x + 4, y + 4, max(1, r - 2))
                let ang = t * 8
                s.fillRect(col("white"), x + 4 + Int(cos(ang) * 2), y + 4 + Int(sin(ang) * 2), 1, 1)
            }
        }
        for (c, life) in blocks {
            let (x, y) = cpx(c)
            s.rect(col("gray"), IRect(x, y, C, C), radius: 2)
            s.rect(col("white"), IRect(x, y, C, C - 1), radius: 2)
            s.fillRect(col("pink"), x + 2, y + 4, 1, 1)
            s.fillRect(col("pink"), x + 5, y + 4, 1, 1)
            if life < 1.2 && Int(t * 10) % 2 == 1 { s.rect(col("gray"), IRect(x, y, C, C), width: 1, radius: 2) }
        }
        if warnRing >= 0 && squeezed <= warnRing && Int(t * 8) % 2 == 1 {
            for c in 0 ..< NCELLS where ringOf(c) == warnRing && tiles[c] != "#" {
                let (x, y) = cpx(c)
                s.rect(col("red"), IRect(x, y, C, C), width: 1)
            }
        }
        for c in pending {
            let (x, y) = cpx(c)
            s.rect(col("orange"), IRect(x + 1, y + 1, C - 2, C - 2), width: 1)
        }
        for v in vents {
            let stt = v.state(stageTime)
            let x = OX + v.x * C, y = OY + v.y * C
            if v.life != -1 {
                s.fillRect(col("darkgray"), x, y, C, C)
                for k in stride(from: 1, to: 7, by: 2) { s.fillRect(col("black"), x + 1, y + k, C - 2, 1) }
                if v.life < 1.0 && Int(t * 10) % 2 == 1 { continue }
            }
            if stt == 1 {
                for i in 0 ..< 3 {
                    let px = x + 2 + i * 2
                    let py = y - Int(ndPmod(t * 12 + Double(i * 3), 5))
                    s.fillRect(col("white"), px, py, 1, 1)
                }
                s.rect(col(Int(t * 10) % 2 == 1 ? "orange" : "yellow"), IRect(x, y, C, C), width: 1)
            } else if stt == 2 {
                for (i, b) in v.beam.enumerated() {
                    let (bx, by) = cpx(b)
                    let wob = Int(sin(t * 20 + Double(i)))
                    s.circle(col("gray"), bx + 4 + wob, by + 4, 4)
                    s.circle(col("white"), bx + 4 + wob, by + 3, 3)
                    s.fillRect(col("cream"), bx + 2 - wob, by + 2, 2, 1)
                }
            }
        }
    }

    private func drawItem(_ s: Surface, _ it: NdItem, _ t: Double) {
        let (x, y) = cpx(it.cell)
        if it.life > 0 && it.life < 1.5 && Int(t * 10) % 2 == 1 { return }
        let bob = Int(sin(t * 5 + Double(it.cell)))
        switch it.kind {
        case "gold":
            Cute.dumpling(s, x, y + bob, golden: true, t: t)
        case "fortune":
            s.ellipse(col(rainbow(0, t)), x, y + 2 + bob, 8, 6)
            s.ellipse(col("black"), x, y + 2 + bob, 8, 6, width: 1)
            s.fillRect(col("white"), x + 2, y + 4 + bob, 1, 1)
            s.fillRect(col("white"), x + 5, y + 4 + bob, 1, 1)
            if Int(t * 8) % 2 == 1 {
                s.fillRect(col("white"), x + 7, y + bob, 1, 1)
                s.fillRect(col("yellow"), x - 1, y + 2 + bob, 1, 1)
            }
        case "tea", "chili", "magnet":
            s.circle(col("white"), x + 4, y + 4 + bob, 5)
            s.blit(sprite("ns_" + it.kind), x, y + bob)
        case "weak":
            let ring = 6 + Int(ndPmod(t * 8, 3))
            s.circle(col(Int(t * 6) % 2 == 1 ? "red" : "yellow"), x + 4, y + 4, ring, width: 1)
            switch it.look {
            case "sugar":
                s.fillRect(col("gray"), x + 1, y + 2 + bob, 7, 6)
                s.fillRect(col("white"), x + 1, y + 1 + bob, 6, 6)
                s.fillRect(col("sky"), x + 2, y + 2 + bob, 1, 1)
            case "bean":
                s.ellipse(col("black"), x, y + 1 + bob, 9, 7)
                s.ellipse(col("choco"), x + 1, y + 2 + bob, 7, 5)
                s.fillRect(col("pink"), x + 2, y + 3 + bob, 2, 1)
            case "bun":
                Cute.dumpling(s, x, y + bob, golden: true, t: t)
                s.fillRect(col("red"), x + 3, y + 1 + bob, 2, 1)
            default:
                s.blit(sprite("ns_chili"), x, y + bob)
            }
        default:
            break
        }
    }

    private func drawRoller(_ s: Surface, _ r: NdRoller, _ t: Double) {
        let x = OX + r.x * C, y = OY + r.y * C
        if r.kind == "ball" {
            s.circle(col("peach"), x + 4, y + 4, 5, width: 1)
            s.circle(col("black"), x + 4, y + 4, 4)
            s.circle(col("brown"), x + 4, y + 4, 3)
            let k = Int(r.spin) % 4
            s.fillRect(col("orange"), x + 2 + (k % 2) * 2, y + 2 + (k / 2) * 2, 2, 1)
            Cute.eyes(s, x + 4 + r.dx, y + 4 + r.dy, 1, mood: "angry")
        } else if r.kind == "slip" {
            s.fillRect(col("black"), x + 1, y + 2, 7, 5)
            s.fillRect(col("white"), x + 1, y + 2, 6, 4)
            s.fillRect(col("red"), x + 2, y + 4, 4, 1)
        } else {
            let gold = r.kind == "gold"
            s.ellipse(col("black"), x - 1, y + 3, 10, 5)
            s.ellipse(col(gold ? "yellow" : "white"), x - 1, y + 3, 10, 4)
            s.fillRect(col(gold ? "white" : "cream"), x + 1, y + 1, 6, 3)
            s.fillRect(col(gold ? "orange" : "red"), x + 1, y, 6, 2)
            if gold && Int(t * 8) % 2 == 1 {
                s.fillRect(col("white"), x + 7, y - 1, 1, 1)
                s.circle(col("yellow"), x + 4, y + 3, 6, width: 1)
            }
        }
    }

    private func drawAttacks(_ s: Surface, _ t: Double, _ top: Bool) {
        for a in attacks {
            switch a.kind {
            case "row", "col":
                if a.t < a.tele && !top {
                    if Int(t * 12) % 2 == 1 {
                        let c = col("red")
                        for k in a.cells { let (x, y) = cpx(k); s.fillRect(c, x + 3, y + 3, 2, 2) }
                    }
                    let (x, y) = cpx(a.cells[0])
                    if a.kind == "row" {
                        drawText(s, "!", OX - 8, y, "red", shadow: nil)
                        drawText(s, "!", OX + GW * C + 3, y, "red", shadow: nil)
                    } else {
                        drawText(s, "!", x + 1, a.cells[0] < GW ? OY - 10 : y - 9, "red", shadow: nil)
                    }
                } else if a.live && top {
                    for (i, k) in a.cells.enumerated() {
                        let (x, y) = cpx(k)
                        if a.style == "steam" {
                            let wob = Int(sin(t * 25 + Double(i)))
                            s.circle(col("gray"), x + 4 + wob, y + 4, 5)
                            s.circle(col("white"), x + 4 + wob, y + 3, 4)
                        } else if a.style == "quake" {
                            s.fillRect(col("choco"), x, y + 2, C, 4)
                            s.fillRect(col("brown"), x + (i * 3) % 6, y + 1, 2, 6)
                        } else {
                            s.fillRect(col("orange"), x, y + 1, C, 6)
                            s.fillRect(col("yellow"), x, y + 2, C, 2)
                        }
                    }
                    if a.style == "ladle" && a.kind == "row" {
                        let u = (a.t - a.tele) / max(0.01, a.act)
                        let (_, y0) = cpx(a.cells[0])
                        let lx = OX + Int(u * Double(GW * C))
                        s.circle(col("black"), lx, y0 + 4, 7)
                        s.circle(col("gray"), lx, y0 + 4, 6)
                        s.circle(col("white"), lx - 2, y0 + 2, 2)
                    }
                }
            case "drop" where !top:
                let u = min(1, a.t / a.tele)
                for (i, k) in a.cells.enumerated() {
                    let (x, y) = cpx(k)
                    let rr = 1 + Int(u * 3)
                    if Int(t * 10) % 2 == 1 { s.rect(col("red"), IRect(x, y, C, C), width: 1) }
                    s.ellipse(col("black"), x + 4 - rr, y + 5, rr * 2, 3)
                    let fy = y - Int((1 - u) * 60)
                    if i == a.gold {
                        s.ellipse(col("choco"), x, fy + 1, 8, 6)
                        s.fillRect(col("pink"), x + 2, fy + 2, 2, 1)
                    } else {
                        s.fillRect(col("gray"), x, fy + 1, C, C - 1)
                        s.fillRect(col("white"), x, fy, C, C - 2)
                    }
                }
            case "toss" where top:
                let u = min(1, a.t / a.tele)
                let (tx, ty) = cpx(a.cells[0])
                let (sx, sy) = a.src
                let x = Double(sx) + Double(tx + 4 - sx) * u
                let y = Double(sy) + Double(ty + 4 - sy) * u - sin(u * .pi) * 30
                if WEAK_LOOK[boss?.kind ?? "crab"] == "bun" {
                    Cute.dumpling(s, Int(x) - 4, Int(y) - 4, golden: true, t: t)
                } else {
                    s.blit(sprite("ns_chili"), Int(x) - 4, Int(y) - 4)
                }
                if Int(t * 10) % 2 == 1 { s.circle(col("red"), tx + 4, ty + 4, 4, width: 1) }
            case "plate" where top && Int(t * 10) % 2 == 1:
                let (x, y) = cpx(a.cells[0])
                let ch = a.dx == 1 ? "}" : a.dx == -1 ? "{" : a.dy == -1 ? "|" : "`"
                drawText(s, ch, x + 1, y, a.gold == 1 ? "yellow" : "red", shadow: nil, outline: "black")
            case "dash" where !top && Int(t * 12) % 2 == 1:
                for k in a.cells {
                    let (x, y) = cpx(k)
                    s.rect(col("lavender"), IRect(x + 1, y + 1, C - 2, C - 2), width: 1)
                }
            default:
                break
            }
        }
    }

    private func drawNoodle(_ s: Surface) {
        let n = body.count
        if invuln > 0 && state == "play" && Int(t * 12) % 2 == 1 { return }
        let fever = hype.feverOn
        let ghost = ghostT > 0
        let ghostN = 4 * lv("ghost")
        let k = col("black")
        let base = col(ghost ? "lavender" : "cream")
        let pts = body.map { (OX + ($0 % GW) * C + 4, OY + ($0 / GW) * C + 4) }
        func segCol(_ i: Int) -> Color {
            if fever { return col(rainbow(i, t)) }
            if ghostN > 0 && i >= n - ghostN { return col("lavender") }
            return base
        }
        func linked(_ i: Int) -> Bool { abs(pts[i].0 - pts[i - 1].0) <= C && abs(pts[i].1 - pts[i - 1].1) <= C }
        for i in stride(from: n - 1, to: 0, by: -1) where linked(i) { s.line(k, pts[i].0, pts[i].1, pts[i - 1].0, pts[i - 1].1, width: 7) }
        for i in stride(from: n - 1, through: 0, by: -1) { s.circle(k, pts[i].0, pts[i].1, (i < n - 2 ? 3 : 2) + 1) }
        for i in stride(from: n - 1, to: 0, by: -1) where linked(i) {
            s.line(segCol(i), pts[i].0, pts[i].1, pts[i - 1].0, pts[i - 1].1, width: 5)
        }
        let peach = col("orange")
        for i in stride(from: n - 1, through: 0, by: -1) {
            s.circle(segCol(i), pts[i].0, pts[i].1, i < n - 2 ? 3 : 2)
            if i % 3 == 1 && !fever { s.fillRect(peach, pts[i].0 - 1, pts[i].1 - 1, 2, 1) }
        }
        let (hx, hy) = pts[0], (dx, dy) = dir
        let hr = 4 + (slurp > 0 ? 1 : 0)
        s.circle(k, hx, hy, hr + 1)
        s.circle(fever ? col(rainbow(0, t)) : base, hx, hy, hr)
        if dead { Cute.eyes(s, hx, hy - 1, 2, mood: "sleepy") } else { Cute.eyes(s, hx + dx, hy - 1 + dy, 2, blink: Int(t * 1.3) % 6 == 0) }
        Cute.blush(s, hx, hy + 1, 2)
        if slurp > 0 { s.circle(col("hotpink"), hx + dx * 3, hy + dy * 3 + 1, 1) }
        if dashT > 0 {
            for i in 0 ..< 3 {
                s.fillRect(col("yellow"), hx - dx * (7 + i * 3) + dy * (i - 1) * 3, hy - dy * (7 + i * 3) + dx * (i - 1) * 3, 2, 1)
            }
        }
    }

    // ---------------------------------------------------------------- bosses
    private func drawBoss(_ s: Surface, _ t: Double) {
        guard let b = boss else { return }
        if b.dead && state != "bossdown" { return }
        var x = OX + b.x * C, y = OY + b.y * C
        let w = b.w * C, h = b.h * C
        if b.dead {
            x += Int.random(in: -2 ... 2)
            y += Int.random(in: -2 ... 2)
            if Int(t * 20) % 2 == 1 {
                parts.burst(Double(x + Int.random(in: 0 ..< w)), Double(y + Int.random(in: 0 ..< h)), 3, ["yellow", "white", "red"], 50, 0.4)
            }
        }
        let hit = b.flash > 0 && Int(t * 30) % 2 == 0
        let mood = b.angry || b.anim > 0 ? "angry" : "happy"
        switch b.kind {
        case "crab": drawCrab(s, x, y, w, h, t, hit, mood, b)
        case "teapot": drawTeapot(s, x, y, w, h, t, hit, mood, b)
        case "sushi": drawSushi(s, x, y, w, h, t, hit, mood, b)
        case "golem": drawGolem(s, x, y, w, h, t, hit, mood, b)
        case "ghost": drawGhost(s, x, y, w, h, t, hit, mood, b)
        default: drawBao(s, x, y, w, h, t, hit, mood, b)
        }
    }

    private func bodyCol(_ name: String, _ hit: Bool) -> Color { col(hit ? "white" : name) }

    private func drawCrab(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ t: Double, _ hit: Bool, _ mood: String, _ b: NdBoss) {
        let k = col("black")
        let cx = x + w / 2
        let bob = Int(sin(t * 6))
        for side in [-1, 1] {   // legs
            for i in 0 ..< 3 {
                let lx = cx + side * (10 + i * 5)
                s.fillRect(k, lx, y + h - 4 + (i + Int(t * 8)) % 2, 2, 4)
            }
        }
        s.ellipse(k, x + 1, y + 5 + bob, w - 2, h - 6)
        s.ellipse(bodyCol("red", hit), x + 2, y + 6 + bob, w - 4, h - 8)
        s.ellipse(bodyCol("hotpink", hit), x + 8, y + 8 + bob, w - 16, 4)
        // chef hat
        s.rect(k, IRect(cx - 9, y - 3 + bob, 18, 9), radius: 4)
        s.rect(col("white"), IRect(cx - 8, y - 2 + bob, 16, 7), radius: 3)
        s.fillRect(col("gray"), cx - 8, y + 4 + bob, 16, 1)
        Cute.eyes(s, cx, y + 13 + bob, 5, mood: mood)
        Cute.mouth(s, cx, y + 17 + bob, mood == "angry" ? "angry" : "happy")
        for side in [-1, 1] {   // claws, the right one waves the ladle
            let ccx = x + (side < 0 ? 3 : w - 4)
            let ccy = y + 12 + Int(sin(t * 5 + Double(side)) * 2)
            s.circle(k, ccx, ccy, 5)
            s.circle(bodyCol("red", hit), ccx, ccy, 4)
            s.fillRect(k, ccx - 1, ccy - 4, 2, 4)
            if side > 0 {
                s.line(col("gray"), ccx, ccy, ccx + 6, ccy - 8, width: 2)
                s.circle(col("gray"), ccx + 7, ccy - 9, 3)
            }
        }
    }

    private func drawTeapot(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ t: Double, _ hit: Bool, _ mood: String, _ b: NdBoss) {
        let k = col("black")
        let cx = x + w / 2
        let bodyC = bodyCol("teal", hit)
        s.circle(k, x + 4, y + 18, 6, width: 2)        // handle
        s.polygon(k, [(Double(x + w - 9), Double(y + 16)), (Double(x + w + 5), Double(y + 8)), (Double(x + w + 6), Double(y + 12)), (Double(x + w - 7), Double(y + 24))])
        s.polygon(bodyC, [(Double(x + w - 9), Double(y + 17)), (Double(x + w + 4), Double(y + 9)), (Double(x + w + 4), Double(y + 11)), (Double(x + w - 8), Double(y + 22))])
        s.ellipse(k, x + 3, y + 7, w - 6, h - 7)
        s.ellipse(bodyC, x + 4, y + 8, w - 8, h - 9)
        s.ellipse(bodyCol("mint", hit), x + 9, y + 11, w - 18, 5)
        let lidY = y + 3 - (b.lid > 0 ? 4 + Int(abs(sin(t * 12)) * 3) : 0)
        s.ellipse(k, cx - 10, lidY, 20, 8)
        s.ellipse(bodyCol("white", hit), cx - 9, lidY + 1, 18, 6)
        s.circle(col("yellow"), cx, lidY, 2)
        for side in [-1, 1] {   // little dragon horns
            s.polygon(col("yellow"), [(Double(cx + side * 12), Double(y + 10)), (Double(cx + side * 16), Double(y + 3)), (Double(cx + side * 9), Double(y + 9))])
        }
        Cute.eyes(s, cx, y + 18, 5, mood: mood)
        s.fillRect(k, cx - 2, y + 22, 1, 1)
        s.fillRect(k, cx + 2, y + 22, 1, 1)
        if b.anim > 0 || b.lid > 0 {
            for i in 0 ..< 3 {
                let py = y - 2 - Int(ndPmod(t * 30 + Double(i * 6), 14))
                s.circle(col("white"), x + w + 4 + i * 2 - 2, py + 8, 2)
            }
        }
    }

    private func drawSushi(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ t: Double, _ hit: Bool, _ mood: String, _ b: NdBoss) {
        let k = col("black")
        let cx = x + w / 2
        s.rect(k, IRect(x, y + h - 6, w, 6), radius: 2)       // conveyor
        s.fillRect(col("gray"), x + 1, y + h - 5, w - 2, 3)
        for i in 0 ..< 8 { s.fillRect(col("darkgray"), x + 2 + (i * 8 + Int(t * 20)) % (w - 4), y + h - 5, 2, 3) }
        s.rect(k, IRect(x + 2, y + 1, w - 4, h - 6), radius: 5)
        s.rect(bodyCol("white", hit), IRect(x + 3, y + 2, w - 6, h - 8), radius: 4)
        s.rect(bodyCol("orange", hit), IRect(x + 3, y + 2, w - 6, 6), radius: 3)
        for i in 0 ..< 5 { s.fillRect(col("peach"), x + 8 + i * 10, y + 3, 4, 1) }
        s.fillRect(k, cx - 4, y + 7, 8, h - 13)                                  // nori band
        Cute.eyes(s, cx - 14, y + 13, 3, mood: mood)
        Cute.eyes(s, cx + 14, y + 13, 3, mood: mood)
        let mo = b.anim > 0 ? 3 + Int(abs(sin(t * 6)) * 3) : 2
        s.ellipse(col("red"), cx - 6, y + 8 + 6 - mo / 2, 12, mo)
    }

    private func drawGolem(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ t: Double, _ hit: Bool, _ mood: String, _ b: NdBoss) {
        let k = col("black")
        let cx = x + w / 2
        let sq = Int(abs(sin(t * 3)) * 2)
        let tiers = [(h - 12, w - 2), (h - 21, w - 10), (h - 28, w - 20)]
        for (i, (ty, tw)) in tiers.enumerated() {
            let ry = y + ty + (i > 0 ? sq : 0)
            s.ellipse(k, cx - tw / 2 - 1, ry - 1, tw + 2, 13)
            s.ellipse(bodyCol(i != 1 ? "white" : "cream", hit), cx - tw / 2, ry, tw, 11)
        }
        s.circle(k, cx, y + 2, 5)
        s.circle(col("orange"), cx, y + 2, 4)
        s.fillRect(col("lime"), cx, y - 3, 2, 2)
        Cute.eyes(s, cx, y + h - 17 + sq, 5, mood: mood)
        Cute.blush(s, cx, y + h - 14 + sq, 5)
        Cute.mouth(s, cx, y + h - 12 + sq, mood == "angry" ? "angry" : "happy")
        for side in [-1, 1] {
            let ax = cx + side * (w / 2 + 1)
            let ay = y + h - 10 + (b.anim > 0 ? Int(sin(t * 8) * 2) : 0)
            s.circle(k, ax, ay, 4)
            s.circle(bodyCol("white", hit), ax, ay, 3)
        }
    }

    private func drawGhost(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ t: Double, _ hit: Bool, _ mood: String, _ b: NdBoss) {
        let k = col("black")
        let cx = x + w / 2, cy = y + h / 2 + Int(sin(t * 4) * 2)
        if b.inv > 0 && Int(t * 12) % 2 == 1 { return }
        let bodyC = bodyCol("white", hit)
        s.circle(k, cx, cy - 1, 9)
        s.rect(k, IRect(cx - 9, cy - 1, 19, 10))
        s.circle(bodyC, cx, cy - 1, 8)
        s.rect(bodyC, IRect(cx - 8, cy - 1, 17, 8))
        for i in 0 ..< 5 {   // wavy hem
            s.circle((i + Int(t * 8)) % 2 == 1 ? k : bodyC, cx - 8 + i * 4, cy + 8, 2)
            s.circle(bodyC, cx - 8 + i * 4, cy + 7, 2)
        }
        s.fillRect(col("lavender"), cx + 4, cy - 4, 2, 9)
        s.ellipse(k, cx - 7, cy - 14, 14, 8)     // fortune cookie hat
        s.ellipse(col("yellow"), cx - 6, cy - 13, 12, 6)
        s.line(col("orange"), cx - 4, cy - 10, cx + 4, cy - 10)
        s.fillRect(col("white"), cx + 5, cy - 12, 6, 3)           // the fortune slip
        s.fillRect(col("red"), cx + 7, cy - 11, 3, 1)
        let stunned = b.stun > 0
        Cute.eyes(s, cx, cy - 2, 3, mood: stunned ? "wow" : mood)
        Cute.mouth(s, cx, cy + 2, stunned ? "wow" : (mood == "angry" ? "angry" : "happy"))
        Cute.blush(s, cx, cy + 1, 3)
    }

    private func drawBao(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ t: Double, _ hit: Bool, _ mood: String, _ b: NdBoss) {
        let k = col("black")
        let cx = x + w / 2
        let bob = Int(sin(t * 3))
        s.ellipse(k, x, y + 4 + bob, w, h - 3)
        s.ellipse(bodyCol("white", hit), x + 1, y + 5 + bob, w - 2, h - 5)
        for i in -3 ... 3 { s.fillRect(col("cream"), cx + i * 5, y + 6 + bob + abs(i), 1, 5) }   // pleats
        func pts(_ p: [(Int, Int)]) -> [(Double, Double)] { p.map { (Double($0.0), Double($0.1)) } }
        s.polygon(col("black"), pts([(cx - 11, y + 4 + bob), (cx - 11, y - 5 + bob), (cx - 5, y + bob), (cx, y - 7 + bob),
                                     (cx + 5, y + bob), (cx + 11, y - 5 + bob), (cx + 11, y + 4 + bob)]))
        s.polygon(col("yellow"), pts([(cx - 10, y + 3 + bob), (cx - 10, y - 3 + bob), (cx - 5, y + 1 + bob), (cx, y - 5 + bob),
                                      (cx + 5, y + 1 + bob), (cx + 10, y - 3 + bob), (cx + 10, y + 3 + bob)]))
        s.fillRect(col("red"), cx - 1, y - 1 + bob, 3, 2)
        Cute.eyes(s, cx, y + 17 + bob, 6, mood: mood)
        Cute.blush(s, cx, y + 20 + bob, 6)
        s.line(k, cx - 6, y + 23 + bob, cx - 1, y + 21 + bob, width: 2)   // mustache
        s.line(k, cx + 6, y + 23 + bob, cx + 1, y + 21 + bob, width: 2)
    }

    // ---------------------------------------------------------------- HUD & cards
    private func drawHud(_ s: Surface, _ t: Double) {
        drawText(s, String(format: "%07d", score), 4, 4, "white")
        drawText(s, String(format: "HI %07d", max(best, score)), 52, 4, "lavender")
        var label: String, c: String
        if campaign {
            if kind == "bonus" { label = "BONUS"; c = rainbow(0, t) } else if kind == "boss" { label = "BOSS \(stageN)"; c = "red" } else { label = "STAGE \(stageN)"; c = "yellow" }
        } else {
            label = mode == "classic" ? "CLASSIC" : "WRAP"; c = "yellow"
        }
        let hx = W - 4 - 8 * min(6, max(0, lives)) - (lives > 6 ? 14 : 0)
        drawText(s, label, hx - 6, 4, c, align: .right)
        hearts(s, hx, 3, lives)
        // left column: fever gauge
        let gx = 12, gy = 40, gh = 130
        s.blit(sprite("ns_chili"), gx - 1, gy - 12)
        panel(s, IRect(gx - 2, gy - 2, 10, gh + 4), fill: "black", border: theme[2], radius: 2, shadow: false)
        if hype.feverOn {
            let fh = Int(Double(gh) * min(1, hype.feverT / (Hype.feverTime + 2 * Double(lv("fever")))))
            var i = 0
            while i < fh { s.fillRect(col(rainbow(i / 4, t)), gx, gy + gh - i - 4, 6, 4); i += 4 }
        } else {
            let fh = Int(Double(gh) * hype.fever)
            s.fillRect(col("orange"), gx, gy + gh - fh, 6, fh)
            s.fillRect(col("yellow"), gx + 1, gy + gh - fh, 2, fh)
        }
        // right column: abilities and timers
        let rx = W - 24
        var ry = 30
        for i in 0 ..< dashCharges { s.blit(sprite("ns_bolt"), rx + (i % 2) * 10, ry + (i / 2) * 10) }
        ry += 10 * ((dashCharges + 1) / 2) + (dashCharges > 0 ? 4 : 0)
        for i in 0 ..< snips { s.blit(sprite("ns_snip"), rx + (i % 2) * 10, ry + (i / 2) * 10) }
        ry += 10 * ((snips + 1) / 2) + (snips > 0 ? 4 : 0)
        for (name, v, full) in [("ns_tea", ghostT, 5.0), ("ns_magnet", magnetT, 8.0)] where v > 0 {
            s.blit(sprite(name), rx + 4, ry)
            s.fillRect(col("white"), rx, ry + 10, Int(16 * v / full), 2)
            ry += 16
        }
        // bottom row: goal progress
        let by = OY + GH * C + 5
        if kind == "boss", let b = boss {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: by - 1)
            return
        }
        var txt: String
        switch goal {
        case "eat": txt = "EAT \(min(eatenStage, target))/\(target)"
        case "stars": txt = "STARS \(starsTotal - stars.count)/\(starsTotal)"
        case "length": txt = "LENGTH \(body.count)/\(target)"
        case "survive": txt = "SURVIVE \(max(0, Int((Double(target) - stageTime).rounded(.up))))"
        case "feast": txt = "FEAST \(feastTotal - foods.count)/\(feastTotal)"
        case "rush": txt = "GOLDEN \(eatenStage)"
        default: txt = "LENGTH \(body.count)  EATEN \(totalEaten)"
        }
        drawText(s, txt, OX, by, "white")
        if kind == "bonus" {
            let tl = max(0, bonusLeft)
            drawText(s, String(format: "TIME %04.1f", tl), OX + GW * C - (hype.feverOn ? 34 : 0), by,
                     tl > 5 || Int(t * 8) % 2 == 1 ? "yellow" : "red", align: .right)
        } else if !gatesOpen {
            drawText(s, "DOORS OPEN IN \(max(0, st.gate - eatenStage))", OX + GW * C, by, "yellow", align: .right)
        } else if campaign && !hype.feverOn {
            drawText(s, theme[0], OX + GW * C, by, "cream", align: .right)
        }
    }

    private func goalText() -> String {
        let n = target
        switch goal {
        case "eat": return "EAT \(n) DUMPLINGS"
        case "stars": return "GRAB ALL \(n) CHILI STARS"
        case "length": return "GROW TO LENGTH \(n)"
        case "survive": return "SURVIVE \(n) SECONDS"
        case "feast": return "SLURP THE FEAST IN 20 SEC!"
        case "rush": return "GOLDEN RUSH! 20 SECONDS"
        case "endless": return "EAT, GROW, DON'T BUMP!"
        default: return ""
        }
    }

    private func drawIntro(_ s: Surface, _ t: Double) {
        if kind == "boss" && stateT < 2.2 {
            let on = Int(t * 6) % 2 == 0
            s.fillRect(rgba(120, 10, 30, 170), 0, 70, W, 40)
            var i = 0
            while i < W {
                let o = Int(t * 40) % 16
                s.polygon(col("yellow"), [(Double(i + o), 70), (Double(i + o + 8), 70), (Double(i + o), 74)])
                s.polygon(col("yellow"), [(Double(i - o + 8), 110), (Double(i - o + 16), 110), (Double(i - o + 16), 106)])
                i += 16
            }
            if on { drawText(s, "WARNING!!", W / 2, 80, "red", scale: 3, align: .center, outline: "white") }
            drawText(s, "A HUNGRY BOSS APPROACHES", W / 2, 101, "white", align: .center, shadow: nil)
            return
        }
        let y0 = 54
        panel(s, IRect(50, y0, 220, 84), fill: "ink", border: kind == "stage" ? theme[7] : "yellow")
        if kind == "boss", let b = boss {
            drawText(s, b.name, W / 2, y0 + 10, "red", scale: 2, align: .center, outline: "black")
            drawText(s, "STAGE \(stageN)", W / 2, y0 + 32, "yellow", align: .center)
            drawText(s, b.hint, W / 2, y0 + 48, "white", align: .center, shadow: nil)
            drawText(s, "HP \(b.maxhp)", W / 2, y0 + 64, "pink", align: .center, shadow: nil)
            return
        }
        if kind == "bonus" {
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, y0 + 10 + Int(sin(t * 6 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            drawText(s, goal == "feast" ? "DUMPLING FEAST!" : "GOLDEN RUSH!", W / 2, y0 + 34, "yellow", align: .center)
            drawText(s, goalText(), W / 2, y0 + 50, "white", align: .center, shadow: nil)
            drawText(s, "NO LIVES LOST HERE - GO WILD!", W / 2, y0 + 66, "mint", align: .center, shadow: nil)
            return
        }
        if campaign {
            drawText(s, "STAGE \(stageN)", W / 2, y0 + 8, "yellow", scale: 2, align: .center, outline: "black")
            drawText(s, theme[0], W / 2, y0 + 28, theme[7], align: .center)
        } else {
            drawText(s, mode == "classic" ? "CLASSIC" : "WRAP AROUND", W / 2, y0 + 12, "yellow", scale: 2, align: .center, outline: "black")
        }
        drawText(s, goalText(), W / 2, y0 + 44, "white", align: .center, shadow: nil)
        if !st.new.isEmpty {
            drawText(s, "NEW!", W / 2, y0 + 58, rainbow(0, t), align: .center, shadow: nil)
            drawText(s, st.new, W / 2, y0 + 68, "mint", align: .center, shadow: nil)
        } else {
            drawText(s, "READY... SLURP!", W / 2, y0 + 62, "peach", align: .center, shadow: nil)
        }
    }

    private func drawTally(_ s: Surface, _ t: Double) {
        let y0 = 48
        let hh = 30 + 14 * tally.count
        panel(s, IRect(60, y0, 200, hh + 14), fill: "ink", border: "yellow")
        let title = kind == "boss" ? "BOSS DEFEATED!" : kind == "bonus" ? "BONUS RESULT" : "STAGE \(stageN) CLEAR!"
        drawText(s, title, W / 2, y0 + 8, "yellow", align: .center)
        for (i, ln) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 24 + i * 14
            let dim = ln.1 == 0 && i < tallyI
            drawText(s, ln.0, 72, y, dim ? "gray" : "white", shadow: nil)
            drawText(s, dim ? "-" : "\(ln.2)", 248, y, dim ? "gray" : "lime", align: .right, shadow: nil)
        }
        if tallyI >= tally.count {
            let total = tally.reduce(0) { $0 + $1.1 }
            drawText(s, "TOTAL \(total)", W / 2, y0 + hh - 2, lucky ? rainbow(0, t) : "yellow", align: .center)
        }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("peach"))
        let w = s.w, h = s.h
        var y = 0
        while y < h { var x = 0; while x < w { if (x / 8 + y / 8) % 2 == 1 { s.fillRect(col("cream"), x, y, 8, 8) }; x += 8 }; y += 8 }
        let pts = (0 ..< 10).map { (10 + $0 * 6, h / 2 + Int(sin(t * 4 + Double($0) * 0.6) * 6)) }
        for i in 0 ..< pts.count - 1 { s.line(col("black"), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: 7) }
        for i in 0 ..< pts.count - 1 {
            let c = Int(t) % 4 == 3 ? col(rainbow(i, t)) : col("cream")
            s.line(c, pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: 5)
        }
        let (hx, hy) = pts.last!
        s.circle(col("black"), hx, hy, 5)
        s.circle(col("cream"), hx, hy, 4)
        Cute.eyes(s, hx + 1, hy - 1, 2)
        Cute.dumpling(s, w - 22, h / 2 - 4, t: t)
        Cute.dumpling(s, w - 40, 10, golden: true, t: t)
        s.blit(sprite("star", remap: ["y": "r"]), w - 30, h - 16)
    }
}
