#!/usr/bin/env python3
"""
Match Monitor

Polls for match results and settles positions.
"""

import time
from typing import Optional, Dict
from datetime import datetime, timezone

from data.football_api import FootballAPI


class MatchMonitor:
    """Monitor match results and settle positions."""

    def __init__(self):
        self.api = FootballAPI()
        self.poll_interval = 60  # seconds
        self.max_wait = 7200  # 2 hours after match start

    def wait_for_result(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        entry_time: float,
        match_start_time: float,
        timeout: int = 7200,
    ) -> Optional[Dict]:
        """
        Poll for match result.

        Returns:
            {"result": "home", "score": "2-1", "finished": true}
            or None if timeout
        """
        deadline = time.time() + timeout
        attempt = 0

        while time.time() < deadline:
            attempt += 1
            try:
                # Query ESPN or cached data for result
                result = self._query_match_result(home_team, away_team)

                if result and result.get("finished"):
                    return result

                # Not finished, wait and retry
                wait_time = min(300, self.poll_interval * (1 + attempt // 10))
                print(f"[MONITOR] Match {home_team} vs {away_team}: "
                      f"not finished, waiting {wait_time}s... (attempt {attempt})")
                time.sleep(wait_time)

            except Exception as e:
                print(f"[MONITOR] Error querying result: {e}")
                time.sleep(60)

        # Timeout
        print(f"[MONITOR] Timeout waiting for {home_team} vs {away_team}")
        return None

    def _query_match_result(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Query ESPN API for match result."""
        try:
            # Simplified: in production, would parse ESPN API response
            # For now, return None (match not finished)
            # This would be replaced with real ESPN parsing

            return {
                "finished": False,
                "result": None,
                "score": None,
            }

        except Exception as e:
            print(f"[MONITOR] Query error: {e}")
            return None

    def determine_outcome(self, score: str) -> Optional[str]:
        """
        Determine match outcome from score string (e.g., "2-1").

        Returns:
            "home", "draw", or "away"
        """
        if not score or "-" not in score:
            return None

        try:
            parts = score.split("-")
            home_goals = int(parts[0].strip())
            away_goals = int(parts[1].strip())

            if home_goals > away_goals:
                return "home"
            elif home_goals < away_goals:
                return "away"
            else:
                return "draw"

        except Exception:
            return None

    def calculate_pnl(
        self,
        bet_amount: float,
        odds: float,
        direction: str,
        result: str,
    ) -> float:
        """Calculate PnL from bet outcome."""
        won = direction == result
        if won:
            # Payout = bet / odds
            payout = bet_amount / odds
            pnl = payout - bet_amount
        else:
            pnl = -bet_amount

        return pnl


def main():
    """Test match monitor."""
    monitor = MatchMonitor()

    print("[TEST] Determining outcomes...")
    test_scores = ["2-1", "0-0", "1-2", "invalid"]
    for score in test_scores:
        result = monitor.determine_outcome(score)
        print(f"  {score}: {result}")

    print("\n[TEST] Calculating PnL...")
    test_cases = [
        (10, 0.50, "home", "home"),  # Win
        (10, 0.50, "home", "away"),  # Loss
        (15, 0.30, "draw", "draw"),  # Win
    ]
    for bet, odds, direction, result in test_cases:
        pnl = monitor.calculate_pnl(bet, odds, direction, result)
        print(f"  Bet ${bet} @ {odds:.2f} on {direction}, result {result}: PnL=${pnl:+.2f}")


if __name__ == "__main__":
    main()
