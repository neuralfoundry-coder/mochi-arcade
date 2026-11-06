// ROOFTOP RUN bosses (port of games/rooftop_run_boss.py): GULLY, BRUNO the guard dog, SGT. COO's pigeon squad,
// RUMBLE the thundercloud and GULLY's fish blimp. Each keeps pace with Tora, throws telegraphed attacks, then gets
// worn out and lands on the roof ahead - the moment to jump on it.
import Foundation

private let RR_PATTERNS: [String: [[String]]] = [
    "gully": [["drop", "dive", "dive"],
              ["drop", "dive", "feathers", "dive"],
              ["feathers", "dive", "drop", "dive"],
              ["feathers", "dive", "dive", "feathers", "dive"]],
    "bruno": [["bark", "bone", "bark"],
              ["bark", "bone", "charge", "bark"],
              ["bark", "charge", "bone", "charge"],
              ["bone", "charge", "bark", "bone", "charge"]],
    "squad": [["crumbs", "dive", "dive"],
              ["crumbs", "dive", "crumbs", "dive"],
              ["dive", "crumbs", "dive", "dive"],
              ["crumbs", "dive", "dive", "crumbs", "dive"]],
    "storm": [["bolt", "rain", "bolt"],
              ["bolt", "gust", "bolt", "rain"],
              ["bolt", "bolt", "gust", "bolt"],
              ["rain", "bolt", "gust", "bolt", "bolt"]],
    "blimp": [["cannon", "anchor", "cannon"],
              ["cannon", "minis", "anchor", "cannon"],
              ["minis", "cannon", "anchor", "minis"],
              ["cannon", "minis", "anchor", "cannon", "minis"]],
]
private let RR_HOME: [String: (Double, Double)] = ["gully": (232, 52), "bruno": (236, 0), "squad": (214, 62),
                                                    "storm": (220, 40), "blimp": (214, 42)]

final class RRShot {
    let k: String
    var x, y, vx, vy: Double
    var t = 0.0
    var life: Double
    var state = 0
    var gy = 0.0
    init(_ k: String, _ x: Double, _ y: Double, _ vx: Double = 0, _ vy: Double = 0, life: Double = 3) {
        self.k = k; self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.life = life
    }

    func rect() -> RRRect? {
        switch k {
        case "shell": return state != 0 ? RRRect(x - 4, y - 6, 8, 6) : RRRect(x - 4, y - 4, 8, 8)
        case "feather", "crumb", "hail": return RRRect(x - 2, y - 2, 5, 5)
        case "wave": return RRRect(x - 3, y - 11, 7, 11)
        case "bone": return state != 0 ? RRRect(x - 5, y - 4, 10, 4) : RRRect(x - 5, y - 3, 10, 6)
        case "bolt": return state == 1 ? RRRect(x - 8, gy - 16, 17, 16) : nil
        case "debris": return RRRect(x - 5, y - 9, 10, 9)
        case "fishbone": return RRRect(x - 4, y - 3, 9, 6)
        case "anchor": return RRRect(x - 6, y - 12, 12, 12)
        case "mini": return RRRect(x - 6, y - 4, 12, 8)
        default: return nil
        }
    }
}

struct RRSquadMember { var dx, dy: Double; var alive = true; var back = 0.0 }

final class RRBoss {
    unowned let sc: RooftopRun
    let kind, name: String
    let lv: Int
    let final: Bool
    let rate: Double
    var hp, maxhp: Int
    let needStomp: Bool
    var state = "enter"
    var t = 0.0                 // time in state
    var at = 0.0                // time in the current attack
    var sx, sy: Double          // screen position while airborne
    var wx = 0.0, wy = 0.0      // world position while dazed on the roof
    var flash = 0.0
    var queue: [String] = []
    var act: String?
    var shots: [RRShot] = []
    var nFired = 0
    var tx = 0.0, ty = 0.0
    var weather = 0.0           // storm rain / gust slow-down left
    var gust = false
    var squad: [RRSquadMember] = []
    var diver = -1              // squad member doing the current dive (-1 = sergeant)
    var by = 0.0, bvy = 0.0, bground = true     // bruno's feet (world) and hop
    var diveY = 0.0, diveX = 0.0

    init(_ sc: RooftopRun, _ spec: RRBossSpec) {
        self.sc = sc
        kind = spec.kind; name = spec.name
        lv = spec.lv; final = spec.final; rate = spec.rate
        hp = spec.hp; maxhp = spec.hp
        needStomp = lv >= 2
        sx = 360; sy = RR_HOME[spec.kind]?.1 ?? 50
        if kind == "squad" {
            let n = 3 + lv
            for i in 0 ..< n {
                squad.append(RRSquadMember(dx: Double((i % 3) * 22 - 22 + (i / 3) * 11),
                                           dy: Double((i / 3) * 16 - 8 + (i % 2) * 6)))
            }
            hp = spec.hp + n - 3
            maxhp = hp
        }
    }

