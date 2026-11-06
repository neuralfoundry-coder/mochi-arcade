// HAIRBALL HAVOC - single-screen arena shooter starring Biscuit the cream cat (port of games/hairball_havoc.py).
// Stage tables: HairballHavocData.swift (exported from Python). Art: HairballHavocArt.swift. Bosses: HairballHavocBoss.swift.
import Foundation

let HH_PSPEED = 82.0
let HH_HB = 3.0                     // Biscuit's hitbox (half size) against bullets and toys
let HH_BODY = 4.0                   // her half size against walls and furniture
let HH_SHOT_V = 220.0
private let EXTRA_LIVES = [20000, 60000, 120000, 200000]
private let EXTRA_EVERY = 150000
let HH_DIRS8: [(Double, Double)] = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
private let KIT_ORDER = ["rapid", "big", "box", "zoom", "spread", "bomb", "tail", "purr", "pal", "bounce", "magnet", "nip"]
private let DROPS: [(String, Double)] = [("F", 7), ("Y", 5), ("X", 3), ("L", 3), ("H", 2), ("N", 2)]
let HH_TOY_SPRITE: [Int: String] = [HH_MOUSE: "hh_mouse", HH_CAR: "hh_car", HH_SOCK: "hh_sock", HH_VAC: "hh_vac", HH_DRUM: "hh_drum",
                                    HH_BALL: "hh_ball", HH_PLANE: "hh_plane", HH_POPBOX: "hh_popbox", HH_GOLEM: "hh_golem",
                                    HH_HELI: "hh_heli", HH_TOP: "hh_top", HH_MINIBALL: "hh_miniball", HH_BLOCKLET: "hh_blocklet",
                                    HH_GOLD: "hh_mouse"]
let HH_TOY_COLORS: [Int: [String]] = [HH_MOUSE: ["gray", "white", "pink"], HH_CAR: ["red", "yellow", "sky"], HH_SOCK: ["white", "red", "sky"],
                                      HH_VAC: ["darkgray", "gray", "red"], HH_DRUM: ["brown", "red", "yellow"],
                                      HH_BALL: ["hotpink", "yellow", "sky"], HH_PLANE: ["white", "lavender"],
                                      HH_POPBOX: ["purple", "yellow", "lavender"], HH_GOLEM: ["red", "sky", "lime"],
                                      HH_HELI: ["blue", "sky", "gray"], HH_TOP: ["orange", "yellow"], HH_MINIBALL: ["hotpink", "yellow"],
                                      HH_BLOCKLET: ["yellow", "sky"], HH_GOLD: ["yellow", "orange", "white"]]
private let CHASERS: Set<Int> = [HH_MOUSE, HH_BLOCKLET, HH_GOLEM, HH_SOCK, HH_DRUM, HH_VAC]
let HH_BOSS_BULLET = [2, 3, 4, 0, 5, 7]
private let FEVER_TINT: [Character] = ["P", "o", "y", "l", "m", "s", "v"]
private let TINT_NAME: [Character: String] = ["c": "cream", "P": "hotpink", "o": "orange", "y": "yellow", "l": "lime", "m": "mint",
                                              "s": "sky", "v": "lavender"]
private let QUIPS_WIN = ["PURRFECT!", "NOT A SCRATCH!", "TOO EASY.", "I NEED A NAP..."]
let HH_TAU = 2 * Double.pi

func hhRnd(_ a: Double, _ b: Double) -> Double { Double.random(in: min(a, b) ... max(a, b)) }
func hhChance() -> Double { Double.random(in: 0 ..< 1) }
func hhSign() -> Double { Bool.random() ? 1 : -1 }
/// Python-style float modulo (result has the sign of the divisor).
func hhMod(_ a: Double, _ b: Double) -> Double { a - b * (a / b).rounded(.down) }
func hhDir8(_ dx: Double, _ dy: Double) -> Int { ((Int((atan2(dy, dx) / (.pi / 4)).rounded()) % 8) + 8) % 8 }
func hhNorm(_ dx: Double, _ dy: Double) -> (Double, Double) {
    let d = hypot(dx, dy)
    return d > 1e-6 ? (dx / d, dy / d) : (1, 0)
}
func hhSegDist(_ px: Double, _ py: Double, _ ax: Double, _ ay: Double, _ bx: Double, _ by: Double) -> Double {
    let dx = bx - ax, dy = by - ay
    let l2 = dx * dx + dy * dy
    let u = l2 < 1e-6 ? 0 : max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
    return hypot(px - (ax + dx * u), py - (ay + dy * u))
}

let HH_ICONS = ["rapid": "hh_ic_rapid", "big": "hh_ic_big", "spread": "hh_yarn", "tail": "hh_ic_tail", "box": "hh_box",
                "zoom": "hh_ic_zoom", "bomb": "hh_bomb", "purr": "heart", "pal": "hh_kitten", "bounce": "hh_ic_bounce",
                "magnet": "hh_fish", "nip": "hh_catnip"]

/// Upgrade card icon: the pixel sprite at double size.
func hhCardIcon(_ id: String) -> (Surface, Int, Int, Double) -> Void {
    return { s, cx, cy, _ in
        let sp = sprite(HH_ICONS[id]!, scale: 2)
        s.blit(sp, cx - sp.w / 2, cy - sp.h / 2)
    }
}

let HH_POOL: [Upgrade] = [
    Upgrade(id: "rapid", name: "QUICK SPIT", desc: "SPIT HAIRBALLS|FASTER", color: "orange", draw: hhCardIcon("rapid"), max: 5),
    Upgrade(id: "big", name: "BIG FLUFF", desc: "BIGGER HAIR-|BALLS THAT|HIT HARDER", color: "peach", draw: hhCardIcon("big"), max: 3),
    Upgrade(id: "spread", name: "YARN TWIST", desc: "+2 SIDE SHOTS|THAT FAN OUT", color: "pink", draw: hhCardIcon("spread"), max: 2),
    Upgrade(id: "tail", name: "TAIL SHOT", desc: "ALSO SPIT|BEHIND YOU|LV2: SIDEWAYS", color: "yellow", draw: hhCardIcon("tail"), max: 2),
    Upgrade(id: "box", name: "BOX FORT", desc: "+1 BOX SHIELD|EVERY STAGE", color: "peach", draw: hhCardIcon("box"), max: 3),
    Upgrade(id: "zoom", name: "ZOOMIES", desc: "RUN|FASTER", color: "sky", draw: hhCardIcon("zoom"), max: 3),
    Upgrade(id: "bomb", name: "BIG BELLY", desc: "+1 HAIRBALL|BOMB, BIGGER|BLASTS", color: "red", draw: hhCardIcon("bomb"), max: 3),
    Upgrade(id: "purr", name: "PURR POWER", desc: "PURR STARTS|HIGHER,|+2 MAX PURR", color: "hotpink", draw: hhCardIcon("purr"), max: 2),
    Upgrade(id: "pal", name: "KITTEN PAL", desc: "A KITTEN|FIGHTS AT|YOUR SIDE", color: "lime", draw: hhCardIcon("pal"), max: 2),
    Upgrade(id: "bounce", name: "RICOCHET", desc: "HAIRBALLS|BOUNCE OFF|WALLS", color: "lavender", draw: hhCardIcon("bounce"), max: 2),
    Upgrade(id: "magnet", name: "WHISKER SENSE", desc: "PULLS IN|TREATS, PETS|AND POWER-UPS", color: "mint", draw: hhCardIcon("magnet"), max: 2),
    Upgrade(id: "nip", name: "CATNIP NOSE", desc: "POWER-UPS|AND FEVER|LAST LONGER", color: "lime", draw: hhCardIcon("nip"), max: 3),
]

protocol HHBody: AnyObject { var x: Double { get set }; var y: Double { get set } }

final class HHToy: HHBody {
    let uid, kind: Int
    var x, y: Double
    var hp, maxhp: Double
    let w, h: Int
    let elite: Bool
    var vx = 0.0, vy = 0.0
    var t = 0.0, flash = 0.0
    var alive = true
    var state = 0
    var timer = hhRnd(0.6, 2.0)
    var aux = 0.0
    var side = 1.0
    var stuck = 0.0
    var face = 1
    var ext = 0.0
    var ax = 0.0, ay = 0.0
    var spawnT = 0.4
    var parade = false, gold = false, minion = false
    var jitT = 0.0, jit = 0.0           // chasers wobble off the straight line a little
    var seed = hhRnd(0, 6.28)

    init(_ uid: Int, _ kind: Int, _ x: Double, _ y: Double, _ elite: Bool, _ hpx: Double) {
        self.uid = uid; self.kind = kind; self.x = x; self.y = y; self.elite = elite
        let k = HHData.kinds[kind]
        hp = Double(k.hp) * (elite ? 2 : 1) * hpx
        maxhp = hp
        w = k.w; h = k.h
    }
}

final class HHShot {
    var x, y, vx, vy, dmg: Double
    let r, kind: Int
    var pierce, bounce: Int
    var life = 2.0
    var hits: [Int] = []
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ dmg: Double, _ r: Int, _ pierce: Int, _ bounce: Int, _ kind: Int) {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.dmg = dmg; self.r = r; self.pierce = pierce; self.bounce = bounce; self.kind = kind
    }
}

final class HHBullet {
    var x, y, vx, vy: Double
    let kind: Int
    var fuse: Double
    var t = 0.0
    init(_ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ kind: Int, _ fuse: Double = 0) {
        self.x = x; self.y = y; self.vx = vx; self.vy = vy; self.kind = kind; self.fuse = fuse
    }
}

final class HHItem {
    var x, y, vx, vy: Double
    let kind: String
    var t = 0.0, life = 9.0
    init(_ x: Double, _ y: Double, _ kind: String, _ vx: Double = 0, _ vy: Double = 0) { self.x = x; self.y = y; self.kind = kind; self.vx = vx; self.vy = vy }
}

final class HHPet: HHBody {
    let kind, coat: Int                 // kind 0 kitten, 1 hamster, 2 golden hamster
    var x, y: Double
    var vx = 0.0, vy = 0.0
    var t = hhRnd(0, 3)
    var timer = hhRnd(0.5, 2.0)
    var state = "idle"                  // idle | saved | lost
    var fade = 0.0
    init(_ kind: Int, _ x: Double, _ y: Double, _ coat: Int) { self.kind = kind; self.x = x; self.y = y; self.coat = coat }
}

final class HHBoss {
    let kind, lv: Int
    let final: Bool
    let name: String
    var hp: Double
    let maxhp: Double
    let bw, bh: Double
    let minion: Int
    let phases: [[String]]
    let nphase: Int
    var parts: [(dx: Double, dy: Double, r: Int, hp: Double, flash: Double, alive: Bool)]
    var x = Double(W) / 2, y = Double(HH_IY0 - 30)
    let hy = 74.0
    var t = 0.0
    var state = "enter"
    var phase = 0
    var atk: String?
    var at = 0.0
    var ai = 0, an = 0
    var rest = 1.2
    var flash = 0.0
    var face = 1
    var moving = false
    var tx = Double(W) / 2, ty = 80.0
    var sx = 0.0, sy = 0.0
    var wx = Double(W) / 2, wy = 90.0, wt = 0.0
    var ang = 0.0
    var dir = 1.0
    var lanes: [(Double, Double)] = []
    var spots: [(Double, Double)] = []
    var ext = 0.0, z = 0.0, aux = 0.0
    var heading = Double.pi / 2
    var trail: [(Double, Double)] = []
    var head = (Double(W) / 2, 0.0)

