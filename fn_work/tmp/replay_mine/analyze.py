"""93 局回放挖掘分析（对 mined.json 出全量统计表）"""
import json, glob, collections, statistics, math
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
M=json.load(open(f'{ROOT}/fn_work/tmp/replay_mine/mined.json'))
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
ATKS={a['attackId']:a for a in json.load(open(f'{ROOT}/references/engine/cabt-attacks.json'))}
conv_ids={f.split('/')[-1].split('.')[0] for f in glob.glob(f'{ROOT}/references/episodes/conv/*.conv.json')}

def L(*a): print(*a)

# ============ 1. 胜负结构 ============
L('#### 1. 胜负结构')
reasons=collections.Counter(); winners=collections.Counter()
glen=[]; fp_win=0; fp_tot=0; fp_firstgame=collections.Counter()
gpm=collections.Counter()
turns_per_game=[]
for m in M:
    gpm[len(m['games'])]+=1
    for g in m['games']:
        reasons[g['reason']]+=1
        winners[g['winner']]+=1
        glen.append(g['n_frames'])
        turns_per_game.append(g['n_turns'])
        if g['firstPlayer'] is not None and g['winner'] is not None:
            fp_tot+=1
            if g['winner']==g['firstPlayer']: fp_win+=1
    fg=m['games'][0]
    fp_firstgame[(fg['firstPlayer'], m['match_winner'])]+=1
L('games per match:',dict(sorted(gpm.items())),'| total games:',sum(reasons.values()))
L('reason dist:',dict(sorted(reasons.items())))
L('game winner dist:',dict(winners))
L('game frames: min',min(glen),'p25',statistics.quantiles(glen,n=4)[0],'median',statistics.median(glen),'mean',round(statistics.mean(glen),1),'p75',statistics.quantiles(glen,n=4)[2],'max',max(glen))
L('episode steps: min',min(m['n_steps'] for m in M),'median',statistics.median([m['n_steps'] for m in M]),'max',max(m['n_steps'] for m in M))
L('turns per game: min',min(turns_per_game),'median',statistics.median(turns_per_game),'mean',round(statistics.mean(turns_per_game),1),'max',max(turns_per_game))
L(f'first-player game win rate: {fp_win}/{fp_tot} = {fp_win/fp_tot:.3f}')
L('first-game firstPlayer x match winner:',dict(fp_firstgame))
# reason x winner
rw=collections.Counter((g['reason'],g['winner']) for g in (x for m in M for x in m['games']))
L('reason x winner:',dict(sorted(rw.items())))
# who wins by reason: relative to firstPlayer
rrel=collections.Counter()
for m in M:
    for g in m['games']:
        rrel[(g['reason'],'first' if g['winner']==g['firstPlayer'] else 'second')]+=1
L('reason x winner-is-first:',dict(sorted(rrel.items())))

# ============ 2. 回 turn 结构 ============
L(); L('#### 2. 回合结构')
tac=collections.Counter(); evsum=collections.Counter()
ae=collections.Counter(); sup=collections.Counter(); sw=collections.Counter()
stadium=collections.Counter(); evol=collections.Counter(); tool=collections.Counter()
over_ae=over_sup=over_sw=0
first_att=0; first_turn_games=0; fp_is_first_turn=0
second_first_att=0
tac_list=[]
turns_all=[]
for m in M:
    for g in m['games']:
        if g['first_turn_player'] is not None:
            first_turn_games+=1
            if g['first_turn_player']==g['firstPlayer']: fp_is_first_turn+=1
        if g['first_turn_attacks']: first_att+=g['first_turn_attacks']
        ts=g['turns']
        for t in ts:
            turns_all.append(t)
            tac[t['tac_max']]+=1
            tac_list.append(t['tac_max'])
            es=t['attach_energy']+t['attach_tool']+t['supporter']+t['item']+t['stadium']+t['switch']+t['evolve']+t['attack']
            evsum[es]+=1
            ae[t['attach_energy']]+=1; sup[t['supporter']]+=1; sw[t['switch']]+=1
            stadium[t['stadium']]+=1; evol[t['evolve']]+=1; tool[t['attach_tool']]+=1
            if t['attach_energy']>1: over_ae+=1
            if t['supporter']>1: over_sup+=1
            if t['switch']>1: over_sw+=1
        # second player's first turn = turn idx 1
        if len(ts)>1 and ts[1]['attack']>0: second_first_att+=ts[1]['attack']
