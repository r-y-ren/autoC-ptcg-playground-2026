import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
M=json.load(open(f'{ROOT}/fn_work/tmp/replay_mine/mined.json'))
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
conv_ids={f.split('/')[-1].split('.')[0] for f in glob.glob(f'{ROOT}/references/episodes/conv/*.conv.json')}

# ---------- E. SelectContext 数值谱（conv 同法：active=status ACTIVE 侧, win=match winner） ----------
def ctx_table(records, key):
    rows=collections.defaultdict(lambda:[0,0])
    for r in records:
        act=r.get(key)
        if act is None: continue
        rows[r['ctx']][0 if act==r['mwin'] else 1]+=1
    return rows

recs_all=[]; recs_old=[]; recs_new=[]
for m in M:
    is_old=str(m['eid']) in conv_ids
    for r in m['obs_records']:
        r['mwin']=m['match_winner']; r['eid']=m['eid']
        recs_all.append(r)
        (recs_old if is_old else recs_new).append(r)

t_all=ctx_table(recs_all,'active_status'); t_old=ctx_table(recs_old,'active_status'); t_new=ctx_table(recs_new,'active_status')
t_all_act=ctx_table(recs_all,'active_action')
N=lambda t: sum(w+l for w,l in t.values())
print('=== E. SelectContext 数值谱（active=status-ACTIVE 侧；win/lose=对局胜者侧/败者侧）===')
print(f'样本: 93 局全部 {N(t_all)} 决策拍 | 档案子集(61) {N(t_old)} | 新增子集(32) {N(t_new)}')
hdr=f'{"ctx":>4} {"93win":>6} {"93lose":>6} {"93share%":>8} {"61win":>6} {"61lose":>6} {"61share%":>8} {"32win":>6} {"32lose":>6} {"32share%":>8} {"win率93":>7} {"win率61":>7}'
print(hdr)
order=sorted(t_all, key=lambda c:-(t_all[c][0]+t_all[c][1]))
for c in order:
    a=t_all[c]; o=t_old.get(c,[0,0]); n=t_new.get(c,[0,0])
    sa=100*(a[0]+a[1])/N(t_all); so=100*(o[0]+o[1])/N(t_old) if N(t_old) else 0; sn=100*(n[0]+n[1])/N(t_new) if N(t_new) else 0
    wa=a[0]/(a[0]+a[1]) if a[0]+a[1] else 0; wo=o[0]/(o[0]+o[1]) if o[0]+o[1] else 0
    print(f'{c:>4} {a[0]:>6} {a[1]:>6} {sa:>8.2f} {o[0]:>6} {o[1]:>6} {so:>8.2f} {n[0]:>6} {n[1]:>6} {sn:>8.2f} {wa:>7.3f} {wo:>7.3f}')
# status vs action attribution delta
diff=sum(1 for r in recs_all if r['active_status']!=r['active_action'])
none_act=sum(1 for r in recs_all if r['active_action'] is None)
print(f'归属差异: status≠action {diff}/{len(recs_all)} = {100*diff/len(recs_all):.1f}% ; 无动作拍 {none_act}')

# ---------- context 数值<->名称映射 ----------
mp=collections.defaultdict(collections.Counter)
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    steps=d['steps']; viz=steps[0][0].get('visualize') or []
    if len(viz)!=len(steps): continue
    for i,fr in enumerate(viz):
        vs=(fr.get('select') or {}).get('context')
        pair=steps[i]
        for j in (0,1):
            sel=(pair[j].get('observation') or {}).get('select') or {}
            if sel and sel.get('context') is not None and vs:
                mp[sel.get('context')][vs]+=1
print('=== 数值 ctx -> viz 名称映射（同帧配对）===')
for c in sorted(mp):
    tot=sum(mp[c].values())
    top=mp[c].most_common(3)
    print(f'  ctx {c}: n={tot} -> {top}')

# ---------- 3. 奖赏：按玩家归属重算 ----------
print('=== 3b. 奖赏跳变（按 KO 归属方=奖赏方对手，同帧±2 配对）===')
val=collections.defaultdict(collections.Counter)
jd=collections.Counter(); clean=0; dirty=0
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    viz=d['steps'][0][0]['visualize']
    koq={0:[],1:[]}   # owner player -> [(frame,cardId)]
    lastjump={0:-99,1:-99}
    for i,fr in enumerate(viz):
        logs=fr.get('logs') or []
        cur=fr.get('current') or {}
        for lg in logs:
            if lg['type']=='MoveCard' and lg.get('toArea')==3 and lg.get('fromArea') in (4,5) and CARDS.get(lg.get('cardId'),{}).get('cardType')==0:
                koq[lg.get('playerIndex')].append((i,lg.get('cardId')))
        pls=cur.get('players') or []
        for p in (0,1):
            if p>=len(pls): continue
            npr=len(pls[p].get('prize') or [])
            prev=pls[p].get('_prev')
            # 用帧内顺序：跳变在本帧被检测，KOs 排队于对方
            key=f'{p}'
        # 简化：逐帧 diff 用外部数组
    # 第二遍：diff
    prev=[None,None]
    koq={0:[],1:[]}
    for i,fr in enumerate(viz):
        logs=fr.get('logs') or []
        cur=fr.get('current') or {}
        for lg in logs:
            if lg['type']=='MoveCard' and lg.get('toArea')==3 and lg.get('fromArea') in (4,5) and CARDS.get(lg.get('cardId'),{}).get('cardType')==0:
                koq[lg.get('playerIndex')].append((i,lg.get('cardId')))
        pls=cur.get('players') or []
        for p in (0,1):
            if p>=len(pls): continue
            npr=len(pls[p].get('prize') or [])
            if prev[p] is not None and npr<prev[p]:
                jump=prev[p]-npr
                opp=1-p
                # 取对方队列中 frame in [i-2, i] 的 KO，最多匹配 jump 张（按奖赏值贪心）
                cand=[x for x in koq[opp] if i-2<=x[0]<=i]
                jd[jump]+=1
                if len(cand)==1:
                    c=cand[0][1]
                    fl='megaEx' if CARDS.get(c,{}).get('megaEx') else 'ex' if CARDS.get(c,{}).get('ex') else 'normal'
                    val[fl][jump]+=1; clean+=1
                    koq[opp]=[x for x in koq[opp] if x is not cand[0]]
                elif len(cand)==0:
                    dirty+=1
                else:
                    dirty+=1
                    # 多 KO：记录组合
                    fls=tuple(sorted('megaEx' if CARDS.get(c,{}).get('megaEx') else 'ex' if CARDS.get(c,{}).get('ex') else 'normal' for _,c in cand))
                    val[fls][jump]+=1
                    koq[opp]=[x for x in koq[opp] if x not in cand]
            if npr>0 or prev[p] is None:
                prev[p]=npr
print('单 KO 干净配对:',clean,'含歧义:',dirty)
print('flag -> jump（干净单 KO）:')
for k,v in val.items(): print('  ',k,dict(sorted(v.items())))
print('jump 全体分布:',dict(sorted(jd.items())))