    // ------------------------------------------------------------------ helpers
    var cam: Double { sc.cam }
    var home: (Double, Double) { RR_HOME[kind] ?? (230, 50) }

    func world() -> (Double, Double) {
        if state == "dazed" || state == "hit" { return (wx, wy) }
        return (cam + sx, sy)
    }

    func speed() -> Double { 1 + 0.15 * Double(lv) }
    func sergeantOnly() -> Bool { kind == "squad" && !squad.contains { $0.alive } }

    func newQueue() {
        var pat = RR_PATTERNS[kind]![min(3, lv)]
        if final { pat.append("anchor") }      // the very last fight throws one more volley per round
        queue = pat
    }

    // ------------------------------------------------------------------ update
    func update(_ dt: Double) {
        t += dt
        flash = max(0, flash - dt)
        weather = max(0, weather - dt)
        let (hx, hy) = home
        if kind == "bruno" { brunoFeet(dt) }
        switch state {
        case "enter":
            sx += (hx - sx) * min(1, dt * 2.5)
            if t > 2.2 && sc.state == "play" { state = "fight"; t = 0; newQueue() }
        case "fight":
            bob(dt, hx, hy)
            if act == nil {
                if !queue.isEmpty {
                    act = queue.removeFirst()
                    at = 0
                    nFired = 0
                    startAct()
                } else {
                    land()
                }
            } else {
                at += dt * rate
                runAct(dt)
            }
        case "dazed":
            wy = sc.roofY(wx) ?? wy
            let limit = max(1.6, 3.0 - 0.3 * Double(lv))
            if t > limit || sc.body.x > wx + 60 { takeOff() }
        case "hit":
            if t > 0.5 { takeOff() }
        case "up":
            sx += (hx - sx) * min(1, dt * 3)
            sy += (hy - sy) * min(1, dt * 3)
            if t > 1.0 { state = "fight"; t = 0; newQueue() }
        case "dead":
            sy += 60 * dt
            sx += 30 * dt
        default: break
        }
        for i in squad.indices { squad[i].back = max(0, squad[i].back - dt) }
        updateShots(dt)
    }

    func bob(_ dt: Double, _ hx: Double, _ hy: Double) {
        if act == "dive" || act == "charge" { return }
        let k = kind == "storm" ? 0.6 : 1.0
        sx += (hx + sin(t * 0.9) * 14 * k - sx) * min(1, dt * 3)
        if kind != "bruno" { sy += (hy + sin(t * 2.1) * 6 - sy) * min(1, dt * 3) }
    }

    func brunoFeet(_ dt: Double) {
        let x = (state != "dazed" && state != "hit") ? cam + sx : wx
        let g = sc.roofY(x)
        let ahead = sc.roofY(x + 22)
        if bground {
            if let gy = g {
                by = gy
                if ahead == nil { bground = false; bvy = -230 }
            } else {
                bground = false
                bvy = 0
            }
        }
        if !bground {
            bvy += 900 * dt
            by += bvy * dt
            if let gy = g, bvy > 0, by >= gy - 1 { by = gy; bground = true }
            if by > Double(H + 20) {        // missed the roof: pop back up on the next one
                by = sc.nextRoof(x)?.y ?? 150
                bvy = 0
                bground = true
            }
        }
        if state != "dazed" && state != "hit" { sy = by }
    }

    /// Worn out: settle on the roof ahead until Tora jumps on it (or runs past).
    func land() {
        var x = cam + 290
        var r = sc.roofY(x)
        var k = 0
        while r == nil && k < 30 { x += 10; r = sc.roofY(x); k += 1 }
        wx = x
        wy = r ?? 150
        state = "dazed"
        t = 0
        act = nil
        if kind == "squad" { diver = -1 }
        sc.bossLanded()
    }

    func takeOff() {
        sx = wx - cam
        sy = kind != "bruno" ? wy - 20 : by
        state = "up"
        t = 0
    }

    // ------------------------------------------------------------------ attacks
    func startAct() {
        let b = sc.body
        switch act {
        case "dive":
            let low = Double.random(in: 0 ..< 1) < 0.5
            let ground = sc.roofY(b.x) ?? b.y
            diveY = ground - (low ? 6 : 17)
            if kind == "squad" {
                let alive = squad.indices.filter { squad[$0].alive }
                diver = alive.randomElement() ?? -1
            }
        case "charge":
            diveX = sx
        case "bolt":
            tx = b.x + Double.random(in: 140 ... 190) * sc.speed / 100
            ty = sc.roofY(tx) ?? 150
            let sh = RRShot("bolt", tx, ty, life: 1.6)
            sh.gy = ty
            shots.append(sh)
        case "rain", "gust":
            weather = 2.4
            gust = act == "gust"
        default: break
        }
    }

