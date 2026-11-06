// PAW PINBALL bosses (port of games/paw_pinball_boss.py): BUSTER the bully dog, ROBO-VAC, CAW the crow,
// CUKE the cucumber and SPRITZ the spray bottle. Every attack is telegraphed; things thrown at a paw stun it unless
// the paw is swinging up or held up when they arrive, which bats them back for a COUNTER hit.
import Foundation

private let MOVES: [String: [String]] = ["buster": ["toss", "charge"], "robovac": ["suck", "bunnies"],
                                         "caw": ["toss", "shield", "dive"], "cuke": ["hop", "pickles"],
                                         "spritz": ["squirt", "mist"]]
private let RADIUS: [String: Double] = ["buster": 13, "robovac": 13, "caw": 11, "cuke": 12, "spritz": 12]
private let HOME_Y: [String: Double] = ["buster": 52, "robovac": 54, "caw": 46, "cuke": 56, "spritz": 38]
private let TELL: [String: Double] = ["toss": 0.75, "charge": 0.7, "suck": 0.9, "bunnies": 0.5, "shield": 0.45,
                                      "dive": 0.85, "hop": 0.9, "pickles": 0.55, "squirt": 0.85, "mist": 0.5]
private let X_MIN = 124.0, X_MAX = 212.0
private let TOSSED = ["buster": "bone", "caw": "pebble", "robovac": "bone", "cuke": "pebble", "spritz": "drop"]

final class PPProj {
    var x, y, vx, vy: Double
    let kind: String
    let side: Int          // targeted paw (or damage, for fish missiles)
    var back = false       // batted back up by a paw
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ kind: String, _ side: Int) {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.kind = kind; self.side = side
    }
}

final class PPBoss {
    unowned let sc: PawPinball
    let kind, name, title: String
    var hp: Int
    let maxhp: Int
    let spd, rate: Double
    let round: Int
    var moves: [String]
    let r: Double
    var homeY: Double
    var x = 168.0, y = -24.0
    var state = "enter"           // enter | idle | fight | dead
    var t = 0.0, cool = 2.2
    var act = "", actT = 0.0, phase = 0
    var flash = 0.0, shield = 0.0, iframes = 0.0
    var angry = false
    var dir = 1.0, ang = 0.0
    var side = 0
    var tx = 0.0, ty = 0.0, sx = 0.0, sy = 0.0
    var jet = 0.0
    var mists: [(x: Double, y: Double, t: Double)] = []
    var bunnies: [(x: Double, y: Double, t: Double)] = []
    var pickles: [(x: Double, y: Double, vy: Double, side: Int)] = []
    var projs: [PPProj] = []
    var held: PPBall?
    var heldT = 0.0, deadT = 0.0
    var hits = 0

    init(_ sc: PawPinball, _ spec: PPBossSpec) {
        self.sc = sc
        kind = spec.kind; name = spec.name; title = spec.title
        hp = spec.hp; maxhp = spec.hp
        spd = spec.speed; rate = spec.rate; round = spec.round
        moves = MOVES[kind] ?? ["toss"]
        for e in spec.extra { if let m = MOVES[e]?.first, !moves.contains(m) { moves.append(m) } }
        r = RADIUS[kind] ?? 12
        homeY = HOME_Y[kind] ?? 50
    }

    // ---------------------------------------------------------------- scene hooks
    func dyn() -> [PPDyn] {
        var out: [PPDyn] = []
        if state == "fight" {
            if act == "dive" && phase == 1 {
                out.append(PPDyn(x: x, y: y, r: r, kind: "grab", solid: false, ref: 0))
            } else if act == "suck" && phase == 1 {
                out.append(PPDyn(x: x, y: y, r: r, kind: "eat", solid: false, ref: 0))
            } else {
                out.append(PPDyn(x: x, y: y, r: r, kind: "boss", solid: true, ref: 0))
            }
        }
        for (i, b) in bunnies.enumerated() { out.append(PPDyn(x: b.x, y: b.y, r: 4, kind: "bunny", solid: true, ref: i)) }
        for (i, p) in pickles.enumerated() { out.append(PPDyn(x: p.x, y: p.y, r: 4, kind: "pickle", solid: true, ref: i)) }
        return out
    }

