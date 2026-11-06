// CLOUD POUNCE sky bosses (port of games/cloud_pounce_boss.py): HOOTSTORM, BILLOWHALE, RIBBON DRAKE,
// BLINKER SAUCER and NOCTURNE. SORA hurts a boss by landing on its head; every attack is telegraphed first.
// Coordinates: x on the 224 px wrapping field, h = altitude (screen y = 200 - h, the arena camera never moves).
import Foundation

private let BASE_H: [String: Double] = ["owl": 150, "whale": 152, "kite": 148, "ufo": 160, "eclipse": 146]
private let SIZE: [String: (Double, Double)] = ["owl": (14, 14), "whale": (26, 10), "kite": (9, 9), "ufo": (22, 8), "eclipse": (15, 15)]
private let ATTACKS: [String: [String]] = [
    "owl": ["feathers", "bolt", "gust"],
    "whale": ["spout", "geyser", "dive"],
    "kite": ["lanterns", "swoop", "ring"],
    "ufo": ["dots", "beam", "drones"],
    "eclipse": ["crescents", "starfall", "eclipse"],
]
private let TELE: [String: Double] = ["feathers": 0.7, "bolt": 0.9, "gust": 0.8, "spout": 0.6, "geyser": 1.0, "dive": 1.0,
                                      "lanterns": 0.6, "swoop": 0.9, "ring": 0.7, "dots": 0.5, "beam": 0.8, "drones": 0.5,
                                      "crescents": 0.6, "starfall": 0.9, "eclipse": 0.6]

final class CPProj {
    let kind: String
    var x, h, vx, vh: Double
    let life, grav, r: Double
    var age = 0.0
    var alive = true
    var ox = 0.0, oh = 0.0          // crescents: where they were thrown from
    init(_ kind: String, _ x: Double, _ h: Double, _ vx: Double, _ vh: Double, _ life: Double = 6, grav: Double = 0, r: Double = 3) {
        self.kind = kind; self.x = x; self.h = h; self.vx = vx; self.vh = vh; self.life = life; self.grav = grav; self.r = r
    }
}

final class CPBoss {
    unowned let g: CloudPounce
    let kind, name: String
    let tier: Int
    var maxhp, hp: Int
    var rate, spd: Double
    var attacks: [String]
    var state = "enter"
    var x = CP.FWd / 2, h = 270.0
    let baseH: Double
    var t = 0.0, atkT = 2.2
    var atkI = 0
    var flash = 0.0, inv = 0.0
    var phase = 1
    var dieT = 0.0
    var tele: (a: String, left: Double, full: Double, x: Double, h: Double)?
    var projs: [CPProj] = []
    var cols: [(kind: String, x: Double, hw: Double, lo: Double, hi: Double, left: Double)] = []
    var push = 0.0, pushT = 0.0
    var dark = 0.0, darkT = 0.0
    var dotl: [(x: Double, h: Double, life: Double, ph: Double)] = []
    var drones: [(x: Double, h: Double, vx: Double, life: Double)] = []
    var dir = 1.0                   // whale heading
    var mode = ""                   // dive / swoop in progress
    var modeT = 0.0
    var mx = 0.0, mh = 0.0          // dive / swoop target
    var tx = 0.0, th = 0.0          // where the last telegraphed attack aims
    var trail: [(Double, Double)] = []
    var trailT = 0.0, angryT = 0.0, boomT = 0.0

    init(_ game: CloudPounce, _ spec: CPBossSpec) {
        g = game
        kind = spec.kind; name = spec.name; tier = spec.tier
        maxhp = spec.hp; hp = spec.hp
        rate = spec.rate
        spd = spec.speed * (0.85 + 0.15 * game.fspeed)
        attacks = (ATTACKS[spec.kind] ?? []) + spec.extra
        baseH = BASE_H[spec.kind] ?? 150
    }

    // ------------------------------------------------------------------ queries for the game
    /// (x, altitude of the head top, half width) or nil.
    func stompZone() -> (Double, Double, Double)? {
        if state != "fight" || mode == "dive" { return nil }
        let (hw, hh) = SIZE[kind]!
        return (x, h + hh, hw)
    }