    func runAct(_ dt: Double) {
        guard let a = act else { return }
        let (bx, by0) = world()
        let tora = sc.body
        let tele = max(0.35, 0.8 - 0.1 * Double(lv))
        switch a {
        case "drop":                // GULLY drops clam shells (they roll along the roof)
            if at > tele && nFired < 1 + lv && at > tele + Double(nFired) * 0.35 {
                nFired += 1
                shots.append(RRShot("shell", bx, by0 + 6, sc.speed * 0.6, 0, life: 4))
                sc.sfx("pop")
            }
            if at > tele + 1.4 { act = nil }
        case "feathers":            // aimed feather darts
            if at > tele && nFired == 0 {
                nFired = 1
                let ax = tora.x + 60, ay = tora.y - 8
                let base = atan2(ay - by0, ax - bx)
                let ks: [Double] = lv < 2 ? Array([-1.0, 0, 1].prefix(2 + min(1, lv))) : [-1, 0, 1]
                for k in ks {
                    let ang = base + k * 0.22
                    shots.append(RRShot("feather", bx, by0, cos(ang) * 140 + sc.speed * 0.4, sin(ang) * 140, life: 3))
                }
                sc.sfx("shoot")
            }
            if at > tele + 1.0 { act = nil }
        case "dive":                // swoop across at head or paw height (slide or jump)
            if at < tele { return }
            if nFired == 0 {
                nFired = 1
                diveX = 330
                sc.sfx("jump")
            }
            diveX -= 250 * speed() * dt
            if !(kind == "squad" && diver >= 0) { sx = diveX; sy = diveY }
            if diveX < -40 {
                if kind == "squad" {
                    if diver >= 0 { squad[diver].back = 1.0; diver = -1 }   // the pigeon rejoins from above
                    act = nil
                } else {
                    sx = 340
                    sy = home.1
                    act = nil
                }
            }
        case "bark":                // BRUNO: a shock-wave that runs along the roof
            if at > tele && nFired == 0 {
                nFired = 1
                shots.append(RRShot("wave", bx - 12, by - 1, -150 + sc.speed, 0, life: 3))
                sc.sfx("explode")
            }
            if at > tele + 0.9 { act = nil }
        case "bone":                // lobbed bone that lands ahead of Tora and lies there
            if at > tele && nFired < 1 + (lv >= 2 ? 1 : 0) {
                nFired += 1
                let landX = tora.x + Double.random(in: 120 ... 170) * sc.speed / 100
                shots.append(RRShot("bone", bx, by0 - 16, (landX - bx) / 1.0, -260, life: 3.2))
                sc.sfx("jump")
            }
            if at > tele + 1.2 { act = nil }
        case "charge":              // BRUNO charges back across the roof - jump over him
            if at < tele + 0.3 { return }
            if nFired == 0 { nFired = 1; sc.sfx("explode") }
            sx -= 230 * speed() * dt
            if sx < -50 { sx = 360; act = nil }
        case "crumbs":              // the squad drops bread crumbs
            if at > tele && nFired < 4 + lv && at > tele + Double(nFired) * 0.18 {
                nFired += 1
                let x = tora.x + Double.random(in: 60 ... 220)
                shots.append(RRShot("crumb", x, 30, sc.speed * 0.2, 110 + 20 * Double(lv), life: 3))
                sc.sfx("pop")
            }
            if at > tele + 1.6 { act = nil }
        case "bolt":
            if at > 1.9 { act = nil }
        case "rain", "gust":
            if nFired < 3 + lv && at > 0.5 + Double(nFired) * 0.5 {
                nFired += 1
                if a == "rain" {
                    for _ in 0 ..< 3 {
                        let x = tora.x + Double.random(in: 40 ... 260)
                        shots.append(RRShot("hail", x, 20, sc.speed * 0.3, 140, life: 3))
                    }
                } else {
                    let gx = cam + Double(W) + 10
                    shots.append(RRShot("debris", gx, sc.roofY(gx) ?? 150, -90, 0, life: 4))
                }
            }
            if at > 2.6 { act = nil }
        case "cannon":              // BLIMP: fish-bone shells lobbed at Tora
            if at > tele && nFired < 2 + (lv >= 2 ? 1 : 0) && at > tele + Double(nFired) * 0.45 {
                nFired += 1
                let landX = tora.x + Double.random(in: 70 ... 160) * sc.speed / 100
                shots.append(RRShot("fishbone", bx - 20, by0 + 10, (landX - bx) / 1.0, -120, life: 2.4))
                sc.sfx("shoot")
            }
            if at > tele + 1.5 { act = nil }
        case "anchor":
            if at > tele && nFired == 0 {
                nFired = 1
                shots.append(RRShot("anchor", bx, by0 + 14, sc.speed, 60, life: 4.5))
                sc.sfx("tin")
            }
            if at > tele + 1.2 { act = nil }
        case "minis":
            if at > tele && nFired < 2 + (lv >= 2 ? 1 : 0) && at > tele + Double(nFired) * 0.6 {
                nFired += 1
                let ground = sc.roofY(tora.x + 200) ?? tora.y
                let y = ground - ((nFired + lv) % 2 == 1 ? 6 : 17)
                let sh = RRShot("mini", cam + Double(W) + 10, y, sc.speed - 220, 0, life: 3)
                sh.gy = y
                shots.append(sh)
                sc.sfx("jump")
            }
            if at > tele + 2.0 { act = nil }
        default:
            act = nil
        }
    }

