"""最终统计：回合边界修复 + 奖赏干净配对 + W/R 全对检验 + 决策量"""
import json, glob, collections, statistics
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
ATKS={a['attackId']:a for a in json.load(open(f'{ROOT}/references/engine/cabt-attacks.json'))}
def flag(cid):
    c=CARDS.get(cid,{})
    return 'megaEx' if c.get('megaEx') else 'ex' if c.get('ex') else 'normal'

pick_turn=collections.defaultdict(collections.Counter)      # action type -> per-turn picks
log_turn=collections.defaultdict(collections.Counter)       # log type -> per-turn events
prize_val=collections.defaultdict(collections.Counter)      # ko flag -> attributed takes
amb=0; clean=0
game_consist=collections.Counter()
dec_dist=[]
w_ex=[]; r_ex=[]; plain_rows=[]
low_games=[]
turns_total=0; games_total=0

for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    viz=d['steps'][0][0]['visualize']
    segs=[]; start=0
    for i,fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type')=='Result':
                segs.append((start,i,{'reason':lg.get('reason'),'winner':lg.get('result')}))
                start=i+1
    if start<len(viz):
        segs.append((start,len(viz)-1,None))
    for gi,(f0,f1,res) in enumerate(segs):
        games_total+=1
        turn_idx=-1; cur=None; prev_sel=None
        per_turn=collections.defaultdict(collections.Counter)
        per_turn_log=collections.defaultdict(collections.Counter)
        dec=[0,0]
        open_kos={0:[],1:[]}
        takes_by=[0,0]; kos_by={0:collections.Counter(),1:collections.Counter()}
        pend=None
        for i in range(f0,f1+1):
            fr=viz[i]
            logs=fr.get('logs') or []
            # --- 1) 先记本帧应答（归属到帧首仍在进行的 turn）---
            selv=fr.get('selected'); act=fr.get('action') or []
            if selv and prev_sel is not None:
                who=None
                for j in (0,1):
                    a=act[j] if j<len(act) else None
                    if a and list(a)==list(selv):
                        who=j
                if who is not None:
                    dec[who]+=1
                mx=prev_sel.get('maxCount') or 1
                picks=[x for x in selv if isinstance(x,int)] if isinstance(selv,list) else [selv]
                if len(picks)>mx:
                    picks=picks[:1]
                opts=prev_sel.get('option') or []
                if prev_sel.get('context')=='Main':
                    for idx in picks:
                        if idx<len(opts):
                            per_turn[(turn_idx,cur)][opts[idx].get('type')]+=1
            # --- 2) 事件账本 ---
            for lg in logs:
                t=lg.get('type')
                if t=='TurnStart':
                    if cur is not None or turn_idx>=0:
                        pass
                    turn_idx+=1; cur=lg.get('playerIndex')
                    if turn_idx>0: turns_total+=0
                    per_turn_log[(turn_idx,cur)]['x']=0
                elif t=='Attach':
                    ct=CARDS.get(lg.get('cardId'),{}).get('cardType')
                    per_turn_log[(turn_idx,cur)]['attach_energy' if ct in (5,6) else 'attach_tool' if ct==2 else 'attach_other']+=1
                elif t=='Play':
                    ct=CARDS.get(lg.get('cardId'),{}).get('cardType')
                    per_turn_log[(turn_idx,cur)]['supporter' if ct==3 else 'item' if ct==1 else 'stadium' if ct==4 else 'play_other']+=1
                elif t=='Switch':
                    per_turn_log[(turn_idx,cur)]['switch']+=1
                elif t=='Evolve':
                    per_turn_log[(turn_idx,cur)]['evolve']+=1
                elif t=='Attack':
                    per_turn_log[(turn_idx,cur)]['attack']+=1
                    pend={'attacker':lg.get('cardId'),'attackId':lg.get('attackId')}
                elif t=='HpChange':
                    v=lg.get('value') or 0
                    if pend and v<0:
                        A=CARDS.get(pend['attacker'],{}); D=CARDS.get(lg.get('cardId'),{}); a=ATKS.get(pend['attackId'],{})
                        if (a.get('damage') or 0)>0:
                            w=(D.get('weakness')==A.get('energyType')); r=(D.get('resistance')==A.get('energyType'))
                            exp=max(0,a['damage']*(2 if w else 1)-(30 if r else 0))
                            row=(eid,i,a.get('name'),a['damage'],A.get('energyType'),D.get('name'),D.get('weakness'),D.get('resistance'),exp,-v,bool((a.get('text') or '').strip()))
                            if not row[-1]:
                                plain_rows.append(row)
                            if r: r_ex.append(row)
                            if w: w_ex.append(row)
                        pend=None
                elif t=='MoveCard':
                    if lg.get('toArea')==3 and lg.get('fromArea') in (4,5) and CARDS.get(lg.get('cardId'),{}).get('cardType')==0:
                        open_kos[lg.get('playerIndex')].append({'card':lg.get('cardId'),'acc':0,'frame':i})
                        kos_by[1-lg.get('playerIndex')][flag(lg.get('cardId'))]+=1
                    if lg.get('fromArea')==6 and lg.get('toArea')==2:
                        p=lg.get('playerIndex'); takes_by[p]+=1
                        cands=[k for k in open_kos[1-p] if i-3<=k['frame']<=i]
                        if len(cands)==1:
                            cands[0]['acc']+=1; clean+=1
                            prize_val[flag(cands[0]['card'])][cands[0]['acc']]+=1
                        else:
                            amb+=1
                            if cands:
                                cands[0]['acc']+=1
            prev_sel=fr.get('select')
        # 决策量
        dec_dist.append(dec)
        if min(dec)<10:
            low_games.append((eid,gi,dec,res))
        # game 级奖赏一致性：takes_by[p] == Σ 值(kos of 1-p)？
        for p in (0,1):
            exp=sum((1 if k=='normal' else 2 if k=='ex' else 3)*n for k,n in kos_by[p].items())
            game_consist[(exp==takes_by[1-p])]+=1
        for k,c in per_turn.items():
            for typ,n in c.items():
                pick_turn[typ][n]+=1
        for k,c in per_turn_log.items():
            for typ,n in c.items():
                if typ!='x': log_turn[typ][n]+=1

