#!/usr/bin/env python3
"""
Football Data Integration — football-data.org (primary) + ESPN (secondary)

Order of preference for fixtures:
  1. football-data.org  → partidos EN VIVO o SCHEDULED (reales)
  2. ESPN API           → próximos partidos (Premier League, La Liga, etc.)
  3. Synthetic data     → sólo si todo lo anterior falla
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Mapeo football-data.org competition codes
FOOTBALL_DATA_IDS = {
    "pl":           "PL",    # Premier League
    "laliga":       "PD",    # La Liga
    "bundesliga":   "BL1",   # Bundesliga
    "ligue1":       "FL1",   # Ligue 1
    "seriea":       "SA",    # Serie A
    "brasil":       "BSA",   # Brasileirão
    "ucl":          "CL",    # Champions League
    "libertadores": "CLI",   # Copa Libertadores
}

# Mapeo ESPN IDs (sólo Europa tiene endpoints libres)
ESPN_IDS = {
    "pl":         "eng.1",
    "laliga":     "esp.1",
    "seriea":     "ita.1",
    "bundesliga": "ger.1",
    "ligue1":     "fra.1",
}


class FootballAPI:
    """
    Fuente de fixtures y estadísticas para el bot.

    Prioridad de datos:
      1. football-data.org (partidos en vivo o próximos)
      2. ESPN (próximos partidos de ligas europeas)
      3. Datos sintéticos (fallback final)
    """

    def __init__(self, league_code: str = "pl", cache_file: str = "fixtures_cache.json"):
        self.league_code = league_code.lower()
        # Guardar cache en cache/ (relativo a la raíz del proyecto)
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _cache_dir = os.path.join(_root, "cache")
        os.makedirs(_cache_dir, exist_ok=True)
        self.cache_file = os.path.join(_cache_dir, f"{self.league_code}_{cache_file}")
        self.cache_data: Dict = {}
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    self.cache_data = json.load(f)
            except Exception:
                pass

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache_data, f, indent=2)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # PUBLIC: fetch fixtures
    # ─────────────────────────────────────────────────────────────

    def fetch_upcoming_fixtures(self, days_ahead: int = 7) -> Optional[List[Dict]]:
        """
        Devuelve los próximos partidos para la liga configurada.

        Primero intenta football-data.org, luego ESPN, luego sintético.
        Siempre incluye partidos en vivo (IN_PLAY, PAUSED).
        """
        league_name = self._league_name()

        # 1. football-data.org (mejor fuente: incluye en vivo)
        fixtures = self._fetch_from_football_data(days_ahead, league_name)
        if fixtures:
            self.cache_data["fixtures"] = fixtures
            self._save_cache()
            return fixtures

        # 2. ESPN (sólo ligas europeas)
        if self.league_code in ESPN_IDS:
            fixtures = self._fetch_from_espn(days_ahead, league_name)
            if fixtures:
                self.cache_data["fixtures"] = fixtures
                self._save_cache()
                return fixtures

        # 3. Cache anterior
        if "fixtures" in self.cache_data and self.cache_data["fixtures"]:
            return self.cache_data["fixtures"]

        # 4. Sintético como último recurso
        print(f"[API] Generating synthetic fixtures for {self.league_code}")
        return self._generate_synthetic_fixtures(days_ahead, league_name)

    # ─────────────────────────────────────────────────────────────
    # PRIVATE: sources
    # ─────────────────────────────────────────────────────────────

    def _fetch_from_football_data(self, days_ahead: int, league_name: str) -> List[Dict]:
        """Obtiene partidos desde football-data.org (en vivo + próximos)."""
        if not FOOTBALL_DATA_API_KEY:
            return []

        comp_id = FOOTBALL_DATA_IDS.get(self.league_code)
        if not comp_id:
            return []

        now = datetime.now(timezone.utc)
        date_to = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        date_from = now.strftime("%Y-%m-%d")

        headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
        fixtures = []

        # ── Partidos EN VIVO / PAUSED (máxima prioridad) ──
        try:
            r = requests.get(
                f"{FOOTBALL_DATA_BASE_URL}/competitions/{comp_id}/matches",
                headers=headers,
                params={"status": "IN_PLAY,PAUSED"},
                timeout=6,
            )
            if r.status_code == 200:
                for match in r.json().get("matches", []):
                    f = self._parse_fd_match(match, league_name)
                    if f:
                        fixtures.append(f)
        except Exception as e:
            print(f"[API] football-data live error ({self.league_code}): {e}")

        # ── Partidos PROGRAMADOS hoy y próximos días ──
        try:
            r = requests.get(
                f"{FOOTBALL_DATA_BASE_URL}/competitions/{comp_id}/matches",
                headers=headers,
                params={"status": "SCHEDULED", "dateFrom": date_from, "dateTo": date_to},
                timeout=6,
            )
            if r.status_code == 200:
                for match in r.json().get("matches", []):
                    f = self._parse_fd_match(match, league_name)
                    if f:
                        fixtures.append(f)
        except Exception as e:
            print(f"[API] football-data scheduled error ({self.league_code}): {e}")

        # Ordenar: en vivo primero, luego por fecha
        fixtures.sort(key=lambda x: (0 if x["status"] in ("IN_PLAY", "PAUSED") else 1, x["timestamp"]))
        return fixtures

    def _parse_fd_match(self, match: Dict, league_name: str) -> Optional[Dict]:
        """Convierte un match de football-data.org al formato interno del bot."""
        try:
            home = match.get("homeTeam", {}).get("name", "")
            away = match.get("awayTeam", {}).get("name", "")
            if not home or not away:
                return None

            utc_date = match.get("utcDate", "")
            dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
            status = match.get("status", "SCHEDULED")

            # Score actual (si está en vivo)
            score_data = match.get("score", {})
            ft = score_data.get("fullTime", {})
            home_score = ft.get("home")
            away_score = ft.get("away")

            return {
                "date":       dt.isoformat(),
                "timestamp":  int(dt.timestamp()),
                "home_team":  home,
                "away_team":  away,
                "status":     status,
                "league":     league_name,
                "home_score": home_score,
                "away_score": away_score,
                "match_id":   match.get("id"),
                "source":     "football-data.org",
            }
        except Exception:
            return None

    def _fetch_from_espn(self, days_ahead: int, league_name: str) -> List[Dict]:
        """Obtiene próximos partidos desde ESPN (sólo ligas europeas)."""
        espn_id = ESPN_IDS.get(self.league_code)
        if not espn_id:
            return []

        try:
            now = datetime.now(timezone.utc)
            url = f"https://site.api.espn.com/site/v2/sports/soccer/{espn_id}/events"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            fixtures = []
            for evt in data.get("events", []):
                try:
                    evt_date = datetime.fromisoformat(evt["date"].replace("Z", "+00:00"))
                    days_until = (evt_date - now).days
                    if not (0 <= days_until <= days_ahead):
                        continue

                    comps = evt.get("competitions", [{}])[0]
                    competitors = comps.get("competitors", [])
                    if len(competitors) < 2:
                        continue

                    home = competitors[0].get("team", {}).get("name", "")
                    away = competitors[1].get("team", {}).get("name", "")
                    if not home or not away:
                        continue

                    fixtures.append({
                        "date":      evt_date.isoformat(),
                        "timestamp": int(evt_date.timestamp()),
                        "home_team": home,
                        "away_team": away,
                        "status":    "SCHEDULED",
                        "league":    league_name,
                        "source":    "espn",
                    })
                except Exception:
                    continue

            fixtures.sort(key=lambda x: x["timestamp"])
            return fixtures

        except Exception as e:
            print(f"[API] ESPN fetch error ({self.league_code}): {e}")
            return []

    def _generate_synthetic_fixtures(self, days_ahead: int, league_name: str) -> List[Dict]:
        """Genera fixtures sintéticos sólo si todo lo anterior falla."""
        import random

        try:
            from data.leagues_data import get_all_teams_for_league
            teams = list(get_all_teams_for_league(self.league_code))
        except Exception:
            return []

        if len(teams) < 2:
            return []

        fixtures = []
        now = datetime.now(timezone.utc)
        random.seed(int(now.timestamp()))

        for _ in range(4):
            days_offset = random.randint(1, days_ahead)
            fixture_date = now + timedelta(days=days_offset)
            home, away = random.sample(teams, 2)
            fixtures.append({
                "date":      fixture_date.isoformat(),
                "timestamp": int(fixture_date.timestamp()),
                "home_team": home,
                "away_team": away,
                "status":    "SCHEDULED",
                "league":    league_name,
                "source":    "synthetic",
            })

        fixtures.sort(key=lambda x: x["timestamp"])
        self.cache_data["fixtures"] = fixtures
        self._save_cache()
        return fixtures

    # ─────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────

    def fetch_team_stats(self, team_name: str) -> Optional[Dict]:
        """Estadísticas del equipo (cache o valores por defecto)."""
        if "team_stats" not in self.cache_data:
            self.cache_data["team_stats"] = {}

        if team_name in self.cache_data["team_stats"]:
            return self.cache_data["team_stats"][team_name]

        stats = {
            "team_name":           team_name,
            "form_5":              [1, 1, 0, 1, 1],
            "home_form_5":         [1, 1, 0, 1, 1],
            "away_form_5":         [1, 1, 0, 1, 1],
            "goals_for":           45,
            "goals_against":       20,
            "goals_for_home":      28,
            "goals_against_home":  10,
            "goals_for_away":      17,
            "goals_against_away":  10,
            "h2h_record":          {},
        }
        self.cache_data["team_stats"][team_name] = stats
        return stats

    def fetch_head_to_head(self, home_team: str, away_team: str) -> Dict:
        return {
            "home_wins": 2, "draws": 1, "away_wins": 0,
            "last_3": [
                {"date": "2024-01-01", "result": "1-0", "winner": "HOME"},
                {"date": "2023-11-15", "result": "2-2", "winner": "DRAW"},
                {"date": "2023-09-30", "result": "0-1", "winner": "AWAY"},
            ],
        }

    def get_league_avg_stats(self) -> Dict:
        return {"avg_goals_per_match": 2.7, "avg_goals_home": 1.4, "avg_goals_away": 1.3}

    def _league_name(self) -> str:
        names = {
            "pl": "Premier League", "laliga": "La Liga",
            "seriea": "Serie A", "bundesliga": "Bundesliga",
            "ligue1": "Ligue 1", "brasil": "Brasileirao",
            "mex": "Liga MX", "mls": "MLS",
            "ucl": "Champions League", "libertadores": "Copa Libertadores",
            "superlig": "Super Lig", "nfl": "NFL",
        }
        return names.get(self.league_code, "Football League")


# ─────────────────────────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    for code in ["laliga", "ligue1", "seriea", "brasil"]:
        api = FootballAPI(league_code=code)
        fixtures = api.fetch_upcoming_fixtures(days_ahead=1)
        print(f"\n[{code.upper()}] {len(fixtures or [])} fixtures")
        for f in (fixtures or [])[:4]:
            score = ""
            if f.get("home_score") is not None:
                score = f"  {f['home_score']}-{f['away_score']}"
            print(f"  {f['status']:10} {f['home_team']} vs {f['away_team']}{score}  [{f.get('source','')}]")
