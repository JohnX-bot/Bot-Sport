from math import exp, factorial
from typing import Dict, Tuple
import math

def poisson_prob(lam: float, k: int) -> float:
    """P(X=k) where X ~ Poisson(lambda)"""
    try:
        return (lam ** k) * exp(-lam) / factorial(k)
    except:
        return 0.0

def dc_correction(home_goals: int, away_goals: int,
                   lambda_h: float, lambda_a: float, rho: float = -0.18) -> float:
    """
    Dixon-Coles low-score correction factor.
    Corrects the independence assumption for low-scoring games.
    rho ≈ -0.18 sube probabilidad de empates (0-0, 1-1) que el Poisson puro subestima.
    Valor más negativo = más empates predichos.
    """
    if home_goals == 0 and away_goals == 0:
        return 1 - lambda_h * lambda_a * rho
    elif home_goals == 0 and away_goals == 1:
        return 1 + lambda_h * rho
    elif home_goals == 1 and away_goals == 0:
        return 1 + lambda_a * rho
    elif home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0

def calculate_match_probabilities(
    home_attack: float,    # Home team attack strength (goals_scored/avg)
    home_defense: float,   # Home team defense strength (goals_conceded/avg)
    away_attack: float,    # Away team attack strength
    away_defense: float,   # Away team defense strength
    league_avg_goals: float = 2.6,   # League average goals per game
    home_advantage: float = 1.30,    # Home field advantage (~30% boost típico en fútbol)
    max_goals: int = 8,
) -> Dict[str, float]:
    """
    Calculates home_win, draw, away_win probabilities using Poisson model.

    Attack/Defense strengths are relative to league average (1.0 = average).
    Higher attack = more goals scored.
    Higher defense = more goals conceded (bad defense).

    Returns: {"home": float, "draw": float, "away": float}
    """
    # Expected goals
    lambda_home = home_attack * away_defense * home_advantage * (league_avg_goals / 2)
    lambda_away = away_attack * home_defense * (league_avg_goals / 2)

    # Clamp to reasonable range
    lambda_home = max(0.3, min(lambda_home, 5.0))
    lambda_away = max(0.3, min(lambda_away, 5.0))

    p_home = p_draw = p_away = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p_h = poisson_prob(lambda_home, h)
            p_a = poisson_prob(lambda_away, a)
            correction = dc_correction(h, a, lambda_home, lambda_away)
            p = p_h * p_a * correction

            if h > a:
                p_home += p
            elif h == a:
                p_draw += p
            else:
                p_away += p

    # Normalize to sum to 1
    total = p_home + p_draw + p_away
    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total

    return {
        "home": round(p_home, 4),
        "draw": round(p_draw, 4),
        "away": round(p_away, 4),
        "lambda_home": round(lambda_home, 3),
        "lambda_away": round(lambda_away, 3),
    }

def apply_form_adjustment(probs: Dict, home_form_score: float, away_form_score: float) -> Dict:
    """
    Adjusts probabilities based on recent form.
    form_score: -1.0 (terrible form) to +1.0 (great form), 0 = average
    Max adjustment: ±8%
    """
    MAX_ADJ = 0.08
    home_adj = home_form_score * MAX_ADJ
    away_adj = away_form_score * MAX_ADJ

    h = probs["home"] + home_adj - away_adj * 0.5
    a = probs["away"] + away_adj - home_adj * 0.5
    d = 1.0 - h - a

    # Keep within bounds
    h = max(0.05, min(h, 0.90))
    a = max(0.05, min(a, 0.90))
    d = max(0.05, min(d, 0.60))

    total = h + d + a
    return {
        "home": round(h / total, 4),
        "draw": round(d / total, 4),
        "away": round(a / total, 4),
        "lambda_home": probs.get("lambda_home", 0),
        "lambda_away": probs.get("lambda_away", 0),
    }

def apply_lineup_adjustment(probs: Dict, home_lineup_score: float, away_lineup_score: float) -> Dict:
    """
    Adjusts probabilities based on lineup quality vs usual.
    lineup_score: -1.0 (many key players missing) to +1.0 (full strength), 0 = normal
    Max adjustment: ±5%
    """
    MAX_ADJ = 0.05
    home_adj = home_lineup_score * MAX_ADJ
    away_adj = away_lineup_score * MAX_ADJ

    h = probs["home"] + home_adj - away_adj * 0.4
    a = probs["away"] + away_adj - home_adj * 0.4
    d = 1.0 - h - a

    h = max(0.05, min(h, 0.90))
    a = max(0.05, min(a, 0.90))
    d = max(0.05, min(d, 0.60))
    total = h + d + a
    return {
        "home": round(h / total, 4),
        "draw": round(d / total, 4),
        "away": round(a / total, 4),
        "lambda_home": probs.get("lambda_home", 0),
        "lambda_away": probs.get("lambda_away", 0),
    }