    /// NOCTURNE's star shields block a stomp while one sits on top of its head.
    func blocked(_ x: Double) -> Bool {
        if kind != "eclipse" { return false }
        return shieldAngles().contains { sin($0) > 0.82 }
    }

    func shieldAngles() -> [Double] {
        let n = 3 + (tier >= 10 ? 1 : 0)
        let sp = 1.5 * spd * (dark > 0.5 ? 2.0 : 1.0)
        return (0 ..< n).map { t * sp + Double($0) * 2 * .pi / Double(n) }
    }

    /// Does SORA's box (centre cx, cy, half sizes rx, ry) touch anything harmful?
    func touch(_ cx: Double, _ cy: Double, _ rx: Double, _ ry: Double) -> Bool {
        if state != "fight" { return false }
        let (hw, hh) = SIZE[kind]!
        if abs(cpWrapd(cx - x)) < hw + rx - 3 && abs(cy - h) < hh + ry - 3 { return true }
        if kind == "kite" {
            for (sx, sh) in segments() where abs(cpWrapd(cx - sx)) < rx + 3 && abs(cy - sh) < ry + 3 { return true }
        }
        if kind == "eclipse" {
            for a in shieldAngles() {
                let sx = x + cos(a) * 24, sh = h + sin(a) * 24
                if abs(cpWrapd(cx - sx)) < rx + 2 && abs(cy - sh) < ry + 2 && sin(a) < 0.82 { return true }
            }
        }
        for p in projs where abs(cpWrapd(cx - p.x)) < rx + p.r - 1 && abs(cy - p.h) < ry + p.r - 1 {
            p.alive = false
            return true
        }
        for c in cols where abs(cpWrapd(cx - c.x)) < c.hw + rx - 2 && c.lo < cy && cy < c.hi { return true }
        for d in drones where abs(cpWrapd(cx - d.x)) < rx + 5 && abs(cy - d.h) < ry + 3 { return true }
        return false
    }

    /// Drones squashed by SORA's feet (falling onto them). Returns how many.
    func stompMinions(_ px: Double, _ ph: Double, _ vh: Double) -> Int {
        if vh >= 0 { return 0 }
        var n = 0
        for i in drones.indices {
            let d = drones[i]
            if d.life > 0 && abs(cpWrapd(px - d.x)) < 9 && d.h - 2 <= ph && ph <= d.h + 7 {
                drones[i].life = 0
                n += 1
                g.parts.burst(d.x, Double(g.sy(d.h)), 10, ["lime", "white", "gray"], 60, 0.4)
            }
        }
        drones.removeAll { $0.life <= 0 }
        return n
    }

    func dots() -> [(Double, Double)] { dotl.map { ($0.x, $0.h) } }

    /// RIBBON DRAKE's tail: points along its recent path.
    func segments() -> [(Double, Double)] {
        var out: [(Double, Double)] = []
        for i in 1 ..< 8 {
            let k = i * 3
            if k < trail.count { out.append(trail[k]) }
        }
        return out
    }

    @discardableResult
    func hit(_ dmg: Int) -> Bool {
        if state != "fight" { return false }
        flash = 0.25
        if inv > 0 { return false }
        inv = 0.45
        hp -= dmg
        if hp <= 0 {
            hp = 0
            state = "dead"
            dieT = 0
            projs = []; cols = []; dotl = []; drones = []
            tele = nil
            push = 0
            dark = 0
            return true
        }
        if phase == 1 && hp <= maxhp / 2 {
            phase = 2
            spd *= 1.2
            rate *= 0.8
            angryT = 1.2
            g.hype.banner("\(name) IS ANGRY!", color: "red", dur: 1.2, scale: 1, sound: "warning")
            for a in ATTACKS[kind]! where !attacks.contains(a) { attacks.append(a) }
        }
        return true
    }

