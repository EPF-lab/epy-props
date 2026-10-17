"""
Backtest de la regla de PICKS (DvP) contra LÍNEAS REALES de cierre de las casas (DunkAPI, get_prop_history).

Uso (Windows):
    py backtest_dunkapi.py --estimar          (no gasta créditos: muestra qué pediría)
    py backtest_dunkapi.py                    (pide los datos, con un tope de créditos; guarda todo en data/dunkapi_cache)
    py backtest_dunkapi.py --creditos 450 --ultimos 20

Clave: variable de entorno DUNKAPI_API_KEY (de usuario en Windows). Nunca se escribe en el repositorio.

Qué hace:
1. Con historial.json reconstruye el DvP de cada día (solo partidos anteriores) y simula PICKS en los
   últimos N partidos de cada jugador (igual que backtest_dvp_gratis.py).
2. Elige los pares (jugador, mercado) con más jugadas DvP en esa ventana, hasta el tope de créditos
   (buscar jugador = 1 crédito; historial de su línea = 10 créditos por mercado).
3. Para esos pares baja, partido a partido, la línea de CIERRE (mediana entre casas), las cuotas y el resultado.
4. Compara el % de acierto de las jugadas con DvP contra la línea real con: (a) las mismas jugadas sin filtro
   y (b) la probabilidad implícita de la cuota sin margen. La diferencia (b) es la ventaja frente a la casa.
"""
import argparse, json, math, os, re, sys, time, unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_dvp_gratis import COL, MK, NOMBRE, ROOT, MIN_PREV_JUGADOR, snap, wilson, dvp_rank  # noqa: E402

API = "https://mcp.dunkapi.com/v1/"
CACHE = os.path.join(ROOT, "data", "dunkapi_cache")
MARKET = {"pts": "player_points", "reb": "player_rebounds", "ast": "player_assists", "tpm": "player_threes", "stl": "player_steals"}

def api_key():
    k = os.environ.get("DUNKAPI_API_KEY", "").strip()
    if not k and os.name == "nt":                     # variable de usuario guardada con setx / SetEnvironmentVariable
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h: k = winreg.QueryValueEx(h, "DUNKAPI_API_KEY")[0].strip()
        except OSError: pass
    return k

def norm(s):
    s = unicodedata.normalize("NFKD", s); s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(w for w in re.sub(r"[^a-z0-9 ]", " ", s).split() if w not in ("jr", "sr", "ii", "iii", "iv"))

