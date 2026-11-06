// On-screen controls: D-pad on the left, A/B/X/Y on the right, MENU at the top. Multi-touch.
import UIKit

final class TouchControlsView: UIView {
    private(set) var held = Set<Action>()
    private var perTouch: [ObjectIdentifier: Set<Action>] = [:]
    private var labels: [Action: String] = [.a: "OK", .b: "BACK"]
    private var level: CGFloat = 0.6
    private var dpad = CGPoint.zero
    private var dpadR: CGFloat = 60
    private var buttons: [Action: (CGPoint, CGFloat)] = [:]
    private var menuRect = CGRect.zero
    var onTouch: (() -> Void)?

    override init(frame: CGRect) {
        super.init(frame: frame)
        isMultipleTouchEnabled = true
        isOpaque = false
        backgroundColor = .clear
        contentMode = .redraw
    }

    required init?(coder: NSCoder) { fatalError() }

    func layoutFor(canvas: CGRect, safe: UIEdgeInsets, portrait: Bool) {
        let b = bounds
        if portrait {
            // Game-Boy style: the pad lives in the space under the screen
            let top = canvas.maxY + 16, bottom = b.height - safe.bottom - 16
            let zone = max(120, bottom - top)
            let cy = top + zone / 2
            dpadR = max(54, min(130, min(zone * 0.38, b.width * 0.18)))
            dpad = CGPoint(x: safe.left + 24 + dpadR, y: cy)
            let br = max(30, min(70, dpadR * 0.52))
            let rx = b.width - safe.right - 24 - br * 2.4
            buttons = [
                .a: (CGPoint(x: rx + br * 1.2, y: cy + br * 0.2), br),
                .b: (CGPoint(x: rx - br * 1.2, y: cy + br * 0.9), br),
                .x: (CGPoint(x: rx - br * 1.2, y: cy - br * 1.5), br * 0.82),
                .y: (CGPoint(x: rx + br * 1.2, y: cy - br * 2.1), br * 0.82),
            ]
            let mw = max(80, dpadR * 1.1)
            menuRect = CGRect(x: b.width / 2 - mw / 2, y: top, width: mw, height: 32)   // centred above the pad
        } else {
            // Landscape. The pad and buttons sit in the side margins when they fit and otherwise float over
            // the edges of the game. Sizes follow the screen height, so they stay thumb-sized on iPad too.
            // The bottom corners are clear of the camera housing, so the horizontal safe area is ignored there.
            let sideL = max(canvas.minX, 0), sideR = max(b.width - canvas.maxX, 0)
            dpadR = max(46, min(84, b.height * 0.15))
            let bottom = b.height - max(safe.bottom, 8) - 10
            dpad = CGPoint(x: max(sideL / 2, dpadR + 22), y: bottom - dpadR)
            let br = max(28, min(46, b.height * 0.075))
            let rx = b.width - max(sideR / 2, br * 2.5 + 18)
            let ry = bottom - br * 1.9
            buttons = [
                .a: (CGPoint(x: rx + br * 1.1, y: ry + br * 0.75), br),
                .b: (CGPoint(x: rx - br * 1.1, y: ry + br * 1.35), br),
                .x: (CGPoint(x: rx - br * 1.1, y: ry - br * 1.15), br * 0.82),
                .y: (CGPoint(x: rx + br * 1.1, y: ry - br * 1.75), br * 0.82),
            ]
            let mw: CGFloat = 74
            let mx = b.width - max(sideR / 2, mw / 2 + 34)
            menuRect = CGRect(x: mx - mw / 2, y: max(safe.top, 0) + 14, width: mw, height: 30)
        }
        setNeedsDisplay()
    }

    func update(labels new: [Action: String], opacity: Int) {
        let lv = CGFloat(max(2, min(10, opacity))) / 10
        if new != labels || lv != level { labels = new; level = lv; setNeedsDisplay() }
    }

    // ------------------------------------------------------------------ touches
    private func actions(at p: CGPoint) -> Set<Action> {
        if menuRect.insetBy(dx: -10, dy: -10).contains(p) { return [.back] }
        let dx = p.x - dpad.x, dy = p.y - dpad.y
        if hypot(dx, dy) < dpadR * 1.45 {
            var s = Set<Action>()
            let dead = dpadR * 0.22
            if abs(dx) > dead && abs(dx) > abs(dy) * 0.45 { s.insert(dx < 0 ? .left : .right) }
            if abs(dy) > dead && abs(dy) > abs(dx) * 0.45 { s.insert(dy < 0 ? .up : .down) }
            return s
        }
        var best: (Action, CGFloat)?
        for (a, (c, r)) in buttons where labels[a] != nil {
            let d = hypot(p.x - c.x, p.y - c.y)
            if d < r * 1.3 && (best == nil || d < best!.1) { best = (a, d) }
        }
        return best.map { [$0.0] } ?? []
    }

