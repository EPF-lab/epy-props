"""
Agrega a la página (SNAP.players en web/index.html) y a web/historial.json los jugadores que ya juegan esta temporada
pero no estaban en la página: novatos 2026 y quienes se perdieron 2025-26 (VanVleet, Lillard, Kyrie...).
Datos gratis de ESPN. Su ID en la página es "e" + ID de ESPN (la foto sale de ESPN).
Promedio base: 2025-26 si jugó 20+ partidos; si no, 2024-25; si tampoco, lo que lleva esta temporada.

Uso:  py agregar_jugadores.py                 (todos los que promedian 20+ minutos en 2+ partidos)
      py agregar_jugadores.py "Cameron Boozer" "Fred VanVleet"
"""
import json, os, re, sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diario as D, modelo as M  # noqa: E402

PAGINA = os.path.join(M.ROOT, "web", "index.html")
MINMIN, MINPJ = 20, 2
# posición confirmada a mano (las demás se deducen y quedan "por confirmar", fuera de PICKS)
POS = {"Fred VanVleet": "PG", "Damian Lillard": "PG", "Kyrie Irving": "PG", "Cameron Boozer": "PF"}
TEMPS = {2025: "2024-25", 2026: "2025-26", 2027: "2026-27"}

def get(url):
    import urllib.request
    return json.load(urllib.request.urlopen(url, timeout=30))

def faltantes(S, H, nombres):
    """Jugadores de los boxscores de esta temporada que no están en la página: {nombre: (id ESPN, partidos, minutos)}."""
    tengo = {M.key(p[0]) for p in S["players"]}
    gids = sorted({r[0] for v in H["p"].values() for r in v if r[1] >= int(D.INICIO.replace("-", ""))})
    out = {}
    for g in gids:
        sm = D.espn("summary", event=g) or {}
        for t in sm.get("boxscore", {}).get("players", []):
            for blk in t.get("statistics", []):
                ix = {n: i for i, n in enumerate(blk.get("names") or [])}
                for a in blk.get("athletes", []):
                    n = (a.get("athlete") or {}).get("displayName", "")
                    if a.get("didNotPlay") or not a.get("stats") or M.key(n) in tengo or "MIN" not in ix: continue
                    mi = str(a["stats"][ix["MIN"]]); mi = int(mi) if mi.isdigit() else 0
                    x = out.setdefault(n, [a["athlete"]["id"], 0, 0]); x[1] += 1; x[2] += mi
    if nombres: return {n: v for n, v in out.items() if M.key(n) in {M.key(x) for x in nombres}}
    return {n: v for n, v in out.items() if v[1] >= MINPJ and v[2] / v[1] >= MINMIN}

def filas(eid, abbr):
    """Partidos de temporada regular 2024-25 a 2026-27 en el formato del historial, por temporada."""
    eq = {t["team"]["id"]: t["team"]["displayName"] for t in get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams")["sports"][0]["leagues"][0]["teams"]}
    res = {}
    for yr in TEMPS:
        try: d = get(f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{eid}/gamelog?season={yr}")
        except Exception: continue
        ix = {n: i for i, n in enumerate(d.get("names") or [])}
        for st in d.get("seasonTypes", []):
            if "Regular Season" not in st.get("displayName", ""): continue
            for c in st.get("categories", []):
                for e in c.get("events", []):
                    ev = d["events"].get(e["eventId"]); s = e["stats"]
                    if not ev: continue
                    me = abbr(eq.get(ev["team"]["id"], "")); op = abbr(ev["opponent"]["displayName"])
                    if not me or not op: continue      # Juego de las Estrellas y similares
                    dia = (datetime.fromisoformat(ev["gameDate"][:19]) - timedelta(hours=6)).strftime("%Y%m%d")
                    n = lambda k: int(float(str(s[ix[k]]).split("-")[0])) if k in ix and str(s[ix[k]]).split("-")[0].replace(".", "").isdigit() else 0
                    res.setdefault(yr, []).append([int(ev["id"]), int(dia), me, op, 1 if ev.get("atVs") == "vs" else 0, n("minutes"), n("points"),
                                                   n("totalRebounds"), n("assists"), n("threePointFieldGoalsMade-threePointFieldGoalsAttempted"), n("steals")])
    return res

def posicion(nombre, eid, base):
    if nombre in POS: return POS[nombre], 1
    ab = ((get(f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{eid}").get("athlete") or {}).get("position") or {}).get("abbreviation", "")
    if ab in M.POS: return ab, 0
    if ab == "C": return "C", 0
    if ab == "G": return ("PG" if base["ast"] >= 4.5 else "SG"), 0
    return ("PF" if base["reb"] >= 6 else "SF"), 0

def main():
    S = M.load_snap(); H = json.load(open(D.HIST, encoding="utf-8"))
    abbr = lambda n: (S["teams"].get(D.ALIAS.get(n.lower(), n)) or [None, None])[1]
    nuevos = []
    for nombre, (eid, pj, mins) in faltantes(S, H, sys.argv[1:]).items():
        por = filas(eid, abbr)
        if not por.get(2027): print("sin partidos esta temporada:", nombre); continue
        yr = next((y for y in (2026, 2025) if len(por.get(y, [])) >= 20), 2027)
        rs = por[yr]; prom = lambda i: round(sum(r[i] for r in rs) / len(rs), 2)
        base = {"min": prom(5), "pts": prom(6), "reb": prom(7), "ast": prom(8), "tpm": prom(9), "stl": prom(10)}
        pos, manual = posicion(nombre, eid, base)
        eq25 = por[2026][-1][2] if por.get(2026) else ""
        eq26 = por[2027][-1][2]
        pid = "e" + str(eid)
        S["players"].append([nombre, eq25, eq26, pos, "", base["min"], base["pts"], base["reb"], base["ast"], manual, pid, base["tpm"], base["stl"]])
        H["p"][pid] = sorted([r for y in por for r in por[y]], key=lambda r: r[1])
        nuevos.append(nombre)
        print(f"{nombre} ({eq26}, {pos}{'' if manual else ' por confirmar'}): base {TEMPS[yr]} {base['pts']} pts {base['reb']} reb {base['ast']} ast en {base['min']} min; {len(H['p'][pid])} partidos al historial")
    if not nuevos: return print("No hay jugadores nuevos que agregar.")
    html = open(PAGINA, encoding="utf-8").read()
    snap = "const SNAP=" + json.dumps(S, ensure_ascii=False, separators=(",", ":")) + ";"
    html = re.sub(r"^const SNAP=.*;$", lambda _: snap, html, count=1, flags=re.M)
    open(PAGINA, "w", encoding="utf-8", newline="").write(html)
    json.dump(H, open(D.HIST, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"Agregados {len(nuevos)} jugadores.")

if __name__ == "__main__": main()
