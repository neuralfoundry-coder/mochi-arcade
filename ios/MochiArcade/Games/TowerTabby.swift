// TOWER TABBY - single-screen climbing platformer with Mikan the chubby orange tabby, 200-stage campaign
// (port of games/tower_tabby.py - keep in step). Stages come from the Python generator through
// GameData.json("tower_tabby"); entities and drawing helpers live in TowerTabbyArt.swift, bosses in TowerTabbyBoss.swift.
import Foundation

private let GRAV = 700.0, JUMP_V = 165.0, RUN = 72.0, CLIMB = 46.0
private let POUNCE_VX = 165.0, POUNCE_VY = 125.0, BED_V = 252.0, MAX_FALL = 260.0
private let PW = 10.0, PH = 11.0
private let BOPPABLE: Set<String> = ["yarn", "cone", "mouse", "spider", "ball", "marble", "moth", "dust"]
private let ROLLERS: Set<String> = ["yarn", "marble", "dust", "mouse", "ball", "bot"]

private func ttIcon(_ name: String) -> (Surface, Int, Int, Double) -> Void {
    { s, cx, cy, _ in s.blit(sprite(name, 0, flip: false, remap: nil, scale: 2), cx - 9, cy - 9) }
}

let TT_UPGRADES: [Upgrade] = [
    Upgrade(id: "speed", name: "QUICK PAWS", desc: "RUN FASTER", color: "lime", draw: ttIcon("tt_i_speed"), max: 3),
    Upgrade(id: "climb", name: "CLIMB CLAWS", desc: "CLIMB 35%|FASTER", color: "mint", draw: ttIcon("tt_i_climb"), max: 3),
    Upgrade(id: "pounce", name: "POUNCE PRO", desc: "LONGER POUNCE|QUICKER|RECOVERY", color: "orange", draw: ttIcon("tt_i_pounce"), max: 3),
    Upgrade(id: "heart", name: "NINE LIVES", desc: "+1 LIFE|RIGHT NOW", color: "pink", draw: ttIcon("tt_i_heart"), max: 3),
    Upgrade(id: "bell", name: "BELL COLLAR", desc: "BLOCKS 1 HIT|EVERY STAGE|LV2: REFILLS", color: "yellow", draw: ttIcon("tt_i_bell"), max: 2),
    Upgrade(id: "magnet", name: "FISH MAGNET", desc: "PULLS FISH|AND ITEMS|TO YOU", color: "red", draw: ttIcon("tt_i_magnet"), max: 3),
    Upgrade(id: "wand", name: "LONG WAND", desc: "WAND LASTS|LONGER, WIDER|SWATS", color: "lavender", draw: ttIcon("tt_i_wand"), max: 3),
    Upgrade(id: "lucky", name: "LUCKY TAIL", desc: "MORE DROPS|AND GOLDEN|FISH", color: "hotpink", draw: ttIcon("tt_i_lucky"), max: 3),
    Upgrade(id: "nap", name: "CATNAP AURA", desc: "HAZARDS MOVE|8% SLOWER", color: "teal", draw: ttIcon("tt_i_nap"), max: 3),
    Upgrade(id: "kitty", name: "KITTEN CALL", desc: "KITTENS RUN|TO YOU +50%|KITTEN BONUS", color: "peach", draw: ttIcon("tt_i_kitty"), max: 2),
]

