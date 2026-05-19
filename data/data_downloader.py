#!/usr/bin/env python3
"""
Automatic Sports Data Downloader

Descarga datos históricos de football-data.co.uk y procesa para el bot.
Soporta múltiples ligas y temporadas.
"""

import csv
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
from urllib.request import urlopen
from urllib.error import URLError

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FootballDataDownloader:
    """Descarga datos de football-data.co.uk."""

    # Mapping de deportes a IDs de football-data
    LEAGUE_CODES = {
        "pl": "E0",           # Premier League
        "laliga": "SP1",      # La Liga
        "bundesliga": "D1",   # Bundesliga
        "seriea": "I1",       # Serie A
        "ligue1": "F1",       # Ligue 1
        "mex": "MX1",         # Liga Mexicana (MX1)
    }

    BASE_URL = "https://www.football-data.co.uk"

    def __init__(self, cache_dir: str = "data/historical"):
        """
        Inicializar downloader.

        Args:
            cache_dir: Directorio para cachear archivos descargados
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def download_season(
        self,
        sport: str,
        season: str,
    ) -> Optional[str]:
        """
        Descargar datos de una temporada.

        Args:
            sport: Código de deporte (pl, laliga, etc.)
            season: Año de temporada (ej: "2023-24", "2024-25")

        Returns:
            Ruta al archivo descargado o None si falla
        """
        if sport not in self.LEAGUE_CODES:
            print(f"[ERROR] Deporte desconocido: {sport}")
            print(f"  Opciones: {list(self.LEAGUE_CODES.keys())}")
            return None

        league_code = self.LEAGUE_CODES[sport]
        cache_file = os.path.join(
            self.cache_dir,
            f"{sport}_{season}.csv",
        )

        # Verificar si ya está en cache
        if os.path.exists(cache_file):
            print(f"[CACHE] Usando archivo local: {cache_file}")
            return cache_file

        # Construir URL
        # Format: https://www.football-data.co.uk/mmz4281/2324/E0.csv
        # Convert "2023-24" to "2324"
        season_code = season.replace("-", "")[-4:]  # "2023-24" -> "2324"
        url = f"{self.BASE_URL}/mmz4281/{season_code}/{league_code}.csv"

        print(f"[DOWNLOAD] Descargando desde: {url}")

        try:
            with urlopen(url, timeout=30) as response:
                content = response.read().decode("utf-8")

            # Guardar en cache
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"[SUCCESS] Descargado: {cache_file}")
            return cache_file

        except URLError as e:
            print(f"[ERROR] No se pudo descargar: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Error descargando datos: {e}")
            return None

    def parse_csv(self, csv_path: str) -> List[Dict]:
        """
        Parsear CSV de football-data.co.uk.

        Formato esperado:
        Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR,...

        Returns:
            Lista de diccionarios con partidos
        """
        if not os.path.exists(csv_path):
            print(f"[ERROR] Archivo no encontrado: {csv_path}")
            return []

        matches = []

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        date_str = row.get("Date", "")
                        home_team = row.get("HomeTeam", "")
                        away_team = row.get("AwayTeam", "")
                        home_goals = row.get("FTHG", "0")
                        away_goals = row.get("FTAG", "0")

                        # Saltar si faltan campos críticos
                        if not all([date_str, home_team, away_team]):
                            continue

                        # Parse fecha (formato: DD/MM/YY o DD/MM/YYYY)
                        try:
                            if len(date_str.split("/")[2]) == 2:
                                # DD/MM/YY
                                date_obj = datetime.strptime(date_str, "%d/%m/%y")
                            else:
                                # DD/MM/YYYY
                                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                            date_formatted = date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            # Si no se puede parsear, saltar
                            continue

                        # Parse goles
                        try:
                            home_goals_int = int(float(home_goals))
                            away_goals_int = int(float(away_goals))
                        except (ValueError, TypeError):
                            continue

                        # Determinar resultado
                        if home_goals_int > away_goals_int:
                            result = "home"
                        elif home_goals_int < away_goals_int:
                            result = "away"
                        else:
                            result = "draw"

                        match = {
                            "date": date_formatted,
                            "home_team": home_team.strip(),
                            "away_team": away_team.strip(),
                            "home_goals": home_goals_int,
                            "away_goals": away_goals_int,
                            "result": result,
                            "home_stats": {},
                            "away_stats": {},
                            "h2h": {},
                        }

                        matches.append(match)

                    except Exception as e:
                        # Saltar filas problemáticas
                        continue

            print(f"[PARSE] Procesados {len(matches)} partidos de {csv_path}")
            return matches

        except Exception as e:
            print(f"[ERROR] Error parseando CSV: {e}")
            return []

    def get_team_stats(
        self,
        matches: List[Dict],
        team: str,
        as_of_date: str,
    ) -> Dict:
        """
        Calcular estadísticas de equipo hasta una fecha.

        Args:
            matches: Lista de todos los partidos
            team: Nombre del equipo
            as_of_date: Fecha límite (YYYY-MM-DD)

        Returns:
            Diccionario con estadísticas
        """
        team_matches = []

        # Encontrar todos los partidos del equipo antes de la fecha
        for match in matches:
            if match["date"] >= as_of_date:
                continue

            if team in [match["home_team"], match["away_team"]]:
                team_matches.append(match)

        if not team_matches:
            return {
                "form_5": 0.50,
                "form_10": 0.50,
                "gd": 0.0,
                "gd_home": 0.0,
                "strength": 0.0,
                "attack_strength": 0.0,
                "defense_strength": 0.0,
                "days_rest": 3,
                "matches_last_7days": 0,
            }

        # Form (últimos 5 y 10 partidos)
        def calc_form(n: int) -> float:
            recent = team_matches[-n:] if len(team_matches) >= n else team_matches
            if not recent:
                return 0.50
            wins = sum(
                1 for m in recent
                if (m["home_team"] == team and m["result"] == "home") or
                   (m["away_team"] == team and m["result"] == "away")
            )
            draws = sum(
                1 for m in recent
                if m["result"] == "draw"
            )
            return (wins * 3 + draws) / (len(recent) * 3)

        form_5 = calc_form(5)
        form_10 = calc_form(10)

        # Goal Differential
        goals_for = 0
        goals_against = 0
        for match in team_matches:
            if match["home_team"] == team:
                goals_for += match["home_goals"]
                goals_against += match["away_goals"]
            else:
                goals_for += match["away_goals"]
                goals_against += match["home_goals"]

        gd = (goals_for - goals_against) / max(1, len(team_matches)) if team_matches else 0.0

        # Strength (simplificado)
        strength = (form_5 - 0.5) * 0.2  # Rango: -0.1 a 0.1

        return {
            "form_5": form_5,
            "form_10": form_10,
            "gd": gd,
            "gd_home": gd * 0.9,  # Aproximación
            "strength": strength,
            "attack_strength": strength * 1.5,
            "defense_strength": -strength * 0.5,
            "days_rest": 3,  # Aproximación
            "matches_last_7days": min(3, len(team_matches[-2:])),  # Aproximación
        }

    def enrich_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        Enriquecer partidos con estadísticas de equipos.

        Args:
            matches: Lista de partidos

        Returns:
            Partidos con home_stats, away_stats, h2h
        """
        for i, match in enumerate(matches):
            # Estadísticas de equipo
            match["home_stats"] = self.get_team_stats(
                matches, match["home_team"], match["date"]
            )
            match["away_stats"] = self.get_team_stats(
                matches, match["away_team"], match["date"]
            )

            # Head-to-head (últimos 10 enfrentamientos)
            h2h_matches = [
                m for m in matches[:i]
                if (m["home_team"] == match["home_team"] and
                    m["away_team"] == match["away_team"]) or
                   (m["home_team"] == match["away_team"] and
                    m["away_team"] == match["home_team"])
            ][-10:]

            h2h_home_wins = sum(
                1 for m in h2h_matches
                if (m["home_team"] == match["home_team"] and m["result"] == "home") or
                   (m["away_team"] == match["home_team"] and m["result"] == "away")
            )
            h2h_draws = sum(1 for m in h2h_matches if m["result"] == "draw")
            h2h_away_wins = len(h2h_matches) - h2h_home_wins - h2h_draws

            match["h2h"] = {
                "home_wins": h2h_home_wins,
                "draws": h2h_draws,
                "away_wins": h2h_away_wins,
            }

        return matches


def main():
    """Test downloader."""
    downloader = FootballDataDownloader()

    print("[TEST] Descargando datos PL 2023-24...\n")

    # Descargar
    csv_path = downloader.download_season("pl", "2023-24")

    if not csv_path:
        print("[ERROR] No se pudo descargar")
        return 1

    # Parsear
    matches = downloader.parse_csv(csv_path)

    if not matches:
        print("[ERROR] No se pudo parsear")
        return 1

    # Enriquecer
    matches = downloader.enrich_matches(matches)

    print(f"\n[RESULT] Total partidos: {len(matches)}")
    print(f"\n[SAMPLE] Primeros 3 partidos:")
    for match in matches[:3]:
        print(f"\n  {match['date']}: {match['home_team']} {match['home_goals']}-{match['away_goals']} {match['away_team']}")
        print(f"    Resultado: {match['result']}")
        print(f"    Home form_5: {match['home_stats'].get('form_5', 0):.2f}")
        print(f"    Away form_5: {match['away_stats'].get('form_5', 0):.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
