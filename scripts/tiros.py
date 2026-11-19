"""Mapa de tiros de la temporada 2026-27 desde el jugada a jugada de ESPN (gratis, sin clave).

Escribe web/tiros.json, que la pestaña Partidos usa para el mapa de tiros de cada jugador y la defensa del
rival por zona. Es incremental: solo baja los partidos que faltan. Lo corre diario.py cada madrugada; también
se puede correr a mano:  py scripts/tiros.py

Coordenadas de ESPN (verificado 18-nov-2026 con el texto "N-foot"): x = 0..50 pies a lo ancho (aro en x=25),
y = pies desde la línea del aro hacia el centro de la cancha (aro en y=0). Valores enteros; los tiros libres
traen un valor basura y se descartan.

Formato: {v, asof, temporada, g:{eventId:[AAAAMMDD, local, visitante]}, n:{espnId:nombre},
          s:[[eventId, espnId, equipo, x, y, metido(1/0), zona, puntos]]}
Zonas: RA área restringida (<=4 pies) · PT pintura fuera del RA · MR media distancia · C3 triple de esquina · AB3 triple de arriba.
Equipos con las abreviaturas del historial (PHO, BRK, CHO, NOP, SAS, GSW, NYK, UTA, WAS).
"""
import json
import math
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(RAIZ, "web", "tiros.json")
INICIO = os.environ.get("TEMPORADA_INICIO", "2026-10-20")
API = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
E2H = {"PHX": "PHO", "BKN": "BRK", "CHA": "CHO", "NO": "NOP", "SA": "SAS", "GS": "GSW", "NY": "NYK", "UTAH": "UTA", "WSH": "WAS"}
FT = re.compile(r"(\d+)-foot")


def get(path, **q):
    url = API + path + ("?" + "&".join(f"{k}={v}" for k, v in q.items()) if q else "")
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                return json.load(r)
        except Exception:
            if i == 2:
                raise
            time.sleep(2 + 3 * i)


def zona(x, y, pts, texto):
    if pts == 3:
        return "C3" if y <= 9 and abs(x - 25) >= 20 else "AB3"
    m = FT.search(texto or "")
    d = float(m.group(1)) if m else math.hypot(x - 25, y)
    if d <= 4:
        return "RA"
    if abs(x - 25) <= 8 and y <= 14:
        return "PT"
    return "MR"


def partido(eid):
    """Tiros de campo de un partido: lista de filas y nombres de los tiradores."""
    sm = get("summary", event=eid)
    comp = sm["header"]["competitions"][0]
    ab = {c["team"]["id"]: E2H.get(c["team"]["abbreviation"], c["team"]["abbreviation"]) for c in comp["competitors"]}
    home = next(ab[c["team"]["id"]] for c in comp["competitors"] if c["homeAway"] == "home")
    away = next(ab[c["team"]["id"]] for c in comp["competitors"] if c["homeAway"] == "away")
    filas, nombres = [], {}
    for p in sm.get("plays", []):
        if not p.get("shootingPlay") or p.get("pointsAttempted") not in (2, 3):
            continue
        c, parts = p.get("coordinate") or {}, p.get("participants") or []
        x, y = c.get("x"), c.get("y")
        if x is None or y is None or not parts or not (-5 <= x <= 55) or not (-6 <= y <= 94):
            continue
        aid = str(parts[0]["athlete"]["id"])
        team = ab.get((p.get("team") or {}).get("id"))
        if not team:
            continue
        pts = p["pointsAttempted"]
        filas.append([eid, aid, team, int(x), int(y), 1 if p.get("scoringPlay") else 0, zona(x, y, pts, p.get("text")), pts])
        m = re.match(r"^(.+?) (makes|misses) ", p.get("text") or "")
        if m and aid not in nombres:
            nombres[aid] = m.group(1)
    return home, away, filas, nombres


def actualizar(hasta=None, pausa=0.2):
    d = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"v": 1, "temporada": "2026-27", "g": {}, "n": {}, "s": []}
    hasta = hasta or (datetime.now(timezone(timedelta(hours=-4))).date() - timedelta(days=1))  # hasta ayer, hora de Caracas
    dia, nuevos = date.fromisoformat(INICIO), 0
    while dia <= hasta:
        for ev in get("scoreboard", dates=dia.strftime("%Y%m%d")).get("events", []):
            eid = str(ev["id"])
            if eid in d["g"] or ev["status"]["type"]["name"] != "STATUS_FINAL":
                continue
            try:
                home, away, filas, nombres = partido(eid)
            except Exception as ex:
                print("  no se pudo leer", eid, ex)
                continue
            if not filas:                     # partido sin coordenadas: se reintenta la próxima vez
                continue
            d["g"][eid] = [int(dia.strftime("%Y%m%d")), home, away]
            d["s"].extend(filas)
            for k, v in nombres.items():
                d["n"].setdefault(k, v)
            nuevos += 1
            time.sleep(pausa)
        dia += timedelta(days=1)
    d["asof"] = hasta.isoformat()
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return nuevos, len(d["g"]), len(d["s"])


if __name__ == "__main__":
    n, g, s = actualizar()
    print(f"Tiros: {n} partidos nuevos; {g} partidos y {s} tiros en {OUT}")
    sys.exit(0)
