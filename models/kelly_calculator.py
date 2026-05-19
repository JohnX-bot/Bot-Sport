#!/usr/bin/env python3
"""
Kelly Criterion for 3-Way Bets

Adapted from binary Kelly for trinomial outcomes (Win/Draw/Loss).
"""

from typing import Dict, Optional


class KellyCalculator:
    """Calculate optimal bet sizes using Kelly criterion."""

    def __init__(self, kelly_fraction: float = 0.25):
        """
        Args:
            kelly_fraction: Fraction of full Kelly to use (e.g., 0.25 = quarter Kelly)
        """
        self.kelly_fraction = kelly_fraction

    def calculate_3way_kelly(
        self,
        p_home: float,
        p_draw: float,
        p_away: float,
        odds_home: float,
        odds_draw: float,
        odds_away: float,
        bankroll: float,
        min_bet: float = 1.0,
        max_bet: float = 50.0,
    ) -> Dict:
        """
        Calculate Kelly-sized bets for all three outcomes.

        Args:
            p_home, p_draw, p_away: Model's probabilities (must sum ≈ 1.0)
            odds_home, odds_draw, odds_away: Market odds (decimal, e.g., 0.55)
            bankroll: Available USDC
            min_bet, max_bet: Bet constraints

        Returns:
            {
                "bets": {"home": 10, "draw": 5, "away": 3},
                "total_bet": 18,
                "allocations": {"home": 0.10, "draw": 0.05, "away": 0.03},
                "edges": {"home": 0.02, "draw": -0.03, "away": 0.05},
                "recommended": {"direction": "away", "amount": 3},
            }
        """

        # Validate inputs
        prob_sum = p_home + p_draw + p_away
        if abs(prob_sum - 1.0) > 0.01:
            p_home /= prob_sum
            p_draw /= prob_sum
            p_away /= prob_sum

        # Calculate edges (P_model - odds)
        edge_home = p_home - odds_home
        edge_draw = p_draw - odds_draw
        edge_away = p_away - odds_away

        # Binary Kelly for each outcome (simplified approach)
        # This treats each outcome independently, then applies fraction
        bets = {}
        allocations = {}

        for outcome, p, odds in [
            ("home", p_home, odds_home),
            ("draw", p_draw, odds_draw),
            ("away", p_away, odds_away),
        ]:
            # Kelly for binary (outcome wins vs all others lose)
            if odds <= 0 or odds >= 1:
                bets[outcome] = 0
                allocations[outcome] = 0
                continue

            b = (1.0 / odds) - 1  # Payout if win
            q = 1.0 - p  # Prob of loss

            # Kelly fraction
            kelly_f = (p * b - q) / b if b > 0 else 0
            if kelly_f <= 0:
                bets[outcome] = 0
                allocations[outcome] = 0
                continue

            # Apply kelly_fraction (e.g., 0.25 = quarter Kelly)
            kelly_f = max(0, kelly_f * self.kelly_fraction)

            # Convert to USDC
            bet_amount = kelly_f * bankroll
            bet_amount = max(min_bet, min(max_bet, bet_amount))

            bets[outcome] = bet_amount
            allocations[outcome] = bet_amount / bankroll

        total_bet = sum(bets.values())

        # Recommend best opportunity
        edges = {
            "home": edge_home,
            "draw": edge_draw,
            "away": edge_away,
        }
        best_dir = max(edges, key=edges.get)
        best_edge = edges[best_dir]

        return {
            "bets": bets,
            "total_bet": total_bet,
            "allocations": allocations,
            "edges": edges,
            "recommended": {
                "direction": best_dir,
                "amount": bets[best_dir],
                "edge": best_edge,
            },
        }

    def calculate_single_bet(
        self,
        p: float,
        odds: float,
        bankroll: float,
        min_bet: float = 1.0,
        max_bet: float = 50.0,
    ) -> float:
        """
        Calculate Kelly-sized bet for a single outcome.

        Args:
            p: Probability of winning
            odds: Market odds (decimal)
            bankroll: Available capital
            min_bet, max_bet: Constraints

        Returns:
            Bet amount in USDC
        """
        if odds <= 0 or odds >= 1 or p <= odds:
            return 0.0

        b = (1.0 / odds) - 1
        f = (p * b - (1 - p)) / b if b > 0 else 0

        if f <= 0:
            return 0.0

        f = f * self.kelly_fraction
        bet = bankroll * f
        bet = max(min_bet, min(max_bet, bet))

        if bet > bankroll:
            bet = bankroll

        return bet


def main():
    """Test Kelly calculation."""
    calc = KellyCalculator(kelly_fraction=0.25)

    # Test 3-way
    print("[TEST] 3-way Kelly:")
    result = calc.calculate_3way_kelly(
        p_home=0.48,
        p_draw=0.25,
        p_away=0.27,
        odds_home=0.55,
        odds_draw=0.28,
        odds_away=0.35,
        bankroll=100.0,
        min_bet=1.0,
        max_bet=15.0,
    )

    print(f"  Bets: Home=${result['bets']['home']:.2f}, "
          f"Draw=${result['bets']['draw']:.2f}, "
          f"Away=${result['bets']['away']:.2f}")
    print(f"  Total: ${result['total_bet']:.2f}")
    print(f"  Edges: Home={result['edges']['home']:+.3f}, "
          f"Draw={result['edges']['draw']:+.3f}, "
          f"Away={result['edges']['away']:+.3f}")
    print(f"  Recommended: {result['recommended']['direction']} "
          f"${result['recommended']['amount']:.2f} "
          f"(edge {result['recommended']['edge']:+.3f})")

    print("\n[TEST] Single bet:")
    bet = calc.calculate_single_bet(
        p=0.48,
        odds=0.55,
        bankroll=100.0,
    )
    print(f"  Kelly bet for P(0.48) @ odds 0.55: ${bet:.2f}")


if __name__ == "__main__":
    main()
