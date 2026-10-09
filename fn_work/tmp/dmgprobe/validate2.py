import ctypes, json, os, random, sys
cg = os.path.abspath(".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg")
lib = ctypes.cdll.LoadLibrary(os.path.join(cg, "libcg.so"))
lib.GameInitialize()
class StartData(ctypes.Structure):
    _fields_=[("battlePtr",ctypes.c_void_p),("errorPlayer",ctypes.c_int),("errorType",ctypes.c_int)]
class SerialData(ctypes.Structure):
    _fields_=[("json",ctypes.c_char_p),("data",ctypes.POINTER(ctypes.c_ubyte)),("count",ctypes.c_int),("selectPlayer",ctypes.c_int)]
lib.BattleStart.restype=StartData; lib.BattleStart.argtypes=[ctypes.POINTER(ctypes.c_int)]
lib.GetBattleData.restype=SerialData; lib.GetBattleData.argtypes=[ctypes.c_void_p]
lib.Select.restype=ctypes.c_int; lib.Select.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_int),ctypes.c_int]
lib.BattleFinish.argtypes=[ctypes.c_void_p]
lib.VisualizeData.restype=ctypes.c_char_p; lib.VisualizeData.argtypes=[ctypes.c_void_p]
lib.AllCard.restype=ctypes.c_char_p; lib.AllAttack.restype=ctypes.c_char_p
cards={c["cardId"]:c for c in json.loads(lib.AllCard())}
atks={a["attackId"]:a for a in json.loads(lib.AllAttack())}
pokes=[c for c in cards.values() if c.get("hp",0)>0]
energies=[c for c in cards.values() if c.get("cardType")==5]
basic=[c["cardId"] for c in pokes if c.get("basic")]
samples=[]; seen=set()
NG=int(sys.argv[1]) if len(sys.argv)>1 else 60
for g in range(NG):
    random.seed(5000+g)
    def mk():
        d=random.sample(basic,20)+[random.choice([c["cardId"] for c in energies])]*40
        random.shuffle(d); return d
    sd=lib.BattleStart((ctypes.c_int*120)(*(mk()+mk())))
    if not sd.battlePtr: continue
    for step in range(3000):
        o=json.loads(lib.GetBattleData(sd.battlePtr).json.decode())
        cur=o.get("current")
        if cur and cur.get("result",-1)>=0: break
        sel=o.get("select")
        if sel is None: break
        opts=sel.get("option") or []; mc=int(sel.get("maxCount") or 0); mn=int(sel.get("minCount") or 0)
        pick=list(range(min(max(mn,1),len(opts)))) if opts and mc>0 else []
        try: lib.Select(sd.battlePtr,(ctypes.c_int*len(pick))(*pick),len(pick))
        except Exception: break
    try: vis=json.loads(lib.VisualizeData(sd.battlePtr).decode())
    except Exception: vis=[]
    pending=None
    for e in vis:
        for lg in (e.get("logs") or []):
            t=lg.get("type")
            if t=="Attack": pending=(lg.get("cardId"),lg.get("attackId"))
            elif t=="HpChange" and pending:
                v=lg.get("value")
                if v is not None and v<0:
                    k=(pending[1],pending[0],lg.get("cardId"),v)
                    if k not in seen:
                        seen.add(k); samples.append({"atk":pending[0],"aid":pending[1],"dfn":lg.get("cardId"),"actual":-v})
                pending=None
    lib.BattleFinish(sd.battlePtr)

def pred(aid,ac,dc):
    a=atks.get(aid); A=cards.get(ac); D=cards.get(dc)
    if not a or not A or not D: return None
    d=a.get("damage") or 0
    if d<=0 or (a.get("text") or "").strip(): return None
    if D.get("weakness") is not None and D["weakness"]==A["energyType"]: d*=2
    if D.get("resistance") is not None and D["resistance"]==A["energyType"]: d=max(0,d-30)
    return d
ok=bad=0; wshow=[]; rshow=[]
for s in samples:
    p=pred(s["aid"],s["atk"],s["dfn"])
    if p is None: continue
    A=cards[s['atk']]; D=cards[s['dfn']]; a=atks[s['aid']]
    w=(D.get("weakness") is not None and D["weakness"]==A["energyType"])
    r=(D.get("resistance") is not None and D["resistance"]==A["energyType"])
    row=dict(atk=A['name'],et=A['energyType'],atk_card=s['atk'],base=a['damage'],atk_name=a['name'],
             dfn=D['name'],w=D.get("weakness"),r=D.get("resistance"),pred=p,actual=s['actual'],wtrig=w,rtrig=r)
    if p==s['actual']:
        ok+=1
        if w and len(wshow)<6: wshow.append(row)
        if r and len(rshow)<6: rshow.append(row)
    else: bad+=1
print(f"TOTAL samples={len(samples)}  plain-attack checked ok={ok} mismatch={bad}")
print("\n--- WEAKNESS-TRIGGERED CASES (pred should be base*2) ---")
for r in wshow:
    print(f"  {r['atk_name'][:16]:18s} base={r['base']:3d}  atk {r['atk'][:20]:22s}(et={r['et']})  -> def {r['dfn'][:20]:22s}(w={r['w']})  pred={r['pred']:3d} actual={r['actual']:3d}")
print("\n--- RESISTANCE-TRIGGERED CASES (pred should be base-30) ---")
for r in rshow:
    print(f"  {r['atk_name'][:16]:18s} base={r['base']:3d}  atk {r['atk'][:20]:22s}(et={r['et']})  -> def {r['dfn'][:20]:22s}(r={r['r']})  pred={r['pred']:3d} actual={r['actual']:3d}")
# check any card where weakness==resistance same type
both=[c for c in pokes if c.get('weakness') is not None and c.get('resistance') is not None and c['weakness']==c['resistance']]
print("\ncards where weakness==resistance type:", len(both))
