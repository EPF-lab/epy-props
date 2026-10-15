import pandas as pd, numpy as np, re, unicodedata
def norm(s):
    s=unicodedata.normalize("NFKD",str(s)); s="".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]","",s.lower())
# PARÁMETROS (a calibrar con histórico; son supuestos de partida)
DAMP=0.30      # qué parte de la producción neta que dejan/aportan los movimientos se traslada a los que se quedan
CAP=0.06       # tope del ajuste: ±6% del promedio del jugador
ARR_W=0.60     # los que llegan no replican toda su producción (comparten balón)
HEAD=40.0      # minutos máximos por juego de referencia: quien ya juega ~35+ tiene poco margen para absorber
MINW=10
P=pd.read_pickle("P.pkl"); P=P[P.key!="leagueaverage"].copy()
for k,t in {"jordanhawkins":"MEM","kamjones":"CHI","camwhitmore":"CLE","garyharris":"DET"}.items():
    P.loc[P.key==k,["Equipo_2627","Movimiento"]]=[t,"Cambió de equipo"]
P["Equipo_2627"]=P.Equipo_2627.fillna("SIN EQUIPO")
J=pd.read_pickle("jug.pkl"); J["key"]=J.Jugador.map(norm)
AGG={"2TM","3TM","4TM","0"}
rows=J[(~J.TEAM_ABBREVIATION.isin(AGG))&(J.MIN>=MINW)&(J.key!="leagueaverage")].copy()
rows["cur"]=rows.key.map(P.set_index("key").Equipo_2627)
teams=sorted(rows.TEAM_ABBREVIATION.unique())
for s in ["PTS","REB","AST"]: P[f"adj_{s}"]=0.0
for t in teams:
    prev=rows[rows.TEAM_ABBREVIATION==t]; dep=prev[prev.cur!=t]
    now=P[(P.Equipo_2627==t)&(P.MIN>=MINW)]
    arrv=now[~now.key.isin(set(prev.key))]; ret=now[now.key.isin(set(prev.key))]
    for s in ["PTS","REB","AST"]:
        net=ARR_W*arrv[s].sum()-dep[s].sum()
        w=ret[s]*np.clip(HEAD-ret.MIN,1,None); w=w/w.sum()
        d=(-net*w*DAMP).clip(lower=-CAP*ret[s],upper=CAP*ret[s])
        P.loc[ret.index,f"adj_{s}"]=d.values
for s in ["PTS","REB","AST"]: P[f"{s}_proj_base"]=(P[s]+P[f"adj_{s}"]).round(2)
P.to_pickle("P2.pkl")
cols=["Jugador","Equipo_2627","MIN","PTS","adj_PTS","AST","adj_AST","REB","adj_REB"]
q=P[P.MIN>=25]
print("MAYORES SUBIDAS (PTS):");print(q.sort_values("adj_PTS",ascending=False)[cols].round(2).head(10).to_string(index=False))
print("MAYORES BAJADAS (PTS):");print(q.sort_values("adj_PTS")[cols].round(2).head(8).to_string(index=False))
print("MAYORES SUBIDAS (AST):");print(q.sort_values("adj_AST",ascending=False)[cols].round(2).head(6).to_string(index=False))
print("jugadores que tocan el tope:",int(((q.adj_PTS.abs()>=CAP*q.PTS-1e-9)).sum()),"de",len(q))
print(P[P.key.isin(["shaigilgeousalexander","lukadoncic","austinreaves","jamalmurray","jaylenbrown","tyresemaxey"])][cols].round(2).to_string(index=False))
