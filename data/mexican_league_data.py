#!/usr/bin/env python3
"""
Generador de Datos de Liga Mexicana

Crea datos sintéticos realistas basados en equipos y rendimiento histórico
de Liga Mexicana para entrenar el modelo.

IMPORTANTE: Solo usa equipos de CLUBS (Liga Mexicana), no selección nacional.
Validación: data/leagues_data.py
"""

import sys
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.leagues_data import get_all_teams_for_league, validate_team_for_league


class MexicanLeagueDataGenerator:
    """Genera datos sintéticos pero realistas de Liga Mexicana."""

    # Equipos VÁLIDOS de Liga Mexicana (obtenidos de leagues_data)
    TEAMS = list(get_all_teams_for_league("mex"))

    # Probabilidades de victoria por equipo (força relativa)
    # Solo para equipos VÁLIDOS de Liga Mexicana
    TEAM_STRENGTH = {
        "Tigres": 0.62,
        "Monterrey": 0.58,
        "Guadalajara": 0.56,
        "Pachuca": 0.52,
        "Toluca": 0.51,
        "Pumas": 0.47,
        "Cruz Azul": 0.46,
        "Santos": 0.45,
        "Queretaro": 0.44,
        "Necaxa": 0.48,
        "Atletico San Luis": 0.43,
        "FC Juarez": 0.36,
        "Atlante": 0.38,
        "Mazatlan": 0.42,
        "Bravos": 0.40,
        "Puebla": 0.45,
        "Leon": 0.50,
        "Morelia": 0.41,
    }

    def __init__(self):
        """Inicializar generador."""
        self.matches = []

    def generate_season(self, season: str = "2025-26", num_rounds: int = 17) -> List[Dict]:
        """
        Generar una temporada de Liga Mexicana.

        Liga MX tiene ~34 partidos (17 rondas x 2 fases o similar).

        Args:
            season: Año de temporada
            num_rounds: Número de jornadas

        Returns:
            Lista de partidos simulados
        """
        matches = []
        start_date = datetime(2025, 7, 1)  # Inicia en julio

        round_num = 0

        # Crear partidos
        for round_idx in range(num_rounds):
            # Cada jornada tiene 9 partidos (18 equipos / 2)
            for i in range(9):
                # Seleccionar equipos únicos para este partido
                available_teams = self.TEAMS.copy()
                home_team = random.choice(available_teams)
                available_teams.remove(home_team)
                away_team = random.choice(available_teams)

                # Simular resultado basado en fortaleza de equipos
                home_strength = self.TEAM_STRENGTH.get(home_team, 0.5)
                away_strength = self.TEAM_STRENGTH.get(away_team, 0.5)

                # Aplicar ventaja de casa (+5%)
                home_prob = (home_strength + away_strength / 2) * 1.05
                home_prob = min(home_prob, 0.95)

                # Generar resultado
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

                match_date = start_date + timedelta(days=round_idx * 7 + (i % 7))

                match = {
                    "date": match_date.strftime("%Y-%m-%d"),
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "result": result,
                    "home_stats": {
                        "form_5": random.uniform(0.35, 0.70),
                        "form_10": random.uniform(0.35, 0.70),
                        "gd": random.uniform(-0.5, 1.0),
                        "strength": self.TEAM_STRENGTH.get(home_team, 0.5) - 0.5,
                        "attack_strength": self.TEAM_STRENGTH.get(home_team, 0.5) - 0.5,
                        "defense_strength": self.TEAM_STRENGTH.get(home_team, 0.5) - 0.5,
                        "days_rest": random.randint(3, 7),
                        "matches_last_7days": random.randint(0, 2),
                    },
                    "away_stats": {
                        "form_5": random.uniform(0.35, 0.70),
                        "form_10": random.uniform(0.35, 0.70),
                        "gd": random.uniform(-0.5, 1.0),
                        "strength": self.TEAM_STRENGTH.get(away_team, 0.5) - 0.5,
                        "attack_strength": self.TEAM_STRENGTH.get(away_team, 0.5) - 0.5,
                        "defense_strength": self.TEAM_STRENGTH.get(away_team, 0.5) - 0.5,
                        "days_rest": random.randint(3, 7),
                        "matches_last_7days": random.randint(0, 2),
                    },
                    "h2h": {
                        "home_wins": random.randint(0, 3),
                        "draws": random.randint(0, 2),
                        "away_wins": random.randint(0, 3),
                    }
                }

                matches.append(match)

        return matches

    def save_matches(self, matches: List[Dict], filepath: str):
        """Guardar matches en archivo local."""
        import json
        with open(filepath, 'w') as f:
            json.dump(matches, f, indent=2)
        print(f"[OK] {len(matches)} partidos guardados en {filepath}")

    def load_matches(self, filepath: str) -> List[Dict]:
        """Cargar matches desde archivo."""
        import json
        with open(filepath, 'r') as f:
            return json.load(f)


def main():
    """Generar datos de Liga Mexicana."""
    print("\n" + "="*80)
    print("GENERADOR DE DATOS: LIGA MEXICANA 2025-26")
    print("="*80)

    generator = MexicanLeagueDataGenerator()

    print("\n[1] Generando partidos de Liga Mexicana...")
    matches = generator.generate_season("2025-26", num_rounds=17)
    print(f"[OK] {len(matches)} partidos generados")

    # Guardar
    filepath = "data/mexican_league_2025-26.json"
    generator.save_matches(matches, filepath)

    # Mostrar sample
    print(f"\n[2] Sample de primeros 5 partidos:")
    for match in matches[:5]:
        print(
            f"  {match['date']}: {match['home_team']:<15} {match['home_goals']}"
            f"-{match['away_goals']} {match['away_team']:<15} [{match['result'].upper()}]"
        )

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
