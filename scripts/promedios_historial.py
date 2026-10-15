"""
Lee historial.json y calcula, por jugador, promedios por partido (puntos, rebotes, asistencias, triples, robos)
y la variación real de cada estadística en toda la liga.

Uso (Windows):
    py promedios_historial.py "ruta\\historial.json"
Crea promedios_historial.csv (coma decimal, para Sheets) y muestra en pantalla la variación medida.
"""
import csv, json, sys
from statistics import mean

COLS = {"pts": 6, "reb": 7, "ast": 8, "tpm": 9, "stl": 10}

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "historial.json"
    H = json.load(open(src, encoding="utf-8"))
    rows, disp = [], {k: [0.0, 0.0, 0] for k in list(COLS) + ["pra"]}   # suma (x-media)^2, suma media, jugadores
    for pid, games in H["p"].items():
        n = len(games)
        if not n: continue
        vals = {k: [g[i] for g in games] for k, i in COLS.items()}
        vals["pra"] = [g[6] + g[7] + g[8] for g in games]
        avg = {k: mean(v) for k, v in vals.items()}
        rows.append([pid, n, round(mean(g[5] for g in games), 2)] + [round(avg[k], 3) for k in COLS])
        if n >= 20:                                   # solo jugadores con muestra suficiente para medir variación
            for k, v in vals.items():
                m = avg[k]
                disp[k][0] += sum((x - m) ** 2 for x in v) / (n - 1)
                disp[k][1] += m if k not in ("pts", "pra") else m * m
                disp[k][2] += 1
    out = "promedios_historial.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PLAYER_ID", "PJ", "MIN", "PTS", "REB", "AST", "TRIPLES", "ROBOS"])
        for r in rows: w.writerow([str(x).replace(".", ",") if isinstance(x, float) else x for x in r])
    print(f"{len(rows)} jugadores -> {out}")
    print("Variación medida (jugadores con 20+ partidos):")
    for k, (sv, sm, np_) in disp.items():
        if not np_: continue
        if k in ("pts", "pra"): print(f"  {k}: desviación = {(sv / sm) ** .5:.3f} x media   ({np_} jugadores)")
        else:                   print(f"  {k}: varianza = {sv / sm:.3f} x media   ({np_} jugadores)")

if __name__ == "__main__": main()
