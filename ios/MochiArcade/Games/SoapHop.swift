// SOAP HOP - single-screen bubble platformer (port of games/soap_hop.py).
import Foundation

private let T = 8, COLS = 40, ROWS = 23, TOP = 12
private let FIELD_H = ROWS * T
private let GRAV = 620.0, JUMP = 255.0, RUN = 74.0, FAST_PHASE = 0.32

class SHBody {
    var x, y: Double
    let w, h: Int
    var vx = 0.0, vy = 0.0
    var onGround = false
    init(_ x: Double, _ y: Double, _ w: Int, _ h: Int) { self.x = x; self.y = y; self.w = w; self.h = h }
    var cx: Double { x + Double(w) / 2 }
    var cy: Double { y + Double(h) / 2 }
    func rect() -> IRect { IRect(Int(x), Int(y), w, h) }
}

final class SHEnemy: SHBody {
    let kind: Character
    let base: Double
    var face = Bool.random() ? 1 : -1
    var vdir = Bool.random() ? 1.0 : -1.0
    var angry = false
    var think = Double.random(in: 0.5 ... 1.5)
    init(_ kind: Character, _ x: Double, _ y: Double, _ speed: Double) { self.kind = kind; base = speed; super.init(x, y, 12, 13) }
}

final class SHBubble {
    var x, y, vx: Double
    var age = 0.0, life: Double
    var enemy: SHEnemy?
    let seed = Double.random(in: 0 ..< 6.28)
    var popIn: Double?
    var dead = false
    init(_ x: Double, _ y: Double, _ face: Int, _ life: Double) { self.x = x; self.y = y; vx = Double(face) * 230; self.life = life }
}

final class SHFruit: SHBody {
    let kind: Int, value: Int
    var life = 9.0
    init(fruitAt x: Double, _ y: Double, kind: Int, value: Int) {
        self.kind = kind; self.value = value
        super.init(x, y, 8, 8)
        vx = Double.random(in: -40 ... 40); vy = -140
    }
}

