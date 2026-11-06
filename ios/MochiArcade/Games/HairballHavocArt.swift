// HAIRBALL HAVOC drawing (port of mochi_arcade/games/hairball_havoc_art.py): rooms, furniture, hairballs, toy
// bullets, pick-ups and the boss designs. Sprites (Biscuit, toys, pets, items) come from GeneratedData.
import Foundation

enum HHArt {
    static let books = ["red", "sky", "yellow", "lime", "lavender", "orange"]
    // recolour tables (same as hairball_havoc_sprites.py)
    static let white: [Character: Character] = {
        var d: [Character: Character] = [:]
        for c in "iwcpPeoylmtsbvunhgdr" { d[c] = "w" }
        return d
    }()
    static let golden: [Character: Character] = ["g": "y", "w": "y", "d": "o", "y": "o", "p": "o"]
    static let elite: [Character: Character] = ["g": "v", "w": "v", "r": "u", "s": "v", "b": "u", "n": "u", "y": "P", "o": "P", "l": "v"]
    static let kittenCoats: [[Character: Character]] = [[:], ["g": "o"], ["g": "d"], ["g": "w", "w": "c"]]
    static let blockColours: [[Character: Character]] = [[:], ["y": "s"], ["y": "l"], ["y": "r"]]

    static func tint(_ name: String, _ room: Int) -> String {
        let r = HHData.rooms[room]
        return name == "A" ? r.accentA : (name == "B" ? r.accentB : name)
    }

    private static func outline(_ s: Surface, _ c: Color, _ pts: [(Double, Double)]) {
        for i in 0 ..< pts.count {
            let a = pts[i], b = pts[(i + 1) % pts.count]
            s.line(c, Int(a.0), Int(a.1), Int(b.0), Int(b.1))
        }
    }

    // ------------------------------------------------------------------ room background (built once per stage)
    static func floor(_ s: Surface, _ style: String, _ a: String, _ b: String) {
        let x0 = HH_IX0, y0 = HH_IY0, x1 = HH_IX1, y1 = HH_IY1
        s.fillRect(col(a), x0, y0, x1 - x0, y1 - y0)
        let cb = col(b)
        switch style {
        case "planks":
            for y in stride(from: y0, to: y1, by: 8) {
                s.fillRect(cb, x0, y, x1 - x0, 1)
                let off = ((y - y0) / 8 % 3) * 21
                for x in stride(from: x0 + off, to: x1, by: 64) { s.fillRect(cb, x, y, 1, 8) }
            }
        case "checker":
            for y in stride(from: y0, to: y1, by: 12) {
                for x in stride(from: x0, to: x1, by: 12) where ((x - x0) / 12 + (y - y0) / 12) % 2 == 1 {
                    s.fillRect(cb, x, y, 12, 12)
                }
            }
        case "carpet":
            for y in stride(from: y0 + 2, to: y1, by: 6) {
                for x in stride(from: x0 + 2 + ((y - y0) / 6 % 2 == 1 ? 3 : 0), to: x1, by: 6) { s.fillRect(cb, x, y, 1, 1) }
            }
        case "tiles":
            for y in stride(from: y0, to: y1, by: 12) { s.fillRect(cb, x0, y, x1 - x0, 1) }
            for x in stride(from: x0, to: x1, by: 12) { s.fillRect(cb, x, y0, 1, y1 - y0) }
        default:   // stone
            for y in stride(from: y0, to: y1, by: 8) {
                s.fillRect(cb, x0, y, x1 - x0, 1)
                for x in stride(from: x0 + ((y - y0) / 8 % 2 == 1 ? 8 : 0), to: x1, by: 16) { s.fillRect(cb, x, y, 1, 8) }
            }
        }
        s.fillRect(col("black"), x0, y0, x1 - x0, 2)     // shadow under the top wall
    }

    static func rug(_ s: Surface, _ r: [Int], _ room: Int) {
        let rm = HHData.rooms[room]
        let a = rm.accentA, b = rm.accentB
        let x = HH_IX0 + r[0] * 8, y = HH_IY0 + r[1] * 8, w = r[2] * 8, h = r[3] * 8, pat = r[4]
        s.rect(col(b), IRect(x, y, w, h), radius: 4)
        s.rect(col(a), IRect(x + 2, y + 2, w - 4, h - 4), radius: 3)
        if pat == 0 {
            for yy in stride(from: y + 5, to: y + h - 4, by: 4) { s.fillRect(col(b), x + 4, yy, w - 8, 1) }
        } else if pat == 1 {
            s.ellipse(col(b), x + 6, y + 5, w - 12, h - 10, width: 1)
            s.ellipse(col("white"), x + w / 2 - 4, y + h / 2 - 2, 8, 4)
        } else {
            for xx in stride(from: x + 4, to: x + w - 3, by: 6) {
                for yy in stride(from: y + 4, to: y + h - 3, by: 6) { s.fillRect(col(b), xx, yy, 2, 2) }
            }
        }
        for xx in stride(from: x + 1, to: x + w - 1, by: 3) {      // tassels
            s.fillRect(col("white"), xx, y - 1, 1, 1)
            s.fillRect(col("white"), xx, y + h, 1, 1)
        }
    }

