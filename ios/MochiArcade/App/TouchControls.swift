// On-screen controls.
// Left: a floating pad — put the thumb down anywhere in the left half and slide; the pad centres itself under the
//       thumb and follows it when you slide past the rim, so it never needs to be found by eye. At rest a faint pad
//       sits in the side margin as a hint.
// Right: face buttons on an arc around the right thumb, ordered by the scene's buttonOrder (primary under the
//       resting thumb, the next ones up/left of it), sized for the screen.
// MENU sits in the top-right corner. Multi-touch; each touch keeps the role it started with.
import UIKit

final class TouchControlsView: UIView {
    private(set) var held = Set<Action>()
    private var labels: [Action: String] = [.a: "OK", .b: "BACK"]
    private var order: [Action] = [.a, .b, .x, .y]
    private var fourWay = false
    private var level: CGFloat = 0.6

    // layout
    private var canvasRect = CGRect.zero
    private var padZone = CGRect.zero
    private var padHome = CGPoint.zero
    private var padR: CGFloat = 56
    private var buttons: [Action: (CGPoint, CGFloat)] = [:]
    private var menuRect = CGRect.zero
    private var lastLayout: (CGRect, UIEdgeInsets, Bool)?

    // touch state
    private enum Role { case pad, button, menu, tap }
    private var roles: [ObjectIdentifier: Role] = [:]
    private var buttonTouches: [ObjectIdentifier: Action] = [:]
    private var padTouch: ObjectIdentifier?
    private var padOrigin = CGPoint.zero
    private var padNow = CGPoint.zero
    private var padDirs = Set<Action>()
    private var menuDown = false

    /// When set, touches that start on the game screen are reported as taps (view coordinates).
    var tapMode = false
    var onTap: ((CGPoint) -> Void)?
    var onTouch: (() -> Void)?

    override init(frame: CGRect) {
        super.init(frame: frame)
        isMultipleTouchEnabled = true
        isOpaque = false
        backgroundColor = .clear
        contentMode = .redraw
    }

    required init?(coder: NSCoder) { fatalError() }

    // ------------------------------------------------------------------ layout
    func layoutFor(canvas: CGRect, safe: UIEdgeInsets, portrait p: Bool) {
        lastLayout = (canvas, safe, p)
        let b = bounds
        canvasRect = canvas
        let short = min(b.width, b.height)
        // sizes follow the short side of the screen: thumb-sized on phones, not huge on iPads
        padR = max(44, min(86, short * 0.14))
        let rP = max(30, min(50, short * 0.085))
        let bottom = b.height - max(safe.bottom, 6) - 8
        if p {
            let top = canvas.maxY + 8
            padZone = CGRect(x: 0, y: top, width: b.width * 0.5, height: b.height - top)
            padHome = CGPoint(x: max(safe.left, 8) + padR + 16, y: min(bottom - padR - 8, top + (bottom - top) * 0.55))
            layoutButtons(corner: CGPoint(x: b.width - max(safe.right, 0), y: bottom), rP: rP, b: b)
            let mw: CGFloat = 76
            menuRect = CGRect(x: b.width / 2 - mw / 2, y: top + 4, width: mw, height: 30)
        } else {
            padZone = CGRect(x: 0, y: 0, width: b.width * 0.5, height: b.height)
            // resting hint in the left margin when there is room, else just inside the game edge
            let side = max(canvas.minX, 0)
            padHome = CGPoint(x: max(side / 2, padR * 0.7 + 10), y: bottom - padR - 6)
            layoutButtons(corner: CGPoint(x: b.width, y: bottom), rP: rP, b: b)
            let mw: CGFloat = 70
            menuRect = CGRect(x: b.width - max(safe.right, 0) - mw - 18, y: max(safe.top, 0) + 12, width: mw, height: 28)
        }
        setNeedsDisplay()
    }

    /// Place the visible buttons around the right thumb. Offsets are in units of the button radius from the
    /// bottom-right corner: the primary sits where the thumb rests, the second down-left of it (natural roll),
    /// the third straight above, the fourth up-left — every pair at least one button-gap apart.
    private func layoutButtons(corner: CGPoint, rP: CGFloat, b: CGRect) {
        let vis = order.filter { labels[$0] != nil } + [Action.a, .b, .x, .y].filter { labels[$0] != nil && !order.contains($0) }
        let slots: [[(CGFloat, CGFloat, CGFloat)]] = [   // (dx, dy, size) per visible-button count
            [],
            [(-1.9, -2.1, 1.15)],
            [(-1.7, -2.9, 1.05), (-3.9, -1.5, 0.95)],
            [(-1.7, -2.9, 1.0), (-3.9, -1.5, 0.92), (-1.6, -5.2, 0.9)],
            [(-1.7, -2.9, 1.0), (-3.9, -1.5, 0.92), (-1.6, -5.2, 0.88), (-3.95, -3.95, 0.86)],
        ]
        let use = slots[min(vis.count, 4)]
        buttons = [:]
        for (i, a) in vis.prefix(4).enumerated() {
            let (dx, dy, sf) = use[i]
            let r = rP * sf
            var c = CGPoint(x: corner.x + dx * rP, y: corner.y + dy * rP)
            c.x = min(max(c.x, r + 6), b.width - r - 6)
            c.y = min(max(c.y, r + 6), b.height - r - 4)
            buttons[a] = (c, r)
        }
    }

