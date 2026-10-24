"""
Prepara los datos del día para la página y mide al modelo solo.

1. Partidos de hoy y líneas de props de las casas grandes (The Odds API) -> web/diario.json (la página lo lee sola).
2. Registro de la prueba del modelo -> web/registro.json:
   - guarda cada pick del día que pasa el filtro de DvP (con línea, cuotas, probabilidad, EV y si pasa también el de EV);
   - califica los picks de días anteriores con los resultados reales (marcadores de ESPN).

Uso:
    py diario.py                 (necesita la variable de entorno ODDS_API_KEY; en GitHub es un "secret")
    py diario.py --demo          (sin clave: inventa partidos y líneas para probar la página; no toca el registro)
    py diario.py --solo-calificar (no pide cuotas: solo califica el registro)
    py diario.py --fecha 2026-10-20 (prepara ese día; útil la víspera, cuando las casas ya publicaron las líneas)

Gasto de créditos: la lista de partidos es gratis; por cada partido se piden solo los mercados de PICKS en los que
algún jugador pasó el filtro de DvP (1 crédito por mercado, región "us"). Los resultados de ESPN no gastan créditos.
"""
import argparse, json, os, random, sys, time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

ROOT = M.ROOT
OUT, REG = os.path.join(ROOT, "web", "diario.json"), os.path.join(ROOT, "web", "registro.json")
API = "https://api.the-odds-api.com/v4/sports/basketball_nba"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
CARACAS = timezone(timedelta(hours=-4))
MARKET = {"pts": "player_points", "reb": "player_rebounds", "ast": "player_assists", "tpm": "player_threes", "stl": "player_steals"}
MKEY = {v: k for k, v in MARKET.items()}
INICIO = os.environ.get("TEMPORADA_INICIO", "2026-10-20")   # antes de esta fecha (pretemporada) no se piden cuotas ni se registran picks
ALIAS = {"la clippers": "Los Angeles Clippers"}
key = M.key

def team(name, S):
    n = ALIAS.get(name.lower(), name)
    if n in S["teams"]: return n
    raise SystemExit(f"Equipo desconocido en la API: {name} (añádelo a ALIAS)")

def get(path, apikey, **params):
    import requests
    r = requests.get(f"{API}{path}", params={"apiKey": apikey, **params}, timeout=40)
    if r.status_code != 200: raise SystemExit(f"Error de la API {r.status_code}: {r.text[:200]}")
    return r.json(), r.headers.get("x-requests-remaining")

def today_window(fecha=None):
    if fecha:                                                         # --fecha AAAA-MM-DD: preparar otro día (p. ej. mañana)
        start = datetime.fromisoformat(fecha).replace(tzinfo=CARACAS)
        return start, start + timedelta(days=1)
    now = datetime.now(CARACAS)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)   # el día del calendario en Caracas:
    return start, start + timedelta(days=1)                           # corre a las 3 am y trae los partidos de esa noche

# ---------- registro y calificación ----------
def load_reg():
    try: return json.load(open(REG, encoding="utf-8"))
    except (OSError, ValueError): return {"v": 1, "picks": []}

def lesiones(S):
    """Reporte de lesiones de ESPN: {equipo: [[jugador, estado (Out/Questionable/...), tipo]]} (gratis, sin clave)."""
    d = espn("injuries")
    out = {}
    for t in (d or {}).get("injuries", []):
        n = ALIAS.get(str(t.get("displayName", "")).lower(), t.get("displayName"))
        if n not in S["teams"]: continue
        for x in t.get("injuries", []):
            nm = (x.get("athlete") or {}).get("displayName")
            if nm: out.setdefault(n, []).append([nm, x.get("status") or "", ((x.get("details") or {}).get("type") or "")])
    return out

