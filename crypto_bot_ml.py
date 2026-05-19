#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   CRYPTO BOT v5.0 — POLYMARKET + ML REAL + KELLY + CALIBRACIÓN  ║
╚══════════════════════════════════════════════════════════════════╝

Cambios v4 → v5:

  ✅ ML real (sklearn LogisticRegression calibrado) en vez de heurística
     - Si no existe model.pkl, usa scoring v4 como fallback
  ✅ Kelly fraccionado para sizing en vez de "más confianza = más bet"
  ✅ Tracking de Brier score running (calidad de calibración en vivo)
  ✅ Snapshot recording integrado: graba TODOS los snapshots, no solo
     cuando entra a trade (esto alimenta train_model.py y backtester.py)
  ✅ Edge real = P_modelo - odds, no |precio - 0.5|

Requisitos:
    pip install requests python-dotenv websocket-client scikit-learn numpy

Workflow recomendado:
    1) python collector.py --duration 48      # 2 días recolectando
    2) python train_model.py                  # entrena modelo
    3) python backtester.py                   # valida histórico
    4) python crypto_bot_ml.py                # corre el bot (paper)
    5) python analyze_trades.py               # revisa métricas
    6) abre dashboard.html y carga los JSON   # gráficas
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional

import requests
import websocket
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────── Colores ───────────────────────────
# Windows 10+ soporta ANSI si se habilita VT100 via ctypes
import platform as _platform
if _platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
        G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
        B = "\033[94m"; C = "\033[96m"; W = "\033[97m"
        DIM = "\033[90m"; BOLD = "\033[1m"; RST = "\033[0m"
    except Exception:
        G = R = Y = B = C = W = DIM = BOLD = RST = ""
else:
    G, R, Y, B, C, W = "\033[92m", "\033[91m", "\033[93m", "\033[94m", "\033[96m", "\033[97m"
    DIM, BOLD, RST = "\033[90m", "\033[1m", "\033[0m"

# ─────────────────────────── Config ───────────────────────────
PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").lstrip("0x")
POLY_ADDRESS = os.getenv("POLYMARKET_ADDRESS", "")

# Sizing
BANKROLL_USDC = float(os.getenv("BANKROLL_USDC", "100.0"))
BET_MIN_USDC = float(os.getenv("BET_MIN_USDC", "1.0"))
BET_MAX_USDC = float(os.getenv("BET_MAX_USDC", "20.0"))
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.25"))  # 25% Kelly por defecto

# Edge / entrada
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.03"))  # 3 puntos porcentuales (fallback)
# MIN_EDGE diferenciado por dirección — corrige sesgo del modelo hacia UP
# Si UP tiene WR menor que DOWN, exigir más edge para UP filtra trades de baja calidad
MIN_EDGE_UP = float(os.getenv("MIN_EDGE_UP", str(MIN_EDGE)))
MIN_EDGE_DOWN = float(os.getenv("MIN_EDGE_DOWN", str(MIN_EDGE)))
TRADE_COOLDOWN = int(os.getenv("TRADE_COOLDOWN", "310"))
# Ventana 1: coincide con la ventana de entrenamiento del modelo (rem 180-240s)
ENTRY_WINDOW_MIN_SECS = int(os.getenv("ENTRY_WINDOW_MIN_SECS", "180"))
ENTRY_WINDOW_MAX_SECS = int(os.getenv("ENTRY_WINDOW_MAX_SECS", "240"))
# Ventana 2: últimos segundos — momentum de cierre (rem 10-30s)
# Kelly más chico porque el modelo no fue entrenado en este rango
ENTRY_WINDOW2_MIN_SECS = int(os.getenv("ENTRY_WINDOW2_MIN_SECS", "10"))
ENTRY_WINDOW2_MAX_SECS = int(os.getenv("ENTRY_WINDOW2_MAX_SECS", "30"))
ENTRY_WINDOW2_MIN_EDGE = float(os.getenv("ENTRY_WINDOW2_MIN_EDGE", "0.05"))
ENTRY_WINDOW2_KELLY = float(os.getenv("ENTRY_WINDOW2_KELLY", "0.12"))

# Upgrades: momentum filter + ATR volatility
MOMENTUM_THRESHOLD_V2 = float(os.getenv("MOMENTUM_THRESHOLD_V2", "0.2"))  # trend_score < 0.2 = no entra en V2
VOLATILITY_MULTIPLIER_ATR = float(os.getenv("VOLATILITY_MULTIPLIER_ATR", "1.5"))  # ATR > 1.5x median = mercado volátil

# Horas UTC bloqueadas completamente (hard block — no entra ningún trade)
_skip_raw = os.getenv("SKIP_HOURS_UTC", "")
SKIP_HOURS_UTC = set(int(h.strip()) for h in _skip_raw.split(",") if h.strip().isdigit())

# Horas UTC con filtro de precio mínimo (soft filter — solo entra si el mercado
# ya apunta la misma dirección que el modelo, evita apuestas contrarian en horas malas)
# Análisis: en estas horas los trades con market_price < 0.45 pierden consistentemente
_bad_raw = os.getenv("BAD_HOURS_UTC", "")
BAD_HOURS_UTC = set(int(h.strip()) for h in _bad_raw.split(",") if h.strip().isdigit())
MIN_PRICE_BAD_HOURS = float(os.getenv("MIN_PRICE_BAD_HOURS", "0.45"))

# Snapshot recording
SNAPSHOT_INTERVAL_SECS = int(os.getenv("SNAPSHOT_INTERVAL_SECS", "30"))
RECORD_SNAPSHOTS = os.getenv("RECORD_SNAPSHOTS", "true").lower() == "true"

# Gestion de posicion: venta anticipada (simula redeem automatico en paper)
SELL_WIN_PRICE  = 0.90   # vender si odds de la posicion llegan a 0.90
SELL_WIN_SECS   = 60     # solo si quedan menos de 60s
# STOP_LOSS DESACTIVADO — análisis histórico muestra que destruye valor en mercados binarios:
# 21 SL = -$36.90 vs estimado -$6 si se hubieran dejado resolver (WR global 55%)
# En un binario de 5min las odds intermedias son ruido — el resultado se fija al cierre.
STOP_LOSS_RATIO = 0.0    # 0.0 = nunca activa stop loss
STOP_LOSS_MIN_REM = 90   # no intentar stop-loss si quedan <90s (sin liquidez)

# APIs
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API  = "https://clob.polymarket.com"
COINBASE_WS = "wss://ws-feed.exchange.coinbase.com"
COINBASE_REST = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

# Archivos
TRADES_FILE = "trades_history.json"
SNAPSHOTS_FILE = "snapshots.jsonl"
MODEL_FILE = "model.pkl"
ML_STATE_FILE = "ml_state.json"

PERIOD_SECONDS = 300

# ─────────────────────────── Estado ───────────────────────────
state = {
    "price": 0.0,
    "candle_open": 0.0,
    "closes": deque(maxlen=200),
    "candles_5m": deque(maxlen=60),
    "high_5m": 0.0,
    "low_5m": 0.0,
    "period_start_ts": 0,
    "last_price_ts": 0.0,       # ultimo tick recibido del WS
    "in_trade": False,
    "last_trade_period": None,
    "last_trade_ts": 0,
    "wins": 0,
    "losses": 0,
    "pnl_usdc": 0.0,
    "bankroll_usdc": BANKROLL_USDC,
    # Calibración running
    "brier_sum": 0.0,
    "brier_n": 0,
    # ATR histórico para volatilidad
    "atr_values": deque(maxlen=30),  # últimas 30 mediciones de ATR
}

