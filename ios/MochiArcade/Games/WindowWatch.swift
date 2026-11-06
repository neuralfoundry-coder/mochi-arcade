// WINDOW WATCH - Maru, a very round cat on the windowsill, guards the fishbowls (port of games/window_watch.py).
// Swat things out of the sky: the paw-puff ring catches them and every catch chain-catches its neighbours.
// On touch screens the player taps right where to swat; MEOW is the smart bomb. 200 stages read from the
// exported campaign (games/window_watch_stages.py), art in WindowWatchArt.swift, bosses in WindowWatchBoss.swift.
import Foundation

let WW_TOPY = 14
private let CUR_X0 = 6.0, CUR_X1 = Double(W - 6), CUR_Y0 = 28.0, CUR_Y1 = 168.0
private let LIFE_AT = [30000, 80000, 160000, 300000]         // then every 200000
private let LINEAR = ["drop", "mini", "dart", "hail", "star", "orb", "feather"]
private let SWAY = ["leaf", "bug", "seed", "food", "bubble", "puff", "cap", "treat"]
private let AIMED = LINEAR + ["snow", "leaf", "bug", "seed", "food", "bubble", "puff"]
private let WIND_AFF: [String: Double] = ["leaf": 1.0, "seed": 1.0, "food": 0.8, "cap": 0.6, "bubble": 0.7, "puff": 0.9,
                                          "drop": 0.45, "bug": 0.3, "snow": 0.3, "hail": 0.25, "mini": 0.5, "moth": 0.3,
                                          "feather": 0.6]
private let POWERS: [String: (String, String, String?)] = [
    "N": ("lime", "CATNIP FRENZY!", "FREE BIG SWATS"), "T": ("orange", "FISH TREAT!", "+1 MEOW"),
    "S": ("sky", "SNOOZY SKY", "EVERYTHING SLOWS"), "H": ("pink", "FRESH WATER!", "BOWLS REFILLED"),
    "$": ("yellow", "LUCKY COIN!", nil)]
private let MARU_LINES = ["MARU IS ON WATCH!", "MARU: NOT MY FISHIES!", "MARU WIGGLES... READY!", "MARU: MRRP!",
                          "MARU STRETCHES HER PAWS", "MARU: THE SKY LOOKS SNEAKY", "MARU FLUFFS UP!", "MARU: PURR... FOCUS."]
private let BONUS_SUB = ["treats": "SWATS ARE FREE - CATCH THEM ALL!", "bubbles": "POP THE PARTY BUBBLES!",
                         "fireflies": "CHAIN THE FIREFLIES!"]

// ----------------------------------------------------------------------------- campaign data (EXPORT)
struct WWKind { let r: Int; let pts: Int; let hp: Int; let speed: Double; let harm: Bool }
struct WWEvent { let t: Double; let k: String; let x, y: Double; let tg: Int; let v, p, q: Double }
struct WWBossSpec { let kind, name: String; let hp: Int; let rate: Double; let attacks, extra: [String]; let tier, phases: Int }
struct WWTheme { let name, top, bottom, curtain: String; let deco: [String]; let song: String }
struct WWStage {
    let n: Int, kind: String, tier: Int, theme: Int, name: String, newLine: String
    let speed: Double, wind: Double, treasures: [String], events: [WWEvent], time: Double, bonus: String
    let boss: WWBossSpec?
}

enum WWData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static let root: [String: Any] = (GameData.json("window_watch") as? [String: Any]) ?? [:]

    static let kinds: [String: WWKind] = {
        var d: [String: WWKind] = [:]
        for (k, v) in (root["kinds"] as? [String: [Any]]) ?? [:] where v.count >= 5 {
            d[k] = WWKind(r: Int(num(v[0])), pts: Int(num(v[1])), hp: Int(num(v[2])), speed: num(v[3]),
                          harm: (v[4] as? Bool) ?? ((v[4] as? NSNumber)?.boolValue ?? false))
        }
        return d
    }()
    static func kind(_ k: String) -> WWKind { kinds[k] ?? WWKind(r: 3, pts: 0, hp: 1, speed: 0, harm: false) }

    static let treasures: [String: (hw: Int, top: Int, hp: Int)] = {
        var d: [String: (hw: Int, top: Int, hp: Int)] = [:]
        for (k, v) in (root["treasures"] as? [String: [Any]]) ?? [:] where v.count >= 3 {
            d[k] = (Int(num(v[0])), Int(num(v[1])), Int(num(v[2])))
        }
        return d
    }()

    static let slots: [Int] = ((root["slots"] as? [Any]) ?? [64, 160, 256]).map { Int(num($0)) }

    static let themes: [WWTheme] = ((root["themes"] as? [[Any]]) ?? []).map { a in
        WWTheme(name: a[0] as? String ?? "", top: a[1] as? String ?? "sky", bottom: a[2] as? String ?? "cream",
                curtain: a[3] as? String ?? "pink", deco: a[4] as? [String] ?? [], song: a[5] as? String ?? "ww_sill")
    }

    static let stages: [WWStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: WWBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = WWBossSpec(kind: b["kind"] as? String ?? "cloud", name: b["name"] as? String ?? "", hp: Int(num(b["hp"])),
                              rate: num(b["rate"]), attacks: b["attacks"] as? [String] ?? [], extra: b["extra"] as? [String] ?? [],
                              tier: Int(num(b["tier"])), phases: Int(num(b["phases"])))
        }
        let events: [WWEvent] = ((d["events"] as? [[Any]]) ?? []).map { e in
            WWEvent(t: num(e[0]), k: e[1] as? String ?? "drop", x: num(e[2]), y: num(e[3]), tg: Int(num(e[4])),
                    v: num(e[5]), p: num(e[6]), q: num(e[7]))
        }
        return WWStage(n: Int(num(d["n"])), kind: d["kind"] as? String ?? "normal", tier: Int(num(d["tier"])),
                       theme: Int(num(d["theme"])), name: d["name"] as? String ?? "", newLine: d["new"] as? String ?? "",
                       speed: num(d["speed"]), wind: num(d["wind"]), treasures: d["treasures"] as? [String] ?? ["bowl", "bowl", "bowl"],
                       events: events, time: num(d["time"]), bonus: d["bonus"] as? String ?? "", boss: boss)
    }
}