final class SoapHop: GameScene {
    override var music: String? { "soap" }
    override var buttons: [Action: String] { [.a: "JUMP", .b: "BUBBLE"] }
    var lives: Int, spd: Double, trapTime: Double, stage: Int
    var map: [[Character]] = [], levelName = "", theme: [String] = [], loop = 0
    var enemies: [SHEnemy] = [], bubbles: [SHBubble] = [], fruits: [SHFruit] = []
    var start = (0.0, 0.0)
    var player = SHBody(0, 0, 12, 14)
    var face = 1, inv = 2.0, shootCd = 0.0, coyote = 0.0, jumpBuf = 0.0
    var state = "intro", stateT = 0.0, levelT = 0.0, hurry = false
    var chain = 0, chainT = 0.0
    var field = Surface(W, FIELD_H)

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        spd = SPEEDS[d] ?? 1
        trapTime = ["easy": 9.0, "normal": 7.0, "hard": 5.0][d] ?? 7
        stage = Int(opt["stage"] ?? "1") ?? 1
        super.init(app, info, opt)
        loadStage()
    }

    func loadStage() {
        let lv = GData.soapLevels[(stage - 1) % GData.soapLevels.count]
        loop = (stage - 1) / GData.soapLevels.count
        levelName = lv.name
        theme = GData.soapThemes[(stage - 1) % GData.soapThemes.count]
        enemies = []; bubbles = []; fruits = []
        let speed = spd * (1 + 0.15 * Double(loop))
        var m = lv.map.map { Array($0) }
        for r in 0 ..< m.count {
            for c in 0 ..< m[r].count {
                let ch = m[r][c], x = Double(c * T), y = Double(TOP + r * T)
                if ch == "P" { start = (x, y + Double(T) - 14) } else if ch == "g" || ch == "f" {
                    enemies.append(SHEnemy(ch, x - 2, y + Double(T) - 13, speed))
                }
                if "Pgf".contains(ch) { m[r][c] = "." }
            }
        }
        map = m
        player = SHBody(start.0, start.1, 12, 14)
        face = 1; inv = 2; shootCd = 0; coyote = 0; jumpBuf = 0
        state = "intro"; stateT = 0; levelT = 0; hurry = false; chain = 0; chainT = 0
        renderField()
    }

    func renderField() {
        let blk = theme[0], blkD = theme[1], plat = theme[2], platD = theme[3]
        field = Surface(W, FIELD_H)
        for r in 0 ..< map.count {
            for c in 0 ..< map[r].count {
                let x = c * T, y = r * T
                if map[r][c] == "#" {
                    field.fillRect(col(blkD), x, y, T, T)
                    field.fillRect(col(blk), x, y, T - 1, T - 1)
                    if (r + c) % 2 == 0 { field.fillRect(col("white"), x + 2, y + 2, 1, 1) }
                } else if map[r][c] == "=" {
                    field.fillRect(col(platD), x, y + 1, T, T - 3)
                    field.fillRect(col(plat), x, y, T, 3)
                    field.fillRect(col("white"), x + 1, y, 3, 1)
                }
            }
        }
    }

    func cell(_ px: Double, _ py: Double) -> Character {
        let c = Int(floor(px / Double(T))), r = Int(floor((py - Double(TOP)) / Double(T)))
        if r < 0 || r >= ROWS { return "." }
        if c < 0 || c >= COLS { return "#" }
        return map[r][c]
    }

    @discardableResult
    func move(_ b: SHBody, _ dt: Double, gravity: Bool = true) -> Bool {
        if gravity { b.vy = min(b.vy + GRAV * dt, 270) }
        var hitWall = false
        b.x += b.vx * dt
        for yy in [b.y + 1, b.y + Double(b.h) / 2, b.y + Double(b.h) - 1] {
            if b.vx > 0 && cell(b.x + Double(b.w), yy) == "#" {
                b.x = floor((b.x + Double(b.w)) / Double(T)) * Double(T) - Double(b.w) - 0.01; hitWall = true
            } else if b.vx < 0 && cell(b.x, yy) == "#" {
                b.x = (floor(b.x / Double(T)) + 1) * Double(T) + 0.01; hitWall = true
            }
        }
        let prevBottom = b.y + Double(b.h)
        b.y += b.vy * dt
        b.onGround = false
        let xs = [b.x + 1, b.x + Double(b.w) / 2, b.x + Double(b.w) - 1]
        if b.vy >= 0 {
            let bottom = b.y + Double(b.h)
            for xx in xs {
                let ch = cell(xx, bottom)
                let rowTop = Double(TOP) + floor((bottom - Double(TOP)) / Double(T)) * Double(T)
                if ch == "#" || (ch == "=" && prevBottom <= rowTop + 1) {
                    b.y = rowTop - Double(b.h); b.vy = 0; b.onGround = true; break
                }
            }
        } else {
            for xx in xs where cell(xx, b.y) == "#" {
                b.y = Double(TOP) + (floor((b.y - Double(TOP)) / Double(T)) + 1) * Double(T); b.vy = 0; break
            }
        }
        if b.y > Double(TOP + FIELD_H) { b.y -= Double(FIELD_H) } else if b.y + Double(b.h) < Double(TOP) { b.y += Double(FIELD_H) }
        return hitWall
    }

    // ------------------------------------------------------------------ update
    override func tick(_ dt: Double) {
        stateT += dt
        let au = app.audio
        if state == "intro" && stateT > 1.4 { state = "play"; stateT = 0 }
        if ["intro", "play", "clear"].contains(state) { updatePlayer(dt) }
        if state == "dead" && stateT > 1.2 {
            if lives <= 0 { endGame(false, "STAGE \(stage)"); return }
            player = SHBody(start.0, start.1, 12, 14); inv = 2.5; state = "play"; stateT = 0
        }
        if state == "play" {
            levelT += dt
            if levelT > 50 && !hurry { hurry = true; au.play("hurt"); enemies.forEach { $0.angry = true } }
        }
        updateEnemies(dt)
        updateBubbles(dt)
        updateFruits(dt)
        chainT -= dt
        if state == "play" && enemies.isEmpty && !bubbles.contains(where: { $0.enemy != nil }) {
            state = "clear"; stateT = 0
            au.play("levelup")
            add(1000 + max(0, Int((60 - levelT) * 50)), Double(W / 2), Double(TOP + 70), "mint")
        }
        if state == "clear" && stateT > 3 { stage += 1; loadStage() }
    }

    func updatePlayer(_ dt: Double) {
        let inp = app.input, au = app.audio, p = player
        inv = max(0, inv - dt)
        shootCd -= dt
        let mv = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        p.vx = Double(mv) * RUN
        if mv != 0 { face = mv }
        coyote = p.onGround ? 0.09 : coyote - dt
        jumpBuf = inp.hit(.a) ? 0.12 : jumpBuf - dt
        if jumpBuf > 0 && coyote > 0 { p.vy = -JUMP; jumpBuf = 0; coyote = 0; au.play("jump") }
        if p.vy < 0 && !inp.down(.a) { p.vy *= 0.85 }
        move(p, dt)
        if inp.hit(.b) && shootCd <= 0 && bubbles.count < 7 {
            shootCd = 0.28
            bubbles.append(SHBubble(p.cx + Double(face * 6), p.cy - 1, face, 6.5))
            au.play("bubble")
        }
    }

    func updateEnemies(_ dt: Double) {
        let p = player
        for e in enemies {
            let sp = e.base * (e.angry ? 1.7 : 1.0)
            if e.kind == "g" {
                e.vx = Double(e.face) * 32 * sp
                if move(e, dt) { e.face *= -1 }
                if e.onGround {
                    let ahead = cell(e.cx + Double(e.face * 8), e.y + Double(e.h) + 2)
                    e.think -= dt
                    if ahead == "." && Double.random(in: 0 ..< 1) < 0.5 * dt * 10 { e.face *= -1 }
                    if e.think <= 0 {
                        e.think = Double.random(in: 0.8 ... 2.0)
                        if p.y + Double(p.h) < e.y - 4 && Double.random(in: 0 ..< 1) < 0.55 { e.vy = -JUMP * 0.95 }
                        else if Double.random(in: 0 ..< 1) < 0.25 { e.face = p.cx > e.cx ? 1 : -1 }
                    }
                }
            } else {
                e.vx = Double(e.face) * 30 * sp
                e.vy = e.vdir * 22 * sp
                let nx = e.x + e.vx * dt, ny = e.y + e.vy * dt
                if cell(nx + (e.vx > 0 ? Double(e.w) : 0), e.cy) == "#" { e.face *= -1 } else { e.x = nx }
                if cell(e.cx, ny + (e.vy > 0 ? Double(e.h) : 0)) == "#" || ny < Double(TOP + 2) || ny + Double(e.h) > Double(TOP + FIELD_H - 2) {
                    e.vdir *= -1
                } else { e.y = ny }
            }
            if state == "play" && inv <= 0 && e.rect().inflate(-3, -3).intersects(p.rect()) { hurt() }
        }
    }

    func hurt() {
        lives -= 1
        state = "dead"; stateT = 0
        app.audio.play("hurt")
        app.shake(3, 0.3)
        parts.burst(player.cx, player.cy, 20, ["white", "pink", "hotpink"], 80, 0.8)
    }

    func updateBubbles(_ dt: Double) {
        let p = player, au = app.audio
        for b in bubbles where !b.dead {
            b.age += dt; b.life -= dt
            if let pi = b.popIn {
                b.popIn = pi - dt
                if b.popIn! <= 0 { pop(b) }
                continue
            }
            if b.age < FAST_PHASE {
                b.x += b.vx * dt
                b.vx *= 0.92
                if cell(b.x + (b.vx > 0 ? 7 : -7), b.y) == "#" { b.age = FAST_PHASE }
                if b.enemy == nil, let idx = enemies.firstIndex(where: { abs($0.cx - b.x) < 11 && abs($0.cy - b.y) < 11 }) {
                    b.enemy = enemies[idx]; b.life = trapTime
                    enemies.remove(at: idx)
                    add(50); au.play("trap")
                }
            } else {
                let rise = b.enemy != nil ? 18.0 : 22.0
                b.y -= rise * dt
                b.x += sin(t * 2 + b.seed) * 8 * dt
                if cell(b.x, b.y - 8) == "#" { b.y += rise * dt }
                if b.y < Double(TOP - 8) { b.y += Double(FIELD_H) }
                b.x = max(Double(T * 2 + 8), min(Double(W - T * 2 - 8), b.x))
                if state != "dead" && hypot(p.cx - b.x, p.cy - b.y) < 12 {
                    if p.vy > 0 && p.y + Double(p.h) < b.y && app.input.down(.a) { p.vy = -JUMP * 0.95; au.play("jump") } else { pop(b) }
                }
            }
            if b.life <= 0 && !b.dead {
                if let e = b.enemy {
                    e.x = b.x - Double(e.w) / 2; e.y = b.y - Double(e.h) / 2; e.angry = true
                    enemies.append(e); b.enemy = nil
                }
                pop(b, quiet: true)
            }
        }
        for (i, a) in bubbles.enumerated() {
            for b2 in bubbles[(i + 1)...] {
                let dx = b2.x - a.x, dy = b2.y - a.y, d = hypot(dx, dy)
                if d > 0 && d < 13 && a.age > FAST_PHASE && b2.age > FAST_PHASE {
                    let push = (13 - d) * 0.5
                    a.x -= dx / d * push; a.y -= dy / d * push; b2.x += dx / d * push; b2.y += dy / d * push
                }
            }
        }
        bubbles.removeAll { $0.dead }
    }

    func pop(_ b: SHBubble, quiet: Bool = false) {
        if b.dead { return }
        b.dead = true
        let au = app.audio
        parts.burst(b.x, b.y, 8, ["white", "sky", "lavender"], 50, 0.4)
        if b.enemy != nil {
            chain = chainT > 0 ? chain + 1 : 1
            chainT = 0.5
            let pts = min(8000, 500 * (1 << (chain - 1)))
            add(pts, b.x, b.y - 10, chain < 2 ? "yellow" : "mint")
            let kind = (stage - 1) % 8
            fruits.append(SHFruit(fruitAt: b.x - 4, b.y - 4, kind: kind, value: 100 * (kind + 1)))
            au.play("pop")
            app.shake(1.5, 0.12)
            for o in bubbles where o.enemy != nil && o.popIn == nil && !o.dead && hypot(o.x - b.x, o.y - b.y) < 24 { o.popIn = 0.09 }
        } else if !quiet {
            add(10); au.play("pop")
        }
    }

    func updateFruits(_ dt: Double) {
        let p = player
        for f in fruits {
            f.life -= dt
            f.vx *= 0.98
            move(f, dt)
            if f.onGround { f.vx = 0 }
            if state != "dead" && f.rect().intersects(p.rect()) {
                f.life = -1
                add(f.value, f.cx, f.y - 6, "peach")
                app.audio.play("fruit")
                parts.burst(f.cx, f.cy, 6, ["yellow", "white"], 40, 0.4)
            }
        }
        fruits.removeAll { $0.life <= 0 }
    }

    // ------------------------------------------------------------------ draw
    override func render(_ s: Surface) {
        var y = 0
        while y < H { s.fillRect(lerpCol(theme[4], theme[5], Double(y) / Double(H)), 0, y, W, 4); y += 4 }
        for i in 0 ..< 12 {
            let x = (Double(i * 53) + t * Double(4 + i % 3)).truncatingRemainder(dividingBy: Double(W))
            s.circle(col("ink"), Int(x), TOP + (i * 37) % FIELD_H, 2 + i % 3)
        }
        s.blit(field, 0, TOP)
        for f in fruits where f.life > 2 || Int(f.life * 10) % 2 == 1 { Cute.fruit(s, f.kind, Int(f.x), Int(f.y)) }
        for e in enemies {
            if e.kind == "g" { Cute.grump(s, Int(e.x) - 2, Int(e.y) - 2, t, flip: e.face < 0, angry: e.angry) }
            else { Cute.flutter(s, Int(e.x) - 2, Int(e.y) - 2, t, flip: e.face < 0, angry: e.angry) }
        }
        for b in bubbles {
            if let e = b.enemy {
                if e.kind == "g" { Cute.grump(s, Int(b.x) - 8, Int(b.y) - 8, t, angry: b.life < 2, trapped: true) }
                else { Cute.flutter(s, Int(b.x) - 8, Int(b.y) - 8, t, angry: b.life < 2, trapped: true) }
                bubble(s, b.x, b.y, 10, t, tint: b.life < 2 && Int(b.life * 8) % 2 == 1 ? "red" : "lavender")
            } else {
                bubble(s, b.x, b.y, b.age < FAST_PHASE ? 7 : 8, t)
            }
        }
        let p = player
        if state != "dead" && (inv <= 0 || Int(inv * 12) % 2 == 0) {
            let img: Surface
            if !p.onGround { img = sprite("momo_jump", 0, flip: face < 0) }
            else if abs(p.vx) > 1 { img = sprite("momo_walk", Int(t * 10), flip: face < 0) }
            else { img = sprite("momo_idle", Int(t * 2), flip: face < 0) }
            s.blit(img, Int(p.x) - 2, Int(p.y) - 1)
        }
        parts.draw(s)
        floats.draw(s)
        s.fillRect(col("black"), 0, 0, W, TOP)
        drawText(s, String(format: "%07d", score), 4, 3, "white", shadow: nil)
        drawText(s, String(format: "HI %07d", max(best, score)), W / 2, 3, "lavender", align: .center, shadow: nil)
        drawText(s, "STAGE \(stage)", W - 4, 3, "yellow", align: .right, shadow: nil)
        hearts(s, 54, 3, lives)
        if state == "intro" { banner(s, "STAGE \(stage)", levelName) }
        else if state == "clear" { banner(s, "SPARKLING CLEAN!", "STAGE CLEAR", "mint") }
        else if hurry && levelT < 52.5 && Int(t * 6) % 2 == 1 {
            drawText(s, "HURRY!", W / 2, 90, "red", scale: 2, align: .center, outline: "black")
        }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("deep"))
        let w = s.w, h = s.h
        var x = 0
        while x < w { s.fillRect(col("pink"), x, h - 8, 7, 7); x += 8 }
        s.fillRect(col("cream"), 10, h - 30, 40, 3)
        s.blit(sprite("momo_walk", Int(t * 8)), 16 + Int(sin(t) * 10), h - 24)
        let rise = (t * 6).truncatingRemainder(dividingBy: 10)
        bubble(s, Double(w - 30) + sin(t * 2) * 3, Double(h - 36) - rise, 9, t)
        Cute.grump(s, w - 38, h - 44 - Int(rise), t, trapped: true)
        Cute.grump(s, w - 26, h - 24, t, flip: true)
    }
}
