"""
Actualiza los promedios de los jugadores y la tabla DvP de la página (SNAP en web/index.html) con los partidos
de la temporada nueva que ya están en web/historial.json, mezclándolos con el año pasado:
    valor = (n·media_nueva + k·media_previa) / (n + k)      n = partidos jugados esta temporada

k medido con scripts/calibrar_mezcla.py (2024-25 -> 2025-26, 4 partidos nuevos, error en los 20 siguientes):
  jugadores: minutos 2, puntos 4, rebotes 8, asistencias 5, triples 6, robos 15 (el año nuevo pesa mucho y rápido:
             con solo el año pasado el error en puntos era 9,6 % mayor).
  DvP: los primeros 4-10 partidos de un rival casi no predicen lo que permitirá después (α≈0,03); la tabla del año
       pasado, encogida como ya hace el factor (c·λ≈0,4), sí. Por eso k = 100: hoy pesa ~4 %, con 40 partidos ~29 %.
Los valores del año pasado se guardan una vez en SNAP.prev / SNAP.dvp_prev, así que se puede correr cada día.
También cambia el equipo del jugador si su último partido fue con otro (traspasos).
Uso:  py actualizar_parametros.py          (lo corre también diario.py cada madrugada)
"""
import json, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

PAGINA, HIST = os.path.join(M.ROOT, "web", "index.html"), os.path.join(M.ROOT, "web", "historial.json")
INICIO = int(os.environ.get("TEMPORADA_INICIO", "2026-10-20").replace("-", ""))
COLP = {5: 5, 6: 6, 7: 7, 8: 8, 11: 9, 12: 10}          # columna en SNAP.players -> columna en el historial
KJ = {5: 2, 6: 4, 7: 8, 8: 5, 11: 6, 12: 15}            # k por columna (min, pts, reb, ast, triples, robos)
KDVP = 100
DVPC = [6, 8, 7, 9, 10]                                  # orden de SNAP.dvp: pts, ast, reb, triples, robos

def actualizar(S, H):
    """Cambia S en memoria. Devuelve un resumen."""
    prev = S.setdefault("prev", {})
    if "dvp_prev" not in S: S["dvp_prev"] = json.loads(json.dumps(S["dvp"]))
    nuevos = {pid: sorted((r for r in v if r[1] >= INICIO and r[5] > 0), key=lambda r: r[1]) for pid, v in H["p"].items()}
    cambios, traspasos = 0, []
    for p in S["players"]:
        pid = str(p[10]) if p[10] else "n:" + M.key(p[0])      # sin ID no hay historial: solo se guarda su base
        if pid not in prev: prev[pid] = [p[2]] + [p[c] if len(p) > c else None for c in COLP]
        pv = dict(zip(COLP, prev[pid][1:])); rs = nuevos.get(pid) or []; n = len(rs)
        for c, h in COLP.items():
            if len(p) <= c: continue
            cu = sum(r[h] for r in rs) / n if n else None
            if pv[c] is None: p[c] = round(cu, 2) if n >= 3 else None
            else: p[c] = round((n * cu + KJ[c] * pv[c]) / (n + KJ[c]), 2) if n else pv[c]
        if n:
            cambios += 1
            if rs[-1][2] != p[2]: traspasos.append(f"{p[0]}: {p[2]} -> {rs[-1][2]}"); p[2] = rs[-1][2]
    # DvP de esta temporada: lo que permite cada rival a cada posición por partido (posiciones de la página)
    pos_of = {str(p[10]): p[3] for p in S["players"] if p[10]}
    nombre = {v[1]: k for k, v in S["teams"].items()}
    tot = defaultdict(lambda: defaultdict(lambda: [0.0] * 5)); juegos = defaultdict(set)
    for pid, rs in nuevos.items():
        ps = pos_of.get(pid)
        for r in rs:
            t = nombre.get(r[3])
            if not t: continue
            juegos[t].add(r[0])
            if ps:
                for i, h in enumerate(DVPC): tot[t][ps][i] += r[h]
    dp, eqs = S["dvp_prev"], [t for t in S["dvp"] if juegos.get(t)]
    for ps in M.POS:
        for i in range(5):
            mp = sum(dp[t][ps][i] for t in dp) / len(dp)
            mc = sum(tot[t][ps][i] / len(juegos[t]) for t in eqs) / len(eqs) if eqs else 0
            for t in S["dvp"]:
                n = len(juegos.get(t, ()))
                dvp = dp[t][ps][i] / mp - 1
                if n and mc: dvp = (n * (tot[t][ps][i] / n / mc - 1) + KDVP * dvp) / (n + KDVP)
                S["dvp"][t][ps][i] = round(mp * (1 + dvp), 2)
    pj = sorted(len(v) for v in juegos.values())
    ult = max((r[1] for rs in nuevos.values() for r in rs), default=None)
    if ult:                                              # el indicador de datos de la página usa ts/asof
        ult = str(ult); S["ts"] = f"{ult[:4]}-{ult[4:6]}-{ult[6:]}T23:59:00"
        S["asof"] = f"{int(ult[6:])}-{['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][int(ult[4:6]) - 1]}-{ult[:4]}"
    S["ajuste"] = {"hasta": max((r[1] for rs in nuevos.values() for r in rs), default=None), "jugadores": cambios,
                   "partidos_equipo": [pj[0], pj[-1]] if pj else None, "k": {"jug": KJ, "dvp": KDVP}}
    return {"jugadores": cambios, "traspasos": traspasos, "partidos": pj}

def guardar(S):
    html = open(PAGINA, encoding="utf-8").read()
    snap = "const SNAP=" + json.dumps(S, ensure_ascii=False, separators=(",", ":")) + ";"
    html = re.sub(r"^const SNAP=.*;$", lambda _: snap, html, count=1, flags=re.M)
    open(PAGINA, "w", encoding="utf-8", newline="").write(html)

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    S = M.load_snap(); H = json.load(open(HIST, encoding="utf-8"))
    r = actualizar(S, H); guardar(S)
    print(f"Actualizados {r['jugadores']} jugadores con partidos de esta temporada; rivales con {r['partidos'][:1]}-{r['partidos'][-1:]} partidos.")
    for t in r["traspasos"]: print("  equipo nuevo:", t)

if __name__ == "__main__": main()
