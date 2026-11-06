// SOAP HOP bosses, every 10th stage (port of games/soap_hop_boss.py - keep the two in step).
// Telegraphed patterns; the stage table (SHData) decides HP, speed and the pattern list.
import Foundation

private let BT = 8, BTOP = 12
private let BFLOOR = Double(BTOP + 21 * BT)
private let BLEFT = Double(2 * BT), BRIGHT = Double(W - 2 * BT)
private let RADIUS: [String: Double] = ["king": 15, "mop": 15, "vac": 16, "sock": 8, "soot": 16, "grime": 20]
private let MINION: [String: String] = ["king": "g", "mop": "g", "vac": "f", "sock": "f", "soot": "w", "grime": "b"]
private let FLYING = ["vac", "soot"]

final class SHBoss {
    let kind: String, name: String
    var hp: Int, maxhp: Int
    let pats: [String]
    let spd: Double
    let r: Double
    var x = Double(W) / 2 + 56, y = -40.0
    let homeY: Double
    var vx = 0.0, vy = 0.0
    var face = -1
    var mode = "enter", modeT = 0.0, step = 0
    var patI = 0, count = 0
    var flash = 0.0
    var phase = 1
    var squash = 0.0, lift = 0.0, inhale = 0.0, charge = 0.0, walk = 0.0
    var t = 0.0
    var trail: [(Int, Int)] = []
    var tx = Double(W) / 2
    var dead = false

    init(_ sd: SHStage) {
        kind = sd.boss; name = sd.nm
        hp = sd.hp; maxhp = sd.hp
        pats = sd.pat; spd = sd.spd
        r = RADIUS[kind] ?? 15
        if FLYING.contains(kind) { homeY = Double(BTOP + 40) } else if kind == "sock" { homeY = Double(BTOP + 60) } else { homeY = BFLOOR - r }
    }

    // ------------------------------------------------------------------ helpers
    func segs() -> [(Int, Int)] {
        if kind != "sock" { return [] }
        let n = 4 + Int(ceil(8 * Double(hp) / Double(maxhp)))
        var out: [(Int, Int)] = []
        for i in 1 ... n {
            let k = trail.count - 1 - i * 4
            if k < 0 { break }
            out.append(trail[k])
        }
        return out
    }

    var ground: Bool { kind == "king" || kind == "grime" || kind == "mop" }
    var speed: Double { spd * (1 + 0.15 * Double(phase - 1)) }

    func hurt(_ sc: SoapHop, _ n: Int, _ label: String? = nil) {
        if mode == "enter" || mode == "dying" || dead { return }
        hp -= n
        flash = 0.12
        sc.add(20 * n)
        sc.hype.hit(1, fever: 0.012)
        sc.app.audio.play("brick")
        if let l = label {
            sc.floats.add(x, y - r - 8, l, "orange")
            sc.hype.hitstop(0.05)
            sc.app.shake(2, 0.15)
        }
        let np = 1 + (Double(hp) <= Double(maxhp) * 0.66 ? 1 : 0) + (Double(hp) <= Double(maxhp) * 0.33 ? 1 : 0)
        if hp <= 0 {
            hp = 0
            mode = "dying"; modeT = 0
            sc.bossDefeated()
        } else if np > phase {
            phase = np
            sc.hype.banner("GRRR!!", "IT'S GETTING ANGRY", color: "red", dur: 1.0, scale: 2, sound: "boom")
            sc.app.shake(4, 0.4)
            mode = "rest"; modeT = 0.6
        }
    }

    /// Does a circle touch the weak point?
    func hits(_ px: Double, _ py: Double, _ rad: Double) -> Bool { hypot(px - x, py - y) < r + rad }

    /// Does a circle touch any harmful part (body or sock segments)?
    func touches(_ px: Double, _ py: Double, _ rad: Double) -> Bool {
        if hits(px, py, rad) { return true }
        return segs().contains { hypot(px - Double($0.0), py - Double($0.1)) < 5 + rad }
    }

