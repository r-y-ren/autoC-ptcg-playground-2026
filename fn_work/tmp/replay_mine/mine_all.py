"""93 局官方回放规则实证挖掘器（2026-10-06）。
输出 fn_work/tmp/replay_mine/mined.json：每 match 的 game 分段 + 全量事件抽取。
数据源：references/episodes/episode-*-replay.json 的 steps[0][0].visualize 命名日志流。
"""
import json, glob, os, collections, statistics

ROOT = '/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS = {c['cardId']: c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
ATKS = {a['attackId']: a for a in json.load(open(f'{ROOT}/references/engine/cabt-attacks.json'))}

def card(cid):
    return CARDS.get(cid) or {}

def cflag(cid):
    c = card(cid)
    return ('megaEx' if c.get('megaEx') else 'ex' if c.get('ex') else 'normal')

def parse_match(path):
    d = json.load(open(path))
    steps = d['steps']
    viz = steps[0][0].get('visualize') or []
    eid = (d.get('info') or {}).get('EpisodeId')
    rewards = d.get('rewards') or []
    mwin = 0 if (rewards[0] or 0) > (rewards[1] or 0) else 1
    out = {
        'file': os.path.basename(path), 'eid': eid,
        'teams': (d.get('info') or {}).get('TeamNames'),
        'rewards': rewards, 'match_winner': mwin,
        'n_steps': len(steps), 'n_frames': len(viz),
        'games': [],
    }
    # ---- observation 侧：决策归属 + 数值 context 谱（conv 同法）----
    obs_records = []   # (step, active_by_status, active_by_action, ctx_numeric, my_prize_len)
    for i, pair in enumerate(steps):
        if i == 0:
            continue
        a0 = bool(pair[0].get('action')); a1 = bool(pair[1].get('action'))
        act_by_action = 0 if a0 else (1 if a1 else None)
        act_by_status = 0 if pair[0].get('status') == 'ACTIVE' else 1
        st = pair[act_by_status]
        sel = (st.get('observation') or {}).get('select') or {}
        cur = (st.get('observation') or {}).get('current') or {}
        players = cur.get('players') or []
        my = players[act_by_status] if len(players) > act_by_status else {}
        obs_records.append({
            'step': i, 'active_status': act_by_status, 'active_action': act_by_action,
            'ctx': sel.get('context'), 'prize': len(my.get('prize') or []),
        })
    out['obs_records'] = obs_records

    # ---- viz 侧：game 分段（Result 日志为界）----
    segs = []
    start = 0
    for i, fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type') == 'Result':
                segs.append((start, i, {'reason': lg.get('reason'), 'winner': lg.get('result')}))
                start = i + 1
    if start < len(viz):
        segs.append((start, len(viz) - 1, None))
    out['n_games'] = len(segs)

    for gi, (f0, f1, res) in enumerate(segs):
        g = {
            'idx': gi, 'f0': f0, 'f1': f1, 'n_frames': f1 - f0 + 1,
            'reason': (res or {}).get('reason'), 'winner': (res or {}).get('winner'),
            'incomplete': res is None,
        }
        fp = None
        decisions = [0, 0]
        turns = []
        cur_turn = None
        prize_jumps = []   # (frame, player, jump, ko_cards[])
        ko_queue = []
        status_events = collections.Counter()   # (player,status) inflicted transitions
        status_turns = collections.Counter()    # (player,status) turn-exposure
        hp_nonattack = []   # (frame, player, value, putDamageCounter)
        dmg_samples = []    # 攻击伤害样本
        pending_atk = None
        coin_turnstart = 0
        last_prize = [None, None]
        prev_status = [{}, {}]
        tac_max = [0, 0]   # per current turn
        attach_energy_per_turn = []
        supporter_per_turn = []
        switch_per_turn = []
        attach_tool_per_turn = []
        stadium_per_turn = []
        evolve_per_turn = []
        attack_per_turn = []
        first_turn_attacks = 0
        first_turn_player = None
        second_first_turn_attacks = 0
        turn_idx = -1
        for i in range(f0, f1 + 1):
            fr = viz[i]
            cur = fr.get('current') or {}
            act = fr.get('action') or []
            for p in (0, 1):
                a = act[p] if p < len(act) else None
                if a:
                    decisions[p] += 1
            if fp is None and cur.get('firstPlayer') not in (None, -1):
                fp = cur.get('firstPlayer')
            pls = cur.get('players') or []
            for p in (0, 1):
                if p >= len(pls):
                    continue
                pl = pls[p]
                # prize jump
                npr = len(pl.get('prize') or [])
                if last_prize[p] is not None and npr < last_prize[p]:
                    jump = last_prize[p] - npr
                    kos = ko_queue[:]
                    ko_queue = []
                    prize_jumps.append({'frame': i, 'player': p, 'jump': jump,
                                        'ko_cards': [{'cardId': k, 'flag': cflag(k), 'name': card(k).get('name')} for k in kos]})
                if npr > 0 or last_prize[p] is None:
                    last_prize[p] = npr
                # status flags
                for s in ('poisoned', 'burned', 'asleep', 'paralyzed', 'confused'):
                    v = bool(pl.get(s))
                    pv = prev_status[p].get(s)
                    if v and pv is False:
                        status_events[(p, s)] += 1
                    prev_status[p][s] = v
            # logs
            logs = fr.get('logs') or []
            frame_pending = None
            atk_no_hp = 0
            for lg in logs:
                t = lg.get('type')
                if t == 'TurnStart':
                    if cur_turn is not None:
                        turns.append(cur_turn)
                    turn_idx += 1
                    p = lg.get('playerIndex')
                    cur_turn = {'idx': turn_idx, 'player': p, 'frame': i,
                                'attach_energy': 0, 'attach_tool': 0, 'supporter': 0, 'item': 0,
                                'stadium': 0, 'switch': 0, 'evolve': 0, 'attack': 0, 'coin': 0,
                                'tac_max': 0, 'statuses': set()}
                    if first_turn_player is None:
                        first_turn_player = p
                elif t == 'TurnEnd':
                    if cur_turn is not None:
                        cur_turn['frame_end'] = i
                        turns.append(cur_turn)
                        cur_turn = None
                elif t == 'Attach':
                    ct = card(lg.get('cardId')).get('cardType')
                    if cur_turn:
                        if ct in (5, 6):
                            cur_turn['attach_energy'] += 1
                        elif ct == 2:
                            cur_turn['attach_tool'] += 1
                elif t == 'Play':
                    ct = card(lg.get('cardId')).get('cardType')
                    if cur_turn:
                        if ct == 3:
                            cur_turn['supporter'] += 1
                        elif ct == 1:
                            cur_turn['item'] += 1
                        elif ct == 4:
                            cur_turn['stadium'] += 1
                elif t == 'Switch':
                    if cur_turn:
                        cur_turn['switch'] += 1
                elif t == 'Evolve':
                    if cur_turn:
                        cur_turn['evolve'] += 1
                elif t == 'Attack':
                    if cur_turn:
                        cur_turn['attack'] += 1
                    if cur_turn and cur_turn['idx'] == 0:
                        first_turn_attacks += 1
                    frame_pending = {'frame': i, 'attacker': lg.get('cardId'), 'attackId': lg.get('attackId'),
                                     'player': lg.get('playerIndex')}
                    if pending_atk is not None:
                        atk_no_hp += 1
                    pending_atk = frame_pending
                elif t == 'Coin':
                    if cur_turn:
                        cur_turn['coin'] += 1
                elif t == 'HpChange':
                    v = lg.get('value')
                    if frame_pending and v is not None and v < 0:
                        tgt = lg.get('cardId')
                        A = card(frame_pending['attacker']); D = card(tgt); a = ATKS.get(frame_pending['attackId']) or {}
                        dmg_samples.append({
                            'frame': i, 'attacker': frame_pending['attacker'], 'attackId': frame_pending['attackId'],
                            'atk_player': frame_pending['player'], 'tgt_player': lg.get('playerIndex'),
                            'atk_name': a.get('name'), 'base': a.get('damage'), 'text': (a.get('text') or '').strip(),
                            'a_type': A.get('energyType'), 'a_name': A.get('name'),
                            'target': tgt, 'd_name': D.get('name'),
                            'weak': D.get('weakness'), 'res': D.get('resistance'),
                            'actual': -v, 'target_hp': D.get('hp'),
                        })
                    elif v is not None and v < 0:
                        hp_nonattack.append({'frame': i, 'player': lg.get('playerIndex'), 'value': v,
                                             'putDamageCounter': lg.get('putDamageCounter'), 'cardId': lg.get('cardId')})
                    # 正向/治疗不计
                elif t == 'MoveCard':
                    ct = card(lg.get('cardId')).get('cardType')
                    if lg.get('toArea') == 3 and lg.get('fromArea') in (4, 5) and ct == 0:
                        ko_queue.append(lg.get('cardId'))
            if pending_atk is not None and frame_pending is None:
                pending_atk = None  # 攻击跨帧出伤：放弃配对（计数见 atk_unmatched）
            if cur_turn is not None:
                cur_turn['tac_max'] = max(cur_turn['tac_max'], cur.get('turnActionCount') or 0)
                for s in ('poisoned', 'burned', 'asleep', 'paralyzed', 'confused'):
                    for p in (0, 1):
                        if p < len(pls) and pls[p].get(s):
                            cur_turn['statuses'].add((p, s))
        if cur_turn is not None:
            turns.append(cur_turn)
        for t in turns:
            st = t.pop('statuses', set())
            for (p, s) in st:
                status_turns[(p, s)] += 1
        atk_total = sum(t.get('attack', 0) for t in turns)
        g['n_attacks'] = atk_total
        g['firstPlayer'] = fp
        g['first_turn_player'] = first_turn_player
        g['first_turn_attacks'] = first_turn_attacks
        g['decisions'] = decisions
        g['turns'] = turns
        g['n_turns'] = len(turns)
        g['prize_jumps'] = prize_jumps
        g['status_events'] = {f'{p}:{s}': v for (p, s), v in status_events.items()}
        g['status_turns'] = {f'{p}:{s}': v for (p, s), v in status_turns.items()}
        g['hp_nonattack'] = hp_nonattack
        g['atk_unmatched'] = atk_total - len([d for d in dmg_samples if d.get('actual')])
        g['dmg_samples'] = dmg_samples
        out['games'].append(g)
    return out

def main():
    files = sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json'))
    all_matches = []
    for f in files:
        all_matches.append(parse_match(f))
    json.dump(all_matches, open(f'{ROOT}/fn_work/tmp/replay_mine/mined.json', 'w'), ensure_ascii=False)
    print('matches:', len(all_matches))
    print('games:', sum(m['n_games'] for m in all_matches))
    print('game segs (incl incomplete):', sum(len(m['games']) for m in all_matches))

if __name__ == '__main__':
    main()