    init(_ st: HHStage) {
        let spec = HHData.bosses[st.boss]
        kind = st.boss; lv = st.lv; final = st.final; name = st.name
        hp = Double(st.hp); maxhp = Double(st.hp)
        (bw, bh) = spec.box
        minion = spec.minion
        phases = st.phases; nphase = st.nphase
        let mh = Double(st.hp)
        if kind == 4 {
            parts = Array(repeating: (dx: 0.0, dy: 0.0, r: 8, hp: mh * 0.08, flash: 0.0, alive: true), count: st.cars)
        } else {
            parts = spec.parts.map { (dx: $0.0, dy: $0.1, r: $0.2, hp: mh * $0.3, flash: 0.0, alive: true) }
        }
        trail = (0 ..< 80).map { (Double(W) / 2, Double(HH_IY0 - 30) - Double($0) * 2) }
        head = (x, y - 20)
    }
}

struct HHLane { let kind, door: Int; let delay: Double; let count, gold: Int; var done = 0 }
struct HHTally { var title: String; var lines: [(String, Int)]; var t = 0.0; var shown = 0; var total: Int; var quip: String }

final class HairballHavoc: GameScene, HHBody {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD   RUN (8 WAYS)", "FIRE  SPIT HAIRBALLS (HOLD = AIM LOCK)", "BOMB  HAIRBALL BOMB"]
    static let helpSkip = 3

    var stageMusic = "hh_house"
    override var music: String? { stageMusic }
    override var buttons: [Action: String] {
        if overlay != nil || phase == "tally" { return [.a: "OK"] }
        return [.a: "FIRE", .b: "BOMB"]
    }
    override var buttonOrder: [Action] { [.a, .b] }
    override var fourWay: Bool { false }

