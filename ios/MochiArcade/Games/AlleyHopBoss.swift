// ALLEY HOP bosses (port of mochi_arcade/games/alley_hop_boss.py): one telegraphed attack engine (charge / ring /
// strike / rows / cols / rest) wearing six original costumes - BRUNO, SWEEPO, the GULL GANG, BANDIT COON,
// KING CLAW, HOOTSWORTH - plus BIG BOSS BRUNO on stage 200. Sushi hops onto the boss while it rests.
import Foundation

private let AHB_SIZE: [String: (Int, Int)] = ["bruno": (28, 22), "sweepo": (40, 24), "gulls": (14, 12), "coon": (24, 20),
                                               "claw": (44, 20), "owl": (26, 24), "king": (32, 26)]
private let AHB_EDGE: Set<String> = ["bruno", "sweepo", "owl", "king"]
private let AHB_DIZZY_AFTER_CHARGE: Set<String> = ["bruno", "owl", "king"]
private let AHB_SOLID: Set<String> = ["idle", "move", "tell", "act"]
private let AHB_SHOT_SPEED: [String: Double] = ["ball": 75, "bone": 80, "suds": 55, "jet": 210, "feather": 90, "egg": 105,
                                                 "lid": 85, "can": 62, "bubble": 50, "dart": 130]
private let AHB_UP_SHOTS: Set<String> = ["jet", "bubble"]

struct AHShot { var x, y, vx, vy: Double; let kind: String; var spin: Double }

final class AHBoss {
    unowned let g: AlleyHop
    let kind, name: String
    var hp: Int
    let maxhp: Int
    let sp, restT, tellT: Double
    let atk: [String]
    let nshots: Int
    let rk, ck: String
    let w, h: Int
    var state = "enter"
    var st = 0.0, t = 0.0
    var ai = 0
    var cur = ""
    var face = -1
    var x, y: Double
    var hx, hy: Double                 // where the boss can be bopped while it rests
    var sx = 0.0, sy = 0.0             // strike: start of the leap
    var tx = 0.0, ty = 0.0             // strike target / charge row
    var zone: IRect?                   // strike impact area
    var zoneT = 0.0                    // > 0 while the impact hurts
    var rows: [Int] = [], cols: [Int] = []
    var side = 1                       // volleys from the left (1) or right (-1)
    var ring = -1.0
    var shots: [AHShot] = []
    var flash = 0.0
    let homeX: Double

    init(_ game: AlleyHop, _ spec: AHBossSpec) {
        g = game
        kind = spec.kind; name = spec.name
        hp = spec.hp; maxhp = spec.hp
        sp = spec.sp; restT = spec.rest; tellT = spec.tell
        atk = spec.atk; nshots = spec.n
        rk = spec.rk; ck = spec.ck
        (w, h) = AHB_SIZE[spec.kind] ?? (28, 22)
        x = Double(W + 30); y = Double(ahCY(5))
        if kind == "coon" || kind == "claw" { x = Double(W / 2); y = Double(ahCY(1) - 40) } else if kind == "gulls" { x = Double(W / 2); y = Double(AH_TOP - 30) }
        hx = x; hy = y
        homeX = Double(W - w / 2 - 4)
    }

    // ------------------------------------------------------------------ helpers
    func targetRow() -> Int { max(1, min(9, g.sushi.row)) }
    func targetCol() -> Int { max(0, min(19, ahCol(g.sushiX()))) }

    /// (x, y) the boss returns to after a rest / hurt.
    func home() -> (Double, Double) {
        if AHB_EDGE.contains(kind) {
            let lx = Double(w / 2 + 4), rx = Double(W - w / 2 - 4)
            return (x < Double(W) / 2 ? lx : rx, max(Double(ahCY(1)), min(Double(ahCY(9)), y)))
        }
        if kind == "gulls" { return (Double(W / 2), Double(AH_TOP + 2)) }
        if kind == "claw" { return (Double(W / 2), Double(ahCY(1) - 2)) }
        return (max(40, min(Double(W - 40), x)), Double(ahCY(1) - 2))
    }

    func body() -> (Double, Double, Double, Double)? {
        if kind == "gulls" {
            if cur == "strike" && ["act", "rest", "hurt"].contains(state) { return (hx - 7, hy - 6, 14, 12) }
            return nil
        }
        return (x - Double(w) / 2, y - Double(h) / 2, Double(w), Double(h))
    }

