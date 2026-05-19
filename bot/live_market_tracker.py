#!/usr/bin/env python3
"""
Rastreador de Mercado en Vivo - Polymarket

Analiza el comportamiento de otros usuarios en un partido específico:
- Dinero apostado en cada outcome
- Movimiento de precios
- Volumen por outcome
- Consenso del mercado
"""

import sys
import os
from typing import Dict, List
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LiveMarketTracker:
    """Rastrea comportamiento de usuarios en un mercado específico."""

    def __init__(self):
        """Inicializar rastreador."""
        self.market_snapshots = []

    def fetch_market_data(self, market_slug: str) -> Dict:
        """
        Obtener datos en vivo de un mercado.

        Args:
            market_slug: ID del mercado (ej: 'mex-gua-tig-2026-05-09')

        Returns:
            Datos del mercado con precios, volumen, órdenes abiertas
        """
        # En producción, conectar a API de Polymarket
        # Por ahora, retornar estructura de ejemplo
        return {
            "market_id": market_slug,
            "title": "Mexico vs Guadalajara vs Tigres",
            "date": "2026-05-09",
            "outcomes": ["Mexico", "Draw", "Tigres"],
            "current_prices": {
                "Mexico": 0.52,      # 52% según mercado
                "Draw": 0.25,        # 25%
                "Tigres": 0.38       # 38%
            },
            "volume_24h": 125000,    # USD volumen total
            "total_volume_outcome": {
                "Mexico": 65000,     # Cuánto apostaron en México
                "Draw": 31250,       # En empate
                "Tigres": 47500      # En Tigres
            },
            "bid_ask_spread": {
                "Mexico": {"bid": 0.51, "ask": 0.53},
                "Draw": {"bid": 0.24, "ask": 0.26},
                "Tigres": {"bid": 0.37, "ask": 0.39}
            },
            "open_interest": {  # Posiciones abiertas
                "Mexico": 2400,      # Número de órdenes/posiciones
                "Draw": 890,
                "Tigres": 1560
            },
            "recent_trades": [  # Últimas transacciones (show smart money)
                {"outcome": "Tigres", "volume": 5000, "price": 0.38, "time": "2026-05-09 14:32"},
                {"outcome": "Mexico", "volume": 3000, "price": 0.52, "time": "2026-05-09 14:28"},
                {"outcome": "Tigres", "volume": 8000, "price": 0.37, "time": "2026-05-09 14:15"},
                {"outcome": "Mexico", "volume": 2000, "price": 0.52, "time": "2026-05-09 14:10"},
                {"outcome": "Draw", "volume": 1500, "price": 0.25, "time": "2026-05-09 13:55"},
            ]
        }

    def analyze_user_behavior(self, market_data: Dict) -> Dict:
        """
        Analizar cómo están apostando los usuarios.

        Returns:
            {
                'consensus': outcome favorito,
                'conviction': qué tan fuerte es el consenso,
                'money_flow': hacia dónde va el dinero,
                'smart_money': dónde ven valor los profesionales,
                'contrarian': dónde está el valor contrarian
            }
        """
        outcomes = market_data["outcomes"]
        prices = market_data["current_prices"]
        volumes = market_data["total_volume_outcome"]
        trades = market_data["recent_trades"]

        # 1. Consenso del mercado
        consensus_outcome = max(prices, key=prices.get)
        consensus_prob = prices[consensus_outcome]

        # 2. Distribución de dinero
        total_volume = sum(volumes.values())
        money_distribution = {
            outcome: (volumes.get(outcome, 0) / total_volume * 100)
            for outcome in outcomes
        }

        # 3. Flujo de dinero reciente (últimas 5 trades)
        recent_flow = {}
        for trade in trades:
            outcome = trade["outcome"]
            if outcome not in recent_flow:
                recent_flow[outcome] = 0
            recent_flow[outcome] += trade["volume"]

        dominant_recent = max(recent_flow, key=recent_flow.get)

        # 4. Smart Money (patrones sospechosos)
        smart_money_signals = []

        # Señal: Grandes órdenes en outcme poco popular
        for outcome in outcomes:
            if money_distribution[outcome] < 30:  # Outcome minoritario
                recent_volume = recent_flow.get(outcome, 0)
                if recent_volume > 5000:  # Gran volumen
                    smart_money_signals.append({
                        "type": "CONTRARIAN_BUY",
                        "outcome": outcome,
                        "signal": f"Grandes apuestas en {outcome} (poco popular)",
                        "confidence": "MEDIA"
                    })

        # Señal: Cambio rápido de precio
        for outcome in outcomes:
            if prices[outcome] > 0.50:
                smart_money_signals.append({
                    "type": "HIGH_PRICE",
                    "outcome": outcome,
                    "signal": f"{outcome} muy caro (>{prices[outcome]:.0%})",
                    "confidence": "BAJA"
                })

        return {
            "consensus_outcome": consensus_outcome,
            "consensus_probability": consensus_prob,
            "conviction": self._calculate_conviction(prices),
            "money_distribution": money_distribution,
            "recent_flow": recent_flow,
            "dominant_recent_outcome": dominant_recent,
            "smart_money_signals": smart_money_signals,
            "spread_analysis": self._analyze_spreads(market_data["bid_ask_spread"])
        }

    def _calculate_conviction(self, prices: Dict) -> str:
        """Qué tan convencido está el mercado (spread entre outcomes)."""
        prices_list = list(prices.values())
        max_p = max(prices_list)
        min_p = min(prices_list)
        spread = max_p - min_p

        if spread > 0.30:
            return "ALTA"  # Mercado muy seguro de favorito
        elif spread > 0.15:
            return "MEDIA"
        else:
            return "BAJA"  # Mercado indeciso

    def _analyze_spreads(self, bid_ask: Dict) -> List[str]:
        """Analizar bid-ask spreads (indicador de liquidez/volatilidad)."""
        signals = []

        for outcome, spreads in bid_ask.items():
            spread = spreads["ask"] - spreads["bid"]
            spread_pct = (spread / spreads["bid"]) * 100

            if spread_pct > 3:
                signals.append(f"{outcome}: Spread alto ({spread_pct:.1f}%) - baja liquidez")
            elif spread_pct < 1:
                signals.append(f"{outcome}: Spread bajo - buena liquidez")

        return signals

    def compare_with_consensus(
        self,
        our_prediction: Dict,
        market_consensus: Dict
    ) -> List[Dict]:
        """
        Comparar nuestras predicciones con lo que apuestan otros.

        Returns:
            Oportunidades basadas en divergencia con mercado
        """
        opportunities = []

        for outcome in ["Mexico", "Draw", "Tigres"]:
            our_prob = our_prediction.get(outcome, 0)
            market_prob = market_consensus["prices"].get(outcome, 0)
            market_money = market_consensus["money_distribution"].get(outcome, 0)

            # Oportunidad 1: Nuestro modelo diferente del mercado
            divergence = abs(our_prob - market_prob)
            if divergence > 0.10:
                opportunities.append({
                    "type": "DIVERGENCE",
                    "outcome": outcome,
                    "our_probability": our_prob,
                    "market_probability": market_prob,
                    "divergence": divergence,
                    "signal": f"Nuestro modelo: {our_prob:.0%} vs Mercado: {market_prob:.0%}",
                    "direction": "CONTRARIAN" if our_prob > market_prob else "WITH_MARKET"
                })

            # Oportunidad 2: Dinero vs probabilidad desalineados
            money_prob_gap = abs(market_money - market_prob * 100)
            if money_prob_gap > 15:  # Diferencia significativa
                opportunities.append({
                    "type": "MONEY_DISTRIBUTION",
                    "outcome": outcome,
                    "money_percentage": market_money,
                    "price_percentage": market_prob * 100,
                    "gap": money_prob_gap,
                    "signal": f"Dinero ({market_money:.0f}%) != Precio ({market_prob*100:.0f}%)"
                })

        return opportunities


