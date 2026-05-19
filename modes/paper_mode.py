#!/usr/bin/env python3
"""
Paper Trading Mode

Real-time simulation with live Polymarket odds.
All trades are virtual (no real orders placed).
Configuration controlled by .env file with PAPER_MODE=true.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent dirs to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sport_config import get_sport_config


def run_paper(sports: list, predictor: str, bankroll: float) -> int:
    """
    Run paper trading mode.

    Args:
        sports: List of sport codes ["pl", "nfl", etc]
        predictor: "heuristic" or "logistic"
        bankroll: Starting bankroll in USDC

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Load .env configuration
    load_dotenv()

    # Ensure PAPER_MODE is true
    paper_mode = os.getenv("PAPER_MODE", "true").lower() == "true"
    if not paper_mode:
        print("[ERROR] Paper mode requires PAPER_MODE=true in .env")
        return 1

    print(f"\n{'='*70}")
    print(f"PAPER TRADING MODE")
    print(f"{'='*70}")
    print(f"Sports     : {', '.join(sports)}")
    print(f"Predictor  : {predictor}")
    print(f"Bankroll   : ${bankroll:.2f}")
    print(f"Config     : PAPER_MODE={paper_mode}")
    print(f"{'='*70}\n")

    # Validate sports
    for sport in sports:
        try:
            get_sport_config(sport)
        except ValueError as e:
            print(f"[ERROR] {e}")
            return 1

    # Import and run the main bot logic
    try:
        from bot.sports_bot_main import main as run_bot_main

        # Set environment overrides (if needed)
        os.environ["BANKROLL_USDC"] = str(bankroll)
        if predictor == "logistic":
            os.environ["PREDICTOR_TYPE"] = "logistic"
        else:
            os.environ["PREDICTOR_TYPE"] = "heuristic"

        # For multi-sport, we'd need to enhance sports_bot_main to support it
        # For now, run single sport
        if len(sports) > 1:
            print(f"[WARN] Multi-sport paper mode not yet supported")
            print(f"[WARN] Running first sport only: {sports[0]}")
            sports = [sports[0]]

        # Run the main bot with the selected sport
        sport_code = sports[0]
        print(f"[PAPER] Starting trading for {sport_code}...")
        return run_bot_main(sport_code=sport_code)

    except ImportError as e:
        print(f"[ERROR] Could not import bot: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n[PAPER] Stopped by user")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    """CLI interface for paper trading mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Sports betting bot - Paper trading mode")
    parser.add_argument("--sport", default="pl", help="Sport code (pl, nfl, laliga, ucl) or comma-separated")
    parser.add_argument("--predictor", default="heuristic", help="Predictor (heuristic, logistic)")
    parser.add_argument("--bankroll", type=float, default=100.0, help="Starting bankroll (USDC)")

    args = parser.parse_args()

    # Parse sports
    sports = [s.strip() for s in args.sport.lower().split(",")]

    # Run paper trading
    return run_paper(sports=sports, predictor=args.predictor, bankroll=args.bankroll)


if __name__ == "__main__":
    sys.exit(main())