    /// The crab's striking claw - at rest it hangs next to the body.
    func clawPos() -> (Double, Double) {
        if cur == "strike" && ["act", "rest", "hurt", "tell"].contains(state) { return (hx, hy) }
        return (x + 30, y + 10)
    }

    var vulnerable: Bool { state == "rest" }

    func bopRect() -> (Double, Double, Double, Double)? {
        if !vulnerable { return nil }
        if kind == "claw" || kind == "gulls" { return (hx - 10, hy - 10, 20, 20) }
        return (hx - Double(w) / 2 - 3, hy - Double(h) / 2 - 3, Double(w + 6), Double(h + 6))
    }

    func setState(_ s: String) { state = s; st = 0 }

    // ------------------------------------------------------------------ damage tests
    /// Does anything of the boss hit an entity centred at (ex, ey)?
    func hurts(_ ex: Double, _ ey: Double, _ r: Double = 5) -> Bool {
        let ex0 = ex - r, ey0 = ey - r, ex1 = ex + r, ey1 = ey + r
        func over(_ rx: Double, _ ry: Double, _ rw: Double, _ rh: Double, _ inset: Double = 3) -> Bool {
            rx + inset < ex1 && rx + rw - inset > ex0 && ry + inset < ey1 && ry + rh - inset > ey0
        }
        if state == "dead" { return false }
        let b = body()
        var solid = AHB_SOLID.contains(state)
        if kind == "gulls" { solid = cur == "strike" && state == "act" }
        if kind == "claw" {
            solid = !["hurt", "dead", "enter"].contains(state)
            let (cx, cy) = clawPos()
            if cur == "strike" && state == "act" && over(cx - 7, cy - 6, 14, 12, 1) { return true }
        }
        if let b = b, solid, over(b.0, b.1, b.2, b.3) { return true }
        if zoneT > 0, let z = zone, over(Double(z.x), Double(z.y), Double(z.w), Double(z.h), 0) { return true }
        if ring >= 0 {
            let d = ((ex - x) * (ex - x) + (ey - y) * (ey - y)).squareRoot()
            if abs(d - ring) < 7 { return true }
        }
        for sh in shots where abs(sh.x - ex) < 5 + r && abs(sh.y - ey) < 5 + r { return true }
        return false
    }

    /// Sushi bopped the boss while it rested.
    func hit() {
        hp -= 1
        flash = 0.5
        zoneT = 0
        if hp <= 0 {
            setState("dead")
            shots = []
            ring = -1
        } else {
            setState("hurt")
        }
    }

