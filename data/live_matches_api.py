#!/usr/bin/env python3
"""
Live Matches API — football-data.org v4

UNA sola llamada al endpoint global /matches?status=IN_PLAY,PAUSED
retorna TODOS los partidos en vivo de todas las ligas.
Esto evita el rate limit (10 req/min) y el problema de 429.
"""

import requests
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Mapeo: código interno → código de competición en football-data.org
LEAGUE_MAPPING = {
    "pl":           "PL",    # Premier League
    "laliga":       "PD",    # La Liga
    "bundesliga":   "BL1",   # Bundesliga
    "ligue1":       "FL1",   # Ligue 1
    "seriea":       "SA",    # Serie A
    "brasil":       "BSA",   # Brasileirão
    "ucl":          "CL",    # Champions League
    "libertadores": "CLI",   # Copa Libertadores
    "mex":          None,
    "mls":          None,
    "superlig":     None,
    "nfl":          None,
}

# Mapa inverso: código API → código interno
_API_TO_INTERNAL = {v: k for k, v in LEAGUE_MAPPING.items() if v}

# Cache global: un solo dict para todas las ligas
_global_cache: Dict[str, List] = {}   # {league_code: [matches]}
_global_cache_ts: float = 0.0
_CACHE_TTL = 90  # segundos


# ─────────────────────────────────────────────────────────────────
# Función principal: UNA llamada para todos los partidos en vivo
# ─────────────────────────────────────────────────────────────────

def refresh_all_live_matches() -> Dict[str, List[Dict]]:
    """
    Llama UNA vez al endpoint global de football-data.org y retorna
    todos los partidos en vivo agrupados por código de liga interna.
    Respeta el cache de 90 segundos.
    """
    global _global_cache, _global_cache_ts

    if not FOOTBALL_DATA_API_KEY:
        return {}

    now = time.time()
    if now - _global_cache_ts < _CACHE_TTL:
        return _global_cache

    try:
        # UNA sola petición HTTP para TODOS los partidos en vivo
        url = f"{FOOTBALL_DATA_BASE_URL}/matches"
        headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
        params = {"status": "IN_PLAY,PAUSED"}

        resp = requests.get(url, headers=headers, params=params, timeout=8)

        if resp.status_code == 429:
            print("[API] Rate limit (429) — esperando 15s antes de reintentar")
            time.sleep(15)
            resp = requests.get(url, headers=headers, params=params, timeout=8)

        resp.raise_for_status()
        matches_raw = resp.json().get("matches", [])

    except requests.exceptions.RequestException as e:
        print(f"[API] Error obteniendo partidos en vivo: {e}")
        return _global_cache   # devolver cache anterior aunque esté vencido

    # Distribuir por liga interna
    result: Dict[str, List] = {}
    for match in matches_raw:
        comp_code = match.get("competition", {}).get("code", "")
        league_code = _API_TO_INTERNAL.get(comp_code)
        if not league_code:
            continue

        parsed = _parse_match(match)
        if parsed:
            result.setdefault(league_code, []).append(parsed)

    _global_cache = result
    _global_cache_ts = now
    return result


def _parse_match(match: Dict) -> Optional[Dict]:
    """Convierte un match raw de football-data.org al formato interno."""
    try:
        home = match.get("homeTeam", {}).get("name", "")
        away = match.get("awayTeam", {}).get("name", "")
        if not home or not away:
            return None

        utc_date = match.get("utcDate", "")
        status = match.get("status", "SCHEDULED")

        ft = match.get("score", {}).get("fullTime", {})
        home_score = ft.get("home")
        away_score = ft.get("away")

        minute = _estimate_minute(utc_date, status)

        if status == "PAUSED":
            display_status = "DESCANSO"
        elif status == "IN_PLAY":
            display_status = "DESCANSO" if (minute and 44 <= minute <= 46) else "EN VIVO"
        elif status == "FINISHED":
            display_status = "FINALIZADO"
        else:
            display_status = "EN VIVO"

        return {
            "home_team":       home,
            "away_team":       away,
            "home_team_short": match.get("homeTeam", {}).get("shortName", ""),
            "away_team_short": match.get("awayTeam", {}).get("shortName", ""),
            "home_score":      home_score,
            "away_score":      away_score,
            "minute":          minute,
            "status":          status,
            "display_status":  display_status,
            "match_id":        match.get("id"),
            "utc_date":        utc_date,
            "competition":     match.get("competition", {}).get("name", ""),
        }
    except Exception:
        return None


