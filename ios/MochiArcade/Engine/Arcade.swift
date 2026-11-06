// Arcade kit shared by every game (port of mochi_arcade/arcade.py - keep the two in step):
// 200-stage campaign helpers, Hype (banners, combo, FEVER, jackpot, flash, hit-stop, slow-mo),
// the boss health bar and the between-stage upgrade picker.
import Foundation

let STAGES = 200
let HYPE_COLORS = ["hotpink", "orange", "yellow", "lime", "mint", "sky", "lavender"]

func isBoss(_ n: Int) -> Bool { n % 10 == 0 }
func isBonus(_ n: Int) -> Bool { n % 10 == 5 }
func checkpointOf(_ n: Int) -> Int { (n - 1) / 10 * 10 + 1 }
func tier(_ n: Int) -> Int { (n - 1) / 10 }
func checkpoints(_ reach: Int) -> [Int] { Array(stride(from: 1, through: max(1, min(reach, STAGES)), by: 10)) }
func rainbow(_ i: Int, _ t: Double = 0) -> String { HYPE_COLORS[(i + Int(t * 12)) % HYPE_COLORS.count] }
func easeOut(_ x: Double) -> Double { 1 - pow(1 - x, 3) }

final class Hype {
    static let feverTime = 8.0
    static let comboTime = 2.2

    unowned let scene: GameScene
    struct Banner { var text: String; var sub: String?; var color: String; var age: Double; var dur: Double; var rainbow: Bool; var scale: Int }
    struct Drop { var x, y, vx, vy: Double; var kind: String; var c: String; var spin: Double }
    var banners: [Banner] = []
    var flashT = 0.0, flashDur = 0.0, flashC = "white"
    var stopT = 0.0, slowT = 0.0, slowF = 1.0
    var combo = 0, comboT = 0.0, bestCombo = 0
    var fever = 0.0, feverT = 0.0
    var rain: [Drop] = []
    var t = 0.0
    var comboY = 12          // games can move the combo counter off their HUD

    init(_ scene: GameScene) { self.scene = scene }

    var feverOn: Bool { feverT > 0 }
    var mult: Int { feverOn ? 2 : 1 }

    // ------------------------------------------------------------------ events
    func banner(_ text: String, _ sub: String? = nil, color: String = "yellow", dur: Double = 1.5, rainbow rb: Bool = false,
                scale: Int = 2, sound: String? = nil) {
        banners.removeAll { $0.text == text }
        banners.append(Banner(text: text, sub: sub, color: color, age: 0, dur: dur, rainbow: rb, scale: scale))
        if let s = sound { scene.app.audio.play(s) }
    }

    func flash(_ c: String = "white", _ dur: Double = 0.18) { flashC = c; flashT = dur; flashDur = dur }
    func hitstop(_ dur: Double = 0.06) { stopT = max(stopT, dur) }
    func slowmo(_ factor: Double = 0.35, _ dur: Double = 0.7) { slowF = factor; slowT = dur }

    /// kind: confetti | coins | stars | hearts
    func shower(_ n: Int = 40, _ kind: String = "confetti") {
        for _ in 0 ..< n {
            let c = kind == "confetti" ? HYPE_COLORS.randomElement()! : (kind == "coins" ? "yellow" : "white")
            rain.append(Drop(x: .random(in: 0 ..< Double(W)), y: .random(in: -80 ..< -4), vx: .random(in: -14 ..< 14),
                             vy: .random(in: 30 ..< 70), kind: kind, c: c, spin: .random(in: 0 ..< 6)))
        }
    }

    @discardableResult
    func hit(_ n: Int = 1, fever f: Double = 0.035) -> Int {
        combo += n
        comboT = Hype.comboTime
        bestCombo = max(bestCombo, combo)
        for m in [10, 25, 50, 100, 200, 300, 500] where combo - n < m && m <= combo {
            banner("\(m) COMBO!", color: m < 50 ? "peach" : "hotpink", dur: 1.0, rainbow: m >= 100, sound: "combo")
            if m >= 50 { shower(20 + m / 5, "stars") }
        }
        feverAdd(f * Double(n))
        return combo
    }