    static func walls(_ s: Surface, _ room: Int, _ doors: [(Int, Int)]) {
        let r = HHData.rooms[room]
        s.fillRect(col("black"), 0, 0, W, 10)
        s.fillRect(col(r.wall), 0, 10, W, 14)
        for x in stride(from: 4, to: W, by: 10) { s.fillRect(col(r.stripe), x, 12, 2, 8) }
        s.fillRect(col("black"), 0, 10, W, 1)
        s.fillRect(col("brown"), 0, 20, W, 4)
        s.fillRect(col("peach"), 0, 20, W, 1)
        for (i, x) in [44, 120, 200, 276].enumerated() {          // pictures and windows between the doors
            if doors.contains(where: { $0.0 == 0 && abs(HH_IX0 + $0.1 * 8 + 12 - x) < 26 }) { continue }
            if i % 2 == 0 {
                s.fillRect(col("choco"), x - 9, 11, 18, 9)
                s.fillRect(col("sky"), x - 8, 12, 16, 7)
                s.fillRect(col("white"), x - 8, 15, 16, 1)
                s.fillRect(col("white"), x, 12, 1, 7)
            } else {
                s.fillRect(col("yellow"), x - 6, 12, 12, 8)
                s.fillRect(col("ink"), x - 5, 13, 10, 6)
                s.blit(sprite("heart"), x - 3, 13)
            }
        }
        for x in [0, HH_IX1] {
            s.fillRect(col("ink"), x, 10, 8, H - 10)
            s.fillRect(col("deep"), x + (x == 0 ? 7 : 0), 24, 1, HH_IY1 - 24)
        }
        s.fillRect(col("black"), 0, HH_IY1, W, H - HH_IY1)
        s.fillRect(col("deep"), 0, HH_IY1, W, 1)
    }

    static func door(_ s: Surface, _ side: Int, _ pos: Int) {
        let r = HHData.doorRect(side, pos)
        if side == 0 {
            s.fillRect(col("choco"), r.x - 2, r.y, r.w + 4, r.h)
            s.fillRect(col("black"), r.x, r.y + 2, r.w, r.h - 2)
            s.fillRect(col("brown"), r.x - 2, r.y, r.w + 4, 1)
        } else {
            s.fillRect(col("choco"), r.x, r.y - 2, r.w, r.h + 4)
            s.fillRect(col("black"), r.x + (side == 1 ? 2 : 0), r.y, r.w - 2, r.h)
        }
    }

