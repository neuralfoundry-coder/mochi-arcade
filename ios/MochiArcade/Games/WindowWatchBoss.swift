// WINDOW WATCH bosses (port of mochi_arcade/games/window_watch_boss.py): six original sky troublemakers plus the
// final STORM KING. They throw things at the treasures (telegraphed first) or swoop at them themselves.
import Foundation

private let HOME_Y: [String: Double] = ["cloud": 46, "crow": 52, "jelly": 58, "twister": 60, "kite": 54, "moth": 60, "king": 48]
private let RADIUS: [String: Int] = ["cloud": 19, "crow": 14, "jelly": 17, "twister": 15, "kite": 15, "moth": 15, "king": 24]
private let SPECIAL = ["swoop", "dash", "slam", "chase"]

final class WWBoss {
    unowned let sc: WindowWatch
    let kind, name: String
    var hp: Int
    let maxhp: Int
    let rate: Double
    let attacks, extra: [String]
    let tier, phases: Int
    var phase = 1
    var x = 160.0, y = -40.0
    let hy: Double
    let r: Int
    var t = 0.0
    var state = "enter"
    var mode = "idle"
    var mt = 0.0
    var cd = 2.2
    var tele = 0.0
    var next = ""
    var queue: [String] = []
    var flash = 0.0
    var inv = 0.0            // invulnerable after a hit (so a boss can't be shredded in seconds)
    var deadT = 0.0
    var tg = 0
    var dropCd = 0.0
    var gx = 160.0           // jelly: wander goal
    var dir = 1

    init(_ sc: WindowWatch, _ spec: WWBossSpec) {
        self.sc = sc
        kind = spec.kind; name = spec.name
        hp = spec.hp; maxhp = spec.hp
        rate = spec.rate
        attacks = spec.attacks; extra = spec.extra
        tier = spec.tier; phases = spec.phases
        hy = HOME_Y[spec.kind] ?? 50
        r = RADIUS[spec.kind] ?? 15
    }

    // ---------------------------------------------------------------- helpers
    func sp() -> Double { 1.0 + 0.04 * Double(tier) }

    func pool() -> [String] {
        if kind == "king" { return attacks + extra }
        let base = phase == 1 && extra.isEmpty ? Array(attacks.prefix(2)) : attacks
        return base + extra
    }

    func interval() -> Double { 3.0 / (rate * [1.0, 1.3, 1.6][phase - 1]) }
    func hittable() -> Bool { state == "fight" && inv <= 0 }

    /// Where the boss wants to be while idle.
    func home() -> (Double, Double) {
        switch kind {
        case "cloud", "king": return (160 + sin(t * 0.55) * 100, hy + sin(t * 1.3) * 5)
        case "crow": return (160 + sin(t * 0.7) * 112, hy + sin(t * 1.4) * 14)
        case "jelly":
            if abs(gx - x) < 6 { gx = Double.random(in: 60 ... 260) }
            let step = gx > x ? 46.0 : -46.0
            return (x + step * 0.4, hy - abs(sin(t * 2.2)) * 12)
        case "twister": return (160 + sin(t * 0.9) * 118, hy + sin(t * 3) * 2)
        case "kite": return (160 + sin(t * 0.8) * 118, hy + sin(t * 2.2) * 16)
        default: return (x + max(-40, min(40, sc.cx - x)), hy + sin(t * 2.5) * 8)
        }
    }

