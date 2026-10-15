import pandas as pd, numpy as np, re, unicodedata
from positions import parse
def norm(s):
    s=unicodedata.normalize("NFKD",str(s)); s="".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]","",s.lower())
J=pd.read_pickle("jug.pkl"); J["key"]=J.Jugador.map(norm)
print("filas con equipo '0':",J[J.TEAM_ABBREVIATION=="0"][["Jugador","MIN","PTS"]].head(5).to_dict("records"))
AGG={"2TM","3TM","4TM","0"}
M=pd.read_csv("moves.csv",encoding="utf-8-sig"); M["key"]=M.Jugador.map(norm)

# ---- 1) una fila por jugador: equipo 2025-26 (último), stats base (total si fue traspasado) ----
rows=[]
for k,g in J.groupby("key",sort=False):
    team_rows=g[~g.TEAM_ABBREVIATION.isin(AGG)]
    tot=g[g.TEAM_ABBREVIATION.isin(AGG)]
    base=tot.iloc[0] if len(tot) else g.iloc[0]
    last=team_rows.iloc[-1] if len(team_rows) else g.iloc[-1]
    rows.append(dict(key=k,Jugador=g.iloc[0].Jugador,Equipo_2526=last.TEAM_ABBREVIATION,
        equipos_2526="/".join(team_rows.TEAM_ABBREVIATION),MIN=base.MIN,PTS=base.PTS,REB=base.REB,AST=base.AST))
P=pd.DataFrame(rows)

# ---- 2) equipo 2026-27 según movimientos ----
arr=M[M.Tipo=="Llegada"].groupby("key").Equipo.apply(list)
ren=M[M.Tipo=="Renovación"].groupby("key").Equipo.apply(list)
sal=M[M.Tipo=="Salida"].groupby("key").Equipo.apply(list)
conf=arr[arr.map(len)>1]; print("jugadores con >1 llegada (revisar):",conf.to_dict())
def cur(r):
    if r.key in arr.index: return arr[r.key][-1],"Cambió de equipo"
    if r.key in ren.index: return ren[r.key][-1],"Renovó"
    if r.key in sal.index: return None,"Salió (sin equipo confirmado)"
    return r.Equipo_2526,"Sin movimiento reportado"
tmp=P.apply(cur,axis=1,result_type="expand"); P["Equipo_2627"]=tmp[0]; P["Movimiento"]=tmp[1]
no_match=M[~M.key.isin(P.key)&M.Tipo.isin(["Llegada","Renovación","Salida"])]
print("movimientos de jugadores que NO están en tu hoja (novatos/sin datos):",len(no_match),"de",len(M))
print("salidas sin equipo nuevo:",P[P.Movimiento.str.startswith("Salió")].Jugador.tolist())

# ---- 3) posiciones ----
pos=parse(); pos_n={norm(k):v for k,v in pos.items()}
def heur(r):
    m=max(r.MIN,1); reb=r.REB/m*36; ast=r.AST/m*36
    if ast>=5.5 and reb<6.5: return "PG"
    if ast>=3.5 and reb<5.5: return "SG"
    if reb>=9: return "C"
    if reb>=7: return "PF"
    return "SF"
P["Pos"]=[pos_n[k][0] if k in pos_n else None for k in P.key]
P["Pos_alt"]=[pos_n[k][1] if k in pos_n else "" for k in P.key]
P["Confianza_pos"]=np.where(P.Pos.notna(),"manual","estimada (stats)")
P.loc[P.Pos.isna(),"Pos"]=P[P.Pos.isna()].apply(heur,axis=1)
print("posición manual:",int((P.Confianza_pos=='manual').sum()),"| estimada:",int((P.Confianza_pos!='manual').sum()))
print("manuales sin match en la hoja:",[k for k in pos_n if k not in set(P.key)][:20])
P.to_pickle("P.pkl")
print(P[P.Movimiento=="Cambió de equipo"].shape[0],"jugadores cambiaron de equipo")