    static func furniture(_ s: Surface, _ k: Int, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ room: Int) {
        let f = HHData.furn[k]
        let style = f.style
        let ct = col(tint(f.top, room)), cf = col(tint(f.front, room)), kk = col("black")
        let cx = x + w / 2
        if ["plant", "lamp", "barrel", "gear"].contains(style) {
            s.ellipse(kk, x + 1, y + h - 5, w - 2, 6)
            let cy = y + h / 2 - 1
            let r = min(w, h) / 2 - 1
            if style == "plant" {
                s.polygon(cf, [(Double(cx - 5), Double(cy + 1)), (Double(cx + 5), Double(cy + 1)),
                               (Double(cx + 4), Double(y + h - 2)), (Double(cx - 4), Double(y + h - 2))])
                s.fillRect(ct, cx - 6, cy, 12, 2)
                for (i, d) in [(-4, -3), (4, -3), (0, -6), (-6, 1), (6, 1), (0, -1)].enumerated() {
                    s.circle(col(i % 2 == 1 ? "teal" : "lime"), cx + d.0, cy + d.1, 3)
                }
                s.fillRect(col("white"), cx - 1, cy - 7, 1, 1)
            } else if style == "lamp" {
                s.fillRect(col("brown"), cx - 1, cy, 2, h / 2)
                s.circle(cf, cx, cy - 1, r)
                s.circle(ct, cx, cy - 2, r - 2)
                s.fillRect(col("white"), cx - 2, cy - 4, 2, 1)
            } else if style == "barrel" {
                s.circle(kk, cx, cy, r + 1)
                s.circle(ct, cx, cy, r)
                s.circle(cf, cx, cy, r - 2, width: 1)
                s.circle(cf, cx, cy, 2)
            } else {    // gear
                for i in 0 ..< 8 {
                    let a = Double(i) * 2 * .pi / 8
                    s.fillRect(cf, Int(Double(cx) + cos(a) * Double(r - 1)) - 2, Int(Double(cy) + sin(a) * Double(r - 1)) - 2, 4, 4)
                }
                s.circle(ct, cx, cy, r - 2)
                s.circle(cf, cx, cy, r - 5, width: 1)
                s.circle(kk, cx, cy, 2)
            }
            return
        }
        // a block in 3/4 view: shadow, front face, top surface, outline
        s.fillRect(kk, x + 2, y + 2, w, h)
        s.rect(cf, IRect(x, y, w, h), radius: 2)
        s.rect(ct, IRect(x, y, w, h - 4), radius: 2)
        s.rect(kk, IRect(x, y, w, h), width: 1, radius: 2)
        s.fillRect(kk, x + 1, y + h - 4, w - 2, 1)
        let ty = y + 1, th = h - 5
        switch style {
        case "cushion":
            s.fillRect(cf, x + 1, ty, w - 2, 4)
            s.fillRect(cf, x + 1, ty, 3, th)
            s.fillRect(cf, x + w - 4, ty, 3, th)
            let n = max(1, (w - 8) / 12)
            let cw = (w - 8) / n
            for i in 0 ..< n { s.rect(cf, IRect(x + 4 + i * cw, ty + 5, cw - 1, th - 6), width: 1, radius: 2) }
        case "wood":
            for yy in stride(from: ty + 3, to: ty + th - 1, by: 4) { s.fillRect(cf, x + 2, yy, w - 4, 1) }
            s.circle(col("white"), cx, ty + th / 2, 3)
            s.circle(col("sky"), cx, ty + th / 2, 1)
        case "shelf":
            if w >= h {
                for (i, xx) in stride(from: x + 2, to: x + w - 3, by: 3).enumerated() {
                    s.fillRect(col(books[i % 6]), xx, ty + 1 + i % 2, 2, th - 2 - i % 2)
                }
            } else {
                for (i, yy) in stride(from: ty + 1, to: ty + th - 2, by: 3).enumerated() {
                    s.fillRect(col(books[i % 6]), x + 2 + i % 2, yy, w - 4 - i % 2, 2)
                }
            }
        case "bed":
            s.fillRect(col("brown"), x + 1, ty, w - 2, 3)
            s.rect(col("white"), IRect(x + 4, ty + 4, w - 8, 7), radius: 3)
            s.fillRect(cf, x + 1, ty + 13, w - 2, 2)
            for xx in stride(from: x + 4, to: x + w - 3, by: 6) { s.fillRect(cf, xx, ty + 17, 2, 2) }
        case "box":
            s.fillRect(col("yellow"), cx - 1, ty, 3, th)
            s.fillRect(cf, x + 1, ty + th / 2, w - 2, 1)
        case "counter":
            for xx in stride(from: x + 6, to: x + w - 4, by: 12) { s.fillRect(col("gray"), xx, ty, 1, th) }
            s.circle(col("darkgray"), x + w - 7, ty + th / 2, 3)
            s.circle(col("darkgray"), x + w - 15, ty + th / 2, 3)
            s.fillRect(col("peach"), x + 4, ty + 3, 7, 5)
        case "fridge":
            s.fillRect(col("gray"), x + w - 5, ty + 2, 2, th - 4)
            s.fillRect(cf, x + 1, ty + th / 2 - 2, w - 2, 1)
            s.fillRect(col("red"), x + 4, ty + 3, 2, 2)
            s.fillRect(col("yellow"), x + 7, ty + 5, 2, 2)
        case "washer":
            s.circle(col("gray"), cx, ty + th / 2 + 1, 7)
            s.circle(col("sky"), cx, ty + th / 2 + 1, 5)
            s.fillRect(col("white"), cx - 2, ty + th / 2 - 2, 2, 1)
            s.fillRect(col("lime"), x + 3, ty + 1, 3, 1)
        case "tub":
            s.rect(col("sky"), IRect(x + 3, ty + 2, w - 6, th - 3), radius: 4)
            for (i, d) in [(6, 4), (14, 7), (22, 3), (30, 6)].enumerated() where x + d.0 < x + w - 4 {
                s.circle(col("white"), x + d.0, ty + d.1, i % 2 == 1 ? 2 : 1)
            }
        case "piano":
            s.fillRect(col("white"), x + 2, ty + th - 5, w - 4, 4)
            for xx in stride(from: x + 3, to: x + w - 3, by: 3) { s.fillRect(kk, xx, ty + th - 5, 1, 2) }
            s.fillRect(col("white"), cx - 5, ty + 2, 10, 5)
            s.fillRect(kk, cx - 3, ty + 4, 6, 1)
        case "crate":
            s.rect(cf, IRect(x + 1, ty, w - 2, th), width: 1)
            s.line(cf, x + 2, ty + 1, x + w - 3, ty + th - 2)
            s.line(cf, x + w - 3, ty + 1, x + 2, ty + th - 2)
        case "tv":
            s.fillRect(col("night"), x + 3, ty + 1, w - 6, th - 2)
            s.fillRect(col("sky"), x + 4, ty + 2, 4, 1)
            s.fillRect(col("lavender"), x + 4, ty + 4, 2, 1)
        case "chest":
            s.fillRect(cf, x + 1, ty + th / 2, w - 2, 1)
            s.fillRect(col("yellow"), cx - 2, ty + th / 2 - 1, 4, 3)
            s.fillRect(cf, x + 4, ty, 1, th)
            s.fillRect(cf, x + w - 5, ty, 1, th)
        case "blocks":
            for (i, c) in ["red", "sky", "yellow", "lime"].enumerated() {
                let bx = x + 1 + (i % 2) * 7, by = ty + (i / 2) * 6
                s.fillRect(col(c), bx, by, 6, 5)
                s.fillRect(kk, bx, by + 5, 6, 1)
                s.fillRect(col("white"), bx + 1, by + 1, 1, 1)
            }
        case "arcade":
            s.fillRect(col("night"), x + 3, ty + 1, w - 6, th - 6)
            for i in 0 ..< 3 { s.fillRect(col(books[i]), x + 5 + i * 5, ty + 3 + i % 2 * 3, 2, 2) }
            s.circle(col("red"), x + 6, ty + th - 2, 2)
            s.fillRect(col("yellow"), x + w - 8, ty + th - 3, 2, 2)
        case "bench":
            for yy in stride(from: ty + 3, to: ty + th - 1, by: 4) { s.fillRect(cf, x + 2, yy, w - 4, 1) }
            s.fillRect(col("gray"), x + 6, ty + 3, 8, 3)
            s.fillRect(col("brown"), x + 14, ty + 4, 7, 1)
            s.fillRect(col("darkgray"), x + w - 12, ty + 6, 6, 4)
        case "pool":
            s.fillRect(col("choco"), x + 1, ty, w - 2, th)
            s.fillRect(ct, x + 4, ty + 3, w - 8, th - 6)
            for (i, c) in ["white", "red", "yellow", "blue", "hotpink"].enumerated() {
                s.circle(col(c), x + 10 + i * 7, ty + 6 + (i % 2) * 8, 1)
            }
        default: break
        }
    }