    func updateShots(_ dt: Double) {
        for s in shots {
            s.t += dt
            switch s.k {
            case "shell":
                if s.state == 0 {
                    s.vy += 600 * dt
                    s.x += s.vx * dt
                    s.y += s.vy * dt
                    if let g = sc.roofY(s.x), s.y >= g, s.y - s.vy * dt <= g + 2 { s.y = g; s.state = 1; s.vx = -55 }
                } else {
                    s.x += s.vx * dt
                    if sc.roofY(s.x) == nil { s.state = 0; s.vy = 0 }
                }
            case "feather", "crumb", "hail", "mini":
                s.x += s.vx * dt
                s.y += s.vy * dt
                if s.k != "mini", let g = sc.roofY(s.x), s.y >= g {
                    s.life = 0
                    sc.parts.burst(s.x, g - 2, 4, ["white", "cream"], 30, 0.3)
                }
            case "wave":
                s.x += s.vx * dt
            case "bone", "fishbone":
                if s.state == 0 {
                    s.vy += 520 * dt
                    s.x += s.vx * dt
                    s.y += s.vy * dt
                    if let g = sc.roofY(s.x), s.vy > 0, s.y >= g {
                        if s.k == "fishbone" {
                            s.life = 0
                            sc.parts.burst(s.x, g - 2, 8, ["white", "gray", "sky"], 50, 0.4)
                            sc.sfx("brick")
                        } else {
                            s.y = g; s.state = 1; s.vx = 0; s.life = min(s.life, s.t + 1.6)
                        }
                    }
                }
            case "bolt":
                let strike = max(0.5, 0.95 - 0.12 * Double(lv))
                if s.state == 0 && s.t > strike {
                    s.state = 1
                    sc.sfx("boom")
                    sc.app.shake(3, 0.2)
                    sc.hype.flash("white", 0.12)
                } else if s.state == 1 && s.t > strike + 0.45 {
                    s.state = 2
                    s.life = 0
                }
            case "debris":
                s.x += s.vx * dt
                if let g = sc.roofY(s.x) { s.y = g } else { s.y += 200 * dt }
            case "anchor":
                if s.state == 0 {
                    s.vy += 700 * dt
                    s.y += s.vy * dt
                    s.x += s.vx * dt
                    if let g = sc.roofY(s.x), s.y >= g {
                        s.y = g; s.state = 1; s.vx = -80
                        sc.sfx("tin")
                        sc.app.shake(2, 0.15)
                    }
                } else {
                    s.x += s.vx * dt
                    if let g = sc.roofY(s.x) { s.y = g } else { s.state = 0; s.vy = 0 }
                }
            default: break
            }
        }
        shots.removeAll { !($0.t < $0.life && $0.y < Double(H + 30) && $0.x > cam - 60) }
    }

    // ------------------------------------------------------------------ contact with Tora
    /// The boss's own hit box in world space (or nil).
    func bodyRect() -> RRRect? {
        let (x, y) = world()
        if ["enter", "dead", "up", "hit"].contains(state) { return nil }
        switch kind {
        case "gully": return state != "dazed" ? RRRect(x - 12, y - 6, 24, 12) : RRRect(x - 14, y - 20, 28, 20)
        case "bruno": return RRRect(x - 13, y - 20, 26, 20)
        case "squad":
            if state == "dazed" { return RRRect(x - 7, y - 12, 14, 12) }
            if act == "dive" { return RRRect(cam + diveX - 6, diveY - 4, 12, 8) }
            return nil
        case "storm": return state == "dazed" ? RRRect(x - 14, y - 12, 28, 12) : nil
        case "blimp": return state == "dazed" ? RRRect(x - 13, y - 12, 26, 12) : nil
        default: return nil
        }
    }

    /// While attacking, touching the boss's body hurts (gully/squad dives, bruno charges or runs).
    func dangerous() -> Bool {
        if state != "fight" { return false }
        if kind == "gully" || kind == "squad" { return act == "dive" && nFired > 0 }
        return kind == "bruno"
    }

