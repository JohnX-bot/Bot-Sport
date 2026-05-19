#!/usr/bin/env python3
"""
Sports Betting Bot for Premier League on Polymarket

Main trading loop with multi-position management.
"""

import json
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Dict, List

from dotenv import load_dotenv

# Enable ANSI colors in Windows Terminal
if sys.platform == "win32":
    os.system("color")  # Enable color support in Windows console

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.football_api import FootballAPI
from data.feature_extractor import FeatureExtractor
from models.predictor_heuristic import FootballPredictor
from models.kelly_calculator import KellyCalculator
from bot.polymarket_adapter import PolymarketSportsAdapter
from bot.position_manager import PositionManager
from bot.match_monitor import MatchMonitor

load_dotenv()

# ─────────────────────────── Colors ───────────────────────────
G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[94m"
C = "\033[96m"
W = "\033[97m"
DIM = "\033[90m"
BOLD = "\033[1m"
RST = "\033[0m"

# ─────────────────────────── Config ───────────────────────────
PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
BANKROLL_USDC = float(os.getenv("BANKROLL_USDC", "100.0"))
BET_MIN_USDC = float(os.getenv("BET_MIN_USDC", "1.0"))
BET_MAX_USDC = float(os.getenv("BET_MAX_USDC", "15.0"))
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.20"))

MIN_EDGE_HOME = float(os.getenv("MIN_EDGE_HOME", "0.04"))
MIN_EDGE_DRAW = float(os.getenv("MIN_EDGE_DRAW", "0.06"))
MIN_EDGE_AWAY = float(os.getenv("MIN_EDGE_AWAY", "0.04"))

POSITIONS_MAX = int(os.getenv("POSITIONS_MAX", "6"))
MATCHES_PER_WEEK = int(os.getenv("MATCHES_PER_WEEK", "5"))

FIXTURES_REFRESH_HOURS = int(os.getenv("FIXTURES_REFRESH_HOURS", "6"))
MARKET_WAIT_TIMEOUT = int(os.getenv("MARKET_WAIT_TIMEOUT", "3600"))

SELL_WIN_ODDS = float(os.getenv("SELL_WIN_ODDS", "0.90"))
SELL_WIN_MIN_REM_SECS = int(os.getenv("SELL_WIN_MIN_REM_SECS", "600"))

RECORD_SNAPSHOTS = os.getenv("RECORD_SNAPSHOTS", "true").lower() == "true"
SNAPSHOT_INTERVAL_SECS = int(os.getenv("SNAPSHOT_INTERVAL_SECS", "60"))

TRADES_FILE = os.getenv("TRADES_FILE", "logs/match_history.json")
SNAPSHOTS_FILE = os.getenv("SNAPSHOTS_FILE", "logs/predictions.jsonl")
ML_STATE_FILE = os.getenv("ML_STATE_FILE", "logs/ml_state.json")
POSITIONS_FILE = os.getenv("POSITIONS_FILE", "logs/positions.json")

# ─────────────────────────── State ───────────────────────────
state = {
    "bankroll_usdc": BANKROLL_USDC,
    "pnl_usdc": 0.0,
    "wins": 0,
    "losses": 0,
    "brier_sum": 0.0,
    "brier_n": 0,
    "last_fixtures_fetch": 0,
    "last_heartbeat": 0,
}

state_lock = threading.Lock()


def ts() -> str:
    """Timestamp string."""
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str, color: str = W) -> None:
    """Colored logging."""
    print(f"{DIM}[{ts()}]{RST} {color}{msg}{RST}")


def banner(sport_name: str = "Premier League"):
    """Print startup banner."""
    mode_str = f"{Y}PAPER MODE{RST}" if PAPER_MODE else f"{R}*** LIVE MODE ***{RST}"
    ln = "=" * 60
    print(f"""
{C}{ln}{RST}
{BOLD}   SPORTS BOT v1  |  {sport_name}  |  {mode_str}  |  ${BANKROLL_USDC:.2f}{RST}
{C}{ln}{RST}
  Bankroll      : ${BANKROLL_USDC:.2f} USDC
  Bet range     : ${BET_MIN_USDC:.2f} – ${BET_MAX_USDC:.2f}
  Kelly         : {KELLY_FRACTION*100:.0f}% (fractional)
  Min edges     : Home {MIN_EDGE_HOME*100:.0f}pp, Draw {MIN_EDGE_DRAW*100:.0f}pp, Away {MIN_EDGE_AWAY*100:.0f}pp
  Positions max : {POSITIONS_MAX} parallel
  Matches/week  : {MATCHES_PER_WEEK} (top by edge)
{C}{ln}{RST}
""")


