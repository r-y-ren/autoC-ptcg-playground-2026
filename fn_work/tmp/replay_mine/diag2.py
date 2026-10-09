import json, glob, collections
ROOT='/mnt/data/Code/autoC/workspace/ptcg-playground-2026'
CARDS={c['cardId']:c for c in json.load(open(f'{ROOT}/references/engine/cabt-cards.json'))}

# A. -10 pdc 事件的帧上下文（哪些日志同帧）；B. Attach 来源区；C. Switch vs retreated 标志
ctxA=collections.Counter(); attach_src=collections.Counter(); sw_flag=collections.Counter()
flag_flip=collections.Counter()
per_match=collections.Counter()
n10_by_match=collections.Counter()
for f in sorted(glob.glob(f'{ROOT}/references/episodes/episode-*-replay.json')):
    d=json.load(open(f))
    eid=(d.get('info') or {}).get('EpisodeId')
    viz=d['steps'][0][0]['visualize']
    prev_ret={'cur':None}; prev_en={'cur':None}; prev_sup={'cur':None}; prev_st={'cur':None}
    for i,fr in enumerate(viz):
        logs=fr.get('logs') or []
        kinds=[l['type'] for l in logs]
        cur=fr.get('current') or {}
        pls=cur.get('players') or []
        # A: -10 pdc context
        for l in logs:
            if l['type']=='HpChange' and l.get('value')==-10 and l.get('putDamageCounter'):
                others=tuple(sorted(set(k for k in kinds if k!='HpChange')))
                ctxA[others]+=1
                n10_by_match[eid]+=1
        # B: Attach source via same-frame MoveCard same serial
        mv={}
        for l in logs:
            if l['type']=='MoveCard':
                mv[l.get('serial')]=(l.get('fromArea'),l.get('toArea'))
        for l in logs:
            if l['type']=='Attach':
                ct=CARDS.get(l.get('cardId'),{}).get('cardType')
                src=mv.get(l.get('serial'))
                attach_src[(ct,src)]+=1
        # C: Switch vs retreated flag
        for p in (0,1):
            if p<len(pls):
                r=pls[p].get('retreated'); e=pls[p].get('energyAttached') if False else cur.get('energyAttached')
                pass
        ret=cur.get('retreated'); en=cur.get('energyAttached'); sup=cur.get('supporterPlayed'); st=cur.get('stadiumPlayed')
        for name,val,prev in (('retreated',ret,prev_ret),('energyAttached',en,prev_en),
                              ('supporterPlayed',sup,prev_sup),('stadiumPlayed',st,prev_st)):
            # flags are global current-level (per current player?) -> single value
            pass
        # current-level flags are for the acting player; track flips
        for name,val in (('retreated',ret),('energyAttached',en),('supporterPlayed',sup),('stadiumPlayed',st)):
            key=(name, val)
        # switch logs vs retreated flag flip in same frame
        nsw=sum(1 for l in logs if l['type']=='Switch')
        if nsw:
            sw_flag[(nsw, bool(ret), i)]+=0  # placeholder
            sw_flag[(nsw, bool(ret))]+=1
        if en is True and (prev_en.get('cur') is False):
            flag_flip['energyAttached']+=1
        if ret is True and (prev_ret.get('cur') is False):
            flag_flip['retreated']+=1
        if sup is True and (prev_sup.get('cur') is False):
            flag_flip['supporterPlayed']+=1
        if st is True and (prev_st.get('cur') is False):
            flag_flip['stadiumPlayed']+=1
        prev_ret['cur']=ret; prev_en['cur']=en; prev_sup['cur']=sup; prev_st['cur']=st
print('A. -10 pdc 事件同帧日志组合 top:')
for k,v in ctxA.most_common(12): print('   ',k,v)
print('   受影响 match 数:',len(n10_by_match),'top:',n10_by_match.most_common(8))
print('B. Attach (cardType, (fromArea,toArea)) 分布:')
for k,v in sorted(attach_src.items(),key=lambda x:-x[1]): print('   ',k,v)
print('C. Switch 帧 (n_switch, retreated_flag):')
for k,v in sorted(sw_flag.items(),key=lambda x:-x[1])[:12]: print('   ',k,v)
print('D. flag flips (per match-level count of False->True at current scope):',dict(flag_flip))