    // ------------------------------------------------------------------ frame
    func update(_ sc: SoapHop, _ dt: Double) {
        t += dt
        flash -= dt
        let p = sc.player
        if kind == "sock" {
            trail.append((Int(x), Int(y)))
            if trail.count > 80 { trail.removeFirst() }
        }
        if mode == "enter" {
            y += (homeY - y) * min(1, dt * 2.2)
            if sc.state == "play" { mode = "rest"; modeT = 1.0 }
            return
        }
        if mode == "dying" {
            modeT += dt
            x += Double.random(in: -1.5 ... 1.5)
            if modeT > 1.8 && !dead { dead = true; sc.bossBurst() }
            return
        }
        let sp = speed
        squash *= pow(0.85, dt * 60)
        if mode == "rest" {
            idle(sc, dt, sp)
            modeT -= dt
            if modeT <= 0 { nextPattern(sc) }
        } else {
            switch mode {
            case "hop": pHop(sc, dt, sp, p)
            case "slam": pSlam(sc, dt, sp, p)
            case "walk": pWalk(sc, dt, sp, p)
            case "splash": pSplash(sc, dt, sp, p)
            case "spit": pSpit(sc, dt, sp, p)
            case "minions": pMinions(sc, dt, sp, p)
            case "drift": pDrift(sc, dt, sp, p)
            case "inhale": pInhale(sc, dt, sp, p)
            case "puff": pPuff(sc, dt, sp, p)
            case "rain": pRain(sc, dt, sp, p)
            case "bolt": pBolt(sc, dt, sp, p)
            case "slither": pSlither(sc, dt, sp, p)
            case "lunge": pLunge(sc, dt, sp, p)
            default: rest(sc)
            }
        }
        let airborne = mode == "hop" || (mode == "slam" && kind != "mop")
        if ground && !airborne {
            vy = min(vy + 620 * dt, 300)
            y += vy * dt
            if y >= BFLOOR - r { y = BFLOOR - r; vy = 0 }
        }
        x = max(BLEFT + r, min(BRIGHT - r, x))
        if sc.state == "play" && touches(p.cx, p.cy, 5) { sc.hurt() }
    }

    func idle(_ sc: SoapHop, _ dt: Double, _ sp: Double) {
        if FLYING.contains(kind) {
            x += (tx - x) * min(1, dt * 0.8)
            y = homeY + sin(t * 2) * 6
        } else if kind == "sock" {
            slither(dt, 38 * sp)
        }
        inhale = max(0, inhale - dt * 2)
        charge = max(0, charge - dt * 2)
        if lift > 0 { lift = max(0, lift - dt * 2) } else if lift < 0 { lift = min(0, lift + dt * 2) }
    }

    func nextPattern(_ sc: SoapHop) {
        var nm = pats[patI % pats.count]
        patI += 1
        if nm == "minions" && sc.minionCount() >= 3 { nm = "spit" }
        mode = nm; modeT = 0; step = 0
        let p = sc.player
        face = p.cx > x ? 1 : -1
        if nm == "hop" {
            count = 2 + phase
        } else if nm == "drift" {
            tx = Double.random(in: BLEFT + 40 ... BRIGHT - 40)
        } else if nm == "slither" {
            let a = Double.random(in: 0.4 ... 1.1) * (Bool.random() ? 1 : -1)
            vx = cos(a) * Double(face); vy = sin(a)
        }
    }

    func rest(_ sc: SoapHop, _ base: Double = 1.1) {
        mode = "rest"
        modeT = max(0.35, (base - 0.12 * Double(phase - 1)) / spd)
        step = 0
    }

    // ------------------------------------------------------------------ patterns
    func pHop(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        if step == 0 {
            squash = 0.6
            if modeT > 0.38 / sp {
                step = 1; modeT = 0
                face = p.cx > x ? 1 : -1
                vy = -(250 + 25 * Double(phase))
                vx = Double(face) * (70 + 15 * Double(phase)) * sp
                sc.app.audio.play("jump")
            }
        } else {
            vy += 620 * dt
            x += vx * dt
            y += vy * dt
            if x < BLEFT + r || x > BRIGHT - r { vx = -vx }
            if y >= BFLOOR - r && vy > 0 {
                y = BFLOOR - r; vy = 0
                squash = 0.5
                sc.app.shake(2, 0.15)
                sc.parts.burst(x, BFLOOR - 2, 8, ["gray", "white"], 50, 0.4)
                if phase >= 2 || kind == "grime" {
                    sc.shoot("wave", x - r, BFLOOR, -90 * sp, 0)
                    sc.shoot("wave", x + r, BFLOOR, 90 * sp, 0)
                }
                count -= 1
                if count > 0 { step = 0; modeT = 0 } else { rest(sc) }
            }
        }
    }