    /// The static background of a stage: HUD band, walls, floor, rug, doors and furniture.
    static func buildRoom(_ st: HHStage) -> Surface {
        let r = HHData.rooms[st.room]
        let s = Surface(W, H, fill: col("black"))
        floor(s, r.floor, r.a, r.b)
        if let rg = st.rug { rug(s, rg, st.room) }
        walls(s, st.room, st.doors)
        for d in st.doors { door(s, d.0, d.1) }
        for f in st.furn.enumerated().sorted(by: { ($0.element.y + $0.element.h, $0.offset) < ($1.element.y + $1.element.h, $1.offset) }) {
            let p = f.element
            furniture(s, p.k, HH_IX0 + p.x * 8, HH_IY0 + p.y * 8, p.w * 8, p.h * 8, st.room)
        }
        return s
    }

    // ------------------------------------------------------------------ shots, bullets, pick-ups
    static func hairball(_ s: Surface, _ x: Int, _ y: Int, _ r: Int, _ kind: Int, _ t: Double) {
        let c1: String, c2: String
        if kind == 2 { c1 = rainbow(x / 6, t); c2 = "white" } else if kind == 1 { c1 = "pink"; c2 = "white" } else { c1 = "peach"; c2 = "cream" }
        s.circle(col("choco"), x, y, r + 1)
        s.circle(col(c1), x, y, r)
        s.fillRect(col(c2), x - 1, y - 1, 1, 1)
        if r >= 3 { s.fillRect(col("brown"), x + 1, y, 1, 1) }
    }

    static let bulletR = [2, 2, 2, 3, 2, 3, 0, 2]