L('total turns:',len(turns_all))
L('turnActionCount dist:',dict(sorted(tac.items())))
L('event-sum/turn dist:',dict(sorted(evsum.items())))
L('energy attach/turn:',dict(sorted(ae.items())),'| turns with >1:',over_ae)
L('supporter/turn:',dict(sorted(sup.items())),'| turns with >1:',over_sup)
L('switch/turn:',dict(sorted(sw.items())),'| turns with >1:',over_sw)
L('tool attach/turn:',dict(sorted(tool.items())))
L('stadium/turn:',dict(sorted(stadium.items())))
L('evolve/turn:',dict(sorted(evol.items())))
L(f'games where first TurnStart player == firstPlayer: {fp_is_first_turn}/{first_turn_games}')
L('attacks in first turn (turn idx0):',first_att)
L('attacks in second player first turn (turn idx1):',second_first_att)

# ============ 3. 奖赏 ============
L(); L('#### 3. 奖赏实证')
jd=collections.Counter(); jk=collections.Counter(); flag_prize=collections.Counter()
multi=0
for m in M:
    for g in m['games']:
        for j in g['prize_jumps']:
            jd[j['jump']]+=1
            flags=tuple(sorted(k['flag'] for k in j['ko_cards']))
            jk[(j['jump'],flags,len(j['ko_cards']))]+=1
            if len(j['ko_cards'])>1: multi+=1
            for k in j['ko_cards']:
                flag_prize[k['flag']]+=1
L('prize jump dist:',dict(sorted(jd.items())))
L('jump x (ko flags, n_ko):')
for k,v in sorted(jk.items()): L('   ',k,v)
L('KO cards by flag:',dict(flag_prize))
L('jumps with >1 KO card:',multi)
L('total prize jumps:',sum(jd.values()))

# ============ 4. 状态条件 ============
L(); L('#### 4. 状态条件')
se=collections.Counter(); ste=collections.Counter()
for m in M:
    for g in m['games']:
        for k,v in g['status_events'].items(): se[k]+=v
        for k,v in g['status_turns'].items(): ste[k]+=v
L('inflicted events (player:status):',dict(se))
L('turn exposure (player:status):',dict(ste))
hpn=collections.Counter(); games_hpn=0
for m in M:
    for g in m['games']:
        if g['hp_nonattack']: games_hpn+=1
        for h in g['hp_nonattack']: hpn[(h['value'],h['putDamageCounter'])]+=1
L('non-attack HpChange (value,putDamageCounter):',dict(hpn),'games affected:',games_hpn)
selfhit=0; samples_self=[]
for m in M:
    for g in m['games']:
        for d in g['dmg_samples']:
            if d.get('atk_player')==d.get('tgt_player'):
                selfhit+=1
                if len(samples_self)<5: samples_self.append((m['eid'],d['atk_name'],d['actual'],d.get('text','')[:40]))
L('HpChange on attacker own side (confusion self-hit or recoil):',selfhit, samples_self)

# ============ 6. 伤害实证 ============
L(); L('#### 6. 伤害实证')
plain=[]; allpairs=0
for m in M:
    for g in m['games']:
        for d in g['dmg_samples']:
            allpairs+=1
            if (d['base'] or 0)>0 and not d['text']:
                plain.append((m,d,g,d))
