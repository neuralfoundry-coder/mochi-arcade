// TOWER TABBY bosses (port of games/tower_tabby_boss.py - keep in step).
// Seven original bosses with telegraphed patterns; many attacks end with the boss DAZED: pounce it (3) or land on
// it (2). Feather-wand swats send projectiles back at it (1). HP and pattern lists come from the stage data.
import Foundation

private let FLOOR = TT_LEVEL_Y[0]
private let TOPY = 14.0
private let RADIUS: [String: Int] = ["kaw": 13, "storm": 15, "vac": 14, "mouse": 14, "spritz": 12, "dot": 8, "golem": 15]
private let HITBOX: [String: (Double, Double)] = ["kaw": (12, 9), "storm": (14, 10), "vac": (16, 7), "mouse": (15, 9),
                                                 "spritz": (10, 12), "dot": (8, 8), "golem": (14, 14)]
private let FLYERS: Set<String> = ["kaw", "storm", "dot"]
private let STORM_REMAP: [Character: Character] = ["d": "u", "r": "y", "w": "y"]

final class TTBoss {
    let kind: String
    let name: String
    var hp: Int, maxhp: Int
    let pats: [String]
    let spd: Double
    let r: Int
    let hw, hh: Double
    let flyer: Bool
    var x = Double(W) / 2 + 60, y = -30.0
    let homeY: Double
    var vx = 0.0, vy = 0.0
    var face = -1
    var mode = "enter", modeT = 0.0, step = 0
    var patI = 0, count = 0
    var flash = 0.0
    var phase = 1
    var daze = 0.0, inv = 0.0
    var air = false
    var tx = Double(W) / 2
    var t = 0.0
    var dead = false
    var squash = 0.0, glow = 0.0
    var way: [(Double, Double)] = []
    var timer = 0.0

    init(_ sd: TTStage, _ sc: TowerTabby) {
        kind = sd.boss
        name = sd.nm
        hp = sd.hp; maxhp = sd.hp
        pats = sd.pat.isEmpty ? ["swoop"] : sd.pat
        spd = sd.spd
        r = RADIUS[kind] ?? 13
        (hw, hh) = HITBOX[kind] ?? (12, 9)
        flyer = FLYERS.contains(kind)
        homeY = flyer ? 58 : FLOOR - hh
    }

    // ------------------------------------------------------------------ helpers
    func speed() -> Double { spd * (1 + 0.15 * Double(phase - 1)) }

    func hits(_ px: Double, _ py: Double, _ rad: Double) -> Bool { abs(px - x) < hw + rad && abs(py - y) < hh + rad }

    func touches(_ p: TTPlayer) -> Bool { abs(p.x - x) < hw + 4 && p.y - 10 < y + hh - 1 && p.y > y - hh + 3 }

    func hurt(_ sc: TowerTabby, _ n: Int, _ label: String? = nil) {
        if mode == "enter" || mode == "dying" || dead { return }
        hp -= n
        flash = 0.15
        sc.add(50 * n)
        sc.hype.hit(1, fever: 0.02)
        sc.app.audio.play("brick")
        if let l = label {
            sc.floats.add(x, y - Double(r) - 8, l, "orange")
            sc.hype.hitstop(n >= 2 ? 0.06 : 0.03)
            sc.app.shake(2 + Double(n) * 0.5, 0.15)
        }
        let new = 1 + (Double(hp) <= Double(maxhp) * 0.66 ? 1 : 0) + (Double(hp) <= Double(maxhp) * 0.33 ? 1 : 0)
        if hp <= 0 {
            hp = 0
            mode = "dying"; modeT = 0; daze = 0
            sc.bossDefeated()
        } else if new > phase {
            phase = new
            sc.hype.banner("GRRR!!", "IT'S GETTING ANGRY", color: "red", dur: 1.0, scale: 2, sound: "boom")
            sc.app.shake(4, 0.4)
            daze = 0
            air = false
            rest(0.6)
        }
    }

    func rest(_ base: Double = 1.1) {
        mode = "rest"
        modeT = max(0.35, (base - 0.12 * Double(phase - 1)) / spd)
        step = 0
    }