    /// Tora's body against the boss: "stomp", "hit", "bump", "hurt" or nil.
    func check(_ b: RRBody, _ box: RRRect) -> String? {
        guard let r = bodyRect(), box.hits(r) else { return nil }
        if state == "dazed" {
            if b.vy > 0 && b.y <= r.y + 7 { return "stomp" }
            return needStomp ? "bump" : "hit"
        }
        return dangerous() ? "hurt" : nil
    }

    func takeHit(_ dmg: Int) -> Bool {
        hp -= dmg
        flash = 0.35
        if hp <= 0 {
            hp = 0
            state = "dead"
            t = 0
            sx = wx - cam
            sy = wy - 20
            shots = []
            return true
        }
        if kind == "squad", let i = squad.firstIndex(where: { $0.alive }) { squad[i].alive = false }
        state = "hit"
        t = 0
        return false
    }

    func hurts(_ box: RRRect) -> Bool { shots.contains { s in s.rect().map { box.hits($0) } ?? false } }

    /// Run-speed factor while RUMBLE's rain or gusts blow.
    func slow() -> Double { weather <= 0 ? 1.0 : (gust ? 0.6 : 0.8) }

    // ------------------------------------------------------------------ drawing
    func draw(_ s: Surface, _ t: Double) {
        let cam = self.cam
        for sh in shots where ["shell", "crumb", "hail", "bone", "fishbone", "anchor"].contains(sh.k) && sh.state == 0 {
            if let g = sc.roofY(sh.x), g - sh.y > 6 {
                let w = 4 + Int(max(0, 60 - (g - sh.y)) / 10)
                s.ellipse(col("black"), Int(sh.x - cam) - w, Int(g) - 2, w * 2 + 1, 3)
            }
        }
        for sh in shots { rrDrawShot(s, sh, cam, t) }
        if kind == "storm" && weather > 0 { rrDrawStormWeather(s, t, gust) }
        let (x, y) = world()
        let sx = Int(x - cam), sy = Int(y)
        let hit = flash > 0 && Int(t * 20) % 2 == 1
        switch kind {
        case "gully":
            if act == "dive" && nFired == 0 && state == "fight" { drawDiveWarning(s, t) }
            let remap: [Character: Character]? = hit ? ["w": "r", "g": "r"] : nil
            if state == "dazed" || state == "hit" {
                s.blit(sprite("rr_gully_nofish", 0, remap: remap, scale: 2), sx - 22, sy - 30)
                rrDizzy(s, sx - 6, sy - 30, t)
            } else if state == "dead" {
                s.blit(sprite("rr_gully_dead", 0, scale: 2), sx - 22, sy - 16)
            } else {
                s.blit(sprite("rr_gully", Int(t * 8) % 2, remap: remap, scale: 2), sx - 22, sy - 16)
            }
        case "bruno": rrDrawBruno(s, sx, sy, t, self, hit)
        case "squad": rrDrawSquad(s, self, t, hit)
        case "storm": rrDrawStorm(s, sx, sy, t, self, hit)
        case "blimp": rrDrawBlimp(s, sx, sy, t, self, hit)
        default: break
        }
        if state == "dazed" && Int(t * 4) % 2 == 1, let r = bodyRect() {
            let ax = Int(r.x + r.w / 2 - cam)
            let ay = Int(r.y) - 18 - Int(abs(sin(t * 6)) * 3)
            s.polygon(col("yellow"), [(Double(ax - 4), Double(ay - 4)), (Double(ax + 4), Double(ay - 4)), (Double(ax), Double(ay + 1))])
            drawText(s, needStomp ? "JUMP ON IT!" : "GET IT!", ax, ay - 13, "yellow", align: .center, outline: "ink")
        }
    }

    func drawDiveWarning(_ s: Surface, _ t: Double) {
        if Int(t * 10) % 2 == 1 { drawText(s, "!", W - 12, Int(diveY) - 6, "red", scale: 2, outline: "ink") }
        var xx = 84
        while xx < W - 22 { s.fillRect(col("red"), xx, Int(diveY), 5, 1); xx += 10 }
    }
}

/// A 1-px arc from a0 to a1 degrees (0 = right, 90 = down), plotted point by point.
func rrArc(_ s: Surface, _ c: String, _ cx: Int, _ cy: Int, _ r: Double, _ a0: Int, _ a1: Int) {
    let cc = col(c)
    var a = a0
    while a <= a1 {
        let ra = Double(a) * .pi / 180
        s.fillRect(cc, cx + Int((cos(ra) * r).rounded()), cy + Int((sin(ra) * r).rounded()), 1, 1)
        a += 6
    }
}

func rrDizzy(_ s: Surface, _ x: Int, _ y: Int, _ t: Double) {
    for i in 0 ..< 3 {
        let a = t * 5 + Double(i) * 2.1
        s.fillRect(col("yellow"), x + Int(cos(a) * 8), y + Int(sin(a) * 2), 2, 2)
    }
}

