import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
def flag(cid):
    c=CARDS.get(cid,{}); return 'megaEx' if c.get('megaEx') else 'ex' if c.get('ex') else 'normal'

malformed=0; decisions_total=0
pick_turn=collections.defaultdict(collections.Counter)   # action type -> per-turn pick count dist
energy_attach_turn=collections.Counter()
tool_attach_turn=collections.Counter()
name_map=collections.defaultdict(collections.Counter)
dec_per_game=[]
end_actions=0
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    steps=d['steps']; viz=steps[0][0]['visualize']
    segs=[]; start=0
    for i,fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type')=='Result': segs.append((start,i)); start=i+1
    if start<len(viz): segs.append((start,len(viz)-1))
    for gi,(f0,f1) in enumerate(segs):
        turn_idx=-1; cur=None
        per_turn=collections.defaultdict(lambda: collections.Counter())
        dec=[0,0]
        for i in range(f0,f1+1):
            fr=viz[i]
            for lg in (fr.get('logs') or []):
                if lg['type']=='TurnStart':
                    turn_idx+=1; cur=lg.get('playerIndex')
            sel=fr.get('select') or {}
            selv=fr.get('selected')
            act=fr.get('action') or []
            if not selv: continue
            decisions_total+=1
            # acting player = whose action equals selected
            who=None
            for j in (0,1):
                a=act[j] if j<len(act) else None
                if a and list(a)==list(selv): who=j
            if who is not None: dec[who]+=1
            mx=sel.get('maxCount') or 1
            picks=[x for x in selv if isinstance(x,int)] if isinstance(selv,list) else [selv]
            if len(picks)>mx: malformed+=1; picks=picks[:1]
            ctx=sel.get('context')
            opts=sel.get('option') or []
            for idx in picks:
                if idx>=len(opts): continue
                ot=opts[idx].get('type')
                if ctx=='Main':
                    per_turn[(turn_idx,cur)][ot]+=1
                    if ot=='Attach':
                        o=opts[idx]
                        hidx=o.get('index')
                        pls=(fr.get('current') or {}).get('players') or []
                        hand=(pls[o.get('playerIndex')] if o.get('playerIndex') is not None and o.get('playerIndex')<len(pls) else (pls[cur] if cur is not None and cur<len(pls) else {})).get('hand') or []
                        cid=(hand[hidx].get('id') if isinstance(hidx,int) and hidx<len(hand) else None)
                        ct=CARDS.get(cid,{}).get('cardType')
                        if ct in (5,6): energy_attach_turn[(turn_idx,cur)]+=1
                        elif ct==2: tool_attach_turn[(turn_idx,cur)]+=1
                        else: energy_attach_turn[(turn_idx,cur,'unk')]+=1
            # name map: viz[i] <-> steps[i+1]
            si=i+1
            if si<len(steps) and who is not None:
                s2=(steps[si][who].get('observation') or {}).get('select') or {}
                if s2.get('context') is not None and ctx:
                    name_map[s2.get('context')][ctx]+=1
        dec_per_game.append(dec)
        for k,c in per_turn.items():
            for typ,n in c.items():
                pick_turn[typ][n]+=1
print('consumed decisions:',decisions_total,'malformed multi-pick:',malformed,f'({100*malformed/max(1,decisions_total):.2f}%)')
print('每回合动作类型 pick 分布（已剔畸形多选,按 turn 计数）:')
for typ in ('Attach','Retreat','Play','Evolve','Attack','Ability','End'):
    print('  ',typ,dict(sorted(pick_turn[typ].items())))
print('每回合“能量附着”pick（按卡类型识别）:',dict(sorted(collections.Counter(energy_attach_turn).items()))[:0] or '')
et=collections.Counter(v for k,v in energy_attach_turn.items() if len(k)==2)
tt=collections.Counter(v for k,v in tool_attach_turn.items() if len(k)==2)
print('  energy-attach picks/turn dist:',dict(sorted(et.items())))
print('  tool-attach picks/turn dist:',dict(sorted(tt.items())))
print('  unclassified attach:',sum(v for k,v in energy_attach_turn.items() if len(k)==3))
print()
print('== 数值 ctx -> 名称（offset+1 消耗决策配对）==')
for c in sorted(name_map):
    tot=sum(name_map[c].values())
    print(f'  ctx {c}: n={tot} ->',name_map[c].most_common(3))
