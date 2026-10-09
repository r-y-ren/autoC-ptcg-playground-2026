# Pokémon TCG AI Battle Challenge — Project Guide

## 🔴 關鍵規則（Session 重啟時第一條）

1. **只提交版本當用戶明確說「提交」或「submit」**
   — 不可以自作主張 build + submit，即使你認為代碼是好的。
2. **每輪 Session 先讀這份文件的 Current status + 下方 doc 列表**
   — 確定目前做什麼、做到哪、什麼是廢案。
3. **每輪 Session 先讀 `docs/per_deck_policy_plan.md`**
   — 這是當前策略方針（比照官方 sample 寫每張牌的完整政策）。

Competition: **Pokémon TCG AI Battle Challenge** (Kaggle × The Pokémon Company × 松尾研 × HEROZ).
Goal: build an `agent(obs_dict)` that wins the standard-format card battle. Two tracks:
- **Simulation**: `pokemon-tcg-ai-battle` (Elo ladder, auto-battles). **官方時程（用戶 8-20 貼出的 rules 頁確認）：Entry Deadline 8-09、Team Merger 8-10、Final Submission Deadline 2026-08-17、8-17～~8-31 只讓對局跑到收斂後排行榜定案（不接受新提交）。** 我們 8-20 補提交遭 API 拒絕（`400 Submission not allowed: Submissions have been disabled for this competition`）正是因為已過 8-17。**這個賽道已經死了，分數永久凍結在 7-25 那組爛配對，不用再花力氣**。獎勵只有 Knowledge，無現金。
- **Strategy report**: `pokemon-tcg-ai-battle-challenge-strategy` ($240K 現金)。Deadline **2026-09-13**（`kaggle competitions list` 確認仍開放，`userHasEntered=True`，但 0 submissions — 完全沒動）。**這是唯一還能拿分的賽道，現在是主力。**
- 天梯賽道歷史規則（已失效）：5 submissions/day；latest 2 are scored。

## Current status (2026-08-20 — 天梯賽道確認已關閉提交，最終分數凍結在 7-25 爛配對；主力轉往策略報告 $240K)

- **8-20 盤點：7-25 之後停擺 26 天沒有 commit/提交。試圖補提交 Alakazam v4.3（重跑 #54874307 同一 build）+ 凍結 v4.2 對照組（agents/_ab_v42_frozen）想把 7-25 的 Grimmsnarl-Luca 實驗性提交（474.5，見 [Grimmsnarl Track]）擠出「latest 2 scored」視窗、拉回 735.4 地板 —— 兩次 API 呼叫都是 `400 Bad Request`，用 `api.competition_submit` 直接看 response body 才挖出真正原因：`Submissions have been disabled for this competition`。用戶隨後貼出官方 rules 頁時程確認：**Final Submission Deadline = 2026-08-17**（比我們猜的 8-16 晚一天），8-17～~8-31 只是讓對局跑到收斂、排行榜定案，不接受新提交。結論：**天梯分數永久定格在 Grimmsnarl(474.5) + v4.3(672.7) 這組爛配對，無法補救**。7-25 uncommitted 的 GrimmsnarlPolicy 程式碼已補 commit（284834c），純收尾。
- **8-20 策略報告 SHIPPED（用戶明確指示「做完直接送出」）：規則抓齊 = Kaggle Writeup 格式、限 2000 字、每隊僅 1 次提交（非天梯式）、9-13 截止（GMT+8 顯示 9-14 07:59）、評分 Model 70%/Deck 20%/Report 10%、8 位 Finalist 各 $30K、AI 輔助寫作未被禁止。已提交 writeup《Piloting Beats Deckbuilding: A Divergence-Mined Alakazam Policy》（1441 字，網址 `.../writeups/new-writeup-1787202751459`）—— 內容涵蓋 deck 選卡邏輯、divergence-mining 方法論、「毒藥偵測器」五次教訓、四道閘門逐一數據（deck swap 80.4%、rush-gate 62.5→64%、fortress-gate 35→75%、escape-fuel 39→65%）、Grimmsnarl 負面實驗誠實揭露、未竟事項。**Kaggle 規定 9-14 截止前都可以編輯重交，非鎖死** —— 若之後想補強（如加圖表到 Media Gallery、或用戶想微調文字），直接編輯同一篇 writeup 即可，不會產生重複提交。**
- **下一步：策略報告已交出基本版，剩餘時間（9-13 前）可選擇性打磨：(1) 加 Media Gallery 圖表（Elo 收斂曲線、逐對手勝率長條圖，目前只有文字表格）；(2) 若使用者想找人 review 內容；(3) 天梯這邊已無事可做，除非用戶另有指示。**