    var lives: Int
    let spd: Double
    let auto: Bool
    var stageN: Int
    var px = Double(W) / 2, py = 108.0
    var x: Double { get { px } set { px = newValue } }
    var y: Double { get { py } set { py = newValue } }
    var vx = 0.0, vy = 0.0
    var fx = 0.0, fy = 1.0
    var face8 = 2
    var locked = false
    var levels: [String: Int] = [:]
    var toys: [HHToy] = [], shots: [HHShot] = [], bullets: [HHBullet] = [], items: [HHItem] = [], pets: [HHPet] = []
    var spawned: [HHToy] = []
    var boss: HHBoss?
    var inv = 1.5
    var deadT: Double?
    var fireT = 0.0
    var shotN = 0
    var walkT = 0.0, happyT = 0.0, blinkT = 2.0
    var yarnT = 0.0, laserT = 0.0, laserTick = 0.0
    var laserEnd: (Double, Double)?
    var bombT = 0.0, bombX = 0.0, bombY = 0.0
    var bombHit = Set<Int>()
    var pullX = 0.0, pullY = 0.0
    var trail: [(Double, Double)] = []
    var pals: [(x: Double, y: Double, t: Double)] = Array(repeating: (Double(W) / 2, 108, 0.3), count: 2)
    var extraI = 0
    var nextExtra = EXTRA_LIVES[0]
    var uid = 0
    var feverWas = false
    var bg: Surface?
    var bgN = -1
    var tally: HHTally?
    var vicT = 0.0
    var bombs = 2, shield = 0
    // per stage
    var st: HHStage
    var mode = "normal"
    var tierN = 0
    var furnR: [(Double, Double, Double, Double)] = []
    var doors: [(Int, Int)] = []
    var stageT = 0.0, introT = 0.0, clearT = 0.0, waveT = 0.0
    var deaths = 0, saved = 0, lost = 0, hits = 0, total = 0, broken = 0
    var spawnI = 0
    var purr = 1
    var maxSaid = false
    var mods: [String] = []
    var lights = false, slip = false
    var totalPets = 0
    var goldT = -1.0
    var lanes: [HHLane] = []
    var phase = "intro"

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        spd = SPEEDS[d] ?? 1
        auto = (opt["aim"] ?? "lock").lowercased() == "auto"
        // an explicit "stage" (GIF recorder, tests) wins over the checkpoint start picked in the setup screen
        stageN = max(1, min(STAGES, Int(opt["stage"] ?? opt["start"] ?? "1") ?? 1))
        st = HHData.stage(stageN)
        super.init(app, info, opt)
        hype.comboY = 13            // the combo counter sits on a plate in the top wall
        var kit = (stageN - 1) / 10 // a checkpoint start hands out the power you'd roughly have
        let given = kit
        var i = 0
        while kit > 0 && i < 200 {
            let u = HH_POOL.first { $0.id == KIT_ORDER[i % KIT_ORDER.count] }!
            if lv(u.id) < u.max { levels[u.id] = lv(u.id) + 1; kit -= 1 }
            i += 1
        }
        bombs = 2 + lv("bomb")
        shield = 0
        hype.feverTime = 8.0 + 1.5 * Double(lv("nip"))
        startStage()
        if given > 0 { hype.banner("CHECKPOINT!", "+\(given) POWER LEVELS", color: "lime", dur: 2.0) }
    }

    // ------------------------------------------------------------------ helpers
    func lv(_ id: String) -> Int { levels[id] ?? 0 }

    func say(_ x: Double, _ y: Double, _ text: String, _ c: String) {
        let hw = Double(textWidth(text) / 2 + 2)
        floats.add(max(hw, min(Double(W) - hw, x)), max(30, y), text, c)
    }

    func purrBase() -> Int { 1 + lv("purr") }
    func purrMax() -> Int { 8 + 2 * lv("purr") }

    /// A box centred at (x, y) leaves the floor or (walkers only) touches furniture.
    func blocked(_ x: Double, _ y: Double, _ hw: Double, _ hh: Double, _ fly: Bool = false) -> Bool {
        if x - hw < Double(HH_IX0) || x + hw > Double(HH_IX1) || y - hh < Double(HH_IY0) || y + hh > Double(HH_IY1) { return true }
        if fly { return false }
        for (fx, fy, fw, fh) in furnR where x + hw > fx && x - hw < fx + fw && y + hh > fy && y - hh < fy + fh { return true }
        return false
    }

    func solidPt(_ x: Double, _ y: Double) -> Bool {
        if x < Double(HH_IX0) || x >= Double(HH_IX1) || y < Double(HH_IY0) || y >= Double(HH_IY1) { return true }
        for (fx, fy, fw, fh) in furnR where fx <= x && x < fx + fw && fy <= y && y < fy + fh { return true }
        return false
    }

    /// Axis-separated move (slides along walls); returns which axes were blocked.
    @discardableResult
    func move(_ o: HHBody, _ dx: Double, _ dy: Double, _ hw: Double, _ hh: Double, _ fly: Bool = false) -> (Bool, Bool) {
        let inside = blocked(o.x, o.y, hw, hh, fly)
        var hx = false, hy = false
        if dx != 0 {
            if !inside && blocked(o.x + dx, o.y, hw, hh, fly) { hx = true } else { o.x += dx }
        }
        if dy != 0 {
            if !inside && blocked(o.x, o.y + dy, hw, hh, fly) { hy = true } else { o.y += dy }
        }
        if inside {      // spawned or pushed into something: nudge back onto the floor
            o.x = max(Double(HH_IX0) + hw, min(Double(HH_IX1) - hw, o.x))
            o.y = max(Double(HH_IY0) + hh, min(Double(HH_IY1) - hh, o.y))
        }
        return (hx, hy)
    }

    /// Nearest thing to shoot at (auto aim, kitten pals).
    func targetOf(_ x: Double, _ y: Double) -> ((Double, Double)?, Double) {
        var best: (Double, Double)?
        var bd = 1e9
        for e in toys where e.alive && e.spawnT <= 0 {
            let d = (e.x - x) * (e.x - x) + (e.y - y) * (e.y - y)
            if d < bd { best = (e.x, e.y); bd = d }
        }
        if let b = boss, b.state == "fight" {
            let d = (b.x - x) * (b.x - x) + (b.y - y) * (b.y - y)
            if d < bd { best = (b.x, b.y); bd = d }
        }
        return (best, bd)
    }

    // ------------------------------------------------------------------ stages
    func startStage() {
        let n = stageN
        st = HHData.stage(n)
        mode = st.type
        tierN = tier(n)
        reached(n)
        if bgN != n { bg = HHArt.buildRoom(st); bgN = n }
        furnR = st.furn.map { (Double(HH_IX0 + $0.x * 8), Double(HH_IY0 + $0.y * 8), Double($0.w * 8), Double($0.h * 8)) }
        doors = st.doors
        toys = []; bullets = []; items = []; spawned = []
        boss = nil
        px = Double(W) / 2; py = 108
        vx = 0; vy = 0
        stageT = 0; introT = 0; clearT = 0; waveT = 0
        deaths = 0; saved = 0; lost = 0; hits = 0; total = 0; broken = 0
        spawnI = 0
        purr = purrBase()
        maxSaid = false
        shield = max(shield, lv("box"))
        tally = nil
        trail = []
        mods = st.mods
        lights = mods.contains("LIGHTS OUT")
        slip = mods.contains("SLIPPERY")
        pets = st.pets.map { HHPet($0.kind, Double(HH_IX0 + $0.x * 8 + 4), Double(HH_IY0 + $0.y * 8 + 4), $0.coat) }
        totalPets = pets.count
        goldT = mode == "normal" && hype.lucky(0.04) ? hhRnd(10, 25) : -1
        lanes = []
        let au = app.audio
        let song = tierN < 10 ? "hh_house" : "hh_deep"
        if mode == "boss" {
            phase = "warning"
            boss = HHBoss(st)
            stageMusic = "boss"
            au.play("warning")
        } else {
            phase = "intro"
            stageMusic = mode == "bonus" ? "bonus" : song
            au.play("stage")
            if mode == "bonus" {
                inv = max(inv, 0.5)
                if st.mode == "parade" {
                    yarnT = st.dur + 3
                    lanes = st.lanes.map { HHLane(kind: $0.kind, door: $0.door, delay: $0.delay, count: $0.count, gold: $0.gold) }
                    total = st.lanes.reduce(0) { $0 + $1.count }
                } else {
                    total = totalPets
                }
            }
        }
        if !hype.feverOn || mode == "boss" { au.music(stageMusic) }
    }

    func nextStage() { stageN += 1; startStage() }

    func checkClear() {
        if phase != "play" { return }
        let done: Bool
        if mode == "boss" {
            done = boss == nil
        } else if mode == "bonus" {
            if st.mode == "parade" {
                done = stageT >= st.dur || (lanes.allSatisfy { $0.done >= $0.count } && toys.isEmpty)
            } else {
                done = stageT >= st.dur || !pets.contains { $0.state == "idle" }
            }
        } else {
            done = spawnI >= st.spawns.count && !toys.contains { $0.kind != HH_GOLD }
        }
        if !done { return }
        phase = "clear"
        clearT = 0
        cancelBullets()
        for e in toys where e.alive { parts.burst(e.x, e.y, 8, HH_TOY_COLORS[e.kind]!, 60, 0.5) }
        toys = []
        happyT = 3
        if mode != "boss" { app.audio.play("levelup") }
        if mode == "normal" && totalPets > 0 && saved == totalPets {
            hype.banner("ALL PETS SAFE!", color: "pink", dur: 1.4, sound: "bonus")
            hype.shower(30, "hearts")
        }
    }

    func startTally() {
        let t = tierN
        var lines: [(String, Int)] = []
        var title: String
        if mode == "normal" {
            lines.append(("CLEAR BONUS", 1000 + 250 * t))
            lines.append(("TIME BONUS", max(0, Int(st.par - stageT)) * 50))
            if totalPets > 0 { lines.append(("PETS SAVED \(saved)/\(totalPets)", saved * (1000 + 200 * t))) }
            lines.append(("NO MISS", deaths == 0 ? 3000 + 750 * t : 0))
            if totalPets > 0 && saved == totalPets && deaths == 0 { lines.append(("PERFECT!!", 5000 + 1000 * t)) }
            title = "STAGE \(stageN) CLEAR!"
        } else if mode == "bonus" {
            if st.mode == "parade" {
                lines.append(("TOYS POPPED \(hits)/\(total)", hits * (100 + 10 * t)))
            } else {
                lines.append(("PETS SAVED \(saved)/\(total)", saved * (300 + 30 * t)))
                hits = saved
            }
            if hits >= total { lines.append(("PERFECT!!", 10000 + 2500 * t)) }
            title = "BONUS ROOM OVER"
        } else {
            lines.append(("BOSS BONUS", 10000 + 5000 * t))
            lines.append(("TIME BONUS", max(0, Int(st.par - stageT)) * 100))
            lines.append(("NO MISS", deaths == 0 ? 5000 + 1000 * t : 0))
            if bossParts { lines.append(("PARTS BROKEN \(broken)", broken * 2000)) }
            title = "\(st.name) DOWN!"
        }
        let perfect = lines.contains { $0.0.hasPrefix("PERFECT") }
        let quip = perfect ? QUIPS_WIN[0] : (deaths == 0 ? QUIPS_WIN[1] : (deaths >= 2 ? QUIPS_WIN[3] : QUIPS_WIN[2]))
        tally = HHTally(title: title, lines: lines, total: lines.reduce(0) { $0 + $1.1 }, quip: quip)
        phase = "tally"
    }

    func updateTally(_ dt: Double) {
        guard var tl = tally else { return }
        tl.t += dt
        let n = tl.lines.count
        while tl.shown < n && tl.t >= 0.35 + Double(tl.shown) * 0.4 {
            let (label, v) = tl.lines[tl.shown]
            tl.shown += 1
            if label.hasPrefix("PERFECT") {
                app.audio.play("win")
                hype.shower(50, "coins")
                hype.flash("yellow", 0.2)
            } else {
                app.audio.play(v > 0 ? "coin" : "move")
            }
        }
        tally = tl
        let end = 0.35 + Double(n) * 0.4 + 0.4
        if tl.t >= end + 1.4 || (tl.t >= end && app.input.hit(.a, .b)) { finishTally() }
    }

    func finishTally() {
        guard let tl = tally else { return }
        tally = nil
        if tl.total > 0 { add(tl.total, Double(W / 2), 110, "yellow") }
        phase = "between"
        if mode == "boss" {
            if st.final || stageN >= STAGES {
                phase = "victory"
                vicT = 0
                hype.banner("HOUSE SAVED!!", "ALL 200 STAGES CLEAR", dur: 4.0, rainbow: true, sound: "win")
                hype.shower(120, "confetti")
                hype.shower(40, "hearts")
                app.audio.music("fever")
                return
            }
            pickUpgrade(HH_POOL, levels, title: "POWER UP!") { [unowned self] id in self.onPick(id) }
        } else if mode == "bonus" && hits * 2 >= total {
            pickUpgrade(HH_POOL, levels, title: "BONUS PICK!") { [unowned self] id in self.onPick(id) }
        } else {
            nextStage()
        }
    }

    func onPick(_ id: String?) {
        if let id = id {
            levels[id] = lv(id) + 1
            if id == "bomb" { bombs += 1 } else if id == "box" { shield += 1 } else if id == "nip" { hype.feverTime = 8.0 + 1.5 * Double(lv("nip")) }
        } else {
            add(25000, Double(W / 2), 100, "lime")
            hype.banner("MAX POWER!", "+25000", color: "lime", dur: 1.4)
        }
        nextStage()
    }

    var bossParts: Bool { [1, 3, 4].contains(st.boss) }

    // ------------------------------------------------------------------ update
    override func tick(_ dt: Double) {
        let au = app.audio
        stageT += phase == "play" ? dt : 0
        introT += dt
        inv = max(0, inv - dt)
        happyT = max(0, happyT - dt)
        yarnT = max(0, yarnT - dt)
        laserT = max(0, laserT - dt)
        updatePlayer(dt)
        if ending != nil { return }
        pullX = 0; pullY = 0
        updateShots(dt)
        for e in toys where e.alive { updateToy(e, dt) }
        separate()
        if boss != nil { updateBoss(dt) }
        updatePets(dt)
        if phase == "play" { spawnLogic(dt) }
        updateBullets(dt)
        updateItems(dt)
        collide()
        if bombT > 0 { updateBomb(dt) }
        toys = toys.filter { $0.alive } + spawned
        spawned = []
        checkExtra()
        if hype.feverOn != feverWas {
            feverWas = hype.feverOn
            if mode != "boss" && phase != "victory" { au.music(feverWas ? "fever" : stageMusic) }
        }
        if phase == "intro" && introT >= 2.4 {
            phase = "play"
        } else if phase == "warning", let b = boss, b.state == "fight" {
            phase = "play"
        } else if phase == "clear" {
            clearT += dt
            if clearT >= 1.2 { startTally() }
        } else if phase == "tally" {
            updateTally(dt)
        } else if phase == "victory" {
            vicT += dt
            if Int(vicT * 4) != Int((vicT - dt) * 4) {
                parts.burst(hhRnd(40, Double(W - 40)), hhRnd(40, 150), 30, [rainbow(Int.random(in: 0 ..< 7)), "white", "yellow"], 110, 1.0)
                au.play("explode")
            }
            if vicT >= 5 { endGame(true, "ALL 200 STAGES!") }
        }
        checkClear()
    }

    func checkExtra() {
        while score >= nextExtra {
            lives += 1
            extraI += 1
            nextExtra = extraI < EXTRA_LIVES.count ? EXTRA_LIVES[extraI] : nextExtra + EXTRA_EVERY
            if !hype.banners.isEmpty {
                say(px, py - 16, "1UP!", "mint")
                app.audio.play("extra")
            } else {
                hype.banner("1UP!", "AN EXTRA LIFE", color: "mint", dur: 1.3, sound: "extra")
            }
            hype.shower(16, "hearts")
        }
    }

    func setFace(_ dx: Double, _ dy: Double) {
        (fx, fy) = hhNorm(dx, dy)
        face8 = hhDir8(dx, dy)
    }

    func updatePlayer(_ dt: Double) {
        let inp = app.input
        if var d = deadT {
            d -= dt
            deadT = d
            if d <= 0 {
                if lives <= 0 { endGame(false, "STAGE \(stageN)"); return }
                respawn()
            }
            return
        }
        let dx = Double((inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0))
        let dy = Double((inp.down(.down) ? 1 : 0) - (inp.down(.up) ? 1 : 0))
        let firing = inp.down(.a) && !["tally", "between", "victory"].contains(phase)
        if auto {
            locked = false
            if firing {
                if let tg = targetOf(px, py).0 { setFace(tg.0 - px, tg.1 - py) } else if dx != 0 || dy != 0 { setFace(dx, dy) }
            } else if dx != 0 || dy != 0 {
                setFace(dx, dy)
            }
        } else {
            if (dx != 0 || dy != 0) && (inp.hit(.a) || !inp.down(.a)) { setFace(dx, dy) }   // a fresh press takes the stick's direction, then holds it
            locked = inp.down(.a)
        }
        let fever = hype.feverOn
        var sp = HH_PSPEED * (1 + 0.12 * Double(lv("zoom"))) * (fever ? 1.3 : 1.0)
        if dx != 0 && dy != 0 { sp *= 0.7071 }
        let k = min(1.0, dt * (slip ? 3.0 : 22.0))
        vx += (dx * sp - vx) * k
        vy += (dy * sp - vy) * k
        let mx = (vx + pullX) * dt, my = (vy + pullY) * dt
        let (hx, hy) = move(self, mx, my, HH_BODY, HH_BODY)
        if hx && dy == 0 { nudge(mx, 0) }
        if hy && dx == 0 { nudge(0, my) }
        if hx && slip { vx = -vx * 0.3 }
        if hy && slip { vy = -vy * 0.3 }
        let moving = abs(vx) + abs(vy) > 12
        walkT = moving ? walkT + dt * (fever ? 1.6 : 1.0) : 0
        blinkT -= dt
        if blinkT < -0.12 { blinkT = hhRnd(1.5, 4.0) }
        if moving && (trail.isEmpty || abs(trail[trail.count - 1].0 - px) + abs(trail[trail.count - 1].1 - py) > 2) {
            trail.append((px, py))
            if trail.count > 60 { trail.removeFirst() }
        }
        updatePals(dt)
        fireT -= dt
        laserEnd = nil
        if firing {
            if laserT > 0 { fireLaser(dt) }
            if fireT <= 0 {
                fire()
                fireT = 0.16 * pow(0.87, Double(lv("rapid"))) * (fever ? 0.5 : 1.0)
            }
        }
        if inp.hit(.b) { bomb() }
    }

    /// Corner assist: running straight into the corner of a piece of furniture slides around it.
    func nudge(_ mx: Double, _ my: Double) {
        for k in 1 ... 5 {
            for sd in [-1.0, 1.0] {
                let kk = Double(k)
                if mx != 0 && !blocked(px + mx, py + sd * kk, HH_BODY, HH_BODY) {
                    move(self, 0, sd * min(kk, abs(mx) + 0.5), HH_BODY, HH_BODY)
                    return
                }
                if my != 0 && !blocked(px + sd * kk, py + my, HH_BODY, HH_BODY) {
                    move(self, sd * min(kk, abs(my) + 0.5), 0, HH_BODY, HH_BODY)
                    return
                }
            }
        }
    }

    func respawn() {
        deadT = nil
        inv = 2.5
        px = Double(W) / 2; py = 108
        vx = 0; vy = 0
        bombs = max(bombs, 2)
        cancelBullets()
        for e in toys {          // shoo the toys away from the middle
            let dx = e.x - px, dy = e.y - py
            let d = hypot(dx, dy)
            if d < 60 {
                let (ux, uy) = d > 1 ? hhNorm(dx, dy) : (1, 0)
                move(e, ux * (60 - d), uy * (60 - d), Double(e.w) * 0.4, Double(e.h) * 0.4, HHData.kinds[e.kind].flies)
            }
        }
    }

    func updatePals(_ dt: Double) {
        let n = lv("pal")
        for i in 0 ..< n {
            let idx = trail.count - 1 - 10 * (i + 1)
            let (tx, ty) = trail.isEmpty ? (px - 12, py) : trail[max(0, idx)]
            pals[i].x += (tx - pals[i].x) * min(1, dt * 6)
            pals[i].y += (ty - pals[i].y) * min(1, dt * 6)
            pals[i].t -= dt
            if pals[i].t <= 0 && deadT == nil && ["play", "warning", "intro"].contains(phase) {
                let (tg, d2) = targetOf(pals[i].x, pals[i].y)
                if let tg = tg, d2 < 150 * 150 {
                    let (ux, uy) = hhNorm(tg.0 - pals[i].x, tg.1 - pals[i].y)
                    shots.append(HHShot(pals[i].x, pals[i].y, ux * 200, uy * 200, 0.6, 1, 0, 0, 3))
                    pals[i].t = 0.55
                } else {
                    pals[i].t = 0.2
                }
            }
        }
    }

    func fire() {
        if shots.count > 300 { return }          // maxed-out power + FEVER + ricochet: keep it sane
        let x = px + fx * 5, y = py + fy * 5 - 1
        let base = atan2(fy, fx)
        let fever = hype.feverOn
        let big = lv("big")
        let dmg = 1.0 + 0.5 * Double(big), r = 2 + big / 2
        let kind = fever ? 2 : 0
        let pierce = fever ? 1 : 0
        let bounce = lv("bounce")
        var angs: [Double] = laserT > 0 ? [] : [0]
        for i in 0 ..< lv("spread") { angs += [0.18 * Double(i + 1), -0.18 * Double(i + 1)] }
        let tail = lv("tail")
        if tail > 0 { angs.append(.pi) }
        if tail >= 2 { angs += [.pi / 2, -.pi / 2] }
        for a in angs {                      // side and tail shots are a little weaker than the main one
            shots.append(HHShot(x, y, cos(base + a) * HH_SHOT_V, sin(base + a) * HH_SHOT_V, a == 0 ? dmg : dmg * 0.7, r, pierce, bounce, kind))
        }
        if yarnT > 0 {
            for a in [0.3, -0.3, 0.6, -0.6] {
                shots.append(HHShot(x, y, cos(base + a) * HH_SHOT_V, sin(base + a) * HH_SHOT_V, 0.8, 2, pierce, bounce, fever ? 2 : 1))
            }
        }
        shotN += 1
        if shotN % 2 == 1 && !angs.isEmpty { app.audio.play("shoot") }
    }

    func fireLaser(_ dt: Double) {
        let x = px + fx * 5, y = py + fy * 5 - 1
        var ex = x, ey = y
        for _ in 0 ..< 170 {
            let nx = ex + fx * 2, ny = ey + fy * 2
            if solidPt(nx, ny) { break }
            ex = nx; ey = ny
        }
        laserEnd = (ex, ey)
        laserTick -= dt
        if laserTick > 0 { return }
        laserTick = 0.07
        let dmg = 0.6 + 0.2 * Double(lv("big"))
        for e in toys where e.alive && e.spawnT <= 0 && hhSegDist(e.x, e.y, x, y, ex, ey) < Double(max(e.w, e.h)) / 2 {
            damage(e, dmg, fx, fy)
        }
        if let b = boss, b.state == "fight", b.z < 8 {
            for i in 0 ..< b.parts.count where b.parts[i].alive {
                let (qx, qy) = partPos(b, i)
                if hhSegDist(qx, qy, x, y, ex, ey) < Double(b.parts[i].r) + 2 { hurtPart(b, i, dmg); return }
            }
            if hhSegDist(b.x, b.y, x, y, ex, ey) < min(b.bw, b.bh) / 2 { hurtBoss(dmg) }
        }
    }

    func updateShots(_ dt: Double) {
        for sh in shots {
            sh.life -= dt
            let nx = sh.x + sh.vx * dt, ny = sh.y + sh.vy * dt
            if solidPt(nx, ny) {
                if sh.bounce > 0 {
                    sh.bounce -= 1
                    if solidPt(nx, sh.y) { sh.vx = -sh.vx }
                    if solidPt(sh.x, ny) { sh.vy = -sh.vy }
                    if !solidPt(nx, sh.y) && !solidPt(sh.x, ny) { sh.vx = -sh.vx; sh.vy = -sh.vy }
                } else {
                    sh.life = 0
                    parts.burst(sh.x, sh.y, 3, ["peach", "cream"], 30, 0.25)
                }
                continue
            }
            sh.x = nx; sh.y = ny
        }
        shots.removeAll { $0.life <= 0 }
    }

    // ------------------------------------------------------------------ toys
    func spawnLogic(_ dt: Double) {
        if mode == "bonus" {
            if st.mode == "parade" {
                for li in lanes.indices {
                    var ln = lanes[li]
                    while ln.done < ln.count && stageT >= ln.delay + Double(ln.done) * 0.32 {
                        let (side, pos) = doors[ln.door]
                        let (x, y, ix, iy) = HHData.doorSpawn(side, pos)
                        let e = spawnToy(ln.kind, x, y, false)
                        e.parade = true; e.gold = ln.done == ln.gold
                        e.spawnT = 0.15
                        let v = 62 + 2 * Double(tierN)
                        e.vx = ix * v; e.vy = iy * v
                        e.aux = hhRnd(0, 6.28)
                        ln.done += 1
                    }
                    lanes[li] = ln
                }
            }
            return
        }
        if mode != "normal" { return }
        let sp = st.spawns
        let alive = toys.filter { $0.alive && $0.kind != HH_GOLD }.count
        if alive < st.maxOn { waveT += dt }
        if spawnI < sp.count && alive == 0 && sp[spawnI].time - waveT > 1.0 { waveT = sp[spawnI].time - 1.0 }   // nobody left: hurry the next wave in
        while spawnI < sp.count && sp[spawnI].time <= waveT {
            let s = sp[spawnI]
            var di = s.door
            var (side, pos) = doors[di]
            var (x, y, ix, iy) = HHData.doorSpawn(side, pos)
            if abs(x - px) < 30 && abs(y - py) < 30 && deadT == nil {     // Biscuit is camping in the doorway: use another door
                di = (di + 1) % doors.count
                (side, pos) = doors[di]
                (x, y, ix, iy) = HHData.doorSpawn(side, pos)
            }
            let hw = Double(HHData.kinds[s.kind].w) / 2, hh = Double(HHData.kinds[s.kind].h) / 2
            spawnToy(s.kind, x + ix * (hw - 4), y + iy * (hh - 4), s.elite != 0, ix, iy)
            spawnI += 1
        }
        if goldT > 0 && goldT <= stageT {
            goldT = -1
            let (side, pos) = doors[Int.random(in: 0 ..< doors.count)]
            let (x, y, _, _) = HHData.doorSpawn(side, pos)
            spawnToy(HH_GOLD, x, y, false)
            hype.banner("GOLDEN MOUSE!", "CATCH IT!", color: "yellow", dur: 1.4, scale: 1, sound: "coin")
        }
    }

    @discardableResult
    func spawnToy(_ kind: Int, _ x: Double, _ y: Double, _ elite: Bool, _ ix: Double = 0, _ iy: Double = 1) -> HHToy {
        uid += 1
        let e = HHToy(uid, kind, x, y, elite, st.hpx)
        if kind == HH_CAR {
            let d = HH_DIRS8[hhDir8(px - x, py - y)]
            (e.vx, e.vy) = hhNorm(d.0, d.1)
        } else if [HH_TOP, HH_BALL, HH_MINIBALL].contains(kind) {    // diagonal into the room
            (e.vx, e.vy) = hhNorm(ix != 0 ? ix : hhSign(), iy != 0 ? iy : hhSign())
        } else if kind == HH_PLANE {
            e.aux = atan2(iy, ix)
        }
        e.face = px >= x ? 1 : -1
        spawned.append(e)
        if kind != HH_GOLD { parts.burst(x, y, 6, ["white", "gray"], 30, 0.3) }
        return e
    }

    func toySpeed(_ e: HHToy) -> Double { Double(HHData.kinds[e.kind].speed) * st.spd * spd * (e.elite ? 1.15 : 1.0) }

    func updateToy(_ e: HHToy, _ dt: Double) {
        e.t += dt
        e.flash = max(0, e.flash - dt)
        if e.spawnT > 0 { e.spawnT -= dt; return }
        let k = e.kind
        if e.parade {
            e.x += e.vx * dt
            e.y += e.vy * dt
            let wig = sin(e.t * 6 + e.aux) * 18
            e.x += -e.vy / 70 * wig * dt
            e.y += e.vx / 70 * wig * dt
            if e.x < Double(HH_IX0 - 8) || e.x > Double(HH_IX1 + 8) || e.y > Double(HH_IY1 + 8) || e.y < Double(HH_IY0 - 16) { e.alive = false }
            e.face = e.vx >= 0 ? 1 : -1
            return
        }
        var sp = toySpeed(e)
        let hw = Double(e.w) * 0.4, hh = Double(e.h) * 0.4
        var cx = px, cy = py
        if deadT != nil {          // Biscuit is down: the toys mill about
            cx = Double(W) / 2 + sin(e.seed) * 80; cy = 108 + cos(e.seed) * 50
        }
        var tx = cx, ty = cy
        if [HH_MOUSE, HH_BLOCKLET, HH_GOLEM, HH_SOCK, HH_DRUM, HH_VAC, HH_GOLD].contains(k) {
            if k == HH_MOUSE || k == HH_BLOCKLET, let le = laserEnd, (le.0 - e.x) * (le.0 - e.x) + (le.1 - e.y) * (le.1 - e.y) < 90 * 90 {
                tx = le.0; ty = le.1           // can't resist the red dot!
            }
            if k == HH_VAC {
                let prey = pets.filter { $0.state == "idle" }
                if let p = prey.min(by: { ($0.x - e.x) * ($0.x - e.x) + ($0.y - e.y) * ($0.y - e.y) < ($1.x - e.x) * ($1.x - e.x) + ($1.y - e.y) * ($1.y - e.y) }) {
                    tx = p.x; ty = p.y
                }
                if tierN >= 4 && deadT == nil {
                    let dx = e.x - px, dy = e.y - py
                    let d = hypot(dx, dy)
                    if d > 6 && d < 48 {
                        let pull = 24 + 2 * Double(tierN)
                        pullX += dx / d * pull
                        pullY += dy / d * pull
                        e.state = 1
                    } else {
                        e.state = 0
                    }
                }
            }
            var mult = 1.0
            if k == HH_MOUSE {                   // wind up, then dash
                e.timer -= dt
                if e.timer <= 0 {
                    e.aux = e.aux != 0 ? 0 : 1
                    e.timer = e.aux != 0 ? 0.45 : hhRnd(1.6, 2.8)
                }
                mult = e.aux != 0 ? 0 : (e.timer < 0.5 ? 1.5 : 1.0)
            }
            if k == HH_SOCK {                    // hop, hop, spit
                let hop = hhMod(e.t * 1.4, 1.0)
                mult = hop < 0.35 ? 2.4 : 0
                e.timer -= dt
                if e.timer <= 0 {
                    toyShot(e, 0, tierN >= 8 ? 3 : 1)
                    e.timer = st.fire * hhRnd(0.8, 1.3) / spd
                }
            }
            if k == HH_DRUM {
                e.timer -= dt
                mult = e.timer < 0.6 ? 0 : 1
                if e.timer <= 0 {
                    let n = min(12, 6 + tierN / 3)
                    let off = hhRnd(0, 1)
                    for i in 0 ..< n { bshot(e.x, e.y - 2, (Double(i) + off) * HH_TAU / Double(n), st.bv * 0.6 * spd, 1) }
                    e.timer = st.fire * 1.3 * hhRnd(0.9, 1.3) / spd
                    app.audio.play("paddle")
                }
            }
            if k == HH_GOLD {                    // runs away, leaves after a while
                if e.t < 9 {
                    tx = 2 * e.x - px; ty = 2 * e.y - py
                } else {
                    let (side, pos) = doors[0]
                    let ds = HHData.doorSpawn(side, pos)
                    tx = ds.0; ty = ds.1
                    if abs(tx - e.x) + abs(ty - e.y) < 10 {
                        e.alive = false
                        say(e.x, e.y - 10, "IT GOT AWAY!", "gray")
                        return
                    }
                }
                if Int(e.t * 15) != Int((e.t - dt) * 15) { parts.sparkle(e.x, e.y, rainbow(Int(e.t * 15))) }
            }
            e.jitT -= dt
            if e.jitT <= 0 { e.jitT = hhRnd(0.5, 1.0); e.jit = hhRnd(-0.6, 0.6) }
            var ang = atan2(ty - e.y, tx - e.x) + e.jit
            if e.stuck > 0 { e.stuck -= dt; ang += e.side * .pi / 2 }
            let vxx = cos(ang) * sp * mult, vyy = sin(ang) * sp * mult
            let (hx, hy) = move(e, vxx * dt, vyy * dt, hw, hh)
            if (hx || hy) && e.stuck <= 0 { e.stuck = hhRnd(0.3, 0.7); e.side = hhSign() }
            if abs(vxx) > 1 { e.face = vxx > 0 ? 1 : -1 }
        } else if [HH_CAR, HH_BALL, HH_MINIBALL, HH_TOP].contains(k) {
            if k == HH_TOP {
                sp *= 1 + min(1, e.t / 8)
                let a = atan2(e.vy, e.vx) + hhRnd(-3, 3) * dt
                e.vx = cos(a); e.vy = sin(a)
            }
            let (hx, hy) = move(e, e.vx * sp * dt, e.vy * sp * dt, hw, hh)
            if hx { e.vx = -e.vx }
            if hy { e.vy = -e.vy }
            if (hx || hy) && (k == HH_CAR || k == HH_TOP) && hhChance() < 0.45 {
                let d = HH_DIRS8[hhDir8(cx - e.x, cy - e.y)]
                (e.vx, e.vy) = hhNorm(d.0, d.1)
                if blocked(e.x + e.vx * 3, e.y + e.vy * 3, hw, hh) {
                    if hx { e.vx = -e.vx }
                    if hy { e.vy = -e.vy }
                }
            }
            if hx || hy { parts.burst(e.x, e.y, 2, ["white"], 30, 0.2) }
            e.face = e.vx >= 0 ? 1 : -1
        } else if k == HH_PLANE {
            let want = atan2(cy - e.y, cx - e.x)
            let diff = hhMod(want - e.aux + .pi, HH_TAU) - .pi
            e.aux += max(-1.7 * dt, min(1.7 * dt, diff))
            e.x += cos(e.aux) * sp * dt
            e.y += sin(e.aux) * sp * dt
            if e.x < Double(HH_IX0 + 4) || e.x > Double(HH_IX1 - 4) {
                e.aux = .pi - e.aux
                e.x = max(Double(HH_IX0 + 4), min(Double(HH_IX1 - 4), e.x))
            }
            if e.y < Double(HH_IY0 + 4) || e.y > Double(HH_IY1 - 4) {
                e.aux = -e.aux
                e.y = max(Double(HH_IY0 + 4), min(Double(HH_IY1 - 4), e.y))
            }
            e.face = cos(e.aux) >= 0 ? 1 : -1
        } else if k == HH_HELI {
            let gx = cx + sin(e.t * 0.9 + e.seed) * 50
            let gy = cy - 34 + cos(e.t * 1.3) * 10
            let (ux, uy) = hhNorm(gx - e.x, gy - e.y)
            e.x = max(Double(HH_IX0 + 6), min(Double(HH_IX1 - 6), e.x + ux * sp * dt))
            e.y = max(Double(HH_IY0 + 5), min(Double(HH_IY1 - 5), e.y + uy * sp * dt))
            e.face = ux >= 0 ? 1 : -1
            e.timer -= dt
            if e.timer <= 0 && deadT == nil {
                e.timer = st.fire * hhRnd(0.9, 1.4) / spd
                bullets.append(HHBullet(e.x, e.y + 4, 0, 12, 6, 1.3))
            }
        } else if k == HH_POPBOX {
            updatePopbox(e, dt, sp, hw, hh)
        }
    }

    func updatePopbox(_ e: HHToy, _ dt: Double, _ sp: Double, _ hw: Double, _ hh: Double) {
        e.timer -= dt
        if e.state == 0 {                        // waiting
            if e.timer <= 0 {
                let d = hypot(px - e.x, py - e.y)
                if d < 72 && deadT == nil {
                    e.state = 2; e.timer = 0.55
                    (e.ax, e.ay) = hhNorm(px - e.x, py - e.y)
                    app.audio.play("move")
                } else {
                    e.state = 1; e.timer = 0.5
                    let a = atan2(py - e.y, px - e.x) + hhRnd(-0.8, 0.8)
                    e.vx = cos(a); e.vy = sin(a)
                }
            }
        } else if e.state == 1 {                 // hop
            move(e, e.vx * sp * 2.2 * dt, e.vy * sp * 2.2 * dt, hw, hh)
            if e.timer <= 0 { e.state = 0; e.timer = hhRnd(0.5, 1.1) }
        } else if e.state == 2 {                 // wind-up (telegraph)
            if e.timer <= 0 { e.state = 3; e.timer = 0.6; app.audio.play("jump") }
        } else if e.state == 3 {                 // punch out and hold
            e.ext = min(44, e.ext + 260 * dt)
            if e.timer <= 0 { e.state = 4; e.timer = 0.4 }
        } else {                                 // pull the spring back in
            e.ext = max(0, e.ext - 140 * dt)
            if e.timer <= 0 && e.ext <= 0 { e.state = 0; e.timer = hhRnd(0.8, 1.6) }
        }
        e.face = px >= e.x ? 1 : -1
    }

    func separate() {
        let walkers = toys.filter { $0.alive && CHASERS.contains($0.kind) && $0.spawnT <= 0 }
        if walkers.count < 2 { return }
        for i in 0 ..< walkers.count {
            let a = walkers[i]
            for j in (i + 1) ..< walkers.count {
                let b = walkers[j]
                let dx = b.x - a.x, dy = b.y - a.y
                if abs(dx) < 8 && abs(dy) < 8 {
                    let (ux, uy) = abs(dx) + abs(dy) > 0.01 ? hhNorm(dx, dy) : (1, 0)
                    move(a, -ux * 0.6, -uy * 0.6, Double(a.w) * 0.4, Double(a.h) * 0.4)
                    move(b, ux * 0.6, uy * 0.6, Double(b.w) * 0.4, Double(b.h) * 0.4)
                }
            }
        }
    }

    func toyShot(_ e: HHToy, _ kind: Int, _ n: Int) {
        if deadT != nil { return }
        let a0 = atan2(py - e.y, px - e.x)
        for i in 0 ..< n { bshot(e.x, e.y, a0 + (Double(i) - Double(n - 1) / 2) * 0.3, st.bv * spd, kind) }
        app.audio.play("pop")
    }

    func bshot(_ x: Double, _ y: Double, _ ang: Double, _ sp: Double, _ kind: Int) {
        if bullets.count < 220 { bullets.append(HHBullet(x, y, cos(ang) * sp, sin(ang) * sp, kind)) }
    }

    func updateBullets(_ dt: Double) {
        var keep: [HHBullet] = []
        for b in bullets {
            b.t += dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            if b.kind == 6 {                       // toy bomb: fall, then burst
                b.vy *= max(0, 1 - dt * 2)
                b.fuse -= dt
                if b.fuse <= 0 {
                    let n = tierN < 14 ? 6 : 8
                    for i in 0 ..< n { bshot(b.x, b.y, Double(i) * HH_TAU / Double(n) + 0.2, st.bv * 0.6 * spd, 7) }
                    parts.burst(b.x, b.y, 10, ["red", "orange", "yellow"], 60, 0.4)
                    app.audio.play("pop")
                    continue
                }
            } else if b.kind == 3 && b.fuse > 0 {  // suction dust: dies at the vacuum
                b.fuse -= dt
                if b.fuse <= 0 { continue }
            }
            if solidPt(b.x, b.y) && !(b.kind == 3 && b.fuse > 0) {
                parts.burst(b.x, b.y, 3, ["white", "gray"], 25, 0.2)
                continue
            }
            keep.append(b)
        }
        bullets = keep
    }

    func cancelBullets(_ near: Double? = nil) {
        var keep: [HHBullet] = []
        var bits = items.filter { $0.kind == "c" }.count
        for b in bullets {
            if let n = near, (b.x - px) * (b.x - px) + (b.y - py) * (b.y - py) > n * n { keep.append(b); continue }
            if bits < 120 { items.append(HHItem(b.x, b.y, "c", hhRnd(-30, 30), hhRnd(-40, -10))); bits += 1 }
        }
        bullets = keep
    }

    // ------------------------------------------------------------------ pets and pick-ups
    func updatePets(_ dt: Double) {
        let roundup = mode == "bonus" && st.mode == "roundup"
        var keep: [HHPet] = []
        let mag = 40 * Double(lv("magnet"))
        for p in pets {
            p.t += dt
            if p.state != "idle" {
                p.fade += dt
                if p.fade < 0.6 { keep.append(p) }
                continue
            }
            p.timer -= dt
            let fast = p.kind == 2
            // flee from nearby toys (and in the roundup, from Biscuit - catch them!)
            var threat: (Double, Double)?
            for e in toys where e.alive && !e.parade && abs(e.x - p.x) < 32 && abs(e.y - p.y) < 32 { threat = (e.x, e.y); break }
            if roundup && abs(px - p.x) < 34 && abs(py - p.y) < 34 { threat = (px, py) }
            if mag > 0 && !roundup && hypot(px - p.x, py - p.y) < mag + 20 {
                let (ux, uy) = hhNorm(px - p.x, py - p.y)
                p.vx = ux * 40; p.vy = uy * 40
            } else if let th = threat {
                let (ux, uy) = hhNorm(p.x - th.0, p.y - th.1)
                let run = roundup ? (fast ? 58.0 : 46.0) : 40.0
                p.vx = ux * run; p.vy = uy * run
            } else if p.timer <= 0 {
                p.timer = hhRnd(0.8, 2.0)
                if hhChance() < 0.35 {
                    p.vx = 0; p.vy = 0
                } else {
                    let a = hhRnd(0, HH_TAU)
                    let v = (roundup ? 30.0 : 14.0) * (fast ? 1.6 : 1.0)
                    p.vx = cos(a) * v; p.vy = sin(a) * v
                }
            }
            let (hx, hy) = move(p, p.vx * dt, p.vy * dt, 3, 3)
            if hx { p.vx = -p.vx }
            if hy { p.vy = -p.vy }
            for e in toys where e.alive && e.kind == HH_VAC && e.spawnT <= 0 && abs(e.x - p.x) < 8 && abs(e.y - p.y) < 8 {   // caught by a vac-bot?
                p.state = "lost"; p.fade = 0
                lost += 1
                say(p.x, p.y - 10, "OH NO!", "gray")
                app.audio.play("trap")
                break
            }
            if p.state == "idle" && deadT == nil && abs(px - p.x) < 9 && abs(py - p.y) < 9 { rescue(p) }
            keep.append(p)
        }
        pets = keep
    }

    func rescue(_ p: HHPet) {
        p.state = "saved"; p.fade = 0
        saved += 1
        happyT = 0.8
        let au = app.audio
        parts.burst(p.x, p.y, 12, ["pink", "white", "hotpink"], 50, 0.6)
        if mode == "bonus" {
            if p.kind == 2 {
                hype.jackpot(5000 + 500 * tierN, sub: "GOLDEN HAMSTER!")
            } else {
                add((200 + 20 * tierN) * min(purr, 8), p.x, p.y - 8, "pink")
                if saved % 3 == 0 { purr = min(purrMax(), purr + 1) }
            }
            au.play("fruit")
            hype.hit(fever: 0.03)
            return
        }
        let before = purr
        purr = min(purrMax(), purr + 1)
        add(500 * purr, p.x, p.y - 8, "pink")
        say(p.x, p.y - 18, "PURR X\(purr)", "hotpink")
        hype.hit(fever: 0.05)
        au.play("bonus")
        if purr == purrMax() && before < purr && !maxSaid {
            maxSaid = true
            hype.banner("MAX PURR!", "X\(purr) POINTS", color: "hotpink", dur: 1.3, sound: "combo")
            hype.shower(24, "hearts")
        }
    }

    func drop(_ x: Double, _ y: Double) {
        var kind = DROPS[DROPS.count - 1].0
        if hype.lucky(0.012) {
            kind = "G"
        } else {
            var r = hhRnd(0, DROPS.reduce(0) { $0 + $1.1 })
            for (kd, w) in DROPS {
                r -= w
                if r <= 0 { kind = kd; break }
            }
        }
        items.append(HHItem(x, y, kind, hhRnd(-20, 20), hhRnd(-30, -10)))
    }

    func updateItems(_ dt: Double) {
        let mag = [0.0, 50, 90][lv("magnet")]
        let alive = deadT == nil
        var keep: [HHItem] = []
        for it in items {
            it.t += dt
            if it.kind == "c" {
                if it.t < 0.3 || !alive {
                    it.x += it.vx * dt
                    it.y += it.vy * dt
                    if it.t > 1.5 { continue }
                } else {
                    let (ux, uy) = hhNorm(px - it.x, py - it.y)
                    let v = 160 + it.t * 200
                    it.x += ux * v * dt
                    it.y += uy * v * dt
                }
                keep.append(it)
                continue
            }
            it.life -= dt
            if it.life <= 0 { continue }
            let d = hypot(px - it.x, py - it.y)
            if alive && d < mag {
                let (ux, uy) = hhNorm(px - it.x, py - it.y)
                it.x += ux * 150 * dt
                it.y += uy * 150 * dt
            } else {
                let k = min(1.0, dt * 5)
                it.vx -= it.vx * k
                it.vy -= it.vy * k
                if !solidPt(it.x + it.vx * dt, it.y + it.vy * dt) {
                    it.x += it.vx * dt
                    it.y += it.vy * dt
                }
            }
            keep.append(it)
        }
        items = keep
    }

    func collect(_ it: HHItem) {
        let k = it.kind, au = app.audio
        let x = it.x, y = it.y
        let t = tierN
        let nip = 1 + 0.25 * Double(lv("nip"))
        if k == "c" { score += 10 * hype.mult; return }
        if k == "F" { add(300 + 50 * t, x, y - 8, "sky"); au.play("eat"); return }
        au.play("powerup")
        switch k {
        case "Y":
            yarnT = 12 * nip
            say(x, y - 12, "YARN SPREAD!", "pink")
        case "L":
            laserT = 8 * nip
            say(x, y - 12, "LASER POINTER!", "red")
        case "N":
            say(x, y - 12, "CATNIP!", "lime")
            if !hype.feverOn { hype.startFever() } else { hype.feverT += 4 }
        case "X":
            if shield < 3 + lv("box") { shield += 1; say(x, y - 12, "BOX SHIELD!", "peach") } else { add(2000, x, y - 12, "peach") }
        case "H":
            if bombs < 3 + lv("bomb") { bombs += 1; say(x, y - 12, "HAIRBALL BOMB +1", "orange") } else { add(2000, x, y - 12, "orange") }
        case "G":
            hype.jackpot(10000 + 1000 * t, sub: "GOLDEN TUNA!")
        default: break
        }
    }

    // ------------------------------------------------------------------ collisions
    func collide() {
        for sh in shots {
            for e in toys {
                if sh.life <= 0 { break }
                if !e.alive || e.spawnT > 0 || sh.hits.contains(e.uid) { continue }
                if abs(sh.x - e.x) <= Double(e.w) / 2 + Double(sh.r) && abs(sh.y - e.y) <= Double(e.h) / 2 + Double(sh.r) {
                    damage(e, sh.dmg, sh.vx / HH_SHOT_V, sh.vy / HH_SHOT_V)
                    if sh.pierce > 0 { sh.pierce -= 1; sh.hits.append(e.uid) } else { sh.life = 0 }
                }
            }
            if sh.life > 0 && boss != nil { shotBoss(sh) }
        }
        shots.removeAll { $0.life <= 0 }
        if deadT != nil || ["victory", "tally", "between"].contains(phase) { return }
        var keep: [HHItem] = []
        for it in items {
            let r = it.kind == "c" ? 7.0 : 10.0
            if (it.x - px) * (it.x - px) + (it.y - py) * (it.y - py) < r * r { collect(it) } else { keep.append(it) }
        }
        items = keep
        if inv > 0 || phase == "clear" { return }
        for (i, b) in bullets.enumerated() {
            let r = Double(HHArt.bulletR[b.kind])
            if r > 0 && abs(b.x - px) <= HH_HB + r && abs(b.y - py) <= HH_HB + r {
                bullets.remove(at: i)
                hurt()
                return
            }
        }
        for e in toys where e.alive && e.spawnT <= 0 && !e.parade {
            if abs(e.x - px) <= Double(e.w) * 0.4 + HH_HB && abs(e.y - py) <= Double(e.h) * 0.4 + HH_HB {
                if e.kind == HH_GOLD { continue }
                hurt()
                return
            }
            if e.kind == HH_POPBOX && e.ext > 6 {
                let hx = e.x + e.ax * e.ext, hy = e.y + e.ay * e.ext
                if abs(hx - px) <= 5 + HH_HB && abs(hy - py) <= 5 + HH_HB { hurt(); return }
            }
        }
        if let b = boss, b.state == "fight" { bossHitsPlayer(b) }
    }

    func damage(_ e: HHToy, _ dmg: Double, _ ux: Double = 0, _ uy: Double = 0) {
        if !e.alive { return }
        if e.parade { killToy(e); return }
        e.hp -= dmg
        if e.hp > 0 {
            if e.flash <= 0 { app.audio.play("tin") }
            e.flash = 0.1
            if e.kind != HH_GOLEM && e.kind != HH_POPBOX {
                move(e, ux * 2, uy * 2, Double(e.w) * 0.4, Double(e.h) * 0.4, HHData.kinds[e.kind].flies)
            }
            return
        }
        killToy(e)
    }

    func killToy(_ e: HHToy) {
        if !e.alive { return }
        e.alive = false
        let t = tierN
        let au = app.audio
        parts.burst(e.x, e.y, 14, HH_TOY_COLORS[e.kind]!, 80, 0.6)
        au.play([HH_GOLEM, HH_VAC, HH_DRUM].contains(e.kind) ? "explode" : "pop")
        if e.kind == HH_GOLD {
            parts.burst(e.x, e.y, 40, ["yellow", "orange", "white"], 140, 1.0)
            hype.jackpot(15000 + 1500 * t, sub: "GOLDEN MOUSE +\((15000 + 1500 * t) * hype.mult)")
            hype.hit()
            return
        }
        if e.parade {
            hits += 1
            if e.gold {
                add(3000 + 300 * t, e.x, e.y - 8, "yellow")
                hype.shower(16, "coins")
                au.play("coin")
            } else {
                add(100 + 10 * t, e.x, e.y - 8, "yellow")
            }
            hype.hit(fever: 0.02)
            return
        }
        let base = Int(Double(HHData.kinds[e.kind].points) * (1 + 0.1 * Double(t))) / 10 * 10 * (e.elite ? 2 : 1)
        let pts = base * purr + hype.comboBonus(5)
        add(pts, e.x, e.y - 8, purr > 1 ? "hotpink" : "yellow")
        hype.hit(fever: 0.03)
        if [HH_GOLEM, HH_VAC, HH_DRUM].contains(e.kind) { app.shake(2, 0.15) }
        if e.kind == HH_BALL {
            for sd in [-1.0, 1.0] {
                let m = spawnToy(HH_MINIBALL, e.x + sd * 3, e.y, false)
                m.spawnT = 0
                var qx = -e.vy * sd, qy = e.vx * sd            // the halves fly apart sideways
                if abs(qx) + abs(qy) < 0.1 { qx = sd; qy = 1 }
                (m.vx, m.vy) = hhNorm(qx + e.vx * 0.5, qy + e.vy * 0.5)
            }
        } else if e.kind == HH_GOLEM {
            for i in 0 ..< 3 {
                let m = spawnToy(HH_BLOCKLET, e.x + Double(i - 1) * 5, e.y, false)
                m.spawnT = 0.1
                m.seed = Double(i)
            }
        }
        if !e.minion && hhChance() < 0.07 + 0.002 * Double(t) + (e.elite ? 0.1 : 0) { drop(e.x, e.y) }
    }

    func hurt() {
        if inv > 0 || deadT != nil { return }
        let au = app.audio
        if shield > 0 {
            shield -= 1
            inv = 1.2
            cancelBullets(44)
            parts.burst(px, py, 20, ["peach", "brown", "yellow"], 90, 0.5)
            au.play("pop")
            say(px, py - 16, "BOX SAVED YOU!", "peach")
            app.shake(2, 0.2)
            return
        }
        lives -= 1
        deaths += 1
        deadT = 1.6
        yarnT = 0; laserT = 0
        purr = purrBase()
        hype.breakCombo()
        au.play("hurt")
        app.shake(4, 0.4)
        hype.flash("red", 0.2)
        parts.burst(px, py, 30, ["cream", "white", "orange", "peach"], 100, 1.0)
    }

    func bomb() {
        if bombs <= 0 || deadT != nil || !["intro", "play", "warning"].contains(phase) { return }
        bombs -= 1
        bombT = 0.6
        bombX = px; bombY = py
        bombHit = []
        inv = max(inv, 1.4)
        cancelBullets()
        if let b = boss, b.state == "fight" {
            if b.atk == "lane" || b.atk == "suck" { b.atk = nil; b.rest = 1.0; b.ext = 0 }
            hurtBoss(b.maxhp * (0.035 + 0.01 * Double(lv("bomb"))))
        }
        hype.flash("white", 0.3)
        hype.hitstop(0.08)
        app.shake(5, 0.5)
        app.audio.play("boom")
        say(px, py - 20, "HAIRBALL BOMB!", "orange")
    }

    func updateBomb(_ dt: Double) {
        bombT = max(0, bombT - dt)
        let rad = (1 - bombT / 0.6) * (100 + 15 * Double(lv("bomb")))
        for e in toys where e.alive && !bombHit.contains(e.uid) && (e.x - bombX) * (e.x - bombX) + (e.y - bombY) * (e.y - bombY) < rad * rad {
            bombHit.insert(e.uid)
            damage(e, 6 + 2 * Double(lv("bomb")))
        }
    }

    // ------------------------------------------------------------------ draw
    override func render(_ s: Surface) {
        let t = self.t
        if let bg = bg { s.blit(bg, 0, 0) }
        for it in items { HHArt.item(s, it.kind, Int(it.x), Int(it.y), t + it.t, it.life) }
        for p in pets { drawPet(s, p) }
        if let b = boss, b.state == "fight" { drawTells(s, b) }
        for e in toys.sorted(by: { $0.y < $1.y }) { drawToy(s, e) }
        if let b = boss { drawBoss(s, b) }
        if lights && (phase == "intro" || phase == "play") { drawDark(s) }
        drawDoors(s)
        for sh in shots { HHArt.hairball(s, Int(sh.x), Int(sh.y), sh.kind != 3 ? sh.r : 1, sh.kind != 3 ? sh.kind : 0, t) }
        drawCat(s)
        if let le = laserEnd {
            let x0 = Int(px + fx * 5), y0 = Int(py + fy * 5 - 1)
            let ex = Int(le.0), ey = Int(le.1)
            s.line(col("red"), x0, y0, ex, ey, width: 3)
            s.line(col(Int(t * 30) % 2 == 1 ? "white" : "pink"), x0, y0, ex, ey)
            s.circle(col("red"), ex, ey, 3)
            s.fillRect(col("white"), ex - 1, ey - 1, 2, 2)
        }
        for bl in bullets { HHArt.bullet(s, bl.kind, Int(bl.x), Int(bl.y), t, bl.fuse) }
        if let b = boss, b.state == "fight", b.atk == "lane", b.ext > 0, b.kind != 2 {
            let (mx, my) = muzzle(b)
            let L = laneLen(b) * b.ext
            for (ax, ay) in b.lanes {
                let ex = Int(mx + ax * L), ey = Int(my + ay * L)
                s.line(col(b.kind != 3 ? "hotpink" : "lavender"), Int(mx), Int(my), ex, ey, width: 7)
                s.line(col("white"), Int(mx), Int(my), ex, ey, width: 3)
            }
        }
        if bombT > 0 {
            let r = Int((1 - bombT / 0.6) * (100 + 15 * Double(lv("bomb"))))
            s.circle(col("orange"), Int(bombX), Int(bombY), r, width: 4)
            if r > 6 { s.circle(col("cream"), Int(bombX), Int(bombY), r - 5, width: 2) }
        }
        parts.draw(s)
        floats.draw(s)
        drawHud(s)
        if phase == "intro" { drawIntro(s) } else if phase == "warning" { drawWarning(s) } else if phase == "tally" && tally != nil { drawTally(s) }
    }

    override func draw(_ s: Surface) {
        super.draw(s)
        if paused { drawPower(s, 160) }
    }

    /// Pause screen: the upgrades collected so far.
    func drawPower(_ s: Surface, _ y: Int) {
        let owned = HH_POOL.filter { lv($0.id) > 0 }
        if owned.isEmpty { return }
        let x0 = W / 2 - owned.count * 11 + 11
        for (i, u) in owned.enumerated() {
            let cx = x0 + i * 22
            s.circle(col(u.color), cx, y, 10)
            s.circle(col("ink"), cx, y, 8)
            let sp = sprite(HH_ICONS[u.id]!)
            s.blit(sp, cx - sp.w / 2, y - sp.h / 2)
            for p in 0 ..< u.max { s.fillRect(col(p < lv(u.id) ? "yellow" : "darkgray"), cx - u.max * 2 + p * 4, y + 12, 3, 3) }
        }
    }

    /// Doors flash and show an arrow just before a toy walks in.
    func drawDoors(_ s: Surface) {
        if mode != "normal" || phase != "play" { return }
        let sp = st.spawns
        var hot = Set<Int>()
        var i = spawnI
        while i < sp.count && sp[i].time - waveT < 0.9 { hot.insert(sp[i].door); i += 1 }
        let blink = Int(t * 10) % 2 == 1
        for di in hot.sorted() {
            let (side, pos) = doors[di]
            let r = HHData.doorRect(side, pos)
            s.fillRect(col(blink ? "red" : "orange"), r.x + (side == 1 ? 2 : 0), r.y + (side == 0 ? 2 : 0),
                       r.w - (side != 0 ? 2 : 0), r.h - (side == 0 ? 2 : 0))
            let (sx, sy, ix, iy) = HHData.doorSpawn(side, pos)
            let ax = sx + ix * 8, ay = sy + iy * 8
            s.polygon(col(blink ? "yellow" : "white"), [(ax + ix * 4, ay + iy * 4), (ax - iy * 4, ay + ix * 4), (ax + iy * 4, ay - ix * 4)])
        }
    }

    func drawPet(_ s: Surface, _ p: HHPet) {
        let x = Int(p.x), y = Int(p.y)
        let name = p.kind == 0 ? "hh_kitten" : "hh_hamster"
        let remap: [Character: Character]? = p.kind == 0 ? HHArt.kittenCoats[p.coat % 4] : (p.kind == 2 ? ["o": "y", "w": "w"] : nil)
        if p.state == "saved" {
            let yy = y - Int(p.fade * 40)
            s.blit(sprite(name, 0, remap: remap), x - 4, yy - 4)
            s.blit(sprite("heart"), x - 3, yy - 12)
            return
        }
        if p.state == "lost" {
            if Int(p.fade * 20) % 2 == 0 { s.blit(sprite(name, 0, remap: HHArt.white), x - 4, y - 4 + Int(p.fade * 6)) }
            return
        }
        let moving = abs(p.vx) + abs(p.vy) > 1
        let fr = moving ? Int(t * 8) % 2 : 0
        let hop = moving ? -Int(abs(sin(p.t * 9)) * 2) : 0
        s.blit(sprite(name, fr, flip: p.vx < 0, remap: remap), x - 4, y - 4 + hop)
        if p.kind == 2 && Int(t * 8) % 2 == 1 { s.fillRect(col("white"), x + 3, y - 5 + hop, 1, 1) }
        if mode == "normal" && Int(t * 2 + p.t) % 3 == 0 {     // "help!" bubble
            s.fillRect(col("white"), x - 2, y - 13, 5, 6)
            drawText(s, "!", x - 2, y - 13, "hotpink", shadow: nil)
        }
    }

    func drawToy(_ s: Surface, _ e: HHToy) {
        let x = Int(e.x), y = Int(e.y)
        if e.spawnT > 0 {
            let r = Int((0.4 - e.spawnT) / 0.4 * 7) + 1
            s.circle(col("white"), x, y, r, width: 1)
            return
        }
        var fr = Int(t * 8 + e.seed) % 2
        if e.kind == HH_SOCK { fr = e.timer < 0.45 ? 1 : 0 } else if e.kind == HH_DRUM { fr = e.timer < 0.6 && Int(t * 16) % 2 == 1 ? 1 : 0 } else if e.kind == HH_POPBOX {
            fr = e.state == 2 && Int(t * 20) % 2 == 1 ? 1 : 0
        } else if e.kind == HH_MOUSE && e.aux != 0 { fr = Int(t * 16) % 2 }
        var remap: [Character: Character]? = nil
        if e.flash > 0 { remap = HHArt.white } else if e.kind == HH_GOLD || e.gold { remap = HHArt.golden } else if e.elite { remap = HHArt.elite } else if e.kind == HH_BLOCKLET {
            remap = HHArt.blockColours[Int(e.seed * 7) % 4]
        }
        let sp = sprite(HH_TOY_SPRITE[e.kind]!, fr, flip: e.face < 0, remap: remap)
        var hop = e.kind == HH_SOCK ? -Int(abs(sin(e.t * 1.4 * .pi)) * 3) : 0
        if e.kind == HH_POPBOX && e.state == 1 { hop = -Int(sin(max(0, e.timer) / 0.5 * .pi) * 5) }
        s.fillRect(col("black"), x - e.w / 2 + 1, y + e.h / 2 - 1, e.w - 2, 2)
        s.blit(sp, x - sp.w / 2, y - sp.h / 2 + hop)
        if e.kind == HH_POPBOX && e.ext > 0 {
            let hx = e.x + e.ax * e.ext, hy = e.y + e.ay * e.ext
            HHArt.spring(s, Double(x), Double(y - 4), hx, hy, t)
            HHArt.clown(s, Int(hx), Int(hy), 5, t)
        }
        if e.kind == HH_VAC && e.state == 1 && Int(t * 12) % 2 == 1 {
            for i in 0 ..< 3 {
                let a = t * 3 + Double(i) * 2.1
                let r = 30 - hhMod(t * 40 + Double(i) * 10, 26)
                s.fillRect(col("white"), Int(e.x + cos(a) * r), Int(e.y + sin(a) * r), 1, 1)
            }
        }
        if e.kind == HH_HELI && e.timer < 0.4 { s.fillRect(col(Int(t * 16) % 2 == 1 ? "red" : "yellow"), x - 1, y + 4, 2, 2) }
    }

    /// LIGHTS OUT: only a pool of light around Biscuit (and the toys' glowing eyes).
    func drawDark(_ s: Surface) {
        let r1 = 44, r2 = 58
        let cx = Int(px), cy = Int(py)
        let far = rgba(8, 4, 20, 225), mid = rgba(8, 4, 20, 140)
        for y in HH_IY0 ..< HH_IY1 {
            let dy = y - cy
            if abs(dy) >= r2 { s.fillRect(far, HH_IX0, y, HH_IX1 - HH_IX0, 1); continue }
            let h2 = Int(Double(r2 * r2 - dy * dy).squareRoot())
            s.fillRect(far, HH_IX0, y, max(0, cx - h2 - HH_IX0), 1)
            s.fillRect(far, cx + h2, y, max(0, HH_IX1 - cx - h2), 1)
            let h1 = abs(dy) < r1 ? Int(Double(r1 * r1 - dy * dy).squareRoot()) : 0
            if h1 > 0 {
                s.fillRect(mid, cx - h2, y, h2 - h1, 1)
                s.fillRect(mid, cx + h1, y, h2 - h1, 1)
            } else {
                s.fillRect(mid, cx - h2, y, h2 * 2, 1)
            }
        }
        for e in toys where e.alive && e.spawnT <= 0 {
            let c = col(Int(t * 3 + e.seed) % 4 != 0 ? "red" : "yellow")
            s.fillRect(c, Int(e.x) - 2, Int(e.y) - 2, 1, 1)
            s.fillRect(c, Int(e.x) + 2, Int(e.y) - 2, 1, 1)
        }
    }

    func catView() -> (String, Bool) {
        let (dx, dy) = HH_DIRS8[face8]
        if dx != 0 { return ("hh_cat_side", dx < 0) }
        return dy < 0 ? ("hh_cat_back", false) : ("hh_cat_front", false)
    }

    func drawCat(_ s: Surface) {
        let x = Int(px), y = Int(py)
        for i in 0 ..< lv("pal") {             // kitten pals
            s.blit(sprite("hh_kitten", Int(t * 8) % 2, remap: HHArt.kittenCoats[(i + 1) % 4]), Int(pals[i].x) - 4, Int(pals[i].y) - 4)
        }
        if deadT != nil {
            let spin = Int(t * 12) % 2 == 0
            s.blit(sprite("hh_cat_front", 0, flip: spin), x - 6, y - 7)
            for sd in [-1, 1] {                 // X eyes
                let ex = x + sd * 3 - (sd < 0 ? 1 : 0)
                s.fillRect(col("cream"), ex - 1, y - 3, 3, 2)
                s.fillRect(col("black"), ex - 1, y - 3, 1, 1)
                s.fillRect(col("black"), ex + 1, y - 3, 1, 1)
                s.fillRect(col("black"), ex, y - 2, 1, 1)
            }
            for i in 0 ..< 3 {
                let a = t * 6 + Double(i) * HH_TAU / 3
                s.fillRect(col("yellow"), Int(Double(x) + cos(a) * 9), Int(Double(y - 10) + sin(a) * 3), 2, 2)
            }
            return
        }
        if inv > 0 && Int(inv * 12) % 2 == 1 && ["play", "intro", "warning"].contains(phase) { return }
        var (name, flip) = catView()
        let happy = happyT > 0 || ["clear", "tally", "victory"].contains(phase)
        if happy && phase != "play" { name = "hh_cat_front"; flip = false }
        let fr = walkT > 0 ? 1 + Int(walkT * 8) % 2 : 0
        var bob = fr == 1 ? -1 : 0
        if happy && phase != "play" { bob = -Int(abs(sin(t * 6)) * 4) }
        var remap: [Character: Character]? = nil
        if hype.feverOn { remap = ["c": FEVER_TINT[Int(t * 12) % 7]] }
        s.blit(sprite(name, fr, flip: flip, remap: remap), x - 6, y - 7 + bob)
        if name == "hh_cat_front" {
            let base: Character = remap?["c"] ?? "c"
            let body = col(TINT_NAME[base] ?? "cream")
            let ey = y - 3 + bob
            if happy {                           // ^^ eyes
                for ex in [x - 3, x + 2] {
                    s.fillRect(body, ex - 1, ey, 3, 2)
                    s.fillRect(col("black"), ex - 1, ey + 1, 1, 1)
                    s.fillRect(col("black"), ex, ey, 1, 1)
                    s.fillRect(col("black"), ex + 1, ey + 1, 1, 1)
                }
            } else if blinkT < 0 {
                for ex in [x - 3, x + 2] {
                    s.fillRect(body, ex, ey, 1, 2)
                    s.fillRect(col("black"), ex - 1, ey + 1, 3, 1)
                }
            }
        }
        if shield > 0 {                          // if it fits, she sits: a cardboard box around her
            let bx = x - 7, by = y + 1 + bob
            s.fillRect(col("black"), bx, by, 14, 7)
            s.fillRect(col("peach"), bx + 1, by + 1, 12, 5)
            s.fillRect(col("brown"), bx + 1, by + 3, 12, 1)
            s.fillRect(col("yellow"), x - 1, by + 1, 2, 5)
            s.line(col("peach"), bx, by, bx - 3, by - 3)
            s.line(col("peach"), bx + 13, by, bx + 16, by - 3)
            if shield > 1 { drawText(s, "\(shield)", bx + 16, by, "peach", shadow: "black") }
        }
        if ["play", "intro", "warning"].contains(phase) {      // aim guide: where the hairballs go
            let c = (locked || (auto && app.input.down(.a))) ? "yellow" : "gray"
            for (i, d) in [10.0, 15.0, 20.0].enumerated() {
                let gx = Int(px + fx * d), gy = Int(py + fy * d)
                let big = i == 2
                s.fillRect(col(c), gx - (big ? 1 : 0), gy - (big ? 1 : 0), big ? 2 : 1, big ? 2 : 1)
            }
        }
        if happyT > 0 && phase == "play" && Int(t * 6) % 2 == 1 { s.blit(sprite("heart"), x + 5, y - 14) }
    }

    func drawHud(_ s: Surface) {
        if hype.combo >= 3 {
            let w = textWidth("\(hype.combo) COMBO") + 8
            panel(s, IRect(W / 2 - w / 2, 11, w, 12), fill: "black", border: "peach", radius: 3, shadow: false)
        }
        drawText(s, String(format: "%07d", score), 4, 2, "white")
        drawText(s, "@\(max(0, lives))", 50, 2, "pink")
        if let b = boss, phase != "warning" {
            bossBar(s, b.name, b.hp, b.maxhp, t, y: 0, x: 74, w: 172)
        } else {
            drawText(s, "HI " + String(format: "%07d", max(best, score)), W / 2, 2, "lavender", align: .center)
        }
        let c = mode == "boss" ? "red" : (mode == "bonus" ? "mint" : "yellow")
        drawText(s, "STAGE \(stageN)", W - 4, 2, c, align: .right)
        let y = HH_IY1 + 1
        for i in 0 ..< min(bombs, 6) {           // hairball bombs
            let x = 6 + i * 8
            s.circle(col("choco"), x, y + 3, 3)
            s.circle(col("peach"), x, y + 3, 2)
        }
        let x0 = 8 + min(bombs, 6) * 8
        for i in 0 ..< min(shield, 4) {          // boxes
            s.fillRect(col("peach"), x0 + i * 7, y + 1, 5, 5)
            s.fillRect(col("brown"), x0 + i * 7, y + 3, 5, 1)
        }
        if mode != "boss" {
            let pc = purr >= purrMax() ? rainbow(0, t) : "hotpink"
            s.blit(sprite("heart"), 96, y)
            drawText(s, "PURR X\(purr)", 105, y, pc, shadow: nil)
        }
        var x = 168
        for (name, left, full, c) in [("hh_yarn", yarnT, 12.0, "pink"), ("hh_laser", laserT, 8.0, "red")] {
            if left > 0 && !(left < 2 && Int(t * 8) % 2 == 1) {
                s.blit(sprite(name), x, y - 1)
                s.fillRect(col("darkgray"), x + 10, y + 3, 20, 2)
                s.fillRect(col(c), x + 10, y + 3, Int(20 * min(1, left / full)), 2)
                x += 34
            }
        }
        if !hype.feverOn {
            let fx0 = W - 44
            s.fillRect(col("darkgray"), fx0, y + 2, 40, 3)
            s.fillRect(col(hype.fever > 0.8 ? rainbow(0, t) : "lime"), fx0, y + 2, Int(40 * hype.fever), 3)
            drawText(s, "NIP", fx0 - 20, y, "gray", shadow: nil)
        }
    }

    func stageHint() -> String { "HOLD FIRE = AIM LOCK + STRAFE" }

    func drawIntro(_ s: Surface) {
        let a = introT
        let drop = Int((1 - easeOut(min(1, a / 0.25))) * -60) + Int(easeOut(max(0, (a - 2.1) / 0.3)) * -90)
        let room = HHData.rooms[st.room]
        if mode == "bonus" {
            let y0 = 104 + drop
            panel(s, IRect(40, y0, 240, 40), fill: "ink", border: "mint")
            if st.mode == "parade" {
                drawText(s, "TOY PARADE!", W / 2, y0 + 6, "mint", scale: 2, align: .center, outline: "ink")
                drawText(s, "POP THEM ALL - THEY CAN'T HURT YOU", W / 2, y0 + 26, "white", align: .center)
            } else {
                drawText(s, "KITTEN ROUNDUP!", W / 2, y0 + 6, "pink", scale: 2, align: .center, outline: "ink")
                drawText(s, "CATCH EVERY RUNAWAY PET!", W / 2, y0 + 26, "white", align: .center)
            }
            return
        }
        let new = st.new
        let tall = 46 + (new >= 0 ? 16 : 0) + 9 * mods.count + (stageN == 1 ? 10 : 0)
        let y0 = 124 - tall / 2 + drop                // below the banner slot (CHECKPOINT!, 1UP!)
        panel(s, IRect(56, y0, 208, tall), fill: "ink", border: "yellow")
        drawText(s, "STAGE \(stageN)", W / 2, y0 + 5, "yellow", scale: 2, align: .center, outline: "ink")
        drawText(s, "\(room.name) \((stageN - 1) % 10 + 1)/10", W / 2, y0 + 23, "lavender", align: .center)
        drawText(s, "\"\(room.quip)\"", W / 2, y0 + 33, "cream", align: .center, shadow: nil)
        var y = y0 + 44
        for m in mods {
            drawText(s, "\(m): \(HHData.modText[m] ?? "")", W / 2, y, "orange", align: .center, shadow: nil)
            y += 9
        }
        if new >= 0 {
            let sp = sprite(HH_TOY_SPRITE[new]!, Int(t * 6) % 2)
            s.blit(sp, 76 - sp.w / 2, y + 6 - sp.h / 2)
            drawText(s, "NEW: \(HHData.kinds[new].name)", 90, y, "lime", shadow: nil)
            drawText(s, HHData.kinds[new].intro, 90, y + 8, "white", shadow: nil)
            y += 16
        }
        if stageN == 1 { drawText(s, stageHint(), W / 2, y, "mint", align: .center, shadow: nil) }
    }

    func drawWarning(_ s: Surface) {
        for by in [52, 118] {
            s.fillRect(col("yellow"), 0, by, W, 8)
            let off = Int(t * 40) % 12
            for i in -1 ..< 29 {
                let x = Double(i * 12 + off), Y = Double(by)
                s.polygon(col("black"), [(x, Y), (x + 5, Y), (x + 1, Y + 7), (x - 4, Y + 7)])
            }
        }
        if Int(t * 4) % 2 == 0 {
            drawText(s, "WARNING", W / 2, 68, "red", scale: 3, align: .center, outline: "ink")
        } else {
            drawText(s, "WARNING", W / 2, 68, "white", scale: 3, align: .center, outline: "red")
        }
        if let b = boss {
            drawText(s, "\(b.name) IS COMING", W / 2, 94, "white", align: .center, outline: "ink")
            drawText(s, HHData.bosses[b.kind].intro, W / 2, 105, "peach", align: .center, outline: "ink")
        }
    }

    func drawTally(_ s: Surface) {
        guard let tl = tally else { return }
        let n = tl.lines.count
        let h = 34 + n * 11 + 26
        let y0 = 96 - h / 2
        panel(s, IRect(50, y0, 220, h), fill: "ink", border: "yellow")
        drawText(s, tl.title, W / 2, y0 + 6, mode == "boss" ? rainbow(0, t) : "yellow", align: .center)
        for i in 0 ..< tl.shown {
            let (label, v) = tl.lines[i]
            let age = tl.t - (0.35 + Double(i) * 0.4)
            let shown = Int(Double(v) * min(1, age / 0.3))
            let y = y0 + 20 + i * 11
            drawText(s, label, 60, y, label.hasPrefix("PERFECT") ? rainbow(i, t) : "white", shadow: nil)
            drawText(s, v > 0 ? "\(shown)" : "-", 260, y, v > 0 ? "lime" : "gray", align: .right, shadow: nil)
        }
        if tl.shown >= n {
            let y = y0 + 22 + n * 11
            s.fillRect(col("lavender"), 60, y - 2, 200, 1)
            drawText(s, "TOTAL", 60, y + 2, "yellow", shadow: nil)
            drawText(s, "\(tl.total * hype.mult)", 260, y + 2, "yellow", align: .right, shadow: nil)
            let bob = Int(abs(sin(t * 5)) * 2)
            s.blit(sprite("hh_cat_front", 0), 62, y + 12 - bob)
            drawText(s, "BISCUIT: \"\(tl.quip)\"", 80, y + 15, "cream", shadow: nil)
        }
    }

    // ------------------------------------------------------------------ carousel preview
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        s.fill(col("brown"))
        for y in stride(from: 0, to: h, by: 8) {
            s.fillRect(col("choco"), 0, y, w, 1)
            for x in stride(from: ((y / 8) % 3) * 21, to: w, by: 64) { s.fillRect(col("choco"), x, y, 1, 8) }
        }
        s.fillRect(col("peach"), 0, 0, w, 9)
        for x in stride(from: 3, to: w, by: 8) { s.fillRect(col("orange"), x, 1, 2, 6) }
        s.fillRect(col("brown"), 0, 7, w, 3)
        HHArt.furniture(s, 0, 6, 16, 32, 20, 0)
        HHArt.furniture(s, 3, w - 22, 14, 16, 16, 0)
        let cx = w / 2 + Int(sin(t * 1.3) * Double(w / 4))
        let cy = h - 16
        s.blit(sprite("hh_cat_back", 1 + Int(t * 8) % 2), cx - 6, cy - 7)
        for i in 0 ..< 3 {
            let yy = cy - 12 - (Int(t * 120) + i * 16) % 46
            HHArt.hairball(s, cx, yy, 2, 0, t)
        }
        for i in 0 ..< 3 {
            let mx = Int(hhMod(t * 30 + Double(i) * Double(w) / 3, Double(w + 20))) - 10
            let my = 30 + i * 8 + Int(sin(t * 3 + Double(i)) * 3)
            if (mx - cx) * (mx - cx) > 36 || i > 0 { s.blit(sprite("hh_mouse", Int(t * 8 + Double(i)) % 2), mx - 5, my - 4) }
        }
        s.blit(sprite("hh_kitten", Int(t * 4) % 2), w - 18, h - 14)
        if Int(t * 2) % 2 == 1 { s.blit(sprite("heart"), w - 17, h - 22) }
    }
}
