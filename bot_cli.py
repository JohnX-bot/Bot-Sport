#!/usr/bin/env python3
"""
CLI para Polymarket Bot

Uso:
  python bot_cli.py --sport mex --mode paper --bankroll 100
  python bot_cli.py --sport mex --search "mexico tigres" --min-edge 0.05
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.polymarket_bot import PolymarketBot


def main():
    parser = argparse.ArgumentParser(
        description="Bot de Trading para Polymarket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Buscar oportunidades en Liga Mexicana
  python bot_cli.py --sport mex --bankroll 100

  # Búsqueda específica
  python bot_cli.py --sport mex --search "mexico tigres"

  # Modo live (requiere credenciales)
  python bot_cli.py --sport mex --mode live --bankroll 100

  # Edge mínimo personalizado
  python bot_cli.py --sport mex --min-edge 0.05
        """
    )

    parser.add_argument(
        "--sport",
        default="mex",
        choices=["pl", "mex", "laliga", "ucl", "nfl"],
        help="Deporte (default: mex)"
    )

    parser.add_argument(
        "--mode",
        default="paper",
        choices=["paper", "live", "backtest"],
        help="Modo de operación (default: paper)"
    )

    parser.add_argument(
        "--bankroll",
        type=float,
        default=100.0,
        help="Capital inicial en USD (default: 100)"
    )

    parser.add_argument(
        "--min-edge",
        type=float,
        default=0.03,
        help="Edge minimo para apostar (default: 0.03 = 3 porciento)"
    )

    parser.add_argument(
        "--search",
        type=str,
        help="Buscar mercado específico (ej: 'mexico tigres')"
    )

    args = parser.parse_args()

    # Validaciones
    if args.mode == "live" and args.bankroll > 500:
        print("[ADVERTENCIA] Modo LIVE con bankroll alto. Continuar? (y/n)")
        if input().lower() != "y":
            print("[CANCELADO]")
            return 1

    if args.mode == "live":
        print("[ALERTA] MODO LIVE - DINERO REAL")
        print(f"         Bankroll: ${args.bankroll:.2f}")
        print(f"         Sport: {args.sport.upper()}")
        print("         Confirmar? (y/n)")
        if input().lower() != "y":
            print("[CANCELADO]")
            return 1

    # Inicializar bot
    print("\n" + "="*100)
    print(f"POLYMARKET BOT - {args.mode.upper()} MODE")
    print("="*100)

    bot = PolymarketBot(
        sport=args.sport,
        bankroll=args.bankroll,
        paper_mode=(args.mode != "live"),
        min_edge=args.min_edge
    )

    # Buscar oportunidades
    search_term = args.search or "football"
    opportunities = bot.find_opportunities(search_term)

    if opportunities:
        print(f"\n[OK] {len(opportunities)} oportunidades encontradas\n")

        # Mostrar oportunidades
        print(f"{'Mercado':<50} {'Edge':<10} {'Acción':<15}")
        print("-" * 100)

        for opp in opportunities[:10]:
            edge_str = f"{opp['best_edge']['value']:+.1%}"
            print(
                f"{opp['title'][:49]:<50} "
                f"{edge_str:<10} "
                f"{opp['recommendation']:<15}"
            )

        # Ejecutar trades
        if args.mode == "paper":
            print(f"\n[BOT] Ejecutando trades (PAPER MODE - sin dinero real)...")

            for opp in opportunities[:5]:
                if opp["best_edge"]["value"] > args.min_edge:
                    trade = bot.execute_trade(
                        market_id=opp["market_id"],
                        outcome=opp["best_edge"]["outcome"],
                        probability=opp["prediction"][opp["best_edge"]["outcome"]],
                        market_price=opp["prices"][
                            ["home", "draw", "away"].index(opp["best_edge"]["outcome"])
                        ],
                        edge=opp["best_edge"]["value"]
                    )

                    print(f"\n  [TRADE] {opp['title'][:40]}")
                    print(f"  Outcome: {opp['best_edge']['outcome'].upper()}")
                    print(f"  Edge: {opp['best_edge']['value']:+.1%}")
                    print(f"  Stake: ${trade['stake']:.2f}")
        elif args.mode == "live":
            print(f"\n[BOT] LIVE MODE - Requiere credenciales Polymarket")
            print(f"      Configurar PRIVATE_KEY y POLYMARKET_ADDRESS en .env")

    else:
        print("\n[INFO] Sin oportunidades encontradas")
        print("[NOTA] Para datos en tiempo real, necesitas credenciales de Polymarket")

    # Resumen
    bot.print_summary()

    print("\n" + "="*100)
    print("BOT COMPLETADO")
    print("="*100 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