# Señal para forzar reinicio del WS desde el loop principal
_ws_restart = threading.Event()
state_lock = threading.Lock()


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")  # hora local del sistema


def log(msg: str, color: str = W) -> None:
    print(f"{DIM}[{ts()}]{RST} {color}{msg}{RST}")


# ─────────────────────────── LIVE order helpers ────────────────────────────

def _get_token_id(market: dict, direction: str) -> Optional[str]:
    """Extrae el token_id CLOB para el lado UP o DOWN del mercado activo."""
    try:
        token_ids_raw = market.get("clobTokenIds")
        outcomes_raw  = market.get("outcomes")
        token_ids = json.loads(token_ids_raw) if isinstance(token_ids_raw, str) else token_ids_raw
        outcomes  = json.loads(outcomes_raw)  if isinstance(outcomes_raw,  str) else outcomes_raw
        for outcome, tid in zip(outcomes, token_ids):
            if direction.lower() in outcome.lower() and tid:
                return tid
    except Exception:
        pass
    return None


def _live_build_client():
    """Crea y autentica un ClobClient V2. Solo llamar en LIVE mode.
    Polymarket desplegó CTF Exchange V2 el 28-Apr-2026:
      - Nuevo contrato: 0xE111180000d2663C0091e4f400237545B87B996B
      - EIP-712 version "2" (antes "1")
      - Requiere py_clob_client_v2 (pip install py_clob_client_v2)
    """
    from py_clob_client_v2 import ClobClient
    # Paso 1: cliente L1 (solo PK) para derivar credenciales
    client_l1 = ClobClient(
        host=CLOB_API,
        chain_id=137,
        key=PRIVATE_KEY,
        signature_type=2,
        funder=POLY_ADDRESS,
    )
    api_creds = client_l1.create_or_derive_api_key()
    # Paso 2: cliente L2 (PK + creds) listo para operar
    client = ClobClient(
        host=CLOB_API,
        chain_id=137,
        key=PRIVATE_KEY,
        creds=api_creds,
        signature_type=2,
        funder=POLY_ADDRESS,
    )
    return client


def live_buy(market: dict, direction: str, price: float,
             usdc_amount: float) -> Optional[dict]:
    """
    Coloca una orden de compra GTC real en Polymarket.
    Devuelve {"token_id", "shares", "cost_usdc"} o None si falla.
    """
    import math
    try:
        from py_clob_client_v2 import OrderArgs, OrderType, PartialCreateOrderOptions, Side
    except ImportError as e:
        log(f"[LIVE] ERROR: py_clob_client_v2 no instalado. Ejecuta: pip install py_clob_client_v2 — {e}", R)
        return None

    token_id = _get_token_id(market, direction)
    if not token_id:
        log(f"[LIVE] ERROR: sin token_id para {direction}", R)
        return None

    MIN_CLOB_SHARES = 5   # Polymarket CLOB rechaza ordenes con < 5 shares
    price_r         = round(price, 2)
    budget_shares   = math.floor(usdc_amount / price_r)
    shares          = max(budget_shares, MIN_CLOB_SHARES)
    cost_usdc       = shares * price_r

    # Si el minimo CLOB nos obliga a apostar mas de 3.5x del Kelly, mejor saltar
    # (relajado de 2.0 a 3.5 para permitir trades viables con bankroll pequeno)
    if cost_usdc > usdc_amount * 3.5:
        log(f"[LIVE] Skip: minimo CLOB requiere {shares} shares (${cost_usdc:.2f}) "
            f"pero Kelly dice ${usdc_amount:.2f} — over-bet excesivo", Y)
        return None

    if shares > budget_shares:
        log(f"[LIVE] Ajuste minimo CLOB: {budget_shares} → {shares} shares "
            f"(${budget_shares*price_r:.2f} → ${cost_usdc:.2f})", Y)

    log(f"[LIVE] BUY {direction} | {shares} shares @ {price_r:.2f} = ${cost_usdc:.2f}", C)

    try:
        client = _live_build_client()
        resp = client.create_and_post_order(
            order_args=OrderArgs(
                token_id=token_id,
                price=price_r,
                size=float(shares),
                side=Side.BUY,
            ),
            options=PartialCreateOrderOptions(tick_size="0.01"),
            order_type=OrderType.GTC,
        )
        log(f"[LIVE] Orden BUY enviada: {resp}", G)
        time.sleep(10)  # esperar fill
        return {"token_id": token_id, "shares": shares, "cost_usdc": cost_usdc}
    except Exception as e:
        log(f"[LIVE] ERROR en buy: {e}", R)
        return None


def get_polymarket_outcome(token_id: str, bet: float, shares: float,
                           direction: str, entry_open: float,
                           max_wait: int = 180) -> tuple:
    """
    Consulta data-api.polymarket.com para obtener el resultado REAL de la posicion.
    Reintenta hasta max_wait segundos esperando que Polymarket resuelva.
    Devuelve (won: bool, pnl: float, exit_type: str).
    Si no logra determinarlo, hace fallback al precio local de BTC.
    """
    log("[LIVE] Consultando resultado real en Polymarket...", C)
    deadline = time.time() + max_wait
    attempt  = 0

    while time.time() < deadline:
        attempt += 1
        try:
            r = requests.get(
                "https://data-api.polymarket.com/positions",
                params={"user": POLY_ADDRESS},
                timeout=8,
            )
            if r.status_code != 200:
                time.sleep(8)
                continue

            positions = r.json()

            # Buscar la posicion por asset (token_id exacto)
            pos = next(
                (p for p in positions if str(p.get("asset", "")) == str(token_id)),
                None,
            )

            if pos is None:
                # Puede que ya fue redeemada automaticamente o aun no aparece
                log(f"[LIVE] Posicion no encontrada (intento {attempt}), esperando...", DIM)
                time.sleep(10)
                continue

            redeemable  = pos.get("redeemable", False)
            cur_price   = float(pos.get("curPrice", -1))
            cur_val     = float(pos.get("currentValue", 0))

            # SOLO aceptar resultado cuando el mercado este REALMENTE cerrado.
            # redeemable=True es el unico indicador definitivo de Polymarket.
            # curPrice extremo (0.99) NO es definitivo — puede revertirse.
            if not redeemable:
                log(f"[LIVE] Mercado aun abierto (redeemable=False, curPrice={cur_price:.3f}), esperando...", DIM)
                time.sleep(10)
                continue

            # Mercado YA RESUELTO (redeemable=True). curPrice es 1.0 (WIN) o 0.0 (LOSS)
            # Usamos cur_price >= 0.5 como umbral conservador (en teoria es 1.0 o 0.0)
            if cur_price >= 0.5:
                won = True
                pnl = cur_val - bet          # ganancia real segun Polymarket
                log(f"[LIVE] Resultado Polymarket: WIN | curPrice={cur_price:.3f} "
                    f"| valor=${cur_val:.2f} | PnL=${pnl:+.2f}", G)
            else:
                won = False
                pnl = cur_val - bet          # cur_val sera ~0 pero usamos valor real
                log(f"[LIVE] Resultado Polymarket: LOSS | curPrice={cur_price:.3f} "
                    f"| valor=${cur_val:.2f} | PnL=${pnl:+.2f}", R)

            return won, pnl, "polymarket_resolution"

        except Exception as e:
            log(f"[LIVE] Error consultando resultado: {e}", Y)
            time.sleep(8)

    # Timeout: fallback a precio local BTC
    log("[LIVE] Timeout Polymarket. Usando precio local BTC como fallback.", Y)
    with state_lock:
        exit_price_fb = state["price"]
    won = ((direction == "UP"   and exit_price_fb >= entry_open) or
           (direction == "DOWN" and exit_price_fb <  entry_open))
    pnl = (shares * 1.0 - bet) if won else -bet
    return won, pnl, "resolution_fallback"


