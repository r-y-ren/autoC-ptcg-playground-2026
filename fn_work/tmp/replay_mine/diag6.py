import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
pick_turn=collections.defaultdict(collections.Counter)
malformed=0; total=0
energy_turn=collections.Counter(); tool_turn=collections.Counter()
name_map=collections.defaultdict(collections.Counter)
dec_game=[]
retreat_examples=[]
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    steps=d['steps']; viz=d['steps'][0][0]['visualize']
    segs=[]; start=0
    for i,fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type')=='Result': segs.append((start,i)); start=i+1
    if start<len(viz): segs.append((start,len(viz)-1))
    for gi,(f0,f1) in enumerate(segs):
        turn_idx=-1; cur=None
        per_turn=collections.defaultdict(collections.Counter)
        dec=[0,0]
        prev_sel=None
        for i in range(f0,f1+1):
            fr=viz[i]
            for lg in (fr.get('logs') or []):
                if lg['type']=='TurnStart':
                    turn_idx+=1; cur=lg.get('playerIndex')
            selv=fr.get('selected'); act=fr.get('action') or []
            if selv and prev_sel is not None:
                total+=1
                who=None
                for j in (0,1):
                    a=act[j] if j<len(act) else None
                    if a and list(a)==list(selv): who=j
                if who is not None: dec[who]+=1
                mx=prev_sel.get('maxCount') or 1
                picks=[x for x in selv if isinstance(x,int)] if isinstance(selv,list) else [selv]
                if len(picks)>mx:
                    malformed+=1
                opts=prev_sel.get('option') or []
                ctx=prev_sel.get('context')
                for idx in picks:
                    if idx>=len(opts): continue
                    ot=opts[idx].get('type')
                    if ctx=='Main':
                        per_turn[(turn_idx,cur)][ot]+=1
                        if ot=='Attach':
                            o=opts[idx]; hidx=o.get('index')
                            pid=o.get('playerIndex')
                            pls=(fr.get('current') or {}).get('players') or []
                            pl=pls[pid] if pid is not None and pid<len(pls) else (pls[cur] if cur is not None and cur<len(pls) else {})
                            hand=pl.get('hand') or []
                            cid=(hand[hidx].get('id') if isinstance(hidx,int) and 0<=hidx<len(hand) else None)
                            ct=CARDS.get(cid,{}).get('cardType')
                            if ct in (5,6): energy_turn[(turn_idx,cur)]+=1
                            elif ct==2: tool_turn[(turn_idx,cur)]+=1
                            else: energy_turn[(turn_idx,cur,'unk')]+=1
                    if ot=='Retreat' and len(retreat_examples)<8:
                        retreat_examples.append((eid,gi,turn_idx,cur,i))
                # name map: answered select named (prev_sel) vs numeric obs ctx at step i+? 
                si=i
                if si<len(steps) and who is not None:
                    s2=(steps[si][who].get('observation') or {}).get('select') or {}
                    if s2.get('context') is not None:
                        name_map[s2.get('context')][prev_sel.get('context')]+=1
            prev_sel=fr.get('select')
        dec_game.append(dec)
        for k,c in per_turn.items():
            for typ,n in c.items():
                pick_turn[typ][n]+=1
print('consumed decisions:',total,'multi-pick(>maxCount):',malformed,f'({100*malformed/max(1,total):.2f}%)')
print('每回合动作 pick 分布（select[i-1]×selected[i] 正确配对）:')
for typ in ('Attach','Retreat','Play','Evolve','Attack','Ability','End'):
    print('  ',typ,dict(sorted(pick_turn[typ].items())))
et=collections.Counter(v for k,v in energy_turn.items() if len(k)==2)
tt=collections.Counter(v for k,v in tool_turn.items() if len(k)==2)
print('energy-attach picks/turn:',dict(sorted(et.items())))
print('tool-attach picks/turn:',dict(sorted(tt.items())))
print('unclassified attach picks:',sum(v for k,v in energy_turn.items() if len(k)==3))
print()
print('== 数值 ctx -> 名称（步骤观测 select × 应答）==')
for c in sorted(name_map):
    tot=sum(name_map[c].values())
    print(f'  ctx {c}: n={tot} ->',name_map[c].most_common(3))
