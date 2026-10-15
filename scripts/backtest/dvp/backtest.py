"""
Backtest 1 (pretemporada):  ¿qué prior predice mejor el rendimiento defensivo de la temporada completa?
    A) media de liga   B) 100% año pasado   C) shrinkage con continuidad (leave-one-season-out)
Backtest 2 (en temporada):  ¿qué k mezcla mejor prior + datos recientes para predecir los juegos restantes?
"""
import numpy as np
import pandas as pd
from .continuity import team_continuity
from .shrink import make_prior, blend, fit_lambda


def season_means(games: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Valor medio de `metric` PERMITIDO por equipo y temporada + media de liga."""
    t = games.groupby(["season", "team"])[metric].mean().rename("val").reset_index()
    t["league"] = t.groupby("season")["val"].transform("mean")
    return t


def build_preseason_table(games, rosters, metric, curr_minutes=None):
    """
    Una fila por (season, team) con prev, c, target. 
    curr_minutes: minutos proyectados por temporada (en producción vienen de tu proyección).
    En backtest usamos los minutos reales de esa temporada (ligero look-ahead, ver README).
    """
    sm = season_means(games, metric)
    seasons = sorted(sm["season"].unique())
    rows = []
    for s_prev, s in zip(seasons[:-1], seasons[1:]):
        prev_r = rosters[rosters.season == s_prev]
        curr_r = (curr_minutes if curr_minutes is not None else rosters)
        curr_r = curr_r[curr_r.season == s]
        c = team_continuity(prev_r, curr_r)
        a = sm[sm.season == s_prev].set_index("team")
        b = sm[sm.season == s].set_index("team")
        for team in b.index:
            if team in a.index and team in c.index:
                rows.append(dict(season=s, team=team, prev=a.loc[team, "val"],
                                 prev_league=a.loc[team, "league"],
                                 league=b.loc[team, "league"], c=c[team],
                                 target=b.loc[team, "val"]))
    return pd.DataFrame(rows)


def preseason_backtest(games, rosters, metric):
    df = build_preseason_table(games, rosters, metric)
    df["prev_dev"] = df["prev"] - df["prev_league"]
    df["target_dev"] = df["target"] - df["league"]
    out, lams = [], {}
    for s in df.season.unique():
        tr, te = df[df.season != s], df[df.season == s].copy()
        lam = fit_lambda(tr.prev_dev, tr.c, tr.target_dev)   # sin look-ahead
        lams[s] = lam
        te["pred_league"] = te["league"]
        te["pred_last"] = te["league"] + te["prev_dev"]
        te["pred_shrink"] = make_prior(te["prev"], te["prev_league"], te["c"], lam) \
                            - te["prev_league"] + te["league"]
        out.append(te)
    r = pd.concat(out)
    res = {m: dict(MAE=float((r[f"pred_{m}"] - r.target).abs().mean()),
                   RMSE=float(np.sqrt(((r[f"pred_{m}"] - r.target) ** 2).mean())))
           for m in ["league", "last", "shrink"]}
    return pd.DataFrame(res).T, lams, r


def inseason_backtest(games, rosters, metric, lam, checkpoints=(5, 10, 20, 30, 45),
                      k_grid=(1, 5, 10, 15, 20, 30, 50, 80)):
    """Para cada n: predice la media de los juegos n+1..fin con blend(prior, media de los n primeros)."""
    games = games.sort_values(["season", "team", "game_date"])
    pre = build_preseason_table(games, rosters, metric)
    pre["prior"] = make_prior(pre["prev"], pre["prev_league"], pre["c"], lam)
    rows = []
    for (s, t), g in games.groupby(["season", "team"]):
        p = pre[(pre.season == s) & (pre.team == t)]
        if p.empty: continue
        v = g[metric].to_numpy()
        for n in checkpoints:
            if len(v) <= n + 10: continue
            rows.append(dict(season=s, team=t, n=n, cur=v[:n].mean(),
                             rest=v[n:].mean(), prior=p["prior"].iloc[0]))
    d = pd.DataFrame(rows)
    res = []
    for n, g in d.groupby("n"):
        row = {"n": n, "solo_prior": ((g.prior - g.rest) ** 2).mean() ** .5,
               "solo_actual": ((g.cur - g.rest) ** 2).mean() ** .5}
        for k in k_grid:
            row[f"k={k}"] = ((blend(g.prior, g.cur, n, k) - g.rest) ** 2).mean() ** .5
        res.append(row)
    res = pd.DataFrame(res).set_index("n")
    best_k = res[[f"k={k}" for k in k_grid]].mean().idxmin()
    return res, best_k
