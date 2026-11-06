// BOUNCE BUN bosses (port of games/bounce_bun_boss.py): CAKE CASTLE, JELLY DONUT, COOKIE JAR, GINGER-BOT,
// CANDY WHALE - telegraphed attacks, phases at 66% / 33% health, borrowed attacks on later tiers.
import Foundation

private let LEFT = 8.0, RIGHT = Double(W - 8), TOP = 20.0
private let PADDLE_Y = 182
private let STYLE = ["cake": "flame", "donut": "jam", "jar": "crumb", "robot": "gear", "whale": "candy"]

final class BBBody {
    var x, y: Double
    let w, h: Int
    var vx = 0.0, vy = 0.0
    var hp: Int
    let size: Int
    var flash = 0.0, shake = 0.0
    var alive = true
    init(_ x: Double, _ y: Double, _ w: Int, _ h: Int, _ hp: Int, _ size: Int = 0) {
        self.x = x; self.y = y; self.w = w; self.h = h; self.hp = hp; self.size = size
    }
    func rect() -> IRect { IRect(Int(x - Double(w) / 2), Int(y - Double(h) / 2), w, h) }
}

final class BBPart {
    let kind: String
    let dx, dy: Double
    let w, h: Int
    var hp: Int
    let maxhp: Int
    var x = 0.0, y = 0.0
    var alive = true
    var flash = 0.0, regrow = 0.0, glow = 0.0
    init(_ kind: String, _ dx: Double, _ dy: Double, _ w: Int, _ h: Int, _ hp: Int) {
        self.kind = kind; self.dx = dx; self.dy = dy; self.w = w; self.h = h; self.hp = hp; maxhp = hp
    }
    func rect() -> IRect { IRect(Int(x - Double(w) / 2), Int(y - Double(h) / 2), w, h) }
}

final class BBTele {
    let kind: String
    let x, y: Double
    var t: Double
    let xs: [Double]
    init(_ kind: String, _ x: Double, _ y: Double, _ t: Double, _ xs: [Double] = []) {
        self.kind = kind; self.x = x; self.y = y; self.t = t; self.xs = xs
    }
}

final class BBProj {
    var x, y, vx, vy: Double
    let style: String
    let g: Double
    var alive = true
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ style: String, _ g: Double = 0) {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.style = style; self.g = g
    }
}

enum BBTarget { case body(BBBody), part(BBPart) }

final class BBBoss {
    unowned let g: BounceBun
    let kind, name, style: String
    let tier, maxhp: Int
    let rate, spd: Double
    let extra: [String]
    var t = 0.0
    var phase = 1
    var atk = 2.0
    var nAtk = 0
    var state = "enter"
    var dieT = 0.0, boomT = 0.0
    var teles: [BBTele] = []
    var projs: [BBProj] = []
    var parts: [BBPart] = []
    var beams: [(x: Double, t: Double)] = []
    var open = false                // cookie jar lid
    var openT = 3.0
    var lidHits = 0
    var dir = 1.0                   // whale heading
    var dive = 0                    // whale: 0 swimming, 1 diving up, 2 hidden, 3 coming back
    var diveT = 8.0
    var targetY = 60.0
    var bodies: [BBBody] = []

    init(_ g: BounceBun, _ spec: BBBossSpec) {
        self.g = g
        kind = spec.kind; name = spec.name; tier = spec.tier; maxhp = spec.hp
        rate = spec.rate; spd = spec.speed; extra = spec.extra
        style = STYLE[spec.kind] ?? "candy"
        let cx = Double(W) / 2
        switch kind {
        case "cake":
            bodies = [BBBody(cx, -40, 96, 40, maxhp)]
            targetY = 62
            let spots: [(Double, Double)] = [(0, -34), (-28, -24), (28, -24), (-41, -12), (41, -12)]
            for (dx, dy) in spots.prefix(3 + (tier >= 6 ? 1 : 0) + (tier >= 11 ? 1 : 0)) {
                parts.append(BBPart("candle", dx, dy, 6, 9, 2 + tier / 5))
            }
        case "donut":
            let b = BBBody(cx, -40, 44, 36, maxhp)
            b.vx = 55 * spd; b.vy = 30 * spd
            bodies = [b]
            targetY = 58
        case "jar":
            bodies = [BBBody(cx, -40, 52, 54, maxhp)]
            targetY = 62
        case "robot":
            bodies = [BBBody(cx, -40, 40, 44, maxhp)]
            targetY = 52
            for side in [-1.0, 1.0] { parts.append(BBPart("arm", side, 0, 30, 8, 4 + tier / 3)) }
        default:
            bodies = [BBBody(cx, -40, 76, 30, maxhp)]
            targetY = 52
        }
    }

