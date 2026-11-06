// MEOW DECK data + battle rules (port of games/meow_deck_data.py and games/meow_deck_rules.py - keep in step).
// The card table, foes, bosses and the 200-floor campaign come from meow_deck.EXPORT (GameData.json("meow_deck"));
// every portrait / foe / icon is a sprite exported through sprites.ART, so no art code lives here.
import Foundation

// ----------------------------------------------------------------------------- data (EXPORT)
struct MDFx { let op: String; let n: Int; let hits: Int }

struct MDCat {
    let id, name, breed, role, spr: String
    let rar, cost, upcost: Int
    let fx, up: [MDFx]
    let text, uptext: [String]
}

/// A foe move: kind, n, x (hits for "atk", block for "atkblk"), id (the foe a "summon" calls).
struct MDMove { let kind: String; let n: Int; let x: Int; let id: String }

struct MDFoeData { let name, spr: String; let hp, tier: Int; let moves: [MDMove] }
struct MDBossData { let name, spr: String; let hp: Int }

struct MDFoeSpec {
    let id: String
    var hp: Int
    var pow: Double
    let blk, zoom: Int
    let boss, elite: Bool
    let phases: [[MDMove]]
}

struct MDStage {
    let n, tier, theme, treats: Int
    let kind, name, mod, newLine, line: String
    let elite: Bool
    let foes: [MDFoeSpec]
}

struct MDTheme { let name, sky, sky2, ground, ground2: String; let deco: Int }
struct MDCharm { let id, name, desc, color, icon: String; let max: Int }

enum MD {
    private static func num(_ v: Any?) -> Double { (v as? NSNumber)?.doubleValue ?? 0 }
    private static func int(_ v: Any?) -> Int { Int(num(v)) }
    private static let root: [String: Any] = (GameData.json("meow_deck") as? [String: Any]) ?? [:]

    private static func fxList(_ v: Any?) -> [MDFx] {
        ((v as? [[Any]]) ?? []).map { a in
            MDFx(op: a[0] as? String ?? "", n: a.count > 1 ? int(a[1]) : 0, hits: a.count > 2 ? int(a[2]) : 1)
        }
    }

    static func move(_ a: [Any]) -> MDMove {
        let kind = a.first as? String ?? "nap"
        var n = 0, id = ""
        if a.count > 1 { if let s = a[1] as? String { id = s } else { n = int(a[1]) } }
        let x = a.count > 2 ? int(a[2]) : (kind == "atk" ? 1 : 0)
        return MDMove(kind: kind, n: n, x: x, id: id)
    }

    private static func moves(_ v: Any?) -> [MDMove] { ((v as? [[Any]]) ?? []).map { move($0) } }

    static let cats: [MDCat] = ((root["cats"] as? [[String: Any]]) ?? []).map { d in
        MDCat(id: d["id"] as? String ?? "", name: d["name"] as? String ?? "", breed: d["breed"] as? String ?? "",
              role: d["role"] as? String ?? "", spr: d["spr"] as? String ?? "", rar: int(d["rar"]), cost: int(d["cost"]),
              upcost: int(d["upcost"]), fx: fxList(d["fx"]), up: fxList(d["up"]),
              text: d["text"] as? [String] ?? [], uptext: d["uptext"] as? [String] ?? [])
    }
    static let cat: [String: MDCat] = Dictionary(uniqueKeysWithValues: cats.map { ($0.id, $0) })

    static let foes: [String: MDFoeData] = ((root["foes"] as? [String: [String: Any]]) ?? [:]).mapValues { d in
        MDFoeData(name: d["name"] as? String ?? "", spr: d["spr"] as? String ?? "", hp: int(d["hp"]), tier: int(d["tier"]),
                  moves: moves(d["moves"]))
    }
    static let bosses: [String: MDBossData] = ((root["bosses"] as? [String: [String: Any]]) ?? [:]).mapValues { d in
        MDBossData(name: d["name"] as? String ?? "", spr: d["spr"] as? String ?? "", hp: int(d["hp"]))
    }

