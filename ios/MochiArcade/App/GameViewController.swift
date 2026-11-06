// Hosts the engine: 60 fps loop, pixel-perfect scaling, touch / keyboard / game-controller input.
import GameController
import SwiftUI
import UIKit

@main
struct MochiArcadeApp: App {
    var body: some SwiftUI.Scene {
        WindowGroup {
            GameView()
                .ignoresSafeArea()
                .statusBarHidden(true)
                .persistentSystemOverlays(.hidden)
                .defersSystemGestures(on: .all)
        }
    }
}

struct GameView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> GameViewController { GameViewController() }
    func updateUIViewController(_ vc: GameViewController, context: Context) {}
}

final class GameViewController: UIViewController {
    let engine = Engine()
    private let screen = CALayer()
    private let controls = TouchControlsView()
    private var link: CADisplayLink?
    private var last: CFTimeInterval = 0
    private var keys = Set<Action>()
    private var touchedRecently = true
    private let haptic = UIImpactFeedbackGenerator(style: .light)
    private var demo: Demo?
    private let forceTouch = ProcessInfo.processInfo.arguments.contains("-touch")
    private var tapPulse = false
    private let rotateHint = UILabel()
    private var hintShownFor = CGSize.zero
    private let forceLandscape = ProcessInfo.processInfo.arguments.contains("-landscape")   // screenshots / tests

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        screen.magnificationFilter = .nearest
        screen.minificationFilter = .nearest
        view.layer.addSublayer(screen)
        controls.frame = view.bounds
        controls.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        controls.onTouch = { [weak self] in
            guard let self = self else { return }
            if self.engine.scene is Title { self.tapPulse = true }   // tap anywhere to start
            guard !self.touchedRecently else { return }
            self.touchedRecently = true
            self.view.setNeedsLayout()
        }
        controls.onTap = { [weak self] p in   // upgrade cards etc.: tap straight on the game screen
            guard let self = self, let o = (self.engine.scene as? GameScene)?.overlay else { return }
            let f = self.screen.frame
            guard f.width > 0 else { return }
            o.tap(Double((p.x - f.minX) / f.width) * Double(W), Double((p.y - f.minY) / f.height) * Double(H))
        }
        view.addSubview(controls)
        rotateHint.text = "↻  Turn your iPad sideways for the big screen"
        rotateHint.font = UIFont(name: "Menlo-Bold", size: 15) ?? .boldSystemFont(ofSize: 15)
        rotateHint.textColor = .white
        rotateHint.textAlignment = .center
        rotateHint.backgroundColor = UIColor(red: 0.17, green: 0.11, blue: 0.29, alpha: 0.85)
        rotateHint.layer.cornerRadius = 12
        rotateHint.clipsToBounds = true
        rotateHint.alpha = 0
        view.addSubview(rotateHint)
        engine.onHaptic = { [weak self] amount in self?.haptic.impactOccurred(intensity: CGFloat(min(1, amount / 4))) }
        engine.start(Title(engine))
        demo = Demo.fromLaunchArguments(engine)
        for n in [Notification.Name.GCControllerDidConnect, .GCControllerDidDisconnect, .GCKeyboardDidConnect, .GCKeyboardDidDisconnect] {
            NotificationCenter.default.addObserver(self, selector: #selector(inputDevicesChanged), name: n, object: nil)
        }
        link = CADisplayLink(target: self, selector: #selector(tick(_:)))
        link?.preferredFrameRateRange = CAFrameRateRange(minimum: 60, maximum: 60, preferred: 60)
        link?.add(to: .main, forMode: .common)
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        becomeFirstResponder()
        if forceLandscape {
            setNeedsUpdateOfSupportedInterfaceOrientations()
            view.window?.windowScene?.requestGeometryUpdate(.iOS(interfaceOrientations: .landscapeRight)) { _ in }
        }
    }

    override var canBecomeFirstResponder: Bool { true }
    override var prefersStatusBarHidden: Bool { true }
    override var prefersHomeIndicatorAutoHidden: Bool { true }
    override var preferredScreenEdgesDeferringSystemGestures: UIRectEdge { .all }
    override var supportedInterfaceOrientations: UIInterfaceOrientationMask {
        if forceLandscape { return .landscape }
        // iPhone: always landscape. iPad: iPadOS 26 windows can't be forced, so portrait gets the handheld layout.
        return UIDevice.current.userInterfaceIdiom == .pad ? .all : .landscape
    }

    @objc private func inputDevicesChanged() {
        touchedRecently = !hasPhysicalInput
        view.setNeedsLayout()
    }

    private var hasPhysicalInput: Bool { !GCController.controllers().isEmpty || GCKeyboard.coalesced != nil }
    private var showTouch: Bool { forceTouch || touchedRecently || !hasPhysicalInput }

    private var appliedScreen = ""

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let b = view.bounds
        guard b.width > 0 && b.height > 0 else { return }
        let sc = view.window?.screen.scale ?? UIScreen.main.scale
        let safe = view.safeAreaInsets
        let mode = engine.settings.screen
        appliedScreen = mode
        let portrait = b.height > b.width * 0.9   // iPad in portrait or a narrow window: game on top, pad below
        func size(_ k: Int) -> CGSize { CGSize(width: CGFloat(W * k) / sc, height: CGFloat(H * k) / sc) }
        // aspect-correct size scaled by f, snapped to whole device pixels
        func fit(_ f: CGFloat) -> CGSize {
            CGSize(width: (CGFloat(W) * f * sc).rounded(.down) / sc, height: (CGFloat(H) * f * sc).rounded(.down) / sc)
        }
        func px(_ v: CGFloat) -> CGFloat { (v * sc).rounded() / sc }
        var k = max(1, Int(min(b.width * sc / CGFloat(W), b.height * sc / CGFloat(H))))
        var frame: CGRect
        if portrait {
            // the game spans the width; with touch controls the pad sits underneath
            let availW = b.width - safe.left - safe.right
            let availH = (b.height - safe.top - safe.bottom) * (showTouch ? 0.6 : 1)
            var sz: CGSize
            if mode == "pixel" {
                while k > 1 && (size(k).width > availW - 24 || size(k).height > availH) { k -= 1 }
                sz = size(k)
            } else {
                sz = fit(min(availW / CGFloat(W), availH / CGFloat(H)))
            }
            let y = showTouch ? safe.top + 8 : (b.height - sz.height) / 2
            frame = CGRect(x: px((b.width - sz.width) / 2), y: px(y), width: sz.width, height: sz.height)
        } else if mode == "stretch" {
            // fill the screen edge to edge (only the camera housing area is kept clear)
            frame = CGRect(x: safe.left, y: 0, width: b.width - safe.left - safe.right, height: b.height)
        } else if mode == "pixel" {
            if showTouch {
                // largest integer scale that leaves room for the controls beside it (inside the safe area)
                let edge = max(safe.left, safe.right)
                var fitK = k
                while fitK > 1 && (b.width - size(fitK).width) / 2 - edge < 92 { fitK -= 1 }
                if (b.width - size(fitK).width) / 2 - edge >= 92 { k = fitK }
            }
            let sz = size(k)
            frame = CGRect(x: px((b.width - sz.width) / 2), y: px((b.height - sz.height) / 2), width: sz.width, height: sz.height)
        } else {
            // full: as large as the screen allows, keeping the aspect ratio; the controls float on top
            let sz = fit(min((b.width - safe.left - safe.right) / CGFloat(W), b.height / CGFloat(H)))
            frame = CGRect(x: px((b.width - sz.width) / 2), y: px((b.height - sz.height) / 2), width: sz.width, height: sz.height)
        }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        screen.frame = frame
        CATransaction.commit()
        controls.isHidden = !showTouch
        controls.layoutFor(canvas: frame, safe: safe, portrait: portrait)
        // iPad held upright: suggest turning it (once per orientation change)
        if portrait && UIDevice.current.userInterfaceIdiom == .pad && hintShownFor != b.size {
            hintShownFor = b.size
            rotateHint.frame = CGRect(x: b.width / 2 - 220, y: frame.maxY + 14, width: 440, height: 40)
            UIView.animate(withDuration: 0.3, animations: { self.rotateHint.alpha = 1 }) { _ in
                UIView.animate(withDuration: 0.6, delay: 3.5, options: [], animations: { self.rotateHint.alpha = 0 })
            }
        } else if !portrait { rotateHint.alpha = 0 }
        if ProcessInfo.processInfo.arguments.contains("-layoutlog") { print("LAYOUT bounds=\(b) safe=\(safe) portrait=\(portrait) touch=\(showTouch) mode=\(mode) frame=\(frame)") }
    }

