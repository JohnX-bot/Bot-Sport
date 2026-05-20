#!/usr/bin/env python3
"""
Test Script: Guadalajara vs Tigres UANL

Demonstrates the bot correctly analyzing the match with:
- Correct team rosters (Guadalajara, not Mexico)
- Player injury data
- Model predictions
- Edge calculations
"""


import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.player_analyzer import PlayerAnalyzer
from models.kelly_calculator import KellyCalculator
import pickle


def test_guadalajara_vs_tigres():
    """Test analysis of Guadalajara vs Tigres UANL."""

    print("\n" + "="*70)
    print("TEST: Guadalajara vs Tigres UANL (9 mayo 2026)")
    print("="*70)

    # Initialize components
    analyzer = PlayerAnalyzer()
    kelly = KellyCalculator(kelly_fraction=0.20)

    # Load trained model
    model_path = "models/logistic_mex_2025-26.pkl"
    scaler_path = "models/logistic_mex_2025-26_scaler.pkl"

    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)

    print("\n[EQUIPO] Análisis de Plantillas")
    print("-" * 70)

    # Guadalajara analysis
    gdl_analysis = analyzer.analyze_available_players("Guadalajara")
    print("\nGuadalajara:")
    print(f"  Jugadores clave disponibles: {gdl_analysis['available_key_players']}/{gdl_analysis['total_key_players']}")
    print(f"  Fortaleza base: {gdl_analysis['squad_strength_base']:.3f}")
    print(f"  Fortaleza ajustada: {gdl_analysis['squad_strength_adjusted']:.3f}")
    print(f"  Impacto lesiones: {gdl_analysis['missing_impact_pct']:.1f}%")
    if gdl_analysis['critical_absences']:
        print(f"  Bajas críticas: {', '.join(gdl_analysis['critical_absences'])}")
    else:
        print(f"  Bajas críticas: Ninguna")

    # Tigres analysis
    tig_analysis = analyzer.analyze_available_players("Tigres")
    print("\nTigres:")
    print(f"  Jugadores clave disponibles: {tig_analysis['available_key_players']}/{tig_analysis['total_key_players']}")
    print(f"  Fortaleza base: {tig_analysis['squad_strength_base']:.3f}")
    print(f"  Fortaleza ajustada: {tig_analysis['squad_strength_adjusted']:.3f}")
    print(f"  Impacto lesiones: {tig_analysis['missing_impact_pct']:.1f}%")
    if tig_analysis['critical_absences']:
        print(f"  Bajas críticas: {', '.join(tig_analysis['critical_absences'])}")
    if tig_analysis['questionable_players']:
        for qp in tig_analysis['questionable_players']:
            prob = qp['availability'] * 100
            print(f"  Dudoso: {qp['name']} ({prob:.0f}% probabilidad de jugar)")

    # Model predictions (simulated for demonstration)
    print("\n[PREDICCIÓN] Modelo Logístico (Liga Mexicana)")
    print("-" * 70)

    # Use base strengths as simplified features
    # In real usage, would use full feature set
    home_strength = gdl_analysis['squad_strength_adjusted']
    away_strength = tig_analysis['squad_strength_adjusted']

    # Simplified prediction (actual model uses 30+ features)
    total_strength = home_strength + away_strength
    p_home = home_strength / total_strength * 0.95 + 0.02  # Ventaja de casa
    p_away = away_strength / total_strength * 0.93
    p_draw = 1 - p_home - p_away

    print(f"\nGuadalajara (Local): {p_home:6.1%}")
    print(f"Empate:              {p_draw:6.1%}")
    print(f"Tigres (Visitante):  {p_away:6.1%}")

    # Polymarket prices (example from market)
    market_prices = {
        "home": 0.44,    # Guadalajara
        "draw": 0.30,    # Empate
        "away": 0.27     # Tigres
    }

    print("\n[MERCADO] Precios Polymarket (simulados)")
    print("-" * 70)
    print(f"Guadalajara: {market_prices['home']:.2f}")
    print(f"Empate:      {market_prices['draw']:.2f}")
    print(f"Tigres:      {market_prices['away']:.2f}")

    # Edge calculation
    print("\n[EDGE] Análisis de Oportunidades")
    print("-" * 70)

    edges = {}
    for outcome in ["home", "draw", "away"]:
        pred_prob = {"home": p_home, "draw": p_draw, "away": p_away}[outcome]
        market_price = market_prices[outcome]
        edge = pred_prob - market_price
        edges[outcome] = edge

    print(f"\nGuadalajara: {p_home:6.1%} - {market_prices['home']:.2f} = {edges['home']:+6.1%}")
    print(f"Empate:      {p_draw:6.1%} - {market_prices['draw']:.2f} = {edges['draw']:+6.1%}")
    print(f"Tigres:      {p_away:6.1%} - {market_prices['away']:.2f} = {edges['away']:+6.1%}")

    # Recommendation
    best_edge_outcome = max(edges, key=edges.get)
    best_edge_value = edges[best_edge_outcome]

    print("\n[RECOMENDACIÓN]")
    print("-" * 70)

    min_edges = {"home": 0.03, "draw": 0.05, "away": 0.03}
    if best_edge_value > min_edges.get(best_edge_outcome, 0.03):
        recommendation = "APOSTAR FUERTE" if best_edge_value > 0.05 else "CONSIDERAR"
        print(f"\nOutcome: {best_edge_outcome.upper()}")
        print(f"Edge: {best_edge_value:+.1%}")
        print(f"Acción: {recommendation}")

        # Kelly sizing
        if best_edge_outcome == "home":
            prob = p_home
        elif best_edge_outcome == "draw":
            prob = p_draw
        else:
            prob = p_away

        stake = kelly.calculate_single_bet(
            p=prob,
            odds=market_prices[best_edge_outcome],
            bankroll=100.0,
            min_bet=1.0,
            max_bet=15.0
        )

        potential_return = stake / market_prices[best_edge_outcome]

        print(f"Bankroll: $100.00")
        print(f"Stake (Kelly 20%): ${stake:.2f}")
        print(f"Retorno potencial: ${potential_return:.2f} si gana")
    else:
        print("\nNo hay edge suficiente. Esperar siguiente oportunidad.")

    print("\n" + "="*70)
    print("TEST COMPLETADO")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_guadalajara_vs_tigres()
