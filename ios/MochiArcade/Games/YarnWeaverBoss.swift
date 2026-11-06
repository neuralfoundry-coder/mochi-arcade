// YARN WEAVER bosses (port of games/yarn_weaver_boss.py): five troublemakers that roam the open rug.
// You can't hit a boss - you take its rug away: claims hurt it (claims close to it hurt double), wrapping its
// minions hurts it, and a boss squeezed into a tiny pocket is cornered at once.
import Foundation

private let PATTERN = ["cloud": "bolts", "mouse": "pellets", "vacuum": "dash", "snoot": "bark", "moth": "dive"]
private let RADIUS = ["cloud": 15, "mouse": 12, "vacuum": 13, "snoot": 14, "moth": 13]

/// Round things that bounce around the open rug (fluffs, pom-poms, bosses).
protocol YWBouncer: AnyObject {
    var x: Double { get set }
    var y: Double { get set }
    var vx: Double { get set }
    var vy: Double { get set }
    var r: Int { get }
    var stuck: Int { get set }
}

func ywLines(_ s: Surface, _ c: String, _ pts: [(Int, Int)], closed: Bool = false, width: Int = 1) {
    for i in 0 ..< pts.count - 1 { s.line(col(c), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: width) }
    if closed, let a = pts.last, let b = pts.first { s.line(col(c), a.0, a.1, b.0, b.1, width: width) }
}

final class YWBoss: YWBouncer {
    unowned let g: YarnWeaver
    let kind, name: String
    let tier: Int
    let maxhp: Int
    var hp: Int
    let rate, speed: Double
    let minions: Int
    let patterns: [String]
    var pi = 0
    let r: Int
    var x = 152.0, y = 60.0, vx = 0.0, vy = 0.0
    var state = "intro"
    var t = 0.0, flash = 0.0, cd = 2.0
    var phase = 0
    struct Tele { var pat: String; var age, dur, tx, ty: Double }
    var tele: [Tele] = []
    var shots: [(x: Double, y: Double, vx: Double, vy: Double)] = []      // pellets
    var rings: [(x: Double, y: Double, r: Double, delay: Double, reach: Double)] = []   // bark waves
    var bolts: [(x: Double, life: Double)] = []                          // lightning
    var dashT = 0.0, mood = 0.0, deadT = 0.0
    var stuck = 0

    init(_ g: YarnWeaver, _ spec: YWBossSpec) {
        self.g = g
        kind = spec.kind; name = spec.name; tier = spec.tier
        maxhp = max(600, Int(Double(g.claimable) * spec.hp))
        hp = maxhp
        rate = spec.rate
        speed = spec.speed * g.hzSpeed
        minions = spec.minions
        patterns = [PATTERN[spec.kind] ?? "bolts"] + spec.extra
        r = (RADIUS[spec.kind] ?? 14) + (spec.name == "GRAND FUZZ" ? 3 : 0)
        let a = Double.random(in: 0.5 ... 2.6)
        vx = cos(a) * speed; vy = sin(a) * speed
    }

