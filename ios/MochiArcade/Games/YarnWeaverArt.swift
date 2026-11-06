// YARN WEAVER art (port of games/yarn_weaver_art.py): the hidden cat pictures, rugs, furniture and hazards.
// KUMO's sprites, the item sprites and the songs come from the Python module via GeneratedData.
import Foundation

let YW_PW = 304, YW_PH = 176
let YW_K_IDLE = 0, YW_K_BLINK = 1, YW_K_WALK1 = 2, YW_K_WALK2 = 3, YW_K_HAPPY = 4, YW_K_HURT = 5, YW_K_WEAVE = 6

/// Python-style floor division (the picture code divides negative offsets).
@inline(__always) func ywDiv(_ a: Int, _ b: Int) -> Int {
    let q = a / b
    return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q
}

enum YWArt {
    static let SIT = 0, LOAF = 1, CURL = 2, PEEK = 3
    static let darkFur: Set<String> = ["darkgray", "choco", "brown", "purple", "blue", "ink", "black", "deep"]
    static let itemSprite = ["fish": "yw_fish", "nip": "yw_nip", "bell": "yw_bell", "heart": "heart", "gold": "yw_gold",
                             "rainbow": "yw_rainbow"]

    // ------------------------------------------------------------------ outlined shapes
    static func oval(_ s: Surface, _ c: String, _ x: Int, _ y: Int, _ w: Int, _ h: Int, _ o: Int = 2) {
        if o > 0 { s.ellipse(col("black"), x - o, y - o, w + 2 * o, h + 2 * o) }
        s.ellipse(col(c), x, y, w, h)
    }

    static func ocircle(_ s: Surface, _ c: String, _ x: Int, _ y: Int, _ r: Int, _ o: Int = 2) {
        if o > 0 { s.circle(col("black"), x, y, r + o) }
        s.circle(col(c), x, y, r)
    }

    static func opoly(_ s: Surface, _ c: String, _ pts: [(Int, Int)], _ o: Int = 2) {
        s.polygon(col(c), pts.map { (Double($0.0), Double($0.1)) })
        if o > 0 {
            for i in 0 ..< pts.count {
                let a = pts[i], b = pts[(i + 1) % pts.count]
                s.line(col("black"), a.0, a.1, b.0, b.1, width: o)
            }
        }
    }

    static func thick(_ s: Surface, _ c: String, _ pts: [(Int, Int)], _ w: Int = 3) {
        for i in 0 ..< pts.count - 1 { s.line(col(c), pts[i].0, pts[i].1, pts[i + 1].0, pts[i + 1].1, width: w) }
    }

    /// Wallpaper behind the cat (also used by the rugs).
    static func bgPattern(_ s: Surface, _ a: String, _ b: String, _ pat: Int, _ x0: Int = 0, _ y0: Int = 0,
                          _ w: Int = YW_PW, _ h: Int = YW_PH) {
        s.fillRect(col(a), x0, y0, w, h)
        let cb = col(b)
        switch pat {
        case 0:
            for k in stride(from: -h, to: w, by: 18) {
                for i in 0 ..< 6 { s.line(cb, x0 + k + i, y0 + h - 1, x0 + k + i + h - 1, y0) }
            }
        case 1:
            for y in stride(from: 6, to: h, by: 16) {
                for x in stride(from: 6 + ((y / 16) % 2 == 1 ? 8 : 0), to: w, by: 16) { s.circle(cb, x0 + x, y0 + y, 3) }
            }
        case 2:
            for y in stride(from: 0, to: h, by: 16) {
                for x in stride(from: 0, to: w, by: 16) where (x / 16 + y / 16) % 2 == 1 { s.fillRect(cb, x0 + x, y0 + y, 16, 16) }
            }
        case 3:
            for y in stride(from: 8, to: h, by: 20) {
                for x in stride(from: 8 + ((y / 20) % 2 == 1 ? 10 : 0), to: w, by: 20) {
                    s.circle(cb, x0 + x - 2, y0 + y, 2)
                    s.circle(cb, x0 + x + 2, y0 + y, 2)
                    s.polygon(cb, [(Double(x0 + x - 4), Double(y0 + y + 1)), (Double(x0 + x + 4), Double(y0 + y + 1)),
                                   (Double(x0 + x), Double(y0 + y + 5))])
                }
            }
        case 4:
            for y in stride(from: 8, to: h, by: 22) {
                for x in stride(from: 10 + ((y / 22) % 2 == 1 ? 11 : 0), to: w, by: 22) {
                    s.fillRect(cb, x0 + x - 3, y0 + y, 7, 1)
                    s.fillRect(cb, x0 + x, y0 + y - 3, 1, 7)
                    s.fillRect(cb, x0 + x - 1, y0 + y - 1, 3, 3)
                }
            }
        case 5:
            for y in stride(from: 10, to: h, by: 22) {
                for x in stride(from: 8 + ((y / 22) % 2 == 1 ? 14 : 0), to: w, by: 28) {
                    s.ellipse(cb, x0 + x, y0 + y - 3, 10, 6)
                    s.polygon(cb, [(Double(x0 + x + 9), Double(y0 + y)), (Double(x0 + x + 14), Double(y0 + y - 3)),
                                   (Double(x0 + x + 14), Double(y0 + y + 3))])
                }
            }
        case 6:
            for y in stride(from: 6, to: h, by: 12) {
                for x in stride(from: 0, to: w, by: 2) {
                    let yy = y + Int(sin(Double(x + y) * 0.25) * 2)
                    s.fillRect(cb, x0 + x, y0 + yy, 2, 2)
                }
            }
        default:
            for y in stride(from: 4, to: h, by: 24) { s.fillRect(cb, x0, y0 + y, w, 4) }
            for x in stride(from: 4, to: w, by: 24) { s.fillRect(cb, x0 + x, y0, 4, h) }
        }
    }

