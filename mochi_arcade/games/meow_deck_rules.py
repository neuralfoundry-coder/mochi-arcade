"""MEOW DECK battle rules - pure logic, no drawing (the scene animates the events this module returns).

The iOS port mirrors this file in ios/MochiArcade/Games/MeowDeckRules.swift - keep the two in step.

Turn: draw 5, gain fish (energy), play cats, end turn; then every foe acts on the intent it showed.
CHAIN: a cat that shares the ROLE (+1) and/or BREED (+1) of the previous cat played this turn keeps the chain
alive; the chain power is added to that cat's damage / block / heal. WILD cats link to anything.
Numbers: all foe damage is int(n * pow + 0.5); percentage effects use integer maths (x*3//4, x*3//2).
"""
import random

from mochi_arcade.games.meow_deck_data import BOSSES, CAT, FOES, POOL, STARTER, TARGETED, hp_mult, reward_weights

HERO = -1


class Card:
    """One cat in the deck. up = groomed (upgraded); gold = turned golden this draw (cost 0, double power)."""
    _next = 1

    def __init__(self, cid, up=False):
        self.cid = cid
        self.up = up
        self.gold = False
        self.uid = Card._next
        Card._next += 1

    @property
    def d(self):
        return CAT[self.cid]

    @property
    def name(self):
        return self.d["name"] + ("+" if self.up else "")

    @property
    def fx(self):
        return self.d["up"] if self.up else self.d["fx"]

    @property
    def text(self):
        return self.d["uptext"] if self.up else self.d["text"]

    @property
    def base_cost(self):
        return self.d["upcost"] if self.up else self.d["cost"]

    def has(self, op):
        return any(f[0] == op for f in self.fx)

    @property
    def targeted(self):
        return any(f[0] in TARGETED for f in self.fx)


class Hero:
    def __init__(self, hp, maxhp):
        self.hp, self.maxhp = hp, maxhp
        self.block = 0
        self.fish = 0
        self.zoom = self.fluff = self.purr = self.spiky = 0
        self.startled = self.soaked = 0
        self.stolen = 0


class Foe:
    def __init__(self, spec, slot, rng):
        self.id = spec["id"]
        self.boss = bool(spec.get("boss"))
        self.elite = bool(spec.get("elite"))
        data = BOSSES[self.id] if self.boss else FOES[self.id]
        self.name, self.spr = data["name"], data["spr"]
        self.hp = self.maxhp = spec["hp"]
        self.pow = spec["pow"]
        self.block = spec.get("blk", 0)
        self.zoom = spec.get("zoom", 0)
        self.phases = spec["phases"] if self.boss else [data["moves"]]
        self.phase = 0
        self.mi = 0 if self.boss else rng.randrange(len(self.phases[0]))
        self.scared = self.dazed = self.itchy = 0
        self.sleepy = False
        self.slot = slot
        self.intent = None
        self.pick_intent()

    @property
    def alive(self):
        return self.hp > 0

    def pick_intent(self):
        mv = self.phases[self.phase]
        self.intent = mv[self.mi % len(mv)]
        self.mi += 1

    def val(self, n):
        return int(n * self.pow + 0.5)

    def atk_value(self, n):
        d = self.val(n) + self.zoom
        if self.scared > 0:
            d = d * 3 // 4
        return max(0, d)


