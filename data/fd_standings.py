#!/usr/bin/env python3
"""
Football-Data.org v4 — Standings & Team Strengths

Calcula ataque/defensa para el modelo de Poisson:
  - attack_strength  = (goles/partido del equipo) / (media de la liga)
  - defense_strength = (goles concedidos/partido) / (media concedida de la liga)
  - form_score       = puntuación ponderada -1..+1 basada en racha reciente

API key: variable de entorno FOOTBALL_DATA_API_KEY (cargada con dotenv)
Cache por liga: TTL de 3600 s (standings no cambian durante un partido)
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────

FOOTBALL_DATA_API_KEY: str = os.getenv("FOOTBALL_DATA_API_KEY", "")
FD_BASE_URL: str = "https://api.football-data.org/v4"

# Códigos de competición en football-data.org
FD_COMPETITIONS: Dict[str, str] = {
    "pl":           "PL",    # Premier League
    "laliga":       "PD",    # La Liga
    "bundesliga":   "BL1",   # Bundesliga
    "ligue1":       "FL1",   # Ligue 1
    "seriea":       "SA",    # Serie A
    "brasil":       "BSA",   # Brasileirao
    "ucl":          "CL",    # Champions League
    "libertadores": "CLI",   # Copa Libertadores
}

# Pesos para el form_score (más reciente = más peso)
# Formato: [último, penúltimo, antepenúltimo, ...]
_FORM_WEIGHTS: List[float] = [0.35, 0.20, 0.15, 0.15, 0.15]

# TTL de la caché en segundos
_CACHE_TTL: int = 3600

# ──────────────────────────────────────────────────────────────────
# Caché en memoria por liga
# ──────────────────────────────────────────────────────────────────

# Estructura: { league_code: { "standings": {...}, "strengths": {...}, "ts": float } }
_cache: Dict[str, Dict] = {}


def _cache_get(league_code: str, key: str):
    """Devuelve el valor del caché si está fresco, None si expiró."""
    entry = _cache.get(league_code, {})
    ts    = entry.get("ts", 0)
    if time.time() - ts < _CACHE_TTL and key in entry:
        return entry[key]
    return None


def _cache_set(league_code: str, key: str, value):
    """Guarda un valor en el caché; actualiza el timestamp."""
    if league_code not in _cache:
        _cache[league_code] = {}
    _cache[league_code][key] = value
    _cache[league_code]["ts"] = time.time()


# ──────────────────────────────────────────────────────────────────
# HTTP helper
# ──────────────────────────────────────────────────────────────────

def _fd_get(endpoint: str, params: Optional[Dict] = None, timeout: int = 10) -> Optional[Dict]:
    """
    GET autenticado a football-data.org v4.

    Maneja:
      - 401: clave inválida
      - 429: rate limit → devuelve None (el llamador usa caché)
      - otros errores de red
    """
    if not FOOTBALL_DATA_API_KEY:
        print("[FD] FOOTBALL_DATA_API_KEY no configurada en .env")
        return None

    url     = f"{FD_BASE_URL}/{endpoint.lstrip('/')}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print(f"[FD] Rate limit (429) en {endpoint} — usando caché si disponible")
            return None
        elif resp.status_code == 401:
            print(f"[FD] Clave de API inválida (401). Verifica FOOTBALL_DATA_API_KEY")
            return None
        elif resp.status_code == 403:
            print(f"[FD] Acceso denegado (403) a {endpoint} — plan insuficiente")
            return None
        elif resp.status_code == 404:
            print(f"[FD] Recurso no encontrado (404): {endpoint}")
            return None
        else:
            print(f"[FD] HTTP {resp.status_code} en {endpoint}")
            return None

    except requests.exceptions.Timeout:
        print(f"[FD] Timeout en {endpoint}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[FD] Error de red ({endpoint}): {e}")
        return None


# ──────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────

def _parse_form_string(form_str: str) -> float:
    """
    Convierte una cadena de forma (e.g. "WWDLW") en un score de -1 a +1.

    Los resultados más recientes están al FINAL de la cadena en FD.
    Pesos: último = 0.35, resto distribuidos.

    W = +1, D = 0, L = -1
    """
    if not form_str:
        return 0.0

    # FD devuelve los resultados del más antiguo al más reciente
    results = list(form_str.upper())[-len(_FORM_WEIGHTS):]  # máx 5 últimos
    results.reverse()  # ahora [más reciente, ..., más antiguo]

    score     = 0.0
    total_wt  = 0.0
    value_map = {"W": 1.0, "D": 0.0, "L": -1.0}

    for i, char in enumerate(results):
        if i >= len(_FORM_WEIGHTS):
            break
        w      = _FORM_WEIGHTS[i]
        val    = value_map.get(char, 0.0)
        score  += val * w
        total_wt += w

    return score / total_wt if total_wt > 0 else 0.0


def _team_name_match(name_to_find: str, candidates: List[str]) -> Optional[str]:
    """
    Búsqueda flexible de nombre de equipo (insensible a mayúsculas, partial match).

    Orden de prioridad:
      1. Coincidencia exacta
      2. La cadena buscada contiene al candidato
      3. El candidato contiene la cadena buscada
    """
    search = name_to_find.lower().strip()

    for candidate in candidates:
        if candidate.lower().strip() == search:
            return candidate

    for candidate in candidates:
        c_lower = candidate.lower().strip()
        if c_lower in search or search in c_lower:
            return candidate

    return None


# ──────────────────────────────────────────────────────────────────
# Funciones públicas
# ──────────────────────────────────────────────────────────────────

def get_league_standings(league_code: str) -> Dict[str, Dict]:
    """
    Obtiene la clasificación completa de una liga.

    Args:
        league_code: código interno (pl, laliga, bundesliga, …)

    Returns:
        Dict mapeando nombre de equipo → stats dict:
          {
            "team_id":      int,
            "won":          int,
            "draw":         int,
            "lost":         int,
            "goalsFor":     int,
            "goalsAgainst": int,
            "played":       int,
            "points":       int,
            "form":         str,   # e.g. "WWDLW"
          }
        Devuelve {} si la liga no está soportada o la API falla.
    """
    league_code = league_code.lower()

    # Caché
    cached = _cache_get(league_code, "standings")
    if cached is not None:
        print(f"[FD] {league_code}: standings desde caché")
        return cached

    comp_id = FD_COMPETITIONS.get(league_code)
    if not comp_id:
        print(f"[FD] Liga no soportada por football-data.org: {league_code}")
        return {}

    data = _fd_get(f"/competitions/{comp_id}/standings")
    if not data:
        # Intento de recuperación: devolver caché aunque esté caducado
        stale = (_cache.get(league_code) or {}).get("standings")
        if stale:
            print(f"[FD] {league_code}: usando standings caducados (API no disponible)")
            return stale
        return {}

    standings_data: Dict[str, Dict] = {}

    for standing_group in data.get("standings", []):
        # Tomar solo el grupo TOTAL (no HOME/AWAY por separado)
        standing_type = standing_group.get("type", "")
        if standing_type not in ("TOTAL", ""):
            continue

        for entry in standing_group.get("table", []):
            try:
                team     = entry.get("team", {})
                team_name = team.get("name", "")
                team_id   = team.get("id", 0)

                if not team_name:
                    continue

                standings_data[team_name] = {
                    "team_id":      team_id,
                    "won":          entry.get("won", 0),
                    "draw":         entry.get("draw", 0),
                    "lost":         entry.get("lost", 0),
                    "goalsFor":     entry.get("goalsFor", 0),
                    "goalsAgainst": entry.get("goalsAgainst", 0),
                    "played":       entry.get("playedGames", 0),
                    "points":       entry.get("points", 0),
                    "form":         entry.get("form", ""),
                }
            except Exception as e:
                print(f"[FD] Error parseando entrada de standings ({league_code}): {e}")
                continue

        if standings_data:
            break  # Con el grupo TOTAL es suficiente

    if not standings_data:
        print(f"[FD] No se encontraron datos de clasificación para {league_code}")

    _cache_set(league_code, "standings", standings_data)
    print(f"[FD] {league_code}: {len(standings_data)} equipos en standings")
    return standings_data


def calculate_team_strengths(league_code: str) -> Dict[str, Dict]:
    """
    Calcula fortalezas de ataque y defensa relativas para todos los equipos
    de una liga, usando el modelo de Poisson.

    Fórmulas:
      attack_strength  = (goles_por_partido_equipo) / (media_goles_liga)
      defense_strength = (goles_concedidos_por_partido) / (media_concedidos_liga)
      form_score       = −1..+1 ponderado (W=+1, D=0, L=−1)

    Args:
        league_code: código interno

    Returns:
        Dict mapeando nombre de equipo → strength dict:
          {
            "attack_strength":  float,  # 1.0 = media de liga
            "defense_strength": float,  # 1.0 = media de liga
            "form_score":       float,  # −1..+1
            "played":           int,
            "goals_per_game":   float,
            "conceded_per_game": float,
          }
    """
    league_code = league_code.lower()

    # Caché
    cached = _cache_get(league_code, "strengths")
    if cached is not None:
        print(f"[FD] {league_code}: strengths desde caché")
        return cached

    standings = get_league_standings(league_code)
    if not standings:
        return {}

    # ── Medias de liga ─────────────────────────────────────────────
    total_goals_for     = 0
    total_goals_against = 0
    total_played        = 0

    for team_stats in standings.values():
        played = team_stats.get("played", 0)
        if played > 0:
            total_goals_for     += team_stats.get("goalsFor", 0)
            total_goals_against += team_stats.get("goalsAgainst", 0)
            total_played        += played

    if total_played == 0:
        print(f"[FD] {league_code}: no hay partidos jugados para calcular medias")
        return {}

    n_teams = len(standings)
    # Dividimos por n_teams porque el total contabiliza cada partido dos veces
    # (una por cada equipo). Liga media = total_goles / n_partidos_totales
    # total_goles_jugados = total_goals_for / n_teams (suma de goles marcados por todos)
    # n_partidos = total_played / n_teams
    games_per_team        = total_played / n_teams
    league_avg_scored     = (total_goals_for / n_teams) / games_per_team  if games_per_team > 0 else 1.0
    league_avg_conceded   = (total_goals_against / n_teams) / games_per_team if games_per_team > 0 else 1.0

    # Evitar división por cero
    if league_avg_scored == 0:
        league_avg_scored = 1.0
    if league_avg_conceded == 0:
        league_avg_conceded = 1.0

    # ── Fortalezas por equipo ──────────────────────────────────────
    strengths: Dict[str, Dict] = {}

    for team_name, stats in standings.items():
        played = stats.get("played", 0)
        if played == 0:
            # Sin partidos: valores neutros
            strengths[team_name] = {
                "attack_strength":   1.0,
                "defense_strength":  1.0,
                "form_score":        0.0,
                "played":            0,
                "goals_per_game":    league_avg_scored,
                "conceded_per_game": league_avg_conceded,
            }
            continue

        goals_for     = stats.get("goalsFor", 0)
        goals_against = stats.get("goalsAgainst", 0)
        form_str      = stats.get("form", "")

        goals_pg    = goals_for     / played
        conceded_pg = goals_against / played

        attack_str  = goals_pg    / league_avg_scored
        defense_str = conceded_pg / league_avg_conceded
        form_score  = _parse_form_string(form_str)

        strengths[team_name] = {
            "attack_strength":   round(attack_str,  4),
            "defense_strength":  round(defense_str, 4),
            "form_score":        round(form_score,  4),
            "played":            played,
            "goals_per_game":    round(goals_pg,    3),
            "conceded_per_game": round(conceded_pg, 3),
        }

    _cache_set(league_code, "strengths", strengths)
    print(f"[FD] {league_code}: strengths calculados para {len(strengths)} equipos "
          f"(avg goles={league_avg_scored:.2f}, avg concedidos={league_avg_conceded:.2f})")
    return strengths


def get_team_recent_matches(
    league_code: str,
    team_id: int,
    limit: int = 5,
) -> List[Dict]:
    """
    Obtiene los últimos partidos terminados de un equipo en una competición.

    Args:
        league_code: código interno
        team_id:     ID numérico de football-data.org (obtenible desde standings)
        limit:       número máximo de partidos

    Returns:
        Lista de dicts con datos básicos de cada partido:
          {
            "date":       str,
            "home_team":  str,
            "away_team":  str,
            "home_score": int,
            "away_score": int,
            "result":     str,   # "1-0", "2-2", …
            "winner":     str,   # "HOME", "AWAY", "DRAW"
          }
    """
    league_code = league_code.lower()
    comp_id     = FD_COMPETITIONS.get(league_code)

    if not comp_id:
        print(f"[FD] get_team_recent_matches: liga no soportada ({league_code})")
        return []

    params = {
        "team":   team_id,
        "status": "FINISHED",
    }

    data = _fd_get(f"/competitions/{comp_id}/matches", params=params)
    if not data:
        return []

    recent: List[Dict] = []

    # Los partidos de FD están ordenados del más antiguo al más reciente;
    # tomamos los últimos 'limit'.
    matches = data.get("matches", [])
    matches_slice = matches[-limit:] if len(matches) >= limit else matches

    for match in matches_slice:
        try:
            home     = match.get("homeTeam", {}).get("name", "")
            away     = match.get("awayTeam", {}).get("name", "")
            score    = match.get("score", {})
            ft       = score.get("fullTime", {})
            hs       = ft.get("home")
            as_      = ft.get("away")
            winner   = score.get("winner", "DRAW")

            # Normalizar winner
            winner_map = {
                "HOME_TEAM": "HOME",
                "AWAY_TEAM": "AWAY",
                "DRAW":      "DRAW",
            }
            winner = winner_map.get(winner, winner)

            recent.append({
                "date":       match.get("utcDate", ""),
                "home_team":  home,
                "away_team":  away,
                "home_score": hs,
                "away_score": as_,
                "result":     f"{hs}-{as_}" if hs is not None and as_ is not None else "?-?",
                "winner":     winner,
            })
        except Exception as e:
            print(f"[FD] Error parseando partido reciente ({league_code}, team {team_id}): {e}")
            continue

    return recent


def get_strengths_for_match(
    league_code: str,
    home_team: str,
    away_team: str,
) -> Dict:
    """
    Devuelve las fortalezas de ataque/defensa y forma para ambos equipos,
    más la media de goles de la liga.

    Si un equipo no se encuentra en los standings (nombres diferentes, etc.),
    se usan valores neutros (1.0 / 0.0).

    Args:
        league_code: código interno
        home_team:   nombre del equipo local
        away_team:   nombre del equipo visitante

    Returns:
        {
          "home_attack":    float,
          "home_defense":   float,
          "home_form":      float,
          "away_attack":    float,
          "away_defense":   float,
          "away_form":      float,
          "league_avg_goals": float,
          "home_found":     bool,
          "away_found":     bool,
        }
    """
    neutral = {
        "home_attack":      1.0,
        "home_defense":     1.0,
        "home_form":        0.0,
        "away_attack":      1.0,
        "away_defense":     1.0,
        "away_form":        0.0,
        "league_avg_goals": 2.6,
        "home_found":       False,
        "away_found":       False,
    }

    league_code = league_code.lower()
    comp_id     = FD_COMPETITIONS.get(league_code)

    if not comp_id:
        print(f"[FD] get_strengths_for_match: liga no soportada ({league_code})")
        return neutral

    strengths = calculate_team_strengths(league_code)
    if not strengths:
        print(f"[FD] get_strengths_for_match: sin datos de strengths para {league_code}")
        return neutral

    team_names = list(strengths.keys())

    # Buscar equipos con partial match
    home_key = _team_name_match(home_team, team_names)
    away_key = _team_name_match(away_team, team_names)

    if not home_key:
        print(f"[FD] Equipo local no encontrado en standings: '{home_team}' ({league_code})")
    if not away_key:
        print(f"[FD] Equipo visitante no encontrado en standings: '{away_team}' ({league_code})")

    home_data = strengths.get(home_key, {}) if home_key else {}
    away_data = strengths.get(away_key, {}) if away_key else {}

    # Calcular media de goles de la liga a partir de los datos disponibles
    all_gpg = [s["goals_per_game"] for s in strengths.values() if s.get("played", 0) > 0]
    league_avg_goals = (sum(all_gpg) / len(all_gpg)) if all_gpg else 2.6

    return {
        "home_attack":    home_data.get("attack_strength",  1.0),
        "home_defense":   home_data.get("defense_strength", 1.0),
        "home_form":      home_data.get("form_score",       0.0),
        "away_attack":    away_data.get("attack_strength",  1.0),
        "away_defense":   away_data.get("defense_strength", 1.0),
        "away_form":      away_data.get("form_score",       0.0),
        "league_avg_goals": round(league_avg_goals, 3),
        "home_found":     home_key is not None,
        "away_found":     away_key is not None,
    }


# ──────────────────────────────────────────────────────────────────
# CLI de prueba
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if not FOOTBALL_DATA_API_KEY:
        print("[FD] ADVERTENCIA: FOOTBALL_DATA_API_KEY no configurada. "
              "Añade la clave en el archivo .env")
        sys.exit(1)

    leagues_to_test = sys.argv[1:] if len(sys.argv) > 1 else ["pl", "laliga"]

    for code in leagues_to_test:
        print(f"\n{'='*60}")
        print(f"[FD] Liga: {code}")
        print("="*60)

        standings = get_league_standings(code)
        if not standings:
            print(f"  Sin datos de standings para {code}")
            continue

        print(f"  Equipos: {len(standings)}")

        strengths = calculate_team_strengths(code)
        if strengths:
            # Mostrar top 3 atacantes
            top_attack = sorted(strengths.items(), key=lambda x: x[1]["attack_strength"], reverse=True)[:3]
            print(f"\n  Top 3 ataque:")
            for name, s in top_attack:
                print(f"    {name:30} atk={s['attack_strength']:.2f}  def={s['defense_strength']:.2f}  form={s['form_score']:+.2f}")

        # Prueba de match strengths
        team_list = list(standings.keys())
        if len(team_list) >= 2:
            home, away = team_list[0], team_list[1]
            print(f"\n  Fortalezas para {home} vs {away}:")
            result = get_strengths_for_match(code, home, away)
            for k, v in result.items():
                if isinstance(v, float):
                    print(f"    {k}: {v:.4f}")
                else:
                    print(f"    {k}: {v}")
