#!/usr/bin/env python3
"""
Cargador Universal de Datos de Ligas

Soporta múltiples ligas con validación automática de equipos.
Previene errores como "Mexico" (selección) en Liga Mexicana (clubs).
"""

import sys
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.leagues_data import (
    get_league,
    validate_team_for_league,
    get_all_teams_for_league,
)


class UniversalDataLoader:
    """Carga datos para cualquier liga con validación."""

    # Fortaleza relativa de equipos (por liga)
    LEAGUE_STRENGTHS = {
        # Liga Mexicana (MX1)
        "mex": {
            "Tigres": 0.62,
            "Monterrey": 0.58,
            "Guadalajara": 0.56,
            "Pachuca": 0.52,
            "Toluca": 0.51,
            "Leon": 0.50,
            "Pumas": 0.47,
            "Cruz Azul": 0.46,
            "Santos": 0.45,
            "Puebla": 0.45,
            "Necaxa": 0.48,
            "Atletico San Luis": 0.43,
            "Mazatlan": 0.42,
            "Bravos": 0.40,
            "Atlante": 0.38,
            "FC Juarez": 0.36,
            "Queretaro": 0.44,
            "Morelia": 0.41,
        },
        # La Liga (España)
        "laliga": {
            "Real Madrid": 0.70,
            "Barcelona": 0.68,
            "Atletico Madrid": 0.62,
            "Real Sociedad": 0.56,
            "Villarreal": 0.54,
            "Athletic Bilbao": 0.52,
            "Valencia": 0.50,
            "Sevilla": 0.49,
            "Getafe": 0.46,
            "Girona": 0.48,
            "Osasuna": 0.45,
            "Mallorca": 0.44,
            "Real Betis": 0.46,
            "Rayo Vallecano": 0.42,
            "Celta": 0.41,
            "Granada": 0.40,
            "Cadiz": 0.38,
            "Almeria": 0.37,
            "Las Palmas": 0.39,
            "Alaves": 0.40,
        },
        # Premier League
        "pl": {
            "Manchester City": 0.75,
            "Manchester United": 0.65,
            "Arsenal": 0.63,
            "Liverpool": 0.62,
            "Chelsea": 0.58,
            "Tottenham Hotspur": 0.55,
            "Newcastle United": 0.52,
            "Brighton": 0.50,
            "Aston Villa": 0.51,
            "West Ham United": 0.46,
            "Fulham": 0.47,
            "Crystal Palace": 0.44,
            "Brentford": 0.45,
            "Wolverhampton Wanderers": 0.43,
            "Bournemouth": 0.42,
            "Everton": 0.41,
            "Ipswich Town": 0.38,
            "Nottingham Forest": 0.40,
            "Leicester City": 0.39,
            "Southampton": 0.35,
        },
        # Serie A (Italia)
        "seriea": {
            "Inter Milan": 0.68,
            "AC Milan": 0.66,
            "Juventus": 0.65,
            "Napoli": 0.58,
            "AS Roma": 0.54,
            "Lazio": 0.53,
            "Atalanta": 0.56,
            "Fiorentina": 0.49,
            "Torino": 0.46,
            "Bologna": 0.45,
            "Monza": 0.42,
            "Sassuolo": 0.44,
            "Verona": 0.41,
            "Como": 0.39,
            "Parma": 0.40,
            "Cagliari": 0.38,
            "Empoli": 0.37,
            "Lecce": 0.36,
            "Frosinone": 0.33,
            "Salernitana": 0.32,
        },
        # Bundesliga (Alemania)
        "bundesliga": {
            "Bayern Munich": 0.72,
            "Borussia Dortmund": 0.62,
            "RB Leipzig": 0.60,
            "Bayer Leverkusen": 0.58,
            "Stuttgart": 0.52,
            "VfL Wolfsburg": 0.48,
            "Eintracht Frankfurt": 0.46,
            "Hoffenheim": 0.45,
            "Borussia Monchengladbach": 0.43,
            "Mainz": 0.42,
            "Augsburg": 0.40,
            "Cologne": 0.38,
            "Union Berlin": 0.44,
            "Werder Bremen": 0.39,
            "Freiburg": 0.41,
            "Bochum": 0.36,
            "Schalke 04": 0.35,
            "Heidenheim": 0.34,
        },
        # Ligue 1 (Francia)
        "ligue1": {
            "Paris Saint-Germain": 0.70,
            "Olympique Marseille": 0.56,
            "AS Monaco": 0.54,
            "Olympique Lyonnais": 0.52,
            "Stade Rennes": 0.48,
            "Lens": 0.47,
            "Nice": 0.45,
            "Toulouse": 0.43,
            "Strasbourg": 0.42,
            "Lille": 0.44,
            "Nantes": 0.41,
            "Saint-Etienne": 0.38,
            "Angers": 0.37,
            "Montpellier": 0.36,
            "Metz": 0.34,
            "Reims": 0.33,
            "Le Havre": 0.32,
            "Lorient": 0.31,
        },
        # MLS (USA/Canada)
        "mls": {
            "Los Angeles FC": 0.58,
            "LA Galaxy": 0.54,
            "New York City FC": 0.52,
            "Seattle Sounders": 0.50,
            "FC Cincinnati": 0.48,
            "Toronto FC": 0.47,
            "Philadelphia Union": 0.46,
            "New York Red Bulls": 0.44,
            "Houston Dynamo": 0.43,
            "Portland Timbers": 0.42,
            "Minnesota United": 0.40,
            "Real Salt Lake": 0.39,
            "Austin FC": 0.45,
            "Chicago Fire": 0.37,
            "Atlanta United": 0.41,
            "Colorado Rapids": 0.38,
            "Sporting Kansas City": 0.40,
            "FC Dallas": 0.36,
            "Vancouver Whitecaps": 0.35,
            "Montreal Impact": 0.34,
            "San Jose Earthquakes": 0.32,
            "New England Revolution": 0.31,
        },
        # Brasileirão
        "brasil": {
            "Palmeiras": 0.65,
            "Flamengo": 0.62,
            "Botafogo": 0.60,
            "Atletico Mineiro": 0.58,
            "Sao Paulo": 0.54,
            "Internacional": 0.52,
            "Gremio": 0.50,
            "Corinthians": 0.48,
            "Fortaleza": 0.46,
            "Santos": 0.44,
            "Vasco da Gama": 0.42,
            "Cruzeiro": 0.41,
            "Bahia": 0.39,
            "RB Bragantino": 0.38,
            "Vitoria": 0.36,
            "Cebolinha": 0.34,
            "Goias": 0.33,
            "Cuiaba": 0.32,
        },
        # Süper Lig (Turquía)
        "superlig": {
            "Galatasaray": 0.68,
            "Fenerbahce": 0.66,
            "Besiktas": 0.62,
            "Trabzonspor": 0.58,
            "Istanbul Basaksehir": 0.52,
            "Kayserispor": 0.48,
            "Sivasspor": 0.46,
            "Gaziantep FK": 0.44,
            "Konyaspor": 0.42,
            "Kasimpasa": 0.40,
            "Antalyaspor": 0.38,
            "Altay": 0.36,
            "Genclerbirligi": 0.34,
            "Adana Demirspor": 0.37,
            "Erzurumspor": 0.33,
            "Alanyaspor": 0.35,
            "Istanbulspor": 0.32,
            "Samsunspor": 0.31,
        },
    }

    def __init__(self, league_code: str):
        """Inicializar cargador para una liga específica."""
        self.league_code = league_code.lower()
        self.league = get_league(self.league_code)
        self.teams = list(get_all_teams_for_league(self.league_code))
        self.strengths = self.LEAGUE_STRENGTHS.get(self.league_code, {})

        print(f"[DataLoader] Inicializado para {self.league.name}")
        print(f"[DataLoader] {len(self.teams)} equipos válidos cargados")

    def validate_team(self, team_name: str) -> bool:
        """Validar que un equipo es válido para esta liga."""
        valid = validate_team_for_league(team_name, self.league_code)
        if not valid:
            print(
                f"[WARNING] Equipo inválido '{team_name}' para {self.league_code}. "
                f"Equipos válidos: {', '.join(sorted(self.teams)[:5])}..."
            )
        return valid

    def get_team_strength(self, team_name: str) -> float:
        """Obtener fortaleza de un equipo."""
        if not self.validate_team(team_name):
            return 0.5  # Default si equipo inválido

        return self.strengths.get(team_name, 0.5)

    def generate_season_data(
        self, season: str = "2025-26", num_rounds: int = 17
    ) -> List[Dict]:
        """
        Generar datos sintéticos de una temporada.

        Returns:
            Lista de partidos simulados
        """
        import random

        matches = []
        start_date = datetime(2025, 7, 1)

        for round_idx in range(num_rounds):
            # Cada jornada tiene N/2 partidos
            for i in range(len(self.teams) // 2):
                # Seleccionar equipos únicos
                available_teams = self.teams.copy()
                home_team = random.choice(available_teams)
                available_teams.remove(home_team)
                away_team = random.choice(available_teams)

                # Fortaleza
                home_strength = self.get_team_strength(home_team)
                away_strength = self.get_team_strength(away_team)

                # Ventaja de casa (+5%)
                home_prob = (home_strength + away_strength / 2) * 1.05
                home_prob = min(home_prob, 0.95)

                # Resultado
                rand = random.random()
                if rand < home_prob:
                    result = "home"
                    home_goals = random.randint(1, 3)
                    away_goals = random.randint(0, 1)
                elif rand < home_prob + 0.25:
                    result = "draw"
                    home_goals = random.randint(1, 2)
                    away_goals = home_goals
                else:
                    result = "away"
                    home_goals = random.randint(0, 1)
                    away_goals = random.randint(1, 3)

                match_date = start_date + timedelta(days=round_idx * 7 + i)

                matches.append({
                    "date": match_date.isoformat(),
                    "round": round_idx + 1,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "result": result,
                    "league": self.league_code,
                    "season": season,
                })

        print(f"[DataLoader] Generados {len(matches)} partidos para {season}")
        return matches


def main():
    """Test cargador universal."""
    print("\n[TEST] Cargador Universal de Datos\n")

    # Test múltiples ligas
    test_leagues = ["mex", "laliga", "pl", "bundesliga"]

    for league_code in test_leagues:
        print(f"\n{league_code.upper()}:")
        loader = UniversalDataLoader(league_code)

        # Test validación
        first_team = sorted(loader.teams)[0]
        print(f"  Equipo válido: {first_team} (fortaleza: {loader.get_team_strength(first_team):.2f})")

        # Test equipo inválido
        invalid_team = "TeamInvalido123"
        is_valid = loader.validate_team(invalid_team)
        print(f"  Equipo inválido: {invalid_team} -> {is_valid}")

    print("\n")


if __name__ == "__main__":
    main()