class Battle:
    def __init__(self, st, deck, hp, maxhp, charms, rng=None, diff=1.0):
        self.st = st
        self.n = st["n"]
        self.rng = rng or random.Random()
        self.charms = charms
        self.diff = diff
        self.hero = Hero(hp, maxhp)
        self.foes = []
        for i, spec in enumerate(st["foes"]):
            spec = dict(spec)
            spec["pow"] = spec["pow"] * diff
            slot = 2 if spec.get("boss") else i
            self.foes.append(Foe(spec, slot, self.rng))
        self.draw_pile = [c for c in deck]
        self.rng.shuffle(self.draw_pile)
        self.hand, self.discard, self.exhaust = [], [], []
        self.turn = 0
        self.chain = 0             # cats in the current chain
        self.power = 0             # chain power (added to dmg / block / heal)
        self.last = None           # last card played this turn
        self.echo = False
        self.best_chain = 0
        self.dmg_taken = 0
        self.dmg_dealt = 0
        self.fever = False         # set by the scene while FEVER is on (cats cost 1 less)
        self.mod = st.get("mod", "")
        self.hand_size = 5 + charms.get("nose", 0) - (1 if self.mod == "windy" else 0)
        self.max_fish = 3 + charms.get("bowl", 0) + (1 if self.mod == "catnip" else 0)
        self.gold_chance = 0.005 + 0.003 * charms.get("bell", 0)
        self.chain_cap = 6 + 3 * charms.get("post", 0)
        self.hero.zoom = charms.get("claws", 0)
        self.hero.fluff = charms.get("coat", 0)
        if self.mod == "lazy":
            for f in self.foes:
                f.sleepy = True

    # ------------------------------------------------------------------ helpers
    def alive(self):
        return [f for f in self.foes if f.alive]

    @property
    def won(self):
        return not self.alive()

    @property
    def lost(self):
        return self.hero.hp <= 0

    def cost(self, card):
        if card.gold:
            return 0
        c = card.base_cost
        if self.fever:
            c = max(0, c - 1)
        return c

    def can_play(self, i):
        if i < 0 or i >= len(self.hand):
            return False
        return self.cost(self.hand[i]) <= self.hero.fish

    def link(self, card):
        """Chain link value of playing card after the last one: role +1, breed +1, wild 1."""
        p = self.last
        if p is None:
            return 0
        m = (1 if card.d["role"] == p.d["role"] else 0) + (1 if card.d["breed"] == p.d["breed"] else 0)
        if m == 0 and card.has("wild"):
            m = 1
        return m

    def draw(self, n, ev):
        got = 0
        for _ in range(n):
            if len(self.hand) >= 10:
                break
            if not self.draw_pile:
                if not self.discard:
                    break
                self.draw_pile = self.discard
                self.discard = []
                self.rng.shuffle(self.draw_pile)
                ev.append(("shuffle", HERO, 0, ""))
            c = self.draw_pile.pop()
            if c.cid != "fleas" and self.rng.random() < self.gold_chance:
                c.gold = True
                ev.append(("golden", HERO, c.uid, c.name))
            self.hand.append(c)
            got += 1
        if got:
            ev.append(("draw", HERO, got, ""))

    # ------------------------------------------------------------------ flow
    def start(self):
        ev = []
        self.begin_turn(ev)
        return ev

    def begin_turn(self, ev):
        h = self.hero
        self.turn += 1
        keep = 5 * self.charms.get("blanket", 0)
        h.block = min(h.block, keep)
        h.fish = max(0, self.max_fish - h.stolen)
        if h.stolen:
            ev.append(("text", HERO, 0, f"-{h.stolen} FISH"))
        h.stolen = 0
        if h.purr > 0:
            self.heal(h.purr, ev)
            h.purr -= 1
        self.chain = self.power = 0
        self.last = None
        self.draw(self.hand_size, ev)
        ev.append(("turn", HERO, self.turn, ""))

    def play(self, i, target):
        """Play hand[i] at foe index target. Returns events."""
        ev = []
        card = self.hand.pop(i)
        self.hero.fish -= self.cost(card)
        m = self.link(card)
        if m > 0:
            self.chain += 1
            self.power += m
        else:
            self.chain = 1
            self.power = 0
        self.best_chain = max(self.best_chain, self.chain)
        bonus = min(self.power, self.chain_cap)
        ev.append(("play", HERO, m, card.name))
        times = 2 if self.echo and not card.has("echo") else 1
        if times == 2:
            self.echo = False
            ev.append(("text", HERO, 0, "ECHO!"))
        mult = 2 if card.gold else 1
        for _ in range(times):
            self.resolve(card, target, bonus, mult, ev)
        self.last = card
        if card.gold:
            ev.append(("jackpot", HERO, 0, card.name))
        card.gold = False
        if card.has("once"):
            self.exhaust.append(card)
        else:
            self.discard.append(card)
        return ev

    def resolve(self, card, target, bonus, mult, ev):
        h = self.hero
        foes = self.foes
        if target is None or target >= len(foes) or not foes[target].alive:
            al = self.alive()
            target = foes.index(al[0]) if al else 0
        for f in card.fx:
            op, n = f[0], f[1]
            hits = f[2] if len(f) > 2 else 1
            if op == "dmg":
                for _ in range(hits):
                    if foes[target].alive:
                        self.hit_foe(target, n * mult + bonus + h.zoom, ev)
            elif op == "all":
                for k, fo in enumerate(foes):
                    if fo.alive:
                        self.hit_foe(k, n * mult + bonus + h.zoom, ev)
            elif op == "rnd":
                for _ in range(hits * mult):
                    al = [k for k, fo in enumerate(foes) if fo.alive]
                    if al:
                        self.hit_foe(self.rng.choice(al), n + bonus + h.zoom, ev)
            elif op == "slam":
                if foes[target].alive:
                    self.hit_foe(target, h.block * mult + bonus + h.zoom, ev)
            elif op == "block":
                self.gain_block(n * mult + bonus, ev)
            elif op == "heal":
                self.heal(n * mult + bonus, ev)
            elif op == "draw":
                self.draw(n * mult, ev)
            elif op == "fish":
                h.fish += n * mult
                ev.append(("fish", HERO, n * mult, ""))
            elif op == "zoom":
                h.zoom += n * mult
                ev.append(("buff", HERO, n * mult, "POWER"))
            elif op == "fluff":
                h.fluff += n * mult
                ev.append(("buff", HERO, n * mult, "FLUFF"))
            elif op == "purr":
                h.purr += n * mult
                ev.append(("buff", HERO, n * mult, "PURR"))
            elif op == "spiky":
                h.spiky += n * mult
                ev.append(("buff", HERO, n * mult, "SPIKY"))
            elif op in ("scare", "daze", "itchy", "sleep"):
                if foes[target].alive:
                    self.debuff(target, op, n * mult, ev)
            elif op in ("scareall", "dazeall", "itchyall"):
                for k, fo in enumerate(foes):
                    if fo.alive:
                        self.debuff(k, op[:-3], n * mult, ev)
            elif op == "fever":
                ev.append(("fever", HERO, n * mult, ""))
            elif op == "echo":
                self.echo = True
                ev.append(("text", HERO, 0, "NEXT CAT X2!"))
            elif op == "cleanse":
                h.startled = h.soaked = 0
                ev.append(("text", HERO, 0, "ALL BETTER!"))
            elif op == "scratch":
                ev.append(("text", HERO, 0, "SCRATCH!"))

    def debuff(self, k, what, n, ev):
        fo = self.foes[k]
        if what == "scare":
            fo.scared += n
            ev.append(("debuff", k, n, "SCARED"))
        elif what == "daze":
            fo.dazed += n
            ev.append(("debuff", k, n, "DAZED"))
        elif what == "itchy":
            fo.itchy += n
            ev.append(("debuff", k, n, "ITCHY"))
        elif what == "sleep":
            fo.sleepy = True
            ev.append(("debuff", k, 1, "SLEEPY"))

    def hit_foe(self, k, raw, ev):
        fo = self.foes[k]
        d = max(0, raw)
        if self.hero.startled > 0:
            d = d * 3 // 4
        if fo.dazed > 0:
            d = d * 3 // 2
        blocked = min(fo.block, d)
        fo.block -= blocked
        d -= blocked
        fo.hp -= d
        self.dmg_dealt += d
        ev.append(("hit", k, d, str(blocked)))
        if fo.hp <= 0:
            fo.hp = 0
            ev.append(("die", k, 0, fo.name))
        elif fo.boss:
            self.check_phase(k, ev)

    def check_phase(self, k, ev):
        fo = self.foes[k]
        n = len(fo.phases)
        if fo.phase >= n - 1:
            return
        cut = [0.5] if n == 2 else [0.66, 0.33]
        if fo.hp <= fo.maxhp * cut[fo.phase]:
            fo.phase += 1
            fo.mi = 0
            fo.scared = fo.dazed = 0
            fo.sleepy = False
            fo.pick_intent()
            ev.append(("phase", k, fo.phase + 1, fo.name))

    def gain_block(self, n, ev):
        h = self.hero
        b = max(0, n + h.fluff)
        if h.soaked > 0:
            b = b * 3 // 4
        h.block += b
        ev.append(("block", HERO, b, ""))

    def heal(self, n, ev):
        h = self.hero
        got = max(0, min(n, h.maxhp - h.hp))
        h.hp += got
        ev.append(("heal", HERO, got, ""))

    def end_turn(self):
        """Discard the hand (FLEAS still in hand bite). Returns events."""
        ev = []
        h = self.hero
        fleas = sum(1 for c in self.hand if c.cid == "fleas")
        if fleas:
            self.hurt_hero(2 * fleas, None, ev, pierce=True)
        for c in self.hand:
            c.gold = False
        self.discard.extend(self.hand)
        self.hand = []
        h.startled = max(0, h.startled - 1)
        h.soaked = max(0, h.soaked - 1)
        self.chain = self.power = 0
        self.last = None
        return ev

    def hurt_hero(self, d, k, ev, pierce=False):
        h = self.hero
        blocked = 0 if pierce else min(h.block, d)
        h.block -= blocked
        d -= blocked
        h.hp = max(0, h.hp - d)
        self.dmg_taken += d
        ev.append(("hurt", HERO, d, str(blocked)))
        if k is not None and h.spiky > 0 and self.foes[k].alive:
            fo = self.foes[k]
            fo.hp = max(0, fo.hp - h.spiky)
            ev.append(("hit", k, h.spiky, "0"))
            if fo.hp <= 0:
                ev.append(("die", k, 0, fo.name))

    def foe_act(self, k):
        """Foe k takes its turn. Returns events (empty if it is dead)."""
        ev = []
        fo = self.foes[k]
        if not fo.alive or self.lost:
            return ev
        fo.block = 0
        if fo.itchy > 0:
            fo.hp = max(0, fo.hp - fo.itchy)
            ev.append(("hit", k, fo.itchy, "ITCHY"))
            fo.itchy -= 1
            if fo.hp <= 0:
                ev.append(("die", k, 0, fo.name))
                return ev
        if fo.sleepy:
            fo.sleepy = False
            ev.append(("text", k, 0, "ZZZ..."))
        else:
            self.do_move(k, fo.intent, ev)
            if fo.alive:
                fo.pick_intent()
        fo.scared = max(0, fo.scared - 1)
        fo.dazed = max(0, fo.dazed - 1)
        return ev

    def do_move(self, k, mv, ev):
        fo = self.foes[k]
        h = self.hero
        kind = mv[0]
        n = mv[1] if len(mv) > 1 else 0
        ev.append(("act", k, 0, kind))
        if kind in ("atk", "atkblk"):
            hits = mv[2] if kind == "atk" and len(mv) > 2 else 1
            for _ in range(hits):
                if h.hp > 0 and fo.alive:
                    self.hurt_hero(fo.atk_value(n), k, ev)
            if kind == "atkblk":
                fo.block += fo.val(mv[2])
                ev.append(("fblock", k, fo.val(mv[2]), ""))
        elif kind == "blk":
            fo.block += fo.val(n)
            ev.append(("fblock", k, fo.val(n), ""))
        elif kind == "shield":
            for j, o in enumerate(self.foes):
                if o.alive:
                    o.block += fo.val(n)
                    ev.append(("fblock", j, fo.val(n), ""))
        elif kind == "buff":
            fo.zoom += n
            ev.append(("fbuff", k, n, "POWER UP"))
        elif kind == "rally":
            for j, o in enumerate(self.foes):
                if o.alive:
                    o.zoom += n
                    ev.append(("fbuff", j, n, "RALLY!"))
        elif kind == "scare":
            h.startled += n
            ev.append(("text", HERO, 0, "STARTLED!"))
        elif kind == "soak":
            h.soaked += n
            ev.append(("text", HERO, 0, "SOAKED!"))
        elif kind == "fleas":
            from_id = "fleas"
            for _ in range(n):
                self.discard.append(Card(from_id))
            ev.append(("junk", HERO, n, ""))
        elif kind == "heal":
            al = [j for j, o in enumerate(self.foes) if o.alive and o.hp < o.maxhp]
            if al:
                j = min(al, key=lambda j: self.foes[j].hp / self.foes[j].maxhp)
                o = self.foes[j]
                got = min(fo.val(n), o.maxhp - o.hp)
                o.hp += got
                ev.append(("fheal", j, got, ""))
        elif kind == "summon":
            free = [s for s in (0, 1) if not any(o.alive and o.slot == s for o in self.foes)]
            if free and len(self.alive()) < 3:
                spec = {"id": n, "hp": int(FOES[n]["hp"] * hp_mult(self.n) * 0.6), "pow": fo.pow, "blk": 0, "zoom": 0}
                new = Foe(spec, free[0], self.rng)
                new.pow = fo.pow
                # reuse a dead slot entry so foe indices stay stable for the scene
                dead = [j for j, o in enumerate(self.foes) if not o.alive and not o.boss]
                if dead:
                    j = dead[0]
                    self.foes[j] = new
                else:
                    self.foes.append(new)
                    j = len(self.foes) - 1
                ev.append(("summon", j, 0, new.name))
            else:
                fo.zoom += 1
                ev.append(("fbuff", k, 1, "POWER UP"))
        elif kind == "steal":
            h.stolen += n
            ev.append(("text", HERO, 0, "FISH SNATCHED!"))
        elif kind == "charge":
            ev.append(("text", k, 0, "CHARGING!"))
        elif kind == "nap":
            ev.append(("text", k, 0, "ZZZ..."))

    def intent_damage(self, fo):
        """(per-hit damage, hits) of a foe's shown attack, or (0, 0)."""
        mv = fo.intent
        if mv[0] == "atk":
            return fo.atk_value(mv[1]), (mv[2] if len(mv) > 2 else 1)
        if mv[0] == "atkblk":
            return fo.atk_value(mv[1]), 1
        return 0, 0

    def incoming(self):
        total = 0
        for fo in self.alive():
            if fo.sleepy:
                continue
            d, hits = self.intent_damage(fo)
            total += d * hits
        return total

    def preview(self, card):
        """Main number shown on a card in hand with the current bonuses (dmg / block / heal), or None."""
        h = self.hero
        m = self.link(card)
        power = (self.power + m) if m > 0 else 0
        bonus = min(power, self.chain_cap)
        mult = 2 if card.gold else 1
        for f in card.fx:
            op, n = f[0], f[1]
            if op in ("dmg", "all", "rnd", "slam"):
                v = (h.block if op == "slam" else n) * (mult if op != "rnd" else 1) + bonus + h.zoom
                if h.startled > 0:
                    v = v * 3 // 4
                return ("dmg", v, f[2] if len(f) > 2 else 1)
            if op == "block":
                v = n * mult + bonus + h.fluff
                if h.soaked > 0:
                    v = v * 3 // 4
                return ("block", v, 1)
            if op == "heal":
                return ("heal", n * mult + bonus, 1)
        return None