def get_polymarket_outcome_paper(token_id_up: str, token_id_dn: str,
                                  bet: float, shares: float,
                                  direction: str, entry_open: float,
                                  max_wait: int = 180) -> tuple:
    """
    PAPER MODE: consulta last-trade-price del CLOB para ambos tokens.
    No requiere posicion real en el wallet. Determina ganador por precio
    resuelto (~1.0 vs ~0.0). Devuelve (won, pnl, exit_type).
    """
    log("[PAPER+ORACLE] Consultando precio resuelto en CLOB...", C)
    deadline = time.time() + max_wait
    attempt  = 0

    while time.time() < deadline:
        attempt += 1
        try:
            r_up = requests.get(
                "https://clob.polymarket.com/last-trade-price",
                params={"token_id": token_id_up}, timeout=8
            )
            r_dn = requests.get(
                "https://clob.polymarket.com/last-trade-price",
                params={"token_id": token_id_dn}, timeout=8
            )
            if r_up.status_code != 200 or r_dn.status_code != 200:
                log(f"[PAPER+ORACLE] HTTP {r_up.status_code}/{r_dn.status_code}, reintentando...", DIM)
                time.sleep(8)
                continue

            price_up = float(r_up.json().get("price", 0))
            price_dn = float(r_dn.json().get("price", 0))

            # Mercado resuelto cuando un token >=0.95 y el otro <=0.05
            resolved = (
                (price_up >= 0.95 and price_dn <= 0.05) or
                (price_dn >= 0.95 and price_up <= 0.05)
            )
            if not resolved:
                log(f"[PAPER+ORACLE] Aun no resuelto (UP={price_up:.3f} "
                    f"DOWN={price_dn:.3f}, intento {attempt})...", DIM)
                time.sleep(10)
                continue

            up_won = price_up >= 0.95
            won    = (direction == "UP" and up_won) or (direction == "DOWN" and not up_won)
            pnl    = (shares * 1.0 - bet) if won else -bet
            result = "WIN" if won else "LOSS"
            log(f"[PAPER+ORACLE] {result} | UP={price_up:.3f} DOWN={price_dn:.3f} "
                f"| PnL=${pnl:+.2f}", G if won else R)
            return won, pnl, "polymarket_resolution"

        except Exception as e:
            log(f"[PAPER+ORACLE] Error: {e}", Y)
            time.sleep(8)

    # Timeout: fallback a precio local BTC
    log("[PAPER+ORACLE] Timeout. Fallback BTC local.", Y)
    with state_lock:
        exit_price_fb = state["price"]
    won = ((direction == "UP"   and exit_price_fb >= entry_open) or
           (direction == "DOWN" and exit_price_fb <  entry_open))
    pnl = (shares * 1.0 - bet) if won else -bet
    return won, pnl, "resolution_fallback"


def live_sell(token_id: str, price: float, shares: int,
              direction: str) -> bool:
    """
    Vende shares ya poseidos en el CLOB (GTC).
    Devuelve True si la orden fue enviada, False si falla.
    """
    try:
        from py_clob_client_v2 import OrderArgs, OrderType, PartialCreateOrderOptions, Side
    except ImportError as e:
        log(f"[LIVE] ERROR: py_clob_client_v2 no instalado. Ejecuta: pip install py_clob_client_v2 — {e}", R)
        return False

    price_r   = round(price, 2)
    usdc_est  = shares * price_r
    log(f"[LIVE] SELL {direction} | {shares} shares @ {price_r:.2f} ~${usdc_est:.2f}", Y)

    try:
        client = _live_build_client()
        resp = client.create_and_post_order(
            order_args=OrderArgs(
                token_id=token_id,
                price=price_r,
                size=float(shares),
                side=Side.SELL,
            ),
            options=PartialCreateOrderOptions(tick_size="0.01"),
            order_type=OrderType.GTC,
        )
        log(f"[LIVE] Orden SELL enviada: {resp}", G)
        return True
    except Exception as e:
        log(f"[LIVE] ERROR en sell: {e}", R)
        return False


# ───────────────────────────────────────────────────────────────────────────

def banner() -> None:
    mode_str  = f"{Y}PAPER MODE{RST}" if PAPER_MODE else f"{R}*** LIVE MODE ***{RST}"
    model_ok  = os.path.exists(MODEL_FILE)
    model_str = f"{G}model.pkl cargado{RST}" if model_ok else f"{Y}sin model.pkl (heuristica){RST}"
    # Intentar leer Brier/AUC del ultimo entrenamiento
    brier_str = ""
    try:
        with open("train_metrics.json") as _f:
            _m = json.load(_f)
        _s = _m.get("summary", {})
        if _s.get("mean_brier"):
            brier_str = f"  Brier {_s['mean_brier']:.3f}  AUC {_s.get('mean_auc', 0):.3f}"
    except Exception:
        pass
    skip_str = ",".join(str(h) for h in sorted(SKIP_HOURS_UTC)) if SKIP_HOURS_UTC else "ninguna"
    bad_str  = ",".join(str(h) for h in sorted(BAD_HOURS_UTC))  if BAD_HOURS_UTC  else "ninguna"
    ln = "=" * 58
    print(f"""
{C}{ln}{RST}
{BOLD}   CRYPTO BOT v5  |  {mode_str}  |  ${BANKROLL_USDC:.2f} USDC{RST}
{C}{ln}{RST}
  Modelo    : {model_str}{brier_str}
  Ventana   : V1 [{ENTRY_WINDOW_MIN_SECS}-{ENTRY_WINDOW_MAX_SECS}s]  edge UP>={MIN_EDGE_UP*100:.1f}pp DOWN>={MIN_EDGE_DOWN*100:.1f}pp  Kelly={KELLY_FRACTION}
  Bet range : ${BET_MIN_USDC:.2f} – ${BET_MAX_USDC:.2f} USDC
  Bloqueadas: UTC {skip_str}h
  Filtro px : UTC {bad_str}h  (min price >={MIN_PRICE_BAD_HOURS:.2f} en esas horas)
  Upgrades  : Momentum filter (V2: trend_score>{MOMENTUM_THRESHOLD_V2}), ATR volatility gate
{C}{ln}{RST}
""")


