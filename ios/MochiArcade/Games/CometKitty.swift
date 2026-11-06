// COMET KITTY - fixed-screen space shooter, 200-stage campaign (port of games/comet_kitty.py).
// Stage tables: CometKittyData.swift (exported from Python). Art: CometKittyArt.swift.
import Foundation

private let PY = 166.0                      // Tama's resting height (top of her 16x16 sprite)
private let PY_MIN = 128.0, PY_MAX = 172.0  // she can drift up and down inside this band
private let EXTRA_LIVES = [30000, 80000, 150000, 250000]
private let EXTRA_EVERY = 150000
private let MEDALS = [100, 200, 300, 500, 800, 1000, 1500, 2000, 3000, 5000]
private let SPREAD: [[Double]] = [[], [8], [8, 18], [8, 18, 30], [8, 18, 30, 42]]
private let PAL_SLOTS: [(Double, Double)] = [(-16, 6), (16, 6), (0, -14)]
private let KIT_ORDER = ["rapid", "spread", "shield", "zoom", "bombs", "lance", "pals", "seeker", "focus", "magnet"]
private let DIVING: Set<String> = ["dive", "dash", "kami"]
private let HARMFUL: Set<String> = ["enter", "home", "dive", "dash", "kami", "free"]
private let TAU = 2 * Double.pi

private func rad(_ deg: Double) -> Double { deg * .pi / 180 }
private func rnd(_ a: Double, _ b: Double) -> Double { Double.random(in: a ... b) }
/// Python-style float modulo (result has the sign of the divisor).
private func pmod(_ a: Double, _ b: Double) -> Double { a - b * (a / b).rounded(.down) }

private func bezier(_ p: [(Double, Double)], _ u: Double) -> (Double, Double) {
    let a = pow(1 - u, 3), b = 3 * u * pow(1 - u, 2), c = 3 * u * u * (1 - u), d = u * u * u
    return (a * p[0].0 + b * p[1].0 + c * p[2].0 + d * p[3].0, a * p[0].1 + b * p[1].1 + c * p[2].1 + d * p[3].1)
}

private func pathPos(_ path: [(Double, Double)], _ dist: Double, _ mirror: Int) -> (Double, Double) {
    var f = dist / CKData.step
    let i = min(path.count - 2, Int(f))
    f -= Double(i)
    let x = path[i].0 + (path[i + 1].0 - path[i].0) * f
    let y = path[i].1 + (path[i + 1].1 - path[i].1) * f
    return (mirror != 0 ? Double(W) - x : x, y)
}

let CK_POOL: [Upgrade] = [
    Upgrade(id: "spread", name: "STAR SPREAD", desc: "MORE STREAMS|OF STARS THAT|FAN OUT WIDE", color: "yellow", draw: CKArt.icon("spread"), max: 3),
    Upgrade(id: "rapid", name: "RAPID PAWS", desc: "SHOOT STARS|FASTER", color: "orange", draw: CKArt.icon("rapid"), max: 5),
    Upgrade(id: "lance", name: "COMET LANCE", desc: "CENTRE SHOT|PIERCES FOES|AND HITS HARD", color: "sky", draw: CKArt.icon("lance"), max: 3),
    Upgrade(id: "seeker", name: "SEEKER STARS", desc: "HOMING STARS|CHASE FOES", color: "lime", draw: CKArt.icon("seeker"), max: 3),
    Upgrade(id: "pals", name: "STAR PALS", desc: "A STAR FRIEND|FLIES BESIDE|YOU, SHOOTING", color: "pink", draw: CKArt.icon("pals"), max: 2),
    Upgrade(id: "shield", name: "BUBBLE GUARD", desc: "+1 BUBBLE|EVERY STAGE|BLOCKS A HIT", color: "mint", draw: CKArt.icon("shield"), max: 3),
    Upgrade(id: "zoom", name: "ZOOMIES", desc: "FLY|FASTER", color: "peach", draw: CKArt.icon("zoom"), max: 3),
    Upgrade(id: "focus", name: "FOCUS CORE", desc: "TINIER HITBOX|LV2: GRAZING|BULLETS SCORES", color: "lavender", draw: CKArt.icon("focus"), max: 2),
    Upgrade(id: "bombs", name: "BOMB POUCH", desc: "+1 COMET BURST|BIGGER BLASTS", color: "red", draw: CKArt.icon("bombs"), max: 3),
    Upgrade(id: "magnet", name: "MAGNET MITTS", desc: "PULLS IN|MEDALS AND|CAPSULES", color: "lavender", draw: CKArt.icon("magnet"), max: 2),
]

final class CKEnemy {
    let uid, kind: Int
    var hp, maxhp: Double
    var x = -60.0, y = -60.0
    var col = 0, row = 0
    var state = "wait"
    var t = 0.0, delay = 0.0
    var path: [(Double, Double)] = []
    var mirror = 0
    var dist = 0.0, speed = 120.0
    var group = -1, cap = -1
    var flash = 0.0
    var alive = true
    var extra = false           // mines, meteors, minis, golden comets: not needed to clear the stage
    var parade = false, entered = false
    var bez: [(Double, Double)] = []
    var dur = 1.0
    var shots: [(Double, Bool)] = []
    var vx = 0.0, vy = 0.0
    var aux = 0.0
    var fireAt = -1.0           // entry-path distance at which it fires once (-1: never)
    var ambAt = -1.0            // entry-path distance at which it dives out of the entry (-1: never)
    var tele = 0.0              // formation volley wind-up
    let seed = Double.random(in: 0 ... 6.28)

    init(_ uid: Int, _ kind: Int, _ hp: Double) { self.uid = uid; self.kind = kind; self.hp = hp; maxhp = hp }
}

final class CKPart { let dx, dy: Double; let r: Int; var hp: Double; var flash = 0.0; var alive = true
    init(_ dx: Double, _ dy: Double, _ r: Int, _ hp: Double) { self.dx = dx; self.dy = dy; self.r = r; self.hp = hp }
}

final class CKBoss {
    let kind, lv: Int
    let final: Bool
    let name: String
    var hp: Double
    let maxhp: Double
    let bw, bh: Double
    let weak: (Double, Double, Int)
    let phases: [[String]]
    let nphase: Int
    var parts: [CKPart]
    var x = Double(W) / 2, y = -40.0
    var cx = Double(W) / 2, hy = 50.0
    var t = 0.0, mt = 0.0
    var state = "enter"
    var phase = 0
    var atk: String?
    var at = 0.0
    var ai = 0, an = 0
    var rest = 1.0
    var flash = 0.0
    var face = 1
    var alpha = 1.0
    var lx: [Double] = [], rx: [Double] = []
    var gap = Double(W) / 2, tx = Double(W) / 2
    var dir = 1.0, ang = 0.0

    init(_ st: CKStage) {
        let spec = CKData.bosses[st.boss]
        kind = st.boss; lv = st.lv; final = st.final; name = st.name
        hp = Double(st.hp); maxhp = Double(st.hp)
        (bw, bh) = spec.box
        weak = spec.weak
        phases = st.phases; nphase = st.nphase
        let mh = Double(st.hp)
        parts = spec.parts.map { CKPart($0.0, $0.1, $0.2, mh * $0.3) }
    }

    func weakPos() -> (Double, Double, Int) {
        let f = kind == 2 ? Double(face) : 1
        return (x + weak.0 * f, y + weak.1, weak.2)
    }
}

final class CKShot {
    var x, y, vx, vy, dmg: Double; var pierce, kind: Int; var hits: [Int] = []; var life: Double
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ dmg: Double, _ pierce: Int, _ kind: Int, _ life: Double) {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.dmg = dmg; self.pierce = pierce; self.kind = kind; self.life = life
    }
}

final class CKBullet {
    var x, y, vx, vy: Double; let kind: Int; var grazed = false
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ kind: Int) { self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.kind = kind }
}

final class CKItem {
    var x, y, vx, vy: Double; let kind: String; var t = 0.0
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ kind: String) { self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.kind = kind }
}

struct CKTally { var title: String; var lines: [(String, Int)]; var t = 0.0; var shown = 0; var total: Int }

final class CometKitty: GameScene {
    var stageMusic = "comet"
    override var music: String? { stageMusic }
    override var buttons: [Action: String] {
        if overlay != nil || phase == "tally" { return [.a: "OK", .b: "BOMB"] }
        return autofire ? [.b: "BOMB"] : [.a: "FIRE", .b: "BOMB"]
    }
    override var buttonOrder: [Action] { autofire && overlay == nil && phase != "tally" ? [.b, .a] : [.a, .b] }
    override var fourWay: Bool { false }

