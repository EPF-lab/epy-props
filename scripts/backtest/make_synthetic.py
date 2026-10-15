"""Datos sintéticos SOLO para probar que el pipeline funciona. Sustituir por datos reales (fetch_data.py)."""
import numpy as np, pandas as pd
rng = np.random.default_rng(7)
TEAMS = [f"T{i:02d}" for i in range(30)]
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
METRICS = {"pts_allowed": (113, 3.0, 11.0), "reb_allowed": (44, 1.5, 6.5)}  # (media, sd equipo, sd juego)
RHO = 0.75        # persistencia real cuando la plantilla es idéntica
pid = 0
rosters, games = [], []
latent = {m: {t: rng.normal(0, sd) for t in TEAMS} for m, (_, sd, _) in METRICS.items()}
prev_roster = None
for si, s in enumerate(SEASONS):
    retain_p = {t: rng.beta(5, 3) for t in TEAMS}
    cur = []
    for t in TEAMS:
        for j in range(10):
            keep = prev_roster is not None and rng.random() < retain_p[t]
            if keep:
                old = prev_roster[(prev_roster.team == t)]
                player = old.iloc[j]["player_id"]; imp = old.iloc[j]["def_impact"]
            else:
                pid += 1; player = pid; imp = rng.normal(0, 1.5)
            cur.append(dict(season=s, team=t, player_id=player, min=[34,32,30,28,26,22,20,18,16,14][j]*82/82,
                            def_impact=imp))
    cur = pd.DataFrame(cur)
    if prev_roster is not None:
        keptshare = {}
        for t in TEAMS:
            a = set(prev_roster[prev_roster.team == t].player_id)
            g = cur[cur.team == t]
            keptshare[t] = (g["min"] * g.player_id.isin(a)).sum() / g["min"].sum()
        for m, (mu, sd, _) in METRICS.items():
            for t in TEAMS:  # el rasgo persiste en proporción a la continuidad real
                latent[m][t] = RHO * keptshare[t] * latent[m][t] + rng.normal(0, sd * 0.8)
    rosters.append(cur); prev_roster = cur
    for t in TEAMS:
        d = pd.date_range(f"{2021+si}-10-20", periods=82, freq="2D")
        rec = {"season": [s]*82, "team": [t]*82, "game_date": d}
        for m, (mu, sd, gsd) in METRICS.items():
            rec[m] = mu + latent[m][t] + rng.normal(0, gsd, 82)
        games.append(pd.DataFrame(rec))
pd.concat(rosters).to_csv("data/rosters.csv", index=False)
pd.concat(games).to_csv("data/team_games.csv", index=False)
print("OK: data/rosters.csv, data/team_games.csv")
