// Front-end scenes: title, profiles, main menu, game select, setup, options, scores, results (port of ui.py).
import Foundation

let RAINBOW = ["pink", "peach", "yellow", "lime", "mint", "sky", "lavender"]

func mochiAvatar(_ s: Surface, _ x: Int, _ y: Int, _ color: String = "white", _ t: Double = 0, scale: Int = 1) {
    let chars: [String: Character] = ["pink": "p", "peach": "e", "mint": "m", "sky": "s", "lavender": "v", "yellow": "y", "lime": "l"]
    var remap: [Character: Character]?
    if let c = chars[color] { remap = ["w": c]; if c == "p" { remap?["p"] = "P" } }
    s.blit(sprite("momo_idle", Int(t * 2) % 2, remap: remap, scale: scale), x, y)
}

func footer(_ s: Surface, _ text: String) {
    s.fillRect(col("ink"), 0, H - 11, W, 11)
    drawText(s, text, W / 2, H - 9, "lavender", align: .center, shadow: nil)
}

// ---------------------------------------------------------------------- menu widget
final class MenuItem {
    enum Kind { case action(() -> Void), choice([(String, String)], () -> String, (String) -> Void),
                     slider(() -> Int, (Int) -> Void), toggle(() -> Bool, (Bool) -> Void) }
    let label: String
    let kind: Kind
    init(_ label: String, _ kind: Kind) { self.label = label; self.kind = kind }
}

final class Menu {
    var items: [MenuItem]
    let x, y, w, spacing: Int
    let center: Bool
    var i = 0

    init(_ items: [MenuItem], x: Int, y: Int, width: Int = 150, spacing: Int = 13, center: Bool = false) {
        self.items = items; self.x = x; self.y = y; w = width; self.spacing = spacing; self.center = center
    }

    func update(_ app: Engine, _ dt: Double) {
        let inp = app.input, au = app.audio
        if inp.repeating(.up, dt: dt) { i = (i - 1 + items.count) % items.count; au.play("move") }
        if inp.repeating(.down, dt: dt) { i = (i + 1) % items.count; au.play("move") }
        let it = items[i]
        let d = (inp.repeating(.right, dt: dt) ? 1 : 0) - (inp.repeating(.left, dt: dt) ? 1 : 0)
        switch it.kind {
        case .action(let on):
            if inp.hit(.a, .start) { au.play("select"); on() }
        case .choice(let choices, let get, let set):
            if d != 0 {
                let vals = choices.map { $0.0 }
                let idx = vals.firstIndex(of: get()) ?? 0
                set(vals[(idx + d + vals.count) % vals.count]); au.play("move")
            }
        case .slider(let get, let set):
            if d != 0 { let nv = max(0, min(10, get() + d)); if nv != get() { set(nv); au.play("move") } }
        case .toggle(let get, let set):
            if d != 0 || inp.hit(.a, .start) { set(!get()); au.play("move") }
        }
    }

    func valueText(_ it: MenuItem) -> String {
        switch it.kind {
        case .slider(let get, _): return String(repeating: "#", count: get()) + String(repeating: ".", count: 10 - get())
        case .toggle(let get, _): return get() ? "ON" : "OFF"
        case .choice(let choices, let get, _): return choices.first { $0.0 == get() }?.1 ?? ""
        case .action: return ""
        }
    }

    func draw(_ s: Surface, _ t: Double) {
        for (n, it) in items.enumerated() {
            let yy = y + n * spacing
            let sel = n == i
            let c = sel ? "yellow" : "white"
            if center {
                drawText(s, it.label, x, yy, c, align: .center)
                if sel { s.blit(sprite("mochi_icon"), x - textWidth(it.label) / 2 - 13 + Int(sin(t * 8) * 2), yy) }
                continue
            }
            if sel { s.blit(sprite("mochi_icon"), x - 12 + Int(sin(t * 8) * 2), yy) }
            drawText(s, it.label, x, yy, c)
            let vt = valueText(it)
            if !vt.isEmpty {
                var arrows = false
                if case .choice = it.kind { arrows = sel }
                if case .slider = it.kind { arrows = sel }
                drawText(s, arrows ? "{ \(vt) }" : vt, x + w, yy, sel ? "mint" : "lavender", align: .right)
            }
        }
    }
}