    var lives: Int
    let spd: Double
    let autofire: Bool
    var stageN: Int
    let stars = Stars(70, seed: 7)
    var px = Double(W) / 2, py = PY
    var vx = 0.0, vy = 0.0
    var shots: [CKShot] = [], bullets: [CKBullet] = [], items: [CKItem] = [], enemies: [CKEnemy] = [], spawned: [CKEnemy] = []
    var boss: CKBoss?
    var levels: [String: Int] = [:]
    var inv = 1.5
    var deadT: Double?
    var fireT = 0.0, seekT = 0.0
    var shotN = 0
    var bombs = 2, shield = 0
    var bombT = 0.0, bombX = 0.0, bombY = 0.0
    var friendT = 0.0, powerT = 0.0
    var pals: [(Double, Double)] = Array(repeating: (Double(W) / 2, PY), count: 3)
    var medalI = 0, extraI = 0
    var nextExtra = EXTRA_LIVES[0]
    var uid = 0
    var feverWas = false
    var tinT = 0.0
    var warp = 0.0
    var bg: Surface?
    var bgTheme = -1
    var tally: CKTally?
    var vicT = 0.0
    // per stage
    var st: CKStage
    var mode = "normal"
    var tierN = 0
    var theme: CKTheme
    var stageT = 0.0, introT = 0.0, clearT = 0.0
    var deaths = 0, squadWipes = 0, hits = 0, total = 0, broken = 0
    var squads: [Int: (Int, Int)] = [:]
    var diveT = 1.0, meteorT = 3.0, volleyT = 3.0, goldT = -1.0
    var diveStart = 0.0
    var phase = "intro"

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        spd = SPEEDS[d] ?? 1
        autofire = ["on", "true"].contains((opt["autofire"] ?? "off").lowercased())
        stageN = max(1, min(STAGES, Int(opt["start"] ?? "1") ?? 1))
        st = CKData.stage(stageN)
        theme = CKData.themes[0]
        super.init(app, info, opt)
        // starting from a checkpoint: hand out the power a player would roughly have by then
        var kit = (stageN - 1) / 10
        let given = kit
        var i = 0
        while kit > 0 && i < 200 {
            let u = CK_POOL.first { $0.id == KIT_ORDER[i % KIT_ORDER.count] }!
            if lv(u.id) < u.max { levels[u.id] = lv(u.id) + 1; kit -= 1 }
            i += 1
        }
        bombs = 2 + lv("bombs")
        shield = 0
        startStage()
        if given > 0 { hype.banner("CHECKPOINT!", "+\(given) POWER LEVELS", color: "lime", dur: 2.0) }
    }

    // ------------------------------------------------------------------ helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func npals() -> Int { min(3, lv("pals") + (friendT > 0 ? 1 : 0)) }
    func hitbox() -> Double { lv("focus") >= 1 ? 2.5 : 4.0 }
    func centre() -> (Double, Double) { (px, py + 9) }

    /// Floating text kept fully on screen.
    func say(_ x: Double, _ y: Double, _ text: String, _ c: String) {
        let hw = Double(textWidth(text) / 2 + 2)
        floats.add(max(hw, min(Double(W) - hw, x)), y, text, c)
    }

    func spawn(_ kind: Int, _ hp: Double) -> CKEnemy { uid += 1; return CKEnemy(uid, kind, hp) }
    func solid(_ e: CKEnemy) -> Bool { e.kind != CK_WISP || sin(stageT * 2.4 + e.seed) > -0.35 }
    func hittable(_ e: CKEnemy) -> Bool { e.alive && e.state != "wait" && e.y > -6 && solid(e) }

    func slot(_ e: CKEnemy) -> (Double, Double) {
        let ft = stageT
        let sway = sin(ft * 0.8) * 12
        let breathe = 1 + sin(ft * 1.6) * 0.05
        return (Double(W) / 2 + Double(e.col) * CKData.colDX * breathe + sway,
                CKData.rowY0 + Double(e.row) * CKData.rowDY + sin(ft * 2 + Double(e.col) * 0.5) * 1.5)
    }

    // ------------------------------------------------------------------ stages
    func startStage() {
        let n = stageN
        st = CKData.stage(n)
        mode = st.type
        tierN = tier(n)
        theme = CKData.themes[st.theme]
        if bgTheme != st.theme { bg = CKArt.backdrop(theme); bgTheme = st.theme }
        reached(n)
        enemies = []; bullets = []; spawned = []
        boss = nil
        stageT = 0; introT = 0; clearT = 0
        deaths = 0; squadWipes = 0; hits = 0; total = 0; broken = 0
        squads = [:]
        diveT = 1; meteorT = 3; volleyT = 3
        goldT = mode == "normal" && hype.lucky(0.03) ? rnd(8, 16) : -1
        shield = max(shield, lv("shield"))
        tally = nil
        diveStart = 0
        let au = app.audio
        if mode == "boss" {
            phase = "warning"
            boss = CKBoss(st)
            stageMusic = "boss"
            au.play("warning")
        } else {
            phase = "intro"
            stageMusic = mode == "bonus" ? "bonus" : "comet"
            au.play("stage")
        }
        if !hype.feverOn || mode == "boss" { au.music(stageMusic) }
        if mode == "normal" {
            var last = 0.0
            for s in st.slots {
                let base = CKData.kinds[s.kind].hp
                let hp = base + ((s.kind != CK_JELLY && s.kind != CK_MOTH) ? st.hpb : st.hpj + (st.mods.contains("ARMORED") ? 1 : 0))
                let e = spawn(s.kind, Double(hp))
                e.col = s.col; e.row = s.row; e.delay = s.delay; e.path = CKData.paths[s.path]; e.mirror = s.mirror
                e.group = s.group; e.cap = s.cap
                e.speed = st.speed * (0.85 + 0.15 * spd)
                e.aux = rnd(2, st.fireGap + 2)
                let plen = Double(e.path.count - 1) * CKData.step
                if Double.random(in: 0 ..< 1) < st.efire { e.fireAt = rnd(0.3, 0.8) * plen }   // a pot shot while flying in
                if Double.random(in: 0 ..< 1) < st.amb { e.ambAt = rnd(0.45, 0.8) * plen }     // breaks off to attack at once
                enemies.append(e)
                squads[s.group, default: (0, 0)].0 += 1
                last = max(last, s.delay)
            }
            diveStart = min(3, last)
        } else if mode == "bonus" {
            for (g, w) in st.waves.enumerated() {
                for i in 0 ..< w.count {
                    let e = spawn(i == w.gold ? CK_GOLD : w.kind, 1)
                    e.parade = true
                    e.delay = w.delay + Double(i) * 20 / st.speed
                    e.path = CKData.paths[w.path]; e.mirror = w.mirror; e.group = g
                    e.speed = st.speed
                    enemies.append(e)
                    total += 1
                }
                squads[g] = (w.count, 0)
            }
        }
    }

    func nextStage() { stageN += 1; startStage() }

    func checkClear() {
        if phase != "play" { return }
        let done: Bool
        if mode == "boss" { done = boss == nil } else if mode == "bonus" { done = enemies.isEmpty } else { done = !enemies.contains { !$0.extra } }
        if !done { return }
        phase = "clear"
        clearT = 0
        cancelBullets()
        for e in enemies where e.alive && e.state != "wait" { parts.burst(e.x, e.y, 8, CKArt.kindColors[e.kind], 60, 0.5) }
        enemies = []
        if mode != "boss" { app.audio.play("levelup") }
    }

    func startTally() {
        let t = tierN
        var lines: [(String, Int)] = []
        var title: String
        if mode == "normal" {
            lines.append(("CLEAR BONUS", 1000 + 250 * t))
            lines.append(("TIME BONUS", max(0, Int(st.par - stageT)) * 50))
            lines.append(("NO MISS", deaths == 0 ? 3000 + 750 * t : 0))
            let sq = st.groups
            lines.append(("SQUADS \(squadWipes)/\(sq)", squadWipes * (300 + 60 * t)))
            if squadWipes >= sq { lines.append(("PERFECT!!", 5000 + 1000 * t)) }
            title = "STAGE \(stageN) CLEAR!"
        } else if mode == "bonus" {
            lines.append(("HITS \(hits)/\(total)", hits * 100))
            if hits >= total { lines.append(("PERFECT!!", 10000 + 2500 * t)) }
            title = "BONUS PARADE OVER"
        } else {
            lines.append(("BOSS BONUS", 10000 + 5000 * t))
            lines.append(("TIME BONUS", max(0, Int(st.par - stageT)) * 100))
            lines.append(("NO MISS", deaths == 0 ? 5000 + 1000 * t : 0))
            if !CKData.bosses[st.boss].parts.isEmpty { lines.append(("PARTS BROKEN \(broken)", broken * 2000)) }
            title = "\(st.name) DEFEATED!"
        }
        tally = CKTally(title: title, lines: lines, total: lines.reduce(0) { $0 + $1.1 })
        phase = "tally"
    }

    func updateTally(_ dt: Double) {
        guard var tl = tally else { return }
        tl.t += dt
        let n = tl.lines.count
        while tl.shown < n && tl.t >= 0.35 + Double(tl.shown) * 0.4 {
            let (label, v) = tl.lines[tl.shown]
            tl.shown += 1
            if label.hasPrefix("PERFECT") {
                app.audio.play("win")
                hype.shower(50, "coins")
                hype.flash("yellow", 0.2)
            } else {
                app.audio.play(v > 0 ? "coin" : "move")
            }
        }
        tally = tl
        let end = 0.35 + Double(n) * 0.4 + 0.4
        if tl.t >= end + 1.4 || (tl.t >= end && app.input.hit(.a, .b)) { finishTally() }
    }

    func finishTally() {
        guard let tl = tally else { return }
        tally = nil
        if tl.total > 0 { add(tl.total, Double(W / 2), 110, "yellow") }
        phase = "between"
        if mode == "boss" {
            if st.final || stageN >= STAGES {
                phase = "victory"
                vicT = 0
                hype.banner("GALAXY SAVED!!", "ALL 200 STAGES CLEAR", dur: 4.0, rainbow: true, sound: "win")
                hype.shower(120, "confetti")
                app.audio.music("fever")
                return
            }
            pickUpgrade(CK_POOL, levels, title: "POWER UP!") { [unowned self] id in self.onPick(id) }
        } else if mode == "bonus" && hits * 2 >= total {
            pickUpgrade(CK_POOL, levels, title: "BONUS PICK!") { [unowned self] id in self.onPick(id) }
        } else {
            nextStage()
        }
    }

    func onPick(_ id: String?) {
        if let id = id {
            levels[id] = lv(id) + 1
            if id == "bombs" { bombs += 1 } else if id == "shield" { shield += 1 }
        } else {
            add(25000, Double(W / 2), 100, "lime")
            hype.banner("MAX POWER!", "+25000", color: "lime", dur: 1.4)
        }
        nextStage()
    }

    // ------------------------------------------------------------------ update
    override func tick(_ dt: Double) {
        let au = app.audio
        stageT += dt
        introT += dt
        tinT = max(0, tinT - dt)
        let warpGoal = ["clear", "tally", "between"].contains(phase) ? 1.0 : 0.0
        warp += (warpGoal - warp) * min(1, dt * 2)
        stars.update(dt, 22 + warp * 160 + (mode == "boss" ? 12 : 0))
        inv = max(0, inv - dt)
        friendT = max(0, friendT - dt)
        powerT = max(0, powerT - dt)
        bombT = max(0, bombT - dt)
        updatePlayer(dt)
        if ending != nil { return }
        updateShots(dt)
        for e in enemies where e.alive { updateEnemy(e, dt) }
        if boss != nil { updateBoss(dt) }
        if phase == "play" && mode == "normal" { spawnEvents(dt) }
        for b in bullets { b.x += b.vx * dt; b.y += b.vy * dt }
        bullets.removeAll { !($0.y > -12 && $0.y < Double(H + 12) && $0.x > -12 && $0.x < Double(W + 12)) }
        updateItems(dt)
        collide()
        enemies = enemies.filter { $0.alive } + spawned
        spawned = []
        checkExtra()
        if hype.feverOn != feverWas {
            feverWas = hype.feverOn
            if mode != "boss" && phase != "victory" { au.music(feverWas ? "fever" : stageMusic) }
        }
        // flow
        if phase == "intro" && introT >= 2.4 {
            phase = "play"
        } else if phase == "warning", let b = boss, b.state == "fight" {
            phase = "play"
        } else if phase == "clear" {
            clearT += dt
            if clearT >= 1.0 { startTally() }
        } else if phase == "tally" {
            updateTally(dt)
        } else if phase == "victory" {
            vicT += dt
            if Int(vicT * 4) != Int((vicT - dt) * 4) {
                parts.burst(rnd(40, Double(W - 40)), rnd(30, 120), 30, [rainbow(Int.random(in: 0 ..< 7)), "white", "yellow"], 110, 1.0)
                au.play("explode")
            }
            if vicT >= 5.0 { endGame(true, "ALL 200 STAGES!") }
        }
        checkClear()
    }

    func checkExtra() {
        while score >= nextExtra {
            lives += 1
            extraI += 1
            nextExtra = extraI < EXTRA_LIVES.count ? EXTRA_LIVES[extraI] : nextExtra + EXTRA_EVERY
            if !hype.banners.isEmpty {
                say(px, py - 14, "1UP!", "mint")
                app.audio.play("extra")
            } else {
                hype.banner("1UP!", "EXTRA KITTY", color: "mint", dur: 1.3, sound: "extra")
            }
            hype.shower(16, "hearts")
        }
    }

    func updatePlayer(_ dt: Double) {
        let inp = app.input
        if var d = deadT {
            d -= dt
            deadT = d
            if d <= 0 {
                if lives <= 0 { endGame(false, "STAGE \(stageN)"); return }
                deadT = nil
                inv = 2.5
                px = Double(W) / 2; py = PY
                vx = 0; vy = 0
                bombs = max(bombs, 2)
                cancelBullets()
            }
            return
        }
        let dx = (inp.down(.right) ? 1.0 : 0) - (inp.down(.left) ? 1.0 : 0)
        let dy = (inp.down(.down) ? 1.0 : 0) - (inp.down(.up) ? 1.0 : 0)
        var sp = 125 * (1 + 0.16 * Double(lv("zoom")))
        if dx != 0 && dy != 0 { sp *= 0.7071 }
        let k = min(1, dt * 18)     // quick ease in/out: smooth like a stick, still snappy
        vx += (dx * sp - vx) * k
        vy += (dy * sp - vy) * k
        px = max(10, min(Double(W) - 10, px + vx * dt))
        py = max(PY_MIN, min(PY_MAX, py + vy * dt))
        for i in pals.indices {
            let kk = min(1, dt * Double(10 - i * 2))
            pals[i].0 += (px + PAL_SLOTS[i].0 - pals[i].0) * kk
            pals[i].1 += (py + PAL_SLOTS[i].1 - pals[i].1) * kk
        }
        let firing = inp.down(.a) || autofire
        fireT -= dt
        if firing && fireT <= 0 && phase != "victory" {
            fire()
            fireT = 0.19 * pow(0.85, Double(lv("rapid"))) * (hype.feverOn ? 0.6 : 1.0)
        }
        let sl = lv("seeker")
        if sl > 0 {
            seekT -= dt
            if firing && seekT <= 0 {
                seekT = [0.75, 0.55, 0.4][sl - 1]
                let sides: [Double] = sl >= 3 ? [-1, 1] : [shotN % 2 == 1 ? -1 : 1]
                for sd in sides { shots.append(CKShot(px + sd * 6, py + 4, sd * 80, -120, 0.8, 0, 3, 2.0)) }
            }
        }
        if inp.hit(.b) { bomb() }
    }

    func fire() {
        let x = px, y = py
        let lance = lv("lance")
        if lance > 0 {
            shots.append(CKShot(x, y - 2, 0, -340, 1 + 0.5 * Double(lance), lance, 1, 1.2))
        } else {
            shots.append(CKShot(x, y - 2, 0, -300, 1, 0, 0, 1.2))
        }
        for a in SPREAD[min(4, lv("spread") + (powerT > 0 ? 1 : 0))] {
            let r = rad(a)
            for sd in [-1.0, 1.0] { shots.append(CKShot(x + sd * 3, y, sin(r) * 300 * sd, -cos(r) * 300, 0.7, 0, 0, 1.2)) }
        }
        if hype.feverOn {     // hyper shot: a fan of rainbow stars
            for a in [-55.0, -40, -25, 25, 40, 55] {
                let r = rad(a)
                shots.append(CKShot(x, y, sin(r) * 280, -cos(r) * 280, 1, 0, 4, 1.2))
            }
        }
        for i in 0 ..< npals() { shots.append(CKShot(pals[i].0, pals[i].1 - 2, 0, -300, 0.8, 0, 2, 1.2)) }
        shotN += 1
        if shotN % 2 == 1 { app.audio.play("shoot") }
    }

    func seekTarget(_ x: Double, _ y: Double) -> (Double, Double)? {
        var best: (Double, Double)?
        var bd = 1e9
        for e in enemies where hittable(e) && e.y < Double(H - 10) {
            let d = (e.x - x) * (e.x - x) + (e.y - y) * (e.y - y)
            if d < bd { best = (e.x, e.y); bd = d }
        }
        if let b = boss, b.state == "fight" {
            let (wx, wy, _) = b.weakPos()
            let d = (wx - x) * (wx - x) + (wy - y) * (wy - y)
            if d < bd { best = (wx, wy) }
        }
        return best
    }

    func updateShots(_ dt: Double) {
        for sh in shots {
            sh.life -= dt
            if sh.kind == 3 {
                if let tg = seekTarget(sh.x, sh.y) {
                    let dx = tg.0 - sh.x, dy = tg.1 - sh.y
                    let d = max(1, (dx * dx + dy * dy).squareRoot())
                    let k = min(1, dt * 7)
                    sh.vx += (dx / d * 260 - sh.vx) * k
                    sh.vy += (dy / d * 260 - sh.vy) * k
                } else {
                    sh.vy = max(-300, sh.vy - 400 * dt)
                }
            }
            sh.x += sh.vx * dt
            sh.y += sh.vy * dt
        }
        shots.removeAll { !($0.life > 0 && $0.y > -10 && $0.y < Double(H + 10) && $0.x > -10 && $0.x < Double(W + 10)) }
    }

    // ------------------------------------------------------------------ enemies
    func updateEnemy(_ e: CKEnemy, _ dt: Double) {
        e.t += dt
        e.flash = max(0, e.flash - dt)
        switch e.state {
        case "wait":
            if e.t >= e.delay {
                e.state = e.parade ? "parade" : "enter"; e.t = 0; e.dist = 0
                (e.x, e.y) = pathPos(e.path, 0, e.mirror)
            }
        case "enter", "parade":
            if e.fireAt > 0 && e.fireAt <= e.dist && (phase == "intro" || phase == "play") {
                e.fireAt = -1
                let n = st.burst
                for i in 0 ..< n { enemyShot(e, (Double(i) - Double(n - 1) / 2) * 12) }
            }
            if e.ambAt > 0 && e.ambAt <= e.dist && phase == "play" && deadT == nil && e.y < PY_MIN - 20 {
                e.ambAt = -1
                ambush(e)
                return
            }
            e.dist += e.speed * dt
            if e.dist >= Double(e.path.count - 1) * CKData.step {
                if e.state == "parade" { e.alive = false } else { e.state = "home" }
            } else {
                (e.x, e.y) = pathPos(e.path, e.dist, e.mirror)
            }
        case "home":
            let (sx, sy) = slot(e)
            let dx = sx - e.x, dy = sy - e.y
            let d = (dx * dx + dy * dy).squareRoot()
            let step = e.speed * dt
            if d <= step + 0.5 {
                e.x = sx; e.y = sy
                e.state = "form"; e.t = 0
                e.entered = true
            } else {
                e.x += dx / d * step
                e.y += dy / d * step
            }
        case "form":
            (e.x, e.y) = slot(e)
            if e.tele > 0 {      // formation volley: glow, then fire
                e.tele -= dt
                if e.tele <= 0 { enemyShot(e, 0) }
            }
            if e.kind == CK_SPORE && phase == "play" && deadT == nil {
                e.aux -= dt
                if e.aux <= 0 {
                    e.aux = st.fireGap * rnd(0.8, 1.5) / spd
                    for a in (tierN >= 8 ? [-14.0, 0, 14] : [0.0]) { enemyShot(e, a) }
                }
            }
        case "dive":
            let u = e.t / e.dur
            if u >= 1 {
                if e.extra {
                    e.alive = false
                } else if e.kind == CK_URCHIN {     // finished its mine-laying pass: fly straight back
                    e.state = "home"
                } else {
                    e.state = "home"
                    e.x = slot(e).0; e.y = -16
                }
                return
            }
            (e.x, e.y) = bezier(e.bez, u)
            for i in e.shots.indices where !e.shots[i].1 && u >= e.shots[i].0 {
                e.shots[i].1 = true
                enemyShot(e, 0)
            }
            if e.kind == CK_URCHIN && u > 0.2 && u < 0.85 {
                e.aux -= dt
                if e.aux <= 0 { e.aux = 0.4; addMine(e.x, e.y + 4, 0, 22, 4) }
            }
        case "dash":
            if e.t < 0.5 {          // wind-up: shiver in place, then shoot down at Tama
                let (sx, sy) = slot(e)
                e.x = sx + sin(e.t * 60) * 1.5; e.y = sy
            } else {
                if e.vx == 0 && e.vy == 0 {
                    let (cx, cy) = centre()
                    let a = atan2(cy - e.y, cx - e.x)
                    let v = 200 * (0.85 + 0.15 * spd)
                    e.vx = cos(a) * v; e.vy = max(60, sin(a) * v)
                    app.audio.play("move")
                }
                e.x += e.vx * dt
                e.y += e.vy * dt
                if e.y > Double(H + 16) || e.x < -20 || e.x > Double(W + 20) {
                    e.state = "home"; e.vx = 0; e.vy = 0
                    e.x = slot(e).0; e.y = -16
                }
            }
        case "kami":
            let sp = min(230, 80 + e.t * 110)
            var ang = atan2(e.vy, e.vx)
            let (cx, cy) = centre()
            if e.y < cy - 12 {
                let want = atan2(cy - e.y, cx - e.x)
                let diff = pmod(want - ang + .pi, TAU) - .pi
                ang += max(-2.2 * dt, min(2.2 * dt, diff))
            }
            e.vx = cos(ang) * sp; e.vy = sin(ang) * sp
            e.x += e.vx * dt
            e.y += e.vy * dt
            if Int(e.t * 20) != Int((e.t - dt) * 20) { parts.sparkle(e.x, e.y - 4, "orange") }
            if e.y > Double(H + 16) || e.x < -24 || e.x > Double(W + 24) || e.y < -40 {
                e.state = "home"; e.vx = 0; e.vy = 0
                e.x = slot(e).0; e.y = -16
            }
        case "free":
            if e.kind == CK_MINE {
                let k = min(1, dt * 1.5)
                e.vy += (16 - e.vy) * k
                e.vx -= e.vx * k
                e.aux -= dt
                if e.aux <= 0 {
                    e.alive = false
                    let n = tierN >= 10 || mode == "boss" ? 6 : 4
                    for i in 0 ..< n { bshot(e.x, e.y, TAU * Double(i) / Double(n) + 0.3, bulletSpeed() * 0.55, 3) }
                    parts.burst(e.x, e.y, 10, ["red", "orange", "yellow"], 60, 0.4)
                }
            } else if e.kind == CK_GOLD {
                e.y = 24 + sin(e.t * 3) * 6
                if Int(e.t * 15) != Int((e.t - dt) * 15) { parts.sparkle(e.x - (e.vx > 0 ? 8 : -8), e.y, rainbow(Int(e.t * 15))) }
            }
            e.x += e.vx * dt
            e.y += e.vy * dt
            if e.y > Double(H + 14) || e.x < -30 || e.x > Double(W + 30) { e.alive = false }
        default: break
        }
    }

    func bulletSpeed() -> Double { st.bv * spd }

    func enemyShot(_ e: CKEnemy, _ spread: Double) {
        if deadT != nil || e.y > PY_MIN - 10 { return }
        let (cx, cy) = centre()
        let sp = bulletSpeed()
        let a = atan2(cy - e.y, cx - e.x) + rad(spread)
        var vx = cos(a) * sp
        let vy = max(sin(a) * sp, sp * 0.35)
        vx = max(-sp * 0.7, min(sp * 0.7, vx))
        bullets.append(CKBullet(e.x, e.y + 5, vx, vy, 0))
    }

    func bshot(_ x: Double, _ y: Double, _ ang: Double, _ sp: Double, _ kind: Int) {
        if bullets.count < 240 { bullets.append(CKBullet(x, y, cos(ang) * sp, sin(ang) * sp, kind)) }
    }

    func addMine(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ fuse: Double) {
        let m = spawn(CK_MINE, 1)
        m.state = "free"; m.extra = true; m.x = x; m.y = y; m.vx = vx; m.vy = vy; m.aux = fuse
        spawned.append(m)
    }

    func spawnEvents(_ dt: Double) {
        // dives
        if stageT >= diveStart && deadT == nil {
            diveT -= dt
            if diveT <= 0 {
                let left = enemies.filter { !$0.extra }.count
                let rush = left <= 5
                diveT = st.diveGap / spd * rnd(0.75, 1.25) * (rush ? 0.5 : 1.0)
                launchDive(st.diveMax + (rush ? 1 : 0))
            }
        }
        // formation volleys: one row glows, then fires together
        if st.volley > 0 && stageT >= diveStart && deadT == nil {
            volleyT -= dt
            if volleyT <= 0 {
                volleyT = st.volley * rnd(0.8, 1.2) / spd
                let rows = Array(Set(enemies.filter { $0.state == "form" && !$0.extra }.map { $0.row })).sorted()
                if let r = rows.randomElement() {
                    for e in enemies where e.state == "form" && e.row == r && !e.extra { e.tele = 0.5 }
                }
            }
        }
        // meteor showers
        if st.mods.contains("METEORS") {
            meteorT -= dt
            if meteorT <= 0 {
                meteorT = rnd(2.5, 4.5)
                let m = spawn(CK_METEOR, 3)
                m.state = "free"; m.extra = true
                m.x = rnd(20, Double(W - 20)); m.y = -10; m.vx = rnd(-15, 15); m.vy = rnd(45, 70)
                spawned.append(m)
            }
        }
        // the rare golden comet
        if goldT > 0 && goldT <= stageT {
            goldT = -1
            let g = spawn(CK_GOLD, 4)
            let side: Double = Bool.random() ? 1 : -1
            g.state = "free"; g.extra = true
            g.x = side > 0 ? -16 : Double(W + 16); g.y = 24; g.vx = side * 85
            spawned.append(g)
            hype.banner("GOLDEN COMET!", "SHOOT IT!", color: "yellow", dur: 1.2, scale: 1, sound: "coin")
        }
    }

    func ambush(_ e: CKEnemy) {
        let side: Double = e.x < Double(W) / 2 ? 1 : -1
        if e.kind == CK_DART {
            e.state = "dash"; e.t = 0.5; e.vx = 0; e.vy = 0      // skip the wind-up: it is already moving
        } else if e.kind == CK_COMET {
            e.state = "kami"; e.t = 0; e.vx = side * 30; e.vy = 60
        } else {
            startDive(e, side, 0)
            e.bez = [(e.x, e.y), (e.x + side * 40, e.y + 30), (px - side * 30, 150), (px + side * 20, Double(H + 24))]
        }
        app.audio.play("move")
    }

    func launchDive(_ maxd: Int) {
        let ready = enemies.filter { $0.state == "form" && !$0.extra }
        let divers = enemies.filter { DIVING.contains($0.state) }.count
        if ready.isEmpty || divers >= maxd { return }
        var e = ready.randomElement()!
        if e.kind == CK_SPORE && Double.random(in: 0 ..< 1) < 0.6 { e = ready.randomElement()! }
        let side: Double = e.x < Double(W) / 2 ? 1 : -1
        if e.kind == CK_DART { e.state = "dash"; e.t = 0; e.vx = 0; e.vy = 0; return }
        if e.kind == CK_COMET {
            e.state = "kami"; e.t = 0; e.vx = side * 30; e.vy = 40
            app.audio.play("move")
            return
        }
        var group = [e]
        if e.kind == CK_PUFF {
            group += ready.filter { $0 !== e && ($0.kind == CK_MOTH || $0.kind == CK_JELLY) && abs($0.col - e.col) <= 2 && $0.row > e.row }.prefix(2)
        } else if e.kind == CK_MOTH {
            group += ready.filter { $0 !== e && $0.kind == CK_MOTH && abs($0.col - e.col) == 1 && $0.row == e.row }.prefix(1)
        }
        for (i, g) in group.enumerated() { startDive(g, side, (Double(i) - Double(group.count - 1) / 2) * 16) }
        app.audio.play("move")
    }

    func startDive(_ g: CKEnemy, _ side: Double, _ off: Double) {
        g.state = "dive"; g.t = 0
        let base = 2.5 * 130 / max(60, st.speed)
        g.dur = max(1.4, rnd(0.9, 1.1) * base / max(0.7, spd))
        let cx = px
        if g.kind == CK_URCHIN {
            let y2 = rnd(104, 118)
            g.bez = [(g.x, g.y), (g.x, y2 + 30), (Double(W) - g.x, y2 + 30), (Double(W) - g.x, g.y)]
            g.aux = 0.2
        } else {
            g.bez = [(g.x, g.y), (g.x + side * 70, g.y - 20), (cx + off - side * 40, 150), (cx + off + side * 30, Double(H + 24))]
        }
        var n = g.extra && mode != "boss" ? 0 : st.shots
        if g.kind == CK_MINI { n = mode == "boss" && (boss?.lv ?? 0) >= 2 ? 1 : 0 }
        g.shots = (0 ..< n).map { _ in (rnd(0.15, 0.55), false) }
    }

    // ------------------------------------------------------------------ boss
    func partPos(_ b: CKBoss, _ i: Int) -> (Double, Double, Bool) {
        let p = b.parts[i]
        if b.kind == 4 {     // RING GRUMP: moons orbit the planet, blocking shots while in front
            let a = b.t * 1.5 + Double(i) * TAU / 3
            return (b.x + cos(a) * 36, b.y + 4 + sin(a) * 14, sin(a) > -0.2)
        }
        return (b.x + p.dx + sin(b.t * 3 + Double(i)) * 2, b.y + p.dy + cos(b.t * 2.5 + Double(i)) * 1.5, true)
    }

    func updateBoss(_ dt: Double) {
        guard let b = boss else { return }
        b.t += dt
        b.flash = max(0, b.flash - dt)
        for p in b.parts { p.flash = max(0, p.flash - dt) }
        if b.state == "enter" {
            let u = min(1, b.t / 2.8)
            b.y = -40 + (b.hy + 40) * easeOut(u)
            if u >= 1 { b.state = "fight"; b.rest = 1.0 }
            return
        }
        if b.state == "dying" {
            b.at += dt
            if Int(b.at * 10) != Int((b.at - dt) * 10) {
                parts.burst(b.x + rnd(-b.bw / 2, b.bw / 2), b.y + rnd(-b.bh / 2, b.bh / 2), 14, ["white", "yellow", "orange", "pink"], 90, 0.6)
                app.audio.play("explode")
                app.shake(3, 0.15)
            }
            if b.at >= 2.2 {
                parts.burst(b.x, b.y, 70, ["white", "yellow", "orange", "pink", "sky"], 160, 1.2)
                hype.shower(80, "stars")
                hype.shower(50, "confetti")
                hype.flash("white", 0.4)
                app.shake(6, 0.6)
                app.audio.play("win")
                boss = nil
            }
            return
        }
        // fight
        if b.atk == nil {
            b.mt += dt
            b.rest -= dt
            if b.rest <= 0 { beginAttack(b) }
        } else {
            if !["laser", "charge", "teleport"].contains(b.atk!) { b.mt += dt * 0.4 }
            b.at += dt
            if runAttack(b, dt) {
                b.atk = nil
                b.rest = st.rest * (1 - 0.12 * Double(b.phase)) * (b.lv == 0 ? 1.25 : 1.0)
            }
        }
        if b.atk != "charge" && b.atk != "teleport" {
            let amp = b.kind == 2 ? 96.0 : (b.kind == 5 ? 34 : 70)
            let tx = b.cx + sin(b.mt * 0.7) * amp
            let old = b.x
            b.x += (tx - b.x) * min(1, dt * 3)
            b.y += (b.hy + sin(b.mt * 1.4) * 5 - b.y) * min(1, dt * 3)
            if abs(b.x - old) > 0.05 { b.face = b.x > old ? 1 : -1 }
        }
        // phases
        if b.phase < b.nphase - 1 && b.hp <= b.maxhp * (1 - Double(b.phase + 1) / Double(b.nphase)) {
            b.phase += 1
            b.atk = nil; b.rest = 1.2
            cancelBullets()
            hype.banner("ANGRY!!", "PHASE \(b.phase + 1)", color: "red", dur: 1.2, sound: "warning")
            hype.flash("red", 0.25)
            hype.hitstop(0.12)
            app.shake(4, 0.4)
        }
    }

    func beginAttack(_ b: CKBoss) {
        let names = b.phases[b.phase]
        let a = names[b.ai % names.count]
        b.atk = a
        b.ai += 1
        b.at = 0; b.an = 0
        let lv = b.lv, ph = b.phase
        if a == "summon" && enemies.filter({ $0.kind == CK_MINI }).count >= 8 { b.atk = "fan" }
        switch a {
        case "laser":
            var xs = [px]
            if lv >= 1 || ph >= 1 { xs += [px - 70, px + 70] }
            if lv >= 3 { xs += [px - 140, px + 140] }
            if b.kind == 3 && !b.parts.contains(where: { $0.alive }) { xs = [px] }
            b.lx = xs.map { max(8, min(Double(W) - 8, $0)) }
        case "rain":
            let n = min(18, 6 + 2 * lv + ph)
            b.rx = Array(Array(0 ..< 20).shuffled().prefix(n)).map { 8 + Double($0) * 16 + rnd(-3, 3) }
        case "wall":
            b.gap = rnd(50, Double(W) - 50)
        case "charge":
            b.tx = max(40, min(Double(W) - 40, px))
        case "teleport":
            let choices = [70.0, 115, 160, 205, 250].filter { abs($0 - b.cx) > 50 }
            b.tx = choices.randomElement() ?? 160
        case "spiral":
            b.dir = b.ai % 2 == 1 ? 1 : -1
            b.ang = rnd(0, TAU)
        default: break
        }
    }

    func muzzle(_ b: CKBoss) -> (Double, Double) { let (wx, wy, _) = b.weakPos(); return (wx, wy) }

    /// Advance the current attack; true when it is over. Every attack starts with a readable telegraph.
    func runAttack(_ b: CKBoss, _ dt: Double) -> Bool {
        let a = b.atk ?? "", at = b.at, lv = b.lv, ph = b.phase
        let bv = bulletSpeed()
        let (mx, my) = muzzle(b)
        let (cx, cy) = centre()
        let au = app.audio
        switch a {
        case "fan":
            let tele = 0.55, vol = min(3, 1 + (lv + ph) / 2), per = 0.5
            let te = at - tele
            while te >= 0 && b.an < vol && te >= Double(b.an) * per {
                var n = 5 + lv + ph
                n += 1 - n % 2
                let base = b.an % 2 == 0 ? atan2(cy - my, cx - mx) : Double.pi / 2
                for i in 0 ..< n { bshot(mx, my, base + rad(-30 + 60 * Double(i) / Double(n - 1)), bv, 0) }
                b.an += 1
                au.play("pop")
            }
            return te >= Double(vol) * per
        case "aim":
            let tele = 0.45, n = 3 + lv + ph, per = 0.16
            let te = at - tele
            while te >= 0 && b.an < n && te >= Double(b.an) * per {
                let srcs = b.kind == 1 ? b.parts.indices.filter { b.parts[$0].alive }.map { partPos(b, $0) } : []
                let (sx, sy) = srcs.isEmpty ? (mx, my) : (srcs[b.an % srcs.count].0, srcs[b.an % srcs.count].1)
                bshot(sx, sy, atan2(cy - sy, cx - sx), bv * 1.45, 2)
                b.an += 1
                au.play("tin")
            }
            return te >= Double(n) * per + 0.2
        case "ring":
            let tele = 0.6, rings = 1 + (lv >= 2 ? 1 : 0) + (ph >= 2 ? 1 : 0), per = 0.55
            let te = at - tele
            while te >= 0 && b.an < rings && te >= Double(b.an) * per {
                let n = 14 + 3 * lv + 2 * ph
                for i in 0 ..< n { bshot(b.x, b.y + 4, TAU * Double(i) / Double(n) + Double(b.an) * .pi / Double(n), bv * 0.75, 1) }
                b.an += 1
                au.play("pop")
            }
            return te >= Double(rings) * per + 0.2
        case "spiral":
            let tele = 0.5, dur = 2.0 + 0.3 * Double(lv)
            let per = max(0.07, 0.11 - 0.01 * Double(lv))
            let arms = 2 + lv / 2 + (ph >= 2 ? 1 : 0)
            let te = at - tele
            while te >= 0 && te < dur && Double(b.an) * per <= te {
                for k in 0 ..< arms {
                    bshot(b.x, b.y + 4, b.ang + TAU * Double(k) / Double(arms) + b.dir * 2.2 * Double(b.an) * per, bv * 0.7, 0)
                }
                b.an += 1
            }
            return te >= dur
        case "laser":
            let tele = 0.95, fire = 0.55
            if b.an == 0 && at >= tele {
                b.an = 1
                au.play("explode")
                app.shake(2, 0.3)
            }
            return at >= tele + fire
        case "rain":
            let tele = 0.7
            let te = at - tele
            while te >= 0 && b.an < b.rx.count && te >= Double(b.an) * 0.07 {
                bshot(b.rx[b.an], -4, .pi / 2, bv * 1.05, 1)
                b.an += 1
            }
            return te >= Double(b.rx.count) * 0.07 + 0.3
        case "summon":
            let tele = 0.5, n = 3 + lv, per = 0.22
            let te = at - tele
            while te >= 0 && b.an < n && te >= Double(b.an) * per {
                let m = spawn(CK_MINI, Double(1 + tierN / 8))
                m.extra = true
                m.x = b.x + rnd(-b.bw / 3, b.bw / 3); m.y = b.y + 6
                startDive(m, Bool.random() ? 1 : -1, rnd(-30, 30))
                spawned.append(m)
                b.an += 1
                au.play("bubble")
            }
            return te >= Double(n) * per + 0.2
        case "mines":
            let tele = 0.4, n = 3 + lv, per = 0.18
            let te = at - tele
            while te >= 0 && b.an < n && te >= Double(b.an) * per {
                addMine(b.x, b.y + 10, rnd(-70, 70), rnd(20, 50), 3.0)
                b.an += 1
                au.play("pop")
            }
            return te >= Double(n) * per + 0.2
        case "charge":
            let tele = 0.8
            if at < tele {
                b.x += (b.tx - b.x) * min(1, dt * 5)
                return false
            }
            let te = at - tele
            b.x = b.tx
            if te < 0.45 {
                b.y = b.hy + (150 - b.hy) * easeOut(te / 0.45)
            } else if te < 0.6 {
                b.y = 150
            } else if te < 1.4 {
                b.y = 150 - (150 - b.hy) * (te - 0.6) / 0.8
            }
            if b.an == 0 && te >= 0.45 {
                b.an = 1
                app.shake(3, 0.3)
                au.play("boom")
                if lv >= 1 { for i in 0 ..< 10 { bshot(b.x, b.y, .pi + .pi * Double(i) / 9, bv * 0.7, 0) } }
            }
            if te >= 1.4 { b.cx = Double(W) / 2; return true }
            return false
        case "wall":
            let tele = 0.6, rows = 1 + lv / 2 + (ph >= 2 ? 1 : 0), per = 1.0
            let te = at - tele
            while te >= 0 && b.an < rows && te >= Double(b.an) * per {
                if b.an > 0 { b.gap = max(40, min(Double(W) - 40, b.gap + (Bool.random() ? -60 : 60))) }
                var x = 8.0
                while x < Double(W - 4) {
                    if abs(x - b.gap) > 24 { bshot(x, b.y + 16, .pi / 2, bv * 0.55, 0) }
                    x += 13
                }
                b.an += 1
                au.play("pop")
            }
            return te >= Double(rows) * per
        case "teleport":
            if at < 0.45 {
                b.alpha = 1 - at / 0.45
            } else if b.an == 0 {
                b.an = 1
                b.cx = b.tx; b.x = b.tx
                b.mt = 0
                au.play("bubble")
            } else {
                b.alpha = min(1, (at - 0.45) / 0.4)
                if b.an == 1 && b.alpha >= 1 && (lv >= 1 || ph >= 1) {
                    b.an = 2
                    let n = 10 + 2 * lv
                    for i in 0 ..< n { bshot(b.x, b.y + 4, TAU * Double(i) / Double(n), bv * 0.7, 1) }
                }
            }
            if at >= 1.0 { b.alpha = 1; return true }
            return false
        default:
            return true
        }
    }

    func hurtBoss(_ dmg: Double, crit: Bool = false, _ x: Double = 0, _ y: Double = 0) {
        guard let b = boss else { return }
        b.hp -= dmg
        score += (crit ? 10 : 2) * hype.mult
        if crit {
            b.flash = 0.05
            parts.sparkle(x, y, "yellow")
            if tinT <= 0 { tinT = 0.09; app.audio.play("tin") }
        }
        if b.hp <= 0 { bossDie() }
    }

    func breakPart(_ b: CKBoss, _ i: Int) {
        let p = b.parts[i]
        p.alive = false
        let (x, y, _) = partPos(b, i)
        parts.burst(x, y, 24, ["white", "yellow", "pink", "lavender"], 100, 0.7)
        add(3000 + 300 * tierN, x, y - 8, "lime")
        say(x, y - 18, "BREAK!", "white")
        broken += 1
        hype.hitstop(0.06)
        hype.hit()
        app.shake(3, 0.2)
        app.audio.play("explode")
        hurtBoss(b.maxhp * CKData.bosses[b.kind].parts[i].3 * 0.5)
    }

    func bossDie() {
        guard let b = boss, b.state != "dying" else { return }
        b.state = "dying"; b.at = 0; b.atk = nil
        b.hp = 0
        cancelBullets()
        for e in enemies where e.extra && e.alive {
            e.alive = false
            parts.burst(e.x, e.y, 8, CKArt.kindColors[e.kind], 60, 0.5)
        }
        hype.hitstop(0.25)
        hype.slowmo(0.3, 1.6)
        hype.flash("white", 0.35)
        hype.banner("\(b.name) DOWN!", dur: 2.2, rainbow: true, sound: "bossdown")
        app.shake(6, 0.8)
        app.audio.stopMusic()
    }

    func shotBoss(_ sh: CKShot) {
        guard let b = boss, b.state != "dying" else { return }
        for (i, p) in b.parts.enumerated() where p.alive {
            let (x, y, front) = partPos(b, i)
            let r = Double(p.r + 2)
            if front && (sh.x - x) * (sh.x - x) + (sh.y - y) * (sh.y - y) <= r * r {
                sh.life = 0
                if b.state == "fight" {
                    p.hp -= sh.dmg
                    p.flash = 0.06
                    score += 2 * hype.mult
                    if p.hp <= 0 { breakPart(b, i) }
                }
                return
            }
        }
        if abs(sh.x - b.x) > b.bw / 2 || abs(sh.y - b.y) > b.bh / 2 { return }
        sh.life = 0
        if b.state != "fight" || b.alpha < 0.5 { parts.sparkle(sh.x, sh.y, "gray"); return }
        let (wx, wy, wr) = b.weakPos()
        let rr = Double(wr + 2)
        if (sh.x - wx) * (sh.x - wx) + (sh.y - wy) * (sh.y - wy) <= rr * rr {
            hurtBoss(sh.dmg * 2, crit: true, sh.x, sh.y)
        } else {
            hurtBoss(sh.dmg)
        }
    }

    // ------------------------------------------------------------------ items
    func drop(_ x: Double, _ y: Double, _ kind: String) {
        if kind == "M" { items.append(CKItem(x, y, rnd(-20, 20), -50, "M")) } else { items.append(CKItem(x, y, 0, 34, kind)) }
    }

    func cancelBullets(_ near: Double? = nil) {
        let (cx, cy) = centre()
        var keep: [CKBullet] = []
        var bits = items.filter { $0.kind == "c" }.count
        for b in bullets {
            if let nr = near, (b.x - cx) * (b.x - cx) + (b.y - cy) * (b.y - cy) > nr * nr { keep.append(b); continue }
            if bits < 140 {
                items.append(CKItem(b.x, b.y, rnd(-30, 30), rnd(-40, -10), "c"))
                bits += 1
            }
        }
        bullets = keep
    }

    func updateItems(_ dt: Double) {
        let (cx, cy) = centre()
        let alive = deadT == nil
        let mag = [0.0, 60, 130][lv("magnet")]
        var keep: [CKItem] = []
        for it in items {
            it.t += dt
            if it.kind == "c" {
                if it.t < 0.3 || !alive {
                    it.x += it.vx * dt
                    it.y += it.vy * dt
                    if it.t > 1.5 { continue }
                } else {
                    let dx = cx - it.x, dy = cy - it.y
                    let d = max(1, (dx * dx + dy * dy).squareRoot())
                    let v = 160 + it.t * 200
                    it.x += dx / d * v * dt
                    it.y += dy / d * v * dt
                }
            } else {
                let dx = cx - it.x, dy = cy - it.y
                let d = (dx * dx + dy * dy).squareRoot()
                if alive && d < mag {
                    it.x += dx / max(1, d) * 170 * dt
                    it.y += dy / max(1, d) * 170 * dt
                } else {
                    if it.kind == "M" {
                        it.vy = min(70, it.vy + 120 * dt)
                        it.vx *= max(0, 1 - dt)
                    } else {
                        it.vx = sin(it.t * 3) * 14
                    }
                    it.x += it.vx * dt
                    it.y += it.vy * dt
                }
                if it.y > Double(H + 6) {
                    if it.kind == "M" && medalI > 0 { medalI = 0; say(it.x, Double(H - 18), "CHAIN LOST", "gray") }
                    continue
                }
            }
            keep.append(it)
        }
        items = keep
    }

    func collect(_ it: CKItem) {
        let k = it.kind, au = app.audio
        let x = it.x, y = it.y
        let t = tierN
        if k == "c" { score += 10 * hype.mult; return }
        if k == "M" {
            let v = MEDALS[min(medalI, MEDALS.count - 1)]
            medalI += 1
            add(v, x, y - 8, "orange")
            au.play("coin")
            if medalI == MEDALS.count { hype.banner("MAX MEDAL!", "5000 EACH", color: "orange", dur: 1.2, scale: 1) }
            return
        }
        au.play("powerup")
        switch k {
        case "P": powerT = 20; say(x, y - 10, "POWER UP!", "yellow")
        case "F": friendT = 25; say(x, y - 10, "FRIEND STAR!", "pink")
        case "B":
            if bombs < 3 + lv("bombs") { bombs += 1; say(x, y - 10, "BOMB +1", "red") } else { add(2000, x, y - 10, "red") }
        case "S": shield = min(lv("shield") + 2, shield + 1); say(x, y - 10, "BUBBLE!", "mint")
        case "$":
            add(3000 * (1 + t / 4), x, y - 10, "orange")
            hype.shower(20, "coins")
            au.play("coin")
        case "L": hype.jackpot(15000 + 1500 * t, sub: "LUCKY STAR!")
        default: break
        }
    }

    // ------------------------------------------------------------------ collisions
    func collide() {
        for sh in shots {
            for e in enemies {
                if sh.life <= 0 { break }
                if sh.hits.contains(e.uid) || !hittable(e) { continue }
                let (w, h) = CKArt.sizes[e.kind]
                if abs(sh.x - e.x) <= Double(w) / 2 + 1.5 && abs(sh.y - e.y) <= Double(h) / 2 + 2 {
                    damage(e, sh.dmg)
                    if sh.pierce > 0 { sh.pierce -= 1; sh.hits.append(e.uid) } else { sh.life = 0 }
                }
            }
            if sh.life > 0 && boss != nil { shotBoss(sh) }
        }
        shots.removeAll { $0.life <= 0 }
        if deadT != nil || phase == "victory" { return }
        let (cx, cy) = centre()
        let hb = hitbox()
        var keep: [CKItem] = []
        for it in items {
            let r = it.kind == "c" ? 8.0 : 12.0
            if (it.x - cx) * (it.x - cx) + (it.y - cy) * (it.y - cy) < r * r { collect(it) } else { keep.append(it) }
        }
        items = keep
        if inv > 0 { return }
        let graze = lv("focus") >= 2
        for b in bullets {
            let r = b.kind == 1 ? 2.0 : 1.0
            if abs(b.x - cx) <= hb + r && abs(b.y - cy) <= hb + r {
                b.y = Double(H + 99)
                hurt()
                return
            }
            if graze && !b.grazed && abs(b.x - cx) < 12 && abs(b.y - cy) < 12 {
                b.grazed = true
                score += 20 * hype.mult
                hype.feverAdd(0.006)
                parts.sparkle(b.x, b.y, "white")
            }
        }
        if let b = boss, b.state == "fight" {
            if b.atk == "laser" && b.at >= 0.95 && b.at < 1.5 {
                for x in b.lx where abs(cx - x) <= 5 + hb - 1 { hurt(); return }
            }
            if abs(b.x - cx) <= b.bw / 2 + hb - 2 && abs(b.y - cy) <= b.bh / 2 + hb - 2 && b.alpha >= 0.5 { hurt(); return }
        }
        for e in enemies {
            if !e.alive || e.parade || e.kind == CK_GOLD || !HARMFUL.contains(e.state) || !solid(e) { continue }
            let (w, h) = CKArt.sizes[e.kind]
            if abs(e.x - cx) <= Double(w) / 2 + hb - 1 && abs(e.y - cy) <= Double(h) / 2 + hb - 1 {
                killEnemy(e)
                hurt()
                return
            }
        }
    }

    func damage(_ e: CKEnemy, _ dmg: Double) {
        e.hp -= dmg
        if e.hp > 0 {
            if e.flash <= 0 { app.audio.play("tin") }
            e.flash = 0.12
            return
        }
        killEnemy(e)
    }

    func killEnemy(_ e: CKEnemy) {
        if !e.alive { return }
        e.alive = false
        let t = tierN
        let au = app.audio
        let diving = DIVING.contains(e.state)
        parts.burst(e.x, e.y, 16, CKArt.kindColors[e.kind], 80, 0.6)
        au.play("explode")
        if e.kind == CK_GOLD && !e.parade {
            parts.burst(e.x, e.y, 40, ["yellow", "orange", "white"], 140, 1.0)
            hype.jackpot(20000 + 2000 * t, sub: "GOLDEN COMET +\((20000 + 2000 * t) * hype.mult)")
            hype.hit()
            return
        }
        if e.parade {
            hits += 1
            var sq = squads[e.group] ?? (1, 0)
            sq.1 += 1
            squads[e.group] = sq
            if e.kind == CK_GOLD {
                add(5000 + 500 * t, e.x, e.y - 8, "yellow")
                hype.shower(24, "coins")
                au.play("coin")
            } else {
                add(100 + 20 * t, e.x, e.y - 8, "yellow")
            }
            if sq.1 == sq.0 {
                add(1000 + 200 * t, e.x, e.y - 18, "lime")
                say(e.x, e.y - 28, "WAVE PERFECT!", "lime")
                au.play("bonus")
            }
            hype.hit(fever: 0.02)
            return
        }
        let k = CKData.kinds[e.kind]
        let base = diving ? k.ptsDive : k.ptsForm
        let pts = Int(Double(base) * (1 + 0.1 * Double(t))) / 10 * 10 + hype.comboBonus(5)
        add(pts, e.x, e.y - 8, diving ? "mint" : "yellow")
        hype.hit(fever: 0.028)
        if !e.extra && !e.entered && e.group >= 0 {
            var sq = squads[e.group] ?? (1, 0)
            sq.1 += 1
            squads[e.group] = sq
            if sq.1 == sq.0 {
                squadWipes += 1
                say(e.x, e.y - 18, "SQUAD!", "lime")
                au.play("bonus")
            }
        }
        if e.cap >= 0 { drop(e.x, e.y, hype.lucky(0.015) ? "L" : CKData.capsules[e.cap]) }
        if e.kind == CK_PUFF || e.kind == CK_SHELL || (diving && Double.random(in: 0 ..< 1) < 0.3) { drop(e.x, e.y, "M") }
        if e.kind == CK_PUFF && diving && friendT <= 0 && Double.random(in: 0 ..< 1) < 0.35 { drop(e.x + 6, e.y, "F") }
        if e.kind == CK_BLOB {
            for sd in [-1.0, 1.0] {
                let m = spawn(CK_MINI, 1)
                m.extra = true
                m.x = e.x + sd * 5; m.y = e.y
                startDive(m, sd, sd * 12)
                spawned.append(m)
            }
        }
    }

    func hurt() {
        let au = app.audio
        let (cx, cy) = centre()
        if shield > 0 {
            shield -= 1
            inv = 1.2
            cancelBullets(48)
            parts.burst(cx, cy, 20, ["mint", "white", "sky"], 90, 0.5)
            au.play("pop")
            say(cx, cy - 18, "POP!", "mint")
            app.shake(2, 0.2)
            return
        }
        lives -= 1
        deaths += 1
        deadT = 1.6
        friendT = 0; powerT = 0
        medalI = 0
        hype.breakCombo()
        au.play("boom")
        app.shake(4, 0.4)
        hype.flash("red", 0.2)
        parts.burst(cx, cy, 30, ["orange", "yellow", "white", "pink"], 110, 1.0)
    }

    func bomb() {
        if bombs <= 0 || deadT != nil || !["intro", "play", "warning"].contains(phase) { return }
        bombs -= 1
        bombT = 0.9
        (bombX, bombY) = centre()
        inv = max(inv, 1.6)
        cancelBullets()
        let pouch = lv("bombs")
        for e in enemies where e.alive && e.state != "wait" && e.kind != CK_GOLD && e.y > -10 && e.y < Double(H + 10) && !e.parade {
            damage(e, Double(5 + 2 * pouch))
        }
        if let b = boss, b.state == "fight" {
            if b.atk == "laser" { b.atk = nil; b.rest = 1.0 }
            hurtBoss(b.maxhp * (0.035 + 0.01 * Double(pouch)))
        }
        hype.flash("white", 0.3)
        hype.hitstop(0.08)
        app.shake(5, 0.5)
        app.audio.play("boom")
        say(bombX, bombY - 20, "COMET BURST!", "orange")
    }

    // ------------------------------------------------------------------ draw
    override func render(_ s: Surface) {
        let t = self.t
        if let bg = bg { s.blit(bg, 0, 0) }
        if warp > 0.05 {
            let ln = Int(warp * 14)
            for (x, y, z) in stars.s {
                s.fillRect(col(["darkgray", "lavender", "white"][z - 1]), Int(x), Int(y) - ln * z / 2, 1, 1 + ln * z / 2)
            }
        } else {
            stars.draw(s, t)
        }
        if let b = boss, b.state == "fight" { drawTells(s, b) }
        for it in items {
            if it.kind == "c" {
                s.fillRect(col(Int(t * 12 + it.x) % 2 == 1 ? "sky" : "white"), Int(it.x) - 1, Int(it.y) - 1, 2, 2)
            } else {
                CKArt.capsule(s, it.kind, Int(it.x), Int(it.y), t + it.t)
            }
        }
        for e in enemies where e.state != "wait" {
            let glow: Bool
            if e.kind == CK_MINE {
                glow = Int(t * (e.aux < 1.0 ? 16 : 3)) % 2 == 1
            } else {
                glow = (e.kind == CK_SPORE && e.state == "form" && e.aux < 0.45 && phase == "play") ||
                    (e.kind == CK_DART && e.state == "dash" && e.t < 0.5) || e.tele > 0
            }
            CKArt.enemy(s, e.kind, Int(e.x), Int(e.y), t + e.seed, hit: e.flash > 0, glow: glow, faded: !solid(e),
                        hp: Int(e.hp.rounded(.up)), d: e.vx >= 0 ? 1 : -1)
            if e.cap >= 0 && e.state != "free" && Int(t * 6) % 2 == 1 { s.circle(col("yellow"), Int(e.x), Int(e.y), 9, width: 1) }
        }
        if let b = boss { drawBoss(s, b) }
        for sh in shots {
            let x = Int(sh.x), y = Int(sh.y)
            switch sh.kind {
            case 1:
                s.fillRect(col("sky"), x - 1, y - 5, 3, 9)
                s.fillRect(col("white"), x, y - 5, 1, 7)
            case 2:
                s.fillRect(col("pink"), x - 1, y - 3, 2, 5)
            case 3:
                s.fillRect(col("lime"), x - 1, y, 3, 1)
                s.fillRect(col("lime"), x, y - 1, 1, 3)
            case 4:
                let c = col(rainbow(ckFdiv(x, 8), t))
                s.fillRect(c, x - 1, y, 3, 1)
                s.fillRect(c, x, y - 1, 1, 3)
            default:
                s.fillRect(col("yellow"), x - 1, y - 3, 3, 6)
                s.fillRect(col("white"), x, y - 3, 1, 3)
            }
        }
        drawPlayer(s)
        for bl in bullets {
            let x = Int(bl.x), y = Int(bl.y)
            switch bl.kind {
            case 1:
                s.circle(col("black"), x, y, 4)
                s.circle(col("hotpink"), x, y, 3)
                s.fillRect(col("white"), x - 1, y - 1, 2, 2)
            case 2:
                s.fillRect(col("black"), x - 2, y - 3, 4, 7)
                s.fillRect(col("red"), x - 1, y - 2, 2, 5)
                s.fillRect(col("white"), x - 1, y - 2, 1, 1)
            default:
                s.circle(col("black"), x, y, 3)
                s.circle(col(bl.kind == 3 ? "orange" : "pink"), x, y, 2)
                s.fillRect(col("white"), x - 1, y - 1, 1, 1)
            }
        }
        if let b = boss, b.state == "fight", b.atk == "laser", b.at >= 0.95 {
            for x in b.lx {
                let xi = Int(x), fl = Int(t * 30) % 2
                s.fillRect(col("hotpink"), xi - 5, Int(b.y) + 8, 10, H)
                s.fillRect(col("white"), xi - 2 - fl, Int(b.y) + 8, 4 + fl * 2, H)
            }
        }
        if bombT > 0 {
            let r = Int((0.9 - bombT) / 0.9 * 330)
            s.circle(col("white"), Int(bombX), Int(bombY), r, width: 3)
            if r > 6 { s.circle(col("yellow"), Int(bombX), Int(bombY), r - 5, width: 2) }
        }
        parts.draw(s)
        floats.draw(s)
        drawHud(s)
        if phase == "intro" { drawIntro(s) } else if phase == "warning" { drawWarning(s) } else if phase == "tally", tally != nil { drawTally(s) }
    }

    override func draw(_ s: Surface) {
        super.draw(s)
        if paused { drawPower(s, 160) }
    }

    /// Pause screen: the upgrades collected so far.
    func drawPower(_ s: Surface, _ y: Int) {
        let owned = CK_POOL.filter { lv($0.id) > 0 }
        if owned.isEmpty { return }
        let x0 = W / 2 - owned.count * 13 + 13
        for (i, u) in owned.enumerated() {
            let cx = x0 + i * 26
            s.circle(col(u.color), cx, y, 12)
            s.circle(col("ink"), cx, y, 10)
            u.draw?(s, cx, y, t)
            for p in 0 ..< u.max { s.fillRect(col(p < lv(u.id) ? "yellow" : "darkgray"), cx - u.max * 2 + p * 4, y + 14, 3, 3) }
        }
    }

    func drawPlayer(_ s: Surface) {
        let t = self.t
        if deadT != nil { return }
        for i in 0 ..< npals() {
            let p = pals[i]
            let temp = i >= lv("pals")
            if !temp || friendT > 3 || Int(t * 8) % 2 == 1 {
                s.blit(sprite("star"), Int(p.0) - 3, Int(p.1) - 3 + Int(sin(t * 6 + Double(i)) * 2))
            }
        }
        if inv > 0 && Int(inv * 12) % 2 == 1 { return }
        let x = Int(px), y = Int(py)
        let bob = Int(sin(t * 5) * 1)
        let flame = Int(t * 20) % 2
        s.fillRect(col(flame == 1 ? "orange" : "yellow"), x - 2, y + 16 + bob, 4, 2 + flame + (vy < -20 ? 2 : 0))
        s.blit(sprite("kitty"), x - 8, y + bob)
        if lv("focus") >= 1 {
            let (cx, cy) = centre()
            s.fillRect(col(Int(t * 6) % 2 == 1 ? "hotpink" : "white"), Int(cx) - 1, Int(cy) - 1, 2, 2)
        }
        if shield > 0 {
            bubble(s, Double(x), Double(y + 8), 12, t, tint: "mint")
            if shield > 1 { s.circle(col("white"), x, y + 8, 14, width: 1) }
        }
    }

    func drawBoss(_ s: Surface, _ b: CKBoss) {
        let t = self.t
        if b.alpha < 1 && Int(t * 30) % 3 >= Int(b.alpha * 3) { return }
        var views: [CKArt.PartView] = []
        for (i, p) in b.parts.enumerated() {
            let (x, y, front) = partPos(b, i)
            views.append(CKArt.PartView(x: Int(x), y: Int(y), r: p.r, alive: p.alive, flash: p.flash, front: front))
        }
        let look = max(-2, min(2, Int((px - b.x) / 30)))
        let ox = b.atk == "charge" && b.at < 0.8 ? Int(sin(t * 50) * 2) : 0
        CKArt.boss(s, b, Int(b.x) + ox, Int(b.y), t, views, look)
        if let a = b.atk, b.at < 0.6, ["fan", "aim", "ring", "spiral", "summon", "mines"].contains(a) {
            let (mx, my) = muzzle(b)
            let r = Int(14 * (1 - b.at / 0.6)) + 2
            s.circle(col(Int(t * 20) % 2 == 1 ? "white" : "yellow"), Int(mx), Int(my), r, width: 1)
        }
    }

    /// Telegraphs drawn under everything: laser warning lines, rain markers, wall preview, charge lane.
    func drawTells(_ s: Surface, _ b: CKBoss) {
        let t = self.t
        let blink = Int(t * 12) % 2 == 1
        switch b.atk {
        case "laser" where b.at < 0.95:
            for x in b.lx {
                let c = col(blink ? "red" : "white")
                var yy = Int(b.y) + 10
                while yy < H { s.fillRect(c, Int(x), yy, 1, 4); yy += 7 }
                drawText(s, "!", Int(x) - 2, Int(PY_MIN) - 12, blink ? "red" : "yellow", shadow: nil)
            }
        case "rain" where b.at < 0.9:
            for x in b.rx {
                let xi = Int(x)
                s.polygon(col(blink ? "yellow" : "orange"), [(Double(xi - 3), 14), (Double(xi + 3), 14), (Double(xi), 18)])
            }
        case "wall" where b.at < 0.6:
            let yy = Int(b.y) + 16
            var x = 8
            while x < W - 4 {
                if abs(Double(x) - b.gap) > 24 { s.fillRect(col(blink ? "pink" : "white"), x - 1, yy, 3, 2) }
                x += 13
            }
            drawText(s, "{}", Int(b.gap) - 6, yy - 3, "lime", shadow: nil)
        case "charge" where b.at < 0.8:
            for sx in [-1.0, 1.0] {
                let x = Int(b.tx + sx * b.bw / 2)
                var yy = Int(b.y) + 10
                while yy < H { s.fillRect(col(blink ? "red" : "orange"), x, yy, 1, 3); yy += 6 }
            }
        case "teleport" where b.an == 0:
            let r = Int(4 + (0.45 - min(0.45, b.at)) * 40)
            s.circle(col("hotpink"), Int(b.tx), Int(b.hy), r, width: 1)
        default: break
        }
    }

    func drawHud(_ s: Surface) {
        drawText(s, String(format: "%07d", score), 4, 2, "white")
        drawText(s, "@\(max(0, lives))", 49, 2, "pink")
        if let b = boss, phase != "warning" {
            bossBar(s, b.name, b.hp, b.maxhp, t)
        } else {
            drawText(s, String(format: "HI %07d", max(best, score)), W / 2, 2, "lavender", align: .center)
        }
        let c = mode == "boss" ? "red" : (mode == "bonus" ? "mint" : "yellow")
        drawText(s, "STAGE \(stageN)", W - 4, 2, c, align: .right)
        let y = H - 8
        for i in 0 ..< max(0, min(bombs, 6)) {
            let x = 6 + i * 8
            s.circle(col("black"), x, y + 3, 4)
            s.circle(col("red"), x, y + 3, 3)
            s.fillRect(col("white"), x - 1, y + 1, 1, 1)
        }
        let x0 = 8 + max(0, min(bombs, 6)) * 8
        for i in 0 ..< max(0, min(shield, 4)) { s.circle(col("mint"), x0 + i * 8, y + 3, 3, width: 1) }
        if medalI > 0 {
            drawText(s, "MEDAL \(MEDALS[min(medalI, MEDALS.count - 1)])", W / 2, y, "orange", align: .center)
        }
        if !hype.feverOn {
            let x = W - 44
            s.fillRect(col("black"), x - 1, y + 1, 42, 5)
            s.fillRect(col("darkgray"), x, y + 2, 40, 3)
            s.fillRect(col(hype.fever > 0.8 ? rainbow(0, t) : "peach"), x, y + 2, Int(40 * hype.fever), 3)
            drawText(s, "FEVER", x - 32, y, "gray", shadow: nil)
        }
    }

    func drawIntro(_ s: Surface) {
        let a = introT
        let drop = Int((1 - easeOut(min(1, a / 0.25))) * -60) + Int(easeOut(max(0, (a - 2.1) / 0.3)) * -80)
        let y0 = 100 + drop
        if mode == "bonus" {
            panel(s, IRect(40, y0, 240, 40), fill: "ink", border: "mint")
            drawText(s, "BONUS PARADE!", W / 2, y0 + 6, "mint", scale: 2, align: .center, outline: "ink")
            drawText(s, "SHOOT THEM ALL - THEY CAN'T SHOOT", W / 2, y0 + 26, "white", align: .center)
            return
        }
        let new = st.new
        panel(s, IRect(60, y0, 200, new < 0 ? 44 : 62), fill: "ink", border: "yellow")
        drawText(s, "STAGE \(stageN)", W / 2, y0 + 6, "yellow", scale: 2, align: .center, outline: "ink")
        let sub = st.mods.isEmpty ? theme.name : st.mods.joined(separator: " + ") + "!"
        drawText(s, sub, W / 2, y0 + 26, st.mods.isEmpty ? "lavender" : "orange", align: .center)
        if stageN == 1 {
            drawText(s, "A: SHOOT (HOLD)   B: COMET BURST", W / 2, y0 + 48, "mint", align: .center, outline: "ink")
        }
        if new >= 0 {
            let k = CKData.kinds[new]
            CKArt.enemy(s, new, 76, y0 + 47, t, hp: 3)
            drawText(s, "NEW: \(k.name)", 90, y0 + 38, "lime", shadow: nil)
            drawText(s, k.desc, 90, y0 + 48, "white", shadow: nil)
        }
    }

    func drawWarning(_ s: Surface) {
        let t = self.t
        for by in [50, 116] {
            s.fillRect(col("yellow"), 0, by, W, 8)
            let off = Int(t * 40) % 12
            for i in -1 ..< 29 {
                let x = i * 12 + off
                s.polygon(col("black"), [(Double(x), Double(by)), (Double(x + 5), Double(by)), (Double(x + 1), Double(by + 7)),
                                         (Double(x - 4), Double(by + 7))])
            }
        }
        if Int(t * 4) % 2 == 0 {
            drawText(s, "WARNING", W / 2, 66, "red", scale: 3, align: .center, outline: "ink")
        } else {
            drawText(s, "WARNING", W / 2, 66, "white", scale: 3, align: .center, outline: "red")
        }
        if let b = boss {
            drawText(s, "\(b.name) APPROACHING", W / 2, 92, "white", align: .center, outline: "ink")
            drawText(s, b.final ? "THE FINAL GUARDIAN!" : CKData.bosses[b.kind].intro, W / 2, 103, "peach", align: .center, outline: "ink")
        }
    }

    func drawTally(_ s: Surface) {
        guard let tl = tally else { return }
        let n = tl.lines.count
        let h = 34 + n * 11 + 14
        let y0 = 92 - h / 2
        panel(s, IRect(50, y0, 220, h), fill: "ink", border: "yellow")
        drawText(s, tl.title, W / 2, y0 + 6, mode == "boss" ? rainbow(0, t) : "yellow", align: .center)
        for i in 0 ..< tl.shown {
            let (label, v) = tl.lines[i]
            let age = tl.t - (0.35 + Double(i) * 0.4)
            let shown = Int(Double(v) * min(1, age / 0.3))
            let y = y0 + 20 + i * 11
            let perfect = label.hasPrefix("PERFECT")
            drawText(s, label, 60, y, perfect ? rainbow(i, t) : "white", shadow: nil)
            drawText(s, v > 0 ? "\(shown)" : "-", 260, y, v > 0 ? "lime" : "gray", align: .right, shadow: nil)
        }
        if tl.shown >= n {
            let y = y0 + 22 + n * 11
            s.fillRect(col("lavender"), 60, y - 2, 200, 1)
            drawText(s, "TOTAL", 60, y + 2, "yellow", shadow: nil)
            drawText(s, "\(tl.total * hype.mult)", 260, y + 2, "yellow", align: .right, shadow: nil)
        }
    }

    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        s.fill(col("night"))
        let st = Stars(25, seed: 2)
        st.update(t, 15)
        st.draw(s, t)
        let kinds = [CK_JELLY, CK_MOTH, CK_DART, CK_SPORE, CK_BLOB, CK_COMET]
        for i in 0 ..< 6 { CKArt.enemy(s, kinds[i], 10 + i * (w - 20) / 5, 10 + (i % 2) * 10 + Int(sin(t * 2 + Double(i)) * 2), t) }
        CKArt.enemy(s, CK_PUFF, w / 2 + Int(sin(t) * 20), 34 + Int(sin(t * 2) * 5), t)
        let kx = w / 2 + Int(sin(t * 1.5) * 24)
        s.blit(sprite("kitty"), kx - 8, h - 18)
        for i in 0 ..< 3 {
            let y = h - 24 - (Int(t * 90) + i * 14) % 42
            s.fillRect(col("yellow"), kx - 1, y, 3, 5)
        }
    }
}