    // ------------------------------------------------------------------ state
    var hp: Int { bodies.filter { $0.alive }.reduce(0) { $0 + max(0, $1.hp) } }

    func vulnerable(_ b: BBBody) -> Bool {
        if state != "fight" { return false }
        if kind == "jar" { return open }
        if kind == "whale" { return dive == 0 }
        return true
    }

    /// The rects the gumball and the lasers bounce off.
    func colliders() -> [(IRect, BBTarget)] {
        var out: [(IRect, BBTarget)] = []
        if state != "fight" && state != "enter" { return out }
        for b in bodies where b.alive && b.y + Double(b.h) / 2 >= TOP {
            if kind == "cake" {
                let cx = Int(b.x), cy = Int(b.y)
                out.append((IRect(cx - 48, cy + 2, 96, 18), .body(b)))
                out.append((IRect(cx - 34, cy - 10, 68, 12), .body(b)))
                out.append((IRect(cx - 22, cy - 20, 44, 10), .body(b)))
            } else {
                out.append((b.rect(), .body(b)))
            }
        }
        for p in parts where p.alive { out.append((p.rect(), .part(p))) }
        return out
    }

    // ------------------------------------------------------------------ damage
    /// The gumball or a laser hit a body or part. Returns true when it did damage.
    @discardableResult
    func hit(_ target: BBTarget, _ dmg: Int) -> Bool {
        switch target {
        case .part(let p):
            if !p.alive || state != "fight" { return false }
            p.hp -= dmg
            p.flash = 0.12
            if p.hp <= 0 {
                p.alive = false
                p.regrow = 10
                g.parts.burst(p.x, p.y, 14, ["yellow", "orange", "white"], 70, 0.6)
                g.app.audio.play("explode")
                g.scoreAt(500, p.x, p.y)
                damage(bodies[0].alive ? bodies[0] : nil, max(1, Int(Double(maxhp) * (kind == "cake" ? 0.04 : 0.06))))
            } else {
                g.app.audio.play("brick")
            }
            return true
        case .body(let b):
            if !vulnerable(b) {
                b.flash = 0.05
                g.app.audio.play("tin")
                if kind == "jar" && state == "fight" && !open {
                    lidHits += 1
                    b.shake = 0.25
                    if lidHits >= 2 { openLid() }       // knock the lid off early
                }
                return false
            }
            damage(b, dmg)
            return true
        }
    }

    func damage(_ body: BBBody?, _ dmg: Int) {
        guard let b = body, b.alive else { return }
        b.hp -= dmg
        b.flash = 0.1
        g.hype.hitstop(0.035)
        g.app.audio.play("brick")
        g.parts.burst(b.x, b.y + Double(b.h) / 2, 5, ["white", "pink", "yellow"], 50, 0.4)
        g.scoreAt(30 * dmg)
        if kind == "donut" { split(b) }
        if b.hp <= 0 {
            b.alive = false
            g.parts.burst(b.x, b.y, 24, ["pink", "hotpink", "peach", "yellow"], 90, 0.8)
            g.app.audio.play("explode")
        }
        let old = phase
        let f = Double(hp) / Double(max(1, maxhp))
        phase = f > 0.66 ? 1 : (f > 0.33 ? 2 : 3)
        if phase > old && hp > 0 {
            g.hype.banner("GRRR!!", "\(name) IS FURIOUS", color: "red", dur: 1.2, scale: 2, sound: "boom")
            g.hype.flash("red", 0.2)
            g.app.shake(3, 0.3)
            if kind == "cake" && phase == 3 && tier >= 4 {
                for p in parts { p.alive = true; p.hp = p.maxhp }     // the candles light up again
            }
        }
        if hp <= 0 { startDying() }
    }