// ---------------------------------------------------------------------- title
final class Title: Scene {
    override var music: String? { "title" }
    override var buttons: [Action: String] { [.a: "START"] }
    let stars = Stars(60)
    let parts = Particles()

    override func update(_ dt: Double) {
        stars.update(dt, 6)
        parts.update(dt)
        if Int(t * 10) % 3 == 0 {
            parts.sparkle(40 + (t * 97).truncatingRemainder(dividingBy: 240), 30 + (t * 53).truncatingRemainder(dividingBy: 40), RAINBOW[Int(t * 7) % 7])
        }
        if app.input.hit(.a, .start) {
            app.audio.play("select")
            app.replace(app.store.profiles.isEmpty ? ProfileCreate(app, first: true) : ProfileSelect(app))
        }
    }

    override func draw(_ s: Surface) {
        s.fill(col("night"))
        stars.draw(s, t)
        s.fillRect(col("deep"), 0, 150, W, 50)
        var x = 0
        while x < W { s.fillRect(col("ink"), x + Int(t * 20) % 16, 150, 8, 2); x += 16 }
        drawWavy(s, "MOCHI", W / 2, 34, t, colorAt: { ["pink", "peach", "yellow", "mint", "sky"][$0 % 5] }, scale: 4, amp: 3)
        drawWavy(s, "ARCADE", W / 2, 70, t + 1, colorAt: { _ in "white" }, scale: 3, amp: 2)
        let x0 = (t * 30).truncatingRemainder(dividingBy: Double(W + 120)) - 60
        let bob = abs(sin(t * 6)) * 6
        s.blit(sprite("momo_walk", Int(t * 8)), Int(x0), 134 - Int(bob))
        Cute.grump(s, Int(x0) - 40, 134, t)
        s.blit(sprite("kitty"), Int(x0) + 30, 128 + Int(sin(t * 3) * 3))
        for (i, c) in ["mint", "pink", "sky", "yellow"].enumerated() {
            Cute.jellyCell(s, Int(x0) - 90 + i * 10, 140, 9, c, t, wobble: sin(t * 8 + Double(i)))
        }
        parts.draw(s)
        if Int(t * 2) % 2 == 0 { drawText(s, "TAP START", W / 2, 108, "yellow", align: .center) }
        drawText(s, "V\(appVersion)", W - 4, 4, "darkgray", align: .right, shadow: nil)
        footer(s, "A: START")
    }
}

let appVersion = (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) ?? "1.0"

// ---------------------------------------------------------------------- profiles
final class ProfileSelect: Scene {
    override var music: String? { "title" }
    override var buttons: [Action: String] { [.a: "OK", .y: "DEL"] }
    var i = 0
    var confirmDelete = false

    override func enter() {
        super.enter()
        if let l = app.store.last(), let idx = app.store.profiles.firstIndex(where: { $0 === l }) { i = idx }
        confirmDelete = false
    }

    override func update(_ dt: Double) {
        let inp = app.input, au = app.audio, store = app.store
        let n = store.profiles.count + 1
        if confirmDelete {
            if inp.hit(.a, .start) { store.delete(store.profiles[i].name); au.play("back"); confirmDelete = false; i = 0 }
            else if inp.hit(.b, .back) { confirmDelete = false }
            return
        }
        if inp.repeating(.up, dt: dt) || inp.repeating(.left, dt: dt) { i = (i - 1 + n) % n; au.play("move") }
        if inp.repeating(.down, dt: dt) || inp.repeating(.right, dt: dt) { i = (i + 1) % n; au.play("move") }
        if inp.hit(.a, .start) {
            au.play("select")
            if i == store.profiles.count { app.replace(ProfileCreate(app)) } else {
                let p = store.profiles[i]
                store.select(p); app.profile = p; app.applySettings()
                app.replace(MainMenu(app))
            }
        } else if inp.hit(.y) && i < store.profiles.count {
            confirmDelete = true
        } else if inp.hit(.back, .b) {
            au.play("back"); app.replace(Title(app))
        }
    }

