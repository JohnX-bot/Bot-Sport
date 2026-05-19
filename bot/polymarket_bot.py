#!/usr/bin/env python3
"""
Bot Principal - Polymarket Trading

Orquesta:
1. Búsqueda de mercados en Polymarket
2. Predicciones con modelos ML
3. Análisis de lesiones/alineaciones
4. Cálculo de edges
5. Ejecución de trades (paper mode)
"""

import sys
import os
import json
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.polymarket_api_client import PolymarketAPIClient
from models.predictor_logistic import LogisticMatchPredictor
from data.player_analyzer import PlayerAnalyzer
from models.kelly_calculator import KellyCalculator


class PolymarketBot:
    """Bot de trading para Polymarket."""

    def __init__(
        self,
        sport: str = "mex",
        bankroll: float = 100.0,
        paper_mode: bool = True,
        min_edge: float = 0.03
    ):
        """
        Inicializar bot.

        Args:
            sport: Deporte (pl, mex, etc)
            bankroll: Capital inicial
            paper_mode: Simulación sin dinero real
            min_edge: Edge mínimo para apostar
        """
        self.sport = sport
        self.bankroll = bankroll
        self.current_bankroll = bankroll
        self.paper_mode = paper_mode
        self.min_edge = min_edge

        # Componentes
        self.api_client = PolymarketAPIClient()
        self.player_analyzer = PlayerAnalyzer()
        self.kelly = KellyCalculator(kelly_fraction=0.20)

        # Cargar modelo según deporte
        model_path = f"models/logistic_{sport}_2025-26.pkl"
        self.predictor = LogisticMatchPredictor(model_path)

        # Historial de trades
        self.trades = []

        print(f"[BOT] Iniciado en {'PAPER MODE' if paper_mode else 'LIVE MODE'}")
        print(f"[BOT] Bankroll: ${bankroll:.2f}")
        print(f"[BOT] Min edge: {min_edge:.1%}")

    def find_opportunities(self, search_term: str = "football") -> List[Dict]:
        """
        Buscar oportunidades de arbitraje en Polymarket.

        Returns:
            Lista de {
                'market': {...},
                'prediction': {'home': 0.65, 'draw': 0.20, 'away': 0.15},
                'edge': {'outcome': 'home', 'value': 0.08},
                'recommendation': 'APOSTAR'
            }
        """
        print(f"\n[BOT] Buscando oportunidades en {self.sport.upper()}...")

        markets = self.api_client.search_markets(search_term)
        opportunities = []

        for market in markets[:10]:  # Limitar a 10 para no saturar
            try:
                # Extraer información
                if not isinstance(market, dict):
                    continue

                market_id = market.get("id", "")
                title = market.get("title", "")
                outcomes = market.get("outcomes", [])
                prices = market.get("prices", [])

                if len(prices) < 3 or len(outcomes) < 3:
                    continue

                # Intentar hacer predicción
                # (En real, necesitaríamos datos del partido)
                print(f"  > {title}: precios {[f'{p:.2f}' for p in prices[:3]]}")

                # Simular predicción para demo
                prediction = {
                    "home": 0.50 + (0.2 * (1 - prices[0])),
                    "draw": 0.25 + (0.2 * (1 - prices[1])),
                    "away": 0.50 + (0.2 * (1 - prices[2]))
                }

                # Calcular edges
                edges = {}
                for i, outcome in enumerate(["home", "draw", "away"]):
                    edge = prediction[outcome] - prices[i]
                    edges[outcome] = edge

                best_outcome = max(edges, key=edges.get)
                best_edge = edges[best_outcome]

                if best_edge > self.min_edge:
                    opportunities.append({
                        "market_id": market_id,
                        "title": title,
                        "outcomes": outcomes,
                        "prices": prices,
                        "prediction": prediction,
                        "edges": edges,
                        "best_edge": {
                            "outcome": best_outcome,
                            "value": best_edge
                        },
                        "recommendation": "APOSTAR" if best_edge > 0.05 else "CONSIDERAR"
                    })

            except Exception as e:
                print(f"  [SKIP] Error procesando {title}: {e}")
                continue

        print(f"[OK] {len(opportunities)} oportunidades encontradas")
        return opportunities

    def execute_trade(
        self,
        market_id: str,
        outcome: str,
        probability: float,
        market_price: float,
        edge: float
    ) -> Dict:
        """
        Ejecutar un trade (paper mode).

        Returns:
            {
                'status': 'EXECUTED',
                'outcome': 'home',
                'stake': 10.5,
                'price': 0.52,
                'potential_return': 20.2,
                'timestamp': '2026-05-09T14:30:00'
            }
        """
        # Calcular stake con Kelly
        stake = self.kelly.calculate_single_bet(
            p=probability,
            odds=market_price,
            bankroll=self.current_bankroll,
            min_bet=1.0,
            max_bet=50.0
        )

        if stake < 1.0:
            return {"status": "SKIPPED", "reason": "Stake muy bajo"}

        # Calcular retorno potencial
        if stake > 0:
            potential_return = (stake / market_price) if market_price > 0 else 0
        else:
            potential_return = 0

        trade = {
            "timestamp": datetime.now().isoformat(),
            "market_id": market_id,
            "outcome": outcome,
            "stake": stake,
            "price": market_price,
            "probability": probability,
            "edge": edge,
            "potential_return": potential_return,
            "status": "PENDING"  # En real sería EXECUTED después de confirmar
        }

        self.trades.append(trade)
        self.current_bankroll -= stake

        return {
            "status": "EXECUTED",
            "stake": stake,
            "price": market_price,
            "outcome": outcome,
            "potential_return": potential_return,
            "timestamp": trade["timestamp"]
        }

    def print_summary(self):
        """Imprimir resumen del bot."""
        print(f"\n{'='*100}")
        print("RESUMEN DE OPERACIONES")
        print(f"{'='*100}")

        print(f"\nCapital inicial:      ${self.bankroll:.2f}")
        print(f"Capital actual:       ${self.current_bankroll:.2f}")
        print(f"Total apostado:       ${self.bankroll - self.current_bankroll:.2f}")
        print(f"Operaciones:          {len(self.trades)}")

        if self.trades:
            print(f"\n{'Resultado':<12} {'Outcome':<10} {'Stake':<10} {'Precio':<10} {'Edge':<10}")
            print("-" * 100)

            for trade in self.trades[-10:]:  # Últimas 10
                print(
                    f"{trade['status']:<12} "
                    f"{trade['outcome']:<10} "
                    f"${trade['stake']:<9.2f} "
                    f"{trade['price']:<10.2f} "
                    f"{trade['edge']:+<10.1%}"
                )


