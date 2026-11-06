// BOUNCE BUN - brick breaker with a bun paddle and snack bricks (port of games/bounce_bun.py).
// 200 stages read from the exported campaign (games/bounce_bun_stages.py), bosses in BounceBunBoss.swift.
import Foundation

private let LEFT = 8.0, RIGHT = Double(W - 8), TOP = 20.0
private let BRW = 16, BRH = 8, BX0 = 16, BY0 = 30
private let PADDLE_Y = 182.0
private let COLS = 18
private let KIND: [Character: String] = ["c": "cookie", "p": "candy", "m": "mint", "l": "lemon", "b": "berry", "h": "choco",
                                         "H": "fudge", "t": "tin", "$": "gold", "x": "bomb", "?": "gift", "r": "jelly",
                                         "k": "key", "L": "lock", "*": "bumper", "o": "portal", "O": "portal2", "C": "coin"]
private let HPS = ["choco": 2, "fudge": 3, "gold": 3]
private let POINTS = ["cookie": 50, "candy": 60, "mint": 70, "lemon": 80, "berry": 90, "choco": 120, "fudge": 200, "gold": 1000,
                      "bomb": 80, "gift": 100, "jelly": 60, "key": 300, "lock": 150, "coin": 150]
private let COLORS: [String: [String]] = [
    "cookie": ["peach", "brown"], "candy": ["pink", "white"], "mint": ["mint", "white"], "lemon": ["yellow", "white"],
    "berry": ["lavender", "purple"], "choco": ["brown", "choco"], "fudge": ["choco", "black"], "gold": ["yellow", "white", "orange"],
    "bomb": ["hotpink", "red", "yellow"], "gift": ["lavender", "yellow"], "jelly": ["mint", "teal"], "key": ["yellow", "orange"],
    "lock": ["gray", "pink"], "coin": ["yellow", "orange"]]
private let CAPS: [String: (String, String)] = ["W": ("sky", "WIDE BUN!"), "M": ("pink", "MULTI BALL!"), "S": ("mint", "SLOW DOWN"),
                                                "G": ("yellow", "STICKY GLUE"), "F": ("orange", "FIREBALL!"), "L": ("lavender", "LASERS!"),
                                                "+": ("red", "EXTRA LIFE!"), "$": ("yellow", "GOLD!")]
private let TIMED = ["wide", "slow", "glue", "fire", "laser"]
private let LIFE_AT = [20000, 60000, 120000, 200000]      // then every 150000

// ----------------------------------------------------------------------------- campaign data (EXPORT)
struct BBBossSpec { let kind, name: String; let hp: Int; let rate, speed: Double; let extra: [String]; let tier: Int }

struct BBStage {
    let n: Int, kind: String, name: String, rows: [String], moves: [[Double]], creep: Bool, tier: Int, speed: Double
    let newLine: String, bonus: String, time: Double, boss: BBBossSpec?
}

struct BBTheme { let name, a, b: String; let pat: Int; let wall: String }

enum BBData {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static let root: [String: Any] = (GameData.json("bounce_bun") as? [String: Any]) ?? [:]

    static let stages: [BBStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        var boss: BBBossSpec?
        if let b = d["boss"] as? [String: Any] {
            boss = BBBossSpec(kind: b["kind"] as? String ?? "cake", name: b["name"] as? String ?? "", hp: Int(num(b["hp"])),
                              rate: num(b["rate"]), speed: num(b["speed"]), extra: b["extra"] as? [String] ?? [],
                              tier: Int(num(b["tier"])))
        }
        let moves = ((d["moves"] as? [[Any]]) ?? []).map { $0.map { num($0) } }
        return BBStage(n: Int(num(d["n"])), kind: d["kind"] as? String ?? "normal", name: d["name"] as? String ?? "",
                       rows: d["rows"] as? [String] ?? [], moves: moves, creep: d["creep"] as? Bool ?? false,
                       tier: Int(num(d["tier"])), speed: num(d["speed"]), newLine: d["new"] as? String ?? "",
                       bonus: d["bonus"] as? String ?? "", time: num(d["time"]), boss: boss)
    }

    static let themes: [BBTheme] = ((root["themes"] as? [[Any]]) ?? []).map { a in
        BBTheme(name: a[0] as? String ?? "", a: a[1] as? String ?? "choco", b: a[2] as? String ?? "brown",
                pat: Int(num(a[3])), wall: a[4] as? String ?? "peach")
    }
}

// ----------------------------------------------------------------------------- upgrade cards
private func iconBall(_ c: String) -> (Surface, Int, Int, Double) -> Void {
    { s, cx, cy, _ in s.circle(col(c), cx, cy, 4); s.fillRect(col("white"), cx - 2, cy - 2, 1, 1) }
}

