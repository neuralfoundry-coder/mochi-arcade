// WHISKER MAZE - a midnight snack raid! (port of mochi_arcade/games/whisker_maze.py)
// Nori the black cat eats fish crumbs in 200 house mazes while dust bots with their own habits patrol;
// catnip zoomies let her bat dizzy bots that slide like pucks and knock over the others.
// Data: WhiskerMazeData.swift (campaign export), art: WhiskerMazeArt.swift, bosses: WhiskerMazeBoss.swift.
import Foundation

private let COLS = WM_COLS, ROWS = WM_ROWS
private let TS = 10, OX = 5, OY = 25
private let NORI_SPEED = 5.4
private let BUFFER = 0.6
private let ASSIST = 0.34
private let DOCK = (15, 7), EXIT = (15, 5)
private let LIFE_AT = [20000, 50000, 100000, 160000]
private let KIND_SPEED: [String: Double] = ["sniffy": 0.95, "zig": 1.0, "fridgy": 0.9, "snoozy": 1.0, "mopsy": 0.9,
                                            "spritz": 0.85, "ruff": 0.8, "bunny": 0.8, "mouse": 0.72]
private let DOCK_X = [13, 14, 16, 17, 15, 15]
private let DIRS: [(Action, WD)] = [(.left, WD(-1, 0)), (.right, WD(1, 0)), (.up, WD(0, -1)), (.down, WD(0, 1))]

@inline(__always) private func rnd(_ v: Double) -> Int { Int(floor(v + 0.5)) }
@inline(__always) private func wrapX(_ x: Int) -> Int { ((x % COLS) + COLS) % COLS }
@inline(__always) private func key(_ x: Int, _ y: Int) -> Int { y * COLS + wrapX(x) }
@inline(__always) private func tpx(_ x: Double) -> Double { Double(OX) + x * Double(TS) + Double(TS / 2) }
@inline(__always) private func tpy(_ y: Double) -> Double { Double(OY) + y * Double(TS) + Double(TS / 2) }
@inline(__always) private func sgn(_ v: Int) -> Int { v > 0 ? 1 : (v < 0 ? -1 : 0) }

private func distWrap(_ ax: Double, _ ay: Double, _ bx: Double, _ by: Double) -> Double {
    var dx = abs(ax - bx)
    dx = min(dx, Double(COLS) - dx)
    let dy = ay - by
    return (dx * dx + dy * dy).squareRoot()
}

// ----------------------------------------------------------------------------- movers
class WMMover {
    var x, y: Double
    var dir = WD.zero
    var face = WD(0, 1)
    init(_ x: Double, _ y: Double) { self.x = x; self.y = y }
    func tile() -> (Int, Int) { (wrapX(rnd(x)), rnd(y)) }
}

final class WMBot: WMMover {
    let kind: String
    var post: (Int, Int)?
    var state = "dock"          // dock | leave | roam | sleep | puck | reboot | gone
    var mode = ""               // per-kind: patrol/chase/return, alert/chase/drowsy, aim, bark/dash/tired
    var timer = 0.0, cd = 0.0
    var dizzy = false
    var frozen = 0.0, spin = 0.0
    var lastTurn = 1
    var hits = 0
    var life = 0.0              // minions
    var prev: (Int, Int)?
    var postDist: [Int: Int] = [:]
    init(_ kind: String, _ x: Int, _ y: Int, _ post: (Int, Int)? = nil) {
        self.kind = kind
        self.post = post
        super.init(Double(x), Double(y))
    }
    func harmful() -> Bool { (state == "roam" || state == "leave") && !dizzy && frozen <= 0 && kind != "mouse" }
}

final class WMItem {
    let kind: String
    let x, y: Int
    var life: Double
    init(_ kind: String, _ x: Int, _ y: Int, _ life: Double) { self.kind = kind; self.x = x; self.y = y; self.life = life }
}

final class WMShot {
    var x, y, vx, vy: Double
    let style: String
    var life: Double
    init(x: Double, y: Double, vx: Double, vy: Double, style: String, life: Double) {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.style = style; self.life = life
    }
}

final class WMMist {
    var x, y: Double
    let dx, dy: Int
    init(_ x: Double, _ y: Double, _ dx: Int, _ dy: Int) { self.x = x; self.y = y; self.dx = dx; self.dy = dy }
}

final class WMHazard {
    let tiles: [(Int, Int)]
    let warn, active: Double
    let style: String
    var t = 0.0
    init(_ tiles: [(Int, Int)], _ warn: Double, _ active: Double, _ style: String) {
        self.tiles = tiles; self.warn = warn; self.active = active; self.style = style
    }
}

/// Distances over walkable tiles from start (doors=true treats every door as open).
private func bfsTiles(_ sc: WhiskerMaze, _ start: (Int, Int), _ who: String, doors: Bool = false) -> [Int: Int] {
    var dist: [Int: Int] = [key(start.0, start.1): 0]
    var q = [start]
    var head = 0
    while head < q.count {
        let (x, y) = q[head]; head += 1
        let d = dist[key(x, y)]! + 1
        for dd in WM_D4 {
            let nx = wrapX(x + dd.x), ny = y + dd.y
            if ny < 0 || ny >= ROWS || dist[key(nx, ny)] != nil { continue }
            let ch = sc.walls[ny][nx]
            let ok = doors && (ch == "D" || ch == "d") ? true : sc.walk(nx, ny, who)
            if ok { dist[key(nx, ny)] = d; q.append((nx, ny)) }
        }
    }
    return dist
}

