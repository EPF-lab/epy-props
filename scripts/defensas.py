"""Tablas de defensas: qué concede cada equipo a cada posición, comparado con lo normal de cada jugador.

Método (el del informe técnico del 22-nov-2026): para cada partido de 20+ minutos de esta temporada,
"esperado" = ritmo por minuto del jugador contra los DEMÁS rivales x minutos que jugó contra este.
Factor = real / esperado, sumado por equipo rival, posición y mercado.

Escribe web/defensas.json, que lee la pestaña PICKS. Lo corre diario.py cada madrugada, así que las tablas
se rehacen solas con los partidos nuevos.

    py scripts/defensas.py            (rehace web/defensas.json con web/historial.json)
"""
import json, math, os, statistics as st
from datetime import date

import modelo as M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "web", "historial.json")
OUT = os.path.join(ROOT, "web", "defensas.json")
DESDE = int(os.environ.get("TEMPORADA_INICIO", "2026-10-20").replace("-", ""))

# columnas de historial.json: [gid, fecha, eq, rival, local, min, pts, reb, ast, tpm, stl, fgm, fga, 3pa, ftm, fta]
COL = {"pts": 6, "reb": 7, "ast": 8, "tpm": 9, "3pa": 13}
COMBO = {"pra": ("pts", "reb", "ast"), "ra": ("reb", "ast"), "pa": ("pts", "ast"), "pr": ("pts", "reb")}
MERCADOS = ["pts", "reb", "ast", "tpm", "pra", "ra", "pa", "pr", "3pa"]
APUESTA = ["pts", "reb", "ast", "tpm", "pra", "ra", "pa", "pr"]       # 3pa se muestra, pero no es mercado de apuesta

MIN_CASO, MIN_RESTO = 20, 100          # partido de 20+ min; el jugador necesita 100+ min ante otros rivales
N_MIN = 12                             # casos mínimos para que una tabla cuente
MAS = dict(f=1.15, sup=.55, f2=1.05, u8=1.0)     # "permite más": fuerte, la mayoría supera, sigue vigente
MENOS = dict(f=.87, sup=.40, f2=.95, u8=1.0)     # "permite menos"
PESO = .6                              # parte del factor que se usa en la proyección (60 %, como en los análisis)
TOPE = .25                             # el ajuste del rival nunca pasa de +-25 %
ENCOGE = .75                           # el modelo es demasiado seguro lejos de la línea: la probabilidad se acerca un 25 % a 50 %
PMIN_PICK = .55                        # probabilidad mínima (ya encogida) para que salga como pick


def val(r, k):
    if k in COMBO: return sum(r[COL[c]] for c in COMBO[k])
    return r[COL[k]] if len(r) > COL[k] else None


def tablas(H, S):
    pos = {str(p[10]): p[3] for p in S["players"]}
    nom = {str(p[10]): p[0] for p in S["players"]}
    G = {}
    for pid, rows in H["p"].items():
        if pid not in pos: continue
        rows = [r for r in rows if r[1] >= DESDE and r[5] > 0]
        if len(rows) < 5: continue
        tmin = sum(r[5] for r in rows)
        for k in MERCADOS:
            rk = [r for r in rows if val(r, k) is not None]
            if len(rk) < 5: continue
            tot, tm = sum(val(r, k) for r in rk), sum(r[5] for r in rk)
            for r in rk:
                if r[5] < MIN_CASO or tm - r[5] < MIN_RESTO: continue
                e = (tot - val(r, k)) / (tm - r[5]) * r[5]
                G.setdefault((r[3], pos[pid], k), []).append([r[1], nom[pid], r[5], val(r, k), round(e, 2)])
    return G


def resumen(v):
    v = sorted(v, key=lambda x: x[0]); n = len(v)
    f = lambda s: sum(x[3] for x in s) / max(sum(x[4] for x in s), .1)
    a, e = sum(x[3] for x in v), sum(x[4] for x in v)
    sup = sum(x[3] > x[4] for x in v)
    h = n // 2
    return dict(n=n, a=a, e=round(e, 1), f=round(f(v), 3), sup=sup, f1=round(f(v[:h]), 3), f2=round(f(v[h:]), 3), u8=round(f(v[-8:]), 3))


def estado(s, k):
    if s["n"] < N_MIN or s["e"] < 5 or k == "3pa": return ""
    q = s["sup"] / s["n"]
    if s["f"] >= MAS["f"] and q >= MAS["sup"] and s["f2"] >= MAS["f2"] and s["u8"] >= MAS["u8"]: return "mas"
    if s["f"] <= MENOS["f"] and q <= MENOS["sup"] and s["f2"] <= MENOS["f2"] and s["u8"] <= MENOS["u8"]: return "menos"
    return ""