L('attack->hpchange pairs:',allpairs,'| plain numeric attacks (base>0, empty text):',len(plain))
ok=bad=0; mism=[]; wok=wbad=rok=rbad=0; rows_all=[]
for m,g,_,d in plain:
    A=CARDS.get(d['attacker']) or {}; D=CARDS.get(d['target']) or {}
    base=d['base']; a_type=d['a_type']
    w=(D.get('weakness') is not None and D.get('weakness')==a_type)
    r=(D.get('resistance') is not None and D.get('resistance')==a_type)
    exp=base*(2 if w else 1)-(30 if r else 0)
    exp=max(0,exp)
    tag=('W' if w else '')+('R' if r else '')
    hit=(exp==d['actual'])
    rows_all.append({'eid':m['eid'],'atk':d['atk_name'],'base':base,'a_type':a_type,'def':d['d_name'],
                     'weak':D.get('weakness'),'res':D.get('resistance'),'tag':tag,'exp':exp,'act':d['actual'],'ok':hit})
    if hit: ok+=1
    else: bad+=1; mism.append(rows_all[-1])
    if w:
        if hit: wok+=1
        else: wbad+=1
    if r:
        if hit: rok+=1
        else: rbad+=1
L(f'plain-attack formula check: match={ok} mismatch={bad} rate={ok/(ok+bad):.3f}')
L(f'  weakness cases: match={wok} mismatch={wbad} | resistance cases: match={rok} mismatch={rbad}')
L('mismatch sample (up to 12):')
for r in mism[:12]: L('   ',r)
# 30-sample: deterministic spread + ensure W/R coverage
import random
random.seed(20261006)
w_rows=[r for r in rows_all if 'W' in r['tag']]
r_rows=[r for r in rows_all if 'R' in r['tag']]
plain_rows=[r for r in rows_all if not r['tag']]
sample=[]
sample+=w_rows[:8]; sample+=r_rows[:8]
rest=[r for r in rows_all if r not in sample]
random.shuffle(rest)
sample+=rest[:30-len(sample)]
sample=sample[:30]
L(f'--- 30 例抽查表（W {sum(1 for s in sample if "W" in s["tag"])} 例 / R {sum(1 for s in sample if "R" in s["tag"])} 例 / 无标记 {sum(1 for s in sample if not s["tag"])} 例）---')
for r in sample: L('   ',r)
L('sample match rate:',sum(1 for s in sample if s['ok']),'/',len(sample))

# ============ 7. 决策量 ============
L(); L('#### 7. 决策量')
dec=[d for m in M for g in m['games'] for d in g['decisions']]
L('per-player per-game decisions: n',len(dec),'min',min(dec),'p10',statistics.quantiles(dec,n=10)[0],
  'median',statistics.median(dec),'mean',round(statistics.mean(dec),1),'p90',statistics.quantiles(dec,n=10)[8],'max',max(dec))
buckets=collections.Counter()
for d in dec:
    if d<10: buckets['<10']+=1
    elif d<20: buckets['10-19']+=1
    elif d<30: buckets['20-29']+=1
    elif d<=42: buckets['30-42']+=1
    elif d<=60: buckets['43-60']+=1
    else: buckets['>60']+=1
L('decision buckets:',dict(buckets))
L('decisions game-sum pair (both sides): median',statistics.median([sum(g['decisions']) for m in M for g in m['games']]))
low=[(m['eid'],g['idx'],g['decisions'],g['n_turns'],g['reason']) for m in M for g in m['games'] if min(g['decisions'])<10]
L('games with a side <10 decisions:',len(low)); L('  ',low[:20])
# match-level totals
mt=[(m['eid'],sum(g['decisions'][0] for g in m['games']),sum(g['decisions'][1] for g in m['games'])) for m in M]
L('match-level decisions per side: median',statistics.median([x[1] for x in mt]),statistics.median([x[2] for x in mt]))
