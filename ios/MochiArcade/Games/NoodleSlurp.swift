// NOODLE SLURP - snake-style game (port of games/noodle_slurp.py).
import Foundation

private let GW = 32, GH = 20, C = 8
private let OX = (W - GW * C) / 2, OY = 26
private let DIRS: [(Action, (Int, Int))] = [(.up, (0, -1)), (.down, (0, 1)), (.left, (-1, 0)), (.right, (1, 0))]
private let STEP = ["slow": 0.16, "normal": 0.115, "fast": 0.08]

private struct P: Hashable { let x: Int; let y: Int }

private func maze(_ n: Int) -> Set<P> {
    var w = Set<P>()
    func h(_ y: Int, _ x0: Int, _ x1: Int) { for x in x0 ... x1 { w.insert(P(x: x, y: y)) } }
    func v(_ x: Int, _ y0: Int, _ y1: Int) { for y in y0 ... y1 { w.insert(P(x: x, y: y)) } }
    switch n % 4 {
    case 1: h(6, 6, 25); h(13, 6, 25)
    case 2:
        for (x, y, dx, dy) in [(4, 3, 1, 1), (27, 3, -1, 1), (4, 16, 1, -1), (27, 16, -1, -1)] {
            h(y, min(x, x + dx * 6), max(x, x + dx * 6)); v(x, min(y, y + dy * 4), max(y, y + dy * 4))
        }
        h(9, 13, 18); h(10, 13, 18)
    case 3:
        v(15, 2, 7); v(16, 2, 7); v(15, 12, 17); v(16, 12, 17)
        h(9, 3, 11); h(10, 3, 11); h(9, 20, 28); h(10, 20, 28)
    default:
        for x in [8, 23] { v(x, 4, 15) }
        h(4, 12, 19); h(15, 12, 19)
    }
    return w
}

