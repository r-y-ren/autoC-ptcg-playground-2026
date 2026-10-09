import json, collections
cards={c["cardId"]:c for c in json.load(open("references/engine/cabt-cards.json"))}
atks={a["attackId"]:a for a in json.load(open("references/engine/cabt-attacks.json"))}
byname={c["name"]:c for c in cards.values()}
an={}
for a in atks.values(): an.setdefault(a["name"],a)
print("=== Q(b): does the attack's energy COST type or the Pokemon's own type drive weakness? ===")
for pn, aname in (("Kadabra","Super Psy Bolt"),("Makuhita","Corkscrew Punch"),("Enamorus","Heart Sign")):
    c=byname.get(pn); a=an.get(aname)
    print(f"  {pn}: energyType(own type)={c['energyType']}  attack '{aname}' cost energies={a['energies']} base={a['damage']}")
print()
print("=== evolutionType / pokemonType semantics ===")
print("pokemonType values:", collections.Counter(c.get("pokemonType") for c in cards.values() if c.get("hp",0)>0))
print("evolutionType values:", collections.Counter(c.get("evolutionType") for c in cards.values() if c.get("hp",0)>0))
print("basic/stage1/stage2:", collections.Counter((c.get("basic"),c.get("stage1"),c.get("stage2")) for c in cards.values() if c.get("hp",0)>0))
print()
print("examples by pokemonType:")
for t in (1,2,3,4):
    ex=[c["name"] for c in cards.values() if c.get("hp",0)>0 and c.get("pokemonType")==t][:3]
    print(f"   pt={t}: {ex}")
print()
print("=== resistance inventory (only these two types ever appear) ===")
print(collections.Counter(c.get("resistance") for c in cards.values() if c.get("hp",0)>0))
print("=== weakness inventory ===")
print(collections.Counter(c.get("weakness") for c in cards.values() if c.get("hp",0)>0))
print()
print("=== attack damage == 0 count (effect attacks) ===")
z=[a for a in atks.values() if (a.get("damage") or 0)==0]
print(len(z),"of",len(atks),"attacks have printed damage 0")
