// BOUNCE BUN - brick breaker with a bun paddle and snack bricks (port of games/bounce_bun.py).
import Foundation

private let LEFT = 8.0, RIGHT = Double(W - 8), TOP = 20.0
private let BRW = 16, BRH = 8, BX0 = 16, BY0 = 30
private let PADDLE_Y = 182.0
private let KIND: [Character: String] = ["c": "cookie", "p": "candy", "m": "mint", "l": "lemon", "b": "berry", "h": "choco", "t": "tin"]
private let POINTS = ["cookie": 50, "candy": 60, "mint": 70, "lemon": 80, "berry": 90, "choco": 120, "tin": 0]

final class BBBall {
    var x, y, vx, vy: Double
    var stuck: Double?
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double) { self.x = x; self.y = y; self.vx = vx; self.vy = vy }
}

final class BBBrick {
    let rect: IRect, kind: String
    var hp: Int, flash = 0.0
    init(_ rect: IRect, _ kind: String) { self.rect = rect; self.kind = kind; hp = kind == "choco" ? 2 : 1 }
}

final class BounceBun: GameScene {
    override var music: String? { "bounce" }
    override var buttons: [Action: String] { [.a: "GO"] }
    var lives: Int, baseSpeed: Double, level: Int
    var px = Double(W) / 2
    var timers = ["wide": 0.0, "slow": 0.0, "glue": 0.0]
    var levelName = "", loop = 0
    var bricks: [BBBrick] = []
    var caps: [(x: Double, y: Double, k: Character, got: Bool)] = []
    var speed = 0.0
    var balls: [BBBall] = []
    var intro = 1.5

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        baseSpeed = 125 * (SPEEDS[d] ?? 1)
        level = Int(opt["level"] ?? "1") ?? 1
        super.init(app, info, opt)
        loadLevel()
    }

    func loadLevel() {
        let (name, rows) = GData.bounceLevels[(level - 1) % GData.bounceLevels.count]
        levelName = name
        loop = (level - 1) / GData.bounceLevels.count
        bricks = []
        for (r, row) in rows.enumerated() {
            for (c, ch) in row.enumerated() {
                if let k = KIND[ch] { bricks.append(BBBrick(IRect(BX0 + c * BRW, BY0 + r * BRH, BRW, BRH), k)) }
            }
        }
        caps = []
        speed = baseSpeed * (1 + 0.12 * Double(loop))
        resetBall()
        intro = 1.5
    }

    func resetBall() {
        let b = BBBall(px, PADDLE_Y - 4, 0, 0)
        b.stuck = 0
        balls = [b]
        for k in timers.keys { timers[k] = 0 }
    }

    func pw() -> Double { (timers["wide"] ?? 0) > 0 ? 48 : 32 }
    func curSpeed() -> Double { speed * ((timers["slow"] ?? 0) > 0 ? 0.65 : 1) }

    override func tick(_ dt: Double) {
        let inp = app.input, au = app.audio
        intro = max(0, intro - dt)
        for k in timers.keys { timers[k] = max(0, timers[k]! - dt) }
        let d = (inp.down(.right) ? 1.0 : 0) - (inp.down(.left) ? 1.0 : 0)
        let half = pw() / 2
        px = max(LEFT + half, min(RIGHT - half, px + d * 170 * dt))
        for b in balls {
            if let st = b.stuck {
                b.x = px + st; b.y = PADDLE_Y - 4
                if inp.hit(.a) && intro <= 0 {
                    let ang = (-20 + (st / half) * 40) * .pi / 180, sp = curSpeed()
                    b.vx = sin(ang) * sp; b.vy = -cos(ang) * sp; b.stuck = nil
                    au.play("paddle")
                }
            }
        }
        for b in balls where b.stuck == nil { moveBall(b, dt) }
        if balls.contains(where: { $0.y > Double(H + 6) }) {
            balls.removeAll { $0.y > Double(H + 6) }
            if balls.isEmpty {
                lives -= 1
                au.play("hurt"); app.shake(3, 0.3)
                if lives <= 0 { endGame(false, "LEVEL \(level)"); return }
                resetBall()
            }
        }
        for i in caps.indices {
            caps[i].y += 55 * dt
            if caps[i].y >= PADDLE_Y - 2 && caps[i].y <= PADDLE_Y + 6 && abs(caps[i].x - px) < pw() / 2 + 6 {
                caps[i].got = true
                power(caps[i].k)
            }
        }
        caps.removeAll { $0.got || $0.y >= Double(H + 8) }
        for b in bricks { b.flash = max(0, b.flash - dt) }
        if !bricks.contains(where: { $0.kind != "tin" }) {
            au.play("levelup")
            add(2000, Double(W / 2), 100, "mint")
            level += 1
            loadLevel()
        }
    }

    func moveBall(_ b: BBBall, _ dt: Double) {
        let au = app.audio
        let sp = max(hypot(b.vx, b.vy), 1), target = curSpeed()
        b.vx = b.vx / sp * target; b.vy = b.vy / sp * target
        let steps = max(1, Int(target * dt / 3) + 1)
        for _ in 0 ..< steps {
            b.x += b.vx * dt / Double(steps); b.y += b.vy * dt / Double(steps)
            if b.x < LEFT + 2 { b.x = LEFT + 2; b.vx = abs(b.vx); au.play("tin") }
            else if b.x > RIGHT - 2 { b.x = RIGHT - 2; b.vx = -abs(b.vx); au.play("tin") }
            if b.y < TOP + 2 { b.y = TOP + 2; b.vy = abs(b.vy); au.play("tin") }
            let half = pw() / 2
            if b.vy > 0 && PADDLE_Y - 2 <= b.y + 2 && b.y + 2 <= PADDLE_Y + 4 && abs(b.x - px) <= half + 2 {
                let off = max(-1, min(1, (b.x - px) / half)), ang = off * 60 * .pi / 180
                b.vx = sin(ang) * target; b.vy = -cos(ang) * target
                b.y = PADDLE_Y - 3
                au.play("paddle")
                if (timers["glue"] ?? 0) > 0 { b.stuck = b.x - px; return }
            }
            let ball = IRect(Int(b.x) - 2, Int(b.y) - 2, 5, 5)
            if let br = bricks.first(where: { $0.rect.intersects(ball) }) {
                let r = br.rect
                let ox = Double(min(ball.right - r.x, r.right - ball.x)), oy = Double(min(ball.bottom - r.y, r.bottom - ball.y))
                if ox < oy { b.vx = -b.vx; b.x += (ox + 0.5) * (b.vx < 0 ? -1 : 1) } else { b.vy = -b.vy; b.y += (oy + 0.5) * (b.vy < 0 ? -1 : 1) }
                hitBrick(br)
            }
        }
    }

    func hitBrick(_ br: BBBrick) {
        let au = app.audio
        if br.kind == "tin" { br.flash = 0.15; au.play("tin"); return }
        br.hp -= 1
        if br.hp > 0 { br.flash = 0.2; au.play("tin"); return }
        bricks.removeAll { $0 === br }
        let r = br.rect
        add((POINTS[br.kind] ?? 50) * (1 + loop))
        speed = min(baseSpeed * 1.8, speed + 1.5)
        au.play("brick")
        let colors = ["cookie": ["peach", "brown"], "candy": ["pink", "white"], "mint": ["mint", "white"], "lemon": ["yellow", "white"],
                      "berry": ["lavender", "purple"], "choco": ["brown", "choco"]][br.kind] ?? ["white"]
        parts.burst(Double(r.centerx), Double(r.centery), 8, colors, 50, 0.5)
        let roll = Double.random(in: 0 ..< 1)
        if roll < 0.025 { caps.append((x: Double(r.centerx), y: Double(r.centery), k: "+", got: false)) }
        else if roll < 0.14 { caps.append((x: Double(r.centerx), y: Double(r.centery), k: Array("WMSG").randomElement()!, got: false)) }
    }

    func power(_ k: Character) {
        let au = app.audio
        au.play("powerup")
        let name = ["W": "WIDE BUN!", "M": "MULTI BALL!", "S": "SLOW DOWN", "G": "STICKY GLUE", "+": "EXTRA LIFE!"][k] ?? ""
        floats.add(px, PADDLE_Y - 12, name, "mint")
        switch k {
        case "W": timers["wide"] = 15
        case "S": timers["slow"] = 10
        case "G": timers["glue"] = 12
        case "+": lives += 1; au.play("extra")
        case "M":
            let src = balls.filter { $0.stuck == nil }
            let b0 = src.first ?? balls[0]
            for a in [-25.0, 25.0] {
                let base = (b0.vx != 0 || b0.vy != 0) ? atan2(b0.vx, -b0.vy) : 0
                let ang = base + a * .pi / 180, sp = curSpeed()
                balls.append(BBBall(b0.x, b0.y, sin(ang) * sp, -abs(cos(ang) * sp)))
            }
        default: break
        }
        add(100)
    }

    override func render(_ s: Surface) {
        s.fill(col("choco"))
        var y = Int(TOP)
        while y < H {
            var x = 0
            while x < W { if (x / 12 + y / 12) % 2 == 1 { s.fillRect(col("brown"), x, y, 12, 12) }; x += 12 }
            y += 12
        }
        s.fillRect(col("black"), 0, 0, W, Int(TOP))
        s.fillRect(col("peach"), 0, Int(TOP), Int(LEFT), H)
        s.fillRect(col("peach"), Int(RIGHT), Int(TOP), W - Int(RIGHT), H)
        s.fillRect(col("cream"), 0, Int(TOP) - 2, W, 2)
        for br in bricks { if br.flash > 0 { s.fillRect(col("white"), br.rect) } else { Cute.brick(s, br.rect, br.kind, hp: br.hp) } }
        for cap in caps {
            let x = Int(cap.x), y = Int(cap.y)
            let c = ["W": "sky", "M": "pink", "S": "mint", "G": "yellow", "+": "red"][cap.k] ?? "white"
            s.rect(col("black"), IRect(x - 7, y - 4, 14, 8), radius: 3)
            s.rect(col(c), IRect(x - 6, y - 3, 12, 6), radius: 3)
            s.blit(renderText(String(cap.k), col("black")), x - 2, y - 3)
        }
        let w = Int(pw())
        let r = IRect(Int(px - pw() / 2), Int(PADDLE_Y), w, 7)
        s.rect(col("black"), r.inflate(2, 2), radius: 4)
        s.rect(col((timers["glue"] ?? 0) <= 0 ? "peach" : "yellow"), r, radius: 4)
        s.fillRect(col("cream"), r.x + 3, r.y + 1, r.w - 6, 2)
        for i in 0 ..< 3 { s.fillRect(col("choco"), r.x + 6 + i * (r.w - 12) / 2, r.y + 3, 2, 1) }
        Cute.eyes(s, r.centerx, r.y + 3, 3, blink: Int(t * 1.2) % 5 == 0)
        for b in balls {
            s.circle(col("black"), Int(b.x), Int(b.y), 3)
            s.circle(col("hotpink"), Int(b.x), Int(b.y), 2)
            s.fillRect(col("white"), Int(b.x) - 1, Int(b.y) - 1, 1, 1)
        }
        parts.draw(s)
        floats.draw(s)
        drawText(s, String(format: "%07d", score), 4, 6, "white", shadow: nil)
        drawText(s, "LEVEL \(level)", W / 2, 6, "yellow", align: .center, shadow: nil)
        hearts(s, W - 54, 6, lives)
        if intro > 0 { banner(s, "LEVEL \(level)", levelName, "peach") }
        else if balls.contains(where: { $0.stuck != nil }) && Int(t * 3) % 2 == 1 { drawText(s, "PRESS A TO LAUNCH", W / 2, 160, "white", align: .center) }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("choco"))
        let w = s.w, h = s.h
        let kinds = ["cookie", "candy", "mint", "lemon", "berry"]
        for r in 0 ..< 4 { for c in 0 ..< w / 16 where (r + c + Int(t)) % 7 != 0 { Cute.brick(s, IRect(c * 16, 4 + r * 8, 16, 8), kinds[(r + c) % 5]) } }
        let bx = Double(w) / 2 + sin(t * 2) * 30, by = Double(h - 20) - abs(sin(t * 3)) * 26
        s.circle(col("hotpink"), Int(bx), Int(by), 2)
        s.rect(col("peach"), IRect(Int(Double(w) / 2 + sin(t * 2) * 25) - 14, h - 10, 28, 5), radius: 3)
    }
}