    private func refresh(_ touches: Set<UITouch>, ended: Bool) {
        for t in touches {
            if ended { perTouch[ObjectIdentifier(t)] = nil } else { perTouch[ObjectIdentifier(t)] = actions(at: t.location(in: self)) }
        }
        let now = perTouch.values.reduce(Set<Action>()) { $0.union($1) }
        if now != held { held = now; setNeedsDisplay() }
    }

    override func touchesBegan(_ t: Set<UITouch>, with e: UIEvent?) { onTouch?(); refresh(t, ended: false) }
    override func touchesMoved(_ t: Set<UITouch>, with e: UIEvent?) { refresh(t, ended: false) }
    override func touchesEnded(_ t: Set<UITouch>, with e: UIEvent?) { refresh(t, ended: true) }
    override func touchesCancelled(_ t: Set<UITouch>, with e: UIEvent?) { refresh(t, ended: true) }

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

    override func draw(_ rect: CGRect) {
        let ink = UIColor(red: 0.17, green: 0.11, blue: 0.29, alpha: 1)
        // D-pad
        let base = UIBezierPath(ovalIn: CGRect(x: dpad.x - dpadR, y: dpad.y - dpadR, width: dpadR * 2, height: dpadR * 2))
        UIColor(white: 1, alpha: 0.14 * level).setFill(); base.fill()
        UIColor(white: 1, alpha: 0.45 * level).setStroke(); base.lineWidth = 2; base.stroke()
        let arm = dpadR * 0.36
        let dirs: [(Action, CGFloat, CGFloat)] = [(.up, 0, -1), (.down, 0, 1), (.left, -1, 0), (.right, 1, 0)]
        for (a, dx, dy) in dirs {
            let c = CGPoint(x: dpad.x + dx * dpadR * 0.58, y: dpad.y + dy * dpadR * 0.58)
            let r = CGRect(x: c.x - arm, y: c.y - arm, width: arm * 2, height: arm * 2)
            let p = UIBezierPath(roundedRect: r, cornerRadius: 6)
            (held.contains(a) ? UIColor(white: 1, alpha: 0.9 * level) : UIColor(white: 1, alpha: 0.55 * level)).setFill()
            p.fill()
            let tri = UIBezierPath()
            let s = arm * 0.5
            if dy != 0 {
                tri.move(to: CGPoint(x: c.x, y: c.y + dy * s)); tri.addLine(to: CGPoint(x: c.x - s, y: c.y - dy * s * 0.6))
                tri.addLine(to: CGPoint(x: c.x + s, y: c.y - dy * s * 0.6))
            } else {
                tri.move(to: CGPoint(x: c.x + dx * s, y: c.y)); tri.addLine(to: CGPoint(x: c.x - dx * s * 0.6, y: c.y - s))
                tri.addLine(to: CGPoint(x: c.x - dx * s * 0.6, y: c.y + s))
            }
            tri.close()
            ink.withAlphaComponent(level).setFill(); tri.fill()
        }
        // face buttons
        for (a, (c, r)) in buttons {
            guard let text = labels[a] else { continue }
            let p = UIBezierPath(ovalIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2))
            let color = TouchControlsView.palette[a] ?? .white
            color.withAlphaComponent((held.contains(a) ? 1.0 : 0.62) * level).setFill(); p.fill()
            UIColor(white: 1, alpha: 0.8 * level).setStroke(); p.lineWidth = held.contains(a) ? 3 : 2; p.stroke()
            label(text, at: CGPoint(x: c.x, y: c.y - 6), size: r > 30 ? 13 : 11)
            label(a.rawValue.uppercased(), at: CGPoint(x: c.x, y: c.y + 9), size: 9)
        }
        // menu
        let m = UIBezierPath(roundedRect: menuRect, cornerRadius: 10)
        UIColor(white: 1, alpha: (held.contains(.back) ? 0.85 : 0.45) * level).setFill(); m.fill()
        label("MENU", at: CGPoint(x: menuRect.midX, y: menuRect.midY), size: 13)
    }
}
