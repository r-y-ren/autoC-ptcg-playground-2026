import json
v=json.load(open("tmp/dmgprobe/vis1.json"))
cards={c["cardId"]:c for c in json.load(open("tmp/dmgprobe/cards.json"))}
atks={a["attackId"]:a for a in json.load(open("tmp/dmgprobe/attacks.json"))}
shown=0
for e in v:
    for lg in (e.get("logs") or []):
        if lg.get("type") in ("Attack","HpChange"):
            print(json.dumps(lg, ensure_ascii=False)[:500])
            shown+=1
            if shown>=18: break
    if shown>=18: break