    func dazed(_ dur: Double, _ sc: TowerTabby, _ word: String = "DIZZY!") {
        daze = max(0.6, dur - 0.12 * Double(phase - 1))
        mode = "dazed"
        vx = 0
        air = false
        sc.floats.add(x, y - Double(r) - 10, word, "yellow")
    }

    // ------------------------------------------------------------------ frame
    func update(_ sc: TowerTabby, _ dt: Double) {
        t += dt
        flash -= dt
        inv -= dt
        glow = max(0, glow - dt * 2)
        squash *= pow(0.85, dt * 60)
        let p = sc.p
        if mode == "enter" {
            y += (homeY - y) * min(1, dt * 2.2)
            if sc.state == "play" { rest(1.0) }
            return
        }
        if mode == "dying" {
            modeT += dt
            x += Double.random(in: -1.5 ... 1.5)
            if modeT > 1.8 && !dead {
                dead = true
                sc.bossBurst()
            }
            return
        }
        let sp = speed()
        switch mode {
        case "dazed":
            daze -= dt
            if daze <= 0 {
                daze = 0
                if flyer { mode = "rise"; step = 0 } else { rest(0.8) }
            }
        case "rest":
            idle(sc, dt, sp)
            modeT -= dt
            if modeT <= 0 { nextPattern(sc) }
        case "rise":
            y += max(-90 * dt, min(90 * dt, homeY - y))
            if abs(y - homeY) < 2 { rest(0.9) }
        case "swoop": pSwoop(sc, dt, sp, p)
        case "drop": pDrop(sc, dt, sp, p)
        case "feathers": pFeathers(sc, dt, sp, p, "feather")
        case "sparks": pFeathers(sc, dt, sp, p, "spark")
        case "beam": pBeam(sc, dt, sp, p)
        case "mice": pMice(sc, dt, sp, p)
        case "spit": pSpit(sc, dt, sp, p)
        case "dash": pDash(sc, dt, sp, p)
        case "suck": pSuck(sc, dt, sp, p)
        case "slam": pSlam(sc, dt, sp, p)
        case "hop": pHop(sc, dt, sp, p)
        case "spray": pSpray(sc, dt, sp, p)
        case "jet": pJet(sc, dt, sp, p)
        case "trace": pTrace(sc, dt, sp, p)
        case "roll": pRoll(sc, dt, sp, p)
        case "toss": pToss(sc, dt, sp, p)
        default: rest(1.0)
        }
        if !flyer && !air {
            vy = min(vy + 620 * dt, 300)
            y += vy * dt
            if y >= FLOOR - hh { y = FLOOR - hh; vy = 0 }
        }
        x = max(hw + 2, min(Double(W) - hw - 2, x))
        if sc.state != "play" || dead || mode == "dying" || p.warpT > 0 { return }
        if touches(p) {
            if daze > 0 {
                if inv <= 0 && (p.pounce || (p.vy > 0 && p.y < y)) {
                    hurt(sc, p.pounce ? 3 : 2, p.pounce ? "POUNCE!" : "STOMP!")
                    p.vy = -190
                    p.vx = (p.x < x ? -1 : 1) * 90
                    p.pounce = false
                    p.ground = nil
                    p.inv = max(p.inv, 0.8)
                    inv = 0.6
                    daze = min(daze, 0.35)
                }
            } else {
                sc.hurt()
            }
        }
    }

    func idle(_ sc: TowerTabby, _ dt: Double, _ sp: Double) {
        let p = sc.p
        if flyer {
            x += (tx - x) * min(1, dt * 0.9)
            y = homeY + sin(t * 2.2) * 6
            if abs(tx - x) < 4 { tx = Double.random(in: 40 ... Double(W - 40)) }
        } else {
            face = p.x > x ? 1 : -1
            if abs(p.x - x) > hw + 30 { x += Double(face) * 18 * sp * dt }      // creeps closer, never into Mikan
        }
    }

    func nextPattern(_ sc: TowerTabby) {
        var name = pats[patI % pats.count]
        patI += 1
        if name == "mice" && sc.hz.filter({ $0.kind == "mouse" }).count >= 3 { name = flyer ? "sparks" : "spit" }
        mode = name; modeT = 0; step = 0; timer = 0
        face = sc.p.x > x ? 1 : -1
        if ["drop", "spit", "toss", "spray"].contains(name) {
            count = 3 + phase
        } else if name == "roll" {
            count = 2 + (phase >= 3 ? 1 : 0)
        }
    }