    // ------------------------------------------------------------------ the cat
    static func eye(_ s: Surface, _ x: Int, _ y: Int, _ c: String, _ mood: Int) {
        if mood == 2 { thick(s, "black", [(x - 7, y + 3), (x, y - 3), (x + 7, y + 3)]); return }
        if mood == 4 { thick(s, "black", [(x - 7, y - 1), (x, y + 3), (x + 7, y - 1)]); return }
        oval(s, c, x - 8, y - 9, 16, 18, 2)
        if mood == 3 {
            s.ellipse(col("black"), x - 6, y - 7, 12, 15)
            s.circle(col("white"), x - 2, y - 3, 3)
            s.circle(col("white"), x + 3, y + 3, 2)
            return
        }
        s.ellipse(col("black"), x - 4, y - 7, 8, 14)
        s.circle(col("white"), x - 3, y - 4, 3)
        s.fillRect(col("white"), x + 2, y + 4, 2, 2)
    }

    static func face(_ s: Surface, _ sp: YWPic, _ hx: Int, _ hy: Int, _ eyeDy: Int = 2, _ noseDy: Int = 14, _ gap: Int = 17,
                     _ moodIn: Int? = nil) {
        let mood = moodIn ?? sp.mood
        let ey = hy + eyeDy
        if mood == 1 {
            eye(s, hx - gap, ey, sp.eye, 0)
            eye(s, hx + gap, ey, sp.eye, 2)
        } else {
            eye(s, hx - gap, ey, sp.eye, mood)
            eye(s, hx + gap, ey, sp.eye, mood)
        }
        let ny = hy + noseDy
        s.ellipse(col("pink"), hx - gap - 15, ny - 1, 10, 5)
        s.ellipse(col("pink"), hx + gap + 5, ny - 1, 10, 5)
        let wc = darkFur.contains(sp.fur) ? "white" : "black"
        for k in 0 ..< 3 {
            s.line(col(wc), hx - 14, ny + 2 + k * 3, hx - 44, ny - 4 + k * 6)
            s.line(col(wc), hx + 14, ny + 2 + k * 3, hx + 44, ny - 4 + k * 6)
        }
        opoly(s, "pink", [(hx - 5, ny - 2), (hx + 5, ny - 2), (hx, ny + 3)], 1)
        thick(s, "black", [(hx, ny + 3), (hx, ny + 6)], 2)
        thick(s, "black", [(hx - 8, ny + 7), (hx - 4, ny + 9), (hx, ny + 6), (hx + 4, ny + 9), (hx + 8, ny + 7)], 2)
        if mood == 3 {
            s.ellipse(col("black"), hx - 3, ny + 8, 7, 6)
            s.ellipse(col("hotpink"), hx - 2, ny + 10, 5, 3)
        }
    }

