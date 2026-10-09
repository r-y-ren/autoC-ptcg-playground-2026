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
lib.AllCard.restype=ctypes.c_char_p
cards = {c["cardId"]: c for c in json.loads(lib.AllCard())}
pokemon = [c for c in cards.values() if c.get("hp",0)>0]
energies = [c for c in cards.values() if c.get("cardType")==5]
print("pokemon:",len(pokemon),"basic energies:",len(energies))
# build a legal-ish deck: 20 pokemon + 40 basic energy? deck must be 60 card ids
random.seed(7)
def makedeck():
    d=[]
    pool=[c["cardId"] for c in pokemon if c.get("basic")]
    d+= random.sample(pool, 20)
    d+= [random.choice([c["cardId"] for c in energies])]*40
    random.shuffle(d)
    return d
d0=makedeck(); d1=makedeck()
arr=(ctypes.c_int*120)(*(d0+d1))
sd=lib.BattleStart(arr)
print("start: ptr",sd.battlePtr,"errPlayer",sd.errorPlayer,"errType",sd.errorType)
if not sd.battlePtr:
    sys.exit("failed to start")
def obs():
    s=lib.GetBattleData(sd.battlePtr)
    o=json.loads(s.json.decode())
    return o
o=obs()
print("keys:",list(o.keys()))
print("select:", json.dumps(o.get("select"))[:600])
print("logs:", json.dumps(o.get("logs"))[:800])
lib.BattleFinish(sd.battlePtr)