    /// A ball (or a counter / fish missile: force, no invulnerability) hits the boss. True if it hurt.
    @discardableResult
    func hit(_ dmg: Int, _ px: Double? = nil, _ py: Double? = nil, force: Bool = false) -> Bool {
        if state != "fight" { return false }
        if shield > 0 {
            sc.app.audio.play("tin")
            sc.floats.add(x, y - 16, "TINK!", "sky")
            return false
        }
        if iframes > 0 && !force { return false }
        iframes = 0.3
        hp = max(0, hp - dmg)
        hits += 1
        flash = 0.15
        sc.hype.hitstop(0.05)
        sc.app.audio.play(dmg >= 3 ? "explode" : "brick")
        sc.parts.burst(px ?? x, py ?? y, 10, ["white", "yellow", "orange"], 70, 0.4)
        sc.app.shake(2, 0.12)
        if hp <= 0 {
            state = "dead"
            deadT = 0
            releaseBall()
            projs = projs.filter { $0.kind == "missile" }
            bunnies = []; pickles = []; mists = []
            sc.bossDefeated()
        } else if !angry && hp <= maxhp / 2 {
            angry = true
            sc.hype.banner("\(name) IS ANGRY!", "WATCH OUT", color: "red", dur: 1.4, scale: 1, sound: "warning")
            sc.hype.flash("red", 0.2)
        }
        return true
    }

    func releaseBall() {
        if let b = held {
            b.state = "play"
            b.x = x; b.y = y + r + 4
            b.vx = Double.random(in: -70 ... 70); b.vy = 200
            held = nil
        }
    }

