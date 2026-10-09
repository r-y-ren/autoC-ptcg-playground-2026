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
lib.BattleFinish.argtypes=[ctypes.c_void_p]; lib.VisualizeData.restype=ctypes.c_char_p; lib.VisualizeData.argtypes=[ctypes.c_void_p]
lib.AllCard.restype=ctypes.c_char_p; lib.AllAttack.restype=ctypes.c_char_p
cards={c["cardId"]:c for c in json.loads(lib.AllCard())}
atks={a["attackId"]:a for a in json.loads(lib.AllAttack())}
pokes=[c for c in cards.values() if c.get("hp",0)>0]
energies=[c for c in cards.values() if c.get("cardType")==5]

# deck A: Fighting (et=6) attackers ; deck B: defenders with resistance==6 (Fighting)
atk_pool=[c["cardId"] for c in pokes if c.get("basic") and c["energyType"]==6]
def_pool=[c["cardId"] for c in pokes if c.get("basic") and c.get("resistance")==6]
print("fighting basics:",len(atk_pool),"resist-F basics:",len(def_pool))
# also grass variant
atk_pool_g=[c["cardId"] for c in pokes if c.get("basic") and c["energyType"]==1]
def_pool_g=[c["cardId"] for c in pokes if c.get("basic") and c.get("resistance")==1]
print("grass basics:",len(atk_pool_g),"resist-G basics:",len(def_pool_g))
combos=[("FIGHTING", atk_pool, def_pool, 6), ("GRASS", atk_pool_g, def_pool_g, 1)]
rows=[]
for label, ap, dp, et in combos:
    if not ap or not dp: continue
    for g in range(60):
        random.seed(20000+g*7)
        A=(random.sample(ap,min(20,len(ap)))+[random.choice([c["cardId"] for c in energies if c["energyType"]==et or c["energyType"]!=et])]*40)
        A=A[:60]
        while len(A)<60: A.append(random.choice(ap))
        B=(random.sample(dp,min(20,len(dp)))+[random.choice([c["cardId"] for c in energies])]*40)[:60]
        while len(B)<60: B.append(random.choice(dp))
        random.shuffle(A); random.shuffle(B)
        sd=lib.BattleStart((ctypes.c_int*120)(*(A+B)))
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
                if t=="Attack": pending=lg.get("cardId"), lg.get("attackId")
                elif t=="HpChange" and pending:
                    v=lg.get("value")
                    if v is not None and v<0:
                        rows.append((label,pending[0],pending[1],lg.get("cardId"),-v))
                    pending=None
        lib.BattleFinish(sd.battlePtr)

print("\nraw damage rows:",len(rows))
seen=set(); shown=0; ok=bad=0
for label,ac,aid,dc,act in rows:
    A=cards.get(ac); D=cards.get(dc); a=atks.get(aid)
    if not A or not D or not a: continue
    base=a.get("damage") or 0
    if base<=0 or (a.get("text") or "").strip(): continue
    if D.get("resistance") != A["energyType"]: continue   # only resistance-triggering cases
    d=base
    if D.get("weakness") is not None and D["weakness"]==A["energyType"]: d*=2
    if D.get("resistance") is not None and D["resistance"]==A["energyType"]: d=max(0,d-30)
    k=(a['name'],A['name'],D['name'],base,act)
    if k in seen: continue
    seen.add(k)
    if d==act: ok+=1
    else: bad+=1
    if shown<14:
        w = " (also weakness x2)" if (D.get("weakness") is not None and D["weakness"]==A["energyType"]) else ""
        print(f"  [{label}] {a['name'][:16]:18s} base={base:3d} atk {A['name'][:18]:20s}(et={A['energyType']}) -> def {D['name'][:18]:20s}(r={D['resistance']}){w}  pred={d:3d} actual={act:3d}")
        shown+=1
print(f"\nresistance-triggered plain cases: ok={ok} mismatch={bad}")
