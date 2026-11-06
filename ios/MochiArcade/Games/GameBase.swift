// Game registry and the shared game scene (port of games/__init__.py and games/base.py).
import Foundation

struct GameInfo {
    let meta: GData.Game
    let howto: [String]
    let make: (Engine, [String: String]) -> Scene
    let preview: (Surface, Double) -> Void
}

let LIVES = ["easy": 5, "normal": 3, "hard": 2]
let SPEEDS = ["easy": 0.8, "normal": 1.0, "hard": 1.25]

enum Games {
    private static func meta(_ id: String) -> GData.Game { GData.games.first { $0.id == id }! }

    /// Replace the keyboard lines of the desktop "how to play" with the touch buttons.
    private static func howto(_ id: String, touch: [String], skip: Int) -> [String] {
        let lines = meta(id).howto
        return touch + Array(lines.dropFirst(skip).dropLast()) + ["MENU  PAUSE"]
    }

    static let all: [GameInfo] = [
        GameInfo(meta: meta("soap_hop"),
                 howto: howto("soap_hop", touch: ["{ }     MOVE", "JUMP    JUMP (HOLD: BOUNCE ON BUBBLES)",
                                                   "BUBBLE  BLOW A BUBBLE"], skip: 3),
                 make: { SoapHop($0, Games.all[0], $1) }, preview: SoapHop.preview),
        GameInfo(meta: meta("jelly_stack"),
                 howto: howto("jelly_stack", touch: ["{ }  MOVE           `  SOFT DROP", "ROT R / |  ROTATE RIGHT   ROT L  LEFT",
                                                      "DROP  HARD DROP       HOLD  SAVE A JELLY"], skip: 3),
                 make: { JellyStack($0, Games.all[1], $1) }, preview: JellyStack.preview),
        GameInfo(meta: meta("comet_kitty"),
                 howto: howto("comet_kitty", touch: ["PAD  FLY (8 WAYS)", "A    SHOOT STARS (HOLD) - OR TURN",
                                                      "     ON AUTO FIRE IN THE OPTIONS", "B    COMET BURST BOMB"], skip: 3),
                 make: { CometKitty($0, Games.all[2], $1) }, preview: CometKitty.preview),
        GameInfo(meta: meta("noodle_slurp"),
                 howto: howto("noodle_slurp", touch: ["D-PAD  STEER THE NOODLE", "A      DASH (WITH THE DASH UPGRADE)"], skip: 2),
                 make: { NoodleSlurp($0, Games.all[3], $1) }, preview: NoodleSlurp.preview),
        GameInfo(meta: meta("bounce_bun"),
                 howto: howto("bounce_bun", touch: ["{ }  MOVE THE BUN (HOLD = FASTER)", "A    LAUNCH (HOLD: STICKY CATCH)",
                                                     "B    SPRINKLE LASER (UPGRADE)"], skip: 3),
                 make: { BounceBun($0, Games.all[4], $1) }, preview: BounceBun.preview),
        // ---- the CAT CORNER (each game's touch help and preview live in its own file)
        GameInfo(meta: meta("whisker_maze"), howto: howto("whisker_maze", touch: WhiskerMaze.touchHelp, skip: WhiskerMaze.helpSkip),
                 make: { WhiskerMaze($0, Games.info("whisker_maze"), $1) }, preview: WhiskerMaze.preview),
        GameInfo(meta: meta("tower_tabby"), howto: howto("tower_tabby", touch: TowerTabby.touchHelp, skip: TowerTabby.helpSkip),
                 make: { TowerTabby($0, Games.info("tower_tabby"), $1) }, preview: TowerTabby.preview),
        GameInfo(meta: meta("alley_hop"), howto: howto("alley_hop", touch: AlleyHop.touchHelp, skip: AlleyHop.helpSkip),
                 make: { AlleyHop($0, Games.info("alley_hop"), $1) }, preview: AlleyHop.preview),
        GameInfo(meta: meta("yarn_weaver"), howto: howto("yarn_weaver", touch: YarnWeaver.touchHelp, skip: YarnWeaver.helpSkip),
                 make: { YarnWeaver($0, Games.info("yarn_weaver"), $1) }, preview: YarnWeaver.preview),
        GameInfo(meta: meta("cloud_pounce"), howto: howto("cloud_pounce", touch: CloudPounce.touchHelp, skip: CloudPounce.helpSkip),
                 make: { CloudPounce($0, Games.info("cloud_pounce"), $1) }, preview: CloudPounce.preview),
        GameInfo(meta: meta("kitten_pile"), howto: howto("kitten_pile", touch: KittenPile.touchHelp, skip: KittenPile.helpSkip),
                 make: { KittenPile($0, Games.info("kitten_pile"), $1) }, preview: KittenPile.preview),
        GameInfo(meta: meta("hairball_havoc"), howto: howto("hairball_havoc", touch: HairballHavoc.touchHelp, skip: HairballHavoc.helpSkip),
                 make: { HairballHavoc($0, Games.info("hairball_havoc"), $1) }, preview: HairballHavoc.preview),
        GameInfo(meta: meta("rooftop_run"), howto: howto("rooftop_run", touch: RooftopRun.touchHelp, skip: RooftopRun.helpSkip),
                 make: { RooftopRun($0, Games.info("rooftop_run"), $1) }, preview: RooftopRun.preview),
        GameInfo(meta: meta("window_watch"), howto: howto("window_watch", touch: WindowWatch.touchHelp, skip: WindowWatch.helpSkip),
                 make: { WindowWatch($0, Games.info("window_watch"), $1) }, preview: WindowWatch.preview),
        GameInfo(meta: meta("paw_pinball"), howto: howto("paw_pinball", touch: PawPinball.touchHelp, skip: PawPinball.helpSkip),
                 make: { PawPinball($0, Games.info("paw_pinball"), $1) }, preview: PawPinball.preview),
        GameInfo(meta: meta("meow_deck"), howto: howto("meow_deck", touch: MeowDeck.touchHelp, skip: MeowDeck.helpSkip),
                 make: { MeowDeck($0, Games.info("meow_deck"), $1) }, preview: MeowDeck.preview),
    ]