    /// Glow + shake for dur seconds; returns true once it is over.
    func telegraph(_ dur: Double) -> Bool {
        glow = 1
        x += sin(t * 60) * 0.6
        if modeT >= dur { modeT = 0; return true }
        return false
    }

    // ------------------------------------------------------------------ patterns
    func pSwoop(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {                                   // line up above Mikan
            x += max(-130 * sp * dt, min(130 * sp * dt, p.x - x))
            y += (40 - y) * min(1, dt * 3)
            if modeT > 0.8 || (abs(p.x - x) < 6 && modeT > 0.4) { step = 1; modeT = 0 }
        } else if step == 1 {                            // telegraph
            if telegraph(0.55 / sp) {
                let ttx = p.x, tty = p.y - 6
                let d = max(1, hypot(ttx - x, tty - y))
                vx = (ttx - x) / d * 250 * sp; vy = (tty - y) / d * 250 * sp
                step = 2
                sc.app.audio.play("shoot")
            }
        } else {
            let prev = y + hh
            x += vx * dt
            y += vy * dt
            var hitY: Double?
            if vy > 0 { hitY = sc.support(x, prev - 1, y + hh)?.0 }
            if y + hh >= FLOOR { hitY = FLOOR }
            if hitY != nil || x <= hw + 2 || x >= Double(W) - hw - 2 || modeT > 1.6 {
                if let hy = hitY { y = hy - hh }
                sc.app.audio.play("boom")
                sc.app.shake(3, 0.25)
                sc.parts.burst(x, y + Double(r), 14, ["white", "gray", "brown"], 70, 0.5)
                if phase >= 2 && hitY == FLOOR {
                    sc.shoot("wave", x - hw, FLOOR - 4, -100 * sp, 0, 4, 0, 3)
                    sc.shoot("wave", x + hw, FLOOR - 4, 100 * sp, 0, 4, 0, 3)
                }
                dazed(1.8, sc, "BONK!")
            }
        }
    }

    func pDrop(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if flyer {
            y += (34 - y) * min(1, dt * 3)
            x += max(-110 * sp * dt, min(110 * sp * dt, tx - x))
        } else {
            squash = 0.3 * abs(sin(t * 12))
        }
        if modeT > 0.45 / sp {
            modeT = 0
            if count <= 0 { rest(1.0); return }
            count -= 1
            let cx = flyer ? x : max(12, min(Double(W) - 12, p.x + Double.random(in: -70 ... 70)))
            let h = sc.spawnHaz("cone", cx, flyer ? y + 6 : TOPY + 4)
            h.vy = 40
            tx = max(30, min(Double(W) - 30, p.x + Double.random(in: -60 ... 60)))
            sc.app.audio.play("move")
        }
    }

    func pFeathers(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer, _ kd: String) {
        modeT += dt
        if step == 0 {
            if telegraph(0.5 / sp) {
                let n = (kd == "feather" ? 3 : 5) + phase
                let base = atan2(p.y - 6 - y, p.x - x)
                let v = (kd == "feather" ? 85.0 : 100.0) * sp
                for i in 0 ..< n {
                    let a = base + (Double(i) - Double(n - 1) / 2) * 0.22
                    sc.shoot(kd, x, y, cos(a) * v, sin(a) * v, 3, 0, 5)
                }
                sc.app.audio.play("shoot")
                step = 1
            }
        } else if modeT > 0.4 {
            rest(1.1)
        }
    }