    func comboBonus(_ base: Int) -> Int { base * min(combo, 50) }
    /// Keep the combo alive while the game decides (e.g. a chain is still resolving).
    func keepCombo() { if combo > 0 { comboT = Hype.comboTime } }
    func breakCombo() { combo = 0; comboT = 0 }

    func feverAdd(_ x: Double) {
        if feverOn { return }
        fever = min(1, fever + x)
        if fever >= 1 { startFever() }
    }

    func startFever(_ dur: Double? = nil) {
        fever = 0
        feverT = dur ?? Hype.feverTime
        banner("FEVER!!", "SCORE X2", dur: 1.6, rainbow: true, sound: "fever")
        flash("yellow", 0.25)
        shower(50, "confetti")
    }

    func jackpot(_ pts: Int = 0, sub: String? = nil) {
        banner("JACKPOT!!", sub ?? (pts > 0 ? "+\(pts * mult)" : nil), dur: 2.0, rainbow: true, sound: "jackpot")
        flash("yellow", 0.3)
        slowmo(0.4, 0.8)
        shower(80, "coins")
        if pts > 0 { scene.add(pts) }
        scene.app.shake(4, 0.4)
    }

    func lucky(_ chance: Double) -> Bool { Double.random(in: 0 ..< 1) < chance }

    // ------------------------------------------------------------------ frame
    func update(_ dt: Double) -> Double {
        t += dt
        if flashT > 0 { flashT -= dt }
        for i in banners.indices { banners[i].age += dt }
        banners.removeAll { $0.age >= $0.dur }
        for i in rain.indices { rain[i].x += rain[i].vx * dt; rain[i].y += rain[i].vy * dt; rain[i].spin += dt * 8 }
        rain.removeAll { $0.y >= Double(H + 8) }
        if stopT > 0 { stopT -= dt; return 0 }
        var gdt = dt
        if slowT > 0 { slowT -= dt; gdt = dt * slowF }
        if comboT > 0 { comboT -= gdt; if comboT <= 0 { combo = 0 } }
        if feverT > 0 {
            feverT -= gdt
            if feverT <= 0 { banner("FEVER END", color: "lavender", dur: 0.9, scale: 1) }
        }
        return gdt
    }

    func draw(_ s: Surface) {
        if feverOn {
            for i in 0 ..< 2 { s.rect(col(rainbow(i, t)), IRect(i, i, W - 2 * i, H - 2 * i), width: 1) }
            if !(feverT < 2 && Int(t * 8) % 2 == 1) { drawText(s, "FEVER", W - 3, H - 9, rainbow(0, t), align: .right) }
        }
        for d in rain {
            let xi = Int(d.x), yi = Int(d.y)
            switch d.kind {
            case "coins":
                let w = max(1, Int(abs(cos(d.spin)) * 3))
                s.fillRect(col("orange"), xi - w, yi - 3, w * 2 + 1, 7)
                s.fillRect(col("yellow"), xi - w + 1, yi - 2, max(1, w * 2 - 1), 5)
            case "stars":
                s.fillRect(col(d.c), xi, yi - 1, 1, 3); s.fillRect(col(d.c), xi - 1, yi, 3, 1)
            case "hearts":
                s.blit(sprite("heart"), xi - 3, yi - 3)
            default:
                s.fillRect(col(d.c), xi, yi, Int(d.spin) % 2 == 1 ? 2 : 1, 2)
            }
        }
        if combo >= 3 {
            let txt = "\(combo) COMBO"
            drawText(s, txt, W / 2, comboY, combo < 25 ? "peach" : rainbow(0, t), align: .center)
            let w = Int(Double(textWidth(txt)) * max(0, comboT) / Hype.comboTime)
            s.fillRect(col("peach"), W / 2 - textWidth(txt) / 2, comboY + 8, w, 1)
        }
        var slotY: Int? = nil          // the oldest keeps its place, newer ones stack below it
        for b in banners { slotY = drawBanner(s, b, below: slotY) }
        if flashT > 0 && scene.app.settings.shake {
            let a = Int(150 * flashT / max(0.01, flashDur))
            s.fillRect(col(flashC, a), 0, 0, W, H)
        }
    }

