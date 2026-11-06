// YARN WEAVER - KUMO the fluffy gray kitten weaves yarn across the rug to claim it and reveal a hidden cat
// picture (port of mochi_arcade/games/yarn_weaver.py). Stage table in YarnWeaverData.swift (exported from Python),
// art in YarnWeaverArt.swift, bosses in YarnWeaverBoss.swift.
import Foundation

private let OPEN: UInt8 = 0, CLAIMED: UInt8 = 1, TRAIL: UInt8 = 2
private let GW = YW_GW, GH = YW_GH, PW = YW_PW, PH = YW_PH, FX = YW_FX, FY = YW_FY
private let DIRS: [Action: (Int, Int)] = [.left: (-1, 0), .right: (1, 0), .up: (0, -1), .down: (0, 1)]
private let DIR_ORDER: [Action] = [.left, .right, .up, .down]
private let LIFE_AT = [30000, 80000, 160000, 300000]      // then every 200000
private let POM_COLS = ["pink", "mint", "sky", "yellow", "lavender", "peach", "lime"]
private let SNAP_TEXT = ["fluff": "SNAP!", "zip": "ZAPPED!", "moth": "NIBBLED!", "fray": "UNRAVELLED!", "knot": "TANGLED!",
                         "nose": "SNIFFED!", "storm": "STATIC!", "pellet": "PELLET!", "bolt": "ZAP!", "bark": "WOOF!",
                         "boss": "BONK!", "pom": "BOING!"]
private let ITEM_TEXT = ["fish": "FISH TREAT!", "nip": "CATNIP RUSH!", "bell": "JINGLE! FREEZE!", "heart": "EXTRA LIFE!",
                         "gold": "GOLDEN YARN!", "rainbow": "RAINBOW YARN!"]

// ----------------------------------------------------------------------------- upgrade cards
let YW_UPGRADES: [Upgrade] = [
    Upgrade(id: "quick", name: "QUICK PAWS", desc: "KUMO MOVES|10% FASTER", color: "pink", draw: { s, cx, cy, t in
        for (i, dx) in [-5, 3].enumerated() {
            let y = cy - 2 + (Int(t * 8) + i) % 2 * 3
            s.circle(col("pink"), cx + dx, y, 3)
            s.fillRect(col("white"), cx + dx - 1, y - 4, 1, 1)
            s.fillRect(col("white"), cx + dx + 1, y - 4, 1, 1)
        }
    }, max: 3),
    Upgrade(id: "knit", name: "TIGHT KNIT", desc: "CAREFUL WEAVE|IS FASTER AND|SCORES MORE", color: "mint", draw: { s, cx, cy, _ in
        for i in stride(from: -6, through: 6, by: 3) { s.fillRect(col(ywDiv(i, 3) % 2 != 0 ? "white" : "mint"), cx + i, cy, 2, 2) }
        s.line(col("gray"), cx - 6, cy - 6, cx + 6, cy + 6)
    }, max: 2),
    Upgrade(id: "guard", name: "STURDY YARN", desc: "BLOCKS ONE|SNAP EVERY|STAGE PER LV", color: "sky", draw: { s, cx, cy, _ in
        s.polygon(col("sky"), [(Double(cx - 6), Double(cy - 6)), (Double(cx + 6), Double(cy - 6)), (Double(cx + 6), Double(cy)),
                               (Double(cx), Double(cy + 7)), (Double(cx - 6), Double(cy))])
        s.fillRect(col("hotpink"), cx - 6, cy - 1, 13, 2)
    }, max: 3),
    Upgrade(id: "claws", name: "SHARP CLAWS", desc: "POUNCE ON A|ZIP INSTEAD|OF GETTING HIT", color: "yellow", draw: { s, cx, cy, _ in
        for i in 0 ..< 3 { s.line(col("white"), cx - 5 + i * 4, cy - 6, cx - 7 + i * 4, cy + 5) }
        s.circle(col("yellow"), cx + 5, cy + 4, 2)
    }, max: 2),
    Upgrade(id: "life", name: "NINE LIVES", desc: "+1 LIFE|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
    Upgrade(id: "luck", name: "LUCKY BELL", desc: "MORE TREATS|AND JACKPOTS", color: "orange", draw: { s, cx, cy, t in
        s.blit(sprite("yw_bell"), cx - 3, cy - 4 + Int(sin(t * 6)))
    }, max: 3),
    Upgrade(id: "fever", name: "PURR POWER", desc: "FEVER FILLS|FASTER AND|LASTS LONGER", color: "yellow", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
    Upgrade(id: "cozy", name: "COZY CORNERS", desc: "STAGES START|WITH CLAIMED|CORNERS", color: "hotpink", draw: { s, cx, cy, _ in
        for (dx, dy) in [(-7, -7), (3, -7), (-7, 3), (3, 3)] { s.fillRect(col("hotpink"), cx + dx, cy + dy, 5, 5) }
    }, max: 3),
    Upgrade(id: "calm", name: "CALM ROOM", desc: "HAZARDS|MOVE 8%|SLOWER", color: "lavender", draw: { s, cx, cy, t in
        YWArt.drawFluff(s, Double(cx), Double(cy), 4, t * 0.3, angry: false)
    }, max: 3),
    Upgrade(id: "strong", name: "STRONG YARN", desc: "LOOSE YARN|FRAYS LATER|AND SLOWER", color: "orange", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.line(col(i == 1 ? "orange" : "yellow"), cx - 6, cy - 3 + i * 3, cx + 6, cy - 3 + i * 3) }
        if Int(t * 6) % 2 == 1 { s.fillRect(col("red"), cx + 5, cy - 1, 2, 2) }
    }, max: 2),
]

// ----------------------------------------------------------------------------- objects
/// Fluff (static ball), fuzzlet (mini), pom-pom (bonus) or a boss minion: bounces around the open rug.
final class YWBall: YWBouncer {
    var x, y, vx, vy: Double
    let r: Int
    let kind, color: String
    var speed: Double
    var turn = Double.random(in: 0.8 ... 2.5)
    var zap = 0.0           // STATIC STORM charge-up
    var born = 0.0          // harmless while popping in (respawns)
    var stuck = 0
    var alive = true
    init(_ x: Double, _ y: Double, _ r: Int, _ speed: Double, _ kind: String, _ color: String) {
        let a = Double.random(in: 0 ..< 2 * .pi)
        self.x = x; self.y = y; self.r = r; self.kind = kind; self.color = color; self.speed = speed
        vx = cos(a) * speed; vy = sin(a) * speed
    }
}

final class YWZip {
    var c: Int
    let hunter: Bool
    var dx: Int, dy = 0
    var acc = 0.0, born = 0.6
    var alive = true
    init(_ c: Int, _ hunter: Bool) { self.c = c; self.hunter = hunter; dx = Bool.random() ? 1 : -1 }
}

final class YWMoth {
    var x, y: Double
    var vx = 0.0, vy = 0.0
    let hx = Double.random(in: 60 ... 244), hy = Double.random(in: 40 ... 136)
    var t = Double.random(in: 0 ..< 10)
    var alive = true
    init(_ x: Double, _ y: Double) { self.x = x; self.y = y }
}

final class YWItem {
    var x, y: Double
    let kind: String
    var life: Double
    init(_ x: Double, _ y: Double, _ kind: String, _ life: Double = 12) { self.x = x; self.y = y; self.kind = kind; self.life = life }
}