    override func draw(_ s: Surface) {
        checkerBg(s, t)
        drawText(s, "WHO'S PLAYING?", W / 2, 14, "yellow", scale: 2, align: .center, outline: "ink")
        let store = app.store
        let items: [Profile?] = store.profiles.map { $0 } + [nil]
        for (n, p) in items.enumerated() {
            let x = 22 + (n % 3) * 96, y = 44 + (n / 3) * 52
            let sel = n == i
            panel(s, IRect(x, y, 84, 44), fill: sel ? "deep" : "ink", border: sel ? "yellow" : "lavender")
            guard let p = p else { drawText(s, "+ NEW", x + 42, y + 18, "mint", align: .center); continue }
            mochiAvatar(s, x + 34, y + 4, p.avatar, sel ? t : 0)
            drawText(s, p.name, x + 42, y + 24, "white", align: .center)
            let best = p.games.values.reduce(0) { $0 + $1.best }
            drawText(s, "\(best)", x + 42, y + 33, "lavender", align: .center, shadow: nil)
        }
        if confirmDelete {
            panel(s, IRect(60, 80, 200, 40), fill: "night", border: "red")
            drawText(s, "DELETE \(store.profiles[i].name)?", W / 2, 88, "red", align: .center)
            drawText(s, "A: YES   B: NO", W / 2, 104, "white", align: .center)
        }
        footer(s, "{} CHOOSE  A: OK  Y: DELETE  MENU: BACK")
    }
}

final class ProfileCreate: Scene {
    override var music: String? { "title" }
    override var buttons: [Action: String] { [.a: "ADD", .b: "DEL", .x: "DONE"] }
    static let keys = ["ABCDEFGHIJ", "KLMNOPQRST", "UVWXYZ0123", "456789-!*<"].map { Array($0) }
    let first: Bool
    var name = ""
    var avatar = 0
    var r = 0, c = 0
    var msg = ""

    init(_ app: Engine, first: Bool = false) { self.first = first; super.init(app) }

    func typeChar(_ ch: Character) { if name.count < MAX_NAME { name.append(ch); app.audio.play("type") } }

    func finish() {
        if name.trimmingCharacters(in: .whitespaces).isEmpty { msg = "TYPE A NAME FIRST"; app.audio.play("hurt"); return }
        guard let p = app.store.create(name, avatar: AVATARS[avatar]) else { msg = "NAME TAKEN OR TOO MANY"; app.audio.play("hurt"); return }
        app.profile = p; app.applySettings(); app.audio.play("win")
        app.replace(MainMenu(app))
    }

    override func update(_ dt: Double) {
        let inp = app.input, au = app.audio
        for ch in inp.text.uppercased() where ch.isLetter || ch.isNumber || "-!*".contains(ch) {
            if ch.isASCII { typeChar(ch) }
        }
        if inp.deleteKey { _ = name.popLast(); return }
        if inp.enterKey || inp.hit(.x) { finish(); return }
        if inp.hit(.back) { au.play("back"); app.replace(app.store.profiles.isEmpty ? Title(app) : ProfileSelect(app)); return }
        if !inp.text.isEmpty { return }
        if inp.repeating(.up, dt: dt) && r > -1 { r -= 1; au.play("move") }
        if inp.repeating(.down, dt: dt) && r < 4 { r += 1; au.play("move") }
        let dx = (inp.repeating(.right, dt: dt) ? 1 : 0) - (inp.repeating(.left, dt: dt) ? 1 : 0)
        if dx != 0 {
            au.play("move")
            if r == -1 { avatar = (avatar + dx + AVATARS.count) % AVATARS.count } else if r >= 0 && r < 4 { c = (c + dx + 10) % 10 }
        }
        if inp.hit(.a) {
            if r == 4 { finish() } else if r >= 0 {
                let ch = ProfileCreate.keys[r][c]
                if ch == "<" { _ = name.popLast() } else { typeChar(ch) }
            } else { r = 0 }
        }
        if inp.hit(.b) { _ = name.popLast() }
    }

