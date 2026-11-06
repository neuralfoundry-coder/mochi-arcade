// PAW PINBALL physics (port of games/paw_pinball_phys.py): a jingle-bell ball on a sloped table.
// Sub-stepped so the ball (and a swinging paw) never moves more than ~1 px per step; paws are tapered capsules that
// hand their surface velocity to the ball. Collisions report events to the scene, which does the scoring.
import Foundation

let PP_GRAV = 330.0
private let VMAX = 640.0
private let CELL = 16.0
private let REST: [Int: Double] = [PP_METAL: 0.42, PP_RUBBER: 0.62, PP_SLING: 0.62, PP_GATE: 0.3]
private let SLING_KICK = 175.0
private let BUMP_KICK = 250.0
private let POST_REST = 0.6
private let FLIP_REST = 0.22         // a still paw: soft, so a ball can be caught
private let FLIP_LIVE = 0.62         // a swinging paw: snappy, the ball leaves early
private let RAMP_MIN = 175.0
let PP_FLIP_R1 = 3.6, PP_FLIP_R2 = 2.2
let PP_UP_ANG = -0.42, PP_REST_ANG = 0.50
private let W_UP = 27.0, W_DOWN = 16.0
let PP_LANE_START = (PP_LANE_X, PP_PLUNGE_Y - PP_BALL_R)

final class PPBall {
    var x, y, vx, vy: Double
    var kind: String            // bell | kitten
    var coat = 0
    var state = "play"          // play | ramp | nap | held | gone
    var ramp = -1
    var rd = 0.0, rv = 0.0
    var napT = 0.0, napCd = 0.0
    var laneIn = 0
    var auto = -1.0
    var stillT = 0.0
    var ax, ay: Double
    var trail: [(Double, Double)] = []
    var bossCd = 0.0
    var launched = false

    init(_ x: Double, _ y: Double, _ vx: Double = 0, _ vy: Double = 0, _ kind: String = "bell") {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.kind = kind
        ax = x; ay = y
    }

    var speed: Double { hypot(vx, vy) }
    var inLane: Bool { x > PP_RW && y > 60 }
    var onPlunger: Bool { inLane && y >= PP_PLUNGE_Y - PP_BALL_R - 1.5 && abs(vy) < 40 }
}

final class PPFlipper {
    let px, py: Double
    let side: Double             // +1 left paw (points right), -1 right paw (points left)
    var len: Double
    var a = PP_REST_ANG
    var w = 0.0
    var pressed = false
    var stun = 0.0
    var power = 1.0

    init(_ x: Double, _ y: Double, _ side: Double, _ len: Double) { px = x; py = y; self.side = side; self.len = len }

    func tip() -> (Double, Double) { (px + side * len * cos(a), py + len * sin(a)) }

    func update(_ h: Double) {
        if pressed && stun <= 0 {
            if a > PP_UP_ANG {
                w = -W_UP * power
                a += w * h
                if a <= PP_UP_ANG { a = PP_UP_ANG; w = 0 }
            } else { w = 0 }
        } else {
            if a < PP_REST_ANG {
                w = W_DOWN
                a += w * h
                if a >= PP_REST_ANG { a = PP_REST_ANG; w = 0 }
            } else { w = 0 }
        }
    }

    var isUp: Bool { a < PP_REST_ANG - 0.25 }
}

struct PPEvent { let kind: String; let a: Int; let x, y: Double }

struct PPDyn { var x, y, r: Double; var kind: String; var solid: Bool; var ref: Int }

final class PPFish {
    let x1, y1, x2, y2: Double
    let face, bank: Int
    var down = 0.0
    init(_ f: [Double]) { x1 = f[0]; y1 = f[1]; x2 = f[2]; y2 = f[3]; face = Int(f[4]); bank = Int(f[5]) }
}

private func segContact(_ b: PPBall, _ x1: Double, _ y1: Double, _ x2: Double, _ y2: Double,
                        _ rad: Double) -> (Double, Double, Double, Double)? {
    let dx = x2 - x1, dy = y2 - y1
    let l2 = dx * dx + dy * dy
    var t = l2 > 0 ? ((b.x - x1) * dx + (b.y - y1) * dy) / l2 : 0
    t = t < 0 ? 0 : (t > 1 ? 1 : t)
    let cx = x1 + dx * t, cy = y1 + dy * t
    let ex = b.x - cx, ey = b.y - cy
    let d2 = ex * ex + ey * ey
    let r = PP_BALL_R + rad
    if d2 >= r * r { return nil }
    let d = d2.squareRoot()
    if d < 1e-6 {
        let ln = l2 > 0 ? l2.squareRoot() : 1
        return (-dy / ln, dx / ln, r, t)
    }
    return (ex / d, ey / d, r - d, t)
}