# ----------------------------------------------------------------------------- bot (tests, GIF recorder, demo)
def card_value(b, i):
    """How good it is to play hand[i] right now (higher is better), and the best target."""
    card = b.hand[i]
    h = b.hero
    al = [k for k, f in enumerate(b.foes) if f.alive]
    if not al:
        return -1, 0
    incoming = b.incoming()
    need = max(0, incoming - h.block)
    m = b.link(card)
    bonus = min((b.power + m) if m > 0 else 0, b.chain_cap)
    mult = 2 if card.gold else 1
    # target: a foe this card can finish, else the hardest hitter, else the weakest
    tgt = max(al, key=lambda k: (b.intent_damage(b.foes[k])[0] * b.intent_damage(b.foes[k])[1], -b.foes[k].hp))
    v = 0.0
    for f in card.fx:
        op, n = f[0], f[1]
        hits = f[2] if len(f) > 2 else 1
        if op in ("dmg", "slam"):
            per = (h.block if op == "slam" else n) * mult + bonus + h.zoom
            total = per * hits
            kills = [k for k in al if b.foes[k].hp + b.foes[k].block <= total]
            if kills:
                tgt = max(kills, key=lambda k: b.intent_damage(b.foes[k])[0] * b.intent_damage(b.foes[k])[1])
                v += 8 + b.foes[tgt].hp
            else:
                v += total * 0.9
        elif op == "all":
            v += (n * mult + bonus + h.zoom) * len(al) * 0.9
        elif op == "rnd":
            v += (n + bonus + h.zoom) * hits * mult * 0.85
        elif op == "block":
            gain = n * mult + bonus + h.fluff
            v += min(gain, need) * 1.3 + max(0, gain - need) * 0.1
            need = max(0, need - gain)
        elif op == "heal":
            v += min(n * mult + bonus, h.maxhp - h.hp) * (0.9 if not card.has("once") else 0.6)
        elif op == "draw":
            v += 2.5 * n * mult
        elif op == "fish":
            v += 3.5 * n * mult
        elif op in ("zoom", "fluff"):
            v += 3.0 * n * mult * (1.0 if b.turn <= 3 else 0.6)
        elif op == "purr":
            v += 1.2 * n * mult if h.hp < h.maxhp else 0.2
        elif op == "spiky":
            v += 1.5 * n * mult if incoming else 0.5
        elif op in ("scare", "scareall"):
            v += incoming * 0.15 * n
        elif op in ("daze", "dazeall"):
            v += 2.0 * n
        elif op in ("itchy", "itchyall"):
            v += 1.2 * n * mult * (len(al) if op == "itchyall" else 1)
        elif op == "sleep":
            d, hits2 = b.intent_damage(b.foes[tgt])
            v += d * hits2 + 2
        elif op == "echo":
            v += 4 if len(b.hand) > 2 else 0
        elif op == "fever":
            v += n / 15
        elif op == "scratch":
            v += 3
        elif op == "cleanse":
            v += 3 if (h.startled or h.soaked) else 0
    v += m * 2
    return v / (b.cost(card) + 0.6), tgt