    @discardableResult
    private func drawBanner(_ s: Surface, _ b: Banner, below: Int? = nil) -> Int {
        let tin = 0.18, tout = 0.2
        let w = textWidth(b.text, b.scale)
        var x = Double(W / 2)
        if b.age < tin {
            x = Double(W) + Double(W / 2 - W) * easeOut(b.age / tin)
        } else if b.age > b.dur - tout {
            x = Double(W / 2) - Double(W / 2 + w) * easeOut((b.age - (b.dur - tout)) / tout)
        }
        var y = b.scale >= 2 ? 62 : 70
        let hh = 8 * b.scale + (b.sub == nil ? 6 : 12)
        if let bl = below { y = bl + 4 }
        s.fillRect(rgba(12, 8, 24, 150), 0, y - 4, W, hh)
        if b.rainbow {
            let x0 = Int(x) - w / 2
            for (i, ch) in b.text.enumerated() {
                let dy = Int(sin(t * 10 + Double(i) * 0.7) * 2)
                drawText(s, String(ch), x0 + i * 6 * b.scale, y + dy, rainbow(i, t), scale: b.scale, shadow: nil, outline: "ink")
            }
        } else {
            drawText(s, b.text, Int(x), y, b.color, scale: b.scale, align: .center, shadow: nil, outline: "ink")
        }
        if let sub = b.sub { drawText(s, sub, Int(x), y + 8 * b.scale + 2, "white", align: .center) }
        return y - 4 + hh
    }
}

func bossBar(_ s: Surface, _ name: String, _ hp: Double, _ maxhp: Double, _ t: Double = 0, y: Int = 2, x: Int = 60, w: Int = 200) {
    let frac = max(0, min(1, hp / max(1, maxhp)))
    panel(s, IRect(x, y, w, 12), fill: "black", border: "red", radius: 3, shadow: false)
    drawText(s, name, x + 4, y + 3, "white", shadow: nil)
    let x0 = x + 6 + textWidth(name), bw = x + w - 4 - x0
    s.fillRect(col("darkgray"), x0, y + 4, bw, 4)
    let c = frac > 0.3 || Int(t * 8) % 2 == 1 ? "red" : "yellow"
    s.fillRect(col(c), x0, y + 4, Int(Double(bw) * frac), 4)
    s.fillRect(col("pink"), x0, y + 4, Int(Double(bw) * frac), 1)
}

/// One stat/ability a player can level up between stages. icon: sprite name, or draw closure (surface, cx, cy, t).
struct Upgrade {
    let id: String
    let name: String
    let desc: String
    var color = "mint"
    var icon: String? = nil
    var draw: ((Surface, Int, Int, Double) -> Void)? = nil
    var max = 5
}

/// Overlay: choose 1 of 3 upgrade cards. onDone(id or nil) is called with the choice.
final class UpgradePick {
    unowned let scene: GameScene
    let levels: [String: Int]
    let onDone: (String?) -> Void
    let title: String
    var cards: [Upgrade]
    var i = 0, t = 0.0
    var done = false

    init(_ scene: GameScene, _ pool: [Upgrade], _ levels: [String: Int], title: String = "POWER UP!", n: Int = 3,
         _ onDone: @escaping (String?) -> Void) {
        self.scene = scene; self.levels = levels; self.onDone = onDone; self.title = title
        cards = Array(pool.filter { (levels[$0.id] ?? 0) < $0.max }.shuffled().prefix(n))
        scene.app.audio.play("levelup")
        if cards.isEmpty { done = true; onDone(nil) }
    }

