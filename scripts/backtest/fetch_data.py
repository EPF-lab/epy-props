"""
Descarga datos reales con nba_api y los guarda en el MISMO formato que make_synthetic.py.
Uso:  pip install nba_api pandas numpy
      python fetch_data.py
(Sin probar en mi entorno: no tiene internet. Si algo falla, pásame el error y lo ajusto.)
"""
import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamelog, leaguedashplayerstats

SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
PAUSE = 1.5  # nba.com limita peticiones

def team_games(season):
    df = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation="T",
                                     season_type_all_star="Regular Season").get_data_frames()[0]
    # cada juego aparece 2 veces (una por equipo): lo "permitido" por A es lo anotado por B
    a = df[["GAME_ID", "GAME_DATE", "TEAM_ABBREVIATION", "PTS", "REB", "FG3M", "FGA", "TOV"]]
    m = a.merge(a, on="GAME_ID", suffixes=("", "_opp"))
    m = m[m.TEAM_ABBREVIATION != m.TEAM_ABBREVIATION_opp]
    return pd.DataFrame({
        "season": season, "team": m.TEAM_ABBREVIATION, "game_date": m.GAME_DATE,
        "pts_allowed": m.PTS_opp, "reb_allowed": m.REB_opp, "fg3m_allowed": m.FG3M_opp,
        "fga_allowed": m.FGA_opp, "tov_forced": m.TOV_opp})

def rosters(season):
    adv = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season, measure_type_detailed_defense="Advanced",
        per_mode_detailed="Totals").get_data_frames()[0]
    adv = adv[adv.GP >= 10]
    lg = adv.DEF_RATING.mean()
    # menor DEF_RATING = mejor defensor -> invertimos el signo. Es un proxy; mejorar con DBPM/tracking.
    return pd.DataFrame({"season": season, "team": adv.TEAM_ABBREVIATION,
                         "player_id": adv.PLAYER_ID, "min": adv.MIN,
                         "def_impact": -(adv.DEF_RATING - lg) / 3})

if __name__ == "__main__":
    G, R = [], []
    for s in SEASONS:
        print("Descargando", s); G.append(team_games(s)); time.sleep(PAUSE)
        R.append(rosters(s)); time.sleep(PAUSE)
    pd.concat(G).to_csv("data/team_games.csv", index=False)
    pd.concat(R).to_csv("data/rosters.csv", index=False)
    print("Listo.")
