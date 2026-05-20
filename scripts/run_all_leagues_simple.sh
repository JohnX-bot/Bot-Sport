#!/bin/bash
# Script simple para ejecutar todas las ligas en background

echo "========================================================================"
echo "INICIANDO BOT MULTI-LIGA (Modo Paper)"
echo "========================================================================"
echo ""

# Crear directorio de logs
mkdir -p logs

# Ligas a ejecutar
LEAGUES=(
    "mex:100:Liga Mexicana"
    "laliga:100:La Liga"
    "pl:100:Premier League"
    "bundesliga:100:Bundesliga"
    "ligue1:100:Ligue 1"
    "brasil:100:Brasileirão"
    "seriea:100:Serie A"
    "mls:100:MLS"
    "superlig:100:Süper Lig"
    "libertadores:100:Copa Libertadores"
    "ucl:100:Champions League"
    "nfl:75:NFL"
)

# Lanzar cada liga
for league_spec in "${LEAGUES[@]}"; do
    IFS=':' read -r code bankroll name <<< "$league_spec"

    echo "[INICIANDO] $name ($code) - Bankroll: \$$bankroll"

    # Lanzar en background
    nohup python bot/unified_bot.py \
        --mode paper \
        --sport "$code" \
        --bankroll "$bankroll" \
        > "logs/bot_${code}.log" 2>&1 &

    echo "  PID: $!"
    sleep 0.5
done

echo ""
echo "========================================================================"
echo "Todas las ligas iniciadas"
echo "========================================================================"
echo ""
echo "Ver logs:"
echo "  tail -f logs/bot_mex.log"
echo "  tail -f logs/bot_pl.log"
echo "  tail -f logs/bot_laliga.log"
echo "  etc..."
echo ""
echo "Ver procesos activos:"
echo "  ps aux | grep unified_bot.py"
echo ""
echo "Detener todo:"
echo "  pkill -f unified_bot.py"
echo ""
