// COMET KITTY - fixed-screen space shooter (port of games/comet_kitty.py).
import Foundation

private let PY = 178.0
private let POINTS: [Int: (Int, Int)] = [0: (50, 100), 1: (80, 160), 2: (150, 400)]

private func bezier(_ p: [(Double, Double)], _ u: Double) -> (Double, Double) {
    let a = pow(1 - u, 3), b = 3 * u * pow(1 - u, 2), c = 3 * u * u * (1 - u), d = u * u * u
    return (a * p[0].0 + b * p[1].0 + c * p[2].0 + d * p[3].0, a * p[0].1 + b * p[1].1 + c * p[2].1 + d * p[3].1)
}

final class CKEnemy {
    let kind, col, row: Int
    var hp: Int
    var state = "enter"
    var t = 0.0
    let delay: Double
    let side: Int
    var x: Double, y = 70.0
    var path: [(Double, Double)]?
    var dur = 1.8
    var shots: [(Double, Bool)] = []
    var hitFlash = 0.0
    var alive = true

    init(_ kind: Int, _ col: Int, _ row: Int, _ delay: Double, _ side: Int) {
        self.kind = kind; self.col = col; self.row = row; self.delay = delay; self.side = side
        hp = kind == 2 ? 2 : 1
        x = side < 0 ? -20 : Double(W + 20)
    }

    var size: (Int, Int) { kind == 2 ? (16, 14) : (12, 12) }
    func rect() -> IRect { let (w, h) = size; return IRect(Int(x) - w / 2, Int(y) - h / 2, w, h) }
}