print('games:',games_total)
print()
print('== A. 每回合动作 pick 分布（帧首回合归属,select[i-1]×selected[i]）==')
for typ in ('Attach','Retreat','Play','Evolve','Attack','Ability','End'):
    print('  ',typ,dict(sorted(pick_turn[typ].items())))
print('== A2. 事件级每回合分布 ==')
for typ in ('attach_energy','attach_tool','supporter','item','stadium','switch','evolve','attack'):
    print('  ',typ,dict(sorted(log_turn[typ].items())))
print()
print('== B. 奖赏 ==')
print('单候选干净配对:',clean,'| 多/零候选:',amb)
print('KO flag -> 累计领取张数（干净单候选）:')
for k,v in prize_val.items():
    print('  ',k,dict(sorted(v.items())))
print('game 级一致性 takes==ΣKO值:',dict(game_consist))
print()
print('== C. W/R 全对检验（含效果攻击） ==')
def match(rows,mode):
    ok=0; bad=0; ex=[]
    for r in rows:
        eid,i,an,base,aet,dn,w,res,exp,act,txt=r
        if mode=='W':
            e=max(0,base*2-(30 if res==aet else 0))
        else:
            e=max(0,base-30)
            if w==aet: e*=2
        if e==act: ok+=1
        else:
            bad+=1
            if len(ex)<8: ex.append(r)
    return ok,bad,ex
wok,wbad,wex2=match(w_ex,'W')
rok,rbad,rex2=match(r_ex,'R')
print(f'weakness 命中对 {len(w_ex)}: 公式 base*2(-30) 吻合 {wok} 不符 {wbad}')
for x in wex2: print('    W-mismatch',x)
print(f'resistance 命中对 {len(r_ex)}: 公式 base-30(再W) 吻合 {rok} 不符 {rbad}')
for x in rex2: print('    R-mismatch',x)
plain_ok=sum(1 for r in plain_rows if r[8]==r[9])
print(f'纯数值攻击（无文本）{len(plain_rows)}: 吻合 {plain_ok} 不符 {len(plain_rows)-plain_ok}')
print()
print('== D. 决策量（每 game 每方,consumed）==')
flat=[x for pair in dec_dist for x in pair]
print('n',len(flat),'min',min(flat),'p10',statistics.quantiles(flat,n=10)[0],'median',statistics.median(flat),
      'mean',round(statistics.mean(flat),1),'p90',statistics.quantiles(flat,n=10)[8],'max',max(flat))
b=collections.Counter()
for x in flat:
    if x<10: b['<10']+=1
    elif x<20: b['10-19']+=1
    elif x<30: b['20-29']+=1
    elif x<=42: b['30-42']+=1
    elif x<=60: b['43-60']+=1
    else: b['>60']+=1
print('buckets:',dict(b))
print('low-decision games (<10 on one side):',len(low_games))
for x in low_games: print('   ',x)
