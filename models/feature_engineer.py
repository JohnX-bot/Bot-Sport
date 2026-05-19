#!/usr/bin/env python3
"""
Advanced Feature Engineer

Generate 30+ features for match prediction from raw statistics.
Designed for Logistic Regression + tree-based models.
"""

import math
from typing import Dict, List, Tuple


class AdvancedFeatureEngineer:
    """Extract advanced features from match data."""

    def __init__(self):
        """Initialize feature engineer."""
        self.feature_names = self._get_feature_names()

    def _get_feature_names(self) -> List[str]:
        """Get list of all feature names."""
        return [
            # Form features (5)
            "home_form_5", "away_form_5",
            "home_form_10", "away_form_10",
            "home_form_trend",
            # Home/Away form (4)
            "home_home_form_3", "away_away_form_3",
            "home_home_form_5", "away_away_form_5",
            # Goal Differential (8)
            "home_gd", "away_gd",
            "home_gd_home", "away_gd_away",
            "home_gd_trend", "away_gd_trend",
            "home_gd_home_trend", "away_gd_away_trend",
            # Strength metrics (6)
            "home_strength", "away_strength",
            "home_attack_strength", "away_attack_strength",
            "home_defense_strength", "away_defense_strength",
            # Head-to-Head (4)
            "h2h_home_wins", "h2h_draws", "h2h_away_wins",
            "h2h_home_win_rate",
            # Rest & Fatigue (4)
            "home_days_rest", "away_days_rest",
            "home_matches_last_7days", "away_matches_last_7days",
            # Momentum (4)
            "home_win_streak", "away_win_streak",
            "home_recent_pct", "away_recent_pct",
            # Consistency (4)
            "home_form_consistency", "away_form_consistency",
            "home_strength_consistency", "away_strength_consistency",
            # Draw tendency (2)
            "home_draw_rate", "away_draw_rate",
            # Squad quality proxies (2)
            "home_quality_index", "away_quality_index",
            # Possession & Pressure (2)
            "home_possession_avg", "away_possession_avg",
        ]

    def extract_features(self, match_data: Dict) -> Dict[str, float]:
        """
        Extract all features from match data.

        Args:
            match_data: {
                home_team, away_team, date,
                home_stats: {form_5, form_10, gd, gd_home, ..., days_rest, recent_form},
                away_stats: {...},
                h2h: {home_wins, draws, away_wins},
            }

        Returns:
            Dictionary of {feature_name: value}
        """
        h = match_data.get("home_stats", {})
        a = match_data.get("away_stats", {})
        h2h = match_data.get("h2h", {})

        features = {}

        # 1. Form features (5)
        features["home_form_5"] = h.get("form_5", 0.50)
        features["away_form_5"] = a.get("form_5", 0.50)
        features["home_form_10"] = h.get("form_10", 0.50)
        features["away_form_10"] = a.get("form_10", 0.50)
        features["home_form_trend"] = h.get("form_10", 0.50) - h.get("form_5", 0.50)

        # 2. Home/Away form (4)
        features["home_home_form_3"] = h.get("home_form_3", 0.50)
        features["away_away_form_3"] = a.get("away_form_3", 0.50)
        features["home_home_form_5"] = h.get("home_form_5", 0.50)
        features["away_away_form_5"] = a.get("away_form_5", 0.50)

        # 3. Goal Differential (8)
        features["home_gd"] = h.get("gd", 0.0)
        features["away_gd"] = a.get("gd", 0.0)
        features["home_gd_home"] = h.get("gd_home", 0.0)
        features["away_gd_away"] = a.get("gd_away", 0.0)
        features["home_gd_trend"] = h.get("gd_10", 0.0) - h.get("gd", 0.0)
        features["away_gd_trend"] = a.get("gd_10", 0.0) - a.get("gd", 0.0)
        features["home_gd_home_trend"] = h.get("gd_home_5", 0.0) - h.get("gd_home", 0.0)
        features["away_gd_away_trend"] = a.get("gd_away_5", 0.0) - a.get("gd_away", 0.0)

        # 4. Strength metrics (6)
        features["home_strength"] = h.get("strength", 0.0)
        features["away_strength"] = a.get("strength", 0.0)
        features["home_attack_strength"] = h.get("attack_strength", 0.0)
        features["away_attack_strength"] = a.get("attack_strength", 0.0)
        features["home_defense_strength"] = h.get("defense_strength", 0.0)
        features["away_defense_strength"] = a.get("defense_strength", 0.0)

        # 5. Head-to-Head (4)
        h2h_total = (h2h.get("home_wins", 0) + h2h.get("draws", 0) +
                     h2h.get("away_wins", 0))
        features["h2h_home_wins"] = float(h2h.get("home_wins", 0))
        features["h2h_draws"] = float(h2h.get("draws", 0))
        features["h2h_away_wins"] = float(h2h.get("away_wins", 0))
        features["h2h_home_win_rate"] = (
            h2h.get("home_wins", 0) / max(1, h2h_total) if h2h_total > 0 else 0.33
        )

        # 6. Rest & Fatigue (4)
        features["home_days_rest"] = float(h.get("days_rest", 3))
        features["away_days_rest"] = float(a.get("days_rest", 3))
        features["home_matches_last_7days"] = float(h.get("matches_last_7days", 1))
        features["away_matches_last_7days"] = float(a.get("matches_last_7days", 1))

        # 7. Momentum (4)
        features["home_win_streak"] = float(h.get("win_streak", 0))
        features["away_win_streak"] = float(a.get("win_streak", 0))
        features["home_recent_pct"] = h.get("recent_form", 0.50)
        features["away_recent_pct"] = a.get("recent_form", 0.50)

        # 8. Consistency (4)
        features["home_form_consistency"] = self._calc_consistency(
            h.get("form_5", 0.50), h.get("form_10", 0.50)
        )
        features["away_form_consistency"] = self._calc_consistency(
            a.get("form_5", 0.50), a.get("form_10", 0.50)
        )
        features["home_strength_consistency"] = self._calc_consistency(
            h.get("strength", 0.0), h.get("strength_avg", 0.0)
        )
        features["away_strength_consistency"] = self._calc_consistency(
            a.get("strength", 0.0), a.get("strength_avg", 0.0)
        )

        # 9. Draw tendency (2)
        features["home_draw_rate"] = h.get("draw_rate", 0.25)
        features["away_draw_rate"] = a.get("draw_rate", 0.25)

        # 10. Squad quality proxies (2)
        features["home_quality_index"] = self._calc_quality_index(h)
        features["away_quality_index"] = self._calc_quality_index(a)

        # 11. Possession & Pressure (2)
        features["home_possession_avg"] = h.get("possession_avg", 0.50)
        features["away_possession_avg"] = a.get("possession_avg", 0.50)

        return features

    def _calc_consistency(self, recent: float, historical: float) -> float:
        """
        Calculate consistency score (how stable is recent form vs history).
        Lower variance = higher consistency.
        """
        if recent == 0 or historical == 0:
            return 0.5
        diff = abs(recent - historical)
        consistency = 1.0 / (1.0 + diff)  # Sigmoid-like, 0-1 range
        return consistency

    def _calc_quality_index(self, team_stats: Dict) -> float:
        """
        Calculate proxy for team squad quality.
        Combines form, strength, and consistency.
        """
        form = team_stats.get("form_5", 0.50)
        strength = team_stats.get("strength", 0.0)
        consistency = self._calc_consistency(
            team_stats.get("form_5", 0.50),
            team_stats.get("form_10", 0.50),
        )
        # Weighted average
        quality = 0.4 * form + 0.4 * (0.5 + strength * 0.1) + 0.2 * consistency
        return max(0.0, min(1.0, quality))  # Clamp to 0-1

    def get_feature_count(self) -> int:
        """Get total number of features."""
        return len(self.feature_names)

    def normalize_features(
        self,
        features: Dict[str, float],
        means: Dict[str, float] = None,
        stds: Dict[str, float] = None,
    ) -> Dict[str, float]:
        """
        Normalize features to zero mean, unit variance.
        If means/stds not provided, uses simple min-max scaling.
        """
        if means is None or stds is None:
            # Simple min-max scaling
            normalized = {}
            for name, value in features.items():
                if name in [
                    "home_form_5", "away_form_5", "home_form_10", "away_form_10",
                    "home_home_form_3", "away_away_form_3",
                    "home_home_form_5", "away_away_form_5",
                    "home_recent_pct", "away_recent_pct",
                    "home_draw_rate", "away_draw_rate",
                    "home_quality_index", "away_quality_index",
                    "home_possession_avg", "away_possession_avg",
                ]:
                    # Already 0-1 range
                    normalized[name] = value
                elif name in [
                    "h2h_home_wins", "h2h_draws", "h2h_away_wins",
                    "home_matches_last_7days", "away_matches_last_7days",
                    "home_win_streak", "away_win_streak",
                ]:
                    # Count features - cap at 10
                    normalized[name] = min(1.0, value / 10.0)
                elif name in [
                    "home_days_rest", "away_days_rest",
                ]:
                    # Rest days 0-7
                    normalized[name] = min(1.0, value / 7.0)
                else:
                    # Goal diff, strength, trends - use tanh to scale
                    normalized[name] = math.tanh(value)
            return normalized
        else:
            # Z-score normalization
            normalized = {}
            for name, value in features.items():
                mean = means.get(name, 0.0)
                std = stds.get(name, 1.0)
                if std == 0:
                    normalized[name] = 0.0
                else:
                    normalized[name] = (value - mean) / std
            return normalized