def _estimate_minute(utc_date_str: str, status: str = "IN_PLAY") -> Optional[int]:
    """Estima el minuto del partido desde la hora de inicio."""
    try:
        kick_off = datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        elapsed = (now - kick_off).total_seconds() / 60

        if elapsed < 0:
            return None

        if status == "PAUSED":
            return 45

        if elapsed <= 45:
            return int(elapsed)
        elif elapsed <= 60:
            return 45             # descanso
        elif elapsed <= 115:
            return int(elapsed - 15)
        else:
            return 90
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# API pública compatible con el código existente
# ─────────────────────────────────────────────────────────────────

def get_all_live_matches() -> Dict[str, List[Dict]]:
    """Retorna todos los partidos en vivo agrupados por liga."""
    return refresh_all_live_matches()


def get_live_matches(league_code: str) -> List[Dict]:
    """Retorna los partidos en vivo de una liga específica."""
    all_matches = refresh_all_live_matches()
    return all_matches.get(league_code, [])


def get_match_info(league_code: str, home_team: str, away_team: str) -> Optional[Dict]:
    """Busca un partido específico por nombres de equipo (exact + partial)."""
    matches = get_live_matches(league_code)
    if not matches:
        return None

    h = home_team.lower().strip()
    a = away_team.lower().strip()

    for m in matches:
        mh = m["home_team"].lower()
        ma = m["away_team"].lower()
        if (h in mh or mh in h) and (a in ma or ma in a):
            return m

    return None


def format_match_display(match_info: Optional[Dict]) -> Dict:
    """Formatea para mostrar en pantalla."""
    if not match_info:
        return {"score": "?-?", "minute": "?", "status": "DESCONOCIDO"}

    hs = match_info.get("home_score")
    as_ = match_info.get("away_score")
    score = f"{hs}-{as_}" if (hs is not None and as_ is not None) else "?-?"

    mn = match_info.get("minute")
    minute_str = "90+'" if (mn and mn >= 90) else (f"{mn}'" if mn else "?")

    return {
        "score":    score,
        "minute":   minute_str,
        "status":   match_info.get("display_status", "EN VIVO"),
        "match_id": match_info.get("match_id"),
    }


# ─────────────────────────────────────────────────────────────────
# Test directo
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not FOOTBALL_DATA_API_KEY:
        print("[ERROR] FOOTBALL_DATA_API_KEY no configurada en .env")
    else:
        print("Llamando al API (UNA sola peticion para todos los partidos)...\n")
        all_m = get_all_live_matches()

        if not all_m:
            print("No hay partidos en vivo ahora.")
        else:
            NAMES = {
                "pl":"Premier League","laliga":"La Liga","bundesliga":"Bundesliga",
                "ligue1":"Ligue 1","seriea":"Serie A","brasil":"Brasileirao",
                "ucl":"Champions League","libertadores":"Copa Libertadores",
            }
            total = 0
            for code, matches in all_m.items():
                print(f"\n[{code.upper()}] {NAMES.get(code,code)} — {len(matches)} en vivo")
                for m in matches:
                    s = f"{m['home_score']}-{m['away_score']}" if m['home_score'] is not None else "?-?"
                    mn = f"{m['minute']}'" if m['minute'] else "?"
                    print(f"  {m['home_team']} vs {m['away_team']}  |  {s}  |  {mn}  |  {m['display_status']}")
                total += len(matches)
            print(f"\nTotal: {total} partidos en vivo")
