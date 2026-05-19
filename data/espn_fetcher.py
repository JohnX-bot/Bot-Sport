#!/usr/bin/env python3
"""
ESPN API Fetcher — datos de partidos sin autenticación

Fuentes:
  - Scoreboard: https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_id}/scoreboard
  - Summary:    https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_id}/summary?event={event_id}

El summary incluye:
  - rosters: formación y plantilla titular/suplente
  - odds: moneylines americanos → probabilidades implícitas
  - headToHeadGames: historial H2H
  - boxscore.form: racha reciente
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

# ──────────────────────────────────────────────────────────────────
# Mapeo de códigos internos → IDs de ESPN
# ──────────────────────────────────────────────────────────────────

ESPN_LEAGUES: Dict[str, str] = {
    "pl":           "eng.1",
    "laliga":       "esp.1",
    "bundesliga":   "ger.1",
    "ligue1":       "fra.1",
    "seriea":       "ita.1",
    "brasil":       "bra.1",
    "mex":          "mex.1",
    "mls":          "usa.1",
    "ucl":          "uefa.champions",
    "libertadores": "conmebol.libertadores",
    "superlig":     "tur.1",
}

ESPN_LEAGUE_NAMES: Dict[str, str] = {
    "pl":           "Premier League",
    "laliga":       "La Liga",
    "bundesliga":   "Bundesliga",
    "ligue1":       "Ligue 1",
    "seriea":       "Serie A",
    "brasil":       "Brasileirao",
    "mex":          "Liga MX",
    "mls":          "MLS",
    "ucl":          "Champions League",
    "libertadores": "Copa Libertadores",
    "superlig":     "Super Lig",
}

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_id}/scoreboard"
ESPN_SUMMARY_URL    = "https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_id}/summary"

# Posiciones ofensivas para cálculo de lineup_strength
_OFFENSIVE_POSITIONS = {"ST", "CF", "LW", "RW", "SS", "FW", "CAM", "AM", "OM"}
_MIDFIELD_POSITIONS   = {"CM", "CDM", "DM", "LM", "RM", "MF", "DMF", "CMF"}


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _american_odds_to_implied(money_line: float) -> float:
    """Convierte moneyline americano a probabilidad implícita (0-1)."""
    if money_line is None:
        return 0.0
    if money_line > 0:
        return 100.0 / (money_line + 100.0)
    else:
        return abs(money_line) / (abs(money_line) + 100.0)


def _calc_lineup_strength(starters: List[Dict], bench: List[Dict]) -> float:
    """
    Calcula un score de -1 a +1 que aproxima si el equipo tiene una alineación
    fuerte o débil.

    Lógica simple:
      - Cuenta atacantes/mediocampistas entre los 11 titulares
      - Si hay muchos atacantes/medios top (por stats) → score positivo
      - Si hay muchos suplentes improvisados → score negativo
      - Si no hay datos → devuelve 0.0 (neutro)
    """
    if not starters:
        return 0.0

    try:
        # Número de titulares ofensivos/medios
        offensive_starters = sum(
            1 for p in starters
            if p.get("position", "").upper() in (_OFFENSIVE_POSITIONS | _MIDFIELD_POSITIONS)
        )
        expected_offensive = 7  # ~7 atacantes+medios en un 4-3-3 o 4-2-3-1

        ratio = offensive_starters / max(len(starters), 1)
        expected_ratio = expected_offensive / 11.0

        score = (ratio - expected_ratio) / expected_ratio  # desviación normalizada
        return max(-1.0, min(1.0, score))
    except Exception:
        return 0.0


def _parse_roster_team(roster_entry: Dict) -> Dict:
    """
    Extrae datos de un entry de roster del summary de ESPN.

    roster_entry keys: formation, roster (list of player dicts)
    """
    formation = roster_entry.get("formation", "")
    players = roster_entry.get("roster", [])

    starters = []
    bench    = []

    for p in players:
        is_starter = p.get("starter", False)
        pos        = (p.get("position") or {}).get("abbreviation", "")
        name       = (p.get("athlete") or {}).get("displayName", "Unknown")
        stats_raw  = p.get("stats", [])

        # stats es una lista de strings en ESPN (ej: ["90'", "0", "0", ...])
        player_dict = {
            "name":     name,
            "position": pos,
            "starter":  is_starter,
            "stats":    stats_raw,
        }

        if is_starter:
            starters.append(player_dict)
        else:
            bench.append(player_dict)

    return {
        "formation": formation,
        "starters":  starters,
        "bench":     bench,
    }


def _safe_get(url: str, params: Optional[Dict] = None, timeout: int = 10) -> Optional[Dict]:
    """GET con manejo de errores; devuelve JSON o None."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        print(f"[ESPN] HTTP {resp.status_code} → {url}")
        return None
    except requests.exceptions.Timeout:
        print(f"[ESPN] Timeout fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ESPN] Request error ({url}): {e}")
        return None