    static func ears(_ s: Surface, _ sp: YWPic, _ hx: Int, _ top: Int, _ spread: Int = 34) {
        let ec = sp.mark == 4 ? sp.fur2 : sp.fur
        for d in [-1, 1] {
            opoly(s, ec, [(hx + d * (spread + 6), top + 20), (hx + d * spread, top - 18), (hx + d * 10, top + 6)])
            s.polygon(col("pink"), [(Double(hx + d * (spread + 1)), Double(top + 13)), (Double(hx + d * (spread - 2)), Double(top - 8)),
                                    (Double(hx + d * 16), Double(top + 6))])
        }
    }

    static func headMarks(_ s: Surface, _ sp: YWPic, _ hx: Int, _ hy: Int, _ hw: Int, _ hh: Int) {
        let f2 = sp.fur2
        switch sp.mark {
        case 1:
            for dx in [-9, 0, 9] { thick(s, f2, [(hx + dx - ywDiv(dx, 9), hy - hh + 6), (hx + dx, hy - hh + 18)], 4) }
            for d in [-1, 1] {
                for k in 0 ..< 2 { thick(s, f2, [(hx + d * (hw - 2), hy + 2 + k * 7), (hx + d * (hw - 12), hy + 4 + k * 7)], 3) }
            }
        case 2:
            s.ellipse(col("white"), hx - 17, hy + 6, 34, hh - 4)
        case 3:
            s.circle(col(f2), hx - hw + 20, hy - hh + 20, 11)
            s.circle(col("darkgray"), hx + hw - 18, hy - hh + 18, 9)
        case 4:
            s.ellipse(col(f2), hx - 19, hy - 2, 38, 30)
        case 5:
            s.circle(col(f2), hx + 20, hy - hh + 16, 5)
            s.circle(col(f2), hx - 24, hy - hh + 22, 4)
        default: break
        }
    }

    static func bodyMarks(_ s: Surface, _ sp: YWPic, _ bx: Int, _ by: Int, _ brx: Int, _ bry: Int) {
        let f2 = sp.fur2
        switch sp.mark {
        case 1:
            for k in [-1, 0, 1] {
                let y = by + k * 12
                for d in [-1, 1] { thick(s, f2, [(bx + d * (brx - 3), y), (bx + d * (brx - 15), y + 3)], 4) }
            }
        case 2:
            s.ellipse(col("white"), bx - brx / 2, by - bry + 8, brx, bry + 8)
        case 3:
            let r = min(brx, bry) * 35 / 100
            s.circle(col(f2), bx + brx * 35 / 100, by + bry * 15 / 100, r)
            s.circle(col("darkgray"), bx - brx * 40 / 100, by - bry * 25 / 100, r * 3 / 4)
        case 5:
            for (fx, fy, r) in [(-40, -30, 6), (45, 10, 5), (-10, 45, 5), (20, -40, 4)] {
                s.circle(col(f2), bx + ywDiv(brx * fx, 100), by + ywDiv(bry * fy, 100), r)
            }
        default: break
        }
    }

    static func pawCol(_ sp: YWPic) -> String { sp.mark == 2 ? "white" : (sp.mark == 4 ? sp.fur2 : sp.fur) }

    static func tail(_ s: Surface, _ sp: YWPic, _ pts0: [(Int, Int)], _ r: Int = 7) {
        let c = (sp.mark == 1 || sp.mark == 4) ? sp.fur2 : sp.fur
        var pts = [pts0[0]]
        for i in 1 ..< pts0.count {               // a smooth tube: circles every couple of pixels
            let (ax, ay) = pts0[i - 1], (bx, by) = pts0[i]
            let k = max(1, Int(Double((bx - ax) * (bx - ax) + (by - ay) * (by - ay)).squareRoot() / 2))
            for j in 1 ... k { pts.append((ax + ywDiv((bx - ax) * j, k), ay + ywDiv((by - ay) * j, k))) }
        }
        for (x, y) in pts { s.circle(col("black"), x, y, r + 2) }
        for (x, y) in pts { s.circle(col(c), x, y, r) }
        if sp.mark == 0 || sp.mark == 2 || sp.mark == 5 {
            let (x, y) = pts[pts.count - 1]
            s.circle(col(sp.fur != "white" ? "white" : "cream"), x, y, r - 1)
        }
    }