    // ---------------------------------------------------------------- update
    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        inv = max(0, inv - dt)
        if state == "enter" {
            y += (hy - y) * min(1, dt * 2.5)
            x += (160 - x) * min(1, dt * 2.5)
            return
        }
        if state == "dead" {
            deadT += dt
            y += 26 * dt
            x += sin(deadT * 40) * 30 * dt
            if Double.random(in: 0 ..< 1) < 0.5 {
                let rr = Double(r)
                sc.parts.burst(x + Double.random(in: -rr ... rr), y + Double.random(in: -rr ... rr), 4, ["white", "yellow", "pink"], 60, 0.5)
            }
            return
        }
        move(dt)
        if mode != "idle" { return }
        if tele > 0 {
            tele -= dt
            if tele <= 0 { perform(next) }
            return
        }
        cd -= dt
        if cd <= 0 {
            if !queue.isEmpty {
                next = queue.removeFirst()
                tele = 0.5
            } else {
                let p = pool()
                next = p.randomElement()!
                tele = 0.8
                if phase >= 3 && Double.random(in: 0 ..< 1) < 0.5 { queue.append(p.randomElement()!) }
            }
            cd = interval()
            if SPECIAL.contains(next) { tg = sc.aliveTarget(Int.random(in: 0 ..< 3)) }
            sc.app.audio.play("hold")
        }
    }

    func move(_ dt: Double) {
        let s = sp()
        if mode == "idle" {
            let (hx, hy2) = home()
            x += (hx - x) * min(1, dt * 3)
            y += (hy2 - y) * min(1, dt * 3)
            return
        }
        mt += dt
        switch mode {
        case "swoop":
            let tr = sc.treasures[tg]
            if stepTo(tr.x, Double(tr.top - 4), 120 * s, dt) {
                sc.bossHitsTreasure(tg)
                mode = "back"; mt = 0
            }
        case "back":
            let (hx, hy2) = home()
            if stepTo(hx, hy2, 110, dt) || mt > 3 { mode = "idle"; mt = 0 }
        case "dash":
            if mt < 0.9 {
                _ = stepTo(x, 112, 140 * s, dt)
            } else {
                x += Double(dir) * 150 * s * dt
                dropCd -= dt
                if dropCd <= 0 {
                    dropCd = 0.32
                    sc.spark(x, y + 6, sc.aliveTarget(sc.nearestSlot(x)), 0)
                }
                if (dir > 0 && x > 292) || (dir < 0 && x < 28) { mode = "back"; mt = 0 }
            }
        case "slam":
            if stepTo(x, 124, 170 * s, dt) {
                sc.app.shake(3, 0.3)
                sc.app.audio.play("bubble")
                for i in 0 ..< 6 {
                    let tgt = sc.aliveTarget(i % 3)
                    sc.spawn("mini", x + (Double(i) - 2.5) * 6, y - 6, tgt, WWData.kind("mini").speed * s)
                }
                mode = "back"; mt = 0
            }
        case "chase":
            let cx = sc.cx, cy = max(40, min(118, sc.cy))
            _ = stepTo(cx, cy, 64 * s, dt)
            dropCd -= dt
            if dropCd <= 0 {
                dropCd = 0.45
                let tgt = sc.aliveTarget(sc.nearestSlot(x))
                sc.spawn("seed", x, y + 8, tgt, WWData.kind("seed").speed * s * 1.2, 4.0, mt)
            }
            if mt > 3.5 { mode = "back"; mt = 0 }
        default:
            break
        }
    }

    func stepTo(_ tx: Double, _ ty: Double, _ speed: Double, _ dt: Double) -> Bool {
        let dx = tx - x, dy = ty - y
        let d = hypot(dx, dy)
        if d <= speed * dt || d < 1 { x = tx; y = ty; return true }
        x += dx / d * speed * dt
        y += dy / d * speed * dt
        return false
    }

    // ---------------------------------------------------------------- attacks
    func perform(_ atk: String) {
        let s = sp()
        let rr = Double(r)
        let n = 1 + phase
        func v(_ k: String) -> Double { WWData.kind(k).speed * s }
        func rnd3() -> Int { sc.aliveTarget(Int.random(in: 0 ..< 3)) }
        switch atk {
        case "drizzle":
            for i in 0 ..< 3 + n {
                sc.spawn("drop", x + Double.random(in: -rr ... rr), y + 8 - Double(i) * 10, rnd3(), v("drop"))
            }
        case "seed":
            sc.spawn("orb", x, y + rr, rnd3(), v("orb"))
            sc.lightning = 0.25
            sc.app.audio.play("explode")
        case "curtain":
            let m = 6 + phase
            let gap = Int.random(in: 0 ..< m)
            for i in 0 ..< m where i != gap {
                let xx = 24 + Double(i) * 272 / Double(m - 1)
                sc.spawn("drop", xx, Double(WW_TOPY), sc.aliveTarget(sc.nearestSlot(xx)), v("drop") * 0.9)
            }
        case "downpour":
            for i in 0 ..< 10 {
                let xx = Double.random(in: 20 ... 300)
                sc.spawn("drop", xx, Double(WW_TOPY - i * 9), sc.aliveTarget(sc.nearestSlot(xx)), v("drop") * 1.1)
            }
        case "feathers":
            for i in 0 ..< 4 + n {
                let tgt = sc.aliveTarget(i % 3)
                sc.spawn("feather", x, y + 4, tgt, v("feather"), ax: Double(WWData.slots[tgt]) + Double.random(in: -26 ... 26))
            }
        case "squad":
            let side = [-1, 1].randomElement()!
            for i in 0 ..< 2 + phase / 2 {
                let tgt = sc.aliveTarget(i % 3)
                let c = sc.spawn("crow", side > 0 ? -8.0 : 328.0, 30.0 + Double(i) * 14, tgt, v("crow"))
                c.p = max(30, min(290, Double(WWData.slots[tgt]) + Double.random(in: -40 ... 40)))
            }
        case "bubbles":
            for i in 0 ..< 2 + phase {
                sc.spawn("bubble", x + Double(i - 1) * 14, y + rr, sc.aliveTarget(i % 3), v("bubble") * 1.3,
                         y + rr + Double.random(in: 30 ... 50), Double.random(in: 0 ... 6))
            }
        case "spray":
            for i in 0 ..< 5 + n {
                let tgt = sc.aliveTarget(i % 3)
                sc.spawn("mini", x, y + rr, tgt, v("mini") * 0.9, ax: Double(WWData.slots[tgt]) + Double.random(in: -20 ... 20))
            }
        case "leafstorm":
            for i in 0 ..< 6 + n {
                let a = Double(i) * 2 * .pi / Double(6 + n)
                sc.spawn("leaf", x + cos(a) * 20, y + sin(a) * 10, sc.aliveTarget(i % 3), v("leaf") * 1.2,
                         Double.random(in: 8 ... 16), a)
            }
        case "acorns":
            for i in 0 ..< 2 + phase {
                sc.spawn("hail", x + Double(i - 1) * 10, y + rr, rnd3(), v("hail"))
            }
        case "gust":
            sc.gustT = 3.2
            sc.gustDir = [-1, 1].randomElement()!
            sc.hype.banner("GUST!", sc.gustDir > 0 ? ">>>" : "<<<", color: "sky", dur: 1.0, scale: 1)
            for _ in 0 ..< 4 {
                let xx = Double.random(in: 30 ... 290)
                sc.spawn("leaf", xx, Double(WW_TOPY), sc.aliveTarget(sc.nearestSlot(xx)), v("leaf"),
                         Double.random(in: 8 ... 14), Double.random(in: 0 ... 6))
            }
        case "sparks":
            for i in 0 ..< 5 + n { sc.spark(x, y + 6, sc.aliveTarget(i % 3), Double.random(in: -24 ... 24)) }
            sc.app.audio.play("explode")
        case "rockets":
            for _ in 0 ..< 2 + phase / 2 {
                let xx = Double.random(in: 30 ... 290)
                sc.spawn("rocket", xx, 206, sc.aliveTarget(sc.nearestSlot(xx)), v("rocket"), Double.random(in: 50 ... 86))
            }
        case "dust":
            let tgt = rnd3()
            for _ in 0 ..< 5 + phase {
                sc.spawn("seed", x + Double.random(in: -10 ... 10), y + 6 + Double.random(in: -4 ... 4), tgt, v("seed") * 1.2,
                         Double.random(in: 3 ... 7), Double.random(in: 0 ... 6))
            }
        case "mothlings":
            for i in 0 ..< 2 + phase / 2 {
                sc.spawn("moth", x + Double(i - 1) * 12, y + 6, sc.aliveTarget(i % 3), v("moth"), Double.random(in: 1.8 ... 3.0))
            }
        case "swoop":
            mode = "swoop"; mt = 0
            sc.app.audio.play("jump")
        case "dash":
            mode = "dash"; mt = 0
            dir = x < 160 ? 1 : -1
            dropCd = 0
        case "slam":
            mode = "slam"; mt = 0
        case "chase":
            mode = "chase"; mt = 0
            dropCd = 0.3
        default:
            break
        }
    }

    // ---------------------------------------------------------------- hits
    /// Returns true when this hit defeated the boss.
    func damage(_ n: Int) -> Bool {
        if state != "fight" { return false }
        hp -= n
        flash = 0.15
        inv = 0.4
        if hp <= 0 {
            hp = 0
            state = "dead"
            mode = "idle"
            deadT = 0
            return true
        }
        let frac = Double(hp) / Double(maxhp)
        let g = sc.hype!
        if phase == 1 && frac <= 0.5 && phases >= 2 {
            phase = 2
            g.banner("GRRRR!", name + " IS MAD", color: "red", dur: 1.3)
            g.flash("red", 0.2)
            cd = min(cd, 0.6)
        } else if phase == 2 && frac <= 0.25 && phases >= 3 {
            phase = 3
            g.banner("FURIOUS!", "LAST PHASE", color: "red", dur: 1.3)
            g.flash("red", 0.25)
            cd = min(cd, 0.4)
        }
        if mode == "swoop" {
            mode = "back"; mt = 0
            sc.floats.add(x, y - 16, "BONK!", "yellow")
        }
        return false
    }

    // ---------------------------------------------------------------- drawing
    func draw(_ s: Surface, _ t: Double) {
        if state == "dead" && deadT > 1.6 { return }
        let x = Int(self.x), y = Int(self.y)
        let hit = flash > 0 && Int(t * 30) % 2 == 0
        let angry = phase >= 2 || mode != "idle"
        switch kind {
        case "cloud", "king": WWBoss.drawCloud(s, x, y, t, hit, angry, kind == "king")
        case "crow": WWBoss.drawCrow(s, x, y, t, hit, angry, mode)
        case "jelly": WWBoss.drawJelly(s, x, y, t, hit, angry, phase)
        case "twister": WWBoss.drawTwister(s, x, y, t, hit, angry)
        case "kite": WWBoss.drawKite(s, x, y, t, hit, angry)
        default: WWBoss.drawMoth(s, x, y, t, hit, angry)
        }
        if tele > 0 && state == "fight" && Int(t * 10) % 2 == 1 {
            let special = SPECIAL.contains(next)
            drawText(s, "!", x - 2, y - r - 14, "red", scale: special ? 2 : 1, shadow: "black")
            if special {
                let tr = sc.treasures[tg]
                for i in 0 ..< 10 {
                    let f = Double(i) / 10
                    s.fillRect(col("red"), Int(Double(x) + (tr.x - Double(x)) * f), Int(Double(y) + Double(tr.top - y) * f), 2, 2)
                }
            }
        }
    }

    static func drawCloud(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ angry: Bool, _ king: Bool) {
        let body = hit ? "white" : (angry ? "darkgray" : "gray")
        let light = angry ? "gray" : "white"
        let puffs = king ? [(-20, 3, 11), (-8, -6, 13), (8, -5, 12), (21, 3, 10), (0, 6, 13)]
                         : [(-15, 3, 9), (-6, -5, 11), (7, -4, 10), (16, 3, 8), (0, 5, 11)]
        for (dx, dy, r) in puffs { s.circle(col("black"), x + dx, y + dy, r + 1) }
        for (dx, dy, r) in puffs { s.circle(col(body), x + dx, y + dy, r) }
        for (dx, dy, r) in puffs[1 ... 2] {
            s.fillRect(col(light), x + dx - 3, y + dy - r + 3, 5, 2)
            s.fillRect(col(light), x + dx - 5, y + dy - r + 5, 2, 2)
        }
        Cute.eyes(s, x, y + 2, 6, look: 0, mood: angry ? "angry" : "happy", size: 2)
        Cute.mouth(s, x, y + 7, angry ? "angry" : "happy")
        Cute.blush(s, x, y + 5, 8)
        for i in 0 ..< 3 {
            let dy = Int(wwMod(t * 40 + Double(i * 7), 12))
            s.fillRect(col("sky"), x - 10 + i * 10, y + 14 + dy, 1, 3)
        }
        if angry && Int(t * 6) % 3 == 0 {
            let fx = Double(x), fy = Double(y)
            s.polygon(col("yellow"), [(fx + 4, fy + 12), (fx - 2, fy + 20), (fx + 2, fy + 20), (fx - 3, fy + 28),
                                      (fx + 6, fy + 18), (fx + 2, fy + 18)])
        }
        if king {
            let fx = Double(x), fy = Double(y)
            s.polygon(col("yellow"), [(fx - 10, fy - 16), (fx - 10, fy - 26), (fx - 5, fy - 20), (fx, fy - 28),
                                      (fx + 5, fy - 20), (fx + 10, fy - 26), (fx + 10, fy - 16)])
            s.fillRect(col("red"), x - 1, y - 21, 3, 3)
            s.fillRect(col("orange"), x - 10, y - 17, 21, 1)
        }
    }

    static func drawCrow(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ angry: Bool, _ mode: String) {
        let flap = Int(sin(t * (mode != "idle" ? 14 : 8)) * 6)
        let body = hit ? "white" : "darkgray"
        let fx = Double(x), fy = Double(y), fl = Double(flap), fl2 = Double(wwDiv(flap, 2))
        for side in [-1.0, 1.0] {
            s.polygon(col("black"), [(fx + side * 6, fy - 3), (fx + side * 26, fy - 8 + fl), (fx + side * 20, fy + 2 + fl2),
                                     (fx + side * 8, fy + 6)])
            s.polygon(col("gray"), [(fx + side * 8, fy - 1), (fx + side * 22, fy - 5 + fl), (fx + side * 18, fy + 1 + fl2),
                                    (fx + side * 9, fy + 4)])
        }
        s.polygon(col("black"), [(fx - 4, fy + 8), (fx - 9, fy + 16), (fx, fy + 12), (fx + 9, fy + 16), (fx + 4, fy + 8)])
        s.ellipse(col("black"), x - 12, y - 9, 25, 21)
        s.ellipse(col(body), x - 11, y - 8, 23, 19)
        s.fillRect(col("gray"), x - 6, y + 2, 12, 5)
        Cute.eyes(s, x, y - 2, 5, look: 0, mood: angry ? "angry" : "happy", size: 2)
        s.polygon(col("orange"), [(fx - 3, fy + 1), (fx + 3, fy + 1), (fx, fy + 6)])
        s.fillRect(col("black"), x - 3, y + 1, 7, 1)
        // captain's cap
        s.fillRect(col("black"), x - 9, y - 15, 19, 6)
        s.fillRect(col("blue"), x - 8, y - 14, 17, 4)
        s.fillRect(col("ink"), x - 10, y - 10, 21, 2)
        s.fillRect(col("yellow"), x - 1, y - 13, 3, 2)
        s.fillRect(col("white"), x - 8, y - 14, 17, 1)
    }

    static func drawJelly(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ angry: Bool, _ phase: Int) {
        let r = 17 - (phase - 1) * 2
        let wob = sin(t * 5) * 1.5
        for i in 0 ..< 5 {
            for j in 0 ..< 5 {
                let px = x - 10 + i * 5 + Int(sin(t * 4 + Double(i) + Double(j) * 0.6) * 2)
                s.fillRect(col((i + j) % 2 == 1 ? "lavender" : "pink"), px, y + r - 4 + j * 3, 2, 2)
            }
        }
        let fx = Double(x), fy = Double(y), fr = Double(r)
        s.ellipse(col("black"), Int(fx - fr - 1 - wob), Int(fy - fr - 1 + wob), Int(2 * fr + 2 + 2 * wob), Int(2 * fr + 2 - 2 * wob))
        s.ellipse(col(hit ? "white" : "lavender"), Int(fx - fr - wob), Int(fy - fr + wob), Int(2 * fr + 2 * wob), Int(2 * fr - 2 * wob))
        s.ellipse(col("pink"), x - r + 4, y - 2, 2 * r - 8, r - 2)
        s.circle(col("white"), x - r / 2, y - r / 2, 3)
        s.fillRect(col("white"), x + r / 2, y - r / 2 - 2, 2, 2)
        Cute.eyes(s, x, y - 1, 6, look: 0, mood: angry ? "angry" : "happy", size: 2)
        Cute.mouth(s, x, y + 5, angry ? "angry" : "wow")
        Cute.blush(s, x, y + 3, 8)
    }

    static func drawTwister(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ angry: Bool) {
        for i in 0 ..< 7 {
            let w = 40 - i * 5
            let yy = y - 16 + i * 5
            let xx = x + Int(sin(t * 6 + Double(i) * 0.8) * 3)
            s.ellipse(col("black"), xx - w / 2 - 1, yy - 1, w + 2, 8)
            s.ellipse(col(hit ? "white" : (i % 2 == 1 ? "lavender" : "sky")), xx - w / 2, yy, w, 6)
        }
        for j in 0 ..< 6 {
            let a = t * 4 + Double(j) * 1.05
            let lx = x + Int(cos(a) * 24)
            let ly = y - 8 + j * 4 + Int(sin(a) * 4)
            s.fillRect(col("black"), lx - 1, ly - 1, 4, 3)
            s.fillRect(col(j % 2 == 1 ? "orange" : "yellow"), lx, ly, 2, 1)
        }
        Cute.eyes(s, x, y - 10, 6, look: 0, mood: angry ? "angry" : "happy", size: 2)
        Cute.mouth(s, x, y - 5, angry ? "angry" : "happy")
    }

    static func drawKite(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ angry: Bool) {
        s.line(col("white"), x - 6, y + 6, x + 30, 200)
        let wave = Double(Int(sin(t * 7) * 4))
        let fx = Double(x), fy = Double(y)
        s.polygon(col("black"), [(fx - 14, fy), (fx - 30, fy - 9 + wave), (fx - 25, fy), (fx - 30, fy + 9 + wave)])
        s.polygon(col(hit ? "white" : "yellow"), [(fx - 15, fy), (fx - 28, fy - 7 + wave), (fx - 24, fy), (fx - 28, fy + 7 + wave)])
        s.ellipse(col("black"), x - 18, y - 10, 36, 20)
        s.ellipse(col(hit ? "white" : (angry ? "red" : "orange")), x - 17, y - 9, 34, 18)
        s.ellipse(col("cream"), x - 12, y + 1, 24, 7)
        for i in 0 ..< 3 {
            for j in 0 ..< 2 {
                let sx = x - 10 + i * 6 + j * 3, sy = y - 6 + j * 4
                s.fillRect(col("yellow"), sx, sy, 3, 1)
                s.fillRect(col("yellow"), sx - 1, sy + 1, 1, 1)
            }
        }
        s.circle(col("black"), x + 15, y, 5)
        s.circle(col("ink"), x + 15, y, 3)
        s.circle(col("white"), x + 8, y - 3, 3)
        s.fillRect(col("black"), x + 8 + (angry ? 1 : 0), y - 3, 2, 2)
        if angry { s.fillRect(col("black"), x + 5, y - 7, 6, 1) }
        for side in [-1.0, 1.0] {
            s.polygon(col("orange"), [(fx - 2, fy + side * 8), (fx - 8, fy + side * 14), (fx + 4, fy + side * 9)])
        }
    }

    static func drawMoth(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ hit: Bool, _ angry: Bool) {
        let flap = Int(abs(sin(t * 6)) * 7)
        for side in [-1, 1] {
            let wx = x + (side > 0 ? 2 : -26)
            s.ellipse(col("black"), wx - 1, y - 16 + flap / 2, 26, 20 - flap)
            s.ellipse(col(hit ? "white" : "lavender"), wx, y - 15 + flap / 2, 24, 18 - flap)
            let ex = x + side * 13
            s.circle(col("purple"), ex, y - 6, 4 - flap / 4)
            s.circle(col("yellow"), ex, y - 6, 2 - flap / 6)
            let lx = x + (side > 0 ? 2 : -18)
            s.ellipse(col("black"), lx - 1, y + 1, 18, 12)
            s.ellipse(col("pink"), lx, y + 2, 16, 10)
        }
        for side in [-1, 1] {
            s.line(col("black"), x + side * 2, y - 10, x + side * 8, y - 20)
            s.circle(col("yellow"), x + side * 8, y - 20, 2)
        }
        s.ellipse(col("black"), x - 6, y - 12, 12, 26)
        s.ellipse(col(hit ? "white" : "cream"), x - 5, y - 11, 10, 24)
        for i in 0 ..< 3 { s.fillRect(col("peach"), x - 4, y + 2 + i * 4, 8, 1) }
        s.ellipse(col("white"), x - 6, y - 6, 12, 4)
        Cute.eyes(s, x, y - 7, 3, look: 0, mood: angry ? "angry" : "happy")
    }
}
