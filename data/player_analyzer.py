#!/usr/bin/env python3
"""
Analizador de Jugadores y Alineaciones

Incorpora:
- Estadísticas individuales de jugadores
- Estado de lesiones
- Alineaciones probables
- Impacto en predicción del equipo
"""

import sys
import os
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PlayerAnalyzer:
    """Analiza jugadores, lesiones y alineaciones."""

    # Base de datos de jugadores (Guadalajara vs Tigres UANL)
    TEAM_ROSTERS = {
        "Guadalajara": {
            "squad_value": 8.6,  # Millones USD
            "key_players": [
                {"name": "Alexis Vega", "position": "RW", "rating": 87, "status": "healthy", "impact": 0.15},
                {"name": "Jose Juan Macias", "position": "ST", "rating": 85, "status": "healthy", "impact": 0.14},
                {"name": "Alan Mozo", "position": "RB", "rating": 82, "status": "healthy", "impact": 0.10},
                {"name": "Hiram Mier", "position": "CB", "rating": 80, "status": "healthy", "impact": 0.08},
                {"name": "Ismael Govea", "position": "CM", "rating": 81, "status": "healthy", "impact": 0.09},
            ],
            "bench_strength": 0.78,
        },
        "Tigres": {
            "squad_value": 8.4,
            "key_players": [
                {"name": "Andre-Pierre Gignac", "position": "ST", "rating": 85, "status": "questionable", "impact": 0.14},
                {"name": "Thiago Almada", "position": "CM", "rating": 84, "status": "healthy", "impact": 0.13},
                {"name": "Joaquin Pereira", "position": "CB", "rating": 81, "status": "healthy", "impact": 0.09},
                {"name": "Nahuel Guzman", "position": "CB", "rating": 80, "status": "healthy", "impact": 0.08},
                {"name": "Jesus Dueñas", "position": "LB", "rating": 77, "status": "injured", "impact": 0.06},
            ],
            "bench_strength": 0.70,
        }
    }

    # Lesiones recientes
    INJURIES = {
        "Guadalajara": [],
        "Tigres": [
            {"player": "Andre-Pierre Gignac", "status": "QUESTIONABLE", "severity": "MODERATE", "probability": 0.4, "details": "Cadera molesta"},
            {"player": "Jesus Dueñas", "status": "OUT", "severity": "SEVERE", "probability": 0.0, "details": "Lesión muscular"},
        ]
    }

    def __init__(self):
        """Inicializar analizador."""
        pass

    def get_team_roster(self, team_name: str) -> Dict:
        """Obtener plantilla de un equipo."""
        return self.TEAM_ROSTERS.get(team_name, {})

    def get_injuries(self, team_name: str) -> List[Dict]:
        """Obtener lesiones actuales de un equipo."""
        return self.INJURIES.get(team_name, [])

    def analyze_available_players(self, team_name: str) -> Dict:
        """
        Analizar jugadores disponibles vs lesionados.

        Returns:
            {
                'total_key_players': 5,
                'available_key_players': 4,
                'missing_impact': 0.14,  # % de impacto perdido
                'squad_strength_adjusted': 0.86,  # Fortaleza ajustada por lesiones
                'lineup_quality': 0.87,
                'critical_absences': ['Andre-Pierre Gignac']
            }
        """
        roster = self.get_team_roster(team_name)
        injuries = self.get_injuries(team_name)

        if not roster or "key_players" not in roster:
            return {}

        key_players = roster["key_players"]
        total_impact = sum(p["impact"] for p in key_players)
        missing_impact = 0

        injured_players = {inj["player"]: inj for inj in injuries}
        available_players = []
        critical_absences = []
        questionable_players = []

        for player in key_players:
            if player["name"] in injured_players:
                injury = injured_players[player["name"]]
                if injury["status"] == "OUT":
                    missing_impact += player["impact"]
                    critical_absences.append(player["name"])
                elif injury["status"] == "QUESTIONABLE":
                    # 40% probabilidad de no jugar
                    missing_impact += player["impact"] * injury["probability"]
                    questionable_players.append({
                        "name": player["name"],
                        "availability": 1 - injury["probability"],
                        "details": injury["details"]
                    })
            else:
                available_players.append(player)

        # Ajuste de fortaleza
        base_strength = (roster.get("squad_value", 8.0) / 10) * 0.5 + roster.get("bench_strength", 0.75) * 0.5
        strength_adjusted = base_strength * (1 - (missing_impact / total_impact))

        return {
            "total_key_players": len(key_players),
            "available_key_players": len(available_players),
            "questionable_players": questionable_players,
            "critical_absences": critical_absences,
            "missing_impact_pct": (missing_impact / total_impact * 100) if total_impact > 0 else 0,
            "squad_strength_base": base_strength,
            "squad_strength_adjusted": strength_adjusted,
            "impact_loss": missing_impact / total_impact if total_impact > 0 else 0,
            "available_players_list": [p["name"] for p in available_players],
        }

    def get_probable_lineup(self, team_name: str) -> List[str]:
        """Obtener alineación probable."""
        roster = self.get_team_roster(team_name)
        injuries = self.get_injuries(team_name)
        injured_names = {inj["player"] for inj in injuries if inj["status"] == "OUT"}

        if not roster or "key_players" not in roster:
            return []

        available = [p["name"] for p in roster["key_players"] if p["name"] not in injured_names]
        return available

    def compare_lineups(self, home_team: str, away_team: str) -> Dict:
        """
        Comparar alineaciones de dos equipos.

        Returns:
            Análisis de ventajas y desventajas por lesiones
        """
        home_analysis = self.analyze_available_players(home_team)
        away_analysis = self.analyze_available_players(away_team)

        home_impact_loss = home_analysis.get("impact_loss", 0)
        away_impact_loss = away_analysis.get("impact_loss", 0)

        # Ventaja relativa (quién está más debilitado)
        lineup_advantage = away_impact_loss - home_impact_loss

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_analysis": home_analysis,
            "away_analysis": away_analysis,
            "home_impact_loss_pct": home_impact_loss * 100,
            "away_impact_loss_pct": away_impact_loss * 100,
            "lineup_advantage": lineup_advantage,  # Positivo = ventaja al local
            "critical_issues": {
                "home": home_analysis.get("critical_absences", []),
                "away": away_analysis.get("critical_absences", []),
            },
            "analysis": self._generate_analysis(home_team, away_team, home_analysis, away_analysis)
        }

    def _generate_analysis(self, home: str, away: str, home_data: Dict, away_data: Dict) -> str:
        """Generar análisis textual."""
        home_impact = home_data.get("missing_impact_pct", 0)
        away_impact = away_data.get("missing_impact_pct", 0)

        if home_impact > 15:
            return f"{home} muy debilitado por lesiones (-{home_impact:.0f}% impacto)"
        elif away_impact > 15:
            return f"{away} está sin jugadores clave (-{away_impact:.0f}% impacto)"
        elif home_impact > away_impact + 5:
            return f"Ventaja {away}: {home} tiene más ausencias"
        elif away_impact > home_impact + 5:
            return f"Ventaja {home}: {away} está diezmado"
        else:
            return "Ambos equipos con plantillas similares disponibles"

    def adjust_prediction(
        self,
        original_probs: Dict[str, float],
        home_team: str,
        away_team: str
    ) -> Dict[str, float]:
        """
        Ajustar probabilidades por lesiones/alineaciones.

        Args:
            original_probs: {"home": 0.65, "draw": 0.20, "away": 0.15}
            home_team, away_team: nombres de equipos

        Returns:
            Probabilidades ajustadas
        """
        comparison = self.compare_lineups(home_team, away_team)

        home_impact = comparison["home_impact_loss_pct"] / 100
        away_impact = comparison["away_impact_loss_pct"] / 100

        # Ajuste: cada 10% de lesiones = -5% en probabilidad de ganar
        home_adjustment = 1 - (home_impact * 0.5)
        away_adjustment = 1 - (away_impact * 0.5)

        adjusted = {
            "home": original_probs.get("home", 0.5) * home_adjustment,
            "away": original_probs.get("away", 0.3) * away_adjustment,
            "draw": original_probs.get("draw", 0.2),  # Menos afectado
        }

        # Normalizar
        total = sum(adjusted.values())
        adjusted = {k: v/total for k, v in adjusted.items()}

        return adjusted


