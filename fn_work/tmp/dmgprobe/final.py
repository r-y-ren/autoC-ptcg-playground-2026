import json, glob, collections
cards={c["cardId"]:c for c in json.load(open("references/engine/cabt-cards.json"))}
atks={a["attackId"]:a for a in json.load(open("references/engine/cabt-attacks.json"))}
def walk(o):
    if isinstance(o,dict):
        if o.get("type") in ("Attack","HpChange") and "cardId" in o: yield o
        for v in o.values(): yield from walk(v)
    elif isinstance(o,list):
        for v in o: yield from walk(v)
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
                rows.append((pending[0],pending[1],lg.get("cardId"),-v)); pending=None
        elif lg.get("type")=="Attack": pending=None
print("official-replay attack->hpchange pairs:", len(rows))
ok=bad=0; wrows=[]; rrows=[]; mism=[]
for ac,aid,dc,act in rows:
    A=cards.get(ac); D=cards.get(dc); a=atks.get(aid)
    if not A or not D or not a: continue
    base=a.get("damage") or 0
    if base<=0 or (a.get("text") or "").strip(): continue
    d=base
    w=(D.get("weakness") is not None and D["weakness"]==A["energyType"])
    r=(D.get("resistance") is not None and D["resistance"]==A["energyType"])
    if w: d*=2
    if r: d=max(0,d-30)
    tag=("W" if w else "")+("R" if r else "")
    rec=(a["name"],base,A["name"],A["energyType"],D["name"],D.get("weakness"),D.get("resistance"),d,act,tag)
    if d==act:
        ok+=1
        if w: wrows.append(rec)
        if r: rrows.append(rec)
    else:
        bad+=1; mism.append(rec)
print(f"plain attacks checked: match={ok} mismatch={bad}")
print("\nWEAKNESS (x2) confirmed cases in OFFICIAL Kaggle replays:")
for r in wrows: print("   ",r)
print("\nRESISTANCE (-30) confirmed cases in OFFICIAL Kaggle replays:")
for r in rrows: print("   ",r)
print("\nUnexplained by base+weakness+resistance alone (extra modifiers in play):")
for r in mism: print("   ",r)
