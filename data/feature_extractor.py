#!/usr/bin/env python3
"""
Feature Extraction for Football Matches

Converts raw team stats into features for prediction models.
"""

from typing import Dict, List, Optional


class FeatureExtractor:
    """Extract ML features from team statistics."""

    def __init__(self, league_avg: Optional[Dict] = None):
        """
        Args:
            league_avg: League-wide averages for normalization
        """
        self.league_avg = league_avg or {
            "avg_goals_per_match": 2.7,
            "avg_goals_home": 1.4,
            "avg_goals_away": 1.3,
        }

    def extract_match_features(
        self,
        home_team: str,
        away_team: str,
        home_stats: Dict,
        away_stats: Dict,
        h2h_record: Dict,
    ) -> Dict:
        """Extract all features for a match."""

        features = {
            "home_form_5": self._calc_form_score(home_stats.get("form_5", [])),
            "away_form_5": self._calc_form_score(away_stats.get("form_5", [])),
            "home_home_form_3": self._calc_form_score(home_stats.get("home_form_5", [])[:3]),
            "away_away_form_3": self._calc_form_score(away_stats.get("away_form_5", [])[:3]),
            "home_gd": self._calc_goal_differential(home_stats),
            "away_gd": self._calc_goal_differential(away_stats),
            "home_gd_home": self._calc_goal_differential(home_stats, venue="home"),
            "away_gd_away": self._calc_goal_differential(away_stats, venue="away"),
            "home_strength": self._calc_strength(home_stats),
            "away_strength": self._calc_strength(away_stats),
            "home_attacks_strength": self._calc_attack_strength(home_stats),
            "away_defense_strength": self._calc_defense_strength(away_stats),
            "h2h_home_wins": h2h_record.get("home_wins", 0),
            "h2h_draws": h2h_record.get("draws", 0),
            "h2h_away_wins": h2h_record.get("away_wins", 0),
        }

        return features

    @staticmethod
    def _calc_form_score(form_list: List[float]) -> float:
        """
        Calculate form score from last N matches.
        form_list: [1.0, 1.0, 0.5, 0.0, 1.0] means W, W, D, L, W
        Returns: average (0-1, higher is better)
        """
        if not form_list:
            return 0.5
        return sum(form_list) / len(form_list)

    @staticmethod
    def _calc_goal_differential(stats: Dict, venue: Optional[str] = None) -> float:
        """Calculate goal differential (for - against)."""
        if venue == "home":
            goals_for = stats.get("goals_for_home", 0)
            goals_against = stats.get("goals_against_home", 0)
        elif venue == "away":
            goals_for = stats.get("goals_for_away", 0)
            goals_against = stats.get("goals_against_away", 0)
        else:
            goals_for = stats.get("goals_for", 0)
            goals_against = stats.get("goals_against", 0)

        if not goals_for and not goals_against:
            return 0.0
        total_games = (goals_for + goals_against) / 2 or 1
        return (goals_for - goals_against) / total_games

    def _calc_strength(self, stats: Dict) -> float:
        """
        Overall team strength (attack + defense combined).
        Normalized vs league average.
        """
        gf = stats.get("goals_for", self.league_avg["avg_goals_per_match"] * 2)
        ga = stats.get("goals_against", self.league_avg["avg_goals_per_match"] * 2)
        strength = (gf - ga) / (self.league_avg["avg_goals_per_match"] * 2)
        return max(-1.0, min(1.0, strength))  # Clamp to [-1, 1]

    def _calc_attack_strength(self, stats: Dict) -> float:
        """Attack strength vs league average."""
        gf = stats.get("goals_for", 0)
        if not gf:
            return 0.0
        # Normalize: 0 = league avg, >0 = better, <0 = worse
        league_gf = self.league_avg.get("avg_goals_per_match", 2.7) * 19  # 38 games
        return (gf - league_gf) / league_gf

    def _calc_defense_strength(self, stats: Dict) -> float:
        """Defense strength vs league average (lower is better)."""
        ga = stats.get("goals_against", 0)
        if not ga:
            return 0.0
        # Normalize: 0 = league avg, >0 = worse, <0 = better
        league_ga = self.league_avg.get("avg_goals_per_match", 2.7) * 19
        # Invert: positive = good defense
        return -(ga - league_ga) / league_ga


def main():
    """Test feature extraction."""
    extractor = FeatureExtractor()

    # Test data
    home_stats = {
        "form_5": [1.0, 1.0, 0.5, 1.0, 0.5],  # W, W, D, W, D
        "home_form_5": [1.0, 1.0, 1.0, 1.0, 0.5],
        "away_form_5": [1.0, 0.5, 0.0, 0.5, 0.5],
        "goals_for": 45,
        "goals_against": 20,
        "goals_for_home": 28,
        "goals_against_home": 10,
    }

    away_stats = {
        "form_5": [0.5, 0.5, 0.0, 1.0, 0.0],  # D, D, L, W, L
        "home_form_5": [1.0, 0.0, 1.0, 0.5, 1.0],
        "away_form_5": [0.0, 1.0, 0.0, 0.5, 0.0],
        "goals_for": 35,
        "goals_against": 28,
        "goals_for_away": 17,
        "goals_against_away": 18,
    }

    h2h = {"home_wins": 2, "draws": 1, "away_wins": 0}

    features = extractor.extract_match_features(
        "Manchester United",
        "Liverpool",
        home_stats,
        away_stats,
        h2h
    )

    print("[TEST] Extracted features:")
    for key, val in sorted(features.items()):
        print(f"  {key}: {val:.4f}")


if __name__ == "__main__":
    main()