    func update(labels new: [Action: String], order o: [Action], fourWay f: Bool, opacity: Int) {
        let lv = CGFloat(max(2, min(10, opacity))) / 10
        guard new != labels || o != order || f != fourWay || lv != level else { return }
        let relayout = Set(new.keys) != Set(labels.keys) || o != order
        labels = new; order = o; fourWay = f; level = lv
        if relayout, let l = lastLayout { layoutFor(canvas: l.0, safe: l.1, portrait: l.2) }
        setNeedsDisplay()
    }

    // ------------------------------------------------------------------ touches
    private func button(at p: CGPoint) -> Action? {
        var best: (Action, CGFloat)?
        for (a, (c, r)) in buttons where labels[a] != nil {
            let d = hypot(p.x - c.x, p.y - c.y)
            if d < r * 1.35 && (best == nil || d < best!.1) { best = (a, d) }
        }
        return best?.0
    }

    private func role(for p: CGPoint) -> Role {
        if menuRect.insetBy(dx: -12, dy: -12).contains(p) { return .menu }
        if button(at: p) != nil { return .button }
        if tapMode { return .tap }
        return .pad   // anywhere else (left half, or empty space) steers
    }

    private func directions() -> Set<Action> {
        guard padTouch != nil else { return [] }
        let dx = padNow.x - padOrigin.x, dy = padNow.y - padOrigin.y
        if hypot(dx, dy) < padR * 0.22 { return [] }
        if fourWay { return [abs(dx) > abs(dy) ? (dx < 0 ? .left : .right) : (dy < 0 ? .up : .down)] }
        // 8-way: each cardinal owns +-60 degrees, so diagonals are the 30-degree overlaps
        let ang = atan2(dy, dx) * 180 / .pi            // 0 = right, 90 = down
        func near(_ target: CGFloat) -> Bool {
            var d = abs(ang - target).truncatingRemainder(dividingBy: 360)
            if d > 180 { d = 360 - d }
            return d <= 60
        }
        var s = Set<Action>()
        if near(0) { s.insert(.right) }
        if near(180) { s.insert(.left) }
        if near(90) { s.insert(.down) }
        if near(-90) { s.insert(.up) }
        return s
    }

    private func recompute() {
        padDirs = directions()
        var now = padDirs
        now.formUnion(buttonTouches.values)
        if menuDown { now.insert(.back) }
        held = now
        setNeedsDisplay()
    }

    override func touchesBegan(_ touches: Set<UITouch>, with e: UIEvent?) {
        onTouch?()
        for t in touches {
            let p = t.location(in: self), id = ObjectIdentifier(t)
            var r = role(for: p)
            if r == .pad && padTouch != nil { r = .tap }      // a second thumb on the left doesn't steal the pad
            roles[id] = r
            switch r {
            case .menu: menuDown = true
            case .button: buttonTouches[id] = button(at: p)
            case .tap: onTap?(p)
            case .pad: padTouch = id; padOrigin = p; padNow = p
            }
        }
        recompute()
    }

    override func touchesMoved(_ touches: Set<UITouch>, with e: UIEvent?) {
        for t in touches {
            let p = t.location(in: self), id = ObjectIdentifier(t)
            switch roles[id] {
            case .button?:
                if let a = button(at: p) { buttonTouches[id] = a }   // slide from one button to the next
            case .pad? where padTouch == id:
                padNow = p
                // drag the anchor along when the thumb goes past the rim, so reversing direction is instant
                let dx = p.x - padOrigin.x, dy = p.y - padOrigin.y, d = hypot(dx, dy)
                if d > padR { padOrigin = CGPoint(x: p.x - dx / d * padR, y: p.y - dy / d * padR) }
            default: break
            }
        }
        recompute()
    }

    override func touchesEnded(_ touches: Set<UITouch>, with e: UIEvent?) { finish(touches) }
    override func touchesCancelled(_ touches: Set<UITouch>, with e: UIEvent?) { finish(touches) }

