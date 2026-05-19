#!/usr/bin/env python3
"""
Position Manager for Multiple Concurrent Bets

Tracks and manages multiple open positions across different matches.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class PositionManager:
    """Manage multiple concurrent match positions."""

    def __init__(self, max_positions: int = 6):
        self.positions: Dict[str, Dict] = {}
        self.max_positions = max_positions
        self.position_history: List[Dict] = []

    def open_position(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        direction: str,  # "home", "draw", "away"
        bet_amount: float,
        odds: float,
        entry_time: float,
        match_start_time: float,
        market_id: str,
    ) -> bool:
        """
        Open a new position.

        Args:
            match_id: Unique match identifier
            direction: Which outcome we're betting on
            bet_amount: USDC wagered
            odds: Market odds (decimal, e.g., 0.55)
            entry_time: Unix timestamp when bet was placed
            match_start_time: Unix timestamp when match starts

        Returns:
            True if opened, False if at max capacity
        """
        if len(self.positions) >= self.max_positions:
            return False

        if match_id in self.positions:
            return False  # Position already exists

        shares = bet_amount / odds
        position = {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "direction": direction,
            "bet_amount": bet_amount,
            "odds": odds,
            "shares": shares,
            "entry_time": entry_time,
            "entry_iso": datetime.fromtimestamp(entry_time, tz=timezone.utc).isoformat(),
            "match_start_time": match_start_time,
            "market_id": market_id,
            "status": "open",  # open, closed_win, closed_loss, closed_early
            "exit_time": None,
            "exit_price": None,
            "pnl": None,
            "win": None,
        }
        self.positions[match_id] = position
        return True

    def close_position(
        self,
        match_id: str,
        result: str,  # "home", "draw", "away"
        pnl: float,
        exit_time: float,
        exit_type: str = "resolution",  # resolution, pre_sell, stop_loss
    ) -> Optional[Dict]:
        """
        Close a position with result.

        Returns:
            Updated position dict, or None if not found
        """
        if match_id not in self.positions:
            return None

        pos = self.positions[match_id]
        won = pos["direction"] == result
        pos["status"] = "closed_win" if won else "closed_loss"
        pos["exit_time"] = exit_time
        pos["exit_iso"] = datetime.fromtimestamp(exit_time, tz=timezone.utc).isoformat()
        pos["pnl"] = pnl
        pos["win"] = won
        pos["exit_type"] = exit_type

        # Move to history
        self.position_history.append(pos)

        # Remove from active
        del self.positions[match_id]

        return pos

    def close_position_early(
        self,
        match_id: str,
        exit_price: float,
        pnl: float,
        exit_time: float,
        reason: str = "pre_sell",
    ) -> Optional[Dict]:
        """Close position before match ends (e.g., take profit)."""
        if match_id not in self.positions:
            return None

        pos = self.positions[match_id]
        won = pnl > 0
        pos["status"] = "closed_win" if won else "closed_loss"
        pos["exit_price"] = exit_price
        pos["exit_time"] = exit_time
        pos["exit_iso"] = datetime.fromtimestamp(exit_time, tz=timezone.utc).isoformat()
        pos["pnl"] = pnl
        pos["win"] = won
        pos["exit_type"] = reason

        self.position_history.append(pos)
        del self.positions[match_id]

        return pos

    def get_position(self, match_id: str) -> Optional[Dict]:
        """Get active position by match ID."""
        return self.positions.get(match_id)

    def get_all_open_positions(self) -> Dict[str, Dict]:
        """Get all currently open positions."""
        return self.positions.copy()

    def get_position_count(self) -> int:
        """Number of open positions."""
        return len(self.positions)

    def get_total_exposure(self) -> float:
        """Total USDC at risk."""
        return sum(p["bet_amount"] for p in self.positions.values())

    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get closed positions history."""
        hist = self.position_history.copy()
        if limit:
            hist = hist[-limit:]
        return hist

    def calculate_stats(self) -> Dict:
        """Calculate performance statistics."""
        if not self.position_history:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl_per_trade": 0.0,
                "open_positions": 0,
                "open_exposure": 0.0,
            }

        total = len(self.position_history)
        wins = sum(1 for p in self.position_history if p.get("win"))
        losses = total - wins
        total_pnl = sum(p.get("pnl", 0) for p in self.position_history)
        avg_pnl = total_pnl / total if total > 0 else 0

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total if total > 0 else 0,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": avg_pnl,
            "open_positions": len(self.positions),
            "open_exposure": self.get_total_exposure(),
        }

    def save_history(self, filepath: str):
        """Save position history to file."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "positions": self.position_history,
            "stats": self.calculate_stats(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_history(self, filepath: str):
        """Load position history from file."""
        try:
            with open(filepath) as f:
                data = json.load(f)
            self.position_history = data.get("positions", [])
        except Exception as e:
            print(f"[POS] Load history error: {e}")


def main():
    """Test position manager."""
    mgr = PositionManager(max_positions=6)

    print("[TEST] Opening positions...")
    now = time.time()

    # Open 3 positions
    for i, (home, away, direction) in enumerate([
        ("Man United", "Liverpool", "home"),
        ("Arsenal", "Tottenham", "away"),
        ("Chelsea", "Man City", "draw"),
    ]):
        match_id = f"match_{i}"
        result = mgr.open_position(
            match_id=match_id,
            home_team=home,
            away_team=away,
            direction=direction,
            bet_amount=10 + i * 5,
            odds=0.50 + i * 0.05,
            entry_time=now,
            match_start_time=now + 3600,
            market_id=f"market_{i}",
        )
        print(f"  {home} vs {away} ({direction}): {'OK' if result else 'FAILED'}")

    print(f"\nOpen positions: {mgr.get_position_count()}")
    print(f"Total exposure: ${mgr.get_total_exposure():.2f}")

    # Close first position
    print("\n[TEST] Closing position...")
    mgr.close_position("match_0", result="home", pnl=5.0, exit_time=now + 5400)

    print(f"Open positions: {mgr.get_position_count()}")
    print(f"Closed positions: {len(mgr.position_history)}")

    # Stats
    print("\n[TEST] Stats:")
    stats = mgr.calculate_stats()
    print(f"  Trades: {stats['total_trades']}")
    print(f"  Win rate: {stats['win_rate']:.1%}")
    print(f"  Total PnL: ${stats['total_pnl']:.2f}")


if __name__ == "__main__":
    main()
