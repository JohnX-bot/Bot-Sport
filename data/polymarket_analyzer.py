#!/usr/bin/env python3
"""
Analizador de Mercado Polymarket

Obtiene datos públicos de Polymarket:
- Probabilidades implícitas (precios actuales)
- Volumen de apuestas
- Orden book
- Patrones de Smart Money

Compara con nuestras predicciones para identificar oportunidades.
"""

import json
import os
import sys
from typing import List, Dict, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PolymarketAnalyzer:
    """Analiza datos públicos de Polymarket."""

    # API Base (datos públicos)
    POLYMARKET_API = "https://clob.polymarket.com"

    def __init__(self):
        """Inicializar analizador."""
        self.markets_cache = {}
        self.last_update = None

    def fetch_markets(self, search_term: str = "pl") -> List[Dict]:
        """
        Buscar mercados en Polymarket.

        Args:
            search_term: Término de búsqueda (ej: "pl", "football", "chelsea")

        Returns:
            Lista de mercados encontrados con prices y volumen
        """
        try:
            # Escapar el término de búsqueda
            escaped_term = quote(search_term)
            url = f"{self.POLYMARKET_API}/markets?search={escaped_term}"
            print(f"[API] Buscando mercados: {search_term}")

            # Headers para evitar bloqueos
            req = Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Accept', 'application/json')

            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            if isinstance(data, dict) and 'data' in data:
                markets = data['data']
            else:
                markets = data if isinstance(data, list) else []

            print(f"[OK] {len(markets)} mercados encontrados")
            return markets

        except URLError as e:
            print(f"[ERROR] No se pudo conectar a Polymarket: {e}")
            print(f"[INFO] Polymarket requiere autenticación o está bloqueando requests")
            return []
        except Exception as e:
            print(f"[ERROR] Error parseando datos: {e}")
            return []

    def extract_market_data(self, market: Dict) -> Dict:
        """
        Extraer datos útiles de un mercado.

        Returns:
            {
                'id': market_id,
                'title': 'Chelsea vs Liverpool',
                'description': '',
                'outcomes': ['Chelsea', 'Draw', 'Liverpool'],
                'prices': [0.55, 0.28, 0.35],  # Probabilidades implícitas
                'volume': 50000,  # USD volumen total
                'liquidity': 10000,  # Liquidez disponible
                'end_date': '2026-05-10',
                'created_at': '2026-05-01'
            }
        """
        try:
            return {
                'id': market.get('id'),
                'title': market.get('title', 'Unknown'),
                'outcomes': market.get('outcomes', []),
                'prices': market.get('prices', []),  # Probabilidades implícitas
                'volume': market.get('volume', 0),
                'liquidity': market.get('liquidity', 0),
                'end_date': market.get('endDate', ''),
                'created_at': market.get('createdAt', ''),
                'trading_volume_24h': market.get('tradingVolume24h', 0),
            }
        except Exception as e:
            print(f"[WARN] Error extrayendo datos del mercado: {e}")
            return {}

    def calculate_implied_probabilities(self, prices: List[float]) -> List[float]:
        """
        Convertir precios a probabilidades implícitas.

        En Polymarket:
        - Precio = probabilidad implícita del outcome
        - Los precios de los 3 outcomes no siempre suman 1 (hay spread)

        Normalizamos para que sumen 1.
        """
        if not prices or len(prices) < 3:
            return prices

        total = sum(prices[:3])
        if total == 0:
            return prices

        normalized = [p / total for p in prices[:3]]
        return normalized

    def compare_with_predictions(
        self,
        market_title: str,
        market_prices: List[float],
        our_probabilities: List[float]
    ) -> Dict:
        """
        Comparar nuestras predicciones con el mercado.

        Returns:
            {
                'outcome': 'HOME',  # Dónde hay edge
                'market_price': 0.55,
                'our_prob': 0.62,
                'edge': +0.07,  # Positivo = oportunidad
                'confidence': 'MEDIA'  # BAJA/MEDIA/ALTA
            }
        """
        implied_probs = self.calculate_implied_probabilities(market_prices)

        outcomes = ['HOME', 'DRAW', 'AWAY']
        edges = []

        for i, outcome in enumerate(outcomes):
            market_p = implied_probs[i] if i < len(implied_probs) else 0
            our_p = our_probabilities[i] if i < len(our_probabilities) else 0
            edge = our_p - market_p

            edges.append({
                'outcome': outcome,
                'market_price': market_p,
                'our_prob': our_p,
                'edge': edge,
                'confidence': self._rate_confidence(edge)
            })

        # Retornar el edge más fuerte
        best_edge = max(edges, key=lambda x: x['edge'])
        return best_edge

    def _rate_confidence(self, edge: float) -> str:
        """Calificar confianza del edge."""
        if abs(edge) < 0.02:
            return "BAJA"
        elif abs(edge) < 0.05:
            return "MEDIA"
        else:
            return "ALTA"

    def detect_smart_money(self, markets: List[Dict]) -> List[Dict]:
        """
        Detectar posiciones de Smart Money.

        Señales:
        - Alto volumen en dirección minoritaria (contrarian)
        - Cambios rápidos de precio
        - Grandes límites de órdenes
        """
        smart_money_trades = []

        for market in markets:
            data = self.extract_market_data(market)
            if not data.get('prices'):
                continue

            prices = data['prices'][:3]

            # Detectar: precio muy desviado vs volumen
            if len(prices) == 3 and data.get('volume', 0) > 1000:
                # Si hay mucho volumen en el outcome de menor precio
                min_price_idx = prices.index(min(prices))
                min_price = min(prices)

                if min_price < 0.30 and data['volume'] > 5000:
                    smart_money_trades.append({
                        'market': data['title'],
                        'signal': f"Alto volumen en outcome bajista (p={min_price:.2f})",
                        'volume': data['volume'],
                        'action': 'WATCH'
                    })

        return smart_money_trades

    def get_market_consensus(self, markets: List[Dict]) -> Dict:
        """
        Obtener consenso del mercado (hacia dónde apuesta la mayoría).

        Returns:
            Resumen de direcciones dominantes por deporte/liga
        """
        consensus = {}

        for market in markets:
            data = self.extract_market_data(market)
            if not data.get('prices') or not data.get('volume'):
                continue

            prices = data['prices'][:3]
            volume = data['volume']

            # Identificar outcome con mayor precio (favorito)
            max_price_idx = prices.index(max(prices))
            outcome_names = ['HOME', 'DRAW', 'AWAY']
            favorite = outcome_names[max_price_idx]

            # Resumen rápido
            market_key = data['title'][:40]  # Truncar título
            consensus[market_key] = {
                'favorite': favorite,
                'probability': max(prices),
                'volume_usd': volume,
            }

        return consensus