def bot_choice(b):
    """(hand index, target) of the best play, or None to end the turn."""
    best = None
    for i in range(len(b.hand)):
        if not b.can_play(i):
            continue
        v, tgt = card_value(b, i)
        if v > 0.4 and (best is None or v > best[0]):
            best = (v, i, tgt)
    return (best[1], best[2]) if best else None


CHARM_PLAN = ["claws", "nap", "bowl", "coat", "nose", "nap", "claws", "post", "blanket", "coat",
              "nap", "bowl", "claws", "nose", "coat", "post", "nap", "blanket", "motor", "bell"]
BASE_HP = 70


def wpick(rng, weights):
    """Weighted index pick (same algorithm on both platforms)."""
    total = sum(weights)
    x = rng.random() * total
    for i, w in enumerate(weights):
        x -= w
        if x < 0:
            return i
    return len(weights) - 1


def reward_card(rng, tier, exclude=()):
    """A random cat for a reward / shop slot on this tier."""
    rar = wpick(rng, reward_weights(tier))
    ids = [c for c in POOL if CAT[c]["rar"] == rar and c not in exclude] or [c for c in POOL if c not in exclude]
    return ids[int(rng.random() * len(ids))]


def reference_kit(tier, rng):
    """A plausible crew for a player who reached this tier: used for checkpoint starts and the campaign check.
    Returns (deck, charms, max hp)."""
    deck = [Card(c) for c in STARTER]
    for k in range(min(5, tier)):                  # a few basics get rehomed along the way
        cid = "rio" if k % 2 == 0 else "sue"
        for c in deck:
            if c.cid == cid:
                deck.remove(c)
                break
    for _ in range(min(18, 3 + 3 * tier)):
        deck.append(Card(reward_card(rng, tier)))
    up = min(0.85, 0.08 * tier)
    for c in deck:
        if rng.random() < up:
            c.up = True
    charms = {}
    for cid in CHARM_PLAN[:tier]:
        charms[cid] = charms.get(cid, 0) + 1
    return deck, charms, BASE_HP + 12 * charms.get("nap", 0)


def simulate(st, deck, charms, maxhp, rng, diff=1.0, max_turns=40):
    """Bot-play one fight. Returns (won, hp_left, turns)."""
    b = Battle(st, [Card(c.cid, c.up) for c in deck], maxhp, maxhp, charms, rng, diff)
    b.start()
    while b.turn <= max_turns:
        for _ in range(30):
            ch = bot_choice(b)
            if ch is None:
                break
            b.play(ch[0], ch[1])
            if b.won:
                return True, b.hero.hp, b.turn
        b.end_turn()
        if b.lost:
            return False, 0, b.turn
        for k in range(len(b.foes)):
            b.foe_act(k)
            if b.lost:
                return False, 0, b.turn
            if b.won:
                return True, b.hero.hp, b.turn
        b.begin_turn([])
    return False, b.hero.hp, b.turn
