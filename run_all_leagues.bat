@echo off
REM Script para ejecutar todas las ligas en Windows

echo.
echo ========================================================================
echo INICIANDO BOT MULTI-LIGA (Modo Paper)
echo ========================================================================
echo.

REM Crear directorio de logs
if not exist logs mkdir logs

REM Lanzar cada liga individualmente
echo [INICIANDO] Liga Mexicana (mex) - Bankroll: $100
start "BOT-mex" /B python bot\unified_bot.py --mode paper --sport mex --bankroll 100 > logs\bot_mex.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] La Liga (laliga) - Bankroll: $100
start "BOT-laliga" /B python bot\unified_bot.py --mode paper --sport laliga --bankroll 100 > logs\bot_laliga.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Premier League (pl) - Bankroll: $100
start "BOT-pl" /B python bot\unified_bot.py --mode paper --sport pl --bankroll 100 > logs\bot_pl.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Bundesliga (bundesliga) - Bankroll: $100
start "BOT-bundesliga" /B python bot\unified_bot.py --mode paper --sport bundesliga --bankroll 100 > logs\bot_bundesliga.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Ligue 1 (ligue1) - Bankroll: $100
start "BOT-ligue1" /B python bot\unified_bot.py --mode paper --sport ligue1 --bankroll 100 > logs\bot_ligue1.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Brasileirao (brasil) - Bankroll: $100
start "BOT-brasil" /B python bot\unified_bot.py --mode paper --sport brasil --bankroll 100 > logs\bot_brasil.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Serie A (seriea) - Bankroll: $100
start "BOT-seriea" /B python bot\unified_bot.py --mode paper --sport seriea --bankroll 100 > logs\bot_seriea.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] MLS (mls) - Bankroll: $100
start "BOT-mls" /B python bot\unified_bot.py --mode paper --sport mls --bankroll 100 > logs\bot_mls.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Super Lig (superlig) - Bankroll: $100
start "BOT-superlig" /B python bot\unified_bot.py --mode paper --sport superlig --bankroll 100 > logs\bot_superlig.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Copa Libertadores (libertadores) - Bankroll: $100
start "BOT-libertadores" /B python bot\unified_bot.py --mode paper --sport libertadores --bankroll 100 > logs\bot_libertadores.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] Champions League (ucl) - Bankroll: $100
start "BOT-ucl" /B python bot\unified_bot.py --mode paper --sport ucl --bankroll 100 > logs\bot_ucl.log 2>&1
timeout /t 1 /nobreak >nul

echo [INICIANDO] NFL (nfl) - Bankroll: $75
start "BOT-nfl" /B python bot\unified_bot.py --mode paper --sport nfl --bankroll 75 > logs\bot_nfl.log 2>&1
timeout /t 1 /nobreak >nul

echo.
echo ========================================================================
echo Todas las ligas iniciadas ^^!
echo ========================================================================
echo.
echo Ver logs:
echo   type logs\bot_mex.log
echo   type logs\bot_pl.log
echo   type logs\bot_laliga.log
echo.
echo Ver procesos activos:
echo   tasklist ^| findstr unified_bot
echo.
echo Detener todo:
echo   taskkill /FI "WINDOWTITLE eq BOT-*" /T
echo.
pause