def jugadores(H, S):
    """Minutos recientes y ritmo por minuto de esta temporada de cada jugador de la página."""
    out = {}
    for p in S["players"]:
        pid = str(p[10]); rows = sorted([r for r in H["p"].get(pid, []) if r[1] >= DESDE and r[5] > 0], key=lambda r: r[1])
        if len(rows) < 3: continue
        tm = sum(r[5] for r in rows); m10 = [r[5] for r in rows[-10:]]
        rate = {k: round(sum(val(r, k) for r in rows if val(r, k) is not None) / tm, 4) for k in MERCADOS}
        pj = {k: round(sum(val(r, k) for r in rows if val(r, k) is not None) / len(rows), 2) for k in MERCADOS}
        out[pid] = dict(g=len(rows), mn5=round(st.mean(r[5] for r in rows[-5:]), 1), mns=round(tm / len(rows), 1),
                        sd=round(st.pstdev(m10), 1), r=rate, pj=pj, ult=rows[-1][1])
    return out


def proyectar(j, k, f):
    """Ritmo por minuto x minutos esperados (60 % recientes, 40 % temporada) x parte del factor del rival."""
    mins = .6 * j["mn5"] + .4 * j["mns"]
    aj = max(-TOPE, min(TOPE, PESO * (f - 1)))
    return j["r"][k] * mins * (1 + aj), mins


def linea_ref(j, k):
    """Línea parecida a la que pondría la casa: su promedio de la temporada, al .5 de abajo."""
    return math.floor(j["pj"][k] - .3) + .5


def construir():
    S = M.load_snap(); H = json.load(open(HIST, encoding="utf-8"))
    G = tablas(H, S)
    eq, filas = {}, {}
    for (t, ps, k), v in G.items():
        s = resumen(v); s["est"] = estado(s, k)
        eq.setdefault(t, {}).setdefault(ps, {})[k] = [s[c] for c in ("n", "a", "e", "f", "sup", "f1", "f2", "u8", "est")]
        if s["est"]: filas[f"{t}|{ps}|{k}"] = sorted(v, key=lambda x: -x[0])
    ult = max(r[1] for rows in H["p"].values() for r in rows)
    return {"v": 1, "asof": f"{str(ult)[:4]}-{str(ult)[4:6]}-{str(ult)[6:]}", "desde": DESDE,
            "cols": ["n", "real", "esperado", "factor", "superaron", "f_1a_mitad", "f_2a_mitad", "f_ultimos8", "estado"],
            "reglas": {"mas": MAS, "menos": MENOS, "n_min": N_MIN, "peso": PESO, "tope": TOPE, "min_caso": MIN_CASO, "encoge": ENCOGE, "pmin": PMIN_PICK},
            "eq": eq, "filas": filas, "jug": jugadores(H, S)}


def picks_del_dia(D, S, juegos, les=None, lineas=None):
    """Los mismos picks que muestra la pestaña PICKS: jugadores de hoy x tablas de 'permite más' / 'permite menos'."""
    ab = {t: v[1] for t, v in S["teams"].items()}
    out = []
    for j in juegos:
        for me, op in ((j["local"], j["visitante"]), (j["visitante"], j["local"])):
            if me not in ab or op not in ab: continue
            fuera = {M.key(l[0]) for l in (les or {}).get(me, []) if str(l[1]).lower().startswith("out")}
            for p in S["players"]:
                if p[2] != ab[me] or not p[9] or M.key(p[0]) in fuera: continue
                jg = D["jug"].get(str(p[10]))
                if not jg or jg["mn5"] < 22: continue
                for k in APUESTA:
                    t = D["eq"].get(ab[op], {}).get(p[3], {}).get(k)
                    if not t or not t[8]: continue
                    side = "O" if t[8] == "mas" else "U"
                    if k == "tpm" and jg["pj"]["tpm"] < (1.2 if side == "O" else 1.5): continue    # solo tiradores de verdad
                    m, mins = proyectar(jg, k, t[3])
                    bk = ((lineas or {}).get(M.key(p[0])) or {}).get(k) or []
                    ln = None
                    if bk:
                        c = {}
                        for r in bk: c[r["ln"]] = c.get(r["ln"], 0) + 1
                        ln = max(c, key=c.get)
                    real = ln is not None
                    if ln is None: ln = linea_ref(jg, k)
                    if ln <= 0: continue
                    po, pu = M.probs(k, m, ln)
                    pw = .5 + ENCOGE * ((po if side == "O" else pu) - .5)
                    if pw < PMIN_PICK: continue
                    out.append(dict(pl=p[0], pid=str(p[10]), eq=me, vs=op, pos=p[3], k=k, side=side, ln=ln, lnreal=real,
                                    m=round(m, 2), mins=round(mins, 1), pr=round(pw, 3), f=t[3], n=t[0], sup=t[4], hora=j.get("hora"),
                                    local=me == j["local"]))
    # una sola jugada por jugador y noche (regla 7 del informe): la de mayor probabilidad
    mejor = {}
    for x in out:
        if x["pid"] not in mejor or x["pr"] > mejor[x["pid"]]["pr"]: mejor[x["pid"]] = x
    return sorted(mejor.values(), key=lambda x: -x["pr"])


if __name__ == "__main__":
    D = construir()
    json.dump(D, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    n = sum(1 for t in D["eq"].values() for ps in t.values() for v in ps.values() if v[8])
    print(f"defensas.json: {len(D['eq'])} equipos, {n} tablas con señal ({len(D['filas'])} con filas), {len(D['jug'])} jugadores, al {D['asof']}")