    // ---------------------------------------------------------------- update
    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        mood = max(0, mood - dt)
        if state == "dead" { deadT += dt; return }
        if state != "fight" { return }
        let frac = Double(hp) / Double(maxhp)
        let ph = frac > 0.66 ? 0 : (frac > 0.33 ? 1 : 2)
        if ph > phase {
            phase = ph
            g.hype.banner("RAGE UP!", name, color: "red", dur: 1.0, scale: 1, sound: "warning")
            for _ in 0 ..< minions { g.spawnMinion(kind, x, y) }
        }
        if g.freeze <= 0 {
            let mult = dashT > 0 ? 3.2 : (tele.isEmpty ? 1.0 : 0.4)
            dashT = max(0, dashT - dt)
            let sp = max(1e-9, (vx * vx + vy * vy).squareRoot())
            let want = speed * (1 + 0.15 * Double(phase)) * mult
            vx = vx / sp * want; vy = vy / sp * want
            g.moveBall(self, dt)
            _ = g.touchCheck(x, y, r, "boss")
            cd -= dt
            if cd <= 0 && tele.isEmpty && dashT <= 0 {
                cd = rate * (1 - 0.18 * Double(phase)) * Double.random(in: 0.8 ... 1.15)
                begin(patterns[pi % patterns.count])
                pi += 1
            }
        }
        for i in tele.indices {
            tele[i].age += dt
            if tele[i].age >= tele[i].dur { fire(tele[i]) }
        }
        tele.removeAll { $0.age >= $0.dur }
        updateShots(dt)
    }

    func begin(_ pat: String) {
        let (kx, ky) = g.kumoPx()
        if pat == "bolts" {
            let n = 2 + phase + tier / 6
            var xs: [Double] = g.weaving ? [kx + ([-1.0, 1.0].randomElement()!) * Double.random(in: 14 ... 30)] : []
            while xs.count < n { xs.append(Double.random(in: 8 ... 296)) }
            for x in xs { tele.append(Tele(pat: "bolts", age: 0, dur: 0.85, tx: max(4, min(300, x)), ty: 0)) }
            g.app.audio.play(phase >= 2 ? "warning" : "trap")
        } else if pat == "pellets" || pat == "dash" || pat == "dive" {
            var tx = kx, ty = ky
            if pat == "dive" && !g.trail.isEmpty {
                let c = g.trail[g.trail.count / 2]
                tx = Double((c % YW_GW) * 2 + 1); ty = Double((c / YW_GW) * 2 + 1)
            }
            tele.append(Tele(pat: pat, age: 0, dur: ["pellets": 0.55, "dash": 0.75, "dive": 0.65][pat] ?? 0.6, tx: tx, ty: ty))
        } else if pat == "bark" {
            tele.append(Tele(pat: "bark", age: 0, dur: 0.7, tx: x, ty: y))
            g.app.audio.play("trap")
        }
        mood = 1.0
    }

    func fire(_ tl: Tele) {
        switch tl.pat {
        case "bolts":
            bolts.append((x: tl.tx, life: 0.3))
            g.app.audio.play("explode")
            g.app.shake(2, 0.15)
            g.strikeColumn(tl.tx)
        case "pellets":
            let base = atan2(tl.ty - y, tl.tx - x)
            let n = 1 + 2 * phase
            for k in 0 ..< n {
                let a = base + (Double(k) - Double(n - 1) / 2) * 14 * .pi / 180
                let sp = Double(85 + 4 * tier)
                shots.append((x: x, y: y, vx: cos(a) * sp, vy: sin(a) * sp))
            }
            g.app.audio.play("shoot")
        case "dash", "dive":
            let a = atan2(tl.ty - y, tl.tx - x)
            vx = cos(a); vy = sin(a)
            dashT = tl.pat == "dash" ? 0.9 : 0.75
            g.app.audio.play("jump")
            if tl.pat == "dive" && phase >= 1 { g.spawnMinion("moth", x, y) }
            if tl.pat == "dash" && phase >= 1 { g.spawnMinion("vacuum", x, y) }
        case "bark":
            let reach = 70.0 + 14 * Double(phase)
            rings.append((x: x, y: y, r: Double(r), delay: 0, reach: reach))
            if phase >= 2 { rings.append((x: x, y: y, r: Double(r), delay: 0.45, reach: reach)) }
            g.app.audio.play("boom")
            g.app.shake(2, 0.2)
            g.floats.add(Double(YW_FX) + x, Double(YW_FY) + y - 20, "WOOF!", "white")
        default: break
        }
    }

    func updateShots(_ dt: Double) {
        for i in bolts.indices { bolts[i].life -= dt }
        bolts.removeAll { $0.life <= 0 }
        for i in shots.indices {
            for _ in 0 ..< 2 {
                shots[i].x += shots[i].vx * dt / 2
                shots[i].y += shots[i].vy * dt / 2
                let px = shots[i].x, py = shots[i].y
                if g.trailHit(px, py, 2) { g.hazardHit("pellet", px, py); shots[i].y = -99; break }
                if g.blocked(px, py) { shots[i].y = -99; break }
                if g.kumoHit(px, py, 3) { g.hazardHit("pellet", px, py); shots[i].y = -99; break }
            }
        }
        shots.removeAll { $0.y <= -50 }
        for i in rings.indices {
            if rings[i].delay > 0 { rings[i].delay -= dt; continue }
            rings[i].r += 105 * dt
            g.ringCheck(rings[i].x, rings[i].y, rings[i].r)
        }
        rings.removeAll { $0.r >= $0.reach }
    }

    func damage(_ n: Int, _ near: Bool) -> Int {
        if state != "fight" { return 0 }
        let dmg = n * (near ? 2 : 1)
        hp = max(0, hp - dmg)
        flash = 0.25
        return dmg
    }

    // ---------------------------------------------------------------- drawing
    func draw(_ s: Surface, _ ox: Int, _ oy: Int, _ t: Double) {
        let bx = ox + Int(x), by = oy + Int(y)
        for tl in tele { drawTele(s, ox, oy, tl, t) }
        if state == "dead" { return }
        let hit = flash > 0 && Int(t * 20) % 2 == 1
        if name == "GRAND FUZZ" {
            ywDrawCloud(s, bx, by, r, t, hit, mood > 0, crown: true)
        } else {
            switch kind {
            case "cloud": ywDrawCloud(s, bx, by, r, t, hit, mood > 0)
            case "mouse": ywDrawRoboMouse(s, bx, by, t, hit, mood > 0, vx)
            case "vacuum": ywDrawVacuum(s, bx, by, t, hit, dashT > 0 || mood > 0)
            case "snoot": ywDrawSnoot(s, bx, by, t, hit, mood > 0)
            default: ywDrawDustwing(s, bx, by, t, hit, mood > 0)
            }
        }
        if g.freeze > 0 { drawText(s, "Z", bx + r, by - r - 6, "sky") }
        for b in bolts {
            let lx = ox + Int(b.x)
            let pts = (0 ..< 17).map { j in (lx + (j % 2 == 1 ? 3 : -3), oy + j * 11) }
            for i in 0 ..< pts.count - 1 {
                s.line(col("yellow"), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: 3)
                s.line(col("white"), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1)
            }
        }
        for p in shots {
            let px = ox + Int(p.x), py = oy + Int(p.y)
            s.circle(col("black"), px, py, 4)
            s.circle(col("yellow"), px, py, 3)
            s.fillRect(col("orange"), px, py, 1, 1)
        }
        for rg in rings where rg.delay <= 0 {
            s.circle(col(Int(t * 12) % 2 == 1 ? "white" : "yellow"), ox + Int(rg.x), oy + Int(rg.y), Int(rg.r), width: 2)
        }
    }

    func drawTele(_ s: Surface, _ ox: Int, _ oy: Int, _ tl: Tele, _ t: Double) {
        let blink = Int(t * 12) % 2 == 1
        if tl.pat == "bolts" {
            let bx = ox + Int(tl.tx)
            let off = Int(tl.age * 40) % 6
            for yy in stride(from: oy + off, to: oy + 176, by: 6) { s.fillRect(col(blink ? "yellow" : "orange"), bx - 1, yy, 3, 3) }
            drawText(s, "!", bx - 2, oy + 2, blink ? "yellow" : "red")
        } else if tl.pat == "pellets" || tl.pat == "dash" || tl.pat == "dive" {
            let c = ["pellets": "red", "dash": "orange", "dive": "lavender"][tl.pat] ?? "red"
            let x0 = Double(ox) + x, y0 = Double(oy) + y
            let a = atan2(tl.ty - y, tl.tx - x)
            let n = tl.pat == "pellets" ? 6 : 9
            for i in 1 ..< n {
                let d = Double(i * 8) + (tl.age * 30).truncatingRemainder(dividingBy: 8)
                if blink || tl.pat != "pellets" {
                    s.fillRect(col(c), Int(x0 + cos(a) * d) - 1, Int(y0 + sin(a) * d) - 1, 2, 2)
                }
            }
        } else if tl.pat == "bark" {
            let rr = Int(Double(r) + 4 + (1 - tl.age / tl.dur) * 10)
            if blink {
                s.circle(col("white"), ox + Int(x), oy + Int(y), rr, width: 1)
                s.circle(col("red"), ox + Int(x), oy + Int(y), 70 + 14 * phase, width: 1)
            }
        }
    }
}

