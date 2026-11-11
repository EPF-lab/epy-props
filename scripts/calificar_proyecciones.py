"""
Califica las proyecciones del análisis (web/proyecciones.json) con lo que hizo el jugador: act (su número) y res (W/L/P; NJ = no jugó).
Lo corre diario.py cada madrugada; también se puede correr a mano:  py scripts/calificar_proyecciones.py
Marcar una jugada como oficial (la que el usuario jugó):  py scripts/calificar_proyecciones.py --jugada "Nolan Traoré" ast 2026-11-08
"""
import argparse, json, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(RAIZ, "web", "proyecciones.json"); HIST = os.path.join(RAIZ, "web", "historial.json")
VAL = {"pts": lambda s: s["pts"], "reb": lambda s: s["reb"], "ast": lambda s: s["ast"], "tpm": lambda s: s["tpm"], "stl": lambda s: s["stl"],
       "pra": lambda s: s["pts"] + s["reb"] + s["ast"], "pr": lambda s: s["pts"] + s["reb"], "pa": lambda s: s["pts"] + s["ast"], "ra": lambda s: s["reb"] + s["ast"]}

def calificar(hoy, box_del_dia=None):
    """Pone act/res a las proyecciones de días anteriores sin resultado. box_del_dia (de diario.py) cubre lo que el historial aún no tiene."""
    try: D = json.load(open(ARCH, encoding="utf-8"))
    except (OSError, ValueError): return 0
    S = M.load_snap(); H = json.load(open(HIST, encoding="utf-8"))
    pid = {M.key(p[0]): str(p[10]) for p in S["players"] if p[10]}
    cache, n = {}, 0
    for e in D["p"]:
        if e.get("res") or e["f"] >= hoy or e.get("ln") is None: continue
        d = int(e["f"].replace("-", "")); s = None
        r = [x for x in H["p"].get(pid.get(M.key(e["pl"]), ""), []) if x[1] == d]
        if r: s = {"pts": r[0][6], "reb": r[0][7], "ast": r[0][8], "tpm": r[0][9], "stl": r[0][10]}
        elif box_del_dia:
            if e["f"] not in cache: cache[e["f"]] = box_del_dia(e["f"])
            box, todos = cache[e["f"]]
            s = (box or {}).get(M.key(e["pl"]))
            if s is None and (todos or (date.fromisoformat(hoy) - date.fromisoformat(e["f"])).days >= 3): e["res"] = "NJ"; n += 1; continue
        if s is None: continue
        e["act"] = VAL[e["k"]](s); e["res"] = "P" if e["act"] == e["ln"] else "W" if e["act"] > e["ln"] else "L"; n += 1
    if n: json.dump(D, open(ARCH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return n

def resumen():
    D = json.load(open(ARCH, encoding="utf-8"))
    for titulo, L in (("Jugadas oficiales", [e for e in D["p"] if e.get("jug")]), ("Todos los análisis", D["p"])):
        r = [e for e in L if e.get("res") in ("W", "L")]; w = sum(e["res"] == "W" for e in r)
        print(f"{titulo}: {w} ganadas, {len(r) - w} perdidas" + (f" ({w / len(r):.0%})" if r else "") + f", {sum(not e.get('res') for e in L)} pendientes")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--jugada", nargs=3, metavar=("JUGADOR", "MERCADO", "FECHA"), action="append")
    a = ap.parse_args()
    if a.jugada:
        D = json.load(open(ARCH, encoding="utf-8"))
        for pl, k, f in a.jugada:
            e = next((x for x in D["p"] if x["f"] == f and x["k"] == k and M.key(x["pl"]) == M.key(pl)), None)
            if not e: sys.exit(f"No hay proyección de {pl} {k} el {f}")
            e["jug"] = True; print("Oficial:", pl, k, f)
        json.dump(D, open(ARCH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import diario
    hoy = (date.today()).isoformat()
    print("Calificadas:", calificar(hoy, diario.box_del_dia)); resumen()

if __name__ == "__main__": main()
