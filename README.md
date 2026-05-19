# Sports Betting Bot — Premier League on Polymarket

AI-powered sports betting bot for Premier League matches on Polymarket. Uses heuristic prediction models, Kelly criterion sizing, and multi-position management.

## Features

- **Heuristic Predictions:** Rule-based scoring using team form, goal differential, head-to-head records
- **Multi-Position Trading:** Manage up to 6 parallel match positions
- **Kelly Criterion Sizing:** Optimal bet sizes for trinomial outcomes (Home/Draw/Away)
- **Flexible Timing:** Bet whenever edge threshold is met
- **Paper Mode:** Full simulation without real funds
- **Live Mode:** Real Polymarket trading (when ready)

## Project Structure

```
BotSport/
├── data/
│   ├── football_api.py          # ESPN/TheSportsDB integration
│   ├── feature_extractor.py     # Team stats → ML features
│   └── fixtures_cache.json      # Cached PL schedule
├── models/
│   ├── predictor_heuristic.py   # Rule-based outcome predictor
│   └── kelly_calculator.py      # 3-way bet sizing
├── bot/
│   ├── sports_bot_main.py       # Main trading loop
│   ├── polymarket_adapter.py    # Polymarket API integration
│   ├── position_manager.py      # Track open positions
│   └── match_monitor.py         # Settle match results
├── logs/
│   ├── match_history.json       # Trade log
│   ├── predictions.jsonl        # Snapshots
│   └── ml_state.json            # Running stats
├── .env                         # Configuration
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install requests python-dotenv
```

### 2. Configure Environment

Edit `.env`:

```bash
PAPER_MODE=true              # false to enable live trading
BANKROLL_USDC=100.0         # Starting bankroll
BET_MIN_USDC=1.0
BET_MAX_USDC=15.0
KELLY_FRACTION=0.20         # 20% Kelly (conservative)

MIN_EDGE_HOME=0.04          # Min 4pp edge for Home
MIN_EDGE_DRAW=0.06          # Min 6pp edge for Draw (harder to predict)
MIN_EDGE_AWAY=0.04          # Min 4pp edge for Away

POSITIONS_MAX=6             # Max parallel positions
MATCHES_PER_WEEK=5          # Top N by edge
```

### 3. Test Individual Modules

```bash
# Test data fetching
python data/football_api.py

# Test feature extraction
python data/feature_extractor.py

# Test heuristic predictor
python models/predictor_heuristic.py

# Test Kelly sizing
python models/kelly_calculator.py

# Test position manager
python bot/position_manager.py

# Test Polymarket integration
python bot/polymarket_adapter.py
```

## Running the Bot

### Paper Mode (Recommended First)

```bash
python bot/sports_bot_main.py
```

Output:
- Real-time position tracking
- Heartbeat logs every 60s
- Trade history logged to `logs/match_history.json`
- Performance stats saved to `logs/ml_state.json`

### Live Mode (When Ready)

1. Get credentials from Polymarket
2. Update `.env`:
   ```bash
   PAPER_MODE=false
   PRIVATE_KEY=your_private_key
   POLYMARKET_ADDRESS=0xyour_address
   ```
3. Start bot: `python bot/sports_bot_main.py`

## Monitoring

### Real-Time Stats

Check `logs/ml_state.json` for:
- Win rate
- Total P&L
- Brier score (calibration metric)
- Bankroll

### Trade History

View all closed positions in `logs/match_history.json`:

```json
{
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "direction": "home",
  "bet_amount": 10.5,
  "odds": 0.55,
  "result": "home",
  "pnl": 2.45,
  "exit_type": "resolution"
}
```

### Snapshots

Live predictions logged to `logs/predictions.jsonl` (one per line):

```json
{"ts": 1234567890, "match": "Man United vs Liverpool", "p_home": 0.48, "odds": {"home": 0.55, "draw": 0.28, "away": 0.35}, "edge": {...}}
```

## How It Works

### 1. Data Collection

- Fetches Premier League fixtures from ESPN API
- Extracts team statistics (form, goal differential, H2H)
- Caches locally to avoid rate limits

### 2. Feature Extraction

Converts raw stats to ML features:
- Form score (last 5 matches)
- Goal differential
- Head-to-head record
- Team strength (attack/defense)

### 3. Prediction

Heuristic scoring model:
- Weights recent form heavily
- Adjusts for home/away advantage
- Factors in H2H history
- Maps score → probability (0-1)

### 4. Edge Calculation

For each outcome:
```
Edge = P_model - Market_odds

Example:
P(Home) = 0.48
Market odds for Home = 0.55
Edge = 0.48 - 0.55 = -0.07 (negative = bad bet)
```

### 5. Bet Sizing (Kelly Criterion)

```
Kelly Fraction = (p*b - q) / b

Where:
p = probability of winning
b = 1/odds - 1 (payout ratio)
q = 1 - p (probability of loss)

Apply kelly_fraction (e.g., 0.25) for conservative sizing.
```

### 6. Position Management

- Track up to 6 parallel positions
- Monitor market prices for early exit (pre-sell)
- Poll for match results
- Calculate P&L and update bankroll

### 7. Calibration

Track Brier score (prediction quality):
```
Brier = avg((p_predicted - actual)²)

Lower is better. Target: <0.25
```

## Next Steps

### Phase 1 (Now) ✅
- ✅ Data pipeline (football_api.py)
- ✅ Feature extraction
- ✅ Heuristic predictor
- ✅ Kelly sizing
- ✅ Position manager
- ✅ Match monitor
- ✅ Bot framework

### Phase 2 (Coming)
- [ ] Integrate real ESPN data parsing
- [ ] Connect to Polymarket API for live market data
- [ ] Implement match result polling
- [ ] Early exit logic (pre-sell on profit)
- [ ] Comprehensive backtesting

### Phase 3 (Validation)
- [ ] Paper trade 3-4 gameweeks
- [ ] Analyze Brier score & win rate
- [ ] Calibrate min_edge thresholds
- [ ] Test across all 3 outcomes (Home/Draw/Away)

### Phase 4 (Live)
- [ ] Add real Polymarket credentials
- [ ] Switch to PAPER_MODE=false
- [ ] Monitor live trading
- [ ] Adjust Kelly fraction as needed

## Troubleshooting

### "No fixtures found"
- ESPN API might be down or rate-limited
- Check fixtures_cache.json for stale data
- Increase FIXTURES_REFRESH_HOURS in .env

### "No Polymarket markets for PL"
- Few markets might be available on Polymarket
- Filter to markets with sufficient liquidity (>$1k volume)
- Consider other leagues as fallback

### High Brier Score (>0.30)
- Heuristic model may be underfitting
- Increase MIN_EDGE thresholds to filter low-confidence bets
- Collect more historical data to retrain

### Negative Win Rate
- Odds are efficient; market is pricing in the same information
- Reduce Kelly fraction (e.g., 0.15 instead of 0.20)
- Check for data quality issues (stale team stats)

## Performance Targets

After 50+ trades:
- **Win Rate:** 50-55% (breakeven with edge)
- **Brier Score:** 0.20-0.25 (well-calibrated)
- **Sharpe Ratio:** >0.5 (consistent returns)
- **Max Drawdown:** <20% of bankroll

## Legal Disclaimer

This bot is for educational purposes. Betting involves risk of loss. Use at your own risk. Verify Polymarket compliance in your jurisdiction before trading.

## Support

For issues or questions:
1. Check logs/ for error messages
2. Test individual modules in isolation
3. Enable verbose logging in the bot

---

**Status:** Beta v1  
**Last Updated:** May 2026