    /// Jelly donut: big -> 2 medium (at half health) -> 2 small each (tier 3+).
    func split(_ b: BBBody) {
        if b.hp <= 0 { return }
        let big = b.size == 0 && Double(b.hp) <= Double(maxhp) * 0.5
        let mid = b.size == 1 && tier >= 3 && Double(b.hp) <= Double(maxhp) * 0.14
        if !(big || mid) { return }
        b.alive = false
        let dims = [(30, 24), (20, 16)][b.size]
        let h1 = b.hp / 2
        for (i, share) in [h1, b.hp - h1].enumerated() where share > 0 {
            let side = Double(i * 2 - 1)
            let nb = BBBody(b.x + side * 10, b.y, dims.0, dims.1, share, b.size + 1)
            let sp = hypot(b.vx, b.vy) * 1.2 + 10
            nb.vx = side * sp * 0.8
            nb.vy = -sp * 0.6
            nb.flash = 0.2
            bodies.append(nb)
        }
        bodies.removeAll { !$0.alive }
        g.app.audio.play("pop")
        g.hype.banner("SPLIT!", color: "pink", dur: 0.8, scale: 1)
    }

    func openLid() {
        open = true
        openT = 4.0
        lidHits = 0
        g.app.audio.play("pop")
        let b = bodies[0]
        g.parts.burst(b.x, b.y - 28, 10, ["hotpink", "red", "white"], 60, 0.5)
        attack("spread", b.x, b.y - 4)
        if phase >= 2 { g.spawnMinions(1 + phase / 2 + tier / 6) }
    }

    func startDying() {
        state = "dying"
        dieT = 2.0
        teles = []; projs = []; beams = []
        g.hype.slowmo(0.35, 1.6)
        g.hype.flash("white", 0.3)
        g.app.audio.play("boom")
    }

    // ------------------------------------------------------------------ attacks
    func attack(_ k: String, _ sx: Double, _ sy: Double) {
        switch k {
        case "aimed": teles.append(BBTele("aimed", sx, sy, 0.75))
        case "drop": teles.append(BBTele("drop", sx, sy, 0.6))
        case "spread": teles.append(BBTele("spread", sx, sy, 0.7))
        case "rain":
            let n = min(7, 3 + tier / 4)
            let xs = (0 ..< n).map { _ in Double.random(in: (LEFT + 10) ... (RIGHT - 10)) }
            teles.append(BBTele("rain", sx, TOP, 1.0, xs))
        case "beam":
            var xs = [g.px]
            if phase >= 3 || tier >= 12 {
                xs.append(max(LEFT + 12, min(RIGHT - 12, g.px + ([-70.0, 70.0].randomElement() ?? 70))))
            }
            teles.append(BBTele("beam", sx, sy, 1.0, xs))
        case "arc": teles.append(BBTele("arc", sx, sy, 0.8))
        default: break
        }
    }

    func fire(_ te: BBTele) {
        let tr = Double(tier)
        switch te.kind {
        case "aimed":
            let dx = g.px - te.x, dy = Double(PADDLE_Y) - te.y
            let d = hypot(dx, dy) > 0 ? hypot(dx, dy) : 1
            let v = 85 + 4 * tr
            projs.append(BBProj(te.x, te.y, dx / d * v, dy / d * v, style))
            g.app.audio.play("shoot")
        case "drop":
            let vx = max(-40, min(40, (g.px - te.x) * 0.3))
            projs.append(BBProj(te.x, te.y, vx, 90 + 4 * tr, style))
            g.app.audio.play("shoot")
        case "spread":
            let n = (tier >= 8 || phase >= 3) ? 5 : 3
            for i in 0 ..< n {
                let a = (Double(i) - Double(n - 1) / 2) * 18 * .pi / 180
                let v = 80 + 3 * tr
                projs.append(BBProj(te.x, te.y, sin(a) * v, cos(a) * v, style))
            }
            g.app.audio.play("shoot")
        case "rain":
            for x in te.xs { projs.append(BBProj(x, TOP + 2, 0, 100 + 3 * tr, "drop")) }
            g.app.audio.play("shoot")
        case "beam":
            for x in te.xs { beams.append((x: x, t: 0.5)) }
            g.app.audio.play("explode")
            g.app.shake(2, 0.3)
        case "arc":
            for _ in 0 ..< min(8, 4 + tier / 5) {
                projs.append(BBProj(te.x, te.y, .random(in: -80 ... 80), .random(in: -120 ... -70), "candy", 150))
            }
            g.app.audio.play("bubble")
        default: break
        }
    }