final class NoodleSlurp: GameScene {
    override var music: String? { "noodle" }
    override var buttons: [Action: String] { [:] }
    let mode: String
    let baseStep: Double
    var mazeN = 1
    private var walls = Set<P>()
    private var body: [P] = []
    var dir = (1, 0)
    var queue: [(Int, Int)] = []
    var grow = 0, eaten = 0, levelEaten = 0
    private var food = P(x: 0, y: 0)
    private var gold: P?
    var goldT = 0.0, slurp = 0.0, stepT = 0.0, intro = 1.2
    var dead = false

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        mode = opt["mode"] ?? "classic"
        baseStep = STEP[opt["speed"] ?? "normal"] ?? 0.115
        super.init(app, info, opt)
        resetLevel()
    }

    func resetLevel() {
        walls = mode == "maze" ? maze(mazeN) : []
        var y = GH / 2 + ((mode == "maze" && mazeN % 4 == 1) ? 3 : 0)
        y = min(GH - 2, y)
        body = (0 ..< 4).map { P(x: 8 - $0, y: y) }
        dir = (1, 0); queue = []; grow = 0; stepT = 0; eaten = 0; levelEaten = 0
        food = freeCell(); gold = nil; goldT = 0; slurp = 0; dead = false; intro = 1.2
    }

    private func freeCell() -> P {
        let occ = Set(body).union(walls)
        for _ in 0 ..< 500 {
            let p = P(x: Int.random(in: 0 ..< GW), y: Int.random(in: 0 ..< GH))
            if !occ.contains(p) && p != food { return p }
        }
        return P(x: 0, y: 0)
    }

    func stepTime() -> Double { max(0.05, baseStep - Double(eaten) * 0.0015) }

    override func tick(_ dt: Double) {
        let inp = app.input
        slurp = max(0, slurp - dt)
        if intro > 0 { intro -= dt }
        for (a, d) in DIRS where inp.hit(a) && queue.count < 3 {
            let last = queue.last ?? dir
            if d != last && d != (-last.0, -last.1) { queue.append(d) }
        }
        if gold != nil { goldT -= dt; if goldT <= 0 { gold = nil } }
        if intro > 0 || dead { return }
        stepT += dt
        while stepT >= stepTime() && !dead { stepT -= stepTime(); advance() }
    }

    func advance() {
        let au = app.audio
        if !queue.isEmpty { dir = queue.removeFirst() }
        let head = body[0]
        var nx = head.x + dir.0, ny = head.y + dir.1
        if mode != "classic" { nx = (nx + GW) % GW; ny = (ny + GH) % GH }
        let np = P(x: nx, y: ny)
        let hit = !(0 ..< GW).contains(nx) || !(0 ..< GH).contains(ny) || walls.contains(np) || body.dropLast().contains(np)
        if hit {
            dead = true
            au.play("hurt"); app.shake(3, 0.3)
            for b in body { parts.burst(Double(OX + b.x * C + 4), Double(OY + b.y * C + 4), 2, ["cream", "peach", "white"], 50, 0.8) }
            endGame(false, "LENGTH \(body.count)", delay: 1.8)
            return
        }
        body.insert(np, at: 0)
        if grow > 0 { grow -= 1 } else { body.removeLast() }
        if np == food {
            eaten += 1; levelEaten += 1; grow += 2; slurp = 0.25
            add(10 + 5 * mazeN, Double(OX + nx * C + 4), Double(OY + ny * C - 4))
            au.play("eat")
            food = freeCell()
            if eaten % 5 == 0 && gold == nil { gold = freeCell(); goldT = 6; au.play("bonus") }
            if mode == "maze" && levelEaten >= 12 {
                mazeN += 1
                au.play("levelup")
                add(1000, Double(W / 2), 100, "mint")
                let keep = eaten
                resetLevel()
                eaten = keep
            }
        } else if let g = gold, np == g {
            gold = nil; grow += 4; slurp = 0.4
            add(500, Double(OX + nx * C + 4), Double(OY + ny * C - 4), "mint")
            au.play("bonus")
            parts.burst(Double(OX + nx * C + 4), Double(OY + ny * C + 4), 14, ["yellow", "white", "orange"], 60, 0.7)
        }
    }

    override func render(_ s: Surface) {
        s.fill(col("choco"))
        panel(s, IRect(OX - 3, OY - 3, GW * C + 6, GH * C + 6), fill: "cream", border: "brown", radius: 3)
        for y in 0 ..< GH { for x in 0 ..< GW where (x / 2 + y / 2) % 2 == 0 { s.fillRect(col("peach"), OX + x * C, OY + y * C, C, C) } }
        for wl in walls {
            s.fillRect(col("brown"), OX + wl.x * C, OY + wl.y * C, C, C)
            s.fillRect(col("choco"), OX + wl.x * C + 1, OY + wl.y * C + 1, C - 2, C - 2)
        }
        Cute.dumpling(s, OX + food.x * C, OY + food.y * C - Int(abs(sin(t * 5))), t: t)
        if let g = gold, goldT > 1.5 || Int(t * 10) % 2 == 1 { Cute.dumpling(s, OX + g.x * C, OY + g.y * C, golden: true, t: t) }
        drawNoodle(s)
        parts.draw(s)
        floats.draw(s)
        drawText(s, "SCORE \(score)", 6, 8, "white")
        drawText(s, "BEST \(max(best, score))", W / 2, 8, "cream", align: .center)
        drawText(s, ["classic": "CLASSIC", "wrap": "WRAP", "maze": "MAZE \(mazeN)"][mode] ?? mode, W - 6, 8, "yellow", align: .right)
        if mode == "maze" { drawText(s, "\(12 - levelEaten) TO NEXT", W / 2, H - 10, "cream", align: .center) }
        if intro > 0 && !dead { banner(s, "READY?", "SLURP!", "peach") }
    }

    func drawNoodle(_ s: Surface) {
        let n = body.count
        let cream = col("cream"), peach = col("orange"), k = col("black")
        let pts = body.map { (OX + $0.x * C + 4, OY + $0.y * C + 4) }
        func linked(_ i: Int) -> Bool { abs(pts[i].0 - pts[i - 1].0) <= C && abs(pts[i].1 - pts[i - 1].1) <= C }
        for i in stride(from: n - 1, to: 0, by: -1) where linked(i) { s.line(k, pts[i].0, pts[i].1, pts[i - 1].0, pts[i - 1].1, width: 7) }
        for i in stride(from: n - 1, through: 0, by: -1) { s.circle(k, pts[i].0, pts[i].1, (i < n - 2 ? 3 : 2) + 1) }
        for i in stride(from: n - 1, to: 0, by: -1) where linked(i) { s.line(cream, pts[i].0, pts[i].1, pts[i - 1].0, pts[i - 1].1, width: 5) }
        for i in stride(from: n - 1, through: 0, by: -1) {
            s.circle(cream, pts[i].0, pts[i].1, i < n - 2 ? 3 : 2)
            if i % 3 == 1 { s.fillRect(peach, pts[i].0 - 1, pts[i].1 - 1, 2, 1) }
        }
        let (hx, hy) = pts[0], (dx, dy) = dir
        let hr = 4 + (slurp > 0 ? 1 : 0)
        s.circle(k, hx, hy, hr + 1)
        s.circle(cream, hx, hy, hr)
        if dead { Cute.eyes(s, hx, hy - 1, 2, mood: "sleepy") } else { Cute.eyes(s, hx + dx, hy - 1 + dy, 2, blink: Int(t * 1.3) % 6 == 0) }
        Cute.blush(s, hx, hy + 1, 2)
        if slurp > 0 { s.circle(col("hotpink"), hx + dx * 3, hy + dy * 3 + 1, 1) }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("peach"))
        let w = s.w, h = s.h
        var y = 0
        while y < h { var x = 0; while x < w { if (x / 8 + y / 8) % 2 == 1 { s.fillRect(col("cream"), x, y, 8, 8) }; x += 8 }; y += 8 }
        let pts = (0 ..< 10).map { (10 + $0 * 6, h / 2 + Int(sin(t * 4 + Double($0) * 0.6) * 6)) }
        for i in 0 ..< pts.count - 1 { s.line(col("black"), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: 7) }
        for i in 0 ..< pts.count - 1 { s.line(col("cream"), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: 5) }
        let (hx, hy) = pts.last!
        s.circle(col("black"), hx, hy, 5)
        s.circle(col("cream"), hx, hy, 4)
        Cute.eyes(s, hx + 1, hy - 1, 2)
        Cute.dumpling(s, w - 22, h / 2 - 4, t: t)
        Cute.dumpling(s, w - 40, 10, golden: true, t: t)
    }
}
