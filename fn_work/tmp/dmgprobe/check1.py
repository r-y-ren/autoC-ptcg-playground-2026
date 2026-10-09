import json
cards={c["cardId"]:c for c in json.load(open("tmp/dmgprobe/cards.json"))}
atks={a["attackId"]:a for a in json.load(open("tmp/dmgprobe/attacks.json"))}
for cid in (39,1276,886,1041):
    c=cards[cid]
    print(f"card {cid}: {c['name'][:30]:32s} et={c['energyType']} w={c['weakness']} r={c['resistance']} hp={c['hp']} attacks={c['attacks']}")
print()
a=atks[31]
print("attack 31:", json.dumps(a, ensure_ascii=False))
print()
print("attack 31 energies:", a["energies"])
# card 39 attacks
print("card 39 attacks:", cards[39]["attacks"])