// ----------------------------------------------------------------------------- the game
final class WhiskerMaze: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD   MOVE - HOLD A TURN EARLY AND", "      NORI TAKES THE NEXT GAP", "DASH  PURR DASH (SHORT BURST)"]
    static let helpSkip = 3
    override var music: String? { song() }
    override var buttons: [Action: String] { [.a: "DASH"] }
    override var buttonOrder: [Action] { [.a] }
    override var fourWay: Bool { true }

    var lives: Int
    let dspeed: Double
    var levels: [String: Int] = [:]
    var lifeI = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    // stage
    var n = 1
    var st: WMStage = WMData.stages[0]
    var tier = 0
    var theme: WMTheme = WMData.themes[0]
    var walls: [[Character]] = []
    var food: [Int: Character] = [:]
    var start = (15, 11)
    var total = 0, crumbsLeft = 0, eaten = 0, secrets = 0, batted = 0
    var doorPhase = 0, doorT = 0.0
    var wet: [Int: Double] = [:]
    var scent: [Int: Double] = [:]
    var items: [WMItem] = []
    var shots: [WMShot] = []
    var mists: [WMMist] = []
    var hazards: [WMHazard] = []
    var zoomT = 0.0, chain = 0, dashT = 0.0, dashCd = 0.0, invuln = 0.0
    var collar = 0
    var stime = 0.0
    var missed = false
    var stageCombo = 0, streak = 0, streakT = 0.0, bestStreak = 0
    var miceCaught = 0, miceTotal = 0, golds = 0
    var bonusLeft = 0.0
    var spawned = Set<String>()
    var luckyGold = false, luckyMilk = false
    var nipSpawn = 6.0, nipCount = 0
    var ndist: [Int: Int] = [:]
    var ndistKey = -1
    var boss: WMBoss?
    var nori = WMMover(15, 11)
    var bots: [WMBot] = []
    var want: WD?
    var wantT = 0.0
    var lastKey: Action?
    var state = "intro"
    var stateT = 0.0, introLen = 2.6
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0
    var bg = Surface(W, H)

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        dspeed = SPEEDS[d] ?? 1
        super.init(app, info, opt)
        hype.comboY = 13
        let s = max(1, min(STAGES, optInt("stage", optInt("start", 1))))
        startStage(s)
        if s > 10 {          // starting from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (s - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func factorPts(_ pts: Int) -> Int { pts * (10 + tier) / 10 }
    @discardableResult
    func scoreAt(_ pts: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int { add(factorPts(pts), x, y, c) }
    func song() -> String { st.kind == "boss" ? "boss" : (st.kind == "bonus" ? "bonus" : (tier % 2 == 0 ? "wm_prowl" : "wm_moon")) }
    var zoomy: Bool { zoomT > 0 }
    func scentLife() -> Double { (6.0 + 0.2 * Double(tier)) * (1 - 0.2 * Double(lv("bell"))) }

    // ---------------------------------------------------------------- stage setup
    func startStage(_ num: Int) {
        n = num
        st = WMData.stages[num - 1]
        tier = st.tier
        theme = st.kind == "bonus" ? (WMData.bonusThemes[st.bonus] ?? WMData.themes[0]) : WMData.themes[min(tier, WMData.themes.count - 1)]
        reached(num)
        walls = []
        food = [:]
        for (y, row) in st.rows.enumerated() {
            var wr: [Character] = []
            for (x, ch) in row.enumerated() {
                wr.append(".oP ".contains(ch) ? " " : ch)
                if ".~Dd".contains(ch) { food[key(x, y)] = "c" } else if ch == "o" { food[key(x, y)] = "o" } else if ch == "%" { food[key(x, y)] = "s" }
                if ch == "P" { start = (x, y) }
            }
            walls.append(wr)
        }
        total = food.values.filter { $0 == "c" }.count
        if st.kind == "bonus" && st.bonus == "fish" {
            for (k, v) in food where v == "c" { food[k] = "f" }
        }
        crumbsLeft = total
        eaten = 0; secrets = 0; batted = 0
        doorPhase = 0
        doorT = st.doorT
        wet = [:]; scent = [:]
        items = []; shots = []; mists = []; hazards = []
        zoomT = 0; chain = 0; dashT = 0; dashCd = 0; invuln = 0
        collar = lv("collar")
        stime = 0
        missed = false
        stageCombo = 0; streak = 0; streakT = 0; bestStreak = 0
        miceCaught = 0; miceTotal = 0; golds = 0
        bonusLeft = st.time
        spawned = []
        luckyGold = st.kind == "normal" && hype.lucky(0.025 + 0.015 * Double(lv("luck")))
        luckyMilk = st.kind == "normal" && hype.lucky(0.015 + 0.01 * Double(lv("luck")))
        nipSpawn = 6.0; nipCount = 0
        ndist = [:]; ndistKey = -1
        boss = st.boss.map { WMBoss(self, $0) }
        bots = []
        resetPositions()
        if st.kind == "bonus" && st.bonus == "mice" {
            miceTotal = min(st.spots.count, 10 + tier / 4)
            for (x, y) in st.spots.prefix(miceTotal) {
                let m = WMBot("mouse", x, y)
                m.state = "roam"
                bots.append(m)
            }
        }
        if st.kind == "bonus" && st.bonus == "fish" {
            for (x, y) in st.spots.prefix(3) { items.append(WMItem("gold", x, y, 99)) }
        }
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.0 : 2.6
        tally = []
        bg = makeBg()
        if hype.feverOn { hype.feverT = 0 }
        hype.feverTime = 8.0 + 1.5 * Double(lv("fever"))
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    /// (Re)place Nori and the bots: start of a stage and after a miss.
    func resetPositions() {
        nori = WMMover(Double(start.0), Double(start.1))
        nori.face = WD(0, 1)
        want = nil; wantT = 0; lastKey = nil
        zoomT = 0
        mists = []; shots = []; hazards = []
        dashT = 0
        let keepMice = bots.filter { $0.kind == "mouse" }
        bots = []
        if st.kind == "normal" {
            let gap = st.release
            for (j, (k, px, py)) in st.bots.enumerated() {
                let b: WMBot
                if k == "fridgy" || k == "snoozy" {
                    b = WMBot(k, px, py, (px, py))
                    b.state = k == "snoozy" ? "sleep" : "roam"
                    b.mode = k == "fridgy" ? "patrol" : ""
                    b.postDist = bfsTiles(self, (px, py), "bot", doors: true)
                } else {
                    b = WMBot(k, DOCK_X[j % DOCK_X.count], DOCK.1)
                    b.timer = 0.6 + Double(j) * gap
                }
                bots.append(b)
            }
        }
        bots += keepMice
        if let bo = boss, bo.state != "dead" && bo.state != "enter" {
            bo.x = 15; bo.y = 8
            bo.state = "idle"
            bo.cd = 2.0
        }
    }

    // ---------------------------------------------------------------- map queries
    func doorOpen(_ ch: Character) -> Bool { (ch == "D") == (doorPhase == 1) }

    /// who: cat (Nori) | bot (maze only) | dock (bots leaving / entering the dock).
    func walk(_ x: Int, _ y: Int, _ who: String) -> Bool {
        if y < 0 || y >= ROWS { return false }
        let ch = walls[y][wrapX(x)]
        switch ch {
        case "#": return false
        case "D", "d": return doorOpen(ch)
        case "%": return who == "cat"
        case "=", "-": return who == "dock"
        default: return true
        }
    }

    func see(_ x: Int, _ y: Int) -> Bool {
        if y < 0 || y >= ROWS { return false }
        let ch = walls[y][wrapX(x)]
        return ch != "#" && ch != "%" && (!(ch == "D" || ch == "d") || doorOpen(ch))
    }

    func isWet(_ x: Int, _ y: Int) -> Bool {
        if y < 0 || y >= ROWS { return false }
        return walls[y][wrapX(x)] == "~" || wet[key(x, y)] != nil
    }

    func openOnly(_ tiles: [(Int, Int)]) -> [(Int, Int)] {
        tiles.filter { $0.0 >= 0 && $0.0 < COLS && $0.1 >= 0 && $0.1 < ROWS && !"#=-".contains(walls[$0.1][$0.0]) }
    }
    func rowTiles(_ y: Int) -> [(Int, Int)] { openOnly((0 ..< COLS).map { ($0, y) }) }
    func colTiles(_ x: Int) -> [(Int, Int)] { openOnly((0 ..< ROWS).map { (x, $0) }) }
    func areaTiles(_ x: Int, _ y: Int, _ r: Int) -> [(Int, Int)] {
        var out: [(Int, Int)] = []
        for dx in -r ... r { for dy in -r ... r { out.append((x + dx, y + dy)) } }
        return openOnly(out)
    }

    /// BFS distances (bot-walkable tiles) from Nori's tile, cached per tile + door state.
    func noriDist() -> [Int: Int] {
        let t = nori.tile()
        let k = key(t.0, t.1) * 2 + doorPhase
        if k != ndistKey {
            ndistKey = k
            ndist = bfsTiles(self, t, "bot")
        }
        return ndist
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        switch state {
        case "intro":
            boss?.update(dt)
            if stateT > introLen || (stateT > 0.5 && app.input.hit(.a)) {
                state = "play"
                stateT = 0
                if let bo = boss, bo.state == "enter" { bo.y = 8; bo.state = "idle" }
            }
        case "play":
            play(dt)
        case "dying":
            if stateT > 1.5 { afterDeath() }
        case "ready":
            if stateT > 1.0 { state = "play"; stateT = 0 }
        case "clear":
            boss?.update(dt)
            if stateT > 1.8 { beginTally() }
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(WM_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        default: break
        }
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = WM_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id]!)", color: u.color, dur: 1.2, scale: 1)
        }
        if id == "life" { lives += 1; app.audio.play("extra") } else if id == "collar" { collar += 1 } else if id == "fever" {
            hype.feverTime = 8.0 + 1.5 * Double(lv("fever"))
        }
    }

    func play(_ dt: Double) {
        stime += dt
        invuln = max(0, invuln - dt)
        dashCd = max(0, dashCd - dt)
        dashT = max(0, dashT - dt)
        if zoomT > 0 {
            zoomT -= dt
            if zoomT <= 0 { endZoomy() }
        }
        stageCombo = max(stageCombo, hype.combo)
        if streakT > 0 {
            streakT -= dt
            if streakT <= 0 { streak = 0 }
        }
        readInput(dt)
        moveNori(dt)
        if state != "play" { return }
        updateDoors(dt)
        for (k, v) in wet {
            if v - dt <= 0 { wet[k] = nil } else { wet[k] = v - dt }
        }
        updateBots(dt)
        if state != "play" { return }
        updateItems(dt)
        updateShots(dt)
        updateHazards(dt)
        if boss != nil && state == "play" { updateBoss(dt) }
        if st.kind == "bonus" && state == "play" {
            bonusLeft -= dt
            if bonusLeft <= 0 { bonusLeft = 0; stageClear() }
        }
        checkLife()
    }

    // ---------------------------------------------------------------- Nori
    func readInput(_ dt: Double) {
        let inp = app.input
        for (a, d) in DIRS where inp.hit(a) {
            lastKey = a
            want = d
            wantT = BUFFER + 0.1 * Double(lv("speed"))
        }
        let held = DIRS.filter { inp.down($0.0) }
        if !held.isEmpty {
            let pick = held.first { $0.0 == lastKey } ?? held[0]
            want = pick.1
            wantT = BUFFER
        } else {
            wantT -= dt
            if wantT <= 0 { want = nil }
        }
        if inp.hit(.a) && dashCd <= 0 && (!nori.dir.isZero || want != nil) {
            dashT = 0.45 + 0.1 * Double(lv("dash"))
            dashCd = 5.0 - 0.9 * Double(lv("dash"))
            app.audio.play("jump")
            parts.burst(tpx(nori.x), tpy(nori.y), 8, ["white", "sky", "lavender"], 50, 0.4)
        }
    }

    func noriSpeed() -> Double {
        var v = NORI_SPEED * (1 + 0.06 * Double(lv("speed")))
        if zoomy { v *= 1.22 }
        if dashT > 0 { v *= 1.7 }
        if st.kind == "bonus" { v *= 1.15 }
        let (tx, ty) = nori.tile()
        if isWet(tx, ty) { v *= 1.25 }
        return v
    }

    func noriChoose(_ m: WMMover, _ tx: Int, _ ty: Int) -> WD? {
        if isWet(tx, ty) && !m.dir.isZero && walk(tx + m.dir.x, ty + m.dir.y, "cat") { return m.dir }  // sliding: no turning
        if let w = want, walk(tx + w.x, ty + w.y, "cat") { return w }
        if !m.dir.isZero && walk(tx + m.dir.x, ty + m.dir.y, "cat") { return m.dir }
        return nil
    }

    func moveNori(_ dt: Double) {
        let n = nori
        var (tx, ty) = n.tile()
        let wetHere = isWet(tx, ty)
        if let w = want, !n.dir.isZero, !wetHere {
            if w == n.dir.rev {
                n.dir = w                          // reverse at once
                n.face = w
            } else if w != n.dir {                // corner assist: snap onto a nearby junction and turn
                let cx = rnd(n.x), cy = rnd(n.y)
                if abs(n.x - Double(cx)) + abs(n.y - Double(cy)) <= ASSIST && walk(cx + w.x, cy + w.y, "cat") {
                    n.x = Double(cx); n.y = Double(cy)
                    n.dir = w
                    n.face = w
                }
            }
        }
        advance(n, noriSpeed() * dt, "cat") { [unowned self] m, x, y in self.noriChoose(m, x, y) }
        if !n.dir.isZero { n.face = n.dir }
        (tx, ty) = n.tile()
        scent[key(tx, ty)] = stime
        if food[key(tx, ty)] != nil { eat(tx, ty) }
        let wl = lv("whisker")
        if wl > 0 && abs(n.x - Double(rnd(n.x))) + abs(n.y - Double(rnd(n.y))) < 0.2 {
            var reach = WM_D4.map { (tx + $0.x, ty + $0.y) }
            if wl >= 2 && !n.dir.isZero { reach.append((tx + 2 * n.dir.x, ty + 2 * n.dir.y)) }
            for (x, y) in reach where y >= 0 && y < ROWS {
                if let f = food[key(x, y)], f == "c" || f == "f", walk(x, y, "cat") {
                    eat(wrapX(x), y, whisker: true)
                    if state != "play" { return }
                }
            }
        }
    }

    /// Move m along the tile grid by dist tiles, calling choose(m, tx, ty) -> dir at every tile centre.
    func advance<M: WMMover>(_ m: M, _ dist0: Double, _ who: String, _ choose: (M, Int, Int) -> WD?) {
        var dist = dist0
        for _ in 0 ..< 8 {
            if dist <= 1e-6 { return }
            let tx = rnd(m.x), ty = rnd(m.y)
            if abs(m.x - Double(tx)) < 1e-6 && abs(m.y - Double(ty)) < 1e-6 {
                m.x = Double(tx); m.y = Double(ty)
                guard let d = choose(m, wrapX(tx), ty), !d.isZero, walk(tx + d.x, ty + d.y, who) else {
                    m.dir = .zero
                    return
                }
                m.dir = d
            }
            let d = m.dir
            if d.isZero { return }
            var step = 0.0
            if d.x != 0 {
                let target = d.x > 0 ? floor(m.x + 1e-9) + 1 : ceil(m.x - 1e-9) - 1
                step = min(dist, abs(target - m.x))
                m.x += Double(d.x) * step
                if abs(m.x - target) < 1e-6 { m.x = target }
            } else {
                let target = d.y > 0 ? floor(m.y + 1e-9) + 1 : ceil(m.y - 1e-9) - 1
                step = min(dist, abs(target - m.y))
                m.y += Double(d.y) * step
                if abs(m.y - target) < 1e-6 { m.y = target }
            }
            dist -= step
            if m.x < -0.5 { m.x += Double(COLS) } else if m.x > Double(COLS) - 0.5 { m.x -= Double(COLS) }
        }
    }

    // ---------------------------------------------------------------- eating
    func eat(_ x: Int, _ y: Int, whisker: Bool = false) {
        guard let kind = food.removeValue(forKey: key(x, y)) else { return }
        let au = app.audio
        let px = tpx(Double(x)), py = tpy(Double(y))
        if kind == "c" || kind == "f" {
            crumbsLeft -= 1
            eaten += 1
            streak += 1
            streakT = 0.8
            bestStreak = max(bestStreak, streak)
            if kind == "f" {
                let combo = hype.hit(1, fever: 0.01)
                if combo % 5 == 0 { scoreAt(50 + 5 * min(combo, 40), px, py - 4, "peach") } else { scoreAt(50 + 5 * min(combo, 40)) }
                parts.burst(px, py, 4, ["cream", "peach", "white"], 30, 0.3)
            } else {
                hype.feverAdd(0.0045 * (1 + 0.35 * Double(lv("fever"))))
                scoreAt(10 + 5 * min(streak / 20, 4))
                if [50, 100, 150, 200].contains(streak) {
                    floats.add(px, py - 10, "STREAK \(streak)!", "cream")
                    au.play("combo")
                }
            }
            if whisker { parts.sparkle(px, py, "white") }
            if eaten % 2 == 0 { au.play("eat") }
            wakeSnoozers(x, y)
            checkSpawns()
            if crumbsLeft <= 0 {
                if boss != nil { refill() } else { stageClear() }
            }
        } else if kind == "s" {
            secrets += 1
            scoreAt(300, px, py - 6, "yellow")
            hype.hit(1, fever: 0.04)
            au.play("fruit")
            parts.burst(px, py, 10, ["yellow", "white"], 40, 0.5)
        } else if kind == "o" {
            scoreAt(50)
            startZoomy(st.nip + 1.5 * Double(lv("nip")))
        }
    }

    /// Boss stages: the crumbs come back so the fight never runs dry.
    func refill() {
        for (y, row) in st.rows.enumerated() {
            for (x, ch) in row.enumerated() where ch == "." || ch == "~" { food[key(x, y)] = "c" }
        }
        total = food.values.filter { $0 == "c" }.count
        crumbsLeft = total
        hype.banner("FRESH CRUMBS!", color: "cream", dur: 1.2, scale: 1, sound: "bonus")
    }

    func checkSpawns() {
        if st.kind != "normal" || st.spots.isEmpty { return }
        let f = Double(eaten) / Double(max(1, total))
        for (k, at, kind) in [("tuna1", 0.33, "tuna"), ("tuna2", 0.72, "tuna"), ("gold", 0.2, "gold"), ("bell", 0.5, "bell"),
                              ("milk", 0.6, "milk")] {
            if spawned.contains(k) || f < at { continue }
            spawned.insert(k)
            if kind == "gold" && !luckyGold { continue }
            if kind == "milk" && !luckyMilk { continue }
            if kind == "bell" && !(st.bell && Double.random(in: 0 ..< 1) < 0.6 + 0.1 * Double(lv("luck"))) { continue }
            let nt = nori.tile()
            let sp = st.spots.filter { abs($0.0 - nt.0) + abs($0.1 - nt.1) >= 6 && food[key($0.0, $0.1)] == nil }
            guard let (x, y) = sp.randomElement() else { continue }
            let life = ["tuna": 9.0 + 2 * Double(lv("tuna")), "gold": 8.0, "bell": 10.0, "milk": 10.0][kind]!
            items.append(WMItem(kind, x, y, life))
            parts.burst(tpx(Double(x)), tpy(Double(y)), 10, ["white", "yellow"], 40, 0.5)
            if kind == "gold" { hype.banner("GOLDEN FISH!", "GRAB IT FAST!", color: "yellow", dur: 1.4, scale: 1, sound: "coin") }
        }
    }

    func wakeSnoozers(_ x: Int, _ y: Int) {
        let r = 3 - (lv("bell") >= 2 ? 1 : 0)
        for b in bots where b.kind == "snoozy" && b.state == "sleep" && !zoomy {
            let (bx, by) = b.tile()
            if abs(bx - x) + abs(by - y) <= r { wake(b) }
        }
    }

    func wake(_ b: WMBot) {
        b.state = "roam"
        b.mode = "alert"
        b.timer = 0.6
        floats.add(tpx(b.x), tpy(b.y) - 12, "!", "red")
        app.audio.play("hold")
    }

    // ---------------------------------------------------------------- zoomies
    func startZoomy(_ dur: Double) {
        zoomT = dur
        chain = 0
        for b in bots where ["roam", "leave", "sleep"].contains(b.state) && b.kind != "mouse" {
            b.dizzy = true
            b.spin = 0.35
        }
        app.audio.play("powerup")
        hype.banner("ZOOMIES!", color: "mint", dur: 0.9, scale: 1)
        parts.burst(tpx(nori.x), tpy(nori.y), 16, ["lime", "mint", "white"], 70, 0.6)
    }

    func endZoomy() {
        zoomT = 0
        for b in bots { b.dizzy = false }
    }

    // ---------------------------------------------------------------- doors
    func updateDoors(_ dt: Double) {
        if !st.feats.contains("doors") { return }
        doorT -= dt
        if doorT > 0 { return }
        let closing: Character = doorPhase == 0 ? "d" : "D"      // the group that is open now closes
        var busy = Set<Int>()
        let movers: [WMMover] = [nori] + bots.filter { ["roam", "leave", "puck"].contains($0.state) }
        for m in movers {
            let (tx, ty) = m.tile()
            busy.insert(key(tx, ty))
            busy.insert(key(tx + m.dir.x, ty + m.dir.y))
        }
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS where walls[y][x] == closing && busy.contains(key(x, y)) { return }   // someone is in the doorway
        }
        doorPhase = 1 - doorPhase
        doorT = st.doorT
        app.audio.play("lock")
    }

    // ---------------------------------------------------------------- bots
    func botSpeed(_ b: WMBot) -> Double {
        var base = NORI_SPEED * st.speed * dspeed * (KIND_SPEED[b.kind] ?? 1)
        if b.kind == "mouse" { return NORI_SPEED * 0.74 }
        if b.state == "leave" { return base * 0.6 }
        if b.dizzy { return base * 0.55 }
        switch (b.kind, b.mode) {
        case ("sniffy", _):
            let (tx, ty) = b.tile()
            if stime - (scent[key(tx, ty)] ?? -99) < 1.5 { base *= 1.08 }
        case ("fridgy", "chase"): base *= 1.22
        case ("snoozy", "chase"): base *= 1.12
        case ("snoozy", "drowsy"): base *= 0.6
        case ("ruff", "dash"): base *= 1.45
        default: break
        }
        return base
    }

    func updateBots(_ dt: Double) {
        for b in bots {
            if b.state == "gone" { continue }
            b.frozen = max(0, b.frozen - dt)
            b.cd = max(0, b.cd - dt)
            if b.state == "dock" {
                b.timer -= dt
                if b.timer <= 0 { b.state = "leave"; b.dizzy = false }
                continue
            }
            if b.state == "reboot" {
                let dx = Double(DOCK.0) - b.x, dy = Double(DOCK.1) - b.y
                let d = (dx * dx + dy * dy).squareRoot()
                let step = 12 * dt
                if d <= step {
                    b.x = Double(DOCK.0); b.y = Double(DOCK.1)
                    b.state = "dock"
                    b.timer = 2.0
                    b.dir = .zero
                    b.mode = ""
                } else {
                    b.x += dx / d * step
                    b.y += dy / d * step
                }
                continue
            }
            if b.state == "puck" { updatePuck(b, dt); continue }
            if b.life > 0 {
                b.life -= dt
                if b.life <= 0 {
                    parts.burst(tpx(b.x), tpy(b.y), 10, ["gray", "white"], 40, 0.4)
                    b.state = "gone"
                    continue
                }
            }
            if b.state == "sleep" || b.frozen > 0 { continue }
            if b.spin > 0 { b.spin -= dt; continue }
            // timed modes that stand still
            if ["alert", "aim", "bark", "tired"].contains(b.mode) {
                b.timer -= dt
                if b.timer > 0 { continue }
                switch b.mode {
                case "alert": b.mode = "chase"; b.timer = 6.0
                case "aim":
                    b.mode = ""
                    b.cd = 2.6
                    let d = b.face
                    mists.append(WMMist(b.x + Double(d.x) * 0.5, b.y + Double(d.y) * 0.5, d.x, d.y))
                    app.audio.play("shoot")
                case "bark": b.mode = "dash"; b.timer = 1.8
                default: b.mode = ""; b.cd = 2.5
                }
            } else if ["chase", "drowsy", "dash"].contains(b.mode) && (b.kind == "snoozy" || b.kind == "ruff") {
                b.timer -= dt
                if b.timer <= 0 {
                    if b.kind == "ruff" {
                        if b.mode == "dash" { b.mode = "tired"; b.timer = 1.6 }
                    } else if b.mode == "chase" {
                        b.mode = "drowsy"; b.timer = 1.6
                    } else {
                        snooze(b)
                        continue
                    }
                }
            }
            advance(b, botSpeed(b) * dt, b.state == "leave" ? "dock" : "bot") { [unowned self] m, x, y in self.botChoose(m, x, y) }
            if !b.dir.isZero { b.face = b.dir }
        }
        bots.removeAll { $0.state == "gone" }
        botTouch()
    }

    func snooze(_ b: WMBot) {
        b.mode = ""
        let cx = rnd(b.x), cy = rnd(b.y)
        if walk(cx, cy, "bot") {
            b.x = Double(cx); b.y = Double(cy)
            b.state = "sleep"
            b.dir = .zero
        }
    }

    func botChoose(_ b: WMBot, _ tx: Int, _ ty: Int) -> WD? {
        if b.prev == nil || b.prev! != (tx, ty) {
            if b.kind == "mopsy", let p = b.prev, walls[p.1][p.0] == " " { wet[key(p.0, p.1)] = 5.0 }
            b.prev = (tx, ty)
        }
        if b.state == "leave" {
            if ty == DOCK.1 && tx != DOCK.0 { return WD(tx < DOCK.0 ? 1 : -1, 0) }
            if tx == EXIT.0 && ty == EXIT.1 {
                b.state = "roam"
                if b.kind == "snoozy" { b.mode = "chase"; b.timer = 4.0 } else if b.kind == "fridgy" { b.mode = "return" }
                return Bool.random() ? WD(1, 0) : WD(-1, 0)
            }
            return WD(0, -1)
        }
        var opts = WM_D4.filter { walk(tx + $0.x, ty + $0.y, "bot") }
        if opts.isEmpty { return nil }
        let back = b.dir.rev
        if opts.count > 1, let i = opts.firstIndex(of: back) { opts.remove(at: i) }
        let nd = noriDist()
        func nd0(_ d: WD, _ dflt: Int) -> Int { nd[key(tx + d.x, ty + d.y)] ?? dflt }
        func toward() -> WD { opts.shuffled().min { nd0($0, 999) < nd0($1, 999) }! }
        func wander(_ straight: Double = 0.55) -> WD {
            if opts.contains(b.dir) && Double.random(in: 0 ..< 1) < straight { return b.dir }
            return opts.randomElement()!
        }
        if b.kind == "mouse" || b.dizzy {
            if Double.random(in: 0 ..< 1) < 0.25 { return opts.randomElement()! }
            return opts.shuffled().max { nd0($0, 0) < nd0($1, 0) }!
        }
        let nt = nori.tile()
        switch b.kind {
        case "sniffy":
            var best: WD?
            var bt = stime - scentLife()
            for d in opts {
                let v = scent[key(tx + d.x, ty + d.y)] ?? -99
                if v > bt { best = d; bt = v }
            }
            if let bd = best { return bd }
            return Double.random(in: 0 ..< 1) < 0.25 ? toward() : wander()
        case "zig":
            if opts.count == 1 { return opts[0] }
            if Double.random(in: 0 ..< 1) < 0.3 + 0.015 * Double(tier) { return toward() }
            let left = WD(b.dir.y, -b.dir.x), right = WD(-b.dir.y, b.dir.x)
            let order = b.lastTurn > 0 ? [left, right] : [right, left]
            for d in order where opts.contains(d) && !d.isZero {
                b.lastTurn = -b.lastTurn
                return d
            }
            return opts.contains(b.dir) ? b.dir : opts.randomElement()!
        case "fridgy":
            let r = max(3, 6 - lv("bell"))
            let pd = b.postDist
            let npd = pd[key(nt.0, nt.1)] ?? 99
            if b.mode == "patrol" && npd <= r {
                b.mode = "chase"
                floats.add(tpx(b.x), tpy(b.y) - 12, "!", "red")
            } else if b.mode == "chase" && npd > r + 3 {
                b.mode = "return"
            } else if b.mode == "return" && (pd[key(tx, ty)] ?? 99) <= 1 {
                b.mode = "patrol"
            }
            func pdd(_ d: WD) -> Int { pd[key(tx + d.x, ty + d.y)] ?? 99 }
            if b.mode == "chase" { return toward() }
            if b.mode == "return" || b.mode.isEmpty { return opts.shuffled().min { pdd($0) < pdd($1) }! }
            let near = opts.filter { pdd($0) <= 4 }
            return near.randomElement() ?? opts.min { pdd($0) < pdd($1) }!
        case "snoozy":
            return b.mode == "chase" ? toward() : wander(0.4)
        case "spritz":
            if b.cd <= 0 && b.mode.isEmpty && lineOfSight((tx, ty), nt) {
                b.mode = "aim"
                b.timer = 0.55
                b.face = WD(sgn(nt.0 - tx), sgn(nt.1 - ty))
                floats.add(tpx(b.x), tpy(b.y) - 12, "!", "red")
                return nil
            }
            return Double.random(in: 0 ..< 1) < 0.3 ? toward() : wander(0.5)
        case "ruff":
            if b.mode == "dash" { return toward() }
            let det = 7 - lv("bell")
            if b.mode.isEmpty && b.cd <= 0 && (nd[key(tx, ty)] ?? 99) <= det {
                b.mode = "bark"
                b.timer = 0.45
                floats.add(tpx(b.x), tpy(b.y) - 12, "WOOF!", "orange")
                app.audio.play("pop")
                return nil
            }
            return wander(0.6)
        case "bunny":
            return Double.random(in: 0 ..< 1) < 0.8 ? toward() : wander()
        default:
            return wander(0.6)    // mopsy
        }
    }

    func lineOfSight(_ a: (Int, Int), _ b: (Int, Int)) -> Bool {
        if a == b { return false }
        if a.1 == b.1 && abs(a.0 - b.0) <= 9 {
            let s = sgn(b.0 - a.0)
            return stride(from: a.0 + s, to: b.0, by: s).allSatisfy { see($0, a.1) }
        }
        if a.0 == b.0 && abs(a.1 - b.1) <= 9 {
            let s = sgn(b.1 - a.1)
            return stride(from: a.1 + s, to: b.1, by: s).allSatisfy { see(a.0, $0) }
        }
        return false
    }

    func botTouch() {
        let n = nori
        for b in bots {
            if ["dock", "reboot", "puck", "gone"].contains(b.state) { continue }
            if distWrap(n.x, n.y, b.x, b.y) > 0.72 { continue }
            if b.kind == "mouse" { catchMouse(b); continue }
            if b.dizzy && zoomy {
                bat(b)
            } else if b.state == "sleep" {
                if !zoomy { wake(b) }
            } else if b.harmful() {
                noriHit(b)
                if state != "play" { return }
            }
        }
        bots.removeAll { $0.state == "gone" }
    }

    func bat(_ b: WMBot) {
        let n = nori
        let d = n.dir.isZero ? n.face : n.dir
        chain += 1
        batted += 1
        let pts = 200 * (1 << min(chain - 1, 5))
        let got = scoreAt(pts, tpx(b.x), tpy(b.y) - 8, "white")
        b.state = "puck"
        b.dizzy = false
        b.x = Double(rnd(b.x)); b.y = Double(rnd(b.y))     // snap onto the grid: it slides from a tile centre
        b.dir = d
        b.timer = 2.5
        b.hits = 0
        b.spin = 0
        b.mode = ""
        hype.hit(1, fever: 0.08 * (1 + 0.35 * Double(lv("fever"))))
        hype.hitstop(0.07)
        app.shake(2, 0.15)
        app.audio.play("pop")
        parts.burst(tpx(b.x), tpy(b.y), 12, ["white", "yellow", "sky"], 70, 0.5)
        if got >= 3200 { hype.banner("WHAM!", "+\(got)", color: "yellow", dur: 1.0, scale: 2) }
    }

    func updatePuck(_ b: WMBot, _ dt: Double) {
        advance(b, 16 * dt, "bot") { [unowned self] m, x, y in
            self.walk(x + m.dir.x, y + m.dir.y, "bot") ? m.dir : nil
        }
        if Int(t * 60) % 2 == 0 { parts.sparkle(tpx(b.x), tpy(b.y), "white") }
        for o in bots {
            if o === b || ["dock", "reboot", "puck", "gone"].contains(o.state) || o.kind == "mouse" { continue }
            if distWrap(b.x, b.y, o.x, o.y) < 0.85 {
                b.hits += 1
                chain += 1
                batted += 1
                let pts = 200 * (1 << min(chain - 1, 5))
                scoreAt(pts, tpx(o.x), tpy(o.y) - 8, "white")
                o.state = o.kind == "bunny" ? "gone" : "reboot"
                o.dizzy = false
                o.mode = ""
                hype.hit(1, fever: 0.08)
                hype.hitstop(0.09)
                app.audio.play("explode")
                parts.burst(tpx(o.x), tpy(o.y), 18, ["yellow", "white", "orange"], 80, 0.6)
                if b.hits == 2 {
                    hype.banner("STRIKE!", "DOUBLE KNOCK", color: "orange", dur: 1.2, sound: "combo")
                    app.shake(3, 0.25)
                } else if b.hits == 3 {
                    hype.banner("SUPER STRIKE!!", "\(b.hits) BOTS IN A ROW", dur: 1.8, rainbow: true, sound: "fever")
                    hype.slowmo(0.35, 0.8)
                    hype.shower(40, "stars")
                    app.shake(5, 0.4)
                    scoreAt(5000, Double(W / 2), 90)
                }
            }
        }
        b.timer -= dt
        if b.dir.isZero || b.timer <= 0 {          // hit a wall: clonk, then fly home to reboot
            b.state = b.kind == "bunny" ? "gone" : "reboot"
            app.audio.play("tin")
            parts.burst(tpx(b.x), tpy(b.y), 8, ["gray", "white"], 40, 0.4)
        }
    }

    func catchMouse(_ b: WMBot) {
        b.state = "gone"
        miceCaught += 1
        let combo = hype.hit(1, fever: 0.12)
        scoreAt(300 + 50 * min(combo, 20), tpx(b.x), tpy(b.y) - 8, "pink")
        app.audio.play("pop")
        parts.burst(tpx(b.x), tpy(b.y), 14, ["gray", "pink", "white"], 60, 0.5)
        if miceCaught >= miceTotal {
            hype.banner("ALL CAUGHT!", "PURR-FECT PARTY", dur: 1.8, rainbow: true, sound: "jackpot")
            hype.shower(50, "confetti")
            stageClear()
        }
    }

    func spawnBunny() {
        guard let bo = boss else { return }
        let (bx, by) = bo.tile()
        var cand: [(Int, Int)] = []
        for dx in -2 ... 2 { for dy in -2 ... 2 { cand.append((bx + dx, by + dy)) } }
        cand = openOnly(cand).filter { walk($0.0, $0.1, "bot") }
        if cand.isEmpty || bots.filter({ $0.kind == "bunny" }).count >= 5 { return }
        let (x, y) = cand.randomElement()!
        let b = WMBot("bunny", x, y)
        b.state = "roam"
        b.life = 8.0
        if zoomy { b.dizzy = true }
        bots.append(b)
        parts.burst(tpx(Double(x)), tpy(Double(y)), 8, ["gray", "white"], 40, 0.4)
    }

    // ---------------------------------------------------------------- items, shots, hazards
    func updateItems(_ dt: Double) {
        let n = nori
        for it in items {
            it.life -= dt
            if it.life <= 0 { continue }
            if distWrap(n.x, n.y, Double(it.x), Double(it.y)) < 0.7 {
                it.life = 0
                take(it)
            }
        }
        items.removeAll { $0.life <= 0 }
        if boss != nil && state == "play" {
            let hasNip = food.values.contains("o")
            if !hasNip && !zoomy {
                nipSpawn -= dt
                if nipSpawn <= 0 {
                    let nt = n.tile()
                    let far = st.nips.sorted { abs($0.0 - nt.0) + abs($0.1 - nt.1) > abs($1.0 - nt.0) + abs($1.1 - nt.1) }
                    let (x, y) = far.count > 2 ? far[1 + nipCount % 2] : far[0]
                    nipCount += 1
                    food[key(x, y)] = "o"
                    nipSpawn = 7.0
                    parts.burst(tpx(Double(x)), tpy(Double(y)), 14, ["lime", "mint", "white"], 50, 0.6)
                    app.audio.play("bubble")
                }
            }
        }
    }

    func take(_ it: WMItem) {
        let px = tpx(Double(it.x)), py = tpy(Double(it.y))
        switch it.kind {
        case "tuna":
            let pts = Int(Double(500 + 250 * tier) * (1 + 0.5 * Double(lv("tuna"))))
            add(pts, px, py - 8, "sky")
            hype.hit(1, fever: 0.15)
            app.audio.play("fruit")
            parts.burst(px, py, 16, ["sky", "white", "blue"], 60, 0.6)
            floats.add(px, py - 18, "TUNA!", "white")
        case "bell":
            for b in bots where b.state == "roam" || b.state == "leave" { b.frozen = 3.0 }
            hype.banner("JINGLE!", "THE BOTS FREEZE", color: "yellow", dur: 1.2, scale: 1, sound: "bonus")
            hype.flash("yellow", 0.15)
        case "gold":
            golds += 1
            if st.kind == "bonus" {
                scoreAt(2000, px, py - 8, "yellow")
                hype.hit(1, fever: 0.2)
                app.audio.play("coin")
                parts.burst(px, py, 16, ["yellow", "white"], 60, 0.6)
            } else {
                hype.jackpot(factorPts(5000), sub: "GOLDEN FISH!")
            }
        case "milk":
            lives += 1
            hype.banner("MILK!", "+1 LIFE", color: "white", dur: 1.4, scale: 2, sound: "extra")
            hype.shower(16, "hearts")
        default: break
        }
    }

    func updateShots(_ dt: Double) {
        let n = nori
        var keep: [WMMist] = []
        for (i, m) in mists.enumerated() {
            m.x += Double(m.dx) * 11 * dt
            m.y += Double(m.dy) * 11 * dt
            let tx = rnd(m.x), ty = rnd(m.y)
            if ty < 0 || ty >= ROWS || !see(tx, ty) {
                parts.burst(tpx(m.x), tpy(m.y), 6, ["sky", "white"], 30, 0.3)
                continue
            }
            if distWrap(n.x, n.y, m.x, m.y) < 0.6 && !zoomy {
                mists = keep + mists[(i + 1)...]
                noriHit(nil)
                return
            }
            keep.append(m)
        }
        mists = keep
        var keepS: [WMShot] = []
        for (i, sh) in shots.enumerated() {
            sh.x += sh.vx * dt
            sh.y += sh.vy * dt
            sh.life -= dt
            if sh.life <= 0 || !(sh.x > -1 && sh.x < Double(COLS) && sh.y > -1 && sh.y < Double(ROWS)) { continue }
            if distWrap(n.x, n.y, sh.x, sh.y) < 0.65 {
                shots = keepS + shots[(i + 1)...]
                noriHit(nil)
                return
            }
            keepS.append(sh)
        }
        shots = keepS
    }

    func addHazard(_ tiles: [(Int, Int)], _ warn: Double, _ active: Double, _ style: String) {
        hazards.append(WMHazard(tiles, warn, active, style))
    }

    func addTraps(_ k: Int) {
        let nt = nori.tile()
        var cand: [(Int, Int)] = []
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS where (walls[y][x] == " " || walls[y][x] == "~") {
                let d = abs(x - nt.0) + abs(y - nt.1)
                if d >= 2 && d <= 6 { cand.append((x, y)) }
            }
        }
        for p in cand.shuffled().prefix(k) { addHazard([p], 0.8, 9.0, "trap") }
    }

    func updateHazards(_ dt: Double) {
        let nt = nori.tile()
        for h in hazards {
            h.t += dt
            if h.t > h.warn + h.active || h.t < h.warn { continue }
            if h.style == "wet" {
                for p in h.tiles { wet[key(p.0, p.1)] = max(wet[key(p.0, p.1)] ?? 0, h.warn + h.active - h.t) }
                continue
            }
            if h.t - dt < h.warn && ["stomp", "pop", "splash"].contains(h.style) { app.shake(3, 0.2) }
            if h.tiles.contains(where: { $0 == nt }) && invuln <= 0 {
                if h.style == "trap" {
                    h.t = 999
                    app.audio.play("brick")
                }
                noriHit(nil)
                if state != "play" { break }
            }
        }
        hazards.removeAll { $0.t > $0.warn + $0.active }
    }

    func updateBoss(_ dt: Double) {
        guard let bo = boss else { return }
        bo.update(dt)
        let n = nori
        if ["dead", "air", "enter"].contains(bo.state) { return }
        let dx = n.x - bo.x, dy = n.y - bo.y
        if (dx * dx + dy * dy).squareRoot() < 1.45 {
            if zoomy && bo.state != "stun" {
                let dmg = 1 + lv("power")
                hype.hitstop(0.12)
                hype.flash("white", 0.15)
                app.shake(4, 0.3)
                app.audio.play("explode")
                parts.burst(tpx(bo.x), tpy(bo.y), 24, ["white", "yellow", "pink"], 90, 0.7)
                scoreAt(1000, tpx(bo.x), tpy(bo.y) - 16, "white")
                hype.hit(1, fever: 0.12)
                n.dir = n.dir.isZero ? WD(0, 1) : n.dir.rev
                if bo.hurt(dmg) {
                    bossDefeated()
                } else {
                    hype.banner("POUNCE!", "\(bo.hp) TO GO", color: "hotpink", dur: 0.9, scale: 1)
                    if bo.phase >= 2 && Double(bo.hp + dmg) > Double(bo.maxhp) * (bo.phase == 2 ? 0.67 : 0.34) {
                        hype.banner("BOSS ANGRY!", color: "red", dur: 1.0, scale: 1, sound: "warning")
                    }
                }
            } else if bo.state != "stun" {
                noriHit(nil)
            }
        }
    }

    // ---------------------------------------------------------------- getting caught
    func noriHit(_ bot: WMBot?) {
        if invuln > 0 || state != "play" { return }
        if collar > 0 {
            collar -= 1
            invuln = 2.0
            hype.banner("JINGLE SAVE!", "COLLAR x\(collar)", color: "red", dur: 1.2, scale: 1, sound: "tin")
            app.shake(3, 0.2)
            bot?.frozen = 1.5
            return
        }
        missed = true
        hype.breakCombo()
        state = "dying"
        stateT = 0
        app.audio.play("hurt")
        app.shake(4, 0.35)
        app.audio.music(nil)
    }

    func afterDeath() {
        let au = app.audio
        lives -= 1
        if lives <= 0 {
            state = "over"
            hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
            au.play("gameover")
            endGame(false, "STAGE \(n)", delay: 2.5)
            return
        }
        au.play("die")
        resetPositions()
        invuln = 1.2
        state = "ready"
        stateT = 0
        au.music(song())
    }

    func checkLife() {
        let k = lifeI
        let target = k < LIFE_AT.count ? LIFE_AT[k] : LIFE_AT.last! + 80000 * (k - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("BONUS LIFE!", "\(target) POINTS", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    // ---------------------------------------------------------------- clear / tally
    func stageClear() {
        if state != "play" { return }
        state = "clear"
        stateT = 0
        endZoomy()
        mists = []; shots = []; hazards = []
        if hype.feverOn { hype.feverT = 0 }
        hype.slowmo(0.3, 0.9)
        app.audio.play("win")
        app.audio.music(nil)
        for b in bots where b.state != "dock" {
            parts.burst(tpx(b.x), tpy(b.y), 10, ["white", "lavender", "yellow"], 50, 0.6)
        }
        if st.kind == "normal" {
            bots = []
            hype.banner("ROOM CLEAR!", "MRRRP!", color: "mint", dur: 1.6)
            hype.shower(30, "confetti")
        }
        if st.kind != "bonus" && !missed {
            hype.banner("PURR-FECT!", "NOT A WHISKER TOUCHED", dur: 1.7, rainbow: true, sound: "fever")
            hype.shower(40, "stars")
        } else if st.kind == "bonus" {
            hype.banner(bonusLeft <= 0 ? "TIME UP!" : "BONUS CLEAR!", color: "yellow", dur: 1.4)
        }
    }

    func bossDefeated() {
        guard let bo = boss else { return }
        app.audio.play("bossdown")
        hype.banner("BOSS DOWN!", bo.name, dur: 2.2, rainbow: true, scale: 2)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        app.shake(6, 0.6)
        scoreAt(15000, Double(W / 2), 80)
        for _ in 0 ..< 4 { parts.burst(tpx(bo.x), tpy(bo.y), 20, ["white", "yellow", "orange", "pink"], 120, 1.0) }
        bots = []
        stageClear()
        hype.slowmo(0.3, 1.2)
    }

    func beginTally() {
        let f = factorPts
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("ROOM CLEAR", f(1000)))
            let par = 30 + 0.32 * Double(total)
            rows.append(("TIME BONUS", f(max(0, Int(par - stime)) * 25)))
            rows.append(("BOTS BATTED x\(batted)", f(batted * 150)))
            if secrets > 0 || st.feats.contains("paw") { rows.append(("SECRET TREATS x\(secrets)", f(secrets * 250))) }
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", f(10000 + 2000 * tier)))
            rows.append(("TIME BONUS", f(max(0, Int(120 - stime)) * 50)))
        } else if st.bonus == "mice" {
            rows.append(("MICE x\(miceCaught)/\(miceTotal)", f(miceCaught * 200)))
            rows.append(("ALL CAUGHT", miceCaught >= miceTotal ? f(10000) : 0))
        } else {
            rows.append(("FISH TREATS x\(eaten)", f(eaten * 20)))
            rows.append(("GOLDEN FISH x\(golds)", f(golds * 500)))
            rows.append(("ALL EATEN", crumbsLeft <= 0 ? f(10000) : 0))
        }
        if st.kind == "bonus" {
            rows.append(("BEST COMBO \(stageCombo)", f(stageCombo * 50)))
        } else {
            rows.append(("BEST STREAK \(bestStreak)", f(bestStreak * 10)))
            rows.append(("NO MISS", missed ? 0 : f(5000)))
        }
        tally = rows.map { (label: $0.0, v: $0.1, shown: 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
    }

    func updateTally(_ dt: Double) {
        let skip = stateT > 0.3 && app.input.hit(.a)
        if tallyI < tally.count {
            if skip {
                for i in tallyI ..< tally.count {
                    tally[i].shown = Double(tally[i].v)
                    if tally[i].v > 0 { add(tally[i].v) }
                }
                tallyI = tally.count
                app.audio.play("coin")
                return
            }
            let v = Double(tally[tallyI].v)
            tally[tallyI].shown = min(v, tally[tallyI].shown + max(1.0, v * dt / 0.4))
            if tally[tallyI].shown >= v {
                if tally[tallyI].v > 0 { add(tally[tallyI].v); app.audio.play("coin") }
                tallyI += 1
            }
        } else {
            tallyWait += dt
            if tallyWait > 1.6 || skip { finishStage() }
        }
    }

    func finishStage() {
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "THE CAT CASTLE IS YOURS", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "SNACK BREAK!"
            state = "pick"
        } else {
            startStage(n + 1)
        }
    }

    // ---------------------------------------------------------------- drawing
    func makeBg() -> Surface {
        let s = Surface(W, H, fill: col("black"))
        let ca = col(theme.fa), cb = col(theme.fb)
        var rng = SeededRNG(UInt64(n))
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS {
                let px = OX + x * TS, py = OY + y * TS
                let ch = walls[y][x]
                if ch == "#" || ch == "%" { continue }
                if ch == "=" || ch == "-" {
                    s.fillRect(col("night"), px, py, TS, TS)
                    if ch == "=" && x % 2 == 1 { s.fillRect(col("darkgray"), px + 2, py + 8, 6, 1) }
                    continue
                }
                switch theme.pat {
                case 0:
                    s.fillRect((x + y) % 2 == 1 ? ca : cb, px, py, TS, TS)
                case 1:
                    s.fillRect(ca, px, py, TS, TS)
                    s.fillRect(cb, px, py + 4, TS, 1)
                    s.fillRect(cb, px, py + 9, TS, 1)
                    if (x + y * 3) % 4 == 0 { s.fillRect(cb, px + 4, py, 1, 4) }
                case 2:
                    s.fillRect(ca, px, py, TS, TS)
                    if (x + y) % 2 == 0 { s.fillRect(cb, px + 4, py + 4, 2, 2) }
                case 3:
                    s.fillRect(ca, px, py, TS, TS)
                    s.fillRect(cb, px, py, TS, 1)
                    s.fillRect(cb, px, py, 1, TS)
                default:
                    s.fillRect(ca, px, py, TS, TS)
                    if Double.random(in: 0 ..< 1, using: &rng) < 0.25 {
                        let c = Double.random(in: 0 ..< 1, using: &rng) < 0.5 ? "lavender" : "white"
                        s.fillRect(col(c), px + Int.random(in: 1 ..< 9, using: &rng), py + Int.random(in: 1 ..< 9, using: &rng), 1, 1)
                    }
                }
            }
        }
        let cw = col(theme.wall), ct = col(theme.top), cs = col(theme.side), k = col("black")
        func solid(_ x: Int, _ y: Int) -> Bool { walls[y][x] == "#" || walls[y][x] == "%" }
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS where solid(x, y) {
                let px = OX + x * TS, py = OY + y * TS
                let up = y > 0 && !solid(x, y - 1)
                let down = y < ROWS - 1 && !solid(x, y + 1)
                let left = x > 0 && !solid(x - 1, y)
                let right = x < COLS - 1 && !solid(x + 1, y)
                s.fillRect(cw, px, py, TS, TS)
                if down {          // the cupboard front under the counter top
                    s.fillRect(cs, px, py + 6, TS, 4)
                    s.fillRect(k, px, py + TS - 1, TS, 1)
                    if (x * 7 + y) % 3 == 0 { s.fillRect(ct, px + 4, py + 7, 2, 1) }
                }
                if up { s.fillRect(ct, px, py, TS, 1) }
                if left { s.fillRect(k, px, py, 1, TS) }
                if right { s.fillRect(k, px + TS - 1, py, 1, TS) }
                if walls[y][x] == "%" { s.fillRect(cs, px + 1, py + 1, TS - 2, down ? 5 : TS - 2) }
            }
        }
        return s
    }

    override func render(_ s: Surface) {
        s.blit(bg, 0, 0)
        drawTiles(s, t)
        drawHazards(s, t)
        for it in items where it.life > 2 || Int(t * 8) % 2 == 1 {
            let sp = sprite("wm_" + it.kind)
            let bob = Int(sin(t * 5 + Double(it.x)))
            let cx = Int(tpx(Double(it.x))), cy = Int(tpy(Double(it.y)))
            s.blit(sp, cx - sp.w / 2, cy - sp.h / 2 + bob)
            if it.kind == "gold" && Int(t * 6) % 2 == 1 { s.fillRect(col("white"), cx + 4, cy - 5, 1, 1) }
        }
        for b in bots { drawBot(s, b, t) }
        if let bo = boss, bo.state != "dead" { drawBoss(s, bo, t) }
        if state != "clear" || boss == nil { drawNori(s, t) }
        for m in mists {
            let x = Int(tpx(m.x)), y = Int(tpy(m.y))
            for i in 0 ..< 3 { s.fillRect(col(i > 0 ? "sky" : "white"), x - m.dx * i * 3 - 1, y - m.dy * i * 3 - 1, 3 - i, 3 - i) }
        }
        for sh in shots {
            let x = Int(Double(OX) + sh.x * Double(TS) + Double(TS) / 2), y = Int(Double(OY) + sh.y * Double(TS) + Double(TS) / 2)
            if sh.style == "toast" {
                s.rect(col("black"), IRect(x - 4, y - 4, 9, 9), radius: 2)
                s.rect(col("peach"), IRect(x - 3, y - 3, 7, 7), radius: 2)
                s.fillRect(col("brown"), x - 3, y - 3, 7, 1)
            } else {
                s.circle(col("blue"), x, y, 3)
                s.circle(col("sky"), x, y - 1, 2)
                s.fillRect(col("white"), x - 1, y - 2, 1, 1)
            }
        }
        if st.dark && state != "clear" && state != "tally" { drawDark(s, t) }
        parts.draw(s)
        floats.draw(s)
        drawHud(s, t)
        if state == "intro" {
            drawIntro(s, t)
        } else if state == "tally" {
            drawTally(s, t)
        } else if state == "ready" {
            drawText(s, "GO, NORI!", W / 2, Int(tpy(Double(start.1))) - 22, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        }
    }

    func drawTiles(_ s: Surface, _ t: Double) {
        let fever = hype.feverOn
        let wall = col(theme.wall), side = col(theme.side)
        let near = nori.tile()
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS {
                let ch = walls[y][x]
                let px = OX + x * TS, py = OY + y * TS
                if ch == "D" || ch == "d" {
                    if doorOpen(ch) {
                        s.fillRect(side, px, py, 2, TS)
                        s.fillRect(side, px + TS - 2, py, 2, TS)
                    } else {
                        let warn = doorT < 0.8 && Int(t * 10) % 2 == 1
                        s.fillRect(col("black"), px, py, TS, TS)
                        s.rect(warn ? col("white") : wall, IRect(px + 1, py + 1, TS - 2, TS - 2), radius: 1)
                        s.fillRect(side, px + 2, py + 2, TS - 4, TS - 4)
                        s.fillRect(col("yellow"), px + TS - 4, py + 4, 1, 2)
                    }
                    if doorT < 0.8 && doorOpen(ch) && Int(t * 10) % 2 == 1 { s.fillRect(col("red"), px + 4, py + 4, 2, 2) }
                } else if ch == "%" {
                    WMArt.paws(s, px, py, abs(x - near.0) + abs(y - near.1) <= 3, t)
                } else if ch == "-" {
                    s.fillRect(col("hotpink"), px, py + 4, TS, 2)
                }
                if ch == "~" || wet[key(x, y)] != nil {
                    let fresh = ch == "~" || (wet[key(x, y)] ?? 0) > 1.0 || Int(t * 8) % 2 == 1
                    if fresh {
                        let sh = (Int(t * 3) + x + y) % 4
                        s.fillRect(col("sky"), px + 1, py + 2 + sh, 3, 1)
                        s.fillRect(col("sky"), px + 5, py + 6 - sh / 2, 4, 1)
                        s.fillRect(col("white"), px + 2 + sh, py + 4, 1, 1)
                    }
                }
                guard let v = food[key(x, y)] else { continue }
                let cx = px + TS / 2, cy = py + TS / 2
                switch v {
                case "c":
                    WMArt.crumb(s, cx, cy, t, fever: fever, x + y)
                case "f":
                    s.fillRect(col("orange"), cx - 3, cy - 1, 4, 3)
                    s.fillRect(col("peach"), cx - 2, cy - 1, 2, 1)
                    s.fillRect(col("orange"), cx + 1, cy - 2, 1, 1)
                    s.fillRect(col("orange"), cx + 1, cy + 1, 1, 1)
                    s.fillRect(col("black"), cx - 2, cy, 1, 1)
                case "s":
                    WMArt.secret(s, cx, cy, t)
                case "o":
                    s.blit(sprite("wm_nip"), cx - 4, cy - 4 + Int(sin(t * 4 + Double(x))))
                    if Int(t * 5 + Double(x)) % 4 == 0 { s.fillRect(col("white"), cx + 3, cy - 4, 1, 1) }
                default: break
                }
            }
        }
        if st.kind == "normal" && bots.contains(where: { $0.kind == "sniffy" }) {
            let life = scentLife()
            let c = col(theme.fb != theme.fa ? theme.fb : "darkgray")
            let pc = col("lavender")
            for (k, when) in scent {
                let x = k % COLS, y = k / COLS
                let age = stime - when
                if age > 0.3 && age < life && (x + y) % 2 == 0 && food[k] == nil {
                    let px = OX + x * TS + 3, py = OY + y * TS + 3
                    let cc = age < life * 0.4 ? pc : c
                    s.fillRect(cc, px, py + 2, 2, 2)
                    s.fillRect(cc, px + 3, py, 1, 1)
                }
            }
        }
    }

    func drawHazards(_ s: Surface, _ t: Double) {
        for h in hazards {
            let st = h.style
            let on = h.t >= h.warn
            if st == "wet" {
                if !on && Int(t * 10) % 2 == 1 {
                    for (x, y) in h.tiles { s.fillRect(col("sky"), OX + x * TS + 4, OY + y * TS + 4, 2, 2) }
                }
                continue
            }
            for (x, y) in h.tiles {
                let px = OX + x * TS, py = OY + y * TS
                if st == "trap" {
                    if on { s.blit(sprite("wm_trap"), px + 1, py + 2) } else if Int(t * 12) % 2 == 1 { s.fillRect(col("yellow"), px + 3, py + 3, 4, 4) }
                    continue
                }
                if !on {
                    if Int(t * 10) % 2 == 1 {
                        let c = ["suck": "sky", "snap": "yellow", "burn": "orange", "quake": "yellow"][st] ?? "red"
                        s.rect(col(c), IRect(px + 1, py + 1, TS - 2, TS - 2), width: 1)
                    }
                    if st == "stomp" || st == "pop" || st == "splash" {
                        let r = 1 + Int(h.t / h.warn * 4)
                        s.ellipse(col("black"), px + 5 - r, py + 5 - r / 2, r * 2, r)
                    }
                    continue
                }
                switch st {
                case "suck":
                    s.fillRect(col("sky"), px, py + 3, TS, 4)
                    s.fillRect(col("white"), px + (Int(t * 40) + x * 3) % TS, py + 4, 2, 2)
                case "snap":
                    var i = 0
                    while i < TS { s.fillRect(col("white"), px + i, py + 2 + (i / 3) % 2 * 4, 2, 2); i += 3 }
                    s.fillRect(col("brown"), px, py + 4, TS, 2)
                case "burn":
                    s.fillRect(col("orange"), px, py + 2, TS, 6)
                    s.fillRect(col("yellow"), px + (Int(t * 30) + x) % 8, py + 3, 2, 3)
                case "quake":
                    s.fillRect(col("brown"), px, py + 4 + Int(sin(t * 40 + Double(x)) * 2), TS, 2)
                case "splash":
                    s.circle(col("sky"), px + 5, py + 5, 5)
                    s.fillRect(col("white"), px + 3, py + 3, 2, 2)
                default:     // stomp / pop impact
                    s.circle(col("white"), px + 5, py + 5, 5, width: 1)
                    s.fillRect(col(st == "pop" ? "peach" : "pink"), px + 2, py + 2, 6, 6)
                }
            }
        }
    }

    func drawBot(_ s: Surface, _ b: WMBot, _ t: Double) {
        let x = Int(tpx(b.x)), y = Int(tpy(b.y))
        if b.state == "reboot" { WMArt.reboot(s, x, y, t); return }
        if b.kind == "mouse" {
            s.blit(sprite("wm_mouse", Int(t * 10) % 2, flip: b.face.x < 0), x - 5, y - 3)
            return
        }
        var state = ""
        if b.state == "sleep" {
            state = "sleep"
        } else if b.dizzy {
            state = "dizzy"
        } else if b.frozen > 0 {
            state = "frozen"
        } else if ["alert", "aim", "bark", "chase", "dash"].contains(b.mode) && b.kind != "zig" {
            state = b.mode != "chase" || b.kind == "fridgy" || b.kind == "snoozy" ? "alert" : ""
        } else if b.mode == "tired" || b.mode == "drowsy" {
            state = "tired"
        }
        var flash = b.dizzy && zoomT < 1.6 && Int(t * 8) % 2 == 0
        if b.state == "puck" { state = "dizzy"; flash = true }
        WMArt.bot(s, b.kind, x, y, t, look: (b.face.x, b.face.y), state: state, flash: flash)
        if b.state == "sleep" {
            let k = Int(t * 2) % 3
            drawText(s, "Z", x + 4 + k * 2, y - 10 - k * 3, "white", shadow: nil)
        } else if b.frozen > 0 && Int(t * 6) % 2 == 1 {
            s.fillRect(col("white"), x - 6, y - 8, 1, 1)
            s.fillRect(col("white"), x + 6, y - 6, 1, 1)
        }
        if b.mode == "aim" && b.timer > 0 {
            for i in 1 ... 3 where Int(t * 12 + Double(i)) % 2 == 1 {
                s.fillRect(col("sky"), x + b.face.x * i * 6, y + b.face.y * i * 6, 2, 2)
            }
        }
    }

    func drawBoss(_ s: Surface, _ bo: WMBoss, _ t: Double) {
        let x = Int(tpx(bo.x))
        var y = Int(tpy(bo.y))
        if bo.airborne() {
            s.ellipse(col("black"), x - 12, y + 6, 24, 6)
            y -= 10 + Int(abs(sin(min(1.0, bo.timer / max(0.01, bo.air.4)) * .pi)) * 14)
        }
        let mood = bo.state == "stun" ? "stun" : (bo.phase >= 3 || bo.state == "wind" ? "angry" : "")
        let flash = bo.flash > 0 && Int(t * 20) % 2 == 0
        WMArt.boss(s, bo.kind, x, y, t, mood: mood, flash: flash, wind: bo.windFrac())
        if bo.state == "wind" {
            drawText(s, "!", x, y - 26, Int(t * 10) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        }
    }

    func drawNori(_ s: Surface, _ t: Double) {
        let n = nori
        let x = tpx(n.x), y = tpy(n.y)
        let face = (n.face.x, n.face.y)
        if state == "dying" {
            let k = stateT
            if k < 0.8 {
                WMArt.nori(s, x + Double(Int(sin(t * 50))), y, face, t, false, "hurt")
            } else if Int(k * 10) % 2 == 0 && k < 1.4 {
                s.circle(col("black"), Int(x), Int(y), max(1, Int((1.4 - k) * 9)))
                s.circle(col("lavender"), Int(x), Int(y), max(1, Int((1.4 - k) * 9)), width: 1)
            }
            if k > 0.79 && k < 0.82 { parts.burst(x, y, 20, ["black", "darkgray", "lavender", "yellow"], 70, 0.8) }
            return
        }
        if invuln > 0 && Int(t * 12) % 2 == 1 { return }
        let moving = !n.dir.isZero && state == "play"
        let mood = state == "clear" || state == "tally" ? "happy" : ""
        if zoomy || dashT > 0 {     // rainbow afterimages
            for i in 1 ... 3 {
                let c = zoomy ? rainbow(i, t) : "sky"
                let ax = Int(x) - n.face.x * i * 4, ay = Int(y) - n.face.y * i * 4
                s.fillRect(col(c), ax - 3, ay - 1, 6, 3)
            }
        }
        let hop = mood == "happy" ? -Int(abs(sin(t * 9)) * 4) : 0
        WMArt.nori(s, x, y + Double(hop), face, t, moving, mood, flash: zoomy && Int(t * 10) % 3 == 0)
        if collar > 0 && Int(t * 2) % 4 == 0 { s.fillRect(col("yellow"), Int(x) + 1, Int(y) + 2, 1, 1) }
        if let w = want, state == "play", w != n.dir, Int(t * 8) % 2 == 1 {
            let ax = Double(Int(x) + w.x * 9), ay = Double(Int(y) + w.y * 9)
            let wx = Double(w.x), wy = Double(w.y)
            if w.x != 0 {
                s.polygon(col("yellow"), [(ax + wx * 2, ay), (ax - wx, ay - 2), (ax - wx, ay + 2)])
            } else {
                s.polygon(col("yellow"), [(ax, ay + wy * 2), (ax - 2, ay - wy), (ax + 2, ay - wy)])
            }
        }
    }

    func drawDark(_ s: Surface, _ t: Double) {
        let n = nori
        let r = 4.2 + (zoomy ? 1.5 : 0)
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS {
                let dx = Double(x) - n.x, dy = Double(y) - n.y
                let a = max(0, min(1, ((dx * dx + dy * dy).squareRoot() - r) / 2.5))
                if a > 0 { s.fillRect(rgba(12, 8, 24, Int(a * 235)), OX + x * TS, OY + y * TS, TS, TS) }
            }
        }
        for b in bots where ["roam", "leave", "sleep"].contains(b.state) {
            let dx = b.x - n.x, dy = b.y - n.y
            if (dx * dx + dy * dy).squareRoot() > r { WMArt.led(s, Int(tpx(b.x)), Int(tpy(b.y)) - 1, t) }
        }
        for it in items where Int(t * 4) % 2 == 1 { s.fillRect(col("yellow"), Int(tpx(Double(it.x))), Int(tpy(Double(it.y))), 1, 1) }
    }

    func drawHud(_ s: Surface, _ t: Double) {
        s.fillRect(col("black"), 0, 0, W, OY - 2)
        drawText(s, String(format: "%07d", score), 4, 3, "white", shadow: nil)
        if streak >= 20 && st.kind != "bonus" {
            let c = ["cream", "peach", "orange", "yellow", "yellow"][min(4, streak / 20)]
            drawText(s, "STREAK \(streak)", 4, 13, streak < 80 ? c : rainbow(0, t), shadow: nil)
        } else {
            drawText(s, "HI " + String(format: "%07d", max(best, score)), 4, 13, "gray", shadow: nil)
        }
        if let bo = boss, bo.state != "dead", state != "intro" {
            bossBar(s, bo.name, Double(bo.hp), Double(bo.maxhp), t, y: 1, x: 58, w: 200)
        } else if st.kind == "bonus" && (state == "play" || state == "intro") {
            let secs = Int(ceil(bonusLeft))
            drawText(s, String(format: "TIME %02d", secs), W / 2, 3, secs > 5 || Int(t * 6) % 2 == 1 ? "yellow" : "red", align: .center, shadow: nil)
        } else {
            drawText(s, "STAGE \(n)", W / 2, 3, "yellow", align: .center, shadow: nil)
        }
        if st.kind == "normal" && hype.combo < 3 {
            drawText(s, "FISH \(crumbsLeft)", W / 2, 13, "cream", align: .center, shadow: nil)
        } else if st.kind == "bonus" && st.bonus == "mice" && hype.combo < 3 {
            drawText(s, "MICE \(miceCaught)/\(miceTotal)", W / 2, 13, "pink", align: .center, shadow: nil)
        }
        hearts(s, W - 54, 3, lives)
        // FEVER gauge + DASH meter
        let x0 = W - 54, y0 = 14
        s.fillRect(col("darkgray"), x0, y0, 48, 3)
        if hype.feverOn {
            for i in 0 ..< 48 { s.fillRect(col(rainbow(i / 6, t)), x0 + i, y0, 1, 3) }
        } else {
            s.fillRect(col("orange"), x0, y0, Int(48 * hype.fever), 3)
        }
        let dmax = 5.0 - 0.9 * Double(lv("dash"))
        let ready = dashCd <= 0
        drawText(s, "DASH", W - 102, 12, ready ? (Int(t * 3) % 2 == 1 ? "sky" : "white") : "gray", shadow: nil)
        s.fillRect(col("darkgray"), W - 75, 14, 16, 3)
        s.fillRect(col("sky"), W - 75, 14, Int(16 * (1 - dashCd / dmax)), 3)
        if zoomT > 0 {        // zoomies timer along the top of the maze
            let full = st.nip + 1.5 * Double(lv("nip"))
            let w = Int(Double(W - 10) * min(1, zoomT / full))
            var i = 0
            while i < w { s.fillRect(col(rainbow(i / 4, t)), 5 + i, OY - 3, 3, 2); i += 4 }
        }
        if collar > 0 {
            for i in 0 ..< collar { s.blit(sprite("wm_bell"), W - 54 + 8 * min(lives, 6) + 2 + i * 8, 2) }
        }
    }

    func drawCardNori(_ s: Surface, _ x: Int, _ y: Int, _ mood: String, _ t: Double) {
        let name = mood == "happy" ? "wm_happy" : "wm_sit"
        let f = mood == "happy" ? 0 : Int(t * 2) % 2
        let r = sprite(name, f, remap: WMArt.rim, scale: 2)
        for (ox, oy) in [(-1, 0), (1, 0), (0, -1), (0, 1)] { s.blit(r, x + ox, y + oy) }
        s.blit(sprite(name, f, scale: 2), x, y)
    }

    func drawIntro(_ s: Surface, _ t: Double) {
        let k = st.kind
        if k == "boss" {
            if Int(t * 4) % 2 == 1 {
                var x = -20
                while x < W + 20 {
                    let fx = Double(x)
                    s.polygon(col("red"), [(fx, 128), (fx + 10, 128), (fx + 20, 136), (fx + 10, 136)])
                    s.polygon(col("red"), [(fx, 170), (fx + 10, 170), (fx + 20, 178), (fx + 10, 178)])
                    x += 20
                }
            }
            panel(s, IRect(40, 138, 240, 30), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 142, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.name) APPROACHES", W / 2, 158, "white", align: .center, shadow: nil)
            return
        }
        let h = st.newLine.isEmpty ? 56 : 66
        let y0 = 70
        panel(s, IRect(24, y0, 272, h), fill: "ink", border: k == "bonus" ? "yellow" : "lavender")
        drawCardNori(s, 32, y0 + 10, k == "bonus" ? "happy" : "", t)
        let cx = 172
        if k == "bonus" {
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), cx - textWidth(title, 2) / 2 + i * 12, y0 + 6 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            let sub = st.bonus == "mice" ? "CATCH THE WIND-UP MICE!" : "EAT ALL THE FISH TREATS!"
            drawText(s, st.name, cx, y0 + 26, "yellow", align: .center)
            drawText(s, sub, cx, y0 + 38, "white", align: .center)
            return
        }
        drawText(s, "STAGE \(n)", cx, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, theme.name, cx, y0 + 24, "lavender", align: .center)
        drawText(s, st.name, cx, y0 + 34, "white", align: .center)
        drawText(s, "\"\(st.quip)\"", cx, y0 + 45, "gray", align: .center, shadow: nil)
        if !st.newLine.isEmpty {
            drawText(s, st.newLine, W / 2, y0 + 56, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center)
        }
    }

    func drawTally(_ s: Surface, _ t: Double) {
        let h = 34 + tally.count * 11
        let y0 = 60
        panel(s, IRect(40, y0, 240, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, W / 2 + 14, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 20 + i * 11
            drawText(s, row.label, 52, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 268, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 {
            drawText(s, "PRESS DASH", W / 2, y0 + h - 11, "lavender", align: .center, shadow: nil)
        }
    }

    // ---------------------------------------------------------------- carousel preview
    /// Nori trots along eating crumbs with bots on her tail - then catnip turns the chase around.
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        s.fill(col("ink"))
        var yy = 0
        while yy < h {
            var xx = 0
            while xx < w { if (xx / 8 + yy / 8) % 2 == 1 { s.fillRect(col("deep"), xx, yy, 8, 8) }; xx += 8 }
            yy += 8
        }
        for ry in [6, h - 14] {
            s.fillRect(col("peach"), 0, ry, w, 8)
            s.fillRect(col("cream"), 0, ry, w, 1)
            s.fillRect(col("brown"), 0, ry + 5, w, 3)
            var x = 6
            while x < w { s.fillRect(col("cream"), x, ry + 6, 3, 1); x += 18 }
        }
        let lane = h / 2 + 2
        let cyc = t.truncatingRemainder(dividingBy: 8.0)
        let kinds = ["sniffy", "zig", "snoozy"]
        if cyc < 4.0 {
            let px = -10 + Double(w + 20) * cyc / 4.0
            var x = 4
            while x < w { if Double(x) > px + 4 { s.fillRect(col("cream"), x, lane, 2, 2) }; x += 9 }
            if px < Double(w - 10) { s.blit(sprite("wm_nip"), w - 12, lane - 4) }
            for (j, k) in kinds.enumerated() { WMArt.bot(s, k, Int(px - 24 - Double(j) * 16), lane, t, look: (1, 0)) }
            WMArt.nori(s, px, Double(lane), (1, 0), t, true)
        } else {
            let px = Double(w + 10) - Double(w + 40) * (cyc - 4.0) / 4.0
            for (j, k) in kinds.enumerated() {
                WMArt.bot(s, k, Int(px - 22 - Double(j) * 16), lane, t, look: (-1, 0), state: "dizzy", flash: Int(t * 8) % 2 == 0)
            }
            for i in 1 ... 3 { s.fillRect(col(rainbow(i, t)), Int(px) + i * 4 - 3, lane - 1, 6, 3) }
            WMArt.nori(s, px, Double(lane), (-1, 0), t, true)
            drawText(s, "ZOOMIES!", w / 2, 16, rainbow(0, t), align: .center)
        }
        s.blit(sprite("wm_tuna"), 4, h - 26)
    }
}
