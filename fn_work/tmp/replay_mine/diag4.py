import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
ATKS={a['attackId']:a for a in json.load(open(f'{ROOT}/references/engine/cabt-attacks.json'))}
def flag(cid):
    c=CARDS.get(cid,{}); return 'megaEx' if c.get('megaEx') else 'ex' if c.get('ex') else 'normal'

prize_map=collections.defaultdict(collections.Counter)   # flag -> attributed take count
cluster_shapes=collections.Counter()
consumed=collections.Counter()          # Main 消耗动作类型
consumed_turn=collections.defaultdict(collections.Counter)  # (game key, turn idx, player) -> action type
retreat_flag_pairs=collections.Counter()
r_pairs=[]; w_pairs=[]
name_map=collections.defaultdict(collections.Counter)
total_takes=0; attributed=0

for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    steps=d['steps']; viz=steps[0][0]['visualize']
    aligned = len(viz)==len(steps)
    segs=[]; start=0
    for i,fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type')=='Result': segs.append((start,i)); start=i+1
    if start<len(viz): segs.append((start,len(viz)-1))
    for gi,(f0,f1) in enumerate(segs):
        # 事件账本
        open_kos={0:[],1:[]}   # owner -> list of dict(card, acc)
        turn_idx=-1; cur_player=None
        for i in range(f0,f1+1):
            fr=viz[i]
            logs=fr.get('logs') or []
            for lg in logs:
                t=lg.get('type')
                if t=='TurnStart':
                    turn_idx+=1; cur_player=lg.get('playerIndex')
            # consumed Main actions + name map
            sel=fr.get('select') or {}
            act=fr.get('action') or []
            selv=fr.get('selected')
            if selv and sel.get('context')=='Main':
                opts=sel.get('option') or []
                for idx in (selv if isinstance(selv,list) else [selv]):
                    if isinstance(idx,int) and idx<len(opts):
                        ot=opts[idx].get('type')
                        consumed[ot]+=1
                        consumed_turn[(eid,gi,turn_idx,cur_player)][ot]+=1
            # consumed-decision name map (aligned files)
            if aligned and selv:
                for j in (0,1):
                    a=act[j] if j<len(act) else None
                    if a and list(a)==list(selv):
                        s2=(steps[i][j].get('observation') or {}).get('select') or {}
                        if s2.get('context') is not None and sel.get('context'):
                            name_map[s2.get('context')][sel.get('context')]+=1
            # prize ledger
            kos=[lg for lg in logs if lg['type']=='MoveCard' and lg.get('toArea')==3 and lg.get('fromArea') in (4,5) and CARDS.get(lg.get('cardId'),{}).get('cardType')==0]
            takes=[lg for lg in logs if lg['type']=='MoveCard' and lg.get('fromArea')==6 and lg.get('toArea')==2]
            for lg in kos:
                open_kos[lg.get('playerIndex')].append({'card':lg.get('cardId'),'acc':0,'frame':i})
            for lg in takes:
                p=lg.get('playerIndex'); total_takes+=1
                q=1-p
                cands=[k for k in open_kos[q] if i-3<=k['frame']<=i and k['acc']<3]
                if len(cands)==1:
                    cands[0]['acc']+=1; attributed+=1
                elif len(cands)>1:
                    # 多 KO 歧义：记形状
                    cluster_shapes[(len(cands),tuple(sorted(flag(k['card']) for k in cands)),)]+=1
                    cands[0]['acc']+=1; attributed+=1
                else:
                    cluster_shapes[('no-ko',)]+=1
            # R/W 案例（全攻击对，含效果攻击）
            pend=None
            for lg in logs:
                if lg['type']=='Attack': pend=lg
                elif lg['type']=='HpChange' and pend and (lg.get('value') or 0)<0:
                    A=CARDS.get(pend.get('cardId'),{}); D=CARDS.get(lg.get('cardId'),{}); a=ATKS.get(pend.get('attackId'),{})
                    if (a.get('damage') or 0)>0:
                        if D.get('resistance')==A.get('energyType'):
                            r_pairs.append((eid,i,a.get('name'),a.get('damage'),D.get('name'),-(lg.get('value')),
                                            'text' if (a.get('text') or '').strip() else 'plain'))
                        if D.get('weakness')==A.get('energyType'):
                            w_pairs.append((eid,i,a.get('name'),a.get('damage'),D.get('name'),-(lg.get('value')),
                                            'text' if (a.get('text') or '').strip() else 'plain'))
                    pend=None
        # 收尾：结算 open kos 的奖赏值
        for q in (0,1):
            for k in open_kos[q]:
                if k['acc']>0:
                    prize_map[flag(k['card'])][k['acc']]+=1
print('== 奖赏值 FIFO 账本 ==')
print('takes total',total_takes,'attributed',attributed)
print('cluster shapes:',dict(cluster_shapes))
print('flag -> attributed prize count:')
for k,v in prize_map.items(): print('  ',k,dict(sorted(v.items())))
print()
print('== Main 消耗动作类型频次（实际执行）==')
for k,v in consumed.most_common(): print('  ',k,v)
# per-turn limits
lim=collections.defaultdict(collections.Counter)
for key,c in consumed_turn.items():
    eid,gi,ti,p=key
    for typ,n in c.items():
        lim[typ][n]+=1
print('每回合消耗次数分布（按 turn 计）:')
for typ in ('Attach','Retreat','Play','Evolve','Attack','Ability','End'):
    print('  ',typ,dict(sorted(lim[typ].items())))
print()
print('== R/W 案例（全部攻击对） ==')
print('resistance 命中对数:',len(r_pairs))
for x in r_pairs[:12]: print('   ',x)
print('weakness 命中对数:',len(w_pairs),'其中 plain:',sum(1 for x in w_pairs if x[-1]=='plain'))
print()
print('== 数值 ctx -> 名称（消耗决策同帧配对）==')
for c in sorted(name_map):
    tot=sum(name_map[c].values())
    print(f'  ctx {c}: n={tot} ->',name_map[c].most_common(3))