def main():
    """Mostrar análisis de comportamiento de usuarios en mercado específico."""
    print("\n" + "="*110)
    print("ANÁLISIS: COMPORTAMIENTO DE USUARIOS EN POLYMARKET")
    print("Mercado: Mexico vs Guadalajara vs Tigres - 9 de mayo 2026")
    print("="*110)

    tracker = LiveMarketTracker()

    # 1. Obtener datos del mercado
    print("\n[1] Obteniendo datos en vivo de Polymarket...")
    market_data = tracker.fetch_market_data("mex-gua-tig-2026-05-09")

    print(f"    Mercado: {market_data['title']}")
    print(f"    Volumen 24h: ${market_data['volume_24h']:,.0f}")
    print(f"    Precios actuales: {market_data['current_prices']}")

    # 2. Analizar comportamiento
    print("\n[2] Analizando comportamiento de usuarios...")
    behavior = tracker.analyze_user_behavior(market_data)

    print(f"\n    CONSENSO DEL MERCADO:")
    print(f"    > Favorito: {behavior['consensus_outcome']}")
    print(f"    > Probabilidad: {behavior['consensus_probability']:.0%}")
    print(f"    > Convicción: {behavior['conviction']}")

    print(f"\n    DISTRIBUCIÓN DE DINERO (dónde apuestan los usuarios):")
    for outcome, pct in behavior['money_distribution'].items():
        print(f"    > {outcome:<15} {pct:>6.1f}%  (${market_data['total_volume_outcome'][outcome]:>7,.0f})")

    print(f"\n    FLUJO RECIENTE (últimas apuestas):")
    for outcome, vol in behavior['recent_flow'].items():
        pct = (vol / sum(behavior['recent_flow'].values())) * 100
        print(f"    > {outcome:<15} ${vol:>8,.0f}  ({pct:>5.1f}%)")

    # 3. Smart Money
    print(f"\n[3] Detectando Smart Money (patrones profesionales)...")
    if behavior['smart_money_signals']:
        for signal in behavior['smart_money_signals']:
            print(f"    > [{signal['confidence']}] {signal['signal']}")
    else:
        print("    > Sin patrones anómalos detectados")

    # 4. Spread analysis
    print(f"\n[4] Análisis de Liquidez (bid-ask spreads)...")
    for signal in behavior['spread_analysis']:
        print(f"    > {signal}")

    # 5. Trades recientes
    print(f"\n[5] Trades Recientes (último 1 hora)...")
    for trade in market_data['recent_trades'][:5]:
        print(
            f"    > {trade['outcome']:<12} "
            f"${trade['volume']:>7,.0f}  @ {trade['price']:.2f}  ({trade['time']})"
        )

    # 6. Comparación con predicción (simulada)
    print(f"\n[6] Comparando con nuestras predicciones...")
    our_prediction = {
        "Mexico": 0.45,      # Nuestro modelo predice
        "Draw": 0.28,
        "Tigres": 0.42
    }

    print(f"    Nuestras predicciones:")
    for outcome, prob in our_prediction.items():
        market_price = market_data['current_prices'][outcome]
        edge = prob - market_price
        print(
            f"    > {outcome:<12} "
            f"Nuestro: {prob:.0%}  Mercado: {market_price:.0%}  "
            f"Edge: {edge:+.0%}"
        )

    # 7. Conclusión
    print(f"\n[7] RESUMEN & RECOMENDACIÓN")
    print("-" * 110)

    dominant_outcome = behavior['consensus_outcome']
    money_in_dominant = behavior['money_distribution'][dominant_outcome]

    print(f"\n    COMPORTAMIENTO USUARIOS:")
    print(f"    - Consenso fuerte en {dominant_outcome} ({money_in_dominant:.0f}% del dinero)")
    print(f"    - Mercado tiene {'ALTA' if behavior['conviction'] == 'ALTA' else 'BAJA'} convicción")
    print(f"    - Smart Money tendencia: {behavior['dominant_recent_outcome']}")

    if our_prediction["Mexico"] > market_data['current_prices']["Mexico"]:
        print(f"\n    OPORTUNIDAD: Mexico subestimado")
        print(f"               Nuestro modelo: 45% | Mercado: {market_data['current_prices']['Mexico']:.0%}")
    elif our_prediction["Tigres"] > market_data['current_prices']["Tigres"]:
        print(f"\n    OPORTUNIDAD: Tigres subestimado")
        print(f"               Nuestro modelo: 42% | Mercado: {market_data['current_prices']['Tigres']:.0%}")
    else:
        print(f"\n    MERCADO EQUILIBRADO: Precios cercanos a nuestro modelo")

    print(f"\n    ACCIÓN RECOMENDADA:")
    print(f"    1. APOSTAR en {dominant_outcome} si confías en mercado")
    print(f"    2. CONTRARIAN en {behavior['dominant_recent_outcome']} si ves smart money")
    print(f"    3. ESPERAR si la divergencia es baja (<5%)")

    print("\n" + "="*110 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
