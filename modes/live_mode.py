#!/usr/bin/env python3
"""
Live Trading Mode

Real Polymarket orders with real money at risk.
Requires valid credentials in .env (PRIVATE_KEY, POLYMARKET_ADDRESS).
Configuration controlled by .env file with PAPER_MODE=false.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent dirs to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sport_config import get_sport_config


def run_live(sports: list, predictor: str, bankroll: float) -> int:
    """
    Run live trading mode.

    WARNING: This places real trades on Polymarket with real money.
    Only run after extensive backtesting and paper trading validation.

    Args:
        sports: List of sport codes ["pl", "nfl", etc]
        predictor: "heuristic" or "logistic"
        bankroll: Starting bankroll in USDC

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Load .env configuration
    load_dotenv()

    # Ensure PAPER_MODE is false (live trading)
    paper_mode = os.getenv("PAPER_MODE", "true").lower() == "true"
    if paper_mode:
        print("[ERROR] Live mode requires PAPER_MODE=false in .env")
        print("[ERROR] Update .env and set PAPER_MODE=false to enable live trading")
        return 1

    # Check credentials
    private_key = os.getenv("PRIVATE_KEY", "").strip()
    polymarket_address = os.getenv("POLYMARKET_ADDRESS", "").strip()

    if not private_key or not polymarket_address:
        print("[ERROR] Live mode requires PRIVATE_KEY and POLYMARKET_ADDRESS in .env")
        print("[ERROR] Do not commit credentials to version control")
        return 1

    print(f"\n{'='*70}")
    print(f"{'*' * 70}")
    print(f"LIVE TRADING MODE - REAL MONEY AT RISK")
    print(f"{'*' * 70}")
    print(f"Sports         : {', '.join(sports)}")
    print(f"Predictor      : {predictor}")
    print(f"Bankroll       : ${bankroll:.2f}")
    print(f"Wallet Address : {polymarket_address[:6]}...{polymarket_address[-6:]}")
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

        # Set environment overrides
        os.environ["BANKROLL_USDC"] = str(bankroll)
        os.environ["PAPER_MODE"] = "false"
        if predictor == "logistic":
            os.environ["PREDICTOR_TYPE"] = "logistic"
        else:
            os.environ["PREDICTOR_TYPE"] = "heuristic"

        # For multi-sport, we'd need to enhance sports_bot_main to support it
        # For now, run single sport
        if len(sports) > 1:
            print(f"[WARN] Multi-sport live mode not yet supported")
            print(f"[WARN] Running first sport only: {sports[0]}")
            sports = [sports[0]]

        # Run the main bot
        return run_bot_main()

    except ImportError as e:
        print(f"[ERROR] Could not import bot: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n[LIVE] Stopped by user")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    """CLI interface for live trading mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Sports betting bot - Live trading mode")
    parser.add_argument("--sport", default="pl", help="Sport code (pl, nfl, laliga, ucl) or comma-separated")
    parser.add_argument("--predictor", default="heuristic", help="Predictor (heuristic, logistic)")
    parser.add_argument("--bankroll", type=float, default=100.0, help="Starting bankroll (USDC)")

    args = parser.parse_args()

    # Parse sports
    sports = [s.strip() for s in args.sport.lower().split(",")]

    # Run live trading
    return run_live(sports=sports, predictor=args.predictor, bankroll=args.bankroll)


if __name__ == "__main__":
    sys.exit(main())