// ----------------------------------------------------------------------------- the game
final class YarnWeaver: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD   WALK THE YARN / WEAVE INTO RUG", "SLOW  HOLD: CAREFUL WEAVE (X2 POINTS)"]
    static let helpSkip = 2

    override var music: String? { song() }
    override var buttons: [Action: String] { [.a: "SLOW"] }
    override var buttonOrder: [Action] { [.a] }
    override var fourWay: Bool { true }

    var lives: Int
    let dspeed: Double
    var levels: [String: Int] = [:]
    var lifeI = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    var wasFever = false
    var lastDir: Action?
    var friends = 0
    private var rugs: [Int: Surface] = [:]
    // stage
    var n = 1
    var st: YWStage = YWData.stages[0]
    var tier = 0
    var theme: YWTheme = YWData.themes[0]
    var grid: [UInt8] = []
    var furn: [UInt8] = []
    var claimable = 1, openN = 1
    var trail: [Int] = [], trailSlow: [Bool] = []
    var weaving = false, careful = false
    var anchor = (YW_GW / 2, YW_GH - 1)
    var kx = YW_GW / 2, ky = YW_GH - 1
    var kacc = 0.0
    var kprev: (Int, Int)?
    var kface = 1
    var kmoveT = 0.0, fray = -1.0, idle = 0.0
    var inv = 0.0, hurtT = 0.0, happyT = 0.0, stun = 0.0
    var freeze = 0.0, nip = 0.0, trailSafe = 0.0
    var recoil: [(c: Int, life: Double)] = []
    var balls: [YWBall] = [], zips: [YWZip] = [], moths: [YWMoth] = [], items: [YWItem] = []
    var wraps: [(x: Double, y: Double, age: Double, c: String)] = []
    var respawns: [(t: Double, kind: String)] = []
    var storms: [(x: Double, y: Double, r: Double)] = []
    var knots: [(x: Int, y: Int, alive: Bool)] = []
    var nose = (st: "wait", t: 0.0, x: 0.0, y: 0.0)
    var guardN = 0, claws = 0
    var hzSpeed = 1.0
    var itemT = 0.0, stormT = 0.0, stime = 0.0
    var missed = false
    var wrappedN = 0, stageCombo = 0, claims = 0
    var pomsTotal = 0, pomsWrapped = 0, fishTotal = 0, fishGot = 0
    var bonusLeft = 0.0
    var golden = false
    var boss: YWBoss?
    var pic = Surface(YW_PW, YW_PH), rug = Surface(YW_PW, YW_PH), furnS = Surface(YW_PW, YW_PH), field = Surface(YW_PW, YW_PH)
    var revealList: [Int] = []
    var revealI = 0
    var state = "setup"
    var stateT = 0.0, introLen = 2.6
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        dspeed = SPEEDS[d] ?? 1
        super.init(app, info, opt)
        hype.comboTime = 5.0          // claims take a while: a longer window to chain them
        hype.comboY = 23
        let start = max(1, min(STAGES, optInt("level", optInt("start", 1))))
        startStage(start)
        if start > 10 {               // starting from a checkpoint: catch up on some upgrades first
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
    func song() -> String { st.kind == "boss" ? "boss" : (st.kind == "bonus" ? "bonus" : theme.song) }
    func carefulMult() -> Double { 2.0 + 0.5 * Double(lv("knit")) }
    func kumoSpeed(_ careful: Bool) -> Double {
        var sp = 38.0 * (1 + 0.1 * Double(lv("quick")))
        if careful { sp *= 0.5 + 0.1 * Double(lv("knit")) }
        if nip > 0 { sp *= 1.4 }
        if hype.feverOn { sp *= 1.2 }
        return sp
    }
    func feverGain(_ x: Double) -> Double { x * (1 + 0.35 * Double(lv("fever"))) }
    func kumoPx() -> (Double, Double) { (Double(kx * 2) + 1, Double(ky * 2) + 1) }
    var claimed: Int { claimable - openN }
    func percent() -> Int { 100 * claimed / max(1, claimable) }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        state = "setup"
        n = num
        st = YWData.stages[num - 1]
        tier = st.tier
        theme = YWData.themes[min(tier, YWData.themes.count - 1)]
        reached(num)
        grid = YWData.baseGrid(st.shapes)
        furn = [UInt8](repeating: 0, count: GW * GH)
        YWData.applyShapes(&furn, st.shapes)
        claimable = grid.filter { $0 == OPEN }.count
        openN = claimable
        let cz = lv("cozy")
        if cz > 0 && st.kind != "bonus" {
            let k = 3 + 4 * cz
            for (x0, y0) in [(1, 1), (GW - 1 - k, 1), (1, GH - 1 - k), (GW - 1 - k, GH - 1 - k)] {
                for y in y0 ..< y0 + k {
                    for x in x0 ..< x0 + k where grid[y * GW + x] == OPEN {
                        grid[y * GW + x] = CLAIMED
                        openN -= 1
                    }
                }
            }
        }
        trail = []; trailSlow = []
        weaving = false; careful = false
        anchor = (GW / 2, GH - 1)
        kx = GW / 2; ky = GH - 1
        kacc = 0; kprev = nil; kface = 1; kmoveT = 0
        fray = -1; idle = 0
        inv = 0; hurtT = 0; happyT = 0; stun = 0
        freeze = 0; nip = 0; trailSafe = 0
        recoil = []
        balls = []; zips = []; moths = []; items = []; wraps = []; respawns = []; storms = []
        knots = st.knots.map { (x: $0.0, y: $0.1, alive: true) }
        nose = (st: "wait", t: st.nose * Double.random(in: 0.6 ... 1.0), x: 0, y: 0)
        guardN = lv("guard")
        claws = lv("claws")
        hzSpeed = dspeed * (1 - 0.08 * Double(lv("calm")))
        itemT = st.items * Double.random(in: 0.4 ... 0.8)
        stormT = st.storm * Double.random(in: 0.7 ... 1.0)
        stime = 0
        missed = false
        wrappedN = 0; stageCombo = 0; claims = 0
        pomsTotal = 0; pomsWrapped = 0; fishTotal = 0; fishGot = 0
        bonusLeft = st.time
        golden = st.kind == "normal" && hype.lucky(0.02 + 0.01 * Double(lv("luck")))
        boss = nil
        for _ in 0 ..< st.fluffs { spawnBall("fluff") }
        for _ in 0 ..< st.minis { spawnBall("mini") }
        for i in 0 ..< st.zips { zips.append(YWZip(GW * (i + 1) / (st.zips + 1), i >= st.zips - st.hunters)) }
        for _ in 0 ..< st.moths { moths.append(YWMoth(Bool.random() ? -6.0 : Double(PW) + 6, Double.random(in: 10 ... 80))) }
        if st.kind == "bonus" {
            if st.bonus == "poms" {
                for _ in 0 ..< st.poms { spawnBall("pom") }
                pomsTotal = st.poms
            } else {
                for _ in 0 ..< st.fish {
                    let (x, y) = findSpot(6, 40)
                    items.append(YWItem(x, y, "fish", 999))
                }
                fishTotal = st.fish
                spawnBall("pom")
            }
        }
        if let b = st.boss { boss = YWBoss(self, b) }
        // pictures
        pic = Surface(PW, PH)
        YWArt.drawPicture(pic, st.pic, golden: golden)
        if let r = rugs[tier] {
            rug = r
        } else {
            let r = Surface(PW, PH)
            YWArt.makeRug(r, theme)
            rugs = [tier: r]
            rug = r
        }
        furnS = rug.copy()
        for sh in st.shapes { YWArt.drawFurniture(furnS, sh) }
        field = rug.copy()
        for i in 0 ..< GW * GH where grid[i] == CLAIMED { paint(i) }
        revealList = []
        revealI = 0
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.2 : 2.6
        tally = []
        hype.comboY = 23
        if hype.feverOn { hype.feverT = 0 }
        wasFever = false
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    // ---------------------------------------------------------------- the grid
    func cellAt(_ x: Double, _ y: Double) -> Int {
        let cx = Int((x / 2).rounded(.down)), cy = Int((y / 2).rounded(.down))
        return cx >= 0 && cx < GW && cy >= 0 && cy < GH ? cy * GW + cx : -1
    }

    func blocked(_ x: Double, _ y: Double) -> Bool {
        let c = cellAt(x, y)
        return c < 0 || grid[c] != OPEN
    }

    func isEdge(_ i: Int) -> Bool {
        if grid[i] != CLAIMED { return false }
        let x = i % GW, y = i / GW
        for yy in y - 1 ... y + 1 where yy >= 0 && yy < GH {
            for xx in x - 1 ... x + 1 where xx >= 0 && xx < GW {
                if grid[yy * GW + xx] != CLAIMED { return true }
            }
        }
        return false
    }

    func yarnCol(_ x: Int, _ y: Int) -> String { ((x + y) / 2) % 2 == 0 ? theme.yarnA : theme.yarnB }

    private func copyCell(_ src: Surface, _ x: Int, _ y: Int) {
        let b = y * 2 * PW + x * 2
        field.px[b] = src.px[b]; field.px[b + 1] = src.px[b + 1]
        field.px[b + PW] = src.px[b + PW]; field.px[b + PW + 1] = src.px[b + PW + 1]
    }

    func paint(_ i: Int) {
        let x = i % GW, y = i / GW
        if grid[i] != CLAIMED {
            copyCell(rug, x, y)
        } else if isEdge(i) {
            field.fillRect(col(yarnCol(x, y)), x * 2, y * 2, 2, 2)
        } else if furn[i] != 0 {
            copyCell(furnS, x, y)
        } else {
            copyCell(pic, x, y)
        }
    }

    /// A random open spot with r pixels of clear rug around it, at least `far` px from KUMO (or avoid).
    func findSpot(_ r: Double, _ far: Double, _ avoid: (Double, Double)? = nil) -> (Double, Double) {
        let (ax, ay) = avoid ?? kumoPx()
        var best: (Double, Double)?
        for k in 0 ..< 300 {
            let x = Double.random(in: r + 3 ... Double(PW) - r - 3), y = Double.random(in: r + 3 ... Double(PH) - r - 3)
            if clearAt(x, y, r) {
                if ((x - ax) * (x - ax) + (y - ay) * (y - ay)).squareRoot() >= far || k > 200 { return (x, y) }
                if best == nil { best = (x, y) }
            }
        }
        if let b = best { return b }
        for i in 0 ..< GW * GH where grid[i] == OPEN { return (Double((i % GW) * 2) + 1, Double((i / GW) * 2) + 1) }
        return (Double(PW) / 2, Double(PH) / 2)
    }

    func clearAt(_ x: Double, _ y: Double, _ r: Double) -> Bool {
        for yy in stride(from: Int(y - r), through: Int(y + r), by: 2) {
            for xx in stride(from: Int(x - r), through: Int(x + r), by: 2) where blocked(Double(xx), Double(yy)) { return false }
        }
        return true
    }

    /// Does a circle at (x, y) touch the loose yarn?
    func trailHit(_ x: Double, _ y: Double, _ rad: Int) -> Bool {
        if trail.isEmpty || trailSafe > 0 { return false }
        let r = Double(rad)
        let x0 = max(0, Int(x - r) / 2), x1 = min(GW - 1, Int(x + r) / 2)
        let y0 = max(0, Int(y - r) / 2), y1 = min(GH - 1, Int(y + r) / 2)
        if x0 > x1 || y0 > y1 { return false }
        let rr = (r + 1) * (r + 1)
        for cy in y0 ... y1 {
            for cx in x0 ... x1 where grid[cy * GW + cx] == TRAIL {
                let dx = Double(cx * 2 + 1) - x, dy = Double(cy * 2 + 1) - y
                if dx * dx + dy * dy <= rr { return true }
            }
        }
        return false
    }

    func kumoHit(_ x: Double, _ y: Double, _ rad: Int) -> Bool {
        if !weaving { return false }
        let (px, py) = kumoPx()
        return ((px - x) * (px - x) + (py - y) * (py - y)).squareRoot() < Double(rad + 3)
    }

    @discardableResult
    func touchCheck(_ x: Double, _ y: Double, _ r: Int, _ kind: String) -> Bool {
        if trailHit(x, y, r) || kumoHit(x, y, r) {
            hazardHit(kind, x, y)
            return true
        }
        return false
    }

    /// A bark / static wave of radius r: it snaps loose yarn it passes over.
    func ringCheck(_ x: Double, _ y: Double, _ r: Double) {
        if !weaving { return }
        for c in trail {
            let dx = Double((c % GW) * 2 + 1) - x, dy = Double((c / GW) * 2 + 1) - y
            if abs((dx * dx + dy * dy).squareRoot() - r) <= 3 { hazardHit("bark", x, y); return }
        }
        let (px, py) = kumoPx()
        if abs(((px - x) * (px - x) + (py - y) * (py - y)).squareRoot() - r) <= 4 { hazardHit("bark", x, y) }
    }

    func strikeColumn(_ x: Double) {
        if !weaving { return }
        let (px, _) = kumoPx()
        if abs(px - x) <= 4 || trail.contains(where: { abs(Double((($0 % GW) * 2) + 1) - x) <= 3 }) { hazardHit("bolt", x, 0) }
    }

    // ---------------------------------------------------------------- spawning
    @discardableResult
    func spawnBall(_ kind: String, _ px: Double? = nil, _ py: Double? = nil, _ color: String? = nil) -> YWBall {
        let sp = st.fspeed * hzSpeed
        var r = 6, speed = 34.0 + 2 * Double(tier), c = color ?? POM_COLS.randomElement()!
        if kind == "fluff" {
            r = 7; speed = sp; c = "gray"
        } else if kind == "mini" {
            r = 4; speed = sp * 1.35; c = color ?? "gray"
        }
        var x = px ?? 0, y = py ?? 0
        if px == nil { (x, y) = findSpot(Double(r + 2), 60) }
        let b = YWBall(x, y, r, speed, kind, c)
        if state == "play" { b.born = kind == "mini" ? 0.4 : 0.8 }
        balls.append(b)
        return b
    }

    func spawnMinion(_ kind: String, _ x: Double, _ y: Double) {
        if kind == "moth" {
            if moths.count < 6 { moths.append(YWMoth(x, y)) }
        } else if balls.filter({ $0.kind == "mini" }).count < 8 {
            spawnBall("mini", x, y, kind == "cloud" ? "lavender" : "gray")
        }
    }

    func respawn(_ kind: String, _ delay: Double) { respawns.append((t: delay, kind: kind)) }

    /// An edge cell far from KUMO for a (re)spawning zip.
    func zipHome() -> Int? {
        var best: Int?, bd = -1
        for _ in 0 ..< 400 {
            let i = Int.random(in: 0 ..< GW * GH)
            if isEdge(i) {
                let d = abs(i % GW - kx) + abs(i / GW - ky)
                if d > bd { best = i; bd = d }
                if bd > 70 { break }
            }
        }
        return best
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        let inp = app.input
        switch state {
        case "intro":
            boss?.update(dt)
            if stateT > introLen || (stateT > 0.6 && inp.hit(.a)) {
                state = "play"
                stateT = 0
                boss?.state = "fight"
            }
        case "play":
            play(dt)
        case "clear":
            boss?.update(dt)
            if stateT > 1.1 { beginReveal() }
        case "reveal":
            updateReveal(dt)
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(YW_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nn = nextN {
                startStage(nn)
            } else {
                state = "intro"
                stateT = 0
            }
        default: break
        }
        for i in wraps.indices { wraps[i].age += dt }
        wraps.removeAll { $0.age >= 1.0 }
        for i in recoil.indices { recoil[i].life -= dt }
        recoil.removeAll { $0.life <= 0 }
        happyT = max(0, happyT - dt)
        hurtT = max(0, hurtT - dt)
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = YW_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id] ?? 1)", color: u.color, dur: 1.2, scale: 1)
        }
        if id == "life" { lives += 1; app.audio.play("extra") } else if id == "guard" { guardN += 1 } else if id == "claws" { claws += 1 }
    }

    func play(_ dt: Double) {
        stime += dt
        inv = max(0, inv - dt)
        stun = max(0, stun - dt)
        freeze = max(0, freeze - dt)
        nip = max(0, nip - dt)
        trailSafe = max(0, trailSafe - dt)
        kmoveT = max(0, kmoveT - dt)
        moveKumo(dt)
        if state != "play" { return }
        updateFray(dt)
        if state != "play" { return }
        updateBalls(dt)
        updateZips(dt)
        updateMoths(dt)
        updateNose(dt)
        updateStorms(dt)
        updateItems(dt)
        boss?.update(dt)
        if state != "play" { return }
        for i in respawns.indices {
            respawns[i].t -= dt
            if respawns[i].t <= 0 {
                let k = respawns[i].kind
                if k == "zip" {
                    if let c = zipHome() { zips.append(YWZip(c, false)) }
                } else if k == "moth" {
                    moths.append(YWMoth(Bool.random() ? -6.0 : Double(PW) + 6, Double.random(in: 10 ... Double(PH) - 10)))
                } else {
                    spawnBall(k)
                }
            }
        }
        respawns.removeAll { $0.t <= 0 }
        if st.kind == "bonus" {
            bonusLeft -= dt
            if bonusLeft <= 0 {
                bonusLeft = 0
                hype.banner("TIME UP!", color: "yellow", dur: 1.2)
                stageClear()
                return
            }
        }
        stageCombo = max(stageCombo, hype.combo)
        if hype.feverOn && !wasFever {
            hype.feverT += 2 * Double(lv("fever"))
            app.audio.music("fever")
            let (px, py) = kumoPx()
            floats.add(Double(FX) + px, Double(FY) + py - 16, "RAINBOW YARN!", "yellow")
        } else if wasFever && !hype.feverOn {
            app.audio.music(song())
        }
        wasFever = hype.feverOn
        checkLife()
    }

    func checkLife() {
        let i = lifeI
        let target = i < LIFE_AT.count ? LIFE_AT[i] : LIFE_AT[LIFE_AT.count - 1] + 200000 * (i - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("BONUS LIFE!", "\(target) POINTS", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    // ---------------------------------------------------------------- KUMO
    func heldDir() -> Action? {
        let inp = app.input
        for a in DIR_ORDER where inp.hit(a) { lastDir = a }
        if let l = lastDir, inp.down(l) { return l }
        for a in DIR_ORDER where inp.down(a) { return a }
        return nil
    }

    func moveKumo(_ dt: Double) {
        let d = heldDir()
        careful = app.input.down(.a)          // careful: slow and precise, x2 stitches
        guard let dir = d, stun <= 0 else {
            kacc = 0
            if weaving { idle += dt }
            return
        }
        kacc += kumoSpeed(careful) * dt
        var moved = false
        while kacc >= 1 {
            kacc -= 1
            if !step(dir) { kacc = 0; break }
            moved = true
            if state != "play" || stun > 0 { break }
        }
        if moved {
            idle = 0
            kmoveT = 0.15
            if let dd = DIRS[dir], dd.0 != 0 { kface = dd.0 }
        } else if weaving {
            idle += dt
        }
    }

    func step(_ d: Action) -> Bool {
        guard let dd = DIRS[d] else { return false }
        let (dx, dy) = dd
        let nx = kx + dx, ny = ky + dy
        if !(nx >= 0 && nx < GW && ny >= 0 && ny < GH) { return weaving ? false : slide(dx, dy) }
        let i = ny * GW + nx
        let v = grid[i]
        if !weaving {
            if v == OPEN {
                weaving = true
                anchor = (kx, ky)
                trail = [i]; trailSlow = [careful]
                grid[i] = TRAIL
                kprev = (kx, ky)
                kx = nx; ky = ny
                fray = 0; idle = 0
                app.audio.play("hold")
                afterStep()
                return true
            }
            if v == CLAIMED && isEdge(i) {
                kprev = (kx, ky)
                kx = nx; ky = ny
                afterStep()
                return true
            }
            return slide(dx, dy)
        }
        if v == OPEN {
            grid[i] = TRAIL
            trail.append(i)
            trailSlow.append(careful)
            kprev = (kx, ky)
            kx = nx; ky = ny
            afterStep()
            return true
        }
        if v == CLAIMED {
            kprev = (kx, ky)
            kx = nx; ky = ny
            finishWeave()
            return true
        }
        return false                       // can't cross your own loose yarn
    }

    /// Walking along the yarn: if the way ahead is blocked, follow the edge round the corner.
    func slide(_ dx: Int, _ dy: Int) -> Bool {
        var opts: [(Int, Int)] = []
        for (sx, sy) in [(dy, dx), (-dy, -dx)] {
            let nx = kx + sx, ny = ky + sy
            if nx >= 0 && nx < GW && ny >= 0 && ny < GH && !(kprev.map { $0.0 == nx && $0.1 == ny } ?? false) && isEdge(ny * GW + nx) {
                opts.append((nx, ny))
            }
        }
        if opts.count != 1 { return false }
        kprev = (kx, ky)
        (kx, ky) = opts[0]
        afterStep()
        return true
    }

    func afterStep() {
        let (x, y) = kumoPx()
        for it in items where it.life > 0 && abs(it.x - x) < 7 && abs(it.y - y) < 7 { collect(it) }
        if weaving {
            for k in knots where k.alive && abs(Double(k.x * 2 + 1) - x) < 6 && abs(Double(k.y * 2 + 1) - y) < 6 {
                hazardHit("knot", x, y)
                return
            }
        }
    }

    /// Stand still while weaving and the loose yarn starts to fray from where you began.
    func updateFray(_ dt: Double) {
        if !weaving { return }
        let delay = 0.9 + 0.5 * Double(lv("strong"))
        if idle > delay {
            fray += Double(26 - 6 * lv("strong")) * dt
            if Int(fray * 4) % 6 == 0 {
                let c = trail[min(trail.count - 1, Int(fray))]
                parts.sparkle(Double(FX + (c % GW) * 2 + 1), Double(FY + (c / GW) * 2 + 1), "orange")
            }
            if fray >= Double(trail.count) {
                let (x, y) = kumoPx()
                hazardHit("fray", x, y)
            }
        }
    }

    // ---------------------------------------------------------------- claiming
    func finishWeave() {
        weaving = false
        for c in trail { grid[c] = CLAIMED }
        claim()
    }

    func claim() {
        let tr = trail
        let slow = trailSlow.filter { $0 }.count
        trail = []; trailSlow = []
        fray = -1
        let regs = YWData.openRegions(grid)
        var keep = -1
        var bestLen = -1
        for (k, r) in regs.enumerated() where r.count > bestLen { keep = k; bestLen = r.count }
        if let b = boss, b.state == "fight" {
            let bc = cellAt(b.x, b.y)
            for (k, r) in regs.enumerated() where r.contains(bc) { keep = k; break }
        }
        var newly = tr
        for (k, r) in regs.enumerated() where k != keep {
            for c in r { grid[c] = CLAIMED }
            newly.append(contentsOf: r)
        }
        openN = keep >= 0 ? regs[keep].count : 0
        var mark = [Bool](repeating: false, count: GW * GH)
        for c in newly { mark[c] = true }
        // repaint the newly claimed cells and their neighbours (old edges may now be inside)
        var dirty = [Bool](repeating: false, count: GW * GH)
        for c in newly {
            let x = c % GW, y = c / GW
            for yy in y - 1 ... y + 1 where yy >= 0 && yy < GH {
                for xx in x - 1 ... x + 1 where xx >= 0 && xx < GW { dirty[yy * GW + xx] = true }
            }
        }
        for c in 0 ..< GW * GH where dirty[c] && grid[c] == CLAIMED { paint(c) }
        // score: bigger single claims are worth more, careful stitches multiply
        let cells = newly.count
        let frac = Double(cells) / Double(max(1, claimable))
        let stitch = 1 + (Double(slow) / Double(max(1, tr.count))) * (carefulMult() - 1)
        let sx = Double(newly.reduce(0) { $0 + $1 % GW } * 2 / max(1, cells) + FX)
        let sy = Double(newly.reduce(0) { $0 + $1 / GW } * 2 / max(1, cells) + FY)
        let mult = st.kind == "bonus" ? 2 : 1
        let pts = Int(Double(cells) * (1 + 3 * frac) * stitch) * mult
        scoreAt(pts, sx, sy)
        claims += 1
        hype.hit(1, fever: feverGain(0.05 + frac * 1.4))
        if hype.combo > 1 { add(factorPts(hype.comboBonus(20))) }
        if stitch > 1.05 { floats.add(sx, sy - 10, String(format: "STITCH X%.1f", stitch), "mint") }
        happyT = 0.7
        for k in stride(from: 0, to: tr.count, by: 3) {
            let c = tr[k]
            parts.burst(Double(FX + (c % GW) * 2 + 1), Double(FY + (c / GW) * 2 + 1), 2, [theme.yarnA, theme.yarnB, "white"], 30, 0.5)
        }
        let au = app.audio
        headline(frac, wrapCaught(mark), cells)
        if frac >= 0.05 && hype.lucky(0.015 + 0.005 * Double(lv("luck"))) {
            hype.jackpot(factorPts(3000), sub: "LUCKY STITCH!")
        }
        // the boss loses rug
        if let b = boss, b.state == "fight" {
            let r2 = Double((b.r + 22) * (b.r + 22))
            let near = newly.contains { c in
                let dx = Double((c % GW) * 2 + 1) - b.x, dy = Double((c / GW) * 2 + 1) - b.y
                return dx * dx + dy * dy <= r2
            }
            let dmg = b.damage(cells, near)
            if dmg > 0 {
                hype.hitstop(0.08)
                floats.add(Double(FX) + b.x, Double(FY) + b.y - Double(b.r) - 8, near ? "CLOSE WEAVE! X2" : "-\(dmg)",
                           near ? "hotpink" : "white")
                parts.burst(Double(FX) + b.x, Double(FY) + b.y, 14, ["white", "yellow", "pink"], 70, 0.5)
                au.play("explode")
            }
            if b.hp > 0 && Double(openN) < Double(claimable) * 0.06 {
                b.hp = 0
                hype.banner("CORNERED!", color: "yellow", dur: 1.2)
            }
            if b.hp <= 0 { bossDefeated(); return }
        }
        // KUMO must stand on yarn
        if !isEdge(ky * GW + kx) { relocateKumo() }
        if st.kind == "normal" && percent() >= st.target {
            stageClear()
        } else if st.kind == "bonus" {
            if st.bonus == "poms" && pomsWrapped >= pomsTotal {
                hype.banner("ALL ROUNDED UP!", dur: 1.4, rainbow: true, sound: "bonus")
                stageClear()
            } else if percent() >= 95 {
                stageClear()
            }
        }
    }

    /// One headline per claim: the biggest news wins (weave size or wrapped hazards).
    func headline(_ frac: Double, _ n: Int, _ cells: Int) {
        let pct = Int(frac * 100)
        if frac >= 0.33 {
            hype.banner("MEGA WEAVE!!!", "\(pct)% IN ONE GO", dur: 1.8, rainbow: true, sound: "jackpot")
            hype.shower(70, "confetti")
            hype.flash("white", 0.3)
            hype.slowmo(0.4, 0.6)
            app.shake(4, 0.4)
        } else if n >= 3 {
            hype.banner("MEGA WRAP!!", "\(n) AT ONCE", dur: 1.6, rainbow: true, sound: "fever")
            hype.shower(50, "confetti")
        } else if frac >= 0.2 {
            hype.banner("HUGE WEAVE!!", "\(pct)%", color: "hotpink", dur: 1.4, sound: "quad")
            hype.shower(40, "stars")
            app.shake(3, 0.25)
        } else if n == 2 {
            hype.banner("DOUBLE WRAP!", color: "lime", dur: 1.2, sound: "combo")
            hype.shower(20, "stars")
        } else if frac >= 0.1 {
            hype.banner("BIG WEAVE!", color: "yellow", dur: 1.1, scale: 1, sound: "line")
        } else if n == 1 {
            hype.banner("WRAPPED!", color: "lime", dur: 1.0, scale: 1, sound: "trap")
        } else {
            app.audio.play(cells > 60 ? "line" : "lock")
        }
    }

    /// Hazards, treats and knots inside the claimed pocket get wrapped up. Returns how many hazards.
    @discardableResult
    func wrapCaught(_ mark: [Bool]) -> Int {
        var caught: [(kind: String, x: Double, y: Double, c: String)] = []
        for b in balls {
            let c = cellAt(b.x, b.y)
            if c >= 0 && mark[c] { b.alive = false; caught.append((b.kind, b.x, b.y, b.color)) }
        }
        balls.removeAll { !$0.alive }
        for z in zips where !isEdge(z.c) {
            z.alive = false
            caught.append(("zip", Double((z.c % GW) * 2) + 1, Double((z.c / GW) * 2) + 1, "yellow"))
        }
        zips.removeAll { !$0.alive }
        for m in moths {
            let c = cellAt(m.x, m.y)
            if c >= 0 && mark[c] { m.alive = false; caught.append(("moth", m.x, m.y, "cream")) }
        }
        moths.removeAll { !$0.alive }
        for it in items {
            let c = cellAt(it.x, it.y)
            if c >= 0 && mark[c] { collect(it) }
        }
        for k in knots.indices where knots[k].alive && mark[knots[k].y * GW + knots[k].x] {
            knots[k].alive = false
            scoreAt(800, Double(FX + knots[k].x * 2), Double(FY + knots[k].y * 2 - 6), "lavender")
            floats.add(Double(FX + knots[k].x * 2), Double(FY + knots[k].y * 2 + 4), "UNTANGLED!", "lavender")
        }
        if nose.st == "warn" || nose.st == "up" {
            let c = cellAt(nose.x, nose.y)
            if c >= 0 && mark[c] {
                nose.st = "wait"; nose.t = st.nose
                scoreAt(1500, Double(FX) + nose.x, Double(FY) + nose.y - 8, "pink")
                floats.add(Double(FX) + nose.x, Double(FY) + nose.y + 4, "BOOP!", "pink")
                app.audio.play("pop")
            }
        }
        if caught.isEmpty { return 0 }
        var bossHit = 0
        for (k, q) in caught.enumerated() {
            wraps.append((x: q.x, y: q.y, age: 0, c: q.c))
            wrappedN += 1
            var pts = 500
            if q.kind == "pom" {
                pomsWrapped += 1
                pts = 600 * pomsWrapped
            } else {
                pts = ["fluff": 1500, "mini": 800, "zip": 700, "moth": 700][q.kind] ?? 500
            }
            scoreAt(pts * (k + 1), Double(FX) + q.x, Double(FY) + q.y - 6, "lime")
            hype.hit(1, fever: feverGain(0.06))
            parts.burst(Double(FX) + q.x, Double(FY) + q.y, 12, [theme.yarnA, theme.yarnB, "white", q.c], 60, 0.6)
            if st.kind == "normal" {
                if q.kind == "fluff" { respawn("fluff", 6) } else if q.kind == "zip" { respawn("zip", 4) } else if q.kind == "moth" { respawn("moth", 6) }
            } else if st.kind == "boss" {
                if q.kind == "zip" { respawn("zip", 5) }
                if q.kind == "mini" || q.kind == "moth" { bossHit += 1 }
            }
        }
        app.audio.play("bubble")
        if bossHit > 0, let b = boss, b.state == "fight" {
            b.hp = max(0, b.hp - bossHit * b.maxhp * 4 / 100)
            b.flash = 0.25
        }
        return caught.count
    }

    /// After a claim KUMO might stand inside the claimed area: hop to the nearest yarn edge.
    func relocateKumo() {
        let start = ky * GW + kx
        var seen = [Bool](repeating: false, count: GW * GH)
        seen[start] = true
        var q = [start]
        var k = 0
        while k < q.count {
            let c = q[k]
            k += 1
            if isEdge(c) { kx = c % GW; ky = c / GW; kprev = nil; return }
            let x = c % GW
            for nb in [x > 0 ? c - 1 : -1, x < GW - 1 ? c + 1 : -1, c - GW, c + GW] where nb >= 0 && nb < GW * GH && !seen[nb] {
                seen[nb] = true
                q.append(nb)
            }
        }
    }

    // ---------------------------------------------------------------- getting hurt
    /// Something touched the loose yarn (or KUMO while weaving / a zip touched KUMO).
    func hazardHit(_ kind: String, _ x: Double, _ y: Double) {
        if state != "play" || inv > 0 { return }
        if kind != "zip" && kind != "fray" && !weaving { return }
        if kind != "zip" && kind != "fray" && kind != "knot" && hype.feverOn { return }   // RAINBOW YARN
        if kind != "zip" && kind != "fray" && kind != "knot" && kind != "pom" && guardN > 0 {
            guardN -= 1
            trailSafe = 1.0
            hype.banner("STURDY YARN!", guardN > 0 ? "\(guardN) LEFT" : nil, color: "sky", dur: 1.0, scale: 1, sound: "tin")
            parts.burst(Double(FX) + x, Double(FY) + y, 10, ["sky", "white"], 50, 0.4)
            return
        }
        loseLife(kind)
    }

    func zipTouch(_ z: YWZip) {
        if inv > 0 || z.born > 0 || state != "play" { return }
        if claws > 0 {
            claws -= 1
            z.alive = false
            let x = Double((z.c % GW) * 2) + 1, y = Double((z.c / GW) * 2) + 1
            wraps.append((x: x, y: y, age: 0, c: "yellow"))
            scoreAt(800, Double(FX) + x, Double(FY) + y - 8, "yellow")
            hype.banner("POUNCE!", color: "yellow", dur: 0.9, scale: 1, sound: "pop")
            respawn("zip", 4)
            return
        }
        hazardHit("zip", 0, 0)
    }

    func loseLife(_ kind: String) {
        let au = app.audio
        hype.breakCombo()
        au.play("hurt")
        app.shake(3, 0.3)
        let (px, py) = kumoPx()
        parts.burst(Double(FX) + px, Double(FY) + py, 14, ["white", "gray", "pink"], 60, 0.6)
        if weaving {
            recoil = trail.map { (c: $0, life: 0.45) }
            for c in trail { grid[c] = OPEN }
            trail = []; trailSlow = []
            weaving = false
            (kx, ky) = anchor
            kprev = nil
        }
        fray = -1
        idle = 0
        hurtT = 0.9
        stun = 0.5
        if st.kind == "bonus" {          // no lives lost in a bonus stage
            inv = 1.0
            floats.add(Double(FX) + px, Double(FY) + py - 12, "BOING!", "pink")
            return
        }
        missed = true
        lives -= 1
        inv = 2.2
        if lives <= 0 {
            state = "over"
            hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
            au.play("gameover")
            endGame(false, "STAGE \(n)", delay: 2.5)
            return
        }
        hype.banner(SNAP_TEXT[kind] ?? "OUCH!", "\(lives) LEFT", color: "pink", dur: 1.1, scale: 1)
    }

    // ---------------------------------------------------------------- hazards
    /// Bounce a round thing around the open rug (claimed rug and loose yarn are walls).
    func moveBall(_ o: YWBouncer, _ dt: Double) {
        let sp = (o.vx * o.vx + o.vy * o.vy).squareRoot()
        let steps = max(1, Int(sp * dt / 1.5) + 1)
        let h = dt / Double(steps)
        let r = Double(o.r)
        var jam = 0
        for _ in 0 ..< steps {
            let nx = o.x + o.vx * h
            let ex = nx + (o.vx > 0 ? r : -r)
            if blocked(ex, o.y) || blocked(ex, o.y - r * 0.7) || blocked(ex, o.y + r * 0.7) {
                o.vx = -o.vx
                jam += 1
            } else {
                o.x = nx
            }
            let ny = o.y + o.vy * h
            let ey = ny + (o.vy > 0 ? r : -r)
            if blocked(o.x, ey) || blocked(o.x - r * 0.7, ey) || blocked(o.x + r * 0.7, ey) {
                o.vy = -o.vy
                jam += 1
            } else {
                o.y = ny
            }
        }
        o.stuck = jam >= 2 * steps ? o.stuck + 1 : 0
        if o.stuck > 20 {                 // wedged in a tight spot: pop out somewhere roomier
            o.stuck = 0
            (o.x, o.y) = findSpot(r + 1, 0, (o.x, o.y))
        }
    }

    func updateBalls(_ dt: Double) {
        let frozen = freeze > 0
        for b in balls {
            b.born = max(0, b.born - dt)
            if frozen && b.kind != "pom" { continue }
            b.turn -= dt
            if b.turn <= 0 {               // crackly static: erratic little swerves
                b.turn = Double.random(in: 0.6 ... 2.2)
                let a = atan2(b.vy, b.vx) + Double.random(in: -0.7 ... 0.7)
                b.vx = cos(a); b.vy = sin(a)
            }
            let sp = max(1e-9, (b.vx * b.vx + b.vy * b.vy).squareRoot())
            let want = b.speed * (b.zap > 0 ? 0.3 : 1.0)
            b.vx = b.vx / sp * want; b.vy = b.vy / sp * want
            moveBall(b, dt)
            if b.zap > 0 {
                b.zap -= dt
                if b.zap <= 0 {
                    storms.append((x: b.x, y: b.y, r: Double(b.r)))
                    app.audio.play("explode")
                }
            }
            if b.born <= 0 {
                touchCheck(b.x, b.y, b.r, b.kind == "pom" ? "pom" : "fluff")
                if state != "play" { return }
            }
        }
    }

    func updateStorms(_ dt: Double) {
        if st.storm > 0 && freeze <= 0 {
            stormT -= dt
            if stormT <= 0 {
                stormT = st.storm * Double.random(in: 0.8 ... 1.2)
                let fl = balls.filter { $0.kind == "fluff" && $0.born <= 0 }
                if let f = fl.randomElement() {
                    f.zap = 0.9
                    app.audio.play("trap")
                }
            }
        }
        for i in storms.indices {
            storms[i].r += 120 * dt
            ringCheck(storms[i].x, storms[i].y, storms[i].r)
        }
        storms.removeAll { $0.r >= 36 }
    }

    func updateZips(_ dt: Double) {
        if freeze > 0 { return }
        let (px, py) = kumoPx()
        let sp = st.zspeed * hzSpeed
        for z in zips {
            z.born = max(0, z.born - dt)
            if !isEdge(z.c) {              // the edge vanished under it
                guard let c = zipHome() else { continue }
                z.c = c
            }
            z.acc += sp * dt
            while z.acc >= 1 {
                z.acc -= 1
                zipStep(z)
            }
            if abs(Double((z.c % GW) * 2 + 1) - px) < 5 && abs(Double((z.c / GW) * 2 + 1) - py) < 5 {
                zipTouch(z)
                if state != "play" { return }
            }
        }
        zips.removeAll { !$0.alive }
    }

    func zipStep(_ z: YWZip) {
        let x = z.c % GW, y = z.c / GW
        var opts: [(Int, Int)] = []
        for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
            if dx == -z.dx && dy == -z.dy { continue }
            let nx = x + dx, ny = y + dy
            if nx >= 0 && nx < GW && ny >= 0 && ny < GH && isEdge(ny * GW + nx) { opts.append((dx, dy)) }
        }
        if opts.isEmpty {
            z.dx = -z.dx; z.dy = -z.dy
            let nx = x + z.dx, ny = y + z.dy
            if nx >= 0 && nx < GW && ny >= 0 && ny < GH && isEdge(ny * GW + nx) { z.c = ny * GW + nx }
            return
        }
        var d: (Int, Int)
        if opts.count == 1 {
            d = opts[0]
        } else if z.hunter && Double.random(in: 0 ..< 1) < 0.75 {
            d = opts.min { abs(x + $0.0 - kx) + abs(y + $0.1 - ky) < abs(x + $1.0 - kx) + abs(y + $1.1 - ky) }!
        } else if opts.contains(where: { $0.0 == z.dx && $0.1 == z.dy }) && Double.random(in: 0 ..< 1) < 0.6 {
            d = (z.dx, z.dy)
        } else {
            d = opts.randomElement()!
        }
        z.dx = d.0; z.dy = d.1
        z.c = (y + d.1) * GW + x + d.0
    }

    func updateMoths(_ dt: Double) {
        let frozen = freeze > 0
        let msp = (18 + 0.8 * Double(tier)) * hzSpeed
        for m in moths {
            m.t += dt
            if frozen { continue }
            var tx: Double, ty: Double, sp: Double
            if weaving && trail.count > 4 {
                let c = trail[trail.count / 2]
                tx = Double((c % GW) * 2) + 1; ty = Double((c / GW) * 2) + 1; sp = msp * 1.25
            } else {
                tx = m.hx + sin(m.t * 0.7) * 60; ty = m.hy + sin(m.t * 1.1) * 30; sp = msp * 0.7
            }
            let a = atan2(ty - m.y, tx - m.x)
            let k = min(1, dt * 2)
            m.vx += (cos(a) * sp - m.vx) * k
            m.vy += (sin(a) * sp - m.vy) * k
            m.x = max(-8, min(Double(PW) + 8, m.x + m.vx * dt))
            m.y = max(-8, min(Double(PH) + 8, m.y + m.vy * dt + sin(m.t * 9) * 0.3))
            if weaving && trailHit(m.x, m.y, 3) {
                hazardHit("moth", m.x, m.y)
                if state != "play" { return }
            }
        }
    }

    func updateNose(_ dt: Double) {
        let every = st.nose
        if every <= 0 || freeze > 0 { return }
        nose.t -= dt
        if nose.st == "wait" && nose.t <= 0 {
            var near: (Double, Double)?
            if weaving, let c = trail.last {
                near = (Double((c % GW) * 2) + 1 + Double.random(in: -20 ... 20), Double((c / GW) * 2) + 1 + Double.random(in: -20 ... 20))
            }
            var (x, y) = findSpot(10, near != nil ? 0 : 30)
            if let nr = near, clearAt(nr.0, nr.1, 10) { (x, y) = nr }
            nose = (st: "warn", t: 1.1, x: x, y: y)
            floats.add(Double(FX) + x, Double(FY) + y - 16, "SNIFF SNIFF", "peach")
        } else if nose.st == "warn" && nose.t <= 0 {
            nose.st = "up"; nose.t = 1.3
            app.audio.play("pop")
            app.shake(2, 0.15)
        } else if nose.st == "up" {
            touchCheck(nose.x, nose.y, 11, "nose")
            if nose.t <= 0 { nose.st = "down"; nose.t = 0.35 }
        } else if nose.st == "down" && nose.t <= 0 {
            nose.st = "wait"; nose.t = every * Double.random(in: 0.8 ... 1.2)
        }
    }

    func updateItems(_ dt: Double) {
        if st.kind != "bonus" {
            itemT -= dt
            if itemT <= 0 {
                itemT = st.items * (1 - 0.12 * Double(lv("luck"))) * Double.random(in: 0.8 ... 1.2)
                if items.count < 3 {
                    var pool = Array(repeating: "fish", count: 10) + Array(repeating: "nip", count: 3) +
                        Array(repeating: "bell", count: 3) + ["rainbow"]
                    if lives < 5 { pool.append("heart") }
                    if Double.random(in: 0 ..< 1) < 0.02 + 0.01 * Double(lv("luck")) { pool = ["gold"] }
                    let (x, y) = findSpot(7, 30)
                    items.append(YWItem(x, y, pool.randomElement()!))
                }
            }
        }
        for it in items { it.life -= dt }
        items.removeAll { $0.life <= 0 }
    }

    func collect(_ it: YWItem) {
        if it.life <= 0 { return }
        it.life = 0
        let au = app.audio
        let x = Double(FX) + it.x, y = Double(FY) + it.y
        let k = it.kind
        parts.burst(x, y, 10, ["yellow", "white", "pink"], 50, 0.5)
        if k == "fish" {
            fishGot += 1
            hype.hit(1, fever: feverGain(0.04))
            scoreAt(300 + hype.comboBonus(10), x, y - 6)
            au.play("eat")
            if st.kind == "bonus" && fishGot >= fishTotal && state == "play" {
                hype.banner("ALL TREATS!", dur: 1.4, rainbow: true, sound: "bonus")
                stageClear()
            }
            return
        }
        floats.add(x, y - 12, ITEM_TEXT[k] ?? "", "mint")
        au.play("powerup")
        switch k {
        case "nip": nip = 8
        case "bell":
            freeze = 4.0 + Double(lv("luck"))
            hype.flash("sky", 0.2)
        case "heart":
            lives += 1
            au.play("extra")
        case "gold": hype.jackpot(factorPts(5000), sub: "GOLDEN YARN!")
        case "rainbow": hype.startFever()
        default: break
        }
    }

    // ---------------------------------------------------------------- clear / reveal / tally
    func stageClear() {
        if state != "play" { return }
        state = "clear"
        stateT = 0
        if weaving {
            for c in trail { grid[c] = OPEN }
            trail = []; trailSlow = []
            weaving = false
            (kx, ky) = anchor
        }
        var left: [(Double, Double, String)] = balls.map { ($0.x, $0.y, $0.color) } + moths.map { ($0.x, $0.y, "cream") }
        left += zips.map { (Double(($0.c % GW) * 2) + 1, Double(($0.c / GW) * 2) + 1, "yellow") }
        for (x, y, c) in left {           // everything left gets wrapped up for a few points
            wraps.append((x: x, y: y, age: -Double.random(in: 0 ... 0.5), c: c))
            scoreAt(300, Double(FX) + x, Double(FY) + y - 6, "lime")
        }
        balls = []; moths = []; zips = []; storms = []; items = []
        if hype.feverOn { hype.feverT = 0 }
        hype.slowmo(0.3, 0.8)
        hype.flash("white", 0.2)
        app.audio.play("win")
        if st.kind == "normal" {
            hype.banner("RUG CLAIMED!", "\(percent())%", color: "mint", dur: 1.4)
            hype.shower(30, "confetti")
        }
        app.audio.music(nil)
        wasFever = false
        happyT = 3.0
        hype.comboY = -20                 // keep the picture caption clear
    }

    func bossDefeated() {
        guard let b = boss else { return }
        b.state = "dead"
        b.hp = 0
        app.audio.play("bossdown")
        hype.banner("WRAPPED UP!", b.name, dur: 2.2, rainbow: true)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        app.shake(6, 0.6)
        scoreAt(20000, Double(FX) + b.x, Double(FY) + b.y - 10)
        wraps.append((x: b.x, y: b.y, age: -0.3, c: "white"))
        stageClear()
        hype.slowmo(0.3, 1.2)
    }

    func beginReveal() {
        state = "reveal"
        stateT = 0
        let x0 = kx, y0 = ky
        revealList = (0 ..< GW * GH).filter { grid[$0] != CLAIMED }.sorted { a, b in
            let da = (a % GW - x0) * (a % GW - x0) + (a / GW - y0) * (a / GW - y0)
            let db = (b % GW - x0) * (b % GW - x0) + (b / GW - y0) * (b / GW - y0)
            return da < db
        }
        revealI = 0
        friends += 1
        app.audio.play("bonus")
    }

    func updateReveal(_ dt: Double) {
        let total = revealList.count
        if revealI < total {
            let k = max(1, Int(Double(total) * dt / 0.9) + 1)
            for i in revealList[revealI ..< min(total, revealI + k)] {
                let x = i % GW, y = i / GW
                copyCell(pic, x, y)
                if Double.random(in: 0 ..< 1) < 0.02 {
                    parts.sparkle(Double(FX + x * 2), Double(FY + y * 2), ["yellow", "white", "pink"].randomElement()!)
                }
            }
            revealI += k
            if revealI >= total {
                field = pic.copy()           // the whole picture, yarn and furniture gone
                hype.shower(30, "hearts")
                if golden { hype.jackpot(factorPts(20000), sub: "A GOLDEN CAT!") }
                app.audio.play("levelup")
            }
        } else if stateT > 2.8 || (stateT > 1.2 && app.input.hit(.a)) {
            beginTally()
        }
    }

    func beginTally() {
        let pct = percent()
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("CLAIMED \(pct)%", factorPts(pct * 100)))
            let extra = max(0, pct - st.target)
            rows.append(("OVER TARGET +\(extra)%", factorPts(extra * 400)))
            let par = 75 + 3 * tier
            rows.append(("TIME BONUS", factorPts(max(0, Int(Double(par) - stime)) * 25)))
            rows.append(("WRAPPED X\(wrappedN)", factorPts(wrappedN * 500)))
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", factorPts(15000 + 2500 * tier)))
            rows.append(("WRAPPED X\(wrappedN)", factorPts(wrappedN * 500)))
        } else if st.bonus == "poms" {
            rows.append(("POM-POMS X\(pomsWrapped)", factorPts(pomsWrapped * 800)))
            rows.append(("ALL ROUNDED UP", pomsWrapped >= pomsTotal ? factorPts(10000) : 0))
            rows.append(("CLAIMED \(pct)%", factorPts(pct * 50)))
        } else {
            rows.append(("TREATS X\(fishGot)", factorPts(fishGot * 300)))
            rows.append(("ALL TREATS", fishGot >= fishTotal ? factorPts(8000) : 0))
            rows.append(("CLAIMED \(pct)%", factorPts(pct * 50)))
        }
        rows.append(("BEST COMBO \(stageCombo)", factorPts(stageCombo * 150)))
        if st.kind != "bonus" { rows.append(("NO MISS", missed ? 0 : factorPts(5000))) }
        tally = rows.map { (label: $0.0, v: $0.1, shown: 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        if st.kind != "bonus" && !missed {
            hype.banner("PURRFECT!", "NO YARN SNAPPED", dur: 1.8, rainbow: true, sound: "fever")
            hype.shower(40, "stars")
        }
    }

    func updateTally(_ dt: Double) {
        let skip = stateT > 0.3 && app.input.hit(.a)
        if tallyI < tally.count {
            if skip {
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
        checkLife()
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "EVERY RUG IN THE HOUSE!", dur: 5.0, rainbow: true, sound: "jackpot")
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
    override func render(_ s: Surface) {
        let th = theme
        s.fill(col("night"))
        for y in stride(from: FY, to: FY + PH, by: 4) {      // rug fringe
            s.fillRect(col("cream"), 2, y + 1, 5, 1)
            s.fillRect(col("cream"), W - 7, y + 1, 5, 1)
        }
        s.rect(col("black"), IRect(FX - 1, FY - 1, PW + 2, PH + 2), width: 1)
        s.blit(field, FX, FY)
        // loose yarn
        let fever = hype.feverOn
        for (k, c) in trail.enumerated() {
            let x = FX + (c % GW) * 2, y = FY + (c / GW) * 2
            let cc: String
            if fever {
                cc = rainbow(k / 3, t)
            } else if trailSlow[k] {
                cc = k % 2 == 1 ? "white" : th.yarnA
            } else {
                cc = (k / 3) % 2 == 1 ? th.yarnA : "white"
            }
            s.fillRect(col(cc), x, y, 2, 2)
        }
        for r in recoil where Int(r.life * 20) % 2 == 1 { s.fillRect(col("red"), FX + (r.c % GW) * 2, FY + (r.c / GW) * 2, 2, 2) }
        if weaving && fray >= 0 && idle > 0.3 && !trail.isEmpty {
            let c = trail[min(trail.count - 1, Int(fray))]
            let x = FX + (c % GW) * 2 + 1, y = FY + (c / GW) * 2 + 1
            s.circle(col("black"), x, y, 3)
            s.circle(col(Int(t * 16) % 2 == 1 ? "orange" : "red"), x, y, 2)
        }
        for k in knots where k.alive { YWArt.drawKnot(s, FX + k.x * 2 + 1, FY + k.y * 2 + 1, t) }
        for it in items { YWArt.drawItem(s, it.kind, Double(FX) + it.x, Double(FY) + it.y, t, it.life) }
        if nose.st == "warn" {
            let r = 6 + Int(nose.t * 12)
            if Int(t * 10) % 2 == 1 { s.circle(col("peach"), FX + Int(nose.x), FY + Int(nose.y), r, width: 1) }
            YWArt.drawNose(s, Double(FX) + nose.x, Double(FY) + nose.y, t, 0.25)
        } else if nose.st == "up" || nose.st == "down" {
            let up = nose.st == "up" ? 1.0 : max(0, nose.t / 0.35)
            YWArt.drawNose(s, Double(FX) + nose.x, Double(FY) + nose.y, t, up)
        }
        for b in balls {
            if b.born > 0 && Int(t * 20) % 2 == 1 { continue }
            if b.kind == "pom" {
                YWArt.drawPom(s, Double(FX) + b.x, Double(FY) + b.y, b.r, t, b.color)
            } else {
                YWArt.drawFluff(s, Double(FX) + b.x, Double(FY) + b.y, b.r, t * (freeze > 0 ? 0.2 : 1.0), angry: true, zap: b.zap,
                                color: b.kind == "fluff" ? "gray" : b.color)
            }
        }
        for sw in storms {
            s.circle(col(Int(t * 20) % 2 == 1 ? "yellow" : "white"), FX + Int(sw.x), FY + Int(sw.y), Int(sw.r), width: 1)
        }
        for z in zips {
            if z.born > 0 && Int(t * 20) % 2 == 1 { continue }
            YWArt.drawZip(s, Double(FX + (z.c % GW) * 2 + 1), Double(FY + (z.c / GW) * 2 + 1), t, hunter: z.hunter)
        }
        for m in moths { YWArt.drawMoth(s, Double(FX) + m.x, Double(FY) + m.y, freeze <= 0 ? t : 0) }
        boss?.draw(s, FX, FY, t)
        for w in wraps where w.age >= 0 { drawWrap(s, Double(FX) + w.x, Double(FY) + w.y, w.age, w.c) }
        drawKumo(s)
        parts.draw(s)
        floats.draw(s)
        drawHud(s)
        if state == "intro" {
            drawIntro(s)
        } else if state == "reveal" && revealI >= revealList.count {
            drawCaption(s)
        } else if state == "tally" {
            drawCaption(s)
            drawTally(s)
        }
    }

    /// A hazard being wrapped up: yarn spirals round it into a little ball, then pops.
    func drawWrap(_ s: Surface, _ fx: Double, _ fy: Double, _ age: Double, _ c: String) {
        let x = Int(fx), y = Int(fy)
        if age < 0.6 {
            let r = 9 - Int(age * 6)
            s.circle(col("black"), x, y, r + 1)
            s.circle(col(theme.yarnA), x, y, r)
            for k in 0 ..< 3 {
                let a = age * 14 + Double(k) * 2.1
                s.line(col("white"), x + Int(cos(a) * Double(r)), y + Int(sin(a) * Double(r)),
                       x - Int(cos(a) * Double(r)), y - Int(sin(a) * Double(r) * 0.5))
            }
        } else {
            let k = (age - 0.6) / 0.4
            for i in 0 ..< 6 {
                let a = Double(i) * 2 * .pi / 6 + age
                let d = Double(Int(4 + k * 14))
                s.fillRect(col(rainbow(i, t)), x + Int(cos(a) * d), y + Int(sin(a) * d), 2, 2)
            }
        }
    }

    func drawKumo(_ s: Surface) {
        if state == "over" { return }
        if inv > 0 && hurtT <= 0 && Int(t * 16) % 2 == 1 { return }
        let x = FX + kx * 2 + 1
        var y = FY + ky * 2 + 1
        let fr: Int
        if hurtT > 0 {
            fr = YW_K_HURT
        } else if happyT > 0 {
            fr = YW_K_HAPPY
            y -= Int(abs(sin(t * 10)) * 3)
        } else if kmoveT > 0 {
            fr = Int(t * 10) % 2 == 1 ? YW_K_WALK1 : YW_K_WALK2
        } else if weaving {
            fr = YW_K_WEAVE
        } else {
            fr = Int(t * 1.3) % 6 == 0 ? YW_K_BLINK : YW_K_IDLE
        }
        s.blit(sprite("yw_kumo", fr, flip: kface < 0), x - 7, y - 10)
        if careful && weaving {
            for k in 0 ..< 2 {
                let a = t * 6 + Double(k) * .pi
                s.fillRect(col("mint"), x + Int(cos(a) * 9), y - 12 + Int(sin(a) * 2), 2, 2)
            }
        }
        if nip > 0 && Int(t * 8) % 2 == 1 {
            s.fillRect(col("lime"), x - 8, y - 2, 1, 1)
            s.fillRect(col("lime"), x + 8, y - 4, 1, 1)
        }
    }

    func drawHud(_ s: Surface) {
        drawText(s, String(format: "%07d", score), 4, 3, "white", shadow: nil)
        if let b = boss, b.state != "dead", state != "intro" {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: 0)
        } else {
            drawText(s, String(format: "HI %07d", max(best, score)), 4, 11, "gray", shadow: nil)
            if st.kind == "bonus" && (state == "play" || state == "intro") {
                let secs = Int(bonusLeft.rounded(.up))
                drawText(s, String(format: "TIME %02d", secs), W / 2, 3, secs > 5 || Int(t * 6) % 2 == 1 ? "yellow" : "red",
                         align: .center, shadow: nil)
            } else {
                drawText(s, "STAGE \(n)", W / 2, 3, "yellow", align: .center, shadow: nil)
            }
            // claim meter with the target tick
            let x0 = 116, w = 88
            let pct = percent()
            let tgt = st.kind == "normal" ? st.target : 95
            s.fillRect(col("darkgray"), x0, 12, w, 4)
            s.fillRect(col(pct < tgt ? theme.yarnA : "lime"), x0, 12, w * min(100, pct) / 100, 4)
            s.fillRect(col("white"), x0 + w * tgt / 100, 10, 1, 8)
            drawText(s, "\(pct)%", x0 + w + 4, 11, pct >= tgt ? "lime" : "white", shadow: nil)
        }
        hearts(s, W - 54, 3, lives)
        let x0 = W - 54, y0 = 13
        s.fillRect(col("darkgray"), x0, y0, 48, 3)
        if hype.feverOn {
            for i in 0 ..< 48 { s.fillRect(col(rainbow(i / 6, t)), x0 + i, y0, 1, 3) }
        } else {
            s.fillRect(col("orange"), x0, y0, Int(48 * hype.fever), 3)
        }
        // charges and timed effects along the bottom of the rug
        var x = FX + 3
        for (label, cnt, c) in [("Y", guardN, "sky"), ("C", claws, "yellow")] {
            for _ in 0 ..< max(0, cnt) {
                s.rect(col(c), IRect(x, FY + PH - 9, 9, 7), radius: 2)
                drawText(s, label, x + 2, FY + PH - 9, "black", shadow: nil)
                x += 11
            }
        }
        for (label, v, c) in [("NIP", nip, "lime"), ("FREEZE", freeze, "sky")] where v > 0 && (v > 2 || Int(t * 8) % 2 == 1) {
            drawText(s, label, x, FY + PH - 9, c)
            x += textWidth(label) + 6
        }
    }

    func drawIntro(_ s: Surface) {
        if st.kind == "boss" {
            if Int(t * 4) % 2 == 1 {
                var x = -20
                while x < W + 20 {
                    let fx = Double(x)
                    s.polygon(col("red"), [(fx, 108), (fx + 10, 108), (fx + 20, 116), (fx + 10, 116)])
                    s.polygon(col("red"), [(fx, 158), (fx + 10, 158), (fx + 20, 166), (fx + 10, 166)])
                    x += 20
                }
            }
            panel(s, IRect(40, 120, 240, 34), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 124, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.boss?.name ?? "") WANTS THE RUG!", W / 2, 142, "white", align: .center, shadow: nil)
            return
        }
        if st.kind == "bonus" {
            panel(s, IRect(40, 78, 240, 62), fill: "ink", border: "yellow")
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, 84 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            let poms = st.bonus == "poms"
            drawText(s, poms ? "POM-POM ROUND-UP!" : "FISH FEAST!", W / 2, 104, "yellow", align: .center)
            drawText(s, poms ? "WRAP UP THE POM-POMS!" : "SCOOP UP ALL THE TREATS!", W / 2, 115, "white", align: .center, shadow: nil)
            drawText(s, "NOTHING CAN HURT YOU HERE", W / 2, 126, "mint", align: .center, shadow: nil)
            return
        }
        let h = st.newLine.isEmpty ? 60 : 70
        panel(s, IRect(34, 74, 252, h), fill: "ink", border: theme.yarnA)
        drawText(s, "STAGE \(n)", W / 2, 80, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, theme.name, W / 2, 98, "lavender", align: .center, shadow: nil)
        drawText(s, "CLAIM \(st.target)% OF THE RUG", W / 2, 109, "white", align: .center, shadow: nil)
        s.blit(sprite("yw_kumo", Int(t * 2) % 5 == 0 ? YW_K_BLINK : YW_K_IDLE), 44, 112)
        drawText(s, "\"\(st.quip)\"", W / 2 + 8, 121, "mint", align: .center, shadow: nil)
        if !st.newLine.isEmpty {
            drawText(s, st.newLine, W / 2, 132, Int(t * 4) % 2 == 1 ? "lime" : "yellow", align: .center, shadow: nil)
        }
    }

    func drawCaption(_ s: Surface) {
        let name = st.pic.name
        var txt = st.kind != "boss" ? "IT'S \(name)!" : "\(name) IS SAFE!"
        if golden { txt = "GOLDEN \(name)!" }
        let w = textWidth(txt) + 16
        panel(s, IRect(W / 2 - w / 2, FY + 4, w, 14), fill: "cream", border: "choco", radius: 3)
        drawText(s, txt, W / 2, FY + 8, "choco", align: .center, shadow: nil)
        drawText(s, "KUMO'S FRIEND #\(friends)", W / 2, FY + 21, "white", align: .center)
    }

    func drawTally(_ s: Surface) {
        let h = 22 + tally.count * 9
        let y0 = H - 4 - h
        panel(s, IRect(60, y0, 200, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, W / 2, y0 + 4, "mint", align: .center, shadow: nil)
        for (i, row) in tally.enumerated() where i <= tallyI {
            let y = y0 + 15 + i * 9
            drawText(s, row.label, 68, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 252, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 { s.blit(sprite("yw_kumo", YW_K_HAPPY), W / 2 - 7, y0 - 14) }
    }

    // ---------------------------------------------------------------- carousel preview
    private static var previewPic: Surface?
    private static var previewRug: Surface?
    private static let previewSpec = YWPic(name: "KUMO", bg: "sky", bg2: "white", pat: 1, pose: 0, fur: "orange", fur2: "peach",
                                           mark: 1, eye: "lime", mood: 0, acc: 1, accc: "hotpink", prop: 0, propc: "red",
                                           cush: "purple", x: 0)

    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        if previewPic == nil {
            let big = Surface(YW_PW, YW_PH)
            YWArt.drawPicture(big, previewSpec)
            let crop = Surface(112, 74)
            for y in 0 ..< 74 { for x in 0 ..< 112 { crop.px[y * 112 + x] = big.px[(22 + y) * YW_PW + YW_PW / 2 - 56 + x] } }
            previewPic = crop
            let r = Surface(112, 74)
            YWArt.bgPattern(r, "brown", "choco", 2, 0, 0, 112, 74)
            previewRug = r
        }
        guard let pic = previewPic, let rugS = previewRug else { return }
        s.blit(rugS, 0, 0)
        let cyc = t.truncatingRemainder(dividingBy: 6.0)
        let rx = 14 + Int(cyc / 1.2) * 18                    // claimed so far: columns left of rx
        for y in 0 ..< min(h, pic.h) { for x in 0 ..< min(rx, w, pic.w) { s.px[y * s.w + x] = pic.px[y * pic.w + x] } }
        for y in stride(from: 0, to: h, by: 2) { s.fillRect(col((y / 2) % 2 == 1 ? "hotpink" : "pink"), rx, y, 2, 2) }
        let ph = cyc.truncatingRemainder(dividingBy: 1.2) / 1.2
        let ky = Int(ph * Double(h - 4)) + 2
        let lx = rx + 16
        for y in stride(from: 0, to: ky, by: 2) { s.fillRect(col((y / 4) % 2 == 1 ? "white" : "hotpink"), lx, y, 2, 2) }
        s.fillRect(col("hotpink"), rx, 0, 18, 2)
        s.blit(sprite("yw_kumo", Int(t * 10) % 2 == 1 ? YW_K_WALK1 : YW_K_WALK2), lx - 7, ky - 10)
        let fx = Double(w) - 18 + sin(t * 2.3) * 10
        let fy = Double(h) / 2 + sin(t * 3.1) * 22
        YWArt.drawFluff(s, fx, fy, 6, t)
    }
}