    static let stages: [MDStage] = ((root["stages"] as? [[String: Any]]) ?? []).map { d in
        let fs = ((d["foes"] as? [[String: Any]]) ?? []).map { f -> MDFoeSpec in
            let ph = ((f["phases"] as? [[[Any]]]) ?? []).map { p in p.map { move($0) } }
            return MDFoeSpec(id: f["id"] as? String ?? "", hp: int(f["hp"]), pow: num(f["pow"]), blk: int(f["blk"]),
                             zoom: int(f["zoom"]), boss: f["boss"] as? Bool ?? false, elite: f["elite"] as? Bool ?? false,
                             phases: ph)
        }
        return MDStage(n: int(d["n"]), tier: int(d["tier"]), theme: int(d["theme"]), treats: int(d["treats"]),
                       kind: d["kind"] as? String ?? "normal", name: d["name"] as? String ?? "", mod: d["mod"] as? String ?? "",
                       newLine: d["new"] as? String ?? "", line: d["line"] as? String ?? "",
                       elite: d["elite"] as? Bool ?? false, foes: fs)
    }

    static let themes: [MDTheme] = ((root["themes"] as? [[Any]]) ?? []).map { a in
        MDTheme(name: a[0] as? String ?? "", sky: a[1] as? String ?? "deep", sky2: a[2] as? String ?? "ink",
                ground: a[3] as? String ?? "darkgray", ground2: a[4] as? String ?? "gray", deco: int(a[5]))
    }
    static let charms: [MDCharm] = ((root["charms"] as? [[Any]]) ?? []).map { a in
        MDCharm(id: a[0] as? String ?? "", name: a[1] as? String ?? "", desc: a[2] as? String ?? "",
                color: a[3] as? String ?? "mint", icon: a[4] as? String ?? "", max: int(a[5]))
    }
    static let mods: [String: [String]] = (root["mods"] as? [String: [String]]) ?? [:]
    static let starter: [String] = root["starter"] as? [String] ?? []
    static let pool: [String] = root["pool"] as? [String] ?? []
    static let breeds: [String: String] = root["breeds"] as? [String: String] ?? [:]
    static let roles: [String: [String]] = root["roles"] as? [String: [String]] ?? [:]
    static let glossary: [String: String] = root["glossary"] as? [String: String] ?? [:]
    static let plan: [String] = root["plan"] as? [String] ?? []
    static let rarity: [[String]] = root["rarity"] as? [[String]] ?? []
    static let price: [Int] = ((root["price"] as? [Any]) ?? []).map { int($0) }
    static let lines: [String] = root["lines"] as? [String] ?? ["LET'S GO!"]
    static let targeted: Set<String> = Set(root["targeted"] as? [String] ?? [])
    static let roleOrder: [String] = root["roleorder"] as? [String] ?? []

    static func roleColor(_ role: String) -> String { roles[role]?[1] ?? "gray" }
    static func roleLabel(_ role: String) -> String { roles[role]?[0] ?? "" }

    static func hpMult(_ n: Int) -> Double { 1.0 + 0.055 * Double(n - 1) + 0.00012 * Double((n - 1) * (n - 1)) }
    /// Rarity weights (common, rare, epic, legend) for card rewards on a tier.
    static func rewardWeights(_ tier: Int) -> [Double] {
        [Double(max(30, 70 - 3 * tier)), Double(25 + tier), Double(5 + tier), Double(tier / 2)]
    }
}

/// Random numbers for the battle (the Python side uses random.Random; only the rules must match, not the stream).
final class MDRng {
    private var g = SystemRandomNumberGenerator()
    func random() -> Double { Double.random(in: 0 ..< 1, using: &g) }
    func below(_ n: Int) -> Int { n <= 0 ? 0 : Int.random(in: 0 ..< n, using: &g) }
    func shuffle<T>(_ a: inout [T]) { a.shuffle(using: &g) }
}

