#!/usr/bin/env python3
"""
Unified Sports Betting Bot

Single entry point supporting:
- Mode: backtest | paper | live
- Sport: pl | nfl | laliga | ucl
- Predictor: heuristic | logistic
"""

import argparse
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sport_config import list_sports, get_sport_config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Sports Betting Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backtest PL 2023-24 with heuristic
  python bot/unified_bot.py --mode backtest --sport pl \\
    --start-date 2023-08-01 --end-date 2024-05-31

  # Paper trade PL with logistic predictor
  python bot/unified_bot.py --mode paper --sport pl --predictor logistic

  # Paper trade multiple sports
  python bot/unified_bot.py --mode paper --sport pl,nfl --bankroll 200

  # Live trading (when ready)
  python bot/unified_bot.py --mode live --sport pl --predictor logistic
        """,
    )

    # Mode
    parser.add_argument(
        "--mode",
        choices=["backtest", "paper", "live"],
        default="paper",
        help="Mode: backtest (historical), paper (simulated real-time), or live (real trades)",
    )

    # Sport(s)
    parser.add_argument(
        "--sport",
        default="pl",
        help=f"Sport code(s): {', '.join(list_sports())} or comma-separated for multiple",
    )

    # Predictor
    parser.add_argument(
        "--predictor",
        choices=["heuristic", "logistic"],
        default="heuristic",
        help="Prediction model: heuristic (rules-based) or logistic (ML)",
    )

    # Bankroll
    parser.add_argument(
        "--bankroll",
        type=float,
        default=100.0,
        help="Starting bankroll in USDC (default 100.0)",
    )

    # Backtest-specific
    parser.add_argument(
        "--start-date",
        help="Backtest start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        help="Backtest end date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    # Validate mode
    mode = args.mode.lower()
    if mode not in ["backtest", "paper", "live"]:
        print(f"[ERROR] Unknown mode: {mode}")
        return 1

    # Validate sport(s)
    sports = [s.strip() for s in args.sport.lower().split(",")]
    for sport in sports:
        try:
            get_sport_config(sport)
        except ValueError as e:
            print(f"[ERROR] {e}")
            return 1

    # Validate predictor
    if args.predictor not in ["heuristic", "logistic"]:
        print(f"[ERROR] Unknown predictor: {args.predictor}")
        return 1

    print(f"\n{'='*70}")
    print(f"UNIFIED SPORTS BETTING BOT")
    print(f"{'='*70}")
    print(f"Mode       : {mode.upper()}")
    print(f"Sport(s)   : {', '.join(sports)}")
    print(f"Predictor  : {args.predictor}")
    print(f"Bankroll   : ${args.bankroll:.2f}")
    print(f"{'='*70}\n")

    # Route to appropriate mode
    if mode == "backtest":
        return _run_backtest(sports, args.predictor, args.start_date, args.end_date, args.bankroll)
    elif mode == "paper":
        return _run_paper(sports, args.predictor, args.bankroll)
    else:  # live
        return _run_live(sports, args.predictor, args.bankroll)


def _run_backtest(sports, predictor, start_date, end_date, bankroll):
    """Run backtest mode."""
    if not start_date or not end_date:
        print("[ERROR] Backtest requires --start-date and --end-date")
        return 1

    from modes.backtest_mode import run_backtest

    print(f"[BACKTEST] Running for {len(sports)} sport(s)...")

    all_reports = {}
    for sport in sports:
        print(f"\n[BACKTEST] {sport.upper()}...")
        report = run_backtest(
            sport=sport,
            predictor=predictor,
            start_date=start_date,
            end_date=end_date,
            bankroll=bankroll,
        )
        all_reports[sport] = report

    # Compare if multiple sports
    if len(all_reports) > 1:
        print(f"\n{'='*70}")
        print(f"COMPARISON ACROSS SPORTS")
        print(f"{'='*70}")
        for sport, report in all_reports.items():
            print(f"\n{sport.upper()}:")
            print(f"  Win rate   : {report.get('win_rate', 0):.1%}")
            print(f"  P&L        : ${report.get('total_pnl', 0):+.2f}")
            print(f"  Return     : {report.get('return_pct', 0):+.1f}%")
            print(f"  Brier      : {report.get('brier_score', 0):.4f}")

    return 0


def _run_paper(sports, predictor, bankroll):
    """Run paper trading mode (real-time simulation)."""
    from modes.paper_mode import run_paper

    print(f"[PAPER] Running real-time simulation for {len(sports)} sport(s)...")
    try:
        result = run_paper(sports=sports, predictor=predictor, bankroll=bankroll)
        return result
    except KeyboardInterrupt:
        print("\n[PAPER] Stopped by user")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return 1


def _run_live(sports, predictor, bankroll):
    """Run live trading mode (real Polymarket trades)."""
    print("\n[WARNING] LIVE MODE - REAL MONEY AT RISK")
    print("[WARNING] This will execute real trades on Polymarket")

    # Confirmation
    response = input("\nType 'YES I UNDERSTAND' to proceed with live trading: ")
    if response != "YES I UNDERSTAND":
        print("[ABORT] Live trading cancelled")
        return 1

    from modes.live_mode import run_live

    print(f"\n[LIVE] Starting live trading for {len(sports)} sport(s)...")
    try:
        result = run_live(sports=sports, predictor=predictor, bankroll=bankroll)
        return result
    except KeyboardInterrupt:
        print("\n[LIVE] Stopped by user")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
