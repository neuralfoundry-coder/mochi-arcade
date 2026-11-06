// PAW PINBALL - flip, bump and purr! (port of mochi_arcade/games/paw_pinball.py)
// Kiki the tuxedo cat runs a cat-cafe pinball machine: the ball is a jingle bell, her paws are the flippers.
// 200 missions over 20 tables (exported from Python, PawPinballData.swift), a boss every 10th stage
// (PawPinballBoss.swift), bonus frenzies on every x5 and upgrade cards after bosses and bonuses.
import Foundation

private let LIFE_AT = [50000, 150000, 300000, 500000]     // then every 300000
private let NAP_TIME = 1.1
private let RIGHT_PANEL = 287

final class PPKitten {
    let x, y: Double
    let coat, spot: Int
    let golden: Bool
    var life: Double
    let id: Int
    init(_ x: Double, _ y: Double, _ coat: Int, _ spot: Int, _ golden: Bool, _ life: Double, _ id: Int) {
        self.x = x; self.y = y; self.coat = coat; self.spot = spot; self.golden = golden; self.life = life; self.id = id
    }
}

final class PPCoin {
    let x: Double
    var y: Double
    let rainbow: Bool
    var life: Double
    init(_ x: Double, _ y: Double, _ rainbow: Bool, _ life: Double) { self.x = x; self.y = y; self.rainbow = rainbow; self.life = life }
}

// ----------------------------------------------------------------------------- upgrade cards
let PP_UPGRADES: [Upgrade] = [
    Upgrade(id: "paws", name: "BIG PAWS", desc: "LONGER|FLIPPERS", color: "white", draw: { s, cx, cy, t in
        let w = 7 + Int(sin(t * 4) * 2)
        for side in [-1, 1] {
            s.line(col("white"), cx + side * 2, cy + 3, cx + side * (2 + w), cy - 1, width: 3)
            s.fillRect(col("pink"), cx + side * (1 + w), cy, 1, 1)
        }
    }, max: 3),
    Upgrade(id: "save", name: "NINE LIVES", desc: "LONGER|BALL SAVE", color: "mint", draw: { s, cx, cy, t in
        s.blit(sprite("pp_bell"), cx - 3, cy - 3 - Int(abs(sin(t * 4)) * 3))
        s.fillRect(col("mint"), cx - 6, cy + 5, 13, 1)
    }, max: 3),
    Upgrade(id: "kick", name: "KICKBACK", desc: "SAVES AN|OUTLANE BALL|LV2 BOTH SIDES", color: "orange", draw: { s, cx, cy, t in
        let y = Int(abs(sin(t * 5)) * 6)
        s.fillRect(col("orange"), cx - 2, cy + 2, 5, 4)
        s.blit(sprite("pp_bell"), cx - 3, cy - 4 - y)
    }, max: 2),
    Upgrade(id: "tail", name: "TAIL POST", desc: "KIKI'S TAIL|GUARDS THE|MIDDLE A WHILE", color: "lavender", draw: { s, cx, cy, t in
        for i in 0 ..< 6 { s.fillRect(col("black"), cx - 3 + i + Int(sin(t * 5 + Double(i))), cy + 4 - i * 2, 2, 2) }
        s.fillRect(col("white"), cx + 3, cy - 7, 2, 2)
    }, max: 3),
    Upgrade(id: "power", name: "POWER PAW", desc: "+1 BOSS HIT|FISH WORTH|MORE", color: "red", draw: { s, cx, cy, _ in
        s.circle(col("red"), cx, cy, 5)
        for (dx, dy) in [(-4, -6), (-1, -8), (2, -8), (5, -6)] { s.circle(col("red"), cx + dx, cy + dy + 2, 1) }
        s.fillRect(col("white"), cx - 1, cy - 1, 2, 2)
    }, max: 3),
    Upgrade(id: "bell", name: "GOLDEN BELL", desc: "+25% ALL|POINTS", color: "yellow", draw: { s, cx, cy, t in
        s.blit(sprite("pp_bell"), cx - 3, cy - 3)
        if Int(t * 6) % 2 == 1 {
            s.fillRect(col("white"), cx + 4, cy - 5, 1, 1)
            s.fillRect(col("white"), cx - 5, cy + 3, 1, 1)
        }
    }, max: 4),
    Upgrade(id: "catnip", name: "CATNIP", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "lime", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
        s.fillRect(col("lime"), cx, cy + 3, 1, 4)
    }, max: 3),
    Upgrade(id: "luck", name: "LUCKY CHARM", desc: "BETTER NAP|PRIZES AND|JACKPOTS", color: "orange", draw: { s, cx, cy, t in
        let w = max(1, Int(abs(cos(t * 3)) * 5))
        s.ellipse(col("orange"), cx - w, cy - 5, w * 2 + 1, 11)
        s.ellipse(col("yellow"), cx - w + 1, cy - 4, max(1, w * 2 - 1), 9)
    }, max: 3),
    Upgrade(id: "spring", name: "SPRING PAWS", desc: "STRONGER|FLIPS, EASIER|RAMPS", color: "sky", draw: { s, cx, cy, t in
        let k = Int(abs(sin(t * 6)) * 3)
        for i in 0 ..< 4 { s.fillRect(col("sky"), cx - 4, cy + 4 - i * (2 + k / 2), 9, 1) }
        s.fillRect(col("white"), cx - 1, cy - 6 - k, 3, 3)
    }, max: 3),
    Upgrade(id: "multi", name: "KITTEN PILE", desc: "+1 KITTEN|IN MULTIBALL", color: "pink", draw: { s, cx, cy, t in
        for (i, dx) in [-5, 0, 5].enumerated() {
            s.blit(sprite("pp_kball", remap: PP_KITTEN_COATS[i]), cx + dx - 3, cy - 3 + Int(sin(t * 6 + Double(i)) * 2))
        }
    }, max: 2),
    Upgrade(id: "life", name: "EXTRA BALL", desc: "+1 BALL|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
]

