// WHISKER MAZE bosses (port of games/whisker_maze_boss.py): a big house gadget lives in the open hall in the
// middle of the maze and attacks with telegraphed patterns; Nori pounces on it while zoomy on catnip.
import Foundation

private let LINE_STYLE = ["suck_row": "suck", "suck_col": "suck", "snap_row": "snap", "snap_col": "snap", "burn_row": "burn"]

final class WMBoss {
    unowned let sc: WhiskerMaze
    let kind, name: String
    let maxhp: Int
    var hp: Int
    let rate, speed: Double
    let patterns: [String]
    let extra: String
    let tier: Int
    var x = 15.0, y = -4.0                   // tile units (centre); flies in from the top
    var state = "enter"                      // enter | idle | wind | air | land | stun | dead
    var cd = 2.2, timer = 0.0, flash = 0.0
    var next = ""
    var air = (0.0, 0.0, 0.0, 0.0, 1.0)     // from x, y, to x, y, duration
    var queue = 0                            // stomps still to come (stomp3)
    var t = 0.0

    init(_ sc: WhiskerMaze, _ spec: WMBossSpec) {
        self.sc = sc
        kind = spec.kind; name = spec.name; maxhp = spec.hp; hp = spec.hp
        rate = spec.rate; speed = spec.speed; patterns = spec.patterns; extra = spec.extra; tier = spec.tier
    }

    var phase: Int {
        let f = Double(hp) / Double(maxhp)
        return f > 0.67 ? 1 : (f > 0.34 ? 2 : 3)
    }

    func windFrac() -> Double { state == "wind" ? 1.0 - timer / 0.5 : 0 }
    func airborne() -> Bool { state == "air" || state == "enter" }

    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        switch state {
        case "dead":
            return
        case "enter":
            y = min(8.0, y + dt * 7)
            if y >= 8.0 { state = "idle" }
            return
        case "stun":
            timer -= dt
            drift(15, 8, dt, 2.0)
            if timer <= 0 { state = "idle"; cd = max(cd, 0.6) }
            return
        case "air":
            timer += dt
            let (fx, fy, tx, ty, dur) = air
            let k = min(1.0, timer / dur)
            x = fx + (tx - fx) * k
            y = fy + (ty - fy) * k
            if k >= 1.0 {
                state = "land"
                timer = 0.55
                sc.app.shake(4, 0.25)
                sc.app.audio.play("boom")
            }
            return
        case "land":
            timer -= dt
            if timer <= 0 {
                if queue > 0 { queue -= 1; leap() } else { state = "idle"; cd = interval() }
            }
            return
        case "wind":
            timer -= dt
            if timer <= 0 {
                state = "idle"
                cd = interval()
                fire(next)
            }
            return
        default: break
        }
        // idle: drift after Nori but stay inside the hall (fly home first when outside it)
        let n = sc.nori
        let inside = x >= 9.5 && x <= 20.5 && y >= 5.5 && y <= 10.5
        drift(max(10, min(20, n.x)), max(6, min(10, n.y)), dt, speed * (inside ? 1.0 : 2.5))
        cd -= dt
        if cd <= 0 && sc.state == "play" {
            let pats = patterns + (phase >= 3 ? [extra] : [])
            next = pats.randomElement()!
            state = "wind"
            timer = 0.5
            sc.app.audio.play("hold")
        }
    }

    func interval() -> Double { rate * [1.0, 0.85, 0.7][phase - 1] }

    func drift(_ tx: Double, _ ty: Double, _ dt: Double, _ sp: Double) {
        let dx = tx - x, dy = ty - y
        let d = (dx * dx + dy * dy).squareRoot()
        if d > 0.01 {
            let step = min(d, sp * dt)
            x += dx / d * step
            y += dy / d * step
        }
    }

    func tile() -> (Int, Int) { (Int(floor(x + 0.5)), Int(floor(y + 0.5))) }

    /// The slipper jumps onto Nori: a shadow marks the landing zone.
    func leap() {
        let (tx, ty) = sc.nori.tile()
        air = (x, y, Double(tx), Double(ty), 0.95)
        state = "air"
        timer = 0
        sc.addHazard(sc.areaTiles(tx, ty, 1), 0.95, 0.3, "stomp")
        sc.app.audio.play("jump")
    }

    func fire(_ p: String) {
        let (nx, ny) = sc.nori.tile()
        let ph = phase
        let (bx, by) = tile()
        if let style = LINE_STYLE[p] {
            sc.addHazard(p.hasSuffix("row") ? sc.rowTiles(ny) : sc.colTiles(nx), 1.0, 0.5, style)
            return
        }
        switch p {
        case "suck_cross":
            sc.addHazard(sc.rowTiles(ny) + sc.colTiles(nx), 1.1, 0.5, "suck")
        case "bunnies":
            for _ in 0 ..< 1 + ph { sc.spawnBunny() }
        case "stomp":
            leap()
        case "stomp3":
            queue = 2
            leap()
        case "hop":
            air = (x, y, Double.random(in: 10 ... 20), Double.random(in: 6 ... 10), 0.6)
            state = "air"
            timer = 0
            sc.addHazard(sc.areaTiles(Int(air.2 + 0.5), Int(air.3 + 0.5), 1), 0.6, 0.25, "stomp")
        case "quake":
            var tiles: [(Int, Int)] = []
            for xx in bx - 5 ... bx + 5 { tiles.append((xx, by)) }
            for yy in by - 5 ... by + 5 { tiles.append((bx, yy)) }
            sc.addHazard(sc.openOnly(tiles), 0.8, 0.4, "quake")
        case "traps", "traps_big":
            sc.addTraps((p == "traps" ? 3 : 6) + ph)
        case "toast", "drip", "drip8":
            let eight = p == "drip8" || ph >= 2
            var dirs: [(Double, Double)] = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            if eight { dirs += [(0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)] }
            for (dx, dy) in dirs {
                sc.shots.append(WMShot(x: x, y: y, vx: dx * 7, vy: dy * 7, style: p == "toast" ? "toast" : "drip", life: 4))
            }
            sc.app.audio.play("shoot")
        case "pop":
            for _ in 0 ..< 2 + ph {
                let tx = nx + Int.random(in: -3 ... 3), ty = ny + Int.random(in: -2 ... 2)
                let o = sc.openOnly([(tx, ty)])
                sc.addHazard(o.isEmpty ? [(nx, ny)] : o, 1.1, 0.3, "pop")
            }
        case "flood":
            var tiles: [(Int, Int)] = []
            for dx in -3 ... 3 { for dy in -3 ... 3 where abs(dx) + abs(dy) <= 3 { tiles.append((nx + dx, ny + dy)) } }
            sc.addHazard(sc.openOnly(tiles), 0.6, 7.0, "wet")
        case "splash":
            sc.addHazard(sc.areaTiles(nx, ny, 1), 0.9, 0.3, "splash")
        default: break
        }
    }

    /// A zoomy pounce landed. Returns true when the boss is beaten.
    func hurt(_ dmg: Int) -> Bool {
        hp = max(0, hp - dmg)
        flash = 0.3
        queue = 0
        if hp <= 0 { state = "dead"; return true }
        state = "stun"
        timer = 1.2
        return false
    }
}
