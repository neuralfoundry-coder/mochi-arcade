// ALLEY HOP - a lane-crossing game (port of mochi_arcade/games/alley_hop.py).
// SUSHI, a calico cat, guides lost kittens home across a night town; picked-up kittens follow her exact hops a beat
// later. 200 stages from the exported campaign (AlleyHopData.swift), bosses in AlleyHopBoss.swift, art in AlleyHopArt.swift.
import Foundation

private let TOP = AH_TOP, CELL = AH_CELL, ROWS = AH_ROWS, COLS = AH_COLS
private let HOP = 0.14, KHOP = 0.13, KDELAY = 0.15, POUNCE_T = 0.27
private let LIFE_AT = [30000, 80000, 150000, 250000]     // then every 150000
private let DIRS: [String: (Int, Int)] = ["up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)]
private let HURTS: Set<String> = ["hit", "train"]

// ----------------------------------------------------------------------------- upgrade cards
let AH_UPGRADES: [Upgrade] = [
    Upgrade(id: "quick", name: "QUICK PAWS", desc: "FASTER|HOPS", color: "mint", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.fillRect(col("mint"), cx - 6 + i * 5 + Int(t * 20) % 5, cy - 3 + i, 3, 1) }
        s.blit(sprite("ah_kit", 0), cx - 5, cy - 4)
    }, max: 3),
    Upgrade(id: "pounce", name: "POUNCE", desc: "POUNCE: LEAP|OVER A LANE|FASTER EACH LV", color: "orange", draw: { s, cx, cy, t in
        let h = Int(abs(sin(t * 4)) * 6)
        s.line(col("orange"), cx - 8, cy + 5, cx, cy - 4 - h)
        s.line(col("orange"), cx, cy - 4 - h, cx + 8, cy + 5)
        s.fillRect(col("white"), cx - 2, cy - 6 - h, 5, 4)
    }, max: 3),
    Upgrade(id: "life", name: "NINE LIVES", desc: "+1 LIFE|RIGHT NOW", color: "hotpink", icon: "heart", max: 5),
    Upgrade(id: "nap", name: "CAT NAP", desc: "+8 SECONDS|ON EVERY|STAGE CLOCK", color: "sky", draw: { s, cx, cy, t in
        s.blit(sprite("ah_clock"), cx - 4, cy - 3)
        drawText(s, "Z", cx + 3, cy - 9 - Int(t * 3) % 3, "sky", shadow: nil)
    }, max: 3),
    Upgrade(id: "magnet", name: "FISH MAGNET", desc: "GRAB TREATS|NEXT TO YOU", color: "lavender", draw: { s, cx, cy, _ in
        s.fillRect(col("red"), cx - 6, cy - 6, 4, 10); s.fillRect(col("red"), cx + 3, cy - 6, 4, 10)
        s.fillRect(col("red"), cx - 6, cy + 1, 13, 4)
        s.fillRect(col("white"), cx - 6, cy - 6, 4, 2); s.fillRect(col("white"), cx + 3, cy - 6, 4, 2)
    }, max: 2),
    Upgrade(id: "bell", name: "GUARDIAN BELL", desc: "SAVES A|LOST KITTEN|EVERY STAGE", color: "yellow", draw: { s, cx, cy, t in
        s.blit(sprite("ah_bell"), cx - 4 + Int(sin(t * 9) * 1.5), cy - 4)
    }, max: 2),
    Upgrade(id: "swim", name: "SWIM PAWS", desc: "SURVIVE A|SPLASH OR FALL|EVERY STAGE", color: "teal", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.fillRect(col("sky"), cx - 7 + Int(sin(t * 4 + Double(i)) * 2), cy + 2 + i * 2, 14, 1) }
        s.blit(sprite("ah_kit", 1), cx - 5, cy - 7)
    }, max: 2),
    Upgrade(id: "box", name: "BOX ARMOR", desc: "BLOCKS ONE|HIT EVERY|STAGE", color: "peach", draw: { s, cx, cy, t in
        AHArt.box(s, cx - 8, cy - 8, 1, t)
    }, max: 2),
    Upgrade(id: "luck", name: "LUCKY CHARM", desc: "MORE TREATS|AND JACKPOTS", color: "red", draw: { s, cx, cy, t in
        s.circle(col("white"), cx, cy, 6)
        s.fillRect(col("black"), cx - 3, cy - 2, 1, 1); s.fillRect(col("black"), cx + 2, cy - 2, 1, 1)
        s.fillRect(col("red"), cx - 4, cy + 3, 9, 2)
        s.fillRect(col("yellow"), cx - 1, cy + 4, 2, 2)
        s.fillRect(col("white"), cx + 6, cy - 4 - Int(abs(sin(t * 5)) * 3), 2, 4)
    }, max: 3),
    Upgrade(id: "fever", name: "FEVER PURR", desc: "FEVER FILLS|FASTER, LASTS|LONGER", color: "pink", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { s.circle(col(rainbow(i, t)), cx - 4 + i * 4, cy + 1 - (i % 2) * 3, 2) }
    }, max: 3),
    Upgrade(id: "family", name: "BIG FAMILY", desc: "+50% FAMILY|BONUS PER|LEVEL", color: "lime", draw: { s, cx, cy, t in
        for i in 0 ..< 3 { AHArt.kitten(s, Double(cx - 8 + i * 8), Double(cy + 6 - (i % 2) * 2), i, t, "happy", 0, i) }
    }, max: 3),
]

// ----------------------------------------------------------------------------- objects
/// Sushi or a kitten: stands on a lane (row, lane-local x) or hops between two lanes.
class AHHopper {
    var row: Int
    var lx: Double
    var hopping = false
    var ht = 0.0, hd = HOP
    var fr: Int                 // row the hop started on
    var fx = 0.0                // world x at the start of the hop
    var tr: Int                 // target row
    var tx = 0.0                // target: world x (Sushi) / lane-local x (kittens: it rides with the lane)
    var track = false
    var kind = "hop"            // hop | pounce
    var face = "up"
    init(_ row: Int, _ lx: Double) { self.row = row; self.lx = lx; fr = row; tr = row }
    func p() -> Double { hopping ? min(1, ht / hd) : 0 }
}

final class AHKitten: AHHopper {
    let homeR: Int
    let homeX: Double
    let coat: Int
    let idx: Int
    var state = "wait"          // wait | line | home | lost
    var queue: [(t: Double, r: Int, lx: Double, kind: String)] = []
    var lostT = 0.0
    var flash = 0.0
    var carrier = false
    init(_ r: Int, _ x: Double, _ coat: Int, _ idx: Int) {
        homeR = r; homeX = x; self.coat = coat; self.idx = idx
        super.init(r, x)
    }
}

final class AHItemObj {
    let kind: String
    let row: Int
    let x: Double
    let carrier: Bool
    var alive = true
    var life = -1.0             // bonus snacks fade away
    init(_ kind: String, _ r: Int, _ x: Double, _ carrier: Bool) { self.kind = kind; row = r; self.x = x; self.carrier = carrier }
}

