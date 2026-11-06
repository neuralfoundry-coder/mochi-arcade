// MEOW DECK - a deck-building card battler where every card is a cat (port of mochi_arcade/games/meow_deck.py).
// TOFU the crew captain climbs 200 floors with a deck of cats: fish are the energy, foes show their plans,
// cats of the same breed or role CHAIN for bonus power. Boss every 10th floor, CAT CAFE (KITTY SLOTS + shop) on x5.
// Rules + data: MeowDeckRules.swift. Portraits, foes and icons are sprites exported from the Python art module.
import Foundation

private let HUD_H = 12, GROUND = 98, PANEL_Y = 112
private let BIG_W = 104, BIG_H = 88, MINI_W = 30, MINI_H = 40
private let HAND_X0 = 110, HAND_X1 = 318
private let FOE_X: [Int: [Int]] = [1: [236], 2: [196, 268], 3: [156, 214, 274]]
private let BOSS_X = [146, 190, 256]
private let SLOT_STRIP = ["rio", "sue", "niko", "goldie", "pearl", "rio", "sue", "niko", "pearl", "fleas"]
private let LIFE_AT = [25000, 70000, 150000, 300000]      // then every 200000
private let DIFF_POW = ["easy": 0.85, "normal": 1.0, "hard": 1.15]
private let INTENT_TEXT = ["atk": "ATTACK", "blk": "BLOCK", "atkblk": "ATTACK + BLOCK", "buff": "POWER UP", "rally": "RALLY THE GANG",
                           "scare": "STARTLE YOU", "soak": "SOAK YOU", "fleas": "THROW FLEAS", "heal": "HEAL A PAL",
                           "summon": "CALL FOR HELP", "steal": "STEAL A FISH", "charge": "CHARGING UP!", "nap": "NAPPING",
                           "shield": "SHIELD THE GANG"]
private let INTENT_ICON = ["atk": "md_i_claw", "blk": "md_i_shield", "atkblk": "md_i_claw", "buff": "md_i_up", "rally": "md_i_up",
                           "scare": "md_i_down", "soak": "md_i_drop", "fleas": "md_i_flea", "heal": "md_i_plus",
                           "summon": "md_i_plus", "steal": "md_i_fishoff", "charge": "md_i_boom", "nap": "md_i_zzz",
                           "shield": "md_i_shield"]
private let WHITE_REMAP: [Character: Character] = Dictionary(uniqueKeysWithValues: "nhoegdiytsrPpbclmuv".map { ($0, "w") })

let MD_CHARMS: [Upgrade] = MD.charms.map { Upgrade(id: $0.id, name: $0.name, desc: $0.desc, color: $0.color, icon: $0.icon, max: $0.max) }

// ----------------------------------------------------------------------------- card drawing
/// (icon sprite, text) for the bottom strip of a card in hand.
private func chip(_ card: MDCard, _ battle: MDBattle?) -> (String, String) {
    let pv = battle?.preview(card)
    let fx = card.fx.filter { !["once", "wild", "gold"].contains($0.op) }
    guard let f0 = fx.first else { return ("md_i_up", "WILD") }
    let op = f0.op, hits = f0.hits
    var n = f0.n
    if card.gold && ["all", "dmg", "block", "heal"].contains(op) { n *= 2 }
    if let p = pv {
        let (kind, v, h) = p
        var icon = ["dmg": "md_i_claw", "block": "md_i_shield", "heal": "md_i_heart"][kind] ?? "md_i_claw"
        if op == "all" { icon = "md_i_boom" }
        return (icon, "\(v)" + (h > 1 ? "X\(h)" : ""))
    }
    let hx = hits > 1 ? "X\(hits)" : ""
    switch op {
    case "dmg", "rnd": return ("md_i_claw", "\(n)\(hx)")
    case "all": return ("md_i_boom", "\(n)")
    case "slam": return ("md_i_claw", "BLK")
    case "block": return ("md_i_shield", "\(n)")
    case "heal": return ("md_i_heart", "\(n)")
    case "draw": return ("md_i_quest", "+\(n)")
    case "fish": return ("md_i_fish", "+\(n)")
    case "zoom": return ("md_i_up", "+\(n)")
    case "fluff": return ("md_i_shield", "+\(n)")
    case "purr": return ("md_i_heart", "+\(n)")
    case "spiky": return ("md_i_spiky", "\(n)")
    case "scare", "scareall", "daze", "dazeall": return ("md_i_down", "\(n)")
    case "itchy", "itchyall": return ("md_i_flea", "\(n)")
    case "sleep": return ("md_i_zzz", "")
    case "echo": return ("md_i_up", "X2")
    case "fever": return ("md_i_up", "\(n)%")
    case "scratch": return ("md_i_flea", "!")
    case "cleanse": return ("md_i_plus", "")
    default: return ("md_i_quest", "")
    }
}

private func cardFrameColor(_ card: MDCard, _ t: Double) -> String {
    if card.gold || card.d.rar == 4 { return rainbow(0, t * 0.5) }
    return card.d.rar > 0 ? MD.rarity[card.d.rar][1] : "lavender"
}

/// A 30x40 cat card in the hand.
private func drawMini(_ s: Surface, _ card: MDCard, _ x: Int, _ y: Int, _ t: Double, _ battle: MDBattle? = nil,
                      dim: Bool = false, sel: Bool = false, cost: Int? = nil) {
    let d = card.d
    let roleC = MD.roleColor(d.role)
    let frame = cardFrameColor(card, t)
    s.rect(col("black"), IRect(x + 1, y + 1, MINI_W, MINI_H), radius: 3)
    s.rect(col("ink"), IRect(x, y, MINI_W, MINI_H), radius: 3)
    s.fillRect(col(roleC), x + 2, y + 2, MINI_W - 4, 6)
    s.fillRect(col("night"), x + 2, y + 8, MINI_W - 4, 24)
    s.blit(sprite(d.spr, Int(t * 0.7 + Double(card.uid) * 0.37) % 9 == 0 ? 1 : 0), x + 3, y + 8)
    s.rect(col(frame), IRect(x, y, MINI_W, MINI_H), width: 1, radius: 3)
    if d.rar >= 2 || card.gold { s.rect(col(frame), IRect(x + 1, y + 1, MINI_W - 2, MINI_H - 2), width: 1, radius: 3) }
    let c = cost ?? card.baseCost
    s.rect(col("black"), IRect(x + 1, y + 1, 9, 9), radius: 2)
    drawText(s, "\(c)", x + 3, y + 2, c < card.baseCost ? "lime" : "sky", shadow: nil)
    if card.up { drawText(s, "+", x + MINI_W - 7, y + 1, "lime", shadow: "black") }
    let (icon, txt) = chip(card, battle)
    s.fillRect(col("black"), x + 2, y + 32, MINI_W - 4, 7)
    s.blit(sprite(icon), x + 3, y + 32)
    drawText(s, txt, x + 11, y + 32, "white", shadow: nil)
    if card.gold {
        for i in 0 ..< 3 {
            let a = t * 3 + Double(i) * 2.1
            s.fillRect(col("white"), x + 15 + Int(cos(a) * 13), y + 20 + Int(sin(a) * 17), 1, 1)
        }
    }
    if dim { s.fillRect(rgba(12, 8, 24, 130), x, y, MINI_W, MINI_H) }
    if sel { s.rect(col(Int(t * 6) % 2 == 1 ? "white" : "yellow"), IRect(x - 1, y - 1, MINI_W + 2, MINI_H + 2), width: 1, radius: 4) }
}

/// The enlarged 104x88 card: 2x portrait, cost, role, breed, rarity, name and text.
private func drawBig(_ s: Surface, _ card: MDCard, _ x: Int, _ y: Int, _ t: Double, cost: Int? = nil,
                     upgraded: Bool = false, note: String? = nil) {
    let d = card.d
    let up = card.up || upgraded
    let roleLabel = MD.roleLabel(d.role), roleC = MD.roleColor(d.role)
    let rarLabel = MD.rarity[d.rar][0], rarC = MD.rarity[d.rar][1]
    let frame = cardFrameColor(card, t)
    panel(s, IRect(x, y, BIG_W, BIG_H), fill: "ink", border: frame, radius: 4)
    if d.rar >= 2 || card.gold { s.rect(col(frame), IRect(x + 1, y + 1, BIG_W - 2, BIG_H - 2), width: 1, radius: 4) }
    s.rect(col(roleC), IRect(x + 3, y + 3, 50, 50))
    s.fillRect(col("night"), x + 4, y + 4, 48, 48)
    s.blit(sprite(d.spr, Int(t * 0.8 + Double(card.uid)) % 7 == 0 ? 1 : 0, scale: 2), x + 4, y + 4)
    var c = cost ?? card.baseCost
    if up && cost == nil { c = d.upcost }
    s.blit(sprite("md_i_fish"), x + 56, y + 6)
    drawText(s, "\(c)", x + 66, y + 4, cost == nil || cost! >= card.baseCost ? "sky" : "lime", scale: 2, shadow: nil, outline: "black")
    drawText(s, roleLabel, x + 56, y + 22, roleC, shadow: "black")
    drawText(s, MD.breeds[d.breed] ?? "", x + 56, y + 32, "white", shadow: "black")
    drawText(s, card.gold ? "GOLDEN" : rarLabel, x + 56, y + 42, card.gold ? rainbow(0, t) : rarC, shadow: "black")
    drawText(s, d.name + (up ? "+" : ""), x + BIG_W / 2, y + 56, up ? "lime" : "yellow", align: .center, shadow: "black")
    let lines = up ? d.uptext : d.text
    for (i, ln) in lines.prefix(3).enumerated() {
        drawText(s, ln, x + BIG_W / 2, y + 65 + i * 8, upgraded ? "lime" : "white", align: .center, shadow: nil)
    }
    if card.gold { drawText(s, "X2!", x + 32, y + 42, rainbow(1, t), shadow: nil, outline: "black") }
    if let nt = note {
        drawText(s, nt, x + 28, y + 6, Int(t * 6) % 2 == 1 ? "lime" : "yellow", align: .center, shadow: nil, outline: "black")
    }
}

/// Blit only the sprite rows that fall inside y0 <= y < y1 (a vertical clip).
private func blitRows(_ s: Surface, _ sp: Surface, _ x: Int, _ y: Int, _ y0: Int, _ y1: Int) {
    let top = max(0, y0 - y), bot = min(sp.h, y1 - y)
    if bot <= top { return }
    for yy in top ..< bot {
        for xx in 0 ..< sp.w {
            let c = sp.px[yy * sp.w + xx]
            if c.ca > 0 { s.put(x + xx, y + yy, c) }
        }
    }
}