// ----------------------------------------------------------------------------- battle
let MD_HERO = -1
let MD_BASE_HP = 70

/// One cat in the deck. up = groomed (upgraded); gold = turned golden this draw (cost 0, double power).
final class MDCard {
    private static var next = 1
    let cid: String
    var up: Bool
    var gold = false
    var uid: Int
    init(_ cid: String, _ up: Bool = false) {
        self.cid = cid; self.up = up
        uid = MDCard.next
        MDCard.next += 1
    }
    var d: MDCat { MD.cat[cid] ?? MD.cats[0] }
    var name: String { d.name + (up ? "+" : "") }
    var fx: [MDFx] { up ? d.up : d.fx }
    var text: [String] { up ? d.uptext : d.text }
    var baseCost: Int { up ? d.upcost : d.cost }
    func has(_ op: String) -> Bool { fx.contains { $0.op == op } }
    var targeted: Bool { fx.contains { MD.targeted.contains($0.op) } }
}

final class MDHero {
    var hp, maxhp: Int
    var block = 0, fish = 0
    var zoom = 0, fluff = 0, purr = 0, spiky = 0
    var startled = 0, soaked = 0, stolen = 0
    init(_ hp: Int, _ maxhp: Int) { self.hp = hp; self.maxhp = maxhp }
}

final class MDFoe {
    let id: String
    let boss, elite: Bool
    let name, spr: String
    var hp, maxhp: Int
    var pow: Double
    var block, zoom: Int
    let phases: [[MDMove]]
    var phase = 0, mi = 0
    var scared = 0, dazed = 0, itchy = 0
    var sleepy = false
    var slot: Int
    var intent = MDMove(kind: "nap", n: 0, x: 0, id: "")

    init(_ spec: MDFoeSpec, _ slot: Int, _ rng: MDRng) {
        id = spec.id
        boss = spec.boss
        elite = spec.elite
        if boss, let b = MD.bosses[id] {
            name = b.name; spr = b.spr
            phases = spec.phases
        } else {
            let f = MD.foes[id]
            name = f?.name ?? id.uppercased(); spr = f?.spr ?? "md_f_pug"
            phases = [f?.moves ?? [MDMove(kind: "nap", n: 0, x: 0, id: "")]]
        }
        hp = spec.hp; maxhp = spec.hp
        pow = spec.pow
        block = spec.blk; zoom = spec.zoom
        self.slot = slot
        mi = boss ? 0 : rng.below(phases[0].count)
        pickIntent()
    }

    var alive: Bool { hp > 0 }

    func pickIntent() {
        let mv = phases[phase]
        intent = mv[mi % mv.count]
        mi += 1
    }

    func val(_ n: Int) -> Int { Int(Double(n) * pow + 0.5) }

    func atkValue(_ n: Int) -> Int {
        var d = val(n) + zoom
        if scared > 0 { d = d * 3 / 4 }
        return max(0, d)
    }
}

struct MDEv { let kind: String; let who: Int; let n: Int; let s: String }

final class MDBattle {
    let st: MDStage
    let n: Int
    let rng: MDRng
    let charms: [String: Int]
    let hero: MDHero
    var foes: [MDFoe] = []
    var drawPile: [MDCard], hand: [MDCard] = [], discard: [MDCard] = [], exhaust: [MDCard] = []
    var turn = 0
    var chain = 0                 // cats in the current chain
    var power = 0                 // chain power (added to dmg / block / heal)
    var last: MDCard?             // last card played this turn
    var echo = false
    var bestChain = 0
    var dmgTaken = 0, dmgDealt = 0
    var fever = false             // set by the scene while FEVER is on (cats cost 1 less)
    let mod: String
    let handSize, maxFish: Int
    let goldChance: Double
    let chainCap: Int

