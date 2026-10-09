import json, glob, os, collections
files=sorted(glob.glob('references/episodes/episode-*-replay.json'))
print('files:',len(files))
rows=[]; eids=collections.Counter()
for f in files:
    try:
        d=json.load(open(f))
    except Exception as e:
        rows.append({'file':os.path.basename(f),'error':str(e)}); continue
    eid=(d.get('info') or {}).get('EpisodeId')
    eids[eid]+=1
    steps=d.get('steps') or []
    viz=(steps[0][0].get('visualize') if steps and steps[0][0].get('visualize') else None)
    nres=0; reslist=[]
    if viz:
        for i,fr in enumerate(viz):
            for lg in (fr.get('logs') or []):
                if lg.get('type')=='Result':
                    nres+=1; reslist.append((i,lg.get('reason'),lg.get('result')))
    st=[s.get('status') for s in steps[-1]] if steps else []
    rows.append({'file':os.path.basename(f),'eid':eid,'steps':len(steps),'viz':len(viz) if viz else 0,
                 'n_results':nres,'results':reslist,'rewards':d.get('rewards'),'statuses':d.get('statuses'),
                 'teams':(d.get('info') or {}).get('TeamNames'),
                 'last_status':st})
json.dump(rows,open('fn_work/tmp/replay_mine/inventory.json','w'),ensure_ascii=False,indent=1)
dups={k:v for k,v in eids.items() if v>1}
print('unique EpisodeIds:',len(eids),'dups:',dups)
print('parse errors:',[r for r in rows if 'error' in r])
print('total Result logs:',sum(r.get('n_results',0) for r in rows))
print('episodes with 0 Result (aborted?):',[(r['file'],r.get('rewards'),r.get('statuses')) for r in rows if r.get('n_results')==0])
print('rewards dist:',collections.Counter(tuple(r.get('rewards') or ()) for r in rows))
print('steps==600 count:',sum(1 for r in rows if r.get('steps')==600))
print('steps min/max:',min(r.get('steps',0) for r in rows),max(r.get('steps',0) for r in rows))
print('results per episode dist:',collections.Counter(r.get('n_results') for r in rows))