// ----------------------------------------------------------------------------- boss art (cute, original)
func ywDrawCloud(_ s: Surface, _ x: Int, _ y: Int, _ r: Int, _ t: Double, _ hit: Bool, _ angry: Bool, crown: Bool = false) {
    let k = Double(r) / 15
    let puffs: [(Double, Double, Double)] = [(-10, 3, 9), (10, 3, 9), (0, -5, 11), (-5, 7, 8), (6, 7, 8)]
    let bob = Int(sin(t * 3) * 2)
    for (dx, dy, rr) in puffs { s.circle(col("black"), x + Int(dx * k), y + Int(dy * k) + bob, Int(rr * k) + 2) }
    for (dx, dy, rr) in puffs { s.circle(col("gray"), x + Int(dx * k), y + Int(dy * k) + bob + 2, Int(rr * k)) }
    for (dx, dy, rr) in puffs { s.circle(col(hit ? "white" : "lavender"), x + Int(dx * k), y + Int(dy * k) + bob, Int(rr * k) - 1) }
    s.fillRect(col("white"), x - Int(6 * k), y - Int(10 * k) + bob, 4, 2)
    Cute.eyes(s, x, y + bob, 5, look: 0, mood: angry ? "angry" : "happy", blink: Int(t * 2) % 6 == 0, size: 2)
    Cute.mouth(s, x, y + 6 + bob, angry ? "angry" : "happy")
    s.ellipse(col("pink"), x - 12, y + 4 + bob, 4, 2)
    s.ellipse(col("pink"), x + 9, y + 4 + bob, 4, 2)
    if Int(t * 5) % 2 == 1 {
        for dx in [-8, 6] {
            let bx = x + dx, by = y + Int(14 * k) + bob
            ywLines(s, "yellow", [(bx, by), (bx + 3, by + 3), (bx, by + 5), (bx + 3, by + 9)], width: 2)
        }
    }
    if crown {
        let pts = [(x - 9, y - 15 + bob), (x - 9, y - 22 + bob), (x - 4, y - 18 + bob), (x, y - 24 + bob),
                   (x + 4, y - 18 + bob), (x + 9, y - 22 + bob), (x + 9, y - 15 + bob)]
        s.polygon(col("yellow"), pts.map { (Double($0.0), Double($0.1)) })
        ywLines(s, "black", pts, closed: true)
        s.fillRect(col("red"), x - 1, y - 19 + bob, 2, 2)
    }
}

