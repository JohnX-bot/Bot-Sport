#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIVE MATCH VIEWER  -  BotSport
Partidos en vivo + Marcador + Reloj en tiempo real + Precios Polymarket

Fuentes:
  1. ESPN API (gratuita)  -- reloj real (campo clock en segundos), marcador
  2. football-data.org    -- respaldo para ligas sin ESPN
  3. Polymarket Gamma API -- precios win/draw/loss por partido

Uso:
  python live_viewer.py             # refresca datos cada 30s, reloj cada 1s
  python live_viewer.py --interval 60
"""

import os
import sys
import time
import json
import argparse
import threading
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional

# UTF-8 en Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────────────────────────
# Colores ANSI
# ─────────────────────────────────────────────────────────────────
os.system("")  # habilitar ANSI en Windows
GRN  = "\033[92m";  YLW  = "\033[93m";  RED  = "\033[91m"
CYN  = "\033[96m";  BOLD = "\033[1m";   DIM  = "\033[2m"
RST  = "\033[0m";   BLU  = "\033[94m";  MAG  = "\033[95m"
def clr(t, c): return f"{c}{t}{RST}"

# ─────────────────────────────────────────────────────────────────
# Ligas: (codigo, nombre, espn_id, fd_id)
# ─────────────────────────────────────────────────────────────────
LEAGUES = [
    ("pl",           "Premier League",    "eng.1",                "PL"),
    ("laliga",       "La Liga",           "esp.1",                "PD"),
    ("bundesliga",   "Bundesliga",        "ger.1",                "BL1"),
    ("ligue1",       "Ligue 1",           "fra.1",                "FL1"),
    ("seriea",       "Serie A",           "ita.1",                "SA"),
    ("brasil",       "Brasileirao",       "bra.1",                "BSA"),
    ("mex",          "Liga MX",           "mex.1",                None),
    ("mls",          "MLS",               "usa.1",                None),
    ("ucl",          "Champions League",  "uefa.champions",       "CL"),
    ("libertadores", "Copa Libertadores", "conmebol.libertadores","CLI"),
    ("superlig",     "Super Lig",         "tur.1",                None),
]

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
ESPN_BASE         = "https://site.api.espn.com/apis/site/v2/sports/soccer"
GAMMA_BASE        = "https://gamma-api.polymarket.com"

# Tags de Polymarket por liga interna
POLY_TAGS: Dict[str, List[str]] = {
    "pl":           ["premier-league", "english-premier-league"],
    "laliga":       ["la-liga"],
    "bundesliga":   ["bundesliga"],
    "ligue1":       ["ligue-1"],
    "seriea":       ["serie-a"],
    "brasil":       ["brazil-serie-a", "soccer-brco"],
    "mex":          ["mex"],
    "mls":          ["mls"],
    "ucl":          ["champions-league"],
    "libertadores": ["lib"],
    "superlig":     ["super-lig", "soccer-trsk"],
}

# ─────────────────────────────────────────────────────────────────
# Estado global compartido entre hilo de datos y hilo de display
# ─────────────────────────────────────────────────────────────────
_data_lock   = threading.Lock()
_match_data  : List[Dict] = []   # lista de partidos en vivo
_poly_data   : Dict[str, Dict] = {}  # mercados polymarket
_last_fetch  : float = 0.0
_poly_count  : int = 0

# ─────────────────────────────────────────────────────────────────
# ESPN: obtener partidos en vivo
# ─────────────────────────────────────────────────────────────────
def fetch_espn_live(espn_id: str) -> List[Dict]:
    try:
        r = requests.get(f"{ESPN_BASE}/{espn_id}/scoreboard", timeout=6)
        r.raise_for_status()
        matches = []
        for evt in r.json().get("events", []):
            state = evt.get("status", {}).get("type", {}).get("state", "")
            if state not in ("in", "halftime"):
                continue

            comp  = evt.get("competitions", [{}])[0]
            teams = comp.get("competitors", [])
            if len(teams) < 2:
                continue

            home = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
            away = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

            status_obj = evt.get("status", {})
            clock_secs = status_obj.get("clock", 0.0)   # segundos totales transcurridos
            period     = status_obj.get("period", 1)
            desc       = status_obj.get("type", {}).get("description", "")
            is_halftime = ("Halftime" in desc or state == "halftime")

            home_name = home.get("team", {}).get("displayName", "?")
            away_name = away.get("team", {}).get("displayName", "?")
            mkey = f"{home_name}_{away_name}"
            _update_stable_clock(mkey, float(clock_secs))

            matches.append({
                "home_team":   home_name,
                "away_team":   away_name,
                "home_score":  home.get("score", "0"),
                "away_score":  away.get("score", "0"),
                "match_key":   mkey,
                "period":      period,
                "halftime":    is_halftime,
                "source":      "ESPN",
            })
        return matches
    except Exception:
        return []

# ─────────────────────────────────────────────────────────────────
# football-data.org: respaldo (una sola llamada)
# ─────────────────────────────────────────────────────────────────
_fd_cache: Dict = {}
_fd_cache_ts: float = 0.0
_FD_TTL = 90

def fetch_fd_all_live() -> Dict[str, List[Dict]]:
    global _fd_cache, _fd_cache_ts
    if not FOOTBALL_DATA_KEY:
        return {}
    now = time.time()
    if now - _fd_cache_ts < _FD_TTL:
        return _fd_cache
    try:
        r = requests.get(
            "https://api.football-data.org/v4/matches",
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params={"status": "IN_PLAY,PAUSED"},
            timeout=8,
        )
        if r.status_code == 429:
            return _fd_cache
        r.raise_for_status()
        fd_to_code = {
            "PL":"pl","PD":"laliga","BL1":"bundesliga","FL1":"ligue1",
            "SA":"seriea","BSA":"brasil","CL":"ucl","CLI":"libertadores",
        }
        result: Dict[str, List] = {}
        for match in r.json().get("matches", []):
            comp_code = match.get("competition", {}).get("code", "")
            lc = fd_to_code.get(comp_code)
            if not lc:
                continue
            utc = match.get("utcDate", "")
            st  = match.get("status", "")
            minute = _calc_fd_minute(utc, st)
            ft = match.get("score", {}).get("fullTime", {})
            hn = match.get("homeTeam", {}).get("name", "?")
            an = match.get("awayTeam", {}).get("name", "?")
            mkey = f"{hn}_{an}"
            clk_secs = float((minute or 0) * 60)
            _update_stable_clock(mkey, clk_secs)
            result.setdefault(lc, []).append({
                "home_team":  hn,
                "away_team":  an,
                "home_score": str(ft.get("home", 0) or 0),
                "away_score": str(ft.get("away", 0) or 0),
                "match_key":  mkey,
                "period":     2 if (minute and minute > 45) else 1,
                "halftime":   (st == "PAUSED"),
                "source":     "FD",
            })
        _fd_cache = result
        _fd_cache_ts = now
        return result
    except Exception:
        return _fd_cache

def _calc_fd_minute(utc_str: str, status: str) -> Optional[int]:
    try:
        ko = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - ko).total_seconds() / 60
        if elapsed < 0:
            return None
        if status == "PAUSED":
            return 45
        if elapsed <= 45:
            return int(elapsed)
        elif elapsed <= 60:
            return 45
        elif elapsed <= 115:
            return int(elapsed - 15)
        return 90
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────
# Polymarket Gamma API
# ─────────────────────────────────────────────────────────────────
def fetch_polymarket_for_leagues() -> Dict[str, Dict]:
    """
    Descarga todos los eventos de futbol activos de Polymarket (Gamma API).
    Retorna: { "Home vs Away": {home_price, draw_price, away_price, volume} }
    """
    seen_tags = set()
    result: Dict[str, Dict] = {}

    all_tags = []
    for tags in POLY_TAGS.values():
        for tag in tags:
            if tag not in seen_tags:
                seen_tags.add(tag)
                all_tags.append(tag)

    for tag in all_tags:
        try:
            r = requests.get(
                f"{GAMMA_BASE}/events",
                params={"active": "true", "closed": "false",
                        "limit": 50, "tag_slug": tag},
                timeout=6,
            )
            if r.status_code != 200:
                continue
            events = r.json() if isinstance(r.json(), list) else []

            for evt in events:
                if evt.get("closed", True) or not evt.get("active", False):
                    continue
                title = evt.get("title", "")
                if " vs." not in title and " vs " not in title:
                    continue

                # Normalizar titulo
                norm_title = title.replace(" vs.", " vs ")
                parts = norm_title.split(" vs ")
                if len(parts) < 2:
                    continue
                poly_home = parts[0].strip()
                poly_away = parts[1].strip()

                home_price = draw_price = away_price = None
                total_vol = 0.0

                for m in evt.get("markets", []):
                    if m.get("closed", True) or not m.get("active", False):
                        continue
                    question = m.get("question", "").lower()
                    outcomes_raw  = m.get("outcomes", "[]")
                    prices_raw    = m.get("outcomePrices", "[]")

                    if isinstance(outcomes_raw, str):
                        try: outcomes_raw = json.loads(outcomes_raw)
                        except: outcomes_raw = []
                    if isinstance(prices_raw, str):
                        try: prices_raw = json.loads(prices_raw)
                        except: prices_raw = []

                    if len(prices_raw) < 2:
                        continue
                    try:
                        p0 = round(float(prices_raw[0]), 3)
                    except:
                        continue

                    vol = m.get("volume") or 0
                    try: total_vol += float(vol)
                    except: pass

                    if "end in a draw" in question or "draw?" in question:
                        draw_price = p0
                    elif "win" in question and "yes" in str(outcomes_raw).lower():
                        # Determinar si es HOME o AWAY segun el equipo nombrado
                        h_words = [w for w in poly_home.lower().split() if len(w) > 3]
                        a_words = [w for w in poly_away.lower().split() if len(w) > 3]
                        if any(w in question for w in h_words):
                            home_price = p0
                        elif any(w in question for w in a_words):
                            away_price = p0

                if home_price is not None or away_price is not None:
                    result[norm_title] = {
                        "title":      norm_title,
                        "poly_home":  poly_home,
                        "poly_away":  poly_away,
                        "home_price": home_price if home_price is not None else "-",
                        "draw_price": draw_price if draw_price is not None else "-",
                        "away_price": away_price if away_price is not None else "-",
                        "volume":     total_vol,
                    }
        except Exception:
            continue

    return result

def _sim(a: str, b: str) -> bool:
    """True si los nombres de equipo se parecen."""
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return True
    stop = {"club", "united", "city", "real", "sporting", "football", "atletico",
            "fc", "sc", "cf", "ac", "af", "se", "ca", "sv"}
    words = [w for w in a.split() if len(w) > 3 and w not in stop]
    return any(w in b for w in words)

def find_poly(home: str, away: str, poly: Dict) -> Optional[Dict]:
    for data in poly.values():
        ph, pa = data["poly_home"], data["poly_away"]
        if _sim(home, ph) and _sim(away, pa):
            return data
        if _sim(home, pa) and _sim(away, ph):
            d = dict(data)
            d["home_price"], d["away_price"] = data["away_price"], data["home_price"]
            return d
    return None

# ─────────────────────────────────────────────────────────────────
# Reloj monotónico por partido (nunca retrocede)
# ─────────────────────────────────────────────────────────────────
# { "Home_Away" : (base_secs: float, set_at_ts: float) }
_stable_clocks: Dict[str, tuple] = {}

def _update_stable_clock(key: str, new_secs: float) -> tuple:
    """
    Actualiza el reloj monotónico de un partido.
    Si la API devuelve un valor capado (menor al reloj corriendo), lo ignora.
    Devuelve (base_secs, set_at_ts) para calcular el tiempo actual.
    """
    now = time.time()
    if key not in _stable_clocks:
        _stable_clocks[key] = (new_secs, now)
        return new_secs, now

    base_secs, set_at = _stable_clocks[key]
    running = base_secs + (now - set_at)   # reloj corriendo ahora mismo

    if new_secs >= running - 5:
        # ESPN devolvió valor igual o mayor (o muy cercano): sincronizar
        _stable_clocks[key] = (new_secs, now)
        return new_secs, now
    else:
        # ESPN devolvió valor capado (ej: 5400 fijo en tiempo extra): ignorar
        # Devolver la referencia actual sin cambiarla
        return base_secs, set_at


def live_clock(match_key: str, period: int, halftime: bool) -> str:
    """
    Calcula y formatea el reloj en tiempo real usando el reloj monotónico.
    match_key = "HomeTeam_AwayTeam"
    """
    if halftime:
        return clr("  DESCANSO ", YLW + BOLD)

    if match_key not in _stable_clocks:
        return clr(" ?:?? ", DIM)

    base_secs, set_at = _stable_clocks[match_key]
    current = base_secs + (time.time() - set_at)

    mins = int(current // 60)
    secs = int(current % 60)

    if period == 1:
        if mins >= 45:
            added = mins - 45
            s = f"45+{added}:{secs:02d}"
            return clr(f" {s:>12} 1T", RED + BOLD)
        return clr(f" {mins}:{secs:02d} 1T", CYN)
    else:
        if mins >= 90:
            added = mins - 90
            s = f"90+{added}:{secs:02d}"
            return clr(f" {s:>12} 2T", RED + BOLD)
        return clr(f" {mins}:{secs:02d} 2T", GRN)

# ─────────────────────────────────────────────────────────────────
# Hilo de datos (refresca ESPN + Polymarket en background)
# ─────────────────────────────────────────────────────────────────
def data_thread(interval: int):
    global _match_data, _poly_data, _last_fetch, _poly_count
    while True:
        try:
            # Polymarket
            poly = fetch_polymarket_for_leagues()

            # football-data.org respaldo
            fd_live = fetch_fd_all_live()

            # ESPN (todas las ligas)
            all_matches = []
            for code, name, espn_id, fd_id in LEAGUES:
                matches = []
                if espn_id:
                    matches = fetch_espn_live(espn_id)
                if not matches and fd_id:
                    matches = fd_live.get(code, [])
                for m in matches:
                    m["league_name"] = name
                    m["league_code"] = code
                all_matches.extend(matches)

            with _data_lock:
                _match_data = all_matches
                _poly_data  = poly
                _poly_count = len(poly)
                _last_fetch = time.time()

        except Exception:
            pass

        time.sleep(interval)

# ─────────────────────────────────────────────────────────────────
# Render (se llama cada segundo desde el main loop)
# ─────────────────────────────────────────────────────────────────
def render():
    with _data_lock:
        matches  = list(_match_data)
        poly     = dict(_poly_data)
        pc       = _poly_count
        lf       = _last_fetch

    now_str = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")

    # Agrupar por liga
    by_league: Dict[str, List[Dict]] = {}
    for m in matches:
        key = m.get("league_name", "?")
        by_league.setdefault(key, []).append(m)

    # Construir buffer de texto
    lines = []
    lines.append(clr("=" * 78, CYN))
    lines.append(clr(f"  LIVE MATCH VIEWER  -  BotSport", BOLD + CYN) +
                 clr(f"          {now_str}", DIM))
    lines.append(clr("=" * 78, CYN))

    if not by_league:
        lines.append("")
        lines.append(clr("  No hay partidos en vivo en este momento.", YLW))
        monitored = ", ".join(l[1] for l in LEAGUES if l[2])
        lines.append(clr("  Ligas: " + monitored, DIM))
    else:
        for code, name, _, _ in LEAGUES:
            league_matches = [m for m in matches if m.get("league_code") == code]
            if not league_matches:
                continue

            lines.append("")
            lines.append(clr(f"  {name.upper()}", BOLD + YLW) +
                         clr(f"  ({len(league_matches)} en vivo)", GRN))
            lines.append(clr("  " + "-" * 74, DIM))

            for m in league_matches:
                hs  = str(m.get("home_score", "0"))
                as_ = str(m.get("away_score", "0"))
                score_str = clr(f" {hs} - {as_} ", BOLD + GRN)

                clk = live_clock(
                    m.get("match_key", f"{m['home_team']}_{m['away_team']}"),
                    m.get("period", 1),
                    m.get("halftime", False),
                )

                home_name = m["home_team"][:22]
                away_name = m["away_team"][:22]
                lines.append(f"  {clr(home_name, BOLD):<24}{score_str:<12}{away_name:<24}{clk}")

                # Polymarket
                pm = find_poly(m["home_team"], m["away_team"], poly)
                if pm:
                    hp  = pm["home_price"]
                    dp  = pm["draw_price"]
                    ap  = pm["away_price"]
                    vol = pm.get("volume", 0)
                    lines.append(clr(f"    Polymarket >> HOME: {hp}  DRAW: {dp}  AWAY: {ap}"
                                     f"  (Vol: ${vol:,.0f})", MAG))
                else:
                    lines.append(clr("    Polymarket >> sin mercado", DIM))

            lines.append(clr("  " + "-" * 74, DIM))

    elapsed = int(time.time() - lf) if lf else 0
    next_r  = max(0, 30 - elapsed)
    lines.append("")
    lines.append(clr("=" * 78, CYN))
    lines.append(clr(f"  Total: {len(matches)} en vivo  |  "
                     f"Polymarket: {pc} mercados  |  "
                     f"Datos en: {elapsed}s  |  "
                     f"Proximo fetch: {next_r}s", DIM))
    lines.append(clr("=" * 78, CYN))

    # Limpiar y pintar de una vez
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(lines), flush=True)

# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Live Match Viewer")
    parser.add_argument("--once",     action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    # Fetch inicial (en primer plano para que haya datos desde el inicio)
    print("Cargando datos...", flush=True)
    poly = fetch_polymarket_for_leagues()
    fd_live = fetch_fd_all_live()
    all_matches = []
    for code, name, espn_id, fd_id in LEAGUES:
        ms = []
        if espn_id:
            ms = fetch_espn_live(espn_id)
        if not ms and fd_id:
            ms = fd_live.get(code, [])
        for m in ms:
            m["league_name"] = name
            m["league_code"] = code
        all_matches.extend(ms)

    with _data_lock:
        _match_data[:] = all_matches
        _poly_data.update(poly)
        globals()["_poly_count"] = len(poly)
        globals()["_last_fetch"] = time.time()

    if args.once:
        render()
        return

    # Hilo de refresco de datos en background
    t = threading.Thread(target=data_thread, args=(args.interval,), daemon=True)
    t.start()

    try:
        while True:
            render()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nLive Viewer detenido.")

if __name__ == "__main__":
    main()
