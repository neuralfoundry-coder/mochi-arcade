// CLOUD POUNCE - SORA the star-patched cat bounces up through the clouds to the moon
// (port of games/cloud_pounce.py). 200 stages read from the exported campaign (games/cloud_pounce_data.py),
// sky bosses in CloudPounceBoss.swift, objects and drawing helpers in CloudPounceData.swift.
import Foundation

final class CloudPounce: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD     STEER SORA (PUSH FURTHER = FASTER)", "POUNCE  DIVE DOWN + POWER BOUNCE"]
    static let helpSkip = 2

    override var music: String? { song() }
    override var buttons: [Action: String] { [.a: "POUNCE"] }
    override var buttonOrder: [Action] { [.a] }
    override var fourWay: Bool { false }

    var lives: Int
    let fspeed: Double
    var levels: [String: Int] = [:]
    var lifeI = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    var wasFever = false
    let field = Surface(CP.FW, H)
    // stage
    var n = 1
    var st: CPStage = CPData.stages[0]
    var tier = 0
    var theme: [String] = ["", "sky", "blue", "deep", "sky", "white"]
    var clouds: [CPCloud] = []
    var items: [CPItem] = []
    var fish: [CPFish] = []
    var foes: [CPFoe] = []
    var hail: [CPHail] = []
    var boss: CPBoss?
    var starsTotal = 0
    var goal = 0.0
    var wind = 0.0, fog = 0.0, hailRate = 0.0
    var windT = 0.0, windDir = 1.0, windOn = 0.0, hailT = 2.0
    // SORA
    var x = CP.FWd / 2, h = 0.0, vx = 0.0, vh = 0.0
    var face = 1
    var pouncing = false
    var pounces = 1
    var landT = 0.0, hurtT = 0.0, invuln = 0.0
    var rocketT = 0.0, balloonT = 0.0
    var balloonC = "red"
    var parasolT = 0.0, magnetT = 0.0
    var shield = false
    var cushion = 0
    var rescueT = 0.0, distractT = 0.0, distractX = 0.0, kick = 0.0
    var chain = 0               // critters knocked out since SORA last touched a cloud
    var bonkT = 0.0
    var milkGiven = false
    var cam = -60.0, bestH = 0.0, topLand = 0.0, altPts = 10.0
    // stage stats
    var stime = 0.0
    var missed = false, hurt = false
    var stageCombo = 0, gotStars = 0, gotFish = 0, stomps = 0, popped = 0, golds = 0
    var moon = false
    var bonusLeft = 0.0, balloonSpawn = 0.0
    var lucky = false
    var state = "intro"
    var stateT = 0.0, introLen = 2.4
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        fspeed = SPEEDS[d] ?? 1
        super.init(app, info, opt)
        hype.comboTime = 2.6
        hype.comboY = 16
        // "stage" is only passed by the GIF recorder
        let start = max(1, min(STAGES, optInt("stage", optInt("start", 1))))
        startStage(start)
        if start > 10 && opt["stage"] == nil {      // from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (start - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func factor(_ pts: Int) -> Int { pts * (10 + tier) / 10 }
    @discardableResult
    func scoreAt(_ pts: Int, _ px: Double? = nil, _ ph: Double? = nil, _ c: String = "yellow") -> Int {
        add(factor(pts), px, ph.map { Double(sy($0) - 10) }, c)
    }
    /// Screen (field) y of an altitude.
    func sy(_ alt: Double) -> Int { Int(Double(H) - (alt - cam)) }
    func song() -> String {
        if st.kind == "boss" { return "boss" }
        if st.kind == "bonus" { return "bonus" }
        return tier % 2 == 0 ? "cp_sky" : "cp_moon"
    }
    func feverGain(_ base: Double) -> Double { base * (1 + 0.35 * Double(lv("fever"))) }
    func vxMax() -> Double {
        var v = CP.VX_MAX * (1 + 0.12 * Double(lv("steer")))
        if rocketT > 0 { v *= 1.25 }
        return v
    }
    func jumpV() -> Double { CP.JUMP_V * (1 + 0.05 * Double(lv("spring"))) }
    func isArena() -> Bool { st.kind == "boss" || (st.kind == "bonus" && st.bonus == "balloons") }
    var isRocketRide: Bool { st.kind == "bonus" && st.bonus == "rocket" }
    func fullPounces() -> Int { 1 + lv("double") }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        n = num
        st = CPData.stages[num - 1]
        tier = st.tier
        theme = CPData.themes[min(tier, CPData.themes.count - 1)]
        reached(num)
        clouds = stride(from: 0, to: st.c.count - 3, by: 4).map { CPCloud(st.c[$0], st.c[$0 + 1], st.c[$0 + 2], st.c[$0 + 3], tier) }
        items = stride(from: 0, to: st.i.count - 2, by: 3).map { CPItem(st.i[$0], Double(st.i[$0 + 1]), Double(st.i[$0 + 2])) }
        for it in items {
            if it.k == CP.I_BALLOON {
                it.gold = hype.lucky(0.025 + 0.012 * Double(lv("luck")))
            } else if it.k == CP.I_STAR && lv("luck") > 0 && hype.lucky(0.004 * Double(lv("luck"))) {
                it.k = CP.I_GOLD
            }
        }
        fish = stride(from: 0, to: st.f.count - 4, by: 5).map { CPFish(st.f[$0], st.f[$0 + 1], st.f[$0 + 2], st.f[$0 + 3], st.f[$0 + 4]) }
        foes = stride(from: 0, to: st.e.count - 4, by: 5).map { CPFoe(st.e[$0], st.e[$0 + 1], st.e[$0 + 2], st.e[$0 + 3], st.e[$0 + 4], fspeed) }
        for r in stride(from: 0, to: st.riv.count - 6, by: 7) {      // rocket ride star rivers
            let h0 = st.riv[r], count = st.riv[r + 1], dh = st.riv[r + 2], xc = st.riv[r + 3], amp = st.riv[r + 4]
            let freq = Double(st.riv[r + 5]), ph = Double(st.riv[r + 6])
            for i in 0 ..< count {
                let sx = Double(xc) + Double(amp) * sin(Double(i) * freq / 100 + ph / 100)
                items.append(CPItem(CP.I_STAR, Double(cpMod(Int(sx), CP.FW)), Double(h0 + i * dh)))
            }
        }
        starsTotal = items.filter { $0.k == CP.I_STAR }.count + fish.reduce(0) { $0 + $1.stars.count }
        hail = []
        boss = st.boss.map { CPBoss(self, $0) }
        goal = Double(st.goal)
        wind = Double(st.mods[0]); fog = Double(st.mods[1]); hailRate = Double(st.mods[2])
        windT = 0; windDir = 1; windOn = 0; hailT = 2
        // SORA
        x = CP.FWd / 2; h = 0; vx = 0; vh = 0
        face = 1
        pouncing = false
        pounces = fullPounces()
        landT = 0; hurtT = 0; invuln = 0
        rocketT = 0; balloonT = 0; balloonC = "red"
        parasolT = 0; magnetT = 0
        shield = lv("bell") > 0
        cushion = lv("cushion")
        rescueT = 0; distractT = 0; distractX = 0; kick = 0; chain = 0; bonkT = 0; milkGiven = false
        cam = -60; bestH = 0; topLand = 0; altPts = 10
        if isArena() {
            cam = st.kind == "bonus" ? -12 : 0
            let sc = st.kind == "boss" ? clouds[1] : clouds[0]
            x = sc.cx(); h = sc.hd
        }
        if isRocketRide { h = 40; cam = -60 }
        // stage stats
        stime = 0
        missed = false; hurt = false
        stageCombo = 0; gotStars = 0; gotFish = 0; stomps = 0; popped = 0; golds = 0
        moon = false
        bonusLeft = st.time
        balloonSpawn = 0
        lucky = st.kind == "normal" && hype.lucky(0.03 + 0.01 * Double(lv("luck")))
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.0 : 2.4
        tally = []
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        switch state {
        case "intro":
            boss?.update(dt)
            followCam(dt)
            if stateT > introLen || (stateT > 0.5 && app.input.hit(.a)) { beginPlay() }
        case "play":
            play(dt)
        case "clear":
            updateClear(dt)
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(CP_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        default: break
        }
        for c in clouds { c.squash = max(0, c.squash - dt) }
    }

    func beginPlay() {
        state = "play"
        stateT = 0
        boss?.state = "fight"
        if isRocketRide {
            rocketT = st.time + 0.5
            app.audio.play("powerup")
        } else {
            vh = jumpV()
            app.audio.play("jump")
        }
        if lucky {          // a rare lucky stage: a catnip rocket from the very first leap
            lucky = false
            hype.banner("SHOOTING STAR!", "LUCKY ROCKET START", dur: 1.6, rainbow: true, sound: "jackpot")
            rocketT = 2.2
            hype.shower(30, "stars")
        }
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = CP_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id] ?? 1)", color: u.color, dur: 1.2, scale: 1)
        }
        switch id {
        case "life": lives += 1; app.audio.play("extra")
        case "bell": shield = true
        case "cushion": cushion += 1
        case "double": pounces += 1
        default: break
        }
    }

    func play(_ dt: Double) {
        stime += dt
        landT = max(0, landT - dt); hurtT = max(0, hurtT - dt); invuln = max(0, invuln - dt)
        parasolT = max(0, parasolT - dt); magnetT = max(0, magnetT - dt); distractT = max(0, distractT - dt)
        bonkT = max(0, bonkT - dt)
        updateClouds(dt)
        moveCat(dt)
        if state != "play" { return }
        updateItems(dt)
        updateFoes(dt)
        updateWeather(dt)
        if boss != nil { updateBoss(dt) }
        if st.kind == "bonus" { updateBonus(dt) }
        followCam(dt)
        stageCombo = max(stageCombo, hype.combo)
        if hype.feverOn && !wasFever {
            hype.feverT += 2 * Double(lv("fever"))
            app.audio.music("fever")
        } else if wasFever && !hype.feverOn {
            app.audio.music(song())
        }
        wasFever = hype.feverOn
        checkLife()
        if state == "play" && !isArena() && h >= goal && !isRocketRide {
            moon = true
            stageClear()
        }
    }

    // ---------------------------------------------------------------- SORA
    /// -1...1: digital left/right, or the touch pad's analog x when the thumb is down.
    func steerInput() -> Double {
        let inp = app.input
        var d = Double((inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0))
        if let a = inp.analog, abs(a.x) > 0.1 {
            d = max(-1, min(1, (a.x - (a.x < 0 ? -0.1 : 0.1)) / 0.75))
        }
        return d
    }

    func moveCat(_ dt: Double) {
        let inp = app.input
        var d = steerInput()
        if distractT > 0 {        // chasing a laser dot!
            let dd = cpWrapd(distractX - x)
            d = abs(dd) < 3 ? 0 : (dd > 0 ? 1 : -1)
        }
        let vmax = vxMax()
        let acc = 760 * (1 + 0.12 * Double(lv("steer")))
        if d != 0 {
            face = d > 0 ? 1 : -1
            let target = d * vmax
            vx = vx < target ? min(target, vx + acc * dt) : max(target, vx - acc * dt)
        } else {
            let dec = 520 * dt
            vx = vx > dec ? vx - dec : (vx < -dec ? vx + dec : 0)
        }
        if kick != 0 {
            vx += kick * dt * 4
            kick *= max(0, 1 - dt * 3)
            if abs(kick) < 5 { kick = 0 }
        }
        if windOn > 0 { vx += windDir * wind * dt }
        if let b = boss, b.push != 0 { vx += b.push * dt }
        let lim = vmax + 70
        vx = max(-lim, min(lim, vx))
        x = cpFmod(x + vx * dt, CP.FWd)
        // pounce (the pad's down only counts without the touch thumb pad, so steering never pounces by accident)
        if (inp.hit(.a) || (inp.analog == nil && inp.hit(.down))) && pounces > 0 && !pouncing && rocketT <= 0
            && balloonT <= 0 && rescueT <= 0 && distractT <= 0 {
            pouncing = true
            pounces -= 1
            vh = -CP.POUNCE_V
            vx *= 0.25
            app.audio.play("trap")
            parts.burst(x, Double(sy(h) - 8), 6, ["white", "lavender"], 40, 0.3)
        }
        let prev = h
        if rescueT > 0 {
            rescueT -= dt
            vh = 120
            h += vh * dt
            if rescueT <= 0 {
                let c = CPCloud(CP.KF, Int(max(0, min(CP.FWd - 40, x - 20))), Int(h - 14), 40, 0)
                c.temp = 3
                clouds.append(c)
                vh = 60
                app.audio.play("pop")
            }
            return
        }
        if rocketT > 0 {
            rocketT -= dt
            vh = st.kind == "bonus" ? CP.ROCKET_SPEED : 300
            pouncing = false
            if Int(stateT * 30) % 2 == 0 {
                parts.burst(x, Double(sy(h) + 2), 2, [rainbow(Int(stime * 10), 0), "orange", "yellow"], 40, 0.4, grav: -20)
            }
            if rocketT <= 0 {
                vh = 220
                pounces = fullPounces()
                hype.banner("FUEL OUT!", color: "orange", dur: 0.8, scale: 1)
            }
        } else if balloonT > 0 {
            balloonT -= dt
            vh = CP.BALLOON_LIFT
            if balloonT <= 0 {
                app.audio.play("pop")
                parts.burst(x, Double(sy(h) - 22), 10, [balloonC, "white"], 50, 0.4)
                pounces = fullPounces()
            }
        } else {
            vh -= CP.G * dt
            if pouncing {
                vh = max(vh, -CP.POUNCE_V - 40)
            } else {
                vh = max(vh, -(parasolT > 0 ? 80.0 : 330.0))
            }
        }
        h += vh * dt
        if isArena() && h > 186 {
            h = 186
            vh = min(vh, 0)
        }
        if vh < 0 {
            checkLand(prev)
            if state != "play" { return }
        }
        // new heights give points
        if h > bestH {
            bestH = h
            while bestH >= altPts && !isArena() {
                add(factor(10))
                altPts += 10
            }
        }
        // falling off the bottom
        if h < cam - 20 {
            fallOff()
        } else if cushion > 0 && vh < -60 && h < cam + 10 && !isArena() {
            cushion -= 1
            let c = CPCloud(CP.KF, Int(max(0, min(CP.FWd - 48, x - 24))), Int(h - 4), 48, 0)
            c.temp = 2.5
            clouds.append(c)
            hype.banner("CUSHION!", color: "white", dur: 0.9, scale: 1, sound: "bubble")
        }
    }

    func overlaps(_ c: CPCloud, _ pad: Double = 3) -> Bool { abs(cpWrapd(x - c.cx())) <= Double(c.w) / 2 + pad }

    func solid(_ c: CPCloud) -> Bool {
        if !c.alive { return false }
        if c.k == CP.KG { return ghostU(c) < 0.7 }
        return true
    }

    func checkLand(_ prev: Double) {
        var best: CPCloud?
        for c in clouds where solid(c) && prev >= c.hd - 0.01 && h <= c.hd && overlaps(c) {
            if pouncing && c.k == CP.KT {
                smashPuff(c)
                continue
            }
            if best == nil || c.h > best!.h { best = c }
        }
        if let b = best { land(b) }
    }

    func smashPuff(_ c: CPCloud) {
        c.alive = false
        if isArena() { c.regrow = 3 }
        app.audio.play("pop")
        parts.burst(c.cx(), Double(sy(c.hd) + 4), 14, ["white", "cream", "lavender"], 60, 0.5)
        hype.hit(1, fever: feverGain(0.03))
        scoreAt(50, c.cx(), c.hd)
    }

    func land(_ c: CPCloud) {
        let au = app.audio
        let g = hype!
        h = c.hd
        let k = c.k
        let powered = pouncing
        var v = jumpV()
        if k == CP.KR {
            v = CP.RAIN_V * (1 + 0.05 * Double(lv("spring")))
        } else if k == CP.KS {
            v = CP.SPRING_V
        }
        if powered && k != CP.KS { v = max(v, CP.POWER_V + 15 * Double(lv("heavy"))) }
        if g.feverOn { v *= 1.1 }
        if k == CP.KZ && zapU(c) >= 0.85 {
            if powered {
                g.banner("GROUNDED!", "+500", color: "yellow", dur: 0.9, scale: 1)
                scoreAt(500, c.cx(), c.hd + 20)
                g.hit(1, fever: feverGain(0.06))
                c.phase += 1.7            // knocks its rhythm back to calm
            } else {
                hurtCat("ZAP!")
            }
        }
        vh = v
        pouncing = false
        pounces = fullPounces()
        chain = 0
        landT = 0.12
        c.squash = 0.2
        let y = Double(sy(c.hd))
        if k == CP.KS {
            au.play("bubble")
            parts.burst(x, y, 12, ["hotpink", "yellow", "mint", "sky"], 70, 0.5)
            floats.add(x, y - 14, "BOING!", rainbow(0, t))
        } else if k == CP.KR {
            au.play("eat")
            parts.burst(x, y + 2, 6, ["sky", "blue"], 40, 0.4)
        } else if powered {
            au.play("explode")
            app.shake(2, 0.15)
            parts.burst(x, y, 16, ["white", "yellow", "lavender"], 90, 0.45)
            shockwave(c)
        } else {
            au.play(c.hd > topLand ? "jump" : "paddle")
            parts.burst(x, y, 4, ["white", "cream"], 30, 0.3)
        }
        if k == CP.KT {
            c.alive = false
            if isArena() { c.regrow = 3 }
            au.play("pop")
            parts.burst(c.cx(), y + 3, 12, ["white", "cream"], 50, 0.5)
        } else if k == CP.KW {
            kick = Double(c.a) * 230
            parts.burst(x, y, 8, ["mint", "white"], 60, 0.4)
            au.play("bubble")
        }
        if c.hd > topLand {       // climbing keeps the combo chain alive, bouncing in place doesn't
            topLand = c.hd
            if g.combo > 0 { g.keepCombo() }
        }
    }

    /// A pounce landing knocks out critters right next to the landing spot.
    func shockwave(_ c: CPCloud) {
        for f in foes where f.alive && (f.k == CP.E_BIRD || f.k == CP.E_KITE) && abs(f.h - c.hd) < 26 && abs(cpWrapd(f.x - x)) < 34 {
            defeatFoe(f, true)
        }
    }

    func zapU(_ c: CPCloud) -> Double {
        let per = max(2.8, 4.2 - 0.06 * Double(tier))
        return cpFmod(stime + Double(c.a) / 100 * per + c.phase, per) / per
    }

    func ghostU(_ c: CPCloud) -> Double { cpFmod(stime + Double(c.a) / 100 * 3.2, 3.2) / 3.2 }

    func updateClouds(_ dt: Double) {
        let tt = stime
        for c in clouds {
            if c.k == CP.KM { c.x = Double(c.x0) + sin(tt * Double(c.b) / 100 + c.phase) * Double(c.a) }
            if !c.alive && c.regrow > 0 {
                c.regrow -= dt
                if c.regrow <= 0 {
                    c.alive = true
                    c.squash = 0.2
                    parts.burst(c.cx(), Double(sy(c.hd) + 4), 6, ["white", "cream"], 30, 0.3)
                }
            }
            if c.temp > 0 {
                c.temp -= dt
                if c.temp <= 0 { c.alive = false }
            }
            if c.k == CP.KZ && c.alive && zapU(c) >= 0.85 && invuln <= 0 && rocketT <= 0 {
                // the bolt under a zapping thunder cloud
                let gap = c.hd - (h + 12)
                if 0 < gap && gap < 70 && abs(cpWrapd(x - c.cx())) < 6 { hurtCat("ZAP!") }
            }
        }
        clouds.removeAll { !($0.alive || $0.regrow > 0 || $0.hd > cam - 30) }
    }

    func followCam(_ dt: Double) {
        if isArena() { return }
        var c = cam
        let target = rocketT > 0 ? h - 90 : h - 112
        if target > c { c += (target - c) * min(1, dt * 7) }
        if state == "play" && fog > 0 && rescueT <= 0 && stime > 1.5 { c += fog * dt }
        moveCam(min(c, goal - 150))
    }

    /// Scroll; sparks and score pop-ups (drawn in screen space) scroll along with the sky.
    func moveCam(_ c: Double) {
        let dc = c - cam
        cam = c
        if dc != 0 {
            for i in parts.p.indices { parts.p[i].y += dc }
            for i in floats.items.indices { floats.items[i].y += dc }
        }
    }

    func hurtCat(_ why: String = "OUCH!") {
        if invuln > 0 || rocketT > 0 || state != "play" { return }
        let au = app.audio
        if shield {
            shield = false
            invuln = 1.5
            au.play("tin")
            hype.banner("BELL SAVE!", color: "yellow", dur: 0.9, scale: 1)
            parts.burst(x, Double(sy(h) - 8), 12, ["yellow", "white"], 60, 0.5)
            return
        }
        hurt = true
        hype.breakCombo()
        invuln = 2
        hurtT = 0.6
        pouncing = false
        vh = min(vh, 80)
        au.play("hurt")
        app.shake(3, 0.3)
        floats.add(x, Double(sy(h) - 20), why, "red")
        parts.burst(x, Double(sy(h) - 8), 10, ["red", "white"], 60, 0.5)
        if st.kind != "bonus" { _ = loseLife() }
    }

    func loseLife() -> Bool {
        missed = true
        lives -= 1
        if lives <= 0 {
            state = "over"
            hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
            app.audio.play("gameover")
            endGame(false, "STAGE \(n)", delay: 2.5)
            return false
        }
        hype.banner("MEW!", "\(lives) LEFT", color: "pink", dur: 1.0, scale: 1)
        return true
    }

    func fallOff() {
        app.audio.play("hurt")
        hype.breakCombo()
        pouncing = false
        rocketT = 0; balloonT = 0
        if st.kind != "bonus" && !loseLife() { return }
        // a rescue balloon carries SORA back up
        rescueT = isArena() ? 0.8 : 1.3
        invuln = 3
        h = cam - 16
        vh = 120
        app.audio.play("bubble")
    }

    func checkLife() {
        let target = lifeI < CP.LIFE_AT.count ? CP.LIFE_AT[lifeI] : CP.LIFE_AT.last! + 100000 * (lifeI - CP.LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("BONUS LIFE!", "\(target) POINTS", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    // ---------------------------------------------------------------- stars, treats, constellations
    func updateItems(_ dt: Double) {
        let au = app.audio
        let g = hype!
        let cy = h + 7
        var mag = 0.0
        if lv("magnet") > 0 { mag = 18 + 12 * Double(lv("magnet")) }
        if magnetT > 0 || g.feverOn { mag = max(mag, 70) }
        for it in items {
            if it.got || abs(it.h - cy) > 120 { continue }
            var dx = cpWrapd(it.x - x)
            var dh = it.h - cy
            if mag > 0 && (it.k == CP.I_STAR || it.k == CP.I_GOLD) && dx * dx + dh * dh < mag * mag {
                let dist = max(1, (dx * dx + dh * dh).squareRoot())
                let step = min(dist, 190 * dt)
                it.x = cpFmod(it.x - dx / dist * step, CP.FWd)
                it.h -= dh / dist * step
                dx = cpWrapd(it.x - x)
                dh = it.h - cy
            }
            let r = it.k != CP.I_BALLOON ? 10.0 : 9.0
            if abs(dx) < r && abs(dh) < r + 2 { collect(it) }
        }
        for f in fish {
            f.glow = max(0, f.glow - dt)
            if f.done || abs(Double(f.h) - cy) > 60 { continue }
            for i in f.stars.indices {
                let s = f.stars[i]
                if !s.got && abs(cpWrapd(s.x - x)) < 9 && abs(s.h - cy) < 11 {
                    f.stars[i].got = true
                    gotStars += 1
                    g.hit(1, fever: feverGain(0.025))
                    scoreAt(30 + g.comboBonus(2), s.x, s.h, "sky")
                    au.play("coin")
                    parts.burst(s.x, Double(sy(s.h)), 5, ["white", "sky"], 30, 0.3)
                }
            }
            if f.stars.allSatisfy({ $0.got }) {
                f.done = true
                f.glow = 1.2
                gotFish += 1
                let pts = scoreAt(1000, Double(f.x), Double(f.h + 14), "yellow")
                g.hit(2, fever: feverGain(0.12))
                if f.gold {
                    g.jackpot(factor(5000), sub: "GOLDEN FISH STARS!")
                } else {
                    g.banner("FISH CONSTELLATION!", "+\(pts)", color: "sky", dur: 1.3, scale: 1, sound: "bonus")
                }
                for (a, b) in f.lines {
                    for k in 0 ..< 4 {
                        let px = f.stars[a].x + cpWrapd(f.stars[b].x - f.stars[a].x) * Double(k) / 4
                        let ph = f.stars[a].h + (f.stars[b].h - f.stars[a].h) * Double(k) / 4
                        parts.sparkle(px, Double(sy(ph)), "yellow")
                    }
                }
            }
        }
        items.removeAll { $0.got || $0.h <= cam - 40 }
    }

    func collect(_ it: CPItem) {
        let au = app.audio
        let g = hype!
        let k = it.k
        if k == CP.I_STAR {
            it.got = true
            gotStars += 1
            g.hit(1, fever: feverGain(0.02))
            scoreAt(50 + g.comboBonus(2), g.combo % 5 == 0 ? it.x : nil, it.h)
            au.play("fruit")
            parts.burst(it.x, Double(sy(it.h)), 4, ["yellow", "white"], 30, 0.3)
        } else if k == CP.I_BALLOON {
            it.got = true
            popped += 1
            g.hit(1, fever: feverGain(0.03))
            scoreAt(100, it.x, it.h, "pink")
            if rocketT > 0 || rescueT > 0 || isArena() {
                au.play("pop")
                parts.burst(it.x, Double(sy(it.h)), 10, ["red", "white"], 50, 0.4)
            } else {
                balloonT = CP.BALLOON_T
                balloonC = it.gold ? "yellow" : CP.BALLOON_COLS[Int(it.ph) % CP.BALLOON_COLS.count]
                pouncing = false
                au.play("bubble")
            }
            if it.gold {
                golds += 1
                g.jackpot(factor(3000), sub: "GOLDEN BALLOON!")
            }
        } else if k == CP.I_GOLD {
            it.got = true
            golds += 1
            g.jackpot(factor(4000), sub: "GOLDEN FISH!")
            parts.burst(it.x, Double(sy(it.h)), 16, ["yellow", "orange", "white"], 70, 0.6)
        } else {
            it.got = true
            power(k)
        }
    }

    func power(_ k: Int) {
        let au = app.audio
        au.play("powerup")
        floats.add(x, Double(sy(h) - 22), CP.CAP_NAMES[k] ?? "", "mint")
        scoreAt(100)
        switch k {
        case CP.I_ROCKET:
            rocketT = 2.2 + 0.45 * Double(lv("rocket"))
            balloonT = 0
            pouncing = false
            hype.flash("orange", 0.15)
        case CP.I_BELL: shield = true
        case CP.I_PARASOL: parasolT = 10
        case CP.I_MAGNET: magnetT = 12
        case CP.I_MILK: lives += 1; au.play("extra")
        default: break
        }
    }

    // ---------------------------------------------------------------- critters
    func updateFoes(_ dt: Double) {
        let tt = stime
        let cx = x, cy = h + 7
        for f in foes {
            if !f.alive {
                f.deadT += dt
                f.vh -= 300 * dt
                f.h += f.vh * dt
                continue
            }
            if f.ah < cam - 60 || f.ah > cam + 300 { continue }
            let k = f.k
            let a = Double(f.a), b = Double(f.b)
            var hw = 4.0, hh = 4.0
            if k == CP.E_BIRD {
                f.x = cpFmod(f.x + a * b * f.spd * dt, CP.FWd)
                f.h = f.ah + sin(tt * 5 + f.ph) * 3
                hw = 7; hh = 5
            } else if k == CP.E_KITE {
                f.x = cpFmod(f.ax + sin(tt * b / 100 + f.ph) * a, CP.FWd)
                f.h = f.ah + cos(tt * b / 50 + f.ph) * 4
                hw = 6; hh = 8
            } else if k == CP.E_DOT {
                f.x = cpFmod(f.ax + sin(tt * b / 100 * 1.3 + f.ph) * a, CP.FWd)
                f.h = f.ah + sin(tt * b / 100 * 0.9) * a * 0.45
            } else {
                f.x = cpFmod(f.ax + cos(tt * b / 100 + f.ph) * a, CP.FWd)
                f.h = f.ah + sin(tt * b / 100 + f.ph) * a * 0.6
            }
            let dx = cpWrapd(f.x - cx)
            let dh = f.h - cy
            if abs(dx) > hw + 5 || abs(dh) > hh + 7 { continue }
            if rescueT > 0 { continue }
            if k == CP.E_DOT {
                if distractT <= 0 && rocketT <= 0 && invuln <= 0 {
                    distractT = 1
                    distractX = f.x
                    pouncing = false
                    floats.add(x, Double(sy(h) - 22), "!?", "red")
                    app.audio.play("type")
                }
                continue
            }
            if rocketT > 0 && k != CP.E_SPARK {
                defeatFoe(f, true)
                continue
            }
            if k != CP.E_SPARK && (pouncing || (vh < 0 && h >= f.h - 3)) {
                defeatFoe(f, pouncing)
                vh = pouncing ? CP.POWER_V + 15 * Double(lv("heavy")) : jumpV() * 1.05
                pouncing = false
                pounces = fullPounces()
                continue
            }
            hurtCat()
        }
        if distractT > 0 {
            if let f = foes.first(where: { $0.k == CP.E_DOT && abs(cpWrapd($0.x - distractX)) < 40 }) { distractX = f.x }
        }
        foes.removeAll { !($0.alive || $0.deadT < 1.5) }
    }

    @discardableResult
    func defeatFoe(_ f: CPFoe, _ powered: Bool) -> Int {
        let g = hype!
        f.alive = false
        f.vh = 120
        stomps += 1
        g.hit(1, fever: feverGain(0.06))
        let base = f.k == CP.E_KITE ? 300 : 200
        let pts = scoreAt(base * (powered ? 2 : 1) + g.comboBonus(10), f.x, f.h + 6, "orange")
        app.audio.play(f.k == CP.E_KITE ? "pop" : "brick")
        g.hitstop(0.04)
        parts.burst(f.x, Double(sy(f.h)), 12, ["white", "yellow", CP.BIRD_COLS[Int(f.ph) % CP.BIRD_COLS.count]], 70, 0.5)
        if powered { floats.add(f.x, Double(sy(f.h) - 18), "POUNCE!", "yellow") }
        chain += 1
        if chain >= 2 {        // several critters in one leap: a sky chain
            let bonus = scoreAt(250 * chain)
            if chain == 3 {
                g.banner("SKY CHAIN!", "+\(bonus)", color: "orange", dur: 1.1, scale: 1, sound: "combo")
            } else {
                floats.add(f.x, Double(sy(f.h) - 28), "CHAIN x\(chain)", "orange")
            }
        }
        return pts
    }

    // ---------------------------------------------------------------- weather
    func updateWeather(_ dt: Double) {
        if wind > 0 {
            windT += dt
            if windOn > 0 {
                windOn -= dt
                if windOn <= 0 {
                    windT = 0
                    windDir = -windDir
                }
            } else if windT > 4.5 {
                windOn = 2.6
                app.audio.play("bubble")
            }
        }
        if hailRate > 0 {
            hailT -= dt
            if hailT <= 0 {
                hailT = 100 / hailRate * .random(in: 0.6 ... 1.4)
                hail.append(CPHail(cpFmod(x + .random(in: -70 ... 70), CP.FWd), cam + Double(H) + 6))
            }
            for hs in hail {
                if hs.warn > 0 {
                    hs.warn -= dt
                    hs.h = cam + Double(H) + 6
                    continue
                }
                hs.h -= 150 * dt
                if abs(cpWrapd(hs.x - x)) < 7 && abs(hs.h - (h + 7)) < 9 {
                    hs.alive = false
                    parts.burst(hs.x, Double(sy(hs.h)), 8, ["white", "sky"], 50, 0.4)
                    hurtCat("HAIL!")
                }
            }
            hail.removeAll { !$0.alive || $0.h <= cam - 20 }
        }
    }

    // ---------------------------------------------------------------- boss
    func updateBoss(_ dt: Double) {
        guard let b = boss else { return }
        b.update(dt)
        if b.state == "dead" {
            if b.dieT > 1.6 && state == "play" { stageClear() }
            return
        }
        if b.state != "fight" || rescueT > 0 { return }
        let cy = h + 7
        if let z = b.stompZone(), vh < 0 {
            let (zx, zh, hw) = z
            if abs(cpWrapd(x - zx)) < hw + 4 && zh - 8 <= h && h <= zh + 6 {
                let away = cpWrapd(x - zx) >= 0 ? 1.0 : -1.0
                if b.blocked(x) || b.inv > 0 {     // shields up / still reeling: SORA just bounces off
                    vh = jumpV()
                    kick = away * 160
                    pouncing = false
                    app.audio.play("tin")
                    floats.add(x, Double(sy(h) - 16), b.inv <= 0 ? "CLANG!" : "BOP!", "gray")
                    return
                }
                let dmg = pouncing ? 2 + lv("heavy") : 1
                b.hit(dmg)
                hype.hit(1, fever: feverGain(0.08))
                scoreAt(250 * dmg, x, h + 8, "orange")
                hype.hitstop(0.08)
                hype.flash("white", 0.12)
                app.shake(3, 0.2)
                app.audio.play(pouncing ? "explode" : "brick")
                parts.burst(x, Double(sy(h)), 14, ["white", "yellow", "orange"], 80, 0.5)
                vh = pouncing ? CP.POWER_V + 15 * Double(lv("heavy")) : jumpV() * 1.1
                kick = away * 200
                pouncing = false
                pounces = fullPounces()
                if b.state == "dead" {
                    bossDefeated()
                } else if b.phase == 2 && !milkGiven {     // a milk bottle for the second half
                    milkGiven = true
                    if let c = clouds.max(by: { $0.hd * 10 - abs(cpWrapd($0.cx() - x)) < $1.hd * 10 - abs(cpWrapd($1.cx() - x)) }) {
                        items.append(CPItem(CP.I_MILK, Double(Int(c.cx())), c.hd + 12))
                        floats.add(c.cx(), Double(sy(c.hd) - 24), "MILK!", "white")
                    }
                }
                return
            }
        }
        let nst = b.stompMinions(x, h, vh)
        if nst > 0 {
            vh = jumpV() * 1.05
            pounces = fullPounces()
            stomps += nst
            hype.hit(nst, fever: feverGain(0.05))
            scoreAt(300 * nst, x, h + 8, "lime")
            app.audio.play("brick")
        }
        if bonkT <= 0 && b.bump(x, cy, 5, 7) {
            bonkT = 0.4
            vh = min(vh, -60)
            kick = (cpWrapd(x - b.x) >= 0 ? 1 : -1) * 180
            pouncing = false
            app.audio.play("tin")
            floats.add(x, Double(sy(h) - 16), "BONK!", "gray")
        }
        if invuln <= 0 && b.touch(x, cy, 5, 7) { hurtCat() }
        for (dx, dh) in b.dots() where distractT <= 0 && invuln <= 0 && abs(cpWrapd(dx - x)) < 7 && abs(dh - cy) < 8 {
            distractT = 0.8
            distractX = dx
            floats.add(x, Double(sy(h) - 22), "!?", "red")
            app.audio.play("type")
        }
    }

    func bossDefeated() {
        let g = hype!
        app.audio.play("bossdown")
        g.banner("BOSS DOWN!", boss?.name, dur: 2.2, rainbow: true, scale: 2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(40, "coins")
        g.slowmo(0.3, 1.4)
        app.shake(6, 0.6)
        scoreAt(15000, CP.FWd / 2, 140)
        app.audio.music(nil)
    }

    // ---------------------------------------------------------------- bonus stages
    func updateBonus(_ dt: Double) {
        bonusLeft -= dt
        if st.bonus == "balloons" {
            balloonSpawn -= dt
            if balloonSpawn <= 0 && bonusLeft > 1 {
                let prog = 1 - bonusLeft / st.time
                balloonSpawn = 0.55 - 0.25 * prog
                let it = CPItem(CP.I_BALLOON, .random(in: 10 ... CP.FWd - 10), cam - 10)
                it.gold = hype.lucky(0.05 + 0.02 * Double(lv("luck")))
                it.ph = Double(Int.random(in: 0 ..< 6))
                items.append(it)
            }
            for it in items where it.k == CP.I_BALLOON {
                it.h += (34 + Double(4 * tier / 2) + it.ph * 3) * dt
                it.x = cpFmod(it.x + sin(stime * 2 + it.ph) * 10 * dt, CP.FWd)
            }
            items.removeAll { $0.h >= 220 }
        }
        if bonusLeft <= 0 {
            bonusLeft = 0
            hype.banner("TIME UP!", color: "yellow", dur: 1.2)
            stageClear()
        }
    }

    // ---------------------------------------------------------------- clear / tally
    func stageClear() {
        if state != "play" { return }
        state = "clear"
        stateT = 0
        pouncing = false
        rocketT = 0; balloonT = 0
        hail = []
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
        app.audio.music(nil)
        if boss != nil { return }
        app.audio.play("win")
        hype.slowmo(0.35, 0.9)
        if moon {
            hype.banner("MOON GATE!", "SORA MADE IT!", dur: 1.8, rainbow: true)
            hype.flash("white", 0.25)
            hype.shower(50, "stars")
        }
    }

    func updateClear(_ dt: Double) {
        // SORA floats happily into the moon gate (or just hovers after a boss / bonus)
        vh = 0
        if moon {
            h += 50 * dt
            x += cpWrapd(CP.FWd / 2 - x) * min(1, dt * 3)
            moveCam(min(cam + 30 * dt, goal - 120))
        }
        if Int(stateT * 10) % 3 == 0 {
            parts.sparkle(x + .random(in: -10 ... 10), Double(sy(h)) - .random(in: 0 ... 16), rainbow(Int(stateT * 10), 0))
        }
        if boss != nil && stateT < 1 { return }
        if stateT > 1.8 { beginTally() }
    }

    func beginTally() {
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("MOON GATE", factor(1000)))
            rows.append(("CLIMB TIME", factor(max(0, Int(Double(st.par) - stime)) * 40)))
            rows.append(("STARS \(gotStars)/\(starsTotal)", factor(gotStars * 20)))
            if !fish.isEmpty { rows.append(("FISH STARS \(gotFish)/\(fish.count)", factor(gotFish * 500))) }
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", factor(10000 + 2000 * tier)))
            rows.append(("NO DAMAGE", hurt ? 0 : factor(8000)))
        } else if st.bonus == "balloons" {
            rows.append(("BALLOONS x\(popped)", factor(popped * 100)))
            rows.append(("GOLDEN x\(golds)", factor(golds * 1000)))
        } else {
            rows.append(("STARS \(gotStars)/\(starsTotal)", factor(gotStars * 40)))
            rows.append(("BALLOONS x\(popped)", factor(popped * 150)))
            if st.bonus == "stars" { rows.append(("MOON REACHED", moon ? factor(5000) : 0)) }
        }
        rows.append(("BEST COMBO \(stageCombo)", factor(stageCombo * 40)))
        if st.kind != "bonus" { rows.append(("NO MISS", missed ? 0 : factor(5000))) }
        tally = rows.map { ($0.0, $0.1, 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        if st.kind != "bonus" && !missed {
            hype.banner("PURRFECT!", "NO MISS", dur: 1.8, rainbow: true, sound: "fever")
            hype.shower(40, "stars")
        }
    }

    func tallyLine() -> String {
        if st.kind == "boss" { return "SORA: THE SKY IS SAFE AGAIN!" }
        if st.kind == "bonus" { return "SORA: WHAT A TREAT!" }
        if !missed && Double(gotStars) >= Double(starsTotal) * 0.8 { return "SORA PURRS: PURRFECT CLIMB!" }
        if !missed { return "SORA: NOT A SINGLE SLIP!" }
        return "SORA: MEW... THAT WAS CLOSE!"
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

    func finishStage() {
        checkLife()
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "SORA REACHED THE MOON!", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "SWEET DREAMS!"
            state = "pick"
        } else {
            startStage(nextN!)
        }
    }

    // ---------------------------------------------------------------- drawing
    func skyCol(_ p0: Double) -> Color {
        let p = max(0, min(1, p0))
        if p < 0.5 { return lerpCol(theme[1], theme[2], p * 2) }
        return lerpCol(theme[2], theme[3], (p - 0.5) * 2)
    }

    func progressAt(_ alt: Double) -> Double {
        if st.kind == "boss" { return 0.85 }
        if isArena() { return 0.3 }
        return alt / max(1, goal)
    }

    override func render(_ s: Surface) {
        let f = field
        drawSky(f, t)
        for c in clouds where c.alive {
            let y = sy(c.hd)
            if -12 < y && y < H + 12 { drawCloudObj(f, c, y, t) }
        }
        for fi in fish { drawFish(f, fi, t) }
        for it in items {
            let y = sy(it.h)
            if -12 < y && y < H + 12 { cpDrawItem(f, it, Int(it.x), y, t) }
        }
        for fo in foes {
            let y = sy(fo.h)
            if -20 < y && y < H + 20 { cpDrawFoe(f, fo, Int(fo.x), y, t, tier) }
        }
        boss?.draw(f, t)
        drawCat(f, t)
        drawWeather(f, t)
        if let b = boss {
            if b.dark > 0 { drawDark(f, b.dark) }
            b.drawFx(f, t)
        }
        parts.draw(f)
        floats.draw(f)
        s.blit(f, CP.FX0, 0)
        drawPanels(s, t)
        if state == "intro" {
            drawIntro(s, t)
        } else if state == "tally" {
            drawTally(s, t)
        }
    }

    func drawSky(_ f: Surface, _ t: Double) {
        var y = 0
        while y < H {
            f.fillRect(skyCol(progressAt(cam + Double(H - y - 2))), 0, y, CP.FW, 4)
            y += 4
        }
        let p = progressAt(cam + Double(H) / 2)
        // twinkling stars come out as the sky darkens
        if p > 0.3 {
            let nst = Int(min(1, (p - 0.3) * 2) * 30)
            for i in 0 ..< nst {
                let sx = (i * 71 + 13) % CP.FW
                let sy0 = Int(cpFmod(Double(i * 37) + cam * 0.2, 210)) - 5
                let c = ["white", "lavender", "yellow", "white", "sky"][(Int(t * 3) + i) % 5]
                f.fillRect(col(c), sx, sy0, 1, i % 3 != 0 ? 1 : 2)
            }
        }
        // soft far clouds (parallax)
        let fc = theme[5]
        for i in 0 ..< 5 {
            let fx = (i * 97 + Int(t * Double(3 + i))) % (CP.FW + 80) - 40
            let fy = Int(cpFmod(Double(i * 61) + cam * 0.35, 260)) - 30
            let sc = skyCol(progressAt(cam + Double(H - fy)))
            let fcol = col(fc)
            let c = rgba(sc.cr + Int(Double(fcol.cr - sc.cr) * 0.28), sc.cg + Int(Double(fcol.cg - sc.cg) * 0.28),
                         sc.cb + Int(Double(fcol.cb - sc.cb) * 0.28))
            for j in 0 ..< 3 {
                let r = 9 + (j % 2) * 3
                f.ellipse(c, fx + j * 12 - r, fy + (j == 1 ? 1 : 0) - r, 2 * r + 1, 2 * r + 1)
            }
            f.rect(c, IRect(fx - 6, fy + 2, 36, 8), radius: 4)
        }
        // the town far below at the start
        if !isArena() && cam < 140 { drawTown(f, t) }
        // the moon gate
        if !isArena() && goal - cam < 300 { drawMoon(f, t) }
    }

    func drawTown(_ f: Surface, _ t: Double) {
        let y0 = sy(0)
        for i in 0 ..< 8 {
            let tx = i * 30 - 6
            let hh = 10 + (i * 7) % 12
            let c = ["choco", "brown", "purple", "deep"][i % 4]
            f.fillRect(col(c), tx, y0 + 4 + hh / 3, 30, H)
            f.polygon(col(i % 2 != 0 ? "red" : "orange"), [(Double(tx - 2), Double(y0 + 5 + hh / 3)), (Double(tx + 15), Double(y0 - 4 + hh / 3)),
                                                         (Double(tx + 32), Double(y0 + 5 + hh / 3))])
            var wy = y0 + 12 + hh / 3
            while wy < H {
                for wx in [tx + 6, tx + 18] {
                    let lit = cpMod(i + wx + wy, 3)
                    f.fillRect(col(lit != 0 ? "yellow" : "ink"), wx, wy, 4, 5)
                }
                wy += 10
            }
        }
        // SORA's own rooftop with a chimney
        f.fillRect(col("darkgray"), CP.FW / 2 + 30, y0 - 14, 10, 14)
        f.fillRect(col("gray"), CP.FW / 2 + 29, y0 - 16, 12, 3)
        f.fillRect(col("ink"), 0, y0, CP.FW, 4)
        var rx = 0
        while rx < CP.FW { f.fillRect(col("red"), rx, y0, 7, 2); rx += 8 }
    }

    func drawMoon(_ f: Surface, _ t: Double) {
        let gy = sy(goal)
        let cx = CP.FW / 2
        let my = gy - 40
        let near = h > goal - 160
        f.circle(col("yellow"), cx, my, 25)
        f.circle(col("cream"), cx, my, 23)
        for (dx, dy, r) in [(-9, -8, 4), (8, 6, 3), (11, -10, 2), (-4, 11, 2)] { f.circle(col("peach"), cx + dx, my + dy, r) }
        // sleepy moon face, it wakes up when SORA comes near
        Cute.eyes(f, cx, my + 1, 6, look: 0, mood: near ? "happy" : "sleepy")
        Cute.mouth(f, cx, my + 6, near ? "happy" : "flat")
        Cute.blush(f, cx, my + 4, 9)
        // the gate: an arch of stars
        for i in 0 ..< 13 {
            let a = Double.pi * Double(i) / 12
            let ax = cx + Int(cos(a) * 70)
            let ay = gy - Int(sin(a) * 34)
            let c = near ? rainbow(i, t) : ((i + Int(t * 4)) % 3 != 0 ? "yellow" : "white")
            f.fillRect(col(c), ax - 1, ay, 3, 1)
            f.fillRect(col(c), ax, ay - 1, 1, 3)
        }
        var gx = cx - 70
        while gx < cx + 71 {
            f.fillRect(col((gx / 6 + Int(t * 8)) % 2 != 0 ? "yellow" : "white"), gx, gy, 3, 1)
            gx += 6
        }
    }

    func drawCloudObj(_ f: Surface, _ c: CPCloud, _ y: Int, _ t: Double) {
        let cxi = Int(c.x)
        let k = c.k
        if k == CP.FLOOR {
            if isArena() {       // BALLOON BASH: a bank of clouds to bounce on
                for i in 0 ..< 7 { cpDrawCloud(f, i * 32, y, 32, CP.KF, t, c.squash, face: i % 2 == 0) }
            }
            return
        }
        let sq = c.squash
        if k == CP.KG {
            let u = state == "play" || state == "clear" ? ghostU(c) : 0
            if u >= 0.7 {
                var xx = cxi
                while xx < cxi + c.w {
                    for xd in [0, -CP.FW, CP.FW] {
                        f.fillRect(col("lavender"), xx + xd, y + 3, 2, 1)
                        f.fillRect(col("lavender"), xx + xd, y + 9, 2, 1)
                    }
                    xx += 4
                }
                return
            }
            if u >= 0.6 && Int(t * 16) % 2 != 0 { return }
        }
        var zs = 0
        if k == CP.KZ && (state == "play" || state == "clear") {
            let u = zapU(c)
            zs = u >= 0.85 ? 2 : (u >= 0.62 ? 1 : 0)
        }
        if c.temp > 0 && c.temp < 0.8 && Int(t * 12) % 2 != 0 { return }
        for xd in [0, -CP.FW, CP.FW] where -c.w - 8 < cxi + xd && cxi + xd < CP.FW + 8 {
            cpDrawCloud(f, cxi + xd, y, c.w, k, t, sq, state: zs, wind: c.a)
        }
        if k == CP.KZ && zs == 2 {
            var bx = cpMod(Int(c.cx()), CP.FW)
            var yy = y + 10
            for i in 0 ..< 7 {
                let nx = bx + ((i + Int(t * 20)) % 2 != 0 ? 2 : -2)
                f.line(col("yellow"), bx, yy, nx, yy + 10, width: 2)
                f.fillRect(col("white"), nx, yy + 10, 1, 1)
                bx = nx; yy += 10
            }
        }
    }

    func drawFish(_ f: Surface, _ fi: CPFish, _ t: Double) {
        if abs(Double(fi.h) - (cam + Double(H) / 2)) > 140 { return }
        let lit = fi.done
        let lc = lit ? col(fi.gold ? "yellow" : "sky") : col("darkgray")
        for (a, b) in fi.lines {
            let x0 = fi.stars[a].x, h0 = fi.stars[a].h
            let dx = cpWrapd(fi.stars[b].x - x0)
            let dh = fi.stars[b].h - h0
            let nn = max(1, Int(max(abs(dx), abs(dh)) / (lit ? 1 : 3)))
            for k in 0 ... nn {
                let px = cpMod(Int(x0 + dx * Double(k) / Double(nn)), CP.FW)
                f.fillRect(lc, px, sy(h0 + dh * Double(k) / Double(nn)), 1, 1)
            }
        }
        for s in fi.stars {
            let y = sy(s.h)
            let sx = Int(s.x)
            if s.got {
                let c = fi.gold ? "yellow" : "white"
                f.fillRect(col(c), sx - 1, y, 3, 1)
                f.fillRect(col(c), sx, y - 1, 1, 3)
            } else {
                let tw = Int(t * 6 + Double(sx)) % 4
                let c = fi.gold ? "yellow" : (tw != 0 ? "white" : "sky")
                f.fillRect(col(c), sx - 2, y, 5, 1)
                f.fillRect(col(c), sx, y - 2, 1, 5)
                f.fillRect(col("white"), sx, y, 1, 1)
            }
        }
        if fi.glow > 0 && Int(t * 10) % 2 != 0 { drawText(f, "FISH!", fi.x, sy(Double(fi.h)) - 16, "yellow", align: .center) }
    }

    func drawCat(_ f: Surface, _ t: Double) {
        let cxi = Int(x)
        let y = sy(h)
        if invuln > 0 && state == "play" && Int(t * 14) % 2 != 0 && rescueT <= 0 { return }
        if y > H + 20 || y < -30 { return }
        // accessories behind SORA
        if balloonT > 0 || rescueT > 0 {
            let bc = rescueT > 0 ? "yellow" : balloonC
            for xd in [0, -CP.FW, CP.FW] {
                cpDrawBalloon(f, cxi + xd + 3, y - 30, bc, t)
                f.line(col("white"), cxi + xd + 3, y - 22, cxi + xd + 1, y - 12)
            }
        }
        if rocketT > 0 { for xd in [0, -CP.FW, CP.FW] { cpDrawRocket(f, cxi + xd, y + 4, t, flame: true) } }
        if parasolT > 0 && vh < 0 { for xd in [0, -CP.FW, CP.FW] { cpDrawParasol(f, cxi + xd, y - 22, t) } }
        if state == "intro" && isRocketRide { for xd in [0, -CP.FW, CP.FW] { cpDrawRocket(f, cxi + xd, y + 4, t) } }
        var name = "cp_fall", frame = 0
        if state == "intro" {
            name = "cp_idle"
            frame = Int(t * 1.3) % 5 == 0 ? 1 : 0
        } else if state == "clear" || state == "tally" {
            name = "cp_happy"
        } else if hurtT > 0 {
            name = "cp_hurt"
        } else if pouncing {
            name = "cp_ball"
        } else if landT > 0 {
            name = "cp_land"
        } else if distractT > 0 {
            name = "cp_fall"
        } else if vh > 130 || balloonT > 0 || rescueT > 0 || rocketT > 0 {
            name = "cp_up"
        } else if vh > -110 {
            name = "cp_star"
        }
        let flip = pouncing && Int(t * 14) % 2 == 1
        let spr = sprite(name, frame, flip: flip)
        if hype.feverOn && state == "play" {
            for i in 1 ..< 4 {
                let ty = y - 8 + Int(vh * 0.02 * Double(i))
                f.circle(col(rainbow(i, t)), cxi - Int(vx * 0.02 * Double(i)), ty, 3 - i / 2)
            }
        }
        for xd in [0, -CP.FW, CP.FW] where -20 < cxi + xd && cxi + xd < CP.FW + 20 {
            if name != "cp_ball" { drawTail(f, cxi + xd, y, t) }
            f.blit(spr, cxi + xd - 8, y - 16)
            if shield {
                let yy = y - 4 + (name == "cp_land" ? 2 : 0)
                f.circle(col("yellow"), cxi + xd, yy, 2)
                f.fillRect(col("orange"), cxi + xd, yy + 1, 1, 1)
            }
        }
        if pouncing {
            for i in 0 ..< 3 { f.fillRect(col("white"), cxi - 6 + i * 6, y - 22 - (Int(t * 40) + i * 5) % 12, 1, 4) }
        }
        if distractT > 0 && Int(t * 6) % 2 != 0 { drawText(f, "!?", cxi, y - 26, "red", align: .center) }
    }

    func drawTail(_ f: Surface, _ x0: Int, _ y: Int, _ t: Double) {
        let side = -face
        let sway = sin(t * 7) * 2
        var pts: [(Int, Int)] = []
        for i in 0 ..< 5 { pts.append((x0 + side * (5 + i), y - 4 - i * 2 + Int(sway * Double(i) / 4))) }
        for (px, py) in pts { f.fillRect(col("black"), px - 1, py - 1, 3, 3) }
        for (i, (px, py)) in pts.enumerated() { f.fillRect(col(i == 4 ? "lavender" : "white"), px, py, 1, 1) }
    }

    func drawWeather(_ f: Surface, _ t: Double) {
        if wind > 0 && state == "play" {
            if windOn > 0 || (windT > 3.5 && Int(t * 8) % 2 != 0) {
                let d = windDir
                for i in 0 ..< 6 {
                    let wy = 30 + i * 28 + Int(sin(t * 3 + Double(i)) * 4)
                    let wx = Int(cpFmod(Double(i * 53) + t * 140 * d, Double(CP.FW + 40))) - 20
                    let c = windOn > 0 ? "white" : "yellow"
                    f.fillRect(col(c), wx, wy, 12, 1)
                    f.fillRect(col(c), wx + (d > 0 ? 12 : -2), wy - 1, 2, 3)
                }
            }
        }
        for hs in hail {
            if hs.warn > 0 {
                if Int(t * 10) % 2 != 0 {
                    let hx = Double(Int(hs.x))
                    f.polygon(col("red"), [(hx - 4, 2), (hx + 4, 2), (hx, 7)])
                }
                continue
            }
            let y = sy(hs.h)
            f.circle(col("sky"), Int(hs.x), y, 4)
            f.circle(col("white"), Int(hs.x) - 1, y - 1, 2)
        }
        if fog > 0 {
            let top = H - 14 + Int(sin(t * 2) * 2)
            var fx = 0
            while fx < CP.FW {
                let yy = top + Int(sin(t * 3 + Double(fx) * 0.2) * 2)
                f.fillRect(col("lavender"), fx, yy, 6, H - yy)
                fx += 6
            }
            fx = 0
            while fx < CP.FW { f.fillRect(col("white"), fx, top + 4 + (fx / 2) % 2 * 3, 1, 1); fx += 2 }
        }
    }

    /// NOCTURNE's eclipse: darkness everywhere except a circle of light around SORA.
    func drawDark(_ s: Surface, _ a: Double) {
        let cx = Int(x)
        let cy = sy(h) - 8
        let r = 44
        let dark = rgba(12, 8, 24, Int(220 * a))
        var y = 0
        while y < H {
            let dy = y - cy
            if abs(dy) < r {
                let half = Int(Double(r * r - dy * dy).squareRoot())
                s.fillRect(dark, 0, y, max(0, cx - half), 2)
                s.fillRect(dark, cx + half, y, max(0, CP.FW - cx - half), 2)
            } else {
                s.fillRect(dark, 0, y, CP.FW, 2)
            }
            y += 2
        }
    }

    func drawPanels(_ s: Surface, _ t: Double) {
        let acc = theme[4]
        for x0 in [0, CP.FX0 + CP.FW] {
            s.fillRect(col("night"), x0, 0, CP.FX0, H)
            for i in 0 ..< 10 {
                s.fillRect(col((i + Int(t * 2)) % 4 != 0 ? "deep" : "lavender"), x0 + (i * 17 + 5) % CP.FX0, (i * 41 + 7) % H, 1, 1)
            }
        }
        s.fillRect(col(acc), CP.FX0 - 1, 0, 1, H)
        s.fillRect(col(acc), CP.FX0 + CP.FW, 0, 1, H)
        // left: score, hi, the altitude meter
        drawText(s, "SCORE", 4, 3, "lavender", shadow: nil)
        drawText(s, String(format: "%07d", score), 4, 12, "white", shadow: nil)
        drawText(s, "HI", 4, 24, "lavender", shadow: nil)
        drawText(s, String(format: "%07d", max(best, score)), 4, 33, "gray", shadow: nil)
        if st.kind == "bonus" {
            let secs = Int(bonusLeft.rounded(.up))
            drawText(s, "TIME", 24, 60, "lavender", align: .center, shadow: nil)
            drawText(s, String(format: "%02d", secs), 24, 72, secs > 5 || Int(t * 6) % 2 != 0 ? "yellow" : "red", scale: 2,
                     align: .center, shadow: nil, outline: "ink")
            drawText(s, st.bonus == "balloons" ? "POPS" : "STARS", 24, 104, "lavender", align: .center, shadow: nil)
            drawText(s, "\(st.bonus != "balloons" ? gotStars : popped)", 24, 114, "white", align: .center, shadow: nil)
        } else if let b = boss {
            drawText(s, "BOSS", 24, 50, "red", align: .center, shadow: nil)
            let hpf = max(0, Double(b.hp) / Double(max(1, b.maxhp)))
            s.rect(col("ink"), IRect(18, 62, 12, 124), radius: 3)
            let hh = Int(120 * hpf)
            s.fillRect(col("red"), 20, 64 + 120 - hh, 8, hh)
            s.fillRect(col("pink"), 20, 64 + 120 - hh, 2, hh)
        } else {
            let top = 58, bot = 184
            s.rect(col("ink"), IRect(19, top, 10, bot - top), radius: 4)
            let p = max(0, min(1, h / max(1, goal)))
            let fh = Int(Double(bot - top - 4) * p)
            s.fillRect(col(acc), 21, bot - 2 - fh, 6, fh)
            s.circle(col("yellow"), 24, top - 7, 6)
            s.circle(col("cream"), 24, top - 7, 5)
            s.fillRect(col("peach"), 22, top - 9, 2, 2)
            s.blit(sprite("cp_happy"), 16, bot - 2 - fh - 10)
            drawText(s, "\(Int(max(0, h) / 10))M", 24, 190, "white", align: .center, shadow: nil)
        }
        // right: stage, lives, fever, power-ups, stars
        let x0 = CP.FX0 + CP.FW + 3
        drawText(s, "STAGE", x0, 3, "lavender", shadow: nil)
        drawText(s, "\(n)", x0 + 21, 12, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        hearts(s, x0, 30, lives, maxShow: 4)
        drawText(s, "FEVER", x0, 42, hype.feverOn ? rainbow(0, t) : "orange", shadow: nil)
        s.fillRect(col("darkgray"), x0, 51, 40, 4)
        if hype.feverOn {
            for i in 0 ..< 40 { s.fillRect(col(rainbow(i / 5, t)), x0 + i, 51, 1, 4) }
        } else {
            s.fillRect(col("orange"), x0, 51, Int(40 * hype.fever), 4)
        }
        var y = 61
        // pounces left this jump
        drawText(s, "POUNCE", x0, y, "pink", shadow: nil)
        for i in 0 ..< fullPounces() {
            s.circle(col(i < pounces ? "hotpink" : "darkgray"), x0 + 4 + i * 9, y + 13, 3)
            s.fillRect(col(i < pounces ? "white" : "gray"), x0 + 3 + i * 9, y + 12, 1, 1)
        }
        y += 22
        for (name, v, full, c) in [("ROCKET", rocketT, 2.2 + 0.45 * Double(lv("rocket")), "orange"),
                                   ("PARASOL", parasolT, 10.0, "pink"), ("MAGNET", magnetT, 12.0, "red")]
            where v > 0 && (v > 2 || Int(t * 8) % 2 != 0) {
            drawText(s, name, x0, y, c, shadow: nil)
            s.fillRect(col("darkgray"), x0, y + 8, 40, 2)
            s.fillRect(col(c), x0, y + 8, Int(40 * min(1, v / full)), 2)
            y += 14
        }
        if shield {
            cpIconBell(s, x0 + 6, y + 5, t)
            drawText(s, "BELL", x0 + 15, y + 2, "yellow", shadow: nil)
            y += 14
        }
        if cushion > 0 {
            cpDrawCloud(s, x0, y + 2, 14, CP.KF, t, 0, face: false)
            drawText(s, "x\(cushion)", x0 + 18, y + 3, "white", shadow: nil)
            y += 14
        }
        if st.kind != "boss" {
            s.blit(sprite("star"), x0, 168)
            drawText(s, "\(gotStars)", x0 + 10, 168, "yellow", shadow: nil)
            if !fish.isEmpty {
                cpDrawFishIcon(s, x0 + 4, 186, "sky")
                drawText(s, "\(gotFish)/\(fish.count)", x0 + 15, 183, "sky", shadow: nil)
            }
        }
        if let b = boss, b.state != "dead", state == "play" || state == "intro" {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: 2, x: CP.FX0 + 4, w: CP.FW - 8)
        }
    }

    func weatherLine() -> String {
        var w: [String] = []
        if wind > 0 { w.append("GUSTS") }
        if fog > 0 { w.append("RISING FOG") }
        if hailRate > 0 { w.append("HAIL") }
        return w.isEmpty ? "" : "WEATHER: " + w.joined(separator: " + ")
    }

    func drawIntro(_ s: Surface, _ t: Double) {
        let cx = CP.FX0 + CP.FW / 2
        if st.kind == "boss" {
            if Int(t * 4) % 2 != 0 {
                var wx = CP.FX0 - 20
                while wx < CP.FX0 + CP.FW + 20 {
                    s.polygon(col("red"), [(Double(wx), 108), (Double(wx + 10), 108), (Double(wx + 20), 116), (Double(wx + 10), 116)])
                    s.polygon(col("red"), [(Double(wx), 158), (Double(wx + 10), 158), (Double(wx + 20), 166), (Double(wx + 10), 166)])
                    wx += 20
                }
            }
            panel(s, IRect(cx - 100, 120, 200, 34), fill: "black", border: "red")
            drawText(s, "WARNING!!", cx, 124, Int(t * 6) % 2 != 0 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.name) APPROACHES", cx, 141, "white", align: .center, shadow: nil)
            return
        }
        let weather = weatherLine()
        let hgt = 56 + (st.newLine.isEmpty ? 0 : 10) + (weather.isEmpty ? 0 : 10)
        let y0 = 34
        panel(s, IRect(cx - 104, y0, 208, hgt), fill: "ink", border: st.kind == "bonus" ? "yellow" : theme[4])
        if st.kind == "bonus" {
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), cx - textWidth(title, 2) / 2 + i * 12, y0 + 6 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            let sub = ["stars": "GRAB STARS - CLIMB TO THE MOON!", "rocket": "RIDE THE ROCKET, CATCH STARS!",
                       "balloons": "POP ALL THE BALLOONS!"][st.bonus] ?? ""
            drawText(s, st.name, cx, y0 + 26, "yellow", align: .center)
            drawText(s, sub, cx, y0 + 38, "white", align: .center, shadow: nil)
            return
        }
        drawText(s, "STAGE \(n)", cx, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, theme[0], cx, y0 + 25, "lavender", align: .center, shadow: nil)
        drawText(s, st.name, cx, y0 + 35, "white", align: .center, shadow: nil)
        var y = y0 + 46
        if !st.newLine.isEmpty {
            drawText(s, st.newLine, cx, y, Int(t * 4) % 2 != 0 ? "mint" : "lime", align: .center, shadow: nil)
            y += 10
        }
        if !weather.isEmpty {
            drawText(s, weather, cx, y, "sky", align: .center, shadow: nil)
            y += 10
        }
        drawText(s, CPData.quips[(n * 3) % CPData.quips.count], cx, y, "pink", align: .center, shadow: nil)
    }

    func drawTally(_ s: Surface, _ t: Double) {
        let cx = CP.FX0 + CP.FW / 2
        let hgt = 46 + tally.count * 11
        let y0 = 84
        panel(s, IRect(cx - 98, y0, 196, hgt), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, cx, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 20 + i * 11
            drawText(s, row.label, cx - 90, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", cx + 90, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        drawText(s, tallyLine(), cx, y0 + hgt - 22, "pink", align: .center, shadow: nil)
        if tallyI >= tally.count && Int(t * 3) % 2 != 0 {
            drawText(s, "TAP POUNCE", cx, y0 + hgt - 11, "lavender", align: .center, shadow: nil)
        }
    }

    // ---------------------------------------------------------------- carousel thumbnail
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        var y = 0
        while y < h { s.fillRect(lerpCol("sky", "deep", 1 - Double(y) / Double(h)), 0, y, w, 3); y += 3 }
        for i in 0 ..< 12 {
            s.fillRect(col((i + Int(t * 3)) % 3 != 0 ? "white" : "yellow"), (i * 37) % w, (i * 23) % (h / 2), 1, 1)
        }
        s.circle(col("yellow"), w - 18, 14, 9)
        s.circle(col("cream"), w - 18, 14, 8)
        Cute.eyes(s, w - 18, 14, 3, look: 0, mood: "sleepy")
        let off = cpFmod(t * 24, 30)
        for i in 0 ..< 4 {
            let cy = Int(Double(i * 30 - 20) + off)
            let cx = (i * 47 + 20) % (w - 40) + 4
            cpDrawCloud(s, cx, cy, i % 2 != 0 ? 32 : 24, i == 2 ? CP.KS : CP.KF, t)
        }
        let by = Double(h) - 13 - abs(sin(t * 3)) * 30
        let bx = w / 2 + Int(sin(t * 1.3) * 26)
        cpDrawCloud(s, bx - 16, h - 14, 32, CP.KF, t, abs(sin(t * 3)) < 0.15 ? 0.15 : 0)
        let name = abs(cos(t * 3)) < 0.4 ? "cp_star" : (cos(t * 3) > 0 ? "cp_up" : "cp_fall")
        s.blit(sprite(name), bx - 8, Int(by) - 16)
        for (i, (fx, fy)) in [(10, 30), (16, 25), (16, 35), (24, 30), (29, 25), (29, 35)].enumerated() {
            let c = (i + Int(t * 4)) % 6 != 0 ? "yellow" : "white"
            s.fillRect(col(c), fx - 1, fy, 3, 1)
            s.fillRect(col(c), fx, fy - 1, 1, 3)
        }
    }
}
