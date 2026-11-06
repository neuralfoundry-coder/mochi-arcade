// HAIRBALL HAVOC bosses (port of the boss half of games/hairball_havoc.py): movement, telegraphed attacks,
// phases, parts, hits and the telegraph drawing. Every 10th stage; drawing of the bodies is in HairballHavocArt.swift.
import Foundation

extension HairballHavoc {
    func partPos(_ b: HHBoss, _ i: Int) -> (Double, Double) {
        let p = b.parts[i]
        if b.kind == 4 {
            let idx = b.trail.count - 1 - 11 * (i + 1)
            return b.trail[max(0, idx)]
        }
        if b.kind == 3 { return (b.x + p.dx + sin(b.t * 3 + Double(i)) * 3, b.y + p.dy + cos(b.t * 2.4 + Double(i) * 1.3) * 2) }
        return (b.x + p.dx, b.y + p.dy)
    }

    func laneOrigin(_ b: HHBoss) -> (Double, Double) { b.kind == 2 ? (b.x, b.y - 14) : muzzle(b) }

    func muzzle(_ b: HHBoss) -> (Double, Double) {
        if b.kind == 1 { return (b.x, b.y + 9) }
        if b.kind == 2 { return b.head }
        if b.kind == 4 { return (b.x + Double(b.face) * 6, b.y - 12) }
        return (b.x, b.y - 2)
    }

    func minions() -> Int { toys.filter { $0.alive && $0.minion }.count }
    func laneLen(_ b: HHBoss) -> Double { b.kind == 2 ? 120 : 260 }

