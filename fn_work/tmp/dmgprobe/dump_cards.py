import ctypes, json, os, sys, platform
cg = os.path.abspath(".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg")
lib = ctypes.cdll.LoadLibrary(os.path.join(cg, "libcg.so"))
lib.GameInitialize()
class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]
lib.AllCard.restype = SerialData
lib.AllAttack.restype = SerialData
sd = lib.AllCard()
raw = ctypes.string_at(sd.data, sd.count).decode("utf-8") if sd.count>0 else (sd.json.decode() if sd.json else "")
cards = json.loads(raw)
print("N cards:", len(cards))
print(json.dumps(cards[:3], ensure_ascii=False, indent=1)[:2000])
out = os.path.join("tmp/dmgprobe","cards.json")
json.dump(cards, open(out,"w"), ensure_ascii=False)
sd2 = lib.AllAttack()
raw2 = ctypes.string_at(sd2.data, sd2.count).decode("utf-8") if sd2.count>0 else (sd2.json.decode() if sd2.json else "")
atk = json.loads(raw2)
print("N attacks:", len(atk))
print(json.dumps(atk[:3], ensure_ascii=False, indent=1)[:2000])
json.dump(atk, open("tmp/dmgprobe/attacks.json","w"), ensure_ascii=False)
