#!/bin/bash
# Script de Verificación y Testing del Bot Polymarket

echo "================================================================================"
echo "                    BOT POLYMARKET - VERIFICACIÓN COMPLETA"
echo "================================================================================"
echo ""

cd "C:/Users/Pc Escritorio/Desktop/BotSport" 2>/dev/null || cd "/c/Users/Pc Escritorio/Desktop/BotSport"

echo "[1/6] Ligas Disponibles y Validación"
echo "────────────────────────────────────────────────────────────────────────────────"
python data/leagues_data.py
echo ""

echo "[2/6] Cargador Universal de Datos"
echo "────────────────────────────────────────────────────────────────────────────────"
python data/universal_data_loader.py
echo ""

echo "[3/6] Sport Config - Todas las Ligas"
echo "────────────────────────────────────────────────────────────────────────────────"
python bot/sport_config.py
echo ""

echo "[4/6] Test Completo - Validación y Prevención de Errores"
echo "────────────────────────────────────────────────────────────────────────────────"
python test_all_leagues.py
echo ""

echo "[5/6] Ejemplo Correctivo - Guadalajara vs Tigres"
echo "────────────────────────────────────────────────────────────────────────────────"
python test_guadalajara_match.py
echo ""

echo "================================================================================"
echo "VERIFICACIÓN COMPLETADA"
echo "================================================================================"
echo ""
echo "COMANDOS ÚTILES:"
echo ""
echo "  Bot Liga Mexicana:"
echo "  python bot/unified_bot.py --mode paper --sport mex --bankroll 100"
echo ""
echo "  Bot La Liga:"
echo "  python bot/unified_bot.py --mode paper --sport laliga --bankroll 100"
echo ""
echo "  Bot Premier League:"
echo "  python bot/unified_bot.py --mode paper --sport pl --bankroll 100"
echo ""
echo "  Bot Bundesliga:"
echo "  python bot/unified_bot.py --mode paper --sport bundesliga --bankroll 100"
echo ""
echo "================================================================================"