private func drawTofu(_ s: Surface, _ x: Int, _ ground: Int, _ t: Double, _ pose: String = "idle", flash: Bool = false) {
    var sp: Surface
    if pose == "idle" {
        let fr = Int(t * 1.3) % 6 == 0 && (t * 1.3).truncatingRemainder(dividingBy: 1) < 0.2 ? 2 : Int(t * 2) % 2
        sp = sprite("md_tofu", fr)
    } else {
        sp = sprite("md_tofu_act", ["attack": 0, "hurt": 1, "happy": 2, "ko": 3][pose] ?? 0)
    }
    if flash { sp = sprite("md_tofu_act", 1, remap: ["w": "r", "c": "P"]) }
    s.blit(sp, x - 16, ground - 32)
}

private func makeBg(_ th: MDTheme) -> Surface {
    let s = Surface(W, PANEL_Y - HUD_H)
    s.fill(col(th.sky))
    let gy = GROUND - HUD_H - 6
    for (i, y) in [0, 8, 18].enumerated() { s.fillRect(col(th.sky2), 0, y, W, 4 - i) }
    switch th.deco {
    case 0:    // fence
        for x in stride(from: 0, to: W, by: 12) {
            s.fillRect(col(th.sky2), x + 1, gy - 30, 10, 30)
            s.fillRect(col(th.ground2), x + 1, gy - 30, 10, 1)
        }
        s.fillRect(col(th.ground2), 0, gy - 22, W, 2)
        s.fillRect(col(th.ground2), 0, gy - 10, W, 2)
    case 1:    // windows
        for x in stride(from: 14, to: W, by: 64) {
            s.fillRect(col(th.sky2), x, 14, 36, 34)
            for (wx, wy) in [(x + 3, 17), (x + 19, 17), (x + 3, 33), (x + 19, 33)] {
                s.fillRect(col((wx / 7 + wy) % 3 != 0 ? "yellow" : "cream"), wx, wy, 14, 12)
            }
        }
    case 2:    // bushes and trees
        for x in stride(from: 10, to: W, by: 46) {
            s.fillRect(col(th.ground2), x + 8, gy - 26, 4, 26)
            s.circle(col(th.sky2), x + 10, gy - 30, 14)
            s.circle(col(th.ground2), x + 4, gy - 4, 8)
            s.circle(col(th.ground2), x + 18, gy - 3, 7)
        }
    case 3:    // shelves with jars
        for y in [24, 52] {
            s.fillRect(col(th.sky2), 0, y, W, 3)
            for x in stride(from: 8, to: W, by: 26) {
                let h = 8 + (x * 7 + y) % 9
                s.rect(col((x / 26) % 2 == 1 ? th.ground2 : th.sky2), IRect(x, y - h, 12, h), radius: 2)
                s.fillRect(col("white"), x + 2, y - h + 2, 2, h - 4)
            }
        }
    case 4:    // roofs and a moon
        s.circle(col("cream"), 40, 26, 10)
        s.circle(col(th.sky), 45, 23, 9)
        for x in stride(from: -20, to: W, by: 70) {
            s.polygon(col(th.sky2), [(Double(x), Double(gy - 12)), (Double(x + 35), Double(gy - 44)), (Double(x + 70), Double(gy - 12))])
            s.fillRect(col(th.sky2), x + 46, gy - 50, 8, 20)
            s.fillRect(col("yellow"), x + 30, gy - 26, 8, 8)
        }
    default:   // stars and a bridge
        for i in 0 ..< 40 { s.fillRect(col(i % 3 != 0 ? "white" : "yellow"), (i * 73) % W, (i * 37) % (gy - 20), 1, 1) }
        for x in stride(from: 0, to: W, by: 80) { s.circle(col(th.sky2), x + 40, gy + 30, 44, width: 4) }
    }
    s.fillRect(col(th.ground), 0, gy, W, PANEL_Y - HUD_H - gy)
    for x in stride(from: 0, to: W, by: 16) { s.fillRect(col(th.ground2), x + ((x / 16) % 2 == 1 ? 8 : 0), gy + 4, 8, 2) }
    s.fillRect(col("black"), 0, gy, W, 1)
    return s
}

// ----------------------------------------------------------------------------- scene helpers
private final class MDFoeFx { var flash = 0.0, shake = 0.0, lunge = 0.0, dead = 0.0 }
private struct MDFly { let card: MDCard; let i, tgt: Int; let x0, y0, x1, y1: Int; var t: Double }
private struct MDTally { let label: String; let v: Int; var shown: Double }

private final class MDView {
    let mode: String
    var i = 0
    let cards: [MDCard]
    let title: String
    let back: Bool
    var t = 0.0
    let paid: Int
    var done = false
    init(_ mode: String, _ cards: [MDCard], _ title: String, _ back: Bool, _ paid: Int) {
        self.mode = mode; self.cards = cards; self.title = title; self.back = back; self.paid = paid
    }
}

private final class MDSlots {
    var spins = 3
    var reels = [0.0, 3.0, 6.0]
    var stop = [false, false, false]
    var target = [0, 0, 0]
    var k = 0
    var wait = 0.0
    var result = ""
}