def main():
    """Ejecutar bot."""
    print("\n" + "="*100)
    print("POLYMARKET BOT - MODO PAPER")
    print("="*100)

    # Inicializar bot
    bot = PolymarketBot(
        sport="mex",
        bankroll=100.0,
        paper_mode=True,
        min_edge=0.03
    )

    # Buscar oportunidades
    opportunities = bot.find_opportunities("football mexico")

    if not opportunities:
        print("\n[INFO] Sin oportunidades encontradas con edge suficiente")
        print("[INFO] Nota: Polymarket requiere autenticación para datos en tiempo real")
        print("       En paper mode, usaremos data simulada...")

        # Demo trade simulado
        print("\n[DEMO] Simulando trade para Mexico vs Tigres...")
        trade = bot.execute_trade(
            market_id="demo-001",
            outcome="home",
            probability=0.907,
            market_price=0.52,
            edge=0.387
        )

        print(f"[OK] Trade ejecutado:")
        print(f"  Outcome: Mexico")
        print(f"  Stake: ${trade['stake']:.2f}")
        print(f"  Precio: {trade['price']:.2f}")
        print(f"  Retorno potencial: ${trade['potential_return']:.2f}")

    else:
        # Ejecutar trades en oportunidades encontradas
        print(f"\n[BOT] Ejecutando trades en {len(opportunities)} oportunidades...")

        for opp in opportunities[:5]:  # Máximo 5 trades
            if opp["best_edge"]["value"] > bot.min_edge:
                trade = bot.execute_trade(
                    market_id=opp["market_id"],
                    outcome=opp["best_edge"]["outcome"],
                    probability=opp["prediction"][opp["best_edge"]["outcome"]],
                    market_price=opp["prices"][
                        ["home", "draw", "away"].index(opp["best_edge"]["outcome"])
                    ],
                    edge=opp["best_edge"]["value"]
                )

                print(f"[TRADE] {opp['title']}")
                print(f"        {opp['best_edge']['outcome'].upper()} @ {opp['best_edge']['value']:+.1%} edge")

    # Mostrar resumen
    bot.print_summary()

    print("\n" + "="*100 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
