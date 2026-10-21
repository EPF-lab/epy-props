"""
Convierte data/movimientos_offseason_2026.csv en web/movimientos.json para la tarjeta "Contexto del rol" de PICKS.
Formato: {"MEM": {"in": [["Jerami Grant", 18.6], ...], "out": [["Ja Morant", 19.5], ...]}, ...}
(ordenados por puntos del año pasado; las renovaciones no se incluyen).

Uso:  py movimientos_json.py      (vuelve a correrlo si actualizas el CSV de movimientos)
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = os.path.join(ROOT, "data", "movimientos_offseason_2026.csv"), os.path.join(ROOT, "web", "movimientos.json")

def num(v):
    try: return float(str(v).replace(",", "."))
    except ValueError: return None

def main():
    pts = {M.key(p[0]): p[6] for p in M.load_snap()["players"]}   # si el CSV no trae puntos, se usan los de la página
    out = {}
    for r in csv.DictReader(open(SRC, encoding="utf-8-sig")):
        lado = {"Llegada": "in", "Salida": "out"}.get(r["Tipo"])
        if not lado: continue
        out.setdefault(r["Equipo"], {"in": [], "out": []})[lado].append([r["Jugador"], num(r.get("PTS_25-26")) or pts.get(M.key(r["Jugador"]))])
    for t in out.values():
        for k in t: t[k].sort(key=lambda z: -(z[1] or 0))
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out)} equipos -> {OUT}")

if __name__ == "__main__": main()