def main():
    """Test del analizador."""
    print("\n" + "="*80)
    print("POLYMARKET ANALYZER - DATOS PÚBLICOS")
    print("="*80)

    analyzer = PolymarketAnalyzer()

    # 1. Buscar mercados de PL
    print("\n[1] Buscando mercados de Premier League...")
    markets = analyzer.fetch_markets("pl football")

    if not markets:
        print("[WARN] No se encontraron mercados. Intentando con término alternativo...")
        markets = analyzer.fetch_markets("football")

    if not markets:
        print("[INFO] No hay datos disponibles de API pública.")
        print("\nPróximos pasos:")
        print("1. Configurar credenciales de Polymarket (POLYMARKET_KEY en .env)")
        print("2. O usar snapshot histórico de precios")
        return 0

    # 2. Extraer datos
    print(f"\n[2] Analizando {len(markets[:5])} mercados principales...")
    print("-" * 80)

    for market in markets[:5]:
        data = analyzer.extract_market_data(market)
        if data:
            print(f"\nMercado: {data['title'][:50]}")
            print(f"  Outcomes: {data['outcomes']}")
            print(f"  Precios (probas): {[f'{p:.2f}' for p in data['prices'][:3]]}")
            print(f"  Volumen: ${data['volume']:,.0f}")
            print(f"  Vol 24h: ${data['trading_volume_24h']:,.0f}")

    # 3. Detectar Smart Money
    print(f"\n[3] Detectando Smart Money...")
    smart_trades = analyzer.detect_smart_money(markets[:20])

    if smart_trades:
        for trade in smart_trades[:5]:
            print(f"  > {trade['market']}: {trade['signal']}")
    else:
        print("  No se detectaron movimientos sospechosos")

    # 4. Consenso del mercado
    print(f"\n[4] Consenso del mercado (Favoritos)...")
    consensus = analyzer.get_market_consensus(markets[:10])
    for market, data in list(consensus.items())[:5]:
        print(f"  {market:<45} -> {data['favorite']} ({data['probability']:.1%})")

    print("\n" + "="*80)
    print("Para datos en tiempo real:")
    print("  1. API de Polymarket necesita credenciales")
    print("  2. O usar websocket para stream de precios")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