func rrDrawShot(_ s: Surface, _ sh: RRShot, _ cam: Double, _ t: Double) {
    let x = Int(sh.x - cam), y = Int(sh.y)
    let st = sh.state != 0
    switch sh.k {
    case "shell":
        s.ellipse(col("black"), x - 5, st ? y - 6 : y - 4, 10, 7)
        s.ellipse(col("peach"), x - 4, st ? y - 5 : y - 3, 8, 5)
        s.fillRect(col("pink"), x - 2, st ? y - 4 : y - 2, 1, 3)
        s.fillRect(col("pink"), x + 1, st ? y - 4 : y - 2, 1, 3)
    case "feather":
        let ang = atan2(sh.vy, sh.vx)
        s.line(col("white"), x, y, x - Int(cos(ang) * 6), y - Int(sin(ang) * 6), width: 2)
        s.fillRect(col("gray"), x, y, 1, 1)
    case "crumb":
        s.fillRect(col("black"), x - 2, y - 2, 5, 5)
        s.fillRect(col("peach"), x - 1, y - 1, 3, 3)
    case "hail":
        s.fillRect(col("white"), x - 1, y - 1, 3, 3)
        s.fillRect(col("sky"), x, y + 1, 1, 1)
    case "wave":
        for i in 0 ..< 3 { rrArc(s, (i + Int(t * 10)) % 2 == 1 ? "yellow" : "white", x, y - 6, Double(4 + i * 3), 110, 250) }
    case "bone":
        s.fillRect(col("white"), x - 4, y - 3, 9, 2)
        for dx in [-5, 4] { s.fillRect(col("white"), x + dx, y - 4, 2, 4) }
        s.fillRect(col("gray"), x - 4, y - 1, 9, 1)
    case "bolt":
        let gy = Int(sh.gy)
        if sh.state == 0 {
            if Int(t * 12) % 2 == 1 {
                var yy = 30
                while yy < gy { s.fillRect(col("yellow"), x, yy, 1, 4); yy += 8 }
            }
            s.ellipse(col("yellow"), x - 8, gy - 2, 17, 4, width: 1)
        } else if sh.state == 1 {
            var px = x
            var yy = 20
            while yy < gy {
                let nx = x + Int.random(in: -4 ... 4)
                s.line(col("white"), px, yy, nx, yy + 8, width: 3)
                s.line(col("yellow"), px, yy, nx, yy + 8)
                px = nx
                yy += 8
            }
            for _ in 0 ..< 6 { s.fillRect(col("yellow"), x - 8 + Int.random(in: 0 ... 16), gy - Int.random(in: 1 ... 14), 2, 2) }
        }
    case "debris":
        s.fillRect(col("black"), x - 5, y - 9, 10, 9)
        s.fillRect(col("gray"), x - 4, y - 8, 8, 7)
        s.fillRect(col("darkgray"), x - 4, y - 5 + Int(t * 8) % 3, 8, 1)
    case "fishbone":
        s.fillRect(col("white"), x - 4, y, 9, 1)
        for i in 0 ..< 3 { s.fillRect(col("white"), x - 2 + i * 2, y - 2, 1, 5) }
        s.circle(col("white"), x - 5, y, 2)
    case "anchor":
        if sh.state == 0 { s.fillRect(col("darkgray"), x, 40, 1, max(0, y - 52)) }
        s.fillRect(col("black"), x - 2, y - 13, 5, 10)
        s.fillRect(col("gray"), x - 1, y - 12, 3, 9)
        rrArc(s, "gray", x, y - 7, 6, 20, 160)
        rrArc(s, "gray", x, y - 6, 6, 20, 160)
    case "mini":
        s.blit(sprite("rr_gully_nofish", Int(t * 10) % 2, remap: ["w": "c", "g": "d"]), x - 9, y - 9)
    default: break
    }
}

