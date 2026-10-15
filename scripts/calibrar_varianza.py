"""
Calibra la variación del modelo (puntos, rebotes, asistencias, triples, robos, PRA) con historial.json
y comprueba, fuera de muestra, si las probabilidades salen bien calibradas.

Uso (Windows):
    py calibrar_varianza.py "ruta\\historial.json"

Qué hace:
1. AJUSTE: con la 1.a mitad de los partidos de cada jugador (20+ partidos) mide su media y su variación.
   - Conteos (rebotes, asistencias, triples, robos): varianza = r x media  (binomial negativa).
   - Puntos y PRA: desviación = a x media^b  (curva normal).  El modelo viejo usaba b = 1.
2. PRUEBA: con la 2.a mitad (partidos que el ajuste no vio) pone líneas alrededor de la media de la 1.a mitad
   y compara la probabilidad de OVER del modelo con la frecuencia real.  Muestra Brier (más bajo = mejor)
   y una tabla por tramos de probabilidad.  Compara parámetros viejos contra nuevos.
"""
import json, math, sys
from statistics import mean

COL = {"pts": 6, "reb": 7, "ast": 8, "tpm": 9, "stl": 10}
OLD = {"pts": ("sd", .30, 1.0), "pra": ("sd", .25, 1.0), "reb": ("nb", 1.3), "ast": ("nb", 1.4), "tpm": ("nb", 1.2), "stl": ("nb", 1.09)}

def vals(g, k): return [r[6] + r[7] + r[8] for r in g] if k == "pra" else [r[COL[k]] for r in g]
def var(v):
    m = mean(v); return sum((x - m) ** 2 for x in v) / (len(v) - 1)

# --- probabilidades (iguales a las de la página) ---
def Phi(z): return .5 * (1 + math.erf(z / 2 ** .5))
def nb_cdf(k, m, r):                       # P(X <= k), binomial negativa con var = r*m
    if k < 0: return 0.0
    if r <= 1.0001:                        # Poisson
        p, s = math.exp(-m), 0.0
        for i in range(k + 1): s += p; p *= m / (i + 1)
        return s
    p, n = 1 / r, m / (r - 1)              # éxitos n, prob p
    pr, s = p ** n, 0.0
    for i in range(k + 1): s += pr; pr *= (i + n) / (i + 1) * (1 - p)
    return s
def p_over(prm, m, L):                     # L termina en ,5 -> sin push
    if m <= 0: return 0.0
    if prm[0] == "sd":
        sd = prm[1] * m ** prm[2]; return 1 - Phi((math.floor(L) + .5 - m) / sd)
    return 1 - nb_cdf(math.floor(L), m, prm[1])

def main():
    H = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "historial.json", encoding="utf-8"))
    P = [sorted(g, key=lambda r: r[1]) for g in H["p"].values() if len(g) >= 20]
    halves = [(g[:len(g) // 2], g[len(g) // 2:]) for g in P]
    fit, test = halves[0::2], halves[1::2]          # ajuste con la mitad de los jugadores, prueba con la otra mitad
    print(f"Jugadores con 20+ partidos: {len(P)} (ajuste {len(fit)}, prueba {len(test)})")
    print("  'dentro'    = variación de cada jugador alrededor de su propia media (lo que hace un partido cualquiera)")
    print("  'predictiva' = variación de la 2.a mitad alrededor de la media de la 1.a mitad (incluye que la media también se mueve)")

    def fit_params(mode):
        out = {}
        for k in ["pts", "pra", "reb", "ast", "tpm", "stl"]:
            pts = []
            for a, b in fit:
                m = mean(vals(a, k))
                if m <= .3: continue
                v = var(vals(a, k)) if mode == "dentro" else mean((x - m) ** 2 for x in vals(b, k))
                if v > 0: pts.append((m, v))
            if OLD[k][0] == "nb":
                out[k] = ("nb", round(sum(v for _, v in pts) / sum(m for m, _ in pts), 3))
            else:                          # regresión log(sd) = log(a) + b log(media)
                X = [math.log(m) for m, _ in pts]; Y = [.5 * math.log(v) for _, v in pts]
                mx, my = mean(X), mean(Y)
                b = sum((x - mx) * (y - my) for x, y in zip(X, Y)) / sum((x - mx) ** 2 for x in X)
                out[k] = ("sd", round(math.exp(my - b * mx), 3), round(b, 3))
        return out
    SETS = {"viejo": OLD, "dentro": fit_params("dentro"), "predictiva": fit_params("predictiva")}

    print("\n1) PARÁMETROS")
    for k in ["pts", "pra", "reb", "ast", "tpm", "stl"]:
        if OLD[k][0] == "nb": print(f"  {k}: varianza = r x media   r: " + "  ".join(f"{n} {s[k][1]:.2f}" for n, s in SETS.items()))
        else:
            ms = (10, 20, 30) if k == "pts" else (15, 30, 45)
            print(f"  {k}: desviación con media {ms}: " + "  ".join(f"{n} " + "/".join(f"{s[k][1] * m ** s[k][2]:.1f}" for m in ms) for n, s in SETS.items()))

    print("\n2) PRUEBA (jugadores que el ajuste no vio, 2.a mitad de sus partidos).  Líneas = media de la 1.a mitad ±0, ±10%, ±20%")
    for k in ["pts", "pra", "reb", "ast", "tpm", "stl"]:
        res = {n: [] for n in SETS}
        for a, b in test:
            m = mean(vals(a, k))
            if m < .3: continue
            for L in sorted({math.floor(m * f) + .5 for f in (.8, .9, 1, 1.1, 1.2)}):
                ps = {n: p_over(s[k], m, L) for n, s in SETS.items()}
                for x in vals(b, k):
                    for n in SETS: res[n].append((ps[n], 1 if x > L else 0))
        print(f"\n  {k}: Brier (más bajo = mejor)  " + "  ".join(f"{n} {mean((p - y) ** 2 for p, y in r):.4f}" for n, r in res.items()) + f"   ({len(res['viejo'])} casos)")
        print("     prob. modelo | " + " | ".join(f"{n:>10}: predijo -> pasó" for n in SETS))
        for lo in (.1, .2, .3, .4, .5, .6, .7, .8):
            row = []
            for n in SETS:
                s = [(p, y) for p, y in res[n] if lo <= p < lo + .1]
                row.append(f"{mean(p for p, _ in s) * 100:5.1f}% -> {mean(y for _, y in s) * 100:5.1f}% ({len(s):5d})" if len(s) >= 100 else " " * 28)
            print(f"     {lo * 100:3.0f}-{lo * 100 + 10:3.0f}%    | " + " | ".join(row))
    print("\nParámetros:", json.dumps(SETS))

if __name__ == "__main__": main()