// ----------------------------------------------------------------------------- upgrade cards
let WW_UPGRADES: [Upgrade] = [
    Upgrade(id: "paw", name: "BIG PAW", desc: "A WIDER|SWAT RING", color: "white", draw: { s, cx, cy, t in
        s.circle(col("white"), cx, cy, 6 + Int(sin(t * 4) * 2), width: 1)
        s.blit(sprite("ww_paw"), cx - 4, cy - 4)
    }, max: 4),
    Upgrade(id: "quick", name: "QUICK PAWS", desc: "PAW ENERGY|REFILLS|FASTER", color: "mint", draw: { s, cx, cy, t in
        for i in 0 ..< 4 {
            let on = i <= Int(t * 4) % 5
            s.blit(sprite("ww_pawicon", remap: on ? nil : ["w": "d"]), cx - 10 + i * 5, cy - 2)
        }
    }, max: 3),
    Upgrade(id: "stamina", name: "MORE PAWS", desc: "+1 MAX|PAW ENERGY", color: "lime", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.blit(sprite("ww_pawicon", remap: i == 2 && Int(t * 3) % 2 == 1 ? ["w": "l"] : nil), cx - 2, cy - 7 + i * 5) }
    }, max: 3),
    Upgrade(id: "chain", name: "CHAIN PURR", desc: "BIGGER|CHAIN RINGS", color: "hotpink", draw: { s, cx, cy, t in
        for i in 0 ..< 3 {
            s.circle(col(["hotpink", "pink", "peach"][i]), cx - 5 + i * 5, cy + (i % 2 == 1 ? 1 : -1) * 2,
                     3 + (Int(t * 4) % 3 == i ? 1 : 0), width: 1)
        }
    }, max: 3),
    Upgrade(id: "meow", name: "LOUD MEOW", desc: "+1 MEOW NOW|+1 MEOW|STOCK", color: "orange", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col("orange"), cx, cy, 3 + i * 3 + Int(t * 6) % 3, width: 1) }
        s.fillRect(col("white"), cx - 1, cy - 1, 3, 3)
    }, max: 3),
    Upgrade(id: "glass", name: "BUBBLE GUARD", desc: "A SHIELD ON|EVERY BOWL|EACH STAGE", color: "sky", draw: { s, cx, cy, t in
        s.circle(col("sky"), cx, cy + 1, 5)
        WWArt.discBelow(s, cx, cy + 1, 4, cy + 1, "blue")
        s.circle(col(Int(t * 4) % 2 == 1 ? "mint" : "white"), cx, cy, 9, width: 1)
    }, max: 2),
    Upgrade(id: "whisker", name: "WHISKER SENSE", desc: "SWATS SNAP|TO THINGS|NEARBY", color: "lavender", draw: { s, cx, cy, _ in
        for side in [-1, 1] {
            for k in [-2, 0, 2] { s.fillRect(col("white"), cx + (side > 0 ? 2 : -8), cy + k + wwDiv(k, 2) * side, 6, 1) }
        }
        s.fillRect(col("pink"), cx - 1, cy - 1, 3, 2)
    }, max: 3),
    Upgrade(id: "calm", name: "CALM SKY", desc: "THINGS FALL|A BIT|SLOWER", color: "teal", draw: { s, cx, cy, t in
        s.blit(sprite("ww_drop"), cx - 3, cy - 6 + Int(t * 3) % 4)
        for i in 0 ..< 3 { s.fillRect(col("teal"), cx - 6 + i * 6, cy + 6, 3, 1) }
    }, max: 3),
    Upgrade(id: "luck", name: "LUCKY CAT", desc: "MORE GIFTS|AND|JACKPOTS", color: "yellow", draw: { s, cx, cy, t in
        let w = max(1, Int(abs(cos(t * 3)) * 5))
        s.ellipse(col("orange"), cx - w, cy - 5, w * 2 + 1, 11)
        s.ellipse(col("yellow"), cx - w + 1, cy - 4, max(1, w * 2 - 1), 9)
    }, max: 3),
    Upgrade(id: "fever", name: "FEVER PURR", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "pink", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
    Upgrade(id: "life", name: "EXTRA LIFE", desc: "+1 LIFE|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
]

// ----------------------------------------------------------------------------- objects
/// Anything that falls or flies in (threats, gifts, fish food, bonus treats).
final class WWThing {
    let id: Int
    let k: String
    var x, y, bx, by: Double
    var vx = 0.0, vy = 0.0
    var v, p, q: Double
    var tg: Int
    let r, pts: Int
    var hp: Int
    let harm: Bool
    var age = 0.0, mt = 0.0, flash = 0.0
    var mode = 0
    var dead = false
    var side = 1
    var letter = ""
    init(_ id: Int, _ k: String, _ x: Double, _ y: Double, _ tg: Int, _ v: Double, _ p: Double, _ q: Double) {
        let kd = WWData.kind(k)
        self.id = id; self.k = k
        self.x = x; self.y = y; bx = x; by = y
        self.v = v; self.p = p; self.q = q; self.tg = tg
        r = kd.r; pts = kd.pts; hp = kd.hp; harm = kd.harm
    }
}

final class WWTreasure {
    let kind: String
    let x: Double
    let hw, top, maxhp: Int
    var hp: Int
    var shield: Int
    var flash = 0.0, wobble = 0.0
    init(_ kind: String, _ x: Double, _ shield: Int) {
        let d = WWData.treasures[kind] ?? (11, 150, 3)
        self.kind = kind; self.x = x
        hw = d.hw; top = d.top; hp = d.hp; maxhp = d.hp
        self.shield = shield
    }
}

/// One swat and every chain it set off.
final class WWGroup { var count = 0 }

final class WWRing {
    let x, y, rmax: Double
    let depth: Int
    let g: WWGroup
    let kind: String
    let dur, hold: Double
    var age = 0.0, r = 0.0
    var hits = Set<Int>()
    var bossHit = false
    var fever = false
    init(_ x: Double, _ y: Double, _ rmax: Double, _ depth: Int, _ g: WWGroup, _ kind: String, _ dur: Double, _ hold: Double) {
        self.x = x; self.y = y; self.rmax = rmax; self.depth = depth; self.g = g; self.kind = kind; self.dur = dur; self.hold = hold
    }
}

struct WWStamp { var x, y, age: Double; var tired: Bool }

private func tri(_ x: Double) -> Double { 2 * abs(2 * (x - (x + 0.5).rounded(.down))) - 1 }

private func pickWeighted(_ opts: [String], _ weights: [Double]) -> String {
    let total = weights.reduce(0, +)
    var r = Double.random(in: 0 ... total)
    for (o, w) in zip(opts, weights) {
        r -= w
        if r <= 0 && w > 0 { return o }
    }
    return opts.last!
}

// ----------------------------------------------------------------------------- the game
final class WindowWatch: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["TAP   SWAT RIGHT THERE (THE RING CHAINS)", "MEOW  MEOW SHOUT - CLEARS THE SKY"]
    static let helpSkip = 3

    override var music: String? { song() }
    override var buttons: [Action: String] { [.b: "MEOW"] }
    override var buttonOrder: [Action] { [.b, .a] }
    override var fourWay: Bool { false }
    override var wantsTaps: Bool { true }

    let diffSpeed: Double
    var lives: Int
    var levels: [String: Int] = [:]
    var cx = Double(W) / 2, cy = 110.0, chold = 0.0
    var mx = Double(W) / 2
    var walking = false
    var happyT = 0.0, hurtT = 0.0, meowT = 0.0, tiredT = 0.0, swatT = 0.0
    var swatSide = 1
    var meows = 2
    var energy = 4.0
    var swatCd = 0.0
    var lifeI = 0
    var uid = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    var wasFever = false
    var lightning = 0.0
    var gustT = 0.0, gustDir = 1
    var tapped = false, tappedNow = false
    // stage
    var n = 1
    var st: WWStage = WWData.stages[0]
    var tier = 0
    var theme: WWTheme = WWData.themes[0]
    var sky = Surface(W, H)
    var treasures: [WWTreasure] = []
    var events: [WWEvent] = []
    var ei = 0
    var things: [WWThing] = []
    var rings: [WWRing] = []
    var stamps: [WWStamp] = []
    var boss: WWBoss?
    var stime = 0.0, windNow = 0.0
    var frenzyT = 0.0, snoozeT = 0.0
    var splashed = false
    var wasted = 0, caught = 0, bestChain = 0, total = 0
    var bonusLeft = 0.0
    var goldAt = -1.0
    var state = "intro"
    var stateT = 0.0, introLen = 2.4
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        diffSpeed = SPEEDS[d] ?? 1
        lives = LIVES[d] ?? 3
        super.init(app, info, opt)
        hype.comboTime = 2.6
        hype.comboY = 30
        let start = max(1, min(STAGES, optInt("stage", optInt("start", 1))))
        startStage(start)
        if start > 10 {          // starting from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (start - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    static func preview(_ s: Surface, _ t: Double) { WWArt.preview(s, t) }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func factor(_ pts: Int) -> Int { pts * (10 + tier) / 10 }
    @discardableResult
    func scoreAt(_ pts: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int { add(factor(pts), x, y, c) }
    func emax() -> Int { 4 + lv("stamina") }
    func meowMax() -> Int { 3 + lv("meow") }
    func regen() -> Double { 0.6 * pow(0.82, Double(lv("quick"))) }
    func freeSwats() -> Bool { frenzyT > 0 || hype.feverOn || st.kind == "bonus" }
    func swatR() -> Double {
        var r = Double(13 + 3 * lv("paw"))
        if frenzyT > 0 { r *= 1.4 }
        if hype.feverOn { r *= 1.25 }
        return r
    }
    func chainR() -> Double { Double(9 + 2 * lv("chain") + (hype.feverOn ? 2 : 0)) }
    func feverGain() -> Double { 0.03 * (1 + 0.35 * Double(lv("fever"))) }
    func speedMul() -> Double { diffSpeed * (1 - 0.07 * Double(lv("calm"))) }
    func song() -> String { st.kind == "boss" ? "boss" : (st.kind == "bonus" ? "bonus" : theme.song) }

    func nearestSlot(_ x: Double) -> Int {
        var best = 0, bd = 1e9
        for i in 0 ..< 3 {
            let d = abs(Double(WWData.slots[i]) - x)
            if d < bd { best = i; bd = d }
        }
        return best
    }

    /// tg, or the nearest treasure that still has water.
    func aliveTarget(_ tg: Int) -> Int {
        if treasures[tg].hp > 0 { return tg }
        var best = tg, bd = 1e9
        for (i, tr) in treasures.enumerated() where tr.hp > 0 && abs(tr.x - treasures[tg].x) < bd {
            best = i; bd = abs(tr.x - treasures[tg].x)
        }
        return best
    }

    func aim(_ th: WWThing, _ speed: Double, _ ax: Double? = nil) {
        let tr = treasures[th.tg]
        let tx = ax ?? tr.x, ty = Double(tr.top + 4)
        let dx = tx - th.bx, dy = ty - th.by
        var d = hypot(dx, dy)
        if d == 0 { d = 1 }
        th.vx = dx / d * speed
        th.vy = dy / d * speed
    }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        n = num
        st = WWData.stages[num - 1]
        tier = st.tier
        theme = WWData.themes[min(st.theme, WWData.themes.count - 1)]
        reached(num)
        sky = WWArt.makeSky(theme, st.theme)
        treasures = st.treasures.enumerated().map { WWTreasure($0.element, Double(WWData.slots[$0.offset]), lv("glass")) }
        events = st.events
        ei = 0
        things = []; rings = []; stamps = []
        boss = st.boss.map { WWBoss(self, $0) }
        stime = 0; windNow = 0
        frenzyT = 0; snoozeT = 0
        gustT = 0
        lightning = 0
        splashed = false
        wasted = 0; caught = 0; bestChain = 0
        total = st.kind != "bonus" ? events.filter { WWData.kind($0.k).harm }.count : events.count
        bonusLeft = st.time
        energy = Double(emax())
        let last = events.last?.t ?? 10
        goldAt = -1
        if st.kind == "normal" && hype.lucky(0.025 + 0.012 * Double(lv("luck"))) { goldAt = Double.random(in: 0.3 ... 0.75) * last }
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.0 : 2.4
        tally = []
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    // ---------------------------------------------------------------- spawning
    @discardableResult
    func spawn(_ k: String, _ x: Double, _ y: Double, _ tg: Int, _ v: Double, _ p: Double = 0, _ q: Double = 0, ax: Double? = nil) -> WWThing {
        uid += 1
        let th = WWThing(uid, k, x, y, tg, v * speedMul(), p, q)
        th.tg = aliveTarget(tg)
        th.side = x < Double(W) / 2 ? 1 : -1
        if AIMED.contains(k) {
            aim(th, th.v, ax)
        } else if k == "cap" || k == "treat" {
            th.vy = th.v
        } else if k == "rocket" {
            th.vy = -th.v
        } else if k == "gold" {
            th.side = p >= 0 ? 1 : -1
        }
        if k == "cap" { th.letter = rollPower() }
        things.append(th)
        return th
    }

    func spawnEvent(_ e: WWEvent) { spawn(e.k, e.x, e.y, e.tg, e.v, e.p, e.q) }

    /// A firework spark on a falling arc that lands on treasure tg (off = miss by that many pixels).
    @discardableResult
    func spark(_ x: Double, _ y: Double, _ tg: Int, _ off: Double) -> WWThing {
        let g = 70 * st.speed * speedMul()
        let tr = treasures[tg]
        let tx = tr.x + off, ty = Double(tr.top + 4)
        let vy0 = -Double.random(in: 20 ... 50)
        let dy = max(4.0, ty - y)
        let tt = (-vy0 + (vy0 * vy0 + 2 * g * dy).squareRoot()) / g
        let th = spawn("spark", x, y, tg, 1.0)
        th.vx = (tx - x) / tt
        th.vy = vy0
        th.p = g
        return th
    }

    func rollPower() -> String {
        let hurt = treasures.contains { $0.hp < $0.maxhp }
        return pickWeighted(["N", "T", "S", "H", "$"], [3, 2, 2, hurt ? 3 : 1, Double(2 + lv("luck"))])
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        tappedNow = tapped
        tapped = false
        moveCursor(dt)
        updateMaru(dt)
        for tr in treasures { tr.flash = max(0, tr.flash - dt); tr.wobble = max(0, tr.wobble - dt) }
        lightning = max(0, lightning - dt)
        switch state {
        case "intro":
            boss?.update(dt)
            if stateT > introLen || (stateT > 0.5 && (app.input.hit(.a) || tappedNow)) {
                state = "play"
                stateT = 0
                boss?.state = "fight"
            }
        case "play":
            play(dt)
        case "clear":
            updateRings(dt)
            updateStamps(dt)
            boss?.update(dt)
            if stateT > 1.6 { beginTally() }
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(WW_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        case "oops":
            updateStamps(dt)
            if stateT > 2.4 { startStage(n) }
        default:
            break
        }
    }

    func onPick(_ id: String?) {
        guard let id = id, let u = WW_UPGRADES.first(where: { $0.id == id }) else { return }
        levels[id] = lv(id) + 1
        hype.banner(u.name, "LEVEL \(levels[id]!)", color: u.color, dur: 1.2, scale: 1)
        switch id {
        case "life": lives += 1; app.audio.play("extra")
        case "meow": meows = min(meowMax(), meows + 1)
        case "glass": for tr in treasures { tr.shield = lv("glass") }
        case "stamina": energy = Double(emax())
        default: break
        }
    }

    /// Touch: swat right where the finger lands (also skips the stage card and the tally).
    override func onTap(_ x: Double, _ y: Double) {
        cx = max(CUR_X0, min(CUR_X1, x))
        cy = max(CUR_Y0, min(CUR_Y1, y))
        tapped = true
        if state == "play" { swat() }
    }

    func moveCursor(_ dt: Double) {
        let inp = app.input
        let dx = (inp.down(.right) ? 1.0 : 0) - (inp.down(.left) ? 1.0 : 0)
        let dy = (inp.down(.down) ? 1.0 : 0) - (inp.down(.up) ? 1.0 : 0)
        if dx != 0 || dy != 0 { chold += dt } else { chold = 0 }
        var v = 120 + min(1, chold / 0.25) * 120
        if dx != 0 && dy != 0 { v *= 0.75 }
        cx = max(CUR_X0, min(CUR_X1, cx + dx * v * dt))
        cy = max(CUR_Y0, min(CUR_Y1, cy + dy * v * dt))
    }

    func updateMaru(_ dt: Double) {
        happyT = max(0, happyT - dt); hurtT = max(0, hurtT - dt); meowT = max(0, meowT - dt)
        tiredT = max(0, tiredT - dt); swatT = max(0, swatT - dt)
        let tx = max(20, min(Double(W) - 20, cx))
        let d = tx - mx
        walking = abs(d) > 3 && meowT <= 0
        if walking { mx += max(-70 * dt, min(70 * dt, d)) }
    }

    func play(_ dt: Double) {
        let inp = app.input
        stime += dt
        swatCd = max(0, swatCd - dt)
        frenzyT = max(0, frenzyT - dt)
        snoozeT = max(0, snoozeT - dt)
        gustT = max(0, gustT - dt)
        if energy < Double(emax()) { energy = min(Double(emax()), energy + dt / regen()) }
        windNow = st.wind * (0.6 + 0.4 * sin(stime * 0.5))
        if gustT > 0 { windNow += Double(gustDir) * 55 }
        if inp.hit(.a) { swat() }
        if inp.hit(.b) { meow() }
        while ei < events.count && events[ei].t <= stime {
            spawnEvent(events[ei])
            ei += 1
        }
        if goldAt > 0 && goldAt <= stime {
            goldAt = -1
            let side = [-1, 1].randomElement()!
            spawn("gold", side > 0 ? -10 : 330, Double.random(in: 40 ... 90), 0, 78, Double(side), 0)
            hype.banner("GOLDEN FISH!", "SWAT IT!", color: "yellow", dur: 1.2, scale: 1, sound: "coin")
        }
        if let b = boss {
            b.update(dt)
            if b.state == "dead" && state == "play" { bossDefeated() }
        }
        let tdt = dt * (snoozeT > 0 ? 0.5 : 1.0)
        for th in things {
            if state != "play" { break }
            if !th.dead { moveThing(th, tdt) }
        }
        updateRings(dt)
        things.removeAll { $0.dead }
        updateStamps(dt)
        checkLife()
        if hype.feverOn && !wasFever {
            hype.feverT += 1.5 * Double(lv("fever"))
            app.audio.music("fever")
        } else if wasFever && !hype.feverOn {
            app.audio.music(song())
        }
        wasFever = hype.feverOn
        if state != "play" { return }
        if st.kind == "bonus" {
            bonusLeft -= dt
            if bonusLeft <= 0 || (ei >= events.count && things.isEmpty) {
                if bonusLeft <= 0 { hype.banner("TIME UP!", color: "yellow", dur: 1.2) }
                stageClear()
            }
        } else if st.kind == "normal" && ei >= events.count && !things.contains(where: { $0.harm }) {
            stageClear()
        }
    }

    // ---------------------------------------------------------------- things
    func moveThing(_ th: WWThing, _ dt: Double) {
        th.age += dt
        th.flash = max(0, th.flash - dt)
        let k = th.k
        let w = windNow * (WIND_AFF[k] ?? 0.15)
        if LINEAR.contains(k) {
            th.x += (th.vx + w) * dt
            th.y += th.vy * dt
        } else if k == "snow" {
            let f = min(2.2, 1 + th.age * 0.45)
            th.x += (th.vx * f + w) * dt
            th.y += th.vy * f * dt
        } else if SWAY.contains(k) {
            th.bx += (th.vx + w) * dt
            th.by += th.vy * dt
            let off: Double
            switch k {
            case "leaf": off = th.p * sin(th.age * 2.2 + th.q)
            case "bug": off = th.p * tri(th.age * 1.3 + th.q)
            case "bubble", "puff": off = 5 * sin(th.age * 1.2 + th.q)
            case "treat": off = 0
            default: off = th.p * sin(th.age * 1.6 + th.q)
            }
            var sp = hypot(th.vx, th.vy)
            if sp == 0 { sp = 1 }
            th.x = th.bx - th.vy / sp * off
            th.y = th.by + th.vx / sp * off
            if (k == "bubble" || k == "puff") && th.y >= th.p {
                split(th)
                return
            }
        } else if k == "crow" {
            if th.mode == 0 {
                th.x += Double(th.side) * th.v * dt
                th.y += sin(th.age * 5) * 8 * dt
                th.vx = Double(th.side) * th.v
                if (th.side > 0 && th.x >= th.p) || (th.side < 0 && th.x <= th.p) {
                    th.mode = 1; th.mt = 0
                    app.audio.play("back")
                }
            } else if th.mode == 1 {
                th.mt += dt
                th.y -= 8 * dt
                if th.mt >= 0.5 {
                    th.mode = 2
                    th.bx = th.x; th.by = th.y
                    th.tg = aliveTarget(th.tg)
                    aim(th, th.v * 1.9)
                }
            } else {
                th.x += th.vx * dt
                th.y += th.vy * dt
            }
        } else if k == "plane" {
            if th.mode == 0 {
                th.x += Double(th.side) * th.v * dt
                th.y += (sin(th.age * 3) * 10 + 6) * dt
                th.vx = Double(th.side) * th.v
                th.vy = cos(th.age * 3) * 30
                if (th.side > 0 && th.x >= th.p) || (th.side < 0 && th.x <= th.p) {
                    th.mode = 1; th.mt = 0
                    th.bx = th.x; th.by = th.y - 14
                }
            } else if th.mode == 1 {
                th.mt += dt
                let a = th.mt * 6.0
                th.x = th.bx + sin(a) * 14 * Double(th.side)
                th.y = th.by + cos(a) * 14
                th.vx = cos(a) * 84 * Double(th.side)
                th.vy = -sin(a) * 84
                if a >= 2 * .pi {
                    th.mode = 2
                    th.bx = th.x; th.by = th.y
                    th.tg = aliveTarget(th.tg)
                    aim(th, th.v * 1.5)
                }
            } else {
                th.x += th.vx * dt
                th.y += th.vy * dt
            }
        } else if k == "moth" {
            if th.mode == 0 {
                th.mt += dt
                let dx = cx - th.x, dy = min(cy, 140) - th.y
                var d = hypot(dx, dy)
                if d == 0 { d = 1 }
                let sp = th.v * 0.8
                let f = min(1, dt * 2)
                th.vx += (dx / d * sp - th.vx) * f
                th.vy += (dy / d * sp - th.vy) * f
                th.x += th.vx * dt + cos(th.age * 7) * 20 * dt
                th.y += th.vy * dt + sin(th.age * 11) * 14 * dt
                if th.mt >= th.p {
                    th.mode = 1
                    th.bx = th.x; th.by = th.y
                    th.tg = aliveTarget(th.tg)
                    aim(th, th.v * 1.5)
                }
            } else {
                th.x += th.vx * dt
                th.y += th.vy * dt
            }
        } else if k == "rocket" {
            th.y += th.vy * dt
            if th.y <= th.p { burst(th); return }
        } else if k == "spark" {
            th.vy += th.p * dt
            th.x += th.vx * dt
            th.y += th.vy * dt
        } else if k == "gold" {
            th.x += Double(th.side) * th.v * dt
            th.y = th.by + sin(th.age * 5) * 14
        } else if k == "fly" {
            let a = th.q + th.age * th.v
            if th.age > 6 { th.by -= 50 * dt } else { th.bx += sin(th.age * 0.7 + th.q) * 10 * dt }
            th.x = th.bx + cos(a) * th.p
            th.y = th.by + sin(a) * th.p * 0.7
        } else if k == "rise" {
            th.y -= th.v * dt
            th.x = th.bx + sin(th.age * 2 + th.q) * th.p
        }
        // landing / leaving
        if th.harm && k != "rocket" {
            for (i, tr) in treasures.enumerated() where tr.hp > 0 && th.y >= Double(tr.top - 2) && abs(th.x - tr.x) <= Double(tr.hw + th.r) {
                th.dead = true
                hitTreasure(i, th.x, th.y)
                return
            }
        } else if k == "food" {
            for tr in treasures where th.y >= Double(tr.top - 2) && abs(th.x - tr.x) <= Double(tr.hw + th.r) {
                th.dead = true
                feed(tr, th)
                return
            }
        }
        if th.y > Double(WW_SILL + 2) && k != "rocket" && k != "rise" && k != "fly" {
            th.dead = true
            if th.harm { parts.burst(th.x, Double(WW_SILL), 4, WWArt.kindColors[k] ?? ["white"], 25, 0.3) }
        } else if th.x < -40 || th.x > Double(W + 40) || th.y < -40 || (k == "rise" && th.y < 26) {
            th.dead = true
            if k == "rise" { parts.burst(th.x, th.y, 4, ["white", "sky"], 20, 0.3) }
        }
    }

    func split(_ th: WWThing) {
        th.dead = true
        app.audio.play("bubble")
        parts.burst(th.x, th.y, 8, ["white", "sky"], 40, 0.4)
        let sp = st.speed
        if th.k == "bubble" {
            for i in 0 ..< 3 { spawn("mini", th.x + Double(i - 1) * 4, th.y, aliveTarget(i), WWData.kind("mini").speed * sp) }
        } else {
            for i in 0 ..< 5 {
                spawn("seed", th.x + Double(i - 2) * 3, th.y, aliveTarget(Int.random(in: 0 ..< 3)), WWData.kind("seed").speed * sp,
                      Double.random(in: 4 ... 9), Double.random(in: 0 ... 6))
            }
        }
    }

    func burst(_ th: WWThing) {
        th.dead = true
        app.audio.play("explode")
        parts.burst(th.x, th.y, 16, ["yellow", "hotpink", "white", "mint"], 70, 0.6)
        for i in 0 ..< 5 {
            let tgt = aliveTarget((th.tg + i) % 3)
            spark(th.x, th.y, tgt, i >= 3 ? Double.random(in: -28 ... 28) : Double.random(in: -6 ... 6))
        }
    }

    func hitTreasure(_ i: Int, _ x: Double, _ y: Double) {
        let tr = treasures[i]
        tr.flash = 0.4
        tr.wobble = 0.3
        if tr.shield > 0 {
            tr.shield -= 1
            floats.add(tr.x, Double(tr.top - 10), "BLOCK!", "mint")
            app.audio.play("tin")
            parts.burst(x, y, 8, ["mint", "white"], 40, 0.4)
            return
        }
        tr.hp -= 1
        splashed = true
        hype.breakCombo()
        hurtT = 0.8
        app.audio.play("hurt")
        app.shake(3, 0.3)
        parts.burst(tr.x, Double(tr.top + 4), 14, ["sky", "blue", "white"], 70, 0.6)
        floats.add(tr.x, Double(tr.top - 10), "SPLASH!", "sky")
        if tr.hp <= 0 {
            hype.banner("OH NO!", "A BOWL RAN DRY", color: "pink", dur: 1.0, scale: 1)
            if treasures.allSatisfy({ $0.hp <= 0 }) { loseLife() }
        }
    }

    func bossHitsTreasure(_ i: Int) {
        let tr = treasures[i]
        if tr.hp > 0 || tr.shield > 0 { hitTreasure(i, tr.x, Double(tr.top)) }
    }

    func feed(_ tr: WWTreasure, _ th: WWThing) {
        if tr.hp <= 0 { return }
        if tr.hp < tr.maxhp {
            tr.hp += 1
            floats.add(tr.x, Double(tr.top - 10), "YUM! +WATER", "lime")
        } else {
            scoreAt(300, tr.x, Double(tr.top - 10), "lime")
            floats.add(tr.x, Double(tr.top - 18), "YUM!", "lime")
        }
        app.audio.play("eat")
        happyT = max(happyT, 0.6)
        parts.burst(tr.x, Double(tr.top), 8, ["orange", "yellow", "lime"], 30, 0.5)
    }

    // ---------------------------------------------------------------- swats
    func swat() {
        if state != "play" || swatCd > 0 { return }
        var x = cx, y = cy
        if !freeSwats() {
            if energy < 1 {
                swatCd = 0.2
                tiredT = 0.6
                app.audio.play("move")
                stamps.append(WWStamp(x: x, y: y, age: 0, tired: true))
                return
            }
            energy -= 1
        }
        let snap = lv("whisker") > 0 ? Double(6 + 5 * lv("whisker")) : 0
        if snap > 0 {
            var best: WWThing?, bd = 1e9
            for th in things where !th.dead && th.k != "food" {
                let d = hypot(th.x - x, th.y - y)
                if d < bd { best = th; bd = d }
            }
            if let b = best, bd <= swatR() + snap {
                let f = min(1, snap / max(1, bd))
                x += (b.x - x) * f
                y += (b.y - y) * f
            }
        }
        let rg = WWRing(x, y, swatR(), 0, WWGroup(), "swat", 0.15, 0.08)
        rg.fever = hype.feverOn
        rings.append(rg)
        stamps.append(WWStamp(x: x, y: y, age: 0, tired: false))
        swatCd = 0.1
        swatT = 0.25
        swatSide = x < mx ? -1 : 1
        app.audio.play("paddle")
    }

    func meow() {
        if state != "play" || meowT > 0 { return }
        if meows <= 0 {
            floats.add(mx, Double(WW_SILL - 30), "NO MEOW LEFT", "gray")
            app.audio.play("back")
            return
        }
        meows -= 1
        meowT = 1.0
        rings.append(WWRing(mx, Double(WW_SILL - 14), 360, 0, WWGroup(), "meow", 0.8, 0))
        hype.banner("MEOW!!", color: "pink", dur: 0.9)
        hype.flash("white", 0.25)
        app.shake(5, 0.5)
        app.audio.play("boom")
    }

    func updateRings(_ dt: Double) {
        var i = 0
        while i < rings.count {
            let rg = rings[i]
            i += 1
            rg.age += dt
            rg.r = rg.rmax * easeOut(min(1, rg.age / rg.dur))
            if rg.age > rg.dur + rg.hold { continue }
            for th in things {
                if th.dead || rg.hits.contains(th.id) || (rg.kind == "meow" && th.k == "food") { continue }
                let dx = th.x - rg.x, dy = th.y - rg.y
                let rr = rg.r + Double(th.r)
                if dx * dx + dy * dy <= rr * rr {
                    rg.hits.insert(th.id)
                    catchThing(th, rg)
                }
            }
            if let b = boss, !rg.bossHit, b.hittable() {
                let dx = b.x - rg.x, dy = b.y - rg.y
                let rr = rg.r + Double(b.r)
                if dx * dx + dy * dy <= rr * rr {
                    rg.bossHit = true
                    hitBoss(rg)
                }
            }
        }
        rings.removeAll { $0.age >= $0.dur + $0.hold + 0.18 }
    }

    func updateStamps(_ dt: Double) {
        for i in stamps.indices { stamps[i].age += dt }
        stamps.removeAll { $0.age >= 0.35 }
    }

    func catchThing(_ th: WWThing, _ rg: WWRing) {
        let k = th.k
        if k == "food" {
            th.dead = true
            wasted += 1
            floats.add(th.x, th.y - 8, "OOPS! FOOD", "red")
            parts.burst(th.x, th.y, 6, ["orange", "yellow"], 30, 0.4)
            app.audio.play("back")
            hype.breakCombo()
            hurtT = 0.5
            return
        }
        if k == "cap" {
            th.dead = true
            power(th.letter, th.x, th.y)
            return
        }
        th.hp -= 1
        if th.hp > 0 {
            th.flash = 0.12
            th.y -= 4
            th.by -= 4
            app.audio.play("tin")
            parts.burst(th.x, th.y, 5, ["white", "sky"], 30, 0.3)
            floats.add(th.x, th.y - 8, "CRACK!", "white")
            return
        }
        th.dead = true
        let g = rg.g
        g.count += 1
        let mult = rg.kind != "meow" ? min(8, 1 + rg.depth) : 1
        var pts = WWData.kind(k).pts * mult + hype.comboBonus(2)
        if k == "rocket" {
            pts += 150
            floats.add(th.x, th.y - 16, "DUD!", "orange")
        }
        if pts > 0 { scoreAt(pts, th.x, th.y - 6, rg.depth == 0 ? "yellow" : "peach") }
        hype.hit(1, fever: feverGain())
        caught += 1
        parts.burst(th.x, th.y, 8, WWArt.kindColors[k] ?? ["white"], 50, 0.5)
        app.audio.play("pop")
        if rg.kind != "meow" && rg.depth < 14 {
            let ch = WWRing(th.x, th.y, chainR(), rg.depth + 1, g, "chain", 0.13, 0.05)
            ch.fever = hype.feverOn
            rings.append(ch)
        }
        if k == "gold" {
            hype.jackpot(factor(5000), sub: "GOLDEN FISH!")
            happyT = 1.5
        }
        if rg.kind != "meow" { chainNews(g, th.x, th.y) }
    }

    func chainNews(_ g: WWGroup, _ x: Double, _ y: Double) {
        let c = g.count
        bestChain = max(bestChain, c)
        if c >= 3 { happyT = max(happyT, 0.5) }
        switch c {
        case 3:
            floats.add(x, y - 16, "CHAIN!", "pink")
        case 5:
            hype.banner("5 CHAIN!", color: "peach", dur: 0.9, scale: 1)
        case 8:
            hype.banner("8 CHAIN!!", "+1000", color: "hotpink", dur: 1.2, sound: "bonus")
            hype.shower(24, "stars")
            hype.hitstop(0.06)
            scoreAt(1000)
        case 12:
            hype.banner("PURRFECT CHAIN!", "+3000", dur: 1.8, rainbow: true, sound: "fever")
            hype.slowmo(0.4, 0.8)
            hype.flash("white", 0.2)
            hype.shower(40, "confetti")
            scoreAt(3000)
            happyT = 1.5
        case 16:
            hype.jackpot(factor(6000), sub: "16 CHAIN!!")
        default:
            break
        }
    }

    func hitBoss(_ rg: WWRing) {
        guard let b = boss else { return }
        var dmg = rg.kind == "meow" ? 3 : 1
        if ["swoop", "dash", "slam"].contains(b.mode) { dmg += 1 }
        let died = b.damage(dmg)
        hype.hitstop(0.04)
        hype.hit(1, fever: feverGain())
        app.shake(2, 0.15)
        app.audio.play("brick")
        parts.burst(b.x, b.y, 10, ["white", "yellow", "pink"], 60, 0.5)
        scoreAt(40 * dmg, b.x, b.y - Double(b.r) - 6, "orange")
        if died { bossDefeated() }
    }

    func power(_ letter: String, _ x: Double, _ y: Double) {
        let (c, name, sub) = POWERS[letter] ?? ("yellow", "LUCKY COIN!", nil)
        app.audio.play("powerup")
        parts.burst(x, y, 14, [c, "white"], 60, 0.6)
        switch letter {
        case "N": frenzyT = 7
        case "T": meows = min(meowMax(), meows + 1)
        case "S": snoozeT = 6
        case "H":
            for tr in treasures { tr.hp = min(tr.maxhp, tr.hp + 1); tr.flash = 0.4 }
        default:
            scoreAt(2000, x, y - 8, "yellow")
            hype.shower(20, "coins")
            app.audio.play("coin")
        }
        hype.banner(name, sub, color: c, dur: 1.2, scale: 1)
        happyT = 0.8
    }

    func checkLife() {
        let i = lifeI
        let target = i < LIFE_AT.count ? LIFE_AT[i] : LIFE_AT.last! + 200000 * (i - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("BONUS LIFE!", "\(target) POINTS", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    func loseLife() {
        if state != "play" { return }
        lives -= 1
        hype.breakCombo()
        app.audio.play("die")
        app.shake(5, 0.5)
        things = []
        rings = []
        stateT = 0
        if lives <= 0 {
            state = "over"
            hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
            endGame(false, "STAGE \(n)", delay: 3.0)
        } else {
            state = "oops"
            hype.banner("ALL DRY!", "TRY AGAIN - \(lives) LEFT", color: "pink", dur: 2.0)
        }
    }

    // ---------------------------------------------------------------- clear / tally
    func stageClear() {
        if state != "play" { return }
        state = "clear"
        stateT = 0
        if hype.feverOn { hype.feverT = 0 }
        for th in things where !th.dead && th.k != "food" && th.k != "cap" {
            parts.burst(th.x, th.y, 6, WWArt.kindColors[th.k] ?? ["white"], 40, 0.4)
        }
        things = []
        hype.slowmo(0.3, 0.8)
        app.audio.play("win")
        happyT = 2.0
        if st.kind == "normal" {
            hype.banner("STAGE CLEAR!", color: "mint", dur: 1.4)
            hype.shower(30, "confetti")
        }
        app.audio.music(nil)
        wasFever = false
    }

    func bossDefeated() {
        if state != "play" { return }
        guard let b = boss else { return }
        app.audio.play("bossdown")
        hype.banner("BOSS DOWN!", b.name, dur: 2.2, rainbow: true)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        app.shake(6, 0.6)
        scoreAt(15000, Double(W) / 2, 80)
        for th in things where th.harm { scoreAt(th.pts, th.x, th.y, "peach") }
        stageClear()
        hype.slowmo(0.3, 1.2)
    }

    func beginTally() {
        let water = treasures.reduce(0) { $0 + max(0, $1.hp) }
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("STAGE CLEAR", factor(1000)))
            rows.append(("CAUGHT \(caught)", factor(caught * 20)))
            rows.append(("WATER LEFT", factor(water * 150)))
            rows.append(("BEST CHAIN \(bestChain)", factor(bestChain * 100)))
            rows.append(("NO SPLASH", splashed ? 0 : factor(5000)))
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", factor(10000 + 2000 * tier)))
            rows.append(("WATER LEFT", factor(water * 300)))
            rows.append(("BEST CHAIN \(bestChain)", factor(bestChain * 100)))
            rows.append(("NO SPLASH", splashed ? 0 : factor(8000)))
        } else {
            rows.append(("CAUGHT \(caught)/\(total)", factor(caught * 50)))
            rows.append(("BEST CHAIN \(bestChain)", factor(bestChain * 150)))
            rows.append(("ALL CAUGHT!", caught >= total ? factor(10000) : 0))
        }
        tally = rows.map { (label: $0.0, v: $0.1, shown: 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        if st.kind != "bonus" && !splashed {
            hype.banner("PURRFECT!", "NOT A SINGLE SPLASH", dur: 1.8, rainbow: true, sound: "fever")
            hype.shower(40, "stars")
        } else if st.kind == "bonus" && caught >= total {
            hype.banner("ALL CAUGHT!", dur: 1.8, rainbow: true, sound: "fever")
        }
    }

    func updateTally(_ dt: Double) {
        let skip = stateT > 0.3 && (app.input.hit(.a) || tappedNow)
        if tallyI < tally.count {
            if skip {
                for j in tallyI ..< tally.count {
                    tally[j].shown = Double(tally[j].v)
                    if tally[j].v > 0 { add(tally[j].v) }
                }
                tallyI = tally.count
                app.audio.play("coin")
                return
            }
            let v = Double(tally[tallyI].v)
            tally[tallyI].shown = min(v, tally[tallyI].shown + max(1, v * dt / 0.4))
            if tally[tallyI].shown >= v {
                if tally[tallyI].v > 0 {
                    add(tally[tallyI].v)
                    app.audio.play("coin")
                }
                tallyI += 1
            }
        } else {
            tallyWait += dt
            if tallyWait > 1.6 || skip { finishStage() }
        }
    }

    func finishStage() {
        checkLife()
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "MARU SAVED EVERY FISH", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            meows = min(meowMax(), meows + 1)
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "SWEET TREAT!"
            state = "pick"
        } else {
            startStage(nextN!)
        }
    }

    // ---------------------------------------------------------------- drawing
    override func render(_ s: Surface) {
        s.blit(sky, 0, 0)
        WWArt.drawSkyFx(s, theme, t, lightning)
        boss?.draw(s, t)
        WWArt.drawSill(s)
        WWArt.drawMaru(s, self, t)
        for tr in treasures { WWArt.drawTreasure(s, tr, t) }
        if state == "play" && Int(t * 8) % 2 == 1 {          // danger: something is about to land on a treasure
            for tr in treasures where tr.hp > 0 {
                if things.contains(where: { $0.harm && $0.k != "rocket" && Double(tr.top - 44) <= $0.y && $0.y < Double(tr.top - 2)
                                       && abs($0.x - tr.x) <= Double(tr.hw + 10) }) {
                    drawText(s, "!", Int(tr.x) - 2, tr.top - 12, "red", shadow: "black")
                }
            }
        }
        for th in things { WWArt.drawThing(s, th, t, theme.deco) }
        drawRings(s)
        parts.draw(s)
        floats.draw(s)
        WWArt.drawFrame(s, theme, t)
        if state == "play" || state == "intro" {
            let ready = freeSwats() || energy >= 1
            let c = frenzyT > 0 ? "lime" : (hype.feverOn ? "yellow" : "white")
            WWArt.drawPawCursor(s, cx, cy, t, ready, c)
        }
        drawHud(s)
        if state == "intro" { drawIntro(s) } else if state == "tally" { drawTally(s) }
    }

    func drawRings(_ s: Surface) {
        for rg in rings {
            let r = Int(rg.r)
            if r < 1 { continue }
            let x = Int(rg.x), y = Int(rg.y)
            if rg.kind == "meow" {
                for i in 0 ..< 3 where r - i * 5 > 0 { s.circle(col(rainbow(i, t)), x, y, r - i * 5, width: 1) }
                continue
            }
            let faded = rg.age > rg.dur + rg.hold
            let c: String
            if rg.fever { c = rainbow(rg.depth, t) } else if rg.kind == "swat" { c = "white" } else { c = ["pink", "peach", "hotpink"][rg.depth % 3] }
            if faded && Int(t * 30) % 2 == 1 { continue }
            s.circle(col(c), x, y, r, width: 1)
            if rg.kind == "swat" && !faded && r > 4 { s.circle(col("lavender"), x, y, r - 3, width: 1) }
        }
        for sp in stamps {
            if sp.tired {
                if Int(sp.age * 20) % 2 == 0 { drawText(s, "PUFF", Int(sp.x), Int(sp.y) - 14, "gray", align: .center, shadow: nil) }
                continue
            }
            if sp.age < 0.12 { s.blit(sprite("ww_paw", scale: 2), Int(sp.x) - 9, Int(sp.y) - 9) }
        }
    }

    func drawHud(_ s: Surface) {
        s.fillRect(col("black"), 0, 0, W, 16)
        drawText(s, String(format: "%07d", score), 4, 1, "white", shadow: nil)
        if let b = boss, b.state != "dead" {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: 2, x: 64, w: 192)
        } else {
            drawText(s, String(format: "HI %07d", max(best, score)), 4, 9, "gray", shadow: nil)
            if st.kind == "bonus" && (state == "play" || state == "intro") {
                let secs = max(0, Int(ceil(bonusLeft)))
                drawText(s, String(format: "TIME %02d", secs), W / 2, 2, secs > 5 || Int(t * 6) % 2 == 1 ? "yellow" : "red",
                         align: .center, shadow: nil)
            } else {
                drawText(s, "STAGE \(n)", W / 2, 2, "yellow", align: .center, shadow: nil)
            }
            if !events.isEmpty && st.kind != "boss" {
                let frac = Double(ei) / Double(events.count)
                s.fillRect(col("darkgray"), W / 2 - 30, 11, 60, 2)
                s.fillRect(col("mint"), W / 2 - 30, 11, Int(60 * frac), 2)
            }
        }
        hearts(s, W - 54, 1, lives)
        let x0 = W - 54, y0 = 11
        s.fillRect(col("darkgray"), x0, y0, 48, 3)
        if hype.feverOn {
            for i in 0 ..< 48 { s.fillRect(col(rainbow(i / 6, t)), x0 + i, y0, 1, 3) }
        } else {
            s.fillRect(col("orange"), x0, y0, Int(48 * hype.fever), 3)
        }
        // paw energy and meows on the windowsill
        let y = WW_SILL + 9
        let free = freeSwats()
        for i in 0 ..< emax() {
            let x = 8 + i * 8
            let full = free || i < Int(energy)
            s.blit(sprite("ww_pawicon", remap: full ? nil : ["w": "d"]), x, y)
            if !full && i == Int(energy) { s.fillRect(col("peach"), x + 1, y + 7, Int(5 * (energy - Double(Int(energy)))), 1) }
        }
        if free && st.kind != "bonus" && Int(t * 4) % 2 == 1 { drawText(s, "FREE!", 10 + emax() * 8, y - 1, "lime", shadow: "black") }
        drawText(s, "MEOW", W - 10 - meowMax() * 7, y - 1, "orange", align: .right, shadow: "black")
        for i in 0 ..< meowMax() {
            s.circle(col("black"), W - 10 - i * 7, y + 3, 3)
            s.circle(col(i < meows ? "orange" : "brown"), W - 10 - i * 7, y + 3, 2)
        }
        var items: [(String, String, Double)] = []
        if frenzyT > 0 { items.append(("CATNIP \(Int(ceil(frenzyT)))", "lime", frenzyT)) }
        if snoozeT > 0 { items.append(("SNOOZE \(Int(ceil(snoozeT)))", "sky", snoozeT)) }
        if abs(windNow) > 8 && state == "play" { items.append((windNow > 0 ? "WIND >>" : "<< WIND", "white", 9)) }
        for (i, it) in items.enumerated() where it.2 > 2 || Int(t * 8) % 2 == 1 {
            drawText(s, it.0, W / 2 + i * 64 - (items.count - 1) * 32, y - 1, it.1, align: .center, shadow: "black")
        }
    }

    func drawIntro(_ s: Surface) {
        if st.kind == "boss" {
            if Int(t * 4) % 2 == 1 {
                var x = -20
                while x < W + 20 {
                    let fx = Double(x)
                    s.polygon(col("red"), [(fx, 96), (fx + 10, 96), (fx + 20, 104), (fx + 10, 104)])
                    s.polygon(col("red"), [(fx, 138), (fx + 10, 138), (fx + 20, 146), (fx + 10, 146)])
                    x += 20
                }
            }
            panel(s, IRect(40, 106, 240, 30), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 110, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.name) APPROACHES", W / 2, 126, "white", align: .center, shadow: nil)
            if !st.newLine.isEmpty { drawText(s, st.newLine, W / 2, 152, "mint", align: .center, shadow: "black") }
            return
        }
        if st.kind == "bonus" {
            panel(s, IRect(30, 86, 260, 52), fill: "ink", border: "yellow")
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, 92 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            drawText(s, st.name, W / 2, 112, "yellow", align: .center)
            drawText(s, BONUS_SUB[st.bonus] ?? "", W / 2, 124, "white", align: .center)
            return
        }
        let y0 = 86
        let h = st.newLine.isEmpty ? 60 : 72
        panel(s, IRect(30, y0, 260, h), fill: "ink", border: "pink")
        drawText(s, "STAGE \(n)", W / 2, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, theme.name, W / 2, y0 + 25, "lavender", align: .center)
        drawText(s, st.name, W / 2, y0 + 36, "white", align: .center)
        if !st.newLine.isEmpty { drawText(s, st.newLine, W / 2, y0 + 48, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center) }
        drawText(s, MARU_LINES[n % MARU_LINES.count], W / 2, y0 + h - 12, "cream", align: .center, shadow: nil)
    }

    func drawTally(_ s: Surface) {
        let h = 44 + tally.count * 11
        let y0 = 84
        panel(s, IRect(64, y0, 192, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, W / 2, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 20 + i * 11
            drawText(s, row.label, 72, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 248, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        if tallyI >= tally.count {
            var line = !splashed ? "MARU PURRS LOUDLY"
                : (treasures.contains { $0.hp < $0.maxhp } ? "MARU: THAT WAS CLOSE..." : "MARU: PHEW!")
            if st.kind == "bonus" { line = "MARU: YUM YUM!" }
            drawText(s, line, W / 2, y0 + h - 22, "cream", align: .center, shadow: nil)
            if Int(t * 3) % 2 == 1 { drawText(s, "TAP TO GO ON", W / 2, y0 + h - 11, "lavender", align: .center, shadow: nil) }
        }
    }
}
