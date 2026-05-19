#!/usr/bin/env python3
"""
Heuristic Football Match Predictor

Rule-based prediction of Win/Draw/Loss probabilities.
"""

import math
from typing import Dict, Tuple


class FootballPredictor:
    """Heuristic predictor for football matches."""

    def __init__(self):
        """Initialize with calibration constants."""
        # These will be tuned based on historical data
        self.form_weight = 1.5
        self.gd_weight = 1.0
        self.strength_weight = 1.2
        self.h2h_weight = 0.5
        self.draw_bias = 0.25  # Draws are ~25% of outcomes

    def predict_match(
        self,
        features: Dict,
        verbose: bool = False,
    ) -> Tuple[float, float, float]:
        """
        Predict probabilities for Home/Draw/Away.

        Returns:
            (p_home, p_draw, p_away) where sum = 1.0
        """

        # Score home team advantage
        home_score = 0.0

        # Form (most recent 5 matches)
        form_diff = features.get("home_form_5", 0.5) - features.get("away_form_5", 0.5)
        home_score += form_diff * self.form_weight * 3  # Max +/- 4.5

        # Recent home/away form (last 3)
        home_home_form = features.get("home_home_form_3", 0.5)
        away_away_form = features.get("away_away_form_3", 0.5)
        home_score += (home_home_form - away_away_form) * 1.5

        # Goal differential
        home_gd = features.get("home_gd", 0.0)
        away_gd = features.get("away_gd", 0.0)
        home_score += (home_gd - away_gd) * self.gd_weight * 2

        # At home advantage for goal differential
        home_gd_home = features.get("home_gd_home", 0.0)
        away_gd_away = features.get("away_gd_away", 0.0)
        home_score += (home_gd_home + away_gd_away) * 1.0

        # Overall strength
        home_strength = features.get("home_strength", 0.0)
        away_strength = features.get("away_strength", 0.0)
        home_score += (home_strength - away_strength) * self.strength_weight * 2

        # Attack strength
        home_attack = features.get("home_attacks_strength", 0.0)
        away_defense = features.get("away_defense_strength", 0.0)
        home_score += home_attack * 0.8
        home_score += away_defense * 0.8  # Defense against away team

        # Head-to-head record
        h2h_home = features.get("h2h_home_wins", 0)
        h2h_away = features.get("h2h_away_wins", 0)
        h2h_diff = h2h_home - h2h_away
        if h2h_diff != 0:
            home_score += h2h_diff * self.h2h_weight

        # Convert score to probability
        # Use sigmoid to map score to [0, 1]
        p_home_base = self._sigmoid(home_score)

        # Draw probability is independent (about 25-30% baseline)
        p_draw = self.draw_bias

        # Remaining probability split between home and away
        p_remaining = 1.0 - p_draw
        p_home = p_home_base * p_remaining
        p_away = (1.0 - p_home_base) * p_remaining

        if verbose:
            print(f"[PREDICT] Score: {home_score:.2f}")
            print(f"  Form diff: {form_diff:.3f}")
            print(f"  GD diff: {home_gd - away_gd:.3f}")
            print(f"  Strength diff: {home_strength - away_strength:.3f}")
            print(f"  → P(Home)={p_home:.3f}, P(Draw)={p_draw:.3f}, P(Away)={p_away:.3f}")

        return p_home, p_draw, p_away

    def predict_with_odds(
        self,
        features: Dict,
        odds: Dict,  # {"home": 0.55, "draw": 0.30, "away": 0.35}
    ) -> Dict:
        """
        Predict match outcome and compute edges.

        Returns:
            {
                "p_home": 0.48,
                "p_draw": 0.25,
                "p_away": 0.27,
                "odds_home": 0.55,
                "odds_draw": 0.30,
                "odds_away": 0.35,
                "edge_home": -0.07,
                "edge_draw": -0.05,
                "edge_away": -0.08,
                "best_edge": {"direction": "home", "edge": -0.07},
            }
        """
        p_home, p_draw, p_away = self.predict_match(features)

        odds_home = odds.get("home", 0.5)
        odds_draw = odds.get("draw", 0.3)
        odds_away = odds.get("away", 0.5)

        edge_home = p_home - odds_home
        edge_draw = p_draw - odds_draw
        edge_away = p_away - odds_away

        edges = {
            "home": edge_home,
            "draw": edge_draw,
            "away": edge_away,
        }
        best_edge_dir = max(edges, key=edges.get)

        return {
            "p_home": p_home,
            "p_draw": p_draw,
            "p_away": p_away,
            "odds_home": odds_home,
            "odds_draw": odds_draw,
            "odds_away": odds_away,
            "edge_home": edge_home,
            "edge_draw": edge_draw,
            "edge_away": edge_away,
            "best_edge": {
                "direction": best_edge_dir,
                "edge": edges[best_edge_dir],
            },
        }

    @staticmethod
    def _sigmoid(x: float, scale: float = 0.5) -> float:
        """Sigmoid function: maps R → [0, 1]."""
        try:
            return 1.0 / (1.0 + math.exp(-x * scale))
        except OverflowError:
            return 1.0 if x > 0 else 0.0


def main():
    """Test the predictor."""
    predictor = FootballPredictor()

    # Test features
    features = {
        "home_form_5": 0.70,      # Good form (7/10 points)
        "away_form_5": 0.50,      # Medium form
        "home_home_form_3": 0.80, # Strong at home
        "away_away_form_3": 0.40, # Weak away
        "home_gd": 0.15,          # +0.15 goals/game
        "away_gd": -0.10,         # -0.10 goals/game
        "home_gd_home": 0.20,     # Stronger at home
        "away_gd_away": -0.25,    # Weaker away
        "home_strength": 0.10,    # Slightly above average
        "away_strength": -0.05,   # Slightly below average
        "home_attacks_strength": 0.05,
        "away_defense_strength": -0.08,
        "h2h_home_wins": 2,
        "h2h_draws": 1,
        "h2h_away_wins": 0,
    }

    print("[TEST] Basic prediction:")
    p_h, p_d, p_a = predictor.predict_match(features, verbose=True)

    print("\n[TEST] With odds:")
    odds = {"home": 0.55, "draw": 0.28, "away": 0.35}
    result = predictor.predict_with_odds(features, odds)
    print(f"  Edge Home: {result['edge_home']:+.4f}")
    print(f"  Edge Draw: {result['edge_draw']:+.4f}")
    print(f"  Edge Away: {result['edge_away']:+.4f}")
    print(f"  Best: {result['best_edge']['direction']} ({result['best_edge']['edge']:+.4f})")


if __name__ == "__main__":
    main()