// ----------------------------------------------------------------------------- the game
final class AlleyHop: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD     HOP (ONE HOP PER PRESS)", "HOP     HOP FORWARD", "POUNCE  LEAP OVER A LANE (UPGRADE)"]
    static let helpSkip = 3

    override var music: String? { song() }
    override var buttons: [Action: String] { lv("pounce") > 0 ? [.a: "HOP", .b: "POUNCE"] : [.a: "HOP"] }
    override var buttonOrder: [Action] { [.a, .b] }
    override var fourWay: Bool { true }

    var lives: Int
    let tmul: Double
    var levels: [String: Int] = [:]
    var lifeI = 0
    var picksLeft = 0, pickTitle = "POWER UP!"
    var nextN: Int?
    // stage
    var n = 1
    var st: AHStage = AHData.stages[0]
    var tier = 0
    var theme: [String] = AHData.themes[0]
    var lanes: [AHLane] = []
    var lt = 0.0, pt = 0.0           // lane time (traffic clock), play time
    var boxes: [Int] = [], boxN: [Int] = []
    var kittens: [AHKitten] = []
    var line: [AHKitten] = []
    var need = 0, homeCount = 0
    var items: [AHItemObj] = []
    var boss: AHBoss?
    var mh: [[Int]] = []
    var wetCells: [Int: Double] = [:]    // row * 100 + col -> seconds (puddles a sweeper leaves behind)
    var freed: [(x: Double, y: Double, tx: Double, ty: Double, t: Double, coat: Int, box: Int)] = []
    var ghosts: [(x: Double, y: Double, t: Double, coat: Int)] = []
    var clock = 0.0, clockFull = 0.0
    var shield = 0, bells = 0, swims = 0
    var zoomT = 0.0, slowT = 0.0, pounceCd = 0.0, inv = 0.0, stun = 0.0
    var missed = false, lostAny = false, hurtBoss = false
    var stageCombo = 0, fishN = 0, goldN = 0, tripN = 0, bestFamily = 0
    var spawnT = 0.0, bumpCd = 0.0, homeWait = 0.0
    var death = "", deadX = 0.0, deadY = 0.0
    var tally: [(label: String, v: Int, shown: Double)] = []
    var tallyI = 0, tallyWait = 0.0
    var buf: (String, Bool)?
    var bufT = 0.0
    var wet = false
    var sushi = AHHopper(10, Double(AH_START_COL * AH_CELL + 8))
    var tripBest = 10
    var safeR = 10, safeX = 0.0
    var homeBox = -1
    var state = "intro"
    var stateT = 0.0, introLen = 2.6
    var bg = Surface(W, H)
    private var mask = [Int](repeating: 0, count: W * H)

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        tmul = SPEEDS[d] ?? 1
        super.init(app, info, opt)
        hype.comboTime = 3.0
        hype.comboY = 14
        let start = max(1, min(STAGES, optInt("stage", optInt("start", 1))))
        startStage(start)
        if start > 10 {          // starting from a checkpoint: catch up on some upgrades first
            picksLeft = min(8, (start - 1) / 10)
            pickTitle = "HEAD START!"
            state = "pick"
        }
    }

    // ---------------------------------------------------------------- helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }
    func factor(_ pts: Int) -> Int { pts * (10 + tier) / 10 }
    @discardableResult
    func scoreAt(_ pts: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int { add(factor(pts), x, y, c) }

    func song() -> String {
        if st.kind == "boss" { return "boss" }
        if st.kind == "bonus" { return "bonus" }
        let focus = AHData.themes[tier][10]
        return focus == "W" || focus == "G" ? "ah_canal" : "ah_alley"
    }

    func feverGain(_ x: Double) -> Double { x * (1 + 0.35 * Double(lv("fever"))) }

    func hopTime(_ kind: String = "hop") -> Double {
        var t = HOP * (1 - 0.1 * Double(lv("quick")))
        if zoomT > 0 { t *= 0.7 }
        if hype.feverOn { t *= 0.85 }
        if kind == "pounce" { t = POUNCE_T * (1 - 0.06 * Double(lv("quick"))) }
        return t
    }

    // ---------------------------------------------------------------- stages
    func startStage(_ num: Int) {
        n = num
        st = AHData.stages[num - 1]
        tier = st.tier
        theme = AHData.themes[tier]
        reached(num)
        lanes = st.lanes
        lt = 0; pt = 0
        boxes = st.boxes
        boxN = [Int](repeating: 0, count: boxes.count)
        kittens = st.kittens.enumerated().map { AHKitten($0.element.r, $0.element.x, $0.element.coat, $0.offset) }
        for k in kittens { k.carrier = lanes[k.homeR].carrier }
        line = []
        need = kittens.count
        homeCount = 0
        items = st.items.map { AHItemObj($0.kind, $0.r, $0.x, lanes[$0.r].carrier) }
        boss = st.boss.map { AHBoss(self, $0) }
        if let b = boss { need = b.hp }
        mh = st.manholes
        wetCells = [:]
        freed = []
        ghosts = []
        let nap = st.kind == "normal" ? 8 * lv("nap") : 3 * lv("nap")
        clock = st.clock + Double(nap)
        clockFull = clock
        shield = lv("box"); bells = lv("bell"); swims = lv("swim")
        zoomT = 0; slowT = 0; pounceCd = 0; inv = 0; stun = 0
        missed = false; lostAny = false; hurtBoss = false
        stageCombo = 0; fishN = 0; goldN = 0; tripN = 0; bestFamily = 0
        spawnT = 0; bumpCd = 0; homeWait = 0
        death = ""
        tally = []
        buf = nil; bufT = 0
        wet = false
        newSushi()
        if st.kind == "normal" {
            let luck = 0.03 + 0.02 * Double(lv("luck"))
            if hype.lucky(luck) { spawnItem("gold") }
            if hype.lucky(0.05 + 0.05 * Double(lv("luck"))) { spawnItem(["nip", "bell", "box", "clock"].randomElement()!) }
            if hype.lucky(0.01 + 0.01 * Double(lv("luck"))) { spawnItem("heart") }
        }
        state = "intro"
        stateT = 0
        introLen = boss != nil ? 3.2 : 2.6
        bg = makeBg()
        if hype.feverOn { hype.feverT = 0 }
        app.audio.music(song())
        app.audio.play(boss != nil ? "warning" : "stage")
        if boss != nil { hype.flash("red", 0.3) }
    }

    func newSushi() {
        sushi = AHHopper(10, Double(AH_START_COL * CELL + 8))
        sushi.face = "up"
        tripBest = 10
        safeR = 10; safeX = Double(AH_START_COL * CELL + 8)
        wet = false
        buf = nil
        homeBox = -1
    }

    func spawnItem(_ kind: String) {
        var cells: [(Int, Int)] = []
        for r in 1 ..< 10 where lanes[r].t == "safe" {
            for c in 0 ..< COLS where !lanes[r].bl.contains(c) && !itemAt(r, Double(c * CELL + 8)) && !kittenAt(r, Double(c * CELL + 8)) {
                cells.append((r, c))
            }
        }
        if let (r, c) = cells.randomElement() { items.append(AHItemObj(kind, r, Double(c * CELL + 8), false)) }
    }

    func itemAt(_ r: Int, _ x: Double) -> Bool { items.contains { $0.alive && $0.row == r && !$0.carrier && abs($0.x - x) < 4 } }
    func kittenAt(_ r: Int, _ x: Double) -> Bool { kittens.contains { $0.state == "wait" && $0.homeR == r && abs($0.homeX - x) < 4 } }

    // ---------------------------------------------------------------- lanes
    func shift(_ r: Int) -> Double { lanes[r].carrier ? ahShift(lanes[r], lt) : 0 }

    func onPlatform(_ r: Int, _ x: Double) -> Bool {
        let ln = lanes[r]
        if ln.t == "belt" { return true }
        let u = ahPmod(x + ahPad(ln) - ahShift(ln, lt), Double(ln.p))
        for (i, it) in ln.it.enumerated() where it.x + 2 <= u && u <= it.x + it.w - 2 && ahDive(ln, i, lt) < 2 { return true }
        return false
    }

    /// World x of something sitting on a carrier pattern at pattern x px.
    func patternWX(_ r: Int, _ px: Double) -> Double {
        let ln = lanes[r]
        return ahPmod(px + ahShift(ln, lt), Double(ln.p)) - ahPad(ln)
    }

    func hx(_ h: AHHopper) -> Double {
        if h.hopping {
            let end = h.track ? h.tx + shift(h.tr) : h.tx
            return h.fx + (end - h.fx) * h.p()
        }
        return h.lx + shift(h.row)
    }

    func hy(_ h: AHHopper) -> Double {
        if h.hopping { return Double(ahCY(h.fr)) + Double(ahCY(h.tr) - ahCY(h.fr)) * h.p() }
        return Double(ahCY(h.row))
    }

    func hrow(_ h: AHHopper) -> Int { h.hopping ? (h.p() >= 0.5 ? h.tr : h.fr) : h.row }
    func sushiX() -> Double { hx(sushi) }

    func kittenWX(_ k: AHKitten) -> Double {
        if k.state == "wait" { return k.carrier ? patternWX(k.homeR, k.homeX) : k.homeX }
        return hx(k)
    }

    func lidOpen(_ i: Int) -> Bool {
        if st.lids.count < 2 { return true }
        return ahPmod(lt + Double(i) * 1.3, st.lids[0]) < st.lids[1]
    }

    func lidWarn(_ i: Int) -> Bool {
        if st.lids.count < 2 { return false }
        let c = ahPmod(lt + Double(i) * 1.3, st.lids[0])
        return st.lids[1] - 0.9 < c && c < st.lids[1]
    }

    func puddle(_ r: Int, _ x: Double) -> Bool {
        let c = ahCol(x)
        return lanes[r].pd.contains(c) || wetCells[r * 100 + c] != nil
    }

    /// A sweeper leaves wet floor behind it.
    func wetCell(_ y: Double, _ x: Double) {
        let r = Int(floor((y - Double(TOP)) / Double(CELL)))
        let c = ahCol(x)
        if r >= 1 && r <= 9 && c >= 0 && c < COLS && (lanes[r].t == "safe" || lanes[r].t == "road") { wetCells[r * 100 + c] = 5.0 }
    }

    /// [(kind, screen x, w, i)] of the traffic in a road lane.
    func vehicles(_ r: Int) -> [(kind: String, X: Double, w: Double, i: Int)] {
        let ln = lanes[r]
        let sh = ahShift(ln, lt)
        return ln.it.enumerated().map { (kind: $0.element.kind, X: ahItemSX(ln, $0.element.x, sh), w: $0.element.w, i: $0.offset) }
    }

    /// What would hurt an entity at (row r, world x) right now? nil / hit / soft / train / squish.
    func danger(_ r: Int, _ x: Double, _ rad: Double = 5, _ airborne: Bool = false) -> String? {
        let ln = lanes[r]
        if !airborne {
            if ln.t == "road" {
                for v in vehicles(r) where v.X + 2 < x + rad && v.X + v.w - 2 > x - rad { return ln.soft ? "soft" : "hit" }
            } else if ln.t == "rail" {
                let tr = ahTrain(ln, lt)
                if let x0 = tr.x0, let x1 = tr.x1, x0 < x + rad && x1 > x - rad { return "train" }
            } else if ln.t == "fence" {
                if !ahGateOpen(ln, lt) { return "squish" }
            }
        }
        if let b = boss, b.hurts(x, Double(ahCY(r)), rad) { return "hit" }
        return nil
    }

    // ---------------------------------------------------------------- update
    override func tick(_ dt: Double) {
        stateT += dt
        switch state {
        case "intro":
            lt += dt * tmul * 0.5
            boss?.update(dt)
            if stateT > introLen || (stateT > 0.5 && app.input.hit(.a)) {
                state = "play"
                stateT = 0
            }
        case "play":
            play(dt)
        case "dead":
            lt += dt * tmul
            updateWorld(dt)
            if stateT > 1.3 {
                if lives <= 0 {
                    state = "over"
                    hype.banner("GAME OVER", "STAGE \(n)", color: "red", dur: 3.0)
                    app.audio.play("gameover")
                    endGame(false, "STAGE \(n)", delay: 2.5)
                } else {
                    newSushi()
                    inv = 1.2
                    state = "play"
                    stateT = 0
                }
            }
        case "bossdown":
            boss?.update(dt)
            updateWorld(dt)
            if stateT > 2.6 { stageClear() }
        case "clear":
            updateWorld(dt)
            if stateT > 1.6 { beginTally() }
        case "tally":
            updateTally(dt)
        case "pick":
            if picksLeft > 0 {
                picksLeft -= 1
                pickUpgrade(AH_UPGRADES, levels, title: pickTitle) { [unowned self] id in self.onPick(id) }
            } else if let nx = nextN {
                startStage(nx)
            } else {
                state = "intro"
                stateT = 0
            }
        default:
            break
        }
    }

    func onPick(_ id: String?) {
        guard let id = id else { return }
        levels[id] = lv(id) + 1
        if let u = AH_UPGRADES.first(where: { $0.id == id }) {
            hype.banner(u.name, "LEVEL \(levels[id]!)", color: u.color, dur: 1.2, scale: 1)
        }
        switch id {
        case "life": lives += 1; app.audio.play("extra")
        case "box": shield += 1
        case "bell": bells += 1
        case "swim": swims += 1
        case "fever": hype.feverTime = 8.0 + 1.5 * Double(levels[id]!)
        default: break
        }
    }

    func play(_ dt: Double) {
        let inp = app.input
        pt += dt
        let slow = slowT > 0 ? 0.35 : 1.0
        lt += dt * tmul * slow
        zoomT = max(0, zoomT - dt)
        slowT = max(0, slowT - dt)
        pounceCd = max(0, pounceCd - dt)
        inv = max(0, inv - dt)
        stun = max(0, stun - dt)
        bumpCd = max(0, bumpCd - dt)
        bufT = max(0, bufT - dt)
        if bufT <= 0 { buf = nil }
        if boss == nil {
            clock -= dt
            if clock <= 0 {
                if st.kind == "bonus" {
                    clock = 0
                    stageClear()
                    return
                }
                clock = max(20, clockFull * 0.5)
                die("time")
                return
            }
        }
        // input: one hop per press, the latest press during a hop is buffered
        var want: String?
        var pounce = false
        for (d, a) in [("up", Action.up), ("down", .down), ("left", .left), ("right", .right)] where inp.hit(a) { want = d }
        if inp.hit(.a) { want = "up" }
        if inp.hit(.b) && lv("pounce") > 0 {
            pounce = true
            want = want ?? sushi.face
        }
        if let w = want {
            buf = (w, pounce)
            bufT = 0.3
        }
        let s = sushi
        if homeBox < 0 {
            if s.hopping {
                s.ht += dt
                if s.ht >= s.hd {
                    sushiLand()
                    if state != "play" { return }
                }
            }
            if !s.hopping && homeBox < 0, let b = buf, stun <= 0 {
                buf = nil
                tryHop(b.0, b.1)
            }
        } else {
            homeWait += dt
            if line.isEmpty || homeWait > 8 {
                for k in line { loseKitten(k, "") }
                tripDone()
                if state != "play" { return }
            }
        }
        updateWorld(dt)
        if state != "play" { return }
        // Sushi's own dangers
        if homeBox < 0 && inv <= 0 {
            let r = hrow(s)
            let x = hx(s)
            let air = s.hopping && s.kind == "pounce" && s.p() > 0.12 && s.p() < 0.88
            if let cause = danger(r, x, 5, air) {
                die(cause)
                if state != "play" { return }
            }
            let lt0 = lanes[s.row].t
            if !s.hopping && (lt0 == "water" || lt0 == "gap") {
                if !onPlatform(s.row, x) || x < 2 || x > Double(W) - 2 {
                    die(lt0 == "water" ? "splash" : "fall")
                    if state != "play" { return }
                }
            }
            if !s.hopping && lanes[s.row].t == "belt" { s.lx = max(8, min(Double(W) - 8, x)) - shift(s.row) }
        }
        if boss != nil {
            updateBoss(dt)
        } else if st.kind == "bonus" && st.bonus == "feast" {
            updateFeast(dt)
        }
        checkLife()
    }

    /// Kittens, items, effects - also while Sushi is down or the stage is being cleared.
    func updateWorld(_ dt: Double) {
        for key in Array(wetCells.keys) {
            wetCells[key]! -= dt
            if wetCells[key]! <= 0 { wetCells[key] = nil }
        }
        for k in kittens {
            k.flash = max(0, k.flash - dt)
            if k.state == "lost" {
                k.lostT -= dt
                if k.lostT <= 0 {
                    k.state = "wait"
                    k.row = k.homeR; k.lx = k.homeX
                    k.hopping = false
                    parts.burst(kittenWX(k), Double(ahCY(k.homeR)), 6, ["white", "pink"], 30, 0.4)
                }
            }
        }
        for k in line { updateKitten(k, dt) }
        for i in ghosts.indices {
            ghosts[i].t += dt
            ghosts[i].y -= 22 * dt
        }
        ghosts.removeAll { $0.t >= 1.2 }
        for i in freed.indices {
            freed[i].t += dt
            if freed[i].t >= 1.0 && freed[i].box >= 0 {
                boxN[freed[i].box] += 1
                parts.burst(freed[i].tx, freed[i].ty, 10, ["pink", "white", "yellow"], 40, 0.5)
                app.audio.play("fruit")
                freed[i].box = -1
            }
        }
        freed.removeAll { $0.t >= 1.0 }
        for it in items where it.life > 0 {
            it.life -= dt
            if it.life <= 0 { it.alive = false }
        }
        items.removeAll { !$0.alive }
    }

    func updateKitten(_ k: AHKitten, _ dt: Double) {
        if k.hopping {
            k.ht += dt
            if k.ht >= k.hd {
                land(k)
                kittenLanded(k)
                if k.state != "line" { return }
            }
        }
        while !k.hopping, let q = k.queue.first, pt >= q.t {
            k.queue.removeFirst()
            if q.kind == "warp" {
                parts.burst(hx(k), Double(ahCY(k.row)), 6, ["gray", "lime"], 30, 0.3)
                k.row = q.r; k.lx = q.lx
                continue
            }
            k.face = q.r < k.row ? "up" : (q.r > k.row ? "down" : (q.lx > k.lx ? "right" : "left"))
            startHop(k, q.r, q.lx, true, q.kind, q.kind == "hop" ? KHOP * (1 - 0.1 * Double(lv("quick"))) : POUNCE_T)
        }
        if zoomT > 0 || k.flash > 0 || state != "play" { return }
        let r = hrow(k)
        let x = hx(k)
        let air = k.hopping && k.kind == "pounce" && k.p() > 0.12 && k.p() < 0.88
        var cause = danger(r, x, 4, air)
        if cause == nil && !k.hopping && (lanes[k.row].t == "water" || lanes[k.row].t == "gap") {
            if !onPlatform(k.row, x) || x < 2 || x > Double(W) - 2 { cause = "splash" }
        }
        if let c = cause { loseKitten(k, c) }
    }

    func startHop(_ h: AHHopper, _ tr: Int, _ tx: Double, _ track: Bool, _ kind: String, _ dur: Double) {
        h.fx = hx(h)
        h.fr = h.row
        h.tr = tr
        h.tx = tx
        h.track = track
        h.kind = kind
        h.hd = dur
        h.ht = 0
        h.hopping = true
    }

    func land(_ h: AHHopper) {
        let end = h.track ? h.tx + shift(h.tr) : h.tx
        h.hopping = false
        h.row = h.tr
        h.lx = h.track ? h.tx : end - shift(h.tr)
    }

    // ---------------------------------------------------------------- Sushi
    /// (ok, snapped x) for a hop into row tr at world x tx.
    func canEnter(_ tr: Int, _ tx0: Double) -> (Bool, Double) {
        var tx = tx0
        if tr < 0 || tr >= ROWS || tx < 4 || tx > Double(W) - 4 { return (false, tx) }
        let ln = lanes[tr]
        if tr == 0 {
            if boss != nil { return (false, tx) }
            for (i, c) in boxes.enumerated() {
                let bx = Double(c * CELL + 8)
                if abs(bx - tx) <= 9 && lidOpen(i) { return (true, bx) }
            }
            return (false, tx)
        }
        if !ln.carrier {
            let c = max(0, min(COLS - 1, ahCol(tx)))
            tx = Double(c * CELL + 8)
            if ln.bl.contains(c) { return (false, tx) }
            if ln.t == "fence" && (!ln.gc.contains(c) || !ahGateOpen(ln, lt)) { return (false, tx) }
        }
        return (true, tx)
    }

    @discardableResult
    func tryHop(_ d: String, _ pounce: Bool) -> Bool {
        let s = sushi
        let (dr, dc) = DIRS[d]!
        s.face = d
        let x = hx(s)
        let tries: [(Int, String)] = pounce && pounceCd <= 0 ? [(2, "pounce"), (1, "hop")] : [(1, "hop")]
        for (dist, kind) in tries {
            let tr = s.row + dr * dist
            let (ok, tx) = canEnter(tr, x + Double(dc * dist * CELL))
            if ok {
                if kind == "pounce" {
                    pounceCd = [4.0, 4.0, 3.0, 2.0][min(3, lv("pounce"))]
                    app.audio.play("powerup")
                } else {
                    app.audio.play(wet ? "move" : "jump")
                }
                let dur = hopTime(kind) * (wet && kind == "hop" ? 1.8 : 1.0)
                wet = false
                startHop(s, tr, tx, false, kind, dur)
                return true
            }
        }
        app.audio.play("tin")
        return false
    }

    func sushiLand() {
        let s = sushi
        land(s)
        let r = s.row
        let x = hx(s)
        for (ki, k) in line.enumerated() { k.queue.append((t: pt + Double(ki) * KDELAY, r: r, lx: s.lx, kind: s.kind)) }
        let ln = lanes[r]
        if r == 0 {
            reachHome(x)
            return
        }
        if (ln.t == "water" || ln.t == "gap") && (!onPlatform(r, x) || x < 2 || x > Double(W) - 2) {
            die(ln.t == "water" ? "splash" : "fall")
            return
        }
        if !ln.carrier { safeR = r; safeX = x }
        wet = (ln.t == "safe" || ln.t == "road" || ln.t == "start") && puddle(r, x)
        if wet {
            app.audio.play("bubble")
            parts.burst(x, Double(ahCY(r) + 4), 6, ["sky", "white"], 30, 0.3)
        }
        if r < tripBest {
            let steps = tripBest - r
            tripBest = r
            scoreAt(10 * steps)
            stageCombo = max(stageCombo, hype.hit(1, fever: feverGain(0.012)))
        }
        pickups(r, x)
        // manhole shortcut: the lower lid pops you out of the upper one
        for m in mh where m[0] == r && abs(Double(m[1] * CELL + 8) - x) < 4 {
            warp(m)
            break
        }
        if let b = boss, let br = b.bopRect() {
            let cyv = Double(ahCY(r))
            if br.0 <= x && x <= br.0 + br.2 && br.1 <= cyv && cyv <= br.1 + br.3 { bopBoss() }
        }
        if ln.t == "road" && !ln.soft {
            for v in vehicles(r) {
                let gap = min(abs(v.X - (x + 5)), abs(x - 5 - (v.X + v.w)))
                if gap < 5 {
                    scoreAt(50, x, Double(ahCY(r) - 12), "mint")
                    floats.add(x, Double(ahCY(r) - 20), "CLOSE!", "mint")
                    hype.hit(1, fever: feverGain(0.02))
                    break
                }
            }
        }
    }

    func warp(_ m: [Int]) {
        let s = sushi
        let r1 = m[0], c1 = m[1], r2 = m[2], c2 = m[3]
        let x1 = Double(c1 * CELL + 8), x2 = Double(c2 * CELL + 8)
        parts.burst(x1, Double(ahCY(r1)), 10, ["gray", "lime", "white"], 50, 0.4)
        s.row = r2; s.lx = x2
        for (ki, k) in line.enumerated() { k.queue.append((t: pt + Double(ki) * KDELAY + 0.01, r: r2, lx: x2, kind: "warp")) }
        parts.burst(x2, Double(ahCY(r2)), 12, ["gray", "lime", "white"], 60, 0.5)
        app.audio.play("pop")
        floats.add(x2, Double(ahCY(r2) - 14), "SHORTCUT!", "lime")
        if r2 < tripBest {
            scoreAt(10 * (tripBest - r2))
            tripBest = r2
        }
        safeR = r2; safeX = x2
        pickups(r2, x2)
    }

    func pickups(_ r: Int, _ x: Double) {
        let mag = lv("magnet")
        for it in items where it.alive {
            let ix = it.carrier ? patternWX(it.row, it.x) : it.x
            let dr = abs(it.row - r)
            let dx = abs(ix - x)
            let near = (dr == 0 && dx < 10) || (mag >= 1 && dr == 0 && dx < 26) || (mag >= 1 && dr == 1 && dx < 10) ||
                (mag >= 2 && dr == 1 && dx < 26)
            if near {
                it.alive = false
                collect(it, ix, Double(ahCY(it.row)))
            }
        }
        for k in kittens where k.state == "wait" && k.homeR == r && abs(kittenWX(k) - x) < 11 { pickKitten(k) }
    }

    func collect(_ it: AHItemObj, _ x: Double, _ y: Double) {
        let g = hype!
        let au = app.audio
        switch it.kind {
        case "fish":
            fishN += 1
            scoreAt(100 + g.comboBonus(5), x, y - 8)
            g.hit(1, fever: feverGain(0.03))
            au.play("eat")
        case "yarn":
            fishN += 1
            scoreAt(50 + g.comboBonus(5), x, y - 8, "pink")
            g.hit(2, fever: feverGain(0.03))
            au.play("fruit")
        case "gold":
            goldN += 1
            if st.kind == "bonus" {
                scoreAt(1500, x, y - 8, "orange")
                g.hit(3, fever: feverGain(0.05))
                au.play("coin")
                parts.burst(x, y, 14, ["yellow", "orange", "white"], 60, 0.6)
            } else {
                g.jackpot(factor(5000), sub: "GOLDEN FISH!")
            }
        case "clock":
            clock += 15
            g.banner("+15 SECONDS", color: "sky", dur: 1.0, scale: 1, sound: "powerup")
        case "nip":
            zoomT = 6.0
            g.banner("ZOOMIES!", "CATNIP POWER", dur: 1.4, rainbow: true, sound: "powerup")
            g.flash("lime", 0.2)
        case "bell":
            slowT = 5.0
            g.banner("TIME PAWS", "TRAFFIC SLOWS DOWN", color: "yellow", dur: 1.4, sound: "powerup")
        case "box":
            shield = min(3, shield + 1)
            g.banner("BOX ARMOR!", color: "peach", dur: 1.0, scale: 1, sound: "powerup")
        case "heart":
            lives += 1
            g.banner("1 UP!", color: "pink", dur: 1.2, sound: "extra")
            g.shower(12, "hearts")
        default:
            break
        }
        parts.burst(x, y, 8, ["yellow", "white", "pink"], 40, 0.4)
    }

    func pickKitten(_ k: AHKitten) {
        let s = sushi
        k.state = "line"
        k.row = s.row
        k.lx = s.lx
        k.hopping = false
        k.queue = []
        k.flash = 0
        line.append(k)
        let x = sushiX(), y = Double(ahCY(s.row))
        scoreAt(200, x, y - 10, "pink")
        stageCombo = max(stageCombo, hype.hit(2, fever: feverGain(0.04)))
        app.audio.play("bonus")
        floats.add(x, y - 20, "MEW!", "white")
        parts.burst(x, y, 8, ["pink", "white"], 40, 0.4)
    }

    func kittenLanded(_ k: AHKitten) {
        let r = k.row
        let x = hx(k)
        if r == 0 {
            deliver(k, x)
            return
        }
        let ln = lanes[r]
        if (ln.t == "water" || ln.t == "gap") && !onPlatform(r, x) { loseKitten(k, "splash") }
    }

    func nearestBox(_ x: Double) -> Int {
        var best = 0
        for j in 0 ..< boxes.count where abs(Double(boxes[j] * CELL + 8) - x) < abs(Double(boxes[best] * CELL + 8) - x) { best = j }
        return best
    }

    func deliver(_ k: AHKitten, _ x: Double) {
        k.state = "home"
        line.removeAll { $0 === k }
        boxN[nearestBox(x)] += 1
        homeCount += 1
        tripN += 1
        scoreAt(500, x, Double(TOP - 2 + 10), "pink")
        stageCombo = max(stageCombo, hype.hit(2, fever: feverGain(0.05)))
        app.audio.play(tripN < 3 ? "coin" : "levelup")
        parts.burst(x, Double(ahCY(0)), 12, ["pink", "hotpink", "white", "yellow"], 50, 0.6)
    }

    func loseKitten(_ k: AHKitten, _ cause: String) {
        if k.state != "line" { return }
        if !cause.isEmpty && bells > 0 {          // GUARDIAN BELL: the kitten is saved once
            bells -= 1
            k.flash = 1.5
            hype.banner("BELL SAVE!", color: "yellow", dur: 1.0, scale: 1, sound: "hold")
            parts.burst(hx(k), hy(k), 10, ["yellow", "white"], 40, 0.5)
            return
        }
        let x = hx(k), y = hy(k)
        line.removeAll { $0 === k }
        k.state = "lost"
        k.lostT = 1.6
        k.queue = []
        k.hopping = false
        if !cause.isEmpty {
            lostAny = true
            hype.breakCombo()
            app.audio.play(cause != "splash" ? "hurt" : "bubble")
            floats.add(x, y - 12, cause != "splash" ? "MEW..." : "SPLASH!", "pink")
            parts.burst(x, y, 10, cause == "splash" ? ["white", "pink", "sky"] : ["white", "pink"], 50, 0.5)
            ghosts.append((x: x, y: y, t: 0, coat: k.coat))
        }
    }

    func reachHome(_ x: Double) {
        homeBox = nearestBox(x)
        homeWait = 0
        tripN = 0
        app.audio.play("select")
        scoreAt(100, x, Double(TOP + 4), "white")
        parts.burst(x, Double(ahCY(0)), 8, ["yellow", "white"], 40, 0.4)
        if line.isEmpty { tripDone() }
    }

    /// Sushi waited in a box until her line was home (or lost). Pay the family bonus, go again.
    func tripDone() {
        let k = tripN
        let g = hype!
        if k >= 2 {
            let pts = factor(250 * k * (k - 1)) * (2 + lv("family")) / 2
            bestFamily = max(bestFamily, k)
            let x = Double(boxes[homeBox] * CELL + 8)
            if k >= 5 {
                g.banner("MEGA FAMILY!", "\(k) KITTENS AT ONCE  +\(pts * g.mult)", dur: 2.0, rainbow: true, sound: "fever")
                g.shower(30, "hearts")
                g.slowmo(0.4, 0.6)
                app.shake(3, 0.3)
            } else if k >= 3 {
                g.banner("FAMILY X\(k)!", "+\(pts * g.mult)", dur: 1.6, rainbow: true, sound: "combo")
                g.shower(14, "hearts")
            } else {
                g.banner("FAMILY X2", "+\(pts * g.mult)", color: "pink", dur: 1.2, scale: 1, sound: "combo")
            }
            add(pts)
            g.hit(k, fever: feverGain(0.06))
            parts.burst(x, Double(ahCY(0)), 20, ["pink", "hotpink", "yellow", "white"], 70, 0.8)
        }
        if k >= 1 { bestFamily = max(bestFamily, k) }
        tripN = 0
        if homeCount >= need && need > 0 {
            stageClear()
            return
        }
        newSushi()
        parts.burst(Double(AH_START_COL * CELL + 8), Double(ahCY(10)), 8, ["white", "yellow"], 30, 0.3)
    }

    func die(_ cause: String) {
        let g = hype!
        let au = app.audio
        let s = sushi
        let x = hx(s), y = hy(s)
        if cause == "squish" {          // a closing gate shoves Sushi back where she came from
            let r = hrow(s)
            let back = s.hopping && s.fr != r ? s.fr : min(ROWS - 1, r + 1)
            s.hopping = false
            s.row = back
            s.lx = Double(max(0, min(COLS - 1, ahCol(x))) * CELL + 8) - shift(back)
            stun = 0.35
            inv = 0.5
            g.breakCombo()
            au.play("tin")
            app.shake(2, 0.2)
            floats.add(x, y - 12, "BONK!", "orange")
            for (ki, k) in line.enumerated() { k.queue.append((t: pt + 0.1 + Double(ki) * KDELAY, r: s.row, lx: s.lx, kind: "hop")) }
            return
        }
        if HURTS.contains(cause) && zoomT > 0 {
            if bumpCd <= 0 {
                bumpCd = 0.4
                scoreAt(100, x, y - 10, "lime")
                floats.add(x, y - 18, "BONK!", "lime")
                au.play("brick")
                g.hit(1)
            }
            return
        }
        if (cause == "splash" || cause == "fall") && swims > 0 {
            swims -= 1
            au.play("bubble")
            g.banner("SWIM PAWS!", color: "teal", dur: 1.0, scale: 1)
            parts.burst(x, y, 12, ["sky", "white"], 50, 0.5)
            s.hopping = false
            s.row = safeR
            s.lx = safeX - shift(safeR)
            for k in line {
                k.hopping = false
                k.queue = []
                k.row = s.row; k.lx = s.lx
            }
            inv = 0.8
            return
        }
        if HURTS.contains(cause) && shield > 0 {
            shield -= 1
            inv = 1.2
            au.play("pop")
            g.banner("BOX ARMOR!", "SAVED YOU", color: "peach", dur: 1.0, scale: 1)
            parts.burst(x, y, 14, ["brown", "peach", "cream"], 60, 0.6)
            app.shake(2, 0.2)
            return
        }
        if cause == "soft" {
            stun = 0.8
            inv = 1.4
            g.breakCombo()
            au.play("hurt")
            floats.add(x, y - 12, "BUMP!", "pink")
            for k in line { loseKitten(k, "") }
            return
        }
        // a real miss
        lives -= 1
        missed = true
        if boss != nil { hurtBoss = true }
        g.breakCombo()
        death = cause
        deadX = x; deadY = y
        state = "dead"
        stateT = 0
        for k in line { loseKitten(k, "") }
        if cause == "splash" || cause == "fall" {
            au.play("bubble")
            parts.burst(x, y, 16, cause == "splash" ? ["sky", "white", "blue"] : ["gray", "white"], 60, 0.6)
        } else {
            au.play("hurt")
            parts.burst(x, y, 16, ["white", "orange", "choco"], 70, 0.6)
        }
        app.shake(cause == "train" || cause == "hit" ? 4 : 2, 0.35)
        let msg = ["hit": "BONK!", "splash": "SPLASH!", "fall": "WHOOPS!", "train": "TOOT TOOT!", "time": "SUNRISE!"][cause] ?? "OUCH!"
        if lives > 0 {
            g.banner(msg, "\(lives) LEFT", color: "pink", dur: 1.2, scale: 1)
        } else {
            au.play("die")
        }
    }

    func checkLife() {
        let i = lifeI
        let target = i < LIFE_AT.count ? LIFE_AT[i] : LIFE_AT[LIFE_AT.count - 1] + 150000 * (i - LIFE_AT.count + 1)
        if score >= target {
            lifeI += 1
            lives += 1
            hype.banner("BONUS LIFE!", "\(target) POINTS", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    // ---------------------------------------------------------------- boss / bonus
    func updateBoss(_ dt: Double) { boss?.update(dt * (slowT > 0 ? 0.5 : 1.0)) }

    func bopBoss() {
        guard let b = boss else { return }
        let g = hype!
        let x = b.hx, y = b.hy
        b.hit()
        g.hitstop(0.08)
        g.flash("white", 0.15)
        app.shake(4, 0.3)
        app.audio.play("explode")
        scoreAt(2000, x, y - 16, "orange")
        stageCombo = max(stageCombo, g.hit(3, fever: feverGain(0.08)))
        parts.burst(x, y, 20, ["yellow", "white", "orange"], 80, 0.6)
        // a kitten pops free and runs to a box
        let i = freed.count + homeCount
        let box = i % boxes.count
        freed.append((x: x, y: y, tx: Double(boxes[box] * CELL + 8), ty: Double(ahCY(0)), t: 0, coat: i % 6, box: box))
        homeCount += 1
        floats.add(x, y - 24, "FREE!", "pink")
        if b.hp <= 0 { bossDefeated() }
    }

    func bossDefeated() {
        let g = hype!
        app.audio.play("bossdown")
        g.banner("BOSS DOWN!", boss?.name, dur: 2.4, rainbow: true, scale: 2)
        g.flash("white", 0.4)
        g.shower(90, "confetti")
        g.shower(30, "hearts")
        g.slowmo(0.3, 1.4)
        app.shake(6, 0.6)
        scoreAt(15000, Double(W) / 2, 80)
        state = "bossdown"
        stateT = 0
        app.audio.music(nil)
    }

    /// FISH FEAST: snacks keep appearing on the belts and sidewalks.
    func updateFeast(_ dt: Double) {
        spawnT -= dt
        let alive = items.filter { $0.alive }.count
        if spawnT <= 0 && alive < 16 {
            spawnT = 0.3
            let r = Int.random(in: 1 ... 10)
            let ln = lanes[r]
            let kind = hype.lucky(0.05 + 0.02 * Double(lv("luck"))) ? "gold" : ["fish", "fish", "yarn"].randomElement()!
            let it: AHItemObj
            if ln.t == "belt" {
                let ix = Double(Int.random(in: Int(ahPad(ln)) ... Int(ahPad(ln)) + W - 16))
                it = AHItemObj(kind, r, ahPmod(ix - ahShift(ln, lt), Double(ln.p)), true)
            } else if ln.t == "safe" || ln.t == "start" {
                it = AHItemObj(kind, r, Double(Int.random(in: 0 ..< COLS) * CELL + 8), false)
            } else {
                return
            }
            it.life = 7.0
            items.append(it)
        }
    }

    // ---------------------------------------------------------------- clear / tally
    func stageClear() {
        if state == "clear" || state == "tally" { return }
        state = "clear"
        stateT = 0
        let g = hype!
        if g.feverOn { g.feverT = 0 }
        g.slowmo(0.4, 0.8)
        app.audio.play("win")
        app.audio.music(nil)
        if st.kind == "normal" {
            g.banner("ALL HOME!", "EVERY KITTEN IS SAFE", color: "mint", dur: 1.5)
            g.shower(30, "confetti")
        } else if st.kind == "bonus" {
            g.banner(clock <= 0 ? "TIME UP!" : "ALL DONE!", color: "yellow", dur: 1.4)
        }
    }

    func beginTally() {
        var rows: [(String, Int)] = []
        if st.kind == "normal" {
            rows.append(("STAGE CLEAR", factor(1000)))
            rows.append(("TIME LEFT \(Int(clock))", factor(Int(clock) * 40)))
            rows.append(("NO KITTEN LOST", lostAny ? 0 : factor(2000)))
        } else if st.kind == "boss" {
            rows.append(("BOSS BONUS", factor(10000 + 2000 * tier)))
            rows.append(("NO DAMAGE", hurtBoss ? 0 : factor(8000)))
        } else if st.bonus == "feast" {
            rows.append(("TREATS X\(fishN)", factor(fishN * 60)))
            rows.append(("GOLDEN X\(goldN)", factor(goldN * 600)))
        } else {
            rows.append(("KITTENS HOME X\(homeCount)", factor(homeCount * 300)))
            rows.append(("BIGGEST FAMILY \(bestFamily)", factor(bestFamily * 800)))
            rows.append(("EVERYONE HOME", homeCount >= need ? factor(5000) : 0))
        }
        rows.append(("BEST COMBO \(stageCombo)", factor(stageCombo * 30)))
        if st.kind != "bonus" { rows.append(("NO MISS", missed ? 0 : factor(3000))) }
        tally = rows.map { (label: $0.0, v: $0.1, shown: 0.0) }
        tallyI = 0
        tallyWait = 0
        state = "tally"
        stateT = 0
        if st.kind == "normal" && !missed && !lostAny {
            hype.banner("PURRFECT!", "NOBODY GOT HURT", dur: 1.8, rainbow: true, sound: "fever")
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
        checkLife()
    }

    func finishStage() {
        if n >= STAGES {
            state = "over"
            hype.banner("ALL CLEAR!!", "EVERY KITTEN IN TOWN IS HOME", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            hype.shower(40, "hearts")
            endGame(true, "ALL 200 STAGES!", delay: 4.5)
            return
        }
        nextN = n + 1
        if st.kind == "boss" || st.kind == "bonus" {
            picksLeft = 1
            pickTitle = st.kind == "boss" ? "BOSS BONUS!" : "TREAT TIME!"
            state = "pick"
        } else {
            startStage(n + 1)
        }
    }

    // ---------------------------------------------------------------- drawing
    func makeBg() -> Surface {
        let th = theme
        let s = Surface(W, H, fill: col("black"))
        let focus = th[10]
        for r in 0 ..< ROWS {
            let ln = lanes[r]
            let y0 = TOP + r * CELL
            switch ln.t {
            case "home":
                s.fillRect(col(th[8]), 0, y0, W, CELL)
                var yy = 0
                while yy < CELL {
                    let off = (yy / 4) % 2 == 0 ? 0 : 8
                    s.fillRect(col("black"), 0, y0 + yy, W, 1)
                    var xx = off
                    while xx < W { s.fillRect(col("black"), xx, y0 + yy, 1, 4); xx += 16 }
                    yy += 4
                }
                s.fillRect(col(th[9]), 0, y0 + CELL - 2, W, 2)
            case "safe", "start":
                drawGround(s, y0, th, focus, r)
            case "road":
                s.fillRect(col(th[3]), 0, y0, W, CELL)
                if lanes[r - 1].t == "road" {
                    var xx = 0
                    while xx < W { s.fillRect(col(th[4]), xx + 2, y0, 8, 1); xx += 16 }
                } else {
                    s.fillRect(col("gray"), 0, y0, W, 1)
                }
                if lanes[r + 1].t != "road" { s.fillRect(col("gray"), 0, y0 + CELL - 1, W, 1) }
                var xx = r * 7 % 13
                while xx < W { s.fillRect(col("black"), xx, y0 + 5 + (xx / 23) % 7, 1, 1); xx += 23 }
            case "water":
                s.fillRect(col(th[5]), 0, y0, W, CELL)
                if lanes[r - 1].t != "water" { s.fillRect(col("choco"), 0, y0, W, 2) }
                if lanes[r + 1].t != "water" { s.fillRect(col("choco"), 0, y0 + CELL - 1, W, 1) }
            case "gap":
                s.fillRect(col(th[7]), 0, y0, W, CELL)
                for i in 0 ..< 12 {
                    let lx = (i * 53 + r * 29) % W
                    let ly = y0 + 4 + (i * 7 + r) % 10
                    s.fillRect(col(i % 3 != 0 ? "yellow" : "lavender"), lx, ly, 1, 1)
                }
                s.fillRect(col("black"), 0, y0, W, 1)
                s.fillRect(col("gray"), 0, y0 + 2, W, 1)
            case "rail":
                s.fillRect(col("darkgray"), 0, y0, W, CELL)
                var xx = 0
                while xx < W { s.fillRect(col("brown"), xx, y0 + 2, 3, 12); xx += 7 }
                s.fillRect(col("gray"), 0, y0 + 4, W, 1)
                s.fillRect(col("gray"), 0, y0 + 11, W, 1)
            case "fence":
                drawGround(s, y0, th, focus, r)
                for c in 0 ..< COLS where !ln.gc.contains(c) {
                    let x = c * CELL
                    s.fillRect(col("black"), x, y0 + 2, CELL, 13)
                    s.fillRect(col("choco"), x, y0 + 4, CELL, 2)
                    s.fillRect(col("choco"), x, y0 + 10, CELL, 2)
                    for px in [x + 1, x + 6, x + 11] {
                        s.fillRect(col("brown"), px, y0 + 2, 4, 13)
                        s.fillRect(col("peach"), px, y0 + 2, 4, 1)
                    }
                }
            case "belt":
                s.fillRect(col("darkgray"), 0, y0, W, CELL)
                s.fillRect(col("gray"), 0, y0 + 1, W, 1)
                s.fillRect(col("gray"), 0, y0 + CELL - 2, W, 1)
            default:
                break
            }
            for c in ln.bl { AHArt.block(s, c * CELL, y0, focus != "G" ? (c + r + n) % 4 : (c % 2 == 1 ? 0 : 2), 0) }
        }
        for m in mh {
            AHArt.manhole(s, m[1] * CELL, TOP + m[0] * CELL, 0)
            let x = m[3] * CELL, y0 = TOP + m[2] * CELL
            s.ellipse(col("black"), x + 1, y0 + 4, 14, 10)
            s.ellipse(col("lime"), x + 3, y0 + 6, 10, 6, width: 1)
        }
        if st.dark {
            for lamp in st.lamps {
                let lx = Int(lamp[0]), ly = Int(lamp[1])
                s.fillRect(col("black"), lx - 1, ly - 2, 3, 12)
                s.fillRect(col("gray"), lx, ly - 1, 1, 10)
            }
        }
        return s
    }

    func drawGround(_ s: Surface, _ y0: Int, _ th: [String], _ focus: String, _ r: Int) {
        s.fillRect(col(th[1]), 0, y0, W, CELL)
        let c2 = col(th[2])
        if focus == "G" {          // roof tiles
            for yy in [y0 + 5, y0 + 11] {
                s.fillRect(c2, 0, yy, W, 1)
                var xx = (yy / 6) % 2 * 4
                while xx < W { s.fillRect(c2, xx, yy - 4, 1, 4); xx += 8 }
            }
        } else if focus == "W" {   // dock planks
            for yy in [y0 + 4, y0 + 9, y0 + 14] { s.fillRect(c2, 0, yy, W, 1) }
            var xx = (r * 11) % 40
            while xx < W { s.fillRect(c2, xx, y0 + 4, 1, 10); xx += 40 }
        } else if focus == "T" || focus == "F" {   // cobbles
            var yy = y0 + 2
            while yy < y0 + CELL {
                var xx = (yy / 5) % 2 * 3
                while xx < W { s.fillRect(c2, xx, yy, 2, 1); xx += 6 }
                yy += 5
            }
        } else {                   // sidewalk slabs
            var xx = 0
            while xx < W { s.fillRect(c2, xx, y0, 1, CELL); xx += 16 }
            s.fillRect(c2, 0, y0 + 8, W, 1)
        }
        let acc = col(th[9])
        for i in 0 ..< 3 { s.fillRect(acc, (r * 37 + i * 101 + n * 13) % W, y0 + 3 + i * 4, 2, 1) }
    }

    override func render(_ s: Surface) {
        let t = self.t
        s.blit(bg, 0, 0)
        let th = theme
        // animated lane bits + traffic / floaters
        for r in 0 ..< ROWS {
            let ln = lanes[r]
            let y0 = TOP + r * CELL
            if ln.t == "water" {
                for i in 0 ..< 10 {
                    let wx = Int(ahPmod(Double(i * 37 + r * 11) + ahShift(ln, lt) * 0.5, Double(W + 20))) - 10
                    s.fillRect(col(th[6]), wx, y0 + 5 + (i * 5) % 8, 5, 1)
                }
            } else if ln.t == "belt" {
                let off = Int(ahPmod(ahShift(ln, lt), 16))
                let d = ln.v > 0 ? 1 : -1
                var xx = -16
                while xx < W + 16 {
                    let x = xx + off
                    s.polygon(col("gray"), [(Double(x), Double(y0 + 5)), (Double(x + 3 * d), Double(y0 + 8)), (Double(x), Double(y0 + 11))])
                    xx += 16
                }
            } else if ln.t == "gap" && ln.sw == 0 {
                let off = Int(ahPmod(ahShift(ln, lt), 12))
                var xx = -12
                while xx < W + 12 { s.fillRect(col("white"), xx + off, y0 + 2, 1, 1); xx += 12 }
            }
            for c in ln.pd { AHArt.puddle(s, c * CELL, y0, t) }
            if ["road", "water", "gap", "belt"].contains(ln.t) {
                let sh = ahShift(ln, lt)
                var d = ln.v >= 0 ? 1 : -1
                if ln.sw != 0 { d = cos(ln.om * lt + ln.ph) >= 0 ? 1 : -1 }
                for (i, it) in ln.it.enumerated() {
                    let X = ahItemSX(ln, it.x, sh)
                    if X > Double(W + 2) || X + it.w < -2 { continue }
                    let Xi = Int(X), w = Int(it.w)
                    if AHArt.traffic.contains(it.kind) {
                        AHArt.drawTraffic(s, it.kind, Xi, y0, d, t, i + r)
                    } else if it.kind == "crate" {
                        AHArt.crate(s, Xi, y0, w, t)
                    } else if it.kind == "duck" {
                        AHArt.ducks(s, Xi, y0, w, d, t, ["up", "tell", "down"][ahDive(ln, i, lt)])
                    } else if it.kind == "fish" {
                        AHArt.fish(s, Xi, y0, w, d, t, ["up", "tell", "down"][ahDive(ln, i, lt)])
                    } else if it.kind == "sheet" {
                        AHArt.sheet(s, Xi, y0, w, t, i + r)
                    } else if it.kind == "tray" {
                        AHArt.tray(s, Xi, y0, t, i)
                    }
                }
            } else if ln.t == "fence" {
                let opn = ahGateOpen(ln, lt), warn = ahGateWarn(ln, lt)
                for c in ln.gc { AHArt.gate(s, c * CELL, y0, t, opn, warn) }
            } else if ln.t == "rail" {
                let warn = ahTrain(ln, lt).warn
                AHArt.signal(s, 2, y0, t, warn)
                AHArt.signal(s, W - 8, y0, t, warn)
            }
        }
        for (key, _) in wetCells { AHArt.puddle(s, (key % 100) * CELL, TOP + (key / 100) * CELL, t) }
        // boxes
        for (i, c) in boxes.enumerated() {
            let closed = !lidOpen(i) || boss != nil
            let glow = !line.isEmpty && !closed && Int(t * 3) % 2 == 0
            AHArt.box(s, c * CELL, TOP, boxN[i], t, closed: closed, warn: lidWarn(i), glow: glow)
        }
        // treats
        for it in items where it.alive && !(it.life > 0 && it.life < 1.5 && Int(t * 10) % 2 == 1) {
            let x = it.carrier ? patternWX(it.row, it.x) : it.x
            if x > -8 && x < Double(W + 8) { AHArt.item(s, it.kind, x, Double(ahCY(it.row)), t) }
        }
        // waiting kittens
        for k in kittens where k.state == "wait" {
            let x = kittenWX(k)
            if x > -8 && x < Double(W + 8) {
                let mood = !line.isEmpty && abs(k.homeR - sushi.row) <= 1 ? "wow" : ""
                AHArt.kitten(s, x, Double(ahCY(k.homeR) + 6), k.coat, t, mood, 0, k.idx)
                if Int(t * 2 + Double(k.idx)) % 4 == 0 { drawText(s, "?", Int(x) + 4, ahCY(k.homeR) - 12, "white", shadow: "black") }
            }
        }
        boss?.drawTells(s, t)
        // the line of kittens, then Sushi
        let sRest = !sushi.hopping
        let huddle = [-7, 7, -11, 11, -4, 4, -9, 9]
        for i in stride(from: line.count - 1, through: 0, by: -1) {
            let k = line[i]
            var x = hx(k), y = hy(k)
            if !k.hopping && sRest && k.row == sushi.row && abs(x - sushiX()) < 3 {
                x += Double(huddle[i % 8])          // huddle around mama
                y += 1
            }
            AHArt.kitten(s, x, y + 6, k.coat, t, homeBox >= 0 ? "happy" : "", k.p(), k.idx, flash: k.flash > 0)
        }
        if state != "dead" || stateT < 0.05 { drawSushi(s, t) } else { drawDeath(s, t) }
        // trains go over everything on the ground
        for r in 0 ..< ROWS where lanes[r].t == "rail" {
            let ln = lanes[r]
            let tr = ahTrain(ln, lt)
            if let x0 = tr.x0, let x1 = tr.x1, x1 > -4 && x0 < Double(W + 4) {
                let d = ln.tr[5] > 0 ? 1 : -1
                AHArt.train(s, d > 0 ? x1 : x0, TOP + r * CELL, ln.tr[2], d, t)
            }
        }
        if let b = boss {
            b.draw(s, t)
            b.drawShots(s, t)
        }
        for f in freed {
            let p = min(1, f.t)
            let x = f.x + (f.tx - f.x) * p
            let y = f.y + (f.ty - f.y) * p - sin(Double.pi * p) * 40
            AHArt.kitten(s, x, y + 6, f.coat, t, "happy", 0, f.coat)
        }
        for g in ghosts where Int(g.t * 12) % 2 == 0 { AHArt.kitten(s, g.x, g.y + 6, g.coat, t, "wow") }
        parts.draw(s)
        if st.dark { drawDark(s, t) }
        if st.rain {
            for i in 0 ..< 40 {
                let rx = Int(ahPmod(Double(i * 37) + t * 60, Double(W + 20))) - 10
                let ry = Int(ahPmod(Double(i * 53) + t * 220, Double(H + 20))) - 10
                s.fillRect(col("sky"), rx, ry, 1, 3)
            }
        }
        floats.draw(s)
        drawHud(s, t)
        if state == "intro" { drawIntro(s, t) } else if state == "tally" { drawTally(s, t) }
    }

    func drawSushi(_ s: Surface, _ t: Double) {
        let sh = sushi
        if homeBox >= 0 {
            let x = boxes[homeBox] * CELL
            let bob = Int(abs(sin(t * 6)) * 2)
            s.blit(sprite("ah_sushi", 5), x, TOP - 2 - bob)
            return
        }
        let x = hx(sh), y = hy(sh)
        var mood = stun > 0 ? "hurt" : ""
        if state == "clear" { mood = "happy" }
        if zoomT > 0 {
            for i in 1 ..< 4 { s.fillRect(col(rainbow(i, t)), Int(x) - 6 + i * 3, Int(y) + 4 + i % 2, 2, 2) }
        }
        if shield > 0 && Int(t * 3) % 3 == 0 { s.rect(col("peach"), IRect(Int(x) - 9, Int(y) - 10, 18, 19), width: 1, radius: 3) }
        AHArt.sushi(s, Int(x) - 8, Int(y) - 9, t, sh.face, mood, sh.p(), flash: inv > 0)
        if wet && Int(t * 6) % 2 == 1 {
            s.fillRect(col("sky"), Int(x) - 6, Int(y) - 10, 1, 2)
            s.fillRect(col("sky"), Int(x) + 6, Int(y) - 8, 1, 2)
        }
        if stun > 0 {
            for i in 0 ..< 3 {
                let a = t * 8 + Double(i) * 2.1
                s.fillRect(col("yellow"), Int(x) + Int(cos(a) * 7), Int(y) - 12 + Int(sin(a) * 2), 1, 1)
            }
        }
    }

    func drawDeath(_ s: Surface, _ t: Double) {
        let x = Int(deadX), y = Int(deadY)
        let p = min(1, stateT / 1.0)
        if death == "splash" || death == "fall" {
            if death == "splash" {
                for i in 0 ..< 3 {
                    let rr = Int(4 + p * 14 + Double(i * 4))
                    s.ellipse(col(i == 0 ? "white" : "sky"), x - rr, y + 2 - rr / 4, rr * 2, rr / 2 + 2, width: 1)
                }
                if p < 0.4 { AHArt.sushi(s, x - 8, y - 9 + Int(p * 20), t, "down", "hurt") }
            } else if p < 0.8 {
                let k = max(1, Int(16 * (1 - p)))
                s.blit(AHArt.scaled(sprite("ah_sushi", 6), k, k), x - k / 2, y - k / 2 + Int(p * 10))
            }
            return
        }
        let jump = Int(sin(Double.pi * min(1, p * 1.4)) * 18)
        AHArt.sushi(s, x - 8, y - 9 - jump, t, "down", "hurt")
        for i in 0 ..< 4 {
            let a = t * 9 + Double(i) * 1.6
            s.fillRect(col("yellow"), x + Int(cos(a) * 10), y - 16 - jump + Int(sin(a) * 3), 2, 2)
        }
    }

    func drawDark(_ s: Surface, _ t: Double) {
        var lights: [(Int, Int, Int)] = []
        func lampOn(_ ph: Double) -> Bool { !(ahPmod(t * 0.9 + ph, 4.0) > 3.3 && Int(t * 15) % 2 == 0) }
        for lamp in st.lamps where lampOn(lamp[3]) { lights.append((Int(lamp[0]), Int(lamp[1]) + 6, Int(lamp[2]))) }
        if homeBox < 0 { lights.append((Int(sushiX()), Int(hy(sushi)), 30)) }
        for k in line { lights.append((Int(hx(k)), Int(hy(k)), 12)) }
        var heads: [(Int, Int)] = []
        for r in 0 ..< ROWS {
            let ln = lanes[r]
            if ln.t == "road" {
                let d = ln.v >= 0 ? 1 : -1
                for v in vehicles(r) where v.X > -50 && v.X < Double(W + 50) {
                    lights.append((Int(AHArt.headlight(v.kind, v.X, d)), ahCY(r), 14))
                    heads.append((Int(d > 0 ? v.X + v.w - 1 : v.X), ahCY(r)))
                }
            } else if ln.t == "rail" {
                let tr = ahTrain(ln, lt)
                if let x0 = tr.x0, let x1 = tr.x1 {
                    let fx = ln.tr[5] > 0 ? x1 + 10 : x0 - 10
                    lights.append((Int(fx), ahCY(r), 26))
                }
            }
        }
        if let b = boss, b.state != "dead" { lights.append((Int(b.x), Int(b.y), 24)) }
        // banded light pools subtracted from the darkness (same formula as the desktop light sprites)
        for i in 0 ..< mask.count { mask[i] = 175 }
        for (lx, ly, rad) in lights {
            let r2 = rad * rad
            for yy in 0 ..< rad * 2 {
                let py = ly - rad + yy
                if py < 0 || py >= H { continue }
                let dy = yy - rad
                for xx in 0 ..< rad * 2 {
                    let px = lx - rad + xx
                    if px < 0 || px >= W { continue }
                    let dx = xx - rad
                    let a = ahLightAlpha(dx * dx + dy * dy, r2)
                    if a > 0 { mask[py * W + px] = max(0, mask[py * W + px] - a) }
                }
            }
        }
        for i in 0 ..< mask.count where mask[i] > 0 { s.put(i % W, i / W, rgba(8, 6, 20, mask[i])) }
        for (x, y) in heads { s.fillRect(col("yellow"), x, y - 1, 1, 2) }
        for lamp in st.lamps where lampOn(lamp[3]) { s.fillRect(col("yellow"), Int(lamp[0]) - 1, Int(lamp[1]) - 3, 3, 2) }
    }

    func drawHud(_ s: Surface, _ t: Double) {
        s.fillRect(col("black"), 0, 0, W, TOP)
        drawText(s, String(format: "%07d", score), 3, 3, "white", shadow: nil)
        if let b = boss, b.state != "dead" {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: 0, x: 50, w: 200)
        } else {
            drawText(s, "HI " + String(format: "%07d", max(best, score)), 52, 3, "gray", shadow: nil)
            drawText(s, "STAGE \(n)", 196, 3, "yellow", align: .center, shadow: nil)
        }
        hearts(s, W - 50, 2, lives)
        // bottom bar: kittens, clock, power-ups, fever
        let y = H - 12
        s.fillRect(col("black"), 0, y, W, 12)
        var x = 3
        if st.kind == "bonus" && st.bonus == "feast" {
            s.blit(sprite("ah_fish"), x, y + 2)
            drawText(s, "X\(fishN)", x + 12, y + 3, "sky", shadow: nil)
            x += 40
        } else {
            let show = min(need, 12)
            for i in 0 ..< show {
                let kx = x + i * 9
                if i < homeCount {
                    let c = col(["orange", "gray", "darkgray", "cream", "white", "peach"][i % 6])
                    s.fillRect(c, kx, y + 4, 7, 5)
                    s.fillRect(c, kx, y + 2, 2, 2)
                    s.fillRect(c, kx + 5, y + 2, 2, 2)
                    s.fillRect(col("black"), kx + 2, y + 5, 1, 1)
                    s.fillRect(col("black"), kx + 4, y + 5, 1, 1)
                } else {
                    let inLine = i < homeCount + line.count
                    s.rect(col(inLine && Int(t * 6) % 2 == 1 ? "pink" : "darkgray"), IRect(kx, y + 2, 7, 7), width: 1)
                }
            }
            if need > show { drawText(s, "+\(need - show)", x + show * 9 + 1, y + 3, "pink", shadow: nil) }
            x += min(need, 12) * 9 + (need > 12 ? 14 : 4)
        }
        if boss == nil {
            let secs = max(0, Int(ceil(clock)))
            let low = secs <= 10
            drawText(s, String(format: "%02d", secs), x + 2, y + 3, low ? (Int(t * 6) % 2 == 1 ? "red" : "yellow") : "white", shadow: nil)
            let bw = 50
            s.fillRect(col("darkgray"), x + 18, y + 5, bw, 3)
            s.fillRect(col(low ? "red" : "sky"), x + 18, y + 5, Int(Double(bw) * max(0, min(1, clock / max(1, clockFull)))), 3)
            x += 74
        }
        // power-ups
        var icons: [(String, Double)] = []
        if zoomT > 0 { icons.append(("ah_nip", zoomT)) }
        if slowT > 0 { icons.append(("ah_bell", slowT)) }
        for (name, v) in icons {
            if v > 1.5 || Int(t * 8) % 2 == 1 { s.blit(sprite(name), x, y + 2) }
            x += 11
        }
        for _ in 0 ..< shield { s.blit(sprite("ah_boxitem"), x, y + 3); x += 10 }
        for _ in 0 ..< bells { s.fillRect(col("yellow"), x + 1, y + 4, 3, 4); x += 6 }
        for _ in 0 ..< swims { s.fillRect(col("teal"), x, y + 6, 5, 2); x += 7 }
        if lv("pounce") > 0 {
            let ready = pounceCd <= 0
            let c = col(ready ? "orange" : "darkgray")      // a little leap arc
            s.line(c, x, y + 9, x + 3, y + 3)
            s.line(c, x + 3, y + 3, x + 6, y + 9)
            if !ready {
                let full = [4.0, 4.0, 3.0, 2.0][min(3, lv("pounce"))]
                s.fillRect(col("orange"), x, y + 10, Int(7 * (1 - pounceCd / full)), 1)
            }
            x += 9
        }
        if !hype.feverOn {          // (during FEVER the kit shows its own label here)
            let x0 = W - 52, y0 = y + 4
            s.fillRect(col("darkgray"), x0, y0, 48, 3)
            s.fillRect(col("orange"), x0, y0, Int(48 * hype.fever), 3)
        }
    }

    func drawIntro(_ s: Surface, _ t: Double) {
        if st.kind == "boss", let b = st.boss {
            if Int(t * 4) % 2 == 1 {
                var x = -20
                while x < W + 20 {
                    s.polygon(col("red"), [(Double(x), 96), (Double(x + 10), 96), (Double(x + 20), 104), (Double(x + 10), 104)])
                    s.polygon(col("red"), [(Double(x), 152), (Double(x + 10), 152), (Double(x + 20), 160), (Double(x + 10), 160)])
                    x += 20
                }
            }
            panel(s, IRect(30, 108, 260, 40), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 112, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(b.name) - \(b.title)", W / 2, 129, "white", align: .center, shadow: nil)
            drawText(s, b.hint, W / 2, 138, "lime", align: .center, shadow: nil)
            return
        }
        let h = st.newLine.isEmpty ? 54 : 64
        let y0 = 92
        panel(s, IRect(24, y0, 272, h), fill: "ink", border: st.kind == "bonus" ? "yellow" : theme[9])
        let bob = Int(abs(sin(t * 5)) * 2)
        s.blit(sprite("ah_sushi", 5, scale: 2), 32, y0 + 10 - bob)
        let cx = 176
        if st.kind == "bonus" {
            let title = "BONUS STAGE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), cx - textWidth(title, 2) / 2 + i * 12, y0 + 6 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            let sub = st.bonus == "feast" ? "GRAB ALL THE TREATS YOU CAN!" : "HUGE FAMILIES = HUGE POINTS!"
            drawText(s, st.name, cx, y0 + 26, "yellow", align: .center)
            drawText(s, sub, cx, y0 + 37, "white", align: .center, shadow: nil)
            return
        }
        drawText(s, "STAGE \(n)", cx, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        drawText(s, "\(theme[0]) - \(st.name)", cx, y0 + 24, "lavender", align: .center, shadow: nil)
        drawText(s, "BRING \(need) KITTENS HOME!", cx, y0 + 34, "white", align: .center, shadow: nil)
        drawText(s, "\"\(st.line)\"", cx, y0 + 44, "peach", align: .center, shadow: nil)
        if !st.newLine.isEmpty { drawText(s, st.newLine, cx, y0 + 54, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center, shadow: nil) }
    }

    func drawTally(_ s: Surface, _ t: Double) {
        let h = 40 + tally.count * 11
        let y0 = 70
        panel(s, IRect(48, y0, 224, h), fill: "ink", border: "mint")
        let head = st.kind == "boss" ? "BOSS CLEAR!" : (st.kind == "bonus" ? "BONUS OVER!" : "STAGE \(n) CLEAR!")
        drawText(s, head, W / 2, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 20 + i * 11
            drawText(s, row.label, 58, y, row.v > 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 262, y, row.v > 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        var quip = !missed && !lostAny ? "PURRFECT! EVERYONE IS HOME!" : (missed ? "PHEW... HOME SWEET HOME!" : "WE MADE IT, LITTLE ONES!")
        if st.kind == "boss" { quip = "AND STAY OUT OF MY ALLEY!" } else if st.kind == "bonus" { quip = "YUM! WHAT A NIGHT!" }
        drawText(s, quip, W / 2, y0 + h - 22, "peach", align: .center, shadow: nil)
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 {
            drawText(s, "TAP HOP", W / 2, y0 + h - 11, "lavender", align: .center, shadow: nil)
        }
    }

    // ---------------------------------------------------------------- carousel preview
    /// Carousel thumbnail: Sushi hops a little family across a road, a canal and another road into a box.
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        s.fill(col("night"))
        let nl = max(2, min(4, (h - 10) / 16))
        let kinds = Array(["safe", "road", "water", "road"].prefix(nl))
        let base = h - 16 * nl
        for (i, kind) in kinds.enumerated() {
            let y0 = h - 16 * (i + 1)
            if kind == "safe" {
                s.fillRect(col("darkgray"), 0, y0, w, 16)
                var xx = 0
                while xx < w { s.fillRect(col("gray"), xx, y0, 1, 16); xx += 16 }
                s.fillRect(col("gray"), 0, y0 + 8, w, 1)
            } else if kind == "road" {
                s.fillRect(col("ink"), 0, y0, w, 16)
                let d = i == 1 ? 1 : -1
                for k in 0 ..< 3 {
                    let X = Int(ahPmod(Double(k * 46) + Double(d) * t * 30 + Double(i * 20), Double(w + 40))) - 30
                    if k % 2 == 1 { AHArt.bike(s, X, y0, d, t) } else { AHArt.scooter(s, X, y0, d, t) }
                }
            } else {
                s.fillRect(col("blue"), 0, y0, w, 16)
                let X = Int(ahPmod(t * 16, Double(w + 60))) - 52
                AHArt.crate(s, X, y0, 48, t)
                AHArt.crate(s, X - 80, y0, 32, t)
            }
        }
        s.fillRect(col("brown"), 0, 0, w, base)
        s.fillRect(col("orange"), 0, base - 2, w, 2)
        var bx = w / 2 - 40
        while bx < w {
            AHArt.box(s, bx - 8, base - 15, bx < w / 2 ? 1 : 0, t)
            bx += 40
        }
        // hop, hop, hop... into the box
        let T = 0.55
        let steps = nl + 3
        let k = Int(t / T) % steps
        let p = ahPmod(t / T, 1.0)
        let hop = min(1, p / 0.35)
        func spot(_ idx0: Int) -> Double {
            let idx = max(0, min(nl, idx0))
            return Double(idx < nl ? h - 16 * idx - 8 : base - 6)
        }
        let cx = w / 2
        for j in [2, 1] {
            let kk = k - j
            if kk < 0 || kk > nl { continue }
            let y = kk < nl ? spot(kk) + (spot(kk + 1) - spot(kk)) * hop : spot(nl)
            AHArt.kitten(s, Double(cx + (j * 2 - 3) * 3), y + 6, j, t, kk >= nl ? "happy" : "", kk < nl ? hop : 0, j)
        }
        if k <= nl {
            let y = k < nl ? spot(k) + (spot(k + 1) - spot(k)) * hop : spot(nl)
            AHArt.sushi(s, cx - 8, Int(y) - 9, t, "up", k >= nl ? "happy" : "", k < nl ? hop : 0)
        }
    }
}

/// Banded light pool alpha subtracted from the darkness (same formula as alley_hop.light_alpha).
@inline(__always) func ahLightAlpha(_ d2: Int, _ r2: Int) -> Int {
    if d2 * 10 < r2 * 3 { return 175 }
    if d2 * 10 < r2 * 6 { return 120 }
    if d2 < r2 { return 60 }
    return 0
}