    init(_ st: MDStage, _ deck: [MDCard], _ hp: Int, _ maxhp: Int, _ charms: [String: Int], _ rng: MDRng, _ diff: Double = 1.0) {
        self.st = st
        n = st.n
        self.rng = rng
        self.charms = charms
        hero = MDHero(hp, maxhp)
        mod = st.mod
        handSize = 5 + (charms["nose"] ?? 0) - (st.mod == "windy" ? 1 : 0)
        maxFish = 3 + (charms["bowl"] ?? 0) + (st.mod == "catnip" ? 1 : 0)
        goldChance = 0.005 + 0.003 * Double(charms["bell"] ?? 0)
        chainCap = 6 + 3 * (charms["post"] ?? 0)
        drawPile = deck
        for (i, s) in st.foes.enumerated() {
            var spec = s
            spec.pow = s.pow * diff
            foes.append(MDFoe(spec, s.boss ? 2 : i, rng))
        }
        rng.shuffle(&drawPile)
        hero.zoom = charms["claws"] ?? 0
        hero.fluff = charms["coat"] ?? 0
        if mod == "lazy" { for f in foes { f.sleepy = true } }
    }

    // ------------------------------------------------------------------ helpers
    func alive() -> [MDFoe] { foes.filter { $0.alive } }
    var won: Bool { alive().isEmpty }
    var lost: Bool { hero.hp <= 0 }

    func cost(_ card: MDCard) -> Int {
        if card.gold { return 0 }
        var c = card.baseCost
        if fever { c = max(0, c - 1) }
        return c
    }

    func canPlay(_ i: Int) -> Bool {
        if i < 0 || i >= hand.count { return false }
        return cost(hand[i]) <= hero.fish
    }

    /// Chain link value of playing card after the last one: role +1, breed +1, wild 1.
    func link(_ card: MDCard) -> Int {
        guard let p = last else { return 0 }
        var m = (card.d.role == p.d.role ? 1 : 0) + (card.d.breed == p.d.breed ? 1 : 0)
        if m == 0 && card.has("wild") { m = 1 }
        return m
    }

    func draw(_ k: Int, _ ev: inout [MDEv]) {
        var got = 0
        for _ in 0 ..< max(0, k) {
            if hand.count >= 10 { break }
            if drawPile.isEmpty {
                if discard.isEmpty { break }
                drawPile = discard
                discard = []
                rng.shuffle(&drawPile)
                ev.append(MDEv(kind: "shuffle", who: MD_HERO, n: 0, s: ""))
            }
            let c = drawPile.removeLast()
            if c.cid != "fleas" && rng.random() < goldChance {
                c.gold = true
                ev.append(MDEv(kind: "golden", who: MD_HERO, n: c.uid, s: c.name))
            }
            hand.append(c)
            got += 1
        }
        if got > 0 { ev.append(MDEv(kind: "draw", who: MD_HERO, n: got, s: "")) }
    }

    // ------------------------------------------------------------------ flow
    func start() -> [MDEv] {
        var ev: [MDEv] = []
        beginTurn(&ev)
        return ev
    }

