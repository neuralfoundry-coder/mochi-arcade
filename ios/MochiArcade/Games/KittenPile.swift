// KITTEN PILE - tuck sleepy kitten pairs into the cat bed; 4 of a colour curl up and fall asleep
// (port of mochi_arcade/games/kitten_pile.py - keep the two in step).
// Rules: KittenPileCore.swift. Art: KittenPileArt.swift. Stage tables come from Python (GameData.json("kitten_pile")).
import Foundation

private let CELL = KPArt.CELL
private let COLS = KP.COLS, ROWS = KP.ROWS
private let BX = 124, BY = 44
private let BW = COLS * CELL, BH = ROWS * CELL
private let FALL = 520.0                 // px/s for tumbling kittens
private let POP_TIME = 0.5
private let LOCK_DELAY = 0.4
private let LIFE_STEP = 30000            // extra lives at 30k, 90k, 180k, 300k ...
private let GOLD_CHANCE = 0.012
private let FOE_X = 261, FOE_Y = 146
private let CHAIN_WORDS = ["", "", "CATNAP!", "SNOOZE!", "SLUMBER!", "DREAMLAND!", "MOONBEAM!", "STARDUST!", "PURRFECT!"]

struct KPPiece { var x: Int; var y: Int; var rot: Int; let a: Int; let b: Int }

final class KPFoe {
    let boss: Bool, id: Int, max: Int, every: Double, pow: Int, atk: [String]
    var hp: Int, t: Double
    var tele: (String, Double)?
    var hit = 0.0, phase: Int, sleep = false
    init(boss: Bool, def d: KPFoeDef, hp: Int) {
        self.boss = boss; id = d.id; max = d.hp; every = d.every; pow = d.pow; atk = d.atk
        self.hp = hp; t = d.every * 0.9
        phase = hp > d.hp / 2 ? 1 : 2
    }
    var def: KPCatDef { boss ? KPData.bosses[id] : KPData.rivals[id] }
}

