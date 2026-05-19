#!/usr/bin/env python3
"""
Comparación: Nuestras predicciones vs Mercado Polymarket

Muestra cómo identificar oportunidades comparando:
- Lo que apuesta el mercado (precios/volumen)
- Lo que predice nuestro modelo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predictor_logistic import LogisticMatchPredictor
from data.data_downloader import FootballDataDownloader


class MarketComparison:
    """Compara predicciones del modelo con consenso del mercado."""

    def __init__(self):
        self.predictor = LogisticMatchPredictor("models/logistic_pl_2025-26.pkl")

    def analyze_matchweek(
        self,
        matches: list,
        market_odds: dict = None
    ) -> list:
        """
        Analizar una jornada completa.

        Args:
            matches: Partidos a analizar
            market_odds: Precios del mercado (si no están disponibles, usar estimados)

        Returns:
            Lista de oportunidades ordenadas por edge
        """
        opportunities = []

        # Precios por defecto del mercado (estimados)
        default_odds = {
            "home": 0.48,
            "draw": 0.28,
            "away": 0.36
        }

        if market_odds is None:
            market_odds = {}

        for match in matches:
            # Nuestras predicciones
            p_h, p_d, p_a = self.predictor.predict_match(match, verbose=False)
            nuestras_probs = {"home": p_h, "draw": p_d, "away": p_a}

            # Precios del mercado
            precios_mercado = market_odds.get(
                f"{match['home_team']} vs {match['away_team']}",
                default_odds.copy()
            )

            # Calcular edges
            for outcome in ["home", "draw", "away"]:
                nuestra_prob = nuestras_probs[outcome]
                precio_mercado = precios_mercado[outcome]
                edge = nuestra_prob - precio_mercado

                if edge > 0.02:  # Solo edges positivos significativos
                    opportunities.append({
                        "fecha": match["date"],
                        "partido": f"{match['home_team']} vs {match['away_team']}",
                        "outcome": outcome.upper(),
                        "nuestra_prob": nuestra_prob,
                        "precio_mercado": precio_mercado,
                        "edge": edge,
                        "confianza": self._rate_confidence(edge),
                        "expectativa": nuestra_prob / precio_mercado - 1  # % return esperado
                    })

        # Ordenar por edge
        opportunities.sort(key=lambda x: x["edge"], reverse=True)
        return opportunities

    def _rate_confidence(self, edge: float) -> str:
        """Calificar confianza del edge."""
        if edge < 0.03:
            return "BAJA"
        elif edge < 0.07:
            return "MEDIA"
        else:
            return "ALTA"

    def detect_smart_money_patterns(self, opportunities: list) -> list:
        """
        Detectar patrones que sugieren Smart Money:
        - High edge en outcome poco popular
        - Múltiples edges en mismo partido
        - Precios desviados vs probabilidad real
        """
        patterns = []

        # Agrupar por partido
        matches_edges = {}
        for opp in opportunities:
            partido = opp["partido"]
            if partido not in matches_edges:
                matches_edges[partido] = []
            matches_edges[partido].append(opp)

        # Buscar patrones
        for partido, edges in matches_edges.items():
            # Si hay múltiples edges en el mismo partido
            if len(edges) > 1:
                total_edge = sum(e["edge"] for e in edges)
                patterns.append({
                    "tipo": "MULTIPLE_EDGES",
                    "partido": partido,
                    "edges": len(edges),
                    "total_edge": total_edge,
                    "signal": "Mercado desalineado - arbitraje potencial"
                })

            # Si hay edge muy alto (>10%)
            for edge in edges:
                if edge["edge"] > 0.10:
                    patterns.append({
                        "tipo": "EDGE_ALTO",
                        "partido": edge["partido"],
                        "outcome": edge["outcome"],
                        "edge": edge["edge"],
                        "signal": "Edge extremadamente alto - verificar modelo"
                    })

        return patterns


def main():
    """Mostrar análisis de comparación mercado vs modelo."""
    print("\n" + "="*110)
    print("ANÁLISIS: PREDICCIONES vs MERCADO")
    print("="*110)

    # Cargar datos
    print("\n[1] Descargando datos 2025-26...")
    downloader = FootballDataDownloader()
    csv_path = downloader.download_season("pl", "2025-26")

    if not csv_path:
        print("[ERROR] No se pudo cargar datos")
        return 1

    matches = downloader.parse_csv(csv_path)
    matches = downloader.enrich_matches(matches)
    print(f"[OK] {len(matches)} partidos cargados")

    # Filtrar últimos partidos (los que están disponibles)
    matches = sorted(matches, key=lambda x: x["date"])[-15:]

    # Analizar
    print(f"\n[2] Analizando {len(matches)} partidos...")
    comparator = MarketComparison()
    opportunities = comparator.analyze_matchweek(matches)

    # Mostrar top opportunities
    print(f"\n[3] Top Oportunidades Identificadas ({len(opportunities)} total)")
    print("-" * 110)
    print(f"{'Fecha':<12} {'Partido':<40} {'Outcome':<8} {'Nuestra':<8} {'Mercado':<8} {'Edge':<8} {'Conf':<6}")
    print("-" * 110)

    for opp in opportunities[:20]:
        print(
            f"{opp['fecha']:<12} "
            f"{opp['partido']:<40} "
            f"{opp['outcome']:<8} "
            f"{opp['nuestra_prob']:<8.2f} "
            f"{opp['precio_mercado']:<8.2f} "
            f"{opp['edge']:+<8.3f} "
            f"{opp['confianza']:<6}"
        )

    # Detectar patrones
    print(f"\n[4] Patrones de Smart Money")
    print("-" * 110)
    patterns = comparator.detect_smart_money_patterns(opportunities)

    if patterns:
        for pattern in patterns[:10]:
            if pattern["tipo"] == "MULTIPLE_EDGES":
                print(f"MÚLTIPLES EDGES: {pattern['partido']}")
                print(f"  -> {pattern['edges']} edges encontrados, edge total: {pattern['total_edge']:+.3f}")
            elif pattern["tipo"] == "EDGE_ALTO":
                print(f"EDGE EXTREMO: {pattern['partido']} - {pattern['outcome']}")
                print(f"  -> Edge: {pattern['edge']:+.3f} (verificar modelo)")
    else:
        print("No se detectaron patrones anómalos")

    # Resumen
    print(f"\n[5] Resumen de Estrategia")
    print("-" * 110)

    if opportunities:
        high_conf = [o for o in opportunities if o["confianza"] == "ALTA"]
        med_conf = [o for o in opportunities if o["confianza"] == "MEDIA"]

        print(f"Total oportunidades: {len(opportunities)}")
        print(f"  - Confianza ALTA:   {len(high_conf)} ({100*len(high_conf)/len(opportunities):.0f}%)")
        print(f"  - Confianza MEDIA:  {len(med_conf)} ({100*len(med_conf)/len(opportunities):.0f}%)")

        avg_edge = sum(o["edge"] for o in opportunities) / len(opportunities)
        avg_expect = sum(o["expectativa"] for o in opportunities) / len(opportunities)

        print(f"\nPromedio edge: {avg_edge:+.3f}")
        print(f"Expectativa de retorno: {avg_expect:+.1%}")

        # ROI estimado
        if avg_edge > 0 and len(opportunities) > 10:
            estimated_roi = (avg_edge * 100) * (len(opportunities) / 100)
            print(f"ROI estimado (si todas resultan): {estimated_roi:+.1f}%")
    else:
        print("No hay oportunidades con edge positivo en el período")

    print("\n" + "="*110)
    print("RECOMENDACIÓN:")
    print("  1. Estos edges son TEÓRICOS (vs precios estimados)")
    print("  2. Con precios REALES de Polymarket pueden cambiar significativamente")
    print("  3. Necesitamos integrar API de Polymarket para precios actuales")
    print("="*110 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