    func beginTurn(_ ev: inout [MDEv]) {
        let h = hero
        turn += 1
        let keep = 5 * (charms["blanket"] ?? 0)
        h.block = min(h.block, keep)
        h.fish = max(0, maxFish - h.stolen)
        if h.stolen > 0 { ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "-\(h.stolen) FISH")) }
        h.stolen = 0
        if h.purr > 0 {
            heal(h.purr, &ev)
            h.purr -= 1
        }
        chain = 0; power = 0
        last = nil
        draw(handSize, &ev)
        ev.append(MDEv(kind: "turn", who: MD_HERO, n: turn, s: ""))
    }

    /// Play hand[i] at foe index target. Returns events.
    func play(_ i: Int, _ target: Int) -> [MDEv] {
        var ev: [MDEv] = []
        let card = hand.remove(at: i)
        hero.fish -= cost(card)
        let m = link(card)
        if m > 0 {
            chain += 1
            power += m
        } else {
            chain = 1
            power = 0
        }
        bestChain = max(bestChain, chain)
        let bonus = min(power, chainCap)
        ev.append(MDEv(kind: "play", who: MD_HERO, n: m, s: card.name))
        let times = echo && !card.has("echo") ? 2 : 1
        if times == 2 {
            echo = false
            ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "ECHO!"))
        }
        let mult = card.gold ? 2 : 1
        for _ in 0 ..< times { resolve(card, target, bonus, mult, &ev) }
        last = card
        if card.gold { ev.append(MDEv(kind: "jackpot", who: MD_HERO, n: 0, s: card.name)) }
        card.gold = false
        if card.has("once") { exhaust.append(card) } else { discard.append(card) }
        return ev
    }

    func resolve(_ card: MDCard, _ target0: Int, _ bonus: Int, _ mult: Int, _ ev: inout [MDEv]) {
        let h = hero
        var target = target0
        if target < 0 || target >= foes.count || !foes[target].alive {
            target = foes.firstIndex { $0.alive } ?? 0
        }
        for f in card.fx {
            let n = f.n, hits = f.hits
            switch f.op {
            case "dmg":
                for _ in 0 ..< hits where foes[target].alive { hitFoe(target, n * mult + bonus + h.zoom, &ev) }
            case "all":
                for k in foes.indices where foes[k].alive { hitFoe(k, n * mult + bonus + h.zoom, &ev) }
            case "rnd":
                for _ in 0 ..< hits * mult {
                    let al = foes.indices.filter { foes[$0].alive }
                    if !al.isEmpty { hitFoe(al[rng.below(al.count)], n + bonus + h.zoom, &ev) }
                }
            case "slam":
                if foes[target].alive { hitFoe(target, h.block * mult + bonus + h.zoom, &ev) }
            case "block": gainBlock(n * mult + bonus, &ev)
            case "heal": heal(n * mult + bonus, &ev)
            case "draw": draw(n * mult, &ev)
            case "fish":
                h.fish += n * mult
                ev.append(MDEv(kind: "fish", who: MD_HERO, n: n * mult, s: ""))
            case "zoom":
                h.zoom += n * mult
                ev.append(MDEv(kind: "buff", who: MD_HERO, n: n * mult, s: "POWER"))
            case "fluff":
                h.fluff += n * mult
                ev.append(MDEv(kind: "buff", who: MD_HERO, n: n * mult, s: "FLUFF"))
            case "purr":
                h.purr += n * mult
                ev.append(MDEv(kind: "buff", who: MD_HERO, n: n * mult, s: "PURR"))
            case "spiky":
                h.spiky += n * mult
                ev.append(MDEv(kind: "buff", who: MD_HERO, n: n * mult, s: "SPIKY"))
            case "scare", "daze", "itchy", "sleep":
                if foes[target].alive { debuff(target, f.op, n * mult, &ev) }
            case "scareall", "dazeall", "itchyall":
                for k in foes.indices where foes[k].alive { debuff(k, String(f.op.dropLast(3)), n * mult, &ev) }
            case "fever":
                ev.append(MDEv(kind: "fever", who: MD_HERO, n: n * mult, s: ""))
            case "echo":
                echo = true
                ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "NEXT CAT X2!"))
            case "cleanse":
                h.startled = 0; h.soaked = 0
                ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "ALL BETTER!"))
            case "scratch":
                ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "SCRATCH!"))
            default: break
            }
        }
    }

    func debuff(_ k: Int, _ what: String, _ n: Int, _ ev: inout [MDEv]) {
        let fo = foes[k]
        switch what {
        case "scare": fo.scared += n; ev.append(MDEv(kind: "debuff", who: k, n: n, s: "SCARED"))
        case "daze": fo.dazed += n; ev.append(MDEv(kind: "debuff", who: k, n: n, s: "DAZED"))
        case "itchy": fo.itchy += n; ev.append(MDEv(kind: "debuff", who: k, n: n, s: "ITCHY"))
        case "sleep": fo.sleepy = true; ev.append(MDEv(kind: "debuff", who: k, n: 1, s: "SLEEPY"))
        default: break
        }
    }

    func hitFoe(_ k: Int, _ raw: Int, _ ev: inout [MDEv]) {
        let fo = foes[k]
        var d = max(0, raw)
        if hero.startled > 0 { d = d * 3 / 4 }
        if fo.dazed > 0 { d = d * 3 / 2 }
        let blocked = min(fo.block, d)
        fo.block -= blocked
        d -= blocked
        fo.hp -= d
        dmgDealt += d
        ev.append(MDEv(kind: "hit", who: k, n: d, s: "\(blocked)"))
        if fo.hp <= 0 {
            fo.hp = 0
            died(k, &ev)
        } else if fo.boss {
            checkPhase(k, &ev)
        }
    }

    /// Foe k is out. When a boss falls its helpers run away.
    func died(_ k: Int, _ ev: inout [MDEv]) {
        let fo = foes[k]
        ev.append(MDEv(kind: "die", who: k, n: 0, s: fo.name))
        if fo.boss {
            for (j, o) in foes.enumerated() where o.alive {
                o.hp = 0
                ev.append(MDEv(kind: "die", who: j, n: 0, s: o.name))
            }
        }
    }

    func checkPhase(_ k: Int, _ ev: inout [MDEv]) {
        let fo = foes[k]
        let n = fo.phases.count
        if fo.phase >= n - 1 { return }
        let cut = n == 2 ? [0.5] : [0.66, 0.33]
        if Double(fo.hp) <= Double(fo.maxhp) * cut[fo.phase] {
            fo.phase += 1
            fo.mi = 0
            fo.scared = 0; fo.dazed = 0
            fo.sleepy = false
            fo.pickIntent()
            ev.append(MDEv(kind: "phase", who: k, n: fo.phase + 1, s: fo.name))
        }
    }

    func gainBlock(_ n: Int, _ ev: inout [MDEv]) {
        var b = max(0, n + hero.fluff)
        if hero.soaked > 0 { b = b * 3 / 4 }
        hero.block += b
        ev.append(MDEv(kind: "block", who: MD_HERO, n: b, s: ""))
    }

    func heal(_ n: Int, _ ev: inout [MDEv]) {
        let got = max(0, min(n, hero.maxhp - hero.hp))
        hero.hp += got
        ev.append(MDEv(kind: "heal", who: MD_HERO, n: got, s: ""))
    }

    /// Discard the hand (FLEAS still in hand bite). Returns events.
    func endTurn() -> [MDEv] {
        var ev: [MDEv] = []
        let fleas = hand.filter { $0.cid == "fleas" }.count
        if fleas > 0 { hurtHero(2 * fleas, nil, &ev, pierce: true) }
        for c in hand { c.gold = false }
        discard.append(contentsOf: hand)
        hand = []
        hero.startled = max(0, hero.startled - 1)
        hero.soaked = max(0, hero.soaked - 1)
        chain = 0; power = 0
        last = nil
        return ev
    }

    func hurtHero(_ d0: Int, _ k: Int?, _ ev: inout [MDEv], pierce: Bool = false) {
        let h = hero
        let blocked = pierce ? 0 : min(h.block, d0)
        h.block -= blocked
        let d = d0 - blocked
        h.hp = max(0, h.hp - d)
        dmgTaken += d
        ev.append(MDEv(kind: "hurt", who: MD_HERO, n: d, s: "\(blocked)"))
        if let k = k, h.spiky > 0, foes[k].alive {
            let fo = foes[k]
            fo.hp = max(0, fo.hp - h.spiky)
            ev.append(MDEv(kind: "hit", who: k, n: h.spiky, s: "0"))
            if fo.hp <= 0 { died(k, &ev) }
        }
    }

    /// Foe k takes its turn. Returns events (empty if it is dead).
    func foeAct(_ k: Int) -> [MDEv] {
        var ev: [MDEv] = []
        let fo = foes[k]
        if !fo.alive || lost { return ev }
        fo.block = 0
        if fo.itchy > 0 {
            fo.hp = max(0, fo.hp - fo.itchy)
            ev.append(MDEv(kind: "hit", who: k, n: fo.itchy, s: "ITCHY"))
            fo.itchy -= 1
            if fo.hp <= 0 {
                died(k, &ev)
                return ev
            }
        }
        if fo.sleepy {
            fo.sleepy = false
            ev.append(MDEv(kind: "text", who: k, n: 0, s: "ZZZ..."))
        } else {
            doMove(k, fo.intent, &ev)
            if fo.alive { fo.pickIntent() }
        }
        fo.scared = max(0, fo.scared - 1)
        fo.dazed = max(0, fo.dazed - 1)
        return ev
    }

    func doMove(_ k: Int, _ mv: MDMove, _ ev: inout [MDEv]) {
        let fo = foes[k]
        let h = hero
        let n = mv.n
        ev.append(MDEv(kind: "act", who: k, n: 0, s: mv.kind))
        switch mv.kind {
        case "atk", "atkblk":
            let hits = mv.kind == "atk" ? max(1, mv.x) : 1
            for _ in 0 ..< hits where h.hp > 0 && fo.alive { hurtHero(fo.atkValue(n), k, &ev) }
            if mv.kind == "atkblk" {
                fo.block += fo.val(mv.x)
                ev.append(MDEv(kind: "fblock", who: k, n: fo.val(mv.x), s: ""))
            }
        case "blk":
            fo.block += fo.val(n)
            ev.append(MDEv(kind: "fblock", who: k, n: fo.val(n), s: ""))
        case "shield":
            for (j, o) in foes.enumerated() where o.alive {
                o.block += fo.val(n)
                ev.append(MDEv(kind: "fblock", who: j, n: fo.val(n), s: ""))
            }
        case "buff":
            fo.zoom += n
            ev.append(MDEv(kind: "fbuff", who: k, n: n, s: "POWER UP"))
        case "rally":
            for (j, o) in foes.enumerated() where o.alive {
                o.zoom += n
                ev.append(MDEv(kind: "fbuff", who: j, n: n, s: "RALLY!"))
            }
        case "scare":
            h.startled += n
            ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "STARTLED!"))
        case "soak":
            h.soaked += n
            ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "SOAKED!"))
        case "fleas":
            for _ in 0 ..< n { discard.append(MDCard("fleas")) }
            ev.append(MDEv(kind: "junk", who: MD_HERO, n: n, s: ""))
        case "heal":
            let al = foes.indices.filter { foes[$0].alive && foes[$0].hp < foes[$0].maxhp }
            if let j = al.min(by: { Double(foes[$0].hp) / Double(foes[$0].maxhp) < Double(foes[$1].hp) / Double(foes[$1].maxhp) }) {
                let o = foes[j]
                let got = min(fo.val(n), o.maxhp - o.hp)
                o.hp += got
                ev.append(MDEv(kind: "fheal", who: j, n: got, s: ""))
            }
        case "summon":
            let free = [0, 1].filter { s in !foes.contains { $0.alive && $0.slot == s } }
            if let f0 = free.first, alive().count < 3, let data = MD.foes[mv.id] {
                let spec = MDFoeSpec(id: mv.id, hp: Int(Double(data.hp) * MD.hpMult(self.n) * 0.6), pow: fo.pow, blk: 0,
                                     zoom: 0, boss: false, elite: false, phases: [])
                let new = MDFoe(spec, f0, rng)
                new.pow = fo.pow
                // reuse a dead slot entry so foe indices stay stable for the scene
                var j: Int
                if let dead = foes.firstIndex(where: { !$0.alive && !$0.boss }) {
                    j = dead
                    foes[j] = new
                } else {
                    foes.append(new)
                    j = foes.count - 1
                }
                ev.append(MDEv(kind: "summon", who: j, n: 0, s: new.name))
            } else {
                fo.zoom += 1
                ev.append(MDEv(kind: "fbuff", who: k, n: 1, s: "POWER UP"))
            }
        case "steal":
            h.stolen += n
            ev.append(MDEv(kind: "text", who: MD_HERO, n: 0, s: "FISH SNATCHED!"))
        case "charge":
            ev.append(MDEv(kind: "text", who: k, n: 0, s: "CHARGING!"))
        case "nap":
            ev.append(MDEv(kind: "text", who: k, n: 0, s: "ZZZ..."))
        default: break
        }
    }

    /// (per-hit damage, hits) of a foe's shown attack, or (0, 0).
    func intentDamage(_ fo: MDFoe) -> (Int, Int) {
        let mv = fo.intent
        if mv.kind == "atk" { return (fo.atkValue(mv.n), max(1, mv.x)) }
        if mv.kind == "atkblk" { return (fo.atkValue(mv.n), 1) }
        return (0, 0)
    }

    /// Main number shown on a card in hand with the current bonuses (dmg / block / heal), or nil.
    func preview(_ card: MDCard) -> (String, Int, Int)? {
        let h = hero
        let m = link(card)
        let pw = m > 0 ? power + m : 0
        let bonus = min(pw, chainCap)
        let mult = card.gold ? 2 : 1
        for f in card.fx {
            switch f.op {
            case "dmg", "all", "rnd", "slam":
                var v = (f.op == "slam" ? h.block : f.n) * (f.op != "rnd" ? mult : 1) + bonus + h.zoom
                if h.startled > 0 { v = v * 3 / 4 }
                return ("dmg", v, f.hits)
            case "block":
                var v = f.n * mult + bonus + h.fluff
                if h.soaked > 0 { v = v * 3 / 4 }
                return ("block", v, 1)
            case "heal":
                return ("heal", f.n * mult + bonus, 1)
            default: continue
            }
        }
        return nil
    }
}

