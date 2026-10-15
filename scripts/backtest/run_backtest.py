import pandas as pd
from dvp.backtest import preseason_backtest, inseason_backtest

games = pd.read_csv("data/team_games.csv", parse_dates=["game_date"])
rosters = pd.read_csv("data/rosters.csv")
for metric in ["pts_allowed", "reb_allowed"]:
    print(f"\n===== {metric} =====")
    tabla, lams, _ = preseason_backtest(games, rosters, metric)
    print("Pretemporada (error vs temporada completa):\n", tabla.round(3))
    lam = sum(lams.values()) / len(lams)
    print(f"lambda medio (LOSO): {lam:.3f}")
    res, best_k = inseason_backtest(games, rosters, metric, lam)
    print("\nEn temporada (RMSE de los juegos restantes):\n", res.round(3).to_string())
    print("Mejor k global:", best_k)