    // ---------------------------------------------------------------- update
    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        shield = max(0, shield - dt)
        iframes = max(0, iframes - dt)
        if state == "enter" {
            y += (homeY - y) * min(1, dt * 3)
            if abs(y - homeY) < 0.5 { y = homeY; state = "idle" }
            return
        }
        if state == "dead" {
            deadT += dt
            y += 30 * dt
            updateProjs(dt)
            return
        }
        updateProjs(dt)
        updateMinions(dt)
        if let b = held {
            heldT -= dt
            b.x = x; b.y = y
            if heldT <= 0 { releaseBall() }
        }
        if state != "fight" { return }
        let s = spd * (angry ? 1.3 : 1)
        if !act.isEmpty {
            actT += dt
            doAct(dt, s)
        } else {
            move(dt, s)
            cool -= dt * (angry ? 1.35 : 1)
            if cool <= 0 { start(moves.randomElement()!) }
        }
    }

    private func move(_ dt: Double, _ s: Double) {
        switch kind {
        case "buster":
            x += dir * 34 * s * dt
            if x > X_MAX || x < X_MIN { dir = -dir; x = max(X_MIN, min(X_MAX, x)) }
            y = homeY - abs(sin(t * 7)) * 2
        case "robovac":
            ang += 0.8 * s * dt
            x = 168 + cos(ang) * 40
            y = homeY + sin(ang) * 12
        case "caw":
            ang += 1.0 * s * dt
            x = 168 + sin(ang) * 42
            y = homeY + sin(ang * 2) * 10
        case "cuke":
            y = homeY + sin(t * 3) * 1.5
        default:
            ang += 0.7 * s * dt
            x = 168 + sin(ang) * 44
            y = homeY
        }
    }

    private func start(_ a: String) {
        act = a; actT = 0; phase = 0
        sx = x; sy = y
        side = Int.random(in: 0 ... 1)
        switch a {
        case "charge": dir = x < 168 ? 1 : -1
        case "dive": tx = Double.random(in: 120 ... 200); ty = Double.random(in: 112 ... 128)
        case "hop": tx = Double.random(in: X_MIN ... X_MAX); ty = Double.random(in: 44 ... 66)
        case "mist": tx = Double.random(in: 122 ... 196); ty = Double.random(in: 96 ... 120)
        default: break
        }
        sc.app.audio.play(["charge", "dive", "squirt", "suck"].contains(a) ? "warning" : "hold")
    }

    private func endAct() {
        act = ""
        cool = rate * Double.random(in: 0.8 ... 1.2)
    }

    func pawTarget() -> (Double, Double) {
        let f = sc.flippers[side]
        let (ftx, _) = f.tip()
        return ((f.px + ftx) / 2, f.py + 2)
    }

    private func doAct(_ dt: Double, _ s: Double) {
        let tell = (TELL[act] ?? 0.6) / min(1.6, s)
        if phase == 0 {
            if act == "charge" || act == "hop" { x = sx + Double.random(in: -1 ... 1) }
            if actT >= tell { phase = 1; actT = 0; fire(act) }
            return
        }
        switch act {
        case "charge":
            x += dir * 230 * s * dt
            if x > X_MAX + 6 || x < X_MIN - 6 {
                x = max(X_MIN, min(X_MAX, x))
                dir = -dir
                endAct()
            }
        case "suck":
            for b in sc.balls where b.state == "play" {
                let dx = x - b.x, dy = y - b.y
                let d = hypot(dx, dy)
                if d > 1 && d < 85 {
                    let f = 420 * (1 - d / 95) * dt
                    b.vx += dx / d * f
                    b.vy += dy / d * f
                }
            }
            if actT > 2.0 { endAct() }
        case "dive":
            if actT < 0.45 {
                let u = actT / 0.45
                x = sx + (tx - sx) * u
                y = sy + (ty - sy) * u * u
            } else if actT < 1.1 {
                let u = (actT - 0.45) / 0.65
                x = tx + (sx - tx) * u
                y = ty + (sy - ty) * (1 - (1 - u) * (1 - u))
            } else {
                x = sx; y = sy
                if held != nil { heldT = 0; releaseBall() }
                endAct()
            }
        case "hop":
            let u = min(1, actT / 0.55)
            x = sx + (tx - sx) * u
            y = sy + (ty - sy) * u - sin(u * .pi) * 26
            if u >= 1 {
                homeY = ty
                land()
                endAct()
            }
        case "squirt":
            jet = actT
            let (fx, fy) = pawTarget()
            for b in sc.balls where b.state == "play" {
                if ppSegDist(b.x, b.y, x, y + 8, fx, fy) < 6 {
                    let dx = fx - x, dy = fy - y
                    var d = hypot(dx, dy)
                    if d == 0 { d = 1 }
                    b.vx += dx / d * 700 * dt
                    b.vy += dy / d * 700 * dt
                }
            }
            if actT > 0.7 {
                let f = sc.flippers[side]
                if f.isUp || f.w < 0 {
                    sc.floats.add(fx, fy - 12, "BLOCKED!", "mint")
                    sc.app.audio.play("tin")
                } else {
                    sc.stunPaw(side, 1.2, "SOAKED!")
                }
                jet = 0
                endAct()
            }
        default:
            endAct()
        }
    }

    private func fire(_ a: String) {
        switch a {
        case "toss":
            let (fx, fy) = pawTarget()
            let tt = 1.05
            let vx = (fx - x) / tt
            let vy = (fy - y - 0.5 * 240 * tt * tt) / tt
            projs.append(PPProj(x, y, vx, vy, TOSSED[kind] ?? "bone", side))
            sc.app.audio.play("shoot")
            endAct()
        case "bunnies":
            for p in sc.tb.spots.shuffled().prefix(2 + min(2, round)) {
                bunnies.append((p.0, p.1, 9.0))
                sc.parts.burst(p.0, p.1, 8, ["gray", "white"], 40, 0.4)
            }
            sc.app.audio.play("pop")
            endAct()
        case "shield":
            shield = 2.2
            endAct()
        case "pickles":
            for i in 0 ..< (2 + min(1, round)) {
                pickles.append((x + (Double(i) - 0.5) * 14, y + 8, 26.0 + 6 * Double(i), i % 2))
            }
            sc.app.audio.play("pop")
            endAct()
        case "mist":
            mists.append((tx, ty, 5.5))
            sc.app.audio.play("bubble")
            endAct()
        case "suck":
            sc.app.audio.play("trap")
        case "squirt":
            sc.app.audio.play("bubble")
        default: break
        }
    }

    private func land() {
        sc.app.shake(3, 0.25)
        sc.app.audio.play("boom")
        sc.parts.burst(x, y + 10, 16, ["lime", "mint", "white"], 70, 0.5)
        for b in sc.balls where b.state == "play" {
            let dx = b.x - x, dy = b.y - y
            let d = hypot(dx, dy)
            if d < 60 {
                let k = 260 * (1 - d / 70)
                let dd = d == 0 ? 1 : d
                b.vx += dx / dd * k
                b.vy += dy / dd * k
            }
        }
    }

    /// Physics reported a ball touching one of our colliders.
    func onBall(_ k: String, _ ref: Int, _ b: PPBall?) {
        switch k {
        case "boss":
            guard let b = b, b.bossCd <= 0 else { return }
            b.bossCd = 0.25
            if hit(sc.ballDmg(), b.x, b.y) { sc.bossHitFx(b) }
        case "grab", "eat":
            guard let b = b, held == nil, b.state == "play" else { return }
            b.state = "held"
            held = b
            heldT = k == "eat" ? 1.0 : 99.0
            sc.app.audio.play("trap")
            sc.hype.banner(k == "grab" ? "STOLEN!" : "GULP!", color: "red", dur: 0.9, scale: 1)
        case "bunny":
            guard ref < bunnies.count else { return }
            let bn = bunnies.remove(at: ref)
            sc.scoreAt(300, bn.x, bn.y - 6)
            sc.parts.burst(bn.x, bn.y, 10, ["gray", "white"], 50, 0.4)
            sc.app.audio.play("pop")
            sc.switchHit()
        case "pickle":
            guard ref < pickles.count else { return }
            let p = pickles.remove(at: ref)
            sc.scoreAt(400, p.x, p.y - 6)
            sc.parts.burst(p.x, p.y, 10, ["lime", "mint"], 50, 0.4)
            sc.app.audio.play("pop")
            sc.switchHit()
        default: break
        }
    }

    private func updateMinions(_ dt: Double) {
        for i in bunnies.indices { bunnies[i].t -= dt }
        bunnies.removeAll { $0.t <= 0 }
        for i in mists.indices {
            mists[i].t -= dt
            let m = mists[i]
            for b in sc.balls where b.state == "play" && (b.x - m.x) * (b.x - m.x) + (b.y - m.y) * (b.y - m.y) < 26 * 26 {
                b.vx *= 1 - 2.2 * dt
                b.vy *= 1 - 1.2 * dt
            }
        }
        mists.removeAll { $0.t <= 0 }
        var keep: [(x: Double, y: Double, vy: Double, side: Int)] = []
        for var p in pickles {
            p.y += p.vy * dt
            let f = sc.flippers[p.side]
            let fx = (f.px + f.tip().0) / 2
            p.x += (fx - p.x) * min(1, dt * 0.6)
            if p.y > PP_FLIP_Y - 8 {
                sc.stunPaw(p.side, 1.4, "PICKLED!")
                sc.parts.burst(p.x, p.y, 8, ["lime"], 40, 0.4)
                continue
            }
            keep.append(p)
        }
        pickles = keep
    }

    private func updateProjs(_ dt: Double) {
        var keep: [PPProj] = []
        for p in projs {
            if p.kind == "missile" {
                let dx = x - p.x, dy = y - p.y
                var d = hypot(dx, dy)
                if d == 0 { d = 1 }
                p.vx += (dx / d * 300 - p.vx) * min(1, dt * 6)
                p.vy += (dy / d * 300 - p.vy) * min(1, dt * 6)
                p.x += p.vx * dt
                p.y += p.vy * dt
                sc.parts.sparkle(p.x, p.y, "orange")
                if d < r + 3 || state == "dead" {
                    if state == "fight" {
                        hit(p.side, p.x, p.y, force: true)
                        sc.floats.add(p.x, p.y - 10, "FISH HIT!", "orange")
                    }
                    continue
                }
                keep.append(p)
                continue
            }
            if p.back {
                p.x += p.vx * dt
                p.y += p.vy * dt
                if state == "fight" && hypot(p.x - x, p.y - y) < r + 4 {
                    if hit(2 + sc.lv("power"), p.x, p.y, force: true) {
                        sc.hype.banner("COUNTER!", color: "mint", dur: 0.9, scale: 1)
                        sc.scoreAt(1500, p.x, p.y - 10)
                    }
                    continue
                }
                if p.y < 4 { continue }
                keep.append(p)
                continue
            }
            p.vy += 240 * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            var hitBall = false
            for b in sc.balls where b.state == "play" && (b.x - p.x) * (b.x - p.x) + (b.y - p.y) * (b.y - p.y) < 36 {
                b.vy += 70
                hitBall = true
            }
            if hitBall {
                sc.parts.burst(p.x, p.y, 6, ["white", "gray"], 40, 0.3)
                continue
            }
            let f = sc.flippers[p.side]
            let fx = (f.px + f.tip().0) / 2, fy = f.py
            if p.y >= fy - 9 && abs(p.x - fx) < 16 {
                if f.w < 0 || f.isUp {
                    p.back = true
                    p.vx = (x - p.x) * 1.25
                    p.vy = -330
                    sc.app.audio.play("paddle")
                    sc.floats.add(p.x, p.y - 10, "BAT!", "mint")
                    keep.append(p)
                } else {
                    sc.stunPaw(p.side, 1.3, "BONK!")
                    sc.parts.burst(p.x, p.y, 8, ["white", "yellow"], 50, 0.3)
                }
                continue
            }
            if p.y > 206 { continue }
            keep.append(p)
        }
        projs = keep
    }

    // ---------------------------------------------------------------- drawing
    func draw(_ s: Surface, _ t: Double) {
        for m in mists {
            for i in 0 ..< 7 {
                let a = t * 0.8 + Double(i) * 0.9
                let mx = Int(m.x + cos(a) * 16), my = Int(m.y + sin(a * 1.3) * 10)
                s.circle(col(i % 2 == 1 ? "sky" : "white"), mx, my, m.t > 1 || Int(t * 8) % 2 == 1 ? 5 : 3, width: 1)
            }
        }
        for b in bunnies where !(b.t < 1.5 && Int(t * 8) % 2 == 1) { PPBoss.drawBunny(s, b.x, b.y, t) }
        for p in pickles { PPBoss.drawPickle(s, p.x, p.y) }
        if state == "fight" && !act.isEmpty && phase == 0 { drawTell(s, t) }
        if act == "squirt" && phase == 1 {
            let (fx, fy) = pawTarget()
            for i in -1 ... 1 { s.line(col(i != 0 ? "sky" : "white"), Int(x) + i, Int(y) + 8, Int(fx) + i, Int(fy)) }
        }
        if act == "suck" && phase == 1 {
            for i in 0 ..< 3 {
                let rr = Int(40 - (t * 60 + Double(i) * 13).truncatingRemainder(dividingBy: 40))
                s.circle(col(i % 2 == 1 ? "lavender" : "white"), Int(x), Int(y), max(2, rr), width: 1)
            }
        }
        let dead = state == "dead"
        if !(dead && Int(t * 12) % 2 == 1) {
            PPBoss.drawBoss(s, kind, x, y, t, flash: flash > 0, angry: angry, shield: shield > 0,
                            tell: phase == 0 ? act : "", dead: dead)
        }
        for p in projs { PPBoss.drawProj(s, p.kind, p.x, p.y, t, back: p.back) }
    }

    private func drawTell(_ s: Surface, _ t: Double) {
        let blink = Int(t * 10) % 2 == 1
        switch act {
        case "toss", "squirt":
            let (fx, fy) = pawTarget()
            if blink { drawText(s, "!", Int(fx) - 2, Int(fy) - 20, "red", scale: 2, shadow: nil, outline: "black") }
            if act == "squirt" {
                for i in stride(from: 0, to: 100, by: 8) {
                    let u = Double(i) / 100
                    s.fillRect(col("sky"), Int(x + (fx - x) * u), Int(y + 8 + (fy - y - 8) * u), 2, 2)
                }
            }
        case "dive":
            for i in stride(from: 0, to: 100, by: 10) {
                let u = Double(i) / 100
                s.fillRect(col(blink ? "red" : "orange"), Int(x + (tx - x) * u), Int(y + (ty - y) * u), 2, 2)
            }
        case "hop":
            s.ellipse(col("black"), Int(tx) - 12, Int(ty) + 8, 24, 6)
            s.ellipse(col(blink ? "red" : "darkgray"), Int(tx) - 12, Int(ty) + 8, 24, 6, width: 1)
        case "suck":
            s.circle(col(blink ? "red" : "lavender"), Int(x), Int(y), Int(30 + sin(t * 20) * 4), width: 1)
        case "charge":
            for i in 0 ..< 3 { s.fillRect(col("peach"), Int(x) - Int(dir) * (14 + i * 5), Int(y) + 10 - i, 2, 2) }
        case "mist":
            s.circle(col("sky"), Int(tx), Int(ty), blink ? 26 : 22, width: 1)
        default: break
        }
    }

    static func drawBunny(_ s: Surface, _ xd: Double, _ yd: Double, _ t: Double) {
        let x = Int(xd), y = Int(yd)
        for a in stride(from: 0, to: 360, by: 60) {
            let r = (Double(a) + t * 90) * .pi / 180
            s.circle(col("darkgray"), x + Int(cos(r) * 3), y + Int(sin(r) * 3), 2)
        }
        s.circle(col("gray"), x, y, 3)
        s.fillRect(col("black"), x - 1, y - 1, 1, 1)
        s.fillRect(col("black"), x + 1, y - 1, 1, 1)
    }

    static func drawPickle(_ s: Surface, _ xd: Double, _ yd: Double) {
        let x = Int(xd), y = Int(yd)
        s.ellipse(col("black"), x - 4, y - 6, 9, 13)
        s.ellipse(col("lime"), x - 3, y - 5, 7, 11)
        s.fillRect(col("teal"), x - 1, y - 3, 1, 1)
        s.fillRect(col("teal"), x + 1, y + 2, 1, 1)
        s.fillRect(col("black"), x - 2, y - 1, 1, 2)
        s.fillRect(col("black"), x + 2, y - 1, 1, 2)
    }

    static func drawProj(_ s: Surface, _ kind: String, _ xd: Double, _ yd: Double, _ t: Double, back: Bool) {
        let x = Int(xd), y = Int(yd)
        if kind == "missile" {
            s.ellipse(col("orange"), x - 5, y - 2, 10, 5)
            s.fillRect(col("black"), x + 2, y - 1, 1, 1)
            s.polygon(col("yellow"), [(Double(x - 5), Double(y)), (Double(x - 8), Double(y - 3)), (Double(x - 8), Double(y + 3))])
            return
        }
        if kind == "bone" {
            let a = t * 14
            let dx = Int(cos(a) * 4), dy = Int(sin(a) * 4)
            s.line(col("cream"), x - dx, y - dy, x + dx, y + dy, width: 2)
            s.circle(col("white"), x - dx, y - dy, 2)
            s.circle(col("white"), x + dx, y + dy, 2)
        } else if kind == "pebble" {
            s.circle(col("black"), x, y, 3)
            s.circle(col("gray"), x, y, 2)
            s.fillRect(col("white"), x - 1, y - 1, 1, 1)
        } else {
            s.polygon(col("sky"), [(Double(x), Double(y - 4)), (Double(x + 3), Double(y + 1)), (Double(x - 3), Double(y + 1))])
            s.circle(col("sky"), x, y + 1, 3)
            s.fillRect(col("white"), x - 1, y, 1, 1)
        }
        if back && Int(t * 10) % 2 == 1 { s.circle(col("mint"), x, y, 6, width: 1) }
    }

    static func drawBoss(_ s: Surface, _ kind: String, _ xd: Double, _ yd: Double, _ t: Double, flash hot: Bool, angry: Bool,
                         shield: Bool, tell: String, dead: Bool) {
        let x = Int(xd), y = Int(yd)
        let X = Double(x), Y = Double(y)
        let k = col("black")
        let blinkRed = angry && Int(t * 6) % 2 == 1
        switch kind {
        case "buster":
            let body = col(hot ? "white" : (blinkRed ? "red" : "brown"))
            s.ellipse(k, x - 15, y - 11, 30, 25)
            s.ellipse(body, x - 14, y - 10, 28, 23)
            for side in [-1, 1] {
                s.ellipse(k, x + side * 13 - 5, y - 10, 10, 14)
                s.ellipse(col("choco"), x + side * 13 - 4, y - 9, 8, 12)
            }
            s.ellipse(col("cream"), x - 9, y - 1, 18, 11)
            s.ellipse(k, x - 3, y - 1, 6, 4)
            Cute.eyes(s, x, y - 5, 5, look: 0, mood: "angry")
            s.fillRect(k, x - 5, y + 6, 11, 1)
            s.fillRect(col("white"), x - 4, y + 4, 2, 2)
            s.fillRect(col("white"), x + 3, y + 4, 2, 2)
            s.fillRect(col("red"), x - 11, y + 11, 22, 3)
            for i in stride(from: -9, to: 10, by: 6) { s.fillRect(col("gray"), x + i, y + 10, 2, 2) }
            if tell == "toss" {
                s.line(col("cream"), x + 12, y - 16, x + 20, y - 22, width: 2)
                s.circle(col("white"), x + 12, y - 16, 2)
                s.circle(col("white"), x + 20, y - 22, 2)
            }
        case "robovac":
            let body = col(hot ? "white" : (blinkRed ? "red" : "gray"))
            s.ellipse(k, x - 15, y - 9, 30, 20)
            s.ellipse(body, x - 14, y - 8, 28, 17)
            s.ellipse(col("white"), x - 10, y - 7, 20, 8)
            s.fillRect(col("darkgray"), x - 9, y - 4, 18, 4)
            let sweep = Int((t * 30).truncatingRemainder(dividingBy: 14))
            s.fillRect(col("red"), x - 8 + sweep, y - 4, 3, 3)
            for side in [-1, 1] {
                let a = t * 20 * Double(side)
                for i in 0 ..< 3 {
                    let bx = x + side * 12 + Int(cos(a + Double(i) * 2.1) * 4)
                    let by = y + 9 + Int(sin(a + Double(i) * 2.1) * 2)
                    s.fillRect(col("yellow"), bx, by, 1, 1)
                }
            }
            if angry { s.fillRect(col("red"), x - 2, y + 3, 4, 2) }
        case "caw":
            let flap = shield ? 0 : sin(t * 14) * 5
            let body = col(hot ? "white" : "black")
            if shield {
                s.ellipse(col("purple"), x - 13, y - 13, 26, 26)
                s.ellipse(col("deep"), x - 11, y - 11, 22, 22)
                s.fillRect(col("lavender"), x - 6, y - 8, 4, 1)
            } else {
                for side in [-1.0, 1.0] {
                    s.polygon(col("deep"), [(X + side * 4, Y - 2), (X + side * 18, Y - 6 - Double(Int(flap))), (X + side * 14, Y + 4)])
                }
                s.ellipse(body, x - 8, y - 9, 16, 19)
                s.circle(body, x, y - 8, 6)
                s.polygon(col("yellow"), [(X - 2, Y - 6), (X + 2, Y - 6), (X, Y - 1)])
                for side in [-1, 1] {
                    s.fillRect(col("white"), x + side * 3 - (side < 0 ? 1 : 0), y - 10, 2, 2)
                    s.fillRect(col(angry ? "red" : "black"), x + side * 3, y - 9, 1, 1)
                }
                s.fillRect(col("purple"), x - 3, y + 2, 6, 1)
            }
            if tell == "dive" { drawText(s, "!", x + 10, y - 20, "red", shadow: nil, outline: "black") }
        case "cuke":
            let body = col(hot ? "white" : (blinkRed ? "red" : "lime"))
            let sq = tell == "hop" ? 2 : 0
            s.ellipse(k, x - 9 - sq, y - 15 + sq, 18 + 2 * sq, 31 - sq)
            s.ellipse(body, x - 8 - sq, y - 14 + sq, 16 + 2 * sq, 29 - sq)
            for (dx, dy) in [(-4, -8), (3, -4), (-3, 4), (4, 8), (0, -11), (-5, 10)] { s.fillRect(col("teal"), x + dx, y + dy, 2, 1) }
            s.fillRect(col("mint"), x - 5, y - 10, 1, 8)
            s.polygon(col("teal"), [(X, Y - 15), (X + 6, Y - 20), (X + 2, Y - 13)])
            Cute.eyes(s, x, y - 3, 3, look: 0, mood: "angry")
            Cute.mouth(s, x, y + 3, "angry")
            if tell == "hop" { for side in [-1, 1] { s.fillRect(k, x + side * 5, y + 15, 2, 3) } }
        default:
            let body = col(hot ? "white" : (blinkRed ? "red" : "sky"))
            s.rect(k, IRect(x - 9, y - 6, 18, 22), radius: 3)
            s.rect(body, IRect(x - 8, y - 5, 16, 20), radius: 3)
            let lvl = Int(6 + sin(t * 2) * 1)
            s.fillRect(col("blue"), x - 7, y + 14 - lvl, 14, lvl)
            s.fillRect(col("white"), x - 6, y - 3, 2, 10)
            s.rect(k, IRect(x - 6, y - 15, 12, 10), radius: 2)
            s.rect(col("red"), IRect(x - 5, y - 14, 10, 8), radius: 2)
            s.fillRect(col("red"), x - 4, y - 7, 3, 5)
            s.fillRect(col("white"), x + 5, y - 12, 4, 2)
            Cute.eyes(s, x, y + 3, 3, look: 0, mood: "angry")
            Cute.mouth(s, x, y + 8, "angry")
        }
        if dead {
            for i in 0 ..< 4 {
                let a = t * 9 + Double(i) * 1.6
                s.fillRect(col("yellow"), x + Int(cos(a) * 16), y - 14 + Int(sin(a) * 4), 2, 2)
            }
        }
    }
}

func ppSegDist(_ px: Double, _ py: Double, _ x1: Double, _ y1: Double, _ x2: Double, _ y2: Double) -> Double {
    let dx = x2 - x1, dy = y2 - y1
    var l2 = dx * dx + dy * dy
    if l2 == 0 { l2 = 1 }
    let t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / l2))
    return hypot(px - (x1 + dx * t), py - (y1 + dy * t))
}
