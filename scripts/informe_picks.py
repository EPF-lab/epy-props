"""Informe de los picks automáticos de PICKS (tablas de defensas): cuáles fueron verdes y cuáles no, sin cuotas.

    py scripts/informe_picks.py              (el día de ayer, hora de Caracas)
    py scripts/informe_picks.py 2026-11-22

Lee web/registro.json (picks con v=2). Si el proceso de la madrugada aún no los calificó, los califica aquí con ESPN
(solo en memoria: no cambia el archivo). Escribe docs/informes/picks_AAAA-MM-DD.md e imprime la ruta.
"""
import json, os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diario as DI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LBL = {"pts": "Puntos", "reb": "Rebotes", "ast": "Asistencias", "tpm": "Triples", "pra": "PRA", "ra": "R+A", "pa": "P+A", "pr": "P+R"}
RES = {"W": "Verde", "L": "Roja", "P": "Push", "NJ": "No jugó", None: "Pendiente"}


def rec(L):
    w = sum(e["res"] == "W" for e in L); l = sum(e["res"] == "L" for e in L)
    return f"{w}-{l}" + (f" ({w / (w + l):.0%})" if w + l else ""), w, l


def main():
    caracas = timezone(timedelta(hours=-4))
    f = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(caracas).date() - timedelta(days=1)).isoformat()
    reg = DI.load_reg()
    V2 = [e for e in reg["picks"] if e.get("v") == 2]
    dia = [e for e in V2 if e["fecha"] == f]
    if not dia: raise SystemExit(f"No hay picks automáticos guardados del {f}.")
    if any(e.get("res") is None for e in dia):          # califica en memoria si la madrugada no lo hizo
        box, todos = DI.box_del_dia(f)
        for e in dia:
            if e.get("res") is not None or not box: continue
            s = box.get(DI.key(e["pl"]))
            if s and s.get(e["k"]) is not None:
                e["act"] = s[e["k"]]
                e["res"] = "P" if e["act"] == e["ln"] else "W" if (e["act"] > e["ln"]) == (e["side"] == "O") else "L"
            elif todos: e["res"] = "NJ"
    t, w, l = rec(dia)
    esp = sum(e["pr"] for e in dia if e.get("res") in ("W", "L"))
    out = [f"# Picks automáticos del {f}: {t}", "",
           f"Verdes: {w} · Rojas: {l} · No jugó: {sum(e.get('res') == 'NJ' for e in dia)} · Pendientes: {sum(e.get('res') is None for e in dia)}.",
           f"El modelo esperaba {esp:.1f} verdes en las {w + l} resueltas (suma de sus probabilidades).", ""]
    out += ["| Jugador | Rival | Mercado | Lado | Línea | Proyección | Prob. | Hizo | Resultado |", "|---|---|---|---|---|---|---|---|---|"]
    orden = {"W": 0, "L": 1, "P": 2, "NJ": 3, None: 4}
    for e in sorted(dia, key=lambda e: (orden.get(e.get("res"), 4), -e["pr"])):
        out.append(f"| {e['pl']} | {e['vs']} | {LBL.get(e['k'], e['k'])} | {'Over' if e['side'] == 'O' else 'Under'} | {e['ln']}"
                   f"{'' if e.get('lnreal') else ' (ref.)'} | {e['m']} | {e['pr']:.0%} | {e.get('act', '–') if e.get('act') is not None else '–'} | {RES.get(e.get('res'), e.get('res'))} |")
    out += ["", "## Por grupo (este día)", "", "| Grupo | Récord |", "|---|---|"]
    for nom, fl in [("Over", lambda e: e["side"] == "O"), ("Under", lambda e: e["side"] == "U"),
                    ("Línea real de las casas", lambda e: e.get("lnreal")), ("Línea de referencia", lambda e: not e.get("lnreal")),
                    ("Probabilidad 65 %+", lambda e: e["pr"] >= .65), ("Probabilidad 55-65 %", lambda e: e["pr"] < .65)] + \
                   [(LBL[k], (lambda k: lambda e: e["k"] == k)(k)) for k in LBL]:
        L = [e for e in dia if fl(e)]
        if L: out.append(f"| {nom} | {rec(L)[0]} |")
    acum = [e for e in V2 if e["fecha"] <= f]
    out += ["", f"## Acumulado desde el {min(e['fecha'] for e in V2)}: {rec(acum)[0]}", "",
            "Ref. = línea de referencia (su promedio de la temporada), no la de las casas. Sin cuotas: solo cuenta si se cumplió."]
    os.makedirs(os.path.join(ROOT, "docs", "informes"), exist_ok=True)
    p = os.path.join(ROOT, "docs", "informes", f"picks_{f}.md")
    open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out[:4])); print(p)


if __name__ == "__main__": main()