/// BRUNO: a stocky guard dog with a studded collar and a little cap.
func rrDrawBruno(_ s: Surface, _ x0: Int, _ y: Int, _ t: Double, _ b: RRBoss, _ hit: Bool) {
    let dazed = b.state == "dazed"
    let charging = b.act == "charge" && b.nFired > 0
    let growl = b.act == "charge" && b.nFired == 0 && b.state == "fight"
    let x = x0 + (growl ? Int(sin(t * 50)) : 0)
    let body = col(hit ? "red" : "brown"), dark = col("choco")
    let run = dazed ? 0 : Int(t * 12) % 2
    s.ellipse(col("black"), x - 14, y - 19, 28, 15)
    s.ellipse(body, x - 13, y - 18, 26, 13)
    s.fillRect(col("cream"), x - 6, y - 9, 10, 3)
    for (i, lx) in [x - 10, x - 5, x + 3, x + 8].enumerated() {
        let off = (i % 2 == 1 ? run : 1 - run) * 2
        s.fillRect(col("black"), lx - 1, y - 6, 4, 6)
        s.fillRect(dark, lx, y - 6 + off / 2, 2, 5 - off / 2)
    }
    s.fillRect(dark, x + 13, y - 18 + Int(sin(t * 15) * 2), 3, 4)
    let hx = x - 14, hy = y - 22 + (dazed ? 2 : 0)
    s.circle(col("black"), hx, hy, 9)
    s.circle(body, hx, hy, 8)
    s.ellipse(col("cream"), hx - 9, hy, 10, 7)
    s.fillRect(col("black"), hx - 8, hy + 1, 3, 2)
    s.ellipse(dark, hx + 2, hy - 9, 7, 9)
    s.ellipse(dark, hx - 7, hy - 9, 6, 7)
    if dazed {
        s.fillRect(col("black"), hx - 4, hy - 3, 3, 1)
        s.fillRect(col("black"), hx + 1, hy - 3, 3, 1)
        s.fillRect(col("pink"), hx - 5, hy + 6, 3, 4 + Int(abs(sin(t * 8)) * 2))      // tongue out
        rrDizzy(s, hx, hy - 14, t)
    } else {
        Cute.eyes(s, hx - 1, hy - 2, 3, look: -1, mood: "angry", size: 1)
        if growl || charging {
            s.fillRect(col("red"), hx - 4, hy - 3, 1, 1)
            s.fillRect(col("red"), hx + 2, hy - 3, 1, 1)
        }
        if b.act == "bark" && b.at > 0.2 && b.at < 1.0 {
            s.fillRect(col("black"), hx - 8, hy + 4, 6, 3)
            drawText(s, "WOOF!", hx - 10, hy - 22, "yellow", align: .center, outline: "ink")
        }
    }
    s.fillRect(col("red"), hx - 2, hy + 6, 9, 3)
    for i in 0 ..< 3 { s.fillRect(col("yellow"), hx - 1 + i * 3, hy + 7, 1, 1) }
    s.fillRect(col("blue"), hx - 6, hy - 10, 12, 3)
    s.fillRect(col("blue"), hx - 9, hy - 8, 5, 2)
    s.fillRect(col("yellow"), hx - 1, hy - 10, 2, 2)
    if growl && Int(t * 8) % 2 == 1 { drawText(s, "GRRR", hx, hy - 24, "red", align: .center, outline: "ink") }
}

func rrDrawSquad(_ s: Surface, _ b: RRBoss, _ t: Double, _ hit: Bool) {
    let cam = b.cam
    let hx = b.sx, hy = b.sy
    for (i, m) in b.squad.enumerated() where m.alive {
        var x: Double, y: Double
        if i == b.diver && b.act == "dive" {
            if b.nFired == 0 {      // wind-up: wobble in place, then swoop
                if Int(t * 10) % 2 == 1 { drawText(s, "!", Int(hx + m.dx), Int(hy + m.dy) - 16, "red", outline: "ink") }
                b.drawDiveWarning(s, t)
                x = hx + m.dx + sin(t * 30) * 2
                y = hy + m.dy
            } else {
                x = b.diveX
                y = b.diveY
            }
        } else {
            x = hx + m.dx + sin(t * 3 + Double(i)) * 3
            y = hy + m.dy + cos(t * 4 + Double(i)) * 3 - m.back * 60
        }
        s.blit(sprite("rr_pigeon_fly", Int(t * 10) + i), Int(x) - 6, Int(y) - 6)
    }
    // the sergeant: a big pigeon with a cap (leads from the back, dives once the squad is down)
    var x = hx + 34, y = hy - 8
    if b.state == "dazed" || b.state == "hit" {
        x = b.wx - cam
        y = b.wy - 6
    } else if b.sergeantOnly() && b.act == "dive" {
        if b.nFired == 0 { b.drawDiveWarning(s, t) } else { x = b.diveX; y = b.diveY }
    }
    let remap: [Character: Character] = hit ? ["g": "r", "d": "P"] : ["g": "v", "d": "u"]
    if b.state == "dazed" || b.state == "hit" {
        s.blit(sprite("rr_pigeon", 0, remap: remap), Int(x) - 6, Int(y) - 4)
        s.fillRect(col("blue"), Int(x) - 5, Int(y) - 6, 6, 2)
        rrDizzy(s, Int(x), Int(y) - 10, t)
    } else {
        s.blit(sprite("rr_pigeon_fly", Int(t * 8) % 2, remap: remap, scale: 2), Int(x) - 12, Int(y) - 12)
        s.fillRect(col("blue"), Int(x) - 10, Int(y) - 12, 9, 3)      // sergeant's cap
        s.fillRect(col("yellow"), Int(x) - 6, Int(y) - 12, 2, 1)
    }
}

