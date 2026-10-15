"""
Prepara los datos del día para la página: partidos de hoy y líneas de props de las casas grandes (The Odds API).
Crea web/diario.json, que la página lee sola al abrirse.

Uso:
    py diario.py                 (necesita la variable de entorno ODDS_API_KEY; en GitHub es un "secret")
    py diario.py --demo          (sin clave: inventa partidos y líneas para probar la página)

Gasto de créditos: la lista de partidos es gratis; por cada partido se piden solo los mercados en los que
algún jugador pasó el filtro de DvP (1 crédito por mercado, región "us").
"""
import argparse, json, os, random, re, sys, unicodedata
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML, OUT = os.path.join(ROOT, "web", "index.html"), os.path.join(ROOT, "web", "diario.json")
API = "https://api.the-odds-api.com/v4/sports/basketball_nba"
CARACAS = timezone(timedelta(hours=-4))
# mismos mercados y posiciones que la pestaña PICKS (índice en la tabla DvP)
MK = {"ast": (1, ["PG", "SG"], "player_assists"), "reb": (2, ["PG", "SF", "PF", "C"], "player_rebounds"),
      "pts": (0, ["PG", "SG", "SF", "C"], "player_points"), "tpm": (3, ["PG", "SG"], "player_threes"),
      "stl": (4, ["PG"], "player_steals")}
MKEY = {v[2]: k for k, v in MK.items()}
PMIN = 22
INICIO = os.environ.get("TEMPORADA_INICIO", "2026-10-20")   # antes de esta fecha (pretemporada) no se piden cuotas: no gasta créditos
ALIAS = {"la clippers": "Los Angeles Clippers"}

def key(name):
    """Misma normalización que la página (normKey): sin acentos, minúsculas, sin puntuación ni sufijos."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(w for w in s.split() if w not in ("jr", "sr", "ii", "iii", "iv"))

def load_snap():
    for line in open(HTML, encoding="utf-8"):
        if line.startswith("const SNAP="):
            return json.loads(line[len("const SNAP="):].rstrip().rstrip(";"))
    raise SystemExit("No encontré const SNAP en index.html")

def dvp_candidates(S, home, away):
    """Jugadores y mercados que pasan el filtro de DvP (rival 1-5 o 26-30), igual que genPicks() de la página."""
    D, out = S["dvp"], []
    rank = lambda t, pos, i: 1 + sum(1 for x in D.values() if x[pos][i] > D[t][pos][i])
    for me, op in ((home, away), (away, home)):
        ab = S["teams"][me][1]
        for p in S["players"]:
            if not (p[9] and p[5] >= PMIN and p[2] == ab): continue
            for k, (i, poss, _) in MK.items():
                if p[3] in poss:
                    r = rank(op, p[3], i)
                    if r <= 5 or r >= 26: out.append((p[0], k))
    return out

def team(name, S):
    n = ALIAS.get(name.lower(), name)
    if n in S["teams"]: return n
    raise SystemExit(f"Equipo desconocido en la API: {name} (añádelo a ALIAS)")

def get(path, apikey, **params):
    import requests
    r = requests.get(f"{API}{path}", params={"apiKey": apikey, **params}, timeout=40)
    if r.status_code != 200: raise SystemExit(f"Error de la API {r.status_code}: {r.text[:200]}")
    return r.json(), r.headers.get("x-requests-remaining")

def today_window():
    now = datetime.now(CARACAS)
    start = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now.hour < 6: start -= timedelta(days=1)          # de madrugada aún cuenta la jornada anterior
    return start, start + timedelta(days=1)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--demo", action="store_true"); a = ap.parse_args()
    S = load_snap(); start, end = today_window()
    data = {"v": 1, "fecha": start.date().isoformat(), "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fuente": "demo" if a.demo else "the-odds-api", "juegos": [], "lineas": {}, "creditos": None, "nota": ""}
    if a.demo:
        rnd = random.Random(start.date().toordinal()); teams = list(S["teams"]); rnd.shuffle(teams)
        for i in range(5):
            h, w = teams[2 * i], teams[2 * i + 1]
            data["juegos"].append({"id": f"demo{i}", "local": h, "visitante": w,
                                   "hora": (start + timedelta(hours=13 + i % 3)).astimezone(timezone.utc).isoformat()})
            for name, k in dvp_candidates(S, h, w):
                p = next(q for q in S["players"] if q[0] == name)
                base = {"pts": p[6], "reb": p[7], "ast": p[8], "tpm": p[11] if len(p) > 11 else None, "stl": p[12] if len(p) > 12 else None}[k]
                if base is None: continue
                ln = max(.5, round(base * rnd.uniform(.85, 1.1)) - .5)
                books = [{"b": b, "ln": ln, "o": round(rnd.uniform(1.75, 2.05), 2), "u": round(rnd.uniform(1.75, 2.05), 2)} for b in ("draftkings", "fanduel")]
                data["lineas"].setdefault(key(name), {})[k] = books
        data["nota"] = "Datos INVENTADOS para probar la página."
    else:
        apikey = os.environ.get("ODDS_API_KEY", "").strip()
        if not apikey: raise SystemExit("Falta ODDS_API_KEY")
        fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        events, left = get("/events", apikey, commenceTimeFrom=fmt(start), commenceTimeTo=fmt(end))
        for ev in events:
            h, w = team(ev["home_team"], S), team(ev["away_team"], S)
            data["juegos"].append({"id": ev["id"], "local": h, "visitante": w, "hora": ev["commence_time"]})
            need = sorted({MK[k][2] for _, k in dvp_candidates(S, h, w)})
            if not need or start.date().isoformat() < INICIO: continue
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
        if not events: data["nota"] = "Hoy no hay partidos de la NBA."
        elif start.date().isoformat() < INICIO: data["nota"] = f"Pretemporada: las cuotas se empiezan a pedir el {INICIO}."
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    n = sum(len(v) for v in data["lineas"].values())
    print(f"{data['fecha']}: {len(data['juegos'])} partidos, {n} líneas de jugador/mercado, créditos restantes: {data['creditos']} -> {OUT}")

if __name__ == "__main__": main()
