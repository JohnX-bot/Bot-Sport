@echo off
REM Script rápido para probar el API de football-data.org

echo ================================================================================
echo PRUEBA RAPIDA DEL API DE FOOTBALL-DATA.ORG
echo ================================================================================
echo.
echo Este script verificara que el API este funcionando correctamente.
echo.

REM Prueba 1: Diagnóstico del API
echo [1/3] Verificando configuracion del API...
python test_api_debug.py > api_test.log 2>&1
echo. [OK] Resultados guardados en api_test.log
echo.

REM Prueba 2: Buscar partidos en vivo
echo [2/3] Buscando partidos en vivo ahora...
python check_live_matches_now.py > live_matches.log 2>&1
echo. [OK] Resultados guardados en live_matches.log
echo.

REM Prueba 3: Mostrar trades simulados
echo [3/3] Mostrando trades en vivo (con datos API si hay, simulados si no)...
echo.
python show_trades_now.py
echo.

echo ================================================================================
echo RESUMEN:
echo - [API] = Datos REALES desde football-data.org
echo - [SIM] = Datos SIMULADOS (cuando no hay partidos en vivo)
echo ================================================================================
echo.
echo Ver mas informacion en: RESUMEN_SOLUCION_API.md
echo.
pause