    /// Choose and launch the next attack for the current phase.
    func pickAttack() {
        nAtk += 1
        let alive = bodies.filter { $0.alive }
        guard let b = alive.randomElement() else { return }
        let bh = Double(b.h)
        if !extra.isEmpty && nAtk % 3 == 0 {
            attack(extra[(nAtk / 3) % extra.count], b.x, b.y + bh / 2)
            return
        }
        switch kind {
        case "cake":
            let candles = parts.filter { $0.alive }
            if phase >= 2 && nAtk % 2 == 0 {
                attack("rain", b.x, b.y)
            } else if !candles.isEmpty {
                for p in candles.shuffled().prefix(min(candles.count, phase >= 3 ? 2 : 1)) {
                    p.glow = 0.75
                    attack(phase >= 3 ? "spread" : "aimed", p.x, p.y - 4)
                }
            } else {
                attack("spread", b.x, b.y + 20)
            }
        case "donut":
            b.shake = 0.6
            attack((phase >= 3 && nAtk % 2 == 1) ? "spread" : "drop", b.x, b.y + bh / 2)
        case "jar":
            if !open { attack(phase >= 3 ? "aimed" : "drop", b.x, b.y + 26) }
        case "robot":
            if phase >= 2 && nAtk % 2 == 0 {
                if let p = parts.first(where: { $0.alive }) { attack("spread", p.x, p.y) } else { attack("beam", b.x, b.y - 8) }
            } else {
                attack("beam", b.x, b.y - 8)
            }
        default:
            if dive == 0 {
                attack("arc", b.x + dir * 20, b.y - 14)
                if phase >= 3 { attack("aimed", b.x - dir * 30, b.y) }
            }
        }
    }

    // ------------------------------------------------------------------ frame
    func update(_ dt: Double) {
        t += dt
        for b in bodies { b.flash = max(0, b.flash - dt); b.shake = max(0, b.shake - dt) }
        for p in parts { p.flash = max(0, p.flash - dt); p.glow = max(0, p.glow - dt) }
        if state == "enter" {
            for b in bodies { b.y += (targetY - b.y) * min(1, dt * 2.5) }
            placeParts()
            return
        }
        if state == "dying" {
            dieT -= dt
            boomT -= dt
            if boomT <= 0 {
                boomT = 0.12
                let b = bodies[0]
                let x = b.x + .random(in: -Double(b.w) / 2 ... Double(b.w) / 2)
                let y = b.y + .random(in: -Double(b.h) / 2 ... Double(b.h) / 2)
                g.parts.burst(x, y, 10, ["yellow", "orange", "white", "pink"], 80, 0.6)
                g.app.audio.play("explode")
                g.app.shake(2, 0.15)
            }
            if dieT <= 0 { state = "dead"; g.bossDefeated() }
            return
        }
        if state != "fight" { return }
        move(dt)
        placeParts()
        atk -= dt
        if atk <= 0 {
            atk = rate * [1.0, 0.85, 0.7][phase - 1]
            pickAttack()
        }
        if kind == "jar" {
            openT -= dt
            if open && openT <= 0 {
                open = false
                openT = rate * 1.0
                g.app.audio.play("lock")
            } else if !open {
                if openT <= 0.8 { bodies[0].shake = 0.1 }       // the lid rattles: about to open
                if openT <= 0 { openLid() }
            }
        }
        if kind == "robot" && phase >= 3 {                       // shield arms grow back
            for p in parts where !p.alive {
                p.regrow -= dt
                if p.regrow <= 0 { p.alive = true; p.hp = p.maxhp; p.flash = 0.3 }
            }
        }
        for te in teles {
            te.t -= dt
            if te.t <= 0 { fire(te) }
        }
        teles.removeAll { $0.t <= 0 }
        // projectiles and beams vs the paddle
        for pr in projs {
            pr.vy += pr.g * dt
            pr.x += pr.vx * dt
            pr.y += pr.vy * dt
            if pr.y > Double(H + 6) || pr.x < -6 || pr.x > Double(W + 6) {
                pr.alive = false
            } else if g.paddleHit(pr.x, pr.y, 3) {
                pr.alive = false
            }
        }
        projs.removeAll { !$0.alive }
        for i in beams.indices {
            beams[i].t -= dt
            if abs(beams[i].x - g.px) < g.pw() / 2 + 4 { g.paddleHit(g.px, Double(PADDLE_Y), 0, beam: true) }
        }
        beams.removeAll { $0.t <= 0 }
    }

