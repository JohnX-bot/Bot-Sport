#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el funcionamiento del API
"""


import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("DIAGNOSTICO DEL API DE FOOTBALL-DATA.ORG")
print("="*80)

# 1. Verificar que el .env existe y se puede leer
print("\n1. Verificando .env file...")
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    print(f"   [OK] Archivo .env encontrado en: {env_path}")
    with open(env_path) as f:
        content = f.read()
        if "FOOTBALL_DATA_API_KEY" in content:
            print(f"   [OK] FOOTBALL_DATA_API_KEY definida en .env")
        else:
            print(f"   [ERROR] FOOTBALL_DATA_API_KEY NO encontrada en .env")
else:
    print(f"   [ERROR] Archivo .env NO encontrado en: {env_path}")

# 2. Verificar que python-dotenv se puede importar
print("\n2. Verificando python-dotenv...")
try:
    from dotenv import load_dotenv
    print(f"   [OK] python-dotenv importado exitosamente")

    # Cargar .env
    load_dotenv()
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if api_key:
        print(f"   [OK] API key cargado: {api_key[:20]}...{api_key[-5:]}")
    else:
        print(f"   [ERROR] API key NO se cargó desde .env")
except ImportError:
    print(f"   [ERROR] python-dotenv NO está instalado. Instala con: pip install python-dotenv")

# 3. Verificar que live_matches_api.py se puede importar
print("\n3. Verificando live_matches_api.py...")
try:
    from data.live_matches_api import get_live_matches, get_match_info
    print(f"   [OK] live_matches_api importado exitosamente")
except ImportError as e:
    print(f"   [ERROR] Error importando live_matches_api: {e}")
    sys.exit(1)

# 4. Verificar que el API key se lee correctamente
print("\n4. Verificando lectura de API key en live_matches_api...")
from data.live_matches_api import FOOTBALL_DATA_API_KEY
if FOOTBALL_DATA_API_KEY:
    print(f"   [OK] API key en live_matches_api: {FOOTBALL_DATA_API_KEY[:20]}...{FOOTBALL_DATA_API_KEY[-5:]}")
else:
    print(f"   [ERROR] API key NO se leyó en live_matches_api")
    print(f"   Nota: live_matches_api.py línea 18 usa os.getenv('FOOTBALL_DATA_API_KEY', '')")

# 5. Probar el API con Premier League (PL)
print("\n5. Probando API con Premier League (PL)...")
print("   Llamando get_live_matches('pl')...")
try:
    matches = get_live_matches("pl")
    if matches:
        print(f"   [OK] Encontrados {len(matches)} partidos en vivo")
        for match in matches[:3]:
            print(f"      - {match['home_team']} vs {match['away_team']}")
            print(f"        Marcador: {match.get('home_score', '?')}-{match.get('away_score', '?')}")
            print(f"        Minuto: {match.get('minute', '?')} | Status: {match.get('status', '?')}")
    else:
        print(f"   [WARN] NO hay partidos en vivo en PL (esto es normal si no hay matches en vivo)")
        print(f"   → Intentando con Brasil...")
        matches = get_live_matches("brasil")
        if matches:
            print(f"   [OK] Encontrados {len(matches)} partidos en Brasil")
            for match in matches[:3]:
                print(f"      - {match['home_team']} vs {match['away_team']}")
        else:
            print(f"   [ERROR] Tampoco hay partidos en Brasil")
except Exception as e:
    print(f"   [ERROR] Error al llamar get_live_matches: {e}")
    import traceback
    traceback.print_exc()

# 6. Probar get_match_info con equipos específicos
print("\n6. Probando get_match_info con equipos específicos...")
test_cases = [
    ("pl", "Manchester United", "Manchester City"),
    ("pl", "Liverpool", "Arsenal"),
    ("brasil", "Flamengo", "Fluminense"),
]

for sport, home, away in test_cases:
    print(f"   Buscando: {home} vs {away} en {sport}")
    try:
        match = get_match_info(sport, home, away)
        if match:
            print(f"      [OK] Encontrado: {match['home_team']} vs {match['away_team']}")
        else:
            print(f"      [ERROR] Partido NO encontrado")
    except Exception as e:
        print(f"      [ERROR] Error: {e}")

# 7. Verificar que positions_pl.json se puede leer y qué equipos contiene
print("\n7. Verificando positions_pl.json...")
import json
positions_file = Path(__file__).parent / "logs" / "positions_pl.json"
if positions_file.exists():
    try:
        with open(positions_file) as f:
            data = json.load(f)
            positions = data.get("positions", [])
            if positions:
                print(f"   [OK] Encontradas {len(positions)} posiciones en PL")
                for pos in positions:
                    home = pos.get("home_team", "?")
                    away = pos.get("away_team", "?")
                    print(f"      - {home} vs {away}")
            else:
                print(f"   [ERROR] Sin posiciones en PL")
    except Exception as e:
        print(f"   [ERROR] Error leyendo positions_pl.json: {e}")
else:
    print(f"   [ERROR] positions_pl.json no existe")

print("\n" + "="*80)
print("FIN DEL DIAGNOSTICO")
print("="*80)
