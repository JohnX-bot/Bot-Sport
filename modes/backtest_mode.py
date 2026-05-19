#!/usr/bin/env python3
"""
Backtest Mode

Historical backtesting entry point.
"""

import sys
from datetime import datetime
from data.sports_data_loader import SportsDataLoader
from bot.backtest_runner import BacktestRunner


def run_backtest(
    sport: str,
    predictor: str,
    start_date: str,
    end_date: str,
    bankroll: float = 100.0,
) -> dict:
    """
    Run backtest for a given sport and date range.

    Args:
        sport: "pl", "nfl", "laliga", "ucl"
        predictor: "heuristic" or "logistic"
        start_date: "2023-08-01"
        end_date: "2024-05-31"
        bankroll: Starting bankroll in USDC

    Returns:
        Backtest report dictionary
    """

    print(f"\n{'='*70}")
    print(f"BACKTEST MODE")
    print(f"{'='*70}")
    print(f"Sport      : {sport.upper()}")
    print(f"Predictor  : {predictor}")
    print(f"Period     : {start_date} to {end_date}")
    print(f"Bankroll   : ${bankroll:.2f}")
    print()

    # Load historical data
    print(f"[LOAD] Loading historical {sport.upper()} data...")
    loader = SportsDataLoader(sport_code=sport)
    matches = loader.load_season(start_date, end_date)

    if not matches:
        print(f"[ERROR] No matches found for {sport} in period {start_date} to {end_date}")
        return {}

    print(f"[LOAD] Loaded {len(matches)} matches")

    # Run backtest
    print(f"\n[BACKTEST] Running simulation...")
    runner = BacktestRunner(
        sport_code=sport,
        predictor_type=predictor,
        bankroll=bankroll,
    )

    report = runner.run(matches)

    # Print report
    print("\n" + "=" * 70)
    print(f"{'BACKTEST REPORT':^70}")
    print("=" * 70)
    print(f"Sport               : {report.get('sport', 'N/A')}")
    print(f"Predictor           : {report.get('predictor', 'N/A')}")
    print(f"Period              : {start_date} to {end_date}")
    print("-" * 70)
    print(f"Matches analyzed    : {report.get('total_matches_analyzed', 0)}")
    print(f"Trades executed     : {report.get('total_trades', 0)}")
    print(f"  Wins              : {report.get('wins', 0)}")
    print(f"  Losses            : {report.get('losses', 0)}")
    print(f"  Win rate          : {report.get('win_rate', 0):.1%}")
    print("-" * 70)
    print(f"Starting bankroll   : ${report.get('starting_bankroll', 0):.2f}")
    print(f"Ending bankroll     : ${report.get('ending_bankroll', 0):.2f}")
    print(f"Total P&L           : ${report.get('total_pnl', 0):+.2f}")
    print(f"Avg P&L/trade       : ${report.get('avg_pnl_per_trade', 0):+.2f}")
    print(f"Return %            : {report.get('return_pct', 0):+.1f}%")
    print("-" * 70)
    print(f"Brier score         : {report.get('brier_score', 0):.4f} (lower is better)")
    print(f"Sharpe ratio        : {report.get('sharpe_ratio', 0):.2f}")
    print(f"Duration            : {report.get('duration_secs', 0):.1f}s")
    print("=" * 70)

    return report


def main():
    """CLI interface for backtest mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Sports betting bot - Backtest mode")
    parser.add_argument("--sport", default="pl", help="Sport code (pl, nfl, laliga, ucl)")
    parser.add_argument("--predictor", default="heuristic", help="Predictor (heuristic, logistic)")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--bankroll", type=float, default=100.0, help="Starting bankroll (USDC)")

    args = parser.parse_args()

    # Validate dates
    try:
        start = datetime.fromisoformat(args.start_date)
        end = datetime.fromisoformat(args.end_date)
        if start > end:
            print("[ERROR] Start date must be before end date")
            sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] Invalid date format: {e}")
        sys.exit(1)

    # Run backtest
    report = run_backtest(
        sport=args.sport,
        predictor=args.predictor,
        start_date=args.start_date,
        end_date=args.end_date,
        bankroll=args.bankroll,
    )

    # Return success
    return 0 if report else 1


if __name__ == "__main__":
    sys.exit(main())
