#!/usr/bin/env python3
"""
Polymarket Sports Markets Integration

Fetch PL match markets and odds from Polymarket via CLOB API.
"""

import json
import time
from typing import Optional, Dict, List

import requests


class PolymarketSportsAdapter:
    """Fetch sports markets from Polymarket."""

    def __init__(self):
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.clob_api = "https://clob.polymarket.com"
        self.market_cache = {}

    def find_pl_markets(self, limit: int = 50) -> List[Dict]:
        """
        Fetch Premier League match markets from Polymarket.

        Returns:
            List of markets with {id, slug, outcomes, clobTokenIds, ...}
        """
        try:
            # Search for PL markets
            resp = requests.get(
                f"{self.gamma_api}/markets",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": limit,
                    "order": "endDate",
                    "ascending": "true",
                },
                timeout=10,
            )
            resp.raise_for_status()
            markets = resp.json()

            # Filter for PL (or any sports markets containing "Premier" or "Football")
            pl_markets = [
                m for m in markets
                if any(
                    keyword in (m.get("slug", "") or "").lower()
                    for keyword in ["premier", "football", "soccer", "pl "]
                )
                and any(
                    keyword in (m.get("slug", "") or "").lower()
                    for keyword in ["vs", "match", "win"]
                )
            ]

            return pl_markets

        except Exception as e:
            print(f"[POLY] Find markets error: {e}")
            return []

    def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        """Fetch a specific market by slug."""
        if slug in self.market_cache:
            return self.market_cache[slug]

        try:
            resp = requests.get(
                f"{self.gamma_api}/markets",
                params={"slug": slug},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            market = data[0] if isinstance(data, list) and data else data
            if market:
                self.market_cache[slug] = market
            return market

        except Exception as e:
            print(f"[POLY] Get market error: {e}")
            return None

    def fetch_odds(self, market: Dict) -> Optional[Dict]:
        """
        Fetch real-time odds for a market (Home/Draw/Away).

        Returns:
            {"home": 0.55, "draw": 0.28, "away": 0.35}
        """
        try:
            token_ids_raw = market.get("clobTokenIds")
            outcomes_raw = market.get("outcomes")

            if not token_ids_raw or not outcomes_raw:
                return None

            token_ids = (
                json.loads(token_ids_raw)
                if isinstance(token_ids_raw, str)
                else token_ids_raw
            )
            outcomes = (
                json.loads(outcomes_raw)
                if isinstance(outcomes_raw, str)
                else outcomes_raw
            )

            odds = {}
            for outcome, token_id in zip(outcomes, token_ids):
                if not token_id:
                    continue

                # Fetch CLOB midpoint price
                price = self._fetch_clob_midpoint(token_id)
                if price is not None:
                    key = self._normalize_outcome_key(outcome)
                    odds[key] = price

            # Validate: must have all 3 outcomes
            if len(odds) == 3 and set(odds.keys()) == {"home", "draw", "away"}:
                return odds

            return None

        except Exception as e:
            print(f"[POLY] Fetch odds error: {e}")
            return None

    def _fetch_clob_midpoint(self, token_id: str) -> Optional[float]:
        """Fetch CLOB midpoint price for a token."""
        try:
            resp = requests.get(
                f"{self.clob_api}/midpoint",
                params={"token_id": token_id},
                timeout=5,
            )
            if resp.status_code != 200:
                return None

            mid = resp.json().get("mid")
            return float(mid) if mid is not None else None

        except Exception:
            return None

    @staticmethod
    def _normalize_outcome_key(outcome: str) -> str:
        """Normalize outcome string to key."""
        outcome_lower = outcome.lower()
        if "home" in outcome_lower or "yes" in outcome_lower:
            return "home"
        elif "draw" in outcome_lower or "tie" in outcome_lower:
            return "draw"
        elif "away" in outcome_lower or "no" in outcome_lower:
            return "away"
        else:
            return outcome_lower

    def validate_odds(self, odds: Dict) -> bool:
        """Validate odds are reasonable (sum ≈ 1.0 for prob bets)."""
        if not odds or len(odds) != 3:
            return False

        total = sum(odds.values())
        # Odds sum to ~1.0 for prediction markets
        return 0.95 <= total <= 1.05 and all(0.01 <= v <= 0.99 for v in odds.values())


def main():
    """Test Polymarket integration."""
    adapter = PolymarketSportsAdapter()

    print("[TEST] Finding PL markets...")
    markets = adapter.find_pl_markets(limit=20)
    print(f"  Found {len(markets)} potential PL markets")

    if markets:
        print(f"\n[TEST] First 3 markets:")
        for m in markets[:3]:
            print(f"  - {m.get('slug')}")

        # Try to fetch odds for first market
        if markets:
            print(f"\n[TEST] Fetching odds for first market...")
            odds = adapter.fetch_odds(markets[0])
            if odds:
                print(f"  Odds: {odds}")
                print(f"  Valid: {adapter.validate_odds(odds)}")
            else:
                print(f"  (No complete odds available)")


if __name__ == "__main__":
    main()