    override func draw(_ s: Surface) {
        checkerBg(s, t)
        drawText(s, "NEW PLAYER", W / 2, 10, "yellow", scale: 2, align: .center, outline: "ink")
        let sel = r == -1
        panel(s, IRect(110, 30, 100, 30), fill: sel ? "deep" : "ink", border: sel ? "yellow" : "lavender")
        mochiAvatar(s, 152, 36, AVATARS[avatar], t)
        if sel { drawText(s, "{", 118, 42, "yellow"); drawText(s, "}", 197, 42, "yellow") }
        panel(s, IRect(90, 66, 140, 16), fill: "black", border: "pink")
        drawText(s, name + (Int(t * 3) % 2 == 1 ? "_" : " "), W / 2, 71, "white", align: .center)
        for (rr, row) in ProfileCreate.keys.enumerated() {
            for (cc, ch) in row.enumerated() {
                let x = 70 + cc * 18, y = 90 + rr * 15
                let on = r == rr && c == cc
                if on { s.rect(col("yellow"), IRect(x - 3, y - 3, 13, 13), radius: 2) }
                drawText(s, ch == "<" ? "{" : String(ch), x, y, on ? "black" : (ch == "<" ? "red" : "white"), shadow: nil)
            }
        }
        let ok = r == 4
        panel(s, IRect(130, 152, 60, 14), fill: ok ? "pink" : "ink", border: ok ? "yellow" : "lavender")
        drawText(s, "OK!", W / 2, 156, ok ? "black" : "white", align: .center, shadow: nil)
        if !msg.isEmpty { drawText(s, msg, W / 2, 172, "red", align: .center) }
        footer(s, "PICK LETTERS  A: ADD  B: DEL  X: DONE")
    }
}

// ---------------------------------------------------------------------- main menu
final class MainMenu: Scene {
    override var music: String? { "title" }
    let stars = Stars(50, seed: 9)
    var menu: Menu!

    override func enter() {
        super.enter()
        let a = app
        menu = Menu([
            MenuItem("PLAY", .action { a.replace(GameSelect(a)) }),
            MenuItem("OPTIONS", .action { a.push(Options(a)) }),
            MenuItem("HIGH SCORES", .action { a.push(Scores(a)) }),
            MenuItem("SWITCH PLAYER", .action { a.replace(ProfileSelect(a)) }),
        ], x: W / 2, y: 96, spacing: 14, center: true)
    }

    override func update(_ dt: Double) {
        stars.update(dt, 5)
        menu.update(app, dt)
        if app.input.hit(.back, .b) { app.audio.play("back"); app.replace(ProfileSelect(app)) }
    }

    override func draw(_ s: Surface) {
        s.fill(col("night"))
        stars.draw(s, t)
        drawWavy(s, "MOCHI ARCADE", W / 2, 22, t, colorAt: { RAINBOW[$0 % 7] }, scale: 2, amp: 2)
        guard let p = app.profile else { return }
        panel(s, IRect(110, 46, 100, 36), fill: "ink", border: "pink")
        mochiAvatar(s, 120, 56, p.avatar, t)
        drawText(s, "HI,", 142, 56, "lavender", shadow: nil)
        drawText(s, p.name, 142, 66, "white")
        menu.draw(s, t)
        footer(s, "|` MOVE   A: OK   MENU: BACK")
    }
}

// ---------------------------------------------------------------------- game select / setup
/// Campaign progress under the game carousel: stage reached, a 200-stage bar with boss marks, best score.
func progressCard(_ s: Surface, _ best: Int, _ plays: Int, _ reach0: Int, _ t: Double) {
    let bx = 64, by = 160, bw = 192
    let reach = max(1, min(reach0, STAGES))
    drawText(s, "STAGE \(reach)/\(STAGES)", bx, by - 10, "yellow")
    drawText(s, "BEST \(best)", bx + bw, by - 10, "mint", align: .right)
    s.fillRect(col("black"), bx - 1, by - 1, bw + 2, 7)
    s.fillRect(col("darkgray"), bx, by, bw, 5)
    let fill = bw * reach / STAGES
    s.fillRect(col("lime"), bx, by, fill, 5)
    s.fillRect(col("white"), bx, by, fill, 1)
    for k in 1 ... STAGES / 10 {   // boss stages: gold once beaten
        let x = bx + bw * k * 10 / STAGES - 1
        s.fillRect(col(k * 10 < reach ? "yellow" : "gray"), x, by - 2, 2, 9)
    }
    if plays == 0 && Int(t * 3) % 2 == 0 {
        drawText(s, "NEW!", bx + bw / 2, by + 9, "hotpink", align: .center)
    } else if plays > 0 {
        drawText(s, "BOSSES \(max(0, (reach - 1) / 10))  PLAYS \(plays)", bx + bw / 2, by + 9, "lavender", align: .center, shadow: nil)
    }
}

