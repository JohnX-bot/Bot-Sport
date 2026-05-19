#!/usr/bin/env python3
"""
Sincronización con SofaScore: Verifica qué partidos están EN VIVO
y compara con datos de football-data.org
"""

import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

from data.live_matches_api import get_live_matches, LEAGUE_MAPPING

print("="*80)
print("VERIFICACION DE PARTIDOS EN VIVO - Sincronización con SofaScore")
print("="*80)

# Información de partidos programados HOY según SofaScore
sofascore_partidos = [
    {
        "liga": "LaLiga",
        "codigo": "laliga",
        "partidos": [
            {"home": "Mallorca", "away": "Villarreal", "hora": "07:00 UTC"},
            {"home": "Athletic Club", "away": "Valencia", "hora": "09:00 UTC"},
            {"home": "Real Oviedo", "away": "Getafe", "hora": "11:30 UTC"},
            {"home": "Barcelona", "away": "Real Madrid", "hora": "14:00 UTC"},
        ]
    },
    {
        "liga": "Liga MX",
        "codigo": "mex",
        "partidos": [
            {"home": "Pumas", "away": "America", "hora": "19:15 UTC"},
        ]
    },
    {
        "liga": "Liga Peruana",
        "codigo": "brasil",  # Usando brasil como aproximado
        "partidos": [
            {"home": "Sport Huancayo", "away": "Juan Pablo II", "hora": "13:00 UTC"},
            {"home": "Comerciantes Unidos", "away": "Melgar", "hora": "15:15 UTC"},
            {"home": "Cusco", "away": "Los Chankas", "hora": "17:30 UTC"},
        ]
    }
]

# Hora actual
ahora = datetime.utcnow()
hora_actual = ahora.strftime("%H:%M UTC")

print(f"\nHora actual: {hora_actual}")
print("\n" + "="*80)
print("PARTIDOS PROGRAMADOS HOY (segun SofaScore)")
print("="*80)

for liga_info in sofascore_partidos:
    print(f"\n[{liga_info['liga'].upper()}]")
    for partido in liga_info['partidos']:
        print(f"  {partido['home']:20} vs {partido['away']:20} | {partido['hora']}")

print("\n" + "="*80)
print("PARTIDOS EN VIVO ENCONTRADOS EN FOOTBALL-DATA.ORG")
print("="*80)

partidos_en_vivo_encontrados = False

for liga_info in sofascore_partidos:
    codigo = liga_info['codigo']

    try:
        matches = get_live_matches(codigo)

        if matches:
            print(f"\n[{liga_info['liga'].upper()}] - {len(matches)} partidos EN VIVO")
            partidos_en_vivo_encontrados = True

            for match in matches:
                estado = match.get('display_status', 'DESCONOCIDO')
                minuto = match.get('minute', '?')
                print(f"  {match['home_team']:20} vs {match['away_team']:20}")
                print(f"    Score: {match.get('home_score', '?')}-{match.get('away_score', '?')} | Min: {minuto}' | {estado}")
        else:
            print(f"\n[{liga_info['liga'].upper()}] - Sin partidos EN VIVO en este momento")

    except Exception as e:
        print(f"\n[{liga_info['liga'].upper()}] - ERROR: {str(e)[:50]}")

def get_tiempo_restante(hora_str, ahora):
    """Calcula tiempo restante hasta una hora"""
    try:
        h, m = map(int, hora_str.split(':'))
        hora = ahora.replace(hour=h, minute=m, second=0, microsecond=0)

        if hora < ahora:
            # Ya pasó, calcular para mañana
            return "mañana"

        diff = hora - ahora
        horas = diff.seconds // 3600
        minutos = (diff.seconds % 3600) // 60

        if horas > 0:
            return f"{horas}h {minutos}m"
        else:
            return f"{minutos}m"
    except:
        return "?"

print("\n" + "="*80)
print("ANALISIS")
print("="*80)

if not partidos_en_vivo_encontrados:
    prox_barcelona = get_tiempo_restante('14:00', ahora)
    prox_pumas = get_tiempo_restante('19:15', ahora)

    print(f"""
RESULTADO: No hay partidos EN VIVO en football-data.org en este momento.

EXPLICACION:
- SofaScore muestra partidos PROGRAMADOS para hoy
- football-data.org solo muestra partidos JUGANDOSE AHORA
- Hora actual: {hora_actual}

PARTIDOS PROXIMOS (según SofaScore):
- Barcelona vs Real Madrid: en {prox_barcelona}
- Pumas vs América: en {prox_pumas}

RECOMENDACION:
Ejecute el bot a los horarios cuando los partidos estén jugándose:
  python run_all_leagues.py

Verá [API] (datos reales) cuando haya partidos EN VIVO.
""")
else:
    print("""
RESULTADO: ENCONTRADOS partidos EN VIVO en football-data.org

El bot mostrará [API] (datos reales) para estos partidos.
Ejecute:
  python show_trades_now.py
""")

print("="*80)
print(f"\n[INFO] Para ver datos [API] reales, ejecute el bot cuando haya partidos jugándose.")
print("[INFO] Use: python show_trades_now.py")