    func move(_ dt: Double) {
        let s = spd
        switch kind {
        case "cake":
            let b = bodies[0]
            let amp = phase == 1 ? 16.0 : 70.0
            b.x = Double(W) / 2 + sin(t * (phase == 1 ? 0.5 : 0.7) * s) * amp
        case "donut":
            for b in bodies where b.alive {
                let hw = Double(b.w) / 2, hh = Double(b.h) / 2
                b.x += b.vx * dt
                b.y += b.vy * dt
                if b.x < LEFT + hw { b.x = LEFT + hw; b.vx = abs(b.vx) } else if b.x > RIGHT - hw { b.x = RIGHT - hw; b.vx = -abs(b.vx) }
                // leave room for the gumball under the ceiling, and stay above the snack rows
                if b.y < TOP + 12 + hh { b.y = TOP + 12 + hh; b.vy = abs(b.vy) } else if b.y > 98 - hh { b.y = 98 - hh; b.vy = -abs(b.vy) }
            }
        case "jar":
            bodies[0].x = Double(W) / 2 + sin(t * 0.6 * s) * 60
        case "robot":
            bodies[0].x = Double(W) / 2 + sin(t * 0.45 * s) * 80
        default:
            let b = bodies[0]
            switch dive {
            case 0:
                b.x += dir * 38 * s * (phase >= 3 ? 1.4 : 1.0) * dt
                if b.x > RIGHT - 46 { dir = -1 } else if b.x < LEFT + 46 { dir = 1 }
                b.y = targetY + sin(t * 1.5) * 5
                if phase >= 2 {
                    diveT -= dt
                    if diveT <= 0 { dive = 1; g.app.audio.play("bubble") }
                }
            case 1:
                b.y -= 110 * dt
                if b.y < -30 { dive = 2; diveT = 1.4; attack("rain", b.x, TOP) }
            case 2:
                diveT -= dt
                if diveT <= 0 {
                    dive = 3
                    b.x = max(LEFT + 46, min(RIGHT - 46, g.px + .random(in: -60 ... 60)))
                }
            default:
                b.y += 90 * dt
                if b.y >= targetY { b.y = targetY; dive = 0; diveT = 9 }
            }
        }
    }

    func placeParts() {
        let b = bodies[0]
        if kind == "cake" {
            for p in parts { p.x = b.x + p.dx; p.y = b.y + p.dy }
        } else if kind == "robot" {
            let sw = sin(t * 1.4 * spd) * 44
            for p in parts { p.x = b.x + p.dx * sw; p.y = b.y + 36 }
        }
    }

    // ------------------------------------------------------------------ draw
    func draw(_ s: Surface, _ t: Double) {
        for bm in beams {
            let x = Int(bm.x)
            let w = Int(t * 30) % 2 == 1 ? 10 : 8
            s.fillRect(col("hotpink"), x - w / 2, Int(TOP), w, H - Int(TOP))
            s.fillRect(col("white"), x - 2, Int(TOP), 4, H - Int(TOP))
        }
        if state == "dead" { return }
        for b in bodies where b.alive {
            let ox = b.shake > 0 ? Int(sin(t * 60) * 2) : 0
            let x = Int(b.x) + ox, y = Int(b.y)
            var hit = b.flash > 0 && Int(t * 40) % 2 == 0
            if state == "dying" && Int(t * 20) % 2 == 1 { hit = true }
            switch kind {
            case "cake": drawCake(s, x, y, t, hit)
            case "donut": drawDonut(s, b, x, y, t, hit)
            case "jar": drawJar(s, x, y, t, hit)
            case "robot": drawRobot(s, x, y, t, hit)
            default: drawWhale(s, x, y, t, hit)
            }
        }
        for p in parts where p.alive { drawPart(s, p, t) }
        for te in teles { drawTele(s, te, t) }
        for pr in projs where pr.y > TOP + 2 { bbDrawProj(s, pr, t) }
    }