    private func finish(_ touches: Set<UITouch>) {
        for t in touches {
            let id = ObjectIdentifier(t)
            switch roles[id] {
            case .menu?: menuDown = false
            case .button?: buttonTouches[id] = nil
            case .pad? where padTouch == id: padTouch = nil
            default: break
            }
            roles[id] = nil
        }
        recompute()
    }

    // ------------------------------------------------------------------ drawing
    private static let palette: [Action: UIColor] = [
        .a: UIColor(red: 1.0, green: 0.56, blue: 0.72, alpha: 1), .b: UIColor(red: 0.49, green: 0.78, blue: 1.0, alpha: 1),
        .x: UIColor(red: 0.43, green: 0.91, blue: 0.72, alpha: 1), .y: UIColor(red: 1.0, green: 0.85, blue: 0.30, alpha: 1),
    ]

    private func label(_ text: String, at c: CGPoint, size: CGFloat) {
        let font = UIFont(name: "Menlo-Bold", size: size) ?? .boldSystemFont(ofSize: size)
        let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: UIColor(white: 0.08, alpha: level)]
        let s = text as NSString
        let sz = s.size(withAttributes: attrs)
        s.draw(at: CGPoint(x: c.x - sz.width / 2, y: c.y - sz.height / 2), withAttributes: attrs)
    }

    private func drawPad(at c: CGPoint, active: Bool) {
        let a: CGFloat = active ? 1 : 0.5
        let base = UIBezierPath(ovalIn: CGRect(x: c.x - padR, y: c.y - padR, width: padR * 2, height: padR * 2))
        UIColor(white: 1, alpha: 0.10 * level * a).setFill(); base.fill()
        UIColor(white: 1, alpha: 0.40 * level * a).setStroke(); base.lineWidth = 2; base.stroke()
        for (d, dx, dy) in [(Action.up, CGFloat(0), CGFloat(-1)), (.down, 0, 1), (.left, -1, 0), (.right, 1, 0)] {
            let on = active && padDirs.contains(d)
            let cc = CGPoint(x: c.x + dx * padR * 0.68, y: c.y + dy * padR * 0.68)
            let s = padR * 0.16
            let tri = UIBezierPath()
            if dy != 0 {
                tri.move(to: CGPoint(x: cc.x, y: cc.y + dy * s)); tri.addLine(to: CGPoint(x: cc.x - s, y: cc.y - dy * s * 0.6))
                tri.addLine(to: CGPoint(x: cc.x + s, y: cc.y - dy * s * 0.6))
            } else {
                tri.move(to: CGPoint(x: cc.x + dx * s, y: cc.y)); tri.addLine(to: CGPoint(x: cc.x - dx * s * 0.6, y: cc.y - s))
                tri.addLine(to: CGPoint(x: cc.x - dx * s * 0.6, y: cc.y + s))
            }
            tri.close()
            (on ? UIColor(white: 1, alpha: 0.95 * level) : UIColor(white: 1, alpha: 0.5 * level * a)).setFill(); tri.fill()
        }
        if active {   // thumb knob
            let dx = padNow.x - c.x, dy = padNow.y - c.y, d = max(1, hypot(dx, dy))
            let k = min(d, padR * 0.62)
            let kc = CGPoint(x: c.x + dx / d * k, y: c.y + dy / d * k)
            let kr = padR * 0.4
            let knob = UIBezierPath(ovalIn: CGRect(x: kc.x - kr, y: kc.y - kr, width: kr * 2, height: kr * 2))
            UIColor(white: 1, alpha: 0.5 * level).setFill(); knob.fill()
            UIColor(white: 1, alpha: 0.9 * level).setStroke(); knob.lineWidth = 2; knob.stroke()
        }
    }

    override func draw(_ rect: CGRect) {
        if padTouch != nil { drawPad(at: padOrigin, active: true) } else { drawPad(at: padHome, active: false) }
        for (a, (c, r)) in buttons {
            guard let text = labels[a] else { continue }
            let on = held.contains(a)
            let p = UIBezierPath(ovalIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2))
            let color = TouchControlsView.palette[a] ?? .white
            color.withAlphaComponent((on ? 1.0 : 0.6) * level).setFill(); p.fill()
            UIColor(white: 1, alpha: 0.85 * level).setStroke(); p.lineWidth = on ? 3 : 2; p.stroke()
            label(text, at: c, size: r > 34 ? 14 : 12)
        }
        let m = UIBezierPath(roundedRect: menuRect, cornerRadius: 10)
        UIColor(white: 1, alpha: (menuDown ? 0.85 : 0.4) * level).setFill(); m.fill()
        label("MENU", at: CGPoint(x: menuRect.midX, y: menuRect.midY), size: 12)
    }
}
