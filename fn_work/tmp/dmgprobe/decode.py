import json, collections
cards = json.load(open("tmp/dmgprobe/cards.json"))
pk = [c for c in cards if c.get("hp",0) > 0]
print("== sample Pokemon (name, pokemonType, energyType, weakness, resistance) ==")
for c in pk[:25]:
    print(f"  {c['cardId']:5d} {c['name'][:32]:34s} pt={c['pokemonType']} et={c['energyType']} w={c['weakness']} r={c['resistance']} hp={c['hp']}")
print()
print("== pokemonType value -> example names ==")
byt = collections.defaultdict(list)
for c in pk: byt[c['pokemonType']].append(c)
for t, cs in sorted(byt.items()):
    print(f"  pt={t}: n={len(cs)} ex={[c['name'] for c in cs[:6]]}")
print()
print("== energyType value -> example names (pokemon) ==")
bye = collections.defaultdict(list)
for c in pk: bye[c['energyType']].append(c)
for t, cs in sorted(bye.items()):
    print(f"  et={t}: n={len(cs)} ex={[c['name'] for c in cs[:6]]}")
print()
print("== energy cards: energyType -> name ==")
enc = [c for c in cards if c.get('cardType')==5 or 'Energy' in c['name']][:40]
for c in enc[:30]:
    print(f"  {c['cardId']:5d} {c['name'][:34]:36s} et={c['energyType']} pt={c['pokemonType']} ctype={c['cardType']}")