    static func accessory(_ s: Surface, _ sp: YWPic, _ hx: Int, _ hy: Int, _ hw: Int, _ hh: Int, _ neck: Int) {
        let a = sp.acc, c = sp.accc
        let top = hy - hh
        if a == 1 {
            let bx = hx + hw - 16, by = top + 8
            opoly(s, c, [(bx - 13, by - 7), (bx - 13, by + 7), (bx, by)], 2)
            opoly(s, c, [(bx + 13, by - 7), (bx + 13, by + 7), (bx, by)], 2)
            ocircle(s, c, bx, by, 4, 2)
        } else if a == 2 && neck != 0 {
            thick(s, c, [(hx - 26, neck), (hx + 26, neck)], 6)
            ocircle(s, "yellow", hx, neck + 6, 6, 2)
            s.fillRect(col("black"), hx - 3, neck + 7, 7, 1)
            s.fillRect(col("white"), hx - 3, neck + 3, 2, 2)
        } else if a == 3 {
            let fx = hx - hw + 18, fy = top + 10
            for k in 0 ..< 5 {
                let ang = Double(k) * 2 * .pi / 5
                ocircle(s, c, fx + Int(cos(ang) * 6), fy + Int(sin(ang) * 6), 4, 1)
            }
            ocircle(s, "yellow", fx, fy, 4, 1)
        } else if a == 4 {
            opoly(s, c, [(hx - 15, top + 6), (hx + 15, top + 6), (hx + 4, top - 30)], 2)
            for k in 1 ..< 3 {
                let y = top + 6 - k * 11, w = 15 - k * 5
                thick(s, "white", [(hx - w + k * 4 - 2, y), (hx + w + k * 2 - 2, y)], 2)
            }
            ocircle(s, "yellow", hx + 4, top - 32, 5, 2)
        } else if a == 5 && neck != 0 {
            s.rect(col("black"), IRect(hx - 32, neck - 7, 64, 14), radius: 5)
            s.rect(col(c), IRect(hx - 30, neck - 5, 60, 10), radius: 4)
            s.rect(col("black"), IRect(hx + 6, neck - 2, 16, 30), radius: 4)
            s.rect(col(c), IRect(hx + 8, neck, 12, 26), radius: 3)
            for k in 0 ..< 3 { s.fillRect(col("white"), hx + 8, neck + 6 + k * 7, 12, 2) }
        } else if a == 6 {
            opoly(s, "yellow", [(hx - 18, top + 8), (hx - 18, top - 8), (hx - 9, top), (hx, top - 13), (hx + 9, top),
                                (hx + 18, top - 8), (hx + 18, top + 8)], 2)
            for (dx, c2) in [(-9, "red"), (0, "sky"), (9, "lime")] { s.circle(col(c2), hx + dx, top + 3, 2) }
        } else if a == 7 {
            for d in [-1, 1] { s.circle(col("black"), hx + d * 17, hy + 2, 12, width: 2) }
            thick(s, "black", [(hx - 6, hy), (hx + 6, hy)], 2)
        }
    }