final class GameSelect: Scene {
    override var music: String? { "title" }
    let vis = Games.playable        // carousel order: only games that are ready
    var k: Int
    var i: Int
    var slide: Double

    init(_ app: Engine, _ index: Int = 0) {
        k = Games.playable.firstIndex(of: index) ?? 0
        i = Games.playable[k]
        slide = Double(k)
        super.init(app)
    }

    override func update(_ dt: Double) {
        let inp = app.input, au = app.audio, n = vis.count
        if inp.repeating(.left, dt: dt) { k = (k - 1 + n) % n; au.play("move") }
        if inp.repeating(.right, dt: dt) { k = (k + 1) % n; au.play("move") }
        i = vis[k]
        slide += (Double(k) - slide) * min(1, dt * 12)
        if inp.hit(.a, .start) { au.play("select"); app.replace(GameSetup(app, i)) }
        else if inp.hit(.back, .b) { au.play("back"); app.replace(MainMenu(app)) }
    }

    override func draw(_ s: Surface) {
        let info = Games.all[i]
        checkerBg(s, t, "night", info.meta.bg, size: 20, speed: 10)
        drawText(s, "PICK A GAME", W / 2, 8, "white", scale: 2, align: .center, outline: "ink")
        drawText(s, "\(k + 1)/\(vis.count)", W - 6, 4, "lavender", align: .right, shadow: nil)
        for (pos, n) in vis.enumerated() {
            let g = Games.all[n]
            let off = Double(pos) - slide
            if abs(off) > 2.2 { continue }
            let cx = W / 2 + Int(off * 120)
            let sel = n == i
            let (w, h) = sel ? (120, 96) : (100, 80)
            let r = IRect(cx - w / 2, 82 - h / 2, w, h)
            panel(s, r, fill: "black", border: sel ? "yellow" : "darkgray")
            let prev = Surface(w - 8, h - 22)
            g.preview(prev, sel ? t : 0)
            s.blit(prev, r.x + 4, r.y + 4)
            drawText(s, g.meta.title, cx, r.bottom - 14, sel ? "yellow" : "gray", align: .center, shadow: nil)
        }
        drawText(s, info.meta.tagline, W / 2, 138, "white", align: .center)
        if let p = app.profile {
            let g = app.store.game(p, info.meta.id)
            progressCard(s, g.best, g.plays, g.reach, t)
        }
        drawText(s, "{", 8, 78, "yellow")
        drawText(s, "}", W - 14, 78, "yellow")
        footer(s, "{} CHOOSE   A: SELECT   MENU: BACK")
    }
}

final class GameSetup: Scene {
    override var music: String? { "title" }
    let index: Int
    let info: GameInfo
    var opts: [String: String]
    var menu: Menu!
    var help = false

    init(_ app: Engine, _ index: Int) {
        self.index = index
        info = Games.all[index]
        let rec = app.profile.map { app.store.game($0, Games.all[index].meta.id) } ?? GameRecord()
        let saved = rec.options
        var o: [String: String] = [:]
        var choicesFor: [String: [(String, String)]] = [:]
        for opt in info.meta.options {
            var ch = opt.choices
            if ch.first?.0 == "checkpoints" {   // start stage: every checkpoint unlocked so far (Arcade.swift)
                ch = checkpoints(rec.reach).map { ("\($0)", "\($0)") }
            }
            choicesFor[opt.key] = ch
            let v = saved[opt.key] ?? opt.def
            if ch.contains(where: { $0.0 == v }) { o[opt.key] = v }
            else if opt.choices.first?.0 == "checkpoints" { o[opt.key] = ch.last?.0 ?? "1" }
            else { o[opt.key] = opt.def }   // saved value from an older version
        }
        opts = o
        super.init(app)
        var items: [MenuItem] = info.meta.options.map { opt in
            MenuItem(opt.label, .choice(choicesFor[opt.key] ?? opt.choices, { [unowned self] in self.opts[opt.key] ?? opt.def },
                                        { [unowned self] v in self.opts[opt.key] = v }))
        }
        items.append(MenuItem("HOW TO PLAY", .action { [unowned self] in self.help.toggle() }))
        items.append(MenuItem("START!", .action { [unowned self] in self.start() }))
        menu = Menu(items, x: 70, y: 60, width: 180, spacing: 14)
        menu.i = items.count - 1
    }