    // ------------------------------------------------------------------ update
    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        inv = max(0, inv - dt)
        angryT = max(0, angryT - dt)
        if state == "dead" {
            dieT += dt
            boomT -= dt
            if boomT <= 0 {
                boomT = 0.12
                g.parts.burst(x + .random(in: -16 ... 16), Double(g.sy(h + .random(in: -10 ... 10))), 10,
                              ["white", "yellow", "orange", "hotpink"], 80, 0.5)
                g.app.audio.play("explode")
            }
            if dieT > 0.9 { h -= 90 * dt }
            return
        }
        move(dt)
        if state == "enter" {
            h = max(baseH, h - 90 * dt)
            return
        }
        updateAttacks(dt)
        updateShots(dt)
    }

    func move(_ dt: Double) {
        let sp = spd
        if mode == "dive" {
            modeT += dt
            if modeT < 1.4 {
                h -= 230 * dt
                x = mx
            } else {
                mode = ""
                h = 260
                state = "fight"
            }
            return
        }
        if mode == "swoop" {
            modeT += dt
            x = cpFmod(mx + dir * 250 * sp * modeT, CP.FWd)
            h += (mh - h) * min(1, dt * 6)
            recordTrail(dt)
            if modeT > 1.1 { mode = "" }
            return
        }
        var tx0 = x, th0 = h
        switch kind {
        case "owl":
            tx0 = CP.FWd / 2 + sin(t * 0.7 * sp) * 70
            th0 = baseH + sin(t * 1.6) * 8
        case "whale":
            x = cpFmod(x + dir * 38 * sp * dt, CP.FWd)
            tx0 = x
            th0 = baseH + sin(t * 1.2) * 6
        case "kite":
            tx0 = CP.FWd / 2 + sin(t * 0.9 * sp) * 80
            th0 = baseH + sin(t * 1.8 * sp) * 16
        case "ufo":
            let dx = cpWrapd(g.x - x)
            if !(tele?.a == "beam") && !cols.contains(where: { $0.kind == "beam" }) {
                x = cpFmod(x + max(-1, min(1, dx / 30)) * 34 * sp * dt, CP.FWd)
            }
            tx0 = x
            th0 = baseH + sin(t * 2) * 5
        default:
            tx0 = CP.FWd / 2 + cos(t * 0.5 * sp) * 52
            th0 = baseH + sin(t * 0.5 * sp) * 12
        }
        if kind == "owl" || kind == "kite" || kind == "eclipse" {
            x += cpWrapd(tx0 - x) * min(1, dt * 3)
            x = cpFmod(x, CP.FWd)
        }
        if state == "fight" || h <= baseH + 1 { h += (th0 - h) * min(1, dt * 3) }
        if kind == "kite" { recordTrail(dt) }
    }

    func recordTrail(_ dt: Double) {
        trailT -= dt
        if trailT <= 0 {
            trailT = 0.03
            trail.insert((x, h), at: 0)
            if trail.count > 40 { trail.removeLast(trail.count - 40) }
        }
    }

    func updateAttacks(_ dt: Double) {
        if var tl = tele {
            tl.left -= dt
            if (tl.a == "bolt" || tl.a == "dive") && tl.left > 0.35 { tl.x = g.x }     // keeps aiming until just before it strikes
            tele = tl
            if tl.left <= 0 {
                tx = tl.x; th = tl.h
                tele = nil
                fire(tl.a)
            }
            return
        }
        if !mode.isEmpty { return }
        atkT -= dt
        if atkT <= 0 {
            atkT = rate * .random(in: 0.85 ... 1.15)
            var a = attacks[atkI % attacks.count]
            atkI += 1
            if Double.random(in: 0 ..< 1) < 0.3 { a = attacks.randomElement()! }
            if a == "eclipse" && darkT > 0 { a = "starfall" }
            var ax = g.x, ah = g.h + 7
            if a == "geyser" {
                let alive = g.clouds.filter { $0.alive }
                if let c = alive.min(by: { abs(cpWrapd($0.cx() - g.x)) + abs($0.hd - g.h) * 0.5 < abs(cpWrapd($1.cx() - g.x)) + abs($1.hd - g.h) * 0.5 }) {
                    ax = c.cx(); ah = c.hd
                }
            }
            if a == "swoop" { ah = max(40, min(170, g.h + 10)) }
            let tt = TELE[a] ?? 0.7
            tele = (a, tt, tt, ax, ah)
            g.app.audio.play(a == "dive" || a == "swoop" || a == "eclipse" ? "warning" : "select")
        }
    }

    func fire(_ a: String) {
        let sp = spd
        let au = g.app.audio
        let px = g.x, ph = g.h + 7
        let bx = x, bh = h
        switch a {
        case "feathers":
            let n = min(7, 3 + tier / 4 + (phase == 2 ? 1 : 0))
            let base = atan2(ph - bh, cpWrapd(px - bx))
            for i in 0 ..< n {
                let ang = base + (Double(i) - Double(n - 1) / 2) * 0.28
                projs.append(CPProj("feather", bx, bh, cos(ang) * 75 * sp, sin(ang) * 75 * sp, 5))
            }
            au.play("shoot")
        case "bolt":
            var xs = [tx]
            if phase == 2 { xs += [cpFmod(tx + 60, CP.FWd), cpFmod(tx - 60, CP.FWd)] }
            for x0 in xs { cols.append(("bolt", x0, 6, -20, 240, 0.35)) }
            au.play("explode")
            g.app.shake(2, 0.15)
        case "gust":
            push = (Double.random(in: 0 ..< 1) < 0.5 ? 1 : -1) * 170 * sp
            pushT = 2.0
            au.play("bubble")
        case "spout":
            for _ in 0 ..< 5 + (phase == 2 ? 1 : 0) {
                projs.append(CPProj("drop", bx, bh + 8, .random(in: -70 ... 70), .random(in: 150 ... 210), 5, grav: 230, r: 3))
            }
            au.play("bubble")
        case "geyser":
            cols.append(("geyser", tx, 7, th, 240, 0.8))
            au.play("bubble")
        case "dive":
            mode = "dive"
            modeT = 0
            mx = tx
            h = 240
            au.play("boom")
        case "lanterns":
            for i in 0 ..< 3 + (phase == 2 ? 1 : 0) {
                projs.append(CPProj("lantern", bx + Double((i - 1) * 14), bh - 6, Double((i - 1) * 12), -30 - Double(i * 4), 7, r: 4))
            }
            au.play("shoot")
        case "swoop":
            mode = "swoop"
            modeT = 0
            dir = cpWrapd(px - bx) > 0 ? 1 : -1
            mx = bx
            mh = th
            au.play("boom")
        case "ring":
            let n = 8 + (phase == 2 ? 4 : 0)
            for i in 0 ..< n {
                let ang = 2 * .pi * Double(i) / Double(n) + t
                projs.append(CPProj("confetti", bx, bh, cos(ang) * 70 * sp, sin(ang) * 70 * sp, 4))
            }
            au.play("pop")
        case "dots":
            for _ in 0 ..< 2 + (phase == 2 ? 1 : 0) {
                dotl.append((.random(in: 10 ... CP.FWd - 10), .random(in: 30 ... 130), 4.5, .random(in: 0 ... 6)))
            }
            au.play("type")
        case "beam":
            cols.append(("beam", bx, 6, -20, bh - 6, 0.7))
            au.play("shoot")
        case "drones":
            for i in 0 ..< 2 { drones.append((bx + Double((i * 2 - 1) * 14), bh - 8, Double(i * 2 - 1) * 20, 9)) }
            au.play("powerup")
        case "crescents":
            for side in [-1.0, 1.0] {
                let p = CPProj("crescent", bx, bh, side, 0, 2.4, r: 4)
                p.ox = bx; p.oh = bh
                p.vh = atan2(ph - bh, cpWrapd(px - bx) + side * 40)
                projs.append(p)
            }
            au.play("shoot")
        case "starfall":
            let n = 4 + (phase == 2 ? 1 : 0)
            for i in 0 ..< n {
                let x0 = cpFmod(tx + Double((i - n / 2) * 40), CP.FWd)
                projs.append(CPProj("star", x0, 210 + Double(i * 12), 0, -150 * sp, 3, r: 4))
            }
            au.play("coin")
        case "eclipse":
            darkT = 3.5
            au.play("boom")
        default: break
        }
    }

    func updateShots(_ dt: Double) {
        for p in projs {
            p.age += dt
            if p.kind == "crescent" {       // out and back like a boomerang
                let u = p.age / p.life
                let reach = 100 * sin(u * .pi)
                p.x = cpFmod(p.ox + cos(p.vh) * reach + p.vx * sin(u * .pi * 2) * 20, CP.FWd)
                p.h = p.oh + sin(p.vh) * reach
            } else {
                p.vh -= p.grav * dt
                if p.kind == "lantern" { p.vx = sin(p.age * 3 + p.ox) * 18 }
                p.x = cpFmod(p.x + p.vx * dt, CP.FWd)
                p.h += p.vh * dt
            }
            if p.age > p.life || p.h < -20 || p.h > 260 { p.alive = false }
        }
        projs.removeAll { !$0.alive }
        for i in cols.indices { cols[i].left -= dt }
        cols.removeAll { $0.left <= 0 }
        if pushT > 0 {
            pushT -= dt
            if pushT <= 0 { push = 0 }
        }
        if darkT > 0 {
            darkT -= dt
            dark = min(1, dark + dt * 2)
        } else {
            dark = max(0, dark - dt * 2)
        }
        for i in dotl.indices {
            dotl[i].life -= dt
            dotl[i].ph += dt
            let d = dotl[i]
            let dx = cpWrapd(g.x - d.x)
            dotl[i].x = cpFmod(d.x + (max(-1, min(1, dx / 40)) * 36 + sin(d.ph * 3) * 50) * dt, CP.FWd)
            dotl[i].h += ((g.h + 7 - d.h) * 0.6 + cos(d.ph * 2.3) * 40) * dt
        }
        dotl.removeAll { $0.life <= 0 }
        for i in drones.indices {
            drones[i].life -= dt
            let dx = cpWrapd(g.x - drones[i].x)
            drones[i].vx += max(-1, min(1, dx / 30)) * 40 * dt
            drones[i].vx = max(-30, min(30, drones[i].vx))
            drones[i].x = cpFmod(drones[i].x + drones[i].vx * dt, CP.FWd)
            drones[i].h = max(30, drones[i].h - 22 * dt)
        }
        drones.removeAll { $0.life <= 0 }
    }

    // ------------------------------------------------------------------ drawing
    func draw(_ s: Surface, _ t: Double) {
        if tele != nil { drawTele(s, t) }
        for c in cols { drawCol(s, c, t) }
        if !(state == "dead" && dieT > 1.4 && Int(t * 20) % 2 != 0) {
            for xd in [0, -CP.FW, CP.FW] {
                let bx = Int(x) + xd
                if -40 < bx && bx < CP.FW + 40 { drawBody(s, bx, g.sy(h), t) }
            }
        }
        for p in projs { cpDrawProj(s, p, Int(p.x), g.sy(p.h), t) }
        for d in dotl {
            let dx = Int(d.x), dy = g.sy(d.h)
            let r = 3 + Int(t * 10) % 2
            s.circle(col("hotpink"), dx, dy, r + 2, width: 1)
            s.circle(col("red"), dx, dy, r)
            s.fillRect(col("white"), dx - 1, dy - 1, 1, 1)
        }
        for d in drones {
            let dx = Int(d.x), dy = g.sy(d.h)
            if d.life < 1.5 && Int(t * 10) % 2 != 0 { continue }
            s.ellipse(col("black"), dx - 7, dy - 2, 15, 6)
            s.ellipse(col("gray"), dx - 6, dy - 1, 13, 4)
            s.circle(col("lime"), dx, dy - 2, 3)
            s.fillRect(col("black"), dx - 1, dy - 3, 1, 1)
            s.fillRect(col("black"), dx + 1, dy - 3, 1, 1)
            s.fillRect(col(rainbow(Int(t * 8), 0)), dx - 5, dy + 1, 1, 1)
            s.fillRect(col(rainbow(Int(t * 8) + 3, 0)), dx + 5, dy + 1, 1, 1)
        }
    }

    func drawTele(_ s: Surface, _ t: Double) {
        guard let tl = tele else { return }
        let blink = Int(t * 12) % 2 != 0
        let x0 = Int(tl.x)
        switch tl.a {
        case "bolt", "beam":
            if blink {
                let y1 = tl.a == "bolt" ? 200 : g.sy(h) + 6
                var y = 0
                while y < y1 { s.fillRect(col(tl.a == "bolt" ? "yellow" : "red"), x0, y, 1, 3); y += 6 }
            }
        case "geyser":
            let y = g.sy(tl.h)
            for i in 0 ..< 4 {
                let by = y - 2 - Int(cpFmod(t * 40 + Double(i * 9), 30))
                s.circle(col("sky"), x0 - 6 + i * 4, by, 2, width: 1)
            }
        case "dive":
            if blink {
                for i in 0 ..< 3 {
                    s.polygon(col("red"), [(Double(x0 - 6), Double(8 + i * 8)), (Double(x0 + 6), Double(8 + i * 8)), (Double(x0), Double(14 + i * 8))])
                }
            }
        case "swoop":
            if blink {
                let y = g.sy(tl.h)
                var xx = 0
                while xx < CP.FW { s.fillRect(col("red"), xx, y, 4, 1); xx += 8 }
            }
        case "starfall":
            let n = 4 + (phase == 2 ? 1 : 0)
            for i in 0 ..< n where blink {
                let xx = Int(cpFmod(tl.x + Double((i - n / 2) * 40), CP.FWd))
                s.blit(sprite("star"), xx - 3, 2)
            }
        case "gust":
            for i in 0 ..< 4 {
                s.fillRect(col(blink ? "white" : "sky"), Int(cpFmod(t * 120 + Double(i * 50), CP.FWd)), 40 + i * 36, 10, 1)
            }
        default:
            // the boss winds up: a glowing ring around its body
            let r = 4 + Int((1 - tl.left / tl.full) * 8)
            s.circle(col(blink ? "yellow" : "white"), Int(x), g.sy(h), r + 14, width: 1)
        }
    }

    func drawCol(_ s: Surface, _ c: (kind: String, x: Double, hw: Double, lo: Double, hi: Double, left: Double), _ t: Double) {
        let x0 = Int(c.x)
        let y0 = max(0, g.sy(c.hi)), y1 = min(200, g.sy(c.lo))
        let hw = Int(c.hw)
        if c.kind == "bolt" {
            var xx = x0
            var y = y0
            while y < y1 {
                let nx = x0 + ((y / 10 + Int(t * 30)) % 2 != 0 ? 3 : -3)
                s.line(col("yellow"), xx, y, nx, y + 10, width: 3)
                s.line(col("white"), xx, y, nx, y + 10)
                xx = nx
                y += 10
            }
        } else if c.kind == "geyser" {
            var y = y0
            while y < y1 {
                let w = hw + Int(sin(t * 20 + Double(y) * 0.3) * 2)
                s.fillRect(col("sky"), x0 - w, y, w * 2, 2)
                s.fillRect(col("white"), x0 - 2 + Int(sin(Double(y) * 0.5 + t * 9) * 2), y, 2, 1)
                y += 2
            }
        } else {
            let w = hw - Int(t * 30) % 2
            s.fillRect(col("hotpink"), x0 - w, y0, w * 2, y1 - y0)
            s.fillRect(col("white"), x0 - 1, y0, 2, y1 - y0)
        }
    }

    func drawBody(_ s: Surface, _ x: Int, _ y: Int, _ t: Double) {
        let hitF = flash > 0 && Int(t * 30) % 2 != 0
        let angry = phase == 2
        let look = cpWrapd(g.x - self.x) > 0 ? 1 : -1
        func P(_ a: Int, _ b: Int) -> (Double, Double) { (Double(a), Double(b)) }
        switch kind {
        case "owl":
            for i in 0 ..< 4 { s.circle(col("darkgray"), x - 15 + i * 10, y + 13, 6) }      // storm cloud perch
            let body = hitF ? "white" : (angry ? "purple" : "lavender")
            let flap = Int(sin(t * 8) * 3)
            for side in [-1, 1] {
                s.ellipse(col("black"), x + side * 13 - 6, y - 6 + flap * side, 12, 16)
                s.ellipse(col("gray"), x + side * 13 - 5, y - 5 + flap * side, 10, 14)
            }
            s.circle(col("black"), x, y, 16)
            s.circle(col(body), x, y, 15)
            s.polygon(col(body), [P(x - 13, y - 8), P(x - 9, y - 20), P(x - 4, y - 12)])
            s.polygon(col(body), [P(x + 13, y - 8), P(x + 9, y - 20), P(x + 4, y - 12)])
            s.ellipse(col("cream"), x - 9, y + 1, 18, 12)
            for i in 0 ..< 3 { s.fillRect(col("peach"), x - 5 + i * 4, y + 5 + (i % 2) * 2, 2, 1) }
            for side in [-1, 1] {
                s.circle(col("white"), x + side * 6, y - 5, 5)
                s.circle(col("black"), x + side * 6 + look * 2, y - 5, 2)
                if angry { s.line(col("black"), x + side * 2, y - 10, x + side * 10, y - 12) }
            }
            s.polygon(col("orange"), [P(x - 2, y - 2), P(x + 2, y - 2), P(x, y + 2)])
            if angry && Int(t * 8) % 2 != 0 {
                let c = col("yellow")
                s.line(c, x + 18, y - 14, x + 21, y - 9); s.line(c, x + 21, y - 9, x + 18, y - 7); s.line(c, x + 18, y - 7, x + 22, y - 2)
            }
        case "whale":
            let d = Int(dir)
            let body = hitF ? "white" : (angry ? "pink" : "white")
            for i in 0 ..< 5 { s.circle(col("sky"), x - 20 + i * 10, y - 7, 6) }
            s.ellipse(col("sky"), x - 29, y - 11, 58, 24)
            s.ellipse(col(body), x - 27, y - 9, 54, 20)
            for i in 0 ..< 5 { s.circle(col(body), x - 20 + i * 10, y - 7, 5) }
            s.ellipse(col("cream"), x - 18, y + 2, 36, 7)
            let tx0 = x - d * 30
            let flip = Int(sin(t * 5) * 3)
            s.polygon(col("sky"), [P(tx0, y), P(tx0 - d * 10, y - 8 + flip), P(tx0 - d * 10, y + 6 + flip)])
            let ex = x + d * 15
            s.fillRect(col("black"), ex, y - 3, 2, angry ? 2 : 3)
            s.fillRect(col("pink"), ex - d * 2, y + 2, 3, 1)
            s.line(col("black"), x + d * 18, y + 4, x + d * 23, y + 3)
            s.fillRect(col("sky"), x + d * 4, y - 14, 3, 2)
        case "kite":
            let segs = segments()
            for i in stride(from: segs.count - 1, through: 0, by: -1) {
                let (sx, sh) = segs[i]
                let sy = g.sy(sh)
                for xd in [0, -CP.FW, CP.FW] {
                    let xx = Int(sx) + xd
                    let r = 5 - i / 2
                    s.polygon(col("black"), [P(xx, sy - r - 1), P(xx + r + 1, sy), P(xx, sy + r + 1), P(xx - r - 1, sy)])
                    s.polygon(col(rainbow(i, 0)), [P(xx, sy - r), P(xx + r, sy), P(xx, sy + r), P(xx - r, sy)])
                }
            }
            let body = hitF ? "white" : (angry ? "hotpink" : "red")
            s.polygon(col("black"), [P(x, y - 12), P(x + 12, y), P(x, y + 12), P(x - 12, y)])
            s.polygon(col(body), [P(x, y - 11), P(x + 11, y), P(x, y + 11), P(x - 11, y)])
            s.polygon(col("yellow"), [P(x, y - 11), P(x + 11, y), P(x, y)])
            for side in [-1, 1] {
                s.line(col("yellow"), x + side * 4, y - 9, x + side * 8, y - 15)
                s.line(col("white"), x + side * 6, y + 3, x + side * 16, y + 6 + Int(sin(t * 6) * 2))
            }
            Cute.eyes(s, x, y - 2, 4, look: look, mood: angry ? "angry" : "happy")
            Cute.mouth(s, x, y + 3, angry ? "angry" : "happy")
        case "ufo":
            s.circle(col("black"), x, y - 3, 11)
            s.circle(col(hitF ? "white" : "sky"), x, y - 3, 10)
            for i in 0 ..< 3 {       // the laser-pointer aliens inside
                let ax = x - 6 + i * 6
                let ay = y - 4 + ((i + Int(t * 4)) % 2 != 0 ? 1 : 0)
                s.circle(col("lime"), ax, ay, 2)
                s.fillRect(col("black"), ax, ay - 1, 1, 1)
                s.fillRect(col("lime"), ax, ay - 4, 1, 2)
                s.fillRect(col("red"), ax + 1, ay + 1, 2, 1)
            }
            s.fillRect(col("white"), x - 6, y - 10, 3, 2)
            s.ellipse(col("black"), x - 24, y - 2, 48, 13)
            s.ellipse(col(angry ? "purple" : "gray"), x - 23, y - 1, 46, 11)
            s.ellipse(col("lavender"), x - 20, y - 1, 40, 4)
            for i in 0 ..< 6 { s.fillRect(col(rainbow(i + Int(t * 10), 0)), x - 17 + i * 7, y + 5, 2, 2) }
        default:
            for a in shieldAngles() {
                s.blit(sprite("star"), x + Int(cos(a) * 24) - 3, y - Int(sin(a) * 24) - 3)
            }
            let body = hitF ? "white" : (angry ? "purple" : "night")
            s.circle(col("lavender"), x, y, 17)
            s.circle(col(body), x, y, 15)
            s.circle(col("ink"), x + 5, y - 4, 12)
            for side in [-1, 1] {
                let ex = x + side * 6
                s.circle(col("yellow"), ex, y - 2, 3)
                s.circle(col("ink"), ex + 1, y - 3, 3)
            }
            s.line(col("yellow"), x - 3, y + 7, x + 3, y + 7)
            for i in 0 ..< 3 { s.fillRect(col("white"), x - 10 + (i * 9 + Int(t * 6)) % 20, y + 10 - i * 3, 1, 1) }
        }
    }
}