    static func prop(_ s: Surface, _ sp: YWPic, _ px: Int, _ py: Int) {
        let c = sp.propc
        switch sp.prop {
        case 1:
            thick(s, c, [(px + 10, py + 10), (px + 26, py + 18), (px + 40, py + 14)], 2)
            ocircle(s, c, px, py, 14, 2)
            for k in -2 ... 2 { s.line(col("white"), px - 10, py + k * 5 - 3, px + 9, py + k * 5 + 3) }
            s.line(col("black"), px - 6, py - 11, px + 8, py + 10)
        case 2:
            opoly(s, c, [(px + 12, py), (px + 22, py - 8), (px + 22, py + 8)], 2)
            oval(s, c, px - 16, py - 7, 30, 14, 2)
            s.circle(col("white"), px - 8, py - 2, 3)
            s.fillRect(col("black"), px - 8, py - 2, 2, 2)
            thick(s, "white", [(px - 2, py + 3), (px + 8, py + 3)], 1)
        case 3:
            s.circle(col("black"), px + 12, py + 2, 8, width: 4)
            s.circle(col(c), px + 12, py + 2, 7, width: 2)
            s.rect(col("black"), IRect(px - 13, py - 13, 26, 28), radius: 4)
            s.rect(col(c), IRect(px - 11, py - 11, 22, 24), radius: 3)
            s.fillRect(col("white"), px - 8, py - 8, 3, 14)
            for k in [-5, 3] {
                thick(s, "white", [(px + k, py - 16), (px + k + 3, py - 21), (px + k, py - 26), (px + k + 3, py - 31)], 2)
            }
        case 4:
            s.circle(col("black"), 34, 32, 19)
            s.circle(col("yellow"), 34, 32, 17)
            s.circle(col(sp.bg), 42, 26, 15)
            for (x, y) in [(70, 20), (90, 46), (58, 58), (YW_PW - 40, 26), (YW_PW - 70, 50)] {
                s.fillRect(col("yellow"), x - 4, y, 9, 1)
                s.fillRect(col("yellow"), x, y - 4, 1, 9)
                s.fillRect(col("white"), x - 1, y - 1, 3, 3)
            }
        case 5:
            thick(s, "lime", [(px, py - 6), (px - 2, py - 30)], 3)
            thick(s, "lime", [(px, py - 14), (px + 10, py - 22)], 3)
            for k in 0 ..< 6 {
                let ang = Double(k) * 2 * .pi / 6
                ocircle(s, c, px - 2 + Int(cos(ang) * 7), py - 32 + Int(sin(ang) * 7), 5, 1)
            }
            ocircle(s, "yellow", px - 2, py - 32, 5, 1)
            opoly(s, "orange", [(px - 14, py - 8), (px + 14, py - 8), (px + 10, py + 14), (px - 10, py + 14)], 2)
            s.fillRect(col("brown"), px - 13, py - 7, 26, 4)
        case 6:
            opoly(s, "sky", [(px - 13, py - 2), (px + 13, py - 2), (px + 9, py + 16), (px - 9, py + 16)], 2)
            for k in [-6, 0, 6] { s.line(col("blue"), px + k, py, px + ywDiv(k * 3, 4), py + 15) }
            let blobs = [(-8, -4), (8, -4), (0, -8), (-4, -12), (4, -12)]
            for (dx, dy) in blobs { s.circle(col("black"), px + dx, py + dy, 8) }
            for (dx, dy) in blobs { s.circle(col(c), px + dx, py + dy, 6) }
            ocircle(s, "red", px, py - 21, 4, 2)
            s.fillRect(col("white"), px - 2, py - 23, 2, 2)
        case 7:
            for (k, bc) in [c, "teal", "orange"].enumerated() {
                let y = py + 10 - k * 11, x = px - 18 + (k % 2) * 4
                s.rect(col("black"), IRect(x - 2, y - 2, 36, 13), radius: 2)
                s.rect(col(bc), IRect(x, y, 32, 9), radius: 2)
                s.fillRect(col("cream"), x + 3, y + 3, 26, 3)
            }
        default: break
        }
    }

