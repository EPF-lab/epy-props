"""
El modelo de la página (web/index.html) en Python, para registrar los picks del día sin abrir la página.
Debe dar los mismos números que el JavaScript: si cambias LAM, CAP, VR, SD o EVMIN en la página, cámbialos aquí.
"""
import json, math, os, re, unicodedata
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAM = {"pts": .7, "reb": .6, "ast": .5, "tpm": .5, "stl": .4}
CAP, EVMIN = .12, .05
SOSP = .15   # EV por encima de esto = "sospechosa" (el modelo probablemente no sabe algo: lesión, rol, minutos)
VR = {"reb": 1.36, "ast": 1.23, "tpm": 1.17, "stl": 1.07}
SD = {"pts": (2.302, .386), "pra": (3.109, .304)}
IDX = {"pts": 0, "ast": 1, "reb": 2, "tpm": 3, "stl": 4}
POS = ["PG", "SG", "SF", "PF", "C"]
# mercados y posiciones de PICKS (igual que MK/PKM en la página)
MK = {"ast": ["PG", "SG"], "reb": ["PG", "SF", "PF", "C"], "pts": ["PG", "SG", "SF", "C"], "tpm": ["PG", "SG"], "stl": ["PG"]}
PKM = ["pts", "ast"]
PMIN = 22

def load_snap():
    for line in open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8"):
        if line.startswith("const SNAP="):
            return json.loads(line[len("const SNAP="):].rstrip().rstrip(";"))
    raise SystemExit("No encontré const SNAP en index.html")

def key(name):
    """Igual que normKey de la página: sin acentos, minúsculas, sin puntuación ni sufijos."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[.'’]", "", s)              # A.J. -> aj, D'Angelo -> dangelo (ESPN y las casas los escriben juntos)
    return " ".join(w for w in re.sub(r"[^a-z0-9 ]", " ", s).split() if w not in ("jr", "sr", "ii", "iii", "iv"))

def base(p, k):
    v = {"pts": p[6], "reb": p[7], "ast": p[8], "tpm": p[11] if len(p) > 11 else None, "stl": p[12] if len(p) > 12 else None}[k]
    return v

class Modelo:
    def __init__(self, S):
        self.S, self.D = S, S["dvp"]
        n = len(self.D)
        self.mean = {p: [sum(t[p][i] for t in self.D.values()) / n for i in range(5)] for p in POS}

    def factor(self, team, pos, k):
        v, m = self.D[team][pos][IDX[k]], self.mean[pos][IDX[k]]
        dev, c = (v - m) / m, self.S["teams"][team][0]
        return 1 + max(-CAP, min(CAP, c * LAM[k] * dev))

    def rank(self, team, pos, k):
        i = IDX[k]; v = self.D[team][pos][i]
        return 1 + sum(1 for x in self.D.values() if x[pos][i] > v)

    def candidatos(self, home, away):
        """Igual que genPicks(): jugadores de 22+ min con posición confirmada, rival 1-5 -> OVER, 26-30 -> UNDER."""
        out = []
        for me, op in ((home, away), (away, home)):
            ab = self.S["teams"][me][1]
            for p in self.S["players"]:
                if not (p[9] and p[5] >= PMIN and p[2] == ab): continue
                for k in PKM:
                    if p[3] not in MK[k]: continue
                    r = self.rank(op, p[3], k)
                    if r <= 5 or r >= 26: out.append({"p": p, "me": me, "op": op, "k": k, "rk": r, "side": "O" if r <= 5 else "U"})
        return out

def Phi(z): return .5 * (1 + math.erf(z / math.sqrt(2)))

def nb_cdf(k, m, v):
    """P(X <= k) con binomial negativa de varianza v*m."""
    if k < 0: return 0.0
    p, n = 1 / v, m / (v - 1)
    pr, s = p ** n, 0.0
    for i in range(k + 1): s += pr; pr *= (i + n) / (i + 1) * (1 - p)
    return min(1.0, s)

def probs(k, m, L):
    """[P(over), P(under)] como probs() de la página."""
    if k in SD:
        a, b = SD[k]; sd = a * m ** b
        return 1 - Phi((math.floor(L) + .5 - m) / sd), Phi((math.ceil(L) - .5 - m) / sd)
    v = VR[k]
    return 1 - nb_cdf(math.floor(L), m, v), nb_cdf(math.ceil(L) - 1, m, v)

def mk_line(books):
    """Línea más común entre casas (desempate como Object.keys de JS) y cuotas medianas en esa línea."""
    if not books: return None
    c = OrderedDict()
    ints = sorted({b["ln"] for b in books if float(b["ln"]).is_integer() and b["ln"] >= 0})
    for l in ints: c[l] = 0
    for b in books: c[b["ln"]] = c.get(b["ln"], 0) + 1
    ln = sorted(c, key=lambda l: -c[l])[0]
    at = [b for b in books if b["ln"] == ln]
    def med(v):
        s = sorted(x for x in v if x and x > 1); n = len(s)
        return None if not n else (s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)
    return {"ln": ln, "o": med(b.get("o") for b in at), "u": med(b.get("u") for b in at), "n": len(at)}

def evaluar(M, x, books):
    """Como pickEV(): proyección, línea del mercado, probabilidad del lado, EV a la cuota del mercado y cuota mínima."""
    b = base(x["p"], x["k"])
    if b is None: return None
    m = b * M.factor(x["op"], x["p"][3], x["k"])
    ml = mk_line(books)
    out = {"base": round(b, 2), "m": round(m, 3)}
    if not ml: return out
    po, pu = probs(x["k"], m, ml["ln"])
    pw, pl = (po, pu) if x["side"] == "O" else (pu, po)
    od = ml["o"] if x["side"] == "O" else ml["u"]
    ev = pw * (od - 1) - pl if od and od > 1 else None
    out.update({"ln": ml["ln"], "o": ml["o"], "u": ml["u"], "nb": ml["n"], "pw": round(pw, 4),
                "ev": None if ev is None else round(ev, 4), "min": round(1 + (EVMIN + pl) / pw, 3) if pw > 0 else None,
                "sel": ev is not None and ev >= EVMIN, "sos": ev is not None and ev > SOSP})
    return out
