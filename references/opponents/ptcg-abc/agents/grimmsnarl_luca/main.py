"""Marnie's Grimmsnarl ex — full policy (2026-07-25).
Deck = ladder #1 Luca's exact 60. A damage-counter CONTROL deck, not a beatdown.

Engine (mined from Luca's 7-23 games, ~3400 MAIN + 500 DAMAGE_COUNTER decisions):
  - Marnie's Grimmsnarl ex (648, 320HP): *Punk Up* auto-attaches up to 5 Basic {D}
    when it EVOLVES a Pokémon -> never hand-fuel the ex. Shadow Bullet [D][D]=180
    + 30 to a bench.
  - Munkidori (112): *Adrena-Brain* — with {D} attached, once/turn MOVE up to 3
    damage counters from OUR mon to the OPPONENT. The finisher/snipe engine.
    Source = Munkidori ITSELF (Froslass keeps pinging it -> self-heal); target =
    something the 30 KOs, else the highest-prize threat.
  - Froslass (104): *Freezing Shroud* pings EVERY ability-mon 10/Checkup (passive).
  - Spikemuth Gym (1259): free Marnie's search each turn. Petrel/Poké Pad/Lillie/
    Night Stretcher = the draw-search chain.

Why a bespoke pilot: GenericPolicy rushed EVOLVE+ATTACK (over-evolved the ex 589x,
under-fired the engine) and scored 24% vs our Alakazam. Luca builds the counter
engine FIRST: attach {D} to Munkidori, fire abilities, chain draw, THEN evolve/attack.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from policy_base import (
    BasePolicy, make_agent, new_diag,
    card_table, attack_table, get_card, prize_count,
    AreaType, CardType, EnergyType, OptionType, Pokemon, SelectContext,
)

# ── Card IDs ────────────────────────────────────────────────────────────────
class C:
    IMPIDIMP = 646         # Basic {D} 70HP, Filch=draw / Corkscrew 10 -> Morgrem
    MORGREM = 647          # Stage1 {D} 100HP, Corkscrew Punch [DD]=60 -> Grimmsnarl ex
    GRIMMSNARL = 648       # Stage2 ex {D} 320HP, 2 prizes, Punk Up (evolve->5 {D}), Shadow Bullet
    MUNKIDORI = 112        # Basic {P} 110HP, Adrena-Brain (move 3 counters me->opp if {D} attached)
    FROSLASS = 104         # Stage1 90HP, Freezing Shroud (Checkup: 10 on every ability-mon)
    SNORUNT = 860          # Basic 70HP -> Froslass
    # Items
    RARE_CANDY = 1079      # Impidimp -> Grimmsnarl ex (skip Morgrem; triggers Punk Up)
    NIGHT_STRETCHER = 1097 # recover mon / basic energy from discard
    BUDDY_POFFIN = 1086    # 2 basics <=70HP -> bench (Impidimp / Snorunt; NOT Munkidori 110HP)
    POKE_PAD = 1152        # dig 2 for a mon -> hand
    UNFAIR_STAMP = 1080    # after our mon KO'd: both shuffle hands, we draw 5 / opp 2
    TOOL_SCRAPPER = 1137   # remove up to 2 tools
    POKEGEAR = 1122        # dig 7 for a Supporter
    # Supporters
    LILLIE = 1227          # shuffle-draw 6 (8 at exactly 6 prizes)
    BOSS = 1182            # gust
    DAWN = 1231            # search / draw
    PETREL = 1219          # search a Trainer -> hand (don't spam)
    # Stadium / Energy
    SPIKEMUTH = 1259       # free Marnie's search each turn
    DARK = 7               # Basic {D} Energy x10 (energy TYPE 7 = DARKNESS)

MARNIE_LINE = {C.IMPIDIMP, C.MORGREM, C.GRIMMSNARL}

# Attack IDs (resolved from card data, never hardcoded)
SHADOW_BULLET = MORGREM_CORK = IMPIDIMP_CORK = FILCH = None
for _aid in (card_table[C.GRIMMSNARL].attacks or []):
    if 'shadow' in (getattr(attack_table.get(_aid), 'name', '') or '').lower():
        SHADOW_BULLET = _aid
for _aid in (card_table[C.MORGREM].attacks or []):
    if 'corkscrew' in (getattr(attack_table.get(_aid), 'name', '') or '').lower():
        MORGREM_CORK = _aid
for _aid in (card_table[C.IMPIDIMP].attacks or []):
    _nm = (getattr(attack_table.get(_aid), 'name', '') or '').lower()
    if 'filch' in _nm:
        FILCH = _aid
    elif 'corkscrew' in _nm:
        IMPIDIMP_CORK = _aid

UNNECESSARY = -10000000

# ── deck load ────────────────────────────────────────────────────────────────
def _resolve_deck_path():
    cands = [os.path.join(_HERE, "deck.csv"), "deck.csv", "/kaggle_simulations/agent/deck.csv"]
    cands += [os.path.join(p, "deck.csv") for p in sys.path if p]
    for p in cands:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("deck.csv not found")

with open(_resolve_deck_path()) as f:
    my_deck = [int(x) for x in f.read().splitlines() if x.strip()]
if len(my_deck) != 60:
    raise ValueError(f"deck.csv must have 60 ids, got {len(my_deck)}")

DIAG = new_diag()


# ── Policy ───────────────────────────────────────────────────────────────────
class GrimmsnarlPolicy(BasePolicy):
    ENERGY_TYPES = {C.DARK}
    ATTACKER_IDS = {C.GRIMMSNARL}

    def go_first(self):
        return True   # setup-heavy Stage-2 line; not a divergence vs Luca (verify if IS_FIRST mined)

    # ── derived state ──────────────────────────────────────────────────────
    def _collect(self):
        self.line_count = self.field[C.IMPIDIMP] + self.field[C.MORGREM] + self.field[C.GRIMMSNARL]
        self.grimm_on_board = self.field[C.GRIMMSNARL] > 0
        self.morgrem_on_board = self.field[C.MORGREM] > 0
        self.munki_on_board = self.field[C.MUNKIDORI] > 0
        self.froslass_on_board = self.field[C.FROSLASS] > 0
        self.bench_body_count = sum(1 for p in self.me.bench if p is not None)
        self.open_bench = self.bench_body_count < 5
        self.active = self.me.active[0] if self.me.active else None
        self.opp = self.opponent.active[0] if self.opponent.active else None

    def score(self, o):
        self._collect()
        return super().score(o)

    def _munki_needs_dark(self, p):
        """A Munkidori with 0 {D} energy wants exactly 1 {D} to switch on Adrena-Brain.
        (should_fuel/attach_helps can't see this: Munkidori's only ATTACK needs {P} we don't run,
        so the generic energy gate would either reject it forever or chase an unreachable attack.)"""
        return p is not None and p.id == C.MUNKIDORI and self.energy_count(p) == 0

    # ── damage model ────────────────────────────────────────────────────────
    def _atk_dmg(self, aid, target):
        if target is None or aid is None:
            return 0
        a = attack_table.get(aid)
        base = getattr(a, 'damage', 0) or 0
        if base <= 0:
            return 0
        d = card_table.get(target.id)
        if d is not None and d.weakness is not None and d.weakness in (getattr(a, 'energies', None) or []):
            base *= 2
        return base

    # ── MAIN play priorities (hand_score) ────────────────────────────────────
    def hand_score(self, cid):
        # Pokémon: open the line, bench the engine, don't flood.
        if cid == C.IMPIDIMP:
            if self.line_count == 0:
                return 17000                       # open the Marnie's line
            return 6000 - 300 * self.field[C.IMPIDIMP] if self.open_bench else 400
        if cid == C.MUNKIDORI:
            # the finisher engine — Luca benches it early (PLAY 100x). Keep 1-2.
            if self.field[C.MUNKIDORI] == 0:
                return 13000
            return 7000 if (self.field[C.MUNKIDORI] < 2 and self.open_bench) else 400
        if cid == C.SNORUNT:
            if self.field[C.FROSLASS] == 0 and self.field[C.SNORUNT] == 0:
                return 9000                        # start the Froslass ping engine
            return 3000 if self.open_bench else 300

        if cid == C.RARE_CANDY:
            # Impidimp -> Grimmsnarl ex (Punk Up). Only when we have a base and the ex in hand.
            if self.hand[C.GRIMMSNARL] and (self.field[C.IMPIDIMP] or self.field[C.MORGREM]):
                return 15000
            return 400
        if cid == C.BUDDY_POFFIN:
            if not self.open_bench:
                return UNNECESSARY
            # only fetches <=70HP basics = Impidimp / Snorunt
            if self.line_count == 0 or (self.field[C.FROSLASS] == 0 and self.field[C.SNORUNT] == 0):
                return 14000
            return 9000 if self.bench_body_count <= 3 else UNNECESSARY
        if cid == C.POKE_PAD:
            if self.line_count == 0 and self.hand[C.IMPIDIMP] == 0:
                return 10000                       # dig a base
            if not self.munki_on_board and self.hand[C.MUNKIDORI] == 0:
                return 9000
            return 7500
        if cid == C.NIGHT_STRETCHER:
            need = (self.discard.get(C.GRIMMSNARL, 0) or self.discard.get(C.MUNKIDORI, 0)
                    or self.discard.get(C.DARK, 0) or self.discard.get(C.MORGREM, 0))
            return 4000 if need else 300
        if cid == C.TOOL_SCRAPPER:
            opp_has_tool = any(p is not None and (p.tools or [])
                               for p in (self.opponent.active + self.opponent.bench))
            return 6000 if opp_has_tool else 200
        if cid == C.UNFAIR_STAMP:
            return 10000 if self.me.handCount <= 4 else 1200

        if cid == C.SPIKEMUTH:
            if self.state.stadiumPlayed:
                return UNNECESSARY
            return 9000 if self.stadium_id != C.SPIKEMUTH else 100   # free Marnie's search each turn
        if cid == C.POKEGEAR:
            return 6000 if not self.state.supporterPlayed else 3000

        if cid == C.LILLIE:
            if self.state.supporterPlayed:
                return UNNECESSARY
            h = self.me.handCount
            return 12000 if h <= 3 else (7500 if h <= 5 else 2000)
        if cid == C.DAWN:
            if self.state.supporterPlayed:
                return UNNECESSARY
            return 8500
        if cid == C.PETREL:
            # search-a-Trainer supporter; USEFUL but we over-played it 145x vs Luca's 95. Temper,
            # and never on an already-fat hand / when Spikemuth already digs the line for free.
            if self.state.supporterPlayed:
                return UNNECESSARY
            if self.me.handCount >= 6:
                return 1500
            return 8000
        if cid == C.BOSS:
            if self.state.supporterPlayed:
                return UNNECESSARY
            if self.opp is not None and self.have_ready_attacker():
                for p in self.opponent.bench:
                    if p is None:
                        continue
                    if self._atk_dmg(SHADOW_BULLET, p) >= p.hp and prize_count(p) >= 2:
                        return 12000               # multi-prize gust-KO
            return 500

        if cid == C.DARK:
            # attach: Munkidori-enable first, else a body that still needs its attack cost
            if any(self._munki_needs_dark(p) for p in self.my_board()):
                return 9000
            for p in self.my_board():
                if p is not None and self.should_fuel(p) and self.attach_helps(p, None):
                    return 8500
            return 800
        return 1000

    def score_play(self, o):
        card = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        return 0 if card is None else self.hand_score(card.id)

    def score_play_poke(self, card):
        return self.hand_score(card.id)

    def score_play_trainer(self, card):
        return self.hand_score(card.id)

    # ── ATTACH ───────────────────────────────────────────────────────────────
    def score_attach(self, o):
        p = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(p, Pokemon):
            return 0
        src = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        # 1 {D} onto a 0-energy Munkidori switches on Adrena-Brain (the engine) — bypass the
        # generic should_fuel gate, which can't recognise a non-attack ability enabler.
        if self._munki_needs_dark(p) and src is not None and self.is_energy(src.id):
            return 12000 + (200 if o.inPlayArea == AreaType.ACTIVE else 0)
        return super().score_attach(o)

    def score_card(self, o):
        # REMOVE_DAMAGE_COUNTER (Adrena-Brain source) + ATTACH_TO Munkidori aren't covered by base.
        ctx = self.context
        if ctx == SelectContext.REMOVE_DAMAGE_COUNTER and o.playerIndex == self.my_index:
            card = get_card(self.obs, o.area, o.index, o.playerIndex)
            if isinstance(card, Pokemon):
                dmg = max(0, (getattr(card, 'maxHp', 0) or 0) - (getattr(card, 'hp', 0) or 0))
                if dmg <= 0:
                    return -1
                # Adrena-Brain moves up to 3 counters off ONE of our mons -> heal the MOST-damaged
                # body we want alive. Luca sources from Grimmsnarl ex AND Munkidori roughly equally
                # (situational, both engine/attacker), NOT flat-Munkidori (that regressed 50->37%).
                keep = card.id in (C.GRIMMSNARL, C.MUNKIDORI)
                return dmg * 20 + (1500 if keep else 0)
        if ctx == SelectContext.ATTACH_TO:
            card = get_card(self.obs, o.area, o.index, o.playerIndex)
            if self._munki_needs_dark(card) and o.playerIndex == self.my_index:
                return 12000 + (200 if o.inPlayArea == AreaType.ACTIVE else 0)
        # NOTE: an ATTACH_FROM "don't strip the ex" rule looked right on the divergence metric
        # (we sourced off the ex 239x vs Luca's 32x) but REGRESSED the A/B 51%->37% — reverted.
        # The mirror-A/B poison lesson again: divergence-agreement != wins.
        return super().score_card(o)

    def attach_priority(self, p, is_active):
        concentrate = self.energy_count(p) * 600
        if p.id == C.GRIMMSNARL:
            return 8000 + concentrate + (300 if is_active else 0)
        if p.id == C.MORGREM:
            return 3500 + concentrate            # backup Corkscrew attacker before the ex lands
        return -1                                 # Punk Up fuels the ex; don't spread elsewhere

    # ── ABILITY (Adrena-Brain / Spikemuth search) ───────────────────────────
    def score_ability(self, o):
        card = get_card(self.obs, o.area, o.index, self.my_index)
        cid = card.id if card is not None else None
        if cid == C.MUNKIDORI:
            return 16000                          # the finisher — move counters onto the opponent
        if cid == C.SPIKEMUTH:
            return 15000                          # free Marnie's search
        return 13000                              # any other engine ability still beats evolve/attack

    # ── EVOLVE (below the engine: fixes the 589x over-evolve) ────────────────
    def score_evolve(self, o):
        card = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        cid = card.id if card is not None else None
        if cid == C.GRIMMSNARL:
            return 12500                          # Punk Up payoff, but AFTER engine abilities
        if cid == C.MORGREM:
            return 12000
        if cid == C.FROSLASS:
            return 9000
        return 8000

    def score_evolves_choice(self, card):
        if card is None:
            return 1000
        if card.id in MARNIE_LINE:
            return 3000
        if card.id == C.FROSLASS:
            return 2000
        return 1000

    # ── ATTACK ───────────────────────────────────────────────────────────────
    def score_attack(self, o):
        active = self.active
        opp = self.opp
        if active is None or opp is None:
            return 800
        aid = o.attackId
        dmg = self._atk_dmg(aid, opp)
        if dmg <= 0:
            return 550 if aid == FILCH else 500   # Filch (draw) over END when nothing else
        if opp.hp <= dmg and prize_count(opp) >= len(self.me.prize):
            return 95000                          # game-winning KO
        score = 1000 + min(dmg, 360)
        if aid == SHADOW_BULLET:
            score += 1200                         # the workhorse (+30 bench snipe too)
        if opp.hp <= dmg:
            score += 2500 + prize_count(opp) * 250
        return score

    # ── sub-select scorers ───────────────────────────────────────────────────
    def score_active_choice(self, o, card):
        if not isinstance(card, Pokemon):
            return 0
        if o.playerIndex == self.op_index:
            return self.gust_value(card)
        if o.playerIndex != self.my_index:
            return 0
        if self.context != SelectContext.TO_ACTIVE:
            # SWITCH is VOLUNTARY (during our turn): bring in the ready attacker to Shadow Bullet —
            # Luca switches Grimmsnarl ex in 55x. (My throwaway-shield logic wrongly blocked that,
            # regressing SWITCH 72->34%.)
            score = len(card.energies or []) * 10
            if card.id in self.ATTACKER_IDS:
                score += 300 if self.can_attack(card) else 120
            score += getattr(card, 'hp', 0) // 30
            return score + 1
        # TO_ACTIVE is FORCED (after a KO): promote a THROWAWAY line body as a shield; keep the
        # engine (Munkidori/Froslass) and the 2-prize ex safe on the bench (Luca: Morgrem 35/
        # Impidimp 25, Munkidori ~0; we wrongly promoted Munkidori 49x).
        score = len(card.energies or []) * 5
        if card.id == C.MORGREM:
            score += 260
        elif card.id == C.IMPIDIMP:
            score += 210
        elif card.id == C.SNORUNT:
            score += 150
        elif card.id == C.GRIMMSNARL:
            score += 40 if self.can_attack(card) else -60
        elif card.id == C.MUNKIDORI:
            score -= 40                           # engine — keep benched
        elif card.id == C.FROSLASS:
            score -= 20                           # passive engine — keep benched
        return score + 1

    def score_setup_active(self, card):
        if card is None:
            return 0
        if card.id == C.IMPIDIMP:
            return 50                             # open with Impidimp (Filch), NEVER Munkidori
        if card.id == C.MORGREM:
            return 30
        if card.id == C.SNORUNT:
            return 20
        return 5

    def score_to_bench(self, card):
        if card is None:
            return 0
        d = card_table.get(card.id)
        if d is None or d.cardType != CardType.POKEMON:
            return 0
        cid = card.id
        n = self.field[cid]
        if cid == C.IMPIDIMP:
            return 200 - 30 * n
        if cid == C.MUNKIDORI:
            return 170 - 60 * n
        if cid == C.SNORUNT:
            return 120 - 40 * n
        return 60 - 20 * n

    def score_to_hand(self, card):
        # search/draw grab (TO_HAND). Luca grabs Munkidori/Energy/Froslass/Unfair Stamp; he does
        # NOT hoard the Marnie's line (Spikemuth searches it free) — we over-grabbed Impidimp 102x.
        if card is None:
            return 0
        cid = card.id
        score = 160 - self.hand[cid] * 40
        if cid == C.MUNKIDORI:
            score += 90 if self.field[C.MUNKIDORI] < 2 else 20
        elif cid == C.DARK:
            need = any(self._munki_needs_dark(p) or (self.should_fuel(p) and self.attach_helps(p, None))
                       for p in self.my_board() if p is not None)
            score += 85 if need else 35
        elif cid == C.FROSLASS:
            score += 75 if self.field[C.FROSLASS] == 0 else 10
        elif cid == C.UNFAIR_STAMP:
            score += 85 if self.me.handCount <= 4 else 20
        elif cid == C.SNORUNT:
            score += 40 if self.field[C.FROSLASS] == 0 and self.field[C.SNORUNT] == 0 else 10
        elif cid == C.IMPIDIMP:
            started = self.line_count > 0 or self.hand[C.IMPIDIMP] > 0
            score += -30 if started else 60       # Spikemuth digs the line for free once started
        elif cid == C.MORGREM:
            score += 30 if (self.field[C.IMPIDIMP] and self.field[C.MORGREM] == 0) else -20
        elif cid == C.GRIMMSNARL:
            score += 45 if (self.field[C.MORGREM] and self.field[C.GRIMMSNARL] == 0) else 10
        return score

    def score_spread_target(self, card):
        # Adrena-Brain / Shadow-Bullet placed damage onto the OPPONENT. Prefer a target the move
        # KOs now (Luca funnels counters into a kill), else the highest-prize threat, else low HP.
        hp = getattr(card, 'hp', 0) or 0
        pz = prize_count(card)
        if hp <= 30:
            return 9000 + pz * 600                # <=3 counters (30) KOs it
        return 3000 - hp * 6 + pz * 300

    def score_discard(self, card):
        if card is None:
            return 0
        cid = card.id
        if cid in (C.GRIMMSNARL, C.MUNKIDORI):
            return -200
        if cid in (C.IMPIDIMP, C.MORGREM):
            return -100 if (self.hand[cid] <= 1 and self.line_count < 2) else 10
        if cid == C.DARK:
            return 30 if self.hand[C.DARK] >= 3 else -30
        if cid == C.LILLIE:
            return -50 if self.hand[cid] <= 1 else 25
        if cid in (C.SNORUNT, C.FROSLASS):
            return -40 if self.field[C.FROSLASS] == 0 else 25
        if self.hand[cid] >= 2:
            return 60
        return 5

    def score_putback(self, card):
        if card is None:
            return 0
        cid = card.id
        if self.hand[cid] >= 2:
            return 70
        if cid in MARNIE_LINE or cid == C.MUNKIDORI:
            return -30 if self.field[cid] == 0 else 60
        return 10


_impl = make_agent(GrimmsnarlPolicy, my_deck, DIAG)


def agent(obs_dict):
    return _impl(obs_dict)
