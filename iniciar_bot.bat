@echo off
chcp 65001 >nul
title BotSport - Opportunity Finder
color 0A

echo.
echo  ============================================================
echo   BOTSPORT - OPPORTUNITY FINDER
echo   Se abrira el navegador con el reporte automaticamente.
echo   NO CIERRES ESTA VENTANA - es lo que mantiene el bot vivo.
echo  ============================================================
echo.
echo  Opciones:
echo    1) Min edge 3%%  (mas oportunidades)
echo    2) Min edge 5%%  (solo buenas)
echo    3) Min edge 8%%  (solo excelentes)
echo.
set /p OPT="  Elige opcion (1/2/3) o Enter para 5%%: "

if "%OPT%"=="1" set EDGE=0.03
if "%OPT%"=="2" set EDGE=0.05
if "%OPT%"=="3" set EDGE=0.08
if "%EDGE%"=="" set EDGE=0.05

echo.
echo  Iniciando con min-edge %EDGE% ...
echo  Ctrl+C para detener.
echo.

cd /d "%~dp0"
python opportunity_finder.py --html --min-edge %EDGE%

echo.
echo  Bot detenido. Presiona una tecla para cerrar.
pause >nul
