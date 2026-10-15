"""
Descarga las fotos de los jugadores y crea fotos.json, para que SALGAN en las imágenes de compartir.
(Las fotos que ves en la página se cargan directo de internet, pero el navegador no deja usarlas para
 generar una imagen; por eso se guardan aquí, en miniatura, dentro de un archivo.)

Uso (Windows):
    py -m pip install pillow
    py fetch_fotos.py --jugadores "TU CSV DE JUGADORES" --ids jugadores_ids.csv
Opciones:  --min 15  (solo jugadores con 15 o más minutos)   --salida fotos.json
Es reanudable: guarda cada foto en la carpeta 'cache_fotos'. Si se corta, vuelve a correrlo.
"""
import argparse, base64, csv, io, json, os, re, sys, time, unicodedata, urllib.request

URL = "https://cdn.nba.com/headshots/nba/latest/260x190/{}.png"

def fix(s):
    try: return s.encode("latin1").decode("utf-8")
    except Exception: return s
def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())

def load_players(jug_csv, ids_csv, minmin):
    ids = {}
    for row in csv.DictReader(open(ids_csv, encoding="utf-8-sig")):
        if row["PLAYER_ID"].strip(): ids[norm(fix(row["Jugador"]))] = (fix(row["Jugador"]), row["PLAYER_ID"].strip().split(".")[0])
    mins = {}
    for row in csv.DictReader(open(jug_csv, encoding="utf-8-sig")):
        if row.get("TEAM_ABBREVIATION") == "0": continue
        try: m = float(str(row["MIN"]).replace(",", "."))
        except (ValueError, KeyError): continue
        n = norm(fix(row["Jugador"])); mins[n] = max(mins.get(n, 0), m)
    return [ids[n] for n, m in mins.items() if n in ids and m >= minmin]

def encode(raw):
    """Miniatura con transparencia, lo más liviana posible (WEBP; si no, PNG)."""
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGBA"); im.thumbnail((170, 124))
    b = io.BytesIO()
    try: im.save(b, "WEBP", quality=82); mime = "image/webp"
    except Exception: b = io.BytesIO(); im.save(b, "PNG", optimize=True); mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(b.getvalue()).decode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jugadores", default="EPY_NBA_-_Jugadores.csv"); ap.add_argument("--ids", default="jugadores_ids.csv")
    ap.add_argument("--min", type=float, default=15); ap.add_argument("--salida", default="fotos.json"); a = ap.parse_args()
    try: import PIL  # noqa
    except ImportError: sys.exit("Falta Pillow. Corre primero:  py -m pip install pillow")
    players = load_players(a.jugadores, a.ids, a.min); os.makedirs("cache_fotos", exist_ok=True)
    print(f"{len(players)} fotos a descargar."); out, fails = {}, []
    for i, (name, pid) in enumerate(players, 1):
        cf = os.path.join("cache_fotos", pid + ".txt")
        if os.path.exists(cf): out[pid] = open(cf).read(); continue
        for att in range(3):
            try:
                req = urllib.request.Request(URL.format(pid), headers={"User-Agent": "Mozilla/5.0"})
                du = encode(urllib.request.urlopen(req, timeout=20).read()); open(cf, "w").write(du); out[pid] = du; break
            except Exception as e:
                if att == 2: fails.append((name, str(e)[:70]))
                else: time.sleep(1.5)
        time.sleep(0.15)
        if i % 25 == 0 or i == len(players): print(f"  {i}/{len(players)}")
    with open(a.salida, "w", encoding="utf-8") as f: json.dump({"v": 1, "p": out}, f, separators=(",", ":"))
    print(f"Listo: {len(out)} fotos, {os.path.getsize(a.salida)/1e6:.1f} MB -> {a.salida}")
    for fl in fails: print("  sin foto:", *fl)

if __name__ == "__main__": main()