func cpDrawProj(_ s: Surface, _ p: CPProj, _ x: Int, _ y: Int, _ t: Double) {
    switch p.kind {
    case "feather":
        s.line(col("white"), x - 3, y - 1, x + 3, y + 1, width: 2)
        s.fillRect(col("gray"), x - 3, y - 1, 2, 1)
    case "drop":
        s.circle(col("blue"), x, y, 3)
        s.circle(col("sky"), x, y, 2)
        s.fillRect(col("white"), x - 1, y - 1, 1, 1)
    case "lantern":
        s.rect(col("black"), IRect(x - 4, y - 5, 9, 11), radius: 3)
        s.rect(col("red"), IRect(x - 3, y - 4, 7, 9), radius: 3)
        s.fillRect(col("yellow"), x - 1, y - 2, 3, 5)
        s.fillRect(col("black"), x - 2, y - 6, 5, 1)
    case "confetti":
        s.fillRect(col(rainbow(Int(p.age * 10 + p.ox), 0)), x - 1, y - 1, 3, 3)
    case "crescent":
        for i in 0 ..< 7 {
            let a = -1.2 + Double(i) * 0.4 + t * 8
            s.fillRect(col("yellow"), x + Int(cos(a) * 4), y + Int(sin(a) * 4), 2, 2)
        }
    default:
        s.blit(sprite("star"), x - 3, y - 3)
        if Int(t * 12) % 2 != 0 { s.fillRect(col("white"), x, y - 5, 1, 2) }
    }
}