    func pBeam(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            var xs = [p.x]
            if phase >= 2 { xs += [p.x - 72, p.x + 72] }
            for bx in xs where bx > 4 && bx < Double(W) - 4 { sc.shoot("beam", bx, 0, 0, 0, 3, 0.8 / sp, 0.35) }
            glow = 1
            sc.app.audio.play("warning")
            step = 1
        } else if modeT > 1.3 {
            rest(1.0)
        }
    }

    func pMice(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            if telegraph(0.4) {
                for i in 0 ..< (1 + (phase + 1) / 2) {
                    let d = i % 2 == 0 ? 1 : -1
                    let h = sc.spawnHaz("mouse", x + Double(d * 6), y - 4, Double(d) * 60, -150)
                    h.dir = d
                }
                sc.app.audio.play("pop")
                step = 1
            }
        } else if modeT > 0.5 {
            rest(1.2)
        }
    }

    func pSpit(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            if telegraph(0.4 / sp) { step = 1 }
            return
        }
        if modeT > 0.35 / sp {
            modeT = 0
            if count <= 0 || count > 6 { rest(1.0); return }
            count -= 1
            face = p.x > x ? 1 : -1
            sc.spawnHaz("dust", x + Double(face * r), y - 2, Double(face) * 70, -80)
            sc.app.audio.play("shoot")
        }
    }

    func pDash(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            if Int(t * 20) % 2 == 1 { sc.parts.sparkle(x - Double(face * r), y + Double(r) - 2, "white") }
            if telegraph(0.55 / sp) {
                step = 1
                sc.app.audio.play("shoot")
            }
        } else {
            x += Double(face) * 165 * sp * dt
            if x <= hw + 2 || x >= Double(W) - hw - 2 {
                sc.app.audio.play("boom")
                sc.app.shake(4, 0.3)
                sc.parts.burst(x + Double(face * r), y, 14, ["white", "gray"], 70, 0.5)
                if phase >= 2 {
                    for _ in 0 ..< 2 {
                        let h = sc.spawnHaz("cone", Double.random(in: 20 ... Double(W - 20)), TOPY + 4)
                        h.vy = 30
                    }
                }
                dazed(1.7, sc, "BONK!")
            }
        }
    }

    func pSuck(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            if telegraph(0.6 / sp) {
                step = 1
                sc.app.audio.play("bubble")
            }
        } else if step == 1 {
            glow = 1
            if p.climb == nil && abs(p.y - y) < 46 { p.x += (x > p.x ? 1 : -1) * 44 * sp * dt }
            if Int(t * 30) % 2 == 1 {
                let a = Double.random(in: -0.6 ... 0.6) + (face > 0 ? 0 : .pi)
                sc.parts.p.append(Particles.P(x: x + cos(a) * 40, y: y + sin(a) * 30, vx: -cos(a) * 80, vy: -sin(a) * 60,
                                              life: 0.45, full: 0.45, c: "white", grav: 0, size: 1))
            }
            if modeT > 2.2 {
                step = 2
                sc.app.audio.play("explode")
                dazed(1.9, sc, "OVERHEAT!")
            }
        }
    }

    func pSlam(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            squash = 0.6
            if modeT > 0.4 / sp {
                step = 1; modeT = 0
                air = true
                vy = -330
                vx = max(-150 * sp, min(150 * sp, (p.x - x) / 0.95))
                sc.app.audio.play("jump")
            }
        } else {
            vy += 700 * dt
            x += vx * dt
            y += vy * dt
            if y >= FLOOR - hh && vy > 0 {
                y = FLOOR - hh; vy = 0
                air = false
                squash = 0.6
                sc.app.shake(3, 0.25)
                sc.app.audio.play("boom")
                sc.parts.burst(x, FLOOR - 2, 12, ["white", "gray"], 60, 0.5)
                sc.shoot("wave", x - hw, FLOOR - 4, -100 * sp, 0, 4, 0, 3)
                sc.shoot("wave", x + hw, FLOOR - 4, 100 * sp, 0, 4, 0, 3)
                dazed(1.25, sc)
            }
        }
    }

    func pHop(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            squash = 0.5
            if modeT > 0.35 / sp {
                step = 1; modeT = 0
                air = true
                vy = -300
                let fw = Double(W)
                let target = abs(fw - 2 * x) > 60 ? fw - x : (x > fw / 2 ? 40 : fw - 40)
                vx = (target - x) / 0.86
                sc.app.audio.play("jump")
            }
        } else {
            vy += 700 * dt
            x += vx * dt
            y += vy * dt
            if y >= FLOOR - hh && vy > 0 {
                y = FLOOR - hh; vy = 0
                air = false
                sc.app.shake(2, 0.15)
                sc.parts.burst(x, FLOOR - 2, 8, ["sky", "white"], 50, 0.4)
                dazed(0.9, sc, "SPLOSH!")
            }
        }
    }

    func pSpray(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            if telegraph(0.4 / sp) { step = 1 }
            return
        }
        if modeT > 0.16 / sp {
            modeT = 0
            if count <= 0 || count > 8 { rest(1.1); return }
            count -= 1
            let svx = (p.x - x) / 1.1 * Double.random(in: 0.7 ... 1.3)
            sc.shoot("spray", x + Double(face * 6), y - Double(r), svx, -170 - Double.random(in: 0 ... 80), 2.5, 0, 4)
            sc.app.audio.play("bubble")
        }
    }

    func pJet(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            var ys = [p.y - 6]
            if phase >= 3 {
                let other = [TT_LEVEL_Y[1] - 6, TT_LEVEL_Y[2] - 6, TT_LEVEL_Y[0] - 6].filter { abs($0 - ys[0]) > 20 }
                if let o = other.randomElement() { ys.append(o) }
            }
            for jy in ys { sc.shoot("jet", 0, jy, 0, 0, 3, 0.85 / sp, 0.6) }
            glow = 1
            sc.app.audio.play("warning")
            step = 1
        } else if modeT > 0.85 / sp + 0.7 {
            dazed(1.8, sc, "GURGLE!")
        }
    }

    func pTrace(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            way = [(Double.random(in: 30 ... Double(W - 30)), Double.random(in: 40 ... 120)),
                   (Double.random(in: 30 ... Double(W - 30)), Double.random(in: 40 ... 140)),
                   (p.x, p.y - hh)]
            step = 1
            modeT = 0
            sc.app.audio.play("warning")
        } else if step == 1 {
            glow = 1
            if modeT > 0.85 / sp { step = 2; modeT = 0 }
        } else if step == 2 {
            if way.isEmpty {
                sc.app.shake(2, 0.15)
                sc.parts.burst(x, y, 14, ["red", "hotpink", "white"], 60, 0.5)
                let g = sc.support(x, y, FLOOR + 1)?.0
                y = (g ?? FLOOR) - hh
                dazed(1.7, sc, "FIZZLE!")
                return
            }
            let (wx, wy) = way[0]
            let d = hypot(wx - x, wy - y)
            let stp = 280 * sp * dt
            if d <= stp {
                x = wx; y = wy
                way.removeFirst()
            } else {
                x += (wx - x) / d * stp
                y += (wy - y) / d * stp
            }
            timer -= dt
            if phase >= 2 && timer <= 0 {
                timer = 0.05
                sc.shoot("spark", x, y, 0, 0, 2, 0, 0.5)
            }
        }
    }

    /// Bounces across the room in big hops (run underneath!), dizzy after the last wall.
    func pRoll(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if step == 0 {
            if telegraph(0.6 / sp) {
                step = 1
                air = true
                vy = -260
                sc.app.audio.play("jump")
            }
        } else {
            vy += 640 * dt
            x += Double(face) * 120 * sp * dt
            y += vy * dt
            if y >= FLOOR - hh && vy > 0 {
                y = FLOOR - hh
                vy = -260
                squash = 0.5
                sc.app.audio.play("lock")
                sc.parts.burst(x, FLOOR - 2, 6, ["pink", "white"], 40, 0.3)
            }
            if x <= hw + 2 || x >= Double(W) - hw - 2 {
                face = -face
                x = max(hw + 3, min(Double(W) - hw - 3, x))
                count -= 1
                sc.app.audio.play("boom")
                sc.app.shake(3, 0.2)
                if phase >= 2 { sc.spawnHaz("yarn", Double.random(in: 30 ... Double(W - 30)), TOPY + 4) }
                if count <= 0 {
                    air = false
                    dazed(1.7, sc)
                }
            }
        }
    }

    func pToss(_ sc: TowerTabby, _ dt: Double, _ sp: Double, _ p: TTPlayer) {
        modeT += dt
        if modeT > 0.32 / sp {
            modeT = 0
            if count <= 0 || count > 6 { rest(1.1); return }
            count -= 1
            let svx = (p.x - x) * 0.9 + Double.random(in: -25 ... 25)
            sc.spawnHaz("yarn", x, y - Double(r), svx, -230)
            squash = 0.4
            sc.app.audio.play("jump")
        }
    }

    // ------------------------------------------------------------------ draw
    func draw(_ s: Surface, _ t: Double) {
        if dead { return }
        let x = Int(self.x), y = Int(self.y), r = self.r
        let hit = flash > 0 && Int(flash * 30) % 2 == 1
        if mode == "trace" && step == 1 {
            let pts = [(self.x, self.y)] + way
            for i in 0 ..< max(0, pts.count - 1) {
                let (ax, ay) = pts[i], (bx, by) = pts[i + 1]
                let n = Int(hypot(bx - ax, by - ay) / 6)
                for j in 0 ..< max(0, n) where (j + Int(t * 20)) % 2 == 1 {
                    let f = Double(j) / Double(max(1, n))
                    s.fillRect(col("red"), Int(ax + (bx - ax) * f), Int(ay + (by - ay) * f), 2, 2)
                }
            }
        }
        if glow > 0 && Int(t * 16) % 2 == 1 { s.circle(col(kind != "dot" ? "yellow" : "hotpink"), x, y, r + 4, width: 1) }
        switch kind {
        case "kaw", "storm":
            var remap: [Character: Character]? = kind == "storm" ? STORM_REMAP : nil
            if hit { remap = ["k": "w", "d": "w", "i": "w", "u": "w"] }
            let img = sprite(daze > 0 ? "tt_kaw_dazed" : "tt_kaw_fly", daze > 0 ? 0 : Int(t * 10) % 3, flip: face > 0,
                             remap: remap, scale: 2)
            s.blit(img, x - 16, y - 12)
            if kind == "storm" && Int(t * 10) % 3 == 0 {
                for i in 0 ..< 3 {
                    let a = t * 5 + Double(i) * 2.1
                    s.fillRect(col("yellow"), Int(Double(x) + cos(a) * 20), Int(Double(y) + sin(a) * 14), 2, 2)
                }
            }
        case "vac":
            let body = hit ? col("white") : col(daze > 0 ? "red" : "darkgray")
            s.ellipse(col("black"), x - 17, y - 8, 34, 16)
            s.ellipse(body, x - 16, y - 7, 32, 14)
            s.ellipse(col("gray"), x - 13, y - 7, 26, 6)
            s.fillRect(col("black"), x - 7, y - 4, 14, 5)
            let eye = daze > 0 ? "yellow" : (glow > 0 ? "red" : "lime")
            s.fillRect(col(eye), x - 5 + face, y - 3, 3, 2)
            s.fillRect(col(eye), x + 2 + face, y - 3, 3, 2)
            let nx = x + face * 16
            s.fillRect(col("black"), min(nx, nx + face * 7), y, 8, 5)
            s.fillRect(col("gray"), min(nx, nx + face * 7) + 1, y + 1, 6, 3)
            for i in stride(from: -12, to: 13, by: 4) { s.fillRect(col("yellow"), x + i, y + 5, 2, 1) }
            if daze > 0 {
                for i in 0 ..< 3 { s.fillRect(col("white"), x - 4 + i * 4, y - 12 - Int(ttFmod(t * 20 + Double(i * 5), 10)), 2, 2) }
            }
        case "mouse":
            let sq = Int(squash * 5)
            s.ellipse(col("black"), x - 18, y - 10 + sq, 36, 20 - sq)
            s.ellipse(hit ? col("white") : col("gray"), x - 17, y - 9 + sq, 34, 18 - sq)
            let ex = x + face * 9
            for dx in [-5, 5] {
                s.circle(col("black"), ex + dx - face * 4, y - 10 + sq, 5)
                s.circle(col("pink"), ex + dx - face * 4, y - 10 + sq, 3)
            }
            Cute.eyes(s, ex - face * 2, y - 3 + sq, 3, look: face, mood: daze > 0 ? "sleepy" : "angry")
            s.circle(col("pink"), x + face * 17, y + sq, 2)
            let X = Double(x), Y = Double(y + sq)
            s.polygon(col("yellow"), [(X - 6, Y - 9), (X - 6, Y - 15), (X - 3, Y - 12), (X, Y - 16), (X + 3, Y - 12), (X + 6, Y - 15), (X + 6, Y - 9)])
            let kw = 2 + Int(abs(sin(t * (daze > 0 ? 2 : 9))) * 4)
            let kx = x - face * 18
            s.fillRect(col("yellow"), kx - 1, y - 4 + sq, 3, 3)
            s.fillRect(col("orange"), kx - kw, y - 7 + sq, 2 * kw + 1, 2)
            s.line(col("pink"), x - face * 15, y + 5, x - face * 24, y + 1)
        case "spritz":
            let sq = Int(squash * 4)
            s.rect(col("black"), IRect(x - 10, y - 12 + sq, 20, 25 - sq), radius: 4)
            s.rect(hit ? col("white") : col("sky"), IRect(x - 9, y - 11 + sq, 18, 23 - sq), radius: 4)
            s.fillRect(col("blue"), x - 9, y + 4, 18, 8)
            s.fillRect(col("white"), x - 6, y - 6 + sq, 12, 8)
            Cute.eyes(s, x, y - 3 + sq, 3, look: face, mood: daze > 0 ? "sleepy" : "angry")
            s.fillRect(col("black"), x - 4, y - 16 + sq, 8, 5)
            s.fillRect(col("blue"), x - 3, y - 15 + sq, 6, 3)
            let nx = x + face * 4
            s.fillRect(col("blue"), min(nx, nx + face * 6), y - 15 + sq, 7, 2)
            s.fillRect(col("black"), x + face * 3 - 1, y - 11 + sq, 2, 4)
        case "dot":
            let pulse = 1 + Int(abs(sin(t * 6)) * 2)
            let rr = r + (daze > 0 ? 4 : 0)
            for i in stride(from: 3, to: 0, by: -1) { s.circle(lerpCol("red", "deep", Double(i) * 0.25), x, y, rr + i * 2 + pulse) }
            s.circle(col(hit ? "white" : "red"), x, y, rr)
            s.circle(col("hotpink"), x - 2, y - 2, rr / 2)
            s.fillRect(col("white"), x - 3, y - 3, 2, 2)
            if daze > 0 {
                Cute.eyes(s, x, y + 1, 3, look: 0, mood: "sleepy")
            } else {
                for i in 0 ..< 4 {
                    s.fillRect(col("hotpink"), Int(Double(x) - vx * 0.02 * Double(i)) - 1, Int(Double(y) - vy * 0.02 * Double(i)) - 1, 2, 2)
                }
            }
        case "golem":
            let sq = Int(squash * 4)
            s.circle(col("black"), x, y + sq / 2, r + 1)
            s.circle(col(hit ? "white" : "hotpink"), x, y + sq / 2, r)
            for j in 0 ..< 4 {
                let a = (mode == "roll" ? Double(x) * 0.08 : 0) + Double(j) * 0.8
                let dx = cos(a) * Double(r), dy = sin(a) * Double(r)
                s.line(col("purple"), Int(Double(x) - dx * 0.9), Int(Double(y) - dy * 0.9), Int(Double(x) + dx * 0.9), Int(Double(y) + dy * 0.9))
            }
            Cute.eyes(s, x + face * 2, y - 3, 4, look: face, mood: daze > 0 ? "sleepy" : "angry", size: 2)
            for side in [-1, 1] {
                let wob = Int(sin(t * 6 + Double(side)) * 3)
                s.line(col("hotpink"), x + side * r, y, x + side * (r + 6), y - 6 + wob)
            }
        default:
            break
        }
        if daze > 0 {
            for i in 0 ..< 3 {
                let a = t * 6 + Double(i) * 2.1
                s.fillRect(col("yellow"), Int(Double(x) + cos(a) * Double(r + 2)), Int(Double(y - r - 4) + sin(a) * 3), 2, 2)
            }
        } else if glow > 0 && mode != "rest" && mode != "rise" {
            drawText(s, "!", x, y - r - 14, Int(t * 12) % 2 == 1 ? "red" : "yellow", align: .center, shadow: nil)
        }
    }
}