def main():
    """Demostración del analizador de jugadores."""
    print("\n" + "="*110)
    print("ANALISIS DE JUGADORES Y ALINEACIONES - MÉXICO vs TIGRES")
    print("="*110)

    analyzer = PlayerAnalyzer()

    # 1. Analizar disponibilidad
    print("\n[1] ESTADO DE LESIONES Y DISPONIBILIDAD")
    print("-" * 110)

    for team in ["Mexico", "Tigres"]:
        analysis = analyzer.analyze_available_players(team)
        injuries = analyzer.get_injuries(team)

        print(f"\n{team.upper()}:")
        print(f"  Jugadores clave disponibles: {analysis['available_key_players']}/{analysis['total_key_players']}")
        print(f"  Impacto de lesiones: {analysis['missing_impact_pct']:.1f}%")
        print(f"  Fortaleza ajustada: {analysis['squad_strength_adjusted']:.2f}")

        if analysis['critical_absences']:
            print(f"  BAJA CRÍTICA: {', '.join(analysis['critical_absences'])}")

        for q in analysis['questionable_players']:
            print(f"  DUDOSO: {q['name']} ({q['details']}) - {q['availability']*100:.0f}% chance jugar")

    # 2. Alineación probable
    print(f"\n[2] ALINEACIÓN PROBABLE")
    print("-" * 110)

    mexico_lineup = analyzer.get_probable_lineup("Mexico")
    tigres_lineup = analyzer.get_probable_lineup("Tigres")

    print(f"\nMexico: {len(mexico_lineup)} jugadores clave disponibles")
    for p in mexico_lineup:
        print(f"  > {p}")

    print(f"\nTigres: {len(tigres_lineup)} jugadores clave disponibles")
    for p in tigres_lineup:
        print(f"  > {p}")

    # 3. Comparación
    print(f"\n[3] COMPARACIÓN DE ALINEACIONES")
    print("-" * 110)

    comparison = analyzer.compare_lineups("Mexico", "Tigres")

    print(f"\nMexico:")
    print(f"  Impacto de lesiones: {comparison['home_impact_loss_pct']:.1f}%")
    print(f"  Jugadores disponibles: {comparison['home_analysis']['available_key_players']}")

    print(f"\nTigres:")
    print(f"  Impacto de lesiones: {comparison['away_impact_loss_pct']:.1f}%")
    print(f"  Jugadores disponibles: {comparison['away_analysis']['available_key_players']}")

    print(f"\nANALISIS: {comparison['analysis']}")

    # 4. Impacto en predicción
    print(f"\n[4] IMPACTO EN PROBABILIDADES")
    print("-" * 110)

    original = {"home": 0.907, "draw": 0.093, "away": 0.000}
    adjusted = analyzer.adjust_prediction(original, "Mexico", "Tigres")

    print(f"\nPredicciones ANTES de considerar lesiones:")
    print(f"  Mexico:  {original['home']:.1%}")
    print(f"  Empate:  {original['draw']:.1%}")
    print(f"  Tigres:  {original['away']:.1%}")

    print(f"\nPredicciones DESPUÉS de considerar lesiones:")
    home_change = adjusted['home'] - original['home']
    away_change = adjusted['away'] - original['away']
    home_str = "(sin cambio)" if abs(home_change) < 0.01 else f"({home_change:+.1%})"
    away_str = "(sin cambio)" if abs(away_change) < 0.01 else f"({away_change:+.1%})"

    print(f"  Mexico:  {adjusted['home']:.1%}  {home_str}")
    print(f"  Empate:  {adjusted['draw']:.1%}")
    print(f"  Tigres:  {adjusted['away']:.1%}  {away_str}")

    if comparison['away_impact_loss_pct'] > 10:
        print(f"\n[ALERTA] Tigres muy debilitado: {', '.join(comparison['critical_issues']['away'])}")
        print(f"         Reduce chances de sorpresa significativamente")

    print("\n" + "="*110 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
