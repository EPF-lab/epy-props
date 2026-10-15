"""
Descarga el historial por partido de los jugadores y crea historial.json (para los gráficos de PICKS).

Uso (Windows):
    py fetch_gamelogs.py --jugadores "TU ARCHIVO DE JUGADORES.csv" --ids jugadores_ids.csv
Opciones:
    --temporadas 2025-26 2024-25     temporadas a bajar (por defecto solo 2025-26)
    --min 15                         solo jugadores con 15 o más minutos por partido
    --salida historial.json

Es reanudable: guarda cada jugador en la carpeta 'cache_historial'. Si se corta, vuelve a correrlo.
Al empezar la temporada 2026-27, corre con:  --temporadas 2026-27 2025-26  y se actualiza.
"""
import argparse, csv, json, os, re, sys, time, unicodedata
from datetime import datetime, date

AB = {"BKN": "BRK", "CHA": "CHO", "PHX": "PHO"}      # abreviaturas de la NBA -> las de tu hoja

def fix(s):
    try: return s.encode("latin1").decode("utf-8")
    except Exception: return s
def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())
def pdate(x):
    x = str(x).strip()
    for f in ("%b %d, %Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try: return datetime.strptime(x.title() if f == "%b %d, %Y" else x, f)
        except ValueError: pass
    raise ValueError("fecha no reconocida: " + x)

def parse_rows(records):
    """[gameId, fecha AAAAMMDD, equipo, rival, local(1/0), min, pts, reb, ast, triples, robos]"""
    rows = []
    for r in records:
        m = str(r["MATCHUP"]).replace("vs.", "vs").split()          # ["LAL","vs","ATL"] o ["LAL","@","ATL"]
        tm, opp = AB.get(m[0], m[0]), AB.get(m[-1], m[-1])
        g = r.get("Game_ID", r.get("GAME_ID"))
        rows.append([int(g), int(pdate(r["GAME_DATE"]).strftime("%Y%m%d")), tm, opp, 1 if "vs" in m else 0,
                     int(r.get("MIN") or 0), int(r.get("PTS") or 0), int(r.get("REB") or 0),
                     int(r.get("AST") or 0), int(r.get("FG3M") or 0), int(r.get("STL") or 0)])
    return rows

def load_players(jug_csv, ids_csv, minmin):
    ids = {}
    for row in csv.DictReader(open(ids_csv, encoding="utf-8-sig")):
        if row["PLAYER_ID"].strip(): ids[norm(fix(row["Jugador"]))] = (fix(row["Jugador"]), row["PLAYER_ID"].strip().split(".")[0])
    mins = {}
    for row in csv.DictReader(open(jug_csv, encoding="utf-8-sig")):
        if row.get("TEAM_ABBREVIATION") == "0": continue
        try: m = float(str(row["MIN"]).replace(",", "."))
        except (ValueError, KeyError): continue
        n = norm(fix(row["Jugador"])); mins[n] = max(mins.get(n, 0), m)
    return [ids[n] for n, m in mins.items() if n in ids and m >= minmin]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jugadores", default="EPY_NBA_-_Jugadores.csv"); ap.add_argument("--ids", default="jugadores_ids.csv")
    ap.add_argument("--temporadas", nargs="+", default=["2025-26"]); ap.add_argument("--min", type=float, default=15)
    ap.add_argument("--salida", default="historial.json"); a = ap.parse_args()
    from nba_api.stats.endpoints import playergamelog
    players = load_players(a.jugadores, a.ids, a.min)
    print(f"{len(players)} jugadores a descargar ({', '.join(a.temporadas)}). Puede tardar 10 a 15 minutos.")
    os.makedirs("cache_historial", exist_ok=True); out, fails = {}, []
    for i, (name, pid) in enumerate(players, 1):
        rows = []
        for seas in a.temporadas:
            cf = os.path.join("cache_historial", f"{pid}_{seas}.json")
            if os.path.exists(cf): rows += json.load(open(cf)); continue
            for att in range(4):
                try:
                    df = playergamelog.PlayerGameLog(player_id=pid, season=seas, season_type_all_star="Regular Season", timeout=30).get_data_frames()[0]
                    r = parse_rows(df.to_dict("records")); json.dump(r, open(cf, "w")); rows += r; break
                except Exception as e:
                    if att == 3: fails.append((name, seas, str(e)[:90]))
                    else: time.sleep(2 * (att + 1))
            time.sleep(0.7)
        if rows: out[pid] = sorted(rows, key=lambda r: r[1])
        if i % 20 == 0 or i == len(players): print(f"  {i}/{len(players)}")
    data = {"v": 1, "asof": date.today().isoformat(), "temporadas": a.temporadas, "p": out}
    with open(a.salida, "w", encoding="utf-8") as f: json.dump(data, f, separators=(",", ":"))
    print(f"Listo: {len(out)} jugadores, {sum(len(v) for v in out.values())} partidos, {os.path.getsize(a.salida)/1e6:.1f} MB -> {a.salida}")
    for fl in fails: print("  falló:", *fl)
    if fails: print("Si hubo fallos, vuelve a correr el mismo comando: reutiliza lo ya descargado y reintenta solo lo que falta.")

if __name__ == "__main__": main()