    func pSlam(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        if kind != "mop" {
            if step == 0 {
                squash = 0.8
                if modeT > 0.55 / sp {
                    step = 1
                    vy = -340
                    vx = (p.cx - x) * 0.9
                    sc.app.audio.play("jump")
                }
            } else {
                vy += 620 * dt
                x += vx * dt
                y += vy * dt
                if y >= BFLOOR - r && vy > 0 {
                    y = BFLOOR - r; vy = 0
                    squash = 0.8
                    quake(sc, sp)
                    rest(sc)
                }
            }
            return
        }
        if step == 0 || step == 2 {
            lift = min(1, modeT / (0.7 / sp))
            if modeT > 0.7 / sp {
                step += 1; modeT = 0
                lift = -1
                quake(sc, sp)
            }
        } else if step == 1 {
            if phase >= 2 && modeT > 0.45 { step = 2; modeT = 0 } else if phase < 2 && modeT > 0.4 { rest(sc) }
        } else {
            if modeT > 0.4 { rest(sc) }
        }
    }

    func quake(_ sc: SoapHop, _ sp: Double) {
        sc.app.shake(4, 0.35)
        sc.app.audio.play("boom")
        let v = (100 + 20 * Double(phase)) * sp
        sc.shoot("wave", x - r, BFLOOR, -v, 0)
        sc.shoot("wave", x + r, BFLOOR, v, 0)
        sc.parts.burst(x, BFLOOR - 2, 14, ["white", "sky", "gray"], 70, 0.5)
    }

    func pWalk(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        face = p.cx > x ? 1 : -1
        x += Double(face) * 38 * sp * dt
        walk += dt
        if modeT > 1.6 { rest(sc, 0.6) }
    }

    func pSplash(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        lift = 0.5
        if step == 0 && modeT > 0.45 / sp {
            step = 1
            sc.app.audio.play("bubble")
            for _ in 0 ..< 3 + phase {
                sc.shoot("water", x + Double(face * 10), y - 18, Double.random(in: -110 ... 110), Double.random(in: -270 ... -200))
            }
        }
        if modeT > 0.9 { rest(sc) }
    }

    func pSpit(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        if step == 0 { squash = -0.25 }
        charge = 1
        if step == 0 && modeT > 0.6 / sp {
            step = 1
            sc.app.audio.play("shoot")
            let n = phase == 1 ? 3 : 5
            let ox = x, oy = y + (FLYING.contains(kind) ? r * 0.3 : 0)
            let base = atan2(p.cy - oy, p.cx - ox)
            for i in 0 ..< n {
                let a = base + (Double(i) - Double(n - 1) / 2) * 0.28
                sc.shoot("dust", ox + cos(a) * r, oy + sin(a) * r, cos(a) * 85 * sp, sin(a) * 85 * sp)
            }
        }
        if modeT > 0.95 / sp { rest(sc) }
    }

    func pMinions(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        squash = 0.2 * sin(modeT * 30)
        if step == 0 && modeT > 0.6 {
            step = 1
            sc.app.audio.play("trap")
            for side in [-1.0, 1.0] where sc.minionCount() < 3 {
                sc.spawnMinion(MINION[kind] ?? "g", x + side * (r + 8), y - 4)
            }
        }
        if modeT > 1.0 { rest(sc) }
    }

    func pDrift(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        x += max(-50 * sp * dt, min(50 * sp * dt, tx - x))
        y = homeY + sin(t * 2) * 6
        if modeT > 1.6 {
            tx = max(BLEFT + 40, min(BRIGHT - 40, p.cx + Double.random(in: -60 ... 60)))
            rest(sc, 0.5)
        }
    }

    func pInhale(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        if step == 0 {
            inhale = min(0.5, modeT)
            if modeT > 0.55 { step = 1; modeT = 0; sc.app.audio.play("trap") }
            return
        }
        inhale = 1
        let mx = x, my = y + 6
        if sc.state == "play" && abs(p.cx - mx) < 150 { p.x += (mx > p.cx ? 1 : -1) * 45 * dt }
        for b in sc.bubbles where !b.dead && b.kind == "normal" {
            let d = hypot(mx - b.x, my - b.y)
            if d < 10 {
                b.dead = true
                sc.parts.burst(b.x, b.y, 6, ["white", "sky"], 40, 0.3)
                if b.enemy != nil { hurt(sc, 4, "GULP!!") } else { hurt(sc, 2, "GULP!") }
            } else if d < 140 {
                b.x += (mx - b.x) / d * 100 * dt
                b.y += (my - b.y) / d * 100 * dt
            }
        }
        if modeT > 2.0 + 0.3 * Double(phase) { rest(sc) }
    }