    func start() {
        if let p = app.profile { app.store.setOptions(p, info.meta.id, opts) }
        app.replace(info.make(app, opts))
    }

    override func update(_ dt: Double) {
        if help { if app.input.hit(.a, .b, .start, .back) { help = false }; return }
        menu.update(app, dt)
        if app.input.hit(.back, .b) { app.audio.play("back"); app.replace(GameSelect(app, index)) }
    }

    override func draw(_ s: Surface) {
        checkerBg(s, t, "night", info.meta.bg, size: 20, speed: 6)
        drawText(s, info.meta.title, W / 2, 12, "yellow", scale: 2, align: .center, outline: "ink")
        drawText(s, info.meta.tagline, W / 2, 34, "white", align: .center)
        panel(s, IRect(52, 52, 216, 14 + 14 * menu.items.count), fill: "ink", border: "lavender")
        menu.draw(s, t)
        if help {
            panel(s, IRect(20, 24, 280, 160), fill: "night", border: "yellow")
            drawText(s, "HOW TO PLAY", W / 2, 32, "yellow", align: .center)
            for (n, line) in info.howto.enumerated() { drawText(s, line, 30, 48 + n * 11, "white", shadow: nil) }
        }
        footer(s, "|` MOVE  {} CHANGE  A: OK  MENU: BACK")
    }
}

// ---------------------------------------------------------------------- options / scores / result
final class Options: Scene {
    override var keepsMusic: Bool { true }
    var menu: Menu!

    override func enter() {
        super.enter()
        let a = app
        guard let p = a.profile else { return }
        func commit() { a.applySettings(); a.save() }
        menu = Menu([
            MenuItem("MUSIC", .slider({ p.settings.music }, { p.settings.music = $0; commit() })),
            MenuItem("SOUND FX", .slider({ p.settings.sfx }, { p.settings.sfx = $0; commit(); a.audio.play("fruit") })),
            MenuItem("SCREEN", .choice([("full", "FULL"), ("stretch", "STRETCH"), ("pixel", "PIXEL")],
                                       { p.settings.screen }, { p.settings.screen = $0; commit() })),
            MenuItem("BUTTONS", .slider({ p.settings.controls }, { p.settings.controls = max(2, $0); commit() })),
            MenuItem("SCANLINES", .toggle({ p.settings.scanlines }, { p.settings.scanlines = $0; commit() })),
            MenuItem("SCREEN SHAKE", .toggle({ p.settings.shake }, { p.settings.shake = $0; commit() })),
            MenuItem("VIBRATION", .toggle({ p.settings.haptics }, { p.settings.haptics = $0; commit() })),
            MenuItem("BACK", .action { a.pop() }),
        ], x: 70, y: 46, width: 180, spacing: 14)
    }

    override func update(_ dt: Double) {
        menu.update(app, dt)
        if app.input.hit(.back, .b) { app.audio.play("back"); app.pop() }
    }

    override func draw(_ s: Surface) {
        checkerBg(s, t)
        drawText(s, "OPTIONS", W / 2, 14, "yellow", scale: 2, align: .center, outline: "ink")
        panel(s, IRect(50, 36, 220, 132), fill: "ink", border: "lavender")
        menu.draw(s, t)
        footer(s, "|` MOVE   {} CHANGE   MENU: BACK")
    }
}

final class Scores: Scene {
    override var keepsMusic: Bool { true }
    var i = 0

    override func update(_ dt: Double) {
        let inp = app.input
        if inp.repeating(.left, dt: dt) { i = Games.step(i, -1); app.audio.play("move") }
        if inp.repeating(.right, dt: dt) { i = Games.step(i, 1); app.audio.play("move") }
        if inp.hit(.back, .a, .start, .b) { app.audio.play("back"); app.pop() }
    }

