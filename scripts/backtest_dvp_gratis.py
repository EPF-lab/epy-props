"""
Backtest GRATIS de la regla de PICKS (DvP) con historial.json, sin cuotas ni líneas reales.

Uso:
    py backtest_dvp_gratis.py              (usa web/historial.json y los jugadores de web/index.html)
    py backtest_dvp_gratis.py --ultimos 20 (ventana de evaluación: últimos N partidos de cada jugador)

Cómo funciona (sin mirar el futuro):
- DvP "de ese día": para cada partido, lo que cada rival permitió a cada posición en sus partidos ANTERIORES
  a esa fecha (con los jugadores del historial, que son los de 15+ minutos). Ranking 1 = el que más permite.
- Línea aproximada: promedio del jugador en sus partidos ANTERIORES de la temporada, redondeado a ,5
  (floor(media)+0,5, sin push). Variante: promedio de sus últimos 10.
- Regla de PICKS: jugadores con posición confirmada y 22+ min; mismos mercados y posiciones que la página;
  rival 1-5 -> OVER, rival 26-30 -> UNDER.
- Control: las mismas jugadas (jugador, mercado, línea) SIN filtro de rival. Lo que importa es la diferencia
  entre el % de acierto con DvP y el del control, porque la línea aproximada tiene sus propios sesgos.
- Referencia: a cuota 1,91 hace falta acertar 52,4 % para no perder.
"""
import argparse, json, math, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COL = {"pts": 6, "reb": 7, "ast": 8, "tpm": 9, "stl": 10}
MK = {"ast": ["PG", "SG"], "reb": ["PG", "SF", "PF", "C"], "pts": ["PG", "SG", "SF", "C"], "tpm": ["PG", "SG"], "stl": ["PG"]}
NOMBRE = {"pts": "Puntos", "reb": "Rebotes", "ast": "Asistencias", "tpm": "Triples", "stl": "Robos"}
POS = ["PG", "SG", "SF", "PF", "C"]
MIN_PREV_JUGADOR, MIN_PREV_EQUIPO = 10, 10

def snap():
    for l in open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8"):
        if l.startswith("const SNAP="): return json.loads(l[len("const SNAP="):].rstrip().rstrip(";"))