/// Push the ball out along n and reflect its velocity relative to a surface moving at (svx, svy).
@discardableResult
private func bounce(_ b: PPBall, _ nx: Double, _ ny: Double, _ depth: Double, _ e: Double,
                    _ svx: Double = 0, _ svy: Double = 0) -> Double {
    b.x += nx * depth
    b.y += ny * depth
    let rvx = b.vx - svx, rvy = b.vy - svy
    let vn = rvx * nx + rvy * ny
    if vn < 0 {
        b.vx -= (1 + e) * vn * nx
        b.vy -= (1 + e) * vn * ny
        return -vn
    }
    return 0
}

/// Static table geometry with a uniform grid for the broad phase.
final class PPWorld {
    let segs: [[Double]]
    var circs: [(x: Double, y: Double, r: Double, kind: Int, idx: Int)] = []
    let cols = 320 / 16 + 1, rows = 210 / 16 + 1
    var grid: [[Int]]

    init(_ tb: PPTable) {
        segs = tb.walls
        for (i, p) in tb.posts.enumerated() { circs.append((p[0], p[1], p[2], 0, i)) }
        for (i, b) in tb.bumpers.enumerated() { circs.append((b.0, b.1, 9.0, 1, i)) }
        grid = Array(repeating: [], count: cols * rows)
        let pad = PP_BALL_R + 2
        for (i, s) in segs.enumerated() {
            reg(i, min(s[0], s[2]) - pad, min(s[1], s[3]) - pad, max(s[0], s[2]) + pad, max(s[1], s[3]) + pad)
        }
        for (i, c) in circs.enumerated() { reg(10000 + i, c.x - c.r - pad, c.y - c.r - pad, c.x + c.r + pad, c.y + c.r + pad) }
    }

    private func reg(_ item: Int, _ x0: Double, _ y0: Double, _ x1: Double, _ y1: Double) {
        let ya = max(0, Int(floor(y0 / CELL))), yb = min(rows - 1, Int(floor(y1 / CELL)))
        let xa = max(0, Int(floor(x0 / CELL))), xb = min(cols - 1, Int(floor(x1 / CELL)))
        if ya > yb || xa > xb { return }
        for cy in ya ... yb { for cx in xa ... xb { grid[cy * cols + cx].append(item) } }
    }

    func near(_ x: Double, _ y: Double) -> [Int] {
        let cx = Int(floor(x / CELL)), cy = Int(floor(y / CELL))
        if cx < 0 || cy < 0 || cx >= cols || cy >= rows { return [] }
        return grid[cy * cols + cx]
    }
}

/// Steps every free ball. The scene owns balls, paws and the dynamic things (fish, kittens, boss ...).
final class PPPhysics {
    unowned let sc: PawPinball
    let world: PPWorld
    let tb: PPTable
    var events: [PPEvent] = []
    var grav = PP_GRAV

    init(_ scene: PawPinball, _ tb: PPTable) { sc = scene; self.tb = tb; world = PPWorld(tb) }

    func emit(_ kind: String, _ a: Int, _ x: Double, _ y: Double) { events.append(PPEvent(kind: kind, a: a, x: x, y: y)) }

    func step(_ dt: Double) {
        let balls = sc.balls.filter { $0.state == "play" }
        let flips = sc.flippers
        var vmax = 0.0
        for b in balls { vmax = max(vmax, abs(b.vx) + abs(b.vy)) }
        var fl = 0.0
        for f in flips where f.pressed || f.a < PP_REST_ANG { fl = max(fl, W_UP * f.power * f.len) }
        let n = max(2, min(28, Int(((vmax + fl) * dt / 1.0).rounded(.up))))
        let h = dt / Double(n)
        for _ in 0 ..< n {
            for f in flips { f.update(h) }
            for b in balls where b.state == "play" {
                b.vy += grav * h
                let px = b.x, py = b.y
                b.x += b.vx * h
                b.y += b.vy * h
                statics(b)
                dynamics(b)
                for f in flips { flipper(b, f) }
                sensors(b, px, py)
                let sp = b.vx * b.vx + b.vy * b.vy
                if sp > VMAX * VMAX {
                    let k = VMAX / sp.squareRoot()
                    b.vx *= k
                    b.vy *= k
                }
                if b.y > 206 {
                    b.state = "gone"
                    emit("drain", 0, b.x, b.y)
                }
            }
            if balls.count > 1 { ballPairs(balls) }
        }
    }

