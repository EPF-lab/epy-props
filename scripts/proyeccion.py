"""
Guarda la proyección final de un análisis en web/proyecciones.json. Ese día la página la muestra en lugar de la del modelo
(Calculadora, detalle e imagen de captura) y la Calculadora calcula la probabilidad con ella.
Uso:
  py scripts/proyeccion.py "Nolan Traoré" ast 4.7 --rango 4.3 5.3 --vs "Dallas Mavericks" --linea 3.5 --cuota -130 --prob 0.66 --nota "Sin Dëmin ni Brown"
Mercados: pts reb ast tpm stl pra pr pa ra. --fecha AAAA-MM-DD (por defecto hoy). --borrar quita la de ese jugador, mercado y día.
"""
import argparse, json, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

ARCH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "proyecciones.json")
MERCADOS = ("pts", "reb", "ast", "tpm", "stl", "pra", "pr", "pa", "ra")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jugador"); ap.add_argument("mercado", choices=MERCADOS); ap.add_argument("media", type=float, nargs="?")
    ap.add_argument("--rango", type=float, nargs=2); ap.add_argument("--vs"); ap.add_argument("--linea", type=float)
    ap.add_argument("--cuota"); ap.add_argument("--prob", type=float); ap.add_argument("--nota"); ap.add_argument("--fecha", default=date.today().isoformat())
    ap.add_argument("--borrar", action="store_true")
    a = ap.parse_args()
    S = M.load_snap()
    if not any(M.key(p[0]) == M.key(a.jugador) for p in S["players"]): sys.exit(f"No encuentro a {a.jugador} en la página: escribe el nombre como aparece allí.")
    if a.vs and a.vs not in S["teams"]: sys.exit(f"Rival desconocido: {a.vs}. Usa el nombre completo, por ejemplo 'Dallas Mavericks'.")
    try: D = json.load(open(ARCH, encoding="utf-8"))
    except (OSError, ValueError): D = {"v": 1, "p": []}
    mismo = lambda e: e["f"] == a.fecha and e["k"] == a.mercado and M.key(e["pl"]) == M.key(a.jugador)
    D["p"] = [e for e in D["p"] if not mismo(e)]
    if not a.borrar:
        if a.media is None: sys.exit("Falta la media proyectada.")
        e = {"f": a.fecha, "pl": a.jugador, "k": a.mercado, "m": a.media}
        if a.rango: e["lo"], e["hi"] = a.rango
        for c, v in (("vs", a.vs), ("ln", a.linea), ("od", a.cuota), ("pr", a.prob), ("nota", a.nota)):
            if v is not None: e[c] = v
        D["p"].append(e)
    D["p"].sort(key=lambda e: (e["f"], e["pl"], e["k"]))
    json.dump(D, open(ARCH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(("Borrada" if a.borrar else "Guardada") + f": {a.jugador} {a.mercado} {a.fecha} ({len(D['p'])} en el archivo)")

if __name__ == "__main__": main()
