#!/usr/bin/env python3
"""
Verifica qué partidos están en vivo AHORA en cada liga
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.live_matches_api import get_live_matches, FOOTBALL_DATA_API_KEY, LEAGUE_MAPPING

print("="*80)
print("VERIFICAR PARTIDOS EN VIVO AHORA")
print("="*80)

if not FOOTBALL_DATA_API_KEY:
    print("\n[ERROR] API key no configurada!")
    sys.exit(1)

print(f"\nAPI Key: {FOOTBALL_DATA_API_KEY[:20]}...{FOOTBALL_DATA_API_KEY[-5:]}")
print(f"Base URL: https://api.football-data.org/v4\n")

ligas_a_verificar = [
    ("pl", "Premier League"),
    ("laliga", "La Liga"),
    ("bundesliga", "Bundesliga"),
    ("ligue1", "Ligue 1"),
    ("seriea", "Serie A"),
    ("brasil", "Brasileirão"),
    ("mex", "Liga Mexicana"),
    ("mls", "MLS"),
    ("ucl", "Champions League"),
    ("libertadores", "Copa Libertadores"),
    ("superlig", "Süper Lig"),
    ("nfl", "NFL (sin soporte)"),
]

print("Buscando partidos en vivo...\n")
print("-"*80)

total_en_vivo = 0

for code, name in ligas_a_verificar:
    league_id = LEAGUE_MAPPING.get(code)

    if not league_id:
        print(f"{code:15} | {name:30} | NO SOPORTADO EN API")
        continue

    try:
        matches = get_live_matches(code)
        count = len(matches)
        total_en_vivo += count

        if count > 0:
            print(f"{code:15} | {name:30} | [OK] {count} partidos en vivo")
            for match in matches[:2]:  # Mostrar máximo 2 primeros
                print(f"                |   - {match['home_team']} vs {match['away_team']} ({match['display_status']})")
            if count > 2:
                print(f"                |   ... y {count-2} más")
        else:
            print(f"{code:15} | {name:30} | Sin partidos en vivo")
    except Exception as e:
        print(f"{code:15} | {name:30} | ERROR: {str(e)[:40]}")

print("-"*80)
print(f"\nTotal de partidos en vivo encontrados: {total_en_vivo}")

if total_en_vivo == 0:
    print("\n[INFO] No hay partidos en vivo ahora mismo.")
    print("       Esto es NORMAL a las 14:29 UTC (principalmente horario vespertino).")
    print("       Los partidos suelen estar en vivo:")
    print("       - Viernes-Domingo: 14:00-20:00 horario local")
    print("       - Miércoles: Partidos internacionales (Champions League, Europa League)")
    print("\n[TIP] Para ver datos reales [API], espere a un horario con partidos programados.")
else:
    print("\n[OK] Hay partidos en vivo! El bot debería mostrar datos [API].")

print("\n" + "="*80)
