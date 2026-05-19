#!/usr/bin/env python3
"""
Improved Backtest Runner

Usa datos REALES descargados de football-data.co.uk en lugar de mock.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.sport_config import get_sport_config
from data.data_downloader import FootballDataDownloader
from models.predictor_heuristic import FootballPredictor
from models.predictor_logistic import LogisticMatchPredictor
from models.kelly_calculator import KellyCalculator


class ImprovedBacktestRunner:
    """Backtest con datos REALES."""

    def __init__(
        self,
        sport_code: str = "pl",
        predictor_type: str = "logistic",
        bankroll: float = 100.0,
    ):
        self.sport_config = get_sport_config(sport_code)
        self.predictor_type = predictor_type
        self.bankroll = bankroll
        self.downloader = FootballDataDownloader()

        # Initialize predictor
        if predictor_type == "logistic":
            self.predictor = LogisticMatchPredictor()
        else:
            self.predictor = FootballPredictor()

        self.kelly = KellyCalculator(kelly_fraction=self.sport_config.kelly_fraction)

        # Stats
        self.stats = {
            "total_matches": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "brier_sum": 0.0,
            "brier_n": 0,
            "current_bankroll": bankroll,
        }

    def run(self, sport: str, season: str) -> Dict:
        """
        Backtest en datos REALES descargados.

        Args:
            sport: Código de deporte (pl, laliga, etc.)
            season: Temporada (ej: "2023-24")

        Returns:
            Backtest report con estadísticas
        """
        print(f"[BACKTEST] Descargando datos reales {sport.upper()} {season}...")

        # Descargar y parsear datos REALES
        csv_path = self.downloader.download_season(sport, season)
        if not csv_path:
            print("[ERROR] No se pudo descargar datos")
            return {}

        matches = self.downloader.parse_csv(csv_path)
        if not matches:
            print("[ERROR] No se pudo parsear datos")
            return {}

        # Enriquecer con estadísticas
        matches = self.downloader.enrich_matches(matches)

        print(f"[BACKTEST] Iniciando simulación en {len(matches)} partidos...")
        print(f"  Deporte: {self.sport_config.name}")
        print(f"  Predictor: {self.predictor_type}")
        print(f"  Bankroll inicial: ${self.bankroll:.2f}")
        print(f"  Min edges: {self.sport_config.min_edges}\n")

        start_time = time.time()

        for i, match in enumerate(matches):
            self.stats["total_matches"] += 1

            date = match.get("date", "")
            home = match.get("home_team", "")
            away = match.get("away_team", "")

            # Predicción con datos REALES
            p_home, p_draw, p_away = self.predictor.predict_match(match, verbose=False)

            # Mock odds (en producción, de Polymarket)
            odds = {
                "home": 0.55,
                "draw": 0.28,
                "away": 0.35,
            }

            # Calcular edges
            edge_home = p_home - odds["home"]
            edge_draw = p_draw - odds["draw"]
            edge_away = p_away - odds["away"]

            edges = {"home": edge_home, "draw": edge_draw, "away": edge_away}
            best_dir = max(edges, key=edges.get)
            best_edge = edges[best_dir]

            # Verificar threshold
            min_edge = self.sport_config.min_edges.get(best_dir, 0.03)
            if best_edge < min_edge:
                continue

            # Calcular apuesta
            if best_dir == "draw":
                p = p_draw
            elif best_dir == "away":
                p = p_away
            else:
                p = p_home

            bet = self.kelly.calculate_single_bet(
                p=p,
                odds=odds[best_dir],
                bankroll=self.stats["current_bankroll"],
                min_bet=1.0,
                max_bet=self.sport_config.positions_max * 5,
            )

            if bet < 1.0:
                continue

            # Ejecutar "apuesta"
            self.stats["total_trades"] += 1
            actual_result = match.get("result", "")

            # Calcular PnL
            won = best_dir == actual_result
            pnl = (bet / odds[best_dir] - bet) if won else -bet

            # Actualizar bankroll
            self.stats["current_bankroll"] += pnl
            self.stats["total_pnl"] += pnl

            if won:
                self.stats["wins"] += 1
            else:
                self.stats["losses"] += 1

            # Actualizar Brier
            self._update_brier(p_home, p_draw, p_away, actual_result)

            # Log cada 10 trades
            if self.stats["total_trades"] % 10 == 0:
                wr = 100 * self.stats["wins"] / max(1, self.stats["total_trades"])
                print(
                    f"  [{self.stats['total_trades']:3d}] {date} {home:20} vs {away:20} | "
                    f"Bet ${bet:6.2f} on {best_dir:6} | "
                    f"Edge {best_edge:+.3f} | Result: {actual_result:6} | "
                    f"PnL ${pnl:+7.2f} | Bank ${self.stats['current_bankroll']:.2f} | "
                    f"WR {wr:5.1f}%"
                )

        elapsed = time.time() - start_time

        return self._compile_report(elapsed)

    def _update_brier(
        self,
        p_home: float,
        p_draw: float,
        p_away: float,
        result: str,
    ):
        """Actualizar Brier score."""
        actual_h = 1.0 if result == "home" else 0.0
        actual_d = 1.0 if result == "draw" else 0.0
        actual_a = 1.0 if result == "away" else 0.0

        brier = (
            (p_home - actual_h) ** 2 + (p_draw - actual_d) ** 2 + (p_away - actual_a) ** 2
        ) / 3

        self.stats["brier_sum"] += brier
        self.stats["brier_n"] += 1

    def _compile_report(self, elapsed: float) -> Dict:
        """Compilar reporte final."""
        total_trades = max(1, self.stats["total_trades"])
        win_rate = self.stats["wins"] / total_trades
        avg_pnl = self.stats["total_pnl"] / total_trades
        brier_avg = self.stats["brier_sum"] / max(1, self.stats["brier_n"])

        # Simple Sharpe
        sharpe = (
            (avg_pnl * 52) / max(0.01, abs(avg_pnl) * 0.1)
            if avg_pnl != 0
            else 0
        )

        report = {
            "sport": self.sport_config.name,
            "predictor": self.predictor_type,
            "duration_secs": elapsed,
            "total_matches_analyzed": self.stats["total_matches"],
            "total_trades": self.stats["total_trades"],
            "trades_per_match": total_trades / max(1, self.stats["total_matches"]),
            "wins": self.stats["wins"],
            "losses": self.stats["losses"],
            "win_rate": win_rate,
            "total_pnl": self.stats["total_pnl"],
            "avg_pnl_per_trade": avg_pnl,
            "starting_bankroll": self.bankroll,
            "ending_bankroll": self.stats["current_bankroll"],
            "return_pct": (
                (self.stats["current_bankroll"] - self.bankroll) / self.bankroll * 100
            ),
            "brier_score": brier_avg,
            "sharpe_ratio": sharpe,
        }

        return report


def main():
    """Test con datos REALES."""
    # Backtest PL 2023-24
    runner = ImprovedBacktestRunner(sport_code="pl", predictor_type="logistic")

    print("\n" + "=" * 70)
    print("BACKTEST CON DATOS REALES - PL 2023-24")
    print("=" * 70)

    report = runner.run("pl", "2023-24")

    if not report:
        return 1

    # Print report
    print("\n" + "=" * 70)
    print("BACKTEST REPORT")
    print("=" * 70)
    print(f"Deporte               : {report['sport']}")
    print(f"Predictor             : {report['predictor']}")
    print(f"Temporada             : PL 2023-24")
    print("-" * 70)
    print(f"Partidos analizados   : {report['total_matches_analyzed']}")
    print(f"Operaciones ejecutadas: {report['total_trades']}")
    if report['total_trades'] > 0:
        print(f"  Ganancias           : {report['wins']}")
        print(f"  Pérdidas            : {report['losses']}")
        print(f"  Win rate            : {report['win_rate']:.1%}")
    print("-" * 70)
    print(f"Bankroll inicial      : ${report['starting_bankroll']:.2f}")
    print(f"Bankroll final        : ${report['ending_bankroll']:.2f}")
    print(f"Total P&L             : ${report['total_pnl']:+.2f}")
    if report['total_trades'] > 0:
        print(f"Promedio P&L/op       : ${report['avg_pnl_per_trade']:+.2f}")
    print(f"Retorno %             : {report['return_pct']:+.1f}%")
    print("-" * 70)
    print(f"Brier score           : {report['brier_score']:.4f}")
    print(f"Sharpe ratio          : {report['sharpe_ratio']:.2f}")
    print(f"Tiempo                : {report['duration_secs']:.1f}s")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
