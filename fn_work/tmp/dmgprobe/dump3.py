import ctypes, json, os
cg = os.path.abspath(".venv/lib/python3.14/site-packages/kaggle_environments/envs/cabt/cg")
lib = ctypes.cdll.LoadLibrary(os.path.join(cg, "libcg.so"))
lib.GameInitialize()
lib.AllCard.restype = ctypes.c_char_p
lib.AllAttack.restype = ctypes.c_char_p
cards = json.loads(lib.AllCard())
atk = json.loads(lib.AllAttack())
print("N cards:", len(cards), "N attacks:", len(atk))
json.dump(cards, open("tmp/dmgprobe/cards.json","w"), ensure_ascii=False)
json.dump(atk, open("tmp/dmgprobe/attacks.json","w"), ensure_ascii=False)
print("sample card:", json.dumps(cards[0], ensure_ascii=False))
print("sample attack:", json.dumps(atk[0], ensure_ascii=False))
# find pokemon with weakness/resistance
pk = [c for c in cards if c.get("cardType")=="POKEMON" or c.get("hp")]
print("n pokemon-ish:", len(pk))
print("keys of first card:", list(cards[0].keys()))
