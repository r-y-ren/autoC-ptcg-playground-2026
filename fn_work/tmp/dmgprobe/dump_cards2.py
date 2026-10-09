import ctypes, json, os
cg = os.path.abspath(".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg")
lib = ctypes.cdll.LoadLibrary(os.path.join(cg, "libcg.so"))
lib.GameInitialize()
class SerialData(ctypes.Structure):
    _fields_ = [("json", ctypes.c_char_p), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("count", ctypes.c_int), ("selectPlayer", ctypes.c_int)]
lib.AllCard.restype = SerialData
lib.AllAttack.restype = SerialData
for name, fn in (("AllCard", lib.AllCard), ("AllAttack", lib.AllAttack)):
    sd = fn()
    print("===", name, "===")
    print("count:", sd.count, "json:", (sd.json[:200] if sd.json else None))
    if sd.count > 0:
        raw = ctypes.string_at(sd.data, sd.count)
        print("data bytes len", len(raw), "head:", raw[:300])
        open(f"tmp/dmgprobe/{name}.bin","wb").write(raw)
    if sd.json:
        open(f"tmp/dmgprobe/{name}.jsonstr","wb").write(sd.json)