    static func bullet(_ s: Surface, _ kind: Int, _ x: Int, _ y: Int, _ t: Double, _ fuse: Double = 0) {
        let k = col("black")
        switch kind {
        case 0:     // button
            s.circle(k, x, y, 3)
            s.circle(col((x + y) % 2 != 0 ? "sky" : "hotpink"), x, y, 2)
            s.fillRect(k, x - 1, y, 1, 1)
            s.fillRect(k, x + 1, y, 1, 1)
        case 1:     // music note
            s.fillRect(k, x - 2, y, 4, 3)
            s.fillRect(col("lavender"), x - 1, y + 1, 2, 1)
            s.fillRect(k, x + 1, y - 4, 1, 4)
            s.fillRect(col("hotpink"), x + 2, y - 4, 1, 2)
        case 2:     // cheese
            s.polygon(k, [(Double(x - 3), Double(y + 2)), (Double(x + 3), Double(y + 2)), (Double(x), Double(y - 3))])
            s.polygon(col("yellow"), [(Double(x - 2), Double(y + 1)), (Double(x + 2), Double(y + 1)), (Double(x), Double(y - 2))])
            s.fillRect(col("orange"), x, y, 1, 1)
        case 3:     // dust bunny
            s.circle(col("darkgray"), x, y, 3)
            s.circle(col("gray"), x, y, 2)
            s.fillRect(col("white"), x - 1, y - 1, 1, 1)
        case 4:     // confetti
            s.fillRect(k, x - 2, y - 2, 4, 4)
            s.fillRect(col(rainbow((x + y) / 3, t)), x - 1, y - 1, 2, 2)
        case 5:     // steam puff
            s.circle(col("gray"), x, y, 4)
            s.circle(col("white"), x, y, 3)
        case 6:     // toy bomb (harmless until it bursts)
            s.circle(k, x, y, 3)
            s.fillRect(col(Int(t * (fuse < 0.5 ? 14 : 5)) % 2 == 1 ? "red" : "gray"), x - 1, y - 1, 2, 2)
            s.fillRect(col("yellow"), x + 2, y - 4, 1, 1)
        default:    // spark
            s.circle(k, x, y, 3)
            s.circle(col("orange"), x, y, 2)
            s.fillRect(col("yellow"), x, y - 1, 1, 1)
        }
    }

    static let itemSprite = ["Y": "hh_yarn", "L": "hh_laser", "N": "hh_catnip", "X": "hh_box", "H": "hh_bomb", "F": "hh_fish", "G": "hh_tuna"]
    static let itemRing = ["Y": "pink", "L": "red", "N": "lime", "X": "peach", "H": "orange", "F": "sky", "G": "yellow"]

    static func item(_ s: Surface, _ kind: String, _ x: Int, _ y: Int, _ t: Double, _ life: Double) {
        if kind == "c" {
            s.fillRect(col(Int(t * 12 + Double(x)) % 2 == 1 ? "sky" : "white"), x - 1, y - 1, 2, 2)
            return
        }
        if life < 2.5 && Int(t * 10) % 2 == 1 { return }
        let bob = Int(sin(t * 5) * 1.5)
        if kind != "F" { s.circle(col(Int(t * 6) % 2 == 1 ? itemRing[kind]! : "white"), x, y + bob, 7, width: 1) }
        let sp = sprite(itemSprite[kind]!)
        s.blit(sp, x - sp.w / 2, y - sp.h / 2 + bob)
        if kind == "G" && Int(t * 8) % 2 == 1 { s.fillRect(col("white"), x + 3, y - 5 + bob, 1, 1) }
    }

    /// A zig-zag spring between two points (pop boxes, King Boing).
    static func spring(_ s: Surface, _ x0: Double, _ y0: Double, _ x1: Double, _ y1: Double, _ t: Double) {
        let dx = x1 - x0, dy = y1 - y0
        let d = max(1.0, hypot(dx, dy))
        let nx = -dy / d, ny = dx / d
        let n = max(2, Int(d / 4))
        var px = x0, py = y0
        for i in 1 ... n {
            let u = Double(i) / Double(n)
            let side: Double = i == n ? 0 : (i % 2 == 1 ? 3 : -3)
            let qx = x0 + dx * u + nx * side, qy = y0 + dy * u + ny * side
            s.line(col("gray"), Int(px), Int(py), Int(qx), Int(qy))
            px = qx; py = qy
        }
    }

    /// A jack-in-the-box head.
    static func clown(_ s: Surface, _ x: Int, _ y: Int, _ r: Int, _ t: Double, crown: Bool = false, flash: Bool = false) {
        s.circle(col("black"), x, y, r + 1)
        s.circle(col(flash ? "white" : "peach"), x, y, r)
        let e = max(1, r / 3)
        s.fillRect(col("black"), x - e - 1, y - e, 2, 2)
        s.fillRect(col("black"), x + e, y - e, 2, 2)
        s.circle(col("red"), x, y + 1, max(1, r / 4))
        s.fillRect(col("black"), x - e, y + e + 1, e * 2 + 1, 1)
        let X = Double(x), Y = Double(y), R = Double(r)
        if crown {
            s.polygon(col("yellow"), [(X - R + 1, Y - R + 2), (X - R + 2, Y - R - 4), (X - 2, Y - R), (X, Y - R - 5), (X + 2, Y - R),
                                      (X + R - 2, Y - R - 4), (X + R - 1, Y - R + 2)])
            s.fillRect(col("hotpink"), x, y - r - 2, 1, 1)
        } else {
            s.polygon(col(rainbow(1, t)), [(X - R + 1, Y - R + 2), (X, Y - R - 5), (X + R - 1, Y - R + 2)])
        }
    }