def update_brier(p_home: float, p_draw: float, p_away: float, result: str) -> float:
    """Update running Brier score."""
    actual_home = 1.0 if result == "home" else 0.0
    actual_draw = 1.0 if result == "draw" else 0.0
    actual_away = 1.0 if result == "away" else 0.0

    brier = ((p_home - actual_home) ** 2 +
             (p_draw - actual_draw) ** 2 +
             (p_away - actual_away) ** 2) / 3

    with state_lock:
        state["brier_sum"] += brier
        state["brier_n"] += 1
        return state["brier_sum"] / state["brier_n"]


def save_ml_state():
    """Save stats to file."""
    with state_lock:
        w, l = state["wins"], state["losses"]
        wr = w / max(1, w + l)
        brier_avg = state["brier_sum"] / max(1, state["brier_n"])

    payload = {
        "updated": ts(),
        "wins": w,
        "losses": l,
        "win_rate": wr,
        "total_trades": w + l,
        "running_brier": brier_avg,
        "bankroll_usdc": state["bankroll_usdc"],
        "pnl_usdc": state["pnl_usdc"],
    }
    with open(ML_STATE_FILE, "w") as f:
        json.dump(payload, f, indent=2)


def save_positions_state(pos_manager, sport_code: str):
    """Save open positions to JSON file for monitoring."""
    try:
        positions_dir = os.path.dirname(POSITIONS_FILE) or "logs"
        os.makedirs(positions_dir, exist_ok=True)

        # Create positions file for this league
        positions_file = os.path.join(positions_dir, f"positions_{sport_code}.json")

        positions = []
        now = int(time.time())

        for match_id, pos in pos_manager.get_all_open_positions().items():
            match_age_seconds = now - pos.get("entry_time", now)
            positions.append({
                "match_id": match_id,
                "home_team": pos.get("home_team", ""),
                "away_team": pos.get("away_team", ""),
                "direction": pos.get("direction", ""),
                "bet_amount": pos.get("bet_amount", 0),
                "odds": pos.get("odds", 0),
                "entry_time": pos.get("entry_time", 0),
                "match_start_time": pos.get("match_start_time", 0),
                "time_elapsed_seconds": match_age_seconds,
            })

        payload = {
            "sport_code": sport_code,
            "timestamp": ts(),
            "open_positions": len(positions),
            "positions": positions,
        }

        with open(positions_file, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        pass  # Silent fail - don't crash bot if file write fails


def score_matches(
    fixtures: List[Dict],
    extractor: FeatureExtractor,
    predictor: FootballPredictor,
    poly_adapter: PolymarketSportsAdapter,
    football_api: FootballAPI = None,
) -> List[Dict]:
    """
    Score all fixtures and return ranked by edge.

    Returns:
        List of {fixture, features, odds, probabilities, edges, best_edge}
    """
    scored = []

    # Use provided API instance or create one
    if football_api is None:
        football_api = FootballAPI()

    for fixture in fixtures:
        home = fixture.get("home_team", "")
        away = fixture.get("away_team", "")

        # Get team stats (from API or cached)
        home_stats = football_api.fetch_team_stats(home)
        away_stats = football_api.fetch_team_stats(away)
        h2h = football_api.fetch_head_to_head(home, away)

        # Extract features
        features = extractor.extract_match_features(home, away, home_stats, away_stats, h2h)

        # Predict
        p_home, p_draw, p_away = predictor.predict_match(features)

        # For now, create dummy odds (in production, fetch from Polymarket)
        # TODO: integrate with Polymarket API to fetch real odds
        odds = {
            "home": 0.55 + abs(hash(home) % 100) / 1000,  # Dummy
            "draw": 0.28,
            "away": 0.35,
        }

        # Calculate edges
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
            "best_edge": {
                "direction": best_edge_dir,
                "value": edges[best_edge_dir],
            },
        })

    # Sort by best edge (descending)
    scored.sort(key=lambda x: x["best_edge"]["value"], reverse=True)
    return scored


def filter_tradeable_matches(
    scored: List[Dict],
    min_edges: Dict,
    count: int,
) -> List[Dict]:
    """Filter matches with sufficient edge."""
    tradeable = []

    for match in scored:
        edge_info = match["best_edge"]
        direction = edge_info["direction"]
        edge = edge_info["value"]

        min_edge = min_edges.get(direction, 0.03)

        if edge >= min_edge:
            tradeable.append(match)

        if len(tradeable) >= count:
            break

    return tradeable


