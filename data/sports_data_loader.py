#!/usr/bin/env python3
"""
Sports Data Loader

Load historical match data from ESPN or CSV for backtesting.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests


class SportsDataLoader:
    """Load historical sports data."""

    def __init__(self, sport_code: str = "pl"):
        self.sport_code = sport_code.lower()
        self.cache_dir = "data/historical"
        os.makedirs(self.cache_dir, exist_ok=True)

    def load_season(
        self,
        season_start: str,  # "2023-08-01"
        season_end: str,  # "2024-05-31"
    ) -> List[Dict]:
        """
        Load all matches from ESPN for a season.

        Returns:
            [{
                "date": "2023-08-15",
                "home_team": "Arsenal",
                "away_team": "Nottingham",
                "home_goals": 2,
                "away_goals": 1,
                "result": "home",  # home/draw/away
                "home_stats": {...},
                "away_stats": {...},
            }]
        """
        cache_file = self._cache_path(season_start, season_end)

        # Try cache first
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                return json.load(f)

        # Fetch from ESPN
        matches = self._fetch_from_espn(season_start, season_end)

        # Cache it
        with open(cache_file, "w") as f:
            json.dump(matches, f, indent=2)

        return matches

    def _cache_path(self, season_start: str, season_end: str) -> str:
        """Get cache file path."""
        return os.path.join(
            self.cache_dir,
            f"{self.sport_code}_{season_start}_{season_end}.json",
        )

    def _fetch_from_espn(self, season_start: str, season_end: str) -> List[Dict]:
        """Fetch historical data from ESPN API."""
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(season_start)
            end_dt = datetime.fromisoformat(season_end)

            # For now, return mock data (in production, parse ESPN API)
            # ESPN doesn't have easy historical API access, so we'd need:
            # - Web scraping
            # - CSV import
            # - Or third-party sports data service

            matches = []
            current_dt = start_dt

            while current_dt <= end_dt:
                # Generate mock matches for testing
                # In production, fetch real data
                if current_dt.weekday() < 5:  # Weekday
                    match = {
                        "date": current_dt.strftime("%Y-%m-%d"),
                        "home_team": "Manchester United",
                        "away_team": "Liverpool",
                        "home_goals": 2,
                        "away_goals": 1,
                        "result": "home",
                        "home_stats": {
                            "form_5": 0.70,
                            "gd": 0.15,
                            "h2h_wins": 2,
                        },
                        "away_stats": {
                            "form_5": 0.50,
                            "gd": -0.10,
                            "h2h_wins": 0,
                        },
                    }
                    matches.append(match)

                current_dt += timedelta(days=3)

            return matches

        except Exception as e:
            print(f"[DATA] ESPN fetch error: {e}")
            return []

    def load_from_csv(self, csv_path: str) -> List[Dict]:
        """
        Load matches from CSV file.

        CSV format:
        date,home_team,away_team,home_goals,away_goals
        2023-08-15,Arsenal,Nottingham,2,1
        ...
        """
        try:
            import csv

            matches = []
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    home_goals = int(row["home_goals"])
                    away_goals = int(row["away_goals"])

                    if home_goals > away_goals:
                        result = "home"
                    elif home_goals < away_goals:
                        result = "away"
                    else:
                        result = "draw"

                    match = {
                        "date": row["date"],
                        "home_team": row["home_team"],
                        "away_team": row["away_team"],
                        "home_goals": home_goals,
                        "away_goals": away_goals,
                        "result": result,
                        "home_stats": {},  # Will be populated from API
                        "away_stats": {},
                    }
                    matches.append(match)

            return matches

        except Exception as e:
            print(f"[DATA] CSV load error: {e}")
            return []

    def get_match_count(self, matches: List[Dict]) -> Dict:
        """Count results distribution."""
        results = {"home": 0, "draw": 0, "away": 0}
        for match in matches:
            result = match.get("result")
            if result in results:
                results[result] += 1

        return results


def main():
    """Test data loading."""
    loader = SportsDataLoader("pl")

    print("[TEST] Loading PL 2023-24 season...")
    matches = loader.load_season("2023-08-01", "2024-05-31")
    print(f"  Loaded {len(matches)} matches")

    if matches:
        print(f"\n[TEST] First 3 matches:")
        for m in matches[:3]:
            print(f"  {m['date']}: {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']}")

        print(f"\n[TEST] Results distribution:")
        dist = loader.get_match_count(matches)
        for result, count in dist.items():
            pct = 100 * count / len(matches)
            print(f"  {result:6} : {count:3} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