final class KittenPile: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["{ }  MOVE              `  FASTER", "ROT R / ROT L  TURN THE PAIR", "DROP (OR PAD |)  DROP IT"]
    static let helpSkip = 3

    override var music: String? { song }
    // Turning is the most frequent action: ROT R sits under the resting thumb, ROT L next to it (a stray turn is undone
    // by the other), DROP is one deliberate reach away (a stray drop is the costliest mistake). Soft drop stays on the pad.
    override var buttons: [Action: String] { [.a: "ROT R", .b: "ROT L", .y: "DROP"] }
    override var buttonOrder: [Action] { [.a, .b, .y] }
    override var fourWay: Bool { true }

    static let pool: [Upgrade] = KPData.upgrades.map { u in
        Upgrade(id: u.id, name: u.name, desc: u.desc, color: u.color, icon: nil, draw: { s, cx, cy, t in
            KittenPile.upgradeIcon(s, u.id, cx, cy, t)
        }, max: u.max)
    }

    static func upgradeIcon(_ s: Surface, _ uid: String, _ cx: Int, _ cy: Int, _ t: Double) {
        switch uid {
        case "peek": KPArt.kitten(s, cx - 6, cy - 6, 4, 4)
        case "cozy": s.blit(sprite("kp_pillow"), cx - 6, cy - 6)
        case "yarn": s.blit(sprite("kp_yarn"), cx - 6, cy - 6)
        case "mouse": s.blit(sprite("kp_mouse"), cx - 6, cy - 6)
        case "fort":
            s.blit(sprite("kp_pillow"), cx - 8, cy - 4)
            s.blit(sprite("kp_pillow"), cx - 4, cy - 8)
        case "purr": KPArt.kitten(s, cx - 6, cy - 6, 1, 3)
        case "catnip":
            s.polygon(col("lime"), [(Double(cx), Double(cy - 7)), (Double(cx + 5), Double(cy)), (Double(cx), Double(cy + 7)), (Double(cx - 5), Double(cy))])
            s.line(col("mint"), cx, cy - 6, cx, cy + 6)
        case "lullaby": drawText(s, "~", cx - 2, cy - 4, "mint", shadow: nil)
        case "guard": KPArt.lantern(s, cx - 2, cy + 1, t)
        case "bell": KPArt.kitten(s, cx - 6, cy - 6, 1 | KP.GOLD, 3, t)
        default: drawText(s, "@", cx - 2, cy - 4, "pink", shadow: nil)
        }
    }

    let speed: Double, foeMult: Double, guide: Bool
    var ups: [String: Int] = [:]
    var lives = 3, lifeK = 1
    var song = "kp_nap"
    var feverWas = false
    var attempt = 0
    var shots: [(x: Double, y: Double, p: Double, power: Int)] = []     // naps at the rival (power -1: a pillow back)
    var coinFx: [(x: Double, y: Double, vx: Double, vy: Double, life: Double)] = []
    var squish: [Int: Double] = [:]           // y * COLS + x -> landing squash timer
    var bedKick = 0.0
    var foeKeep = 0
    var talk: (String, Double)?
    var poppyMood = ("idle", 0.0)
    // stage
    var st: KPStage
    var stageN = 1, tierN = 0
    var theme: KPTheme
    var rng = KRand(1), frng = KRand(2)
    var suI = 0
    var grid = KP.emptyGrid()
    var off = [[Double]](repeating: [Double](repeating: 0, count: COLS), count: ROWS)
    var moodT = [[Double]](repeating: [Double](repeating: 0, count: COLS), count: ROWS)
    var stars0 = 0
    var piece: KPPiece?
    var pieceId = 0
    var queue: [(Int, Int)] = []
    var phase = "wait", phaseT = 0.0
    var chain = 0
    var popping: [(Int, Int, Int)] = []
    var popT = 0.0
    var landed: [(Int, Int, Int)] = []
    var pend = [0, 0, 0]                      // pillows, grandpas, grumpy kittens
    var pendRise = 0
    var fogT = 0.0, zoomT = 0.0, dizzyT = 0.0, rainT = 0.0, riseT = 0.0
    var stime = 0.0
    var kits = 0, coins = 0, bestChain = 0, allClears = 0, rescued = 0
    var missed = false
    var dropped = false                       // a pair was placed since the bed was (re)made (trigger stages)
    var nightLights = 0
    var fallT = 0.0, lockT = 0.0, lockResets = 0
    var dasDir = 0, dasT = 0.0
    var foe: KPFoe?
    var state = "intro", stateT = 0.0
    var quip = ""
    var tally: [(String, Int, Int)] = []
    var tallyI = 0, tallyT = 0.0

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let diff = opt["difficulty"] ?? "normal"
        speed = SPEEDS[diff] ?? 1
        foeMult = ["easy": 0.75, "normal": 1.0, "hard": 1.3][diff] ?? 1
        guide = (opt["guide"] ?? "true") == "true"
        st = KPData.stages[0]
        theme = KPData.themes[0]
        super.init(app, info, opt)
        hype.comboTime = 4.0
        hype.comboY = 14
        lives = LIVES[diff] ?? 3
        let s = optInt("stage", 0)
        beginStage(Swift.max(1, Swift.min(STAGES, s > 0 ? s : optInt("start", 1))))
    }

    // ================================================================ helpers
    func up(_ id: String) -> Int { ups[id] ?? 0 }
    var bonus: Bool { st.k == "snack" || st.k == "domino" }
    var lv: Int { tierN + 1 }
    func mood(_ m: String, _ dur: Double = 1.2) { poppyMood = (m, dur) }
    func say(_ text: String, _ dur: Double = 2.2) { talk = (text, dur) }

    func gravity() -> Double {
        var g = st.g / speed * (1 + 0.12 * Double(up("cozy")))
        if zoomT > 0 { g /= 3 }
        return Swift.max(0.03, g)
    }

    var pendingTotal: Int { pend[0] + pend[1] * 3 + pend[2] }
    var foeName: String { foe?.def.name ?? "" }
    var starsLeft: Int { KP.countCells(grid) { KP.isKitten($0) && $0 & KP.STAR != 0 } }

    // ================================================================ stage flow
    func beginStage(_ n: Int, retry: Bool = false) {
        st = KPData.stages[n - 1]
        stageN = n
        tierN = tier(n)
        theme = KPData.themes[tierN]
        attempt = retry ? attempt + 1 : 0
        rng = KRand(KP.stageSeed(n, attempt))
        frng = KRand(KP.stageSeed(n, attempt, 1))
        suI = 0
        loadRows(st.rows)
        piece = nil
        pieceId = 0
        queue = []
        phase = "wait"; phaseT = 0
        chain = 0
        popping = []; popT = 0
        landed = []
        pend = [0, 0, 0]; pendRise = 0
        fogT = 0; zoomT = 0; dizzyT = 0; rainT = 0; riseT = 0
        stime = 0
        kits = 0; coins = 0; bestChain = 0; allClears = 0; rescued = 0
        missed = retry
        nightLights = up("guard")
        fallT = 0; lockT = 0; lockResets = 0
        dasDir = 0; dasT = 0
        foe = nil
        if let d = st.boss ?? st.rival {
            var keep = d.hp
            if retry && foeKeep > 0 { keep = Swift.min(d.hp, foeKeep + d.hp * 15 / 100) }
            foe = KPFoe(boss: st.boss != nil, def: d, hp: keep)
        }
        foeKeep = 0
        dropped = false
        while queue.count < 4 { queue.append(genPiece()) }
        reached(n)
        let boss = st.k == "boss"
        state = boss && !retry ? "warning" : "intro"
        stateT = 0
        song = boss ? "boss" : bonus ? "bonus" : st.k == "duel" ? "kp_duel" : "kp_nap"
        app.audio.music(song)
        app.audio.play(state == "warning" ? "warning" : "stage")
        feverWas = false
        let lines = KPData.talk[st.k] ?? ["SHH..."]
        quip = lines[(n + attempt) % lines.count].replacingOccurrences(of: "@", with: foeName)
        talk = nil
    }

    func loadRows(_ rows: [String]) {
        grid = rows.isEmpty ? KP.emptyGrid() : KP.parseRows(rows)
        off = [[Double]](repeating: [Double](repeating: 0, count: COLS), count: ROWS)
        moodT = [[Double]](repeating: [Double](repeating: 0, count: COLS), count: ROWS)
        stars0 = starsLeft
    }

    func genPiece() -> (Int, Int) {
        if st.twins {
            let c = 1 + rng.below(st.ncol)
            return (c, c)
        }
        if st.k == "domino" || st.k == "trigger" {          // the pair that sets the prebuilt chain off
            let su = st.setups[Swift.min(suI, st.setups.count - 1)]
            return (su.c, su.c)
        }
        let r = rng.below(1000)
        let yp = Int(st.yarn * (1 + 0.6 * Double(up("yarn"))) * 1000)
        let mp = Int(st.mouse * (1 + 0.6 * Double(up("mouse"))) * 1000)
        let a = 1 + rng.below(st.ncol)
        let b = 1 + rng.below(st.ncol)
        let gold = rng.below(100000) < Int(GOLD_CHANCE * Double(1 + up("bell")) * 100000)
        if r < yp { return (KP.YARN, 0) }
        if r < yp + mp { return (KP.MOUSE, 0) }
        return (a | (gold ? KP.GOLD : 0), b)
    }

    func startPlay() {
        state = "play"; stateT = 0
        phase = "wait"; phaseT = 0.2
        if bonus {
            hype.banner("GO GO GO!", dur: 1.0, rainbow: true)
            if st.k == "snack" { hype.startFever(Double(st.lim)) }
        } else {
            hype.banner("GOOD NIGHT!", color: "lime", dur: 0.9, scale: 1)
        }
        say(quip, 2.6)
    }

    func goalDone() -> Bool {
        switch st.k {
        case "clear": return kits >= st.goal
        case "chain", "trigger": return bestChain >= st.goal
        case "rescue": return starsLeft == 0
        case "pillow": return KP.countCells(grid, KP.isJunk) == 0
        case "storm", "snack", "domino": return stime >= Double(st.lim)
        default: return false
        }
    }

    /// (short goal text, progress text, fraction) for the goal panel.
    func progress() -> (String, String, Double) {
        let g = st.goal
        switch st.k {
        case "clear": return ("NAP \(g) KITTENS", "\(Swift.min(kits, g))/\(g)", Double(kits) / Double(g))
        case "chain": return ("MAKE A \(g) CHAIN", "BEST \(bestChain)", Double(bestChain) / Double(g))
        case "trigger": return ("SET OFF A \(g) CHAIN", "BEST \(bestChain)", Double(bestChain) / Double(g))
        case "rescue":
            let got = stars0 - starsLeft
            return ("TUCK IN \(stars0) STARS", "\(got)/\(stars0)", Double(got) / Double(Swift.max(1, stars0)))
        case "pillow":
            let left = KP.countCells(grid, KP.isJunk)
            return ("CLEAR THE PILLOWS", "LEFT \(left)", 1 - Double(left) / Double(Swift.max(1, g)))
        case "storm":
            return ("SURVIVE \(st.lim) SEC", "\(Swift.max(0, Int(Double(st.lim) - stime + 0.99))) SEC", stime / Double(st.lim))
        case "duel", "boss":
            let f = foe!
            return (f.boss ? "SNOOZE THE BOSS!" : "SNOOZE \(foeName)", "AWAKE \(Swift.max(0, f.hp))", 1 - Double(f.hp) / Double(f.max))
        case "snack": return ("FISH COIN RUSH", "COINS \(coins)", stime / Double(st.lim))
        default:
            return ("DOMINO \(Swift.min(suI + 1, st.setups.count))/\(st.setups.count)", "COINS \(coins)", stime / Double(st.lim))
        }
    }

    func failStage(_ why: String) {
        if state != "play" { return }
        if bonus {
            stageClear()
            hype.banner("BED FULL!", "BONUS OVER", color: "peach", dur: 1.2)
            return
        }
        state = "fail"; stateT = 0
        lives -= 1
        piece = nil
        hype.breakCombo()
        app.audio.play("die")
        app.shake(4, 0.4)
        hype.banner("OH NO!", why, color: "red", dur: 1.6)
        mood("hurt", 2.0)
        say("THE BED IS TOO FULL!")
        if let f = foe { f.tele = nil; foeKeep = f.hp }
    }

    func stageClear() {
        if !["play", "bossdown", "foedown"].contains(state) { return }
        let k = st.k, L = lv
        state = "clear"; stateT = 0
        piece = nil
        app.audio.play("win")
        mood("cheer", 3.0)
        if k != "boss" { hype.banners = [] }
        var lines: [(String, Int)] = []
        if bonus {
            hype.banner("BONUS END!", "\(coins) FISH COINS", color: "yellow", dur: 1.4)
            lines = [("FISH COINS", coins * 50 * L)]
            if allClears > 0 { lines.append(("ALL TUCKED IN", allClears * 3000 * L)) }
            say("YUM! WHAT A FEAST!")
        } else {
            if k != "boss" { hype.banner("STAGE CLEAR!", dur: 1.4, rainbow: true) }
            hype.shower(40, "confetti")
            lines = [(k == "boss" ? "BOSS BONUS" : "CLEAR", (k == "boss" ? 5000 : 1000) * L)]
            if k == "storm" {
                lines.append(("SURVIVED", 1500 * L))
            } else if st.par > 0 {
                lines.append(("TIME", Int(Swift.max(0, Double(st.par) - stime)) * 20 * L))
            }
            lines.append(("BEST CHAIN X\(bestChain)", bestChain * bestChain * 100 * L))
            lines.append(("NO MISS", missed ? 0 : 2000 * L))
            let cells = KP.countCells(grid) { $0 != 0 }
            if cells == 0 { lines.append(("EMPTY BED", 5000 * L)) } else if cells <= 8 { lines.append(("TIDY BED", 1500 * L)) }
            say(KPData.cheers[(stageN + score / 10) % KPData.cheers.count])
        }
        tally = lines.map { ($0.0, $0.1, 0) }
        tallyI = 0; tallyT = 0
    }

    func nextStage() {
        let n = stageN
        if n >= STAGES {
            hype.jackpot(1000000, sub: "ALL 200 BEDS!")
            endGame(true, "ALL 200 STAGES!", delay: 3.5)
            return
        }
        if isBoss(n) || isBonus(n) {
            state = "upgrade"
            pickUpgrade(KittenPile.pool, ups, title: isBoss(n) ? "BOSS REWARD!" : "POWER UP!") { [unowned self] id in self.tookUpgrade(id) }
        } else {
            beginStage(n + 1)
        }
    }

    func tookUpgrade(_ id: String?) {
        if let id = id {
            ups[id, default: 0] += 1
            if id == "milk" { lives += 1; app.audio.play("extra") }
        } else {
            lives += 1
            hype.banner("1UP!", "EVERYTHING IS MAXED", color: "pink", dur: 1.4, sound: "extra")
        }
        beginStage(stageN + 1)
    }

    func checkLife() {
        while score >= LIFE_STEP * lifeK * (lifeK + 1) / 2 {
            lifeK += 1
            lives += 1
            hype.banner("1UP!", "EXTRA LIFE", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(20, "hearts")
        }
    }

    // ================================================================ the piece
    func cells(_ p: KPPiece, x: Int? = nil, y: Int? = nil, rot: Int? = nil) -> [KP.Cell] {
        KP.pieceCells(x ?? p.x, y ?? p.y, rot ?? p.rot, p.b == 0)
    }

    func spawn() {
        if KP.topped(grid) {
            if nightLights > 0 { guardSave(); return }
            failStage("THE BED IS FULL!")
            return
        }
        let (a, b) = queue.removeFirst()
        queue.append(genPiece())
        piece = KPPiece(x: KP.SPAWN_X, y: 0, rot: 0, a: a, b: b)
        pieceId += 1
        fallT = 0; lockT = 0; lockResets = 0
        phase = "piece"
    }

    /// NIGHT LIGHT upgrade: Poppy shoos the top four rows away instead of losing the stage.
    func guardSave() {
        nightLights -= 1
        for y in 0 ..< 4 {
            for x in 0 ..< COLS where grid[y][x] != 0 {
                parts.burst(Double(BX + x * CELL + 6), Double(BY + y * CELL + 6), 4, ["yellow", "white"], 60, 0.5)
                grid[y][x] = 0
            }
        }
        hype.banner("NIGHT LIGHT!", "POPPY SAVES THE BED", color: "orange", dur: 1.4, sound: "powerup")
        hype.flash("yellow", 0.25)
        mood("cheer")
        phase = "wait"; phaseT = 0.4
    }

    func tryMove(_ dx: Int, _ dy: Int) -> Bool {
        guard var p = piece else { return false }
        if KP.fits(grid, cells(p, x: p.x + dx, y: p.y + dy)) {
            p.x += dx; p.y += dy
            piece = p
            return true
        }
        return false
    }

    func grounded() -> Bool {
        guard let p = piece else { return true }
        return !KP.fits(grid, cells(p, y: p.y + 1))
    }

    func bumpLock() {
        if lockResets < 12 { lockT = 0; lockResets += 1 }
    }

    func rotate(_ d: Int) {
        guard var p = piece, p.b != 0 else { return }
        for nr in [(p.rot + d + 4) % 4, (p.rot + 2) % 4] {      // quick turn when boxed in
            let (sx, sy) = KP.DIRS[nr]
            for (kx, ky) in [(0, 0), (-sx, sy > 0 ? -sy : 0)] where KP.fits(grid, cells(p, x: p.x + kx, y: p.y + ky, rot: nr)) {
                p.x += kx; p.y += ky; p.rot = nr
                piece = p
                app.audio.play("rotate")
                bumpLock()
                return
            }
        }
    }

    func hardDrop() {
        guard var p = piece else { return }
        let d = KP.dropY(grid, p.x, p.y, p.rot, p.b == 0) - p.y
        p.y += d
        piece = p
        add(d * 2)
        fallT = 0
        lock()
    }

    func lock() {
        guard let p = piece else { return }
        let codes = p.b == 0 ? [p.a] : [p.a, p.b]
        let cc = cells(p).enumerated().map { ($0.element.x, $0.element.y, codes[$0.offset]) }
        let order = cc.enumerated().sorted { $0.element.1 != $1.element.1 ? $0.element.1 > $1.element.1 : $0.offset < $1.offset }.map { $0.element }
        let res = KP.place(&grid, order)            // the lower kitten lands first
        piece = nil
        dropped = true
        app.audio.play("lock")
        landed = []
        for (i, (x, y, code)) in res.enumerated() {
            let sy = order[i].1
            if y < 0 {                               // no room left in that column: it hops back out
                parts.burst(Double(BX + x * CELL + 6), Double(BY - 4), 8, ["white", "lavender"], 60, 0.5)
                floats.add(Double(BX + x * CELL + 6), Double(BY - 12), "HOP!", "lavender")
                continue
            }
            off[y][x] = Swift.min(0, Double((sy - y) * CELL))
            if code == KP.YARN || code == KP.MOUSE { landed.append((x, y, code)) }
        }
        phase = "settle"
    }

    // ================================================================ resolution
    func moveCells(_ moves: [(Int, Int, Int)], _ extra: Double = 0) {
        for (x, fy, ty) in moves {
            off[ty][x] = Double((fy - ty) * CELL) - extra
            moodT[ty][x] = moodT[fy][x]
            moodT[fy][x] = 0
            off[fy][x] = 0
        }
    }

    func falling() -> Bool {
        for y in 0 ..< ROWS { for x in 0 ..< COLS where off[y][x] < 0 { return true } }
        return false
    }

    func afterSettle() {
        // specials that just landed act first
        while !landed.isEmpty {
            let (x, y, code) = landed.removeFirst()
            if grid[y][x] != code { continue }
            if code == KP.YARN {
                let k = KP.yarnColor(grid, x, y)
                grid[y][x] = 0
                parts.burst(Double(BX + x * CELL + 6), Double(BY + y * CELL + 6), 14, ["pink", "hotpink", "white"], 80, 0.6)
                if k > 0 {
                    var cs: [KP.Cell] = []
                    for yy in 0 ..< ROWS { for xx in 0 ..< COLS where KP.kcolor(grid[yy][xx]) == k { cs.append((xx, yy)) } }
                    hype.banner("YARN BALL!", "\(KPArt.kitNames[k] ?? "") KITTENS NAP", color: "pink", dur: 1.2, scale: 1)
                    startPop([cs])
                    return
                }
                app.audio.play("pop")
            } else {
                let gone = KP.mouseCells(grid, x, y, 1 + (up("mouse") >= 2 ? 1 : 0))
                grid[y][x] = 0
                app.audio.play("tin")
                floats.add(Double(BX + x * CELL + 6), Double(BY + y * CELL - 4), "SQUEAK!", "yellow")
                for (jx, jy) in gone {
                    grid[jy][jx] = 0
                    parts.burst(Double(BX + jx * CELL + 6), Double(BY + jy * CELL + 6), 6, ["white", "cream", "lavender"], 70, 0.5)
                    add(30 * lv)
                }
                if !gone.isEmpty { hype.hit(1) }
            }
            moveCells(KP.applyGravity(&grid))
            if falling() { return }
        }
        let groups = KP.findGroups(grid)
        if !groups.isEmpty { startPop(groups); return }
        endChain()
    }

    func startPop(_ groups: [[KP.Cell]]) {
        chain += 1
        let ch = chain
        let cs = groups.flatMap { $0 }
        popping = cs.map { ($0.x, $0.y, grid[$0.y][$0.x]) }
        popT = 0
        phase = "pop"
        let n = cs.count, L = lv
        let pts = Int(Double(KP.stepPoints(groups, ch, grid)) * (1 + 0.25 * Double(up("lullaby"))) * (1 + 0.1 * Double(tierN)))
        let cx = Double(cs.reduce(0) { $0 + $1.x }) / Double(n)
        let cy = Double(cs.reduce(0) { $0 + $1.y }) / Double(n)
        let px = Double(BX) + cx * Double(CELL) + 6, py = Double(BY) + cy * Double(CELL)
        add(pts, px, py, ch < 2 ? "white" : "yellow")
        kits += n
        bestChain = Swift.max(bestChain, ch)
        let stars = popping.filter { $0.2 & KP.STAR != 0 }.count
        let golds = popping.filter { $0.2 & KP.GOLD != 0 }.count
        if stars > 0 {
            rescued += stars
            hype.banner(stars == 1 ? "STAR TUCKED IN!" : "\(stars) STARS TUCKED IN!", color: "yellow", dur: 1.0, scale: 1, sound: "bonus")
            add(1000 * L * stars)
        }
        if golds > 0 {
            hype.jackpot(5000 * L, sub: "GOLDEN KITTEN!")
            mood("cheer", 2.0)
        }
        if st.k == "snack" || st.k == "domino" {
            coins += n * (st.k == "domino" ? ch : 1)
            for (x, y) in cs.prefix(8) {
                coinFx.append((Double(BX + x * CELL + 2), Double(BY + y * CELL + 3), Double.random(in: -30 ... 30), -70, 1.0))
            }
            app.audio.play("coin")
        }
        hype.hit(groups.count, fever: 0.045 * (1 + 0.35 * Double(up("purr"))) * Double(Swift.min(3, ch)))
        if let f = foe, !f.sleep {
            let power = Int(Double(KP.stepPower(groups, ch)) * (1 + 0.25 * Double(up("catnip")) + 0.05 * Double(tierN)) *
                            (hype.feverOn ? 2 : 1))
            sendNaps(power, px, py)
        }
        app.audio.play(ch == 1 ? "pop" : ch < 4 ? "line" : "quad")
        if ch >= 2 {
            let word = CHAIN_WORDS[Swift.min(ch, CHAIN_WORDS.count - 1)]
            hype.banner("\(ch) CHAIN!", word, color: ch < 4 ? "peach" : "hotpink", dur: 1.0, rainbow: ch >= 5, scale: ch >= 3 ? 2 : 1)
            mood("happy", 1.4)
            if ch >= 4 {
                hype.flash("white", 0.12)
                app.shake(2 + Double(Swift.min(4, ch - 3)), 0.3)
            }
            if ch >= 6 {
                hype.slowmo(0.4, 0.6)
                hype.shower(30 + ch * 6, "stars")
                say("WHAT A TUMBLE!!")
            }
            if ch >= 8 { hype.jackpot(20000 * L, sub: "\(ch) CHAIN!!") }
        } else {
            mood("happy", 0.7)
        }
    }

    func finishPop() {
        let cs = popping.map { KP.Cell(x: $0.0, y: $0.1) }
        for (jx, jy) in KP.junkHits(grid, cs) {
            let c = grid[jy][jx]
            let gone = KP.hitJunk(&grid, jx, jy)
            parts.burst(Double(BX + jx * CELL + 6), Double(BY + jy * CELL + 6), gone ? 6 : 3,
                        c == KP.PILLOW ? ["white", "cream"] : ["gray", "white"], 60, 0.5)
            if gone { add(20 * lv) }
        }
        for (x, y, code) in popping {
            grid[y][x] = 0
            moodT[y][x] = 0
            parts.burst(Double(BX + x * CELL + 6), Double(BY + y * CELL + 6), 5, [KPArt.kitCoat[code & 7] ?? "white", "white", "lavender"], 55, 0.6)
        }
        popping = []
        moveCells(KP.applyGravity(&grid))
        phase = "settle"
    }

    func endChain() {
        if chain > 0 {
            let empty = KP.countCells(grid) { $0 != 0 } == 0
            if empty {
                allClears += 1
                hype.banner("ALL TUCKED IN!", "+\(5000 * lv * hype.mult)", dur: 1.8, rainbow: true, sound: "extra")
                add(5000 * lv)
                hype.shower(50, "hearts")
                hype.flash("pink", 0.25)
                if let f = foe, !f.sleep { sendNaps(30, Double(BX + BW / 2), Double(BY + BH / 2)) }
            }
            if st.k == "domino" && (chain >= 2 || empty) {
                suI += 1
                if suI < st.setups.count {
                    hype.banner("NEXT DOMINO!", color: "mint", dur: 0.9, scale: 1)
                    let su = st.setups[suI]
                    queue = (0 ..< 4).map { _ in (su.c, su.c) }
                    chain = 0
                    dropIn(su.rows)
                    return
                }
                chain = 0
                stageClear()
                return
            }
        }
        chain = 0
        if state != "play" { return }
        if goalDone() && !["storm", "snack", "domino"].contains(st.k) { stageClear(); return }
        if st.k == "trigger" && dropped {               // missed the spot: Poppy makes the domino bed again
            dropped = false
            missed = true
            hype.banner("MISSED!", "POPPY REMAKES THE BED", color: "peach", dur: 1.2, scale: 1)
            say("ALMOST! TRY ANOTHER SPOT")
            dropIn(st.setups[0].rows)
            return
        }
        if pendRise > 0 && raiseBed() { return }
        if pendingTotal > 0 { dropGarbage(); return }
        phase = "wait"; phaseT = 0.05
    }

    /// A fresh prebuilt bed tumbles in from above.
    func dropIn(_ rows: [String]) {
        loadRows(rows)
        for y in 0 ..< ROWS { for x in 0 ..< COLS where grid[y][x] != 0 { off[y][x] = -Double(BH + 20 + (ROWS - y) * 4) } }
        phase = "settle"
    }

    /// Outside play (clear, tally, a rival dozing off) kittens still finish falling.
    func settleVisual(_ dt: Double) {
        for y in 0 ..< ROWS { for x in 0 ..< COLS where off[y][x] < 0 { off[y][x] = Swift.min(0, off[y][x] + FALL * dt) } }
    }

    // ================================================================ pillows, grandpas, grumpy kittens
    func dropGarbage() {
        var items: [Int] = []
        let n = Swift.min(30, pend[0]); pend[0] -= n
        items += [Int](repeating: KP.PILLOW, count: n)
        let g = Swift.min(3, pend[1]); pend[1] -= g
        items += [Int](repeating: KP.GRANDPA, count: g)
        let k = Swift.min(12, pend[2]); pend[2] -= k
        for _ in 0 ..< k { items.append(1 + frng.below(st.ncol)) }
        // full rows across the bed, then the rest in random columns
        var rows: [[Int]] = []
        while items.count >= COLS { rows.append(Array(items[0 ..< COLS])); items.removeFirst(COLS) }
        if !items.isEmpty {
            var colsLeft = Array(0 ..< COLS)
            var row = [Int](repeating: 0, count: COLS)
            for code in items {
                let i = frng.below(colsLeft.count)
                row[colsLeft.remove(at: i)] = code
            }
            rows.append(row)
        }
        for (ri, row) in rows.enumerated() {
            for (x, code) in row.enumerated() where code != 0 {
                let ty = ROWS - 1 - KP.colHeight(grid, x)
                if ty < 0 { continue }
                grid[ty][x] = code
                off[ty][x] = -Double((ty + 2 + ri) * CELL + 8)
                if KP.isKitten(code) { moodT[ty][x] = 2.5 }
            }
        }
        app.audio.play(rows.count > 1 ? "boom" : "hurt")
        app.shake(2 + Double(Swift.min(3, rows.count)), 0.25)
        mood("hurt", 1.2)
        phase = "settle"
    }

    /// BED QUAKE / RISING BED: a row of pillows pushes up from below (one gap).
    func raiseBed() -> Bool {
        pendRise = Swift.max(0, pendRise - 1)
        if grid[0].contains(where: { $0 != 0 }) {
            failStage("PUSHED OUT OF BED!")
            return true
        }
        let gap = frng.below(COLS)
        grid = Array(grid[1...]) + [(0 ..< COLS).map { $0 == gap ? 0 : KP.PILLOW }]
        off = Array(off[1...]) + [[Double](repeating: 0, count: COLS)]
        moodT = Array(moodT[1...]) + [[Double](repeating: 0, count: COLS)]
        if let p = piece, !KP.fits(grid, cells(p)) { piece!.y -= 1 }
        bedKick = 0.25
        app.audio.play("hurt")
        app.shake(3, 0.3)
        mood("hurt")
        if piece == nil { phase = "settle" }
        return piece == nil
    }

    // ================================================================ rivals and bosses
    func sendNaps(_ power0: Int, _ x: Double, _ y: Double) {
        var power = power0
        if power <= 0 { return }
        var blocked = 0
        for (i, cost) in [(0, 1), (2, 1), (1, 3)] {      // cancel pillows, grumpies, then grandpas first
            while power >= cost && pend[i] > 0 { pend[i] -= 1; power -= cost; blocked += 1 }
        }
        if blocked > 0 { floats.add(Double(BX + BW / 2), Double(BY - 18), "BLOCK \(blocked)", "mint") }
        if power <= 0 { return }
        shots.append((x, y, 0, power))
    }

    func hitFoe(_ dmg: Int) {
        guard let f = foe, !f.sleep, state == "play" else { return }
        f.hp = Swift.max(0, f.hp - dmg)
        f.hit = 0.3
        floats.add(Double(FOE_X + Int.random(in: -12 ... 12)), Double(FOE_Y - 30), "-\(dmg)", "red")
        parts.burst(Double(FOE_X), Double(FOE_Y), 6 + Swift.min(20, dmg / 4), ["white", "lavender", "yellow"], 80, 0.6)
        hype.hitstop(0.03 + Swift.min(0.08, Double(dmg) / 600))
        if dmg >= 40 { hype.flash("white", 0.12); app.shake(3, 0.25) }
        if f.hp <= 0 { foeDown(); return }
        let frac = Double(f.hp) / Double(f.max)
        if f.phase == 1 && frac <= 0.5 {
            f.phase = 2
            hype.banner("GRRR!", "\(foeName) IS WIDE AWAKE", color: "red", dur: 1.2, scale: 1)
        }
        if f.phase == 2 && frac <= 0.2 && f.boss && tierN >= 3 {
            f.phase = 3
            hype.banner("LAST YAWN!", color: "red", dur: 1.2)
        }
    }

    func foeDown() {
        guard let f = foe else { return }
        f.sleep = true
        f.tele = nil
        pend = [0, 0, 0]
        if !popping.isEmpty { finishPop() }
        state = f.boss ? "bossdown" : "foedown"
        stateT = 0
        piece = nil
        if f.boss {
            app.audio.stopMusic()
            app.audio.play("bossdown")
            hype.slowmo(0.3, 1.4)
            hype.flash("white", 0.4)
            hype.shower(120, "stars")
            app.shake(6, 0.8)
            hype.banners = []
            hype.banner("BOSS ASLEEP!", foeName, dur: 2.4, rainbow: true)
            add(10000 * lv)
            say("SWEET DREAMS, GRUMPY!")
        } else {
            app.audio.play("win")
            hype.banner("SNOOZED!", "\(foeName) IS ASLEEP", color: "lime", dur: 1.4)
            hype.shower(40, "stars")
        }
        mood("cheer", 3.0)
    }

    func tickFoe(_ dt: Double) {
        guard let f = foe else { return }
        f.hit = Swift.max(0, f.hit - dt)
        if f.sleep { return }
        if var tele = f.tele {
            tele.1 -= dt
            f.tele = tele
            if tele.1 <= 0 {
                f.tele = nil
                foeAttack(tele.0)
                if f.phase >= 3 && frng.below(2) == 0 { f.t = 1.2 }
            }
            return
        }
        f.t -= dt
        if f.t <= 0 {
            f.t = f.every * (f.phase >= 2 ? 0.75 : 1.0)
            let atk = frng.below(100) < 45 ? f.atk[0] : f.atk[frng.below(f.atk.count)]
            f.tele = (atk, Swift.max(1.0, 1.8 - Double(tierN) * 0.04))
            app.audio.play("trap")
        }
    }

    func foeAttack(_ atk: String) {
        guard let f = foe else { return }
        let p = f.pow + (f.phase >= 3 ? 2 : 0)
        let fort = Swift.max(0.25, 1 - 0.25 * Double(up("fort"))) * foeMult
        hype.banner((KPData.attackNames[atk] ?? atk) + "!", color: "red", dur: 0.9, scale: 1)
        shots.append((Double(FOE_X), Double(FOE_Y - 10), 0, -1))       // a pillow flying back at the bed (visual)
        switch atk {
        case "toss": pend[0] += Swift.max(1, Int(Double(p) * fort))
        case "grandpa": pend[1] += Swift.max(1, Int(Double(1 + p / 6) * Swift.min(1.0, fort + 0.25)))
        case "grumpy": pend[2] += Swift.max(2, Int(Double(4 + p / 2) * fort))
        case "fog": fogT = 5.0 + Double(p) * 0.3; app.audio.play("bubble")
        case "zoom": zoomT = 4.0 + Double(p) * 0.2; app.audio.play("powerup")
        case "dizzy": dizzyT = 4.0 + Double(p) * 0.2; app.audio.play("powerup")
        case "rise": pendRise += 1 + (p >= 10 ? 1 : 0)
        default: break
        }
    }

    // ================================================================ update
    override func tick(_ dt: Double) {
        if poppyMood.1 > 0 {
            poppyMood.1 -= dt
            if poppyMood.1 <= 0 { poppyMood.0 = "idle" }
        }
        if var tk = talk {
            tk.1 -= dt
            talk = tk.1 <= 0 ? nil : tk
        }
        bedKick = Swift.max(0, bedKick - dt)
        for key in Array(squish.keys) {
            squish[key]! -= dt
            if squish[key]! <= 0 { squish[key] = nil }
        }
        for y in 0 ..< ROWS { for x in 0 ..< COLS where moodT[y][x] > 0 { moodT[y][x] -= dt } }
        tickShots(dt)
        tickCoins(dt)
        if state != "play" { settleVisual(dt) }
        if hype.feverOn != feverWas && state == "play" && !bonus {
            feverWas = hype.feverOn
            song = feverWas ? "fever" : st.k == "boss" ? "boss" : st.k == "duel" ? "kp_duel" : "kp_nap"
            app.audio.music(song)
        }
        if ending != nil { return }
        stateT += dt
        let inp = app.input
        switch state {
        case "warning":
            if stateT > 2.6 { state = "intro"; stateT = 0 }
        case "intro":
            if stateT > 3.2 || (stateT > 0.5 && inp.hit(.a, .b, .up, .y)) { startPlay() }
        case "fail":
            if stateT > 1.8 {
                if lives <= 0 { endGame(false, "STAGE \(stageN)") } else { beginStage(stageN, retry: true) }
            }
        case "bossdown", "foedown":
            let boss = foe?.boss ?? false
            if boss && stateT > 0.5 && Int(stateT * 10) % 2 == 0 {
                parts.burst(Double(FOE_X + Int.random(in: -16 ... 16)), Double(FOE_Y + Int.random(in: -14 ... 14)), 8,
                            ["lavender", "white", "yellow"], 90, 0.7)
            }
            if stateT > (boss ? 2.4 : 1.3) { stageClear() }
        case "clear":
            if stateT > 1.3 { state = "tally"; stateT = 0 }
        case "tally":
            tickTally(dt)
        case "play":
            tickPlay(dt)
        default:
            break
        }
    }

    func tickTally(_ dt: Double) {
        tallyT += dt
        if tallyI < tally.count {
            var line = tally[tallyI]
            let step = Swift.max(1, line.1 / 24)
            let addv = Swift.min(step, line.1 - line.2)
            line.2 += addv
            tally[tallyI] = line
            score += addv
            if tallyT > 0.06 && addv > 0 { tallyT = 0; app.audio.play("move") }
            if line.2 >= line.1 {
                tallyI += 1
                tallyT = 0
                app.audio.play(line.1 > 0 ? "coin" : "move")
            }
            checkLife()
            return
        }
        if (tallyT > 0.6 && app.input.hit(.a, .b, .up, .y)) || tallyT > 3.0 { nextStage() }
    }

    func tickPlay(_ dt: Double) {
        stime += dt
        fogT = Swift.max(0, fogT - dt)
        zoomT = Swift.max(0, zoomT - dt)
        dizzyT = Swift.max(0, dizzyT - dt)
        if phase == "settle" || phase == "pop" || chain > 0 { hype.keepCombo() }
        checkLife()
        if ["storm", "snack", "domino"].contains(st.k) && stime >= Double(st.lim) && (phase == "piece" || phase == "wait") {
            stageClear()
            if st.k == "storm" { hype.banner("MORNING!", "THE STORM IS OVER", color: "yellow", dur: 1.4) }
            return
        }
        if st.rain > 0 {
            rainT += dt
            if rainT >= st.rain {
                rainT = 0
                pend[0] += Swift.max(1, Int(Double(st.rainN) * Swift.max(0.25, 1 - 0.25 * Double(up("fort")))))
                if tierN >= 6 && frng.below(4) == 0 { pend[1] += 1 }
                app.audio.play("trap")
            }
        }
        if st.rise > 0 {
            riseT += dt
            if riseT >= st.rise { riseT = 0; pendRise += 1 }
        }
        if foe != nil {
            tickFoe(dt)
            if state != "play" { return }
        }
        switch phase {
        case "wait":
            phaseT -= dt
            if phaseT <= 0 { spawn() }
        case "settle":
            var moving = false
            for y in 0 ..< ROWS {
                for x in 0 ..< COLS where off[y][x] < 0 {
                    var o = off[y][x] + FALL * dt
                    if o >= 0 { o = 0; squish[y * COLS + x] = 0.12 } else { moving = true }
                    off[y][x] = o
                }
            }
            if !moving { afterSettle() }
        case "pop":
            popT += dt
            if popT >= POP_TIME { finishPop() }
        case "piece":
            if pendRise > 0 && raiseBed() { return }
            playInput(dt)
        default:
            break
        }
    }

    func playInput(_ dt: Double) {
        let inp = app.input
        guard piece != nil else { return }
        if inp.hit(.up, .y) { hardDrop(); return }
        if inp.hit(.a) { rotate(1) } else if inp.hit(.b) { rotate(-1) }
        var d = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        if dizzyT > 0 { d = -d }
        if d != dasDir {
            dasDir = d; dasT = 0
            if d != 0 && tryMove(d, 0) { app.audio.play("move"); bumpLock() }
        } else if d != 0 {
            dasT += dt
            if dasT > 0.17 {
                dasT -= 0.06
                if tryMove(d, 0) { bumpLock() }
            }
        }
        var g = gravity()
        let soft = inp.down(.down)
        if soft { g = Swift.min(g, 0.035) }
        fallT += dt
        while fallT >= g {
            fallT -= g
            if tryMove(0, 1) {
                if soft { add(1) }
            } else {
                fallT = 0
                break
            }
        }
        if grounded() {
            lockT += dt
            if lockT >= (soft ? 0.08 : LOCK_DELAY) { lock() }
        } else {
            lockT = 0
        }
    }

    func tickShots(_ dt: Double) {
        for i in shots.indices {
            shots[i].p += dt * 2.2
            if shots[i].power > 0 && shots[i].p >= 1 { hitFoe(shots[i].power) }
        }
        shots.removeAll { $0.p >= 1 }
    }

    func tickCoins(_ dt: Double) {
        for i in coinFx.indices {
            coinFx[i].x += coinFx[i].vx * dt
            coinFx[i].y += coinFx[i].vy * dt
            coinFx[i].vy += 160 * dt
            coinFx[i].life -= dt
        }
        coinFx.removeAll { $0.life <= 0 }
    }

    // ================================================================ drawing
    override func render(_ s: Surface) {
        KPArt.drawBg(s, theme, t)
        drawBed(s)
        drawLeft(s)
        drawRight(s)
        drawHud(s)
        parts.draw(s)
        floats.draw(s)
        for c in coinFx where c.life > 0.25 || Int(c.life * 30) % 2 == 1 { s.blit(sprite("kp_fish"), Int(c.x), Int(c.y)) }
        switch state {
        case "warning": drawWarning(s)
        case "intro": drawIntro(s)
        case "tally": drawTally(s)
        default: break
        }
    }

    func drawBed(_ s: Surface) {
        let kick = bedKick > 0 ? Int(sin(t * 60) * 2) : 0
        let by = BY + kick
        KPArt.bed(s, BX, by, BW, BH, theme)
        // danger mark over the spawn column
        if KP.colHeight(grid, KP.SPAWN_X) >= ROWS - 3 && Int(t * 4) % 2 == 1 {
            let x0 = BX + KP.SPAWN_X * CELL
            s.line(col("red"), x0 + 2, by + 2, x0 + 9, by + 9, width: 2)
            s.line(col("red"), x0 + 9, by + 2, x0 + 2, by + 9, width: 2)
        }
        let worried = (0 ..< COLS).map { KP.colHeight(grid, $0) }.max()! >= ROWS - 2
        let popset = Set(popping.map { $0.1 * COLS + $0.0 })
        let fever = hype.feverOn
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS {
                let c = grid[y][x]
                if c == 0 || popset.contains(y * COLS + x) { continue }
                let px = BX + x * CELL
                var py = by + y * CELL + Int(off[y][x])
                if KP.isKitten(c) {
                    var m = 0
                    if moodT[y][x] > 0 { m = 5 } else if fever || state == "clear" || state == "tally" { m = 3 } else if worried { m = 4 } else if Int(t * 2 + Double(x * 7 + y * 13)) % 23 == 0 { m = 1 }
                    if squish[y * COLS + x] != nil { py += 1 }
                    KPArt.kitten(s, px, py, c, m, t)
                } else {
                    KPArt.cell(s, px, py, c, 0, t)
                }
            }
        }
        // paws holding between settled same-colour neighbours
        for y in 0 ..< ROWS {
            for x in 0 ..< COLS {
                let k = KP.kcolor(grid[y][x])
                if k == 0 || off[y][x] < 0 || popset.contains(y * COLS + x) { continue }
                if x + 1 < COLS && KP.kcolor(grid[y][x + 1]) == k && off[y][x + 1] >= 0 && !popset.contains(y * COLS + x + 1) {
                    KPArt.link(s, BX + x * CELL, by + y * CELL, k, true)
                }
                if y + 1 < ROWS && KP.kcolor(grid[y + 1][x]) == k && off[y + 1][x] >= 0 && !popset.contains((y + 1) * COLS + x) {
                    KPArt.link(s, BX + x * CELL, by + y * CELL, k, false)
                }
            }
        }
        if !popping.isEmpty {
            let f = Swift.min(1, popT / POP_TIME)
            for (x, y, code) in popping { KPArt.curl(s, BX + x * CELL, by + y * CELL, code, f) }
        }
        if let p = piece, state == "play" {
            let frac = grounded() ? 0 : Swift.min(1, fallT / gravity()) * Double(CELL)
            let codes = p.b == 0 ? [p.a] : [p.a, p.b]
            if guide || st.k == "trigger" || st.k == "domino" { drawGuide(s, by, p, codes) }
            for (i, c) in cells(p).enumerated() { KPArt.cell(s, BX + c.x * CELL, by + c.y * CELL + Int(frac), codes[i], 0, t) }
        }
        if st.mods.contains("dark") && state == "play" { drawDark(s, by) }
        if fogT > 0 { drawFog(s, by) }
        if (st.k == "trigger" || st.k == "domino") && state == "play" && piece != nil && (st.k == "domino" || tierN < 3 || missed) {
            let su = st.setups[Swift.min(suI, st.setups.count - 1)]        // the glow: drop the pair here
            let gx = BX + su.x * CELL
            let hy = by + (ROWS - KP.colHeight(grid, su.x)) * CELL
            if Int(t * 5) % 2 == 1 { s.rect(col("yellow"), IRect(gx, hy - 24, CELL, 24), width: 1) }
            drawText(s, "`", gx + 3, hy - 34 + Int(sin(t * 6) * 2), "yellow", shadow: "ink")
        }
        drawPending(s)
    }

    func drawGuide(_ s: Surface, _ by: Int, _ p: KPPiece, _ codes: [Int]) {
        var g = grid
        let cc = cells(p).enumerated().map { ($0.element.x, $0.element.y, codes[$0.offset]) }
        let order = cc.enumerated().sorted { $0.element.1 != $1.element.1 ? $0.element.1 > $1.element.1 : $0.offset < $1.offset }.map { $0.element }
        for (x, y, code) in KP.place(&g, order) where y >= 0 {
            let c = code & 8 != 0 ? col("white") : col(KPArt.kitCoat[code & 7] ?? "white")
            let px = BX + x * CELL, py = by + y * CELL
            s.fillRect(c, px + 3, py + 3, 6, 1)
            s.fillRect(c, px + 3, py + 8, 6, 1)
            s.fillRect(c, px + 3, py + 3, 1, 6)
            s.fillRect(c, px + 8, py + 3, 1, 6)
        }
    }

    /// LIGHTS OUT: only the lantern light around the falling pair shows the bed.
    func drawDark(_ s: Surface, _ by: Int) {
        var cx = BX + BW / 2, cy = by + BH / 2
        if let p = piece { cx = BX + p.x * CELL + 6; cy = by + p.y * CELL + 6 }
        let r = 34
        let shade = col("black", 225)
        for yy in 0 ..< BH {
            let dy = yy + by - cy
            if abs(dy) >= r { s.fillRect(shade, BX, by + yy, BW, 1); continue }
            let half = Int(Double(r * r - dy * dy).squareRoot())
            let x0 = cx - half - BX, x1 = cx + half - BX
            if x0 > 0 { s.fillRect(shade, BX, by + yy, Swift.min(BW, x0), 1) }
            if x1 < BW { s.fillRect(shade, BX + Swift.max(0, x1), by + yy, BW - Swift.max(0, x1), 1) }
        }
    }

    /// FLUFF FOG: a lavender cloud over the top of the bed (thick at the top, puffy lower edge).
    func drawFog(_ s: Surface, _ by: Int) {
        let fh = BH * 2 / 3
        var yy = 0
        while yy < fh { s.fillRect(col("lavender", 215 - yy * 100 / fh), BX, by + yy, BW, 3); yy += 3 }
        for i in 0 ..< 5 { s.circle(col("lavender", 120), BX + i * 14 + 8 + Int(sin(t * 2 + Double(i)) * 1), by + fh + 5, 5) }
    }

    /// Pillows, grandpas and grumpy kittens on their way (shown above the bed).
    func drawPending(_ s: Surface) {
        if pendingTotal <= 0 && foe?.tele == nil { return }
        var x = BX
        let y = BY - 14
        var icons: [String] = []
        icons += [String](repeating: "big", count: pend[0] / 6) + [String](repeating: "small", count: pend[0] % 6)
        icons += [String](repeating: "grandpa", count: pend[1])
        icons += [String](repeating: "grumpy", count: pend[2])
        for ic in icons.prefix(12) {
            switch ic {
            case "big": s.blit(sprite("kp_pillow"), x, y - 2); x += 12
            case "small":
                s.rect(col("cream"), IRect(x, y + 3, 6, 5), radius: 2)
                s.fillRect(col("white"), x + 1, y + 4, 4, 2)
                x += 7
            case "grandpa": s.blit(sprite("kp_grandpa"), x, y - 2); x += 12
            default: s.circle(col("red"), x + 3, y + 5, 3); x += 7
            }
        }
        if icons.count > 12 { drawText(s, "+\(icons.count - 12)", x + 1, y + 2, "red", shadow: "ink") }
    }

    func drawHud(_ s: Surface) {
        s.fillRect(rgba(12, 8, 24, 170), 0, 0, W, 11)
        drawText(s, "SCORE " + pad7(score), 4, 2, "yellow", shadow: nil)
        drawText(s, "HI " + pad7(Swift.max(best, score)), 104, 2, "lavender", shadow: nil)
        drawText(s, "STAGE \(stageN)", 196, 2, "white", shadow: nil)
        hearts(s, 262, 2, lives, maxShow: 6)
    }

    private func pad7(_ v: Int) -> String {
        let str = String(v)
        return str.count >= 7 ? str : String(repeating: "0", count: 7 - str.count) + str
    }

    func drawLeft(_ s: Surface) {
        let hue = theme.hue
        panel(s, IRect(4, 14, 112, 50), fill: "night", border: hue)
        drawText(s, KPData.kindTitle[st.k] ?? "", 60, 18, theme.acc, align: .center)
        let (goal, prog, frac) = progress()
        drawText(s, goal, 60, 29, "white", align: .center, shadow: nil)
        s.fillRect(col("darkgray"), 10, 41, 100, 6)
        let w = Int(100 * Swift.max(0, Swift.min(1, frac)))
        s.fillRect(col(frac >= 1 ? "lime" : hue), 10, 41, w, 6)
        s.fillRect(col("white"), 10, 41, w, 1)
        drawText(s, prog, 60, 51, frac >= 1 ? "yellow" : "lavender", align: .center, shadow: nil)
        // purr meter
        panel(s, IRect(4, 67, 112, 20), fill: "night", border: hype.feverOn ? rainbow(0, t) : "pink")
        drawText(s, "PURR", 9, 74, "pink", shadow: nil)
        var fv = hype.feverOn ? 1.0 : hype.fever
        if hype.feverOn {
            fv = st.k != "snack" ? hype.feverT / hype.feverTime : Swift.max(0, 1 - stime / Double(Swift.max(1, st.lim)))
        }
        s.fillRect(col("darkgray"), 36, 73, 74, 8)
        let fw = Int(74 * Swift.max(0, Swift.min(1, fv)))
        for i in 0 ..< fw { s.fillRect(col(hype.feverOn ? rainbow(i / 6, t) : "hotpink"), 36 + i, 73, 1, 8) }
        for i in 1 ..< 4 { s.fillRect(col("night"), 36 + i * 74 / 4, 73, 1, 8) }
        // status chips
        var y = 92
        var chips: [(String, String)] = []
        if zoomT > 0 { chips.append(("ZOOMIES!", "orange")) }
        if dizzyT > 0 { chips.append(("DIZZY!", "lime")) }
        if fogT > 0 { chips.append(("FOGGY!", "lavender")) }
        if nightLights > 0 { chips.append(("NIGHT LIGHT X\(nightLights)", "orange")) }
        for m in st.mods { chips.append((KPData.mods[m] ?? m, "peach")) }
        for (text, c) in chips.prefix(2) {
            drawText(s, text, 8, y, !text.hasSuffix("!") || Int(t * 6) % 2 == 1 ? c : "white", shadow: "ink")
            y += 9
        }
        // Poppy on her rug
        s.ellipse(col(theme.acc), 14, 186, 64, 10)
        s.ellipse(lerpCol("black", theme.acc, 0.6), 20, 188, 52, 6, width: 1)
        var look = 0
        if let p = piece { look = Swift.max(-2, Swift.min(2, p.x - 2)) }
        var m = poppyMood.0
        if m == "idle" {
            if state == "clear" || state == "tally" {
                m = "cheer"
            } else if state == "fail" {
                m = "hurt"
            } else if piece != nil && dasDir != 0 {
                m = "move"
            } else if (0 ..< COLS).map({ KP.colHeight(grid, $0) }).max()! >= ROWS - 2 {
                m = "hurt"
            }
        }
        KPArt.poppy(s, 46, 190, t, m, look: look)
        if let tk = talk { drawTalk(s, tk.0) }
    }

    /// Poppy's speech bubble above her head (at most 2 lines of 17).
    func drawTalk(_ s: Surface, _ text: String) {
        let lines = Array(KPArt.wrap(text, 17).prefix(2))
        let w = (lines.map { textWidth($0) }.max() ?? 0) + 8
        let h = lines.count * 9 + 4
        let x = Swift.max(5, 60 - w / 2), y = 136 - h
        panel(s, IRect(x, y, w, h), fill: "white", border: "black", radius: 3, shadow: false)
        s.polygon(col("white"), [(50, Double(y + h - 1)), (56, Double(y + h - 1)), (48, Double(y + h + 5))])
        s.line(col("black"), 48, y + h + 5, 50, y + h - 1)
        s.line(col("black"), 48, y + h + 5, 56, y + h - 1)
        for (i, ln) in lines.enumerated() { drawText(s, ln, x + 4, y + 3 + i * 9, "ink", shadow: nil) }
    }

    func drawRight(_ s: Surface) {
        let hue = theme.hue
        panel(s, IRect(206, 14, 54, 62), fill: "night", border: hue)
        drawText(s, "NEXT", 233, 17, "white", align: .center, shadow: nil)
        let n = 2 + up("peek")
        if fogT > 0 {
            drawText(s, "?", 233, 40, "lavender", scale: 2, align: .center)
        } else {
            let x0 = 233 - (n * 12 + (n - 1) * 3) / 2
            for (i, pr) in queue.prefix(n).enumerated() {
                let x = x0 + i * 15, y0 = 30 + i * 6
                if pr.1 != 0 {
                    KPArt.cell(s, x, y0, pr.1, 0, t)
                    KPArt.cell(s, x, y0 + 12, pr.0, 0, t)
                } else {
                    KPArt.cell(s, x, y0 + 6, pr.0, 0, t)
                }
            }
        }
        // stage info: time, the kitten colours in play, best chain
        panel(s, IRect(263, 14, 53, 62), fill: "night", border: hue)
        drawText(s, "TIME", 289, 17, "lavender", align: .center, shadow: nil)
        let secs = Int(stime)
        drawText(s, "\(secs / 60):" + (secs % 60 < 10 ? "0" : "") + "\(secs % 60)", 289, 26, "white", align: .center, shadow: nil)
        let nc = st.ncol
        for i in 0 ..< nc { KPArt.kitten(s, 289 - nc * 5 + i * 10 - 1, 37 + (i % 2) * 3, i + 1, 0) }
        drawText(s, "CHAIN X\(bestChain)", 289, 64, "peach", align: .center, shadow: nil)
        // rival / boss, else the upgrade shelf
        panel(s, IRect(206, 80, 110, 116), fill: "night", border: foe?.boss == true ? "red" : hue)
        if let f = foe {
            let d = f.def
            drawText(s, d.name, 261, 84, f.boss ? "red" : "white", align: .center, shadow: "ink")
            bossBar(s, "AWAKE", Double(f.hp), Double(f.max), t, y: 93, x: 210, w: 102)
            var mood = f.sleep ? "sleep" : f.tele != nil ? "angry" : f.phase == 1 ? "smug" : "open"
            if f.hit > 0 { mood = "hurt" }
            KPArt.foe(s, f.boss, d, FOE_X, FOE_Y, t, mood, hit: f.hit > 0)
            if f.sleep { KPArt.drawZ(s, FOE_X + 18, FOE_Y - 28 - Int(t * 8) % 8, "white") }
            if let (atk, left) = f.tele {
                if Int(t * 8) % 2 == 1 { drawText(s, "!", FOE_X - 34, FOE_Y - 20, "red", scale: 2, outline: "ink") }
                drawText(s, KPData.attackNames[atk] ?? atk, 261, 108, "red", align: .center, shadow: "ink")
                let w = Int(96 * Swift.max(0, left) / Swift.max(1, 1.8 - Double(tierN) * 0.04))
                s.fillRect(col("red"), 213, 117, w, 2)
            } else if !f.sleep {
                let w = Int(96 * Swift.max(0, 1 - f.t / Swift.max(0.1, f.every)))
                s.fillRect(col("darkgray"), 213, 117, 96, 2)
                s.fillRect(col("peach"), 213, 117, w, 2)
            }
            drawText(s, d.taunt, 261, 187, "lavender", align: .center, shadow: nil)
        } else {
            drawShelf(s)
        }
        for sh in shots {
            var x = sh.x, y = sh.y
            var tx = Double(FOE_X), ty = Double(FOE_Y)
            if sh.power <= 0 { x = Double(FOE_X); y = Double(FOE_Y - 10); tx = Double(BX + BW / 2); ty = Double(BY - 10) }
            let px = x + (tx - x) * sh.p
            let py = y + (ty - y) * sh.p - sin(sh.p * .pi) * 30
            if sh.power > 0 {
                KPArt.drawZ(s, Int(px) - 1, Int(py) - 1, "white")
                s.circle(col("lavender"), Int(px) + 1, Int(py) + 1, 3, width: 1)
            } else {
                s.blit(sprite("kp_pillow"), Int(px) - 6, Int(py) - 6)
            }
        }
    }

    /// No rival: a moonlit window and the upgrades Poppy has collected.
    func drawShelf(_ s: Surface) {
        s.rect(col("black"), IRect(220, 88, 82, 54), radius: 3)
        let sky = lerpCol("night", theme.hue, 0.2)
        s.fillRect(sky, 222, 90, 78, 50)
        for i in 0 ..< 9 where (Int(t * 2) + i) % 4 != 0 { s.fillRect(col("white"), 226 + (i * 29) % 72, 94 + (i * 17) % 40, 1, 1) }
        s.circle(col("yellow"), 284, 104, 8)
        s.circle(sky, 288, 101, 7)
        s.fillRect(col("brown"), 260, 90, 2, 50)
        s.fillRect(col("brown"), 222, 114, 78, 2)
        drawText(s, "UPGRADES", 261, 148, "white", align: .center, shadow: nil)
        var x = 212, y = 158
        var any = false
        for u in KittenPile.pool {
            let l = up(u.id)
            if l == 0 { continue }
            any = true
            s.circle(col(u.color), x + 6, y + 6, 7)
            s.circle(col("ink"), x + 6, y + 6, 6)
            u.draw?(s, x + 6, y + 6, t)
            drawText(s, "\(l)", x + 10, y + 9, "white", shadow: "ink")
            x += 17
            if x > 300 { x = 212; y += 17 }
        }
        if !any {
            drawText(s, "BEAT A BOSS", 261, 162, "darkgray", align: .center, shadow: nil)
            drawText(s, "OR A BONUS!", 261, 172, "darkgray", align: .center, shadow: nil)
        }
    }

    func drawWarning(_ s: Surface) {
        guard let f = foe else { return }
        let d = KPData.bosses[f.id]
        for i in 0 ..< 2 {
            let y = 46 + i * 92
            s.fillRect(col("red"), 0, y, W, 12)
            let off = Int(t * 60) % 24
            var x = -24
            while x < W + 24 {
                s.polygon(col("black"), [(Double(x + off), Double(y)), (Double(x + off + 10), Double(y)), (Double(x + off + 4), Double(y + 12)),
                                         (Double(x + off - 6), Double(y + 12))])
                x += 24
            }
        }
        s.fillRect(rgba(12, 8, 24, 210), 0, 58, W, 80)
        if Int(t * 4) % 2 == 1 { drawText(s, "WARNING!", W / 2, 64, "red", scale: 3, align: .center, outline: "ink") }
        drawText(s, "A GRUMPY CAT APPROACHES: \(d.name)", W / 2, 92, "white", align: .center)
        drawText(s, "\"\(d.taunt)\"", W / 2, 106, "peach", align: .center)
        drawText(s, f.atk.prefix(3).map { KPData.attackNames[$0] ?? $0 }.joined(separator: ", "), W / 2, 120, "lavender", align: .center)
    }

    func drawIntro(_ s: Surface) {
        let k = st.k
        let appear = Swift.min(1, stateT * 5)
        let y = 40 + Int((1 - appear) * 40)
        let border = k == "boss" ? "red" : bonus ? "yellow" : theme.hue
        let goals = goalLines()
        let h = 70 + 10 * goals.count + 10 * st.tip.count + (st.mods.isEmpty ? 0 : 10)
        panel(s, IRect(34, y, 252, h), fill: "night", border: border)
        drawText(s, "STAGE \(stageN)", W / 2, y + 7, "yellow", scale: 2, align: .center, outline: "ink")
        drawText(s, "\(theme.name)  -  \(KPData.kindTitle[k] ?? "")", W / 2, y + 26, theme.acc, align: .center)
        var yy = y + 39
        for line in goals { drawText(s, line, W / 2, yy, "white", align: .center); yy += 10 }
        if !st.mods.isEmpty {
            drawText(s, st.mods.map { KPData.mods[$0] ?? $0 }.joined(separator: " + "), W / 2, yy, "pink", align: .center)
            yy += 10
        }
        for (i, tip) in st.tip.enumerated() {
            drawText(s, (i == 0 ? "NEW! " : "") + tip, W / 2, yy, Int(t * 4) % 2 == 1 ? "lime" : "mint", align: .center)
            yy += 10
        }
        // Poppy's line, with her face
        yy += 3
        s.fillRect(lerpCol("night", theme.hue, 0.25), 40, yy - 2, 240, 13)
        s.blit(sprite("kp_kit", 3, remap: KPArt.poppyRemap), 43, yy - 1)
        drawText(s, "\"\(quip)\"", 60, yy + 1, "cream", shadow: nil)
        yy += 15
        if missed {
            drawText(s, "TRY AGAIN!", W / 2, yy, "peach", align: .center)
        } else if stateT > 0.5 {
            drawText(s, "TURN: GO!", W / 2, yy, "lavender", align: .center, shadow: nil)
        }
    }

    func goalLines() -> [String] {
        let g = st.goal
        switch st.k {
        case "clear": return ["PUT \(g) KITTENS TO SLEEP"]
        case "chain": return ["MAKE A \(g) CHAIN", "(KITTENS TUMBLING INTO NEW GROUPS)"]
        case "trigger":
            return ["A \(g) CHAIN IS WAITING IN THE BED", tierN < 3 || missed ? "DROP THE PAIR ON THE GLOW!" : "FIND THE SPOT THAT SETS IT OFF!"]
        case "rescue": return ["TUCK IN ALL \(stars0) STAR KITTENS", "(MATCH THEM WITH THEIR COLOUR)"]
        case "pillow": return ["CLEAR EVERY PILLOW FROM THE BED", "(POP KITTENS NEXT TO THEM)"]
        case "storm": return ["SURVIVE \(st.lim) SECONDS OF PILLOW RAIN"]
        case "duel": return ["PILLOW FIGHT WITH \(foeName)!", "CHAINS PUT THEM TO SLEEP"]
        case "boss": return ["PUT \(foeName) TO SLEEP!", "BIG CHAINS HIT HARDEST"]
        case "snack": return ["\(st.lim) SEC: EVERY KITTEN = A FISH COIN", "TWIN PAIRS + PURR FEVER!"]
        default: return ["\(st.setups.count) DOMINO BEDS IN \(st.lim) SEC", "DROP THE PAIR ON THE GLOW!"]
        }
    }

    func drawTally(_ s: Surface) {
        let appear = Swift.min(1, stateT * 6)
        let y = 34 + Int((1 - appear) * 30)
        let k = st.k
        panel(s, IRect(48, y, 224, 26 + 12 * tally.count + 26), fill: "night", border: "yellow")
        let title = k == "boss" ? "BOSS ASLEEP!" : bonus ? "BONUS RESULTS" : "STAGE \(stageN) CLEAR!"
        drawText(s, title, W / 2, y + 8, "yellow", align: .center)
        var total = 0
        for (i, line) in tally.enumerated() {
            if i > tallyI { break }
            let yy = y + 24 + i * 12
            drawText(s, line.0, 60, yy, line.1 > 0 ? "lavender" : "darkgray", shadow: nil)
            drawText(s, line.1 > 0 ? "\(line.2)" : "-", 260, yy, line.1 > 0 ? "white" : "darkgray", align: .right)
            total += line.2
        }
        let yy = y + 28 + 12 * tally.count
        s.fillRect(col("lavender"), 60, yy - 2, 200, 1)
        drawText(s, "TOTAL", 60, yy + 2, "yellow")
        drawText(s, "\(total)", 260, yy + 2, "yellow", align: .right)
        if tallyI >= tally.count && tallyT > 0.6 {
            drawText(s, "TURN: NEXT BED", W / 2, yy + 16, Int(t * 3) % 2 == 1 ? "white" : "lavender", align: .center, shadow: nil)
        }
    }

    // ================================================================ carousel preview
    private static let PV = ["..3.4.", ".1314.", "213442", "221142"]

    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        let th = KPData.themes.isEmpty ? KPTheme(name: "", hue: "lavender", acc: "pink", style: 0) : KPData.themes[Int(t / 6) % KPData.themes.count]
        s.fill(lerpCol("black", th.hue, 0.18))
        for i in 0 ..< 12 where (Int(t * 2) + i) % 5 != 0 { s.fillRect(lerpCol("black", th.hue, 0.4), (i * 37 + 5) % w, (i * 23 + 3) % h, 1, 1) }
        let bx = w - 6 * 12 - 6, by = h - 4 * 12 - 4
        s.rect(col("brown"), IRect(bx - 3, by - 2, 6 * 12 + 6, 4 * 12 + 6), radius: 4)
        s.fillRect(lerpCol("night", th.hue, 0.22), bx, by, 72, 48)
        let ph = t.truncatingRemainder(dividingBy: 4.0)       // a pair falls, the gingers curl up, the rest tumble
        for (r, row) in PV.enumerated() {
            for (x, ch) in row.enumerated() where ch != "." {
                let code = Int(String(ch)) ?? 1
                let px = bx + x * 12
                var py = by + r * 12
                if code == 1 && ph > 2.0 {
                    let f = Swift.min(1, (ph - 2.0) / 0.6)
                    if f < 1 { KPArt.curl(s, px, py, 1, f) }
                    continue
                }
                if ph > 2.6 && code != 1 && r < 2 && (x == 1 || x == 2) {
                    let below = Array(PV[r + 1])[x]
                    py += below == "1" ? Swift.min(12, Int((ph - 2.6) * 60)) : 0
                }
                KPArt.kitten(s, px, py, code, ph > 2.0 ? 3 : 0, t)
            }
        }
        if ph < 2.0 {
            let fy = by - 24 + Int(Swift.min(1, ph / 1.6) * 24)
            KPArt.kitten(s, bx + 2 * 12, fy - 12, 1, 0, t)
            KPArt.kitten(s, bx + 2 * 12, fy, 1, 0, t)
        }
        if ph > 2.0 && ph < 3.4 { drawText(s, "2 CHAIN!", bx + 36, by - 10, rainbow(0, t), align: .center, shadow: nil, outline: "ink") }
        KPArt.poppy(s, 20, h - 3, t, ph > 2.0 && ph < 3.4 ? "cheer" : "idle")
    }
}
