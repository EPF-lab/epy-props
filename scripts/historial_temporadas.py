"""
Agrega temporadas anteriores (solo temporada regular) a web/historial.json con los boxscores de ESPN (gratis).
Sirve para que el gráfico tenga más enfrentamientos contra un mismo rival.

Uso:  py historial_temporadas.py              (2024-25)
      py historial_temporadas.py 2024-10-22 2025-04-14
Es reanudable: guarda el avance cada 10 días y no repite los días ya cargados.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diario as D, modelo as M  # noqa: E402

TRAMOS = [("2024-10-22", "2025-04-14")]   # temporada regular 2024-25 (lo más atrás que se usa)

def main():
    tramos = [(sys.argv[1], sys.argv[2])] if len(sys.argv) == 3 else TRAMOS
    S = M.load_snap()
    for desde, hasta in tramos:
        n, dias = D.actualizar_historial(S, hasta, desde=desde, pausa=0.15)
        print(f"{desde} a {hasta}: {n} partidos de jugador nuevos en {len(dias)} días", flush=True)

if __name__ == "__main__": main()