    var mood: String { phase >= 2 ? "angry" : "happy" }

    func drawCake(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool) {
        let tiers = [IRect(x - 48, y + 2, 96, 18), IRect(x - 34, y - 10, 68, 12), IRect(x - 22, y - 20, 44, 10)]
        for (i, r) in tiers.enumerated() {
            let body = hit ? "white" : ["cream", "peach", "cream"][i]
            s.rect(col("black"), r.inflate(2, 2), radius: 3)
            s.rect(col(body), r, radius: 3)
            s.fillRect(col(hit ? "white" : "pink"), r.x, r.y, r.w, 4)
            var dx = 4
            while dx < r.w - 3 { s.fillRect(col("pink"), r.x + dx, r.y + 4, 3, 2 + (dx / 9) % 3); dx += 9 }
            s.fillRect(col("choco"), r.x + 2, r.y + r.h - 3, r.w - 4, 1)
        }
        Cute.eyes(s, x, y + 9, 10, mood: mood, blink: Int(t * 1.3) % 6 == 0, size: 2)
        Cute.mouth(s, x, y + 14, phase >= 3 ? "angry" : "happy")
        Cute.blush(s, x, y + 12, 14)
        s.circle(col("red"), x, y - 23, 3)
        s.fillRect(col("white"), x - 1, y - 25, 1, 1)
    }

    func drawDonut(_ s: Surface, _ b: BBBody, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool) {
        let w = b.w, h = b.h
        let r = IRect(x - w / 2, y - h / 2, w, h)
        let o = r.inflate(2, 2)
        s.ellipse(col("black"), o.x, o.y, o.w, o.h)
        s.ellipse(col(hit ? "white" : "peach"), r.x, r.y, r.w, r.h)
        let f = r.inflate(-4, -6).moved(0, -2)
        s.ellipse(col(hit ? "white" : "hotpink"), f.x, f.y, f.w, f.h)
        let hw = max(4, w / 4), hh = max(3, h / 5)
        s.ellipse(col("ink"), x - hw / 2, y + h / 8 - hh / 2, hw, hh)
        for i in 0 ..< 7 {
            let a = Double(i) * 0.9 + Double(b.size)
            let sx = x + Int(cos(a) * Double(w) * 0.32), sy = y - 2 + Int(sin(a) * Double(h) * 0.25)
            s.fillRect(col(["yellow", "mint", "sky", "white"][i % 4]), sx, sy, 2, 1)
        }
        if b.size < 2 {
            Cute.eyes(s, x, y - h / 5, max(3, w / 6), mood: mood, blink: Int(t * 1.5) % 5 == 0)
        } else {
            Cute.eyes(s, x, y - 3, 3, mood: "angry")
        }
    }