def registrar(reg, fecha, juegos, lineas, S, les=None):
    """Rehace los picks de hoy (todos los que pasan DvP) con lo que dicen las casas a esta hora."""
    md = M.Modelo(S)
    reg["picks"] = [e for e in reg["picks"] if e["fecha"] != fecha]
    for j in juegos:
        for x in md.candidatos(j["local"], j["visitante"]):
            p = x["p"]; ev = M.evaluar(md, x, (lineas.get(key(p[0])) or {}).get(x["k"]) or [])
            if ev is None: continue
            st = next((l[1] for l in (les or {}).get(x["me"], []) if key(l[0]) == key(p[0])), None)
            if st: ev["les"] = st
            if st and st.lower().startswith("out"): ev["selb"] = False      # si está fuera no cuenta como seleccionada
            reg["picks"].append({"id": f"{fecha}|{p[0]}|{x['k']}|{x['side']}", "fecha": fecha, "hora": j.get("hora"),
                                 "pl": p[0], "pid": p[10], "eq": x["me"], "vs": x["op"], "pos": p[3], "k": x["k"],
                                 "side": x["side"], "rk": x["rk"], **ev, "res": None, "act": None})

def espn(path, **params):
    import requests
    for att in range(3):
        try:
            r = requests.get(f"{ESPN}/{path}", params=params, timeout=30)
            if r.status_code == 200: return r.json()
        except requests.RequestException: pass
        time.sleep(3 * (att + 1))
    return None

def box_del_dia(fecha):
    """{normKey(jugador): {pts, reb, ast, tpm, stl}} de los partidos terminados de esa fecha y si todos terminaron."""
    sb = espn("scoreboard", dates=fecha.replace("-", ""))
    if not sb: return None, False
    out, todos = {}, True
    for ev in sb.get("events", []):
        st = ev.get("status", {}).get("type", {})
        if not st.get("completed"):
            if st.get("name") not in ("STATUS_POSTPONED", "STATUS_CANCELED"): todos = False
            continue
        sm = espn("summary", event=ev["id"])
        for t in (sm or {}).get("boxscore", {}).get("players", []):
            for blk in t.get("statistics", []):
                names = blk.get("names") or blk.get("labels") or []
                ix = {n: i for i, n in enumerate(names)}
                for a in blk.get("athletes", []):
                    s = a.get("stats") or []
                    if a.get("didNotPlay") or not s or "PTS" not in ix: continue
                    num = lambda c: int(str(s[ix[c]]).split("-")[0]) if c in ix and str(s[ix[c]]).split("-")[0].lstrip("-").isdigit() else None
                    ath = a.get("athlete") or {}
                    nm = ath.get("displayName") or ath.get("fullName") or ath.get("shortName")
                    if not nm: continue
                    out[key(nm)] = {"pts": num("PTS"), "reb": num("REB"), "ast": num("AST"),
                                                             "tpm": num("3PT"), "stl": num("STL")}
    return out, todos

HIST = os.path.join(ROOT, "web", "historial.json")