# ─────────────────────── Indicadores técnicos ───────────────────────

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-i] - closes[-i - 1]
        (gains if diff > 0 else losses).append(abs(diff))
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_ema(arr, period):
    if len(arr) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(arr[:period]) / period
    for v in arr[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def calc_macd(closes):
    if len(closes) < 26:
        return None
    ema12 = calc_ema(list(closes), 12)
    ema26 = calc_ema(list(closes), 26)
    if ema12 is None or ema26 is None:
        return None
    return ema12 - ema26


def calc_bb_position(closes, period=20):
    if len(closes) < period:
        return None
    window = list(closes)[-period:]
    sma = sum(window) / period
    var = sum((c - sma) ** 2 for c in window) / period
    std = var ** 0.5
    if std == 0:
        return 50.0
    upper, lower = sma + 2 * std, sma - 2 * std
    pos = (closes[-1] - lower) / (upper - lower) * 100
    return max(0, min(100, pos))


def calc_vwap_delta(candles, current_price):
    if not candles or not current_price:
        return None
    total_pv = sum(((c["h"] + c["l"] + c["c"]) / 3) * c["v"] for c in candles)
    total_v = sum(c["v"] for c in candles)
    if total_v == 0:
        return None
    vwap = total_pv / total_v
    return (current_price - vwap) / vwap * 100


def calc_atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    cs = list(candles)[-(period + 1):]
    trs = []
    for i in range(1, len(cs)):
        h, l, prev_c = cs[i]["h"], cs[i]["l"], cs[i - 1]["c"]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return sum(trs) / len(trs) if trs else None


def calc_trend_score(candles, period=5):
    if len(candles) < period:
        return None
    cs = list(candles)[-period:]
    ups = sum(1 for c in cs if c["c"] > c["o"])
    return (ups / period) * 2 - 1


def _round(v, n=2):
    return round(v, n) if isinstance(v, (int, float)) else None


# ─────────────────────── Upgrades: Volatility & Momentum ───────────────────

def get_median_atr() -> Optional[float]:
    """Devuelve la mediana de ATR histórico (últimas 30 mediciones)."""
    with state_lock:
        atr_vals = list(state["atr_values"])
    if len(atr_vals) < 5:
        return None  # necesitamos al menos 5 datos
    atr_vals_sorted = sorted(atr_vals)
    mid = len(atr_vals_sorted) // 2
    return atr_vals_sorted[mid]


def record_atr(atr_value: Optional[float]) -> None:
    """Registra un nuevo valor de ATR en el historial."""
    if atr_value is None:
        return
    with state_lock:
        state["atr_values"].append(atr_value)


def check_momentum_reversal(trend_score: Optional[float], in_window2: bool) -> bool:
    """
    Retorna True si DEBE SKIPEAR el trade (momentum reversal).
    En V2 (últimos 10-30s): si trend_score < MOMENTUM_THRESHOLD_V2, saltar
    (indica reversion de tendencia en los ultimos segundos — modelo no puede predecir esto)
    """
    if not in_window2 or trend_score is None:
        return False
    if trend_score < MOMENTUM_THRESHOLD_V2:
        return True
    return False


def get_atr_volatility_factor(atr_current: Optional[float]) -> float:
    """
    Retorna factor de ajuste para edge basado en ATR.
    > 1.0 significa mercado muy volátil (aumentar edge requerido)
    = 1.0 significa volatilidad normal (sin cambio)
    """
    if atr_current is None:
        return 1.0
    median_atr = get_median_atr()
    if median_atr is None or median_atr <= 0:
        return 1.0
    ratio = atr_current / median_atr
    if ratio > VOLATILITY_MULTIPLIER_ATR:
        return 1.2  # +20% edge requerido en mercados muy volátiles
    return 1.0


# ─────────────────────── Snapshot ───────────────────────

FEATURES_ORDER = [
    "delta_pct", "rsi", "macd", "bb_position", "vwap_delta_pct",
    "atr", "momentum", "trend_score", "remaining_secs", "odds_up",
]


def build_snapshot(market: Optional[dict], odds: Optional[dict]) -> Optional[dict]:
    with state_lock:
        price = state["price"]
        candle_open = state["candle_open"]
        closes = list(state["closes"])
        candles = list(state["candles_5m"])
        ws_period_start = state["period_start_ts"]
    if not price or not closes:
        return None

    now = int(time.time())
    period_start = (now // PERIOD_SECONDS) * PERIOD_SECONDS
    period_close = period_start + PERIOD_SECONDS
    remaining = period_close - now
    if ws_period_start != period_start:
        return None  # WS stale

    delta = (price - candle_open) / candle_open if candle_open else 0
    momentum = (closes[-1] - closes[-11]) if len(closes) > 11 else None

    return {
        "ts": now,
        "iso_ts": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "period_start_ts": period_start,
        "period_close_ts": period_close,
        "remaining_secs": remaining,
        "price": round(price, 2),
        "candle_open": round(candle_open, 2),
        "delta_pct": round(delta * 100, 6),
        "rsi": _round(calc_rsi(closes)),
        "macd": _round(calc_macd(closes), 4),
        "bb_position": _round(calc_bb_position(closes), 2),
        "vwap_delta_pct": _round(calc_vwap_delta(candles, price), 4),
        "atr": _round(calc_atr(candles), 4),
        "momentum": _round(momentum, 4),
        "trend_score": _round(calc_trend_score(candles), 3),
        "market_id": market.get("id") if market else None,
        "market_slug": market.get("slug") if market else None,
        "clobTokenIds": (json.loads(market["clobTokenIds"]) if isinstance(market.get("clobTokenIds"), str) else market.get("clobTokenIds")) if market else None,
        "outcomes": (json.loads(market["outcomes"]) if isinstance(market.get("outcomes"), str) else market.get("outcomes")) if market else None,
        "odds_up": odds["up"] if odds else None,
        "odds_down": odds["down"] if odds else None,
        "resolved": False,
        "resolved_outcome": None,
        "resolved_price": None,
    }


# ─────────────────────── Modelo (sklearn) ───────────────────────

class ModelPredictor:
    """Carga model.pkl si existe; si no, usa heurística v4."""

    def __init__(self, path: str = MODEL_FILE):
        self.path = path
        self.pkg = None
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            log(f"No existe {self.path}, usando scoring heurístico", Y)
            return
        try:
            with open(self.path, "rb") as f:
                self.pkg = pickle.load(f)
            log(f"Modelo cargado: {self.path} "
                f"(trained_at={self.pkg.get('trained_at', '?')[:19]})", G)
        except Exception as e:
            log(f"Error cargando modelo: {e}. Fallback heurístico.", R)

    def predict_p_up(self, snap: dict) -> Optional[float]:
        if self.pkg is None:
            return self._heuristic(snap)
        try:
            import numpy as np
            feats = []
            for fname in self.pkg["features"]:
                v = snap.get(fname)
                if v is None:
                    return None
                feats.append(float(v))
            X = np.array([feats])
            Xs = self.pkg["scaler"].transform(X)
            return float(self.pkg["model"].predict_proba(Xs)[0][1])
        except Exception as e:
            log(f"Predict error: {e}", R)
            return None

    @staticmethod
    def _heuristic(snap: dict) -> Optional[float]:
        delta = snap.get("delta_pct")
        if delta is None:
            return None
        score = 0
        if abs(delta) > 0.20:
            score += 7 if delta > 0 else -7
        elif abs(delta) > 0.10:
            score += 5 if delta > 0 else -5
        elif abs(delta) > 0.05:
            score += 3 if delta > 0 else -3
        else:
            return 0.5
        mom = snap.get("momentum")
        if mom is not None:
            score += 2 if mom > 0 else -2
        rsi = snap.get("rsi")
        if rsi is not None:
            if rsi < 30:
                score += 1
            elif rsi > 70:
                score -= 1
        trend = snap.get("trend_score")
        if trend is not None:
            score += int(round(trend))
        return max(0.05, min(0.95, 0.5 + (score / 12) * 0.45))


# ─────────────────────── Kelly sizing ───────────────────────

def kelly_bet(p: float, odds: float, bankroll: float, kelly_frac: float = None) -> float:
    """Devuelve el monto a apostar usando Kelly fraccionado.

    p          : prob de ganar según el modelo (0-1)
    odds       : precio del mercado (lo que cuesta una share)
    bankroll   : USDC disponible
    kelly_frac : fracción a aplicar (default: KELLY_FRACTION del .env)
    """
    if kelly_frac is None:
        kelly_frac = KELLY_FRACTION
    if odds <= 0 or odds >= 1 or p <= odds:
        return 0.0
    b = (1 / odds) - 1
    f_full = (b * p - (1 - p)) / b
    if f_full <= 0:
        return 0.0
    f = f_full * kelly_frac
    bet = bankroll * f
    bet = max(BET_MIN_USDC, min(BET_MAX_USDC, bet))
    if bet > bankroll:
        bet = bankroll
    return bet


# ─────────────────────── Coinbase WS ───────────────────────

def _on_message(_wsapp, msg):
    try:
        data = json.loads(msg)
        if data.get("type") != "ticker" or data.get("product_id") != "BTC-USD":
            return
        price = float(data.get("price", 0))
        if not price:
            return
        with state_lock:
            now = int(time.time())
            period_start = (now // PERIOD_SECONDS) * PERIOD_SECONDS
            if state["period_start_ts"] != period_start:
                state["period_start_ts"] = period_start
                state["candle_open"] = price
                state["high_5m"] = price
                state["low_5m"] = price
            else:
                state["high_5m"] = max(state["high_5m"], price)
                state["low_5m"] = min(state["low_5m"], price)
            state["price"] = price
            state["last_price_ts"] = time.time()
            state["closes"].append(price)
    except Exception:
        pass


def _on_open(wsapp):
    log("Conectado a Coinbase WS", G)
    wsapp.send(json.dumps({
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channels": ["ticker"],
    }))


def run_ws_forever():
    while True:
        _ws_restart.clear()
        # FIX: resetear last_price_ts al iniciar nueva conexion.
        # Sin esto, el watchdog ve timestamp viejo y mata la nueva
        # conexion antes de recibir el primer tick de precio.
        with state_lock:
            state["last_price_ts"] = time.time()
        try:
            ws = websocket.WebSocketApp(
                COINBASE_WS,
                on_message=_on_message,
                on_open=_on_open,
                on_error=lambda _w, e: log(f"WS err: {e}", R),
                on_close=lambda *_a: log("WS cerrado, reconectando...", Y),
            )
            # run_forever en hilo para poder matarlo si llega la señal de restart
            t = threading.Thread(target=ws.run_forever,
                                 kwargs={"ping_interval": 20, "ping_timeout": 10},
                                 daemon=True)
            t.start()
            # Esperar hasta que el hilo muera O llegue señal de restart
            while t.is_alive():
                if _ws_restart.is_set():
                    log("WS: reinicio forzado por precio estancado", Y)
                    try:
                        ws.close()
                    except Exception:
                        pass
                    # FIX: esperar max 10s a que el hilo muera.
                    # ws.close() en Windows a veces no termina run_forever.
                    deadline = time.time() + 10
                    while t.is_alive() and time.time() < deadline:
                        time.sleep(0.5)
                    if t.is_alive():
                        log("WS: hilo no termino en 10s, forzando salida de loop", Y)
                    break
                time.sleep(1)
        except Exception as e:
            log(f"WS crash: {e}", R)
        time.sleep(3)


def fetch_5min_candles():
    try:
        r = requests.get(COINBASE_REST,
                         params={"granularity": 300, "limit": 60},
                         timeout=10)
        r.raise_for_status()
        data = r.json()
        candles = []
        for c in reversed(data):
            candles.append({"o": c[3], "h": c[2], "l": c[1], "c": c[4], "v": c[5]})
        with state_lock:
            state["candles_5m"] = deque(candles, maxlen=60)
            for c in candles:
                state["closes"].append(c["c"])
        log(f"Velas 5m bootstrap: {len(candles)}", G)
    except Exception as e:
        log(f"Error bootstrap velas: {e}", R)


# ─────────────────────── Polymarket ───────────────────────

_market_log_state = {"last_found": None, "miss_count": 0, "last_slug": None}


def current_market_slug() -> str:
    now = int(time.time())
    window_start = (now // PERIOD_SECONDS) * PERIOD_SECONDS
    return f"btc-updown-5m-{window_start}"


def fetch_market_by_slug(slug: str) -> Optional[dict]:
    try:
        r = requests.get(f"{GAMMA_API}/markets",
                         params={"slug": slug}, timeout=10)
        r.raise_for_status()
        d = r.json()
        if isinstance(d, list):
            return d[0] if d else None
        if isinstance(d, dict):
            return d
        return None
    except Exception:
        return None


def fetch_current_market() -> Optional[dict]:
    slug = current_market_slug()
    market = fetch_market_by_slug(slug)
    if market:
        if _market_log_state["last_found"] is not True:
            log(f"Mercado activo: {slug}", G)
            _market_log_state["last_found"] = True
        _market_log_state["last_slug"] = slug
        return market

    # Fallback: filtrar por endDate futuro
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        r = requests.get(
            f"{GAMMA_API}/markets",
            params={"active": "true", "closed": "false", "limit": 500,
                    "order": "endDate", "ascending": "true"},
            timeout=10,
        )
        r.raise_for_status()
        markets = r.json()
        cands = [
            m for m in markets
            if ("btc" in (m.get("slug", "") or "").lower()
                or "bitcoin" in (m.get("slug", "") or "").lower())
            and ("updown" in (m.get("slug", "") or "").lower()
                 or "up-or-down" in (m.get("slug", "") or "").lower())
            and (m.get("endDate", "") > now_iso)
        ]
        five_min = [m for m in cands if "5m" in (m.get("slug", "") or "").lower()]
        if five_min:
            cands = five_min
        if not cands:
            _market_log_state["miss_count"] += 1
            if _market_log_state["last_found"] is not False:
                log(f"AVISO: Sin mercado BTC activo. Esperado: {slug}", Y)
                _market_log_state["last_found"] = False
            return None
        if _market_log_state["last_found"] is not True:
            log(f"Mercado fallback: {cands[0].get('slug')}", G)
            _market_log_state["last_found"] = True
        cands.sort(key=lambda m: m.get("endDate", ""))
        return cands[0]
    except Exception as e:
        log(f"Error market: {e}", R)
        return None


def _fetch_clob_midpoint(token_id: str) -> Optional[float]:
    try:
        r = requests.get(f"{CLOB_API}/midpoint",
                         params={"token_id": token_id}, timeout=5)
        if r.status_code != 200:
            return None
        mid = r.json().get("mid")
        return float(mid) if mid is not None else None
    except Exception:
        return None


def fetch_odds(market: dict) -> Optional[dict]:
    """Obtiene odds en tiempo real del CLOB API."""
    try:
        token_ids_raw = market.get("clobTokenIds")
        outcomes_raw = market.get("outcomes")
        if not token_ids_raw or not outcomes_raw:
            return _fetch_odds_fallback(market)
        token_ids = (json.loads(token_ids_raw)
                     if isinstance(token_ids_raw, str) else token_ids_raw)
        outcomes = (json.loads(outcomes_raw)
                    if isinstance(outcomes_raw, str) else outcomes_raw)
        odds = {}
        for o, tid in zip(outcomes, token_ids):
            if not tid:
                continue
            p = _fetch_clob_midpoint(tid)
            if p is None:
                continue
            key = ("up" if "up" in o.lower()
                   else "down" if "down" in o.lower() else o.lower())
            odds[key] = p
        if "up" in odds and "down" in odds:
            # Filtro: odds extremas = datos estancados del período anterior
            if not (0.05 <= odds["up"] <= 0.95):
                return None
            return odds
        return _fetch_odds_fallback(market)
    except Exception:
        return _fetch_odds_fallback(market)


def _fetch_odds_fallback(market: dict) -> Optional[dict]:
    try:
        prices_raw = market.get("outcomePrices")
        outcomes_raw = market.get("outcomes")
        if not prices_raw or not outcomes_raw:
            return None
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        if not prices or not outcomes:
            return None
        odds = {}
        for o, p in zip(outcomes, prices):
            if p is None or p == "":
                continue
            key = ("up" if "up" in o.lower()
                   else "down" if "down" in o.lower() else o.lower())
            try:
                odds[key] = float(p)
            except (ValueError, TypeError):
                continue
        if "up" in odds and "down" in odds:
            if not (0.05 <= odds["up"] <= 0.95):
                return None
            return odds
        return None
    except Exception:
        return None


def append_snapshot(snap: dict) -> None:
    if not RECORD_SNAPSHOTS:
        return
    with open(SNAPSHOTS_FILE, "a") as f:
        f.write(json.dumps(snap) + "\n")


def read_latest_snapshot() -> dict | None:
    """Lee el ultimo snapshot escrito por el collector (para monitorear odds durante espera)."""
    last = None
    try:
        with open(SNAPSHOTS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        last = json.loads(line)
                    except Exception:
                        pass
    except Exception:
        pass
    return last


def append_trade(trade: dict) -> None:
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE) as f:
                trades = json.load(f)
        except Exception:
            trades = []
    trades.append(trade)
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)


def update_brier(p: float, won: bool) -> float:
    """Brier score = (p - actual)^2 promedio. Menor = mejor calibrado."""
    actual = 1.0 if won else 0.0
    sq = (p - actual) ** 2
    with state_lock:
        state["brier_sum"] += sq
        state["brier_n"] += 1
        return state["brier_sum"] / state["brier_n"]


def save_ml_state(predictor: ModelPredictor, running_brier: float) -> None:
    payload = {
        "updated": ts(),
        "model_loaded": predictor.pkg is not None,
        "model_trained_at": predictor.pkg.get("trained_at") if predictor.pkg else None,
        "wins": state["wins"],
        "losses": state["losses"],
        "win_rate": (state["wins"] / max(1, state["wins"] + state["losses"])),
        "running_brier": running_brier,
        "bankroll_usdc": state["bankroll_usdc"],
        "pnl_usdc": state["pnl_usdc"],
    }
    with open(ML_STATE_FILE, "w") as f:
        json.dump(payload, f, indent=2)


# ─────────────────────── Loop principal ───────────────────────

def main():
    banner()
    predictor = ModelPredictor()

    threading.Thread(target=run_ws_forever, daemon=True).start()
    fetch_5min_candles()
    time.sleep(3)
    log("Bot iniciado", G)

    last_snap_ts = 0
    last_market_fetch = 0
    cached_market = None
    market_fail_count = 0       # fallos consecutivos al buscar mercado
    snap_none_count = 0         # snapshots nulos consecutivos
    last_conn_warn = 0          # ultima vez que logueamos aviso de conexion
    last_heartbeat = 0          # ultimo pulso de estado

    while True:
        try:
            now = time.time()

            # ── Watchdog: precio estancado ──────────────────────
            with state_lock:
                last_tick = state["last_price_ts"]
            secs_sin_tick = now - last_tick if last_tick else 999
            if last_tick and secs_sin_tick > 60:
                if now - last_conn_warn > 30:
                    log(f"AVISO: sin tick de precio hace {secs_sin_tick:.0f}s — forzando reconexion WS", Y)
                    last_conn_warn = now
                _ws_restart.set()   # señal al hilo WS para que se reinicie
            elif secs_sin_tick < 10 and last_conn_warn > 0:
                log("Conexion WS restaurada", G)
                last_conn_warn = 0

            # ── Refrescar mercado cada 60s (con retry si falla) ──
            if (now - last_market_fetch) > 60:
                market = fetch_current_market()
                if market:
                    cached_market = market
                    if market_fail_count > 0:
                        log(f"Polymarket reconectado tras {market_fail_count} intentos", G)
                    market_fail_count = 0
                else:
                    market_fail_count += 1
                    wait = min(300, 30 * market_fail_count)  # backoff: 30s, 60s, 90s... max 5min
                    if market_fail_count == 1 or market_fail_count % 5 == 0:
                        log(f"Sin mercado Polymarket (intento {market_fail_count}). Reintento en {wait}s", Y)
                    last_market_fetch = now - (60 - wait)   # adelantar el proximo intento

                last_market_fetch = now

            odds = fetch_odds(cached_market) if cached_market else None
            snap = build_snapshot(cached_market, odds)

            # Grabar snapshot periódico
            if snap and (now - last_snap_ts) >= SNAPSHOT_INTERVAL_SECS:
                append_snapshot(snap)
                last_snap_ts = now
                # Registrar ATR para análisis de volatilidad
                atr_val = snap.get("atr")
                if atr_val is not None:
                    record_atr(atr_val)

            if snap is None or odds is None:
                snap_none_count += 1
                if snap_none_count == 10:
                    log("AVISO: 10 snapshots nulos seguidos — verificar WS y mercado", Y)
                elif snap_none_count == 60:
                    log("ERROR: 60 snapshots nulos — posible corte de conexion prolongado", R)
                    fetch_5min_candles()
                # Heartbeat aunque no haya snap
                if (now - last_heartbeat) >= 30:
                    with state_lock:
                        cur_price = state["price"]
                    log(f"[sin datos] BTC=${cur_price:.2f} | buscando mercado...", DIM)
                    last_heartbeat = now
                time.sleep(2)
                continue
            else:
                if snap_none_count >= 10:
                    log(f"Snapshot OK restaurado tras {snap_none_count} nulos", G)
                snap_none_count = 0

            rem = snap["remaining_secs"]
            current_hour = datetime.fromtimestamp(now, tz=timezone.utc).hour

            # Filtro horario: evitar horas con sesgo adverso confirmado
            if SKIP_HOURS_UTC and current_hour in SKIP_HOURS_UTC:
                if (now - last_heartbeat) >= 30:
                    mins_left = 60 - datetime.fromtimestamp(now, tz=timezone.utc).minute
                    log(f"[bloqueado hora {current_hour}h UTC] BTC=${snap['price']:.2f} | "
                        f"rem={rem}s | bankroll=${state['bankroll_usdc']:.2f} | "
                        f"sale del bloqueo en ~{mins_left}min", DIM)
                    last_heartbeat = now
                time.sleep(10)
                continue

            in_window1 = ENTRY_WINDOW_MIN_SECS <= rem <= ENTRY_WINDOW_MAX_SECS
            in_window2 = ENTRY_WINDOW2_MIN_SECS <= rem <= ENTRY_WINDOW2_MAX_SECS

            # Heartbeat: muestra estado aunque no estemos en ventana de entrada
            if (now - last_heartbeat) >= 30:
                odds_up = snap.get("odds_up")
                if in_window1 or in_window2:
                    estado = "EN VENTANA"
                elif rem > ENTRY_WINDOW_MAX_SECS:
                    faltan = rem - ENTRY_WINDOW_MAX_SECS
                    estado = f"ventana V1 en {faltan}s"
                else:
                    estado = f"fuera de ventana (rem={rem}s)"
                odds_str = f"{odds_up:.3f}" if odds_up is not None else "---"
                w, l = state["wins"], state["losses"]
                wr_str = f"{100*w//max(1,w+l)}%" if (w+l) > 0 else "--"
                log(f"BTC ${snap['price']:,.0f}  rem={rem}s  odds={odds_str}  "
                    f"bank=${state['bankroll_usdc']:.2f}  {w}W/{l}L({wr_str})  {estado}", DIM)
                last_heartbeat = now

            # V2 desactivado: no tradear en ultimos 10-30s (WR 33%, perdiendo)
            # El collector sigue grabando esos snapshots para analisis futuro
            if not in_window1:
                time.sleep(2)
                continue

            # Un trade por período (aplica a ambas ventanas)
            if state["last_trade_period"] == snap["period_close_ts"]:
                time.sleep(2)
                continue
            if (now - state["last_trade_ts"]) < TRADE_COOLDOWN:
                time.sleep(2)
                continue

            # Predicción
            p_up = predictor.predict_p_up(snap)
            if p_up is None:
                time.sleep(2)
                continue

            # Segunda defensa: rechazar odds extremas en cualquier ventana
            # (pueden filtrarse en fetch_odds pero llegar aqui por cache/timing)
            if not (0.05 <= odds["up"] <= 0.95):
                time.sleep(2)
                continue

            edge_up = p_up - odds["up"]
            edge_down = (1 - p_up) - odds["down"]

            # Parámetros según la ventana activa
            if in_window1:
                # V1 usa los thresholds diferenciados por dirección
                active_min_edge_up = MIN_EDGE_UP
                active_min_edge_down = MIN_EDGE_DOWN
                active_kelly = KELLY_FRACTION
                window_label = "V1[180-240s]"
            else:
                # V2: rechazar odds extremos — mercado casi resuelto, modelo da basura
                odds_up_val = odds.get("up", 0.5)
                if not (0.05 <= odds_up_val <= 0.95):
                    log(f"V2 skip: odds extremos ({odds_up_val:.3f}) — mercado casi cerrado", DIM)
                    time.sleep(3)
                    continue
                # V2 usa el mismo threshold para ambas direcciones (más exigente)
                active_min_edge_up = ENTRY_WINDOW2_MIN_EDGE
                active_min_edge_down = ENTRY_WINDOW2_MIN_EDGE
                active_kelly = ENTRY_WINDOW2_KELLY
                window_label = "V2[10-30s]"

            # ── UPGRADE 1: Filtro de momentum (reversal en últimos segundos) ──────
            if check_momentum_reversal(snap.get("trend_score"), in_window2):
                log(f"V2 skip: trend_score={snap['trend_score']:.3f} < {MOMENTUM_THRESHOLD_V2} "
                    f"— reversión de tendencia en ultimos segundos", DIM)
                time.sleep(3)
                continue

            # ── UPGRADE 2: ATR volatility gate ─────────────────────────────────────
            atr_current = snap.get("atr")
            vol_factor = get_atr_volatility_factor(atr_current)
            if vol_factor > 1.0:
                # Mercado muy volátil: aumentar edge requerido
                active_min_edge_up *= vol_factor
                active_min_edge_down *= vol_factor
                log(f"   ATR {atr_current:.4f} > mediana (vol high) → edge +{(vol_factor-1)*100:.0f}%", DIM)

            # Decidir dirección con thresholds asimétricos (ahora ajustados por volatilidad)
            up_qualifies = edge_up >= active_min_edge_up
            down_qualifies = edge_down >= active_min_edge_down

            if up_qualifies and down_qualifies:
                # Ambos califican: ganar el de mayor edge (proporcional a su threshold)
                if edge_up - active_min_edge_up >= edge_down - active_min_edge_down:
                    direction, p, price, edge = "UP", p_up, odds["up"], edge_up
                else:
                    direction, p, price, edge = "DOWN", 1 - p_up, odds["down"], edge_down
            elif up_qualifies:
                direction, p, price, edge = "UP", p_up, odds["up"], edge_up
            elif down_qualifies:
                direction, p, price, edge = "DOWN", 1 - p_up, odds["down"], edge_down
            else:
                time.sleep(3)
                continue

            # ── Filtro de precio para horas problemáticas ──────────────────
            # En BAD_HOURS_UTC solo se entra si el mercado YA apunta la misma
            # dirección (price >= MIN_PRICE_BAD_HOURS). Apuestas contrarian
            # (precio bajo = mercado en contra) fallan consistentemente en estas horas.
            if BAD_HOURS_UTC and current_hour in BAD_HOURS_UTC:
                if price < MIN_PRICE_BAD_HOURS:
                    log(
                        f"[hora mala {current_hour}h] Skip contrarian: "
                        f"{direction} price={price:.3f} < min={MIN_PRICE_BAD_HOURS:.2f}",
                        DIM
                    )
                    time.sleep(3)
                    continue

            bet = kelly_bet(p, price, state["bankroll_usdc"], kelly_frac=active_kelly)
            if bet < BET_MIN_USDC:
                log(f"Skip: bet calculado ${bet:.2f} < min ${BET_MIN_USDC}", DIM)
                time.sleep(3)
                continue

            payout_if_win = bet / price
            expected_pnl = payout_if_win - bet

            _sep = "─" * 56
            print()
            log(_sep, C)
            dir_sym = "▲ UP  " if direction == "UP" else "▼ DOWN"
            log(f"  SEÑAL {window_label}   {dir_sym}  odds={price:.3f}  P_modelo={p:.3f}", C)
            log(f"  Edge={edge*100:+.2f}pp   Bet=${bet:.2f}   Payout=${payout_if_win:.2f}   E[PnL]=${expected_pnl:+.2f}", C)
            log(_sep, C)

            live_token_id  = None
            live_shares_int = 0
            paper_token_up = None
            paper_token_dn = None

            if PAPER_MODE:
                log("  (PAPER MODE — no se ejecuta orden real)", DIM)
                shares = bet / price  # shares virtuales
                # Extraer token_ids del snapshot para consultar oracle real sin posicion
                _token_ids = snap.get("clobTokenIds")
                _outcomes  = snap.get("outcomes")
                if _token_ids and _outcomes and len(_token_ids) == 2 and len(_outcomes) == 2:
                    if str(_outcomes[0]).lower().startswith("up"):
                        paper_token_up, paper_token_dn = _token_ids[0], _token_ids[1]
                    else:
                        paper_token_up, paper_token_dn = _token_ids[1], _token_ids[0]
                    log(f"  [PAPER+ORACLE] tokens listos ({str(paper_token_up)[:12]}...)", DIM)
                else:
                    log("  [PAPER+ORACLE] Sin tokens en snapshot, usara BTC local", Y)
            else:
                buy_result = live_buy(market, direction, price, bet)
                if buy_result is None:
                    log("[LIVE] Compra fallida — saltando este periodo", R)
                    time.sleep(5)
                    continue
                live_token_id   = buy_result["token_id"]
                live_shares_int = buy_result["shares"]
                shares          = float(live_shares_int)
                bet             = buy_result["cost_usdc"]
                log(f"[LIVE] Posicion abierta: {live_shares_int} shares "
                    f"{direction} @ {price:.3f} (costo real ${bet:.2f})", G)

            entry_open = snap["candle_open"]
            entry_price_btc = snap["price"]
            entry_period = snap["period_close_ts"]

            with state_lock:
                state["in_trade"] = True
                state["last_trade_period"] = entry_period
                state["last_trade_ts"] = now

            # ── Esperar resolución monitoreando odds ──────────────────
            wait = max(1, int(snap["remaining_secs"])) + 10
            last_odds_check = 0
            exit_early = None   # {"type": str, "pnl": float, "exit_odds": float}

            for sec in range(wait, 0, -1):
                with state_lock:
                    cur = state["price"]
                msg = f"  ⏳ cierre en {sec:>3}s  BTC ${cur:,.0f}"
                print(f"\r{DIM}[{ts()}]{RST} {C}{msg}{RST:<50}", end="", flush=True)
                time.sleep(1)

                # Revisar odds cada 20s para stop-loss
                now_inner = time.time()
                if (now_inner - last_odds_check) >= 20:
                    last_odds_check = now_inner
                    lsnap = read_latest_snapshot()
                    if lsnap:
                        pos_odds = lsnap.get("odds_up" if direction == "UP" else "odds_down")
                        rem_now  = lsnap.get("remaining_secs", sec)
                        if pos_odds is not None:
                            ratio = pos_odds / price
                            # Pre-sell: cobrar ganancia anticipada sin esperar redeem
                            if pos_odds >= SELL_WIN_PRICE and rem_now <= SELL_WIN_SECS:
                                usdc_rec = shares * pos_odds
                                exit_early = {
                                    "type": "pre_sell_win",
                                    "pnl": usdc_rec - bet,
                                    "exit_odds": pos_odds,
                                }
                                mode_lbl = "[LIVE]" if not PAPER_MODE else "(paper)"
                                if not PAPER_MODE and live_token_id and live_shares_int > 0:
                                    live_sell(live_token_id, pos_odds,
                                              live_shares_int, direction)
                                log(f"\n  PRE-SELL {mode_lbl}: odds={pos_odds:.3f} "
                                    f"rem={rem_now}s | recupera ~${usdc_rec:.2f}", G)
                                break
                            # Stop-loss: solo si queda tiempo suficiente (con liquidez)
                            if ratio <= STOP_LOSS_RATIO and rem_now > STOP_LOSS_MIN_REM:
                                usdc_rec = shares * pos_odds
                                exit_early = {
                                    "type": "stop_loss",
                                    "pnl": usdc_rec - bet,
                                    "exit_odds": pos_odds,
                                }
                                mode_lbl = "[LIVE]" if not PAPER_MODE else "(paper)"
                                if not PAPER_MODE and live_token_id and live_shares_int > 0:
                                    live_sell(live_token_id, pos_odds,
                                              live_shares_int, direction)
                                log(f"\n  STOP-LOSS {mode_lbl}: odds={pos_odds:.3f} "
                                    f"({ratio*100:.0f}% del entry) | recupera ~${usdc_rec:.2f}", Y)
                                break
            print()

            # ── Calcular resultado ────────────────────────────────────
            with state_lock:
                exit_price = state["price"]

            if exit_early:
                pnl       = exit_early["pnl"]
                won       = pnl > 0
                exit_type = exit_early["type"]
            elif live_token_id:
                # LIVE: oracle via /positions (posicion real en wallet)
                won, pnl, exit_type = get_polymarket_outcome(
                    live_token_id, bet, shares, direction, entry_open
                )
            elif paper_token_up and paper_token_dn:
                # PAPER+ORACLE: oracle via /last-trade-price (sin posicion real)
                won, pnl, exit_type = get_polymarket_outcome_paper(
                    paper_token_up, paper_token_dn, bet, shares, direction, entry_open
                )
            else:
                # Fallback: precio local BTC (solo si no hay tokens en snapshot)
                won = ((direction == "UP"   and exit_price >= entry_open) or
                       (direction == "DOWN" and exit_price <  entry_open))
                pnl       = expected_pnl if won else -bet
                exit_type = "resolution_local"

            if won:
                with state_lock:
                    state["wins"] += 1
                    state["pnl_usdc"] += pnl
                    state["bankroll_usdc"] += pnl
            else:
                with state_lock:
                    state["losses"] += 1
                    state["pnl_usdc"] += pnl
                    state["bankroll_usdc"] += pnl

            running_brier = update_brier(p, won)

            with state_lock:
                state["in_trade"] = False
                wins, losses = state["wins"], state["losses"]
                bankroll = state["bankroll_usdc"]

            wr_now = 100 * wins / max(1, wins + losses)
            if won:
                result_str = f"{G}✓ WIN {RST}"
                pnl_str    = f"{G}+${pnl:.2f}{RST}"
            else:
                result_str = f"{R}✗ LOSS{RST}"
                pnl_str    = f"{R}-${abs(pnl):.2f}{RST}"
            exit_lbl = f" [{exit_type}]" if exit_type not in ("resolution","resolution_fallback") else ""
            log(f"  {result_str}{exit_lbl}  PnL {pnl_str}  bank ${bankroll:.2f}  "
                f"{wins}W/{losses}L ({wr_now:.0f}%)  Brier {running_brier:.4f}",
                G if won else R)
            print()

            trade = {
                "time": ts(),
                "iso_ts": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                "direction": direction,
                "entry_open": entry_open,
                "entry_price_btc": entry_price_btc,
                "exit_price_btc": exit_price,
                "market_price": price,
                "p_model": round(p, 6),
                "edge": round(edge, 6),
                "bet": round(bet, 4),
                "payout_if_win": round(payout_if_win, 4),
                "pnl": round(pnl, 4),
                "bankroll_after": round(bankroll, 4),
                "won": won,
                "running_brier": round(running_brier, 6),
                "rsi": snap.get("rsi"),
                "macd": snap.get("macd"),
                "delta_pct": snap.get("delta_pct"),
                "remaining_secs": snap.get("remaining_secs"),
                "entry_window": window_label,
                "exit_type": exit_type,
                "model_used": predictor.pkg is not None,
            }
            append_trade(trade)
            save_ml_state(predictor, running_brier)

            time.sleep(3)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Error en loop: {e}", R)
            import traceback
            traceback.print_exc()
            time.sleep(5)

    # Resumen final
    print(f"\n{Y}{'=' * 70}{RST}")
    log("BOT DETENIDO", Y)
    log(f"Wins: {state['wins']} | Losses: {state['losses']} | "
        f"PnL: ${state['pnl_usdc']:+.2f} | "
        f"Bankroll: ${state['bankroll_usdc']:.2f}", W)
    if state["brier_n"] > 0:
        log(f"Brier final: {state['brier_sum']/state['brier_n']:.4f}", C)
    log(f"Trades en {TRADES_FILE}, snapshots en {SNAPSHOTS_FILE}", DIM)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        log("Detenido por el usuario", Y)
