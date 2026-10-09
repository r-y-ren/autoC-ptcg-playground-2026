import json, glob, os
cards={c["cardId"]:c for c in json.load(open("references/engine/cabt-cards.json"))}
atks={a["attackId"]:a for a in json.load(open("references/engine/cabt-attacks.json"))}
files=sorted(glob.glob("references/episodes/*.json"))
print("replay files:", len(files))
ok=bad=skip=0; wshow=[]; rshow=[]; mism=[]
tot=0
for f in files:
    try: data=json.load(open(f))
    except Exception: continue
    # replay format: try to find logs
    def walk(o):
        if isinstance(o,dict):
            if o.get("type") in ("Attack","HpChange") and "cardId" in o:
                yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o,list):
            for v in o:
                yield from walk(v)
    logs=list(walk(data))
    pending=None
    for lg in logs:
        t=lg.get("type")
        if t=="Attack": pending=(lg.get("cardId"), lg.get("attackId"))
        elif t=="HpChange" and pending:
            v=lg.get("value")
            if v is not None and v<0:
                tot+=1
                A=cards.get(pending[0]); D=cards.get(lg.get("cardId")); a=atks.get(pending[1])
                pending=None
                if not A or not D or not a: skip+=1; continue
                base=a.get("damage") or 0
                if base<=0 or (a.get("text") or "").strip(): skip+=1; continue
                d=base
                w=(D.get("weakness") is not None and D["weakness"]==A["energyType"])
                r=(D.get("resistance") is not None and D["resistance"]==A["energyType"])
                if w: d*=2
                if r: d=max(0,d-30)
                row=(a['name'],base,A['name'],A['energyType'],D['name'],D.get('weakness'),D.get('resistance'),d,-v)
                if d==-v:
                    ok+=1
                    if w and len(wshow)<5: wshow.append(row)
                    if r and len(rshow)<5: rshow.append(row)
                else:
                    bad+=1
                    if len(mism)<20: mism.append(row)
print(f"attack->dmg samples from OFFICIAL replays: {tot}")
print(f"plain-attack cases: match={ok}  mismatch={bad}  skipped={skip}")
print("\nWEAKNESS cases in official replays:")
for r in wshow: print("  ",r)
print("\nRESISTANCE cases in official replays:")
for r in rshow: print("  ",r)
print("\nmismatches:")
for r in mism[:20]: print("  ",r)