# ──────────────────────────────────────────────────────────────────
# Funciones principales
# ──────────────────────────────────────────────────────────────────

def get_scheduled_matches(league_code: str) -> List[Dict]:
    """
    Obtiene partidos programados/en vivo para una liga.

    Args:
        league_code: código interno (pl, laliga, bundesliga, …)

    Returns:
        Lista de dicts con datos básicos del partido.
        Formato mínimo compatible con get_match_detail().
    """
    league_code = league_code.lower()
    espn_id     = ESPN_LEAGUES.get(league_code)
    league_name = ESPN_LEAGUE_NAMES.get(league_code, league_code.upper())

    if not espn_id:
        print(f"[ESPN] Liga desconocida: {league_code}")
        return []

    url  = ESPN_SCOREBOARD_URL.format(espn_id=espn_id)
    data = _safe_get(url)

    if not data:
        print(f"[ESPN] No se pudo obtener scoreboard de {league_code}")
        return []

    matches: List[Dict] = []

    for event in data.get("events", []):
        try:
            event_id    = str(event.get("id", ""))
            event_date  = event.get("date", "")
            competitions = event.get("competitions", [{}])
            comp         = competitions[0] if competitions else {}
            competitors  = comp.get("competitors", [])

            if len(competitors) < 2:
                continue

            # ESPN ordena: index 0 = home, 1 = away (generalmente)
            home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

            home_team    = (home_comp.get("team") or {}).get("displayName", "")
            away_team    = (away_comp.get("team") or {}).get("displayName", "")
            home_team_id = str((home_comp.get("team") or {}).get("id", ""))
            away_team_id = str((away_comp.get("team") or {}).get("id", ""))

            if not home_team or not away_team:
                continue

            # Parsear fecha
            try:
                dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                date_iso = dt.isoformat()
            except Exception:
                date_iso = event_date

            # Status
            status_obj  = comp.get("status") or {}
            status_type = (status_obj.get("type") or {}).get("name", "STATUS_SCHEDULED")
            status_map  = {
                "STATUS_SCHEDULED":  "SCHEDULED",
                "STATUS_IN_PROGRESS": "IN_PLAY",
                "STATUS_HALFTIME":   "IN_PLAY",
                "STATUS_FINAL":      "FINISHED",
                "STATUS_POSTPONED":  "POSTPONED",
                "STATUS_CANCELED":   "CANCELLED",
            }
            status = status_map.get(status_type, status_type)

            matches.append({
                "event_id":     event_id,
                "league_code":  league_code,
                "league_name":  league_name,
                "home_team":    home_team,
                "away_team":    away_team,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "date":         date_iso,
                "status":       status,
                # Campos de detalle vacíos — se rellenan con get_match_detail()
                "home_formation": "",
                "away_formation": "",
                "home_starters":  [],
                "away_starters":  [],
                "home_ml_odds":   0.0,
                "away_ml_odds":   0.0,
                "home_implied":   0.0,
                "away_implied":   0.0,
                "draw_implied":   0.0,
                "h2h":            [],
            })

        except Exception as e:
            print(f"[ESPN] Error parseando evento ({league_code}): {e}")
            continue

    print(f"[ESPN] {league_code}: {len(matches)} partidos encontrados")
    return matches