    func drawJar(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool) {
        let r = IRect(x - 26, y - 22, 52, 50)
        s.rect(col("black"), r.inflate(2, 2), radius: 8)
        s.rect(col(hit ? "white" : "sky"), r, radius: 8)
        s.rect(col("ink"), r.inflate(-6, -6), radius: 6)
        for (cx, cy) in [(-12, 14), (4, 16), (14, 8), (-6, 4), (8, -2)] {
            s.circle(col("peach"), x + cx, y + cy, 6)
            s.fillRect(col("choco"), x + cx - 2, y + cy - 1, 2, 1)
            s.fillRect(col("choco"), x + cx + 1, y + cy + 2, 2, 1)
        }
        s.fillRect(col("white"), r.x + 4, r.y + 6, 2, 30)
        var lid: IRect
        if open {
            // the lid pops up and an eye peeks out
            s.circle(col("white"), x, y - 20, 9)
            let px = max(-4, min(4, Int((g.ballX() - Double(x)) / 20)))
            s.circle(col("black"), x + px, y - 19, 4)
            s.fillRect(col("white"), x + px - 2, y - 21, 1, 1)
            lid = IRect(x - 28, y - 44 - Int(abs(sin(t * 8)) * 3), 56, 9)
        } else {
            lid = IRect(x - 28 + (openT < 0.8 ? Int(sin(t * 50) * 2) : 0), y - 30, 56, 9)
            Cute.eyes(s, x, y - 14, 9, mood: phase >= 2 ? "angry" : "sleepy")
        }
        s.rect(col("black"), lid.inflate(2, 2), radius: 3)
        s.rect(col(hit ? "white" : "red"), lid, radius: 3)
        s.fillRect(col("pink"), lid.x + 3, lid.y + 2, lid.w - 6, 1)
        s.fillRect(col("red"), lid.centerx - 4, lid.y - 3, 8, 3)
    }

    func drawRobot(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool) {
        let body = col(hit ? "white" : "brown")
        let r = IRect(x - 20, y - 6, 40, 28)
        s.rect(col("black"), r.inflate(2, 2), radius: 5)
        s.rect(body, r, radius: 5)
        s.circle(col("black"), x, y - 12, 13)
        s.circle(body, x, y - 12, 12)
        var i = -16
        while i <= 16 { s.fillRect(col("white"), x + i, y - 4, 2, 1); i += 4 }
        for (k, c) in ["red", "mint", "yellow"].enumerated() { s.circle(col(c), x, y + 3 + k * 6, 2) }
        let charging = teles.contains { $0.kind == "beam" }
        let eye = charging && Int(t * 16) % 2 == 1 ? "red" : "white"
        for side in [-1, 1] {
            s.circle(col(eye), x + side * 5, y - 14, 3)
            s.fillRect(col("black"), x + side * 5 - (side < 0 ? 1 : 0), y - 14, 1, 2)
        }
        s.fillRect(col("white"), x - 4, y - 7, 8, 1)
        s.fillRect(col("white"), x - 5, y - 8, 1, 1)
        s.fillRect(col("white"), x + 4, y - 8, 1, 1)
        s.fillRect(col("gray"), x, y - 29, 1, 5)
        s.circle(col(Int(t * 3) % 2 == 1 ? "red" : "yellow"), x, y - 30, 2)
    }

    func drawWhale(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool) {
        let d = Int(dir)
        let body = col(hit ? "white" : "sky")
        let r = IRect(x - 38, y - 15, 76, 30)
        let tx = Double(x - d * 38), fy = Double(y), dd = Double(d)
        s.polygon(col("black"), [(tx, fy), (tx - dd * 16, fy - 12), (tx - dd * 16, fy + 8)])
        s.polygon(body, [(tx + dd, fy), (tx - dd * 14, fy - 10), (tx - dd * 14, fy + 6)])
        let o = r.inflate(2, 2)
        s.ellipse(col("black"), o.x, o.y, o.w, o.h)
        s.ellipse(body, r.x, r.y, r.w, r.h)
        s.ellipse(col("mint"), x - 30, y + 2, 60, 12)
        for i in 0 ..< 5 { s.fillRect(col("teal"), x - 20 + i * 9, y + 6, 1, 6) }
        let ex = x + d * 22
        s.circle(col("white"), ex, y - 3, 4)
        s.circle(col("black"), ex + d, y - 3, 2)
        if phase >= 2 { s.fillRect(col("black"), ex - 3, y - 8 - (d > 0 ? 1 : 0), 6, 1) }
        Cute.blush(s, ex, y + 3, 3)
        s.fillRect(col("blue"), x + d * 6, y - 15, 4, 2)
        if teles.contains(where: { $0.kind == "arc" }) {       // the spout builds up
            let hh = 4 + Int(abs(sin(t * 20)) * 6)
            s.fillRect(col("white"), x + d * 6 + 1, y - 15 - hh, 2, hh)
            s.circle(col("pink"), x + d * 6 + 2, y - 16 - hh, 3)
        }
    }