// ----------------------------------------------------------------------------- the game
final class MeowDeck: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["TAP A CAT CARD, TAP IT AGAIN TO PLAY IT", "TAP A FOE TO AIM (ATTACKS GO RIGHT AWAY)",
                            "PLAY  PLAY THE CHOSEN CAT", "END   END YOUR TURN    CREW  YOUR DECK"]
    static let helpSkip = 5

    private var diff = "normal"
    private var lives = 3
    private var charms: [String: Int] = [:]
    private var treats = 0
    private var lifeI = 0
    private var feverTurns = 0
    private var state = "intro"
    private var stateT = 0.0
    private var battle: MDBattle?
    private var view: MDView?
    private var offers: [MDCard?] = []
    private var prices: [Int]?
    private var pickI = 0
    private var pickMode = "reward"
    private var cafeI = 0
    private var cafeUsed = Set<String>()
    private var shopOffers: [MDCard?] = []
    private var shopPrices: [Int] = []
    private var slots: MDSlots?
    private var tally: [MDTally] = []
    private var tallyI = 0, tallyWait = 0.0, treatsWon = 0
    private var after: [String] = []
    private var flying: MDFly?
    private var cameo: (card: MDCard, t: Double)?
    private var foeQueue: [Int] = []
    private var foeT = 0.0
    private var fxs: [Int: MDFoeFx] = [:]
    private var heroPose = "idle", heroPoseT = 0.0, heroFlash = 0.0
    private var dealT: [Int: Double] = [:]
    private var sel = 0, tgt = 0
    private var msg = "", msgT = 0.0
    private var tapFlag = false, tapOk = false
    private let rng = MDRng()
    private var deck: [MDCard] = []
    private var maxhp = MD_BASE_HP, hp = MD_BASE_HP
    private var n = 1
    private var st: MDStage = MD.stages[0]
    private var theme: MDTheme = MD.themes[0]
    private var bg = Surface(W, PANEL_Y - HUD_H)
    private var introLen = 2.4

    override var music: String? { song() }
    override var wantsTaps: Bool { true }
    override var buttons: [Action: String] {
        if view != nil { return view!.mode == "look" ? [.a: "CLOSE"] : (view!.back ? [.a: "PICK", .b: "BACK"] : [.a: "PICK"]) }
        switch state {
        case "player", "anim", "foes": return [.a: "PLAY", .b: "END", .x: "CREW"]
        case "reward": return prices == nil ? [.a: "TAKE", .x: "CREW"] : [.a: "BUY", .b: "BACK", .x: "CREW"]
        case "slots": return [.a: "STOP"]
        case "cafe": return [.a: "OK", .x: "CREW"]
        default: return [.a: "OK"]
        }
    }
    override var buttonOrder: [Action] { [.a, .b, .x] }
    override var fourWay: Bool { false }

    override init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        super.init(app, info, opt)
        diff = optStr("difficulty", "normal")
        lives = LIVES[diff] ?? 3
        hype.feverTime = 999          // FEVER lasts turns, not seconds (ended by endTurn)
        hype.comboTime = 999          // the chain is per turn
        hype.comboY = -20             // we draw our own CHAIN counter
        let start = max(1, min(STAGES, optInt("stage", optInt("start", 1))))
        let tier = (start - 1) / 10
        if tier > 0 {     // a checkpoint start brings a crew fit for the floor
            (deck, charms, maxhp) = mdReferenceKit(tier, rng)
            treats = 30 * tier
        } else {
            deck = MD.starter.map { MDCard($0) }
            maxhp = MD_BASE_HP
        }
        lives += charms["lives"] ?? 0
        hp = maxhp
        startFloor(start)
    }

    // ---------------------------------------------------------------- helpers
    private func song() -> String {
        if st.kind == "boss" { return "boss" }
        if st.kind == "bonus" { return "bonus" }
        return n <= 100 ? "md_duel" : "md_night"
    }

    private var tierN: Int { st.tier }
    private func lv(_ id: String) -> Int { charms[id] ?? 0 }
    private func say(_ text: String, _ dur: Double = 1.4) { msg = text; msgT = dur }
    private func setState(_ s: String) { state = s; stateT = 0 }

    private func checkLife() {
        let need = lifeI < LIFE_AT.count ? LIFE_AT[lifeI] : LIFE_AT[LIFE_AT.count - 1] + 200000 * (lifeI - LIFE_AT.count + 1)
        if score >= need {
            lifeI += 1
            lives += 1
            hype.banner("EXTRA LIFE!", "TOFU FEELS LUCKY", color: "pink", dur: 1.4, scale: 1, sound: "extra")
            hype.shower(20, "hearts")
        }
    }

    @discardableResult
    private func scoreAt(_ pts: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int {
        let got = add(pts, x, y, c)
        checkLife()
        return got
    }

    // ---------------------------------------------------------------- floors
    private func startFloor(_ k: Int) {
        n = k
        st = MD.stages[k - 1]
        theme = MD.themes[st.theme]
        bg = makeBg(theme)
        reached(k)
        battle = nil
        view = nil
        slots = nil
        tally = []
        after = []
        fxs = [:]
        flying = nil
        cameo = nil
        heroPose = "idle"
        endFever(quiet: true)
        hype.breakCombo()
        setState("intro")
        introLen = st.kind == "boss" ? 3.0 : 2.4
        app.audio.music(song())
        app.audio.play(st.kind == "boss" ? "warning" : "stage")
        if st.kind == "boss" { hype.flash("red", 0.3) }
        if st.kind != "bonus" { beginFight() }
    }

    private func beginFight() {
        for c in deck { c.gold = false }
        battle = MDBattle(st, deck, hp, maxhp, charms, rng, DIFF_POW[diff] ?? 1.0)
        fxs = [:]
        sel = 0
        tgt = 0
    }

    /// Intro is over: deal the first hand.
    private func goFight() {
        if battle == nil { beginFight() }
        onEvents(battle!.start())
        retarget()
        setState("player")
    }

    private func retryFloor() {
        hp = maxhp
        startFloor(n)
    }

    // ---------------------------------------------------------------- update
    /// Z pressed - or the screen tapped (touch) - to continue.
    private func aHit() -> Bool { app.input.hit(.a) || tapOk }

    override func tick(_ dt: Double) {
        tapOk = tapFlag
        tapFlag = false
        stateT += dt
        msgT = max(0, msgT - dt)
        heroPoseT = max(0, heroPoseT - dt)
        if heroPoseT <= 0 && heroPose != "ko" { heroPose = "idle" }
        heroFlash = max(0, heroFlash - dt)
        if var cm = cameo {
            cm.t += dt
            cameo = cm.t > 0.9 ? nil : cm
        }
        for v in fxs.values {
            v.flash = max(0, v.flash - dt); v.shake = max(0, v.shake - dt)
            v.lunge = max(0, v.lunge - dt); v.dead = max(0, v.dead - dt)
        }
        for (uid, v) in dealT { dealT[uid] = v + dt }
        dealT = dealT.filter { $0.value <= 1.0 }
        if view != nil { updateView(dt); return }
        switch state {
        case "intro":
            if stateT > introLen || (stateT > 0.5 && aHit()) {
                if st.kind == "bonus" { openSlots() } else { goFight() }
            }
        case "player": updatePlayer(dt)
        case "anim": updateFly(dt)
        case "foes": updateFoes(dt)
        case "win": if stateT > 1.6 { beginTally() }
        case "tally": updateTally(dt)
        case "reward": updatePicker(dt)
        case "next": nextStep()
        case "slots": updateSlots(dt)
        case "cafe": updateCafe(dt)
        case "ko":
            if stateT > 2.4 || (stateT > 1.0 && aHit()) {
                if lives > 0 { retryFloor() } else {
                    setState("over")
                    endGame(false, "FLOOR \(n)", delay: 0.5)
                }
            }
        default: break
        }
    }

    // ---------------------------------------------------------------- player turn
    private func retarget(_ step: Int = 0) {
        guard let b = battle else { return }
        let al = b.foes.indices.filter { b.foes[$0].alive }
        if al.isEmpty { return }
        if !al.contains(tgt) { tgt = al.min { abs($0 - tgt) < abs($1 - tgt) }! }
        if step != 0 {
            let order = al.sorted { foeX($0) < foeX($1) }
            let i = order.firstIndex(of: tgt) ?? 0
            tgt = order[((i + step) % order.count + order.count) % order.count]
        }
    }

    private func updatePlayer(_ dt: Double) {
        guard let b = battle else { return }
        let inp = app.input
        b.fever = hype.feverOn
        let k = b.hand.count
        if k > 0 {
            sel = max(0, min(sel, k - 1))
            if inp.repeating(.left, dt: dt) { sel = (sel - 1 + k) % k; app.audio.play("move") }
            if inp.repeating(.right, dt: dt) { sel = (sel + 1) % k; app.audio.play("move") }
        }
        if inp.hit(.up) { retarget(-1); app.audio.play("move") }
        if inp.hit(.down) { retarget(1); app.audio.play("move") }
        if inp.hit(.x) { openView("look"); return }
        if inp.hit(.a) && k > 0 {
            tryPlay(sel, tgt)
        } else if inp.hit(.b) {
            endTurn()
        }
    }

    private func tryPlay(_ i: Int, _ target: Int) {
        guard let b = battle else { return }
        if !b.canPlay(i) {
            app.audio.play("back")
            say("NOT ENOUGH FISH!")
            floats.add(Double(handPos(i).0 + MINI_W / 2), Double(PANEL_Y + 4), "NEED FISH", "red")
            return
        }
        let card = b.hand[i]
        let (x0, y0) = handPos(i)
        let (tx, ty) = card.targeted ? (foeX(target), GROUND - 20) : (38, GROUND - 20)
        flying = MDFly(card: card, i: i, tgt: target, x0: x0, y0: y0, x1: tx - MINI_W / 2, y1: ty - MINI_H / 2, t: 0)
        app.audio.play("card")
        if card.d.role == "swipe" || card.targeted { heroPose = "attack"; heroPoseT = 0.4 }
        setState("anim")
    }

    private func updateFly(_ dt: Double) {
        guard var f = flying, let b = battle else { return }
        f.t += dt
        flying = f
        if f.t < 0.2 { return }
        let idx = b.hand.firstIndex { $0 === f.card } ?? f.i
        let ev = b.play(idx, f.tgt)
        flying = nil
        cameo = (f.card, 0)
        afterPlay(ev)
        if b.won {
            fightWon()
        } else {
            retarget()
            sel = min(sel, max(0, b.hand.count - 1))
            setState("player")
        }
    }

    private func afterPlay(_ ev: [MDEv]) {
        guard let b = battle else { return }
        let link = ev.first?.kind == "play" ? ev[0].n : 0
        let nip = 1 + 0.25 * Double(lv("catnip"))
        if link > 0 {
            hype.hit(1, fever: 0)
            hype.feverAdd((0.05 + 0.05 * Double(link)) * nip)
            scoreAt(50 * b.chain)
            floats.add(60, Double(PANEL_Y - 18), link >= 2 ? "PURRFECT CHAIN!" : "CHAIN X\(b.chain)!", link >= 2 ? "lime" : "peach")
            if link >= 2 { app.audio.play("combo") }
            if [4, 6, 8].contains(b.chain) {
                hype.banner("CHAIN X\(b.chain)!", "THE CREW IS IN SYNC", color: "lime", dur: 1.0, scale: 1, sound: "combo")
            }
        } else {
            hype.breakCombo()
            hype.hit(1, fever: 0)
            hype.feverAdd(0.03 * nip)
        }
        onEvents(ev)
    }

    private func endTurn() {
        guard let b = battle else { return }
        onEvents(b.endTurn())
        hype.breakCombo()
        if feverTurns > 0 {
            feverTurns -= 1
            if feverTurns == 0 { endFever() }
        }
        app.audio.play("select")
        if b.lost { heroKo(); return }
        foeQueue = b.foes.indices.filter { b.foes[$0].alive }
        foeT = 0
        setState("foes")
    }

    private func updateFoes(_ dt: Double) {
        guard let b = battle else { return }
        foeT += dt
        if foeT < 0.35 { return }
        if foeQueue.isEmpty {
            var ev: [MDEv] = []
            b.beginTurn(&ev)
            onEvents(ev)
            retarget()
            sel = 0
            setState("player")
            return
        }
        let k = foeQueue.removeFirst()
        foeT = 0
        if k >= b.foes.count || !b.foes[k].alive { foeT = 0.3; return }
        fx(k).lunge = 0.3
        onEvents(b.foeAct(k))
        if b.lost { heroKo() } else if b.won { fightWon() }
    }

    private func fx(_ k: Int) -> MDFoeFx {
        if let v = fxs[k] { return v }
        let v = MDFoeFx()
        fxs[k] = v
        return v
    }

    // ---------------------------------------------------------------- events -> juice
    private func onEvents(_ ev: [MDEv]) {
        guard let b = battle else { return }
        let tr = tierN
        let nip = 1 + 0.25 * Double(lv("catnip"))
        for e in ev {
            let who = e.who, k = e.n, s = e.s
            let x = who == MD_HERO ? 38.0 : Double(foeX(who))
            let y = who == MD_HERO ? Double(GROUND - 40) : Double(GROUND - foeH(who) - 6)
            switch e.kind {
            case "hit":
                let v = fx(who)
                v.flash = 0.15; v.shake = 0.25
                if k > 0 {
                    floats.add(x, y + 10, "\(k)", s != "ITCHY" ? "white" : "lime")
                    parts.burst(x, Double(GROUND - 14), 8, ["white", "yellow", "orange"], 50, 0.4)
                    scoreAt(10 * k)
                    app.audio.play(k < 12 ? "pop" : "explode")
                    hype.feverAdd(0.004 * Double(k) * nip)
                    if k >= 25 { app.shake(3, 0.2); hype.hitstop(0.06) }
                } else if s != "0" && s != "" {
                    floats.add(x, y + 10, "BLOCKED", "sky")
                    app.audio.play("tin")
                }
            case "die":
                let fo = b.foes[who]
                fx(who).dead = 0.6
                parts.burst(x, Double(GROUND - 14), 24, ["white", "pink", "yellow", "lavender"], 80, 0.7)
                app.audio.play(fo.boss ? "bossdown" : "explode")
                if fo.boss {
                    bossDefeated(fo)
                } else {
                    scoreAt(150 * (tr + 1) * (fo.elite ? 2 : 1), x, y - 6, "lime")
                    hype.feverAdd(0.08 * nip)
                    app.shake(2, 0.15)
                }
            case "hurt":
                if k > 0 {
                    heroPose = "hurt"; heroPoseT = 0.35
                    heroFlash = 0.15
                    floats.add(38, Double(GROUND - 46), "-\(k)", "red")
                    app.audio.play("hurt")
                    app.shake(2 + Double(min(4, k / 8)), 0.2)
                    parts.burst(38, Double(GROUND - 16), 10, ["red", "pink", "white"], 50, 0.4)
                } else if s != "0" && s != "" {
                    floats.add(38, Double(GROUND - 46), "BLOCKED!", "sky")
                    app.audio.play("tin")
                }
            case "block":
                floats.add(20, Double(GROUND - 30), "+\(k)", "sky")
                app.audio.play("hold")
                scoreAt(5 * k)
            case "heal":
                if k > 0 {
                    floats.add(38, Double(GROUND - 46), "+\(k)", "lime")
                    parts.burst(38, Double(GROUND - 20), 8, ["pink", "hotpink", "white"], 40, 0.5)
                    app.audio.play("fruit")
                    scoreAt(5 * k)
                }
            case "buff":
                floats.add(38, Double(GROUND - 52), "+\(k) \(s)", "orange")
                app.audio.play("powerup")
            case "fish":
                floats.add(Double(HAND_X0 + 20), Double(PANEL_Y + 2), "+\(k) FISH", "sky")
                app.audio.play("coin")
            case "debuff":
                floats.add(x, y - 4, s, "lavender")
                app.audio.play("trap")
            case "fever":
                hype.feverAdd(Double(k) / 100)
                floats.add(38, Double(GROUND - 52), "FEVER +\(k)%", "yellow")
            case "text":
                floats.add(x, y - 4, s, "peach")
            case "golden":
                hype.banner("GOLDEN KITTEN!", "IT COSTS 0 AND HITS X2!", dur: 1.4, rainbow: true, scale: 1, sound: "bonus")
                hype.shower(16, "stars")
            case "jackpot":
                hype.jackpot(3000 * (tr + 1), sub: "\(s)!")
                treats += 25
                checkLife()
            case "phase":
                hype.banner("PHASE \(k)!", "\(s) GETS SERIOUS", color: "red", dur: 1.6, sound: "warning")
                hype.flash("red", 0.3)
                app.shake(5, 0.4)
            case "summon":
                floats.add(x, y - 4, "HELP ARRIVES!", "orange")
                fx(who).flash = 0.3
                fx(who).dead = 0
                app.audio.play("warning")
            case "junk":
                floats.add(Double(HAND_X0 + 60), Double(PANEL_Y + 2), "+\(k) FLEAS IN DECK", "brown")
                app.audio.play("trap")
            case "fblock":
                floats.add(x, y, "+\(k)", "sky")
            case "fheal":
                floats.add(x, y, "+\(k)", "lime")
                app.audio.play("fruit")
            case "fbuff":
                floats.add(x, y - 4, s, "orange")
            case "draw":
                for (j, c) in b.hand.suffix(k).enumerated() { dealT[c.uid] = -0.05 * Double(j) }
                app.audio.play("move")
            case "turn":
                if k > 1 { floats.add(Double(W / 2), Double(PANEL_Y - 18), "TURN \(k)", "white") }
            default: break
            }
        }
        if hype.feverOn && feverTurns == 0 {
            feverTurns = 2          // FEVER: the rest of this turn and the next one
            say("FEVER! CATS COST 1 LESS")
        }
    }

    private func endFever(quiet: Bool = false) {
        if hype.feverOn {
            hype.feverT = 0
            if !quiet { hype.banner("FEVER END", color: "lavender", dur: 0.9, scale: 1) }
        }
        feverTurns = 0
    }

    private func heroKo() {
        heroPose = "ko"; heroPoseT = 99
        lives -= 1
        hp = 0
        endFever(quiet: true)
        app.audio.play("die")
        app.audio.music(nil)
        hype.slowmo(0.4, 0.8)
        if lives > 0 {
            hype.banner("TOFU FAINTED!", "\(lives) LIVES LEFT - TRY AGAIN", color: "red", dur: 2.2)
        } else {
            hype.banner("GAME OVER", "TOFU NEEDS A LONG NAP", color: "red", dur: 2.4)
        }
        setState("ko")
    }

    // ---------------------------------------------------------------- winning
    private func fightWon() {
        guard let b = battle else { return }
        hp = b.hero.hp
        endFever(quiet: true)
        hype.breakCombo()
        heroPose = "happy"; heroPoseT = 99
        app.audio.play("win")
        if st.kind != "boss" {
            hype.banner("VICTORY!", MD.lines[(n + b.turn) % MD.lines.count], color: "mint", dur: 1.5)
            hype.shower(30, "confetti")
        }
        hype.slowmo(0.4, 0.6)
        setState("win")
    }

    private func bossDefeated(_ fo: MDFoe) {
        hype.banner("BOSS DOWN!", fo.name, dur: 2.2, rainbow: true)
        hype.flash("white", 0.4)
        hype.shower(90, "confetti")
        hype.shower(40, "coins")
        hype.slowmo(0.3, 1.2)
        app.shake(6, 0.6)
        scoreAt(10000 + 3000 * tierN, Double(W / 2), 60)
    }

    private func beginTally() {
        guard let b = battle else { return }
        let t1 = tierN + 1
        var rows: [(String, Int)] = []
        if st.kind == "boss" { rows.append(("BOSS BONUS", 5000 * t1)) } else { rows.append(("VICTORY", 500 * t1 * (st.elite ? 2 : 1))) }
        rows.append(("TURNS \(b.turn)", max(0, 7 - b.turn) * 150 * t1))
        rows.append(("BEST CHAIN X\(b.bestChain)", b.bestChain * 120 * t1))
        rows.append(("NO SCRATCH", b.dmgTaken == 0 ? 1500 * t1 : 0))
        let mult = (1 + 0.5 * Double(lv("jar"))) * (st.mod == "treats" ? 2 : 1)
        treatsWon = Int(Double(st.treats + Int(rng.random() * 5)) * mult) + 2 * lv("bell")
        tally = rows.map { MDTally(label: $0.0, v: $0.1, shown: 0) }
        tallyI = 0
        tallyWait = 0
        treats += treatsWon
        let heal = 4 * lv("motor")
        if st.kind == "boss" { hp = maxhp } else if heal > 0 { hp = min(maxhp, hp + heal) }
        if b.dmgTaken == 0 {
            hype.banner("PURRFECT!", "NOT A SCRATCH", dur: 1.6, rainbow: true, sound: "fever")
            hype.shower(30, "stars")
        }
        setState("tally")
    }

    private func updateTally(_ dt: Double) {
        let skip = stateT > 0.3 && aHit()
        if tallyI < tally.count {
            if skip {
                for j in tallyI ..< tally.count {
                    tally[j].shown = Double(tally[j].v)
                    if tally[j].v > 0 { scoreAt(tally[j].v) }
                }
                tallyI = tally.count
                app.audio.play("coin")
                return
            }
            let v = Double(tally[tallyI].v)
            tally[tallyI].shown = min(v, tally[tallyI].shown + max(1.0, v * dt / 0.35))
            if tally[tallyI].shown >= v {
                if tally[tallyI].v > 0 {
                    scoreAt(tally[tallyI].v)
                    app.audio.play("coin")
                }
                tallyI += 1
            }
        } else {
            tallyWait += dt
            if tallyWait > 1.4 || skip { finishFight() }
        }
    }

    private func finishFight() {
        if n >= STAGES {
            setState("over")
            hype.banner("ALL CLEAR!!", "THE CREW RULES THE TOWER", dur: 5.0, rainbow: true, sound: "jackpot")
            hype.shower(120, "confetti")
            endGame(true, "ALL 200 FLOORS!", delay: 4.5)
            return
        }
        after = st.kind == "boss" ? ["charm", "groom", "reward"] : ["reward"]
        setState("next")
    }

    private func nextStep() {
        if after.isEmpty { startFloor(n + 1); return }
        let step = after.removeFirst()
        switch step {
        case "charm":
            setState("charm")
            pickUpgrade(MD_CHARMS, charms, title: "COLLAR CHARM!") { [unowned self] id in self.onCharm(id) }
        case "groom": openView("groom", back: false)
        default: openReward()
        }
    }

    private func onCharm(_ uid: String?) {
        if let uid = uid {
            charms[uid] = lv(uid) + 1
            if let u = MD_CHARMS.first(where: { $0.id == uid }) {
                hype.banner(u.name, "LEVEL \(charms[uid]!)", color: u.color, dur: 1.2, scale: 1)
            }
            if uid == "nap" {
                maxhp += 12
                hp = min(maxhp, hp + 12)
            } else if uid == "lives" {
                lives += 1
                app.audio.play("extra")
            }
        }
        setState("next")
    }

    // ---------------------------------------------------------------- reward / shop picker
    private func makeOffers(_ k: Int, boss: Bool = false, shop: Bool = false) -> [MDCard?] {
        let tr = tierN
        var out: [MDCard?] = []
        var ids: [String] = []
        for j in 0 ..< k {
            let rich = boss || (shop && j == 0)
            var cid = mdRewardCard(rng, tr + (rich ? 3 : 0), ids)
            if (rich || st.elite) && MD.cat[cid]?.rar == 0 { cid = mdRewardCard(rng, tr + 4, ids) }
            ids.append(cid)
            out.append(MDCard(cid, rng.random() < min(0.5, 0.03 * Double(tr))))
        }
        if hype.lucky(0.01 + 0.006 * Double(lv("bell"))) { out[Int(rng.random() * Double(k))] = MDCard("goldie") }
        return out
    }

    private func openReward() {
        offers = makeOffers(3, boss: st.kind == "boss")
        prices = nil
        pickMode = "reward"
        pickI = 0
        if offers.contains(where: { $0?.cid == "goldie" }) {
            hype.banner("LUCKY!", "A GOLDEN KITTEN WANTS TO JOIN!", dur: 1.8, rainbow: true, sound: "bonus")
        }
        app.audio.play("levelup")
        setState("reward")
    }

    private func updatePicker(_ dt: Double) {
        let inp = app.input
        let k = offers.count
        if inp.hit(.left) { pickI = (pickI - 1 + k + 1) % (k + 1); app.audio.play("move") }
        if inp.hit(.right) { pickI = (pickI + 1) % (k + 1); app.audio.play("move") }
        if inp.hit(.down) { pickI = k; app.audio.play("move") }
        if inp.hit(.up) && pickI == k { pickI = 0; app.audio.play("move") }
        if inp.hit(.x) { openView("look"); return }
        if stateT > 0.4 && inp.hit(.a) {
            takeOffer(pickI)
        } else if stateT > 0.4 && inp.hit(.b) && pickMode == "shop" {
            takeOffer(k)
        }
    }

    private func takeOffer(_ i: Int) {
        let k = offers.count
        if i >= k {          // skip / leave
            if pickMode == "reward" {
                treats += 10
                floats.add(Double(W / 2), 150, "+10 TREATS", "orange")
                app.audio.play("coin")
                setState("next")
            } else {
                shopOffers = offers
                setState("cafe")
            }
            return
        }
        guard let c = offers[i] else { return }
        if let p = prices?[i] {
            if treats < p {
                app.audio.play("back")
                say("NOT ENOUGH TREATS!")
                return
            }
            treats -= p
        }
        deck.append(c)
        app.audio.play("card")
        hype.banner("NEW CREW!", c.name, color: MD.rarity[c.d.rar][1], dur: 1.2, scale: 1)
        hype.shower(12 + 8 * c.d.rar, "stars")
        if c.cid == "goldie" { hype.jackpot(5000 * (tierN + 1), sub: "LUCKY GOLDIE JOINS!") }
        if prices == nil {
            setState("next")
        } else {
            offers[i] = nil
            shopOffers = offers
            pickI = k
        }
    }

    // ---------------------------------------------------------------- deck viewer
    private func crew() -> [MDCard] {
        func ord(_ r: String) -> Int { MD.roleOrder.firstIndex(of: r) ?? 9 }
        return deck.sorted { a, b in
            if ord(a.d.role) != ord(b.d.role) { return ord(a.d.role) < ord(b.d.role) }
            if a.d.name != b.d.name { return a.d.name < b.d.name }
            return a.up && !b.up
        }
    }

    private func openView(_ mode: String, back: Bool = true, paid: Int = 0) {
        var cards = crew()
        if mode == "groom" {
            cards = cards.filter { !$0.up && $0.cid != "fleas" }
            if cards.isEmpty { setState(back ? state : "next"); return }
        }
        if mode == "rehome" { cards = cards.filter { $0.cid != "goldie" } }
        let titles = ["look": "YOUR CREW: \(deck.count) CATS", "groom": "GROOMING: PICK A CAT TO UPGRADE",
                      "rehome": "REHOME: WHICH CAT FINDS A NEW HOME?"]
        view = MDView(mode, cards, titles[mode] ?? "", back, paid)
        app.audio.play("select")
    }

    private func updateView(_ dt: Double) {
        guard let v = view else { return }
        v.t += dt
        let inp = app.input
        let k = v.cards.count
        let cols = 6
        if k > 0 {
            if inp.repeating(.left, dt: dt) { v.i = (v.i - 1 + k) % k; app.audio.play("move") }
            if inp.repeating(.right, dt: dt) { v.i = (v.i + 1) % k; app.audio.play("move") }
            if inp.repeating(.up, dt: dt) && v.i >= cols { v.i -= cols; app.audio.play("move") }
            if inp.repeating(.down, dt: dt) && v.i + cols < k { v.i += cols; app.audio.play("move") }
        }
        if v.mode == "look" {
            if v.t > 0.2 && inp.hit(.x, .b, .a) { closeView() }
            return
        }
        if v.t > 0.3 && inp.hit(.a) && k > 0 {
            viewPick(v.i)
        } else if v.back && inp.hit(.b, .x) {
            closeView()
        }
    }

    private func viewPick(_ i: Int) {
        guard let v = view else { return }
        let c = v.cards[i]
        if v.mode == "groom" {
            c.up = true
            hype.banner("GROOMED!", c.name, color: "lime", dur: 1.2, scale: 1, sound: "powerup")
            hype.shower(16, "stars")
        } else {
            deck.removeAll { $0 === c }
            hype.banner("REHOMED", "\(c.d.name) FOUND A COZY HOME", color: "peach", dur: 1.4, scale: 1, sound: "select")
        }
        v.done = true
        closeView()
    }

    private func closeView() {
        guard let v = view else { return }
        view = nil
        app.audio.play("back")
        if v.mode == "groom" && !v.back {
            setState("next")
        } else if v.paid > 0 && !v.done {      // cancelled a cafe service: money back
            treats += v.paid
            cafeUsed.remove(v.mode)
        }
    }

    // ---------------------------------------------------------------- KITTY SLOTS + CAT CAFE (bonus floors)
    private func openSlots() {
        slots = MDSlots()
        setState("slots")
    }

    private func updateSlots(_ dt: Double) {
        guard let sl = slots else { return }
        let speed = 7.5 - 0.8 * Double(lv("bell"))
        let k = Double(SLOT_STRIP.count)
        for r in 0 ..< 3 {
            if !sl.stop[r] {
                sl.reels[r] = (sl.reels[r] + speed * dt * (1 + 0.15 * Double(r))).truncatingRemainder(dividingBy: k)
            } else {
                let tg = Double(sl.target[r]), cur = sl.reels[r]
                if abs(cur - tg) > 0.01 {
                    let step = speed * dt
                    var d = (tg - cur).truncatingRemainder(dividingBy: k)
                    if d < 0 { d += k }
                    sl.reels[r] = d <= step ? tg : (cur + step).truncatingRemainder(dividingBy: k)
                }
            }
        }
        if sl.k < 3 {
            if stateT > 0.4 && aHit() {
                let r = sl.k
                sl.stop[r] = true
                sl.target[r] = Int(floor(sl.reels[r] + 1)) % SLOT_STRIP.count
                sl.k += 1
                app.audio.play("lock")
                if sl.k == 3 { sl.wait = 0 }
            }
        } else {
            sl.wait += dt
            if sl.wait > 0.45 && sl.result.isEmpty { slotPayout() }
            if sl.wait > 1.8 || (sl.wait > 0.8 && aHit()) {
                sl.spins -= 1
                if sl.spins <= 0 {
                    openCafe()
                } else {
                    sl.k = 0
                    sl.stop = [false, false, false]
                    sl.result = ""
                    stateT = 0
                }
            }
        }
    }

    private func slotPayout() {
        guard let sl = slots else { return }
        let t1 = tierN + 1
        let sym = (0 ..< 3).map { SLOT_STRIP[sl.target[$0] % SLOT_STRIP.count] }
        if sym.filter({ $0 == "goldie" }).count == 3 {
            sl.result = "JACKPOT!!"
            hype.jackpot(10000 * t1, sub: "THREE GOLDEN KITTENS!")
            treats += 60
            deck.append(MDCard("goldie"))
            say("LUCKY GOLDIE JOINED THE CREW!", 2.0)
        } else if sym[0] == sym[1] && sym[1] == sym[2] && sym[0] != "fleas" {
            sl.result = "TRIPLE CATS!"
            scoreAt(2500 * t1, Double(W / 2), 60)
            treats += 25
            hype.banner("TRIPLE CATS!", "+25 TREATS", color: "yellow", dur: 1.2, sound: "bonus")
            hype.shower(40, "coins")
        } else if sym[0] == sym[1] && sym[1] == sym[2] {
            sl.result = "ITCHY!"
            treats += 1
            app.audio.play("trap")
        } else if Set(sym).count == 2 {
            sl.result = "PAIR! +8 TREATS"
            scoreAt(500 * t1, Double(W / 2), 60)
            treats += 8
            app.audio.play("coin")
        } else if sym.contains("goldie") {
            sl.result = "GOLDEN GLIMPSE +5"
            treats += 5
            app.audio.play("coin")
        } else {
            sl.result = "NO LUCK"
            app.audio.play("move")
        }
    }

    /// (label, price): nil = no price shown, 0 = free, -1 = already done.
    private func cafeItems() -> [(String, Int?)] {
        let t = tierN
        return [("ADOPT A CAT", nil), ("CATNAP: HEAL 40%", cafeUsed.contains("nap") ? -1 : 0),
                ("GROOM A CAT", cafeUsed.contains("groom") ? -1 : 35 + 5 * t),
                ("REHOME A CAT", cafeUsed.contains("rehome") ? -1 : 25 + 5 * t), ("LEAVE THE CAFE", nil)]
    }

    private func openCafe() {
        cafeI = 0
        cafeUsed = []
        shopOffers = makeOffers(3, shop: true)
        shopPrices = shopOffers.map { MD.price[$0!.d.rar] + 5 * tierN }
        setState("cafe")
        say("BOBA: WELCOME TO THE CAT CAFE!", 2.0)
    }

    private func updateCafe(_ dt: Double) {
        let inp = app.input
        let k = cafeItems().count
        if inp.repeating(.up, dt: dt) { cafeI = (cafeI - 1 + k) % k; app.audio.play("move") }
        if inp.repeating(.down, dt: dt) { cafeI = (cafeI + 1) % k; app.audio.play("move") }
        if stateT > 0.3 && inp.hit(.a) {
            cafePick(cafeI)
        } else if stateT > 0.3 && inp.hit(.x) {
            openView("look")
        }
    }

    private func cafePick(_ i: Int) {
        let price = cafeItems()[i].1
        if price == -1 {
            app.audio.play("back")
            say("ALREADY DONE TODAY!")
            return
        }
        switch i {
        case 0:
            offers = shopOffers
            prices = shopPrices
            pickMode = "shop"
            pickI = 0
            setState("reward")
        case 1:
            let heal = min(maxhp - hp, maxhp * 2 / 5)
            hp += heal
            cafeUsed.insert("nap")
            floats.add(60, 120, "+\(heal) HP", "lime")
            hype.banner("CATNAP", "TOFU FEELS FRESH", color: "lavender", dur: 1.2, scale: 1, sound: "levelup")
        case 2, 3:
            let p = price ?? 0
            if treats < p {
                app.audio.play("back")
                say("NOT ENOUGH TREATS!")
                return
            }
            if i == 2 && !deck.contains(where: { !$0.up && $0.cid != "fleas" }) {
                app.audio.play("back")
                say("EVERY CAT IS GROOMED!")
                return
            }
            treats -= p
            cafeUsed.insert(i == 2 ? "groom" : "rehome")
            openView(i == 2 ? "groom" : "rehome", paid: p)
        default:
            app.audio.play("select")
            prices = nil
            startFloor(n + 1)
        }
    }

    // ---------------------------------------------------------------- layout
    private func foeX(_ k: Int) -> Int {
        guard let b = battle, k >= 0, k < b.foes.count else { return 236 }
        let fo = b.foes[k]
        if b.foes.contains(where: { $0.boss }) { return BOSS_X[fo.slot] }
        return FOE_X[min(3, b.foes.count)]![min(k, 2)]
    }

    private func foeH(_ k: Int) -> Int { sprite(battle!.foes[k].spr).h }

    private func handLayout(_ k: Int) -> [(Int, Int)] {
        if k == 0 { return [] }
        let sp = min(32.0, Double(HAND_X1 - HAND_X0 - MINI_W) / Double(max(1, k - 1)))
        let total = Double(MINI_W) + sp * Double(k - 1)
        let x0 = Double(HAND_X0) + (Double(HAND_X1 - HAND_X0) - total) / 2
        return (0 ..< k).map { i in
            let off = Double(i) - Double(k - 1) / 2
            return (Int(x0 + Double(i) * sp), Int(140 + off * off * 0.7))
        }
    }

    private func handPos(_ i: Int) -> (Int, Int) {
        let lay = handLayout(battle?.hand.count ?? 0)
        if lay.isEmpty { return (HAND_X0, 140) }
        var (x, y) = lay[min(i, lay.count - 1)]
        if i == sel && state == "player" { y -= 10 }
        return (x, y)
    }

    // ---------------------------------------------------------------- touch
    override func onTap(_ x: Double, _ y: Double) {
        if view != nil { tapView(x, y); return }
        switch state {
        case "player":
            guard let b = battle else { return }
            var hit: Int?
            for i in stride(from: b.hand.count - 1, through: 0, by: -1) {     // topmost card first
                let (cx, cy) = handPos(i)
                if Double(cx) <= x && x < Double(cx + MINI_W) && Double(cy) <= y && y < Double(cy + MINI_H + 12) {
                    if hit == nil || i == sel { hit = i }
                }
            }
            if let h = hit, y >= Double(PANEL_Y) {
                if h == sel { tryPlay(h, tgt) } else { sel = h; app.audio.play("move") }
                return
            }
            for (k, fo) in b.foes.enumerated() where fo.alive {
                let sp = sprite(fo.spr)
                let fx0 = Double(foeX(k))
                if abs(x - fx0) <= Double(sp.w / 2 + 4) && Double(GROUND - sp.h - 16) <= y && y <= Double(GROUND + 8) {
                    tgt = k
                    app.audio.play("move")
                    if !b.hand.isEmpty && sel < b.hand.count && b.hand[sel].targeted { tryPlay(sel, k) }
                    return
                }
            }
            if x < 106 && y >= Double(PANEL_Y) && !b.hand.isEmpty { tryPlay(sel, tgt) }
        case "intro", "tally", "ko", "slots":
            tapFlag = true
        case "reward":
            for k in 0 ..< offers.count where Double(3 + k * 106) <= x && x < Double(3 + k * 106 + BIG_W) && 22 <= y && y < 140 {
                if k == pickI { takeOffer(k) } else { pickI = k; app.audio.play("move") }
                return
            }
            if 100 <= x && x < 220 && 146 <= y && y < 168 { takeOffer(offers.count) }
        case "cafe":
            for i in 0 ..< cafeItems().count where 10 <= x && x < 170 && Double(46 + i * 18) <= y && y < Double(46 + i * 18 + 16) {
                if i == cafeI { cafePick(i) } else { cafeI = i; app.audio.play("move") }
                return
            }
        default: break
        }
    }

    private func tapView(_ x: Double, _ y: Double) {
        guard let v = view else { return }
        if v.mode == "look" { closeView(); return }
        if x >= 210 && y >= 160 {          // the hint corner cancels
            if v.back { closeView() }
            return
        }
        let first = viewFirst()
        for j in 0 ..< min(24, v.cards.count - first) {
            let cx = 6 + (j % 6) * 34, cy = 16 + (j / 6) * 43
            if Double(cx) <= x && x < Double(cx + MINI_W) && Double(cy) <= y && y < Double(cy + MINI_H) {
                let i = first + j
                if i == v.i { viewPick(i) } else { v.i = i; app.audio.play("move") }
                return
            }
        }
        if 212 <= x && x < 316 && 12 <= y && y < 100 { viewPick(v.i) }
    }

    private func viewFirst() -> Int {
        guard let v = view else { return 0 }
        let row = v.i / 6
        let top = max(0, min(row - 1, (v.cards.count - 1) / 6 - 3))
        return top * 6
    }

    // ---------------------------------------------------------------- drawing
    override func render(_ s: Surface) {
        s.fill(col("black"))
        s.blit(bg, 0, HUD_H)
        if st.kind == "bonus" { drawCafeScene(s, t) }
        if battle != nil {
            drawField(s, t)
            drawPanel(s, t)
        }
        parts.draw(s)
        floats.draw(s)
        if state == "reward" { drawPicker(s, t) } else if state == "slots" { drawSlots(s, t) } else if state == "cafe" { drawCafe(s, t) }
        drawHud(s, t)
        if state == "intro" { drawIntro(s, t) } else if state == "tally" { drawTally(s, t) }
        if view != nil { drawView(s, t) }
        if msgT > 0 {
            let w = textWidth(msg) + 10
            let my = ["player", "anim", "foes"].contains(state) ? 84 : HUD_H + 2
            panel(s, IRect(W / 2 - w / 2, my, w, 13), fill: "black", border: "yellow", radius: 3, shadow: false)
            drawText(s, msg, W / 2, my + 3, "yellow", align: .center, shadow: nil)
        }
    }

    private func drawHud(_ s: Surface, _ t: Double) {
        s.fillRect(col("black"), 0, 0, W, HUD_H)
        drawText(s, String(format: "%07d", score), 3, 3, "white", shadow: nil)
        s.blit(sprite("md_i_treat"), 48, 2)
        drawText(s, "\(treats)", 57, 3, "orange", shadow: nil)
        if let b = battle, let boss = b.foes.first(where: { $0.boss && $0.alive }) {
            bossBar(s, String(boss.name.prefix(14)), Double(boss.hp), Double(boss.maxhp), t, y: 0, x: 84, w: 166)
        } else {
            drawText(s, st.kind == "bonus" ? "CAT CAFE" : "FLOOR \(n)", 136, 3, "yellow", align: .center, shadow: nil)
            drawText(s, "HI \(max(best, score))", 252, 3, "gray", align: .right, shadow: nil)
        }
        hearts(s, W - 62, 2, lives, maxShow: 5)
        let x0 = W - 62, y0 = 10
        s.fillRect(col("darkgray"), x0, y0, 40, 2)
        if hype.feverOn {
            for i in 0 ..< 40 { s.fillRect(col(rainbow(i / 5, t)), x0 + i, y0, 1, 2) }
        } else {
            s.fillRect(col("orange"), x0, y0, Int(40 * hype.fever), 2)
        }
        s.fillRect(col("darkgray"), 0, HUD_H - 1, W, 1)
    }

    private func drawField(_ s: Surface, _ t: Double) {
        guard let b = battle else { return }
        drawTofu(s, 38, GROUND, t, heroPose, flash: heroFlash > 0 && Int(t * 30) % 2 == 1)
        let h = b.hero
        hpBar(s, 14, GROUND + 1, 50, h.hp, h.maxhp, h.block)
        var sx = 6
        for (val, icon, c) in [(h.zoom, "md_i_up", "orange"), (h.fluff, "md_i_shield", "sky"), (h.purr, "md_i_heart", "pink"),
                               (h.spiky, "md_i_spiky", "gray"), (h.startled, "md_i_down", "lavender"),
                               (h.soaked, "md_i_drop", "sky")] where val != 0 {
            s.blit(sprite(icon), sx, GROUND - 46)
            drawText(s, "\(val)", sx + 8, GROUND - 46, c, shadow: "black")
            sx += 8 + textWidth("\(val)") + 3
        }
        // the cat that was just played pops in next to TOFU
        if let cm = cameo, cm.t < 0.7 || Int(t * 20) % 2 == 1 {
            let c = cm.card
            let y = 26 + Int((1 - easeOut(min(1, cm.t / 0.15))) * 18)
            s.rect(col("black"), IRect(57, y + 1, 52, 52), radius: 4)
            s.rect(col(MD.roleColor(c.d.role)), IRect(56, y, 52, 52), radius: 4)
            s.blit(sprite(c.d.spr, 0, scale: 2), 58, y + 2)
            drawText(s, c.name, 82, y - 9, "yellow", align: .center, shadow: nil, outline: "black")
        }
        for (k, fo) in b.foes.enumerated() {
            let v = fx(k)
            if !fo.alive && v.dead <= 0 { continue }
            drawFoe(s, k, fo, v, t)
        }
        // target info line
        if ["player", "anim"].contains(state) && tgt >= 0 && tgt < b.foes.count && b.foes[tgt].alive {
            let fo = b.foes[tgt]
            let info = fo.name + ": " + (fo.sleepy ? "SLEEPING" : st.mod == "foggy" ? "???" : intentLabel(fo))
            let w = textWidth(info) + 8
            s.fillRect(col("black"), W - w - 2, HUD_H + 2, w, 10)
            drawText(s, info, W - 6, HUD_H + 4, "white", align: .right, shadow: nil)
        }
        if let f = flying {
            let a = easeOut(min(1, f.t / 0.2))
            let x = Double(f.x0) + Double(f.x1 - f.x0) * a
            let y = Double(f.y0) + Double(f.y1 - f.y0) * a - sin(a * .pi) * 24
            drawMini(s, f.card, Int(x), Int(y), t, b)
        }
    }

    private func intentLabel(_ fo: MDFoe) -> String {
        let mv = fo.intent
        var txt = INTENT_TEXT[mv.kind] ?? mv.kind.uppercased()
        if mv.kind == "atk" || mv.kind == "atkblk" {
            let (d, hits) = battle!.intentDamage(fo)
            txt += " \(d)" + (hits > 1 ? "X\(hits)" : "")
        }
        return txt
    }

    private func hpBar(_ s: Surface, _ x: Int, _ y: Int, _ w: Int, _ hp: Int, _ maxhp: Int, _ block: Int = 0) {
        s.fillRect(col("black"), x - 1, y - 1, w + 2, 6)
        s.fillRect(col("darkgray"), x, y, w, 4)
        let fw = Int(Double(w) * Double(max(0, hp)) / Double(max(1, maxhp)))
        s.fillRect(col(Double(hp) > Double(maxhp) * 0.3 || Int(t * 6) % 2 == 1 ? "red" : "yellow"), x, y, fw, 4)
        s.fillRect(col("pink"), x, y, fw, 1)
        drawText(s, "\(max(0, hp))/\(maxhp)", x + w / 2, y + 5, "white", align: .center, shadow: "black")
        if block > 0 {
            s.blit(sprite("md_i_shield"), x - 9, y - 3)
            drawText(s, "\(block)", x - 6, y + 5, "sky", align: .center, shadow: "black")
        }
    }

    private func drawFoe(_ s: Surface, _ k: Int, _ fo: MDFoe, _ v: MDFoeFx, _ t: Double) {
        var sp = sprite(fo.spr, Int(t * 2 + Double(k)) % 2)
        let w = sp.w, h = sp.h
        let x = foeX(k)
        let lunge = v.lunge > 0 ? sin(min(1, v.lunge / 0.3) * .pi) * 12 : 0
        let shake = v.shake > 0 ? Int(sin(t * 60) * 2) : 0
        let dx = Int(Double(x - w / 2) - lunge) + shake
        var dy = GROUND - h
        if !fo.alive {
            if Int(t * 20) % 2 == 1 { return }
            dy += Int((0.6 - v.dead) * 20)
        }
        if v.flash > 0 && Int(t * 30) % 2 == 1 { sp = sprite(fo.spr, 0, remap: WHITE_REMAP) }
        if fo.sleepy && fo.alive { drawText(s, "Z", dx + w - 4, dy - 6 - Int(t * 4) % 4, "white", shadow: "black") }
        s.blit(sp, dx, dy)
        if !fo.alive { return }
        let bw = min(44, max(30, w))
        hpBar(s, x - bw / 2, GROUND + 1, bw, fo.hp, fo.maxhp, fo.block)
        // intent bubble
        let iy = dy - 12 + Int(sin(t * 4 + Double(k)) * 1.5)
        var icon = "md_i_quest", txt = "", c = "white"
        if fo.sleepy {
            icon = "md_i_zzz"
        } else if st.mod == "foggy" {
            txt = "?"
        } else {
            let mv = fo.intent
            icon = INTENT_ICON[mv.kind] ?? "md_i_quest"
            switch mv.kind {
            case "atk", "atkblk":
                let (d, hits) = battle!.intentDamage(fo)
                txt = "\(d)" + (hits > 1 ? "X\(hits)" : "")
                c = d * hits >= 15 ? "red" : "white"
            case "blk", "shield", "heal": txt = "\(fo.val(mv.n))"
            case "steal": txt = "-\(mv.n)"
            case "buff", "rally", "fleas": txt = "+\(mv.n)"
            case "scare", "soak": txt = "\(mv.n)"
            case "charge": txt = "!!"; c = "orange"
            default: break
            }
        }
        let tw = 9 + (txt.isEmpty ? 0 : textWidth(txt) + 1)
        s.fillRect(col("black"), x - tw / 2 - 1, iy - 1, tw + 2, 9)
        s.blit(sprite(icon), x - tw / 2, iy)
        if !txt.isEmpty { drawText(s, txt, x - tw / 2 + 9, iy + 1, c, shadow: nil) }
        // statuses
        var sx = x - bw / 2
        for (val, icon2, cc) in [(fo.zoom, "md_i_up", "orange"), (fo.scared, "md_i_down", "lavender"),
                                 (fo.dazed, "md_i_skull", "white"), (fo.itchy, "md_i_flea", "lime")] where val != 0 {
            s.blit(sprite(icon2), sx, iy - 9)
            drawText(s, "\(val)", sx + 8, iy - 9, cc, shadow: "black")
            sx += 9 + textWidth("\(val)") + 2
        }
        if fo.elite {
            let pts: [(Int, Int)] = [(x - 5, iy - 2), (x - 5, iy - 7), (x - 2, iy - 4), (x, iy - 8), (x + 2, iy - 4), (x + 5, iy - 7), (x + 5, iy - 2)]
            s.polygon(col("yellow"), pts.map { (Double($0.0), Double($0.1)) })
        }
        if ["player", "anim"].contains(state) && k == tgt {
            let cc = Int(t * 5) % 2 == 1 ? "yellow" : "white"
            let x0 = dx - 3, y0 = dy - 2, x1 = dx + w + 2, y1 = GROUND + 1
            for (cx, cy, ddx, ddy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)] {
                s.fillRect(col(cc), min(cx, cx + ddx * 4), cy, 5, 1)
                s.fillRect(col(cc), cx, min(cy, cy + ddy * 4), 1, 5)
            }
        }
    }

    private func drawPanel(_ s: Surface, _ t: Double) {
        guard let b = battle else { return }
        s.fillRect(col("night"), 0, PANEL_Y, W, H - PANEL_Y)
        s.fillRect(col("lavender"), 0, PANEL_Y, W, 1)
        // fish (energy)
        let nf = max(b.maxFish, b.hero.fish)
        for i in 0 ..< nf { s.blit(sprite(i < b.hero.fish ? "md_i_fish" : "md_i_fishoff"), HAND_X0 + i * 9, PANEL_Y + 4) }
        drawText(s, "\(b.hero.fish)/\(b.maxFish)", HAND_X0 + nf * 9 + 3, PANEL_Y + 4, "sky", shadow: nil)
        // chain
        if b.chain >= 2 {
            drawText(s, "CHAIN X\(b.chain) +\(min(b.power, b.chainCap))", 216, PANEL_Y + 4, Int(t * 6) % 2 == 1 ? "lime" : "yellow", shadow: "black")
        } else if b.echo {
            drawText(s, "ECHO READY", 216, PANEL_Y + 4, "orange", shadow: "black")
        }
        drawText(s, "DRAW \(b.drawPile.count)", HAND_X0, H - 8, "gray", shadow: nil)
        drawText(s, "DISC \(b.discard.count)", HAND_X0 + 52, H - 8, "gray", shadow: nil)
        let can = b.hand.indices.contains { b.canPlay($0) }
        let hx = W - 3 - (hype.feverOn ? 36 : 0)
        if state == "player" {
            drawText(s, hype.feverOn ? "END" : "END TURN", hx, H - 8, !can && Int(t * 4) % 2 == 1 ? "yellow" : "lavender",
                     align: .right, shadow: nil)
        } else if state == "foes" {
            drawText(s, "FOES' TURN", hx, H - 8, "red", align: .right, shadow: nil)
        }
        // hand
        var order = b.hand.indices.filter { $0 != sel }
        if sel < b.hand.count { order.append(sel) }
        for i in order {
            let c = b.hand[i]
            var (x, y) = handPos(i)
            if let d0 = dealT[c.uid], d0 < 0.2 {
                let a = easeOut(max(0, d0) / 0.2)
                x = Int(Double(W) + Double(x - W) * a)
                y = Int(Double(H) + Double(y - H) * a)
            }
            if let f = flying, f.card === c { continue }
            drawMini(s, c, x, y, t, b, dim: !b.canPlay(i), sel: i == sel && state == "player", cost: b.cost(c))
        }
        // big card
        let busy = ["player", "anim", "foes"].contains(state)
        if !b.hand.isEmpty && busy && sel < b.hand.count {
            let c = b.hand[sel]
            let m = b.link(c)
            drawBig(s, c, 2, PANEL_Y, t, cost: b.cost(c), note: m > 0 && b.last != nil ? "+\(m) CHAIN" : nil)
        } else {
            panel(s, IRect(2, PANEL_Y, BIG_W, BIG_H), fill: "ink", border: "darkgray")
            if busy {
                drawText(s, "NO CATS", 2 + BIG_W / 2, PANEL_Y + 30, "gray", align: .center, shadow: nil)
                drawText(s, "IN HAND", 2 + BIG_W / 2, PANEL_Y + 40, "gray", align: .center, shadow: nil)
            } else if !deck.isEmpty {
                drawText(s, "TOFU'S CREW", 2 + BIG_W / 2, PANEL_Y + 8, "peach", align: .center, shadow: nil)
                drawText(s, "\(deck.count) CATS", 2 + BIG_W / 2, PANEL_Y + 20, "white", align: .center, shadow: nil)
                for k in 0 ..< 3 {
                    let c = deck[(Int(t * 0.8) + k * 5) % deck.count]
                    s.blit(sprite(c.d.spr), 10 + k * 30, PANEL_Y + 34)
                }
                drawText(s, "HP \(b.hero.hp)/\(maxhp)", 2 + BIG_W / 2, PANEL_Y + 66, "pink", align: .center, shadow: nil)
            }
        }
    }

    private func drawIntro(_ s: Surface, _ t: Double) {
        if st.kind == "boss" {
            if Int(t * 4) % 2 == 1 {
                for x in stride(from: -20, to: W + 20, by: 20) {
                    let xd = Double(x)
                    s.polygon(col("red"), [(xd, 108), (xd + 10, 108), (xd + 20, 116), (xd + 10, 116)])
                    s.polygon(col("red"), [(xd, 152), (xd + 10, 152), (xd + 20, 160), (xd + 10, 160)])
                }
            }
            panel(s, IRect(40, 118, 240, 32), fill: "black", border: "red")
            drawText(s, "WARNING!!", W / 2, 122, Int(t * 6) % 2 == 1 ? "red" : "yellow", scale: 2, align: .center, outline: "ink")
            drawText(s, "\(st.name) APPROACHES", W / 2, 139, "white", align: .center, shadow: nil)
            return
        }
        let lines = 3 + (st.newLine.isEmpty ? 0 : 1) + (st.mod.isEmpty ? 0 : 1)
        let h = 30 + lines * 10
        let y0 = 120 - h / 2
        panel(s, IRect(40, y0, 240, h), fill: "ink", border: st.kind == "bonus" ? "yellow" : "peach")
        if st.kind == "bonus" {
            let title = "BONUS: CAT CAFE"
            for (i, ch) in title.enumerated() {
                drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, y0 + 6 + Int(sin(t * 8 + Double(i)) * 2),
                         rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
            }
            drawText(s, "3 FREE SPINS OF KITTY SLOTS,", W / 2, y0 + 26, "white", align: .center)
            drawText(s, "THEN SNACKS, NAPS AND NEW CATS!", W / 2, y0 + 36, "white", align: .center)
            drawText(s, "TREATS: \(treats)", W / 2, y0 + 48, "orange", align: .center)
            return
        }
        drawText(s, "FLOOR \(n)", W / 2, y0 + 6, "yellow", scale: 2, align: .center, shadow: nil, outline: "ink")
        var y = y0 + 24
        drawText(s, theme.name, W / 2, y, "lavender", align: .center)
        y += 10
        drawText(s, st.name, W / 2, y, st.elite ? "orange" : "white", align: .center)
        y += 10
        if !st.mod.isEmpty, let m = MD.mods[st.mod] {
            drawText(s, "\(m[0]): \(m[1])", W / 2, y, "sky", align: .center)
            y += 10
        }
        if !st.newLine.isEmpty {
            drawText(s, st.newLine, W / 2, y, Int(t * 4) % 2 == 1 ? "mint" : "lime", align: .center)
            y += 10
        }
        drawText(s, "TOFU: " + st.line, W / 2, y + 2, "peach", align: .center, shadow: nil)
    }

    private func drawTally(_ s: Surface, _ t: Double) {
        let h = 46 + tally.count * 11
        let y0 = 104
        panel(s, IRect(64, y0, 192, h), fill: "ink", border: "mint")
        drawText(s, st.kind == "boss" ? "BOSS CLEAR!" : "FLOOR \(n) CLEAR!", W / 2, y0 + 6, "mint", align: .center)
        for (i, row) in tally.enumerated() {
            if i > tallyI { break }
            let y = y0 + 20 + i * 11
            drawText(s, row.label, 72, y, row.v != 0 ? "white" : "gray", shadow: nil)
            drawText(s, "\(Int(row.shown))", 248, y, row.v != 0 ? "yellow" : "darkgray", align: .right, shadow: nil)
        }
        let y = y0 + 20 + tally.count * 11
        s.blit(sprite("md_i_treat"), 72, y)
        drawText(s, "TREATS +\(treatsWon)", 82, y, "orange", shadow: nil)
        if tallyI >= tally.count && Int(t * 3) % 2 == 1 {
            drawText(s, "TAP OR OK", W / 2, y0 + h - 10, "lavender", align: .center, shadow: nil)
        }
    }

    private func drawPicker(_ s: Surface, _ t: Double) {
        s.fillRect(rgba(12, 8, 24, 200), 0, 0, W, H)
        let shop = prices != nil
        let title = shop ? "CAFE ADOPTIONS" : "ADOPT A CAT!"
        for (i, ch) in title.enumerated() {
            drawText(s, String(ch), W / 2 - textWidth(title, 2) / 2 + i * 12, 16 + Int(sin(t * 6 + Double(i) * 0.6) * 2),
                     rainbow(i, t), scale: 2, shadow: nil, outline: "ink")
        }
        for (k, oc) in offers.enumerated() {
            let x = 3 + k * 106
            let appear = easeOut(min(1, max(0, stateT * 4 - Double(k) * 0.4)))
            let isSel = k == pickI
            let y = 34 + Int((1 - appear) * 120) - (isSel ? 4 : 0)
            guard let c = oc else {
                panel(s, IRect(x, y, BIG_W, BIG_H), fill: "night", border: "darkgray")
                drawText(s, "ADOPTED!", x + BIG_W / 2, y + 40, "gray", align: .center, shadow: nil)
                continue
            }
            drawBig(s, c, x, y, t)
            if isSel && Int(t * 6) % 2 == 1 { s.rect(col("white"), IRect(x - 1, y - 1, BIG_W + 2, BIG_H + 2), width: 1, radius: 5) }
            let have = deck.filter { $0.cid == c.cid }.count
            drawText(s, have == 0 ? "NEW!" : "YOU HAVE \(have)", x + BIG_W / 2, y + BIG_H + 4, have == 0 ? "mint" : "gray",
                     align: .center, shadow: nil)
            if let p = prices?[k] {
                drawText(s, "\(p) TREATS", x + BIG_W / 2, y + BIG_H + 13, treats >= p ? "orange" : "red", align: .center, shadow: nil)
            }
        }
        let isSel = pickI == offers.count
        panel(s, IRect(100, 148, 120, 18), fill: isSel ? "ink" : "night", border: isSel ? "yellow" : "darkgray")
        drawText(s, shop ? "BACK TO THE CAFE" : "SKIP: +10 TREATS", W / 2, 154, isSel ? "yellow" : "gray", align: .center, shadow: nil)
        s.blit(sprite("md_i_treat"), 4, 189)
        drawText(s, "\(treats)", 14, 190, "orange", shadow: nil)
        drawText(s, "TAP A CAT, TAP AGAIN TO TAKE IT", W - 4, 190, "lavender", align: .right, shadow: nil)
    }

    private func drawView(_ s: Surface, _ t: Double) {
        guard let v = view else { return }
        s.fillRect(rgba(12, 8, 24, 230), 0, 0, W, H)
        drawText(s, v.title, 6, 4, "yellow", shadow: nil)
        let first = viewFirst()
        let cards = v.cards
        for j in 0 ..< max(0, min(24, cards.count - first)) {
            let i = first + j
            drawMini(s, cards[i], 6 + (j % 6) * 34, 16 + (j / 6) * 43, t, sel: i == v.i)
        }
        if cards.count > first + 24 { drawText(s, "`", 104, 188, "white", shadow: nil) }
        if first > 0 { drawText(s, "|", 104, 9, "white", shadow: nil) }
        if cards.isEmpty {
            drawText(s, "NO CATS TO PICK", 104, 90, "gray", align: .center, shadow: nil)
            return
        }
        let c = cards[min(v.i, cards.count - 1)]
        let groom = v.mode == "groom"
        drawBig(s, c, 212, 12, t, upgraded: groom)
        var y = 104
        for f in c.fx {
            if let g = MD.glossary[f.op] {
                drawText(s, g, 212, y, "lavender", shadow: nil)
                y += 9
                if y > 122 { break }
            }
        }
        y = max(y, 124)
        if let b = battle, v.mode == "look" {
            drawText(s, "DRAW \(b.drawPile.count) DISC \(b.discard.count)", 212, y, "gray", shadow: nil)
            y += 10
        }
        var k = 0
        for ch in MD_CHARMS {
            let l = lv(ch.id)
            if l == 0 { continue }
            let x = 212 + (k % 5) * 21, yy = y + (k / 5) * 20
            if yy > 172 { break }
            if let ic = ch.icon { s.blit(sprite(ic), x, yy) }
            drawText(s, "\(l)", x + 13, yy + 10, "yellow", shadow: "black")
            k += 1
        }
        var hint = ["look": "TAP TO CLOSE", "groom": "TAP AGAIN: GROOM", "rehome": "TAP AGAIN: REHOME"][v.mode] ?? ""
        if groom && v.back { hint = "TAP AGAIN: GROOM" }
        drawText(s, hint, W - 4, 190, Int(t * 3) % 2 == 1 ? "lavender" : "white", align: .right, shadow: nil)
    }

    private func drawCafeScene(_ s: Surface, _ t: Double) {
        s.fillRect(col("brown"), 0, HUD_H, W, PANEL_Y - HUD_H)
        for x in stride(from: 0, to: W, by: 20) { s.fillRect(col("choco"), x, HUD_H, 10, PANEL_Y - HUD_H) }
        s.fillRect(col("peach"), 0, 92, W, 20)
        s.fillRect(col("choco"), 0, 92, W, 2)
        s.fillRect(col("cream"), 0, PANEL_Y, W, H - PANEL_Y)
        for x in stride(from: 0, to: W, by: 16) {
            for y in stride(from: PANEL_Y, to: H, by: 16) where (x / 16 + y / 16) % 2 == 1 { s.fillRect(col("peach"), x, y, 16, 16) }
        }
        for (i, x) in [22, 62, 262, 300].enumerated() {
            s.rect(col("orange"), IRect(x - 6, 36, 12, 16), radius: 3)
            s.fillRect(col("white"), x - 4, 38, 2, 10)
            if i != 0 { s.blit(sprite(MD.cats[(i * 11 + Int(t / 3)) % 60].spr), x - 12, 68) }
        }
        let happy = slots != nil && slots!.result.contains("!")
        drawTofu(s, 30, 108, t, happy ? "happy" : "idle")
    }

    private func drawSlots(_ s: Surface, _ t: Double) {
        guard let sl = slots else { return }
        panel(s, IRect(80, 30, 160, 112), fill: "red", border: "yellow", radius: 8)
        s.fillRect(col("hotpink"), 84, 34, 152, 14)
        let title = "KITTY SLOTS"
        for (i, ch) in title.enumerated() {
            drawText(s, String(ch), W / 2 - textWidth(title) / 2 + i * 6, 38, rainbow(i, t), shadow: "black")
        }
        let k = SLOT_STRIP.count
        for r in 0 ..< 3 {
            let x = 96 + r * 44
            s.rect(col("white"), IRect(x - 2, 52, 36, 64), radius: 4)
            let pos = sl.reels[r]
            let base = Int(floor(pos))
            let frac = pos - Double(base)
            for j in -1 ..< 3 {
                let sym = SLOT_STRIP[((base + j) % k + k) % k]
                let yy = 72 + Int((Double(j) - frac) * 26) - 12
                blitRows(s, sprite("md_c_" + sym), x + 5, yy, 53, 115)
            }
            s.rect(col(sl.stop[r] ? "yellow" : "black"), IRect(x - 2, 52, 36, 64), width: 2, radius: 4)
        }
        s.fillRect(col("yellow"), 90, 83, 4, 2)
        s.fillRect(col("yellow"), 226, 83, 4, 2)
        s.line(col("gray"), 244, 60, 244, 96, width: 3)
        s.circle(col("red"), 244, 58 + (sl.k < 3 && Int(t * 3) % 2 == 1 ? 12 : 0), 5)
        drawText(s, "SPINS LEFT \(sl.spins)", W / 2, 122, "white", align: .center, shadow: "black")
        if !sl.result.isEmpty {
            drawText(s, sl.result, W / 2, 131, sl.result.contains("!") ? rainbow(0, t) : "white", align: .center, shadow: "black")
        } else if sl.k < 3 && Int(t * 3) % 2 == 1 {
            drawText(s, "TAP: STOP REEL \(sl.k + 1)", W / 2, 131, "yellow", align: .center, shadow: "black")
        }
        drawText(s, "LINE UP 3 GOLDEN KITTENS FOR THE JACKPOT!", W / 2, 186, "choco", align: .center, shadow: nil)
    }

    private func drawCafe(_ s: Surface, _ t: Double) {
        panel(s, IRect(6, 22, 172, 120), fill: "ink", border: "peach")
        drawText(s, "CAT CAFE MENU", 92, 28, "peach", align: .center, shadow: nil)
        for (i, item) in cafeItems().enumerated() {
            let (label, price) = item
            let y = 46 + i * 18
            let isSel = i == cafeI
            if isSel {
                s.rect(col("deep"), IRect(10, y - 3, 164, 15), radius: 3)
                drawText(s, "}", 12, y, "yellow", shadow: nil)
            }
            drawText(s, label, 22, y, price == -1 ? "gray" : (isSel ? "yellow" : "white"), shadow: nil)
            if let p = price {
                if p > 0 {
                    drawText(s, "\(p)", 168, y, treats >= p ? "orange" : "red", align: .right, shadow: nil)
                } else if p == 0 {
                    drawText(s, "FREE", 168, y, "lime", align: .right, shadow: nil)
                } else {
                    drawText(s, "DONE", 168, y, "gray", align: .right, shadow: nil)
                }
            }
        }
        s.blit(sprite("md_barista", Int(t * 1.5) % 5 == 0 ? 1 : 0, scale: 2), 226, 44)
        s.fillRect(col("choco"), 200, 92, 110, 8)
        panel(s, IRect(186, 22, 128, 18), fill: "white", border: "ink", radius: 6, shadow: false)
        drawText(s, "BOBA: HI TOFU!", 250, 28, "ink", align: .center, shadow: nil)
        s.blit(sprite("md_i_treat"), 196, 120)
        drawText(s, "TREATS \(treats)", 206, 121, "orange", shadow: "black")
        s.blit(sprite("md_i_heart"), 196, 131)
        drawText(s, "HP \(hp)/\(maxhp)", 206, 131, "pink", shadow: "black")
        drawText(s, "TAP AN ITEM, TAP AGAIN TO CHOOSE", W / 2, 190, "choco", align: .center, shadow: nil)
    }

    // ---------------------------------------------------------------- carousel
    static func preview(_ s: Surface, _ t: Double) {
        let w = s.w, h = s.h
        let gy = h - 12
        s.fill(col("deep"))
        for y in stride(from: 0, to: gy, by: 8) { s.fillRect(col("ink"), 0, y, w, 4) }
        s.fillRect(col("darkgray"), 0, gy, w, h - gy)
        s.fillRect(col("black"), 0, gy, w, 1)
        s.blit(sprite("md_tofu", Int(t * 2) % 2), -4, gy - 30)
        let pug = sprite("md_f_pug", Int(t * 2) % 2)
        s.blit(pug, w - pug.w + 2, gy - pug.h + 2)
        s.fillRect(col("black"), w - 23, gy - 37, 18, 9)
        s.blit(sprite("md_i_claw"), w - 22, gy - 36)
        drawText(s, "6", w - 12, gy - 35, "white", shadow: nil)
        let k = Int(t * 1.5)
        for i in [0, 2, 1] {           // the middle card on top
            let card = MDCard(MD.cats[(k + i * 7) % 66].id)
            card.uid = i
            let y = 6 + abs(i - 1) * 4 + Int(sin(t * 3 + Double(i)) * 2)
            drawMini(s, card, w / 2 - 17 + (i - 1) * 15, y, t, sel: i == 1)
        }
    }
}
