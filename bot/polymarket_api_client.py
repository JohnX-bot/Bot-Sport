#!/usr/bin/env python3
"""
Cliente API de Polymarket

Obtiene datos en tiempo real:
- Mercados disponibles
- Precios actuales (bid/ask)
- Volumen
- Órdenes abiertas
"""

import json
import sys
import os
from typing import List, Dict, Optional
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import URLError
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PolymarketAPIClient:
    """Cliente para conectar con API de Polymarket."""

    # Endpoints públicos (sin autenticación requerida)
    API_BASE = "https://clob.polymarket.com"
    MARKETS_ENDPOINT = "/markets"
    ORDERBOOK_ENDPOINT = "/orderbook"

    def __init__(self, timeout: int = 10):
        """
        Inicializar cliente.

        Args:
            timeout: Timeout para requests (segundos)
        """
        self.timeout = timeout
        self.session_cache = {}
        self.last_error = None

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Hacer request a API de Polymarket.

        Args:
            endpoint: URL relativa (ej: /markets)
            params: Parámetros query

        Returns:
            Respuesta JSON o None si falla
        """
        try:
            url = f"{self.API_BASE}{endpoint}"

            if params:
                query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
                url += f"?{query_string}"

            req = Request(url)
            req.add_header("User-Agent", "PolymarketBot/1.0")
            req.add_header("Accept", "application/json")

            with urlopen(req, timeout=self.timeout) as response:
                data = response.read().decode("utf-8")
                return json.loads(data) if data else None

        except URLError as e:
            self.last_error = f"URLError: {e}"
            print(f"[ERROR] {self.last_error}")
            return None
        except json.JSONDecodeError as e:
            self.last_error = f"JSON Error: {e}"
            print(f"[ERROR] {self.last_error}")
            return None
        except Exception as e:
            self.last_error = str(e)
            print(f"[ERROR] {self.last_error}")
            return None

    def search_markets(self, search_term: str = "football") -> List[Dict]:
        """
        Buscar mercados por término.

        Args:
            search_term: Término de búsqueda (ej: "mexico", "tigres", "football")

        Returns:
            Lista de mercados encontrados
        """
        print(f"[API] Buscando mercados: {search_term}")

        response = self._make_request(self.MARKETS_ENDPOINT, {"search": search_term})

        if not response:
            return []

        # Extraer mercados de respuesta
        markets = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(markets, list):
            markets = [markets] if markets else []

        print(f"[OK] {len(markets)} mercados encontrados")
        return markets

    def get_orderbook(self, market_id: str) -> Dict:
        """
        Obtener orden book (bid/ask) de un mercado.

        Args:
            market_id: ID del mercado

        Returns:
            {
                'bids': [{'price': 0.52, 'size': 1000}, ...],
                'asks': [{'price': 0.53, 'size': 2000}, ...],
                'market_price': 0.525
            }
        """
        response = self._make_request(f"{self.ORDERBOOK_ENDPOINT}/{market_id}")

        if not response:
            return {"bids": [], "asks": [], "market_price": 0.5}

        bids = response.get("bids", [])
        asks = response.get("asks", [])

        # Calcular precio de mercado (midpoint)
        if bids and asks:
            best_bid = float(bids[0]["price"]) if isinstance(bids[0], dict) else float(bids[0])
            best_ask = float(asks[0]["price"]) if isinstance(asks[0], dict) else float(asks[0])
            market_price = (best_bid + best_ask) / 2
        else:
            market_price = 0.5

        return {
            "bids": bids,
            "asks": asks,
            "market_price": market_price,
            "best_bid": bids[0] if bids else None,
            "best_ask": asks[0] if asks else None
        }

    def get_market_data(self, market_id: str) -> Dict:
        """
        Obtener datos completos de un mercado.

        Returns:
            {
                'market_id': 'xxx',
                'title': 'Mexico vs Tigres',
                'outcomes': ['Mexico', 'Draw', 'Tigres'],
                'prices': [0.52, 0.25, 0.38],
                'volume_24h': 125000,
                'liquidity': 50000,
                'orderbook': {...}
            }
        """
        # Obtener datos básicos
        response = self._make_request(f"{self.MARKETS_ENDPOINT}/{market_id}")

        if not response:
            return {}

        # Obtener orden book
        orderbook = self.get_orderbook(market_id)

        return {
            "market_id": market_id,
            "title": response.get("title", "Unknown"),
            "outcomes": response.get("outcomes", []),
            "prices": response.get("prices", []),
            "volume_24h": response.get("volume24h", 0),
            "liquidity": response.get("liquidity", 0),
            "orderbook": orderbook,
            "timestamp": datetime.now().isoformat()
        }

    def find_market_by_name(self, home_team: str, away_team: str) -> Optional[Dict]:
        """
        Buscar mercado específico por nombres de equipos.

        Args:
            home_team: Equipo local (ej: "Mexico")
            away_team: Equipo visitante (ej: "Tigres")

        Returns:
            Datos del mercado o None
        """
        search_term = f"{home_team} {away_team}"
        markets = self.search_markets(search_term)

        if not markets:
            return None

        # Retornar el primer mercado encontrado (mejor match)
        best_match = markets[0]
        return self.get_market_data(best_match.get("id", ""))


def main():
    """Test del cliente."""
    print("\n" + "="*80)
    print("POLYMARKET API CLIENT - TEST")
    print("="*80)

    client = PolymarketAPIClient()

    # 1. Buscar mercados
    print("\n[1] Buscando mercados de futbol...")
    markets = client.search_markets("football mexico")

    if markets:
        print(f"\n[2] Datos del primer mercado:")
        market = markets[0]
        if isinstance(market, dict):
            print(f"  ID: {market.get('id', 'N/A')}")
            print(f"  Titulo: {market.get('title', 'N/A')}")
            print(f"  Outcomes: {market.get('outcomes', [])}")
            print(f"  Precios: {market.get('prices', [])}")
    else:
        print("[INFO] No hay datos disponibles de API pública")
        print("[NOTA] Polymarket requiere autenticación para datos en tiempo real")
        print("       Usar PAPER_MODE con precios simulados para testing")

    print("\n" + "="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