    // ------------------------------------------------------------------ bosses
    typealias Part = (x: Int, y: Int, r: Int, alive: Bool, flash: Bool)

    /// Draw boss b centred at (x, y). parts: already positioned.
    static func boss(_ s: Surface, _ b: HHBoss, _ x: Int, _ y: Int, _ t: Double, _ look: Int, _ parts: [Part], _ flash: Bool) {
        let k = b.kind
        s.ellipse(col("black"), x - Int(b.bw) / 2, y + Int(b.bh) / 2 - 3 + Int(b.z), Int(b.bw), 7)
        if k == 0 || k == 5 { mech(s, b, x, y, t, look, flash, k == 5) } else if k == 1 { fort(s, b, x, y, t, look, parts, flash) } else if k == 2 {
            king(s, b, x, y, t, look, flash)
        } else if k == 3 { socktopus(s, b, x, y, t, look, parts, flash) } else { train(s, b, x, y, t, look, parts, flash) }
    }

    static func mech(_ s: Surface, _ b: HHBoss, _ x: Int, _ y: Int, _ t: Double, _ look: Int, _ flash: Bool, _ gold: Bool) {
        let body = flash ? "white" : (gold ? "yellow" : "gray")
        let dark = gold ? "orange" : "darkgray"
        let k = col("black")
        let step = b.moving ? Int(sin(t * 8) * 2) : 0
        for sd in [-1, 1] {                                         // legs
            let lx = x + sd * 11
            let dy = sd > 0 ? step * sd : -step
            s.fillRect(k, lx - 5, y + 8 + dy, 10, 9)
            s.fillRect(col(dark), lx - 4, y + 9 + dy, 8, 7)
        }
        var tail: [(Int, Int)] = []
        for i in 0 ..< 6 { tail.append((x + 18 + Int(sin(t * 3 + Double(i) * 0.7) * 3) + i * 3, y + 6 - i * 3)) }
        for i in 0 ..< tail.count - 1 { s.line(col("pink"), tail[i].0, tail[i].1, tail[i + 1].0, tail[i + 1].1, width: 2) }
        for sd in [-1, 1] {                                         // big round ears
            s.circle(k, x + sd * 16, y - 13, 10)
            s.circle(col(body), x + sd * 16, y - 13, 9)
            s.circle(col("pink"), x + sd * 16, y - 13, 5)
        }
        s.ellipse(k, x - 21, y - 14, 42, 28)
        s.ellipse(col(body), x - 20, y - 13, 40, 26)
        s.fillRect(col(dark), x - 20, y + 4, 40, 2)                 // armour seam
        let hatch = b.atk == "summon" && b.at > 0.3
        s.fillRect(k, x - 7, y + 3, 14, 7)
        s.fillRect(col(hatch ? "black" : dark), x - 6, y + 4, 12, 5)
        s.fillRect(k, x - 13, y - 9, 26, 8)                         // visor eyes look at Biscuit
        let glow = !(["lane", "fan"].contains(b.atk ?? "") && b.at < 0.6 && Int(t * 16) % 2 == 1) ? "red" : "white"
        for sd in [-1, 1] {
            s.fillRect(col(glow), x + sd * 6 - 2 + look, y - 7, 5, 4)
            s.fillRect(col("white"), x + sd * 6 - 1 + look, y - 7, 1, 1)
        }
        s.circle(col("hotpink"), x, y - 1, 2)                       // nose
        for sd in [-1, 1] {
            for i in [-1, 1] { s.line(k, x + sd * 4, y - 1 + i, x + sd * 14, y - 2 + i * 3) }
        }
        let kw = Int(abs(cos(t * 4)) * 6) + 1                       // wind-up key turning on its back
        s.fillRect(col(gold ? "orange" : "yellow"), x - 1, y - 22, 3, 8)
        s.fillRect(col(gold ? "orange" : "yellow"), x - kw, y - 25, kw * 2 + 1, 4)
        s.fillRect(k, x - kw, y - 25, kw * 2 + 1, 1)
        let hot = ["fan", "rain"].contains(b.atk ?? "") && b.at < 0.6 && Int(t * 14) % 2 == 1
        for sd in [-1, 1] {                                         // cheese launchers on the shoulders
            let pts: [(Double, Double)] = [(Double(x + sd * 20), Double(y - 4)), (Double(x + sd * 27), Double(y - 9)), (Double(x + sd * 27), Double(y))]
            s.polygon(col(hot ? "white" : "yellow"), pts)
            outline(s, k, pts)
        }
        if gold {
            let X = Double(x), Y = Double(y)
            s.polygon(col("yellow"), [(X - 9, Y - 13), (X - 9, Y - 21), (X - 4, Y - 16), (X, Y - 23), (X + 4, Y - 16), (X + 9, Y - 21), (X + 9, Y - 13)])
            s.fillRect(col("hotpink"), x - 1, y - 18, 3, 3)
        }
    }