def actualizar_historial(S, hoy):
    """Agrega a web/historial.json los partidos de la temporada nueva (desde INICIO hasta ayer) con los boxscores de ESPN.
    Mismo formato que fetch_gamelogs.py: [gameId, AAAAMMDD, equipo, rival, local(1/0), min, pts, reb, ast, triples, robos],
    con el ID de la NBA del jugador (el de la página). Solo pide los días que faltan (ESPN es gratis)."""
    try: H = json.load(open(HIST, encoding="utf-8"))
    except (OSError, ValueError): H = {"v": 1, "asof": None, "temporadas": [], "p": {}}
    hechos = set(H.get("espn_fechas", []))
    ids = {key(p[0]): str(p[10]) for p in S["players"] if p[10]}
    abbr = lambda n: (S["teams"].get(ALIAS.get(n.lower(), n)) or [None, None])[1]
    d, fin, nuevos, dias = date.fromisoformat(INICIO), date.fromisoformat(hoy), 0, []
    while d < fin:
        f = d.isoformat(); d += timedelta(days=1)
        if f in hechos: continue
        sb = espn("scoreboard", dates=f.replace("-", ""))
        if not sb: continue
        evs = sb.get("events", [])
        if any(not e.get("status", {}).get("type", {}).get("completed") for e in evs): continue   # día sin terminar: se reintenta mañana
        for ev in evs:
            comp = ev["competitions"][0]["competitors"]
            eq = {c["team"]["id"]: (abbr(c["team"]["displayName"]), c["homeAway"] == "home") for c in comp}
            sm = espn("summary", event=ev["id"])
            for t in (sm or {}).get("boxscore", {}).get("players", []):
                tid = t.get("team", {}).get("id"); me, home = eq.get(tid, (None, False))
                op = next((v[0] for k, v in eq.items() if k != tid), None)
                if not me or not op: continue
                for blk in t.get("statistics", []):
                    ix = {n: i for i, n in enumerate(blk.get("names") or [])}
                    for a in blk.get("athletes", []):
                        st = a.get("stats") or []
                        pid = ids.get(key((a.get("athlete") or {}).get("displayName", "")))
                        if a.get("didNotPlay") or not st or not pid or "PTS" not in ix: continue
                        n = lambda c: int(str(st[ix[c]]).split("-")[0].split(":")[0]) if c in ix and str(st[ix[c]]).split("-")[0].split(":")[0].isdigit() else 0
                        row = [int(ev["id"]), int(f.replace("-", "")), me, op, 1 if home else 0, n("MIN"), n("PTS"), n("REB"), n("AST"), n("3PT"), n("STL")]
                        lst = H["p"].setdefault(pid, [])
                        if not any(r[0] == row[0] for r in lst): lst.append(row); nuevos += 1
        hechos.add(f); dias.append(f)
    if dias:
        for lst in H["p"].values(): lst.sort(key=lambda r: r[1])
        H["espn_fechas"] = sorted(hechos); H["asof"] = hoy
        if "2026-27" not in H.get("temporadas", []): H["temporadas"] = H.get("temporadas", []) + ["2026-27"]
        json.dump(H, open(HIST, "w", encoding="utf-8"), separators=(",", ":"))
    return nuevos, dias

