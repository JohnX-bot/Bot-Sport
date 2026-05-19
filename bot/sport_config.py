#!/usr/bin/env python3
"""
Sport Configuration

Parameterized settings for different sports (PL, NFL, LaLiga, etc).
"""

from typing import Dict, List


class SportConfig:
    """Configuration for a specific sport."""

    def __init__(
        self,
        name: str,
        league_id: str,
        outcomes: List[str],
        min_edges: Dict[str, float],
        kelly_fraction: float = 0.20,
        positions_max: int = 6,
        features: List[str] = None,
    ):
        self.name = name
        self.league_id = league_id
        self.outcomes = outcomes  # ["home", "draw", "away"] or ["home", "away"]
        self.min_edges = min_edges
        self.kelly_fraction = kelly_fraction
        self.positions_max = positions_max
        self.features = features or []

    def to_dict(self) -> Dict:
        """Export as dictionary."""
        return {
            "name": self.name,
            "league_id": self.league_id,
            "outcomes": self.outcomes,
            "min_edges": self.min_edges,
            "kelly_fraction": self.kelly_fraction,
            "positions_max": self.positions_max,
            "features": self.features,
        }


# ─────────────────────────── Predefined Configs ───────────────────────────

SPORTS = {
    "pl": SportConfig(
        name="Premier League",
        league_id="eng.1",
        outcomes=["home", "draw", "away"],  # 3-way
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.20,
        positions_max=6,
        features=[
            "form_5",
            "gd",
            "h2h_home_wins",
            "home_strength",
            "away_strength",
            "rest_days",
            "injuries_count",
        ],
    ),
    "nfl": SportConfig(
        name="National Football League",
        league_id="nfl",
        outcomes=["home", "away"],  # Binary (no draws)
        min_edges={"home": 0.04, "away": 0.04},
        kelly_fraction=0.15,  # More conservative than PL
        positions_max=4,  # Fewer games per week
        features=[
            "form_5",
            "yards_diff",
            "turnover_diff",
            "home_strength",
            "rest_days",
            "injuries_count",
        ],
    ),
    "laliga": SportConfig(
        name="La Liga",
        league_id="esp.1",
        outcomes=["home", "draw", "away"],  # 3-way (like PL)
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.20,
        positions_max=6,
        features=[
            "form_5",
            "gd",
            "h2h_home_wins",
            "home_strength",
            "away_strength",
        ],
    ),
    "ucl": SportConfig(
        name="UEFA Champions League",
        league_id="ucl",
        outcomes=["home", "draw", "away"],  # 3-way
        min_edges={"home": 0.04, "draw": 0.07, "away": 0.05},
        kelly_fraction=0.18,  # Slightly more conservative (European comps)
        positions_max=4,
        features=[
            "form_5",
            "gd",
            "h2h_home_wins",
            "home_strength",
            "away_strength",
        ],
    ),
    "mex": SportConfig(
        name="Liga Mexicana (MX1)",
        league_id="mex.1",
        outcomes=["home", "draw", "away"],  # 3-way (like PL)
        min_edges={"home": 0.03, "draw": 0.05, "away": 0.03},  # Lower thresholds (higher volatility)
        kelly_fraction=0.18,  # Slightly more conservative than PL
        positions_max=6,
        features=[
            "form_5",
            "gd",
            "h2h_home_wins",
            "home_strength",
            "away_strength",
            "form_consistency",
        ],
    ),
    "brasil": SportConfig(
        name="Campeonato Brasileiro Serie A",
        league_id="bra.1",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.18,
        positions_max=6,
        features=["form_5", "gd", "h2h_home_wins", "home_strength", "away_strength"],
    ),
    "libertadores": SportConfig(
        name="Copa Libertadores",
        league_id="lib",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.05, "draw": 0.07, "away": 0.05},  # Higher edge (fewer games)
        kelly_fraction=0.15,  # More conservative
        positions_max=4,
        features=["form_5", "gd", "h2h_home_wins", "home_strength", "away_strength"],
    ),
    "seriea": SportConfig(
        name="Serie A (Italia)",
        league_id="ita.1",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.20,
        positions_max=6,
        features=["form_5", "gd", "h2h_home_wins", "home_strength", "away_strength"],
    ),
    "bundesliga": SportConfig(
        name="Bundesliga (Alemania)",
        league_id="ger.1",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.20,
        positions_max=6,
        features=["form_5", "gd", "h2h_home_wins", "home_strength", "away_strength"],
    ),
    "ligue1": SportConfig(
        name="Ligue 1 (Francia)",
        league_id="fra.1",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.20,
        positions_max=6,
        features=["form_5", "gd", "h2h_home_wins", "home_strength", "away_strength"],
    ),
    "mls": SportConfig(
        name="Major League Soccer (USA/Canada)",
        league_id="mls",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.17,
        positions_max=5,
        features=["form_5", "gd", "home_strength", "away_strength"],  # Fewer features (less historical data)
    ),
    "superlig": SportConfig(
        name="Süper Lig (Turquia)",
        league_id="tur.1",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.04, "draw": 0.06, "away": 0.04},
        kelly_fraction=0.18,
        positions_max=6,
        features=["form_5", "gd", "h2h_home_wins", "home_strength", "away_strength"],
    ),
    "worldcup": SportConfig(
        name="FIFA World Cup",
        league_id="wcup",
        outcomes=["home", "draw", "away"],
        min_edges={"home": 0.05, "draw": 0.08, "away": 0.05},
        kelly_fraction=0.12,  # Very conservative (rare events, high variance)
        positions_max=2,  # Fewer simultaneous positions
        features=["form_10", "h2h_wins", "strength_rating"],  # Different features
    ),
}


def get_sport_config(sport_code: str) -> SportConfig:
    """Get config for a sport. Raise if not found."""
    if sport_code.lower() not in SPORTS:
        raise ValueError(
            f"Unknown sport: {sport_code}. Available: {list(SPORTS.keys())}"
        )
    return SPORTS[sport_code.lower()]


def list_sports() -> List[str]:
    """List available sports."""
    return list(SPORTS.keys())


def main():
    """Test configurations."""
    print("[TEST] Available sports:")
    for code in list_sports():
        config = get_sport_config(code)
        print(f"  {code:6} : {config.name:30} | Outcomes: {', '.join(config.outcomes)}")

    print("\n[TEST] PL Config:")
    pl = get_sport_config("pl")
    print(f"  League: {pl.league_id}")
    print(f"  Min edges: {pl.min_edges}")
    print(f"  Kelly fraction: {pl.kelly_fraction}")
    print(f"  Max positions: {pl.positions_max}")


if __name__ == "__main__":
    main()