// ----------------------------------------------------------------------------- the game
final class PawPinball: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["LEFT HALF  LEFT PAW (OR THE LEFT BUTTON)", "RIGHT      RIGHT PAW - HOLD AND LET GO",
                            "           TO LAUNCH THE BALL", "NUDGE      NUDGE THE TABLE (DON'T TILT!)"]
    static let helpSkip = 3

    override var music: String? { song() }
    override var buttons: [Action: String] { [.a: waitingPlunger ? "LAUNCH" : "RIGHT", .b: "LEFT", .x: "NUDGE"] }
    override var buttonOrder: [Action] { [.a, .b, .x] }
    override var fourWay: Bool { false }

    var lives: Int
    var levels: [String: Int] = [:]
    var lifeI = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    var mood = "idle", moodT = 0.0
    // stage
    var n = 1
    var st: PPStage = PPData.stages[0]
    var tier = 0
    var tb: PPTable = PPData.arena
    var theme: PPTheme
    var phys: PPPhysics!
    var flippers: [PPFlipper] = []
    var rampEase = 1.0
    var fish: [PPFish] = []
    var banks: [Int] = []
    var bankReset: [Int: Double] = [:]
    var bumpT: [Double] = []
    var rampLens: [[Double]] = []
    var rampFlash: [Double] = []
    var lanes = [false, false, false, false]
    var bonusX = 1
    var kittens: [PPKitten] = []
    var kittenCd = 2.0
    var uid = 0
    var coins: [PPCoin] = []
    var coinCd = 0.5
    var dyn: [PPDyn] = []
    var balls: [PPBall] = []
    var queue: [String] = []
    var goals: [(String, Int)] = []
    var prog: [String: Int] = [:]
    var timeLeft = 0.0, timerOn = false
    var saveT = 0.0, saveReady = true
    var kick = [false, false]
    var tailT = 0.0, tailOn = false
    var tilt = 0.0, tilted = false
    var locks = 0, lockLit = false, multiball = false, jackpotLit = false, jpT = 0.0
    var lastRamp = -99.0, chain = 0
    var skill = -1, skillT = 0.0
    var pull = 0.0, armed = false
    var spinA = 0.0, spinV = 0.0
    var stageScore = 0
    var stats: [String: Int] = [:]
    var missed = false, extraGiven = false
    var stime = 0.0, soundT = 0.0
    var boss: PPBoss?
    var golden = false, goldenT = 0.0
    var bg = Surface(W, H)
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0
    var state = "intro"
    var stateT = 0.0, introLen = 2.6

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = (LIVES[d] ?? 3) + 1           // pinball eats balls: one spare on top
        theme = PPData.tables.first?.theme ?? PPData.arena.theme
        super.init(app, info, opt)
        hype.comboTime = 3.0
        hype.comboY = 191
        let start = max(1, min(STAGES, optInt("stage", optInt("start", 1))))
        startStage(start)
        if start > 10 {          // starting from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (start - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    // ---------------------------------------------------------------- input (touch: the whole left half is the left paw)
    private var padTouch: Bool { app.input.analog != nil }
    private var leftPaw: Bool { padTouch || app.input.down(.b, .left) }
    private var rightPaw: Bool { app.input.down(.a) || (!padTouch && app.input.down(.right)) }
    private var plungeHeld: Bool { app.input.down(.a) || (!padTouch && app.input.down(.down)) }
    private var nudgeHit: Bool { app.input.hit(.x) || (!padTouch && app.input.hit(.up)) }
    private var waitingPlunger: Bool { state == "play" && balls.contains { $0.state == "play" && $0.onPlunger && $0.auto < 0 } }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func pts(_ base: Double) -> Int { Int(base * Double(10 + tier) / 10 * (1 + 0.25 * Double(lv("bell")))) }
    @discardableResult
    func scoreAt(_ base: Double, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int { add(pts(base), x, y, c) }

    @discardableResult
    override func add(_ pts0: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int {
        let got = super.add(pts0, x, y, c)
        stageScore += got
        if prog["score"] != nil { prog["score"]! += got }
        checkLife()
        return got
    }

    func ballDmg() -> Int { 1 + lv("power") }
    func song() -> String { st.kind == "boss" ? "boss" : (st.kind == "bonus" ? "bonus" : (tier % 2 == 0 ? "pp_cafe" : "pp_moon")) }
    func pawLen() -> Double { 23 + 2 * Double(lv("paws")) }
    func saveLen() -> Double { st.save + 4 * Double(lv("save")) }
    func locksNeeded() -> Int { 2 }
    func setMood(_ m: String, _ dur: Double = 1.2) { mood = m; moodT = dur }
    func nextId() -> Int { uid += 1; return uid }
    private func bump(_ k: String, _ by: Int = 1) { if prog[k] != nil { prog[k]! += by } }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        n = num
        st = PPData.stages[num - 1]
        tier = st.tier
        tb = st.kind == "boss" ? PPData.arena : PPData.tables[tier]
        theme = PPData.tables[tier].theme
        reached(num)
        phys = PPPhysics(self, tb)
        phys.grav = PP_GRAV * st.grav
        flippers = [PPFlipper(PP_FLIP_X[0], PP_FLIP_Y, 1, pawLen()), PPFlipper(PP_FLIP_X[1], PP_FLIP_Y, -1, pawLen())]
        for f in flippers { f.power = 1 + 0.07 * Double(lv("spring")) }
        rampEase = 1 - 0.1 * Double(lv("spring"))
        fish = tb.fish.map { PPFish($0) }
        banks = Array(Set(fish.map { $0.bank })).sorted()
        bankReset = [:]
        for b in banks { bankReset[b] = 0 }
        bumpT = Array(repeating: 0, count: tb.bumpers.count)
        rampLens = tb.ramps.map { ppRampLengths($0.path) }
        rampFlash = Array(repeating: 0, count: tb.ramps.count)
        lanes = [false, false, false, false]
        bonusX = 1
        kittens = []
        kittenCd = 2
        coins = []
        coinCd = 0.5
        dyn = []
        balls = []
        queue = []
        goals = st.goals
        prog = [:]
        for (g, _) in goals { prog[g] = 0 }
        timeLeft = st.time
        timerOn = false
        saveT = 0; saveReady = true
        kick = [lv("kick") >= 1, lv("kick") >= 2]
        tailT = 0; tailOn = false
        tilt = 0; tilted = false
        locks = 0; lockLit = false; multiball = false; jackpotLit = false; jpT = 0
        lastRamp = -99; chain = 0
        skill = -1; skillT = 0
        pull = 0; armed = false
        spinA = 0; spinV = 0
        stageScore = 0
        stats = ["switch": 0, "jackpot": 0, "coins": 0, "rainbow": 0, "combo": 0]
        missed = false; extraGiven = false
        stime = 0; soundT = 0
        boss = st.boss.map { PPBoss(self, $0) }
        golden = st.kind == "normal" && hype.lucky(0.04 + 0.015 * Double(lv("luck")))
        goldenT = Double.random(in: 8 ... 20)
        bg = PPArt.makeBg(tb, theme)
        tally = []
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.2 : 2.6
        if st.kind == "bonus" {
            queue = Array(repeating: "kitten", count: st.bonus == "party" ? 3 : 2)
            jackpotLit = st.bonus == "party"
        } else {
            serve("bell", auto: false)
        }
        if hype.feverOn { hype.feverT = 0 }
        hype.feverTime = 8 + 2 * Double(lv("catnip"))
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil {
            hype.flash("red", 0.3)
            setMood("angry", 99)
        } else {
            setMood("happy", 1.5)
        }
    }

    @discardableResult
    func serve(_ kind: String = "bell", auto: Bool = true) -> PPBall {
        let b = PPBall(PP_LANE_START.0, PP_LANE_START.1, 0, 0, kind)
        b.coat = Int.random(in: 0 ... 5)
        if auto {
            b.auto = 0.35
        } else {
            skill = Int.random(in: 0 ... 3)
            skillT = 0
        }
        balls.append(b)
        return b
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        moodT -= dt
        if moodT <= 0 { mood = boss != nil && boss!.state != "dead" ? "angry" : "idle" }
        switch state {
        case "intro":
            flipInput(dt)
            phys.events = []
            phys.step(dt)
            boss?.update(dt)
            if stateT > introLen || (stateT > 0.5 && app.input.hit(.a)) {
                state = "play"
                stateT = 0
                armed = !plungeHeld
                boss?.state = "fight"
            }
        case "play":
            play(dt)
        case "lost":
            flipInput(dt)
            if stateT > 1.6 {
                state = "play"
                stateT = 0
                saveReady = true
                tilted = false
                tilt = 0
                serve("bell", auto: false)
                armed = !plungeHeld
            }
        case "clear":
            flipInput(dt)
            boss?.update(dt)
            if stateT > 1.8 { beginTally() }
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(PP_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        default: break
        }
        updateFx(dt)
    }

    private func updateFx(_ dt: Double) {
        for i in bumpT.indices { bumpT[i] = max(0, bumpT[i] - dt) }
        for i in rampFlash.indices { rampFlash[i] = max(0, rampFlash[i] - dt) }
        spinA += spinV * dt
        spinV *= max(0, 1 - dt * 1.5)
        for b in balls where b.state == "play" {
            b.trail.append((b.x, b.y))
            if b.trail.count > 6 { b.trail.removeFirst() }
        }
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = PP_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id]!)", color: u.color, dur: 1.2, scale: 1)
        }
        switch id {
        case "life":
            lives += 1
            app.audio.play("extra")
        case "paws":
            for f in flippers { f.len = pawLen() }
        case "spring":
            for f in flippers { f.power = 1 + 0.07 * Double(lv("spring")) }
            rampEase = 1 - 0.1 * Double(lv("spring"))
        case "kick":
            kick = [lv("kick") >= 1, lv("kick") >= 2]
        default: break
        }
    }

    // ---------------------------------------------------------------- input
    private func flipInput(_ dt: Double) {
        let presses = [leftPaw, rightPaw]
        for (i, f) in flippers.enumerated() {
            f.stun = max(0, f.stun - dt)
            var p = presses[i]
            if tilted || !["play", "intro", "lost", "clear"].contains(state) { p = false }
            if p && !f.pressed && f.stun <= 0 {
                app.audio.play("lock")
                if !lanes.allSatisfy({ $0 }) {      // lane change: the lit letters slide with the paws
                    lanes = i == 0 ? Array(lanes[1...] + lanes[..<1]) : Array(lanes[3...] + lanes[..<3])
                }
            }
            f.pressed = p
        }
    }

    private func plunger(_ dt: Double) {
        let held = plungeHeld
        let ball = balls.first { $0.state == "play" && $0.onPlunger }
        if let b = ball, b.auto >= 0 {
            b.auto -= dt
            if b.auto < 0 { launch(b, 0.62 + Double.random(in: 0 ... 0.3)) }
            return
        }
        if !held {
            if pull > 0.04, let b = ball { launch(b, pull) }
            pull = 0
            armed = true
        } else if armed && ball != nil {
            pull = min(1, pull + dt / 0.9)
        }
    }

    private func launch(_ b: PPBall, _ power: Double) {
        b.vy = -(240 + 380 * power)
        b.vx = 0
        b.auto = -1
        app.audio.play("shoot")
        pull = 0
    }

    private func nudge() {
        if tilted { return }
        tilt += 0.4
        app.shake(2, 0.15)
        app.audio.play("hold")
        for b in balls where b.state == "play" && !b.inLane {
            b.vy -= 80
            b.vx += Double.random(in: -30 ... 30)
        }
        if tilt > 1.0 {
            tilted = true
            saveT = 0
            hype.banner("TILT!", "PAWS OFF THE TABLE", color: "red", dur: 2.0, sound: "boom")
            hype.flash("red", 0.3)
            setMood("hurt", 2.0)
            hype.breakCombo()
        } else if tilt > 0.6 {
            hype.banner("DANGER!", color: "orange", dur: 0.8, scale: 1)
        }
    }

    // ---------------------------------------------------------------- play
    private func play(_ dt: Double) {
        stime += dt
        soundT -= dt
        flipInput(dt)
        plunger(dt)
        if nudgeHit { nudge() }
        tilt = max(0, tilt - dt * 0.35)
        if saveT > 0 { saveT -= dt }
        if tailT > 0 { tailT -= dt }
        tailOn = tailT > 0
        jpT -= dt
        if multiball && !jackpotLit && jpT <= 0 {
            jackpotLit = true
            hype.banner("JACKPOT LIT!", "HIT A RAMP", color: "yellow", dur: 1.0, scale: 1)
        }
        if skill >= 0 { skillT += dt }
        if !queue.isEmpty && !balls.contains(where: { $0.state == "play" && $0.inLane }) {
            serve(queue.removeFirst(), auto: true)
        }
        if timerOn && st.time > 0 {
            timeLeft -= dt
            if timeLeft <= 0 {
                if st.kind == "bonus" {          // a bonus frenzy just ends
                    timeLeft = 0
                    stageClear()
                } else {
                    timeUp()
                }
                return
            }
        }
        updateKittens(dt)
        if st.kind == "bonus" && st.bonus == "fountain" { updateCoins(dt) }
        boss?.update(dt)
        for bank in banks where (bankReset[bank] ?? 0) > 0 {
            bankReset[bank]! -= dt
            if bankReset[bank]! <= 0 { for f in fish where f.bank == bank { f.down = 0 } }
        }
        dyn = makeDyn()
        phys.events = []
        phys.step(dt)
        for ev in phys.events { onEvent(ev.kind, ev.a, ev.x, ev.y) }
        updateBalls(dt)
        updateDrains()
        checkMission()
    }

    private func makeDyn() -> [PPDyn] {
        var out: [PPDyn] = []
        for k in kittens { out.append(PPDyn(x: k.x, y: k.y, r: 5, kind: "kitten", solid: true, ref: k.id)) }
        for (i, c) in coins.enumerated() { out.append(PPDyn(x: c.x, y: c.y, r: 5, kind: "coin", solid: false, ref: i)) }
        if let b = boss { out += b.dyn() }
        return out
    }

    private func updateBalls(_ dt: Double) {
        for b in balls {
            b.bossCd = max(0, b.bossCd - dt)
            b.napCd = max(0, b.napCd - dt)
            if b.state == "ramp" {
                let r = tb.ramps[b.ramp]
                let lens = rampLens[b.ramp]
                b.rd += b.rv * dt
                let p = ppRampPos(r.path, lens, b.rd)
                b.x = p.0; b.y = p.1
                if b.rd >= lens[lens.count - 1] {
                    b.state = "play"
                    b.vx = r.out.0; b.vy = r.out.1
                    b.trail = []
                    rampDone(b, b.ramp)
                }
            } else if b.state == "nap" {
                b.napT += dt
                if b.napT > NAP_TIME, let sa = tb.saucer {
                    b.state = "play"
                    b.napCd = 0.6
                    let d: Double = sa.0 > PP_CX + 10 ? -1 : (sa.0 < PP_CX - 10 ? 1 : (Bool.random() ? 1 : -1))
                    b.vx = d * Double.random(in: 110 ... 160)
                    b.vy = Double.random(in: 120 ... 170)
                    app.audio.play("shoot")
                    parts.burst(b.x, b.y, 8, ["lavender", "white"], 50, 0.4)
                }
            } else if b.state == "play" {
                if b.y > 172 && b.vy > 0 {         // kickbacks in the outlanes
                    let side = b.x < 84 ? 0 : (b.x > 226 && b.x < PP_RW ? 1 : -1)
                    if side >= 0 && kick[side] {
                        kick[side] = false
                        b.vy = -470; b.vx = side == 0 ? 25 : -25
                        hype.banner("KICKBACK!", color: "orange", dur: 0.9, scale: 1, sound: "boom")
                        app.shake(3, 0.2)
                        parts.burst(b.x, b.y, 12, ["orange", "yellow"], 80, 0.5)
                    }
                }
                if hypot(b.x - b.ax, b.y - b.ay) > 5 {    // stuck rescue (cradling on a raised paw is fine)
                    b.ax = b.x; b.ay = b.y; b.stillT = 0
                } else {
                    b.stillT += dt
                    let nearPaws = b.y > 150 && abs(b.x - PP_CX) < 40
                    if b.stillT > 2.5 && !nearPaws && !b.inLane {
                        b.vy = -220; b.vx = Double.random(in: -90 ... 90)
                        b.stillT = 0
                        floats.add(b.x, b.y - 8, "NUDGE!", "white")
                    }
                    if b.stillT > 6 && b.inLane && b.auto < 0 && st.kind == "bonus" { b.auto = 0.1 }
                }
            }
        }
    }

    private func updateDrains() {
        let gone = balls.filter { $0.state == "gone" }
        if gone.isEmpty { return }
        balls = balls.filter { $0.state != "gone" }
        var saved = false
        for b in gone where st.kind == "bonus" || (saveT > 0 && !tilted) {
            queue.append(b.kind)
            saved = true
        }
        if saved && st.kind != "bonus" {
            hype.banner("BALL SAVED!", "KIKI CAUGHT IT", color: "mint", dur: 1.2, scale: 1, sound: "powerup")
        }
        let alive = balls.filter { $0.state != "gone" }
        if multiball && alive.count + queue.count <= 1 {
            multiball = false
            jackpotLit = false
            hype.banner("MULTIBALL OVER", color: "lavender", dur: 1.0, scale: 1)
        }
        if alive.isEmpty && queue.isEmpty { ballLost() }
    }

    private func ballLost() {
        lives -= 1
        missed = true
        multiball = false
        jackpotLit = st.kind == "bonus" && st.bonus == "party"
        timerOn = false
        hype.breakCombo()
        app.audio.play("die")
        setMood("sad", 2.0)
        app.shake(3, 0.3)
        boss?.releaseBall()
        if lives <= 0 {
            state = "over"
            hype.banner("GAME OVER", "KIKI NEEDS A NAP...", color: "red", dur: 3.0)
            endGame(false, "STAGE \(n)", delay: 2.6)
            app.audio.play("gameover")
            return
        }
        state = "lost"
        stateT = 0
        hype.banner("BALL LOST", "\(lives) LEFT", color: "pink", dur: 1.4, scale: 1)
    }

    private func timeUp() {
        hype.banner("TIME UP!", "-1 BALL", color: "red", dur: 1.6, sound: "hurt")
        timeLeft = st.time
        for b in balls {
            if b.state == "held" { boss?.releaseBall() }
            parts.burst(b.x, b.y, 8, ["white", "gray"], 40, 0.4)
        }
        balls = []
        queue = []
        ballLost()
    }

    private func checkLife() {
        let target = lifeI < LIFE_AT.count ? LIFE_AT[lifeI] : LIFE_AT[LIFE_AT.count - 1] + 300000 * (lifeI - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("EXTRA BALL!", color: "hotpink", dur: 1.5, sound: "extra")
            hype.shower(30, "hearts")
        }
    }

    // ---------------------------------------------------------------- events
    func switchHit() {
        stats["switch", default: 0] += 1
        bump("hits")
        hype.hit(1, fever: 0.016 * (1 + 0.4 * Double(lv("catnip"))))
    }

    private func onEvent(_ kind: String, _ a: Int, _ x: Double, _ y: Double) {
        let au = app.audio
        switch kind {
        case "bumper":
            if bumpT[a] > 0.05 { return }
            bumpT[a] = 0.15
            au.play("pop")
            scoreAt(100, x, y - 12)
            parts.burst(x, y, 6, ["white", theme.bump, "yellow"], 50, 0.35)
            bump("bump")
            switchHit()
            if boss == nil && Double.random(in: 0 ..< 1) < 0.15 {
                floats.add(x, y - 18, ["MEW!", "MRRP!", "NYA!", "PURR!"].randomElement()!, "pink")
            }
        case "sling":
            if soundT <= 0 { au.play("brick"); soundT = 0.05 }
            scoreAt(30)
            switchHit()
        case "wall":
            if soundT <= 0 && a > 200 { au.play("tin"); soundT = 0.08 }
        case "fish":
            fishHit(a, x, y)
        case "lane":
            laneHit(a, x, y)
        case "spin":
            let spins = max(1, a / 70)
            spinV = min(40, Double(a) / 8)
            au.play("type")
            scoreAt(40 * Double(spins), x, y - 8, "pink")
            bump("spin", spins)
            switchHit()
        case "nap":
            napHit(x, y)
        case "ramp_in":
            au.play("jump")
            rampFlash[a] = 0.5
            setMood("wow", 1.0)
        case "ramp_fail":
            floats.add(x, y - 8, "TOO SLOW!", "gray")
        case "launched":
            launched()
        case "kitten":
            kittenHit(a, x, y)
        case "coin":
            if a < coins.count && coins[a].life > 0 {
                let c = coins[a]
                c.life = 0
                if c.rainbow {
                    stats["rainbow", default: 0] += 1
                    scoreAt(2500, c.x, c.y - 8, "hotpink")
                    au.play("bonus")
                    hype.shower(14, "stars")
                } else {
                    stats["coins", default: 0] += 1
                    scoreAt(250, c.x, c.y - 8)
                    au.play("coin")
                }
                switchHit()
            }
        case "boss", "grab", "eat", "bunny", "pickle":
            if let bs = boss {
                let b = ballAt(x, y)
                if b != nil || kind == "bunny" || kind == "pickle" { bs.onBall(kind, a, b) }
            }
        default: break
        }
    }

    private func ballAt(_ x: Double, _ y: Double) -> PPBall? {
        var best: PPBall?, bd = 1e9
        for b in balls where b.state == "play" {
            let d = (b.x - x) * (b.x - x) + (b.y - y) * (b.y - y)
            if d < bd { best = b; bd = d }
        }
        return best
    }

    private func launched() {
        if saveReady && st.kind != "bonus" {
            saveReady = false
            saveT = saveLen()
            if lv("tail") > 0 { tailT = 5 + 10 * Double(lv("tail")) }
        }
        timerOn = true
    }

    private func fishHit(_ i: Int, _ x: Double, _ y: Double) {
        let f = fish[i]
        app.audio.play("fruit")
        scoreAt(500 * (1 + 0.5 * Double(lv("power"))), x, y - 8, "sky")
        parts.burst(x, y, 8, ["sky", "white", "blue"], 50, 0.4)
        bump("fish")
        switchHit()
        let bank = f.bank
        if fish.filter({ $0.bank == bank }).allSatisfy({ $0.down > 0 }) {
            bankReset[bank] = 1.2
            scoreAt(2500, x, y - 18, "mint")
            app.audio.play("line")
            if let bs = boss {
                hype.banner("FISH BARRAGE!", color: "orange", dur: 1.0, scale: 1)
                for k in 0 ..< 2 { bs.projs.append(PPProj(x + Double(k * 2 - 1) * 6, y, Double(k * 2 - 1) * 60, -160, "missile", ballDmg())) }
            } else if tb.saucer != nil && !multiball && !lockLit && st.kind == "normal" {
                lockLit = true
                hype.banner("LOCK IS LIT!", "SHOOT THE NAP BED", color: "lavender", dur: 1.2, scale: 1)
            } else {
                hype.banner("FISH FRY!", color: "sky", dur: 0.9, scale: 1)
            }
        }
    }

    private func laneHit(_ i: Int, _ x: Double, _ y: Double) {
        if skill >= 0 {
            if i == skill && skillT < 6 {
                hype.banner("SKILL SHOT!", "+\(pts(5000))", dur: 1.4, rainbow: true, sound: "bonus")
                scoreAt(5000)
                setMood("happy", 1.5)
            }
            skill = -1
        }
        if !lanes[i] {
            lanes[i] = true
            app.audio.play("select")
            scoreAt(250, x, y - 10)
        } else {
            scoreAt(100, x, y - 10)
        }
        switchHit()
        if lanes.allSatisfy({ $0 }) {
            lanes = [false, false, false, false]
            bonusX = min(6, bonusX + 1)
            scoreAt(2000 + 500 * Double(bonusX))
            bump("meow")
            hype.banner("MEOW!!", "BONUS X\(bonusX)", dur: 1.4, rainbow: true, sound: "quad")
            hype.shower(20, "hearts")
            setMood("happy", 1.6)
            if lv("kick") > 0 { kick = [lv("kick") >= 1 || kick[0], lv("kick") >= 2 || kick[1]] }
        }
    }

    private func napHit(_ x: Double, _ y: Double) {
        app.audio.play("trap")
        setMood("sleepy", NAP_TIME + 0.4)
        scoreAt(1000, x, y - 12, "lavender")
        bump("nap")
        switchHit()
        if st.kind == "bonus" { return }
        if lockLit && !multiball {
            lockLit = false
            locks += 1
            if locks >= locksNeeded() {
                startMultiball()
            } else {
                hype.banner("KITTEN LOCKED!", "\(locks)/\(locksNeeded())", color: "pink", dur: 1.3, sound: "levelup")
            }
            return
        }
        napPrize(x, y)
    }

    private func napPrize(_ x: Double, _ y: Double) {
        let r = Double.random(in: 0 ..< 1)
        let luck = Double(lv("luck"))
        if r < 0.015 + 0.01 * luck {
            hype.jackpot(pts(20000), sub: "NAP JACKPOT!")
            stats["jackpot", default: 0] += 1
            setMood("wow", 2.0)
            return
        }
        if r < 0.04 + 0.012 * luck && !extraGiven {
            extraGiven = true
            lives += 1
            hype.banner("EXTRA BALL!", "SWEET DREAMS", color: "hotpink", dur: 1.5, sound: "extra")
            return
        }
        var prizes = ["points", "save", "lane", "catnip"]
        if !tb.fish.isEmpty && !lockLit && !multiball { prizes.append("lock") }
        if !kick[0] { prizes.append("kick") }
        switch prizes.randomElement()! {
        case "points":
            let got = scoreAt(5000 + 2500 * luck)
            hype.banner("DREAM POINTS", "+\(got)", color: "yellow", dur: 1.1, scale: 1)
        case "save":
            saveT = max(saveT, 10)
            hype.banner("BALL SAVE 10S", color: "mint", dur: 1.1, scale: 1)
        case "lane":
            let off = lanes.indices.filter { !lanes[$0] }
            if let i = off.randomElement() { lanes[i] = true }
            hype.banner("FREE LETTER", color: "yellow", dur: 1.1, scale: 1)
        case "catnip":
            hype.feverAdd(0.35)
            hype.banner("CATNIP!", "FEVER UP", color: "lime", dur: 1.1, scale: 1)
        case "lock":
            lockLit = true
            hype.banner("LOCK IS LIT!", color: "lavender", dur: 1.1, scale: 1)
        default:
            kick[0] = true
            hype.banner("KICKBACK LIT", color: "orange", dur: 1.1, scale: 1)
        }
        app.audio.play("powerup")
    }

    private func startMultiball() {
        locks = 0
        multiball = true
        jackpotLit = true
        saveT = max(saveT, 10)
        queue += Array(repeating: "kitten", count: 2 + lv("multi"))
        hype.banner("KITTEN MULTIBALL!", "HIT THE RAMPS FOR JACKPOTS", dur: 2.0, rainbow: true, sound: "fever")
        hype.shower(40, "confetti")
        hype.flash("pink", 0.25)
        setMood("wow", 2.5)
        bump("multi")
    }

    private func rampDone(_ b: PPBall, _ i: Int) {
        let r = tb.ramps[i]
        rampFlash[i] = 0.6
        app.audio.play("levelup")
        let name = r.kind == "tower" ? "TOWER CLIMB!" : "FISH SLIDE!"
        scoreAt(1000, b.x, b.y - 10, "mint")
        bump("ramp")
        switchHit()
        if stime - lastRamp < 5.0 && st.kind != "bonus" {
            chain += 1
            stats["combo", default: 0] += 1
            bump("combo")
            let bonus = scoreAt(500 * Double(min(4, chain)))
            hype.banner("RAMP COMBO!", "+\(bonus)", color: "orange", dur: 1.1, scale: 1, sound: "combo")
        } else {
            chain = 0
            floats.add(b.x, b.y - 18, name, "white")
        }
        lastRamp = stime
        setMood("happy", 1.2)
        if let bs = boss {
            let e = r.path[r.path.count - 1]
            bs.projs.append(PPProj(e.0, e.1, 0, -120, "missile", ballDmg() + 1))
            hype.banner("POUNCE!", color: "orange", dur: 0.8, scale: 1)
            return
        }
        if jackpotLit {
            if st.kind == "bonus" {
                scoreAt(1000, b.x, b.y - 18, "hotpink")
                hype.banner("PARTY POINTS!", color: "hotpink", dur: 0.8, scale: 1)
                stats["jackpot", default: 0] += 1
            } else {
                jackpotLit = false
                jpT = 5
                stats["jackpot", default: 0] += 1
                hype.jackpot(pts(8000 + 1000 * Double(tier)), sub: "KITTEN JACKPOT!")
            }
        }
    }

    private func kittenHit(_ kid: Int, _ x: Double, _ y: Double) {
        guard let i = kittens.firstIndex(where: { $0.id == kid }) else { return }
        let k = kittens.remove(at: i)
        if k.golden {
            hype.jackpot(pts(25000), sub: "GOLDEN KITTEN!")
            stats["jackpot", default: 0] += 1
            setMood("wow", 2.0)
        } else {
            app.audio.play("eat")
            scoreAt(1500, x, y - 10, "pink")
            hype.banner("RESCUED!", color: "pink", dur: 0.7, scale: 1)
            setMood("happy", 1.0)
        }
        bump("rescue")
        parts.burst(x, y, 12, ["pink", "white", "yellow"], 60, 0.5)
        switchHit()
    }

    private func updateKittens(_ dt: Double) {
        for k in kittens { k.life -= dt }
        kittens = kittens.filter { $0.life > 0 || !$0.golden }
        if golden && stime > goldenT, let p = tb.spots.randomElement() {
            golden = false
            kittens.append(PPKitten(p.0, p.1, 0, -1, true, 12, nextId()))
            hype.banner("GOLDEN KITTEN!", "QUICK - BEFORE IT RUNS", dur: 1.4, rainbow: true, sound: "bonus")
        }
        guard let have = prog["rescue"], let need = goals.first(where: { $0.0 == "rescue" })?.1, have < need else { return }
        kittenCd -= dt
        if kittenCd <= 0 && kittens.filter({ !$0.golden }).count < 2 {
            let used = Set(kittens.map { $0.spot })
            let free = tb.spots.indices.filter { !used.contains($0) }
            if let i = free.randomElement() {
                let p = tb.spots[i]
                kittens.append(PPKitten(p.0, p.1, Int.random(in: 0 ... 5), i, false, 0, nextId()))
                app.audio.play("bubble")
            }
            kittenCd = 2.5
        }
    }

    private func updateCoins(_ dt: Double) {
        for c in coins {
            if c.life > 0 { c.life -= dt }
            c.y += sin(stime * 2 + c.x) * 4 * dt
        }
        coins = coins.filter { $0.life > 0 }
        coinCd -= dt
        if coinCd <= 0 && coins.count < 8 {
            coinCd = 0.45
            let x = Double.random(in: 104 ... 216), y = Double.random(in: 48 ... 132)
            if !(x < 110 && y < 112) { coins.append(PPCoin(x, y, Double.random(in: 0 ..< 1) < 0.06, 7)) }
        }
    }

    func stunPaw(_ side: Int, _ dur: Double, _ text: String) {
        let f = flippers[side]
        f.stun = dur
        f.pressed = false
        let (tx, _) = f.tip()
        floats.add((f.px + tx) / 2, f.py - 14, text, "red")
        app.audio.play("hurt")
        setMood("hurt", 1.0)
    }

    func bossHitFx(_ b: PPBall) {
        scoreAt(500, b.x, b.y - 10, "orange")
        switchHit()
        setMood("happy", 0.6)
    }

    func bossDefeated() {
        guard let bs = boss else { return }
        app.audio.play("bossdown")
        hype.banner("BOSS DOWN!", bs.name, dur: 2.4, rainbow: true, scale: 2)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        hype.slowmo(0.3, 1.4)
        app.shake(6, 0.6)
        scoreAt(15000, bs.x, bs.y)
        setMood("happy", 3.0)
        stageClear(quiet: true)
    }

    // ---------------------------------------------------------------- mission
    private func checkMission() {
        if state != "play" { return }
        if st.kind == "normal" && goals.allSatisfy({ (prog[$0.0] ?? 0) >= $0.1 }) { stageClear() }
    }

    private func stageClear(quiet: Bool = false) {
        if state != "play" { return }
        state = "clear"
        stateT = 0
        queue = []
        if !quiet {
            app.audio.play("win")
            hype.banner(st.kind == "bonus" ? "BONUS OVER!" : "MISSION CLEAR!", color: "mint", dur: 1.6)
            hype.shower(30, "confetti")
            hype.slowmo(0.3, 0.8)
            setMood("happy", 2.5)
        }
        for b in balls { parts.burst(b.x, b.y, 10, ["yellow", "white"], 60, 0.5) }
        balls = []
        kittens = kittens.filter { !$0.golden }
        app.audio.music(nil)
    }

    private func beginTally() {
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("MISSION BONUS", pts(3000 + 300 * Double(tier))))
            if st.time > 0 { rows.append(("TIME LEFT \(Int(timeLeft))S", pts(Double(Int(timeLeft) * 100)))) }
            rows.append(("MEOW BONUS X\(bonusX)", pts(1000 * Double(bonusX))))
            rows.append(("NO MISS", missed ? 0 : pts(5000)))
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", pts(10000 + 1000 * Double(tier))))
            rows.append(("NO MISS", missed ? 0 : pts(8000)))
        } else {
            let sw = stats["switch"] ?? 0, jp = stats["jackpot"] ?? 0
            rows.append(("SWITCHES x\(sw)", pts(Double(sw * 10))))
            if st.bonus == "party" {
                rows.append(("PARTY SHOTS x\(jp)", pts(Double(jp * 1000))))
            } else {
                let c = stats["coins"] ?? 0, rb = stats["rainbow"] ?? 0
                rows.append(("FISH COINS x\(c)", pts(Double(c * 100))))
                rows.append(("RAINBOW FISH x\(rb)", pts(Double(rb * 1000))))
            }
        }
        rows.append(("BEST COMBO \(hype.bestCombo)", pts(Double(min(hype.bestCombo, 200) * 20))))
        tally = rows.map { ($0.0, $0.1, 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        hype.bestCombo = 0
        if st.kind != "bonus" && !missed {
            hype.banner("PURRFECT!", "NO BALL LOST", dur: 1.8, rainbow: true, sound: "fever")
            hype.shower(40, "stars")
        }
    }

    private func updateTally(_ dt: Double) {
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
            tally[tallyI].shown = min(v, tally[tallyI].shown + max(1, v * dt / 0.4))
            if tally[tallyI].shown >= v {
                if tally[tallyI].v > 0 {
                    add(tally[tallyI].v)
                    app.audio.play("coin")
                }
                tallyI += 1
            }
        } else {
            tallyWait += dt
            if tallyWait > 1.6 || skip { finishStage() }
        }
    }

    private func finishStage() {
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "KIKI'S CAFE IS SAVED", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "TREAT TIME!"
            state = "pick"
        } else {
            startStage(nextN!)
        }
    }

    // ---------------------------------------------------------------- drawing
    override func render(_ s: Surface) {
        let t = self.t
        s.blit(bg, 0, 0)
        for (i, l) in tb.lanes.enumerated() { PPArt.laneLetter(s, i, l.0, lanes[i], t, skill: i == skill) }
        if tb.spinner.count == 4 { PPArt.spinner(s, tb.spinner, spinA, t) }
        if let sa = tb.saucer {
            PPArt.saucer(s, sa.0, sa.1, t, busy: balls.contains { $0.state == "nap" }, lit: lockLit)
        }
        for f in fish { PPArt.fish(s, f, t) }
        for (i, b) in tb.bumpers.enumerated() { PPArt.bumper(s, b.0, b.1, theme.bump, bumpT[i], t, i) }
        for k in kittens { PPArt.kitten(s, k.x, k.y, k.coat, t, golden: k.golden) }
        for c in coins { PPArt.coinFish(s, c.x, c.y, t, rainbowFish: c.rainbow) }
        if tailOn {
            s.line(col("black"), 155, 182, 155, 191, width: 4)
            s.fillRect(col("white"), 154, 182, 2, 2)
        }
        if saveT > 0 && (saveT > 2 || Int(t * 8) % 2 == 1) { s.blit(sprite("pp_bell"), 152, 192) }
        for (side, on) in kick.enumerated() where on {
            let x = side == 0 ? 78 : 232
            s.fillRect(col(Int(t * 4) % 2 == 1 ? "orange" : "yellow"), x - 2, 196, 5, 3)
        }
        boss?.draw(s, t)
        for b in balls where (b.state == "play" || b.state == "nap") && !(b.state == "nap" && Int(t * 6) % 2 == 1) {
            PPArt.ball(s, b, t, fever: hype.feverOn)
        }
        for f in flippers { PPArt.flipper(s, f, t, fever: hype.feverOn) }
        drawPlunger(s, t)
        for (i, r) in tb.ramps.enumerated() {
            let lit = jackpotLit || boss != nil
            var c = r.kind == "tower" ? "mint" : "sky"
            if rampFlash[i] > 0 && Int(t * 12) % 2 == 1 { c = "white" }
            PPArt.ramp(s, r, rampLens[i], t, c, lit: lit)
        }
        for b in balls where b.state == "ramp" { PPArt.ball(s, b, t, fever: hype.feverOn) }
        parts.draw(s)
        floats.draw(s)
        drawHud(s, t)
        if state == "intro" { drawIntro(s, t) } else if state == "tally" { drawTally(s, t) }
        if tilted && Int(t * 4) % 2 == 1 { drawText(s, "TILT", 155, 100, "red", scale: 3, align: .center, shadow: nil, outline: "black") }
    }

    private func drawPlunger(_ s: Surface, _ t: Double) {
        let y = Int(PP_PLUNGE_Y + pull * 8), x = Int(PP_LANE_X)
        s.fillRect(col("gray"), x - 1, y, 3, H - y)
        s.fillRect(col("red"), x - 4, y, 9, 2)
        if waitingPlunger && Int(t * 3) % 2 == 1 {
            for i in 0 ..< 3 { s.fillRect(col("yellow"), x - 1, 150 + i * 6 - Int(t * 12) % 6, 3, 2) }
        }
    }

    private func drawHud(_ s: Surface, _ t: Double) {
        // ---- left panel: score, stage, mission, MEOW
        drawText(s, String(format: "%08d", score), 4, 3, "white", shadow: nil)
        drawText(s, "HI " + String(format: "%07d", max(best, score)), 4, 12, "gray", shadow: nil)
        drawText(s, "STAGE \(n)", 4, 24, "yellow", shadow: nil)
        var y = 35
        if st.kind == "normal" {
            drawText(s, "MISSION", 4, y, "lavender", shadow: nil)
            y += 10
            for (g, c) in goals {
                let have = min(prog[g] ?? 0, c)
                let word = PPData.goals[g]?.0 ?? g.uppercased()
                let done = have >= c
                let txt = g == "score" ? "\(word) \(c / 1000)K" : (g == "multi" ? word : "\(word) \(have)/\(c)")
                drawText(s, txt, 4, y, done ? "lime" : "white", shadow: nil)
                s.fillRect(col("darkgray"), 4, y + 8, 58, 2)
                s.fillRect(col(done ? "lime" : "orange"), 4, y + 8, Int(58 * Double(have) / Double(max(1, c))), 2)
                y += 13
            }
        } else if st.kind == "boss" {
            drawText(s, "BOSS FIGHT", 4, y, "red", shadow: nil)
            drawText(s, boss?.name ?? "", 4, y + 10, "white", shadow: nil)
            drawText(s, "HIT IT WITH", 4, y + 24, "gray", shadow: nil)
            drawText(s, "THE BELL!", 4, y + 33, "gray", shadow: nil)
            y += 46
        } else {
            drawText(s, "BONUS!", 4, y, rainbow(0, t), shadow: nil)
            drawText(s, st.bonus == "party" ? "SCORE ALL" : "GRAB THE", 4, y + 10, "white", shadow: nil)
            drawText(s, st.bonus == "party" ? "YOU CAN!" : "GOLD FISH!", 4, y + 19, "white", shadow: nil)
            y += 32
        }
        if st.time > 0 {
            let secs = Int(timeLeft.rounded(.up))
            drawText(s, "TIME \(secs)", 4, y + 2, secs > 10 || Int(t * 6) % 2 == 1 ? "yellow" : "red", shadow: nil)
        }
        for (i, ch) in "MEOW".enumerated() {
            let c = lanes[i] ? (Int(t * 4 + Double(i)) % 3 != 0 ? "yellow" : "white") : "darkgray"
            drawText(s, String(ch), 6 + i * 14, 112, c, scale: 2, shadow: "black")
        }
        drawText(s, "BONUS X\(bonusX)", 4, 130, "peach", shadow: nil)
        y = 142
        if multiball {
            drawText(s, "MULTIBALL", 4, y, rainbow(1, t), shadow: nil)
            y += 10
        } else if lockLit {
            drawText(s, "LOCK LIT!", 4, y, Int(t * 4) % 2 == 1 ? "pink" : "lavender", shadow: nil)
            y += 10
        } else if locks > 0 {
            drawText(s, "LOCKED \(locks)/\(locksNeeded())", 4, y, "pink", shadow: nil)
            y += 10
        }
        if jackpotLit && Int(t * 4) % 2 == 1 { drawText(s, "JACKPOT!", 4, y, "yellow", shadow: nil) }
        // ---- right panel: Kiki, balls, fever, status
        panel(s, IRect(256, 2, 62, 58), fill: "night", border: theme.wall, radius: 3, shadow: false)
        var lx = 0.0, ly = 0.0
        var m = mood
        var tgt: PPBall?
        for b in balls where (b.state == "play" || b.state == "ramp") && (tgt == nil || b.y > tgt!.y) { tgt = b }
        if let g = tgt {
            lx = max(-1, min(1, (g.x - 160) / 70))
            ly = max(-1, min(1, (g.y - 90) / 70))
            if m == "idle" && g.y > 160 && abs(g.x - PP_CX) < 16 && g.vy > 60 { m = "worried" }
        }
        PPArt.kiki(s, RIGHT_PANEL, 28, m, t, lx, ly, blink: Int(t * 1.3) % 5 == 0 && m == "idle")
        drawText(s, "KIKI", 260, 5, "white", shadow: "black")
        drawText(s, "BALLS", 258, 64, "lavender", shadow: nil)
        for i in 0 ..< max(0, min(lives, 7)) { s.blit(sprite("pp_bell"), 258 + i * 8, 73) }
        if lives > 7 { drawText(s, "+\(lives - 7)", 300, 73, "yellow", shadow: nil) }
        drawText(s, "FEVER", 258, 84, "orange", shadow: nil)
        let x0 = 258, y0 = 93
        s.fillRect(col("darkgray"), x0, y0, 58, 3)
        if hype.feverOn {
            for i in 0 ..< 58 { s.fillRect(col(rainbow(i / 6, t)), x0 + i, y0, 1, 3) }
        } else {
            s.fillRect(col("orange"), x0, y0, Int(58 * hype.fever), 3)
        }
        y = 101
        if saveT > 0 && (saveT > 2 || Int(t * 8) % 2 == 1) {
            drawText(s, "SAVE \(Int(saveT.rounded(.up)))", 258, y, "mint", shadow: nil)
            y += 10
        }
        if kick[0] || kick[1] { drawText(s, "KICKBACK", 258, y, "orange", shadow: nil); y += 10 }
        if tailOn { drawText(s, "TAIL POST", 258, y, "lavender", shadow: nil); y += 10 }
        if tilt > 0.55 && !tilted {
            drawText(s, "DANGER", 258, y, Int(t * 8) % 2 == 1 ? "red" : "orange", shadow: nil)
            y += 10
        }
        if tilted { drawText(s, "TILT!", 258, y, "red", shadow: nil) }
        if waitingPlunger {
            s.fillRect(col("darkgray"), 306, 150, 6, 40)
            let h = Int(40 * pull)
            s.fillRect(col(pull > 0.9 ? "red" : "yellow"), 306, 190 - h, 6, h)
            if Int(t * 2) % 2 == 1 || pull > 0 {
                drawText(s, "PULL", 258, 162, "yellow", shadow: nil)
                drawText(s, "AND", 258, 171, "yellow", shadow: nil)
                drawText(s, "LET GO", 258, 180, "yellow", shadow: nil)
            }
        }
        if let bs = boss, ["fight", "idle", "enter"].contains(bs.state) {
            bossBar(s, bs.name, Double(bs.hp), Double(bs.maxhp), t, y: 1, x: PP_TX0 + 2, w: PP_TX1 - PP_TX0 - 4)
        }
    }

    private func drawIntro(_ s: Surface, _ t: Double) {
        let cx = 160
        if st.kind == "boss", let b = st.boss {
            if Int(t * 4) % 2 == 1 {
                for x in stride(from: PP_TX0, to: PP_TX1, by: 20) {
                    let X = Double(x)
                    s.polygon(col("red"), [(X, 108), (X + 10, 108), (X + 20, 116), (X + 10, 116)])
                    s.polygon(col("red"), [(X, 152), (X + 10, 152), (X + 20, 160), (X + 10, 160)])
                }
            }
            panel(s, IRect(PP_TX0 + 4, 118, PP_TX1 - PP_TX0 - 8, 32), fill: "black", border: "red")
            drawText(s, "WARNING!!", cx, 122, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(b.name) - \(b.title)", cx, 139, "white", align: .center, shadow: nil)
            return
        }
        let h = 53 + 9 * max(1, goals.count) + (st.newLine.isEmpty ? 0 : 10) + (st.time > 0 ? 9 : 0)
        let y0 = 70
        panel(s, IRect(PP_TX0 + 2, y0, PP_TX1 - PP_TX0 - 4, h), fill: "ink", border: st.kind == "bonus" ? "yellow" : "peach")
        if st.kind == "bonus" {
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), cx - textWidth(title, 2) / 2 + i * 12, y0 + 6 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            drawText(s, st.name, cx, y0 + 26, "yellow", align: .center)
            let sub = st.bonus == "party" ? "A 3-KITTEN MULTIBALL PARTY!" : "GRAB THE GOLD FISH COINS!"
            drawText(s, sub, cx, y0 + 37, "white", align: .center, shadow: nil)
            drawText(s, "\(Int(st.time)) SECONDS, NO DRAINS!", cx, y0 + 47, "mint", align: .center, shadow: nil)
            return
        }
        drawText(s, "STAGE \(n)", cx, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, tb.name, cx, y0 + 24, "lavender", align: .center, shadow: nil)
        drawText(s, "\"\(st.name)\"", cx, y0 + 33, "peach", align: .center, shadow: nil)
        var y = y0 + 45
        for (g, c) in goals {
            let txt = (PPData.goals[g]?.1 ?? g).replacingOccurrences(of: "{n}", with: g == "score" ? "\(c / 1000)K" : "\(c)")
            drawText(s, txt, cx, y, "white", align: .center, shadow: nil)
            y += 9
        }
        if st.time > 0 {
            drawText(s, "IN \(Int(st.time)) SECONDS!", cx, y, "orange", align: .center, shadow: nil)
            y += 9
        }
        if !st.newLine.isEmpty {
            drawText(s, st.newLine, cx, y + 2, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center, shadow: nil)
        }
    }

    private func drawTally(_ s: Surface, _ t: Double) {
        let h = 34 + tally.count * 11
        let y0 = 76
        panel(s, IRect(PP_TX0 + 6, y0, PP_TX1 - PP_TX0 - 12, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, 160, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() where i <= tallyI {
            let y = y0 + 20 + i * 11
            drawText(s, row.label, PP_TX0 + 12, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", PP_TX1 - 12, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 {
            drawText(s, "PRESS A", 160, y0 + h - 11, "lavender", align: .center, shadow: nil)
        }
    }

    // ---------------------------------------------------------------- carousel
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        s.fill(col("choco"))
        for y in stride(from: 0, to: h, by: 8) {
            for x in stride(from: 0, to: w, by: 8) where (x / 8 + y / 8) % 2 == 1 { s.fillRect(col("brown"), x, y, 8, 8) }
        }
        let cx = w / 2
        PPArt.bumper(s, 22, 30, "orange", Int(t * 3) % 3 == 0 ? 0.1 : 0, t, 0)
        PPArt.bumper(s, 52, 24, "pink", Int(t * 3) % 3 == 1 ? 0.1 : 0, t, 1)
        for i in 0 ..< 3 { s.blit(sprite("pp_fish"), 12 + i * 12, 46) }
        for side in [1.0, -1.0] {
            let f = PPFlipper(Double(cx) - side * 22, Double(h - 12), side, 17)
            let up = (Int(t * 2) % 2 == 0) == (side == 1)
            f.a = up ? -0.4 : 0.5
            PPArt.flipper(s, f, t, fever: false)
        }
        let bx = Double(cx) + sin(t * 2.3) * 20
        let by = Double(h) - 20 - abs(sin(t * 3.1)) * 32
        s.blit(sprite("pp_bell"), Int(bx) - 3, Int(by) - 3)
        PPArt.kiki(s, w - 16, 20, Int(t) % 3 == 0 ? "happy" : "idle", t, sin(t * 2.3), 0.5)
        drawText(s, "MEOW", 4, 3, rainbow(0, t), shadow: "black")
    }
}
