"""
Mide cuánto pesar los partidos de la temporada nueva frente al promedio del año pasado (mezcla n/(n+k)),
con web/historial.json: el año "pasado" es 2024-25 y se predice 2025-26 a partir de sus primeros N partidos.

- Jugadores: base = (n·media_nueva + k·media_previa)/(n+k); objetivo = cada uno de los 20 partidos siguientes.
- DvP: desviación de cada rival por posición frente a la media de la liga (lo que permite), mezclada igual;
  objetivo = desviación en los 20 partidos siguientes del rival.
Imprime el mejor k por estadística para N = 2, 4, 6, 10. Uso:  py calibrar_mezcla.py
"""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

PREV, NEW = (20241022, 20250414), (20251021, 20260412)
COL = {"min": 5, "pts": 6, "reb": 7, "ast": 8, "tpm": 9, "stl": 10}
DVPC = {"pts": 6, "ast": 8, "reb": 7, "tpm": 9, "stl": 10}
KS = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200]
NS, SIG = (2, 4, 6, 10), 20

def en(r, t): return t[0] <= r[1] <= t[1]

def jugadores(H):
    out = {}
    for n in NS:
        err = {s: [0.0] * len(KS) for s in COL}; cnt = 0
        for v in H["p"].values():
            a = [r for r in v if en(r, PREV) and r[5] > 0]; b = sorted((r for r in v if en(r, NEW) and r[5] > 0), key=lambda r: r[1])
            if len(a) < 25 or len(b) < n + 10: continue
            fut = b[n:n + SIG]; cnt += 1
            for s, c in COL.items():
                pv = sum(r[c] for r in a) / len(a); cu = sum(r[c] for r in b[:n]) / n
                for i, k in enumerate(KS):
                    p = (n * cu + k * pv) / (n + k) if n + k else pv
                    err[s][i] += sum((r[c] - p) ** 2 for r in fut) / len(fut)
        out[n] = ({s: KS[min(range(len(KS)), key=lambda i: e[i])] for s, e in err.items()}, cnt)
    return out

def dvp(H, pos_of):
    # total que permite cada equipo a cada posición, por partido: {(fecha-ordenada) ...}
    juegos = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))   # (temp, rival) -> gameId -> (pos, stat) -> valor
    fecha = {}
    for pid, v in H["p"].items():
        pos = pos_of.get(pid)
        if not pos: continue
        for r in v:
            t = "a" if en(r, PREV) else "b" if en(r, NEW) else None
            if not t or r[5] <= 0: continue
            fecha[r[0]] = r[1]
            for s, c in DVPC.items(): juegos[(t, r[3])][r[0]][(pos, s)] += r[c]
    def media(t, eq, lst=None):
        g = juegos[(t, eq)]; ids = lst if lst is not None else list(g)
        return {(p, s): sum(g[i][(p, s)] for i in ids) / len(ids) for p in M.POS for s in DVPC} if ids else None
    eqs = sorted({e for (_, e) in juegos})
    liga = {t: {(p, s): sum(media(t, e)[(p, s)] for e in eqs) / len(eqs) for p in M.POS for s in DVPC} for t in "ab"}
    out = {}
    for n in NS:
        err = {s: [0.0] * len(KS) for s in DVPC}
        for e in eqs:
            ids = sorted(juegos[("b", e)], key=lambda i: fecha[i])
            if len(ids) < n + 10: continue
            pv, cu, fu = media("a", e), media("b", e, ids[:n]), media("b", e, ids[n:n + SIG])
            for p in M.POS:
                for s in DVPC:
                    L = liga["b"][(p, s)]; dp = pv[(p, s)] / liga["a"][(p, s)] - 1; dc = cu[(p, s)] / L - 1; df = fu[(p, s)] / L - 1
                    for i, k in enumerate(KS):
                        d = (n * dc + k * dp) / (n + k) if n + k else dp
                        err[s][i] += (df - d) ** 2
        out[n] = {s: KS[min(range(len(KS)), key=lambda i: e[i])] for s, e in err.items()}
    return out

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    H = json.load(open(os.path.join(M.ROOT, "web", "historial.json"), encoding="utf-8")); S = M.load_snap()
    pos_of = {str(p[10]): p[3] for p in S["players"] if p[10]}
    for n, (ks, c) in jugadores(H).items(): print(f"Jugadores, N={n:2} partidos nuevos ({c} jugadores): mejor k {ks}")
    for n, ks in dvp(H, pos_of).items(): print(f"DvP,       N={n:2} partidos nuevos: mejor k {ks}")

if __name__ == "__main__": main()