    static func info(_ id: String) -> GameInfo { all.first { $0.meta.id == id }! }
}

class GameScene: Scene {
    let info: GameInfo
    let opt: [String: String]
    var score = 0
    var paused = false
    var ending: Double?
    var endArgs = (false, "")
    let parts = Particles()
    let floats = FloatText()
    let best: Int
    var pauseMenu: Menu!
    private(set) var hype: Hype!            // banners, combo, FEVER, jackpot, flash, hit-stop (Arcade.swift)
    var overlay: UpgradePick?               // e.g. upgrade cards between stages

    init(_ app: Engine, _ info: GameInfo, _ opt: [String: String]) {
        self.info = info
        self.opt = opt
        best = app.profile.map { app.store.game($0, info.meta.id).best } ?? 0
        super.init(app)
        pauseMenu = Menu([
            MenuItem("RESUME", .action { [unowned self] in self.resume() }),
            MenuItem("RESTART", .action { [unowned self] in self.app.replace(self.info.make(self.app, self.opt)) }),
            MenuItem("QUIT TO MENU", .action { [unowned self] in self.quitToMenu() }),
        ], x: W / 2, y: 92, spacing: 14, center: true)
        hype = Hype(self)
    }

    /// Taps go to an open overlay (upgrade cards) first, otherwise to onTap (only when wantsTaps is true).
    override func tap(_ x: Double, _ y: Double) {
        if let o = overlay { o.tap(x, y) } else if !paused { onTap(x, y) }
    }
    func onTap(_ x: Double, _ y: Double) {}

    func optInt(_ k: String, _ d: Int) -> Int { Int(opt[k] ?? "") ?? d }
    func optStr(_ k: String, _ d: String) -> String { opt[k] ?? d }