    func pPuff(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        inhale = 0.6
        if step == 0 && modeT > 0.5 / sp {
            step = 1
            sc.app.audio.play("shoot")
            let n = 4 + phase
            for i in 0 ..< n {
                let a = (50 + 80 * Double(i) / Double(n - 1)) * .pi / 180
                sc.shoot("dust", x, y + 8, cos(a) * 70 * sp, sin(a) * 70 * sp)
            }
        }
        if modeT > 0.9 { rest(sc) }
    }

    func pRain(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        charge = 1
        if step == 0 {
            step = 1
            sc.app.audio.play(kind == "soot" ? "warning" : "move")
            var xs = [p.cx]
            for _ in 0 ..< 2 + phase { xs.append(Double.random(in: BLEFT + 8 ... BRIGHT - 8)) }
            for xx in xs { sc.shoot("mark", xx, BFLOOR, 0, 0) }
        }
        if modeT > 1.4 { rest(sc) }
    }

    func pBolt(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        charge = 1
        if step == 0 && modeT > 0.3 {
            step = 1
            sc.shoot("bolt", p.cx, Double(BTOP), 0, 0)
            if phase >= 3 {
                sc.shoot("bolt", p.cx - 56, Double(BTOP), 0, 0)
                sc.shoot("bolt", p.cx + 56, Double(BTOP), 0, 0)
            }
        }
        if modeT > 1.4 { rest(sc) }
    }

    func slither(_ dt: Double, _ v: Double) {
        x += vx * v * dt
        y += vy * v * dt + sin(t * 6) * 20 * dt
        if x < BLEFT + 10 || x > BRIGHT - 10 { vx = -vx; x = max(BLEFT + 10, min(BRIGHT - 10, x)) }
        if y < Double(BTOP + 18) || y > BFLOOR - 10 { vy = -vy; y = max(Double(BTOP + 18), min(BFLOOR - 10, y)) }
        face = vx > 0 ? 1 : -1
    }

    func pSlither(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        slither(dt, 75 * sp)
        if modeT > 2.6 { rest(sc, 0.5) }
    }

    func pLunge(_ sc: SoapHop, _ dt: Double, _ sp: Double, _ p: SHBody) {
        modeT += dt
        if step == 0 {
            charge = 1
            x += sin(t * 50) * 0.6
            if modeT > 0.55 / sp {
                step = 1; modeT = 0
                let d = max(1, hypot(p.cx - x, p.cy - y))
                vx = (p.cx - x) / d; vy = (p.cy - y) / d
                sc.app.audio.play("jump")
            }
        } else {
            charge = 0
            slither(dt, 200 * sp)
            if modeT > 0.65 { rest(sc) }
        }
    }

    // ------------------------------------------------------------------ draw
    func draw(_ s: Surface, _ t: Double) {
        let fl = flash > 0 && Int(flash * 40) % 2 == 0
        let ix = Int(x), iy = Int(y)
        if dead { return }
        switch kind {
        case "king": SHArt.king(s, ix, iy, t, squash: squash, flash: fl, phase: phase)
        case "grime": SHArt.grime(s, ix, iy, t, squash: squash, flash: fl, phase: phase)
        case "mop": SHArt.mop(s, ix, iy, t, lift: lift, flash: fl, walk: walk, phase: phase)
        case "vac": SHArt.vac(s, ix, iy, t, inhale: inhale, flash: fl, phase: phase)
        case "soot": SHArt.soot(s, ix, iy, t, charge: charge, flash: fl, phase: phase)
        default:
            let sg = segs()
            for i in stride(from: sg.count - 1, through: 0, by: -1) { SHArt.sockSeg(s, sg[i].0, sg[i].1, i, flash: fl) }
            SHArt.sockHead(s, ix, iy, t, face: face, lunge: mode == "lunge" && step == 1, flash: fl)
        }
        if ["spit", "lunge", "slam", "minions", "puff", "splash"].contains(mode) && step == 0 && Int(t * 10) % 2 == 1 {
            drawText(s, "!", ix, iy - Int(r) - 22, "red", scale: 2, align: .center, outline: "black")
        }
    }
}