    /// Paint the hidden picture described by a stage's picture spec onto s (PW x PH).
    static func drawPicture(_ s: Surface, _ sp0: YWPic, golden: Bool = false) {
        var sp = sp0
        if golden {
            sp = YWPic(name: sp0.name, bg: sp0.bg, bg2: sp0.bg2, pat: sp0.pat, pose: sp0.pose, fur: "yellow", fur2: "orange", mark: 5,
                       eye: "sky", mood: sp0.mood, acc: 6, accc: sp0.accc, prop: sp0.prop, propc: sp0.propc, cush: sp0.cush, x: sp0.x)
        }
        bgPattern(s, sp.bg, sp.bg2, sp.pat)
        let cx = YW_PW / 2 + sp.x
        let pose = sp.pose
        if sp.prop == 4 { prop(s, sp, 0, 0) }
        let sideX = sp.x >= 0 ? cx - 96 : cx + 96
        if pose != PEEK {
            oval(s, sp.cush, cx - 74, 146, 148, 28, 2)
            s.fillRect(col("white"), cx - 50, 152, 30, 2)
        }
        let fur = sp.fur, paw = pawCol(sp)
        if pose == SIT {
            let hx = cx, hy = 66, hw = 44, hh = 33
            tail(s, sp, [(cx + 38, 152), (cx + 50, 146), (cx + 58, 136), (cx + 62, 124), (cx + 62, 112), (cx + 58, 101)])
            oval(s, fur, cx - 44, 126, 26, 34)
            oval(s, fur, cx + 18, 126, 26, 34)
            oval(s, fur, cx - 34, 82, 68, 80)
            bodyMarks(s, sp, cx, 122, 34, 40)
            oval(s, paw, cx - 22, 152, 18, 12)
            oval(s, paw, cx + 4, 152, 18, 12)
            ears(s, sp, hx, hy - hh)
            oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
            headMarks(s, sp, hx, hy, hw, hh)
            face(s, sp, hx, hy)
            accessory(s, sp, hx, hy, hw, hh, hy + hh - 2)
        } else if pose == LOAF {
            let hx = cx, hy = 92, hw = 40, hh = 30
            tail(s, sp, [(cx + 62, 140), (cx + 60, 152), (cx + 50, 160), (cx + 38, 164), (cx + 26, 165)], 6)
            oval(s, fur, cx - 62, 106, 124, 58)
            bodyMarks(s, sp, cx, 135, 62, 29)
            oval(s, paw, cx - 26, 158, 18, 9)
            oval(s, paw, cx + 8, 158, 18, 9)
            ears(s, sp, hx, hy - hh, 30)
            oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
            headMarks(s, sp, hx, hy, hw, hh)
            face(s, sp, hx, hy)
            accessory(s, sp, hx, hy, hw, hh, hy + hh - 2)
        } else if pose == CURL {
            let bx = cx + 10, by = 112, br = 50
            ocircle(s, fur, bx, by, br, 2)
            if sp.mark != 2 { bodyMarks(s, sp, bx, by, br, br) }
            tail(s, sp, stride(from: -30, to: 110, by: 16).map { a in
                (bx + Int(cos(Double(a) * .pi / 180) * 46), by + Int(sin(Double(a) * .pi / 180) * 46))
            }, 7)
            let hx = cx - 22, hy = 122, hw = 36, hh = 28
            ears(s, sp, hx, hy - hh, 28)
            oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
            headMarks(s, sp, hx, hy, hw, hh)
            face(s, sp, hx, hy, 2, 13, 15, 4)
            oval(s, paw, hx + 18, hy + 18, 18, 10)
            accessory(s, sp, hx, hy, hw, hh, 0)
            for (k, z) in [(hx + 34, hy - 46), (hx + 46, hy - 60), (hx + 60, hy - 72)].enumerated() {
                let (zx, zy) = z
                thick(s, "white", [(zx, zy), (zx + 4 + k, zy), (zx, zy + 4 + k), (zx + 4 + k, zy + 4 + k)], 2)
            }
        } else {
            let hx = cx, hy = 86, hw = 42, hh = 31
            tail(s, sp, [(cx + 64, 150), (cx + 70, 138), (cx + 74, 126), (cx + 76, 114)], 6)
            ears(s, sp, hx, hy - hh)
            oval(s, fur, hx - hw, hy - hh, hw * 2, hh * 2)
            headMarks(s, sp, hx, hy, hw, hh)
            face(s, sp, hx, hy)
            accessory(s, sp, hx, hy, hw, hh, 0)
            opoly(s, "peach", [(cx - 62, 112), (cx - 84, 98), (cx - 70, 92), (cx - 46, 112)], 2)
            opoly(s, "peach", [(cx + 62, 112), (cx + 84, 98), (cx + 70, 92), (cx + 46, 112)], 2)
            s.fillRect(col("black"), cx - 64, 110, 128, 70)
            s.fillRect(col("orange"), cx - 62, 112, 124, 70)
            s.fillRect(col("brown"), cx - 62, 112, 124, 3)
            s.fillRect(col("peach"), cx - 8, 122, 16, 30)
            oval(s, paw, cx - 36, 104, 20, 12)
            oval(s, paw, cx + 16, 104, 20, 12)
        }
        if sp.prop != 0 && sp.prop != 4 { prop(s, sp, max(22, min(YW_PW - 30, sideX)), 140) }
        if golden {
            for (x, y) in [(40, 40), (YW_PW - 40, 60), (70, 140), (YW_PW - 60, 150), (YW_PW / 2 + 70, 30)] {
                s.fillRect(col("white"), x - 5, y, 11, 1)
                s.fillRect(col("white"), x, y - 5, 1, 11)
                s.fillRect(col("yellow"), x - 1, y - 1, 3, 3)
            }
        }
    }

    // ------------------------------------------------------------------ rugs and furniture
    /// The unclaimed rug: a woven pattern in the room's colours with a soft knit texture.
    static func makeRug(_ s: Surface, _ th: YWTheme) {
        bgPattern(s, th.a, th.b, th.pat)
        let dark = col("black")
        for y in stride(from: 1, to: YW_PH, by: 4) {
            for x in stride(from: (y / 4) % 2 * 2, to: YW_PW, by: 4) { s.put(x, y, dark) }
        }
    }