    static func fort(_ s: Surface, _ b: HHBoss, _ x: Int, _ y: Int, _ t: Double, _ look: Int, _ parts: [Part], _ flash: Bool) {
        let k = col("black")
        let body = flash ? "white" : "darkgray"
        for sd in [-1, 1] {                                         // side brushes
            let a = t * (["suck", "charge"].contains(b.atk ?? "") ? 14 : 5) * Double(sd)
            let bx = x + sd * 22, by = y + 10
            for i in 0 ..< 3 {
                let aa = a + Double(i) * 2 * .pi / 3
                s.line(col("yellow"), bx, by, Int(Double(bx) + cos(aa) * 7), Int(Double(by) + sin(aa) * 4))
            }
        }
        s.ellipse(k, x - 28, y - 17, 56, 36)
        s.ellipse(col("sky"), x - 27, y - 16, 54, 34)               // bumper
        s.ellipse(col(body), x - 25, y - 17, 50, 30)
        s.ellipse(col(flash ? "white" : "gray"), x - 21, y - 15, 42, 22)
        for i in 0 ..< 8 {                                          // light ring
            let a = Double(i) * 2 * .pi / 8 + t
            let on = (i + Int(t * 6)) % 4 == 0
            s.fillRect(col(on ? "red" : "black"), Int(Double(x) + cos(a) * 18) - 1, Int(Double(y - 4) + sin(a) * 9) - 1, 2, 2)
        }
        s.fillRect(k, x - 10, y - 9, 20, 9)                         // face screen
        s.fillRect(col("night"), x - 9, y - 8, 18, 7)
        for sd in [-1, 1] {
            s.fillRect(col("sky"), x + sd * 5 - 1 + look, y - 6, 3, 3)
            if b.phase > 0 { s.fillRect(col("red"), x + sd * 5 - 2, y - 8, 5, 1) }
        }
        let sucking = b.atk == "suck" && b.at > 0.8
        s.fillRect(k, x - 14, y + 7, 28, 5)                         // intake
        s.fillRect(col(sucking && Int(t * 20) % 2 == 1 ? "hotpink" : "black"), x - 13, y + 8, 26, 3)
        for p in parts {                                            // turrets
            if !p.alive {
                s.circle(col("black"), p.x, p.y, p.r)
                s.fillRect(col("darkgray"), p.x - 1, p.y - 1, 2, 2)
                continue
            }
            s.circle(k, p.x, p.y, p.r + 1)
            s.circle(col(p.flash ? "white" : "lavender"), p.x, p.y, p.r)
            s.fillRect(col("purple"), p.x - 2, p.y - 2, 4, 2)
        }
    }

    static func king(_ s: Surface, _ b: HHBoss, _ x: Int, _ y0: Int, _ t: Double, _ look: Int, _ flash: Bool) {
        let k = col("black")
        let z = Int(b.z)
        let y = y0 - z
        s.fillRect(k, x - 17, y - 13, 34, 30)
        s.fillRect(col(flash ? "white" : "purple"), x - 16, y - 12, 32, 28)
        s.fillRect(col("lavender"), x - 16, y - 12, 32, 5)          // box top
        s.fillRect(k, x - 16, y - 7, 32, 1)
        let X = Double(x), Y = Double(y)
        s.polygon(col("yellow"), [(X, Y - 3), (X + 3, Y + 3), (X + 8, Y + 3), (X + 4, Y + 7), (X + 6, Y + 12), (X, Y + 9), (X - 6, Y + 12),
                                  (X - 4, Y + 7), (X - 8, Y + 3), (X - 3, Y + 3)])
        let a = t * 6                                                // crank
        s.fillRect(col("gray"), x + 16, y + 1, 4, 2)
        s.line(col("gray"), x + 19, y + 2, Int(Double(x + 19) + cos(a) * 5), Int(Double(y + 2) + sin(a) * 5), width: 2)
        let (hx, hy) = b.head
        spring(s, X, Y - 12, hx, hy + 6 - Double(z), t)
        clown(s, Int(hx), Int(hy) - z, 9, t, crown: true, flash: flash)
    }