final class CometKitty: GameScene {
    override var music: String? { "comet" }
    override var buttons: [Action: String] { [.a: "FIRE"] }
    var lives: Int, spd: Double, wave: Int
    let stars = Stars(80, seed: 7)
    var px = Double(W) / 2
    var shots: [(Double, Double)] = []
    var bullets: [(x: Double, y: Double, vx: Double, vy: Double)] = []
    var items: [(x: Double, y: Double, got: Bool)] = []
    var inv = 2.0
    var deadT: Double?
    var wingman = 0.0
    var nextExtra = 20000
    var enemies: [CKEnemy] = []
    var bonus = false
    var waveT = 0.0, bannerT = 1.8, diveT = 3.0
    var bonusHits = 0

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        spd = SPEEDS[d] ?? 1
        wave = Int(opt["wave"] ?? "1") ?? 1
        super.init(app, info, opt)
        startWave()
    }

    func slot(_ e: CKEnemy) -> (Double, Double) {
        let sway = sin(t * 0.9) * 14, breathe = 1 + sin(t * 1.7) * 0.06
        return (Double(W) / 2 + (Double(e.col) - 3.5) * 26 * breathe + sway, Double(30 + e.row * 16))
    }

    func startWave() {
        enemies = []
        bonus = wave % 4 == 0
        waveT = 0; bannerT = 1.8; diveT = 3; bonusHits = 0
        if bonus {
            for g in 0 ..< 5 {
                let side = g % 2 == 0 ? -1 : 1
                for i in 0 ..< 8 {
                    let e = CKEnemy(i % 2, 0, 0, Double(g) * 2.2 + Double(i) * 0.16, side)
                    e.state = "parade"
                    let y0 = Double(30 + g * 22)
                    var path = [(-24.0, y0), (Double(W) * 0.35, 190.0), (Double(W) * 0.65, -10.0), (Double(W + 24), y0 + 60)]
                    if side > 0 { path = path.map { (Double(W) - $0.0, $0.1) } }
                    e.path = path
                    e.dur = 3.2
                    enemies.append(e)
                }
            }
            return
        }
        var layout: [(Int, Int, Int)] = (2 ..< 6).map { (2, 0, $0) }
        for r in [1, 2] { for c in 1 ..< 7 { layout.append((1, r, c)) } }
        for r in [3, 4] { for c in 0 ..< 8 { layout.append((0, r, c)) } }
        for (n, (kind, row, c)) in layout.enumerated() {
            let group = n / 8
            enemies.append(CKEnemy(kind, c, row, 0.6 + Double(group) * 1.5 + Double(n % 8) * 0.13, group % 2 == 0 ? -1 : 1))
        }
    }

    override func tick(_ dt: Double) {
        let inp = app.input, au = app.audio
        stars.update(dt, 22)
        waveT += dt; bannerT -= dt
        inv = max(0, inv - dt)
        wingman = max(0, wingman - dt)
        let diff = spd * (1 + 0.06 * Double(wave - 1))
        if deadT == nil {
            let d = (inp.down(.right) ? 1.0 : 0) - (inp.down(.left) ? 1.0 : 0)
            px = max(10, min(Double(W - 10), px + d * 130 * dt))
            let limit = wingman > 0 ? 3 : 2
            if inp.hit(.a) && shots.count < limit {
                shots.append((px, PY))
                if wingman > 0 { shots.append((px + 14, PY + 4)) }
                au.play("shoot")
            }
        } else {
            deadT! -= dt
            if deadT! <= 0 {
                if lives <= 0 { endGame(false, "WAVE \(wave)"); return }
                deadT = nil; inv = 2.5; px = Double(W) / 2
            }
        }
        shots = shots.map { ($0.0, $0.1 - 270 * dt) }.filter { $0.1 > -8 }
        for e in enemies { updateEnemy(e, dt, diff) }
        if !bonus && waveT > 6 {
            diveT -= dt
            if diveT <= 0 {
                diveT = max(0.5, 2.4 - Double(wave) * 0.12) / spd * Double.random(in: 0.7 ... 1.3)
                launchDive()
            }
        }
        bullets = bullets.map { (x: $0.x + $0.vx * dt, y: $0.y + $0.vy * dt, vx: $0.vx, vy: $0.vy) }.filter { $0.y > -10 && $0.y < Double(H + 10) }
        items = items.map { (x: $0.x, y: $0.y + 45 * dt, got: $0.got) }
        collide()
        items.removeAll { $0.got || $0.y >= Double(H + 10) }
        enemies.removeAll { !$0.alive }
        if score >= nextExtra {
            lives += 1; nextExtra += 50000
            au.play("extra"); floats.add(px, PY - 14, "1UP!", "mint")
        }
        if enemies.isEmpty && ending == nil {
            if bonus {
                let pts = bonusHits >= 40 ? 10000 : bonusHits * 100
                add(pts, Double(W / 2), 100, "mint")
                floats.add(Double(W / 2), 86, "BONUS \(bonusHits) HITS", "yellow")
                au.play(bonusHits >= 40 ? "win" : "levelup")
            } else { au.play("levelup") }
            wave += 1
            startWave()
        }
    }

    func updateEnemy(_ e: CKEnemy, _ dt: Double, _ diff: Double) {
        e.t += dt
        e.hitFlash = max(0, e.hitFlash - dt)
        switch e.state {
        case "enter":
            if e.t < e.delay { return }
            if e.path == nil {
                let sx = e.side < 0 ? -20.0 : Double(W + 20)
                e.path = [(sx, 60), (Double(W) / 2 - Double(e.side) * 70, 190), (Double(W) / 2 + Double(e.side) * 90, 40)]
            }
            let u = min(1, (e.t - e.delay) / e.dur)
            (e.x, e.y) = bezier(Array(e.path!.prefix(3)) + [slot(e)], u)
            if u >= 1 { e.state = "form" }
        case "form":
            (e.x, e.y) = slot(e)
        case "parade":
            if e.t < e.delay { e.x = -50; return }
            let u = (e.t - e.delay) / e.dur
            if u >= 1 { e.alive = false; return }
            (e.x, e.y) = bezier(e.path!, u)
        case "dive":
            let u = e.t / e.dur
            if u >= 1 { e.state = "return"; e.t = 0; e.path = [(e.x, -16), (e.x, 20)]; return }
            (e.x, e.y) = bezier(e.path!, u)
            for i in e.shots.indices where !e.shots[i].1 && u >= e.shots[i].0 {
                e.shots[i].1 = true
                let ang = atan2(PY - e.y, px - e.x), sp = 105 * diff
                bullets.append((x: e.x, y: e.y + 6, vx: cos(ang) * sp * 0.45, vy: abs(sin(ang)) * sp + 30))
            }
        case "return":
            let u = min(1, e.t / 1.2)
            let (sx, sy) = slot(e)
            (e.x, e.y) = bezier([e.path![0], e.path![1], (sx, sy - 20), (sx, sy)], u)
            if u >= 1 { e.state = "form" }
        default: break
        }
    }

    func launchDive() {
        let ready = enemies.filter { $0.state == "form" }
        guard let e = ready.randomElement() else { return }
        var group = [e]
        if e.kind == 2 { group += ready.filter { $0.kind == 1 && $0.row == 1 && abs($0.col - e.col) <= 1 }.prefix(2) }
        let side = e.x < Double(W) / 2 ? 1.0 : -1.0
        for (i, g) in group.enumerated() {
            g.state = "dive"; g.t = 0
            g.dur = Double.random(in: 2.3 ... 2.9) / max(0.7, spd)
            let off = (Double(i) - Double(group.count - 1) / 2) * 16
            g.path = [(g.x, g.y), (g.x + side * 70, g.y - 20), (px + off - side * 40, 150), (px + off + side * 30, Double(H + 24))]
            let n = 1 + (Double.random(in: 0 ..< 1) < 0.3 + Double(wave) * 0.04 ? 1 : 0)
            g.shots = (0 ..< n).map { _ in (Double.random(in: 0.15 ... 0.55), false) }
        }
        app.audio.play("move")
    }

    func collide() {
        let au = app.audio
        var i = 0
        while i < shots.count {
            let sh = shots[i]
            let r = IRect(Int(sh.0) - 2, Int(sh.1) - 3, 5, 7)
            if let e = enemies.first(where: { $0.alive && ($0.state != "enter" || $0.t > $0.delay) && $0.rect().intersects(r) }) {
                shots.remove(at: i)
                hitEnemy(e)
            } else { i += 1 }
        }
        if deadT != nil { return }
        let pr = IRect(Int(px) - 6, Int(PY) + 3, 12, 11)
        if inv <= 0 {
            if let bi = bullets.firstIndex(where: { pr.contains($0.x, $0.y) }) {
                bullets[bi].y = Double(H + 99)
                killPlayer(); return
            }
            for e in enemies where e.alive && (e.state == "dive" || e.state == "parade") && e.rect().inflate(-2, -2).intersects(pr) {
                if e.state == "dive" { e.alive = false; parts.burst(e.x, e.y, 14, ["sky", "white", "pink"], 70, 0.6) }
                killPlayer(); return
            }
        }
        for k in items.indices where pr.contains(items[k].x, items[k].y) {
            items[k].got = true
            wingman = 20
            add(1000, px, PY - 10, "mint")
            au.play("powerup")
        }
    }

    func hitEnemy(_ e: CKEnemy) {
        let au = app.audio
        e.hp -= 1
        if e.hp > 0 { e.hitFlash = 0.3; au.play("tin"); return }
        e.alive = false
        let diving = e.state == "dive" || e.state == "return"
        var pts = diving ? POINTS[e.kind]!.1 : POINTS[e.kind]!.0
        if e.state == "parade" { bonusHits += 1; pts = 100 }
        add(pts, e.x, e.y - 8, diving ? "mint" : "yellow")
        let colors = [0: ["sky", "white", "blue"], 1: ["pink", "hotpink", "white"], 2: ["purple", "yellow", "white"]][e.kind]!
        parts.burst(e.x, e.y, 16, colors, 80, 0.6)
        au.play("explode")
        if e.kind == 2 && diving && Double.random(in: 0 ..< 1) < 0.35 && wingman <= 0 { items.append((x: e.x, y: e.y, got: false)) }
    }

    func killPlayer() {
        lives -= 1
        deadT = 1.6
        wingman = 0
        shots.removeAll()
        app.audio.play("boom")
        app.shake(4, 0.4)
        parts.burst(px, PY + 8, 30, ["orange", "yellow", "white", "pink"], 110, 1.0)
    }

    override func render(_ s: Surface) {
        s.fill(col("night"))
        stars.draw(s, t)
        for it in items {
            s.blit(sprite("star"), Int(it.x) - 3, Int(it.y) - 3)
            if Int(t * 10) % 2 == 1 { s.fillRect(col("white"), Int(it.x), Int(it.y) - 6, 1, 2) }
        }
        for e in enemies {
            if e.state == "enter" && e.t < e.delay { continue }
            let (w, h) = e.size
            let flash = e.hitFlash > 0 || (e.hp < 2 && e.kind == 2 && Int(t * 6) % 2 == 0)
            Cute.spaceJelly(s, Int(e.x) - w / 2, Int(e.y) - h / 2, t + Double(e.col), e.kind, hit: flash)
        }
        for sh in shots {
            let x = Int(sh.0), y = Int(sh.1)
            s.fillRect(col("yellow"), x - 1, y - 3, 3, 6)
            s.fillRect(col("white"), x, y - 3, 1, 3)
        }
        for b in bullets {
            s.circle(col("pink"), Int(b.x), Int(b.y), 2)
            s.fillRect(col("white"), Int(b.x) - 1, Int(b.y) - 1, 1, 1)
        }
        if deadT == nil && (inv <= 0 || Int(inv * 12) % 2 == 0) {
            let bob = Int(sin(t * 5))
            s.blit(sprite("kitty"), Int(px) - 8, Int(PY) + bob)
            let flame = Int(t * 20) % 2
            s.fillRect(col(flame == 1 ? "orange" : "yellow"), Int(px) - 2, Int(PY) + 16 + bob, 4, 2 + flame)
            if wingman > 0 && (wingman > 3 || Int(t * 8) % 2 == 1) {
                s.blit(sprite("star"), Int(px) + 11, Int(PY) + 6 + Int(sin(t * 6) * 2))
            }
        }
        parts.draw(s)
        floats.draw(s)
        drawText(s, String(format: "%07d", score), 4, 2, "white", shadow: nil)
        drawText(s, String(format: "HI %07d", max(best, score)), W / 2, 2, "lavender", align: .center, shadow: nil)
        drawText(s, "WAVE \(wave)", W - 4, 2, "yellow", align: .right, shadow: nil)
        for i in 0 ..< max(0, min(lives, 6)) { s.blit(sprite("heart"), 4 + i * 8, H - 8) }
        if bannerT > 0 {
            if bonus { banner(s, "BONUS PARADE!", "SHOOT THEM ALL", "mint") } else { banner(s, "WAVE \(wave)", "GET READY!") }
        }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("night"))
        let w = s.w, h = s.h
        let st = Stars(25, seed: 2)
        st.update(t, 15)
        st.draw(s, t)
        for i in 0 ..< 5 { Cute.spaceJelly(s, 6 + i * 18 + Int(sin(t + Double(i)) * 3), 6 + (i % 2) * 12, t, i % 2) }
        Cute.spaceJelly(s, w / 2 - 8, 30 + Int(sin(t * 2) * 6), t, 2)
        s.blit(sprite("kitty"), w / 2 - 8 + Int(sin(t * 1.5) * 20), h - 18)
        s.fillRect(col("yellow"), w / 2 + Int(sin(t * 1.5) * 20), h - 30 - Int(t * 60) % 20, 2, 4)
    }
}
