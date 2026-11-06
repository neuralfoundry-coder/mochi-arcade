// JELLY STACK - falling-block puzzle with wobbly jellies (port of games/jelly_stack.py).
import Foundation

private let BW = 10, BH = 20, CELL = 9
private let BX = (W - BW * CELL) / 2, BY = 12
private let LINE_PTS = [1: 100, 2: 300, 3: 500, 4: 800]

final class JSPiece {
    let kind: String
    var rot = 0, x = 3, y: Int
    init(_ kind: String) { self.kind = kind; y = kind == "I" ? -2 : -1 }
    func cells(_ x: Int? = nil, _ y: Int? = nil, _ rot: Int? = nil) -> [(Int, Int)] {
        let xx = x ?? self.x, yy = y ?? self.y, r = rot ?? self.rot
        return GData.jellyRot[kind]![r].map { (xx + $0.0, yy + $0.1) }
    }
}

final class JellyStack: GameScene {
    override var music: String? { "jelly" }
    override var buttons: [Action: String] { [.a: "ROT L", .b: "ROT R", .x: "HOLD", .y: "DROP"] }
    let mode: String, ghost: Bool, startLevel: Int
    var level: Int
    var grid = [[String?]](repeating: [String?](repeating: nil, count: BW), count: BH)
    var wob = [[Double]](repeating: [Double](repeating: 0, count: BW), count: BH)
    var bag: [String] = []
    var queue: [String] = []
    var hold: String?
    var holdUsed = false
    var lines = 0, combo = -1
    var b2b = false
    var clearing: ([Int], Double)?
    var dasDir = 0, dasT = 0.0, arrT = 0.0
    var time = 0.0
    var message = "", messageT = 0.0
    var cur = JSPiece("T")
    var fallT = 0.0, lockT = 0.0, lockResets = 0

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        mode = opt["mode"] ?? "marathon"
        startLevel = Int(opt["level"] ?? "1") ?? 1
        level = startLevel
        ghost = (opt["ghost"] ?? "true") == "true"
        super.init(app, info, opt)
        queue = (0 ..< 4).map { _ in nextKind() }
        spawn()
    }

    func nextKind() -> String {
        if bag.isEmpty { bag = GData.jellyKinds.shuffled() }
        return bag.removeLast()
    }

    func gravity() -> Double {
        let lv = Double(min(level, 20))
        return max(0.016, pow(0.8 - (lv - 1) * 0.007, lv - 1))
    }

    func spawn(_ kind: String? = nil) {
        var k = kind
        if k == nil { k = queue.removeFirst(); queue.append(nextKind()) }
        cur = JSPiece(k!)
        fallT = 0; lockT = 0; lockResets = 0
        if !fits(cur.cells()) { app.audio.play("die"); endGame(false, "\(lines) LINES") }
    }

    func fits(_ cells: [(Int, Int)]) -> Bool {
        for (x, y) in cells {
            if x < 0 || x >= BW || y >= BH { return false }
            if y >= 0 && grid[y][x] != nil { return false }
        }
        return true
    }

    func grounded() -> Bool { !fits(cur.cells(nil, cur.y + 1)) }

    @discardableResult
    func tryMove(_ dx: Int, _ dy: Int) -> Bool {
        if fits(cur.cells(cur.x + dx, cur.y + dy)) {
            cur.x += dx; cur.y += dy
            if dx != 0 && grounded() && lockResets < 15 { lockT = 0; lockResets += 1 }
            return true
        }
        return false
    }

    func rotate(_ d: Int) {
        let a = cur.rot, b = (cur.rot + d + 4) % 4
        let table = cur.kind == "I" ? GData.jellyKicksI : GData.jellyKicks
        for (kx, ky) in table[a * 10 + b] ?? [(0, 0)] where fits(cur.cells(cur.x + kx, cur.y - ky, b)) {
            cur.x += kx; cur.y -= ky; cur.rot = b
            if grounded() && lockResets < 15 { lockT = 0; lockResets += 1 }
            app.audio.play("rotate")
            return
        }
    }

    func say(_ m: String) { message = m; messageT = 1.2 }

    func lock() {
        for (x, y) in cur.cells() {
            if y < 0 { app.audio.play("die"); endGame(false, "\(lines) LINES"); return }
            grid[y][x] = GData.jellyColors[cur.kind]
            wob[y][x] = 1
        }
        app.audio.play("lock")
        let full = (0 ..< BH).filter { y in grid[y].allSatisfy { $0 != nil } }
        if !full.isEmpty {
            clearing = (full, 0.32)
            let n = full.count
            var pts = (LINE_PTS[n] ?? 0) * level
            if n == 4 {
                if b2b { pts = pts * 3 / 2 }
                b2b = true
                app.audio.play("quad"); app.shake(3, 0.3); say("JELLY PARTY!")
            } else {
                b2b = false
                app.audio.play("line")
                if n == 3 { say("TRIPLE!") }
            }
            combo += 1
            if combo > 0 { pts += 50 * combo * level; say("COMBO x\(combo + 1)") }
            add(pts, Double(BX + BW * CELL / 2), Double(BY + full[0] * CELL), "mint")
            for y in full {
                for x in 0 ..< BW { parts.burst(Double(BX + x * CELL + 4), Double(BY + y * CELL + 4), 3, [grid[y][x] ?? "white", "white"], 60, 0.6) }
            }
        } else {
            combo = -1
            spawn()
        }
        holdUsed = false
    }

    func finishClear() {
        guard let (rows, _) = clearing else { return }
        for y in rows.sorted(by: >) { grid.remove(at: y); wob.remove(at: y) }
        for _ in rows {
            grid.insert([String?](repeating: nil, count: BW), at: 0)
            wob.insert([Double](repeating: 0, count: BW), at: 0)
        }
        for y in 0 ..< BH { for x in 0 ..< BW where grid[y][x] != nil { wob[y][x] = max(wob[y][x], 0.6) } }
        lines += rows.count
        clearing = nil
        let newLevel = max(level, startLevel + lines / 10)
        if newLevel > level && mode != "sprint" { level = newLevel; app.audio.play("levelup"); say("LEVEL \(level)") }
        if mode == "sprint" && lines >= 40 {
            score = max(1, Int(100000 - time * 300))
            endGame(true, String(format: "%.1f SEC", time)); return
        }
        if mode == "marathon" && lines >= 150 { endGame(true, "150 LINES!"); return }
        spawn()
    }

    override func tick(_ dt: Double) {
        let inp = app.input
        time += dt
        messageT -= dt
        for y in 0 ..< BH { for x in 0 ..< BW where wob[y][x] > 0 { wob[y][x] = max(0, wob[y][x] - dt * 2.5) } }
        if var c = clearing {
            c.1 -= dt
            clearing = c
            if c.1 <= 0 { finishClear() }
            return
        }
        if ending != nil { return }
        if inp.hit(.x) && !holdUsed {
            app.audio.play("hold")
            let k = cur.kind
            if let h = hold { spawn(h) } else { spawn() }
            hold = k; holdUsed = true
            return
        }
        if inp.hit(.y) || inp.spaceKey {
            var n = 0
            while tryMove(0, 1) { n += 1 }
            add(n * 2)
            parts.burst(Double(BX) + (Double(cur.x) + 1.5) * Double(CELL), Double(BY + (cur.y + 2) * CELL), 6, ["white", "lavender"], 40, 0.3)
            lock()
            return
        }
        if inp.hit(.up, .b) { rotate(1) } else if inp.hit(.a) && !inp.spaceKey { rotate(-1) }
        let d = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        if d != dasDir {
            dasDir = d; dasT = 0; arrT = 0
            if d != 0 && tryMove(d, 0) { app.audio.play("move") }
        } else if d != 0 {
            dasT += dt
            if dasT > 0.167 {
                arrT += dt
                while arrT >= 0.033 { arrT -= 0.033; if !tryMove(d, 0) { break } }
            }
        }
        var g = gravity()
        if inp.down(.down) { g = min(g, 0.03) }
        fallT += dt
        while fallT >= g {
            fallT -= g
            if tryMove(0, 1) { if inp.down(.down) { add(1) } } else { fallT = 0; break }
        }
        if grounded() { lockT += dt; if lockT >= 0.5 { lock() } } else { lockT = 0 }
    }

    // ------------------------------------------------------------------ draw
    func drawCells(_ s: Surface, _ kind: String, _ cells: [(Int, Int)], ghost: Bool = false) {
        for (x, y) in cells where y >= 0 {
            Cute.jellyCell(s, BX + x * CELL, BY + y * CELL, CELL, GData.jellyColors[kind]!, t, face: true, ghost: ghost)
        }
    }

    func mini(_ s: Surface, _ kind: String, _ cx: Int, _ cy: Int) {
        let cells = GData.jellyRot[kind]![0]
        let xs = cells.map { $0.0 }, ys = cells.map { $0.1 }
        let w = (xs.max()! - xs.min()! + 1) * 7, h = (ys.max()! - ys.min()! + 1) * 7
        for (x, y) in cells {
            Cute.jellyCell(s, cx - w / 2 + (x - xs.min()!) * 7, cy - h / 2 + (y - ys.min()!) * 7, 7, GData.jellyColors[kind]!, face: false)
        }
    }

    override func render(_ s: Surface) {
        s.fill(col("ink"))
        for i in 0 ..< 14 {
            let x = (i * 47) % W
            let y = Double(H) - (t * Double(8 + i % 4) * 2 + Double(i * 31)).truncatingRemainder(dividingBy: Double(H + 20))
            s.circle(col("deep"), x, Int(y), 3 + i % 4)
        }
        let bw = BW * CELL, bh = BH * CELL
        panel(s, IRect(BX - 3, BY - 3, bw + 6, bh + 6), fill: "black", border: "lavender", radius: 3)
        for y in 0 ..< BH { for x in 0 ..< BW where (x + y) % 2 == 0 { s.fillRect(col("night"), BX + x * CELL, BY + y * CELL, CELL, CELL) } }
        let clearingRows = Set(clearing?.0 ?? [])
        for y in 0 ..< BH {
            for x in 0 ..< BW {
                guard let c = grid[y][x] else { continue }
                if clearingRows.contains(y) {
                    if Int(clearing!.1 * 20) % 2 == 1 { s.fillRect(col("white"), BX + x * CELL, BY + y * CELL, CELL, CELL) }
                    continue
                }
                Cute.jellyCell(s, BX + x * CELL, BY + y * CELL, CELL, c, t, wobble: sin(t * 30 + Double(x)) * wob[y][x] * 1.5)
            }
        }
        if clearing == nil && ending == nil {
            if ghost {
                var gy = cur.y
                while fits(cur.cells(nil, gy + 1)) { gy += 1 }
                drawCells(s, cur.kind, cur.cells(nil, gy), ghost: true)
            }
            drawCells(s, cur.kind, cur.cells())
        }
        panel(s, IRect(14, 14, 76, 40), fill: "ink", border: "pink")
        drawText(s, "HOLD", 52, 18, "pink", align: .center, shadow: nil)
        if let h = hold { mini(s, h, 52, 40) }
        panel(s, IRect(14, 62, 76, 112), fill: "ink", border: "lavender")
        var rows = [("SCORE", "\(score)"), ("LEVEL", "\(level)"), ("LINES", "\(lines)")]
        rows.append(mode == "sprint" ? ("TIME", String(format: "%.1f", time)) : ("BEST", "\(max(best, score))"))
        for (n, (k, v)) in rows.enumerated() {
            drawText(s, k, 20, 68 + n * 26, "lavender", shadow: nil)
            drawText(s, v, 84, 78 + n * 26, "white", align: .right)
        }
        panel(s, IRect(230, 14, 76, 100), fill: "ink", border: "mint")
        drawText(s, "NEXT", 268, 18, "mint", align: .center, shadow: nil)
        for (n, k) in queue.prefix(3).enumerated() { mini(s, k, 268, 40 + n * 26) }
        drawText(s, ["marathon": "MARATHON", "sprint": "SPRINT 40", "endless": "ENDLESS"][mode] ?? mode, 268, 124, "yellow", align: .center)
        if mode == "sprint" { drawText(s, "\(max(0, 40 - lines)) TO GO", 268, 136, "white", align: .center) }
        parts.draw(s)
        floats.draw(s)
        if messageT > 0 { drawText(s, message, BX + bw / 2, BY + 60, "yellow", align: .center, outline: "black") }
    }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("ink"))
        let h = s.h
        let kinds = ["mint", "pink", "yellow", "sky", "lavender", "lime", "peach"]
        for y in 0 ..< 4 {
            for x in 0 ..< 10 where (x * 7 + y * 3) % 5 != 0 {
                Cute.jellyCell(s, 2 + x * 9, h - 9 - y * 9, 9, kinds[(x + y) % 7], t, wobble: sin(t * 6 + Double(x)))
            }
        }
        let py = Int((t * 20).truncatingRemainder(dividingBy: 30))
        for (cx, cy) in [(4, 0), (5, 0), (6, 0), (5, 1)] { Cute.jellyCell(s, 2 + cx * 9, py + cy * 9, 9, "pink", t) }
    }
}
