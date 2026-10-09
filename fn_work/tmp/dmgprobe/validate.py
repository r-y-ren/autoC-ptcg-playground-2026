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

def predict(atk_id, atk_card_id, def_card_id):
    a=atks.get(atk_id); atk=cards.get(atk_card_id); dfn=cards.get(def_card_id)
    if not a or not atk or not dfn: return None
    d=a.get("damage") or 0
    if d<=0: return None
    # only plain "does N damage" attacks (no text) to avoid effect confounders
    if (a.get("text") or "").strip(): return None
    if dfn.get("weakness") is not None and dfn["weakness"]==atk["energyType"]: d*=2
    if dfn.get("resistance") is not None and dfn["resistance"]==atk["energyType"]: d=max(0,d-30)
    return d

samples=[]
seen=set()
NGAMES=int(sys.argv[1]) if len(sys.argv)>1 else 40
for g in range(NGAMES):
    random.seed(1000+g)
    def mk():
        d=random.sample(basic,20)+[random.choice([c["cardId"] for c in energies])]*40
        random.shuffle(d); return d
    a0=mk(); a1=mk()
    sd=lib.BattleStart((ctypes.c_int*120)(*(a0+a1)))
    if not sd.battlePtr: continue
    for step in range(3000):
        s=lib.GetBattleData(sd.battlePtr); o=json.loads(s.json.decode())
        cur=o.get("current")
        if cur and cur.get("result",-1)>=0: break
        sel=o.get("select")
        if sel is None: break
        opts=sel.get("option") or []
        mc=int(sel.get("maxCount") or 0); mn=int(sel.get("minCount") or 0)
        pick=list(range(min(max(mn,1),len(opts)))) if opts and mc>0 else []
        try: lib.Select(sd.battlePtr,(ctypes.c_int*len(pick))(*pick),len(pick))
        except Exception: break
    try:
        vis=json.loads(lib.VisualizeData(sd.battlePtr).decode())
    except Exception:
        vis=[]
    # pair Attack logs with following HpChange logs
    pending=None
    for e in vis:
        for lg in (e.get("logs") or []):
            t=lg.get("type")
            if t=="Attack":
                pending=(lg.get("cardId"), lg.get("attackId"), lg.get("playerIndex"))
            elif t=="HpChange" and pending:
                v=lg.get("value")
                if v is not None and v<0:
                    key=(pending[1],pending[0],lg.get("cardId"),v)
                    if key not in seen:
                        seen.add(key)
                        samples.append({"atk_card":pending[0],"attack":pending[1],
                                        "def_card":lg.get("cardId"),"actual":-v})
                pending=None
    lib.BattleFinish(sd.battlePtr)

print("unique damage samples:", len(samples))
ok=bad=skip=0
fails=[]
for s in samples:
    p=predict(s["attack"],s["atk_card"],s["def_card"])
    if p is None:
        skip+=1; continue
    if p==s["actual"]: ok+=1
    else:
        bad+=1
        if len(fails)<25: fails.append((s,p))
print(f"plain-attack samples: ok={ok} mismatch={bad} skipped(text/zero)={skip}")
for f,p in fails[:25]:
    atk=cards[f['atk_card']]; dfn=cards[f['def_card']]; a=atks[f['attack']]
    print(f"  MISMATCH {a['name'][:18]:20s} base={a['damage']:4d} atk={atk['name'][:18]:20s}(et={atk['energyType']}) "
          f"def={dfn['name'][:18]:20s}(w={dfn['weakness']} r={dfn['resistance']}) pred={p} actual={f['actual']}")
json.dump(samples, open("tmp/dmgprobe/samples.json","w"))

# targeted weakness/resistance case counts
wcases=sum(1 for s in samples if cards[s['def_card']].get('weakness') is not None
           and cards[s['def_card']]['weakness']==cards[s['atk_card']]['energyType'])
rcases=sum(1 for s in samples if cards[s['def_card']].get('resistance') is not None
           and cards[s['def_card']]['resistance']==cards[s['atk_card']]['energyType'])
print("samples where weakness should trigger:", wcases)
print("samples where resistance should trigger:", rcases)
