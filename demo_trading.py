#!/usr/bin/env python3
"""
Quick Demo: See Trading Logic in Action

Runs bot for 2 minutes with expedited trade closure (30 seconds).
Shows ENTRY → MONITORING → WIN/LOSS cycle.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.sport_config import get_sport_config
from data.football_api import FootballAPI
from data.feature_extractor import FeatureExtractor
from models.predictor_heuristic import FootballPredictor
from models.kelly_calculator import KellyCalculator
from bot.polymarket_adapter import PolymarketSportsAdapter
from bot.position_manager import PositionManager
from bot.trading_loop import TradingLoop


def demo():
    """Run a quick 2-minute demo of the trading bot."""
    print("\n" + "="*70)
    print("DEMO: Trading Bot in Action")
    print("="*70)
    print("\nThis demo will:")
    print("  1. Load Liga Mexicana")
    print("  2. Get fixtures")
    print("  3. Predict match outcomes")
    print("  4. Find matches with edge")
    print("  5. PLACE BETS (paper mode)")
    print("  6. Close positions after 30 seconds")
    print("  7. Show P&L")
    print("\nRunning for 2 minutes...\n")

    # Configuration
    league_code = "mex"
    bankroll = 100.0
    demo_duration = 120  # 2 minutes

    # Initialize components
    sport_config = get_sport_config(league_code)
    football_api = FootballAPI(league_code=league_code)
    extractor = FeatureExtractor()
    predictor = FootballPredictor()
    kelly = KellyCalculator(kelly_fraction=0.20)
    poly_adapter = PolymarketSportsAdapter()
    pos_manager = PositionManager(max_positions=6)

    # State
    state = {
        "bankroll_usdc": bankroll,
        "pnl_usdc": 0.0,
        "wins": 0,
        "losses": 0,
        "brier_sum": 0.0,
        "brier_n": 0,
        "last_fixtures_fetch": 0,
        "last_heartbeat": 0,
    }

    # Logger
    def log(msg, color=""):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    # Trading loop
    trading_loop = TradingLoop(
        pos_manager=pos_manager,
        kelly_calc=kelly,
        poly_adapter=poly_adapter,
        football_api=football_api,
        state=state,
        config=sport_config,
        logger=log
    )

    log(f"=== Demo Start ===", )
    log(f"League: {sport_config.name}")
    log(f"Bankroll: ${bankroll:.2f}")
    log(f"Kelly Fraction: 20%")
    log("")

    # Get fixtures
    log("Fetching fixtures...")
    fixtures = football_api.fetch_upcoming_fixtures(days_ahead=7)
    log(f"Found {len(fixtures)} fixtures")
    log("")

    if not fixtures:
        log("No fixtures available. Exiting.", color="RED")
        return

    # Score fixtures
    log("Scoring fixtures...")
    min_edges = {
        "home": sport_config.min_edges.get("home", 0.04),
        "draw": sport_config.min_edges.get("draw", 0.06),
        "away": sport_config.min_edges.get("away", 0.04),
    }

    scored = []
    for fixture in fixtures:
        home = fixture.get("home_team", "")
        away = fixture.get("away_team", "")

        home_stats = football_api.fetch_team_stats(home)
        away_stats = football_api.fetch_team_stats(away)
        h2h = football_api.fetch_head_to_head(home, away)

        features = extractor.extract_match_features(home, away, home_stats, away_stats, h2h)
        p_home, p_draw, p_away = predictor.predict_match(features)

        # Dummy odds (convert probabilities to decimal odds with margin)
        # Fair odds = 1/probability, but with 3% margin
        margin = 0.03
        fair_odds = {
            "home": 1.0 / p_home,
            "draw": 1.0 / p_draw,
            "away": 1.0 / p_away,
        }

        # Apply bookmaker margin
        odds = {
            "home": fair_odds["home"] * (1 - margin),
            "draw": fair_odds["draw"] * (1 - margin),
            "away": fair_odds["away"] * (1 - margin),
        }

        edge_home = p_home - odds["home"]
        edge_draw = p_draw - odds["draw"]
        edge_away = p_away - odds["away"]
        edges = {"home": edge_home, "draw": edge_draw, "away": edge_away}
        best_edge_dir = max(edges, key=edges.get)

        scored.append({
            "fixture": fixture,
            "features": features,
            "odds": odds,
            "probabilities": {"home": p_home, "draw": p_draw, "away": p_away},
            "edges": edges,
            "best_edge": {"direction": best_edge_dir, "value": edges[best_edge_dir]},
        })

    scored.sort(key=lambda x: x["best_edge"]["value"], reverse=True)

    # Filter tradeable
    # Note: Demo uses lower thresholds to ensure trades
    demo_thresholds = {
        "home": 0.005,  # 0.5% to get any trades
        "draw": 0.005,
        "away": 0.005,
    }

    tradeable = []
    for match in scored:
        edge_info = match["best_edge"]
        direction = edge_info["direction"]
        edge = edge_info["value"]
        min_edge = demo_thresholds.get(direction, 0.005)

        if edge >= min_edge:
            tradeable.append(match)

        if len(tradeable) >= 5:
            break

    # If still no tradeable, add a synthetic one for demo purposes
    if not tradeable and scored:
        # Create a synthetic match with guaranteed edge for demo
        best_match = scored[0]
        synthetic = best_match.copy()
        synthetic["best_edge"] = {"direction": "home", "value": 0.05}  # 5% edge
        tradeable = [synthetic]
        log("  [DEMO] Added synthetic match with guaranteed edge for demo")


    log(f"Tradeable matches: {len(tradeable)}")
    for m in tradeable:
        log(f"  {m['fixture']['home_team']} vs {m['fixture']['away_team']} | "
            f"Edge: {m['best_edge']['value']:+.2%}")
    log("")

    # Demo loop
    start_time = time.time()
    demo_end_time = start_time + demo_duration
    last_heartbeat = 0
    last_entry_attempt = 0

    log("=== Demo Trading Loop ===\n")

    while time.time() < demo_end_time:
        now = time.time()

        # Entry logic every 15 seconds
        if now - last_entry_attempt > 15:
            entries = trading_loop.execute_entry_logic(tradeable)
            if entries > 0:
                log(f"[+] Placed {entries} new entries\n")
            last_entry_attempt = now

        # Monitoring logic every 5 seconds
        closures = trading_loop.execute_monitoring_logic(demo_mode_seconds=30)
        if closures > 0:
            log(f"[+] Closed {closures} positions\n")

        # Heartbeat every 20 seconds
        if now - last_heartbeat > 20:
            w, l = state["wins"], state["losses"]
            wr = 100 * w / max(1, w + l)
            open_pos = pos_manager.get_position_count()
            exposure = pos_manager.get_total_exposure()
            bankroll = state["bankroll_usdc"]

            log(f"Status: Pos {open_pos}/6 | Exp ${exposure:.2f} | "
                f"Bank ${bankroll:.2f} | {w}W/{l}L ({wr:.0f}%)")

            last_heartbeat = now

        time.sleep(2)

    # Summary
    print("\n" + "="*70)
    log("=== Demo Complete ===")
    print("="*70)

    w, l = state["wins"], state["losses"]
    wr = 100 * w / max(1, w + l)
    total_pnl = state["bankroll_usdc"] - bankroll

    print(f"\nResults:")
    print(f"  Wins/Losses: {w}W / {l}L ({wr:.0f}%)")
    print(f"  Starting Bankroll: ${bankroll:.2f}")
    print(f"  Final Bankroll: ${state['bankroll_usdc']:.2f}")
    print(f"  Total P&L: ${total_pnl:+.2f}")
    print(f"  Return: {100*total_pnl/bankroll:+.2f}%")
    print("\n[SUCCESS] Demo complete. This is what full trading bot does.")
    print("  Run: python run_all_leagues.py")
    print("       to trade all 12 leagues simultaneously.")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        print("\n\nDemo stopped by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
