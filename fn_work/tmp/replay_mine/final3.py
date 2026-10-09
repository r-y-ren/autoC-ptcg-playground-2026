"""终判 2：簇级奖赏一致性（Σ理论值==Σ领取）+ Attach 动作卡型拆分"""
import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
def flag(cid):
    c=CARDS.get(cid,{})
    return 'megaEx' if c.get('megaEx') else 'ex' if c.get('ex') else 'normal'
def val(cid):
    return {'normal':1,'ex':2,'megaEx':3}[flag(cid)]

clusters=[]
attach_split=collections.defaultdict(collections.Counter)
attach_unknown=0
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    viz=d['steps'][0][0]['visualize']
    segs=[]; start=0
    for i,fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type')=='Result': segs.append((start,i)); start=i+1
    if start<len(viz): segs.append((start,len(viz)-1))
    for gi,(f0,f1) in enumerate(segs):
        prev_play={0:set(),1:set()}
        events=[]   # (frame, kind, player, card)
        turn_idx=-1; cur=None; prev_sel=None; prev_state=None
        per_turn=collections.defaultdict(collections.Counter)
        for i in range(f0,f1+1):
            fr=viz[i]; logs=fr.get('logs') or []
            # attach split: 用 i-1 帧手牌解析 Attach 选项的 index
            selv=fr.get('selected')
            if selv and prev_sel is not None and prev_sel.get('context')=='Main':
                opts=prev_sel.get('option') or []
                picks=[x for x in selv if isinstance(x,int)] if isinstance(selv,list) else [selv]
                mx=prev_sel.get('maxCount') or 1
                for idx in picks[:mx]:
                    if idx>=len(opts): continue
                    o=opts[idx]
                    if o.get('type')=='Attach':
                        hidx=o.get('index'); pid=o.get('playerIndex')
                        st=prev_state or {}
                        pls=st.get('players') or []
                        if pid is None: pid=cur
                        pl=pls[pid] if pid is not None and pid<len(pls) else {}
                        hand=pl.get('hand') or []
                        cid=hand[hidx].get('id') if isinstance(hidx,int) and 0<=hidx<len(hand) else None
                        ct=CARDS.get(cid,{}).get('cardType') if cid else None
                        if ct in (5,6): per_turn[(turn_idx,cur)]['attach_energy']+=1
                        elif ct==2: per_turn[(turn_idx,cur)]['attach_tool']+=1
                        else:
                            attach_unknown+=1
                            per_turn[(turn_idx,cur)]['attach_unk']+=1
            prev_state=fr.get('current'); prev_sel=fr.get('select')
            for lg in logs:
                t=lg.get('type')
                if t=='TurnStart': turn_idx+=1; cur=lg.get('playerIndex')
                elif t=='MoveCard':
                    if lg.get('toArea')==3 and lg.get('fromArea') in (4,5) and CARDS.get(lg.get('cardId'),{}).get('cardType')==0:
                        p=lg.get('playerIndex')
                        if lg.get('serial') in prev_play[p]:
                            events.append((i,'ko',p,lg.get('cardId')))
                    if lg.get('fromArea')==6 and lg.get('toArea')==2:
                        events.append((i,'take',lg.get('playerIndex'),None))
            cur_st=fr.get('current') or {}
            pls=cur_st.get('players') or []
            play={0:set(),1:set()}
            for p in (0,1):
                if p<len(pls):
                    for pk in (pls[p].get('active') or [])+(pls[p].get('bench') or []):
                        play[p].add(pk.get('serial'))
            prev_play=play
        # 簇切分：事件间隔 >2 帧则新簇
        cl=[]; last=None
        for ev in events:
            if last is not None and ev[0]-last>2:
                clusters.append((eid,gi,cl)); cl=[]
            cl.append(ev); last=ev[0]
        if cl: clusters.append((eid,gi,cl))
        for k,c in per_turn.items():
            for typ,n in c.items():
                attach_split[typ][n]+=1

match=0; mismatch=[]
for eid,gi,cl in clusters:
    kos=[e for e in cl if e[1]=='ko']; takes=[e for e in cl if e[1]=='take']
    exp=sum(val(k[3]) for k in kos); act=len(takes)
    if exp==act: match+=1
    else: mismatch.append((eid,gi,exp,act,[ (k[0],flag(k[3]),CARDS.get(k[3],{}).get('name')) for k in kos],len(takes)))
print('KO/Take 簇总数:',len(clusters))
print('簇级一致（Σ1/2/3 值 == 领取张数）:',match,f'({100*match/len(clusters):.1f}%)')
print('不一致簇:',len(mismatch))
endgame=sum(1 for m in mismatch if m[3]<m[2])
print('  其中“少领”(终局截断)型:',endgame,'| 多领/其他型:',len(mismatch)-endgame)
for m in mismatch[:10]: print('   ',m)
print()
print('Attach 动作每回合拆分（卡型识别）:')
for typ in ('attach_energy','attach_tool','attach_unk'):
    print('  ',typ,dict(sorted(attach_split[typ].items())))
print('  未识别:',attach_unknown)