    // ---------------------------------------------------------------- contacts
    private func statics(_ b: PPBall) {
        for item in world.near(b.x, b.y) {
            if item < 10000 {
                let s = world.segs[item]
                let kind = Int(s[4])
                guard let c = segContact(b, s[0], s[1], s[2], s[3], 0) else { continue }
                if kind == PP_GATE && (s[2] - s[0]) * (b.y - s[1]) - (s[3] - s[1]) * (b.x - s[0]) < 0 { continue }
                let imp = bounce(b, c.0, c.1, c.2, REST[kind] ?? 0.42)
                if kind == PP_SLING && imp > 40 {
                    b.vx += c.0 * SLING_KICK
                    b.vy += c.1 * SLING_KICK
                    emit("sling", item, b.x, b.y)
                } else if imp > 120 {
                    emit("wall", Int(imp), b.x, b.y)
                }
            } else {
                let c = world.circs[item - 10000]
                let ex = b.x - c.x, ey = b.y - c.y
                let d2 = ex * ex + ey * ey
                let rr = c.r + PP_BALL_R
                if d2 >= rr * rr { continue }
                var d = d2.squareRoot()
                if d == 0 { d = 0.001 }
                let nx = ex / d, ny = ey / d
                if c.kind == 1 {
                    bounce(b, nx, ny, rr - d, 0.5)
                    let vn = b.vx * nx + b.vy * ny
                    if vn < BUMP_KICK {
                        b.vx += nx * (BUMP_KICK - vn)
                        b.vy += ny * (BUMP_KICK - vn)
                    }
                    emit("bumper", c.idx, c.x, c.y)
                } else {
                    let imp = bounce(b, nx, ny, rr - d, POST_REST)
                    if imp > 120 { emit("wall", Int(imp), b.x, b.y) }
                }
            }
        }
    }

    private func dynamics(_ b: PPBall) {
        for (i, f) in sc.fish.enumerated() where f.down <= 0 {
            guard let c = segContact(b, f.x1, f.y1, f.x2, f.y2, 2) else { continue }
            bounce(b, c.0, c.1, c.2, 0.35)
            f.down = 1
            emit("fish", i, (f.x1 + f.x2) / 2, (f.y1 + f.y2) / 2)
        }
        for (ri, r) in tb.ramps.enumerated() {
            let g = r.gate
            guard let c = segContact(b, g[0], g[1], g[2], g[3], 0) else { continue }
            let (dx, dy) = r.dir
            let into = b.vx * dx + b.vy * dy
            let front = (b.x - g[0]) * dx + (b.y - g[1]) * dy < 0.5
            if front && into >= RAMP_MIN * sc.rampEase {
                b.state = "ramp"
                b.ramp = ri
                b.rd = 0
                b.rv = max(170, min(320, into * 0.85))
                emit("ramp_in", ri, b.x, b.y)
                return
            }
            bounce(b, c.0, c.1, c.2, 0.3)
            if front && into > 60 { emit("ramp_fail", ri, b.x, b.y) }
        }
        for d in sc.dyn {
            let ex = b.x - d.x, ey = b.y - d.y
            let d2 = ex * ex + ey * ey
            let rr = d.r + PP_BALL_R
            if d2 >= rr * rr { continue }
            if !d.solid { emit(d.kind, d.ref, d.x, d.y); continue }
            var dd = d2.squareRoot()
            if dd == 0 { dd = 0.001 }
            let nx = ex / dd, ny = ey / dd
            bounce(b, nx, ny, rr - dd, 0.55)
            if d.kind == "boss" || d.kind == "bunny" || d.kind == "pickle" {
                let vn = b.vx * nx + b.vy * ny
                if vn < 190 {
                    b.vx += nx * (190 - vn)
                    b.vy += ny * (190 - vn)
                }
            }
            emit(d.kind, d.ref, b.x, b.y)
        }
        if sc.tailOn, let c = segContact(b, 155, 184, 155, 190, 2.5) { bounce(b, c.0, c.1, c.2, 0.55) }
    }