def get_match_detail(league_code: str, event_id: str) -> Dict:
    """
    Obtiene información detallada de un partido: formaciones, alineaciones,
    cuotas y H2H.

    Args:
        league_code: código interno (pl, laliga, …)
        event_id:    ID del evento de ESPN

    Returns:
        Dict con todos los campos enriquecidos. Si algo falla, devuelve
        el campo correspondiente vacío/neutro.
    """
    league_code = league_code.lower()
    espn_id     = ESPN_LEAGUES.get(league_code)
    league_name = ESPN_LEAGUE_NAMES.get(league_code, league_code.upper())

    if not espn_id:
        print(f"[ESPN] Liga desconocida para detail: {league_code}")
        return {}

    url  = ESPN_SUMMARY_URL.format(espn_id=espn_id)
    data = _safe_get(url, params={"event": event_id})

    if not data:
        print(f"[ESPN] No se pudo obtener summary para evento {event_id} ({league_code})")
        return {}

    # ── Datos base del evento ──────────────────────────────────────
    header       = data.get("header") or {}
    competitions = header.get("competitions", [{}])
    comp         = competitions[0] if competitions else {}
    competitors  = comp.get("competitors", [])

    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0] if competitors else {})
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else {})

    home_team    = (home_comp.get("team") or {}).get("displayName", "")
    away_team    = (away_comp.get("team") or {}).get("displayName", "")
    home_team_id = str((home_comp.get("team") or {}).get("id", ""))
    away_team_id = str((away_comp.get("team") or {}).get("id", ""))

    event_date_str = comp.get("date", "")
    try:
        dt       = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        date_iso = dt.isoformat()
    except Exception:
        date_iso = event_date_str

    status_obj  = comp.get("status") or {}
    status_type = (status_obj.get("type") or {}).get("name", "STATUS_SCHEDULED")
    status_map  = {
        "STATUS_SCHEDULED":   "SCHEDULED",
        "STATUS_IN_PROGRESS": "IN_PLAY",
        "STATUS_HALFTIME":    "IN_PLAY",
        "STATUS_FINAL":       "FINISHED",
        "STATUS_POSTPONED":   "POSTPONED",
        "STATUS_CANCELED":    "CANCELLED",
    }
    status = status_map.get(status_type, status_type)

    # ── Rosters / formaciones / titulares ─────────────────────────
    home_formation = ""
    away_formation = ""
    home_starters: List[Dict] = []
    away_starters: List[Dict] = []
    home_bench:    List[Dict] = []
    away_bench:    List[Dict] = []

    rosters = data.get("rosters", [])
    if rosters and len(rosters) >= 2:
        try:
            # ESPN: rosters[0] = home, rosters[1] = away
            home_roster_raw = rosters[0]
            away_roster_raw = rosters[1]

            home_parsed = _parse_roster_team(home_roster_raw)
            away_parsed = _parse_roster_team(away_roster_raw)

            home_formation = home_parsed["formation"]
            away_formation = away_parsed["formation"]
            home_starters  = home_parsed["starters"]
            away_starters  = away_parsed["starters"]
            home_bench     = home_parsed["bench"]
            away_bench     = away_parsed["bench"]

        except Exception as e:
            print(f"[ESPN] Error parseando rosters (event {event_id}): {e}")
    else:
        if not rosters:
            print(f"[ESPN] Sin datos de roster para evento {event_id}")

    home_lineup_strength = _calc_lineup_strength(home_starters, home_bench)
    away_lineup_strength = _calc_lineup_strength(away_starters, away_bench)

    # ── Odds ──────────────────────────────────────────────────────
    home_ml_odds  = 0.0
    away_ml_odds  = 0.0
    home_implied  = 0.0
    away_implied  = 0.0
    draw_implied  = 0.0

    odds_list = data.get("odds", [])
    if odds_list:
        try:
            odds_entry    = odds_list[0]
            home_ml_raw   = (odds_entry.get("homeTeamOdds") or {}).get("moneyLine")
            away_ml_raw   = (odds_entry.get("awayTeamOdds") or {}).get("moneyLine")

            if home_ml_raw is not None:
                home_ml_odds = float(home_ml_raw)
                home_implied = _american_odds_to_implied(home_ml_odds)

            if away_ml_raw is not None:
                away_ml_odds = float(away_ml_raw)
                away_implied = _american_odds_to_implied(away_ml_odds)

            # Probabilidad de empate = residual (puede ser negativo si hay vig)
            draw_implied = max(0.0, 1.0 - home_implied - away_implied)

        except Exception as e:
            print(f"[ESPN] Error parseando odds (event {event_id}): {e}")
    else:
        print(f"[ESPN] Sin odds para evento {event_id}")

    # ── Head-to-Head ──────────────────────────────────────────────
    h2h: List[Dict] = []
    h2h_raw = data.get("headToHeadGames", [])

    for game in (h2h_raw or []):
        try:
            game_comps   = game.get("competitions", [{}])
            game_comp    = game_comps[0] if game_comps else {}
            game_players = game_comp.get("competitors", [])

            if len(game_players) < 2:
                continue

            g_home = next((c for c in game_players if c.get("homeAway") == "home"), game_players[0])
            g_away = next((c for c in game_players if c.get("homeAway") == "away"), game_players[1])

            g_home_name  = (g_home.get("team") or {}).get("displayName", "")
            g_away_name  = (g_away.get("team") or {}).get("displayName", "")
            g_home_score = g_home.get("score", "?")
            g_away_score = g_away.get("score", "?")
            g_date       = game.get("date", "")

            h2h.append({
                "date":       g_date,
                "home_team":  g_home_name,
                "away_team":  g_away_name,
                "home_score": g_home_score,
                "away_score": g_away_score,
                "score":      f"{g_home_score}-{g_away_score}",
            })
        except Exception:
            continue

    # ── Resultado ─────────────────────────────────────────────────
    return {
        "event_id":            event_id,
        "league_code":         league_code,
        "league_name":         league_name,
        "home_team":           home_team,
        "away_team":           away_team,
        "home_team_id":        home_team_id,
        "away_team_id":        away_team_id,
        "date":                date_iso,
        "status":              status,
        "home_formation":      home_formation,
        "away_formation":      away_formation,
        "home_starters":       home_starters,
        "away_starters":       away_starters,
        "home_bench":          home_bench,
        "away_bench":          away_bench,
        "home_lineup_strength": home_lineup_strength,
        "away_lineup_strength": away_lineup_strength,
        "home_ml_odds":        home_ml_odds,
        "away_ml_odds":        away_ml_odds,
        "home_implied":        home_implied,
        "away_implied":        away_implied,
        "draw_implied":        draw_implied,
        "h2h":                 h2h,
    }


