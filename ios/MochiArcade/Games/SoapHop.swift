// SOAP HOP - single-screen bubble platformer, 200-stage campaign (port of games/soap_hop.py - keep in step).
// Stages, themes and boss parameters come from the Python generator through GameData.json("soap_hop").
import Foundation

private let T = 8, COLS = 40, ROWS = 23, TOP = 12
private let FIELD_H = ROWS * T
private let FLOOR_Y = TOP + 21 * T
private let GRAV = 620.0, JUMP = 255.0, RUN = 74.0, FAST_PHASE = 0.32
private let LETTERS = ["M", "O", "C", "H", "I"]
private let POWERS = ["soda", "clock", "gem", "shield"]

@inline(__always) private func pmod(_ a: Int, _ b: Int) -> Int { ((a % b) + b) % b }

// ---------------------------------------------------------------------- exported stage table
struct SHStage {
    var k = "normal", nm = "", th = 0
    var map: [String] = []
    var p = [19, 20]
    var en: [(String, Int, Int, Int)] = []
    var mods: [String] = []
    var wind = 0, par = 60
    var new = ""
    var boss = "king", lv = 0, hp = 10
    var pat: [String] = []
    var spd = 1.0
    var bt = "party", time = 20
}

struct SHTheme { let name, blk, blkD, plat, platD, skyA, skyB, style: String; let snack: Int }

enum SHData {
    static let root: [String: Any] = (GameData.json("soap_hop") as? [String: Any]) ?? [:]

    private static func int(_ v: Any?) -> Int { (v as? NSNumber)?.intValue ?? 0 }

    /// "4#4.2=" -> "####....==" (map rows are run-length encoded in the export)
    static func unrle(_ s: String) -> String {
        var out = "", n = 0
        for ch in s {
            if let d = ch.wholeNumberValue { n = n * 10 + d } else { out += String(repeating: ch, count: n); n = 0 }
        }
        return out
    }

    static let stages: [SHStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var s = SHStage()
        s.k = d["k"] as? String ?? "normal"
        s.nm = d["nm"] as? String ?? ""
        s.th = int(d["th"])
        s.map = (d["map"] as? [String] ?? []).map(unrle)
        s.p = (d["p"] as? [Any])?.map { int($0) } ?? [19, 20]
        s.en = ((d["en"] as? [[Any]]) ?? []).map { ($0[0] as? String ?? "g", int($0[1]), int($0[2]), int($0[3])) }
        s.mods = d["mods"] as? [String] ?? []
        s.wind = int(d["wind"])
        s.par = int(d["par"])
        s.new = d["new"] as? String ?? ""
        s.boss = d["boss"] as? String ?? "king"
        s.lv = int(d["lv"])
        s.hp = max(1, int(d["hp"]))
        s.pat = d["pat"] as? [String] ?? ["hop"]
        s.spd = (d["spd"] as? NSNumber)?.doubleValue ?? 1
        s.bt = d["bt"] as? String ?? "party"
        s.time = d["time"] == nil ? 20 : int(d["time"])
        return s
    }

    static let themes: [SHTheme] = ((root["themes"] as? [[Any]]) ?? []).map { a in
        let s = a.prefix(8).map { $0 as? String ?? "white" }
        return SHTheme(name: s[0], blk: s[1], blkD: s[2], plat: s[3], platD: s[4], skyA: s[5], skyB: s[6], style: s[7],
                       snack: int(a[8]))
    }

    /// kind -> (name, intro tier, flies, blurb)
    static let enemies: [String: (String, Int, Bool, String)] = ((root["enemies"] as? [String: [Any]]) ?? [:]).mapValues {
        ($0[0] as? String ?? "", int($0[1]), ($0[2] as? NSNumber)?.boolValue ?? false, $0[3] as? String ?? "")
    }

    static let mods: [String: String] = (root["mods"] as? [String: String]) ?? [:]
}

// ---------------------------------------------------------------------- entities
class SHBody {
    var x, y: Double
    let w, h: Int
    var vx = 0.0, vy = 0.0
    var onGround = false
    init(_ x: Double, _ y: Double, _ w: Int, _ h: Int) { self.x = x; self.y = y; self.w = w; self.h = h }
    var cx: Double { x + Double(w) / 2 }
    var cy: Double { y + Double(h) / 2 }
    func rect() -> IRect { IRect(Int(x), Int(y), w, h) }
}

final class SHEnemy: SHBody {
    let kind: String
    let base: Double
    var face = Bool.random() ? 1 : -1
    var vdir = Bool.random() ? 1.0 : -1.0
    var angry: Bool
    var think = Double.random(in: 0.5 ... 1.5)
    var golden = false
    var lid: Bool
    var mode = "walk", modeT = 0.0
    var cool = Double.random(in: 1.5 ... 3.0)
    var swell = 0.0, stun = 0.0
    var minion = false
    init(_ kind: String, _ x: Double, _ y: Double, _ speed: Double, angry: Bool = false) {
        self.kind = kind; base = speed; self.angry = angry; lid = kind == "s"
        super.init(x, y, 12, 13)
    }
}

final class SHBubble {
    var x, y, vx, vy: Double
    var age = 0.0, life: Double
    var enemy: SHEnemy?
    let seed = Double.random(in: 0 ..< 6.28)
    var popIn: Double?
    var dead = false
    let kind: String          // normal | letter | party
    var sub = 0, value = 0
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ life: Double, _ kind: String = "normal") {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.life = life; self.kind = kind
    }
}

final class SHItem: SHBody {
    let kind: String
    let sub: Int, value: Int
    var life = 9.0
    var rain = false
    init(_ x: Double, _ y: Double, _ kind: String, _ sub: Int = 0, _ value: Int = 0) {
        self.kind = kind; self.sub = sub; self.value = value
        super.init(x, y, 8, 8)
        vx = Double.random(in: -40 ... 40); vy = -140
    }
}

final class SHShot {
    let kind: String
    var x, y, vx, vy: Double
    var age = 0.0
    var dead = false
    let r: Double, grav: Double, warn: Double
    init(_ kind: String, _ x: Double, _ y: Double, _ vx: Double, _ vy: Double) {
        self.kind = kind; self.x = x; self.y = y; self.vx = vx; self.vy = vy
        r = ["dust": 3.0, "drop": 3.0, "water": 2.0][kind] ?? 0
        grav = ["drop": 260.0, "water": 420.0][kind] ?? 0
        warn = ["bolt": 0.75, "mark": 0.85][kind] ?? 0
    }
}

let SH_UPGRADES: [Upgrade] = [
    Upgrade(id: "range", name: "BIG BLOW", desc: "BUBBLES FLY|FARTHER", color: "sky", draw: SHArt.iconRange, max: 3),
    Upgrade(id: "rate", name: "RAPID PUFF", desc: "BLOW FASTER|+2 BUBBLES|AT ONCE", color: "mint", draw: SHArt.iconRate, max: 3),
    Upgrade(id: "trap", name: "STICKY SOAP", desc: "BIGGER BUBBLES|HOLD GRUMPS|LONGER", color: "lavender", draw: SHArt.iconTrap, max: 3),
    Upgrade(id: "speed", name: "QUICK FEET", desc: "RUN FASTER", color: "lime", draw: SHArt.iconSpeed, max: 3),
    Upgrade(id: "jump", name: "SPRING EARS", desc: "HIGHER JUMP|LV2: DOUBLE|JUMP IN AIR", color: "yellow", draw: SHArt.iconJump, max: 3),
    Upgrade(id: "heart", name: "EXTRA HEART", desc: "+1 LIFE|RIGHT NOW", color: "pink", draw: SHArt.iconHeart, max: 3),
    Upgrade(id: "chain", name: "CHAIN CHARM", desc: "WIDER CHAINS|+50% CHAIN|POINTS", color: "orange", draw: SHArt.iconChain, max: 3),
    Upgrade(id: "magnet", name: "SNACK MAGNET", desc: "PULLS SNACKS|AND ITEMS|TO YOU", color: "red", draw: SHArt.iconMagnet, max: 3),
    Upgrade(id: "shield", name: "BUBBLE SHIELD", desc: "BLOCKS 1 HIT|EVERY STAGE|LV2: REFILLS", color: "teal", draw: SHArt.iconShield, max: 2),
    Upgrade(id: "twin", name: "TWIN BLOW", desc: "A 2ND BUBBLE|FLIES UPWARD", color: "hotpink", draw: SHArt.iconTwin, max: 1),
]