    override func draw(_ s: Surface) {
        let info = Games.all[i]
        checkerBg(s, t, "night", info.meta.bg)
        drawText(s, "HIGH SCORES", W / 2, 10, "yellow", scale: 2, align: .center, outline: "ink")
        drawText(s, "{ \(info.meta.title) }", W / 2, 34, "white", align: .center)
        panel(s, IRect(60, 48, 200, 124), fill: "ink", border: "lavender")
        let top = app.profile.map { app.store.game($0, info.meta.id).top } ?? []
        if top.isEmpty { drawText(s, "NO SCORES YET!", W / 2, 100, "lavender", align: .center) }
        for (n, e) in top.prefix(9).enumerated() {
            let y = 56 + n * 12
            let c = n < 3 ? ["yellow", "white", "peach"][n] : "lavender"
            drawText(s, "\(n + 1).", 72, y, c)
            drawText(s, "\(e.score)", 170, y, c, align: .right)
            drawText(s, String(e.detail.prefix(9)), 250, y, "gray", align: .right, shadow: nil)
        }
        footer(s, "{} GAME   MENU: BACK")
    }
}

final class Result: Scene {
    override var music: String? { nil }
    override var buttons: [Action: String] { [.a: "AGAIN", .b: "GAMES"] }
    let info: GameInfo, opts: [String: String], score: Int, cleared: Bool, detail: String
    var newBest = false
    var rank: Int?
    let parts = Particles()

    init(_ app: Engine, _ info: GameInfo, _ opts: [String: String], _ score: Int, _ cleared: Bool, _ detail: String) {
        self.info = info; self.opts = opts; self.score = score; self.cleared = cleared; self.detail = detail
        super.init(app)
        if let p = app.profile { (newBest, rank) = app.store.record(p, info.meta.id, score, detail) }
        app.audio.play(cleared || newBest ? "win" : "gameover")
    }

    static let roll = 1.2   // seconds for the score to count up

    override func update(_ dt: Double) {
        parts.update(dt)
        if t - dt < Result.roll && Result.roll <= t && score > 0 {
            app.audio.play("coin")
            if newBest {
                app.audio.play("jackpot")
                for k in 0 ..< 6 { parts.burst(Double(40 + k * 48), 90, 14, RAINBOW, 90, 1.1) }
            }
        }
        if newBest && t > Result.roll && Int(t * 20) % 2 == 0 {
            parts.burst(Double(W / 2) + (t * 131).truncatingRemainder(dividingBy: 160) - 80, 70, 3, RAINBOW, 50, 0.8)
        }
        guard t > 0.6 else { return }
        if app.input.hit(.a, .start) { app.audio.play("select"); app.replace(info.make(app, opts)) }
        else if app.input.hit(.b, .back) {
            app.audio.play("back")
            app.replace(GameSelect(app, Games.all.firstIndex { $0.meta.id == info.meta.id } ?? 0))
        }
    }

    override func draw(_ s: Surface) {
        checkerBg(s, t, "night", info.meta.bg, speed: 4)
        drawWavy(s, cleared ? "STAGE CLEAR!" : "GAME OVER", W / 2, 30, t, colorAt: { _ in self.cleared ? "yellow" : "pink" }, scale: 2, amp: 2)
        panel(s, IRect(70, 60, 180, 90), fill: "ink", border: "lavender")
        drawText(s, "SCORE", W / 2, 70, "lavender", align: .center)
        let k = min(1, t / Result.roll)
        let shown = Int(Double(score) * (1 - pow(1 - k, 3)))
        drawText(s, "\(shown)", W / 2, 82, k < 1 ? "white" : "yellow", scale: 2, align: .center, outline: "black")
        if !detail.isEmpty { drawText(s, detail, W / 2, 104, "mint", align: .center) }
        if newBest && t > Result.roll {
            for (i, ch) in "NEW BEST!".enumerated() {
                drawText(s, String(ch), W / 2 - 27 + i * 6, 118 + Int(sin(t * 8 + Double(i)) * 2), RAINBOW[(i + Int(t * 10)) % 7])
            }
        } else if newBest {
        } else if let p = app.profile { drawText(s, "BEST \(app.store.game(p, info.meta.id).best)", W / 2, 118, "lavender", align: .center) }
        if let r = rank { drawText(s, "RANK #\(r)", W / 2, 132, "peach", align: .center) }
        parts.draw(s)
        footer(s, "A: PLAY AGAIN   B: GAMES")
    }
}