    func resume() { paused = false; app.audio.resumeMusic() }

    func quitToMenu() {
        resume()
        app.replace(GameSelect(app, Games.all.firstIndex { $0.meta.id == info.meta.id } ?? 0))
    }

    /// Score points (doubled during FEVER). Returns the points actually scored.
    @discardableResult
    func add(_ pts0: Int, _ x: Double? = nil, _ y: Double? = nil, _ c: String = "yellow") -> Int {
        let pts = pts0 * hype.mult
        score += pts
        if let x = x, let y = y { floats.add(x, y, "\(pts)", hype.feverOn ? "lime" : c) }
        return pts
    }

    /// Remember the furthest stage reached (unlocks checkpoints 1, 11, 21 ... in the setup screen).
    func reached(_ stage: Int) {
        guard let p = app.profile else { return }
        if stage > p.games[info.meta.id, default: GameRecord()].reach {
            p.games[info.meta.id, default: GameRecord()].reach = stage
            app.save()
        }
    }

    /// Show 3 upgrade cards; onDone(id or nil) runs when the player picks one.
    func pickUpgrade(_ pool: [Upgrade], _ levels: [String: Int], title: String = "POWER UP!", _ onDone: @escaping (String?) -> Void) {
        overlay = UpgradePick(self, pool, levels, title: title, onDone)
    }

    func endGame(_ cleared: Bool = false, _ detail: String = "", delay: Double = 1.6) {
        if ending == nil { ending = delay; endArgs = (cleared, detail); app.audio.stopMusic() }
    }

    override func update(_ dt: Double) {
        let inp = app.input
        if paused {
            pauseMenu.update(app, dt)
            if inp.hit(.back) { resume() }
            return
        }
        if var e = ending {
            e -= dt
            ending = e
            _ = hype.update(dt)
            parts.update(dt); floats.update(dt)
            tickEnding(dt)
            if e <= 0 { app.replace(Result(app, info, opt, score, endArgs.0, endArgs.1)) }
            return
        }
        if inp.hit(.start, .back) {
            paused = true
            pauseMenu.i = 0
            app.audio.play("select")
            app.audio.pauseMusic()
            return
        }
        let gdt = hype.update(dt)
        if let o = overlay {
            o.update(dt)
            if o.done && overlay === o { overlay = nil }   // onDone may already have opened the next overlay
            parts.update(dt); floats.update(dt)
            return
        }
        tick(gdt)
        parts.update(gdt)
        floats.update(gdt)
    }

    func tick(_ dt: Double) {}
    func tickEnding(_ dt: Double) {}
    func render(_ s: Surface) {}

    override func draw(_ s: Surface) {
        render(s)
        hype.draw(s)
        overlay?.draw(s)
        if paused {
            s.fillRect(rgba(12, 8, 24, 170), 0, 0, W, H)
            panel(s, IRect(90, 64, 140, 76), fill: "ink", border: "yellow")
            drawText(s, "PAUSED", W / 2, 72, "yellow", align: .center)
            pauseMenu.draw(s, t)
        }
    }

    func hearts(_ s: Surface, _ x: Int, _ y: Int, _ n: Int, maxShow: Int = 6) {
        for i in 0 ..< max(0, min(n, maxShow)) { s.blit(sprite("heart"), x + i * 8, y) }
        if n > maxShow { drawText(s, "+\(n - maxShow)", x + maxShow * 8 + 2, y, "pink", shadow: nil) }
    }

    func banner(_ s: Surface, _ text: String, _ sub: String? = nil, _ c: String = "yellow") {
        panel(s, IRect(60, 80, 200, sub == nil ? 24 : 36), fill: "ink", border: c)
        drawText(s, text, W / 2, 88, c, align: .center)
        if let sub = sub { drawText(s, sub, W / 2, 101, "white", align: .center) }
    }
}
