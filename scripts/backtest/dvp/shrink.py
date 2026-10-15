"""Prior con encogimiento y mezcla bayesiana con datos de la temporada en curso."""
import numpy as np


def make_prior(prev_val, league_mean, c, lam):
    """prior = media_liga + c * lambda * (valor_año_pasado - media_liga)"""
    return league_mean + c * lam * (prev_val - league_mean)


def blend(prior, current_mean, n_games, k):
    """w = k/(k+n). Con n=0 -> solo prior. Con n grande -> solo datos nuevos."""
    w = k / (k + np.asarray(n_games, dtype=float))
    return w * prior + (1 - w) * current_mean


def fit_lambda(prev_dev, c, target_dev):
    """
    Estima lambda por mínimos cuadrados sin intercepto:
        (y - media_liga) = lambda * [c * (prev - media_liga)]
    """
    x = np.asarray(c) * np.asarray(prev_dev)
    y = np.asarray(target_dev)
    return float((x * y).sum() / (x * x).sum())