final class TowerTabby: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD     WALK  (UP / DOWN: CLIMB)", "JUMP    JUMP (HOLD = HIGHER)", "POUNCE  LEAP AND CATCH YARN & CONES",
                            "PAD DOWN AT A BOX TUNNEL: DIVE IN"]
    static let helpSkip = 4

    private var stageMusic = "tower"
    override var music: String? { stageMusic }
    override var buttons: [Action: String] { [.a: "JUMP", .b: "POUNCE"] }
    override var buttonOrder: [Action] { [.a, .b] }
    override var fourWay: Bool { false }

    var lives: Int, spd: Double, stage: Int
    var ups: [String: Int] = [:]
    var nextExtra = 30000
    var picks = 0, afterPicks = "", pickTitle = "POWER UP!"
    var wasFever = false
    var kittensSaved = 0
    var tally: [(String, Int, Double)] = [], tallyI = 0, tallyT = 0.0, tallyTotal = 0

    var sd = TTStage()
    var kind = "normal", tierN = 0
    var theme = TTTheme(name: "", wa: "deep", wb: "ink", carpet: "pink", carpetD: "hotpink", post: "peach", stripe: "brown",
                        style: "window", accent: "yellow")
    var mods: [String] = []
    var segs: [TTSeg] = [], posts: [TTPost] = [], hams: [TTHam] = []
    var warps: [((Int, Int), (Int, Int))] = []
    var goal: (Double, Double)?
    var hz: [TTHaz] = [], shots: [TTShot] = [], items: [TTPickup] = [], kits: [TTKitten] = []
    var hs = 1.0
    var wind = 0
    var fishTotal = 0, fishGot = 0
    var start = (0.0, 0.0)
    var p = TTPlayer(0, 0)
    var shield = false, shieldT = 0.0
    var wandT = 0.0, nipT = 0.0, milkT = 0.0
    var levelT = 0.0, hurry = false, missed = false
    var chain = 0, chainT = 0.0, bestChain = 0, bops = 0, gotKits = 0
    var kaw: TTKaw?
    var mothT = 0.0, mothLeft = 0.0
    var boss: TTBoss?
    var wandSpawn = 6.0
    var bonusN = 0, bonusGot = 0, timeLeft = 20.0
    var state = "intro", stateT = 0.0, introState = "intro"
    var field = Surface(W, H)

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        let d = opt["difficulty"] ?? "normal"
        lives = LIVES[d] ?? 3
        spd = SPEEDS[d] ?? 1
        stage = max(1, min(STAGES, Int(opt["stage"] ?? opt["start"] ?? "1") ?? 1))
        super.init(app, info, opt)
        for u in TT_UPGRADES { ups[u.id] = 0 }
        hype.comboY = 14
        loadStage()
        let head = min(5, tier(stage))
        if head > 0 {           // starting from a checkpoint: catch up on the upgrades a full run would have
            picks = head; afterPicks = "intro"; pickTitle = "HEAD START!"
            state = "picks"
        }
    }

    func up(_ id: String) -> Int { ups[id] ?? 0 }

    // ------------------------------------------------------------------ stage setup
    func loadStage() {
        let all = TTData.stages
        sd = all.isEmpty ? TTStage() : all[min(all.count, stage) - 1]
        kind = sd.k
        tierN = tier(stage)
        if !TTData.themes.isEmpty { theme = TTData.themes[min(sd.th, TTData.themes.count - 1)] }
        mods = sd.mods
        buildTree()
        hz = []; shots = []; items = []; kits = []
        hs = sd.hs * spd * (1 - 0.08 * Double(up("nap")))
        wind = mods.contains("wind") ? (stage % 2 == 1 ? 1 : -1) : 0
        spawnPlaced()
        for (c, k) in sd.fish {
            let x = Double(c * TT_CW + 8)
            let gold = hype.lucky(0.015 + 0.01 * Double(up("lucky")))
            items.append(TTPickup(gold ? "gfish" : "fish", x, surface(k, x) - 5, 100 + 20 * tierN))
        }
        for (c, k, kd) in sd.it {
            let x = Double(c * TT_CW + 8)
            items.append(TTPickup(kd, x, surface(k, x) - 6))
        }
        for (i, (c, k)) in sd.kit.enumerated() {
            let x = Double(c * TT_CW + 8)
            kits.append(TTKitten(x, surface(k, x), (stage + i) % TT_KITTEN_COLORS.count))
        }
        fishTotal = sd.fish.count
        fishGot = 0
        let sx = Double((sd.lv.first?.firstIndex(of: "P") ?? 2) * TT_CW + 8)
        start = (sx, TT_FLOOR)
        p = TTPlayer(start.0, start.1)
        shield = up("bell") > 0
        shieldT = 0
        wandT = 0; nipT = 0; milkT = 0
        levelT = 0; hurry = false; missed = false
        chain = 0; chainT = 0; bestChain = 0; bops = 0; gotKits = 0
        kaw = (kind == "normal" || kind == "bonus") ? TTKaw(sd.rate) : nil
        if let k = kaw, kind == "bonus" {
            k.party = true
            k.rate = sd.bt == "fish" ? 0.24 : 0.42
            k.throwT = 1.2
        }
        mothT = sd.moth
        mothLeft = mothT * 0.6
        boss = kind == "boss" ? TTBoss(sd, self) : nil
        wandSpawn = 6
        bonusN = 0; bonusGot = 0
        timeLeft = Double(sd.time)
        renderField()
        reached(stage)
        if kind == "boss" {
            state = "warning"
            stageMusic = "boss"
            app.audio.play("warning")
        } else {
            state = "intro"
            stageMusic = kind == "bonus" ? "bonus" : (tierN >= 10 ? "tower_high" : "tower")
            app.audio.play("stage")
            if kind == "bonus" {
                hype.banner("BONUS STAGE!", sd.bt == "fish" ? "CATCH THE FISH RAIN!" : "POUNCE THE RAINBOW YARN!", dur: 2.0, rainbow: true)
            }
        }
        introState = state
        stateT = 0
        wasFever = false
        app.audio.music(stageMusic)
    }

    private func segClass(_ ch: Character) -> String {
        switch ch { case "S": return "bed"; case "X": return "box"; case "<", ">": return "belt"; default: return "plank" }
    }

    func buildTree() {
        segs = []; posts = []; hams = []; warps = []
        for k in 0 ..< min(6, sd.lv.count) {
            let row = sd.lv[k]
            var c = 0
            while c < TT_NC {
                let ch = row[c]
                if TT_SOLID.contains(ch) {
                    let kd = segClass(ch)
                    let c0 = c
                    while c < TT_NC && TT_SOLID.contains(row[c]) && segClass(row[c]) == kd && (kd != "belt" || row[c] == ch) { c += 1 }
                    segs.append(TTSeg(c0 * TT_CW, c * TT_CW, k, sd.sl[k], kd, kd == "belt" ? (ch == "<" ? -1 : 1) : 0))
                } else if ch == "~" {
                    let c0 = c
                    while c < TT_NC && row[c] == "~" { c += 1 }
                    hams.append(TTHam(Double(c0 * TT_CW), Double(c * TT_CW - 32), k, 0.5 * Double(hams.count % 2)))
                } else {
                    c += 1
                }
            }
            for (c, ch) in row.enumerated() where ch == "H" || ch == "R" {
                posts.append(TTPost(c * TT_CW + 8, k, ch == "R", sd.sl))
            }
        }
        for ((k1, c1), (k2, c2)) in sd.warpPairs() { warps.append(((c1 * TT_CW + 8, k1), (c2 * TT_CW + 8, k2))) }
        if let g = sd.find("G") {
            let gx = Double(g.1 * TT_CW + 8)
            goal = (gx, ttYAt(5, sd.sl[5], gx))
        } else {
            goal = nil
        }
    }

    func surface(_ k: Int, _ x: Double) -> Double { ttYAt(k, sd.sl[k], x) }

    func spawnPlaced() {
        for (kd, c, k) in sd.en {
            let x = Double(c * TT_CW + 8)
            let h: TTHaz
            if kd == "spider" {
                h = TTHaz("spider", x, surface(k + 1, x) + 8, 4)
                h.ay = surface(k + 1, x) + 7
                h.k = k
            } else if kd == "spritz" {
                h = TTHaz("spritz", c == 0 ? 5 : Double(W - 5), surface(k, x) - 9, 5)
                h.k = k
                h.dir = c == 0 ? 1 : -1
                h.cool = Double.random(in: 1.0 ... 2.6)
            } else {
                h = TTHaz(kd, x, surface(k, x) - 5, 5)
                h.k = k
            }
            h.life = 1e9
            hz.append(h)
        }
    }

    /// The static part of the tree (posts, ropes, planks, the cushion, box tunnels) drawn once per stage.
    func renderField() {
        field = Surface(W, H)
        for po in posts { TTArt.post(field, po, theme) }
        for sg in segs where sg.kind == "plank" { TTArt.plank(field, sg, theme, sd) }
        for ((x1, k1), (x2, k2)) in warps {
            for (x, k) in [(x1, k1), (x2, k2)] { TTArt.tunnel(field, Double(x), surface(k, Double(x))) }
        }
        if let g = goal { TTArt.cushion(field, g.0, g.1) }
    }

    // ------------------------------------------------------------------ upgrades
    func runSpeed() -> Double { RUN * (1 + 0.12 * Double(up("speed"))) * (nipT > 0 ? 1.45 : 1.0) }
    func climbSpeed() -> Double { CLIMB * (1 + 0.35 * Double(up("climb"))) * (nipT > 0 ? 1.3 : 1.0) }
    func wandReach() -> Double { 16 + 4 * Double(up("wand")) }

    func took(_ uid: String?) {
        guard let uid = uid else {
            add(10000)
            hype.banner("ALL MAXED!", "+10000", color: "yellow", dur: 1.4)
            return
        }
        ups[uid, default: 0] += 1
        if uid == "heart" { lives += 1 }
        if uid == "bell" { shield = true }
        if uid == "nap" { hs = sd.hs * spd * (1 - 0.08 * Double(up("nap"))) }
        let name = TT_UPGRADES.first { $0.id == uid }?.name ?? uid
        hype.banner(name, "LEVEL \(up(uid))", color: "mint", dur: 1.1, scale: 1)
    }

    // ------------------------------------------------------------------ physics
    /// Highest shelf / hammock surface under x between top and bottom.
    func support(_ x: Double, _ top: Double, _ bottom: Double) -> (Double, TTPlat)? {
        var best: Double?
        var what: TTPlat?
        for sg in segs {
            if sg.gone > 0 || x < Double(sg.x0) || x >= Double(sg.x1) { continue }
            let y = sg.y(x)
            if top <= y && y <= bottom && (best == nil || y < best!) { best = y; what = sg }
        }
        for hm in hams where hm.x0 <= x && x < hm.x1 && top <= hm.y && hm.y <= bottom && (best == nil || hm.y < best!) {
            best = hm.y; what = hm
        }
        if let b = best, let w = what { return (b, w) }
        return nil
    }

    /// support() over a body's feet: the centre and +-feet pixels (ledge forgiveness for Mikan).
    func supportW(_ x: Double, _ top: Double, _ bottom: Double, _ feet: Double) -> (Double, TTPlat)? {
        var r = support(x, top, bottom)
        if feet > 0 && r == nil {
            for fx in [x - feet, x + feet] {
                if let r2 = support(fx, top, bottom), r == nil || r2.0 < r!.0 { r = r2 }
            }
        }
        return r
    }

    /// Walk / fall a body whose position is (centre x, feet y). Returns "wall", "land" or "".
    @discardableResult
    func moveBody(_ b: TTBody, _ dt: Double, _ half: Double, grav: Double = GRAV, walls: Bool = true, feet: Double = 0) -> String {
        var ev = ""
        let g = b.ground
        if let hm = g as? TTHam { b.x += hm.dx }
        if let sg = g as? TTSeg, sg.kind == "belt" { b.x += Double(sg.belt) * 32 * dt }
        b.x += (b.vx + Double(wind) * 14) * dt
        if walls {
            if b.x < half { b.x = half; ev = "wall" } else if b.x > Double(W) - half { b.x = Double(W) - half; ev = "wall" }
        }
        if g != nil {
            if let (y, ng) = supportW(b.x, b.y - 4, b.y + 5, feet) {
                b.y = y; b.ground = ng; b.vy = 0
                return ev
            }
            b.ground = nil
            b.vy = 0
        }
        b.vy = min(b.vy + grav * dt, MAX_FALL)
        let prev = b.y
        b.y += b.vy * dt
        if b.vy >= 0, let (y, ng) = supportW(b.x, prev - 1, b.y, feet) {
            b.y = y; b.ground = ng; b.vy = 0
            ev = "land"
        }
        return ev
    }

    /// Hazards keep their centre in (x, y); reuse the body mover with feet = y + r.
    @discardableResult
    func moveHaz(_ h: TTHaz, _ dt: Double, grav: Double = GRAV) -> String {
        h.y += h.r
        let ev = moveBody(h, dt, h.r, grav: grav)
        h.y -= h.r
        return ev
    }

    // ------------------------------------------------------------------ update
    override func tick(_ dt: Double) {
        stateT += dt
        if state == "picks" {
            if picks > 0 {
                picks -= 1
                pickUpgrade(TT_UPGRADES, ups, title: pickTitle) { [unowned self] id in self.took(id) }
            } else if afterPicks == "next" {
                nextStage()
            } else {
                state = introState; stateT = 0
            }
            return
        }
        if state == "tally" { updateTally(dt); return }
        if state == "won" { return }
        if state == "intro" && stateT > 1.9 {
            state = "play"; stateT = 0
        } else if state == "warning" && stateT > 2.8 {
            state = "play"; stateT = 0
            p.inv = max(p.inv, 1.0)
        }
        let st = state
        for hm in hams { hm.update(t) }
        for sg in segs {
            sg.boing = max(0, sg.boing - dt)
            if sg.gone > 0 {
                sg.gone -= dt
                if sg.gone <= 0 {
                    sg.stand = 0
                    let mx = Double(sg.x0 + sg.x1) / 2
                    parts.burst(mx, sg.y(mx), 6, ["peach", "brown"], 30, 0.3)
                }
            }
        }
        if ["intro", "warning", "play", "bossdown", "timeup"].contains(st) || (st == "clear" && kind != "normal") {
            updatePlayer(dt)
        } else if st == "dead" {
            updateDead(dt)
        } else if st == "clear" {
            p.anim += dt
        }
        if st == "play" {
            levelT += dt
            if kind == "normal" && levelT > Double(sd.par) && !hurry {
                hurry = true
                hype.banner("HURRY UP!", "KAW IS GETTING CRANKY", color: "red", dur: 1.3, sound: "warning")
            }
        }
        wandT = max(0, wandT - dt)
        nipT = max(0, nipT - dt)
        milkT = max(0, milkT - dt)
        if shieldT > 0 {
            shieldT -= dt
            if shieldT <= 0 && up("bell") >= 2 { shield = true; app.audio.play("powerup") }
        }
        chainT -= dt
        if chainT <= 0 { chain = 0 }
        if kaw != nil { updateKaw(dt) }
        if st != "intro" && st != "warning" { updateHazards(dt) }
        updateShots(dt)
        updateItems(dt)
        updateKittens(dt)
        if let b = boss {
            b.update(self, dt)
            if st == "play" {
                wandSpawn -= dt
                if wandSpawn <= 0 {
                    wandSpawn = 11
                    if wandT <= 0 && !items.contains(where: { $0.kind == "wand" }) { spawnWand() }
                }
            }
        }
        if kind == "bonus" { updateBonus(dt) }
        if mothT > 0 && st == "play" { updateMoths(dt) }
        if st == "bossdown" && stateT > 3.8 { state = "clear"; stateT = 0 }
        if st == "timeup" && stateT > 1.6 { startTally() }
        if st == "clear" && stateT > 2.4 { startTally() }
        checkExtra()
        let fever = hype.feverOn
        if fever != wasFever && kind == "normal" { app.audio.music(fever ? "fever" : stageMusic) }
        wasFever = fever
    }

    func checkExtra() {
        while score >= nextExtra {
            lives += 1
            nextExtra = nextExtra < 80000 ? 80000 : nextExtra + 100000
            hype.banner("1UP!", "EXTRA LIFE", color: "pink", dur: 1.4, sound: "extra")
            hype.shower(16, "hearts")
        }
    }

    func nextStage() {
        if stage >= STAGES {
            state = "won"
            hype.banner("TOP CAT!!", "ALL 200 PERCHES WON", dur: 3.0, rainbow: true, sound: "win")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 STAGES CLIMBED!", delay: 3.5)
            return
        }
        stage += 1
        loadStage()
    }

    // ------------------------------------------------------------------ the player
    func updatePlayer(_ dt: Double) {
        let inp = app.input, au = app.audio
        p.inv = max(0, p.inv - dt)
        p.pcd -= dt
        p.anim += dt
        p.swipe = max(0, p.swipe - dt)
        p.trail.append((p.x, p.y))
        if p.trail.count > 60 { p.trail.removeFirst() }
        if p.warpT > 0 {
            p.warpT -= dt
            if p.warpT <= 0, let (x, k) = p.warpTo {
                p.x = Double(x); p.y = surface(k, Double(x))
                p.ground = support(p.x, p.y - 2, p.y + 2)?.1
                p.inv = max(p.inv, 0.6)
                au.play("pop")
                parts.burst(p.x, p.y - 6, 10, ["peach", "brown", "white"], 50, 0.4)
            }
            return
        }
        if p.climb != nil { updateClimb(dt); return }
        let mx = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
        if !p.pounce {
            let target = Double(mx) * runSpeed()
            if mods.contains("slick") && p.ground != nil {
                p.vx += (target - p.vx) * min(1, dt * 3.5)
            } else {
                p.vx = target
            }
            if mx != 0 { p.face = mx }
        }
        if let g = p.ground, !((g as? TTSeg)?.kind == "bed") {
            p.coyote = 0.08
            p.airPounce = true
        } else {
            p.coyote -= dt
        }
        p.jbuf = inp.hit(.a) ? 0.12 : p.jbuf - dt
        if p.jbuf > 0 && p.coyote > 0 && !p.pounce {
            p.vy = -JUMP_V
            p.ground = nil
            p.jbuf = 0; p.coyote = 0
            au.play("jump")
        }
        if p.vy < 0 && !inp.down(.a) && !p.pounce && !p.boost { p.vy *= pow(0.86, dt * 60) }
        if inp.hit(.b) && p.pcd <= 0 && (p.ground != nil || p.airPounce) { startPounce() }
        if inp.down(.up) && !p.pounce, let po = postHere(true) { grab(po); return }
        if inp.hit(.down) && p.ground != nil {
            if let w = tunnelHere() {
                p.warpT = 0.45; p.warpTo = w
                p.vx = 0
                au.play("trap")
                parts.burst(p.x, p.y - 6, 8, ["peach", "brown"], 40, 0.3)
                return
            }
            if let po = postHere(false) {
                grab(po)
                p.y += 1
                return
            }
        }
        let wasAir = p.ground == nil
        let ev = moveBody(p, dt, 6, feet: 3)
        if let g = p.ground {
            if wasAir {
                p.pounce = false
                p.boost = false
                if ev == "land" { parts.burst(p.x, p.y, 3, ["white"], 20, 0.2) }
            }
            if let sg = g as? TTSeg {
                if sg.kind == "bed" {
                    boing(p, sg)
                } else if sg.kind == "box" && (state == "play" || state == "intro") {
                    sg.stand += dt
                    if sg.stand > 0.45 { collapse(sg) }
                }
            }
        }
        if p.pounce { p.pounceT += dt }
        if state == "play" { checkGoal() }
    }

    func startPounce() {
        let lv = Double(up("pounce"))
        p.pounce = true
        p.pounceT = 0
        p.vx = Double(p.face) * POUNCE_VX * (1 + 0.1 * lv)
        p.vy = p.ground != nil ? -POUNCE_VY : -70
        if p.ground == nil { p.airPounce = false }
        p.ground = nil
        p.pcd = 0.5 - 0.08 * lv
        app.audio.play("shoot")
        parts.burst(p.x, p.y - 2, 5, ["white", "peach"], 40, 0.3)
    }

    func boing(_ b: TTBody, _ sg: TTSeg) {
        b.vy = -BED_V
        b.ground = nil
        sg.boing = 0.25
        if b === p {
            p.pounce = false
            p.boost = true
            p.coyote = 0; p.jbuf = 0
            app.audio.play("jump")
            parts.burst(b.x, b.y, 6, ["pink", "white"], 40, 0.3)
        }
    }

    func collapse(_ sg: TTSeg) {
        sg.gone = 3.2
        app.audio.play("brick")
        for i in 0 ..< (sg.x1 - sg.x0) / 4 {
            parts.burst(Double(sg.x0 + i * 4 + 2), sg.y(Double(sg.x0 + i * 4)), 1, ["peach", "brown"], 60, 0.6)
        }
        if p.ground === sg { p.ground = nil }
    }

    func postHere(_ up: Bool) -> TTPost? {
        for po in posts {
            if abs(p.x - Double(po.x)) > 6 { continue }
            if up {
                if p.y - PH <= po.bot && p.y > po.top + 1.5 && p.y <= po.bot + 2 { return po }
                if po.rope && p.ground == nil && p.y > po.top + 1.5 && p.y - PH <= po.bot { return po }
            } else if p.ground != nil && abs(p.y - po.top) < 3 {
                return po
            }
        }
        return nil
    }

    func tunnelHere() -> (Int, Int)? {
        for (a, b) in warps {
            for (here, there) in [(a, b), (b, a)] {
                let (x, k) = here
                if abs(p.x - Double(x)) < 8 && abs(p.y - surface(k, Double(x))) < 3 { return there }
            }
        }
        return nil
    }

    func grab(_ po: TTPost) {
        p.climb = po
        p.x = Double(po.x)
        p.vx = 0; p.vy = 0
        p.ground = nil
        p.pounce = false
    }

    func updateClimb(_ dt: Double) {
        guard let po = p.climb else { return }
        let inp = app.input
        let dy = (inp.down(.down) ? 1 : 0) - (inp.down(.up) ? 1 : 0)
        p.y += Double(dy) * climbSpeed() * dt
        if dy != 0 { p.anim += dt * 2 }
        if p.y <= po.top {
            p.y = po.top
            p.climb = nil
            p.ground = support(p.x, p.y - 3, p.y + 3)?.1
            return
        }
        if po.rope {
            if p.y - PH > po.bot { p.climb = nil }
        } else if p.y >= po.bot {
            p.y = po.bot
            p.climb = nil
            p.ground = support(p.x, p.y - 3, p.y + 3)?.1
            return
        }
        if inp.hit(.a) && p.climb != nil {
            let mx = (inp.down(.right) ? 1 : 0) - (inp.down(.left) ? 1 : 0)
            p.climb = nil
            p.vy = -JUMP_V * 0.6
            p.vx = Double(mx) * runSpeed()
            if mx != 0 { p.face = mx }
            app.audio.play("jump")
        }
    }

    func checkGoal() {
        guard let (gx, gy) = goal, p.ground != nil else { return }
        if abs(p.x - gx) < 11 && abs(p.y - gy) < 4 { reachGoal() }
    }

    func reachGoal() {
        guard let (gx, gy) = goal else { return }
        state = "clear"; stateT = 0
        p.x = gx; p.y = gy - 6
        p.vx = 0; p.vy = 0
        if let k = kaw { k.mode = "flee"; k.modeT = 0 }
        for h in hz where h.kind != "spritz" {
            h.dead = true
            parts.burst(h.x, h.y, 6, ["white", h.color], 40, 0.4)
        }
        hz.removeAll { $0.dead }
        shots = []
        if levelT < Double(sd.par) * 0.5 {
            hype.banner("SPEED CLIMB!!", "+5000", dur: 1.8, rainbow: true, sound: "win")
            hype.shower(50, "confetti")
            add(5000)
        } else {
            hype.banner("TOP CAT!", "THE CUSHION IS MINE", color: "yellow", dur: 1.6, sound: "levelup")
        }
        hype.shower(14, "hearts")
        add(1000, gx, gy - 24, "yellow")
    }

    func hurt() {
        if p.inv > 0 || state != "play" || p.warpT > 0 || nipT > 0 { return }
        if shield {
            shield = false
            shieldT = 18
            p.inv = 1.5
            app.audio.play("tin")
            app.shake(2, 0.2)
            parts.burst(p.x, p.y - 6, 16, ["yellow", "white"], 70, 0.5)
            floats.add(p.x, p.y - 18, "DING!", "yellow")
            return
        }
        lives -= 1
        missed = true
        hype.breakCombo()
        state = "dead"; stateT = 0
        p.climb = nil
        p.ground = nil
        p.vy = -200
        p.vx = -Double(p.face) * 30
        app.audio.play("hurt")
        app.shake(3, 0.3)
        hype.flash("red", 0.15)
        parts.burst(p.x, p.y - 6, 18, ["orange", "white", "peach"], 80, 0.7)
    }

    func updateDead(_ dt: Double) {
        p.vy += GRAV * dt
        p.x += p.vx * dt
        p.y += p.vy * dt
        if stateT > 1.4 {
            if lives <= 0 {
                state = "over"
                endGame(false, "STAGE \(stage) - \(kittensSaved) KITTENS SAVED")
                return
            }
            respawn()
        }
    }

    func respawn() {
        var x = start.0
        if let b = boss, abs(b.x - x) < 90 { x = b.x > Double(W) / 2 ? 24 : Double(W) - 24 }   // boss fights: far side
        p = TTPlayer(x, start.1)
        p.inv = 2.2
        state = "play"; stateT = 0
        shots = []
        hz = hz.filter { $0.life > 1e8 }
        if let k = kaw { k.throwT = 2.2; k.mode = "fly" }
        wandT = 0
    }

    // ------------------------------------------------------------------ KAW
    func updateKaw(_ dt: Double) {
        guard let k = kaw else { return }
        k.modeT += dt
        k.taunt -= dt
        if k.mode == "flee" {
            k.y -= 70 * dt
            k.x += Double(k.face) * -40 * dt
            return
        }
        if k.stun > 0 {
            k.stun -= dt
            k.y = min(34, k.y + 30 * dt)
            return
        }
        k.y += (22 + sin(t * 3) * 3 - k.y) * min(1, dt * 3)
        if k.mode == "perch" {
            if k.modeT > 1.0 {
                k.mode = "fly"; k.modeT = 0
                k.tx = Double.random(in: 24 ... Double(W - 24))
            }
        } else {
            let d = k.tx - k.x
            let sp = (hurry ? 80.0 : 52.0) * (k.party ? 1.3 : 1.0)
            if abs(d) < 3 {
                if Double.random(in: 0 ..< 1) < 0.35 {
                    k.mode = "perch"; k.modeT = 0
                } else {
                    k.tx = Double.random(in: 24 ... Double(W - 24))
                }
            } else {
                k.x += max(-sp * dt, min(sp * dt, d))
                k.face = d > 0 ? 1 : -1
            }
        }
        if state != "play" || milkT > 0 { return }
        if k.aim > 0 {
            k.aim -= dt
            if k.aim <= 0 { kawThrow(k) }
            return
        }
        k.throwT -= dt * (hurry ? 1.6 : 1.0)
        if k.throwT <= 0 {
            k.throwT = k.rate * Double.random(in: 0.8 ... 1.2)
            if k.party {
                kawThrow(k)
            } else {
                k.aim = 0.42
                k.nextKind = sd.mix.randomElement() ?? "yarn"
            }
        }
        if k.taunt <= 0 && !k.party { k.taunt = Double.random(in: 6 ... 11) }
    }

    func kawThrow(_ k: TTKaw) {
        let x = max(14, min(Double(W) - 14, k.x)), y = k.y + 8
        if k.party {
            if sd.bt == "fish" {
                let gold = Double.random(in: 0 ..< 1) < 0.05
                let it = TTPickup(gold ? "gfish" : "fish", Double.random(in: 12 ... Double(W - 12)), 14, 150 + 15 * tierN)
                it.falling = true; it.life = 5
                it.vy = 20
                items.append(it)
            } else {
                let h = TTHaz("yarn", x, y, 5)
                h.harmless = true
                h.gold = Double.random(in: 0 ..< 1) < 0.06
                h.life = 9
                h.color = h.gold ? "yellow" : TT_YARN_COLORS.randomElement()!
                hz.append(h)
            }
            bonusN += 1
            return
        }
        if hype.lucky(0.012 + 0.006 * Double(up("lucky"))) {
            let it = TTPickup("coin", x, y)
            it.falling = true
            items.append(it)
            hype.banner("KAW DROPPED HIS SHINY!", color: "yellow", dur: 1.2, scale: 1, sound: "bonus")
            return
        }
        spawnDrop(k.nextKind ?? "yarn", x, y)
        app.audio.play("move")
    }

    @discardableResult
    func spawnDrop(_ kd: String, _ x: Double, _ y: Double) -> TTHaz {
        let h: TTHaz
        switch kd {
        case "cone":
            h = TTHaz("cone", x, y, 4)
            h.vy = 40
        case "cushion":
            h = TTHaz("cushion", x, y, 7)
            h.mode = "fall"
            h.ay = support(x, y + 7, Double(H))?.0 ?? TT_FLOOR
        case "ball":
            h = TTHaz("ball", x, y, 4)
            h.life = 11
        case "marble":
            h = TTHaz("marble", x, y, 3)
            h.life = 13
        default:
            h = TTHaz("yarn", x, y, mods.contains("heavy") ? 6 : 5)
        }
        hz.append(h)
        return h
    }

    // ------------------------------------------------------------------ hazards
    func updateHazards(_ dt: Double) {
        let frozen = milkT > 0
        for h in hz {
            if h.dead { continue }
            h.age += dt
            h.t += dt
            if h.batted { updateBatted(h, dt); continue }
            if !frozen {
                h.life -= dt
                hazStep(h, dt)
            }
            if h.life <= 0 || h.y > Double(H + 20) {
                h.dead = true
                if h.kind == "yarn" && h.life <= 0 { parts.burst(h.x, h.y, 5, [h.color, "white"], 30, 0.3) }
                continue
            }
            if state != "play" || p.warpT > 0 || h.kind == "spritz" { continue }
            hazVsPlayer(h, frozen)
        }
        hz.removeAll { $0.dead }
    }

    func hazStep(_ h: TTHaz, _ dt: Double) {
        let sp = hs
        switch h.kind {
        case "yarn", "marble", "dust":
            let base = (["yarn": 50.0, "marble": 88.0, "dust": 58.0][h.kind] ?? 50) * sp * (mods.contains("heavy") && h.kind == "yarn" ? 1.2 : 1)
            if h.kind == "yarn" && !h.harmless { h.r = max(2.5, h.r - dt * 0.18) }
            h.vx = h.ground != nil ? Double(h.dir) * base : h.vx * 0.98
            let was = h.ground
            let ev = moveHaz(h, dt)
            if ev == "wall" {
                h.dir = -h.dir
                if let sg = h.ground as? TTSeg, sg.k == 0, h.kind != "dust" { h.dead = true }   // rolls out under the sofa
            }
            if h.ground != nil && was == nil { hazLanded(h) }
            h.spin += h.vx * dt / max(2, h.r)
            if h.kind == "yarn" {
                h.path.append((h.x, h.y + h.r - 1))
                if h.path.count > 14 { h.path.removeFirst() }
            }
        case "cone":
            h.vy = min(h.vy + 220 * dt, 95 + 25 * sp)
            h.y += h.vy * dt
            h.x += Double(wind) * 10 * dt
            h.spin += dt * 6
            if h.y >= TT_FLOOR - h.r {
                h.dead = true
                parts.burst(h.x, TT_FLOOR - 2, 8, ["brown", "choco", "peach"], 50, 0.4)
                app.audio.play("brick")
            }
        case "cushion":
            if h.mode == "fall" {
                h.vy = min(h.vy + 400 * dt, 200)
                h.y += h.vy * dt
                if h.y + h.r >= h.ay {
                    h.y = h.ay - h.r
                    h.mode = "sit"; h.cool = 3.2
                    app.audio.play("lock")
                    app.shake(1.5, 0.12)
                    parts.burst(h.x, h.ay, 8, ["lavender", "white"], 50, 0.4)
                }
            } else {
                h.cool -= dt
                if h.cool <= 0 {
                    h.dead = true
                    parts.burst(h.x, h.y, 10, ["lavender", "white", "pink"], 50, 0.4)
                }
            }
        case "ball":
            h.vx = Double(h.dir) * 46 * sp
            let ev = moveHaz(h, dt, grav: 520)
            if ev == "wall" { h.dir = -h.dir }
            if let g = h.ground {
                if let sg = g as? TTSeg, sg.k == 0, h.x < 8 || h.x > Double(W) - 8 { h.dead = true }
                h.vy = -175
                h.ground = nil
                h.spin = 0.3
            }
        case "mouse", "bot":
            patrol(h, dt, sp)
        case "spider":
            let top = h.ay
            let bot = surface(h.k, h.x) - 9
            let ph = h.t * (1.1 + 0.05 * Double(tierN)) * sp
            h.y = top + (bot - top) * (0.5 - 0.5 * cos(ph))
        case "spritz":
            h.cool -= dt
            if h.cool <= 0 && state == "play" {
                h.mode = "squirt"
                h.cool = max(1.6, 3.0 - 0.06 * Double(tierN)) / sp
                let sx = h.x + Double(h.dir) * 8
                let s = TTShot("drop", sx, surface(h.k, sx) - 7, Double(h.dir) * 100 * sp, 0, 2.5, 0, 4)
                s.k = h.k
                shots.append(s)
                app.audio.play("bubble")
            }
        case "moth":
            h.x += h.vx * dt
            h.y = h.ay + sin(h.t * 4) * 9
            if h.x < -12 || h.x > Double(W + 12) { h.dead = true }
        default:
            break
        }
    }

    func hazLanded(_ h: TTHaz) {
        if let sg = h.ground as? TTSeg {
            if sg.kind == "bed" {
                h.vy = -200
                h.ground = nil
                sg.boing = 0.25
                return
            }
            if sg.slope != 0 { h.dir = sg.slope }
        }
        if h.kind == "yarn" && h.age > 0.2 { parts.burst(h.x, h.y + h.r, 2, [h.color], 20, 0.2) }
    }

    /// Toy mice and mini vacs walk their shelf and turn at the ends; mice hop, vacs ride the posts.
    func patrol(_ h: TTHaz, _ dt: Double, _ sp: Double) {
        if h.stun > 0 { h.stun -= dt; return }
        if h.mode == "climb", let po = h.post {
            h.y += Double(h.cdir) * 24 * sp * dt
            h.x = Double(po.x)
            if (h.cdir < 0 && h.y + h.r <= po.top) || (h.cdir > 0 && h.y + h.r >= po.bot) {
                h.y = (h.cdir < 0 ? po.top : po.bot) - h.r
                h.mode = ""
                h.vy = 0
                h.ground = support(h.x, h.y + h.r - 3, h.y + h.r + 3)?.1
                h.cool = 2
            }
            return
        }
        let speed = (h.kind == "mouse" ? 30.0 : 26.0) * sp
        if h.ground != nil {
            let ax = h.x + Double(h.dir) * 8
            if support(ax, h.y + h.r - 6, h.y + h.r + 6) == nil || ax < 4 || ax > Double(W) - 4 { h.dir = -h.dir }
            if let po = p.climb, abs(h.x + Double(h.dir) * 10 - Double(po.x)) < 14 && abs(h.y + h.r - po.top) < 6 {
                h.dir = h.x > Double(po.x) ? 1 : -1       // keep clear of the top of the post Mikan is climbing
            }
            h.vx = Double(h.dir) * speed
            h.cool -= dt
            if h.kind == "mouse" && h.cool <= 0 {
                h.cool = Double.random(in: 1.2 ... 2.4)
                h.vy = -120
                h.ground = nil
            } else if h.kind == "bot" && h.cool <= 0 {
                for po in posts {
                    if po.rope || abs(Double(po.x) - h.x) > 2 || p.climb === po { continue }
                    let feet = h.y + h.r
                    h.cool = 1.5
                    if abs(feet - po.bot) < 3 && Double.random(in: 0 ..< 1) < 0.6 {
                        h.mode = "climb"; h.post = po; h.cdir = -1; h.ground = nil
                        return
                    }
                    if abs(feet - po.top) < 3 && Double.random(in: 0 ..< 1) < 0.6 {
                        h.mode = "climb"; h.post = po; h.cdir = 1; h.ground = nil
                        h.y += 2
                        return
                    }
                    break
                }
            }
        }
        if moveHaz(h, dt) == "wall" { h.dir = -h.dir }
    }

    func hazVsPlayer(_ h: TTHaz, _ frozen: Bool) {
        if h.kind == "cushion" && h.mode == "sit" {
            if p.ground == nil && p.vy > 0 && abs(p.x - h.x) < 10 && h.y - h.r - 3 <= p.y && p.y <= h.y {
                p.vy = -205
                p.pounce = false
                p.boost = true
                p.airPounce = true
                app.audio.play("jump")
                parts.burst(p.x, p.y, 5, ["lavender", "white"], 30, 0.3)
            }
            return
        }
        if wandT > 0 && !h.harmless && (BOPPABLE.contains(h.kind) || h.kind == "bot") && hypot(h.x - p.x, h.y - (p.y - 6)) < wandReach() {
            bat(h)                      // the feather wand swats anything in reach
            return
        }
        if !touch(h) {
            if ROLLERS.contains(h.kind) && !h.jumped && p.ground == nil && p.climb == nil
                && abs(h.x - p.x) < 5 && h.y - h.r - 34 < p.y && p.y < h.y - h.r - 1 {
                h.jumped = true
                let pts = add(100 + 10 * tierN, h.x, h.y - 12, "white")
                hype.hit(1, fever: 0.04)
                app.audio.play(pts >= 200 ? "coin" : "fruit")
            }
            return
        }
        if h.harmless {
            if p.pounce || p.ground == nil { bonusCatch(h) }
            return
        }
        if p.climb != nil && (h.kind == "mouse" || h.kind == "bot") && !frozen && nipT <= 0 {
            h.dir = h.x > p.x ? 1 : -1          // patrollers bump into a climbing cat and turn around
            if h.mode == "climb" { h.cdir = -h.cdir }
            return
        }
        if frozen || nipT > 0 || (p.pounce && BOPPABLE.contains(h.kind)) { bop(h); return }
        if p.pounce && h.kind == "bot" {
            h.stun = 2
            p.vy = -150
            p.vx = -p.vx * 0.5
            app.audio.play("tin")
            floats.add(h.x, h.y - 10, "BONK", "white")
            return
        }
        if h.kind == "bot" && h.stun > 0 { return }
        hurt()
    }

    func touch(_ h: TTHaz) -> Bool {
        let cx = max(p.x - PW / 2, min(h.x, p.x + PW / 2))
        let cy = max(p.y - PH, min(h.y, p.y))
        return (cx - h.x) * (cx - h.x) + (cy - h.y) * (cy - h.y) < (h.r - 0.5) * (h.r - 0.5)
    }

    /// Pounced! The hazard is caught for points (chains within 1.2 s multiply).
    func bop(_ h: TTHaz) {
        h.dead = true
        chain = chainT > 0 ? chain + 1 : 1
        chainT = 1.2
        bestChain = max(bestChain, chain)
        bops += 1
        let pts = add((200 + 20 * tierN) * min(8, chain), h.x, h.y - 10, "yellow")
        hype.hit(1, fever: 0.07)
        hype.hitstop(0.04)
        app.audio.play("pop")
        parts.burst(h.x, h.y, 12, [h.kind == "yarn" ? h.color : "white", "white", "yellow"], 70, 0.5)
        if p.pounce && p.ground == nil { p.vy = min(p.vy, -110) }
        if chain == 2 {
            floats.add(h.x, h.y - 22, "DOUBLE!", "mint")
        } else if chain == 4 {
            hype.banner("PURR-FECT CHAIN!", "+\(pts)", dur: 1.3, rainbow: true, sound: "combo")
            hype.slowmo(0.45, 0.5)
            hype.shower(30, "stars")
        } else if chain == 6 {
            hype.jackpot(10000 + 1000 * tierN, sub: "POUNCE MASTER!")
        }
        maybeDrop(h.x, h.y)
    }

    /// The feather wand swats a hazard back up the tree.
    func bat(_ h: TTHaz) {
        if h.batted { return }
        h.batted = true
        h.harmless = true
        h.ground = nil
        h.vy = -260
        h.vx = Double(p.face) * 50
        p.swipe = 0.18
        chain = chainT > 0 ? chain + 1 : 1
        chainT = 1.2
        bestChain = max(bestChain, chain)
        add((150 + 15 * tierN) * min(8, chain), h.x, h.y - 10, "lavender")
        hype.hit(1, fever: 0.05)
        app.audio.play("paddle")
        parts.burst(h.x, h.y, 8, ["lavender", "white", "pink"], 60, 0.4)
    }

    func updateBatted(_ h: TTHaz, _ dt: Double) {
        if let b = boss, !b.dead {
            let d = max(1, hypot(b.x - h.x, b.y - h.y))
            h.vx += ((b.x - h.x) / d * 300 - h.vx) * min(1, dt * 6)
            h.vy += ((b.y - h.y) / d * 300 - h.vy) * min(1, dt * 6)
            if b.hits(h.x, h.y, h.r) {
                h.dead = true
                b.hurt(self, 1, "SWAT!")
                parts.burst(h.x, h.y, 10, ["lavender", "white"], 60, 0.4)
            }
        } else {
            h.vy += 120 * dt
        }
        h.x += h.vx * dt
        h.y += h.vy * dt
        h.spin += dt * 14
        if let k = kaw, k.mode != "flee", k.stun <= 0, abs(h.x - k.x) < 12, abs(h.y - k.y) < 10 {
            h.dead = true
            stunKaw()
        }
        if h.y < -20 || h.y > Double(H + 20) || h.x < -20 || h.x > Double(W + 20) { h.dead = true }
    }

    func stunKaw() {
        guard let k = kaw else { return }
        k.stun = 1.6
        k.aim = 0
        k.throwT = max(k.throwT, 2.5)
        add(1000 + 100 * tierN, k.x, k.y + 14, "orange")
        hype.banner("BULLSEYE!", "KAW IS SEEING STARS", color: "orange", dur: 1.2, scale: 1, sound: "boom")
        hype.hitstop(0.08)
        app.shake(3, 0.25)
        for i in 0 ..< 3 {
            let it = TTPickup("fish", k.x, k.y + 6, 200 + 20 * tierN)
            it.falling = true; it.life = 8
            it.vx = Double(i - 1) * 40; it.vy = -90
            items.append(it)
        }
    }

    func maybeDrop(_ x: Double, _ y: Double) {
        let luck = Double(up("lucky"))
        let r = Double.random(in: 0 ..< 1)
        let kd: String
        if r < 0.01 + 0.006 * luck {
            kd = "gfish"
        } else if r < 0.04 + 0.015 * luck {
            kd = ["wand", "bell", "milk", "nip"].randomElement()!
        } else if r < 0.2 {
            kd = "fish"
        } else {
            return
        }
        let it = TTPickup(kd, x, y, 100 + 20 * tierN)
        it.falling = true; it.life = 8
        it.vy = -110
        it.vx = Double.random(in: -30 ... 30)
        items.append(it)
    }

    func updateMoths(_ dt: Double) {
        mothLeft -= dt
        if mothLeft <= 0 {
            mothLeft = mothT * Double.random(in: 0.8 ... 1.2)
            let k = Int.random(in: 1 ... 4)
            let side = Bool.random() ? 1.0 : -1.0
            let h = TTHaz("moth", side > 0 ? -8 : Double(W + 8), 0, 4)
            h.ay = TT_LEVEL_Y[k] - 17
            h.y = h.ay
            h.vx = side * 38 * hs
            h.life = 20
            hz.append(h)
        }
    }

    func wandSpot() -> (Double, Int) {
        var cells: [(Int, Int)] = []
        for k in 1 ..< 4 { for c in 0 ..< TT_NC where "=<>".contains(sd.lv[k][c]) { cells.append((k, c)) } }
        if cells.isEmpty { cells = (2 ..< TT_NC - 2).map { (0, $0) } }
        let (k, c) = cells.randomElement()!
        return (Double(c * TT_CW + 8), k)
    }

    func spawnWand() {
        let (x, k) = wandSpot()
        let it = TTPickup("wand", x, surface(k, x) - 6)
        it.life = 9
        items.append(it)
        parts.burst(x, it.y, 12, ["lavender", "pink", "white"], 50, 0.5)
        app.audio.play("bonus")
    }

    // ------------------------------------------------------------------ shots (spritzers and bosses)
    func updateShots(_ dt: Double) {
        for s in shots {
            if s.dead { continue }
            s.age += dt
            if s.kind == "beam" || s.kind == "jet" {
                if s.age >= s.warn + s.life {
                    s.dead = true
                } else if s.age >= s.warn && state == "play" && p.warpT <= 0 {
                    if s.age - dt < s.warn {
                        app.audio.play(s.kind == "beam" ? "explode" : "bubble")
                        app.shake(2, 0.15)
                    }
                    if s.kind == "beam" && abs(p.x - s.x) < 6 + s.r {
                        hurt()
                    } else if s.kind == "jet" && abs(p.y - 6 - s.y) < 5 {
                        hurt()
                    }
                }
                continue
            }
            if s.batted {
                if let b = boss, !b.dead {
                    let d = max(1, hypot(b.x - s.x, b.y - s.y))
                    s.vx = (b.x - s.x) / d * 280; s.vy = (b.y - s.y) / d * 280
                    if b.hits(s.x, s.y, s.r) {
                        s.dead = true
                        b.hurt(self, 1, "SWAT!")
                    }
                }
                s.x += s.vx * dt
                s.y += s.vy * dt
                if s.y < -10 || s.x < -10 || s.x > Double(W + 10) { s.dead = true }
                continue
            }
            if s.kind == "spray" { s.vy += 260 * dt } else if s.kind == "wave" { s.y = TT_FLOOR - 4 }
            s.x += s.vx * dt
            s.y += s.vy * dt
            if s.kind == "drop" && s.k >= 0 { s.y = surface(s.k, s.x) - 7 }
            s.life -= dt
            if s.life <= 0 || s.x < -10 || s.x > Double(W + 10) || s.y > Double(H + 10) || s.y < -20 {
                s.dead = true
                continue
            }
            if s.kind == "spray" && s.vy > 0 && support(s.x, s.y - 4, s.y + 1) != nil {
                s.dead = true
                parts.burst(s.x, s.y, 4, ["sky", "white"], 30, 0.3)
                continue
            }
            if state != "play" || p.warpT > 0 { continue }
            let near = abs(s.x - p.x) < PW / 2 + s.r && p.y - PH - s.r < s.y && s.y < p.y + s.r
            if wandT > 0 && s.kind != "wave" && hypot(s.x - p.x, s.y - p.y + 6) < wandReach() {
                s.batted = true
                p.swipe = 0.18
                add(100 + 10 * tierN, s.x, s.y - 8, "lavender")
                app.audio.play("paddle")
                if boss == nil { s.vy = -240; s.vx = 0 }
                continue
            }
            if near {
                s.dead = true
                hurt()
            }
        }
        shots.removeAll { $0.dead }
    }

    // ------------------------------------------------------------------ items and kittens
    func updateItems(_ dt: Double) {
        let mag = [0.0, 36, 56, 84][min(3, up("magnet"))]
        for it in items {
            it.t += dt
            if it.life > 0 {
                it.life -= dt
                if it.life <= 0 { it.life = -2; continue }
            }
            let d = hypot(p.x - it.x, p.y - 6 - it.y)
            if mag > 0 && d < mag && state == "play" && it.kind != "coin" {
                it.x += (p.x - it.x) / max(1, d) * 140 * dt
                it.y += (p.y - 6 - it.y) / max(1, d) * 140 * dt
                it.falling = false
                if Int(t * 20) % 4 == 0 { parts.sparkle(it.x, it.y, "red") }
            } else if it.falling {
                if it.kind == "coin" {
                    it.vy = min(it.vy + 300 * dt, 90)
                    it.y += it.vy * dt
                    if it.y > TT_FLOOR - 4 {
                        it.life = -2
                        parts.burst(it.x, TT_FLOOR - 2, 6, ["yellow", "white"], 40, 0.3)
                        continue
                    }
                } else {
                    it.vy = min(it.vy + 380 * dt, 160)
                    let prev = it.y + 4
                    it.x = max(6, min(Double(W) - 6, it.x + it.vx * dt))
                    it.vx *= 0.98
                    it.y += it.vy * dt
                    if it.vy > 0, let (y, _) = support(it.x, prev - 1, it.y + 4) {
                        it.y = y - 4; it.falling = false; it.vy = 0
                    }
                }
            }
            if (state == "play" || state == "timeup" || state == "bossdown") && p.warpT <= 0
                && abs(it.x - p.x) < 9 && p.y - PH - 5 < it.y && it.y < p.y + 4 {
                it.life = -2
                collect(it)
            }
        }
        items.removeAll { !($0.life > 0 || $0.life == -1) }
    }

    func collect(_ it: TTPickup) {
        let h: Hype = hype
        let au = app.audio
        parts.burst(it.x, it.y, 6, ["yellow", "white"], 40, 0.4)
        switch it.kind {
        case "fish":
            add(it.value, it.x, it.y - 8, "peach")
            h.hit(1, fever: 0.03)
            au.play("fruit")
            fishGot += 1
            if kind == "bonus" { bonusGot += 1 }
        case "gfish":
            if kind == "bonus" {
                bonusGot += 1
                add(2000, it.x, it.y - 8, "yellow")
                au.play("coin")
                h.shower(20, "coins")
            } else {
                fishGot += 1
                h.jackpot(5000 + 1000 * tierN, sub: "GOLDEN FISH!")
            }
        case "coin":
            h.jackpot(8000 + 1000 * tierN, sub: "KAW'S TREASURE!")
        case "wand":
            wandT = 8 + 3 * Double(up("wand"))
            h.banner("FEATHER WAND!", "SWAT EVERYTHING!", color: "lavender", dur: 1.2, scale: 1, sound: "powerup")
        case "bell":
            shield = true
            h.banner("JINGLE BELL!", "BLOCKS ONE HIT", color: "yellow", dur: 1.2, scale: 1, sound: "powerup")
        case "milk":
            milkT = 5
            h.banner("WARM MILK!", "EVERYTHING NAPS - POUNCE!", color: "sky", dur: 1.4, scale: 1, sound: "powerup")
            h.flash("white", 0.2)
        case "nip":
            nipT = 6
            h.banner("CATNIP ZOOMIES!!", "UNSTOPPABLE!", dur: 1.4, rainbow: true, sound: "fever")
            h.flash("lime", 0.2)
        case "heart":
            lives += 1
            h.banner("1UP!", color: "pink", dur: 1.0, sound: "extra")
        default:
            break
        }
    }

    func updateKittens(_ dt: Double) {
        let call = up("kitty")
        for (i, kt) in kits.enumerated() {
            kt.t += dt
            if kt.follow {
                let n = kits[..<i].filter { $0.follow }.count
                let idx = max(0, p.trail.count - 1 - (n + 1) * 9)
                if !p.trail.isEmpty {
                    let (tx, ty) = p.trail[idx]
                    kt.x += (tx - kt.x) * min(1, dt * 10)
                    kt.y += (ty - kt.y) * min(1, dt * 10)
                }
                continue
            }
            if call > 0 && state == "play" && abs(p.y - kt.y) < 4 && abs(p.x - kt.x) < 40 + 30 * Double(call) {
                kt.x += (p.x > kt.x ? 1 : -1) * 30 * dt
            }
            if state == "play" && abs(kt.x - p.x) < 10 && p.y - PH - 4 < kt.y && kt.y < p.y + 4 {
                kt.follow = true
                gotKits += 1
                kittensSaved += 1
                add(500, kt.x, kt.y - 12, "pink")
                app.audio.play("bonus")
                hype.hit(1, fever: 0.05)
                parts.burst(kt.x, kt.y - 4, 10, ["pink", "white"], 50, 0.5)
                if gotKits == kits.count && kits.count >= 2 {
                    hype.banner("FAMILY REUNION!", "ALL KITTENS SAFE", color: "pink", dur: 1.6, sound: "extra")
                    hype.shower(30, "hearts")
                } else {
                    floats.add(kt.x, kt.y - 20, "MEW!", "pink")
                }
            }
        }
    }

    // ------------------------------------------------------------------ boss stages (API used by the boss)
    @discardableResult
    func shoot(_ kd: String, _ x: Double, _ y: Double, _ vx: Double, _ vy: Double, _ r: Double = 2, _ warn: Double = 0,
               _ life: Double = 6) -> TTShot {
        let s = TTShot(kd, x, y, vx, vy, r, warn, life)
        shots.append(s)
        return s
    }

    @discardableResult
    func spawnHaz(_ kd: String, _ x: Double, _ y: Double, _ vx: Double = 0, _ vy: Double = 0) -> TTHaz {
        let radii: [String: Double] = ["dust": 4, "mouse": 5, "yarn": 5, "cone": 4]
        let r = radii[kd] ?? 4
        let h = TTHaz(kd, x, y, r)
        h.vx = vx; h.vy = vy
        h.dir = vx > 0 ? 1 : -1
        h.life = kd != "mouse" ? 12 : 14
        hz.append(h)
        return h
    }

    func bossDefeated() {
        guard let b = boss else { return }
        state = "bossdown"; stateT = 0
        hype.banners = []
        hype.slowmo(0.3, 1.6)
        hype.flash("white", 0.4)
        hype.banner("BOSS DOWN!!", "\(b.name) GIVES UP!", dur: 2.6, rainbow: true, sound: "bossdown")
        app.shake(6, 0.8)
        add(10000 + 5000 * tierN, b.x, b.y - 24, "yellow")
        for h in hz { parts.burst(h.x, h.y, 8, ["white", "gray"], 60, 0.5) }
        hz = []
        shots = []
    }

    func bossBurst() {
        guard let b = boss else { return }
        hype.shower(70, "confetti")
        hype.shower(40, "coins")
        hype.flash("yellow", 0.3)
        app.audio.play("explode")
        app.shake(5, 0.5)
        parts.burst(b.x, b.y, 50, ["white", "yellow", "pink", "sky", "lavender"], 140, 1.1, size: 2)
        for i in 0 ..< 12 {
            let it = TTPickup(i % 6 == 0 ? "gfish" : "fish", b.x, b.y, 300 + 50 * tierN)
            it.falling = true; it.life = 9
            it.vx = cos(Double(i) * 2 * .pi / 12) * 80
            it.vy = -200 - Double(i % 3) * 40
            items.append(it)
        }
    }

    // ------------------------------------------------------------------ bonus stages
    func updateBonus(_ dt: Double) {
        if state != "play" { return }
        timeLeft -= dt
        if timeLeft <= 0 {
            timeLeft = 0
            state = "timeup"; stateT = 0
            hype.banner("TIME UP!", color: "yellow", dur: 1.4, sound: "levelup")
            for it in items where it.life > 0 { it.life = -2 }
            for h in hz { parts.burst(h.x, h.y, 4, [h.color, "white"], 30, 0.3) }
            hz = []
            if let k = kaw { k.mode = "flee" }
        }
    }

    func bonusCatch(_ h: TTHaz) {
        h.dead = true
        bonusGot += 1
        let pts = h.gold ? 1000 : 200 + 20 * tierN
        add(pts, h.x, h.y - 10, h.gold ? "yellow" : "white")
        hype.hit(1, fever: 0.04)
        app.audio.play(h.gold ? "coin" : "pop")
        parts.burst(h.x, h.y, 8, [h.color, "white"], 50, 0.4)
    }

    // ------------------------------------------------------------------ tally
    func startTally() {
        var rows: [(String, Int)] = []
        let tr = tierN
        if kind == "normal" {
            rows.append(("CLIMBED!", 1000 + 200 * tr))
            let tb = max(0, Int((Double(sd.par) - levelT) * 60))
            if tb > 0 { rows.append(("TIME BONUS", tb)) }
            if !missed { rows.append(("NO MISS", 3000)) }
            if !kits.isEmpty {
                rows.append(("KITTENS \(gotKits)/\(kits.count)", Int(1000 * Double(gotKits) * (1 + 0.5 * Double(up("kitty"))))))
                if gotKits == kits.count { rows.append(("ALL KITTENS!", 3000)) }
            }
            if fishTotal > 0 && fishGot >= fishTotal { rows.append(("ALL FISH", 2000)) }
            if bestChain >= 2 { rows.append(("BEST CHAIN X\(bestChain)", 400 * bestChain)) }
        } else if kind == "boss" {
            rows.append(("BOSS CLEAR", 5000 + 1000 * tr))
            let tb = max(0, Int((90 - levelT) * 100))
            if tb > 0 { rows.append(("SPEED BONUS", tb)) }
            if !missed { rows.append(("NO MISS", 10000)) }
        } else {
            rows.append(("\(sd.bt == "fish" ? "FISH" : "YARN") \(bonusGot)/\(bonusN)", 50 * bonusGot))
            if bonusN > 0 && Double(bonusGot) >= Double(bonusN) * 0.8 {
                rows.append(("PURR-FECT!!", 10000))
                hype.banner("PURR-FECT!!", dur: 1.8, rainbow: true, sound: "win")
                hype.shower(60, "coins")
            } else if bonusN > 0 && Double(bonusGot) >= Double(bonusN) * 0.5 {
                rows.append(("GREAT!", 3000))
            }
        }
        tally = rows.map { ($0.0, $0.1, 0.0) }
        tallyI = 0; tallyT = 0; tallyTotal = 0
        state = "tally"; stateT = 0
    }

    func updateTally(_ dt: Double) {
        tallyT += dt
        let inp = app.input
        if tallyI < tally.count {
            let i = tallyI
            tally[i].2 = min(Double(tally[i].1), tally[i].2 + Double(max(tally[i].1, 300)) * dt * 2.4)
            if Int(tallyT * 14) != Int((tallyT - dt) * 14) && tally[i].2 < Double(tally[i].1) { app.audio.play("move") }
            let skip = stateT > 0.3 && inp.hit(.a, .b)
            if tally[i].2 >= Double(tally[i].1) || skip {
                for j in (skip ? i ..< tally.count : i ..< i + 1) {
                    tally[j].2 = Double(tally[j].1)
                    tallyTotal += add(tally[j].1)
                }
                tallyI = skip ? tally.count : tallyI + 1
                tallyT = 0
                app.audio.play("coin")
                checkExtra()
            }
            return
        }
        if tallyT > 1.5 || (tallyT > 0.3 && inp.hit(.a, .b)) {
            if kind == "boss" || kind == "bonus" {
                picks = 1; afterPicks = "next"; pickTitle = "POWER UP!"
                state = "picks"; stateT = 0
            } else {
                nextStage()
            }
        }
    }

    // ------------------------------------------------------------------ draw
    override func render(_ s: Surface) {
        TTArt.backdrop(s, theme, t, tierN)
        s.blit(field, 0, 0)
        for hm in hams { TTArt.hammock(s, hm, theme) }
        for sg in segs where sg.kind != "plank" { TTArt.special(s, sg, theme, t) }
        for it in items where it.life < 0 || it.life > 2 || Int(it.life * 10) % 2 == 1 { TTArt.item(s, it, t) }
        for kt in kits where !kt.follow { TTArt.kitten(s, kt, t) }
        for h in hz { TTArt.haz(s, h, t, milkT > 0) }
        if kaw != nil { drawKaw(s) }
        boss?.draw(s, t)
        for kt in kits where kt.follow { TTArt.kitten(s, kt, t) }
        drawPlayer(s)
        for sh in shots { TTArt.shot(s, sh, t) }
        parts.draw(s)
        floats.draw(s)
        if mods.contains("dark") && state != "intro" && state != "tally" { darkness(s) }
        hud(s)
        overlays(s)
    }

    func drawPlayer(_ s: Surface) {
        let st = state
        if st == "over" || p.warpT > 0 { return }
        if kind == "normal" && (st == "clear" || st == "tally") {
            s.blit(sprite("tt_mikan_nap"), Int(p.x) - 8, Int(p.y) - 1)
            if Int(t * 2) % 2 == 1 { drawText(s, "Z", Int(p.x) + 8, Int(p.y) - 10 - Int(t * 8) % 6, "sky", shadow: nil) }
            return
        }
        if p.inv > 0 && st != "dead" && Int(p.inv * 12) % 2 == 1 { return }
        let flip = p.face < 0
        var img: Surface?
        if st == "dead" {
            img = sprite("tt_mikan_hurt", 0, flip: flip)
        } else if p.climb != nil {
            s.blit(sprite("tt_mikan_climb", Int(p.anim * 6)), Int(p.x) - 7, Int(p.y) - 13)
        } else if p.pounce {
            img = sprite("tt_mikan_pounce", 0, flip: flip)
        } else if p.ground == nil {
            img = sprite("tt_mikan_jump", 0, flip: flip)
        } else if abs(p.vx) > 1 {
            img = sprite("tt_mikan_walk", Int(p.anim * 10), flip: flip)
        } else {
            img = sprite("tt_mikan_idle", Int(t * 10) % 31 == 0 ? 1 : 0, flip: flip)
        }
        if let im = img { s.blit(im, Int(p.x) - 8, Int(p.y) - 13) }
        if nipT > 0 {
            for i in 0 ..< 3 {
                let a = t * 9 + Double(i) * 2.1
                s.fillRect(col(rainbow(i, t)), Int(p.x + cos(a) * 9), Int(p.y - 6 + sin(a) * 7), 2, 2)
            }
        }
        if shield && st != "dead" { s.blit(sprite("tt_bell"), Int(p.x) - 3 + (p.face > 0 ? 3 : -3), Int(p.y) - 5) }
        if wandT > 0 && st != "dead" {
            let wx = Int(p.x) + (p.face > 0 ? 5 : -13)
            s.blit(sprite("tt_wand", 0, flip: p.face < 0), wx, Int(p.y) - 16)
            if p.swipe > 0 {
                let rr = wandReach()
                let a0 = -1.6 + (1 - p.swipe / 0.18) * 3.0
                for i in 0 ..< 6 {
                    let a = a0 + Double(i) * 0.12
                    s.fillRect(col(i % 2 == 1 ? "white" : "lavender"), Int(p.x + Double(p.face) * cos(a) * rr), Int(p.y - 6 + sin(a) * rr), 2, 2)
                }
            }
            if !(wandT < 2 && Int(t * 8) % 2 == 1) {
                s.fillRect(col("lavender"), Int(p.x) - 6, Int(p.y) - 17, Int(12 * wandT / (8 + 3 * Double(up("wand")))), 1)
            }
        }
    }

    func drawKaw(_ s: Surface) {
        guard let k = kaw, k.y >= -20 else { return }
        let x = Int(k.x) - 8, y = Int(k.y) - 6
        let flip = k.face > 0
        if k.stun > 0 {
            s.blit(sprite("tt_kaw_dazed", 0, flip: flip), x, y)
            for i in 0 ..< 3 {
                let a = t * 6 + Double(i) * 2.1
                s.fillRect(col("yellow"), Int(k.x + cos(a) * 9), Int(k.y - 8 + sin(a) * 3), 2, 2)
            }
            return
        }
        if k.mode == "perch" && k.aim <= 0 {
            s.blit(sprite("tt_kaw_perch", 0, flip: flip), x, y)
        } else {
            s.blit(sprite("tt_kaw_fly", Int(t * (k.aim > 0 ? 14 : 8)) % 3, flip: flip), x, y)
        }
        if k.party {
            s.polygon(col(rainbow(0, t)), [(Double(x + 4), Double(y + 1)), (Double(x + 8), Double(y + 1)), (Double(x + 6), Double(y - 6))])
            s.fillRect(col("yellow"), x + 5, y - 7, 2, 2)
        }
        if k.aim > 0 {
            drawText(s, "!", Int(k.x), Int(k.y) - 18, Int(t * 12) % 2 == 1 ? "red" : "yellow", align: .center, shadow: nil)
            if let kd = k.nextKind, kd == "cone" || kd == "cushion" {      // show where it will land
                var yy = support(k.x, k.y + 8, Double(H))?.0 ?? TT_FLOOR
                if kd == "cone" { yy = TT_FLOOR }
                if Int(t * 12) % 2 == 1 { s.ellipse(col("black"), Int(k.x) - 6, Int(yy) - 2, 12, 3) }
            }
        } else if k.taunt > 0 && k.taunt < 1.0 && state == "play" {
            panel(s, IRect(Int(k.x) - 14, Int(k.y) - 22, 28, 11), fill: "white", border: "black", radius: 3, shadow: false)
            drawText(s, "KAW!", Int(k.x), Int(k.y) - 20, "black", align: .center, shadow: nil)
        }
    }

    func darkness(_ s: Surface) {
        let R = 60
        let c = rgba(12, 8, 24, 205)
        let cx = Int(p.x), cy = Int(p.y - 6)
        for y in TT_HUD_H ..< H {
            let dy = y - cy
            if abs(dy) < R {
                let half = Int(Double(R * R - dy * dy).squareRoot())
                s.fillRect(c, 0, y, max(0, cx - half), 1)
                s.fillRect(c, cx + half, y, W - (cx + half), 1)
            } else {
                s.fillRect(c, 0, y, W, 1)
            }
        }
    }

    func hud(_ s: Surface) {
        s.fillRect(col("black"), 0, 0, W, TT_HUD_H)
        drawText(s, String(format: "%07d", score), 3, 2, "white", shadow: nil)
        hearts(s, 48, 2, lives, maxShow: 5)
        if kind == "bonus" && (state == "play" || state == "intro") {
            drawText(s, String(format: "TIME %2d", Int(ceil(timeLeft))), 140, 2,
                     timeLeft > 5 || Int(t * 8) % 2 == 1 ? "yellow" : "red", align: .center, shadow: nil)
        } else {
            drawText(s, String(format: "HI %07d", max(best, score)), 140, 2, "lavender", align: .center, shadow: nil)
        }
        s.blit(sprite("tt_kitten", 0, remap: TT_KITTEN_COLORS[3]), 186, 2)
        drawText(s, "\(kittensSaved)", 196, 2, "pink", shadow: nil)
        drawText(s, "STAGE \(stage)", W - 3, 2, "yellow", align: .right, shadow: nil)
        if kind == "bonus" && (state == "play" || state == "intro") {
            s.fillRect(col("yellow"), 0, TT_HUD_H - 1, Int(Double(W) * timeLeft / Double(sd.time)), 1)
        } else if hype.feverOn {
            s.fillRect(col(rainbow(0, t)), 0, TT_HUD_H - 1, Int(Double(W) * hype.feverT / hype.feverTime), 1)
        } else {
            s.fillRect(col("hotpink"), 0, TT_HUD_H - 1, Int(Double(W) * hype.fever), 1)
        }
        if let b = boss, !b.dead, state != "warning", state != "tally" {
            bossBar(s, b.name, Double(b.hp), Double(b.maxhp), t, y: TT_HUD_H + 1)
        }
        if kind == "normal" && state == "play" && !hurry {
            let left = max(0, Int(Double(sd.par) - levelT))
            drawText(s, "\(left)", W - 3, TT_HUD_H + 2, left > 10 ? "white" : "red", align: .right, shadow: "ink")
        }
    }

    func overlays(_ s: Surface) {
        if state == "intro" && kind == "normal" {
            stageCard(s)
        } else if state == "warning" {
            warningCard(s)
        } else if state == "tally" {
            tallyCard(s)
        } else if hurry && state == "play" && levelT < Double(sd.par) + 2.5 && Int(t * 6) % 2 == 1 {
            drawText(s, "HURRY!", W / 2, 100, "red", scale: 2, align: .center, outline: "black")
        }
    }

    func stageCard(_ s: Surface) {
        let k = min(1, stateT * 5)
        let y = Int(46 - (1 - k) * 80)
        let lines = mods.map { TTData.mods[$0] ?? $0 }
        var news: [(String, String, String, String)] = []
        if !sd.new.isEmpty, let hd = TTData.hazards[sd.new] { news.append(("haz", sd.new, hd.0, hd.2)) }
        if !sd.nst.isEmpty, let st = TTData.structs[sd.nst] { news.append(("st", sd.nst, st.0, st.2)) }
        let hh = 64 + 10 * lines.count + 20 * news.count
        panel(s, IRect(52, y, 216, hh), fill: "ink", border: theme.carpet)
        drawText(s, "STAGE \(stage)", W / 2, y + 7, "yellow", scale: 2, align: .center, outline: "black")
        drawText(s, theme.name, W / 2, y + 26, theme.carpet, align: .center, shadow: nil)
        drawText(s, "\"\(sd.nm)\"", W / 2, y + 37, "white", align: .center, shadow: nil)
        s.blit(sprite("tt_mikan_idle", 0), 62, y + 46)
        drawText(s, sd.quip, 82, y + 50, "peach", shadow: nil)
        var yy = y + 62
        for ln in lines {
            drawText(s, "* " + ln + " *", W / 2, yy, "lime", align: .center, shadow: nil)
            yy += 10
        }
        for (kd, key, nm, blurb) in news {
            if kd == "haz" {
                let h = TTHaz(key, 74, Double(yy + 5), 5)
                h.ay = Double(yy - 2)
                h.k = 0
                TTArt.haz(s, h, t, false, icon: true)
            } else {
                TTArt.structIcon(s, key, 66, yy, theme, t)
            }
            drawText(s, "NEW! \(nm)", 92, yy, "hotpink", shadow: nil)
            drawText(s, blurb, 92, yy + 9, "white", shadow: nil)
            yy += 20
        }
    }

    func warningCard(_ s: Surface) {
        let tt = stateT
        for bandY in [46, 132] {
            s.fillRect(col("black"), 0, bandY, W, 12)
            let off = Int(tt * 40) % 16
            for x in stride(from: -16, to: W + 16, by: 16) {
                let bx = Double(x + off), by = Double(bandY)
                s.polygon(col("red"), [(bx, by), (bx + 8, by), (bx + 2, by + 12), (bx - 6, by + 12)])
            }
        }
        if Int(tt * 4) % 2 == 0 { drawText(s, "WARNING", W / 2, 66, "red", scale: 3, align: .center, outline: "black") }
        drawText(s, "SOMETHING BIG IS CLIMBING THE TREE", W / 2, 96, "white", align: .center, outline: "black")
        drawText(s, boss?.name ?? "", W / 2, 110, "yellow", scale: 2, align: .center, outline: "black")
    }

    func tallyCard(_ s: Surface) {
        let n = tally.count
        let hh = 46 + n * 11
        let y0 = 100 - hh / 2
        panel(s, IRect(64, y0, 192, hh), fill: "ink", border: "mint")
        let title = ["normal": "PERCH WON!", "boss": "BOSS DEFEATED!", "bonus": "BONUS RESULT"][kind] ?? ""
        drawText(s, title, W / 2, y0 + 7, "mint", scale: 2, align: .center, outline: "black")
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let yy = y0 + 28 + i * 11
            drawText(s, row.0, 74, yy, "white", shadow: nil)
            drawText(s, "\(Int(row.2))", 246, yy, "yellow", align: .right, shadow: nil)
        }
        if tallyI >= n { drawText(s, "TOTAL \(tallyTotal)", W / 2, y0 + hh - 13, rainbow(0, t), align: .center, shadow: nil) }
    }

    // ------------------------------------------------------------------ carousel thumbnail
    /// Carousel thumbnail (~112 x 74): Mikan climbing toward KAW on the top perch.
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        let carpet = "pink", carpetD = "hotpink", post = "peach", stripe = "brown"
        var y = 0
        while y < h { s.fillRect(lerpCol("deep", "ink", Double(y) / Double(h)), 0, y, w, 2); y += 2 }
        s.fillRect(col("sky"), 70, 8, 30, 22)
        s.circle(col("yellow"), 90, 15, 4)
        s.fillRect(col("hotpink"), 0, h - 6, w, 6)
        for (i, yv) in [h - 26, h - 46].enumerated() {
            let x0 = i % 2 == 0 ? 6 : 34
            for x in x0 ..< (x0 + 72) {
                let yy = yv + Int(floor(Double((x - x0) * (i % 2 == 0 ? 1 : -1)) / 24))
                s.fillRect(col("black"), x, yy, 1, 5)
                s.fillRect(col(carpetD), x, yy + 1, 1, 3)
                s.fillRect(col(carpet), x, yy, 1, 2)
            }
        }
        for (px, y0, y1) in [(60, h - 26, h - 6), (44, h - 46, h - 26)] {
            for yy in y0 ..< y1 { s.fillRect(col((yy / 2) % 3 == 0 ? stripe : post), px - 3, yy, 6, 1) }
        }
        TTArt.cushion(s, 50, Double(h - 46))
        let phase = ttFmod(t * 0.4, 1.0)
        let mx = Int(14 + phase * 60)
        s.blit(sprite("tt_mikan_walk", Int(t * 8)), mx - 8, h - 6 - 13)
        let kx = Int(80 + sin(t * 1.3) * 22)
        s.blit(sprite("tt_kaw_fly", Int(t * 8) % 3, flip: cos(t * 1.3) > 0), kx - 8, 4)
        let yx = 74 - ttFmod(t * 30, 64)
        let yy = h - 26 + Int((yx - 6) / 24) - 5
        s.circle(col("black"), Int(yx), yy, 5)
        s.circle(col("pink"), Int(yx), yy, 4)
        s.fillRect(col("hotpink"), Int(yx) - 2, yy - 1, 4, 1)
        s.blit(sprite("tt_kitten", Int(t * 2), remap: TT_KITTEN_COLORS[1]), 88, h - 46 - 7)
        s.blit(sprite("tt_fish"), 20, h - 30)
    }
}