    private func flipper(_ b: PPBall, _ f: PPFlipper) {
        let (tx, ty) = f.tip()
        let dx = tx - f.px, dy = ty - f.py
        let l2 = dx * dx + dy * dy
        var t = ((b.x - f.px) * dx + (b.y - f.py) * dy) / l2
        t = t < 0 ? 0 : (t > 1 ? 1 : t)
        let cx = f.px + dx * t, cy = f.py + dy * t
        let rr = PP_BALL_R + PP_FLIP_R1 + (PP_FLIP_R2 - PP_FLIP_R1) * t
        let ex = b.x - cx, ey = b.y - cy
        let d2 = ex * ex + ey * ey
        if d2 >= rr * rr { return }
        let d = d2.squareRoot()
        var nx: Double, ny: Double
        if d < 1e-6 {
            let ln = l2.squareRoot()
            nx = dy / ln * f.side; ny = -dx / ln * f.side
        } else {
            nx = ex / d; ny = ey / d
        }
        let s = t * f.len                   // lever arm: the tip moves fastest
        let svx = s * (-f.side * sin(f.a)) * f.w
        let svy = s * cos(f.a) * f.w
        let imp = bounce(b, nx, ny, rr - d, f.w < 0 ? FLIP_LIVE : FLIP_REST, svx, svy)
        if imp > 90 && f.w != 0 { emit("flip_hit", Int(f.side), b.x, b.y) }
    }

    private func sensors(_ b: PPBall, _ px: Double, _ py: Double) {
        for (i, l) in tb.lanes.enumerated() {
            let inside = (b.x - l.0) * (b.x - l.0) + (b.y - l.1) * (b.y - l.1) < 25
            let bit = 1 << i
            if inside && b.laneIn & bit == 0 {
                b.laneIn |= bit
                emit("lane", i, l.0, l.1)
            } else if !inside && b.laneIn & bit != 0 {
                b.laneIn &= ~bit
            }
        }
        let sp = tb.spinner
        if sp.count == 4 && (py - sp[1]) * (b.y - sp[1]) <= 0 && py != b.y && sp[0] <= b.x && b.x <= sp[2] {
            emit("spin", Int(abs(b.vy)), b.x, sp[1])
        }
        if let sa = tb.saucer, b.napCd <= 0 {
            if (b.x - sa.0) * (b.x - sa.0) + (b.y - sa.1) * (b.y - sa.1) < 20 && b.speed < 360 {
                b.state = "nap"
                b.x = sa.0; b.y = sa.1
                b.vx = 0; b.vy = 0
                b.napT = 0
                emit("nap", 0, b.x, b.y)
            }
        }
        if !b.launched && (b.y < 64 || (b.x < PP_RW - PP_BALL_R && b.y < 120)) {
            b.launched = true
            emit("launched", 0, b.x, b.y)
        }
    }

    private func ballPairs(_ balls: [PPBall]) {
        for i in 0 ..< balls.count {
            let a = balls[i]
            if a.state != "play" { continue }
            for j in (i + 1) ..< balls.count {
                let b = balls[j]
                if b.state != "play" { continue }
                let dx = b.x - a.x, dy = b.y - a.y
                let d2 = dx * dx + dy * dy
                if d2 >= (2 * PP_BALL_R) * (2 * PP_BALL_R) || d2 < 1e-9 { continue }
                let d = d2.squareRoot()
                let nx = dx / d, ny = dy / d
                let push = (2 * PP_BALL_R - d) / 2
                a.x -= nx * push; a.y -= ny * push
                b.x += nx * push; b.y += ny * push
                let rv = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
                if rv < 0 {
                    let k = -rv * 0.95
                    a.vx -= nx * k; a.vy -= ny * k
                    b.vx += nx * k; b.vy += ny * k
                }
            }
        }
    }
}

func ppRampLengths(_ path: [(Double, Double)]) -> [Double] {
    var out = [0.0]
    for i in 1 ..< path.count { out.append(out.last! + hypot(path[i].0 - path[i - 1].0, path[i].1 - path[i - 1].1)) }
    return out
}

/// Point and direction at distance d along a ramp path.
func ppRampPos(_ path: [(Double, Double)], _ lens: [Double], _ d: Double) -> (Double, Double, Double, Double) {
    let n = lens.count
    if d >= lens[n - 1] {
        let (x1, y1) = path[n - 2], (x2, y2) = path[n - 1]
        let L = max(0.001, lens[n - 1] - lens[n - 2])
        return (x2, y2, (x2 - x1) / L, (y2 - y1) / L)
    }
    var i = 0
    while i < n - 2 && lens[i + 1] < d { i += 1 }
    let (x1, y1) = path[i], (x2, y2) = path[i + 1]
    let L = max(0.001, lens[i + 1] - lens[i])
    let u = (d - lens[i]) / L
    return (x1 + (x2 - x1) * u, y1 + (y2 - y1) * u, (x2 - x1) / L, (y2 - y1) / L)
}