    func update(_ dt: Double) {
        if done { return }
        t += dt
        let inp = scene.app.input
        if inp.hit(.left) { i = (i - 1 + cards.count) % cards.count; scene.app.audio.play("move") }
        if inp.hit(.right) { i = (i + 1) % cards.count; scene.app.audio.play("move") }
        if t > 0.4 && inp.hit(.a, .start) {
            done = true
            scene.app.audio.play("card")
            onDone(cards[i].id)
        }
    }

    /// touch: tap a card to choose it directly (canvas coordinates)
    func tap(_ x: Double, _ y: Double) {
        guard !done, t > 0.4 else { return }
        let n = cards.count, cw = 88, gap = 8
        let x0 = W / 2 - (n * cw + (n - 1) * gap) / 2
        for k in 0 ..< n where IRect(x0 + k * (cw + gap), 46, cw, 116).contains(x, y) {
            if k == i { done = true; scene.app.audio.play("card"); onDone(cards[k].id) } else { i = k; scene.app.audio.play("move") }
        }
    }

    func draw(_ s: Surface) {
        if done { return }
        s.fillRect(rgba(12, 8, 24, 190), 0, 0, W, H)
        for (k, ch) in title.enumerated() {
            let dy = Int(sin(t * 6 + Double(k) * 0.6) * 2)
            drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + k * 12, 22 + dy, rainbow(k, t), scale: 2, shadow: nil, outline: "ink")
        }
        let n = cards.count, cw = 88, gap = 8
        let x0 = W / 2 - (n * cw + (n - 1) * gap) / 2
        for (k, u) in cards.enumerated() {
            let sel = k == i
            let appear = easeOut(min(1, max(0, t * 4 - Double(k) * 0.4)))
            let x = x0 + k * (cw + gap)
            let y = 50 + Int((1 - appear) * 120) - (sel ? 4 : 0)
            panel(s, IRect(x, y, cw, 112), fill: sel ? "ink" : "night", border: sel ? u.color : "darkgray")
            if sel && Int(t * 6) % 2 == 1 { s.rect(col("white"), IRect(x - 1, y - 1, cw + 2, 114), width: 1, radius: 5) }
            let cx = x + cw / 2, cy = y + 24
            s.circle(col(u.color), cx, cy, 13)
            s.circle(col("ink"), cx, cy, 11)
            if let d = u.draw { d(s, cx, cy, t) } else if let ic = u.icon {
                let sp = sprite(ic)
                s.blit(sp, cx - sp.w / 2, cy - sp.h / 2)
            }
            drawText(s, u.name, cx, y + 44, u.color, align: .center)
            for (li, line) in u.desc.split(separator: "|").prefix(4).enumerated() {
                drawText(s, String(line), cx, y + 58 + li * 9, "white", align: .center, shadow: nil)
            }
            let lv = levels[u.id] ?? 0
            for p in 0 ..< u.max {
                let c = p < lv ? "yellow" : (p == lv ? "lime" : "darkgray")
                s.fillRect(col(c), cx - u.max * 4 + p * 8 + 1, y + 100, 6, 4)
            }
        }
        drawText(s, "TAP A CARD - TAP AGAIN TO TAKE IT", W / 2, H - 12, "lavender", align: .center, shadow: nil)
    }
}

/// Per-game data exported from the Python sources (EXPORT in each game module, see ios/tools/gen_data.py).
enum GameData {
    private static var cache: [String: Any] = [:]
    static func json(_ id: String) -> Any? {
        if let c = cache[id] { return c }
        guard let s = GData.gameData[id], let d = s.data(using: .utf8),
              let v = try? JSONSerialization.jsonObject(with: d) else { return nil }
        cache[id] = v
        return v
    }
}
