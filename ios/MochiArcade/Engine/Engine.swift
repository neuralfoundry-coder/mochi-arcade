// Scene stack, input, fades, screen shake and the frame loop (port of mochi_arcade/app.py).
import Foundation

enum Action: String, CaseIterable { case left, right, up, down, a, b, x, y, start, back }

final class Input {
    private(set) var held = Set<Action>()
    private(set) var pressed = Set<Action>()
    private(set) var released = Set<Action>()
    var text = ""                       // characters typed on a hardware keyboard this frame
    var deleteKey = false               // hardware backspace this frame
    var enterKey = false                // hardware return this frame
    var spaceKey = false                // hardware space bar this frame (hard drop in Jelly Stack)
    /// Touch pad deflection while the thumb is down: x, y in -1...1 (nil when no thumb / not touch). Games that
    /// want analog control (e.g. a paddle) can use it; everything else keeps using the digital directions.
    var analog: (x: Double, y: Double)? = nil
    private var rep: [Action: Double] = [:]

    func update(_ now: Set<Action>) {
        pressed = now.subtracting(held)
        released = held.subtracting(now)
        held = now
    }

    func endFrame() { text = ""; deleteKey = false; enterKey = false; spaceKey = false }

    func hit(_ a: Action...) -> Bool { a.contains { pressed.contains($0) } }
    func down(_ a: Action...) -> Bool { a.contains { held.contains($0) } }

    /// True on press, then auto-repeats while held (menus, falling blocks).
    func repeating(_ a: Action, dt: Double, delay: Double = 0.28, rate: Double = 0.075) -> Bool {
        if pressed.contains(a) { rep[a] = -delay; return true }
        if held.contains(a) {
            rep[a, default: 0] += dt
            if rep[a]! >= rate { rep[a]! -= rate; return true }
        }
        return false
    }
}

class Scene {
    unowned let app: Engine
    var t = 0.0
    var music: String? { nil }
    var keepsMusic: Bool { false }
    /// Labels for the touch buttons (A, B, X, Y); nil hides that button.
    var buttons: [Action: String] { [.a: "OK", .b: "BACK"] }
    /// Touch layout priority: the first button sits where the right thumb rests, the next ones around it on an arc.
    var buttonOrder: [Action] { [.a, .b, .x, .y] }
    /// true: the touch pad only reports one direction at a time (grid games); false: 8-way.
    var fourWay: Bool { false }
    /// true: touches on the screen (outside the buttons) are delivered to tap(x, y) in canvas pixels instead of
    /// driving the pad — for games you play by pointing (cards, aiming).
    var wantsTaps: Bool { false }
    func tap(_ x: Double, _ y: Double) {}

    init(_ app: Engine) { self.app = app }
    func enter() { if !keepsMusic { app.audio.music(music) } }
    func update(_ dt: Double) {}
    func draw(_ s: Surface) {}
}

final class Engine {
    let canvas = Surface(W, H, fill: rgba(0, 0, 0))
    let input = Input()
    let audio = Audio()
    let store = Store()
    var profile: Profile?
    private(set) var scenes: [Scene] = []
    private var fade: (out: Bool, t: Double, fn: (() -> Void)?)?
    private var shakeT = 0.0, shakeAmt = 0.0
    var frame = 0
    var onHaptic: ((Double) -> Void)?

    var scene: Scene? { scenes.last }
    var settings: Settings { profile?.settings ?? Settings() }

    func start(_ first: Scene) {
        applySettings()
        scenes = [first]
        first.enter()
    }

    func applySettings() { audio.setVolumes(music: settings.music, sfx: settings.sfx) }
    func save() { store.save() }

    // ------------------------------------------------------------------ scenes
    func push(_ s: Scene) { transition { self.scenes.append(s); s.enter() } }
    func replace(_ s: Scene) { transition { if !self.scenes.isEmpty { self.scenes.removeLast() }; self.scenes.append(s); s.enter() } }
    func pop() { transition { if !self.scenes.isEmpty { self.scenes.removeLast() }; self.scene?.enter() } }
    func resetTo(_ s: Scene) { transition { self.scenes = [s]; s.enter() } }

    private func transition(_ fn: @escaping () -> Void) {
        if scenes.isEmpty { fn() } else { fade = (true, 0, fn) }
    }

    func shake(_ amount: Double = 3, _ time: Double = 0.25) {
        if settings.shake { shakeAmt = max(shakeAmt, amount); shakeT = max(shakeT, time) }
        if settings.haptics { onHaptic?(amount) }
    }

    // ------------------------------------------------------------------ loop
    func step(_ dt0: Double, actions: Set<Action>) {
        let dt = min(dt0, 1.0 / 30)
        input.update(actions)
        if var f = fade {
            f.t += dt
            if f.out && f.t >= 0.14 { f.fn?(); fade = (false, 0, nil) } else { fade = f }
            if let g = fade, !g.out, g.t >= 0.14 { fade = nil }
        }
        if let s = scene, fade == nil || fade?.out == false {
            s.t += dt
            s.update(dt)
        }
        input.endFrame()
        draw()
        frame += 1
    }

    private func draw() {
        let c = canvas
        if let s = scene {
            if shakeT > 0 {
                // draw into a scratch surface, then copy with an offset
                let tmp = Surface(W, H)
                s.draw(tmp)
                shakeT -= 1.0 / 60
                let ox = Int(Double.random(in: -shakeAmt ... shakeAmt)), oy = Int(Double.random(in: -shakeAmt ... shakeAmt))
                if shakeT <= 0 { shakeAmt = 0 }
                c.fill(rgba(0, 0, 0))
                c.blit(tmp, ox, oy)
            } else {
                s.draw(c)
            }
        }
        if let f = fade {
            let a = f.out ? f.t / 0.14 : 1 - f.t / 0.14
            c.fillRect(col("night", Int(max(0, min(1, a)) * 255)), 0, 0, W, H)
        }
        if settings.scanlines { scanlines(c) }
    }
}