def calificar(reg, hoy):
    """Pone el resultado (W/L/P; NJ = no jugó, anulada; SL = sin línea) a los picks de días anteriores."""
    pend = defaultdict(list)
    for e in reg["picks"]:
        if e.get("res") is None and e["fecha"] < hoy: pend[e["fecha"]].append(e)
    n = 0
    for f, es in sorted(pend.items()):
        box, todos = box_del_dia(f)
        if box is None: continue
        viejo = (date.fromisoformat(hoy) - date.fromisoformat(f)).days >= 3
        for e in es:
            s = box.get(key(e["pl"]))
            if s and s.get(e["k"]) is not None:
                e["act"] = s[e["k"]]
                if e.get("ln") is None: e["res"] = "SL"
                elif e["act"] == e["ln"]: e["res"] = "P"
                else: e["res"] = "W" if (e["act"] > e["ln"]) == (e["side"] == "O") else "L"
                n += 1
            elif todos or viejo:
                e["res"] = "NJ"; n += 1
    return n

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--demo", action="store_true"); ap.add_argument("--solo-calificar", action="store_true")
    ap.add_argument("--fecha", help="AAAA-MM-DD: preparar ese día en vez de hoy (hora de Caracas)")
    a = ap.parse_args()
    S = M.load_snap(); start, end = today_window(a.fecha); hoy = start.date().isoformat()
    if a.solo_calificar:
        reg = load_reg(); n = calificar(reg, hoy)
        json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"Calificados {n} picks."); return
    md = M.Modelo(S)
    data = {"v": 1, "fecha": hoy, "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fuente": "demo" if a.demo else "the-odds-api", "juegos": [], "lineas": {}, "creditos": None, "nota": ""}
    if a.demo:
        rnd = random.Random(start.date().toordinal()); teams = list(S["teams"]); rnd.shuffle(teams)
        for i in range(5):
            h, w = teams[2 * i], teams[2 * i + 1]
            data["juegos"].append({"id": f"demo{i}", "local": h, "visitante": w,
                                   "hora": (start + timedelta(hours=13 + i % 3)).astimezone(timezone.utc).isoformat()})
            for x in md.candidatos(h, w):
                b = M.base(x["p"], x["k"])
                if b is None: continue
                ln = max(.5, round(b * rnd.uniform(.85, 1.1)) - .5)
                books = [{"b": bk, "ln": ln, "o": round(rnd.uniform(1.75, 2.05), 2), "u": round(rnd.uniform(1.75, 2.05), 2)} for bk in ("draftkings", "fanduel")]
                data["lineas"].setdefault(key(x["p"][0]), {})[x["k"]] = books
        data["nota"] = "Datos INVENTADOS para probar la página."
    else:
        apikey = os.environ.get("ODDS_API_KEY", "").strip()
        if not apikey: raise SystemExit("Falta ODDS_API_KEY")
        fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        events, left = get("/events", apikey, commenceTimeFrom=fmt(start), commenceTimeTo=fmt(end))
        for ev in events:
            h, w = team(ev["home_team"], S), team(ev["away_team"], S)
            data["juegos"].append({"id": ev["id"], "local": h, "visitante": w, "hora": ev["commence_time"]})
            need = sorted({MARKET[x["k"]] for x in md.candidatos(h, w)})
            if not need or hoy < INICIO: continue
            odds, left = get(f"/events/{ev['id']}/odds", apikey, regions="us", markets=",".join(need), oddsFormat="decimal")
            for bk in odds.get("bookmakers", []):
                for m in bk.get("markets", []):
                    k = MKEY.get(m["key"])
                    if not k: continue
                    rows = {}
                    for o in m.get("outcomes", []):          # {"name":"Over","description":"Jugador","price":1.87,"point":24.5}
                        pl, side = o.get("description"), (o.get("name") or "").lower()
                        if not pl or o.get("point") is None or side not in ("over", "under"): continue
                        r = rows.setdefault((key(pl), o["point"]), {"b": bk["key"], "ln": o["point"], "o": None, "u": None})
                        r["o" if side == "over" else "u"] = o["price"]
                    for (pk, _), r in rows.items():
                        data["lineas"].setdefault(pk, {}).setdefault(k, []).append(r)
        data["creditos"] = int(left) if left and left.isdigit() else left
        data["lesiones"] = lesiones(S)
        if not events: data["nota"] = "Hoy no hay partidos de la NBA."
        elif hoy < INICIO: data["nota"] = f"Pretemporada: las cuotas se empiezan a pedir el {INICIO}."
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    n = sum(len(v) for v in data["lineas"].values())
    print(f"{hoy}: {len(data['juegos'])} partidos, {n} líneas de jugador/mercado, créditos restantes: {data['creditos']} -> {OUT}")
    if a.demo: return
    try:
        nh, dh = actualizar_historial(S, hoy)
        print(f"Historial: {nh} partidos nuevos de jugador ({len(dh)} días) -> {HIST}")
    except Exception as ex:                       # el historial no debe tumbar el proceso diario
        print("Historial: no se pudo actualizar:", ex)
    reg = load_reg(); nc = calificar(reg, hoy)
    if hoy >= INICIO: registrar(reg, hoy, data["juegos"], data["lineas"], S, data.get("lesiones"))
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    hoy_p = [e for e in reg["picks"] if e["fecha"] == hoy]
    print(f"Registro: {nc} picks calificados; hoy {len(hoy_p)} picks DvP ({sum(1 for e in hoy_p if e.get('selb'))} pasan EV con la mezcla; {sum(1 for e in hoy_p if e.get('sel'))} con el modelo solo) -> {REG}")

if __name__ == "__main__": main()