def call(tool, body, key):
    """POST con caché en disco: la misma consulta nunca se paga dos veces."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, tool + "_" + re.sub(r"[^A-Za-z0-9_-]", "_", "_".join(f"{k}-{v}" for k, v in sorted(body.items()))) + ".json")
    if os.path.exists(f): return json.load(open(f, encoding="utf-8")), 0
    import requests
    for att in range(3):
        r = requests.post(API + tool, json=body, headers={"x-api-key": key, "Content-Type": "application/json"}, timeout=60)
        if r.status_code == 429: time.sleep(10 * (att + 1)); continue
        if r.status_code != 200: raise SystemExit(f"DunkAPI {tool} -> {r.status_code}: {r.text[:300]}")
        d = r.json(); json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False); return d, 1
    raise SystemExit("DunkAPI: demasiados intentos (límite de velocidad)")

def dec(o):
    """Cuota decimal desde americana o decimal."""
    if o is None: return None
    o = float(o)
    if abs(o) >= 100: return 1 + o / 100 if o > 0 else 1 + 100 / -o
    return o if o > 1 else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ultimos", type=int, default=20); ap.add_argument("--creditos", type=int, default=450)
    ap.add_argument("--estimar", action="store_true"); a = ap.parse_args()
    H = json.load(open(os.path.join(ROOT, "web", "historial.json"), encoding="utf-8")); S = snap()
    info = {str(p[10]): p for p in S["players"] if p[10]}
    pos_of = {pid: info[pid][3] for pid in H["p"] if pid in info}
    rank_at = dvp_rank(H, pos_of)

    # jugadas de la ventana (como en PICKS) por par (jugador, mercado)
    win = defaultdict(list)                           # (pid, k) -> [(fecha, valor real, lado DvP o None)]
    for pid, games in H["p"].items():
        p = info.get(pid)
        if not p or not p[9] or p[5] < 22: continue
        games = sorted(games, key=lambda r: r[1])
        for j in range(max(MIN_PREV_JUGADOR, len(games) - a.ultimos), len(games)):
            r = games[j]
            for k, poss in MK.items():
                if p[3] not in poss: continue
                rk = rank_at.get((r[1], r[3], p[3], k))
                win[(pid, k)].append((r[1], r[COL[k]], "O" if rk and rk <= 5 else "U" if rk and rk >= 26 else None))
    pares = sorted(win, key=lambda pk: -sum(1 for x in win[pk] if x[2]))
    # elegir pares hasta el tope: 1 crédito por jugador nuevo + 10 por mercado
    plan, gasto, vistos = [], 0, set()
    for pid, k in pares:
        if not sum(1 for x in win[(pid, k)] if x[2]): break
        c = 10 + (0 if pid in vistos else 1)
        if gasto + c > a.creditos: continue
        plan.append((pid, k)); gasto += c; vistos.add(pid)
    n_dvp = sum(sum(1 for x in win[pk] if x[2]) for pk in plan)
    print(f"Plan: {len(plan)} pares jugador-mercado, {len(vistos)} jugadores, ~{gasto} créditos (si no están en caché); {n_dvp} jugadas con DvP en la ventana.")
    for pid, k in plan[:12]: print(f"   {info[pid][0]:28} {NOMBRE[k]:12} {sum(1 for x in win[(pid, k)] if x[2])} jugadas DvP")
    if a.estimar: return
    key = api_key()
    if not key: raise SystemExit("Falta la clave: guarda DUNKAPI_API_KEY como variable de entorno de usuario.")

    # 1) id de DunkAPI (ESPN) de cada jugador  2) historial de línea por mercado
    first = min(d for pk in plan for d, _, _ in win[pk]); fd = f"{str(first)[:4]}-{str(first)[4:6]}-{str(first)[6:]}"
    ids, pagadas = {}, 0
    for pid in vistos:
        d, n = call("search_players", {"name": info[pid][0], "limit": 5}, key); pagadas += n
        cands = d.get("data", {}).get("players", [])
        hit = next((c for c in cands if norm(str(c.get("name") or c.get("full_name") or c.get("display_name") or "")) == norm(info[pid][0])), cands[0] if cands else None)
        if hit: ids[pid] = str(hit.get("id") or hit.get("player_id"))
    lines = {}
    for pid, k in plan:
        if pid not in ids: continue
        d, n = call("get_prop_history", {"player_id": ids[pid], "market": MARKET[k], "from_date": fd, "to_date": "2026-04-30", "limit": 200}, key); pagadas += n
        for g in d.get("data", {}).get("games", []):
            if g.get("line") is None or not g.get("game_date"): continue
            lines[(pid, k, int(g["game_date"][:10].replace("-", "")))] = g
    print(f"Consultas nuevas pagadas: {pagadas}. Partidos con línea real: {len(lines)}.")

    # 3) evaluar
    res = defaultdict(lambda: {"sel": [0, 0, 0.0, 0], "ctl": [0, 0]})   # sel: aciertos, n, suma prob. implícita, n con cuota
    for (pid, k), rows in win.items():
        if (pid, k) not in plan: continue
        for d, x, lado in rows:
            g = lines.get((pid, k, d))
            if not g: continue
            L = float(g["line"]); act = g.get("actual", x)
            act = x if act is None else act
            if act == L: continue                                    # push: no cuenta
            for sd in ("O", "U"):
                c = res[(k, sd)]["ctl"]; c[0] += (act > L) if sd == "O" else (act < L); c[1] += 1
            if lado:
                s = res[(k, lado)]["sel"]; s[0] += (act > L) if lado == "O" else (act < L); s[1] += 1
                oo, uu = dec(g.get("over_odds")), dec(g.get("under_odds"))
                if oo and uu:
                    io, iu = 1 / oo, 1 / uu; s[2] += (io if lado == "O" else iu) / (io + iu); s[3] += 1
    pc = lambda h, n: f"{100 * h / n:5.1f}%" if n else "   – "
    print(f"\n=== Contra la LÍNEA REAL de cierre — últimos {a.ultimos} partidos (pares elegidos) ===")
    print(f"{'Mercado':12} {'Lado':5} | {'con DvP':>8} {'n':>4} {'IC 95%':>10} | {'sin filtro':>10} {'n':>5} | {'prob. casa':>10} | {'ventaja':>8}")
    T = [0, 0, 0.0, 0]; C = [0, 0]
    for k in MK:
        for sd in ("O", "U"):
            s, c = res[(k, sd)]["sel"], res[(k, sd)]["ctl"]
            if not s[1]: continue
            lo, hi = wilson(s[0], s[1]); imp = s[2] / s[3] if s[3] else None
            print(f"{NOMBRE[k]:12} {('OVER' if sd == 'O' else 'UNDER'):5} | {pc(s[0], s[1]):>8} {s[1]:4d} {f'{100*lo:.0f}-{100*hi:.0f}%':>10} | {pc(*c):>10} {c[1]:5d} | "
                  f"{(f'{100*imp:5.1f}%' if imp else '   –'):>10} | {(f'{100*(s[0]/s[1]-imp):+6.1f} pp' if imp else '   –'):>8}")
            for i in range(4): T[i] += s[i]
            C[0] += c[0]; C[1] += c[1]
    if T[1]:
        lo, hi = wilson(T[0], T[1]); imp = T[2] / T[3] if T[3] else None
        print(f"{'TOTAL':12} {'':5} | {pc(T[0], T[1]):>8} {T[1]:4d} {f'{100*lo:.0f}-{100*hi:.0f}%':>10} | {pc(*C):>10} {C[1]:5d} | "
              f"{(f'{100*imp:5.1f}%' if imp else '   –'):>10} | {(f'{100*(T[0]/T[1]-imp):+6.1f} pp' if imp else '   –'):>8}")
    print("\n'prob. casa' = probabilidad implícita del lado del pick en la cuota de cierre, sin margen. 'ventaja' = acierto real menos esa probabilidad.")
    print("Referencia: con cuota 1,91 hace falta 52,4 % de acierto para no perder.")

if __name__ == "__main__": main()