def calculate_live_probabilities(
    lambda_home_full: float,  # Goles esperados partido completo (local)
    lambda_away_full: float,  # Goles esperados partido completo (visitante)
    home_goals: int,           # Goles actuales del local
    away_goals: int,           # Goles actuales del visitante
    minutes_played: float,     # Minutos jugados (0–90+)
    is_halftime: bool = False,
    max_goals: int = 8,
) -> Dict[str, float]:
    """
    Calcula probabilidades CONDICIONALES dado el estado actual del partido.

    Ejemplo: si es 2-0 al minuto 65, la prob de que el visitante gane
    es mucho menor que la pre-partido, porque solo quedan 25 minutos.

    Usa distribución Poisson solo para los goles RESTANTES del partido.
    """
    # Tiempo restante
    if is_halftime:
        minutes_remaining = 45.0
    elif minutes_played >= 90:
        minutes_remaining = 3.0   # tiempo de descuento estimado
    else:
        minutes_remaining = max(90.0 - minutes_played, 1.0)

    # Goles esperados restantes (proporcional al tiempo)
    fraction = minutes_remaining / 90.0
    lam_h = max(0.05, lambda_home_full * fraction)
    lam_a = max(0.05, lambda_away_full * fraction)

    p_home = p_draw = p_away = 0.0

    for h_add in range(max_goals + 1):
        ph = poisson_prob(lam_h, h_add)
        for a_add in range(max_goals + 1):
            pa = poisson_prob(lam_a, a_add)
            final_h = home_goals + h_add
            final_a = away_goals + a_add
            p = ph * pa
            if final_h > final_a:
                p_home += p
            elif final_h == final_a:
                p_draw += p
            else:
                p_away += p

    total = p_home + p_draw + p_away
    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total

    return {
        "home":         round(p_home, 4),
        "draw":         round(p_draw, 4),
        "away":         round(p_away, 4),
        "lambda_home":  round(lam_h, 3),
        "lambda_away":  round(lam_a, 3),
        "mins_left":    round(minutes_remaining, 1),
    }


def min_edge_threshold(model_prob: float) -> float:
    """
    Umbral mínimo de edge requerido según la probabilidad del modelo.
    Más exigente con underdogs (baja probabilidad) porque el modelo
    tiene más incertidumbre y es más fácil equivocarse.

      < 20% (gran underdog): necesita +15% de edge
      20–30% (underdog):     necesita +10%
      30–40% (toss-up bajo): necesita  +7%
      40–50% (toss-up alto): necesita  +4%
      > 50% (favorito):      necesita  +3%
    """
    if model_prob < 0.20:
        return 0.15
    if model_prob < 0.30:
        return 0.10
    if model_prob < 0.40:
        return 0.07
    if model_prob < 0.50:
        return 0.04
    return 0.03


def calculate_edge(model_prob: float, market_price: float) -> float:
    """
    Edge = model probability - market implied probability.
    Positive edge means the model thinks this outcome is underpriced.
    """
    if market_price <= 0 or market_price >= 1:
        return 0.0
    return round(model_prob - market_price, 4)

def kelly_fraction(model_prob: float, market_price: float, fraction: float = 0.25) -> float:
    """
    Kelly criterion bet size as fraction of bankroll.
    fraction=0.25 = Quarter Kelly (conservative, recommended).
    market_price = probability implied by Polymarket (= decimal odds base).
    """
    if market_price <= 0 or market_price >= 1:
        return 0.0
    decimal_odds = 1.0 / market_price
    b = decimal_odds - 1  # net profit per unit bet
    q = 1 - model_prob
    k = (model_prob * b - q) / b
    return round(max(0.0, k) * fraction, 4)

def implied_probability(price: float) -> float:
    """Convert Polymarket price to implied probability."""
    return round(float(price), 4) if 0 < float(price) < 1 else 0.0

if __name__ == "__main__":
    # Test: average team vs average team
    probs = calculate_match_probabilities(1.0, 1.0, 1.0, 1.0)
    print("Average vs Average:", probs)

    # Strong home vs weak away
    probs2 = calculate_match_probabilities(1.3, 0.8, 0.9, 1.2)
    print("Strong home vs weak away:", probs2)

    # Edge example
    poly_home_price = 0.45
    edge = calculate_edge(probs2["home"], poly_home_price)
    kelly = kelly_fraction(probs2["home"], poly_home_price)
    print(f"Model home prob: {probs2['home']:.3f}, Poly price: {poly_home_price}, Edge: {edge:.3f}, Kelly: {kelly:.3f}")
