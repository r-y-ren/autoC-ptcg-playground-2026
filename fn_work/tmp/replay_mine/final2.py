"""奖赏值终判：以'在场对象序列号'识别被 KO 的顶层宝可梦（排除进化链下层卡）"""
import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}
def flag(cid):
    c=CARDS.get(cid,{})
    return 'megaEx' if c.get('megaEx') else 'ex' if c.get('ex') else 'normal'

prize_val=collections.defaultdict(collections.Counter)
jump_dist=collections.Counter()
clean=0; amb=0; skipped_stack=0
take_frames=collections.Counter()
game_ok=collections.Counter()
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    viz=d['steps'][0][0]['visualize']
    segs=[]; start=0
    for i,fr in enumerate(viz):
        for lg in (fr.get('logs') or []):
            if lg.get('type')=='Result':
                segs.append((start,i)); start=i+1
    if start<len(viz): segs.append((start,len(viz)-1))
    for gi,(f0,f1) in enumerate(segs):
        prev_play={0:set(),1:set()}
        kos={0:[],1:[]}   # owner -> [{card, acc, frame}]
        takes_by=[0,0]
        for i in range(f0,f1+1):
            fr=viz[i]
            logs=fr.get('logs') or []
            ko_cards=[lg for lg in logs if lg['type']=='MoveCard' and lg.get('toArea')==3 and lg.get('fromArea') in (4,5) and CARDS.get(lg.get('cardId'),{}).get('cardType')==0]
            for lg in ko_cards:
                p=lg.get('playerIndex'); s=lg.get('serial')
                if s in prev_play[p]:
                    kos[p].append({'card':lg.get('cardId'),'acc':0,'frame':i})
                else:
                    skipped_stack+=1
            tk=[lg for lg in logs if lg['type']=='MoveCard' and lg.get('fromArea')==6 and lg.get('toArea')==2]
            take_frames[len(tk)]+=1
            for lg in tk:
                p=lg.get('playerIndex'); takes_by[p]+=1
                cands=[k for k in kos[1-p] if i-5<=k['frame']<=i]
                if len(cands)==1:
                    cands[0]['acc']+=1; clean+=1
                else:
                    amb+=1
                    if cands: cands[0]['acc']+=1
            cur=fr.get('current') or {}
            pls=cur.get('players') or []
            play={0:set(),1:set()}
            for p in (0,1):
                if p<len(pls):
                    for pk in (pls[p].get('active') or [])+(pls[p].get('bench') or []):
                        play[p].add(pk.get('serial'))
            prev_play=play
        for p in (0,1):
            for k in kos[p]:
                if k['acc']>0:
                    prize_val[flag(k['card'])][k['acc']]+=1
            jump_dist[takes_by[p]]+=1
        for p in (0,1):
            exp=sum((1 if flag(k['card'])=='normal' else 2 if flag(k['card'])=='ex' else 3)*k['acc'] for k in kos[p])
            # 简化一致性：该玩家领的总张数 vs 对方 KO 应得值
        exp0=sum((1 if flag(k['card'])=='normal' else 2 if flag(k['card'])=='ex' else 3) for k in kos[0])
        exp1=sum((1 if flag(k['card'])=='normal' else 2 if flag(k['card'])=='ex' else 3) for k in kos[1])
        game_ok[(exp0==takes_by[1] and exp1==takes_by[0])]+=1
print('单候选干净归属:',clean,'| 多/零候选:',amb,'| 进化链下层卡排除:',skipped_stack)
print('单帧领取张数分布:',dict(sorted(take_frames.items())))
print('KO flag -> 该 KO 实际被领取张数（干净单候选）:')
for k,v in prize_val.items():
    tot=sum(v.values())
    print(f'   {k}: n={tot}',dict(sorted(v.items())))
print('game 级一致性（每方: ΣKO理论值 == 对方领取数）:',dict(game_ok))
print('每玩家领取张数分布:',dict(sorted(jump_dist.items())))