let BB_UPGRADES: [Upgrade] = [
    Upgrade(id: "wide", name: "BIG BUN", desc: "A WIDER|BUN PADDLE", color: "peach", draw: { s, cx, cy, t in
        let w = 14 + Int(sin(t * 4) * 3)
        s.rect(col("peach"), IRect(cx - w / 2, cy - 2, w, 5), radius: 2)
        s.fillRect(col("cream"), cx - w / 2 + 2, cy - 1, w - 4, 1)
    }, max: 4),
    Upgrade(id: "power", name: "POWER BALL", desc: "+1 DAMAGE|CRACKS CHOCO|AND BOSSES", color: "red", draw: iconBall("red"), max: 3),
    Upgrade(id: "laser", name: "SPRINKLE GUN", desc: "HOLD LASER|TO SHOOT|FASTER EACH LV", color: "sky", draw: { s, cx, cy, t in
        for dx in [-4, 4] { s.fillRect(col("sky"), cx + dx, cy - 6 + Int(t * 20) % 4, 1, 5) }
        s.fillRect(col("peach"), cx - 6, cy + 4, 13, 3)
    }, max: 3),
    Upgrade(id: "twin", name: "TWIN START", desc: "+1 GUMBALL|AT EVERY|LAUNCH", color: "pink", draw: { s, cx, cy, t in
        for dx in [-3, 3] { s.circle(col("hotpink"), cx + dx, cy + (dx / 3) * Int(sin(t * 6) * 2), 3) }
    }, max: 2),
    Upgrade(id: "sticky", name: "STICKY BUN", desc: "HOLD LAUNCH|TO CATCH THE|GUMBALL", color: "yellow", draw: { s, cx, cy, _ in
        s.circle(col("hotpink"), cx, cy - 2, 3)
        s.fillRect(col("yellow"), cx - 7, cy + 2, 15, 3)
        s.fillRect(col("yellow"), cx - 1, cy + 1, 3, 1)
    }, max: 1),
    Upgrade(id: "magnet", name: "MAGNET", desc: "PULLS|CAPSULES|TO THE BUN", color: "lavender", draw: { s, cx, cy, _ in
        s.fillRect(col("red"), cx - 6, cy - 6, 4, 10); s.fillRect(col("red"), cx + 3, cy - 6, 4, 10)
        s.fillRect(col("red"), cx - 6, cy + 1, 13, 4)
        s.fillRect(col("white"), cx - 6, cy - 6, 4, 2); s.fillRect(col("white"), cx + 3, cy - 6, 4, 2)
    }, max: 3),
    Upgrade(id: "calm", name: "CALM DOWN", desc: "A SLOWER|GUMBALL", color: "mint", draw: { s, cx, cy, t in
        s.circle(col("mint"), cx, cy, 6, width: 1)
        s.fillRect(col("white"), cx + Int(cos(t * 2) * 4), cy + Int(sin(t * 2) * 4), 1, 1)
        s.fillRect(col("mint"), cx, cy - 4, 1, 4)
    }, max: 3),
    Upgrade(id: "net", name: "SAFETY NET", desc: "SAVES ONE|DROPPED BALL|EVERY STAGE", color: "lime", draw: { s, cx, cy, t in
        var i = -6
        while i <= 6 { s.fillRect(col("lime"), cx + i, cy + 3, 2, 1); i += 3 }
        s.circle(col("hotpink"), cx, cy - 2 - abs(Int(sin(t * 5) * 3)), 2)
    }, max: 2),
    Upgrade(id: "life", name: "EXTRA LIFE", desc: "+1 LIFE|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
    Upgrade(id: "luck", name: "LUCKY DOUGH", desc: "MORE|CAPSULES AND|JACKPOTS", color: "orange", draw: { s, cx, cy, t in
        let w = max(1, Int(abs(cos(t * 3)) * 5))
        s.ellipse(col("orange"), cx - w, cy - 5, w * 2 + 1, 11)
        s.ellipse(col("yellow"), cx - w + 1, cy - 4, max(1, w * 2 - 1), 9)
    }, max: 3),
    Upgrade(id: "fever", name: "FEVER OVEN", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "yellow", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
]

// ----------------------------------------------------------------------------- objects
final class BBBall {
    var x, y, vx, vy: Double
    var stuck: Double?          // x offset from the paddle centre while held
    var hold = false            // caught by STICKY BUN: launches when the button is released
    var heldT = 0.0
    var volley = 0              // bricks broken since the last paddle touch
    var pcd = 0.0, boost = 0.0, idle = 0.0
    var bcd = 0.0               // boss hit cooldown (a gumball pinned against a boss hurts it only so often)
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double) { self.x = x; self.y = y; self.vx = vx; self.vy = vy }
    var box: IRect { IRect(Int(x) - 2, Int(y) - 2, 5, 5) }
}

final class BBBrick {
    let r, c: Int
    let kind: String
    var hp: Int
    var alive = true
    var flash = 0.0, regrow = 0.0, bump = 0.0
    var locked: Bool
    var x, y: Double
    init(_ r: Int, _ c: Int, _ ch: Character) {
        self.r = r; self.c = c
        kind = KIND[ch] ?? "cookie"
        hp = HPS[kind] ?? 1
        locked = kind == "lock"
        x = Double(BX0 + c * BRW); y = Double(BY0 + r * BRH)
    }
    var isPortal: Bool { kind == "portal" || kind == "portal2" }
    var breakable: Bool { kind != "tin" && kind != "bumper" && !isPortal }
    func rect() -> IRect { kind == "bumper" ? IRect(Int(x) + 3, Int(y), BRW - 6, BRH) : IRect(Int(x), Int(y), BRW, BRH) }
}

final class BBCap {
    var x, y: Double
    let k: String
    var got = false
    init(_ x: Double, _ y: Double, _ k: String) { self.x = x; self.y = y; self.k = k }
}

/// Bonus CANDY RAIN: kind 0-7 snacks, 8 golden star, 9 sour drop (ouch).
final class BBSweet {
    var x, y, vy: Double
    let kind: Int
    var got = false
    init(_ x: Double, _ vy: Double, _ kind: Int) { self.x = x; y = TOP; self.vy = vy; self.kind = kind }
}

// ----------------------------------------------------------------------------- the game
final class BounceBun: GameScene {
    override var music: String? { song() }
    override var buttons: [Action: String] { laserLv() > 0 ? [.a: "LAUNCH", .b: "LASER"] : [.a: "LAUNCH"] }
    override var buttonOrder: [Action] { [.a, .b] }
    override var fourWay: Bool { false }

    var lives: Int
    let baseSpeed: Double
    var levels: [String: Int] = [:]
    var px = Double(W) / 2
    var pdir = 0, phold = 0.0, pvel = 0.0, stun = 0.0
    var lifeI = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    var wasFever = false
    // stage
    var n = 1
    var st: BBStage = BBData.stages[0]
    var tier = 0
    var theme: BBTheme = BBData.themes[0]
    var bricks: [BBBrick] = []
    var cell: [Int: BBBrick] = [:]
    var portals: [BBBrick] = []
    var moves: [Int: [Double]] = [:]
    var creep = 0.0
    var total = 0, coinsTotal = 0
    var boss: BBBoss?
    var caps: [BBCap] = []
    var shots: [(x: Double, y: Double)] = []
    var booms: [(r: Int, c: Int, t: Double)] = []
    var sweets: [BBSweet] = []
    var timers: [String: Double] = ["wide": 0, "slow": 0, "glue": 0, "fire": 0, "laser": 0]
    var net = 0
    var laserCd = 0.0, stime = 0.0
    var missed = false, hurt = false
    var stageCombo = 0, coins = 0, caught = 0, golds = 0
    var sweetT = 0.0
    var speed = 0.0, speedCap = 0.0
    var bonusLeft = 0.0
    var fresh = true, lucky = false
    var balls: [BBBall] = []
    var state = "intro"
    var stateT = 0.0, introLen = 2.2
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0
    var bg = Surface(W, H)

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        baseSpeed = 125 * (SPEEDS[d] ?? 1)
        super.init(app, info, opt)
        let start = max(1, min(STAGES, optInt("level", optInt("start", 1))))
        startStage(start)
        if start > 10 {          // starting from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (start - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func factorPts(_ pts: Int) -> Int { pts * (10 + tier) / 10 }
    @discardableResult
    func scoreAt(_ pts: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int { add(factorPts(pts), x, y, c) }
    var isRain: Bool { st.kind == "bonus" && st.bonus == "rain" }
    func pw() -> Double {
        var w = 32.0 + 4 * Double(lv("wide"))
        if (timers["wide"] ?? 0) > 0 { w += 16 }
        if isRain { w += 16 }
        return w
    }
    func fireOn() -> Bool { (timers["fire"] ?? 0) > 0 || hype.feverOn }
    func laserLv() -> Int { (timers["laser"] ?? 0) > 0 ? max(1, lv("laser")) : lv("laser") }
    func ballDmg() -> Int { 1 + lv("power") }
    func feverGain() -> Double { 0.03 * (1 + 0.35 * Double(lv("fever"))) }
    func ballX() -> Double { balls.first { $0.stuck == nil }?.x ?? px }
    func song() -> String { st.kind == "boss" ? "boss" : (st.kind == "bonus" ? "bonus" : "bounce") }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        n = num
        st = BBData.stages[num - 1]
        tier = st.tier
        theme = BBData.themes[min(tier, BBData.themes.count - 1)]
        reached(num)
        bricks = []
        cell = [:]
        for (r, row) in st.rows.enumerated() {
            for (c, ch) in row.enumerated() where KIND[ch] != nil {
                let br = BBBrick(r, c, ch)
                bricks.append(br)
                cell[r * 100 + c] = br
            }
        }
        portals = bricks.filter { $0.isPortal }
        moves = [:]
        for m in st.moves { moves[Int(m[0])] = m }
        creep = 0
        total = bricks.filter { $0.breakable }.count
        coinsTotal = bricks.filter { $0.kind == "coin" }.count
        boss = st.boss.map { BBBoss(self, $0) }
        caps = []; shots = []; booms = []; sweets = []
        for k in TIMED { timers[k] = 0 }
        net = lv("net")
        laserCd = 0; stime = 0
        missed = false; hurt = false
        stageCombo = 0; coins = 0; caught = 0; golds = 0
        sweetT = 0
        speed = baseSpeed * st.speed
        speedCap = baseSpeed * min(1.9, st.speed * 1.45)
        bonusLeft = st.time
        fresh = true
        lucky = st.kind == "normal" && hype.lucky(0.03 + 0.01 * Double(lv("luck")))
        balls = []
        if !isRain { resetBall() }
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.0 : 2.2
        tally = []
        bg = makeBg()
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    func resetBall() {
        let b = BBBall(px, PADDLE_Y - 4, 0, 0)
        b.stuck = 4
        balls = [b]
        fresh = true
        for k in TIMED { timers[k] = 0 }
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        switch state {
        case "intro":
            movePaddle(dt)
            followStuck()
            boss?.update(dt)
            if stateT > introLen || (stateT > 0.5 && app.input.hit(.a)) {
                state = "play"
                stateT = 0
                boss?.state = "fight"
            }
        case "play":
            play(dt)
        case "clear":
            for b in balls where b.stuck == nil { moveBall(b, dt, floor: true) }
            if stateT > 1.4 { beginTally() }
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(BB_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        default: break
        }
        for br in bricks { br.flash = max(0, br.flash - dt); br.bump = max(0, br.bump - dt) }
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = BB_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id] ?? 1)", color: u.color, dur: 1.2, scale: 1)
        }
        if id == "life" { lives += 1; app.audio.play("extra") } else if id == "net" { net += 1 }
    }

    func movePaddle(_ dt: Double) {
        let inp = app.input
        var d = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        if stun > 0 { d = 0 }
        if d != pdir { phold = 0 }
        pdir = d
        var v = 0.0
        if d != 0 {
            phold += dt
            v = 100 + min(1, phold / 0.22) * 170       // fine control first, then fast
        }
        // touch: the paddle speed follows how far the thumb is pushed (analog), for fine aiming on phones
        if stun <= 0, let a = inp.analog, abs(a.x) > 0.12 {
            let k = (abs(a.x) - 0.12) / 0.88
            d = a.x < 0 ? -1 : 1
            v = 40 + k * k * 260
            pdir = d
        }
        let half = pw() / 2
        px = max(LEFT + half, min(RIGHT - half, px + Double(d) * v * dt))
        pvel = Double(d) * v
    }

    func followStuck() {
        let half = pw() / 2
        for b in balls {
            if let s = b.stuck {
                let st = max(-half + 2, min(half - 2, s))
                b.stuck = st
                b.x = px + st; b.y = PADDLE_Y - 4
            }
        }
    }

    func play(_ dt: Double) {
        let inp = app.input, au = app.audio
        stime += dt
        stun = max(0, stun - dt)
        for k in TIMED { timers[k] = max(0, (timers[k] ?? 0) - dt) }
        movePaddle(dt)
        let half = pw() / 2
        // lasers
        laserCd -= dt
        if laserLv() > 0 && inp.down(.b) && laserCd <= 0 && stun <= 0 {
            laserCd = [0.5, 0.5, 0.38, 0.28][min(3, laserLv())]
            for dx in [-half + 3, half - 3] { shots.append((x: px + dx, y: PADDLE_Y - 2)) }
            au.play("shoot")
        }
        // balls on the bun
        followStuck()
        for b in balls where b.stuck != nil {
            b.heldT += dt
            if b.hold {
                if !inp.down(.a) || b.heldT > 3.0 { launch(b) }
            } else if inp.hit(.a) {
                launch(b)
            }
        }
        let floor = st.kind == "bonus" || (boss != nil && boss!.state != "fight")
        for b in balls where b.stuck == nil { moveBall(b, dt, floor: floor) }
        balls.removeAll { $0.y > Double(H + 6) }
        if balls.isEmpty && !isRain {
            loseLife()
            if state != "play" { return }
        }
        updateCaps(dt)
        updateShots(dt)
        updateBricks(dt)
        boss?.update(dt)
        if st.kind == "bonus" { updateBonus(dt) }
        stageCombo = max(stageCombo, hype.combo)
        // FEVER: its own song and a longer FEVER with the oven upgrade
        if hype.feverOn && !wasFever {
            hype.feverT += 2 * Double(lv("fever"))
            au.music("fever")
        } else if wasFever && !hype.feverOn {
            au.music(song())
        }
        wasFever = hype.feverOn
        checkLife()
        if state == "play" && st.kind == "normal" && !bricks.contains(where: { $0.alive && $0.breakable }) { stageClear() }
    }

    func launch(_ b: BBBall) {
        let half = pw() / 2
        let ang = max(-1, min(1, (b.stuck ?? 0) / half)) * 45 * .pi / 180
        let sp = curSpeed(b)
        b.vx = sin(ang) * sp; b.vy = -cos(ang) * sp
        b.stuck = nil
        b.hold = false
        b.volley = 0
        app.audio.play("paddle")
        if fresh {
            fresh = false
            if lucky {          // a rare lucky stage: FEVER from the first bounce
                lucky = false
                hype.banner("LUCKY BAKE!", "FEVER START", dur: 1.4, rainbow: true)
                hype.startFever()
            }
            var extra = lv("twin")
            if st.kind == "bonus" { extra += 2 }
            for i in 0 ..< extra {
                let a = ang + Double((25 + 10 * (i / 2)) * (i % 2 == 0 ? 1 : -1)) * .pi / 180
                balls.append(BBBall(b.x, b.y, sin(a) * sp, -abs(cos(a) * sp)))
            }
        }
    }

    func curSpeed(_ b: BBBall? = nil) -> Double {
        var sp = speed * (1 - 0.06 * Double(lv("calm")))
        if (timers["slow"] ?? 0) > 0 { sp *= 0.7 }
        if let b = b, b.boost > 0 { sp *= 1.3 }
        return sp
    }

    func loseLife() {
        let au = app.audio
        hype.breakCombo()
        missed = true
        lives -= 1
        au.play("hurt")
        app.shake(3, 0.3)
        if lives <= 0 {
            state = "over"
            hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
            au.play("gameover")
            endGame(false, "STAGE \(n)", delay: 2.5)
            return
        }
        hype.banner("OOPS!", "\(lives) LEFT", color: "pink", dur: 1.0, scale: 1)
        caps = []
        resetBall()
    }

    func checkLife() {
        let target = lifeI < LIFE_AT.count ? LIFE_AT[lifeI] : LIFE_AT[LIFE_AT.count - 1] + 150000 * (lifeI - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("BONUS LIFE!", "\(target) POINTS", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    // ---------------------------------------------------------------- the gumball
    func moveBall(_ b: BBBall, _ dt: Double, floor: Bool = false) {
        let au = app.audio
        b.pcd = max(0, b.pcd - dt)
        b.boost = max(0, b.boost - dt)
        b.bcd = max(0, b.bcd - dt)
        b.idle += dt
        let target = curSpeed(b)
        let sp = hypot(b.vx, b.vy) > 0 ? hypot(b.vx, b.vy) : 1
        b.vx = b.vx / sp * target; b.vy = b.vy / sp * target
        if b.idle > 8 {         // stuck in a boring loop: nudge it
            b.idle = 0
            let a = atan2(b.vx, -b.vy) + ([-9.0, 9.0].randomElement() ?? 9) * .pi / 180
            b.vx = sin(a) * target; b.vy = -cos(a) * target
        }
        let steps = max(1, Int(target * dt / 3) + 1)
        for _ in 0 ..< steps {
            b.x += b.vx * dt / Double(steps)
            b.y += b.vy * dt / Double(steps)
            if b.x < LEFT + 2 { b.x = LEFT + 2; b.vx = abs(b.vx); au.play("tin") }
            else if b.x > RIGHT - 2 { b.x = RIGHT - 2; b.vx = -abs(b.vx); au.play("tin") }
            if b.y < TOP + 2 { b.y = TOP + 2; b.vy = abs(b.vy); au.play("tin") }
            if b.y > 194 && b.vy > 0 && (floor || net > 0) {
                b.y = 194; b.vy = -abs(b.vy)
                if !floor {
                    net -= 1
                    floats.add(b.x, 180, "SAVED!", "lime")
                    au.play("bubble")
                    parts.burst(b.x, 196, 10, ["lime", "white"], 50, 0.5)
                }
            }
            let half = pw() / 2
            if b.vy > 0 && PADDLE_Y - 2 <= b.y + 2 && b.y + 2 <= PADDLE_Y + 5 && abs(b.x - px) <= half + 2 {
                paddleBounce(b, half, target)
                if b.stuck != nil { return }
            }
            if collideBricks(b) { minVy(b) }
            if boss != nil && collideBoss(b) { minVy(b) }
            for p in portals where b.pcd <= 0 && abs(b.x - (p.x + 8)) < 5 && abs(b.y - (p.y + 4)) < 4 {
                if let twin = portals.first(where: { $0 !== p && $0.kind == p.kind }) {
                    parts.burst(b.x, b.y, 8, ["lavender", "white"], 40, 0.4)
                    b.x = twin.x + 8; b.y = twin.y + 4
                    b.pcd = 0.5
                    au.play("bubble")
                    parts.burst(b.x, b.y, 8, ["mint", "white"], 40, 0.4)
                    break
                }
            }
        }
    }

    /// Never let the gumball fly almost flat (endless side-to-side loops).
    func minVy(_ b: BBBall) {
        let sp = hypot(b.vx, b.vy) > 0 ? hypot(b.vx, b.vy) : 1
        if abs(b.vy) < sp * 0.28 {
            b.vy = (b.vy == 0 ? -1.0 : (b.vy < 0 ? -1.0 : 1.0)) * sp * 0.28
            b.vx = (b.vx < 0 ? -1.0 : 1.0) * max(0, sp * sp - b.vy * b.vy).squareRoot()
        }
    }

    func paddleBounce(_ b: BBBall, _ half: Double, _ target: Double) {
        let off = max(-1, min(1, (b.x - px) / half))
        let eng = pvel > 0 ? 6.0 : (pvel < 0 ? -6.0 : 0)
        let ang = max(-65, min(65, off * 60 + eng)) * .pi / 180
        b.vx = sin(ang) * target; b.vy = -cos(ang) * target
        b.y = PADDLE_Y - 3
        b.volley = 0
        b.idle = 0
        app.audio.play("paddle")
        let glue = (timers["glue"] ?? 0) > 0
        let catchIt = glue || (lv("sticky") > 0 && app.input.down(.a))
        if catchIt && stun <= 0 {
            b.stuck = b.x - px
            b.hold = !glue
            b.heldT = 0
        }
    }

    /// Bounce on the overlap axis, away from the rect's centre.
    private func reflect(_ b: BBBall, _ r: IRect) {
        let ball = b.box
        let ox = Double(min(ball.right - r.x, r.right - ball.x)), oy = Double(min(ball.bottom - r.y, r.bottom - ball.y))
        if ox < oy {
            if b.x < Double(r.centerx) { b.vx = -abs(b.vx); b.x -= ox + 0.5 } else { b.vx = abs(b.vx); b.x += ox + 0.5 }
        } else {
            if b.y < Double(r.centery) { b.vy = -abs(b.vy); b.y -= oy + 0.5 } else { b.vy = abs(b.vy); b.y += oy + 0.5 }
        }
    }

    func collideBricks(_ b: BBBall) -> Bool {
        let ball = b.box
        let fire = fireOn()
        for br in bricks where br.alive && !br.isPortal {
            let r = br.rect()
            if !r.intersects(ball) { continue }
            if fire && br.breakable && !br.locked {
                hitBrick(br, 99, b)         // FEVER / fireball: burn straight through
                continue
            }
            reflect(b, r)
            if br.breakable { b.idle = 0 }
            if br.kind == "bumper" {
                br.bump = 0.25
                b.boost = 0.45
                app.audio.play("pop")
                scoreAt(10)
                parts.burst(Double(r.centerx), Double(r.centery), 4, ["hotpink", "white"], 40, 0.3)
            } else {
                hitBrick(br, ballDmg(), b)
            }
            return true
        }
        return false
    }

    func collideBoss(_ b: BBBall) -> Bool {
        guard let bs = boss else { return false }
        let ball = b.box
        for (r, target) in bs.colliders() where r.intersects(ball) {
            reflect(b, r)
            b.idle = 0
            if b.bcd <= 0 {
                b.bcd = 0.08
                if bs.hit(target, ballDmg() + (fireOn() ? 2 : 0)) { hype.hit(1, fever: feverGain()) }
            }
            return true
        }
        return false
    }

    // ---------------------------------------------------------------- bricks
    func hitBrick(_ br: BBBrick, _ dmg: Int, _ ball: BBBall?) {
        let au = app.audio
        let k = br.kind
        if k == "tin" || k == "bumper" || (k == "lock" && br.locked) {
            br.flash = 0.15
            au.play("tin")
            return
        }
        br.hp -= dmg
        if br.hp > 0 {
            br.flash = 0.2
            if k == "gold" {
                au.play("coin")
                for _ in 0 ..< 4 { parts.sparkle(br.x + .random(in: 0 ... Double(BRW)), br.y + 4) }
            } else {
                au.play("tin")
            }
            return
        }
        breakBrick(br, ball)
    }

    func breakBrick(_ br: BBBrick, _ ball: BBBall?) {
        let au = app.audio
        let k = br.kind
        br.alive = false
        if k == "jelly" { br.regrow = 6 }
        let cx = br.x + Double(BRW) / 2, cy = br.y + Double(BRH) / 2
        let vol = ball?.volley ?? 0
        hype.hit(1, fever: feverGain())
        let pts = (POINTS[k] ?? 50) * (100 + 10 * min(vol, 20)) / 100 + hype.comboBonus(2)
        scoreAt(pts, pts >= 150 ? cx : nil, cy - 4, "yellow")
        if let ball = ball {
            ball.volley += 1
            if ball.volley % 8 == 0 {
                let bonus = scoreAt(300 * (ball.volley / 8))
                floats.add(cx, cy - 12, "RALLY x\(ball.volley) +\(bonus)", "mint")
                au.play("combo")
            }
        }
        speed = min(speedCap, speed + 1.2)
        parts.burst(cx, cy, 8, COLORS[k] ?? ["white"], 50, 0.5)
        au.play(k == "coin" ? "coin" : "brick")
        if k == "coin" { coins += 1 }
        if k == "bomb" {
            booms.append((r: br.r, c: br.c, t: 0.12))
        } else if k == "key" {
            for q in bricks where q.kind == "lock" && q.locked { q.locked = false; q.flash = 0.3 }
            hype.banner("UNLOCKED!", color: "yellow", dur: 1.0, scale: 1, sound: "bonus")
        } else if k == "gold" {
            hype.jackpot(factorPts(5000))
        }
        if k == "gift" { dropCap(cx, cy, force: true) } else if k != "coin" && k != "gold" { dropCap(cx, cy) }
    }

    func dropCap(_ x: Double, _ y: Double, force: Bool = false) {
        let luck = Double(lv("luck"))
        if caps.count >= 6 || st.kind == "bonus" { return }
        if !force && Double.random(in: 0 ..< 1) >= 0.09 + 0.03 * luck { return }
        var k: String
        if Double.random(in: 0 ..< 1) < 0.015 * (1 + luck) {
            k = "$"
        } else {
            let pool = "WWWMMMSSGG" + (tier >= 1 ? "FF" : "") + (tier >= 2 ? "LL" : "")
            k = Double.random(in: 0 ..< 1) < 0.05 ? "+" : String(pool.randomElement()!)
        }
        caps.append(BBCap(x, y, k))
    }

    func updateBricks(_ dt: Double) {
        let t = stime
        if st.creep { creep = min(24, Double(Int(t / 6) * 2)) }
        for br in bricks {
            var off = 0.0
            if let m = moves[br.r] { off = sin(t * m[2] + m[3]) * m[1] }
            br.x = Double(BX0 + br.c * BRW) + off
            br.y = Double(BY0 + br.r * BRH) + creep
            if br.kind == "jelly" && !br.alive && br.regrow > 0 {
                br.regrow -= dt
                if br.regrow <= 0 {
                    if balls.contains(where: { $0.box.intersects(br.rect()) }) {
                        br.regrow = 0.5        // a gumball is in the way: try again in a moment
                    } else {
                        br.alive = true; br.hp = 1; br.flash = 0.25
                        parts.burst(br.x + 8, br.y + 4, 6, ["mint", "teal"], 30, 0.3)
                    }
                }
            }
        }
        for i in booms.indices { booms[i].t -= dt }
        let ready = booms.filter { $0.t <= 0 }
        booms.removeAll { $0.t <= 0 }
        for bm in ready {
            let src = cell[bm.r * 100 + bm.c]
            let x = src.map { $0.x + 8 } ?? Double(BX0 + bm.c * BRW + 8)
            let y = src.map { $0.y + 4 } ?? Double(BY0 + bm.r * BRH + 4)
            parts.burst(x, y, 18, ["hotpink", "orange", "yellow", "white"], 90, 0.5)
            app.audio.play("explode")
            app.shake(2, 0.15)
            for dr in -1 ... 1 {
                for dc in -1 ... 1 {
                    let rr = bm.r + dr, cc = bm.c + dc
                    guard rr >= 0, cc >= 0, cc < COLS, let q = cell[rr * 100 + cc] else { continue }
                    if q.alive && q.breakable && !q.locked { hitBrick(q, q.kind == "gold" ? 1 : 99, nil) }
                }
            }
        }
    }

    /// COOKIE JAR spits cookies that land as bricks.
    func spawnMinions(_ count: Int) {
        var spots: [(Int, Int)] = []
        for r in 7 ..< 11 { for c in 0 ..< COLS where !(cell[r * 100 + c]?.alive ?? false) { spots.append((r, c)) } }
        var made = 0
        for (r, c) in spots.shuffled() {
            if made >= count { break }
            let br = BBBrick(r, c, Array("cpml").randomElement()!)
            if balls.contains(where: { $0.box.intersects(br.rect().inflate(4, 4)) }) { continue }
            br.flash = 0.3
            bricks.append(br)
            cell[r * 100 + c] = br
            parts.burst(br.x + 8, br.y + 4, 6, ["peach", "brown"], 40, 0.4)
            made += 1
        }
    }

    // ---------------------------------------------------------------- capsules, lasers, bonus
    func updateCaps(_ dt: Double) {
        let mag = Double(lv("magnet"))
        let half = pw() / 2
        for cap in caps {
            cap.y += 52 * dt
            if mag > 0 && cap.y > 90 && abs(cap.x - px) < 30 + 25 * mag {
                let d = px - cap.x
                cap.x += (d < 0 ? -1 : 1) * min(abs(d), (40 + 30 * mag) * dt)
            }
            if PADDLE_Y - 3 <= cap.y && cap.y <= PADDLE_Y + 7 && abs(cap.x - px) < half + 5 {
                cap.got = true
                power(cap.k)
            }
        }
        caps.removeAll { $0.got || $0.y >= Double(H + 8) }
    }

    func power(_ k: String) {
        let au = app.audio
        au.play("powerup")
        floats.add(px, PADDLE_Y - 12, CAPS[k]?.1 ?? "", "mint")
        switch k {
        case "W": timers["wide"] = 15
        case "S": timers["slow"] = 10
        case "G": timers["glue"] = 12
        case "F": timers["fire"] = 8
        case "L": timers["laser"] = 10
        case "+": lives += 1; au.play("extra")
        case "$": hype.jackpot(factorPts(3000))
        case "M":
            var src = Array(balls.filter { $0.stuck == nil }.prefix(3))
            if src.isEmpty { src = Array(balls.prefix(1)) }
            for b0 in src {
                for a in [-25.0, 25.0] where balls.count < 12 {
                    let base = (b0.vx != 0 || b0.vy != 0) ? atan2(b0.vx, -b0.vy) : 0
                    let ang = base + a * .pi / 180, sp = curSpeed()
                    balls.append(BBBall(b0.x, min(b0.y, PADDLE_Y - 6), sin(ang) * sp, -abs(cos(ang) * sp)))
                }
            }
        default: break
        }
        scoreAt(100)
    }

    func updateShots(_ dt: Double) {
        for i in shots.indices {
            shots[i].y -= 300 * dt
            if shots[i].y < TOP { shots[i].y = -99; continue }
            let sx = shots[i].x, sy = shots[i].y
            for br in bricks where br.alive && !br.isPortal && br.rect().contains(Double(Int(sx)), Double(Int(sy))) {
                hitBrick(br, 1, nil)
                shots[i].y = -99
                break
            }
            if shots[i].y > 0, let bs = boss {
                for (r, target) in bs.colliders() where r.contains(Double(Int(sx)), Double(Int(sy))) {
                    if bs.hit(target, 1) { hype.hit(1, fever: feverGain()) }
                    shots[i].y = -99
                    break
                }
            }
        }
        shots.removeAll { $0.y <= 0 }
    }

    func updateBonus(_ dt: Double) {
        bonusLeft -= dt
        if st.bonus == "coins" {
            if coins >= coinsTotal {
                hype.banner("ALL COINS!", color: "yellow", dur: 1.4, rainbow: true, sound: "bonus")
                stageClear()
                return
            }
        } else {
            sweetT -= dt
            if sweetT <= 0 && bonusLeft > 0.8 {
                let prog = 1 - bonusLeft / max(1, st.time)
                sweetT = 0.36 - 0.18 * prog
                let roll = Double.random(in: 0 ..< 1)
                let kind = roll < 0.05 ? 8 : (roll < 0.12 ? 9 : Int.random(in: 0 ..< 8))
                sweets.append(BBSweet(.random(in: (LEFT + 8) ... (RIGHT - 8)), .random(in: 50 ... 90) + 2 * Double(tier), kind))
            }
            let half = pw() / 2
            for sw in sweets {
                sw.y += sw.vy * dt
                if PADDLE_Y - 4 <= sw.y && sw.y <= PADDLE_Y + 6 && abs(sw.x - px) < half + 4 {
                    sw.got = true
                    if sw.kind == 9 {
                        paddleHit(sw.x, PADDLE_Y + 2, 6)
                    } else {
                        let gold = sw.kind == 8
                        hype.hit(1, fever: 0.05)
                        scoreAt(gold ? 500 : 100, sw.x, PADDLE_Y - 10, gold ? "yellow" : "pink")
                        app.audio.play(gold ? "coin" : "eat")
                        parts.burst(sw.x, PADDLE_Y, 6, gold ? ["yellow", "white"] : ["pink", "white"], 40, 0.4)
                        if gold { golds += 1 } else { caught += 1 }
                    }
                }
            }
            sweets.removeAll { $0.got || $0.y >= Double(H + 6) }
        }
        if bonusLeft <= 0 {
            bonusLeft = 0
            hype.banner("TIME UP!", color: "yellow", dur: 1.2)
            stageClear()
        }
    }

    /// A boss shot (or a sour drop) touches the bun: dizzy for a moment. Returns true on contact.
    @discardableResult
    func paddleHit(_ x: Double, _ y: Double, _ r: Double, beam: Bool = false) -> Bool {
        let half = pw() / 2
        if !beam && !(abs(x - px) <= half + r && PADDLE_Y - r - 1 <= y && y <= PADDLE_Y + 7 + r) { return false }
        if stun <= 0 {
            stun = 0.9
            hurt = true
            hype.breakCombo()
            app.audio.play("hurt")
            app.shake(3, 0.25)
            floats.add(px, PADDLE_Y - 10, "OUCH!", "red")
            parts.burst(px, PADDLE_Y, 8, ["red", "white"], 50, 0.4)
        }
        return true
    }

    // ---------------------------------------------------------------- clear / tally / boss
    func stageClear() {
        if state != "play" { return }
        state = "clear"
        stateT = 0
        caps = []; sweets = []; shots = []
        if hype.feverOn { hype.feverT = 0 }
        hype.slowmo(0.25, 1.0)
        hype.flash("white", 0.2)
        app.audio.play("win")
        if st.kind == "normal" {
            hype.banner("STAGE CLEAR!", color: "mint", dur: 1.4)
            hype.shower(30, "confetti")
        }
        app.audio.music(nil)
        wasFever = false
    }

    func bossDefeated() {
        app.audio.play("bossdown")
        hype.banner("BOSS DOWN!", boss?.name, dur: 2.2, rainbow: true, scale: 2)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        app.shake(6, 0.6)
        scoreAt(15000, Double(W) / 2, 70)
        stageClear()
        hype.slowmo(0.3, 1.2)
    }

    func beginTally() {
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("STAGE CLEAR", factorPts(1000)))
            let par = 40 + 0.6 * Double(total)
            rows.append(("TIME BONUS", factorPts(max(0, Int(par - stime)) * 20)))
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", factorPts(10000 + 2000 * tier)))
            rows.append(("NO DAMAGE", hurt ? 0 : factorPts(8000)))
        } else if st.bonus == "coins" {
            rows.append(("COINS \(coins)/\(coinsTotal)", factorPts(coins * 50)))
            rows.append(("ALL COINS", coins >= coinsTotal ? factorPts(10000) : 0))
        } else {
            rows.append(("SWEETS x\(caught)", factorPts(caught * 50)))
            rows.append(("GOLDEN x\(golds)", factorPts(golds * 500)))
            rows.append(("NO OUCH", hurt ? 0 : factorPts(3000)))
        }
        rows.append(("BEST COMBO \(stageCombo)", factorPts(stageCombo * 40)))
        if st.kind != "bonus" { rows.append(("NO MISS", missed ? 0 : factorPts(5000))) }
        tally = rows.map { (label: $0.0, v: $0.1, shown: 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        if st.kind != "bonus" && !missed {
            hype.banner("PERFECT!", "NO BALL LOST", dur: 1.8, rainbow: true, sound: "fever")
            hype.shower(40, "stars")
        }
    }

    func updateTally(_ dt: Double) {
        let skip = stateT > 0.3 && app.input.hit(.a)
        if tallyI < tally.count {
            if skip {           // fast-forward: count everything at once
                for i in tallyI ..< tally.count {
                    tally[i].shown = Double(tally[i].v)
                    if tally[i].v > 0 { add(tally[i].v) }
                }
                tallyI = tally.count
                app.audio.play("coin")
                return
            }
            let v = Double(tally[tallyI].v)
            tally[tallyI].shown = min(v, tally[tallyI].shown + max(1, v * dt / 0.4))
            if tally[tallyI].shown >= v {
                if tally[tallyI].v > 0 { add(tally[tallyI].v); app.audio.play("coin") }
                tallyI += 1
            }
        } else {
            tallyWait += dt
            if tallyWait > 1.6 || skip { finishStage() }
        }
    }

    func finishStage() {
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "THE BAKERIES ARE SAVED", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "SWEET TREAT!"
            state = "pick"
        } else {
            startStage(n + 1)
        }
    }

    // ---------------------------------------------------------------- drawing
    func makeBg() -> Surface {
        let s = Surface(W, H, fill: col(theme.a))
        let cb = col(theme.b)
        switch theme.pat {
        case 0:
            var y = Int(TOP)
            while y < H {
                var x = 0
                while x < W { if (x / 12 + y / 12) % 2 == 1 { s.fillRect(cb, x, y, 12, 12) }; x += 12 }
                y += 12
            }
        case 1:
            var k = -H
            while k < W + H {
                for i in 0 ..< 5 { s.line(cb, k + i, H, k + i + H - Int(TOP), Int(TOP)) }
                k += 16
            }
        case 2:
            var y = Int(TOP) + 6
            while y < H {
                var x = 4 + ((y / 14) % 2 == 1 ? 7 : 0)
                while x < W { s.circle(cb, x, y, 2); x += 14 }
                y += 14
            }
        case 3:
            var y = Int(TOP)
            while y < H {
                s.fillRect(cb, 0, y, W, 1)
                var x = (y / 12) % 2 == 1 ? 0 : 12
                while x < W { s.fillRect(cb, x, y, 1, 12); x += 24 }
                y += 12
            }
        default:
            var y = Int(TOP) + 8
            while y < H + 8 {
                var x = 0
                while x < W + 12 { s.circle(cb, x + ((y / 12) % 2 == 1 ? 6 : 0), y, 6, width: 1); x += 12 }
                y += 12
            }
        }
        s.fillRect(col("black"), 0, 0, W, Int(TOP))
        for (x0, w) in [(0, Int(LEFT)), (Int(RIGHT), W - Int(RIGHT))] {
            s.fillRect(col(theme.wall), x0, Int(TOP), w, H - Int(TOP))
            var y = Int(TOP) + 2
            while y < H { s.fillRect(col("white"), x0 + 2, y, w - 4, 1); y += 8 }
            s.fillRect(col("black"), x0 + (x0 == 0 ? w - 1 : 0), Int(TOP), 1, H - Int(TOP))
        }
        s.fillRect(col("cream"), 0, Int(TOP) - 1, W, 1)
        return s
    }

    override func render(_ s: Surface) {
        s.blit(bg, 0, 0)
        for br in bricks where br.alive || (br.kind == "jelly" && br.regrow > 0) { bbDrawBrick(s, br, t) }
        if net > 0 || (st.kind == "bonus" && st.bonus == "coins") {
            var x = Int(LEFT)
            while x < Int(RIGHT) { s.fillRect(col(Int(t * 4) % 2 == 1 ? "lime" : "mint"), x, 196, 3, 1); x += 6 }
        }
        boss?.draw(s, t)
        for cap in caps { bbDrawCap(s, cap.x, cap.y, cap.k, t) }
        for sw in sweets { bbDrawSweet(s, sw, t) }
        for sh in shots {
            s.fillRect(col("white"), Int(sh.x), Int(sh.y), 1, 5)
            s.fillRect(col(rainbow(Int(sh.y) / 6, t)), Int(sh.x), Int(sh.y) + 2, 1, 3)
        }
        drawPaddle(s)
        let fire = fireOn()
        for b in balls {
            let x = Int(b.x), y = Int(b.y)
            if fire {
                for i in 1 ..< 4 {
                    s.circle(col(rainbow(i, t)), Int(b.x - b.vx * 0.012 * Double(i)), Int(b.y - b.vy * 0.012 * Double(i)), 3 - i / 2)
                }
            }
            s.circle(col("black"), x, y, 3)
            s.circle(col(fire ? rainbow(0, t) : "hotpink"), x, y, 2)
            s.fillRect(col("white"), x - 1, y - 1, 1, 1)
        }
        if state == "play" && st.kind == "normal" && Int(t * 4) % 2 == 1 {
            let left = bricks.filter { $0.alive && $0.breakable }
            if left.count <= 3 {      // point at the last few snacks
                for br in left {
                    let x = Double(Int(br.x) + 8), y = Double(Int(br.y) - 3 - Int(abs(sin(t * 6)) * 2))
                    s.polygon(col("yellow"), [(x - 3, y - 3), (x + 3, y - 3), (x, y)])
                }
            }
        }
        parts.draw(s)
        floats.draw(s)
        drawHud(s)
        if state == "intro" {
            drawIntro(s)
        } else if state == "tally" {
            drawTally(s)
        } else if state == "play" && balls.contains(where: { $0.stuck != nil && !$0.hold }) && Int(t * 3) % 2 == 1 {
            drawText(s, "TAP LAUNCH!", W / 2, 160, "white", align: .center)
        }
        if lv("sticky") > 0 && state == "play" {
            for b in balls where b.stuck != nil && b.hold { drawAim(s, b) }
        }
    }

    func drawAim(_ s: Surface, _ b: BBBall) {
        let half = pw() / 2
        let ang = max(-1, min(1, (b.stuck ?? 0) / half)) * 45 * .pi / 180
        for i in 1 ..< 8 {
            s.fillRect(col("white"), Int(b.x + sin(ang) * Double(i) * 7), Int(b.y - cos(ang) * Double(i) * 7), 1, 1)
        }
    }

    func drawPaddle(_ s: Surface) {
        let w = Int(pw())
        let r = IRect(Int(px - pw() / 2), Int(PADDLE_Y), w, 7)
        let dizzy = stun > 0
        let sticky = (timers["glue"] ?? 0) > 0 || (lv("sticky") > 0 && app.input.down(.a))
        let body = dizzy ? "gray" : (sticky ? "yellow" : "peach")
        s.rect(col("black"), r.inflate(2, 2), radius: 4)
        s.rect(col(body), r, radius: 4)
        s.fillRect(col("cream"), r.x + 3, r.y + 1, r.w - 6, 2)
        for i in 0 ..< 3 { s.fillRect(col("choco"), r.x + 6 + i * (r.w - 12) / 2, r.y + 3, 2, 1) }
        if laserLv() > 0 { for x in [r.x + 1, r.right - 3] { s.fillRect(col("sky"), x, r.y - 2, 2, 3) } }
        if dizzy {
            for side in [-1.0, 1.0] {
                let a = t * 12 * side
                s.fillRect(col("black"), r.centerx + Int(side) * 3 + Int(cos(a)), r.y + 3 + Int(sin(a)), 1, 1)
            }
        } else {
            Cute.eyes(s, r.centerx, r.y + 3, 3, look: Int(max(-1, min(1, pvel / 100))), blink: Int(t * 1.2) % 5 == 0)
        }
    }

    func drawHud(_ s: Surface) {
        drawText(s, String(format: "%07d", score), 4, 3, "white", shadow: nil)
        if let bs = boss, bs.state != "dead" {
            bossBar(s, bs.name, Double(bs.hp), Double(bs.maxhp), t, y: 0)
        } else {
            drawText(s, String(format: "HI %07d", max(best, score)), 4, 11, "gray", shadow: nil)
            if st.kind == "bonus" && (state == "play" || state == "intro") {
                let secs = Int(bonusLeft.rounded(.up))
                drawText(s, String(format: "TIME %02d", secs), W / 2, 3, secs > 5 || Int(t * 6) % 2 == 1 ? "yellow" : "red",
                         align: .center, shadow: nil)
            } else {
                drawText(s, "STAGE \(n)", W / 2, 3, "yellow", align: .center, shadow: nil)
            }
        }
        hearts(s, W - 54, 3, lives)
        // FEVER gauge
        let x0 = W - 54, y0 = 13
        s.fillRect(col("darkgray"), x0, y0, 48, 3)
        if hype.feverOn {
            for i in 0 ..< 48 { s.fillRect(col(rainbow(i / 6, t)), x0 + i, y0, 1, 3) }
        } else {
            s.fillRect(col("orange"), x0, y0, Int(48 * hype.fever), 3)
        }
        // timed effects (bottom left)
        var x = Int(LEFT) + 3
        for (k, letter, c) in [("wide", "W", "sky"), ("slow", "S", "mint"), ("glue", "G", "yellow"), ("fire", "F", "orange"),
                               ("laser", "L", "lavender")] {
            let v = timers[k] ?? 0
            if v > 0 && (v > 2 || Int(t * 8) % 2 == 1) {
                s.rect(col(c), IRect(x, 188, 9, 7), radius: 2)
                s.blit(renderText(letter, col("black")), x + 2, 188)
                x += 12
            }
        }
        if net > 0 && st.kind != "bonus" { drawText(s, "NET x\(net)", Int(RIGHT) - 3, 188, "lime", align: .right) }
    }

    func drawIntro(_ s: Surface) {
        if st.kind == "boss" {
            if Int(t * 4) % 2 == 1 {
                var x = -20
                while x < W + 20 {
                    let fx = Double(x)
                    s.polygon(col("red"), [(fx, 108), (fx + 10, 108), (fx + 20, 116), (fx + 10, 116)])
                    s.polygon(col("red"), [(fx, 150), (fx + 10, 150), (fx + 20, 158), (fx + 10, 158)])
                    x += 20
                }
            }
            panel(s, IRect(40, 118, 240, 30), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 122, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.name) APPROACHES", W / 2, 138, "white", align: .center, shadow: nil)
            return
        }
        let h = st.newLine.isEmpty ? 50 : 62
        panel(s, IRect(30, 96, 260, h), fill: "ink", border: st.kind == "bonus" ? "yellow" : "peach")
        if st.kind == "bonus" {
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, 102 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            drawText(s, st.name, W / 2, 122, "yellow", align: .center)
            drawText(s, st.bonus == "coins" ? "BREAK ALL THE COINS!" : "CATCH THE SWEETS!", W / 2, 134, "white", align: .center)
            return
        }
        drawText(s, "STAGE \(n)", W / 2, 102, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, theme.name, W / 2, 121, "lavender", align: .center)
        drawText(s, st.name, W / 2, 132, "white", align: .center)
        if !st.newLine.isEmpty { drawText(s, st.newLine, W / 2, 145, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center) }
    }

    func drawTally(_ s: Surface) {
        let h = 34 + tally.count * 11
        let y0 = 90
        panel(s, IRect(64, y0, 192, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, W / 2, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() where i <= tallyI {
            let y = y0 + 20 + i * 11
            drawText(s, row.label, 72, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 248, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 {
            drawText(s, "TAP LAUNCH", W / 2, y0 + h - 11, "lavender", align: .center, shadow: nil)
        }
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

// ----------------------------------------------------------------------------- brick / capsule / sweet art
func bbDrawBrick(_ s: Surface, _ br: BBBrick, _ t: Double) {
    let r = IRect(Int(br.x), Int(br.y), BRW, BRH)
    let k = br.kind
    if !br.alive {         // jelly seed, growing back
        let g = Int((6.0 - br.regrow) / 6.0 * 4) + 1
        s.circle(col("teal"), r.centerx, r.centery, g)
        return
    }
    if br.flash > 0 && !br.isPortal { s.rect(col("white"), r, radius: 2); return }
    switch k {
    case "cookie", "candy", "mint", "lemon", "berry", "tin":
        Cute.brick(s, r, k, hp: br.hp)
    case "choco":       // dark outline so it reads on the brown bakeries too
        s.rect(col("black"), r, radius: 2)
        s.rect(col("brown"), r.inflate(-2, -2), radius: 2)
        s.fillRect(col("peach"), r.x + 2, r.y + 1, r.w - 4, 1)
        s.fillRect(col("choco"), r.centerx, r.y + 2, 1, r.h - 3)
        s.fillRect(col("choco"), r.x + 2, r.bottom - 2, r.w - 4, 1)
        if br.hp < 2 { s.line(col("black"), r.x + 3, r.y + 2, r.x + 7, r.bottom - 3) }
    case "fudge":
        s.rect(col("black"), r, radius: 2)
        s.rect(col("choco"), r.inflate(-2, -2), radius: 2)
        var i = 2
        while i < r.w - 2 { s.fillRect(col(br.hp >= 3 ? "white" : "pink"), r.x + i, r.y + 2 + (i / 2) % 2, 1, 1); i += 2 }
        s.fillRect(col("black"), r.x + 5, r.y + 4, 1, r.h - 5)
        s.fillRect(col("black"), r.x + 10, r.y + 4, 1, r.h - 5)
        if br.hp < 3 { s.line(col("peach"), r.x + 2, r.y + 4, r.x + 4, r.bottom - 2) }
        if br.hp < 2 { s.line(col("peach"), r.right - 3, r.y + 4, r.right - 5, r.bottom - 2) }
    case "gold":
        s.rect(col("orange"), r, radius: 2)
        s.rect(col("yellow"), r.inflate(-2, -2), radius: 2)
        let sx = r.x + Int(t * 24 + Double(br.c * 5)) % 28 - 6
        for i in 0 ..< 3 where r.x + 1 <= sx + i && sx + i < r.right - 1 { s.fillRect(col("white"), sx + i, r.y + 1, 1, r.h - 2) }
        drawText(s, "$", r.centerx - 2, r.y, "orange", shadow: nil)
        if br.hp < 3 { s.fillRect(col("orange"), r.x + 3, r.y + 5, 3, 1) }
    case "bomb":
        s.rect(col("red"), r.inflate(-2, 0), radius: 3)
        s.rect(col("hotpink"), r.inflate(-4, -2), radius: 3)
        for (dx, dy) in [(4, 3), (9, 2), (11, 5), (6, 5)] { s.fillRect(col("white"), r.x + dx, r.y + dy, 1, 1) }
        s.fillRect(col((Int(t * 8) + br.c) % 2 == 1 ? "yellow" : "orange"), r.centerx, r.y - 1, 1, 2)
    case "gift":
        s.rect(col("purple"), r, radius: 1)
        s.fillRect(col("lavender"), r.inflate(-2, -2))
        s.fillRect(col("yellow"), r.centerx - 1, r.y, 2, r.h)
        s.fillRect(col("yellow"), r.x, r.centery - 1, r.w, 1)
        s.fillRect(col("orange"), r.centerx - 3, r.y, 2, 1)
        s.fillRect(col("orange"), r.centerx + 1, r.y, 2, 1)
    case "jelly":
        let wob = max(0, Int(sin(t * 6 + Double(br.c)) * 1))
        s.rect(col("teal"), IRect(r.x, r.y + wob, r.w, r.h - wob), radius: 3)
        s.rect(col("mint"), IRect(r.x + 1, r.y + 1 + wob, r.w - 2, r.h - 3 - wob), radius: 2)
        s.fillRect(col("white"), r.x + 3, r.y + 2 + wob, 2, 1)
        s.fillRect(col("black"), r.centerx - 2, r.centery, 1, 1)
        s.fillRect(col("black"), r.centerx + 2, r.centery, 1, 1)
    case "key":
        s.rect(col("orange"), r, radius: 2)
        s.rect(col("yellow"), r.inflate(-2, -2), radius: 2)
        s.circle(col("brown"), r.x + 5, r.centery, 2, width: 1)
        s.fillRect(col("brown"), r.x + 7, r.centery, 6, 1)
        s.fillRect(col("brown"), r.x + 11, r.centery, 1, 2)
    case "lock":
        if br.locked {
            s.rect(col("black"), r, radius: 2)
            s.rect(col("darkgray"), r.inflate(-2, -2), radius: 2)
            s.fillRect(col("gray"), r.x + 2, r.y + 1, r.w - 4, 1)
            s.fillRect(col("yellow"), r.centerx - 1, r.y + 2, 2, 2)
            s.fillRect(col("yellow"), r.centerx, r.y + 4, 1, 2)
        } else {
            s.rect(col("hotpink"), r, radius: 2)
            s.rect(col("pink"), r.inflate(-2, -2), radius: 2)
            s.fillRect(col("white"), r.x + 2, r.y + 2, 3, 1)
            s.rect(col("yellow"), IRect(r.centerx - 2, r.y + 2, 4, 4), width: 1)
        }
    case "bumper":
        let rad = 4 + (br.bump > 0 ? 1 : 0)
        s.circle(col("black"), r.centerx, r.centery, rad + 1)
        s.circle(col(br.bump > 0 ? "white" : "hotpink"), r.centerx, r.centery, rad)
        s.circle(col("yellow"), r.centerx, r.centery, 2)
    case "portal", "portal2":
        let (c1, c2) = k == "portal" ? ("lavender", "purple") : ("orange", "yellow")
        let o = r.inflate(-2, 0), inr = r.inflate(-5, -3)
        s.ellipse(col(c2), o.x, o.y, o.w, o.h)
        s.ellipse(col("night"), inr.x, inr.y, inr.w, inr.h)
        let a = t * 6
        for i in 0 ..< 3 {
            s.fillRect(col(c1), r.centerx + Int(cos(a + Double(i) * 2.1) * 4), r.centery + Int(sin(a + Double(i) * 2.1) * 2), 1, 1)
        }
    case "coin":
        let w = max(1, Int(abs(cos(t * 4 + Double(br.c) * 0.5)) * 4))
        s.ellipse(col("orange"), r.centerx - w, r.y, w * 2 + 1, 8)
        s.ellipse(col("yellow"), r.centerx - w + 1, r.y + 1, max(1, w * 2 - 1), 6)
    default: break
    }
}

func bbDrawCap(_ s: Surface, _ fx: Double, _ fy: Double, _ k: String, _ t: Double) {
    let x = Int(fx), y = Int(fy)
    var c = CAPS[k]?.0 ?? "white"
    if k == "$" { c = Int(t * 10) % 2 == 1 ? "yellow" : "orange" }
    s.rect(col("black"), IRect(x - 7, y - 4, 14, 8), radius: 3)
    s.rect(col(c), IRect(x - 6, y - 3, 12, 6), radius: 3)
    s.fillRect(col("white"), x - 4, y - 2, 2, 1)
    s.blit(renderText(k, col("black")), x - 2, y - 3)
}

func bbDrawSweet(_ s: Surface, _ sw: BBSweet, _ t: Double) {
    let x = Int(sw.x), y = Int(sw.y)
    if sw.kind == 8 {
        let sp = sprite("star")
        s.blit(sp, x - sp.w / 2, y - sp.h / 2)
        if Int(t * 10) % 2 == 1 { s.fillRect(col("white"), x + 4, y - 4, 1, 1) }
    } else if sw.kind == 9 {
        s.circle(col("black"), x, y, 5)
        s.circle(col("lime"), x, y, 4)
        for a in stride(from: 0.0, to: 360.0, by: 60.0) {
            let r = (a + t * 90) * .pi / 180
            s.fillRect(col("black"), x + Int(cos(r) * 5), y + Int(sin(r) * 5), 1, 1)
        }
        Cute.eyes(s, x, y - 1, 2, mood: "angry")
    } else {
        Cute.fruit(s, sw.kind, x - 4, y - 4)
    }
}