func ywDrawRoboMouse(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ aiming: Bool, _ vx: Double) {
    let body = hit ? "white" : "gray"
    for d in [-1, 1] {
        s.circle(col("black"), x + d * 9, y - 9, 7)
        s.circle(col(body), x + d * 9, y - 9, 6)
        s.circle(col("pink"), x + d * 9, y - 9, 3)
    }
    s.ellipse(col("black"), x - 14, y - 9, 28, 20)
    s.ellipse(col(body), x - 13, y - 8, 26, 18)
    s.fillRect(col("white"), x - 8, y - 6, 6, 2)
    for i in 0 ..< 3 { s.fillRect(col("darkgray"), x - 8 + i * 8, y + 5, 2, 2) }
    let ec = aiming && Int(t * 10) % 2 == 1 ? "red" : "sky"
    for d in [-1, 1] {
        s.circle(col("black"), x + d * 5, y - 1, 3)
        s.circle(col(ec), x + d * 5, y - 1, 2)
    }
    s.circle(col("hotpink"), x, y + 3, 2)
    for d in [-1, 1] {
        for k in [0, 3] { s.line(col("black"), x + d * 4, y + 3 + k, x + d * 13, y + 1 + k * 2) }
    }
    let a = t * 6
    let kx = x, ky = y - 12
    s.line(col("yellow"), kx, ky + 3, kx, ky - 3, width: 2)
    s.circle(col("yellow"), kx + Int(cos(a) * 4), ky - 4, 2)
    s.circle(col("yellow"), kx - Int(cos(a) * 4), ky - 4, 2)
    let tl = vx > 0 ? -1 : 1
    ywLines(s, "pink", [(x + tl * 13, y + 4), (x + tl * 18, y + 1 + Int(sin(t * 8) * 2)), (x + tl * 22, y + 4)])
    for d in [-1, 1] {
        s.circle(col("black"), x + d * 7, y + 11, 3)
        s.fillRect(col("gray"), x + d * 7 + (Int(t * 12) % 2 == 1 ? 1 : -1), y + 11, 1, 1)
    }
}