    func updateBoss(_ dt: Double) {
        guard let b = boss else { return }
        b.t += dt
        b.flash = max(0, b.flash - dt)
        for i in b.parts.indices { b.parts[i].flash = max(0, b.parts[i].flash - dt) }
        if b.kind == 4 {
            if b.trail.isEmpty || abs(b.trail[b.trail.count - 1].0 - b.x) + abs(b.trail[b.trail.count - 1].1 - b.y) >= 2 {
                b.trail.append((b.x, b.y))
                if b.trail.count > 90 { b.trail.removeFirst() }
            }
        }
        if b.kind == 2 {                     // the king's head bobs on its spring (or punches along a lane)
            if b.atk == "lane" && b.ext > 0 && !b.lanes.isEmpty {
                let (ax, ay) = b.lanes[0]
                b.head = (b.x + ax * 120 * b.ext, b.y - 14 + ay * 120 * b.ext)
            } else {
                b.head = (b.x + sin(b.t * 2) * 3, b.y - 22 + sin(b.t * 4) * 2)
            }
        }
        if b.state == "enter" {
            let u = min(1, b.t / 2.6)
            b.y = Double(HH_IY0 - 30) + (b.hy - Double(HH_IY0) + 30) * easeOut(u)
            b.moving = true
            if u >= 1 { b.state = "fight"; b.rest = 1.0 }
            return
        }
        if b.state == "dying" {
            b.at += dt
            if Int(b.at * 10) != Int((b.at - dt) * 10) {
                parts.burst(b.x + hhRnd(-b.bw / 2, b.bw / 2), b.y + hhRnd(-b.bh / 2, b.bh / 2), 14, ["white", "yellow", "orange", "pink"], 90, 0.6)
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
        if b.atk == nil {
            b.rest -= dt
            if b.rest <= 0 { beginAttack(b) }
        } else {
            b.at += dt
            if runAttack(b, dt) {
                b.atk = nil
                b.ext = 0
                b.z = 0
                b.rest = st.rest * (1 - 0.1 * Double(b.phase))
            }
        }
        bossMove(b, dt)
        if b.phase < b.nphase - 1 && b.hp <= b.maxhp * (1 - Double(b.phase + 1) / Double(b.nphase)) {
            b.phase += 1
            b.atk = nil; b.rest = 1.2; b.ext = 0; b.z = 0
            cancelBullets()
            hype.banner("ANGRY!!", "PHASE \(b.phase + 1)", color: "red", dur: 1.2, sound: "warning")
            hype.flash("red", 0.25)
            hype.hitstop(0.12)
            app.shake(4, 0.4)
        }
    }

    func bossMove(_ b: HHBoss, _ dt: Double) {
        let busy = b.atk == "charge" || b.atk == "hop"
        let old = b.x
        if b.kind == 4 {                    // the train never stops: it steers around the room
            if !busy {
                b.wt -= dt
                if b.wt <= 0 || abs(b.wx - b.x) + abs(b.wy - b.y) < 20 {
                    b.wt = hhRnd(2.0, 3.5)
                    b.wx = hhRnd(60, 260); b.wy = hhRnd(50, 160)
                }
                let want = atan2(b.wy - b.y, b.wx - b.x)
                let diff = hhMod(want - b.heading + .pi, HH_TAU) - .pi
                b.heading += max(-2.2 * dt, min(2.2 * dt, diff))
                let v = 52 + 8 * Double(b.lv) + (b.parts.contains { $0.alive } ? 0 : 20) + 6 * Double(b.phase)
                b.x += cos(b.heading) * v * dt
                b.y += sin(b.heading) * v * dt
                b.x = max(Double(HH_IX0) + 14, min(Double(HH_IX1) - 14, b.x))
                b.y = max(Double(HH_IY0) + 12, min(Double(HH_IY1) - 12, b.y))
            }
        } else if !busy && b.atk != "suck" {
            b.wt -= dt
            if b.wt <= 0 {
                b.wt = hhRnd(2.0, 3.2)
                b.wx = hhRnd(70, 250); b.wy = hhRnd(56, b.kind != 3 ? 110 : 96)
            }
            let dx = b.wx - b.x, dy = b.wy - b.y
            let d = hypot(dx, dy)
            let v = (26 + 6 * Double(b.lv)) * (b.atk != nil ? 0.4 : 1.0)
            if d > 2 {
                b.x += dx / d * min(d, v * dt)
                b.y += dy / d * min(d, v * dt)
            }
        }
        b.moving = abs(b.x - old) > 0.05 || busy
        if abs(b.x - old) > 0.05 { b.face = b.x > old ? 1 : -1 }
    }

    func beginAttack(_ b: HHBoss) {
        let names = b.phases[b.phase]
        var a = names[b.ai % names.count]
        b.ai += 1
        if a == "summon" && minions() >= 6 { a = "fan" }
        if a == "turret" && !b.parts.contains(where: { $0.alive }) { a = "fan" }
        if a == "hop" && b.kind == 4 { a = "charge" }
        b.atk = a; b.at = 0; b.an = 0
        let tpx = max(Double(HH_IX0) + 20, min(Double(HH_IX1) - 20, px))
        let tpy = max(Double(HH_IY0) + 20, min(Double(HH_IY1) - 16, py))
        if a == "lane" {
            let (mx, my) = laneOrigin(b)
            let base = atan2(py - my, px - mx)
            b.lanes = [(cos(base), sin(base))]
            if b.kind != 2 && (b.lv >= 2 || b.phase >= 2) {
                for off in [0.5, -0.5] { b.lanes.append((cos(base + off), sin(base + off))) }
            }
        } else if a == "rain" {
            let n = min(12, 4 + 2 * b.lv + b.phase)
            b.spots = [(tpx, tpy)]
            for _ in 0 ..< n - 1 {
                b.spots.append((hhRnd(Double(HH_IX0) + 16, Double(HH_IX1) - 16), hhRnd(Double(HH_IY0) + 16, Double(HH_IY1) - 12)))
            }
        } else if a == "charge" || a == "hop" {
            b.tx = tpx; b.ty = tpy
            b.sx = b.x; b.sy = b.y
        } else if a == "spiral" {
            b.dir = b.ai % 2 == 1 ? 1 : -1
            b.ang = hhRnd(0, HH_TAU)
        }
    }

    /// Advance the current attack; true when it is over. Every attack starts with a readable telegraph.
    func runAttack(_ b: HHBoss, _ dt: Double) -> Bool {
        guard let a = b.atk else { return true }
        let at = b.at, lv = b.lv, ph = b.phase
        let bv = st.bv * spd
        let (mx, my) = muzzle(b)
        let kind = HH_BOSS_BULLET[b.kind]
        let au = app.audio
        switch a {
        case "fan":
            let tele = 0.5, per = 0.45
            let vol = min(3, 1 + (lv + ph) / 2)
            while at - tele >= Double(b.an) * per && b.an < vol {
                var n = 5 + lv + ph
                n += 1 - n % 2
                let base = atan2(py - my, px - mx)
                for i in 0 ..< n { bshot(mx, my, base + Double(i - n / 2) * 0.2, bv, kind) }
                b.an += 1
                au.play("shoot")
            }
            return at >= tele + Double(vol) * per
        case "ring":
            let tele = 0.6, per = 0.5
            let vol = min(3, 1 + (lv + ph) / 2)
            while at - tele >= Double(b.an) * per && b.an < vol {
                let n = min(28, 10 + 2 * lv + 2 * ph)
                let off = Double(b.an % 2) * .pi / Double(n)
                for i in 0 ..< n { bshot(b.x, b.y, off + Double(i) * HH_TAU / Double(n), bv * 0.8, kind) }
                b.an += 1
                au.play("pop")
            }
            return at >= tele + Double(vol) * per
        case "spiral":
            let tele = 0.4, dur = 2.2, step = 0.075
            let arms = min(4, 2 + lv / 2)
            while at - tele >= Double(b.an) * step && Double(b.an) * step < dur {
                for i in 0 ..< arms { bshot(b.x, b.y, b.ang + Double(i) * HH_TAU / Double(arms), bv * 0.75, kind) }
                b.ang += b.dir * 0.3
                b.an += 1
            }
            return at >= tele + dur
        case "charge":
            let tele = 0.7
            if at < tele { return false }
            if b.an == 0 {
                let dx = b.tx - b.x, dy = b.ty - b.y
                let d = hypot(dx, dy)
                let step = (230 + 20 * Double(lv)) * dt
                if d <= step || at > tele + 1.3 {
                    b.an = 1; b.aux = at
                    if lv >= 1 || ph >= 1 {
                        let n = 8 + 2 * lv
                        for i in 0 ..< n { bshot(b.x, b.y, Double(i) * HH_TAU / Double(n), bv * 0.7, kind) }
                    }
                    app.shake(4, 0.3)
                    au.play("boom")
                } else {
                    b.x += dx / d * step
                    b.y += dy / d * step
                    if b.kind == 4 { b.heading = atan2(dy, dx) }
                }
                return false
            }
            return at >= b.aux + 0.4
        case "hop":
            let tele = 0.7, air = 0.6
            if at < tele { return false }
            let u = min(1, (at - tele) / air)
            b.x = b.sx + (b.tx - b.sx) * u
            b.y = b.sy + (b.ty - b.sy) * u
            b.z = sin(.pi * u) * 40
            if u >= 1 && b.an == 0 {
                b.an = 1
                b.z = 0
                let n = 10 + 2 * lv
                for i in 0 ..< n { bshot(b.x, b.y + 6, Double(i) * HH_TAU / Double(n), bv * 0.7, kind) }
                app.shake(5, 0.35)
                au.play("boom")
                parts.burst(b.x, b.y + 10, 20, ["white", "gray"], 70, 0.5)
            }
            return at >= tele + air + 0.5
        case "summon":
            if at >= 0.6 && b.an == 0 {
                b.an = 1
                for i in 0 ..< min(4, 2 + lv) {
                    let e = spawnToy(b.minion, b.x + (Double(i) - 1.5) * 12, b.y + 14, false)
                    e.minion = true
                }
                au.play("bubble")
            }
            return at >= 1.0
        case "suck":
            let tele = 0.8, dur = 2.6
            if tele <= at && at < tele + dur && deadT == nil {
                let dx = b.x - px, dy = b.y - py
                let d = max(1, hypot(dx, dy))
                let pull = 52 + 12 * Double(lv)
                pullX += dx / d * pull
                pullY += dy / d * pull
                while at - tele >= Double(b.an) * 0.16 {
                    b.an += 1
                    let side = Int.random(in: 0 ..< 3)
                    var sx: Double, sy: Double
                    if side == 0 {
                        sx = hhRnd(Double(HH_IX0) + 4, Double(HH_IX1) - 4); sy = Double(HH_IY1) - 4
                    } else {
                        sx = side == 1 ? Double(HH_IX0) + 4 : Double(HH_IX1) - 4
                        sy = hhRnd(Double(HH_IY0) + 10, Double(HH_IY1) - 6)
                    }
                    let ang = atan2(b.y - sy, b.x - sx)
                    let v = bv * 0.75
                    bullets.append(HHBullet(sx, sy, cos(ang) * v, sin(ang) * v, 3, hypot(b.x - sx, b.y - sy) / v))
                }
            }
            return at >= tele + dur
        case "lane":
            let tele = 0.7
            if at < tele { return false }
            let u = at - tele
            if u < 0.18 { b.ext = u / 0.18 } else if u < 0.63 { b.ext = 1 } else { b.ext = max(0, 1 - (u - 0.63) / 0.3) }
            if b.an == 0 {
                b.an = 1
                au.play(b.kind == 2 ? "jump" : "shoot")
            }
            return u >= 0.93
        case "rain":
            let tele = 0.9
            if at >= tele + 0.3 && b.an == 0 {
                b.an = 1
                let n = lv >= 1 ? 6 : 4
                for (sx, sy) in b.spots {
                    for i in 0 ..< n { bshot(sx, sy, Double(i) * HH_TAU / Double(n) + 0.4, bv * 0.6, kind) }
                    parts.burst(sx, sy, 6, ["white", "yellow"], 50, 0.3)
                    if deadT == nil && inv <= 0 && hypot(px - sx, py - sy) < 10 { hurt() }
                }
                au.play("explode")
            }
            return at >= tele + 0.8
        case "turret":
            let dur = 2.2
            let alive = b.parts.indices.filter { b.parts[$0].alive }
            while !alive.isEmpty && Double(b.an) * 0.3 <= min(at, dur) - 0.2 {
                let i = alive[b.an % alive.count]
                let (qx, qy) = partPos(b, i)
                let base = atan2(py - qy, px - qx)
                for off in (lv >= 2 ? [-0.12, 0.12] : [0.0]) { bshot(qx, qy, base + off, bv, kind) }
                b.parts[i].flash = 0.1
                b.an += 1
                au.play("shoot")
            }
            return at >= dur || alive.isEmpty
        default:
            return true
        }
    }

    func bossHitsPlayer(_ b: HHBoss) {
        if b.z < 8 {
            if abs(b.x - px) <= b.bw / 2 - 2 + HH_HB && abs(b.y - py) <= b.bh / 2 - 2 + HH_HB { hurt(); return }
        }
        if b.atk == "lane" && b.ext >= 0.5 {
            let (mx, my) = laneOrigin(b)
            let L = laneLen(b) * b.ext
            for (ax, ay) in b.lanes where hhSegDist(px, py, mx, my, mx + ax * L, my + ay * L) < 4 + HH_HB { hurt(); return }
        }
        if b.kind == 2 && hypot(b.head.0 - px, b.head.1 - b.z - py) < 8 + HH_HB { hurt(); return }
        if b.kind == 3 || b.kind == 4 {
            for i in b.parts.indices where b.parts[i].alive {
                let (qx, qy) = partPos(b, i)
                if hypot(qx - px, qy - py) < Double(b.parts[i].r) + HH_HB { hurt(); return }
            }
        }
    }

    func shotBoss(_ sh: HHShot) {
        guard let b = boss, b.state == "fight", b.z < 8 else { return }
        for i in b.parts.indices where b.parts[i].alive {
            let (qx, qy) = partPos(b, i)
            let rr = Double(b.parts[i].r + sh.r)
            if (sh.x - qx) * (sh.x - qx) + (sh.y - qy) * (sh.y - qy) <= rr * rr {
                hurtPart(b, i, sh.dmg)
                sh.life = 0
                return
            }
        }
        if b.kind == 2 && b.atk == "lane" && b.ext > 0.3 {
            let (hx, hy) = b.head
            let rr = Double(9 + sh.r)
            if (sh.x - hx) * (sh.x - hx) + (sh.y - hy) * (sh.y - hy) <= rr * rr {
                hurtBoss(sh.dmg * 2)
                parts.sparkle(hx, hy - 8, "yellow")
                sh.life = 0
                return
            }
        }
        if abs(sh.x - b.x) <= b.bw / 2 + Double(sh.r) && abs(sh.y - b.y) <= b.bh / 2 + Double(sh.r) {
            hurtBoss(sh.dmg)
            sh.life = 0
        }
    }

    func hurtPart(_ b: HHBoss, _ i: Int, _ dmg: Double) {
        b.parts[i].hp -= dmg
        b.parts[i].flash = 0.08
        if b.parts[i].hp <= 0 {
            b.parts[i].alive = false
            broken += 1
            let (qx, qy) = partPos(b, i)
            parts.burst(qx, qy, 24, ["white", "yellow", "orange"], 100, 0.7)
            add(2000, qx, qy - 10, "orange")
            app.audio.play("explode")
            app.shake(3, 0.2)
            hurtBoss(b.maxhp * 0.06)
        }
    }

    func hurtBoss(_ dmg: Double) {
        guard let b = boss, b.state == "fight" else { return }
        b.hp -= dmg
        if b.flash <= 0 { app.audio.play("tin") }
        b.flash = 0.08
        if b.hp <= 0 {
            b.hp = 0
            b.state = "dying"; b.at = 0; b.atk = nil; b.ext = 0; b.z = 0
            cancelBullets()
            for e in toys where e.alive {
                e.alive = false
                parts.burst(e.x, e.y, 10, HH_TOY_COLORS[e.kind]!, 70, 0.5)
            }
            add(5000 * (1 + tierN / 5), b.x, b.y - 20, "yellow")
            app.audio.play("bossdown")
            hype.slowmo(0.3, 1.4)
            hype.hitstop(0.15)
            hype.flash("white", 0.3)
            hype.banner("KO!!", "\(b.name) IS UNWOUND", dur: 2.0, rainbow: true)
            app.shake(5, 0.6)
        }
    }

    // ------------------------------------------------------------------ draw
    func drawBoss(_ s: Surface, _ b: HHBoss) {
        var ps: [HHArt.Part] = []
        for i in b.parts.indices {
            let (qx, qy) = partPos(b, i)
            ps.append((Int(qx), Int(qy), b.parts[i].r, b.parts[i].alive, b.parts[i].flash > 0))
        }
        let look = max(-2, min(2, Int((px - b.x) / 30)))
        let ox = (b.atk == "charge" || b.atk == "hop") && b.at < 0.7 ? Int(sin(t * 50) * 2) : 0
        HHArt.boss(s, b, Int(b.x) + ox, Int(b.y), t, look, ps, b.flash > 0 && Int(t * 30) % 2 == 0)
        if let a = b.atk, b.at < 0.5, ["fan", "ring", "spiral", "summon", "turret"].contains(a) {
            let (mx, my) = a == "fan" ? muzzle(b) : (b.x, b.y)
            let r = Int(14 * (1 - b.at / 0.5)) + 2
            s.circle(col(Int(t * 20) % 2 == 1 ? "white" : "yellow"), Int(mx), Int(my), r, width: 1)
        }
    }

    /// Telegraphs under everything: lane lines, rain shadows, charge path, hop target, suction.
    func drawTells(_ s: Surface, _ b: HHBoss) {
        let blink = Int(t * 12) % 2 == 1
        if b.atk == "lane" && b.at < 0.7 {
            let (mx, my) = laneOrigin(b)
            let L = laneLen(b)
            for (ax, ay) in b.lanes {
                for i in stride(from: 4, to: Int(L), by: 7) {
                    s.fillRect(col(blink ? "red" : "white"), Int(mx + ax * Double(i)), Int(my + ay * Double(i)), 2, 2)
                }
            }
        } else if b.atk == "rain" && b.at < 1.2 {
            for (sx, sy) in b.spots {
                let r = 3 + Int(min(1, b.at / 0.9) * 7)
                s.ellipse(col("black"), Int(sx) - r, Int(sy) - r / 2, r * 2, r)
                if b.at < 0.9 {
                    s.circle(col(blink ? "red" : "yellow"), Int(sx), Int(sy), 10, width: 1)
                } else {
                    let fy = Int(sy - (1.2 - b.at) / 0.3 * 60)
                    HHArt.bullet(s, HH_BOSS_BULLET[b.kind], Int(sx), fy, t)
                }
            }
        } else if b.atk == "charge" && b.at < 0.7 {
            let (ux, uy) = hhNorm(b.tx - b.x, b.ty - b.y)
            let d = Int(hypot(b.tx - b.x, b.ty - b.y))
            for i in stride(from: 0, to: d, by: 8) {
                s.fillRect(col(blink ? "red" : "orange"), Int(b.x + ux * Double(i)) - 1, Int(b.y + uy * Double(i)) - 1, 3, 3)
            }
            s.circle(col("red"), Int(b.tx), Int(b.ty), 8, width: 1)
        } else if b.atk == "hop" && b.an == 0 {
            let r = 6 + Int(min(1, b.at / 0.7) * 12)
            s.ellipse(col("black"), Int(b.tx) - r, Int(b.ty) + 4 - r / 3, r * 2, r * 2 / 3)
            s.circle(col(blink ? "red" : "yellow"), Int(b.tx), Int(b.ty) + 4, r, width: 1)
        } else if b.atk == "suck" {
            for i in 0 ..< 10 {
                let a = Double(i) * HH_TAU / 10 + t
                let r = 80 - hhMod(t * 70 + Double(i) * 13, 70)
                s.fillRect(col(b.at > 0.8 ? "white" : "gray"), Int(b.x + cos(a) * r), Int(b.y + sin(a) * r), 2, 1)
            }
        }
    }
}