    @objc private func tick(_ l: CADisplayLink) {
        let dt = last == 0 ? 1.0 / 60 : l.timestamp - last
        last = l.timestamp
        var actions = keys.union(gamepadActions())
        if !controls.isHidden { actions.formUnion(controls.held) }
        if tapPulse { actions.insert(.start); tapPulse = false }
        if let d = demo { actions = d.actions(engine) }
        engine.input.analog = controls.isHidden ? nil : controls.analog
        engine.step(dt, actions: actions)
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        screen.contents = engine.canvas.cgImage()
        CATransaction.commit()
        let sc = engine.scene
        controls.update(labels: sc?.buttons ?? [:], order: sc?.buttonOrder ?? [.a, .b, .x, .y], fourWay: sc?.fourWay ?? false,
                        opacity: engine.settings.controls)
        controls.tapMode = (sc as? GameScene)?.overlay != nil
        if engine.settings.screen != appliedScreen { view.setNeedsLayout() }
    }

    // ------------------------------------------------------------------ game controllers
    private func gamepadActions() -> Set<Action> {
        var s = Set<Action>()
        for c in GCController.controllers() {
            if let g = c.extendedGamepad {
                if g.dpad.left.isPressed || g.leftThumbstick.xAxis.value < -0.5 { s.insert(.left) }
                if g.dpad.right.isPressed || g.leftThumbstick.xAxis.value > 0.5 { s.insert(.right) }
                if g.dpad.up.isPressed || g.leftThumbstick.yAxis.value > 0.5 { s.insert(.up) }
                if g.dpad.down.isPressed || g.leftThumbstick.yAxis.value < -0.5 { s.insert(.down) }
                if g.buttonA.isPressed { s.insert(.a) }
                if g.buttonB.isPressed { s.insert(.b) }
                if g.buttonX.isPressed { s.insert(.x) }
                if g.buttonY.isPressed { s.insert(.y) }
                if g.buttonMenu.isPressed { s.insert(.start) }
                if g.buttonOptions?.isPressed == true { s.insert(.back) }
            } else if let m = c.microGamepad {
                if m.dpad.left.isPressed { s.insert(.left) }
                if m.dpad.right.isPressed { s.insert(.right) }
                if m.dpad.up.isPressed { s.insert(.up) }
                if m.dpad.down.isPressed { s.insert(.down) }
                if m.buttonA.isPressed { s.insert(.a) }
                if m.buttonX.isPressed { s.insert(.b) }
            }
        }
        return s
    }