// ----------------------------------------------------------------------------- rewards and checkpoint crews
/// Weighted index pick (same algorithm on both platforms).
func mdWpick(_ rng: MDRng, _ weights: [Double]) -> Int {
    let total = weights.reduce(0, +)
    var x = rng.random() * total
    for (i, w) in weights.enumerated() {
        x -= w
        if x < 0 { return i }
    }
    return weights.count - 1
}

/// A random cat for a reward / shop slot on this tier.
func mdRewardCard(_ rng: MDRng, _ tier: Int, _ exclude: [String] = []) -> String {
    let rar = mdWpick(rng, MD.rewardWeights(tier))
    var ids = MD.pool.filter { MD.cat[$0]?.rar == rar && !exclude.contains($0) }
    if ids.isEmpty { ids = MD.pool.filter { !exclude.contains($0) } }
    return ids[Int(rng.random() * Double(ids.count))]
}

/// A plausible crew for a player who reached this tier (checkpoint starts). Returns (deck, charms, max hp).
func mdReferenceKit(_ tier: Int, _ rng: MDRng) -> ([MDCard], [String: Int], Int) {
    var deck = MD.starter.map { MDCard($0) }
    for k in 0 ..< min(5, tier) {                  // a few basics get rehomed along the way
        let cid = k % 2 == 0 ? "rio" : "sue"
        if let i = deck.firstIndex(where: { $0.cid == cid }) { deck.remove(at: i) }
    }
    for _ in 0 ..< min(18, 3 + 3 * tier) { deck.append(MDCard(mdRewardCard(rng, tier))) }
    let up = min(0.85, 0.08 * Double(tier))
    for c in deck where rng.random() < up { c.up = true }
    var charms: [String: Int] = [:]
    for cid in MD.plan.prefix(tier) { charms[cid, default: 0] += 1 }
    return (deck, charms, MD_BASE_HP + 12 * (charms["nap"] ?? 0))
}
