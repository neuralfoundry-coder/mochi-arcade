// ROOFTOP RUN - chase GULLY the fish thief across 200 stages of night-time rooftops (port of games/rooftop_run.py).
// Courses come from the exported stage table (RooftopRunWorld.swift), bosses live in RooftopRunBoss.swift.
import Foundation

private let LIVES_RR = ["easy": 9, "normal": 7, "hard": 5]
private let SPEED_RR = ["easy": 0.9, "normal": 1.0, "hard": 1.1]
private let MAX_LIVES = 9
private let TORA_X = 80.0
private let LIFE_AT = [30000, 80000, 150000, 250000]      // then every 150000

// ----------------------------------------------------------------------------- upgrade cards
let RR_UPGRADES: [Upgrade] = [
    Upgrade(id: "jump2", name: "TWIN LEAP", desc: "JUMP AGAIN|IN MID-AIR", color: "sky", draw: { s, cx, cy, t in
        for i in 0 ..< 2 {
            let y = cy + 3 - i * 6 - Int(abs(sin(t * 4 + Double(i))) * 2)
            s.polygon(col("sky"), [(Double(cx - 4), Double(y + 2)), (Double(cx), Double(y - 2)), (Double(cx + 4), Double(y + 2))])
        }
    }, max: 2),
    Upgrade(id: "spring", name: "SPRING PAWS", desc: "JUMP|HIGHER", color: "lime", draw: { s, cx, cy, t in
        let h = 3 + Int(abs(sin(t * 5)) * 3)
        for i in 0 ..< 4 { s.fillRect(col("lime"), cx - 4, cy + 4 - i * h / 2, 9, 1) }
        s.fillRect(col("orange"), cx - 3, cy - 4 - h, 7, 3)
    }, max: 3),
    Upgrade(id: "magnet", name: "FISH BELL", desc: "PULLS FISH|TO YOU", color: "yellow", draw: { s, cx, cy, t in
        rrDrawCapIcon(s, 0, cx, cy, t)
    }, max: 3),
    Upgrade(id: "fur", name: "THICK FUR", desc: "SHRUGS OFF|ONE HIT|EACH STAGE", color: "peach", draw: { s, cx, cy, _ in
        s.circle(col("peach"), cx, cy, 6, width: 2)
        s.circle(col("orange"), cx, cy, 3)
    }, max: 2),
    Upgrade(id: "save", name: "SAFETY TAIL", desc: "BOUNCES YOU|OUT OF ONE|FALL A STAGE", color: "mint", draw: { s, cx, cy, t in
        var i = -6
        while i <= 6 { s.fillRect(col("lime"), cx + i, cy + 4, 2, 1); i += 3 }
        s.blit(sprite("rr_head"), cx - 4, cy - 6 - Int(abs(sin(t * 5)) * 3))
    }, max: 2),
    Upgrade(id: "glide", name: "TAIL GLIDE", desc: "HOLD JUMP|TO FLOAT|DOWN SLOWLY", color: "lavender", draw: { s, cx, cy, _ in
        s.polygon(col("lavender"), [(Double(cx - 7), Double(cy)), (Double(cx), Double(cy - 5)), (Double(cx + 7), Double(cy))])
        s.fillRect(col("white"), cx, cy, 1, 5)
    }, max: 2),
    Upgrade(id: "pounce", name: "POWER POUNCE", desc: "POUNCES|SHAKE THE ROOF|+ BOSS DAMAGE", color: "orange", draw: { s, cx, cy, t in
        s.fillRect(col("orange"), cx - 1, cy - 6, 3, 7)
        s.polygon(col("orange"), [(Double(cx - 4), Double(cy)), (Double(cx + 4), Double(cy)), (Double(cx), Double(cy + 4))])
        for dx in [-6, 6] { s.fillRect(col("yellow"), cx + dx, cy + 4 - Int(t * 10) % 3, 1, 2) }
    }, max: 2),
    Upgrade(id: "life", name: "NINE LIVES", desc: "+1 LIFE|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
    Upgrade(id: "luck", name: "LUCKY CHARM", desc: "MORE|CAPSULES AND|JACKPOTS", color: "orange", draw: { s, cx, cy, t in
        rrDrawCapIcon(s, 5, cx, cy, t)
    }, max: 3),
    Upgrade(id: "fever", name: "PURR FEVER", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "yellow", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
    Upgrade(id: "chase", name: "HOT PURSUIT", desc: "START EVERY|STAGE CLOSER|TO GULLY", color: "pink", draw: { s, cx, cy, _ in
        s.blit(sprite("rr_feather"), cx - 4, cy - 4)
    }, max: 3),
]

// ----------------------------------------------------------------------------- the game
final class RooftopRun: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["JUMP   JUMP (HOLD = HIGHER)", "SLIDE  SLIDE - IN THE AIR: POUNCE",
                            "PAD    { EASE OFF  } SPRINT (OPTIONAL)"]
    static let helpSkip = 3
    override var music: String? { song() }
    override var buttons: [Action: String] { [.a: "JUMP", .b: "SLIDE"] }
    override var buttonOrder: [Action] { [.a, .b] }
    override var fourWay: Bool { false }

    var lives: Int
    let speedMul: Double
    var levels: [String: Int] = [:]
    var lifeI = 0
    var fishTotal = 0           // whole run: every 100 fish = +1 life
    var feathers = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    var wasFever = false
    var skyCache: [Int: (Surface, Surface, Surface)] = [:]
    // stage
    var n = 1
    var st: RRStage = RRData.stages[0]
    var tier = 0
    var theme: RRTheme = RRData.themes[0]
    var course: RRCourse!
    var roofX: [Double] = []
    var speedBase = 90.0, speed = 90.0
    var body = RRBody(60, 150)
    var cam = 0.0
    var safe: (Double, RRRoof?) = (60, nil)
    var stime = 0.0
    var chase = 35.0
    var fishGot = 0, goldGot = 0, fishN = 0
    var hits = 0, falls = 0, stageCombo = 0
    var invuln = 0.0, hurtT = 0.0, ready = 0.0
    var quip = ""
    var shield = 0, saves = 0
    var timers: [String: Double] = ["magnet": 0, "umbrella": 0, "catnip": 0]
    var gully: (state: String, x: Double, y: Double, t: Double) = ("chase", 0, 0, 0)
    var feather = false
    var flashFeather: (x: Double, y: Double, t: Double)?
    var trail: [(x: Double, y: Double, life: Double)] = []
    var boss: RRBoss?
    var lucky = false
    var state = "intro"
    var stateT = 0.0, introLen = 2.4
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0
    var purr = false
    var ctrlPrev = (false, false)
    var sky: (Surface, Surface, Surface) = (Surface(1, 1), Surface(1, 1), Surface(1, 1))

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES_RR[d] ?? 7
        speedMul = SPEED_RR[d] ?? 1.0
        super.init(app, info, opt)
        hype.comboY = 26
        let start = max(1, min(STAGES, optInt("level", optInt("start", 1))))
        startStage(start)
        if start > 10 {         // starting from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (start - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func factorPts(_ pts: Int) -> Int { pts * (10 + tier) / 10 }
    @discardableResult
    func scoreAt(_ pts: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int { add(factorPts(pts), x, y, c) }
    func sfx(_ name: String) { app.audio.play(name) }
    func song() -> String {
        if st.kind == "boss" { return "boss" }
        if st.kind == "bonus" { return "bonus" }
        return tier < 10 ? "rr_run" : "rr_chase"
    }
    func feverGain() -> Double { 0.022 * (1 + 0.35 * Double(lv("fever"))) }

    /// Index of the last roof starting at or before x (bisect_right - 1).
    func roofIndex(_ x: Double) -> Int {
        var lo = 0, hi = roofX.count
        while lo < hi { let m = (lo + hi) / 2; if x < roofX[m] { hi = m } else { lo = m + 1 } }
        return lo - 1
    }

    /// Top of the (intact) roof under world x, or nil over a gap.
    func roofY(_ x: Double) -> Double? {
        let i = roofIndex(x)
        if i >= 0 {
            let r = course.roofs[i]
            if r.x <= x && x < r.x + r.w && !r.broken { return r.y }
        }
        return nil
    }

    func nextRoof(_ x: Double) -> RRRoof? {
        let i = roofIndex(x) + 1
        return i < course.roofs.count ? course.roofs[i] : nil
    }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        n = num
        st = RRData.stages[num - 1]
        tier = st.tier
        theme = RRData.themes[min(tier, RRData.themes.count - 1)]
        reached(num)
        course = RRCourse(st)
        roofX = course.roofs.map { $0.x }
        speedBase = st.speed * speedMul
        speed = speedBase
        body = RRBody(60, 150)
        body.y = roofY(60) ?? 150
        body.ground = course.roofs[max(0, roofIndex(60))]
        applyUpgrades()
        cam = body.x - TORA_X
        safe = (60, body.ground as? RRRoof)
        stime = 0
        chase = min(100, 35 + 15 * Double(lv("chase")))
        fishGot = 0; goldGot = 0
        fishN = course.fish.count
        hits = 0; falls = 0; stageCombo = 0
        invuln = 0; hurtT = 0; ready = 0
        quip = ""
        shield = lv("fur")
        saves = lv("save")
        timers = ["magnet": 0, "umbrella": 0, "catnip": 0]
        gully = ("chase", 0, 0, 0)
        feather = false
        flashFeather = nil
        trail = []
        boss = st.kind == "boss" ? st.boss.map { RRBoss(self, $0) } : nil
        for hz in course.haz where hz.k == "q" {    // flying pigeons well above the roof bob up and down
            let g = roofY(hz.x)
            hz.b = (g == nil || g! - hz.y > 20) ? 1 : 0
        }
        lucky = st.kind == "normal" && hype.lucky(0.03 + 0.01 * Double(lv("luck")))
        if lucky, let g = course.gold.randomElement() { g.rainbow = true }    // one golden fish is a RAINBOW FISH
        for c in course.caps {                      // rare capsules: milk (+1 life) and the gold bell
            let roll = Double.random(in: 0 ..< 1)
            if roll < 0.02 + 0.01 * Double(lv("luck")) { c.k = 5 } else if roll < 0.07 { c.k = 4 }
        }
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.0 : 2.4
        tally = []
        ctrlPrev = (false, false)
        if let c = skyCache[tier] {
            sky = c
        } else {
            sky = (rrMakeSky(tier), rrMakeSkyline(tier, true), rrMakeSkyline(tier, false))
            skyCache[tier] = sky
        }
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
        app.audio.music(song())
        sfx(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    func applyUpgrades() {
        body.airMax = lv("jump2")
        body.jv = 1 + 0.07 * Double(lv("spring"))
        body.glide = lv("glide")
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = RR_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id]!)", color: u.color, dur: 1.2, scale: 1)
        }
        switch id {
        case "life": lives = min(MAX_LIVES, lives + 1); sfx("extra")
        case "fur": shield += 1
        case "save": saves += 1
        case "chase": chase = min(100, chase + 15)
        default: break
        }
        applyUpgrades()
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
                ctrlPrev = (app.input.down(.a, .up), app.input.down(.down, .b))
                hype.banner("GO!", color: "lime", dur: 0.7, scale: 2)
            }
        case "play":
            play(dt)
        case "fall":
            body.vy += 900 * dt
            body.y += body.vy * dt
            if stateT > 1.0 { afterFall() }
        case "finish":
            finishRun(dt)
        case "clear":
            finishRun(dt)
            if stateT > 2.2 { beginTally() }
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(RR_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        default: break
        }
        updateWorld(dt)
    }

    func readCtrl() -> RRCtrl {
        let inp = app.input
        let jump = inp.down(.a, .up), down = inp.down(.down, .b)
        let (pj, pd) = ctrlPrev
        ctrlPrev = (jump, down)
        let lr = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        return RRCtrl(jumpHit: jump && !pj, jump: jump, downHit: down && !pd, down: down, lr: lr)
    }

    func view() -> RRView { RRView(course, body.x - 60, body.x + 280, speed, stime) }

    func play(_ dt: Double) {
        let b = body
        stime += dt
        for k in Array(timers.keys) { timers[k] = max(0, timers[k]! - dt) }
        invuln = max(0, invuln - dt)
        hurtT = max(0, hurtT - dt)
        ready = max(0, ready - dt)
        for m in course.lifts { m.y = m.at(stime) }
        for ln in course.lines { ln.y = ln.at(stime) }
        speed = speedBase * (boss?.slow() ?? 1.0) * (ready > 0 ? 0 : 1)
        b.boost = timers["catnip"]! > 0 ? 1.25 : 1.0
        b.glide = max(lv("glide"), timers["umbrella"]! > 0 ? 1 : 0)
        let c = readCtrl()
        let prevY = b.y
        for e in rrStep(b, c, dt, view()) { onEvent(e) }
        cam = b.x - TORA_X
        if st.loop > 0 && b.x > Double(st.loop + 120) { wrap(Double(st.loop)) }
        // skylights crack under paws
        if let g = b.ground as? RRRoof, g.glass, g.crack < 0 { g.crack = 0.7; sfx("tin") }
        for r in course.roofs where r.glass && r.crack >= 0 && !r.broken {
            r.crack -= dt
            if r.crack <= 0 { shatter(r) }
        }
        // blocked by a wall: Gully gets away a little
        if b.blocked != nil && b.ground != nil { chaseAdd(-6 * dt) }
        collect(b)
        hazards(dt, b, prevY)
        if let bo = boss {
            bo.update(dt)
            bossContact(b)
        }
        if state != "play" { return }
        // off the bottom of the screen
        if b.y > Double(H + 10) && b.wire == nil {
            if saves > 0 && st.kind != "bonus" {
                saves -= 1
                b.y = Double(H + 4)
                b.vy = -470
                b.hold = false
                b.pounce = false
                floats.add(b.x, Double(H - 30), "SAVED!", "lime")
                sfx("bubble")
                parts.burst(b.x, Double(H - 4), 12, ["lime", "white"], 60, 0.5)
            } else {
                fell()
                return
            }
        }
        if st.kind != "boss" && b.x >= course.finish { crossFinish() }
        updateGully(dt)
        stageCombo = max(stageCombo, hype.combo)
        if hype.feverOn && !wasFever {
            hype.feverT += 2 * Double(lv("fever"))
            app.audio.music("fever")
        } else if wasFever && !hype.feverOn {
            app.audio.music(song())
        }
        wasFever = hype.feverOn
        checkLife()
        if timers["catnip"]! > 0 || hype.feverOn { trail.append((b.x, b.y, 0.3)) }
    }

    func updateWorld(_ dt: Double) {
        for i in trail.indices { trail[i].life -= dt }
        trail.removeAll { $0.life <= 0 }
        for p in course.pads { p.cd = max(0, p.cd - dt) }
        for bx in course.boxes { bx.flash = max(0, bx.flash - dt) }
    }

    /// Boss arenas repeat: jump Tora (and everything that follows her) back one block.
    func wrap(_ L: Double) {
        let b = body
        b.x -= L
        cam -= L
        safe = (safe.0 - L, nil)
        if let bo = boss {
            bo.wx -= L
            for s in bo.shots { s.x -= L }
        }
        for i in parts.p.indices { parts.p[i].x -= L }
        for i in floats.items.indices { floats.items[i].x -= L }
        trail = []
        course.resetConsumables(cam - 20, cam + Double(W) + 20)
        if let g = b.ground, g.solid == "R" { b.ground = course.roofs[max(0, roofIndex(b.x))] }
    }

    func chaseAdd(_ v: Double) { chase = max(0, min(100, chase + v)) }

    func onEvent(_ e: RREvent) {
        let b = body
        switch e.k {
        case "jump":
            sfx("jump")
        case "airjump":
            sfx("jump")
            parts.burst(b.x, b.y, 6, ["white", "sky"], 40, 0.3)
        case "kick":
            sfx("tin")
            hype.hit(1, fever: feverGain())
            chaseAdd(2)
            scoreAt(50)
            parts.burst(b.x + 5, b.y - 6, 6, ["white", "gray"], 40, 0.3)
            floats.add(b.x, b.y - 24, "KICK!", "mint")
        case "bounce":
            sfx("bubble")
            hype.hit(1, fever: feverGain())
            chaseAdd(1)
            scoreAt(30)
            parts.burst(b.x, b.y, 5, ["cream", "white"], 30, 0.3)
        case "grab":
            sfx("hold")
            scoreAt(50)
            parts.burst(b.x, e.wire?.y ?? b.y, 8, ["yellow", "white"], 40, 0.3)
        case "pad":
            guard let p = e.pad else { return }
            p.cd = 1.0
            sfx("powerup")
            hype.hit(1, fever: feverGain())
            parts.burst(p.x, p.y - 4, 20, ["red", "yellow", "white", "hotpink"], 90, 0.6)
            scoreAt(100)
        case "pounce":
            sfx("rotate")
        case "updraft":
            sfx("bubble")
        case "bonk":
            sfx("tin")
        case "land":
            guard let solid = e.solid else { return }
            let roof = solid as? RRRoof
            if let r = roof, !r.glass { safe = (max(r.x + 16, min(b.x, r.x + r.w - 70)), r) }
            if e.pounced {
                sfx("lock")
                app.shake(2, 0.12)
                parts.burst(b.x, b.y, 10, ["white", "gray", "cream"], 60, 0.35)
                if lv("pounce") > 0 { shockwave(b.x, b.y) }
            } else if e.impact > 260 {
                parts.burst(b.x, b.y, 4, ["gray", "white"], 25, 0.25)
            }
            if let box = solid as? RRBox, e.pounced, box.k == "X" || box.k == "C" {
                smash(box)
            } else if let r = roof, r.glass {
                if e.pounced {
                    shatter(r)
                } else if e.impact > 150 && (r.crack < 0 || r.crack > 0.2) {     // a hard landing cracks it fast
                    r.crack = 0.2
                    sfx("tin")
                }
            }
        default: break
        }
    }

    func smash(_ box: RRBox) {
        let b = body
        box.alive = false
        sfx("brick")
        hype.hit(1, fever: feverGain())
        scoreAt(100, box.x + box.w / 2, box.y - 6)
        parts.burst(box.x + box.w / 2, box.y + box.h / 2, 14, ["brown", "peach", "choco"], 70, 0.5)
        b.vy = -220
        b.ground = nil
        if box.k == "C" {
            fishN += 5
            for i in 0 ..< 5 {
                course.fish.append(RRFish(box.x + box.w / 2 + Double(i - 2) * 9, box.y - 18 - Double(i % 2) * 8))
            }
            course.sortFish()
            floats.add(box.x + box.w / 2, box.y - 30, "FISH CRATE!", "sky")
        }
    }

    func shatter(_ r: RRRoof) {
        r.broken = true
        r.crack = -1
        sfx("brick")
        parts.burst(r.x + r.w / 2, r.y + 2, 16, ["sky", "white", "teal"], 70, 0.6)
        if body.ground === r { body.ground = nil; body.vy = 0 }
    }

    func shockwave(_ x: Double, _ y: Double) {
        parts.burst(x, y - 2, 16, ["yellow", "orange", "white"], 90, 0.4)
        for hz in course.haz where hz.alive && (hz.k == "p" || hz.k == "q") &&
            abs(hz.x - x) < 34 + 10 * Double(lv("pounce")) && abs(hz.y - y) < 40 {
            defeat(hz, pounce: true)
        }
        for bx in course.boxes where bx.alive && (bx.k == "X" || bx.k == "C") && abs(bx.x + bx.w / 2 - x) < 30 &&
            abs(bx.y + bx.h - y) < 4 {
            smash(bx)
        }
    }

    // ---------------------------------------------------------------- pickups
    func collect(_ b: RRBody) {
        let box = b.box
        let cx = b.x, cy = b.y - box.h / 2
        let mag = 22 * Double(lv("magnet")) + (timers["magnet"]! > 0 ? 60 : 0) + (hype.feverOn ? 20 : 0)
        var got = 0
        var i = course.fishFrom(b.x - 80 - mag)
        while i < course.fish.count {
            let f = course.fish[i]
            i += 1
            if f.x > b.x + 60 + mag { break }
            if f.got { continue }
            if mag > 0 && abs(f.x - cx) < mag && abs(f.y - cy) < mag {
                let d = max(1e-9, hypot(cx - f.x, cy - f.y))
                let stepv = min(d, 300.0 / 60)
                f.x += (cx - f.x) / d * stepv
                f.y += (cy - f.y) / d * stepv
            }
            if box.x - 4 <= f.x && f.x <= box.x + box.w + 4 && box.y - 4 <= f.y && f.y <= box.y + box.h + 4 {
                f.got = true
                got += 1
                fishGot += 1
                fishTotal += 1
                hype.hit(1, fever: feverGain())
                chaseAdd(1.2)
                add(factorPts(20) + hype.comboBonus(1))
                parts.sparkle(f.x, f.y, "sky")
                if fishTotal % 100 == 0 { extraLife("\(fishTotal) FISH!") }
            }
        }
        if got > 0 { sfx("eat") }
        if mag > 0 { course.sortFish() }
        for g in course.gold where !g.got && box.x - 5 <= g.x && g.x <= box.x + box.w + 5 && box.y - 5 <= g.y && g.y <= box.y + box.h + 5 {
            g.got = true
            goldGot += 1
            chaseAdd(8)
            hype.hit(3, fever: feverGain() * 3)
            sfx("coin")
            parts.burst(g.x, g.y, 14, ["yellow", "orange", "white"], 60, 0.5)
            if g.rainbow { hype.jackpot(factorPts(8000), sub: "RAINBOW FISH!") } else { scoreAt(500, g.x, g.y - 8) }
        }
        for c in course.caps where !c.got && box.x - 6 <= c.x && c.x <= box.x + box.w + 6 && box.y - 8 <= c.y && c.y <= box.y + box.h + 8 {
            c.got = true
            power(c.k, c.x, c.y)
        }
    }

    func power(_ k: Int, _ x: Double, _ y: Double) {
        sfx("powerup")
        chaseAdd(3)
        floats.add(x, y - 10, RR_CAP_NAMES[k], RR_CAP_COLORS[k])
        switch k {
        case 0: timers["magnet"] = 10
        case 1: timers["umbrella"] = 10
        case 2:
            timers["catnip"] = 6
            hype.banner("CATNIP RUSH!", color: "lime", dur: 1.0, scale: 1)
        case 3: shield += 1
        case 4: extraLife("MILK!")
        case 5: hype.jackpot(factorPts(5000))
        default: break
        }
        scoreAt(100)
    }

    func extraLife(_ why: String) {
        if lives < MAX_LIVES {
            lives += 1
            hype.banner("+1 LIFE!", why, color: "pink", dur: 1.3, sound: "extra")
            hype.shower(14, "hearts")
        } else {
            scoreAt(2000)
            hype.banner("NINE LIVES!", "+2000", color: "pink", dur: 1.0, scale: 1, sound: "coin")
        }
    }

    func checkLife() {
        let target = lifeI < LIFE_AT.count ? LIFE_AT[lifeI] : LIFE_AT.last! + 150000 * (lifeI - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            extraLife("\(target) POINTS")
        }
    }

    // ---------------------------------------------------------------- hazards
    func hazards(_ dt: Double, _ b: RRBody, _ prevY: Double) {
        let box = b.box
        let catnip = timers["catnip"]! > 0
        let w = Double(W)
        for hz in course.haz {
            let k = hz.k
            if hz.x < cam - 80 || hz.x > cam + w + 300 {
                if !(k == "q" && hz.state == 1) { continue }
            }
            hz.t += dt
            if !hz.alive {
                if k == "p" || k == "q" { hz.x += 60 * dt; hz.y -= 80 * dt }
                continue
            }
            switch k {
            case "p":
                hz.x += Double(hz.dir) * 18 * dt
                if hz.x < Double(hz.a) { hz.x = Double(hz.a); hz.dir = 1 } else if hz.x > Double(hz.b) { hz.x = Double(hz.b); hz.dir = -1 }
            case "q":
                if hz.state == 0 && hz.x < cam + w + 30 { hz.state = 1 }
                if hz.state == 1 {
                    hz.x -= 46 * dt
                    if hz.b != 0 { hz.y = hz.y0 + sin(hz.t * 4) * 3 }   // high flyers bob, low ones skim the roof
                }
            case "i":
                if hz.state == 0 && b.x > hz.x - 120 {
                    hz.state = 3
                    hz.t = 0
                } else if hz.state == 3 && hz.t > 0.3 {
                    hz.state = 1
                    hz.y = Double(hz.a + 10)
                    hz.vy = 0
                } else if hz.state == 1 {
                    hz.vy += 900 * dt
                    hz.y += hz.vy * dt
                    if hz.y >= hz.y0 {
                        hz.y = hz.y0
                        hz.state = 2
                        hz.t = 0
                        sfx("tin")
                        parts.burst(hz.x, hz.y - 2, 6, ["sky", "white"], 40, 0.3)
                    }
                } else if hz.state == 2 && hz.t > 1.4 {
                    hz.alive = false
                }
            case "d":
                if hz.state == 0 && b.x > hz.x - 260 {
                    hz.state = 1
                    hz.t = 0
                    sfx("warning")
                } else if hz.state == 1 && hz.t > 0.75 {
                    hz.state = 2
                    hz.x = cam + w + 12
                } else if hz.state == 2 {
                    hz.x += (speed - 230) * dt
                    if hz.x < cam - 30 { hz.alive = false }
                }
            case "z":
                if hz.state == 0 && b.x > hz.x - 120 {
                    hz.state = 1
                    hz.t = 0
                } else if hz.state == 1 && hz.t > 0.55 {
                    hz.state = 2
                    hz.t = 0
                    sfx("boom")
                    hype.flash("white", 0.1)
                    app.shake(2, 0.15)
                } else if hz.state == 2 && hz.t > 0.5 {
                    hz.state = 3
                    hz.alive = false
                }
            default: break
            }
            guard let r = hz.rect(stime), box.hits(r) else { continue }
            if k == "p" || k == "q" {
                if catnip || (b.vy > 0 && prevY <= r.y + 4) || (k == "p" && b.slide) {
                    defeat(hz, pounce: b.pounce)
                    if !catnip && !b.slide {
                        b.vy = app.input.down(.a, .up) ? -320 : -260
                        b.hold = true
                        b.pounce = false
                        b.jumps = b.airMax
                    }
                    continue
                }
            }
            if k == "s" && timers["umbrella"]! > 0 { continue }
            if catnip && k != "s" { continue }
            hurt(k == "s" ? "SPLASH!" : "OUCH!")
        }
    }

    func defeat(_ hz: RRHaz, pounce: Bool = false) {
        hz.alive = false
        hz.t = 0
        sfx("pop")
        hype.hit(1, fever: feverGain() * 2)
        chaseAdd(4)
        scoreAt(200 * (pounce ? 2 : 1), hz.x, hz.y - 16, pounce ? "orange" : "yellow")
        parts.burst(hz.x, hz.y - 4, 10, ["gray", "white", "lavender"], 60, 0.4)
        if pounce { floats.add(hz.x, hz.y - 26, "POUNCE!", "orange") }
    }

    func hurt(_ word: String = "OUCH!") {
        if invuln > 0 || state != "play" { return }
        let b = body
        if shield > 0 {
            shield -= 1
            invuln = 1.0
            sfx("tin")
            floats.add(b.x, b.y - 24, "FUR SHIELD!", "peach")
            parts.burst(b.x, b.y - 7, 14, ["peach", "orange", "white"], 60, 0.4)
            return
        }
        hits += 1
        lives -= 1
        invuln = 1.6
        hurtT = 0.45
        chaseAdd(-15)
        hype.breakCombo()
        sfx("hurt")
        app.shake(3, 0.3)
        hype.hitstop(0.08)
        floats.add(b.x, b.y - 24, word, "red")
        parts.burst(b.x, b.y - 7, 10, ["red", "white", "orange"], 60, 0.4)
        if lives <= 0 { gameOver() }
    }

    func fell() {
        if st.kind == "bonus" {
            floats.add(body.x, Double(H - 40), "BOING! AGAIN!", "lime")
            respawn()
            return
        }
        state = "fall"
        stateT = 0
        body.vy = -260
        sfx("die")
        hype.breakCombo()
    }

    func afterFall() {
        falls += 1
        lives -= 1
        chaseAdd(-20)
        if lives <= 0 { gameOver(); return }
        respawn()
        state = "play"
        stateT = 0
        hype.banner("MEOW!", "\(lives) LIVES LEFT", color: "pink", dur: 1.0, scale: 1)
    }

    func respawn() {
        let b = body
        var (x, roof) = safe
        if roof == nil || roof!.broken {
            var i = max(0, roofIndex(x))
            while i > 0 && (course.roofs[i].glass || course.roofs[i].broken) { i -= 1 }
            roof = course.roofs[i]
            x = roof!.x + 16
        }
        b.x = x
        b.y = roof!.y
        b.vy = 0
        b.ground = roof
        b.wire = nil
        b.pounce = false; b.pad = false; b.slide = false; b.cling = false
        b.jumps = b.airMax
        cam = b.x - TORA_X
        invuln = 2.0
        ready = 0.7
    }

    func gameOver() {
        lives = 0
        state = "over"
        hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
        sfx("gameover")
        endGame(false, "STAGE \(n)", delay: 2.6)
    }

    // ---------------------------------------------------------------- Gully and the finish
    func gullyHover() -> Double { 26 + (100 - chase) * 0.75 }

    func updateGully(_ dt: Double) {
        gully.t += dt
        if st.kind != "normal" { return }
        let fin = course.finish
        let gy = roofY(fin - 24) ?? 150
        switch gully.state {
        case "chase":
            gully.x = cam + 330 - chase * 1.1
            gully.y = 34 + sin(gully.t * 3) * 4
            if body.x > fin - 330 { gully.state = "perch"; gully.t = 0 }
        case "perch":
            let tx = fin - 24, ty = gy - gullyHover() + sin(gully.t * 4) * 3
            let k = min(1, dt * 4)
            gully.x += (tx - gully.x) * k
            gully.y += (ty - gully.y) * k
            if !feather && body.box.hits(RRRect(gully.x - 8, gully.y - 6, 16, 12)) { grabFeather() }
        case "flee", "plucked":
            gully.x += (speed + 160) * dt
            gully.y -= 70 * dt
        default: break
        }
    }

    func grabFeather() {
        feather = true
        feathers += 1
        gully.state = "plucked"
        flashFeather = (gully.x, gully.y, 0)
        sfx("bonus")
        hype.hit(5, fever: 0.2)
        hype.slowmo(0.35, 0.6)
        hype.flash("white", 0.15)
        app.shake(3, 0.25)
        if feathers % 10 == 0 {             // a whole fan of Gully's feathers
            hype.jackpot(factorPts(20000), sub: "\(feathers) FEATHERS!")
        } else if chase >= 99.5 {
            hype.jackpot(factorPts(6000), sub: "PERFECT CHASE!")
        } else {
            hype.banner("TAIL FEATHER!", "SQUAAAWK!", color: "yellow", dur: 1.5)
        }
        hype.shower(24, "stars")
        parts.burst(gully.x, gully.y, 18, ["white", "gray", "yellow"], 80, 0.7)
    }

    func crossFinish() {
        state = "finish"
        stateT = 0
        if st.kind == "normal" && !feather {
            gully.state = "flee"
            floats.add(course.finish, (roofY(course.finish) ?? 150) - 70, "SQUAWK HA HA!", "white")
        }
        sfx("win")
        if hype.feverOn { hype.feverT = 0 }
        app.audio.music(nil)
        wasFever = false
        hype.banner(st.kind == "normal" ? "FINISH!" : "GOAL!", color: "mint", dur: 1.3)
        hype.shower(30, "confetti")
    }

    /// After the line (or a beaten boss): Tora skids to a stop and celebrates.
    func finishRun(_ dt: Double) {
        let b = body
        let k = state == "clear" ? max(0, 1 - stateT / 1.6) : max(0, 1 - stateT / 0.9)
        speed = speedBase * k
        boss?.update(dt)
        _ = rrStep(b, RRCtrl(), dt, view())
        if b.y > Double(H + 10) { respawn() }       // never fall after the line
        cam = b.x - TORA_X
        if st.loop > 0 && b.x > Double(st.loop + 120) { wrap(Double(st.loop)) }
        updateGully(dt)
        flashFeather?.t += dt
        if state == "finish" && stateT > 1.7 { beginTally() }
    }

    // ---------------------------------------------------------------- bosses
    func bossLanded() { sfx("bubble") }

    func bossContact(_ b: RRBody) {
        guard let bo = boss else { return }
        let box = b.box
        if bo.state != "dead" && bo.hurts(box) && timers["catnip"]! <= 0 { hurt() }
        let res = bo.check(b, box)
        switch res {
        case "stomp", "hit":
            let stomped = res == "stomp"
            let dmg = 1 + (b.pounce && lv("pounce") > 0 ? 1 : 0)
            b.vy = -330
            b.hold = true
            b.pounce = false
            b.ground = nil
            b.jumps = b.airMax
            sfx("boom")
            hype.hitstop(0.1)
            hype.flash("white", 0.12)
            app.shake(4, 0.25)
            hype.hit(2, fever: feverGain() * 3)
            scoreAt(1000, bo.wx, bo.wy - 30, "orange")
            parts.burst(bo.wx, bo.wy - 10, 20, ["white", "yellow", "orange"], 90, 0.5)
            floats.add(bo.wx, bo.wy - 44, stomped ? "STOMP!" : "BONK!", "yellow")
            if bo.takeHit(dmg) { bossDefeated() }
        case "bump":
            b.vy = -180
            b.ground = nil
            b.x -= 6
            sfx("tin")
            floats.add(b.x, b.y - 24, "FROM ABOVE!", "yellow")
        case "hurt":
            hurt()
        default: break
        }
    }

    func bossDefeated() {
        sfx("bossdown")
        hype.banner("BOSS DOWN!", boss?.name, dur: 2.2, rainbow: true, scale: 2)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        app.shake(6, 0.6)
        scoreAt(15000, body.x + 40, 80)
        state = "clear"
        stateT = 0
        hype.slowmo(0.3, 1.2)
        app.audio.music(nil)
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
    }

    // ---------------------------------------------------------------- tally
    func beginTally() {
        let f = factorPts
        var rows: [(String, Int)] = []
        let clean = hits + falls == 0
        if st.kind == "normal" {
            rows.append(("COURSE CLEAR", f(1000)))
            rows.append(("FISH \(fishGot)/\(fishN)", f(fishGot * 20)))
            if fishGot >= fishN { rows.append(("ALL FISH!", f(5000))) }
            rows.append((feather ? "TAIL FEATHER #\(feathers)" : "TAIL FEATHER", feather ? f(5000) : 0))
            let par = Double(st.len) / max(1, speedBase) * 1.15 + 3
            rows.append(("TIME BONUS", f(max(0, Int(par - stime)) * 100)))
            rows.append(("NO HIT", clean ? f(3000) : 0))
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", f(10000 + 2000 * tier)))
            rows.append(("NO HIT", clean ? f(8000) : 0))
        } else {
            rows.append(("FISH \(fishGot)/\(fishN)", f(fishGot * 50)))
            rows.append(("GOLDEN x\(goldGot)", f(goldGot * 500)))
            rows.append(("ALL FISH!", fishGot >= fishN ? f(10000) : 0))
        }
        rows.append(("BEST COMBO \(stageCombo)", f(stageCombo * 30)))
        tally = rows.map { (label: $0.0, v: $0.1, shown: 0.0) }
        if st.kind == "boss" {
            quip = n >= STAGES ? "MY FISH! FINALLY! *MUNCH*" : "AND STAY DOWN!"
        } else if st.kind == "bonus" {
            quip = "BURP. I MEAN... MEOW."
        } else if feather {
            quip = clean ? "PURRFECT. THAT'S HOW IT'S DONE." : "GOT A FEATHER! THE FISH IS NEXT."
        } else {
            quip = chase < 40 ? "MORE FISH = CLOSER TO GULLY!" : "HE'S GETTING AWAY... NOT FOR LONG!"
        }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        purr = st.kind == "normal" && feather && clean      // shown once the rows are counted
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
                sfx("coin")
                checkLife()
                return
            }
            let v = Double(tally[tallyI].v)
            tally[tallyI].shown = min(v, tally[tallyI].shown + max(1, v * dt / 0.4))
            if tally[tallyI].shown >= v {
                if tally[tallyI].v > 0 { add(tally[tallyI].v); sfx("coin"); checkLife() }
                tallyI += 1
            }
        } else {
            if purr {
                purr = false
                hype.banner("PURRFECT!", "NO HITS + THE FEATHER", dur: 1.6, rainbow: true, sound: "fever")
                hype.shower(40, "stars")
                tallyWait = -0.6
            }
            tallyWait += dt
            if tallyWait > 1.6 || skip { finishStage() }
        }
    }

    func finishStage() {
        hype.banners.removeAll()            // the next stage card starts clean (pick banners come after this)
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "TORA GOT HER FISH BACK!", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "FISHY TREAT!"
            state = "pick"
        } else {
            startStage(n + 1)
        }
    }

    // ---------------------------------------------------------------- drawing
    override func render(_ s: Surface) {
        let t = self.t
        let th = theme
        let icam = Int(cam)
        s.blit(sky.0, 0, 0)
        drawSkyFx(s, t)
        for (layer, k) in [(sky.1, 0.12), (sky.2, 0.3)] {
            let off = rrMod(Int(cam * k), W)
            s.blit(layer, -off, 0)
            s.blit(layer, W - off, 0)
        }
        let c = course!
        let x0 = cam - 40, x1 = cam + Double(W) + 40
        for z in c.winds { rrDrawWind(s, z, cam, t) }
        for wr in c.wires where wr.x1 > x0 && wr.x0 < x1 { rrDrawWire(s, wr, cam, stime) }
        for r in c.roofs where r.x + r.w > x0 && r.x < x1 { rrDrawRoof(s, r, icam, th, t) }
        for v in c.vents { rrDrawVent(s, v, cam, t) }
        for p in c.pads { rrDrawPad(s, p, cam, t) }
        for bx in c.boxes where bx.x + bx.w > x0 && bx.x < x1 { rrDrawBox(s, bx, icam, t) }
        for m in c.lifts { rrDrawLift(s, m, cam) }
        let lantern = th.landmark == "lanterns"
        for ln in c.lines where ln.x1 > x0 && ln.x0 < x1 { rrDrawLine(s, ln, cam, t, lantern: lantern) }
        if st.kind == "normal" { drawFinish(s, t) }
        var i = c.fishFrom(x0)
        while i < c.fish.count {
            let f = c.fish[i]
            if f.x > x1 { break }
            if !f.got { rrDrawFish(s, f, cam, t) }
            i += 1
        }
        for g in c.gold where !g.got { rrDrawFish(s, g, cam, t, gold: true) }
        for cp in c.caps where !cp.got { rrDrawCap(s, cp, cam, t) }
        for hz in c.haz { rrDrawHazard(s, hz, cam, t, stime) }
        boss?.draw(s, t)
        drawGully(s, t)
        drawTora(s, t)
        for q in parts.p {          // world-space particles and score pops
            if q.life < q.full * 0.3 && Int(q.life * 30) % 2 == 1 { continue }
            s.fillRect(col(q.c), Int(q.x) - icam, Int(q.y), q.size, q.size)
        }
        for it in floats.items { drawText(s, it.s, Int(it.x) - icam, Int(it.y), it.c, align: .center) }
        rrDrawWeather(s, th.weather, t, cam)
        drawHud(s, t)
        if state == "intro" { drawIntro(s, t) } else if state == "tally" { drawTally(s, t) }
    }

    func drawSkyFx(_ s: Surface, _ t: Double) {
        switch theme.landmark {
        case "fireworks":
            for i in 0 ..< 3 {
                let p = rrFmod(t * 0.5 + Double(i) / 3, 1)
                let x = 50 + i * 100 + Int(sin(Double(i) * 7) * 20), y = 30 + (i * 17) % 40
                if p < 0.25 {
                    s.fillRect(col("white"), x, y + Int((0.25 - p) * 300), 1, 3)
                } else {
                    let r = Double(Int((p - 0.25) * 40))
                    let c = col(["hotpink", "yellow", "mint"][i])
                    var a = 0
                    while a < 360 {
                        let ra = Double(a) * .pi / 180
                        s.fillRect(c, x + Int(cos(ra) * r), y + Int(sin(ra) * r) + Int(p * 6), 1, 1)
                        a += 30
                    }
                }
            }
        case "lighthouse":
            let bx = 286
            s.fillRect(col("white"), bx - 4, 60, 8, 110)
            var yy = 70
            while yy < 170 { s.fillRect(col("red"), bx - 4, yy, 8, 8); yy += 20 }
            s.fillRect(col("yellow"), bx - 5, 52, 10, 8)
            let a = t * 1.2
            let ex = bx + Int(cos(a) * 160), ey = 56 + Int(sin(a) * 20)
            s.line(col("yellow"), bx, 56, ex, ey)
            s.line(col("cream"), bx, 57, ex, ey + 6)
        case "clouds":
            for i in 0 ..< 4 {
                let x = rrMod(i * 97 - Int(t * Double(12 + i * 4)), W + 80) - 40
                let y = 26 + i * 18
                for (dx, r) in [(0, 9), (10, 12), (22, 8)] { s.circle(col("darkgray"), x + dx, y, r) }
            }
        default: break
        }
        if theme.weather == "storm" && Int(t * 7) % 23 == 0 { s.fillRect(col("lavender"), 0, 0, W, 2) }
    }

    func drawFinish(_ s: Surface, _ t: Double) {
        let fx = Int(course.finish - cam)
        if fx < -30 || fx > W + 30 { return }
        let gy = Int(roofY(course.finish) ?? 150)
        var y = gy - 60
        while y < gy {
            for i in 0 ..< 2 { s.fillRect(col(((y / 6) + i) % 2 == 1 ? "white" : "black"), fx + i * 3, y, 3, 6) }
            y += 6
        }
        s.fillRect(col("gray"), fx + 6, gy - 66, 2, 66)
        drawText(s, "FINISH", fx + 2, gy - 74, rainbow(0, t), align: .center, outline: "ink")
    }

    func drawGully(_ s: Surface, _ t: Double) {
        if st.kind != "normal" { return }
        let x = Int(gully.x - cam), y = Int(gully.y)
        if x > W + 20 || x < -30 { return }
        let flip = gully.state == "flee" || gully.state == "plucked"
        s.blit(sprite(gully.state != "plucked" ? "rr_gully" : "rr_gully_nofish", Int(t * 8) % 2, flip: flip), x - 11, y - 8)
        if gully.state == "perch" && !feather {
            s.blit(sprite("rr_feather"), x + 9, y - 2)        // the tail feather to grab sticks out behind him
            if chase < 30 && Int(t * 3) % 2 == 1 {
                drawText(s, "TOO HIGH? GET CLOSER!", x, y - 22, "white", align: .center, outline: "ink")
            }
        }
        if let ff = flashFeather {
            s.blit(sprite("rr_feather"), Int(ff.x - cam) - 4, Int(ff.y + ff.t * 20) - 4 + Int(sin(ff.t * 6) * 3))
        }
    }

    func drawTora(_ s: Surface, _ t: Double) {
        let b = body
        if invuln > 0 && Int(t * 16) % 2 == 1 && state == "play" { return }
        for tr in trail { s.fillRect(col(rainbow(Int(tr.life * 20), t)), Int(tr.x - cam) - 6, Int(tr.y) - 9, 3, 3) }
        let x = Int(b.x - cam), y = Int(b.y)
        var name = "rr_tora_run", fr = 0
        if state == "fall" {
            name = "rr_tora_hurt"
        } else if ["finish", "clear", "tally"].contains(state) && speed < 5 {
            name = "rr_tora_happy"; fr = Int(t * 4) % 2
        } else if state == "intro" || state == "pick" || ready > 0 {
            name = "rr_tora_idle"; fr = Int(t * 2) % 5 == 0 ? 1 : 0
        } else if hurtT > 0 {
            name = "rr_tora_hurt"
        } else if b.wire != nil {
            name = "rr_tora_jump"
        } else if b.ground == nil {
            if b.cling { name = "rr_tora_cling" } else if b.pounce { name = "rr_tora_pounce" } else {
                name = b.vy < 60 ? "rr_tora_jump" : "rr_tora_fall"
            }
        } else if b.slide {
            name = "rr_tora_slide"
        } else {
            fr = Int(stime * speed / 9) % 4
        }
        var remap: [Character: Character]?
        if timers["catnip"]! > 0 { remap = ["o": Int(t * 10) % 2 == 1 ? "l" : "m"] } else if hype.feverOn && Int(t * 8) % 2 == 1 { remap = ["o": "y"] }
        s.blit(sprite(name, fr, remap: remap), x - 10, y - 16)
        if b.wire != nil {          // hanging from the wire by the front paws
            s.fillRect(col("black"), x + 3, y - 16, 2, 3)
            if Int(t * 20) % 2 == 1 { s.fillRect(col("yellow"), x + 4 + Int.random(in: -3 ... 3), y - 16, 1, 1) }
        }
        if timers["umbrella"]! > 0 {
            s.polygon(col("sky"), [(Double(x - 10), Double(y - 18)), (Double(x + 2), Double(y - 28)), (Double(x + 14), Double(y - 18))])
            s.fillRect(col("white"), x + 2, y - 18, 1, 6)
        }
        if shield > 0 && Int(t * 4) % 4 == 0 { s.circle(col("peach"), x, y - 7, 11, width: 1) }
    }

    func drawHud(_ s: Surface, _ t: Double) {
        s.fillRect(col("black"), 0, 0, W, 21)
        s.fillRect(col("ink"), 0, 21, W, 1)
        drawText(s, String(format: "%07d", score), 4, 3, "white", shadow: nil)
        drawText(s, String(format: "HI %07d", max(best, score)), 4, 12, "gray", shadow: nil)
        s.blit(sprite("rr_head"), W - 30, 2)         // lives: a cat-head icon and the count
        drawText(s, "x\(lives)", W - 21, 3, "pink", shadow: nil)
        s.blit(sprite("rr_fish"), W - 72, 3)
        drawText(s, "\(fishGot)", W - 62, 3, "sky", shadow: nil)
        if let bo = boss, bo.state != "dead" {
            bossBar(s, bo.name, Double(bo.hp), Double(bo.maxhp), t, y: 0, x: 92, w: 136)
        } else {
            let label = st.kind == "bonus" ? "BONUS RUN" : (st.kind == "boss" ? "BOSS STAGE" : "STAGE \(n)")
            drawText(s, label, W / 2, 3, "yellow", align: .center, shadow: nil)
        }
        // course progress (normal + bonus) - a strip with Tora's head and the flag
        if st.kind != "boss" && course.finish > 0 {
            let x0 = 100, w = 120
            s.fillRect(col("darkgray"), x0, 15, w, 2)
            let p = max(0, min(1, body.x / course.finish))
            s.fillRect(col("mint"), x0, 15, Int(Double(w) * p), 2)
            s.fillRect(col("white"), x0 + w, 11, 1, 6)
            s.fillRect(col("red"), x0 + w + 1, 11, 3, 2)
            s.blit(sprite("rr_head"), x0 + Int(Double(w) * p) - 4, 11)
        }
        // CHASE meter (fills with fish) and the FEVER gauge
        let x0 = W - 72
        s.fillRect(col("darkgray"), x0, 13, 46, 3)
        s.fillRect(col(chase >= 99.5 && Int(t * 8) % 2 == 1 ? "yellow" : "orange"), x0, 13, Int(46 * chase / 100), 3)
        s.blit(sprite("rr_feather"), x0 + 47, 10)
        s.fillRect(col("darkgray"), x0, 17, 46, 1)
        if hype.feverOn {
            for i in 0 ..< 46 { s.fillRect(col(rainbow(i / 6, t)), x0 + i, 17, 1, 1) }
        } else {
            s.fillRect(col("hotpink"), x0, 17, Int(46 * hype.fever), 1)
        }
        // timers (bottom left)
        var x = 4
        for (k, ic) in [("magnet", 0), ("umbrella", 1), ("catnip", 2)] {
            let v = timers[k]!
            if v > 0 && (v > 2 || Int(t * 8) % 2 == 1) {
                s.circle(col("black"), x + 6, H - 8, 7)
                s.circle(col(RR_CAP_COLORS[ic]), x + 6, H - 8, 6)
                s.circle(col("ink"), x + 6, H - 8, 4)
                rrDrawCapIcon(s, ic, x + 6, H - 8, t)
                x += 16
            }
        }
        if shield > 0 { drawText(s, "FUR x\(shield)", x + 2, H - 11, "peach") }
    }

    func drawIntro(_ s: Surface, _ t: Double) {
        if st.kind == "boss" {
            if Int(t * 4) % 2 == 1 {
                var x = -20
                while x < W + 20 {
                    s.polygon(col("red"), [(Double(x), 98), (Double(x + 10), 98), (Double(x + 20), 106), (Double(x + 10), 106)])
                    s.polygon(col("red"), [(Double(x), 146), (Double(x + 10), 146), (Double(x + 20), 154), (Double(x + 10), 154)])
                    x += 20
                }
            }
            panel(s, IRect(40, 108, 240, 34), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 112, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.name) IS ON THE ROOF", W / 2, 130, "white", align: .center, shadow: nil)
            return
        }
        let h = 64, y0 = 40
        panel(s, IRect(30, y0, 260, h), fill: "ink", border: st.kind == "bonus" ? "yellow" : "peach")
        if st.kind == "bonus" {
            let title = "BONUS RUN"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, y0 + 6 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            drawText(s, st.name, W / 2, y0 + 26, "yellow", align: .center)
            drawText(s, "NO HAZARDS - GRAB ALL THE FISH!", W / 2, y0 + 38, "white", align: .center)
            drawText(s, "FALLING IS FREE HERE", W / 2, y0 + 50, "mint", align: .center)
            return
        }
        drawText(s, "STAGE \(n)", W / 2, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, "\(theme.name) - \(st.name)", W / 2, y0 + 25, "lavender", align: .center)
        if !st.newLine.isEmpty { drawText(s, st.newLine, W / 2, y0 + 37, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center) }
        drawText(s, "TORA: " + theme.quip, W / 2, y0 + 50, "peach", align: .center)
    }

    func drawTally(_ s: Surface, _ t: Double) {
        let h = 34 + tally.count * 11, y0 = 40
        panel(s, IRect(64, y0, 192, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, W / 2, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 20 + i * 11
            drawText(s, row.label, 72, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 248, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 {
            drawText(s, "PRESS JUMP", W / 2, y0 + h - 11, "lavender", align: .center, shadow: nil)
        }
        if !quip.isEmpty { drawText(s, "TORA: " + quip, W / 2, y0 + h + 6, "peach", align: .center, outline: "ink") }
    }

    // ---------------------------------------------------------------- carousel preview
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        s.fill(col("night"))
        for i in 0 ..< 8 { s.fillRect(lerpCol("night", "deep", Double(i) / 7), 0, i * h / 8, w, h / 8 + 1) }
        s.circle(col("cream"), w - 18, 14, 8)
        s.circle(col("white"), w - 19, 13, 6)
        let off = Int(t * 50)
        for i in 0 ..< 5 {
            let bx = i * 40 - off % 40 - 10
            let top = h - 22 - (((i + off / 40) * 7) % 3) * 6
            s.fillRect(col("ink"), bx, top - 14, 30, h)
        }
        for i in 0 ..< 4 {
            let rx = i * 48 - off % 48
            let ry = h - 16 + (((i + off / 48) * 5) % 2) * 4
            s.fillRect(col("brown"), rx, ry, 38, h - ry)
            s.fillRect(col("peach"), rx - 1, ry, 40, 2)
            var wx = rx + 4
            while wx < rx + 36 { s.fillRect(col("yellow"), wx, ry + 6, 4, 4); wx += 9 }
        }
        for i in 0 ..< 5 {
            let fx = rrMod(i * 23 - off, w + 20) - 10
            s.blit(sprite("rr_fish"), fx, h - 34 - Int(abs(sin(Double(i) + t)) * 10))
        }
        let jy = Int(abs(sin(t * 3)) * 16)
        s.blit(sprite(jy < 3 ? "rr_tora_run" : "rr_tora_jump", Int(t * 12) % 4), 24, h - 32 - jy)
        s.blit(sprite("rr_gully", Int(t * 8) % 2, flip: true), w - 40 + Int(sin(t * 2) * 6), 18 + Int(sin(t * 3) * 3))
    }
}