def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ultimos", type=int, default=20)
    ap.add_argument("--historial", default=os.path.join(ROOT, "web", "historial.json")); a = ap.parse_args()
    H = json.load(open(a.historial, encoding="utf-8")); S = snap()
    info = {str(p[10]): p for p in S["players"] if p[10]}                       # id -> fila de la página
    pos_of = {pid: info[pid][3] for pid in H["p"] if pid in info}

    # 1) lo permitido por cada equipo a cada posición, partido a partido: totales por (rival, juego, posición)
    allowed = defaultdict(lambda: defaultdict(float))                          # (opp, gid, date) -> {(pos,k): suma}
    for pid, games in H["p"].items():
        ps = pos_of.get(pid)
        if not ps: continue
        for r in games:
            key = (r[3], r[0], r[1])
            for k, i in COL.items(): allowed[key][(ps, k)] += r[i]
    por_equipo = defaultdict(list)                                             # opp -> [(fecha, {(pos,k): v})]
    for (opp, gid, d), v in allowed.items(): por_equipo[opp].append((d, v))
    for t in por_equipo: por_equipo[t].sort()
    fechas = sorted({d for t in por_equipo.values() for d, _ in t})
    teams = sorted(por_equipo)

    # ranking DvP de cada fecha usando solo partidos anteriores
    rank_at = {}
    for d in fechas:
        means = {}
        for t in teams:
            prev = [v for dd, v in por_equipo[t] if dd < d]
            if len(prev) < MIN_PREV_EQUIPO: continue
            means[t] = {pk: sum(v.get(pk, 0) for v in prev) / len(prev) for pk in ((p, k) for p in POS for k in COL)}
        if len(means) < 30: continue
        for p in POS:
            for k in COL:
                orden = sorted(means, key=lambda t: -means[t][(p, k)])
                for i, t in enumerate(orden): rank_at[(d, t, p, k)] = i + 1

    # 2) simular la regla en los últimos N partidos de cada jugador
    res = defaultdict(lambda: {"sel": [0, 0], "ctl": [0, 0]})                 # (k, lado, variante) -> [aciertos, total]
    detalle = defaultdict(lambda: [0, 0])                                      # (k, pos, lado) con línea de temporada
    for pid, games in H["p"].items():
        p = info.get(pid)
        if not p or not p[9] or p[5] < 22: continue                           # misma condición que PICKS
        ps = p[3]; games = sorted(games, key=lambda r: r[1])
        for j in range(max(MIN_PREV_JUGADOR, len(games) - a.ultimos), len(games)):
            r, prev = games[j], games[:j]
            for k, poss in MK.items():
                if ps not in poss: continue
                x = r[COL[k]]
                lines = {"temporada": sum(g[COL[k]] for g in prev) / len(prev), "ult10": sum(g[COL[k]] for g in prev[-10:]) / min(10, len(prev))}
                rk = rank_at.get((r[1], r[3], ps, k))
                for var, m in lines.items():
                    L = math.floor(m) + .5
                    o, u = (1 if x > L else 0), (1 if x < L else 0)
                    for lado, hit in (("O", o), ("U", u)):
                        c = res[(k, lado, var)]["ctl"]; c[0] += hit; c[1] += 1
                    if rk is None: continue
                    if rk <= 5:
                        s = res[(k, "O", var)]["sel"]; s[0] += o; s[1] += 1
                        if var == "temporada": d_ = detalle[(k, ps, "O")]; d_[0] += o; d_[1] += 1
                    elif rk >= 26:
                        s = res[(k, "U", var)]["sel"]; s[0] += u; s[1] += 1
                        if var == "temporada": d_ = detalle[(k, ps, "U")]; d_[0] += u; d_[1] += 1

    pc = lambda h, n: f"{100 * h / n:5.1f}%" if n else "   – "
    for var, titulo in (("temporada", "LÍNEA = promedio de la temporada hasta ese día"), ("ult10", "LÍNEA = promedio de los últimos 10 partidos")):
        print(f"\n=== {titulo} — últimos {a.ultimos} partidos de cada jugador ===")
        print(f"{'Mercado':12} {'Lado':5} | {'con DvP':>8} {'n':>5} {'IC 95%':>15} | {'sin filtro':>10} {'n':>6} | {'diferencia':>10}")
        tot = {"sel": [0, 0], "ctl": [0, 0]}
        for k in MK:
            for lado in ("O", "U"):
                s, c = res[(k, lado, var)]["sel"], res[(k, lado, var)]["ctl"]
                if not s[1]: continue
                lo, hi = wilson(*s)
                print(f"{NOMBRE[k]:12} {('OVER' if lado == 'O' else 'UNDER'):5} | {pc(*s):>8} {s[1]:5d} {f'{100*lo:.0f}-{100*hi:.0f}%':>15} | {pc(*c):>10} {c[1]:6d} | {100*(s[0]/s[1]-c[0]/c[1]):+9.1f} pp")
                for z in ("sel", "ctl"): tot[z][0] += res[(k, lado, var)][z][0]; tot[z][1] += res[(k, lado, var)][z][1]
        lo, hi = wilson(*tot["sel"])
        print(f"{'TOTAL':12} {'':5} | {pc(*tot['sel']):>8} {tot['sel'][1]:5d} {f'{100*lo:.0f}-{100*hi:.0f}%':>15} | {pc(*tot['ctl']):>10} {tot['ctl'][1]:6d} | {100*(tot['sel'][0]/tot['sel'][1]-tot['ctl'][0]/tot['ctl'][1]):+9.1f} pp")
    print("\n=== Detalle por posición (línea de temporada) ===")
    for (k, ps, lado), (h, n) in sorted(detalle.items()):
        print(f"  {NOMBRE[k]:12} {ps:3} {('OVER' if lado == 'O' else 'UNDER'):5} {pc(h, n)}  ({n})")
    print("\nReferencia: a cuota 1,91 hace falta 52,4 % para no perder. 'Diferencia' = lo que aporta el filtro de DvP sobre jugar a ciegas.")

if __name__ == "__main__": main()
