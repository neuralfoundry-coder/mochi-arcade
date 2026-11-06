"""TOWER TABBY autoplay (desktop only): GIF recording and headless tests.

Plans a route over the stage's cell graph (tower_tabby_data.neighbours) towards the cushion (kittens and
fish on the way, bonus treats, a dazed boss), then turns each step into key presses; it pounces hazards in
front of Mikan and jumps rolling ones.
"""
import heapq

from mochi_arcade.games import tower_tabby_data as data

CW = data.CW


def _route(lv, start, goals):
    dist, prev = {start: 0}, {}
    q = [(0, start)]
    while q:
        d, cur = heapq.heappop(q)
        if cur in goals:
            path = [cur]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return list(reversed(path))
        if d > dist.get(cur, 1 << 30):
            continue
        for nxt, w in data.neighbours(lv, *cur):
            nd = d + w
            if nd < dist.get(nxt, 1 << 30):
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(q, (nd, nxt))
    return None


def make_bot(sc):
    mem = {"path": None, "at": None, "key": None, "t": 0, "dir": "up", "prev": set()}

    def level_of(x, y):
        return min(range(6), key=lambda k: abs(sc.surface(k, x) - y))

    def cell(x, y):
        return level_of(x, y), max(0, min(data.NC - 1, int(x // CW)))

    def goals():
        p = sc.p
        here = cell(p.x, p.y)
        if sc.kind == "bonus":
            pool = [(h.x, h.y + h.r) for h in sc.hz if h.harmless and h.ground is not None]
            pool += [(i.x, i.y + 4) for i in sc.items if i.kind in ("fish", "gfish") and not i.falling]
            if not pool:
                return None
            x, y = min(pool, key=lambda q: abs(q[0] - p.x) + 4 * abs(q[1] - p.y))
            return {cell(x, y)}
        if sc.kind == "boss":
            b = sc.boss
            if b is None or b.dead:
                return None
            if b.daze > 0:
                return {cell(b.x, b.y + b.hh)}
            wands = [i for i in sc.items if i.kind == "wand"]
            if wands and sc.wand_t <= 0:
                return {cell(wands[0].x, wands[0].y + 6)}
            return None
        for kt in sc.kits:
            if not kt.follow:
                kc = cell(kt.x, kt.y)
                if abs(kc[0] - here[0]) <= 1 and abs(kt.x - p.x) < 100:
                    return {kc}
        for it in sc.items:
            if it.kind != "fish" and not it.falling:
                ic = cell(it.x, it.y + 6)
                if ic[0] == here[0] and abs(it.x - p.x) < 70:
                    return {ic}
        g = data.find(sc.lv, "G")
        return {g} if g else None

    def walk_to(keys, x, tol=2):
        p = sc.p
        if abs(x - p.x) > tol:
            keys.add("right" if x > p.x else "left")

    def dodge(keys):
        p = sc.p
        for h in sc.hz:
            if h.harmless or h.kind == "spritz" or h.batted:
                continue
            dx = h.x - p.x
            same = abs(h.y - (p.y - 6)) < 12
            if h.kind == "cone" and abs(dx) < 12 and h.y < p.y and sc.milk_t <= 0:
                keys.discard("left")
                keys.discard("right")
                keys.add("left" if dx > 0 else "right")
                return
            if h.kind == "cushion" and h.mode == "fall" and abs(dx) < 14 and h.y < p.y:
                keys.discard("left")
                keys.discard("right")
                keys.add("left" if dx > 0 else "right")
                return
            if same and h.kind in ("yarn", "marble", "dust", "mouse", "ball", "moth", "spider", "bot") and abs(dx) < 34:
                facing = (dx > 0) == (p.face > 0)
                if facing and p.pcd <= 0 and p.ground is not None and abs(dx) < 30 and h.kind != "bot":
                    keys.add("b")
                    return
                if p.ground is not None and abs(dx) < 20 and (h.vx * dx < 0 or abs(dx) < 10):
                    keys.add("a")
                    return
        for s in sc.shots:
            if s.kind in ("drop", "wave") and abs(s.y - (p.y - 6)) < 9 and 0 < (s.x - p.x) * (1 if s.vx < 0 else -1) < 26:
                keys.add("a")
                return

    def follow(keys, frame, gl):
        """Press keys for the next step of the route to the goal cells; False when there is no route."""
        p = sc.p
        here = cell(p.x, p.y)
        key = tuple(sorted(gl))
        if mem["path"] is None or mem["at"] != here or mem["key"] != key or mem["t"] % 30 == 0:
            mem["path"] = _route(sc.lv, here, gl)
            mem["at"], mem["key"] = here, key
        path = mem["path"]
        if not path:
            return False
        if len(path) < 2:
            k, c = path[0]
            walk_to(keys, c * CW + 8, 3)
            return True
        (k0, c0), (k1, c1) = path[0], path[1]
        cx = c1 * CW + 8
        px = c0 * CW + 8
        ch = sc.lv[k0][c0]
        if k1 == k0 + 1 and c1 == c0 and ch in "HR":
            if abs(p.x - px) > 2:
                walk_to(keys, px)
            else:
                mem["dir"] = "up"
                keys.add("up")
                if ch == "R" and p.ground is not None and frame % 4 == 0:
                    keys.add("a")
        elif k1 == k0 - 1 and c1 == c0 and sc.lv[k1][c1] in "HR":
            if abs(p.x - px) > 2:
                walk_to(keys, px)
            else:
                mem["dir"] = "down"
                if frame % 2 == 0:
                    keys.add("down")
        elif ch == "W" and (k1 != k0 or abs(c1 - c0) > 1):
            if abs(p.x - px) > 3:
                walk_to(keys, px)
            elif frame % 2 == 0:
                keys.add("down")
        elif k1 == k0 + 1:                         # spring bed: bounce and steer onto the shelf above
            walk_to(keys, cx, 3)
            mem["air_x"] = cx
        elif k1 == k0 and abs(c1 - c0) >= 2:       # jump a gap
            keys.add("right" if c1 > c0 else "left")
            edge = (c0 + (1 if c1 > c0 else 0)) * CW
            if ((p.x >= edge if c1 > c0 else p.x <= edge) or abs(edge - p.x) < 1.5) and p.ground is not None:
                keys.add("a")
                mem["air_x"] = cx
        elif k1 == k0 and (sc.lv[k1][c1] == "~" or ch == "~"):   # hammocks: board when docked, ride, hop off
            right = c1 > c0
            if p.ground in sc.hams:
                h = p.ground
                j = 1
                while j < len(path) and path[j][0] == k0 and sc.lv[k0][path[j][1]] == "~":
                    j += 1
                if j < len(path) and path[j][0] == k0:
                    edge = path[j][1] * CW + (0 if right else CW)
                    docked = h.x1 >= edge - 1 if right else h.x0 <= edge + 1
                    walk_to(keys, edge + (4 if right else -4) if docked else h.x0 + 16, 2)
                else:
                    walk_to(keys, h.x0 + 16, 2)
            else:
                edge = (c0 + 1) * CW if right else c0 * CW
                docked = any(h.k == k1 and (h.x0 <= edge + 1 if right else h.x1 >= edge - 1) and h.x0 - 1 <= edge <= h.x1 + 1
                             for h in sc.hams)
                if docked:
                    keys.add("right" if right else "left")
                else:
                    walk_to(keys, px + (5 if right else -5))
        else:
            walk_to(keys, cx)
        return True

    def f(frame):
        keys = plan(frame)
        p = sc.p
        for k in ("a", "b"):          # make sure a grounded press is a fresh press
            if k in keys and p.ground is not None and k in mem["prev"]:
                keys.discard(k)
        mem["prev"] = set(keys)
        return keys

    def plan(frame):
        keys = set()
        mem["t"] += 1
        p = sc.p
        if sc.state not in ("play", "intro", "warning"):
            if sc.state == "tally" and frame % 20 == 0:
                keys.add("a")
            return keys
        if p.warp_t > 0:
            return keys
        if p.climb is not None:
            keys.add(mem["dir"])
            return keys
        if p.ground is None and mem.get("air_x") is not None and sc.kind == "normal":
            walk_to(keys, mem["air_x"], 2)
            keys.add("a")
            return keys
        if p.ground is not None:
            mem["air_x"] = None
        gl = goals()
        if sc.kind == "boss" and sc.boss is not None:
            b = sc.boss
            if gl and follow(keys, frame, gl):
                if b.daze > 0 and abs(b.x - p.x) < 44 and abs(b.y - (p.y - 6)) < 20 and p.pcd <= 0:
                    keys.discard("left")
                    keys.discard("right")
                    keys.add("right" if b.x > p.x else "left")
                    keys.add("b")
            elif abs(b.x - p.x) < 80 and abs(b.y - p.y) < 50:
                keys.add("left" if b.x > p.x else "right")
            dodge(keys)
            return keys
        if sc.kind == "bonus":
            if gl:
                follow(keys, frame, gl)
            if sc.sd["bt"] == "yarn":
                for h in sc.hz:
                    if h.harmless and abs(h.x - p.x) < 28 and abs(h.y - (p.y - 5)) < 10 and p.pcd <= 0:
                        keys.discard("left")
                        keys.discard("right")
                        keys.add("right" if h.x > p.x else "left")
                        keys.add("b")
                        break
            return keys
        if not gl or not follow(keys, frame, gl):
            if sc.goal:
                walk_to(keys, sc.goal[0], 3)
        dodge(keys)
        return keys
    return f