def main():
    """Test feature engineer."""
    engineer = AdvancedFeatureEngineer()

    # Mock match data
    match = {
        "home_team": "Arsenal",
        "away_team": "Liverpool",
        "date": "2024-05-10",
        "home_stats": {
            "form_5": 0.70,
            "form_10": 0.65,
            "gd": 0.15,
            "gd_home": 0.20,
            "strength": 0.08,
            "attack_strength": 0.12,
            "defense_strength": -0.02,
            "home_form_3": 0.80,
            "home_form_5": 0.75,
            "days_rest": 5,
            "matches_last_7days": 2,
            "win_streak": 2,
            "recent_form": 0.75,
            "draw_rate": 0.15,
            "possession_avg": 0.58,
        },
        "away_stats": {
            "form_5": 0.55,
            "form_10": 0.60,
            "gd": -0.10,
            "gd_away": -0.15,
            "strength": -0.05,
            "attack_strength": 0.05,
            "defense_strength": -0.08,
            "away_form_3": 0.50,
            "away_form_5": 0.55,
            "days_rest": 3,
            "matches_last_7days": 3,
            "win_streak": 1,
            "recent_form": 0.50,
            "draw_rate": 0.20,
            "possession_avg": 0.42,
        },
        "h2h": {
            "home_wins": 4,
            "draws": 2,
            "away_wins": 2,
        },
    }

    # Extract features
    features = engineer.extract_features(match)

    print(f"[TEST] Extracted {len(features)} features:")
    print(f"  Feature count: {engineer.get_feature_count()}")
    print(f"\n[TEST] Sample features:")
    for name in list(features.keys())[:10]:
        print(f"  {name:30} : {features[name]:+.4f}")

    # Normalize
    normalized = engineer.normalize_features(features)
    print(f"\n[TEST] Normalized features (first 10):")
    for name in list(normalized.keys())[:10]:
        print(f"  {name:30} : {normalized[name]:+.4f}")


if __name__ == "__main__":
    main()