/// RUMBLE: a grumpy thundercloud. Shrinks into a little puff when worn out.
func rrDrawStorm(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ b: RRBoss, _ hit: Bool) {
    let dazed = b.state == "dazed"
    let base = hit ? "red" : (dazed ? "gray" : "darkgray")
    var puffs: [(Int, Int, Int)]
    if dazed {
        puffs = [(-8, -6, 6), (0, -9, 7), (8, -6, 6), (0, -4, 8)]
    } else {
        let swell = 1 + (b.weather > 0 ? 0.15 : 0)
        puffs = [(-22, 0, 11), (-8, -9, 14), (10, -7, 13), (24, 1, 10), (0, 4, 13)].map {
            (Int(Double($0.0) * swell), $0.1, Int(Double($0.2) * swell))
        }
    }
    for (dx, dy, r) in puffs { s.circle(col("black"), x + dx, y + dy, r + 1) }
    for (dx, dy, r) in puffs { s.circle(col(base), x + dx, y + dy, r) }
    for (dx, dy, r) in puffs { s.circle(col(dazed ? "white" : "gray"), x + dx - r / 3, y + dy - r / 3, max(1, r / 3)) }
    let ey = y - (dazed ? 4 : 0)
    if dazed {
        Cute.eyes(s, x, ey, 4, look: 0, mood: "sleepy")
        rrDizzy(s, x, y - 18, t)
    } else {
        Cute.eyes(s, x, ey, 6, look: -1, mood: "angry", size: 2)
        Cute.mouth(s, x - 1, y + 6, "angry")
        if b.act == "bolt" && Int(t * 14) % 2 == 1 {
            for i in 0 ..< 3 { s.line(col("yellow"), x - 10 + i * 10, y + 12, x - 13 + i * 10, y + 20, width: 2) }
        }
    }
}

func rrDrawStormWeather(_ s: Surface, _ t: Double, _ gust: Bool) {
    let c = col("sky")
    for i in 0 ..< 50 {
        let x = rrMod(i * 47 + Int(t * (gust ? 300 : 80)), W + 30) - 15
        let y = rrMod(i * 31 + Int(t * 300), H)
        if gust { s.fillRect(col("lavender"), W - x, y, 10, 1) } else { s.line(c, x, y, x - 2, y + 7) }
    }
}

/// GULLY's fish blimp: a fish-shaped balloon, a gondola, and Gully at the controls.
func rrDrawBlimp(_ s: Surface, _ x: Int, _ y: Int, _ t: Double, _ b: RRBoss, _ hit: Bool) {
    let dazed = b.state == "dazed" || b.state == "hit"
    let gx: Int, gy: Int, bx: Int, by: Int, sag: Int
    if dazed { gx = x; gy = y; bx = x + 4; by = y - 30; sag = 4 } else { bx = x; by = y; gx = x; gy = y + 26; sag = 0 }
    let skin = col(hit ? "red" : "sky")
    s.ellipse(col("black"), bx - 31, by - 15 + sag, 62, 30 - sag)
    s.ellipse(skin, bx - 30, by - 14 + sag, 60, 28 - sag)
    s.ellipse(col("blue"), bx - 30, by + 2, 60, 12 - sag)
    s.polygon(col("black"), [(Double(bx + 26), Double(by)), (Double(bx + 42), Double(by - 12)), (Double(bx + 42), Double(by + 12))])
    s.polygon(skin, [(Double(bx + 28), Double(by)), (Double(bx + 40), Double(by - 9)), (Double(bx + 40), Double(by + 9))])
    s.circle(col("white"), bx - 18, by - 3 + sag / 2, 5)
    s.circle(col("black"), bx - 19, by - 3 + sag / 2, 2)
    for i in 0 ..< 3 { s.fillRect(col("white"), bx - 6 + i * 9, by - 9 + sag, 4, 1) }
    s.fillRect(col("darkgray"), gx - 9, by + 12, 1, gy - by - 14)
    s.fillRect(col("darkgray"), gx + 9, by + 12, 1, gy - by - 14)
    s.fillRect(col("black"), gx - 13, gy - 12, 26, 12)
    s.fillRect(col("brown"), gx - 12, gy - 11, 24, 10)
    s.fillRect(col("peach"), gx - 12, gy - 11, 24, 1)
    s.fillRect(col("gray"), gx - 16, gy - 9, 4, 3)          // the cannon
    if b.act == "cannon" && b.state == "fight" && Int(t * 12) % 2 == 1 { s.fillRect(col("yellow"), gx - 18, gy - 9, 2, 3) }
    s.blit(sprite("rr_gully", dazed ? 0 : Int(t * 6) % 2, remap: hit ? ["w": "r"] : nil), gx - 8, gy - 26)
    s.fillRect(col("hotpink"), gx - 2, gy - 28, 6, 2)       // captain's hat
    s.fillRect(col("hotpink"), gx, gy - 31, 3, 3)
    if dazed { rrDizzy(s, gx, gy - 32, t) }
}
