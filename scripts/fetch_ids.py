"""
Saca el ID oficial de cada jugador para mostrar su foto actual (versión 2).
Uso:   py fetch_ids.py "EPY NBA - Jugadores.csv"      (usa el nombre real de tu archivo, entre comillas)
Crea:  jugadores_ids.csv  (Jugador, PLAYER_ID)
Mejora frente a la v1: ignora sufijos (Jr., II, III) y prueba una coincidencia aproximada
por inicial del nombre + apellido cuando es única (te la muestra para que la revises).
"""
import sys, csv, re, unicodedata
from nba_api.stats.static import players

SUF = {"jr", "sr", "ii", "iii", "iv", "v"}
def fix(s):                                   # repara acentos rotos
    try: return s.encode("latin1").decode("utf-8")
    except Exception: return s
def words(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    w = [re.sub(r"[^a-z0-9]", "", x) for x in s.split()]
    return [x for x in w if x and x not in SUF]
def key(s): return "".join(words(s))

lista = sorted(players.get_players(), key=lambda p: not p["is_active"])   # activos primero
exact, short = {}, {}
for p in lista:
    exact.setdefault(key(p["full_name"]), (p["id"], p["full_name"]))
    w = words(p["full_name"])
    if len(w) >= 2: short.setdefault((w[0][0], w[-1]), []).append((p["id"], p["full_name"]))

src = sys.argv[1] if len(sys.argv) > 1 else "EPY_NBA_-_Jugadores.csv"
out, miss, seen, approx = [], [], set(), []
for row in csv.DictReader(open(src, encoding="utf-8")):
    name = fix(row["Jugador"]).strip()
    if name in seen or name == "League Average": continue
    seen.add(name)
    hit = exact.get(key(name))
    if not hit:
        w = words(name)
        c = short.get((w[0][0], w[-1])) if len(w) >= 2 else None
        if c and len(c) == 1: hit = c[0]; approx.append((name, c[0][1]))
    (out if hit else miss).append([name, hit[0] if hit else ""])
with open("jugadores_ids.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["Jugador", "PLAYER_ID"]); w.writerows(out + miss)
print(f"{len(out)} jugadores con ID, {len(miss)} sin coincidencia")
for a, b in approx: print(f"  aproximado: {a}  ->  {b}   (revisa que sea el mismo)")
for m in miss: print("  sin ID:", m[0])
