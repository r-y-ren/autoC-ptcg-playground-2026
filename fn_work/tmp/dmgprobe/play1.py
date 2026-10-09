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
lib.AllCard.restype=ctypes.c_char_p
cards = {c["cardId"]: c for c in json.loads(lib.AllCard())}
pokemon = [c for c in cards.values() if c.get("hp",0)>0]
energies = [c for c in cards.values() if c.get("cardType")==5]
random.seed(11)
def makedeck():
    pool=[c["cardId"] for c in pokemon if c.get("basic")]
    d= random.sample(pool,20) + [random.choice([c["cardId"] for c in energies])]*40
    random.shuffle(d); return d
d0=makedeck(); d1=makedeck()
arr=(ctypes.c_int*120)(*(d0+d1))
sd=lib.BattleStart(arr)
assert sd.battlePtr, "start failed"
def getobs():
    s=lib.GetBattleData(sd.battlePtr); return json.loads(s.json.decode())
allobs=[]
for step in range(4000):
    o=getobs()
    s=o.get("select")
    cur=o.get("current")
    if cur and cur.get("result",-1)>=0:
        break
    if s is None:
        break
    opts=s.get("option") or []
    mc=int(s.get("maxCount") or 0); mn=int(s.get("minCount") or 0)
    if not opts or mc<=0:
        sel=[]
    else:
        k=max(mn,1)
        sel=list(range(min(k,len(opts))))
    try:
        lib.Select(sd.battlePtr,(ctypes.c_int*len(sel))(*sel),len(sel))
    except Exception as e:
        print("select err at",step,e); break
    allobs.append(o)
print("steps played:", len(allobs))
vis=lib.VisualizeData(sd.battlePtr).decode()
open("tmp/dmgprobe/vis1.json","w").write(vis)
v=json.loads(vis)
print("vis entries:", len(v))
# find log types
types=set()
for e in v:
    for lg in (e.get("logs") or []):
        types.add(lg.get("type"))
print("log types:", sorted(t for t in types if t is not None))
# print a few interesting logs
shown=0
for e in v:
    for lg in (e.get("logs") or []):
        if lg.get("type") in ("ATTACK","HP_CHANGE","DAMAGE","ATTACK_DAMAGE","ATTACK_START"):
            print(json.dumps(lg, ensure_ascii=False)[:400]); shown+=1
            if shown>12: break
    if shown>12: break
lib.BattleFinish(sd.battlePtr)