    func drawPart(_ s: Surface, _ p: BBPart, _ t: Double) {
        let hit = p.flash > 0 && Int(t * 40) % 2 == 0
        let r = p.rect()
        if p.kind == "candle" {
            s.fillRect(col("black"), r.inflate(2, 2))
            s.fillRect(col(hit ? "white" : "cream"), r)
            var yy = r.y + 1
            while yy < r.bottom { s.fillRect(col("pink"), r.x, yy, r.w, 1); yy += 3 }
            let big = p.glow > 0
            let fh = 5 + (big ? 3 : 0) + Int(sin(t * 20 + p.dx) * 1)
            let fc = big && Int(t * 20) % 2 == 1 ? "white" : "yellow"
            s.ellipse(col("orange"), r.centerx - 3, r.y - fh, 6, fh + 1)
            s.ellipse(col(fc), r.centerx - 1, r.y - fh + 2, 3, fh - 2)
        } else {
            s.rect(col("black"), r.inflate(2, 2), radius: 3)
            s.rect(col("white"), r, radius: 3)
            if !hit {
                var i = 0
                while i < r.w { s.fillRect(col("red"), r.x + i, r.y + 1, 3, r.h - 2); i += 6 }
            }
            s.fillRect(col("white"), r.x + 2, r.y + 1, r.w - 4, 1)
            for i in 0 ..< p.maxhp { s.fillRect(col(i < p.hp ? "lime" : "darkgray"), r.x + 2 + i * 3, r.bottom + 2, 2, 1) }
        }
    }

    func drawTele(_ s: Surface, _ te: BBTele, _ t: Double) {
        let blink = Int(t * 12) % 2 == 0
        switch te.kind {
        case "aimed", "drop", "spread", "arc":
            if blink { drawText(s, "!", Int(te.x) - 2, Int(te.y) - 14, "yellow", outline: "red") }
            if te.kind == "aimed" { s.circle(col("red"), Int(g.px), PADDLE_Y + 3, blink ? 7 : 6, width: 1) }
        case "rain":
            for x in te.xs {
                if blink { s.polygon(col("red"), [(x - 4, 190), (x + 4, 190), (x, 195)]) }
                s.fillRect(col("red"), Int(x), Int(TOP) + 2, 1, 3)
            }
        case "beam":
            for x in te.xs {
                let xi = Int(x)
                var yy = Int(TOP)
                while yy < H {
                    if (yy / 6 + Int(t * 20)) % 2 == 1 { s.fillRect(col("red"), xi, yy, 1, 3) }
                    yy += 6
                }
                if blink { s.rect(col("red"), IRect(xi - 6, PADDLE_Y - 4, 12, 14), width: 1) }
            }
        default: break
        }
    }
}

func bbDrawProj(_ s: Surface, _ pr: BBProj, _ t: Double) {
    let x = Int(pr.x), y = Int(pr.y)
    switch pr.style {
    case "flame":
        s.circle(col("red"), x, y, 4); s.circle(col("orange"), x, y, 3); s.circle(col("yellow"), x, y - 1, 1)
    case "jam":
        s.circle(col("black"), x, y, 4); s.circle(col("red"), x, y, 3); s.fillRect(col("pink"), x - 1, y - 2, 1, 1)
    case "crumb":
        s.fillRect(col("black"), x - 3, y - 3, 7, 7); s.fillRect(col("peach"), x - 2, y - 2, 5, 5); s.fillRect(col("choco"), x, y, 1, 1)
    case "gear":
        s.circle(col("black"), x, y, 4); s.circle(col(Int(t * 10) % 2 == 1 ? "yellow" : "orange"), x, y, 3)
        s.fillRect(col("black"), x, y, 1, 1)
    case "candy":
        s.circle(col("black"), x, y, 4); s.circle(col("hotpink"), x, y, 3); s.fillRect(col("white"), x - 1, y - 1, 1, 1)
    default:
        s.circle(col("black"), x, y, 3); s.circle(col("white"), x, y, 2); s.fillRect(col("pink"), x, y + 1, 1, 1)
    }
}