func ywDrawVacuum(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ mad: Bool) {
    s.circle(col("black"), x, y, 15)
    s.circle(col(hit ? "white" : "darkgray"), x, y, 14)
    s.circle(col("gray"), x, y, 11)
    s.circle(col("darkgray"), x, y, 11, width: 1)
    s.rect(col("ink"), IRect(x - 8, y - 6, 16, 8), radius: 3)
    if mad {
        for d in [-1, 1] { s.line(col("red"), x + d * 6, y - 4, x + d * 2, y - 2, width: 2) }
    } else {
        for d in [-1, 1] { s.fillRect(col("mint"), x + d * 4 - 1, y - 4, 3, 3) }
    }
    s.fillRect(col("black"), x - 6, y + 6, 12, 3)
    s.fillRect(col(mad ? "red" : "white"), x - 4, y + 7, 8, 1)
    for d in [-1, 1] {
        let a = t * (mad ? 20 : 8) * Double(d)
        let bx = x + d * 12, by = y + 10
        for k in 0 ..< 3 {
            let aa = a + Double(k) * 2.1
            s.line(col("yellow"), bx, by, bx + Int(cos(aa) * 5), by + Int(sin(aa) * 5))
        }
    }
    if Int(t * 4) % 2 == 1 { s.fillRect(col("lime"), x + 9, y - 9, 2, 2) }
}

func ywDrawSnoot(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ barking: Bool) {
    let bob = Int(sin(t * 4))
    for d in [-1, 1] {
        s.ellipse(col("black"), x + d * 14 - 6, y - 8 + bob, 12, 20)
        s.ellipse(col("choco"), x + d * 14 - 5, y - 7 + bob, 10, 18)
    }
    s.ellipse(col("black"), x - 17, y - 12 + bob, 34, 26)
    s.ellipse(col(hit ? "white" : "brown"), x - 16, y - 11 + bob, 32, 24)
    s.ellipse(col("peach"), x - 9, y - 1 + bob, 18, 13)
    for d in [-1, 1] {
        s.circle(col("black"), x + d * 7, y - 5 + bob, 3)
        s.fillRect(col("white"), x + d * 7 - 1, y - 7 + bob, 1, 1)
    }
    s.ellipse(col("black"), x - 6, y - 1 + bob, 12, 8)
    s.fillRect(col("white"), x - 3, y + bob, 3, 2)
    if barking {
        s.ellipse(col("black"), x - 5, y + 7 + bob, 10, 7)
        s.ellipse(col("red"), x - 3, y + 9 + bob, 6, 4)
    } else {
        Cute.mouth(s, x, y + 8 + bob, "happy")
    }
}

func ywDrawDustwing(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ mad: Bool) {
    let flap = sin(t * 14)
    let wh = 11 + Int(flap * 4)
    let wing = hit ? "white" : "lavender"
    for d in [-1, 1] {
        s.ellipse(col("black"), x + (d > 0 ? 2 : -19), y - wh, 17, wh + 2)
        s.ellipse(col(wing), x + (d > 0 ? 3 : -18), y - wh + 1, 15, wh)
        s.circle(col("purple"), x + d * 10, y - ywDiv(wh, 2), 3)
        s.circle(col("yellow"), x + d * 10, y - ywDiv(wh, 2), 1)
        s.ellipse(col("black"), x + (d > 0 ? 1 : -12), y - 1, 11, 10)
        s.ellipse(col("cream"), x + (d > 0 ? 2 : -11), y, 9, 8)
    }
    s.ellipse(col("black"), x - 5, y - 9, 10, 22)
    s.ellipse(col("peach"), x - 4, y - 8, 8, 20)
    for i in 0 ..< 3 { s.fillRect(col("brown"), x - 3, y - 2 + i * 4, 6, 1) }
    s.circle(col("black"), x, y - 10, 5)
    s.circle(col("cream"), x, y - 10, 4)
    Cute.eyes(s, x, y - 10, 2, look: 0, mood: mad ? "angry" : "happy")
    for d in [-1, 1] {
        s.line(col("black"), x + d * 2, y - 14, x + d * 6, y - 20)
        s.fillRect(col("yellow"), x + d * 6 - 1, y - 21, 2, 2)
    }
    s.fillRect(col("yellow"), x - 2, y - 15, 5, 1)
}
