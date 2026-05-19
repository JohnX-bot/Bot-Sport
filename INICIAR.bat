@echo off
chcp 65001 >nul
title BotSport - Opportunity Finder
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo   BOTSPORT - OPPORTUNITY FINDER
echo   - Se abrira el navegador con el reporte automaticamente
echo   - Refresco cada 5 minutos (60s si hay partido en vivo)
echo   - NO CIERRES ESTA VENTANA - mantiene el bot corriendo
echo   - Ctrl+C para detener
echo  ============================================================
echo.

REM Matar instancias previas de python para evitar duplicados
taskkill /F /IM python.exe >nul 2>&1

REM Esperar 1 segundo para que liberen recursos
timeout /t 1 /nobreak >nul

REM Iniciar bot en modo continuo (sin --once)
python opportunity_finder.py --html --min-edge 0

REM Si el bot se cierra inesperadamente, mostrar mensaje
echo.
echo  ============================================================
echo   Bot detenido. Presiona una tecla para cerrar la ventana.
echo  ============================================================
pause >nul