## 歷史紀錄

7-17 以前的每日 status 與 6-21 舊 meta 已移到 [`docs/history.md`](docs/history.md)。
只有 `## Current status` 留在這裡 — CLAUDE.md 每次 session 全載入，歷史不該佔位。

## Meta — 每天用 `tools/autopsy.py` 重跑（meta 翻很快）

當前 meta 看上面的 `## Current status`、`docs/strategy/牌組策略.md`，以及 memory `card_mechanics_reference.md`。

## Repo layout (reorganized 2026-06-18 — see README.md)
- `agents/_base/policy_base.py` — **SHARED `BasePolicy` (ABC) — the single source of truth for the generic, deck-agnostic piloting logic (2026-06-23).** Why it exists: agents are self-contained `main.py` files, so the scaffolding used to be COPY-PASTED per deck — a fix in one deck did NOT propagate, and new decks silently re-introduced solved bugs (e.g. energy over-fill). Now: the **generic ENERGY DISCIPLINE** (`should_fuel`/`can_attack`/`attach_helps`, derived from each attack's real cost — over-fill is impossible by construction), dispatch, sub-scorers, and the robust `agent()` wrapper live in the base and are INHERITED; **deck-specific decisions are `@abstractmethod`s** (incl. `go_first()` — the deck-specific first/second choice) so Python REFUSES to instantiate a subclass that forgets one. A new deck = a thin `BasePolicy` subclass implementing the hooks (see `agents/megastarmie/main.py` as the reference). The Kaggle/cabt loader appends the agent dir to `sys.path`, so the bundled sibling `policy_base.py` imports fine; `build_submission.sh` copies it into the tarball (dev uses a symlink to `agents/_base/`).
- `agents/<deck>/` — each ladder agent. Each: `main.py`, `deck.csv` (60 IDs), `build_submission.sh` (packs `main.py + deck.csv + policy_base.py + cg/`). **New deck → subclass `BasePolicy`** (NOT copy `alakazam/main.py`, which is the LEGACY self-contained style). Legacy agents (alakazam/trevenant) still have inlined scaffolding and have NOT been migrated yet.
  - **After building/changing any agent, run `venv/bin/python tools/check_agent.py agents/<deck>` — it asserts the universal invariants (no energy over-fill, no crashes/fallbacks, legal selections) and reports whether the agent is on `BasePolicy`.** This is the systematic guard against per-deck regressions.
  - `agents/dragapult` = **Dragapult ex (PRIMARY, 6-22)** — adopts the official sample pilot (NOT a `*Policy` class; it's the sample's `_policy()` + a robust `agent()` wrapper). `agents/megastarmie` = **Mega Starmie ex + Cinderace (NEW 6-22, clone of ladder #1 keidroid)** — a `MegaStarmiePolicy` written from scratch on the shared scaffolding, then divergence-tuned vs keidroid (cabt beats our Dragapult 66%). `agents/alakazam` = Alakazam (AlakazamPolicy, hedge). `agents/trevenant` = Hop's Trevenant (demoted). `agents/bellibolt`/`agents/typhlosion` = deprioritized.
- `docs/strategy/` — TC strategy write-ups. `web/` — human-vs-AI sandbox. `research/` — early/superseded experiments.
- `tools/`: `autopsy.py` (daily pipeline: download eps+LB → meta + divergence → `/tmp/autopsy/`), `meta_analyze.py` (episode zip → archetype distribution + WR + top-tier slice + matchup matrix; **run daily**), `replay_divergence.py` (replay top-pilot games through our agent → SelectContext-bucketed agree% = where we pilot differently), `divergence_decode.py` (same, but DECODES each disagreement into card/attack/option NAMES + aggregates human-vs-ours picks, and `--player "TeamName"` isolates ONE pilot — this is how you derive concrete piloting RULES, not just bare indices), `cabt_eval.py` (official-env eval vs sample bots — opponents now STALE: crustle/lucario/abomasnow are extinct), `cabt_ab.py` (A/B two of our agents), **`cabt_gauntlet.py` (run agent vs the REAL top-tier field, prevalence-weighted: Trevenant 41.5%→Mewtwo 0.9%)**, `check_agent.py` (**run after any agent change** — generic invariant checker: energy over-fill, fallbacks/crashes, BasePolicy structure), `battle_analyze.py` (anomaly/loss-cause report).
- **⚠ cabt is NOISY (±~10pts at 40g; use ≥80) AND still mispredicts the ladder** even with the composition-correct gauntlet — because our opponent PILOTS (our agents + GenericPolicy) are weaker than real top-100 humans. The gauntlet contradicted the known ladder result (rated `dragapult_nobonus` −2.2 though the ladder proved 871>778). **cabt is a regression-catcher/yardstick, NOT a strategic oracle; the ladder is the only true judge.**
- **`agents/_base/generic_policy.py`** — `GenericPolicy(BasePolicy)` + `make_generic_agent(deck_ids)`: turns any decklist into a competent cabt opponent (config auto-derived from card data; energy discipline inherited). `agents/_opponents/{chandelure,froslass,mewtwo}/deck.csv` = consensus high-WR lists pulled from episodes; `agents/_opponents/lucario_v3/` = the shared community Lucario pilot.
- **PrizeTracker (`policy_base.py`)** — adopted from the shared "1250 Starmie" agent. Deduces OUR prized cards (decklist − everything visible == prize set, only when it equals the prize count; conservative, returns None when ambiguous). Wired into `make_agent` (persists across decisions); BasePolicy exposes `self.is_prized(cid)` / `self.prized_count(cid)` / `self.copies_in_deck(cid)`. Verified: deduces the prize set ~83% of decisions on real games. First use: megastarmie skips Mega Signal when every Mega Starmie ex is prized (the search would whiff). **Available to ALL BasePolicy agents — add more uses (don't dig for prized pieces; plan around a prized win-con).**
- `docs/official/models/` — official notebooks + `cg-lib/` (local engine). **GITIGNORED** (on the Kaggle site); kept locally for testing. `.kaggle*/`, `private/`, `venv/`, `**/cg/`, `*.tar.gz` also gitignored.

## Build & submit (per agent)
```bash
CG_LIB_PATH="$(pwd)/docs/official/models/cg-lib/cg" bash agents/<agent>/build_submission.sh
venv/bin/kaggle competitions submit pokemon-tcg-ai-battle -f agents/<agent>/submission.tar.gz -m "message"
venv/bin/kaggle competitions submissions pokemon-tcg-ai-battle    # check score
```

## Analyzing the meta (episode replays)
Episodes (real ladder games incl. top players) are Kaggle datasets, one per day:
```bash
venv/bin/kaggle datasets download kaggle/pokemon-tcg-ai-battle-episodes-index -p /tmp/idx --unzip   # /tmp/idx/manifest.csv lists dates + top/median scores
venv/bin/kaggle datasets download kaggle/pokemon-tcg-ai-battle-episodes-2026-06-19 -p /tmp/ep19      # zip ~720MB (manifest's 21GB is the UNCOMPRESSED size)
venv/bin/kaggle competitions leaderboard pokemon-tcg-ai-battle --download -p /tmp/lb                # name→Elo for the top-tier slice
venv/bin/python tools/meta_analyze.py /tmp/ep19/<zip> --elo 1150                                     # archetype distribution + matchups
venv/bin/python tools/replay_divergence.py /tmp/ep19/<zip> agents/alakazam --archetype Alakazam      # piloting divergences
```
Process the .zip directly with Python `zipfile` (do NOT extract — 21GB unpacked). Each episode JSON: `steps[1][pi]['action']` = the 60-card deck; `rewards` = [p0,p1] (winner = higher); `info.Agents[i].Name` = player (map to Elo via the leaderboard CSV's `TeamName`). Replay: `steps[t][pi]['observation']` feeds our `agent`; the ANSWER to obs[t] is `steps[t+1][pi]['action']` (off-by-one — sub-decisions are consecutive same-pi steps; step-1 action is the deck).
Leaderboard: `venv/bin/kaggle competitions leaderboard pokemon-tcg-ai-battle --download`.

## Engine API essentials (cg-lib)
- Game-over: `obs.current.result != -1` (winner index). `obs.select is None` during deck-selection (return the 60 IDs).
- `SelectContext`: MAIN=0, SETUP_ACTIVE=1, SETUP_BENCH=2, SWITCH=3, TO_ACTIVE=4, TO_BENCH=5, TO_HAND=7, DISCARD=8, ATTACH_FROM=21, ATTACH_TO=22, DAMAGE_COUNTER=13/14, IS_FIRST=41, MULLIGAN=42.
- `OptionType`: NUMBER=0, YES=1, NO=2, CARD=3, ENERGY=6, PLAY=7, ATTACH=8, EVOLVE=9, ABILITY=10, RETREAT=12, ATTACK=13, END=14.
- `Pokemon`: `.hp` (current), `.maxHp`, `.energies` (list of EnergyType), `.energyCards`, `.tools`, `.id`.
- `EnergyType`: COLORLESS=0, GRASS=1, FIRE=2, WATER=3, LIGHTNING=4, PSYCHIC=5, FIGHTING=6 ...
- `State`: `.turn`, `.yourIndex`, `.firstPlayer`, `.supporterPlayed`, `.stadiumPlayed`, `.energyAttached`, `.stadium`, `.players[2]`.
- Card data: `all_card_data()` → `card.cardId/hp/weakness/resistance/ex/megaEx/stage1/stage2/attacks/skills/evolvesFrom/retreatCost`. `all_attack()` → `attack.attackId/name/damage/energies/text`.

## Testing: use the OFFICIAL cabt env (accurate), not the ctypes harness
`venv/bin/pip install kaggle-environments` (1.30.1 = ladder version), then:
```bash
venv/bin/python tools/cabt_eval.py agents/alakazam crustle 20   # <our_dir> <crustle|lucario|abomasnow|dragapult|mirror> [games]
```
`tools/cabt_eval.py` builds opponents from the sample notebooks + consensus decks and runs `make('cabt')` matches (~1s/game). The old ctypes loop (battle_start/battle_select) gives UNRELIABLE numbers for some matchups (it crippled the strong day-1 Crustle bot: ctypes 98% vs cabt 20% for the same matchup; mirror & Lucario agree). Trust cabt + the real ladder. Agents need `cg/` copied into their dir for cabt.

## Human-vs-AI web sandbox (`web/`)
Play against the agent in a browser and see the strategy's suggested move + per-option scores at every decision (for finding optimization points by comparing human intuition vs the agent).
```bash
venv/bin/python web/server.py        # then open http://localhost:8000
```
- You pilot the Typhlosion deck (`agents/typhlosion`); pick opponent (Crustle/Lucario) in the header.
- `web/server.py`: stdlib HTTP server wrapping the cg engine; runs the opponent agent automatically; exposes `/new?opp=`, `/state`, `/select`. The human's legal options are labelled and each shows `QuilavaPolicy.rank()` score; the AI's `normalize_selection` pick is flagged `recommended`/★.
- `web/index.html`: single-page board UI. Single global game, single-threaded (one user at a time — the cg engine has global state).

## Strategy reference docs (Traditional Chinese — for the user to review)
- `docs/strategy/牌組策略.md` — all deck strategies, meta distribution, rock-paper-scissors map, expected-WR table, deck-building checklist.
- `docs/strategy/訓練家牌應用.md` — every trainer card by category (draw/search, energy, disruption, heal/recover, switch, tools, stadiums) + application notes & combos.
Keep both updated whenever the meta shifts or we switch decks.

## Card mechanics reference
Full per-deck card/attack/ability details live in the agent memory file `card_mechanics_reference.md`
(`/home/wmh/.claude/projects/-home-wmh-workspaces-ai-projects-ptcg-abc/memory/`). **Update it on every deck change** — the user wants every deck's mechanics kept permanently.

### Dragapult ex (agents/dragapult — PRIMARY, 6-22) — consensus top-tier netdeck
- Pokémon: Dreepy(119, 70HP {N})→Drakloak(120, 90HP, *Recon Directive*: look top2, take 1)→**Dragapult ex(121, 320HP, stage2, 2 prizes)**. Support: Budew(235, 30HP {G}, *Itchy Pollen*[]=10 → opp can't play Items next turn), Fezandipiti ex(140, 210HP {D}, *Flip the Script*: if a mon was KO'd last turn, draw 3; Cruel Arrow[CCC]=100 to any), Latias ex(184, 210HP {P}, *Skyliner*: your Basics have no retreat cost; Eon Blade[PPC]=200), Meowth ex(1071, 170HP {C}, *Last-Ditch Catch*: on play from hand→search a Supporter). Energy: 4 Basic {R}/Fire(id 2) + 4 Basic {P}/Psychic(id 5).
- **Engine**: **Phantom Dive [R][P] = 200 to Active + put 6 damage counters (=60) on opp's BENCH however you like** — the win condition: set up multi-prize turns by pre-loading counters then KO-ing. Jet Headbutt[C]=70 is the cheap fallback. Disruption: **4× Crushing Hammer**(1120, coin-flip discard an opp Energy), Budew item-lock. Accel: **Crispin**(1198, search 2 diff-type basic energy: attach 1 + 1 to hand), **Rare Candy**(1079, Dreepy→Dragapult skip). Search/draw: Buddy-Buddy Poffin(1086, 2 basics ≤70HP→bench), Ultra Ball, Brock's Scouting, Poké Pad, Lillie's Det, Boss(1182), Night Stretcher, Unfair Stamp(1080, comeback draw after a KO), Lucky Helmet(1156 tool), Team Rocket's Watchtower(1256 stadium, {C} mons have no Abilities). **Plays GO SECOND.** Phantom Dive immune-active IDs {158,207,330,345}; no-counter IDs {28,199,203,207,362,1136} + holders of Mist(11)/Rock-Fighting(20) energy. Weakness: none on the line (Budew=Fire-weak).
- **Agent**: NOT a `*Policy` — it's the official sample's `_policy()` + a robust `agent()` wrapper. See the status section for why (sample beat a from-scratch policy 13-1).
- **6-22 PILOT FIX (divergence-driven)**: `divergence_decode` vs Elo≥1150 pool showed **Fezandipiti ex over-prioritization** was the #1 bug. Top players attach energy to Dragapult ex & play Dreepy/Budew/Latias/items over Fezandipiti ex. Fix: Fez PLAY 53000→35000, Fez hand_score(pre_ko) 50000→15000, Dreepy PLAY 51000→54000, ATTACH bonus +25000 when Dragapult ex <2 energy. ⚠ CRITICAL: EVOLVE score MUST stay at 30000 (raising it to 50000 made the ATTACH-vs-EVOLVE divergence WORSE). This is the lesson: every score change must be verified against the divergence data, not made intuitively. See divergence_data in `/tmp/autopsy/`.

### Mega Starmie ex + Cinderace (agents/megastarmie — NEW 6-22, clone of ladder #1 keidroid)
- Pokémon: Staryu(1030, 70HP {W})→**Mega Starmie ex(1031, 330HP, STAGE-1 megaEx, 3 prizes, {W})**; **Cinderace(666, 160HP, Stage-2 {Fire})** played WITHOUT its pre-evos via *Explosiveness* (may put it face-down in the Active Spot during setup → it opens like a Basic). Energy: 9 Basic {W}(id 3) + **4 Ignition Energy(id 17)**.
- **Engine**: Mega Starmie ex — **Jetting Blow [W] = 120 + 50 to 1 bench** (THE WORKHORSE; needs only 1 Water; keidroid's most-used attack) and **Nebula Beam [C][C][C] = 210, ignoring weakness/resistance AND any effects on opp's Active** (pierces Crustle-immunity / Mist / damage-reduction — universal hammer). Cinderace **Turbo Flare [C] = 50 + search 3 Basic Energy → bench** (T1 accel engine). **Ignition Energy provides {C}{C}{C} on an EVOLUTION mon but is DISCARDED end-of-turn** → it is a one-shot Nebula enabler, NOT build-up. Sustain: **Wally's Compassion(1229)** heal ALL dmg on a Mega ex + put its energy to hand (recycle), **Hero's Cape(1159)** +100HP → 430HP wall. Disruption 4× Crushing Hammer. Search/draw: Mega Signal(1145, find a Mega ex), Salvatore(1189, evolve a no-ability mon e.g. Staryu→Mega Starmie this turn), Buddy Poffin, Ultra Ball, Pokégear, Hilda, Lillie's Det, Harlequin, Night Stretcher, Boss. **Plays GO FIRST** (deck-specific; opposite of Dragapult). Weakness: Mega Starmie=Lightning, Cinderace=Water.
- **Agent**: `MegaStarmiePolicy` written from scratch on the shared scaffolding (no official sample exists), then **divergence-mined vs keidroid's 116 games** (`divergence_decode --archetype Cinderace --player keidroid`). The 5 measured fixes → cabt vs our agents 40/52/78 → **66/68/85** (Dragapult/Alakazam/Trevenant). See Current-status section for the fix list. Key piloting truths: **Jetting Blow (1 Water) is the default attack, not Nebula**; **Ignition only as an active-Mega Nebula finisher**; **spread snipes low-HP engine pieces, not high-HP walls**.

### Hop's Trevenant (agents/trevenant — counter-meta deck, DEMOTED 6-22)
- Pokémon (all SINGLE-prize, no ex): Hop's Phantump(878, 70HP {P})→**Hop's Trevenant(879, 140HP)**, Hop's Cramorant(311, 110HP), Hop's Snorlax(304, 150HP). Energy: 4 Mist(11, {C}+prevent effects on holder), 4 Telepath Psychic(19, {P}+search 2 basic {P} on attach). Trainers: Hop's Bag(1115), Pokégear(1122), TR Transceiver(1134)→Petrel(1219, any Trainer), Poké Pad(1152), **Hop's Choice Band(1171, −{C} cost +30 dmg)**, Boss(1182), Hilda(1225), Lillie's Det(1227), **Postwick(1255 stadium, +30 Hop's dmg)**, Secret Box(1092), Night Stretcher(1097).
- **Engine**: Trevenant **Horrifying Revenge** [C]=30, +100 if a Hop's was KO'd last opp turn (=130); with Choice Band it costs 0. Stack +30s (Postwick + Choice Band + **Snorlax "Extra Helpings" ability**, no self-stack) → 130+90=220. Cramorant **Fickle Spitting** [C]=120 only when opp at 3-4 prizes. Plan: flood cheap 1-prize bodies, trade UP into the opp's 3-prize ex, win the prize race. Weakness: Trevenant=Dark, Snorlax=Fighting (=Lucario, keep it benched).

### Lucario / Crustle (reference)
- **Mega Lucario ex = the field king (56%)** — megaEx, 3 prizes. Beat it by trading single-prize attackers up (Trevenant) or out-tempo (Alakazam, even matchup).
- Crustle (now rare): Dwebble(344)→Crustle(345), ability blocks ALL damage from ex/megaEx attacks. Immune-to-ex IDs {158,207,330,345}. Beat with non-ex attackers.

## Next steps / ideas
1. **Check the 6-22 scores next reset (THE key read)**: the latest-2-scored are **`megastarmie` (#5) + Dragapult fix-v2 (778.5)**. Did megastarmie's keidroid-clone land near the #1's tier? If it scores well it becomes a PRIMARY candidate; cabt says it beats our Dragapult 66% but **real ladder is the only judge**. Did the Dragapult Fez fix recover? Re-evaluate the primary based on both.
2. **Run `tools/autopsy.py` daily** — one command gives you fresh meta + divergence data. The meta flips fast (Lucario 56%→extinct in 3 days).
3. **megastarmie piloting headroom**: MAIN context is still only **38% agree** vs keidroid (lots of play-sequencing divergence). If the ladder read is good, the next pass mines MAIN: he plays Pokégear/Mega Signal/draw-search more, we over-play Buddy Poffin (partly curbed) and mis-sequence attaches. `divergence_decode.py agents/megastarmie --archetype Cinderace --player keidroid --context MAIN`.
4. **Watch CINDERACE / Mega Starmie ex (= our megastarmie clone, the keidroid line) + Chandelure + Mega Froslass ex** — Mega Starmie/Cinderace is the rising apex (beats both Trevenant AND Dragapult). If WE don't run it, it's our hardest counter. Pull its share daily.
5. **Alakazam piloting headroom**: archetype is 55% top-tier WR but our pilot scored only 674. No official Alakazam sample exists, so improve via divergence mining vs top Alakazam pilots (Elo≥1150). Hedge.
6. **When score-fixing any agent, NEVER blindly increase scores** — verify EVERY change against the divergence data. The EVOLVE 50000 mistake cost us 2 submissions to correct. Lower the over-prioritized card's score instead (e.g., Fez 53000→35000).

### Lessons learned 6-22 (megastarmie build — divergence mining a top HUMAN pilot from scratch)
- **A from-scratch `*Policy` CAN reach top-tier IF you divergence-mine the #1 pilot, not just intuit scores.** megastarmie went 40→66% vs our Dragapult from 6 *measured* fixes. The earlier "from-scratch loses 13-1 to the sample" lesson holds only for *un-mined* policies — the divergence loop is what closes the gap. When no official sample exists, **clone the #1 player's deck and `divergence_decode --player <name>`** their games.
- **`IS_FIRST` (go first/second) is DECK-SPECIFIC — always read it from the pilot data, never assume.** Dragapult goes second; Mega Starmie goes first (keidroid 27/27). Same for MULLIGAN.
- **Spread/snipe damage (`DAMAGE`/`DAMAGE_COUNTER`) should target the opponent's LOW-HP development pieces** (draw engines, evolution bases like Dunsparce/Phantump/Abra) to deny setup — NOT a high-HP wall you can't KO (we dumped 78 hits into a 150HP Snorlax). Rank targets by low current HP + a KO bonus, not by raw prize value.
- **Before optimizing energy attachment, identify the deck's ACTUAL win attack — it's often the CHEAP workhorse, not the flashy big attack.** Mega Starmie wins with Jetting Blow (1 Water), not Nebula Beam (CCC). Concentrating Water toward the 3-cost attack was wrong; the big attack is enabled on-demand by Ignition Energy. **Watch for end-of-turn-discard energies (Ignition): they are one-shot burst enablers for the turn you attack, never build-up — and never on a benched mon.**
- **A `DISCARD` scorer must hard-protect the win-con line** (we were pitching Mega Starmie ex / its evolve-enabler Salvatore to Ultra Ball). Prefer the most plentiful, cheapest resource (excess basic energy).
- **Sleep/special-conditions are engine-automatic**: the wake-up coin flip resolves inside the compiled cg engine (`manual_coin` off) — the agent is never asked to flip and only ever sees legal options, so robust scaffolding (`_legal_fallback`, 0-fallback) is all that's needed; no special handling.

### Lessons learned 6-23 (the over-fill recurrence → systematic prevention)
- **Root cause of "a bug fixed in one deck reappears in the next": the scaffolding was COPY-PASTED per `main.py`, so generic logic (e.g. energy discipline) was NOT inherited and a new deck could silently omit/break it.** I had even re-implemented over-fill prevention as a HARDCODED per-card `_fuel_goal` in megastarmie instead of the generic attack-cost rule — fragile by design.
- **Fix = a shared `BasePolicy` (ABC) at `agents/_base/policy_base.py`**: generic energy discipline (`should_fuel`/`can_attack`, derived from each attack's real cost — over-fill impossible by construction) + dispatch + robust `agent()` wrapper are INHERITED; deck specifics are `@abstractmethod`s (incl. `go_first()`) so Python refuses to load a subclass that forgets one. The Kaggle loader appends the agent dir to `sys.path`, so a bundled sibling `policy_base.py` imports cleanly (verified by extracting the tarball and loading in a clean dir). **New decks subclass it; do NOT hardcode energy goals — let `should_fuel` derive them.**
- **Plus a behavioral guard: `tools/check_agent.py`** runs ANY agent and asserts the invariants (no over-fill, no fallbacks/crashes, legal selections) — catches the bug class even in bespoke/legacy agents. Make it evolution-line-aware so pre-loading energy on a Basic that carries to a costlier evolution is NOT a false positive. **Run it after any agent change.**
- **cabt A/B at 40 games is NOISY (±~10pts)** — megastarmie read 66/68/85 at 40g but 56/56/84 at 80g (same agent). Never conclude regression-vs-improvement from a 40-game delta; use ≥80, and lean on the highest-signal matchup (here Trevenant, which was unchanged → confirmed the refactor was behavior-preserving).
- **Legacy agents (alakazam/trevenant/dragapult) are NOT yet on BasePolicy** — they pass `check_agent` today, but migrating them is the way to fully close this gap. Do it opportunistically when next touching one.