    static func socktopus(_ s: Surface, _ b: HHBoss, _ x: Int, _ y: Int, _ t: Double, _ look: Int, _ parts: [Part], _ flash: Bool) {
        let k = col("black")
        for p in parts {                                            // sock tentacles
            if !p.alive { s.circle(col("darkgray"), p.x, p.y, 3); continue }
            let n = 5
            for i in 0 ... n {
                let u = Double(i) / Double(n)
                let qx = Int(Double(x) + Double(p.x - x) * u), qy = Int(Double(y + 4) + Double(p.y - y - 4) * u)
                s.circle(k, qx, qy, 4)
                s.circle(col(p.flash ? "white" : (i % 2 == 1 ? "red" : "white")), qx, qy, 3)
            }
            s.circle(col(!p.flash ? "sky" : "white"), p.x, p.y, p.r)
        }
        s.ellipse(k, x - 18, y - 16, 36, 30)
        s.ellipse(col(flash ? "white" : "lavender"), x - 17, y - 15, 34, 28)
        for i in 0 ..< 3 { s.fillRect(col(!flash ? "purple" : "white"), x - 15 + i, y - 6 + i * 6, 30 - i * 2, 2) }
        for sd in [-1, 1] {                                         // button eyes
            let ex = x + sd * 7 + look
            s.circle(k, ex, y - 8, 4)
            s.circle(col(b.phase > 0 ? "hotpink" : "sky"), ex, y - 8, 3)
            s.fillRect(k, ex - 1, y - 8, 1, 1)
            s.fillRect(k, ex + 1, y - 8, 1, 1)
        }
        let open = ["fan", "ring"].contains(b.atk ?? "") && b.at > 0.3
        s.ellipse(k, x - 7, y + 1, 14, open ? 6 : 3)
        if open { s.fillRect(col("hotpink"), x - 4, y + 3, 8, 2) }
        for xx in stride(from: x - 12, to: x + 13, by: 4) { s.fillRect(k, xx, y - 15, 2, 1) }   // stitches
    }

    static func train(_ s: Surface, _ b: HHBoss, _ x: Int, _ y: Int, _ t: Double, _ look: Int, _ parts: [Part], _ flash: Bool) {
        let k = col("black")
        for i in stride(from: parts.count - 1, through: 0, by: -1) {    // carriages, last one first
            let p = parts[i]
            if !p.alive { s.fillRect(col("darkgray"), p.x - 6, p.y - 4, 12, 8); continue }
            let c = p.flash ? "white" : (i % 2 == 1 ? "blue" : "lime")
            s.fillRect(k, p.x - 9, p.y - 7, 18, 14)
            s.fillRect(col(c), p.x - 8, p.y - 6, 16, 10)
            s.fillRect(col("yellow"), p.x - 5, p.y - 9, 10, 4)
            s.fillRect(k, p.x - 5, p.y - 9, 10, 1)
            for sd in [-1, 1] {
                s.circle(k, p.x + sd * 5, p.y + 5, 3)
                s.fillRect(col("gray"), p.x + sd * 5, p.y + 5, 1, 1)
            }
        }
        let f = b.face
        s.fillRect(k, x - 13, y - 9, 26, 18)
        s.fillRect(col(flash ? "white" : "red"), x - 12, y - 8, 24, 14)
        s.fillRect(col("choco"), x - 12, y - 8, 24, 3)
        s.fillRect(col("blue"), x - f * 6 - 4, y - 14, 9, 8)       // cab
        s.fillRect(k, x - f * 6 - 4, y - 14, 9, 1)
        s.fillRect(col("sky"), x - f * 6 - 2, y - 12, 5, 3)
        s.fillRect(k, x + f * 6 - 2, y - 15, 5, 7)                  // chimney
        s.fillRect(col("darkgray"), x + f * 6 - 1, y - 14, 3, 6)
        s.circle(col("yellow"), x + f * 12, y - 1, 2)               // lamp
        for sd in [-1, 0, 1] {
            let wy = y + 7
            s.circle(k, x + sd * 8, wy, 4)
            s.circle(col("gray"), x + sd * 8, wy, 3)
            let a = t * 10
            s.fillRect(k, Int(Double(x + sd * 8) + cos(a) * 2), Int(Double(wy) + sin(a) * 2), 1, 1)
        }
        for sd in [-1, 1] { s.fillRect(k, x + f * 3 + sd * 3, y - 3, 2, 2) }    // angry little face
        s.fillRect(k, x + f * 3 - 2, y + 2, 5, 1)
    }
}