    // ------------------------------------------------------------------ hardware keyboard (same keys as the desktop)
    private static let keymap: [UIKeyboardHIDUsage: Action] = [
        .keyboardLeftArrow: .left, .keyboardA: .left, .keyboardRightArrow: .right, .keyboardD: .right,
        .keyboardUpArrow: .up, .keyboardW: .up, .keyboardDownArrow: .down, .keyboardS: .down,
        .keyboardZ: .a, .keyboardSpacebar: .a, .keyboardX: .b, .keyboardLeftControl: .b, .keyboardRightControl: .b,
        .keyboardC: .x, .keyboardLeftShift: .x, .keyboardRightShift: .x, .keyboardV: .y,
        .keyboardReturnOrEnter: .start, .keypadEnter: .start, .keyboardP: .start,
        .keyboardEscape: .back, .keyboardDeleteOrBackspace: .back,
    ]

    override func pressesBegan(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        var handled = false
        for p in presses {
            guard let k = p.key else { continue }
            if touchedRecently { touchedRecently = false; view.setNeedsLayout() }
            if let a = GameViewController.keymap[k.keyCode] { keys.insert(a); handled = true }
            switch k.keyCode {
            case .keyboardDeleteOrBackspace: engine.input.deleteKey = true
            case .keyboardReturnOrEnter, .keypadEnter: engine.input.enterKey = true
            case .keyboardSpacebar: engine.input.spaceKey = true
            default:
                let ch = k.charactersIgnoringModifiers
                if ch.count == 1, let c = ch.first, c.isASCII, c.isLetter || c.isNumber { engine.input.text += ch }
            }
        }
        if !handled { super.pressesBegan(presses, with: event) }
    }

    override func pressesEnded(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        for p in presses { if let k = p.key, let a = GameViewController.keymap[k.keyCode] { keys.remove(a) } }
        super.pressesEnded(presses, with: event)
    }

    override func pressesCancelled(_ presses: Set<UIPress>, with event: UIPressesEvent?) {
        keys.removeAll()
        super.pressesCancelled(presses, with: event)
    }
}

/// Attract / test mode: `-demo N` jumps straight into game N with random inputs (used for screenshots).
final class Demo {
    private var frame = 0
    private var held = Set<Action>()
    private let keys: [Action]

    init(_ keys: [Action]) { self.keys = keys }

    static func fromLaunchArguments(_ engine: Engine) -> Demo? {
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-demo"), i + 1 < args.count, let n = Int(args[i + 1]) else { return nil }
        if n < 0 {
            if let p = engine.store.last() ?? engine.store.create("MOMO", avatar: "pink") { engine.profile = p }
            engine.resetTo(n == -2 ? GameSelect(engine, 1) : n == -3 ? Options(engine) : MainMenu(engine))
            return Demo([])
        }
        let g = Games.all[n % Games.all.count]
        if let p = engine.store.last() ?? engine.store.create("MOMO", avatar: "pink") { engine.profile = p }
        var opts: [String: String] = [:]
        for o in g.meta.options { opts[o.key] = o.def }
        engine.resetTo(g.make(engine, opts))
        let plans: [[Action]] = [[.left, .right, .a, .b, .b], [.left, .right, .down, .up, .a], [.left, .right, .a, .a],
                                 [.left, .right, .up, .down], [.left, .right, .a]]
        return Demo(plans[n % plans.count])
    }

    func actions(_ engine: Engine) -> Set<Action> {
        frame += 1
        if frame % 6 == 0 { held = Set(keys.filter { _ in Double.random(in: 0 ..< 1) < 0.35 }) }
        return held
    }
}