    static func drawFurniture(_ s: Surface, _ sh: YWShape) {
        let c = sh.c
        if !sh.round {
            let x = sh.x * 2, y = sh.y * 2, w = sh.w * 2, h = sh.h * 2
            s.rect(col("black"), IRect(x, y, w, h), radius: 5)
            s.rect(col(c), IRect(x + 2, y + 2, w - 4, h - 4), radius: 4)
            s.fillRect(col("white"), x + 5, y + 4, max(2, w / 3), 2)
            if w >= 16 && h >= 16 {
                for bx in stride(from: x + 8, to: x + w - 6, by: 12) {
                    for by in stride(from: y + 8, to: y + h - 6, by: 12) { s.fillRect(col("black"), bx, by, 2, 2) }
                }
            }
        } else {
            let x = sh.x * 2 + 1, y = sh.y * 2 + 1, r = sh.r * 2
            s.circle(col("black"), x, y, r + 1)
            s.circle(col(c), x, y, r - 1)
            s.circle(col("black"), x, y, r - 5, width: 1)
            for k in 0 ..< 8 {
                let a = Double(k) * 2 * .pi / 8
                s.fillRect(col("black"), x + Int(cos(a) * Double(r - 3)), y + Int(sin(a) * Double(r - 3)), 1, 1)
                s.line(col("black"), x, y, x + Int(cos(a) * Double(r - 6)), y + Int(sin(a) * Double(r - 6)))
            }
            s.circle(col("black"), x, y, 3)
            s.circle(col("cream"), x, y, 2)
            s.fillRect(col("white"), x - r / 2, y - r / 2 - 2, 4, 2)
        }
    }

    // ------------------------------------------------------------------ hazards and friends
    static func drawFluff(_ s: Surface, _ fx: Double, _ fy: Double, _ r: Int, _ t: Double, angry: Bool = true, zap: Double = 0,
                          color: String = "gray") {
        let x = Int(fx), y = Int(fy)
        let spin = t * 3
        let n = r >= 6 ? 10 : 7
        for k in 0 ..< n {
            let a = spin + Double(k) * 2 * .pi / Double(n)
            let rr = Double(r + 2 + k % 2)
            s.circle(col("black"), x + Int(cos(a) * rr * 0.75), y + Int(sin(a) * rr * 0.75), r / 2 + 2)
        }
        for k in 0 ..< n {
            let a = spin + Double(k) * 2 * .pi / Double(n)
            let rr = Double(r + 2 + k % 2)
            let c = zap > 0 && Int(t * 20) % 2 == 1 ? "yellow" : (k % 3 == 0 ? "white" : color)
            s.circle(col(c), x + Int(cos(a) * rr * 0.75), y + Int(sin(a) * rr * 0.75), r / 2 + 1)
        }
        s.circle(col(color == "gray" ? "lavender" : color), x, y, r)
        if r >= 5 {
            Cute.eyes(s, x, y - 1, max(2, r / 3), look: 0, mood: angry ? "angry" : "happy", blink: Int(t * 3) % 9 == 0)
        } else {
            s.fillRect(col("black"), x - 2, y - 1, 1, 2)
            s.fillRect(col("black"), x + 1, y - 1, 1, 2)
        }
        for k in 0 ..< 2 {
            let a = t * 7 + Double(k) * 3.1 + Double(x) * 0.1
            if Int(t * 12 + Double(k)) % 3 == 0 {
                let ax = x + Int(cos(a) * Double(r + 4)), ay = y + Int(sin(a) * Double(r + 4))
                s.line(col("yellow"), ax, ay, ax + Int(cos(a + 1.3) * 4), ay + Int(sin(a + 1.3) * 4))
            }
        }
    }

    static func drawZip(_ s: Surface, _ fx: Double, _ fy: Double, _ t: Double, hunter: Bool = false) {
        let x = Int(fx), y = Int(fy)
        let (c1, c2) = hunter ? ("red", "orange") : ("yellow", "white")
        let ph = Int(t * 16) % 2
        s.circle(col("black"), x, y, 4)
        for k in 0 ..< 4 {
            let a = Double(k) * .pi / 2 + (ph == 1 ? .pi / 4 : 0)
            s.line(col(c1), x, y, x + Int(cos(a) * 5), y + Int(sin(a) * 5))
        }
        s.circle(col(c1), x, y, 3)
        s.fillRect(col(c2), x - 1, y - 1, 2, 2)
        s.fillRect(col("black"), x - 2, y, 1, 1)
        s.fillRect(col("black"), x + 1, y, 1, 1)
    }