// ---------------------------------------------------------------------- the game
final class SoapHop: GameScene {
    private var stageMusic = "soap"
    override var music: String? { stageMusic }
    override var buttons: [Action: String] { [.a: "JUMP", .b: "BUBBLE"] }
    override var buttonOrder: [Action] { [.a, .b] }
    override var fourWay: Bool { false }

    var lives: Int, spd: Double, trapBase: Double, stage: Int
    var ups: [String: Int] = [:]
    var letters = [false, false, false, false, false]
    var nextExtra = 50000
    var picks = 0, afterPicks = "", pickTitle = "POWER UP!"
    var wasFever = false
    var tally: [(String, Int, Double)] = [], tallyI = 0, tallyT = 0.0, tallyTotal = 0

    var sd = SHStage()
    var kind = "normal", tierN = 0
    var theme = SHTheme(name: "", blk: "pink", blkD: "hotpink", plat: "cream", platD: "peach", skyA: "deep", skyB: "night", style: "bubbles", snack: 0)
    var map: [[Character]] = []
    var levelName = ""
    var mods: [String] = []
    var wind = 0
    var enemies: [SHEnemy] = [], bubbles: [SHBubble] = [], items: [SHItem] = [], shots: [SHShot] = []
    var espeed = 1.0
    var start = (0.0, 0.0)
    var player = SHBody(0, 0, 12, 14)
    var face = 1, inv = 2.0, shootCd = 0.0, coyote = 0.0, jumpBuf = 0.0, airJumps = 0, bounces = 0
    var shield = false, shieldT = 0.0
    var levelT = 0.0, hurry = false
    var chain = 0, chainT = 0.0, bestChain = 0
    var missed = false, snacksOut = 0, snacksGot = 0
    var freezeT = 0.0
    var boss: SHBoss?
    var letterT = -1.0
    var bonusN = 0, bonusGot = 0, spawnT = 0.0, timeLeft = 20.0
    var state = "intro", stateT = 0.0, introState = "intro"
    var field = Surface(W, FIELD_H)

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        spd = SPEEDS[d] ?? 1
        trapBase = ["easy": 9.0, "normal": 7.0, "hard": 5.0][d] ?? 7
        stage = max(1, min(STAGES, Int(opt["stage"] ?? opt["start"] ?? "1") ?? 1))
        super.init(app, info, opt)
        for u in SH_UPGRADES { ups[u.id] = 0 }
        loadStage()
        let head = min(5, tier(stage))
        if head > 0 {           // starting from a checkpoint: catch up on the upgrades a full run would have
            picks = head; afterPicks = "intro"; pickTitle = "HEAD START!"
            state = "picks"
        }
    }

    func up(_ id: String) -> Int { ups[id] ?? 0 }

    // ------------------------------------------------------------------ stage setup
    func loadStage() {
        let all = SHData.stages
        sd = all.isEmpty ? SHStage() : all[min(all.count, stage) - 1]
        kind = sd.k
        tierN = tier(stage)
        if !SHData.themes.isEmpty { theme = SHData.themes[min(sd.th, SHData.themes.count - 1)] }
        map = sd.map.map { Array($0) }
        levelName = sd.nm
        mods = sd.mods
        wind = sd.wind
        enemies = []; bubbles = []; items = []; shots = []
        espeed = spd * (1 + 0.025 * Double(tierN))
        for (k, c, r, angry) in sd.en {
            enemies.append(SHEnemy(k, Double(c * T - 2), Double(TOP + r * T + T - 13), espeed, angry: angry == 1))
        }
        if kind == "normal" && hype.lucky(0.03) {     // rare golden grump -> treasure chest
            let walkers = enemies.filter { "gbzp".contains($0.kind) }
            walkers.randomElement()?.golden = true
        }
        start = (Double(sd.p[0] * T), Double(TOP + sd.p[1] * T + T - 14))
        player = SHBody(start.0, start.1, 12, 14)
        face = 1; inv = 2; shootCd = 0; coyote = 0; jumpBuf = 0; airJumps = 0; bounces = 0
        shield = up("shield") > 0; shieldT = 0
        levelT = 0; hurry = false
        chain = 0; chainT = 0; bestChain = 0
        missed = false; snacksOut = 0; snacksGot = 0
        freezeT = 0
        boss = kind == "boss" ? SHBoss(sd) : nil
        letterT = -1
        if kind == "normal" && letters.contains(false) && hype.lucky(0.55) { letterT = Double.random(in: 5 ... 15) }
        bonusN = 0; bonusGot = 0; spawnT = 0
        timeLeft = Double(sd.time)
        renderField()
        reached(stage)
        if kind == "boss" {
            state = "warning"
            stageMusic = "boss"
            app.audio.play("warning")
        } else {
            state = "intro"
            stageMusic = kind == "bonus" ? "bonus" : (tierN >= 19 ? "soap_final" : "soap")
            app.audio.play("stage")
            if kind == "bonus" {
                hype.banner("BONUS STAGE!", sd.bt == "party" ? "POP EVERY BUBBLE!" : "CATCH THE SNACK RAIN!", dur: 2.0, rainbow: true)
            }
        }
        introState = state
        stateT = 0
        wasFever = false          // a FEVER still running picks its song again on the next tick
        app.audio.music(stageMusic)
    }

    func renderField() {
        field = Surface(W, FIELD_H)
        for r in 0 ..< map.count {
            for c in 0 ..< map[r].count {
                let x = c * T, y = r * T
                if map[r][c] == "#" {
                    field.fillRect(col(theme.blkD), x, y, T, T)
                    field.fillRect(col(theme.blk), x, y, T - 1, T - 1)
                    if (r + c) % 2 == 0 { field.fillRect(col("white"), x + 2, y + 2, 1, 1) }
                } else if map[r][c] == "=" {
                    field.fillRect(col(theme.platD), x, y + 1, T, T - 3)
                    field.fillRect(col(theme.plat), x, y, T, 3)
                    field.fillRect(col("white"), x + 1, y, 3, 1)
                }
            }
        }
    }

    func cell(_ px: Double, _ py: Double) -> Character {
        let c = Int(floor(px / Double(T))), r = Int(floor((py - Double(TOP)) / Double(T)))
        if r < 0 || r >= ROWS || r >= map.count { return "." }
        if c < 0 || c >= COLS { return "#" }
        return map[r][c]
    }

    // ------------------------------------------------------------------ upgrades
    func runSpeed() -> Double { RUN * (1 + 0.12 * Double(up("speed"))) }

    func jumpV() -> Double {
        let lv = up("jump")
        let v = JUMP * (lv >= 1 ? 1.06 : 1.0) * (lv >= 3 ? 1.05 : 1.0)
        return v * (mods.contains("floaty") ? 0.82 : 1.0)
    }

    func trapTime() -> Double { max(3.5, trapBase - 0.08 * Double(tierN)) + 1.5 * Double(up("trap")) }

    func took(_ uid: String?) {
        guard let uid = uid else {
            add(10000)
            hype.banner("ALL MAXED!", "+10000", color: "yellow", dur: 1.4)
            return
        }
        ups[uid, default: 0] += 1
        if uid == "heart" { lives += 1 }
        if uid == "shield" { shield = true }
        let name = SH_UPGRADES.first { $0.id == uid }?.name ?? uid
        hype.banner(name, "LEVEL \(up(uid))", color: "mint", dur: 1.1, scale: 1)
    }

    // ------------------------------------------------------------------ scene API used by the boss
    func shoot(_ kind: String, _ x: Double, _ y: Double, _ vx: Double, _ vy: Double) { shots.append(SHShot(kind, x, y, vx, vy)) }

    func minionCount() -> Int { enemies.filter { $0.minion }.count + bubbles.filter { $0.enemy != nil }.count }

    func spawnMinion(_ kind: String, _ x: Double, _ y: Double) {
        let e = SHEnemy(kind, x - 6, y - 6, espeed)
        e.minion = true
        enemies.append(e)
        parts.burst(x, y, 10, ["gray", "white"], 50, 0.4)
    }

    func bossDefeated() {
        guard let b = boss else { return }
        state = "bossdown"; stateT = 0
        hype.banners = []
        hype.slowmo(0.3, 1.6)
        hype.flash("white", 0.4)
        hype.banner("BOSS DOWN!!", "\(b.name) IS CLEAN!", dur: 2.6, rainbow: true, sound: "bossdown")
        app.shake(6, 0.8)
        add(10000 + 5000 * tierN, b.x, b.y - 24, "yellow")
        for s in shots { s.dead = true }
        for e in enemies {
            parts.burst(e.cx, e.cy, 10, ["white", "gray"], 60, 0.5)
            dropSnack(e.cx - 4, e.cy - 4)
        }
        enemies = []
        for bb in bubbles where bb.enemy != nil {
            bb.dead = true
            dropSnack(bb.x - 4, bb.y - 4)
        }
    }

    func bossBurst() {
        guard let b = boss else { return }
        hype.shower(70, "confetti")
        hype.shower(40, "coins")
        hype.flash("yellow", 0.3)
        app.audio.play("explode")
        app.shake(5, 0.5)
        parts.burst(b.x, b.y, 50, ["white", "yellow", "pink", "sky", "lavender"], 140, 1.1, size: 2)
        for i in 0 ..< 12 {
            let it = SHItem(b.x - 4, b.y - 4, "snack", (theme.snack + i) % 8, 300 + 50 * tierN)
            it.vx = cos(Double(i) * 2 * .pi / 12) * 90
            it.vy = -180 - Double(i % 3) * 40
            items.append(it)
            snacksOut += 1
        }
    }

    // ------------------------------------------------------------------ physics
    @discardableResult
    func move(_ b: SHBody, _ dt: Double, _ grav: Double = GRAV) -> Bool {
        if grav != 0 { b.vy = min(b.vy + grav * dt, 270) }
        var hitWall = false
        b.x += b.vx * dt
        for yy in [b.y + 1, b.y + Double(b.h) / 2, b.y + Double(b.h) - 1] {
            if b.vx > 0 && cell(b.x + Double(b.w), yy) == "#" {
                b.x = floor((b.x + Double(b.w)) / Double(T)) * Double(T) - Double(b.w) - 0.01; hitWall = true
            } else if b.vx < 0 && cell(b.x, yy) == "#" {
                b.x = (floor(b.x / Double(T)) + 1) * Double(T) + 0.01; hitWall = true
            }
        }
        let prevBottom = b.y + Double(b.h)
        b.y += b.vy * dt
        b.onGround = false
        let xs = [b.x + 1, b.x + Double(b.w) / 2, b.x + Double(b.w) - 1]
        if b.vy >= 0 {
            let bottom = b.y + Double(b.h)
            for xx in xs {
                let ch = cell(xx, bottom)
                let rowTop = Double(TOP) + floor((bottom - Double(TOP)) / Double(T)) * Double(T)
                if ch == "#" || (ch == "=" && prevBottom <= rowTop + 1) {
                    b.y = rowTop - Double(b.h); b.vy = 0; b.onGround = true; break
                }
            }
        } else {
            for xx in xs where cell(xx, b.y) == "#" {
                b.y = Double(TOP) + (floor((b.y - Double(TOP)) / Double(T)) + 1) * Double(T); b.vy = 0; break
            }
        }
        if b.y > Double(TOP + FIELD_H) { b.y -= Double(FIELD_H) } else if b.y + Double(b.h) < Double(TOP) { b.y += Double(FIELD_H) }
        return hitWall
    }

    // ------------------------------------------------------------------ update
    override func tick(_ dt: Double) {
        stateT += dt
        let au = app.audio
        if state == "picks" {
            if picks > 0 {
                picks -= 1
                pickUpgrade(SH_UPGRADES, ups, title: pickTitle) { [unowned self] id in self.took(id) }
            } else if afterPicks == "next" {
                nextStage()
            } else {
                state = introState; stateT = 0
            }
            return
        }
        if state == "tally" { updateTally(dt); return }
        if state == "won" { return }
        if state == "intro" && stateT > 1.9 {
            state = "play"; stateT = 0
        } else if state == "warning" && stateT > 2.8 {
            state = "play"; stateT = 0
            inv = max(inv, 1.0)
        }
        let st = state
        if ["intro", "warning", "play", "clear", "bossdown", "timeup"].contains(st) { updatePlayer(dt) }
        if st == "dead" && stateT > 1.3 {
            if lives <= 0 {
                state = "over"
                endGame(false, "STAGE \(stage)")
                return
            }
            player = SHBody(start.0, start.1, 12, 14)
            inv = 2.5
            state = "play"; stateT = 0
        }
        if st == "play" {
            levelT += dt
            if kind == "normal" && levelT > Double(sd.par) && !hurry {
                hurry = true
                hype.banner("HURRY UP!", "THE GRUMPS ARE FURIOUS", color: "red", dur: 1.3, sound: "warning")
                for e in enemies { e.angry = true }
            }
            if letterT >= 0 && letterT <= levelT {
                letterT = -1
                spawnLetter()
            }
        }
        if st != "intro" && st != "warning" { updateEnemies(dt) }
        updateBubbles(dt)
        updateItems(dt)
        updateShots(dt)
        boss?.update(self, dt)
        chainT -= dt
        freezeT -= dt
        if shieldT > 0 {
            shieldT -= dt
            if shieldT <= 0 && up("shield") >= 2 { shield = true; au.play("powerup") }
        }
        if kind == "bonus" { updateBonus(dt) }
        if st == "play" && kind == "normal" && enemies.isEmpty && !bubbles.contains(where: { $0.enemy != nil }) { stageClear() }
        if st == "bossdown" && stateT > 3.8 { state = "clear"; stateT = 0 }
        if st == "timeup" && stateT > 1.6 { startTally() }
        if st == "clear" && stateT > 2.6 { startTally() }
        checkExtra()
        let fever = hype.feverOn
        if fever != wasFever && kind == "normal" { au.music(fever ? "fever" : stageMusic) }
        wasFever = fever
    }

    func checkExtra() {
        while score >= nextExtra {
            lives += 1
            nextExtra = nextExtra < 150000 ? 150000 : nextExtra + 200000
            hype.banner("1UP!", "EXTRA LIFE", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    func stageClear() {
        state = "clear"; stateT = 0
        if chainT > 0 && chain >= 3 {
            hype.banner("CLEAN SWEEP!!", "+5000", dur: 1.8, rainbow: true, sound: "win")
            hype.shower(50, "confetti")
            add(5000)
        } else {
            hype.banner("SPARKLING CLEAN!", "STAGE CLEAR", color: "mint", dur: 1.6, sound: "levelup")
        }
    }

    func nextStage() {
        if stage >= STAGES {
            state = "won"
            hype.banner("ALL CLEAN!!", "200 STAGES SPARKLING", dur: 3.0, rainbow: true, sound: "win")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES CLEAN!", delay: 3.5)
            return
        }
        stage += 1
        loadStage()
    }

    func updatePlayer(_ dt: Double) {
        let inp = app.input, au = app.audio, p = player
        inv = max(0, inv - dt)
        shootCd -= dt
        let mv = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        let target = Double(mv) * runSpeed()
        if mods.contains("slick") { p.vx += (target - p.vx) * min(1, dt * 3.5) } else { p.vx = target }
        if mv != 0 { face = mv }
        if p.onGround {
            coyote = 0.09
            airJumps = up("jump") >= 2 ? 1 : 0
            bounces = 0
        } else {
            coyote -= dt
        }
        jumpBuf = inp.hit(.a) ? 0.12 : jumpBuf - dt
        if jumpBuf > 0 && coyote > 0 {
            p.vy = -jumpV()
            jumpBuf = 0; coyote = 0
            au.play("jump")
        } else if inp.hit(.a) && coyote <= 0 && airJumps > 0 {
            airJumps -= 1
            jumpBuf = 0
            p.vy = -jumpV() * (up("jump") < 3 ? 0.85 : 0.95)
            au.play("jump")
            parts.burst(p.cx, p.y + Double(p.h), 8, ["white", "sky"], 40, 0.3)
        }
        if p.vy < 0 && !inp.down(.a) { p.vy *= pow(0.85, dt * 60) }
        move(p, dt, GRAV * (mods.contains("floaty") ? 0.62 : 1.0))
        let mine = bubbles.filter { $0.kind == "normal" && $0.enemy == nil }.count
        if inp.hit(.b) && shootCd <= 0 && mine < 7 + 2 * up("rate") { blow() }
    }

    func blow() {
        let p = player
        shootCd = max(0.12, 0.28 - 0.055 * Double(up("rate")))
        let sp = 230 * (1 + 0.22 * Double(up("range")))
        bubbles.append(SHBubble(p.cx + Double(face * 6), p.cy - 1, Double(face) * sp, 0, 6.5))
        if up("twin") > 0 { bubbles.append(SHBubble(p.cx + Double(face * 4), p.cy - 4, Double(face) * sp * 0.7, -sp * 0.6, 6.5)) }
        app.audio.play("bubble")
    }

    func spawnLetter() {
        let left = (0 ..< 5).filter { !letters[$0] }
        guard let pick = left.randomElement() else { return }
        let b = SHBubble(Double.random(in: Double(T * 4) ... Double(W - T * 4)), Double(FLOOR_Y - 10), 0, 0, 16, "letter")
        b.age = FAST_PHASE
        b.sub = pick
        bubbles.append(b)
        app.audio.play("bonus")
    }

    // ------------------------------------------------------------------ enemies
    func updateEnemies(_ dt: Double) {
        let p = player
        for e in enemies {
            if !enemies.contains(where: { $0 === e }) { continue }
            let sp = e.base * (e.angry ? 1.6 : 1.0)
            if freezeT > 0 {
                if e.kind != "f" && e.kind != "w" { e.vx = 0; move(e, dt) }
                if state == "play" && e.rect().inflate(-2, -2).intersects(p.rect()) { defeatFrozen(e) }
                continue
            }
            if e.stun > 0 { e.stun -= dt; e.vx = 0; move(e, dt); continue }
            switch e.kind {
            case "g", "s": walker(e, dt, sp * (e.kind == "s" ? 0.8 : 1.0))
            case "b": boing(e, dt, sp)
            case "z": zoomy(e, dt, sp)
            case "p": sneezy(e, dt, sp)
            case "w":
                let d = max(1, hypot(p.cx - e.cx, p.cy - e.cy))
                e.x += (p.cx - e.cx) / d * 18 * sp * dt
                e.y += (p.cy - e.cy) / d * 18 * sp * dt + sin(t * 3 + e.think) * 10 * dt
                e.face = p.cx > e.cx ? 1 : -1
                e.x = max(Double(T * 2), min(Double(W - T * 2 - e.w), e.x))
                e.y = max(Double(TOP + 2), min(Double(FLOOR_Y - e.h), e.y))
            default:
                e.vx = Double(e.face) * 30 * sp
                e.vy = e.vdir * 22 * sp
                let nx = e.x + e.vx * dt, ny = e.y + e.vy * dt
                if cell(nx + (e.vx > 0 ? Double(e.w) : 0), e.cy) == "#" { e.face *= -1 } else { e.x = nx }
                if cell(e.cx, ny + (e.vy > 0 ? Double(e.h) : 0)) == "#" || ny < Double(TOP + 2) || ny + Double(e.h) > Double(TOP + FIELD_H - 2) {
                    e.vdir *= -1
                } else { e.y = ny }
            }
            if state == "play" && inv <= 0 && e.rect().inflate(-3, -3).intersects(p.rect()) { hurt() }
        }
    }

    func walker(_ e: SHEnemy, _ dt: Double, _ sp: Double) {
        let p = player
        e.vx = Double(e.face) * 32 * sp
        if move(e, dt) { e.face *= -1 }
        if e.onGround {
            let ahead = cell(e.cx + Double(e.face * 8), e.y + Double(e.h) + 2)
            e.think -= dt
            if ahead == "." && Double.random(in: 0 ..< 1) < 0.5 * dt * 10 { e.face *= -1 }
            if e.think <= 0 {
                e.think = Double.random(in: 0.8 ... 2.0)
                if p.y + Double(p.h) < e.y - 4 && Double.random(in: 0 ..< 1) < 0.55 { e.vy = -JUMP * 0.95 }
                else if Double.random(in: 0 ..< 1) < 0.25 { e.face = p.cx > e.cx ? 1 : -1 }
            }
        }
    }

    func boing(_ e: SHEnemy, _ dt: Double, _ sp: Double) {
        e.vx = Double(e.face) * (e.onGround ? 10 : 30) * sp
        if move(e, dt) { e.face *= -1 }
        if e.onGround {
            if e.mode != "land" { e.mode = "land"; e.modeT = Double.random(in: 0.15 ... 0.45) }
            e.modeT -= dt
            if e.modeT <= 0 {
                e.mode = "air"
                e.vy = -JUMP * Double.random(in: 0.75 ... 1.0)
                if Bool.random() { e.face = player.cx > e.cx ? 1 : -1 }
            }
        }
    }

    func zoomy(_ e: SHEnemy, _ dt: Double, _ sp: Double) {
        let p = player
        e.cool -= dt
        if e.mode == "rev" {
            e.vx = 0
            move(e, dt)
            e.modeT -= dt
            if Int(e.modeT * 20) % 3 == 0 { parts.sparkle(e.cx - Double(e.face * 6), e.y + Double(e.h), "white") }
            if e.modeT <= 0 { e.mode = "dash"; e.modeT = 0.9; app.audio.play("shoot") }
            return
        }
        if e.mode == "dash" {
            e.vx = Double(e.face) * 130 * sp
            let hit = move(e, dt)
            e.modeT -= dt
            if hit || e.modeT <= 0 {
                e.mode = "walk"; e.cool = 1.4
                if hit { e.face *= -1 }
            }
            return
        }
        walker(e, dt, sp * 1.1)
        if e.onGround && e.cool <= 0 && abs(p.cy - e.cy) < 10 && abs(p.cx - e.cx) < 150
            && (p.cx > e.cx ? 1 : -1) == e.face && state == "play" {
            e.mode = "rev"; e.modeT = 0.45
        }
    }

    func sneezy(_ e: SHEnemy, _ dt: Double, _ sp: Double) {
        let p = player
        if e.mode == "inhale" {
            e.vx = 0
            move(e, dt)
            e.modeT -= dt
            e.swell = min(1, e.swell + dt * 1.4)
            if e.modeT <= 0 {
                e.mode = "walk"; e.swell = 0
                e.cool = Double.random(in: 2.4 ... 4.0) / sp
                shoot("dust", e.cx + Double(e.face * 8), e.cy, Double(e.face) * 80 * (e.angry ? 1.25 : 1.0), 0)
                app.audio.play("shoot")
                parts.burst(e.cx + Double(e.face * 8), e.cy, 6, ["gray", "white"], 40, 0.3)
            }
            return
        }
        e.cool -= dt
        walker(e, dt, sp * 0.65)
        if e.onGround && e.cool <= 0 && state == "play" {
            e.mode = "inhale"; e.modeT = 0.8
            e.face = p.cx > e.cx ? 1 : -1
        }
    }

    func defeatFrozen(_ e: SHEnemy) {
        enemies.removeAll { $0 === e }
        add(500, e.cx, e.y - 6, "sky")
        hype.hit(1, fever: 0.05)
        app.audio.play("pop")
        parts.burst(e.cx, e.cy, 12, ["sky", "white"], 60, 0.5)
        drop(e.cx - 4, e.cy - 4, e)
    }

    func hurt() {
        if inv > 0 || state != "play" { return }
        if shield {
            shield = false
            shieldT = 20
            inv = 1.5
            app.audio.play("pop")
            app.shake(2, 0.2)
            parts.burst(player.cx, player.cy, 16, ["mint", "white"], 70, 0.5)
            floats.add(player.cx, player.y - 6, "SHIELD!", "mint")
            return
        }
        lives -= 1
        missed = true
        hype.breakCombo()
        state = "dead"; stateT = 0
        app.audio.play("hurt")
        app.shake(3, 0.3)
        hype.flash("red", 0.15)
        parts.burst(player.cx, player.cy, 20, ["white", "pink", "hotpink"], 80, 0.8)
    }

    // ------------------------------------------------------------------ bubbles
    func updateBubbles(_ dt: Double) {
        let p = player, au = app.audio
        let catchR = Double(11 + 2 * up("trap"))
        let damp = pow(0.92, dt * 60)
        for b in bubbles where !b.dead {
            b.age += dt; b.life -= dt
            if let pi = b.popIn {
                b.popIn = pi - dt
                if b.popIn! <= 0 { pop(b) }
                continue
            }
            if b.age < FAST_PHASE {
                b.x += b.vx * dt
                b.y += b.vy * dt
                b.vx *= damp
                b.vy *= damp
                if cell(b.x + (b.vx > 0 ? 7 : -7), b.y) == "#" || (b.vy < 0 && cell(b.x, b.y - 7) == "#") { b.age = FAST_PHASE }
                if b.enemy == nil && b.kind == "normal" { bubbleHits(b, catchR) }
            } else {
                let rise = b.enemy != nil ? 18.0 : (b.kind == "party" ? 34.0 : (b.kind == "letter" ? 14.0 : 22.0))
                b.y -= rise * dt
                b.x += sin(t * 2 + b.seed) * 8 * dt + Double(wind) * 16 * dt
                if b.kind != "party" && cell(b.x, b.y - 8) == "#" { b.y += rise * dt }
                if b.y < Double(TOP - 8) { b.y += Double(FIELD_H) }
                b.x = max(Double(T * 2 + 8), min(Double(W - T * 2 - 8), b.x))
                if b.kind == "party" && b.y < Double(TOP + 10) {
                    b.dead = true
                    parts.burst(b.x, b.y, 4, ["white", "sky"], 30, 0.3)
                    continue
                }
                if let bs = boss, b.kind == "normal", bs.hits(b.x, b.y, 8) {
                    b.dead = true
                    parts.burst(b.x, b.y, 6, ["white", "sky"], 40, 0.3)
                    bs.hurt(self, b.enemy != nil ? 4 : 1, b.enemy != nil ? "SPLASH!" : nil)
                    continue
                }
                if state != "dead" && state != "tally" && hypot(p.cx - b.x, p.cy - b.y) < 12 {
                    if b.kind == "letter" {
                        collectLetter(b)
                    } else if p.vy > 0 && p.y + Double(p.h) < b.y && app.input.down(.a) {
                        p.vy = -JUMP * 0.95
                        airJumps = up("jump") >= 2 ? 1 : 0
                        au.play("jump")
                        if b.kind == "party" { bounces += 1; pop(b) }
                    } else {
                        pop(b)
                    }
                }
            }
            if b.life <= 0 && !b.dead {
                if let e = b.enemy {
                    e.x = b.x - Double(e.w) / 2; e.y = b.y - Double(e.h) / 2; e.angry = true
                    enemies.append(e); b.enemy = nil
                }
                pop(b, quiet: true)
            }
        }
        let alive = bubbles.filter { !$0.dead && $0.age > FAST_PHASE }
        for (i, a) in alive.enumerated() {
            for b2 in alive[(i + 1)...] {
                let dx = b2.x - a.x, dy = b2.y - a.y, d = hypot(dx, dy)
                if d > 0 && d < 13 {
                    let push = (13 - d) * 0.5
                    a.x -= dx / d * push; a.y -= dy / d * push; b2.x += dx / d * push; b2.y += dy / d * push
                }
            }
        }
        bubbles.removeAll { $0.dead }
    }

    /// A freshly blown bubble: trap an enemy, knock off a lid, cancel dust, hit the boss or a party bubble.
    func bubbleHits(_ b: SHBubble, _ catchR: Double) {
        let au = app.audio
        if let idx = enemies.firstIndex(where: { abs($0.cx - b.x) < catchR && abs($0.cy - b.y) < catchR }) {
            let e = enemies[idx]
            if e.lid {
                e.lid = false; e.stun = 0.7; e.angry = true
                b.dead = true
                add(30, e.cx, e.y - 6, "white")
                au.play("tin")
                parts.burst(e.cx, e.y, 10, ["gray", "white"], 70, 0.4)
                return
            }
            b.enemy = e
            b.life = trapTime()
            enemies.remove(at: idx)
            add(50)
            au.play("trap")
            return
        }
        for s in shots where s.r > 0 && !s.dead && hypot(s.x - b.x, s.y - b.y) < s.r + 7 {
            s.dead = true
            b.dead = true
            add(30, s.x, s.y - 6, "white")
            parts.burst(s.x, s.y, 6, ["gray", "white"], 40, 0.3)
            au.play("pop")
            return
        }
        if let bs = boss {
            if bs.hits(b.x, b.y, 7) {
                b.dead = true
                parts.burst(b.x, b.y, 6, ["white", "sky"], 50, 0.3)
                bs.hurt(self, 1)
                return
            }
            if bs.touches(b.x, b.y, 7) {
                b.dead = true
                au.play("tin")
                parts.burst(b.x, b.y, 4, ["white"], 30, 0.2)
                return
            }
        }
        for o in bubbles where o.kind == "party" && !o.dead && hypot(o.x - b.x, o.y - b.y) < 14 {
            b.dead = true
            pop(o)
            return
        }
    }

    func pop(_ b: SHBubble, quiet: Bool = false) {
        if b.dead { return }
        b.dead = true
        let au = app.audio
        parts.burst(b.x, b.y, 8, ["white", "sky", "lavender"], 50, 0.4)
        if let e = b.enemy {
            chain = chainT > 0 ? chain + 1 : 1
            chainT = 0.5
            bestChain = max(bestChain, chain)
            let pts = Int(Double(min(8000, 500 * (1 << min(chain - 1, 10)))) * (1 + 0.5 * Double(up("chain"))))
            add(pts, b.x, b.y - 10 - Double(7 * min(4, chain - 1)), chain < 2 ? "yellow" : "mint")
            hype.hit(1, fever: 0.06)
            drop(b.x - 4, b.y - 4, e)
            au.play("pop")
            app.shake(1.5, 0.12)
            if let bs = boss, hypot(b.x - bs.x, b.y - bs.y) < 56 { bs.hurt(self, 4, "SPLASH!") }
            let reach = Double(24 + 10 * up("chain"))
            for o in bubbles where o.enemy != nil && o.popIn == nil && !o.dead && hypot(o.x - b.x, o.y - b.y) < reach { o.popIn = 0.09 }
            chainHype()
        } else if b.kind == "party" {
            let mult = max(1, min(5, bounces))
            add(b.value * mult, b.x, b.y - 10, b.value < 1000 ? "yellow" : "orange")
            bonusGot += 1
            hype.hit(1, fever: 0.03)
            au.play(b.value >= 1000 ? "coin" : "pop")
            if mult > 1 { floats.add(b.x, b.y - 20, "BOUNCE X\(mult)", "lime") }
        } else if b.kind == "letter" {
        } else if !quiet {
            add(10); au.play("pop")
        }
    }

    func chainHype() {
        let n = chain
        if n < 3 { return }
        hype.banners.removeAll { $0.text.hasSuffix("CHAIN!") }
        if n == 5 {
            hype.banner("SUPER CHAIN!", "+5000", dur: 1.4, rainbow: true, sound: "combo")
            hype.slowmo(0.4, 0.6)
            hype.flash("white", 0.15)
            hype.shower(40, "stars")
            add(5000)
        } else if n == 8 {
            hype.jackpot(10000, sub: "MEGA SUDS! +10000")
        } else if n < 5 {
            hype.banner("\(n) CHAIN!", color: "peach", dur: 0.9, scale: 1, sound: "combo")
        } else if n > 8 {
            hype.banner("\(n) CHAIN!", color: "hotpink", dur: 0.9, scale: 2)
        }
    }

    func collectLetter(_ b: SHBubble) {
        b.dead = true
        letters[b.sub] = true
        app.audio.play("coin")
        add(500, b.x, b.y - 10, "yellow")
        parts.burst(b.x, b.y, 14, ["yellow", "white", "orange"], 60, 0.5)
        if !letters.contains(false) {
            letters = [false, false, false, false, false]
            lives += 1
            hype.banner("M-O-C-H-I!", "EXTRA LIFE +10000", dur: 2.2, rainbow: true, sound: "extra")
            hype.shower(40, "hearts")
            hype.shower(40, "confetti")
            hype.flash("pink", 0.25)
            add(10000)
        } else {
            hype.banner(LETTERS[b.sub], "LETTER BUBBLE!", color: "yellow", dur: 0.9)
        }
    }

    // ------------------------------------------------------------------ items
    func dropSnack(_ x: Double, _ y: Double) {
        let k = Double.random(in: 0 ..< 1) < 0.75 ? theme.snack : Int.random(in: 0 ..< 8)
        items.append(SHItem(x, y, "snack", k, 100 * (k + 1) + 20 * tierN))
        snacksOut += 1
    }

    func drop(_ x: Double, _ y: Double, _ e: SHEnemy) {
        if e.golden {
            items.append(SHItem(x, y, "chest"))
            app.audio.play("bonus")
            return
        }
        dropSnack(x, y)
        if kind != "normal" || items.contains(where: { POWERS.contains($0.kind) || $0.kind == "heart" || $0.kind == "cake" }) { return }
        let roll = Double.random(in: 0 ..< 1)
        if roll < 0.012 && lives < 9 {
            items.append(SHItem(x, y, "heart"))
        } else if roll < 0.03 {
            items.append(SHItem(x, y, "cake"))
        } else if roll < 0.075 {
            items.append(SHItem(x, y, POWERS.randomElement()!))
        }
    }

    func updateItems(_ dt: Double) {
        let p = player
        let mag = [0.0, 40, 64, 96][min(3, up("magnet"))]
        for f in items {
            f.life -= dt
            let d = hypot(p.cx - f.cx, p.cy - f.cy)
            if mag > 0 && d < mag && state != "dead" && state != "tally" && f.life < 8.6 {
                f.x += (p.cx - f.cx) / max(1, d) * 150 * dt
                f.y += (p.cy - f.cy) / max(1, d) * 150 * dt
                f.vy = 0
                if Int(t * 20) % 4 == 0 { parts.sparkle(f.cx, f.cy, "red") }
            } else if f.rain && !f.onGround {
                f.vx = 0
                f.vy = min(f.vy + 200 * dt, 70)
                move(f, dt, 0)
            } else {
                f.vx *= pow(0.98, dt * 60)
                move(f, dt)
                if f.onGround { f.vx = 0 }
            }
            if state != "dead" && state != "tally" && f.rect().intersects(p.rect()) {
                f.life = -1
                collect(f)
            }
        }
        items.removeAll { $0.life <= 0 }
    }

    func collect(_ f: SHItem) {
        let au = app.audio, h: Hype = hype
        parts.burst(f.cx, f.cy, 6, ["yellow", "white"], 40, 0.4)
        switch f.kind {
        case "snack":
            add(f.value, f.cx, f.y - 6, "peach")
            h.hit(1, fever: 0.02)
            au.play("fruit")
            snacksGot += 1
            if kind == "bonus" { bonusGot += 1 }
        case "chest":
            h.jackpot(5000 + 1000 * tierN, sub: "TREASURE CHEST!")
        case "cake":
            add(kind != "bonus" ? 3000 : f.value, f.cx, f.y - 8, "orange")
            h.banner("SUPER SNACK!", color: "orange", dur: 1.0, sound: "bonus")
            h.shower(24, "coins")
            if kind == "bonus" { bonusGot += 1 }
        case "gem":
            add(2000, f.cx, f.y - 8, "sky")
            au.play("coin")
        case "heart":
            lives += 1
            h.banner("1UP!", color: "pink", dur: 1.0, sound: "extra")
        case "shield":
            shield = true
            h.banner("BUBBLE SHIELD!", color: "mint", dur: 1.0, scale: 1, sound: "powerup")
        case "clock":
            freezeT = 5
            h.banner("FREEZE!", "TOUCH THEM TO POP!", color: "sky", dur: 1.2, sound: "powerup")
            h.flash("sky", 0.2)
        default:
            h.banner("FIZZ BURST!", color: "hotpink", dur: 1.0, sound: "powerup")
            let p = player
            for i in 0 ..< 10 {
                let a = Double(i) * 2 * .pi / 10
                bubbles.append(SHBubble(p.cx, p.cy, cos(a) * 200, sin(a) * 200, 6.5))
            }
        }
    }

    // ------------------------------------------------------------------ shots
    func updateShots(_ dt: Double) {
        let p = player
        for s in shots where !s.dead {
            s.age += dt
            if s.kind == "bolt" || s.kind == "mark" {
                if s.age >= s.warn {
                    if s.kind == "mark" {
                        s.dead = true
                        shoot("drop", s.x, Double(TOP + 10), 0, 40)
                    } else if s.age < s.warn + 0.3 {
                        if s.age - dt < s.warn { app.audio.play("explode"); app.shake(2, 0.2) }
                        if state == "play" && abs(p.cx - s.x) < 7 { hurt() }
                    } else {
                        s.dead = true
                    }
                }
                continue
            }
            s.vy += s.grav * dt
            s.x += s.vx * dt
            s.y += s.vy * dt
            if s.kind == "wave" {
                if s.x < Double(T * 2) || s.x > Double(W - T * 2) {
                    s.dead = true
                } else if state == "play" && abs(p.cx - s.x) < 6 && p.y + Double(p.h) > Double(FLOOR_Y - 9) {
                    hurt()
                }
                continue
            }
            if s.age > 6 || cell(s.x, s.y) == "#" || s.x < Double(T * 2) || s.x > Double(W - T * 2)
                || (s.grav > 0 && cell(s.x, s.y + s.r) == "=" && s.vy > 0) {
                s.dead = true
                parts.burst(s.x, s.y, 5, ["gray", "white"], 30, 0.3)
                continue
            }
            if state == "play" && hypot(p.cx - s.x, p.cy - s.y) < s.r + 5 {
                s.dead = true
                hurt()
            }
        }
        shots.removeAll { $0.dead }
    }

    // ------------------------------------------------------------------ bonus stages
    func updateBonus(_ dt: Double) {
        if state != "play" { return }
        timeLeft -= dt
        spawnT -= dt
        if spawnT <= 0 {
            if sd.bt == "party" {
                spawnT = 0.3
                let b = SHBubble(Double.random(in: Double(T * 3 + 8) ... Double(W - T * 3 - 8)), Double(FLOOR_Y + 4), 0, 0, 30, "party")
                b.age = FAST_PHASE
                let gold = Double.random(in: 0 ..< 1) < 0.06
                b.sub = Int.random(in: 0 ..< 8)
                b.value = gold ? 1000 : 200 + 20 * tierN
                bubbles.append(b)
            } else {
                spawnT = 0.22
                let cake = Double.random(in: 0 ..< 1) < 0.04
                let it = SHItem(Double.random(in: Double(T * 3) ... Double(W - T * 4)), Double(TOP + 6), cake ? "cake" : "snack",
                                Int.random(in: 0 ..< 8), cake ? 2000 : 200 + 20 * tierN)
                it.vx = 0; it.vy = 10; it.rain = true; it.life = 6
                items.append(it)
            }
            bonusN += 1
        }
        if timeLeft <= 0 {
            timeLeft = 0
            state = "timeup"; stateT = 0
            hype.banner("TIME UP!", color: "yellow", dur: 1.4, sound: "levelup")
            for b in bubbles where b.kind == "party" {
                b.dead = true
                parts.burst(b.x, b.y, 4, ["white", "sky"], 30, 0.3)
            }
            for it in items where it.rain { it.life = 0 }
        }
    }

    // ------------------------------------------------------------------ tally
    func startTally() {
        var rows: [(String, Int)] = []
        let tr = tierN
        if kind == "normal" {
            rows.append(("STAGE CLEAR", 1000 + 200 * tr))
            let tb = max(0, Int((Double(sd.par) - levelT) * 50))
            if tb > 0 { rows.append(("TIME BONUS", tb)) }
            if !missed { rows.append(("NO MISS", 3000)) }
            if snacksOut > 0 && snacksGot >= snacksOut { rows.append(("ALL SNACKS", 2000)) }
            if bestChain >= 2 { rows.append(("BEST CHAIN X\(bestChain)", 400 * bestChain)) }
        } else if kind == "boss" {
            rows.append(("BOSS CLEAR", 5000 + 1000 * tr))
            let tb = max(0, Int((90 - levelT) * 100))
            if tb > 0 { rows.append(("SPEED BONUS", tb)) }
            if !missed { rows.append(("NO MISS", 10000)) }
        } else {
            let word = sd.bt == "party" ? "POPPED" : "CAUGHT"
            rows.append(("\(word) \(bonusGot)/\(bonusN)", 50 * bonusGot))
            if Double(bonusGot) >= Double(bonusN) * 0.85 {
                rows.append(("PERFECT!!", 10000))
                hype.banner("PERFECT!!", dur: 1.8, rainbow: true, sound: "win")
                hype.shower(60, "coins")
            } else if Double(bonusGot) >= Double(bonusN) * 0.55 {
                rows.append(("GREAT!", 3000))
            }
        }
        tally = rows.map { ($0.0, $0.1, 0.0) }
        tallyI = 0; tallyT = 0; tallyTotal = 0
        state = "tally"; stateT = 0
    }

    func updateTally(_ dt: Double) {
        tallyT += dt
        let inp = app.input
        if tallyI < tally.count {
            var row = tally[tallyI]
            row.2 = min(Double(row.1), row.2 + Double(max(row.1, 300)) * dt * 2.4)
            tally[tallyI] = row
            if Int(tallyT * 14) != Int((tallyT - dt) * 14) && row.2 < Double(row.1) { app.audio.play("move") }
            let skip = stateT > 0.3 && inp.hit(.a, .b)
            if row.2 >= Double(row.1) || skip {
                let upto = skip ? tally.count : tallyI + 1
                for i in tallyI ..< upto {
                    tally[i].2 = Double(tally[i].1)
                    tallyTotal += add(tally[i].1)
                }
                tallyI = upto
                tallyT = 0
                app.audio.play("coin")
                checkExtra()
            }
            return
        }
        if tallyT > 1.5 || (tallyT > 0.3 && inp.hit(.a, .b)) {
            if kind == "boss" || kind == "bonus" {
                picks = 1; afterPicks = "next"; pickTitle = "POWER UP!"
                state = "picks"; stateT = 0
            } else {
                nextStage()
            }
        }
    }

    // ------------------------------------------------------------------ draw
    override func render(_ s: Surface) {
        var y = 0
        while y < H { s.fillRect(lerpCol(theme.skyA, theme.skyB, Double(y) / Double(H)), 0, y, W, 4); y += 4 }
        backdrop(s)
        s.blit(field, 0, TOP)
        for sh in shots { drawShot(s, sh) }
        for f in items where f.life > 2 || Int(f.life * 10) % 2 == 1 { SHArt.item(s, f.kind, f.sub, Int(f.x), Int(f.y), t) }
        for e in enemies {
            SHArt.critter(s, e.kind, Int(e.x) - 2, Int(e.y) - 2, t, flip: e.face < 0, angry: e.angry, trapped: false, e)
            if freezeT > 0 { bubble(s, e.cx, e.cy, 9, t, tint: "sky") }
        }
        boss?.draw(s, t)
        for b in bubbles {
            if let e = b.enemy {
                SHArt.critter(s, e.kind, Int(b.x) - 8, Int(b.y) - 8, t, flip: false, angry: b.life < 2, trapped: true, e)
                let tint = b.life < 2 && Int(b.life * 8) % 2 == 1 ? "red" : (e.golden ? "yellow" : "lavender")
                bubble(s, b.x, b.y, 10 + up("trap"), t, tint: tint)
            } else if b.kind == "letter" {
                SHArt.letterBubble(s, b.x, b.y, LETTERS[b.sub], t)
            } else if b.kind == "party" {
                if b.value >= 1000 {
                    bubble(s, b.x, b.y, 9, t, tint: "yellow")
                    s.blit(sprite("star"), Int(b.x) - 3, Int(b.y) - 3)
                } else {
                    Cute.fruit(s, b.sub, Int(b.x) - 4, Int(b.y) - 4)
                    bubble(s, b.x, b.y, 8, t, tint: "sky")
                }
            } else {
                bubble(s, b.x, b.y, b.age < FAST_PHASE ? 7 : 8, t)
            }
        }
        let p = player
        if state != "dead" && state != "over" && (inv <= 0 || Int(inv * 12) % 2 == 0) {
            let img: Surface
            if !p.onGround { img = sprite("momo_jump", 0, flip: face < 0) }
            else if abs(p.vx) > 1 { img = sprite("momo_walk", Int(t * 10), flip: face < 0) }
            else { img = sprite("momo_idle", Int(t * 2), flip: face < 0) }
            s.blit(img, Int(p.x) - 2, Int(p.y) - 1)
            if shield { bubble(s, p.cx, p.cy, 11, t, tint: "mint") }
        }
        parts.draw(s)
        floats.draw(s)
        if mods.contains("dark") && state != "intro" && state != "tally" { darkness(s) }
        hud(s)
        overlays(s)
    }

    func backdrop(_ s: Surface) {
        let shade = lerpCol(theme.skyA, "black", 0.35)
        switch theme.style {
        case "bubbles":
            for i in 0 ..< 12 {
                let x = (Double(i * 53) + t * Double(4 + i % 3)).truncatingRemainder(dividingBy: Double(W))
                s.circle(shade, Int(x), TOP + (i * 37) % FIELD_H, 2 + i % 3)
            }
        case "tiles":
            var x = 0
            while x < W { s.fillRect(shade, x, TOP, 1, FIELD_H); x += 16 }
            var y = TOP
            while y < H { s.fillRect(shade, 0, y, W, 1); y += 16 }
        case "dots":
            for i in 0 ..< 40 { s.fillRect(shade, (i * 41) % W, TOP + (i * 23 + Int(t * 3)) % FIELD_H, 2, 2) }
        case "rain":
            for i in 0 ..< 24 { s.fillRect(shade, (i * 29 + Int(t * 6)) % W, TOP + (i * 47 + Int(t * 60)) % FIELD_H, 1, 5) }
        case "stripes":
            for i in -12 ..< 24 {
                let x0 = i * 16 + Int(t * 4) % 16
                s.line(shade, x0, H, x0 + 60, TOP, width: 3)
            }
        default:
            for i in 0 ..< 30 {
                let lit = Int(t * 2 + Double(i)) % 5 == 0
                s.fillRect(lit ? col("lavender") : shade, (i * 67) % W, TOP + (i * 31) % FIELD_H, 1, 1)
            }
        }
        if wind != 0 {
            for i in 0 ..< 8 {
                s.fillRect(shade, pmod(i * 47 + Int(t * 50 * Double(wind)), W), TOP + 10 + (i * 23) % (FIELD_H - 30), 6, 1)
            }
        }
    }

    func darkness(_ s: Surface) {
        let R = 64
        let c = rgba(12, 8, 24, 200)
        let cx = Int(player.cx), cy = Int(player.cy)
        for y in TOP ..< H {
            let dy = y - cy
            if abs(dy) < R {
                let half = Int(Double(R * R - dy * dy).squareRoot())
                s.fillRect(c, 0, y, max(0, cx - half), 1)
                s.fillRect(c, cx + half, y, W - (cx + half), 1)
            } else {
                s.fillRect(c, 0, y, W, 1)
            }
        }
    }

    func drawShot(_ s: Surface, _ sh: SHShot) {
        let x = Int(sh.x), y = Int(sh.y)
        switch sh.kind {
        case "dust":
            s.circle(col("darkgray"), x, y, 3)
            s.circle(col("gray"), x - 1, y - 1, 1)
        case "drop":
            s.circle(col("black"), x, y, 3)
            s.fillRect(col("darkgray"), x - 1, y - 6, 2, 4)
        case "water":
            s.circle(col("sky"), x, y, 2)
            s.fillRect(col("white"), x - 1, y - 1, 1, 1)
        case "wave":
            for i in 0 ..< 3 {
                let h = 8 - i * 2
                s.fillRect(col(["white", "sky", "blue"][i]), x - 3 + i * (sh.vx > 0 ? -2 : 2), FLOOR_Y - h, 3, h)
            }
        case "mark":
            if Int(sh.age * 12) % 2 == 0 {
                s.ellipse(col("black"), x - 6, FLOOR_Y - 3, 12, 4)
                drawText(s, "!", x, FLOOR_Y - 14, "red", align: .center, shadow: nil)
            }
        default:  // bolt
            if sh.age < sh.warn {
                if Int(sh.age * 16) % 2 == 0 {
                    var yy = TOP + 8
                    while yy < FLOOR_Y { s.fillRect(col("yellow"), x, yy, 1, 3); yy += 6 }
                }
            } else {
                s.fillRect(col("yellow"), x - 4, TOP + 8, 9, FLOOR_Y - TOP - 8)
                s.fillRect(col("white"), x - 1, TOP + 8, 3, FLOOR_Y - TOP - 8)
            }
        }
    }

    func hud(_ s: Surface) {
        s.fillRect(col("black"), 0, 0, W, TOP)
        drawText(s, String(format: "%07d", score), 4, 3, "white", shadow: nil)
        hearts(s, 48, 3, lives, maxShow: 5)
        drawText(s, String(format: "HI %07d", max(best, score)), 150, 3, "lavender", align: .center, shadow: nil)
        for (i, ch) in LETTERS.enumerated() { drawText(s, ch, 190 + i * 7, 3, letters[i] ? "yellow" : "darkgray", shadow: nil) }
        drawText(s, "STAGE \(stage)", W - 4, 3, "yellow", align: .right, shadow: nil)
        if hype.feverOn {
            s.fillRect(col(rainbow(0, t)), 0, TOP - 1, Int(Double(W) * hype.feverT / Hype.feverTime), 1)
        } else {
            s.fillRect(col("hotpink"), 0, TOP - 1, Int(Double(W) * hype.fever), 1)
        }
        if let b = boss, !b.dead, state != "warning" && state != "tally" {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: FLOOR_Y + 4)
        }
        if kind == "bonus" && (state == "play" || state == "intro") {
            let frac = timeLeft / Double(sd.time)
            panel(s, IRect(60, FLOOR_Y + 4, 200, 12), fill: "black", border: "yellow", radius: 3, shadow: false)
            drawText(s, String(format: "TIME %2d", Int(ceil(timeLeft))), 64, FLOOR_Y + 7, "white", shadow: nil)
            s.fillRect(col("darkgray"), 112, FLOOR_Y + 8, 140, 4)
            s.fillRect(col(frac > 0.25 || Int(t * 8) % 2 == 1 ? "yellow" : "red"), 112, FLOOR_Y + 8, Int(140 * frac), 4)
        }
    }

    func overlays(_ s: Surface) {
        if state == "intro" && kind == "normal" { stageCard(s) }
        else if state == "warning" { warningCard(s) }
        else if state == "tally" { tallyCard(s) }
        else if hurry && state == "play" && levelT < Double(sd.par) + 2.5 && Int(t * 6) % 2 == 1 {
            drawText(s, "HURRY!", W / 2, 100, "red", scale: 2, align: .center, outline: "black")
        }
    }

    func stageCard(_ s: Surface) {
        let k = min(1, stateT * 5)
        let y = Int(54 - (1 - k) * 80)
        let lines = mods.map { SHData.mods[$0] ?? $0.uppercased() }
        let new = sd.new
        let hh = 56 + 10 * lines.count + (new.isEmpty ? 0 : 20)
        panel(s, IRect(56, y, 208, hh), fill: "ink", border: theme.blk)
        drawText(s, "STAGE \(stage)", W / 2, y + 7, "yellow", scale: 2, align: .center, outline: "black")
        drawText(s, theme.name, W / 2, y + 26, theme.blk, align: .center, shadow: nil)
        drawText(s, "\"\(levelName)\"", W / 2, y + 37, "white", align: .center, shadow: nil)
        var yy = y + 49
        for ln in lines {
            drawText(s, "* " + ln + " *", W / 2, yy, "lime", align: .center, shadow: nil)
            yy += 10
        }
        if !new.isEmpty, let info = SHData.enemies[new] {
            SHArt.critter(s, new, 70, yy - 1, t)
            drawText(s, "NEW! \(info.0)", 92, yy, "hotpink", shadow: nil)
            drawText(s, info.3, 92, yy + 9, "white", shadow: nil)
        }
    }

    func warningCard(_ s: Surface) {
        let tt = stateT
        for bandY in [46, 132] {
            s.fillRect(col("black"), 0, bandY, W, 12)
            let off = Int(tt * 40) % 16
            var x = -16
            while x < W + 16 {
                s.polygon(col("red"), [(Double(x + off), Double(bandY)), (Double(x + off + 8), Double(bandY)),
                                       (Double(x + off + 2), Double(bandY + 12)), (Double(x + off - 6), Double(bandY + 12))])
                x += 16
            }
        }
        if Int(tt * 4) % 2 == 0 { drawText(s, "WARNING", W / 2, 66, "red", scale: 3, align: .center, outline: "black") }
        drawText(s, "A HUGE DUST BOSS APPROACHES", W / 2, 96, "white", align: .center, outline: "black")
        drawText(s, boss?.name ?? "", W / 2, 110, "yellow", scale: 2, align: .center, outline: "black")
    }

    func tallyCard(_ s: Surface) {
        let n = tally.count
        let hh = 46 + n * 11
        let y0 = 100 - hh / 2
        panel(s, IRect(64, y0, 192, hh), fill: "ink", border: "mint")
        let title = ["normal": "STAGE CLEAR!", "boss": "BOSS DEFEATED!", "bonus": "BONUS RESULT"][kind] ?? ""
        drawText(s, title, W / 2, y0 + 7, "mint", scale: 2, align: .center, outline: "black")
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let yy = y0 + 28 + i * 11
            drawText(s, row.0, 74, yy, "white", shadow: nil)
            drawText(s, "\(Int(row.2))", 246, yy, "yellow", align: .right, shadow: nil)
        }
        if tallyI >= n { drawText(s, "TOTAL \(tallyTotal)", W / 2, y0 + hh - 13, rainbow(0, t), align: .center, shadow: nil) }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("deep"))
        let w = s.w, h = s.h
        var x = 0
        while x < w { s.fillRect(col("pink"), x, h - 8, 7, 7); x += 8 }
        s.fillRect(col("cream"), 10, h - 30, 40, 3)
        s.blit(sprite("momo_walk", Int(t * 8)), 16 + Int(sin(t) * 10), h - 24)
        let rise = (t * 6).truncatingRemainder(dividingBy: 10)
        bubble(s, Double(w - 30) + sin(t * 2) * 3, Double(h - 36) - rise, 9, t)
        Cute.grump(s, w - 38, h - 44 - Int(rise), t, trapped: true)
        Cute.grump(s, w - 26, h - 24, t, flip: true)
    }
}