def get_all_upcoming_matches(delay_between_leagues: float = 0.3) -> List[Dict]:
    """
    Obtiene todos los partidos programados/en vivo de todas las ligas soportadas.

    Args:
        delay_between_leagues: segundos de pausa entre llamadas (evita rate limit)

    Returns:
        Lista combinada de partidos de todas las ligas, ordenada por fecha.
    """
    all_matches: List[Dict] = []

    for league_code in ESPN_LEAGUES:
        try:
            matches = get_scheduled_matches(league_code)
            all_matches.extend(matches)
            if delay_between_leagues > 0:
                time.sleep(delay_between_leagues)
        except Exception as e:
            print(f"[ESPN] Error obteniendo partidos de {league_code}: {e}")
            continue

    # Ordenar: primero los en vivo, luego por fecha
    def _sort_key(m: Dict):
        status_order = 0 if m.get("status") == "IN_PLAY" else 1
        return (status_order, m.get("date", ""))

    all_matches.sort(key=_sort_key)
    print(f"[ESPN] Total: {len(all_matches)} partidos en {len(ESPN_LEAGUES)} ligas")
    return all_matches


def enrich_match_with_detail(match: Dict, delay: float = 0.5) -> Dict:
    """
    Enriquece un partido básico (de get_scheduled_matches) con los datos
    del summary (formaciones, alineaciones, odds, H2H).

    Modifica el dict in-place y también lo devuelve.
    """
    league_code = match.get("league_code", "")
    event_id    = match.get("event_id", "")

    if not league_code or not event_id:
        print("[ESPN] enrich_match_with_detail: faltan league_code o event_id")
        return match

    if delay > 0:
        time.sleep(delay)

    detail = get_match_detail(league_code, event_id)
    if detail:
        match.update(detail)

    return match


# ──────────────────────────────────────────────────────────────────
# CLI de prueba
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    leagues_to_test = sys.argv[1:] if len(sys.argv) > 1 else ["pl", "laliga"]

    for code in leagues_to_test:
        print(f"\n{'='*60}")
        print(f"[ESPN] Probando liga: {code}")
        print("="*60)

        matches = get_scheduled_matches(code)
        if not matches:
            print(f"  Sin partidos para {code}")
            continue

        for m in matches[:3]:
            print(f"\n  {m['status']:12} | {m['home_team']} vs {m['away_team']}")
            print(f"    Fecha: {m['date']}")
            print(f"    Event ID: {m['event_id']}")

            # Probar detail en el primer partido
            if matches.index(m) == 0:
                print(f"  [ESPN] Obteniendo detail del primer partido…")
                detail = get_match_detail(code, m["event_id"])
                if detail:
                    print(f"    Formación local:   {detail.get('home_formation') or 'N/A'}")
                    print(f"    Formación visita:  {detail.get('away_formation') or 'N/A'}")
                    print(f"    Titulares locales: {len(detail.get('home_starters', []))}")
                    print(f"    Odds local:        {detail.get('home_ml_odds', 0):+.0f}  → {detail.get('home_implied', 0):.1%}")
                    print(f"    Odds visita:       {detail.get('away_ml_odds', 0):+.0f}  → {detail.get('away_implied', 0):.1%}")
                    print(f"    Prob. empate:      {detail.get('draw_implied', 0):.1%}")
                    print(f"    H2H partidos:      {len(detail.get('h2h', []))}")