    static func drawMoth(_ s: Surface, _ x: Double, _ y: Double, _ t: Double) {
        s.blit(sprite("yw_moth", Int(t * 10) % 2), Int(x) - 3, Int(y) - 3)
    }

    static func drawNose(_ s: Surface, _ fx: Double, _ fy: Double, _ t: Double, _ up: Double) {
        let x = Int(fx), y = Int(fy)
        let r = max(2, Int(11 * up))
        s.ellipse(col("black"), x - r - 6, y - r / 2 - 3, (r + 6) * 2, r + 8)
        s.ellipse(col("brown"), x - r - 4, y - r / 2 - 1, (r + 4) * 2, r + 4)
        s.ellipse(col("black"), x - r, y - r, r * 2, r * 16 / 10)
        s.ellipse(col("choco"), x - r + 2, y - r + 2, r * 2 - 4, r * 16 / 10 - 4)
        if r > 5 {
            s.fillRect(col("white"), x - r / 2, y - r + 4, 3, 2)
            s.ellipse(col("black"), x - r / 2 - 1, y - 1, 4, 4)
            s.ellipse(col("black"), x + r / 2 - 3, y - 1, 4, 4)
        }
        if up > 0.9 && Int(t * 6) % 2 == 1 {
            for d in [-1, 1] { s.fillRect(col("white"), x + d * (r + 6), y - r, 1, 3) }
        }
    }

    static func drawPom(_ s: Surface, _ fx: Double, _ fy: Double, _ r: Int, _ t: Double, _ c: String) {
        let x = Int(fx), y = Int(fy)
        for k in 0 ..< 12 {
            let a = t * 2 + Double(k) * 2 * .pi / 12
            s.circle(col("black"), x + Int(cos(a) * Double(r - 1)), y + Int(sin(a) * Double(r - 1)), 3)
        }
        for k in 0 ..< 12 {
            let a = t * 2 + Double(k) * 2 * .pi / 12
            s.circle(col(c), x + Int(cos(a) * Double(r - 1)), y + Int(sin(a) * Double(r - 1)), 2)
        }
        s.circle(col(c), x, y, r)
        s.fillRect(col("white"), x - r / 2, y - r / 2, 2, 2)
        Cute.eyes(s, x, y - 1, 2, look: 0, mood: "happy", blink: Int(t * 2 + Double(x)) % 7 == 0)
        s.fillRect(col("pink"), x - 4, y + 1, 1, 1)
        s.fillRect(col("pink"), x + 4, y + 1, 1, 1)
    }

    static func drawKnot(_ s: Surface, _ x: Int, _ y: Int, _ t: Double) {
        s.circle(col("white"), x, y, 8)
        s.circle(col("black"), x, y, 7)
        for k in 0 ..< 6 {
            let a = Double(k) * 1.05 + t * 0.6
            s.line(col(k % 2 == 1 ? "hotpink" : "yellow"), x + Int(cos(a) * 6), y + Int(sin(a) * 6),
                   x - Int(cos(a) * 6), y - Int(sin(a) * 4), width: 2)
        }
        s.line(col("black"), x - 2, y - 2, x + 2, y + 2)
        s.line(col("black"), x + 2, y - 2, x - 2, y + 2)
    }

    static func drawItem(_ s: Surface, _ kind: String, _ x: Double, _ y: Double, _ t: Double, _ life: Double = 9) {
        if life < 2.5 && Int(t * 10) % 2 == 1 { return }
        let img = sprite(itemSprite[kind] ?? "yw_fish")
        let bob = Int(sin(t * 4 + x) * 1.5)
        s.fillRect(col("black"), Int(x) - 3, Int(y) + 4, 7, 1)
        s.blit(img, Int(x) - img.w / 2, Int(y) - img.h / 2 - 1 + bob)
        if (kind == "gold" || kind == "rainbow") && Int(t * 8) % 3 == 0 { s.fillRect(col("white"), Int(x) + 4, Int(y) - 6, 1, 1) }
    }
}
