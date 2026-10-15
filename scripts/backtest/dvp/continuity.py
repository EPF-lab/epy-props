"""Continuidad de roster entre temporadas (0 = equipo nuevo, 1 = idéntico)."""
import numpy as np
import pandas as pd


def team_continuity(prev: pd.DataFrame, curr: pd.DataFrame,
                    use_def_impact: bool = True, alpha: float = 0.5) -> pd.Series:
    """
    prev: columnas [team, player_id, min, def_impact]  (temporada anterior, real)
    curr: columnas [team, player_id, min]              (temporada nueva, minutos PROYECTADOS)
    Devuelve c por equipo = alpha*retenido_prev + (1-alpha)*retenido_curr

    retenido_prev : % del peso defensivo del año pasado que sigue en el equipo
    retenido_curr : % de los minutos proyectados que ocupan jugadores que ya estaban
    """
    p = prev.copy()
    if use_def_impact and "def_impact" in p:
        # peso = minutos * (1 + |impacto|): un buen (o mal) defensor pesa más que un relleno
        p["w"] = p["min"] * (1 + p["def_impact"].abs())
    else:
        p["w"] = p["min"]

    curr_keys = set(zip(curr["team"], curr["player_id"]))
    prev_keys = set(zip(p["team"], p["player_id"]))
    p["kept"] = [(t, i) in curr_keys for t, i in zip(p["team"], p["player_id"])]
    c = curr.copy()
    c["kept"] = [(t, i) in prev_keys for t, i in zip(c["team"], c["player_id"])]

    ret_prev = p.assign(wk=p["w"] * p["kept"]).groupby("team").apply(
        lambda g: g["wk"].sum() / g["w"].sum(), include_groups=False)
    ret_curr = c.assign(mk=c["min"] * c["kept"]).groupby("team").apply(
        lambda g: g["mk"].sum() / g["min"].sum(), include_groups=False)
    return (alpha * ret_prev + (1 - alpha) * ret_curr).rename("continuity")
