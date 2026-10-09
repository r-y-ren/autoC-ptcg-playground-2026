import json, glob, collections
cards={c["cardId"]:c for c in json.load(open("references/engine/cabt-cards.json"))}
atks={a["attackId"]:a for a in json.load(open("references/engine/cabt-attacks.json"))}
byname=collections.defaultdict(list)
for a in atks.values(): byname[a["name"]].append(a)
def walk(o):
    if isinstance(o,dict):
        if o.get("type") in ("Attack","HpChange") and "cardId" in o: yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o,list):
        for v in o: yield from walk(v)
# For attacks whose COST type != attacker own type, check which weakness value gives x2
rows=[]
for f in sorted(glob.glob("references/episodes/*.json")):
    try: data=json.load(open(f))
    except Exception: continue
    pending=None
    for lg in walk(data):
        if lg.get("type")=="Attack": pending=(lg.get("cardId"), lg.get("attackId"))
        elif lg.get("type")=="HpChange" and pending:
            v=lg.get("value")
            if v is not None and v<0:
                A=cards.get(pending[0]); D=cards.get(lg.get("cardId")); a=atks.get(pending[1])
                pending=None
                if not A or not D or not a: continue
                base=a.get("damage") or 0
                if base<=0 or (a.get("text") or "").strip(): continue
                rows.append((a["name"],base,A["name"],A["energyType"],a["energies"],D["name"],D.get("weakness"),D.get("resistance"),-v))
print("all plain-attack rows from official replays:", len(rows))
print("\n=== For attacks whose cost types differ from attacker's own type: which weakness triggers x2? ===")
seen=set()
for name,base,an,et,cost,dn,w,r,act in rows:
    costtypes=set(cost)
    if et in costtypes: continue     # only where own type is NOT among cost types
    key=(name,an,et,tuple(cost),dn,w,act)
    if key in seen: continue
    seen.add(key)
    ratio = act/base if base else 0
    print(f"  {name:20s} base={base:3d} own_type={et} cost={cost} -> {dn:22s}(w={w} r={r}) actual={act:3d} ratio={ratio:.2f}")
print("\n=== summary: ratio==2 vs defender weakness value (attacks with cost != own type) ===")
cnt=collections.Counter()
for name,base,an,et,cost,dn,w,r,act in rows:
    if et in set(cost): continue
    cnt[(w, round(act/base,2))]+=1
for k,v in sorted(cnt.items(), key=lambda x:-x[1])[:20]:
    print("   defender weakness=",k[0]," ratio=",k[1]," count=",v)