def main(sport_code: str = "pl"):
    """
    Main trading loop.

    Args:
        sport_code: League code (pl, laliga, bundesliga, etc.)
    """
    from bot.sport_config import get_sport_config

    # Get sport configuration
    try:
        sport_config = get_sport_config(sport_code)
    except ValueError as e:
        log(f"Invalid sport: {e}", R)
        return 1

    banner_sport = f"{sport_config.name}"

    # Print banner
    banner(sport_name=banner_sport)

    # Initialize components with the correct sport code
    football_api = FootballAPI(league_code=sport_code)
    extractor = FeatureExtractor()
    predictor = FootballPredictor()
    kelly = KellyCalculator(kelly_fraction=KELLY_FRACTION)
    poly_adapter = PolymarketSportsAdapter()
    pos_manager = PositionManager(max_positions=POSITIONS_MAX)
    match_monitor = MatchMonitor()

    log("Bot initialized", G)

    min_edges = {
        "home": MIN_EDGE_HOME,
        "draw": MIN_EDGE_DRAW,
        "away": MIN_EDGE_AWAY,
    }

    # Initialize trading loop
    from bot.trading_loop import TradingLoop
    trading_loop = TradingLoop(
        pos_manager=pos_manager,
        kelly_calc=kelly,
        poly_adapter=poly_adapter,
        football_api=football_api,
        state=state,
        config=sport_config,
        logger=log
    )

    # Main loop
    last_snap_ts = 0
    match_id_counter = 0
    tradeable = []

    while True:
        try:
            now = time.time()

            # ── Refetch fixtures every N hours ──
            if (now - state["last_fixtures_fetch"]) > FIXTURES_REFRESH_HOURS * 3600:
                log(f"Refreshing fixtures...", C)
                fixtures = football_api.fetch_upcoming_fixtures(days_ahead=7)
                if not fixtures:
                    log("No fixtures found", Y)
                    time.sleep(300)
                    continue

                log(f"Found {len(fixtures)} upcoming fixtures", G)

                # Score and filter
                scored = score_matches(fixtures, extractor, predictor, poly_adapter, football_api)
                tradeable = filter_tradeable_matches(
                    scored, min_edges, count=MATCHES_PER_WEEK
                )

                log(f"Tradeable: {len(tradeable)} matches with edge", G)

                state["last_fixtures_fetch"] = now

            # ── Entry Logic: Place new bets ──
            if tradeable:
                entries = trading_loop.execute_entry_logic(tradeable)
                if entries > 0:
                    log(f"Placed {entries} new entries", G)

            # ── Monitoring Logic: Close positions ──
            # In paper mode: close after 30 seconds (for demo)
            # In live mode: would wait for actual match result
            demo_close_seconds = 30 if PAPER_MODE else 3600
            closures = trading_loop.execute_monitoring_logic(demo_mode_seconds=demo_close_seconds)
            if closures > 0:
                log(f"Closed {closures} positions", G)

            # ── Heartbeat ──
            if (now - state["last_heartbeat"]) >= 60:
                with state_lock:
                    open_pos = pos_manager.get_position_count()
                    exposure = pos_manager.get_total_exposure()
                    w, l = state["wins"], state["losses"]
                    wr = 100 * w / max(1, w + l)
                    bankroll = state["bankroll_usdc"]

                log(f"Positions: {open_pos}/{POSITIONS_MAX} | "
                    f"Exposure: ${exposure:.2f} | "
                    f"Bank: ${bankroll:.2f} | "
                    f"{w}W/{l}L ({wr:.0f}%)", DIM)

                state["last_heartbeat"] = now
                save_ml_state()
                save_positions_state(pos_manager, sport_code)

            # ── Sleep and check again ──
            # In real-time mode: lower sleep = faster entry
            # In simulation: can be higher
            time.sleep(5)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error: {e}", R)
            import traceback
            traceback.print_exc()
            time.sleep(5)

    # Final summary
    print(f"\n{Y}{'=' * 60}{RST}")
    log("BOT STOPPED", Y)

    final_stats = pos_manager.calculate_stats()
    log(f"Final: {final_stats['wins']}W/{final_stats['losses']}L | "
        f"PnL ${final_stats['total_pnl']:+.2f} | "
        f"Bank ${state['bankroll_usdc']:.2f}", W)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        log("Stopped by user", Y)