    // ------------------------------------------------------------------ update
    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        zoneT = max(0, zoneT - dt)
        for i in shots.indices {
            shots[i].x += shots[i].vx * dt
            shots[i].y += shots[i].vy * dt
            shots[i].spin += dt
        }
        shots.removeAll { !($0.x > -20 && $0.x < Double(W + 20) && $0.y > -10 && $0.y < 210) }
        if ring >= 0 {
            ring += 120 * sp * dt
            if ring > 100 { ring = -1 }
        }
        st += dt
        switch state {
        case "enter":
            var (hx0, hy0) = home()
            if AHB_EDGE.contains(kind) { hx0 = homeX; hy0 = Double(ahCY(5)) }
            approach(hx0, hy0, 90 * dt)
            if st > 1.6 { setState("idle") }
        case "idle":
            if kind == "coon" {           // the bandit paces along the top alley
                x += sin(t * 1.3) * 40 * dt
                x = max(30, min(Double(W - 30), x))
            }
            if st > max(0.35, 0.9 - 0.12 * sp) { nextAttack() }
        case "move":       // charge: line up with Sushi's row along the edge
            approach(x, ty, 95 * sp * dt)
            if abs(y - ty) < 0.5 || st > 2.5 { setState("tell") }
        case "tell":
            if cur == "strike" && kind == "claw" { hx = x + 30; hy = y + 10 }
            if st > tellT { beginAct() }
        case "act":
            act(dt)
        case "rest":
            if st > restT { setState("ret") }
        case "hurt":
            if st > 0.7 { setState("ret") }
        case "ret":
            if kind == "claw" || kind == "gulls" {
                hx = x + 30; hy = y + 10
                if kind == "gulls" { hx = x; hy = y }
                cur = ""
                setState("idle")
            } else {
                let (hx0, hy0) = home()
                approach(hx0, hy0, 220 * dt)
                hx = x; hy = y
                if (abs(x - hx0) < 1 && abs(y - hy0) < 1) || st > 1.2 {
                    cur = ""
                    setState("idle")
                }
            }
        case "dead":
            y -= 70 * dt
            shots = []
        default:
            break
        }
    }

    func approach(_ tx0: Double, _ ty0: Double, _ step: Double) {
        let dx = tx0 - x, dy = ty0 - y
        let d = (dx * dx + dy * dy).squareRoot()
        if d <= step || d < 0.01 {
            x = tx0; y = ty0
        } else {
            x += dx / d * step
            y += dy / d * step
        }
    }

    func nextAttack() {
        var a = atk[ai % atk.count]
        ai += 1
        cur = a
        if a == "charge" && !AHB_EDGE.contains(kind) { a = "strike"; cur = a }
        if a == "charge" {
            ty = Double(ahCY(targetRow()))
            setState("move")
            return
        }
        if a == "strike" {
            let r = targetRow(), c = targetCol()
            tx = Double(c * AH_CELL + 8); ty = Double(ahCY(r))
            sx = x; sy = y
            if kind == "claw" { sx = x + 30; sy = y + 10 }
            if kind == "gulls" { sx = x; sy = y }
            let (zw, zh): (Int, Int) = ["gulls": (1, 1), "coon": (3, 1), "claw": (2, 2), "owl": (1, 3)][kind] ?? (3, 3)
            let zx = max(0, min(20 - zw, c - zw / 2))
            let zy = max(1, min(10 - zh, r - zh / 2))
            zone = IRect(zx * AH_CELL, AH_TOP + zy * AH_CELL, zw * AH_CELL, zh * AH_CELL)
            if kind == "claw" && zw == 2 {
                tx = Double(zx * AH_CELL + 16)
                ty = Double(AH_TOP + zy * AH_CELL + 16)
            }
            setState("tell")
            g.app.audio.play(ai % 3 == 1 ? "warning" : "move")
            return
        }
        if a == "rows" {
            let rr = targetRow()
            var rs = [rr]
            var k = 0
            while rs.count < min(nshots, 4) && k < 20 {
                k += 1
                let cand = 1 + (rr + 3 * k + ai) % 9
                if rs.allSatisfy({ abs(cand - $0) >= 2 }) { rs.append(cand) }
            }
            rows = rs
            if AHB_EDGE.contains(kind) { side = x < Double(W) / 2 ? 1 : -1 } else { side = ai % 2 == 1 ? 1 : -1 }
            setState("tell")
            return
        }
        if a == "cols" {
            let cc = targetCol()
            var cs = [cc]
            var k = 0
            while cs.count < nshots + 1 && k < 30 {
                k += 1
                let cand = (cc + 5 * k + ai * 3) % 20
                if cs.allSatisfy({ abs(cand - $0) >= 2 }) { cs.append(cand) }
            }
            cols = cs
            setState("tell")
            return
        }
        if a == "ring" {
            setState("tell")
            return
        }
        // rest: busy refilling / digging - a free bop
        hx = x; hy = y
        setState("rest")
        g.app.audio.play("hold")
    }

    func beginAct() {
        let au = g.app.audio
        switch cur {
        case "charge":
            face = x < Double(W) / 2 ? 1 : -1
            au.play(kind == "sweepo" ? "boom" : "jump")
        case "ring":
            ring = 4
            au.play("explode")
            g.app.shake(2, 0.2)
        case "rows":
            for r in rows {
                let x0 = side > 0 ? -8.0 : Double(W + 8)
                let v = (AHB_SHOT_SPEED[rk] ?? 80) * sp * 0.85
                shots.append(AHShot(x: x0, y: Double(ahCY(r)), vx: v * Double(side), vy: 0, kind: rk, spin: 0))
            }
            au.play("shoot")
            setState("idle")
            return
        case "cols":
            let up = AHB_UP_SHOTS.contains(ck)
            for c in cols {
                let v = (AHB_SHOT_SPEED[ck] ?? 80) * sp * 0.85
                let y0 = up ? Double(AH_TOP + 11 * AH_CELL + 6) : Double(AH_TOP + 4)
                shots.append(AHShot(x: Double(c * AH_CELL + 8), y: y0, vx: 0, vy: up ? -v : v, kind: ck, spin: 0))
            }
            au.play("shoot")
            setState("idle")
            return
        case "strike":
            au.play("jump")
        default:
            break
        }
        setState("act")
    }

    func act(_ dt: Double) {
        switch cur {
        case "charge":
            x += Double(face) * 215 * sp * dt
            let lx = Double(w / 2 + 4), rx = Double(W - w / 2 - 4)
            if kind == "sweepo" { g.wetCell(ty, x) }
            if x <= lx || x >= rx {
                x = max(lx, min(rx, x))
                g.app.shake(3, 0.25)
                g.app.audio.play("tin")
                if AHB_DIZZY_AFTER_CHARGE.contains(kind) {
                    hx = x; hy = y
                    setState("rest")
                } else {
                    cur = ""
                    setState("idle")
                }
            }
        case "ring":
            if ring < 0 || st > 1.2 {
                ring = -1
                setState("idle")
            }
        case "strike":
            let dur = 0.36
            let p = min(1, st / dur)
            let nhx = sx + (tx - sx) * p
            let nhy = sy + (ty - sy) * p - sin(Double.pi * p) * 26
            hx = nhx; hy = nhy
            if kind != "claw" && kind != "gulls" { x = nhx; y = nhy }
            if p >= 1 {
                hx = tx; hy = ty
                if kind != "claw" && kind != "gulls" { x = tx; y = ty }
                zoneT = 0.14
                g.app.shake(3, 0.2)
                g.app.audio.play(kind == "bruno" || kind == "king" ? "boom" : "pop")
                g.parts.burst(tx, ty + 4, 10, ["white", "gray", "cream"], 50, 0.4)
                setState("rest")
            }
        default:
            break
        }
    }

    // ------------------------------------------------------------------ drawing
    /// Telegraphs (drawn above the lanes, under the HUD).
    func drawTells(_ s: Surface, _ t: Double) {
        let blink = Int(t * 8) % 2 == 1
        if state == "tell" && cur == "charge" {
            let r = Int(floor((ty - Double(AH_TOP)) / Double(AH_CELL)))
            let y0 = AH_TOP + r * AH_CELL
            let d = x < Double(W) / 2 ? 1 : -1
            for k in 0 ..< 8 {
                let cx = Int(x) + d * (28 + k * 34 + Int(t * 60) % 34)
                if cx >= 0 && cx < W {
                    let pts: [(Double, Double)] = [(Double(cx - 4 * d), Double(y0 + 3)), (Double(cx + 3 * d), Double(y0 + 8)),
                                                   (Double(cx - 4 * d), Double(y0 + 13))]
                    s.polygon(col(blink ? "red" : "orange"), pts)
                }
            }
        }
        if state == "tell" && cur == "strike", let z = zone {
            let p = min(1, st / max(0.1, tellT))
            let rw = Int(4 + 10 * p)
            s.ellipse(col("black"), Int(tx) - rw, Int(ty) + 2, rw * 2, max(2, rw / 2 + 1))
            if blink { s.rect(col("red"), z, width: 1) }
        }
        if state == "tell" && cur == "rows" {
            for r in rows {
                let yy = ahCY(r)
                let xx = side > 0 ? 4 : W - 12
                if blink {
                    drawText(s, side > 0 ? "}}" : "{{", side > 0 ? xx : xx - 6, yy - 3, "red", shadow: "black")
                }
            }
        }
        if state == "tell" && cur == "cols" {
            let up = AHB_UP_SHOTS.contains(ck)
            for c in cols {
                let xx = c * AH_CELL + 8
                if blink {
                    drawText(s, up ? "|" : "`", xx - 2, up ? AH_TOP + 10 * AH_CELL + 4 : AH_TOP + 2, "red", shadow: "black")
                }
                s.fillRect(col("red"), xx, AH_TOP + 16, 1, 10 * AH_CELL - 16)
            }
        }
        if state == "tell" && cur == "ring" && blink { s.circle(col("red"), Int(x), Int(y), 22, width: 1) }
        if ring >= 0 {
            let r = Int(ring)
            s.circle(col("yellow"), Int(x), Int(y), r, width: 2)
            if r > 8 { s.circle(col("white"), Int(x), Int(y), r - 5, width: 1) }
        }
        if zoneT > 0, let z = zone { s.rect(col("white"), z, width: 2) }
    }

    func drawShots(_ s: Surface, _ t: Double) {
        for sh in shots {
            let xi = Int(sh.x), yi = Int(sh.y)
            switch sh.kind {
            case "ball":
                s.circle(col("black"), xi, yi, 5)
                s.circle(col("lime"), xi, yi, 4)
                let a = sh.spin * 10
                s.fillRect(col("white"), xi + Int(cos(a) * 2), yi + Int(sin(a) * 2), 1, 1)
            case "bone":
                s.fillRect(col("black"), xi - 6, yi - 2, 12, 5)
                s.fillRect(col("white"), xi - 5, yi - 1, 10, 3)
                for bx in [xi - 6, xi + 4] {
                    s.circle(col("white"), bx + 1, yi - 2, 2)
                    s.circle(col("white"), bx + 1, yi + 2, 2)
                }
            case "suds", "bubble":
                s.circle(col("sky"), xi, yi, 5, width: 1)
                s.circle(col("white"), xi - 2, yi - 2, 1)
                s.circle(col("sky"), xi + 4, yi + 3, 2, width: 1)
            case "jet":
                s.fillRect(col("sky"), xi - 2, yi - 2, 5, 20)
                s.fillRect(col("white"), xi - 1, yi - 4, 3, 22)
            case "feather", "dart":
                let c = sh.kind == "dart" ? "lavender" : "white"
                if sh.vy != 0 {
                    s.fillRect(col("black"), xi - 2, yi - 6, 5, 12)
                    s.fillRect(col(c), xi - 1, yi - 5, 3, 10)
                    s.fillRect(col(sh.kind == "dart" ? "purple" : "gray"), xi, yi - 5, 1, 10)
                } else {
                    s.fillRect(col("black"), xi - 6, yi - 2, 12, 5)
                    s.fillRect(col(c), xi - 5, yi - 1, 10, 3)
                    s.fillRect(col("gray"), xi - 5, yi, 10, 1)
                }
            case "egg":
                s.ellipse(col("black"), xi - 4, yi - 5, 9, 11)
                s.ellipse(col("white"), xi - 3, yi - 4, 7, 9)
                s.fillRect(col("sky"), xi - 1, yi - 2, 1, 2)
            case "lid":
                let lw = max(1, Int(abs(cos(sh.spin * 8)) * 6))
                s.ellipse(col("black"), xi - lw - 1, yi - 6, lw * 2 + 3, 13)
                s.ellipse(col("gray"), xi - lw, yi - 5, lw * 2 + 1, 11)
                s.fillRect(col("white"), xi, yi - 4, 1, 3)
            case "can":
                AHArt.can(s, xi - 7, yi - 8, 1, t, "teal")
            default:
                break
            }
        }
    }

    func draw(_ s: Surface, _ t: Double) {
        if state == "dead" && y < -40 { return }
        var hurt = flash > 0 && Int(t * 20) % 2 == 1
        let dizzy = state == "rest"
        let angry = ["tell", "act", "move"].contains(state)
        let xi = Int(x), yi = Int(y)
        if state == "dead" { hurt = Int(t * 10) % 2 == 1 }
        switch kind {
        case "bruno", "king":
            AHBoss.dog(s, xi, yi, t, face, angry, dizzy, hurt, kind == "king", state == "act")
        case "sweepo":
            AHBoss.sweeper(s, xi, yi, t, state == "act" ? face : (Double(xi) < Double(W) / 2 ? 1 : -1), angry, dizzy, hurt)
        case "coon":
            AHBoss.coon(s, xi, yi, t, angry, dizzy, hurt)
        case "owl":
            AHBoss.owl(s, xi, yi, t, angry, dizzy, hurt)
        case "claw":
            let (cx, cy) = clawPos()
            AHBoss.crab(s, xi, yi, t, angry, dizzy, hurt, Int(cx), Int(cy))
        default:   // gulls
            let striking = cur == "strike" && ["act", "rest", "hurt"].contains(state)
            let n = max(0, hp - (striking ? 1 : 0))
            if state != "dead" {
                for i in 0 ..< n {
                    let a = t * 1.6 + Double(i) * 2 * Double.pi / Double(max(1, n))
                    let gx = xi + Int(cos(a) * Double(40 + 10 * (i % 2)))
                    let gy = yi + Int(sin(a) * 5)
                    AHBoss.gull(s, gx, gy, t + Double(i), i == n - 1 && hp <= 2, false, false, cos(a) > 0)
                }
            }
            if striking || state == "dead" {
                let (gx, gy) = state == "dead" ? (xi, yi) : (Int(hx), Int(hy))
                AHBoss.gull(s, gx, gy, t, hp <= 1, dizzy, hurt, tx > sx, landed: dizzy)
            }
        }
        if dizzy && kind != "gulls" {
            let (hxi, hyi) = kind == "claw" ? (Int(hx), Int(hy)) : (xi, yi)
            for i in 0 ..< 3 {
                let a = t * 6 + Double(i) * 2.1
                s.fillRect(col("yellow"), hxi + Int(cos(a) * 10), hyi - h / 2 - 4 + Int(sin(a) * 3), 2, 2)
            }
        }
        if dizzy && Int(t * 3) % 2 == 1 {
            let off = (kind != "gulls" && kind != "claw") ? h / 2 : 8
            drawText(s, "HOP!", Int(hx), Int(hy) - off - 14, "lime", align: .center, shadow: "black")
        }
    }

    // ------------------------------------------------------------------ costumes
    /// BRUNO: a big fluffy guard dog with a cap and a studded collar (centre x, y).
    static func dog(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ face: Int, _ angry: Bool, _ dizzy: Bool, _ hurt: Bool,
                    _ king: Bool, _ running: Bool) {
        let body = hurt ? col("white") : col(king ? "orange" : "peach")
        let dark = col(king ? "choco" : "brown")
        let sc = king ? 1.15 : 1.0
        let bw = Int(28 * sc), bh = Int(18 * sc)
        let step = running ? Int(t * 12) % 2 : 0
        s.ellipse(col("black"), x - bw / 2 - 1, y - bh / 2 + 2, bw + 2, bh)
        s.ellipse(body, x - bw / 2, y - bh / 2 + 3, bw, bh - 2)
        for lx in [x - bw / 2 + 4, x + bw / 2 - 8] {
            s.fillRect(col("black"), lx, y + bh / 2 - 2 + step, 5, 4)
            s.fillRect(dark, lx + 1, y + bh / 2 - 2 + step, 3, 3)
        }
        let hx = x + face * (bw / 2 - 5)
        let hy = y - bh / 2 + 2
        s.circle(col("black"), hx, hy, 9)
        s.circle(body, hx, hy, 8)
        for side in [-1, 1] { s.ellipse(dark, hx + side * 7 - 3, hy - 4, 6, 10) }
        s.ellipse(col("cream"), hx - 4 + face * 2, hy + 1, 9, 6)
        s.fillRect(col("black"), hx + face * 3 - 1, hy + 1, 3, 2)
        if dizzy {
            for side in [-1, 1] { s.circle(col("black"), hx + side * 3, hy - 2, 2, width: 1) }
        } else {
            Cute.eyes(s, hx, hy - 2, 3, look: face, mood: angry ? "angry" : "happy")
        }
        if king {
            let pts: [(Double, Double)] = [(hx - 6, hy - 7), (hx - 6, hy - 13), (hx - 3, hy - 9), (hx, hy - 14), (hx + 3, hy - 9),
                                           (hx + 6, hy - 13), (hx + 6, hy - 7)].map { (Double($0.0), Double($0.1)) }
            s.polygon(col("yellow"), pts)
            s.fillRect(col("red"), hx - 1, hy - 10, 2, 2)
        } else {
            s.fillRect(col("blue"), hx - 6, hy - 9, 12, 3)
            s.fillRect(col("blue"), hx + face * 4 - 2, hy - 7, 6, 1)
            s.fillRect(col("yellow"), hx - 1, hy - 9, 2, 2)
        }
        s.fillRect(col("red"), hx - 6, hy + 7, 12, 2)
        for i in 0 ..< 3 { s.fillRect(col("yellow"), hx - 4 + i * 4, hy + 7, 1, 1) }
        let tx = x - face * (bw / 2)
        let wag = Int(sin(t * (angry ? 20 : 8)) * 3)
        s.line(dark, tx, y, tx - face * 4, y - 5 + wag)
    }

    /// SWEEPO: a mint street-sweeper truck with headlight eyes and spinning brushes.
    static func sweeper(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ face: Int, _ angry: Bool, _ dizzy: Bool, _ hurt: Bool) {
        let body = hurt ? col("white") : col("mint")
        s.rect(col("black"), IRect(x - 21, y - 12, 42, 22), radius: 4)
        s.rect(body, IRect(x - 20, y - 11, 40, 20), radius: 3)
        s.fillRect(col("teal"), x - 20, y + 3, 40, 3)
        let tankX = face > 0 ? x - 18 : x - 2
        s.fillRect(col("sky"), tankX, y - 9, 20, 9)
        s.fillRect(col("white"), tankX + 2, y - 8, 6, 1)
        let cabX = face > 0 ? x + 6 : x - 18
        s.fillRect(col("black"), cabX, y - 9, 12, 8)
        s.fillRect(col(dizzy ? "darkgray" : "yellow"), cabX + 2, y - 7, 3, 3)
        s.fillRect(col(dizzy ? "darkgray" : "yellow"), cabX + 7, y - 7, 3, 3)
        if angry { s.fillRect(col("red"), cabX + 1, y - 9, 10, 1) }
        if dizzy { drawText(s, "~", tankX + 6, y - 18, "sky", shadow: nil) }
        let bx = face > 0 ? x + 20 : x - 20
        for k in 0 ..< 2 {
            let cy = y + 6 + k * 4 - 2
            s.circle(col("black"), bx, cy, 4)
            s.circle(col("yellow"), bx, cy, 3)
            let a = t * 25 + Double(k)
            s.fillRect(col("orange"), bx + Int(cos(a) * 3), cy + Int(sin(a) * 3), 1, 1)
        }
        for wx in [x - 12, x + 12] {
            s.circle(col("black"), wx, y + 10, 3)
            s.fillRect(col("gray"), wx, y + 10, 1, 1)
        }
        s.fillRect(Int(t * 6) % 2 == 1 ? col("orange") : col("yellow"), x - 2, y - 14, 4, 2)
    }

    static func gull(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ captain: Bool, _ dizzy: Bool, _ hurt: Bool, _ right: Bool,
                     landed: Bool = false) {
        let body = hurt ? col("yellow") : col("white")
        let flap = landed ? 0 : Int(sin(t * 14) * 3)
        let d = right ? 1 : -1
        for side in [-1, 1] {
            s.line(col("black"), x, y, x + side * 8, y - 2 - flap)
            s.line(col("gray"), x, y - 1, x + side * 7, y - 3 - flap)
        }
        s.ellipse(col("black"), x - 6, y - 4, 12, 9)
        s.ellipse(body, x - 5, y - 3, 10, 7)
        let hx = x + d * 5
        s.circle(col("black"), hx, y - 3, 3)
        s.circle(body, hx, y - 3, 2)
        s.fillRect(col("orange"), hx + d * 2 - (d < 0 ? 1 : 0), y - 3, 3, 1)
        if dizzy {
            s.fillRect(col("black"), hx - 1, y - 4, 2, 1)
            s.fillRect(col("orange"), hx + d * 4, y - 2, 4, 3)
            s.fillRect(col("sky"), hx + d * 4, y - 2, 2, 2)
        } else {
            s.fillRect(col("black"), hx, y - 4, 1, 1)
        }
        if captain {
            s.fillRect(col("blue"), hx - 3, y - 7, 6, 2)
            s.fillRect(col("white"), hx - 2, y - 8, 4, 1)
        }
        if landed {
            s.fillRect(col("orange"), x - 2, y + 4, 1, 2)
            s.fillRect(col("orange"), x + 2, y + 4, 1, 2)
        }
    }

    /// BANDIT COON: a masked raccoon with a ringed tail and a sack of stolen snacks.
    static func coon(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ angry: Bool, _ dizzy: Bool, _ hurt: Bool) {
        let body = hurt ? col("white") : col("gray")
        let tw = Int(sin(t * 6) * 2)
        for i in 0 ..< 4 { s.circle(col(i % 2 == 1 ? "black" : "darkgray"), x + 12 + i * 2, y + 4 - i * 3 + tw, 3) }
        s.ellipse(col("black"), x - 11, y - 4, 22, 15)
        s.ellipse(body, x - 10, y - 3, 20, 13)
        let sackY = y + (dizzy ? 2 : 0)
        s.circle(col("black"), x - 12, sackY + 2, 7)
        s.circle(col("brown"), x - 12, sackY + 2, 6)
        s.fillRect(col("choco"), x - 14, sackY - 4, 4, 2)
        if dizzy && Int(t * 8) % 2 == 1 {
            s.fillRect(col("yellow"), x - 14, sackY - 7, 2, 2)
            s.fillRect(col("pink"), x - 10, sackY - 9, 2, 2)
        }
        s.circle(col("black"), x, y - 7, 8)
        s.circle(body, x, y - 7, 7)
        for side in [-1, 1] {
            s.polygon(col("darkgray"), [(Double(x + side * 3), Double(y - 13)), (Double(x + side * 7), Double(y - 16)),
                                        (Double(x + side * 7), Double(y - 10))])
        }
        s.fillRect(col("black"), x - 6, y - 9, 12, 4)
        if dizzy {
            s.fillRect(col("white"), x - 4, y - 8, 2, 1)
            s.fillRect(col("white"), x + 2, y - 8, 2, 1)
        } else {
            s.fillRect(col(angry ? "red" : "white"), x - 4, y - 8, 2, 2)
            s.fillRect(col(angry ? "red" : "white"), x + 2, y - 8, 2, 2)
        }
        s.fillRect(col("cream"), x - 2, y - 4, 5, 3)
        s.fillRect(col("black"), x, y - 4, 1, 1)
    }

    /// KING CLAW: a big dock crab; one claw strikes and gets stuck in the boards.
    static func crab(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ angry: Bool, _ dizzy: Bool, _ hurt: Bool, _ cx: Int, _ cy: Int) {
        let body = hurt ? col("white") : col("red")
        s.line(col("black"), x + 18, y + 4, cx, cy)
        s.line(col("red"), x + 18, y + 3, cx, cy - 1)
        for i in 0 ..< 3 {
            for side in [-1, 1] {
                let lx = x + side * (12 + i * 4)
                s.fillRect(col("black"), lx - 1, y + 6, 3, 6 - i)
                s.fillRect(col("orange"), lx, y + 6, 1, 5 - i)
            }
        }
        s.ellipse(col("black"), x - 22, y - 9, 44, 19)
        s.ellipse(body, x - 21, y - 8, 42, 17)
        s.fillRect(col("orange"), x - 14, y - 3, 28, 2)
        for side in [-1, 1] {
            let ex = x + side * 7
            s.fillRect(col("black"), ex, y - 14, 1, 6)
            s.circle(col("black"), ex, y - 15, 3)
            s.circle(col("white"), ex, y - 15, 2)
            s.fillRect(col("black"), ex + (angry ? 1 : 0), y - 15, 1, 1)
        }
        s.fillRect(col("yellow"), x - 6, y - 12, 12, 3)
        for i in 0 ..< 3 { s.fillRect(col("yellow"), x - 5 + i * 5, y - 14, 2, 2) }
        s.circle(col("black"), x - 26, y + 6, 6)
        s.circle(body, x - 26, y + 6, 5)
        s.circle(col("black"), cx, cy, 7)
        s.circle(dizzy ? col("pink") : body, cx, cy, 6)
        let gap = dizzy ? 0 : Int(abs(sin(t * 10)) * 3)
        s.fillRect(col("black"), cx - 1, cy - 6, 2, 5 + gap)
        if dizzy { s.fillRect(col("brown"), cx - 7, cy + 5, 14, 2) }
    }

    /// HOOTSWORTH: a round purple night owl with huge glasses and glowing eyes.
    static func owl(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ angry: Bool, _ dizzy: Bool, _ hurt: Bool) {
        let body = hurt ? col("white") : col("purple")
        let flap = dizzy ? 0 : Int(sin(t * 10) * 4)
        for side in [-1, 1] {
            s.polygon(col("lavender"), [(Double(x + side * 9), Double(y - 4)), (Double(x + side * (19 + abs(flap))), Double(y + flap)),
                                        (Double(x + side * 9), Double(y + 8))])
        }
        s.ellipse(col("black"), x - 13, y - 12, 26, 25)
        s.ellipse(body, x - 12, y - 11, 24, 23)
        s.ellipse(col("lavender"), x - 7, y + 1, 14, 9)
        for side in [-1, 1] {
            s.polygon(body, [(Double(x + side * 5), Double(y - 10)), (Double(x + side * 11), Double(y - 16)),
                             (Double(x + side * 10), Double(y - 7))])
            let ex = x + side * 5
            s.circle(col("black"), ex, y - 4, 5)
            s.circle(col(dizzy ? "gray" : "yellow"), ex, y - 4, 4)
            if dizzy {
                s.circle(col("black"), ex, y - 4, 2, width: 1)
            } else {
                s.fillRect(col(angry ? "red" : "black"), ex - 1, y - 5, 2, 2)
            }
        }
        s.fillRect(col("black"), x - 1, y - 4, 2, 1)
        s.polygon(col("orange"), [(Double(x - 2), Double(y)), (Double(x + 2), Double(y)), (Double(x), Double(y + 3))])
        s.fillRect(col("orange"), x - 5, y + 11, 3, 2)
        s.fillRect(col("orange"), x + 3, y + 11, 3, 2)
    }
}
