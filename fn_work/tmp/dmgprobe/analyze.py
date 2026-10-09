import json, collections
cards = json.load(open("tmp/dmgprobe/cards.json"))
atk = {a["attackId"]: a for a in json.load(open("tmp/dmgprobe/attacks.json"))}
pk = [c for c in cards if c.get("hp",0) > 0]
print("pokemon count:", len(pk))
print("pokemonType values:", collections.Counter(c.get("pokemonType") for c in pk))
print("energyType values on pokemon:", collections.Counter(c.get("energyType") for c in pk))
print("weakness values:", collections.Counter(c.get("weakness") for c in pk))
print("resistance values:", collections.Counter(c.get("resistance") for c in pk))
print()
print("cross tab pokemonType x weakness (top):")
ct = collections.Counter((c.get("pokemonType"), c.get("weakness")) for c in pk)
for k,v in sorted(ct.items(), key=lambda x:-x[1])[:25]:
    print("  type",k[0],"weak",k[1],"->",v)
print()
print("cross tab pokemonType x resistance:")
ct2 = collections.Counter((c.get("pokemonType"), c.get("resistance")) for c in pk)
for k,v in sorted(ct2.items(), key=lambda x:-x[1])[:25]:
    print("  type",k[0],"res",k[1],"->",v)
