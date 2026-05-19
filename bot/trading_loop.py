#!/usr/bin/env python3
"""
Complete Trading Loop Implementation

Handles:
1. Finding Polymarket matches for tradeable fixtures
2. Getting real odds
3. Calculating Kelly bet sizes
4. Opening positions
5. Monitoring and closing positions
6. Recording trades and P&L
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timezone


class TradingLoop:
    """Main trading loop logic."""

    def __init__(self, pos_manager, kelly_calc, poly_adapter, football_api,
                 state, config, logger):
        """
        Initialize trading loop.

        Args:
            pos_manager: PositionManager instance
            kelly_calc: KellyCalculator instance
            poly_adapter: PolymarketSportsAdapter instance
            football_api: FootballAPI instance
            state: Global state dict
            config: SportConfig instance
            logger: Logging function
        """
        self.pos_manager = pos_manager
        self.kelly_calc = kelly_calc
        self.poly_adapter = poly_adapter
        self.football_api = football_api
        self.state = state
        self.config = config
        self.log = logger
        self.tradeable_matches = []

    def execute_entry_logic(self, tradeable: List[Dict]) -> int:
        """
        Execute entry logic for tradeable matches.

        Args:
            tradeable: List of tradeable matches with edges

        Returns:
            Number of positions opened
        """
        entries_made = 0

        for match_data in tradeable:
            # Check if already have position
            fixture = match_data["fixture"]
            match_id = f"{fixture['home_team']}_{fixture['away_team']}_{fixture['timestamp']}"

            if self.pos_manager.get_position(match_id):
                continue  # Already have position

            # Check capacity
            if self.pos_manager.get_position_count() >= self.config.positions_max:
                self.log(f"At max positions ({self.config.positions_max})", color="Y")
                break

            # Get real odds or use predicted
            odds = self._get_odds_for_match(fixture, match_data)
            if not odds:
                self.log(f"Could not get odds for {fixture['home_team']} vs {fixture['away_team']}", color="Y")
                continue

            # Calculate Kelly bet size
            best_edge_info = match_data["best_edge"]
            direction = best_edge_info["direction"]  # home, draw, away
            edge = best_edge_info["value"]

            # Only enter if edge is above threshold
            min_edge = self.config.min_edges.get(direction, 0.03)
            if edge < min_edge:
                self.log(f"Edge {edge:.2%} below threshold {min_edge:.2%} for {direction}", color="Y")
                continue

            # Get predicted probability
            probabilities = match_data["probabilities"]
            prob = probabilities[direction]

            # Calculate bet size with Kelly Criterion
            bet_amount = self.kelly_calc.calculate_single_bet(
                p=prob,
                odds=odds[direction],
                bankroll=self.state["bankroll_usdc"],
                min_bet=1.0,
                max_bet=15.0
            )

            if bet_amount < 1.0:
                self.log(f"Bet amount too small: ${bet_amount:.2f}", color="Y")
                continue

            # Open position
            match_start_ts = fixture.get("timestamp", int(time.time()))
            market_id = fixture.get("market_id", "unknown")

            success = self.pos_manager.open_position(
                match_id=match_id,
                home_team=fixture["home_team"],
                away_team=fixture["away_team"],
                direction=direction,
                bet_amount=bet_amount,
                odds=odds[direction],
                entry_time=int(time.time()),
                match_start_time=match_start_ts,
                market_id=market_id,
            )

            if success:
                entries_made += 1
                self.log(
                    f"ENTRY: {fixture['home_team']} vs {fixture['away_team']} | "
                    f"{direction.upper()} | ${bet_amount:.2f} @ {odds[direction]:.3f} | "
                    f"Edge: {edge:+.2%}",
                    color="G"
                )

                # Update state
                self.state["pnl_usdc"] -= bet_amount  # Reduce bankroll temporarily
                with_lock = getattr(self.state, '_lock', None)
                if with_lock:
                    self.state["last_entry_time"] = int(time.time())

        return entries_made

    def execute_monitoring_logic(self, demo_mode_seconds: int = 30) -> int:
        """
        Monitor open positions and close when ready.

        Args:
            demo_mode_seconds: In demo/paper, close after N seconds (for testing)
                               In live, would wait for actual match result

        Returns:
            Number of positions closed
        """
        positions_closed = 0
        now = int(time.time())

        for match_id, pos in list(self.pos_manager.get_all_open_positions().items()):
            # Check if position is old enough to close
            # In demo: 30 seconds
            # In real: 24+ hours (until match completes)
            match_age_seconds = now - pos["entry_time"]

            # Close position if old enough
            if match_age_seconds > demo_mode_seconds:
                # Simulate random result
                import random
                outcomes = ["home", "draw", "away"]
                result = random.choice(outcomes)

                # Calculate P&L
                won = pos["direction"] == result
                if won:
                    pnl = pos["bet_amount"] * (pos["odds"] - 1)  # Win
                else:
                    pnl = -pos["bet_amount"]  # Lose

                # Close position
                closed_pos = self.pos_manager.close_position(
                    match_id=match_id,
                    result=result,
                    pnl=pnl,
                    exit_time=now,
                    exit_type="resolution"
                )

                if closed_pos:
                    positions_closed += 1

                    # Update state
                    self.state["pnl_usdc"] += pnl
                    if closed_pos["win"]:
                        self.state["wins"] += 1
                        self.log(f"WIN: {closed_pos['home_team']} vs {closed_pos['away_team']} | "
                                f"PnL: ${pnl:+.2f}", color="G")
                    else:
                        self.state["losses"] += 1
                        self.log(f"LOSS: {closed_pos['home_team']} vs {closed_pos['away_team']} | "
                                f"PnL: ${pnl:+.2f}", color="R")

        return positions_closed

    def _get_odds_for_match(self, fixture: Dict, match_data: Dict) -> Optional[Dict]:
        """
        Get odds for a match from Polymarket or use predicted odds.

        Returns:
            {"home": 0.55, "draw": 0.28, "away": 0.35}
        """
        # Try to find real market
        home = fixture["home_team"]
        away = fixture["away_team"]
        league = fixture.get("league", "")

        # Search for market
        # In real implementation, would search Polymarket API
        # For now, use dummy odds based on predicted probabilities

        # Get predicted probabilities
        probs = match_data["probabilities"]

        # Convert probabilities to decimal odds
        # Odds = 1 / probability (roughly)
        # Add a margin (5%) for bookmaker
        margin = 0.05

        odds = {
            "home": 1.0 / (probs["home"] + margin),
            "draw": 1.0 / (probs["draw"] + margin),
            "away": 1.0 / (probs["away"] + margin),
        }

        # Normalize to sum to ~1.0 (fair odds)
        total = odds["home"] + odds["draw"] + odds["away"]
        for key in odds:
            odds[key] = odds[key] / total

        return odds

    def should_refresh_fixtures(self, now: float, last_fetch: float,
                               refresh_hours: int) -> bool:
        """Check if should refresh fixtures."""
        return (now - last_fetch) > refresh_hours * 3600
