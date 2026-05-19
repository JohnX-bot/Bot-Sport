# Ejecutar Todas las Ligas Simultáneamente

Tienes 3 opciones. Elige la que prefieras según tu sistema:

---

## Opción 1: Python con Menú Interactivo (Recomendado para Windows)

**Comando:**
```bash
python run_all_leagues.py
```

**Características:**
- ✅ Inicia todas las 12 ligas simultáneamente
- ✅ Menú interactivo para controlar procesos
- ✅ Ver estado de cada liga
- ✅ Ver logs de cualquier liga
- ✅ Detener/reiniciar ligas individuales
- ✅ Fácil de terminar (Ctrl+C)

**Cómo funciona:**
```
1. Inicia las 12 ligas (cada una en su proceso)
2. Cada liga tiene su propio bankroll y log
3. Presiona Ctrl+C para abrir el menú
4. En el menú puedes:
   - Ver estado de todos los procesos
   - Ver logs de cualquier liga
   - Detener/reiniciar ligas específicas
   - Salir (detiene todo automáticamente)
```

**Ejemplo de uso:**
```bash
# Iniciar
python run_all_leagues.py

# En la terminal, verás esto:
[INICIANDO] Liga Mexicana           (mex) - Bankroll: $100
[OK] Liga Mexicana           PID: 12345
[INICIANDO] La Liga                 (laliga) - Bankroll: $100
[OK] La Liga                 PID: 12346
...

# Presiona Ctrl+C cuando quieras entrar al menú:
MULTI-LIGA BOT - MENÚ
========================================================================
1. Ver estado de procesos
2. Ver logs (todas las ligas)
3. Ver logs de una liga específica
4. Detener una liga
5. Detener todas las ligas
6. Reiniciar una liga
7. Salir
========================================================================

Opción: 1

# O ver logs de una liga:
Opción: 3
Liga (mex, laliga, pl, ...): mex

[LOGS] Liga Mexicana
────────────────────────────────────────────────────────────────────────
[BOT] Iniciando paper mode para Liga Mexicana
[API] Generating synthetic fixtures for mex
Found 4 fixtures for Liga Mexicana
...
```

**Detener:**
- Opción 5 del menú (Detener todas las ligas) → Presiona 's'
- O Ctrl+C en el menú

---

## Opción 2: Bash Script (Para Linux/Mac)

**Comando:**
```bash
bash run_all_leagues_simple.sh
```

**Características:**
- ✅ Script simple sin dependencias
- ✅ Lanza todas las ligas en background
- ✅ Genera logs para cada liga

**Cómo funciona:**
```bash
# Inicia todas
bash run_all_leagues_simple.sh

# Ver logs en tiempo real
tail -f logs/bot_mex.log
tail -f logs/bot_pl.log
tail -f logs/bot_laliga.log

# Ver procesos activos
ps aux | grep unified_bot.py

# Detener todo
pkill -f unified_bot.py
```

---

## Opción 3: Batch Script (Windows)

**Comando:**
```cmd
run_all_leagues.bat
```

**Características:**
- ✅ Script nativo de Windows
- ✅ Lanza todas las ligas en ventanas separadas
- ✅ Fácil de ver logs de cada ventana

**Cómo funciona:**
```cmd
# Ejecutar
run_all_leagues.bat

# Se abrirán ~12 ventanas (una por liga)
# Cada ventana ejecuta el bot para esa liga
# Los logs se guardan en logs/bot_*.log

# Ver procesos activos
tasklist /FI "WINDOWTITLE eq BOT-*"

# Detener todo
taskkill /FI "WINDOWTITLE eq BOT-*" /T
```

---

## Comparación de Opciones

| Aspecto | Python | Bash | Batch |
|---------|--------|------|-------|
| **Sistema** | Windows/Linux/Mac | Linux/Mac | Windows |
| **Menú Interactivo** | ✅ Sí | ❌ No | ❌ No |
| **Fácil de Controlar** | ✅ Muy fácil | ⚠️ Medio | ⚠️ Medio |
| **Ver Logs** | ✅ En el menú | ✅ tail -f | ✅ cat/type |
| **Detener Proceso** | ✅ Menú | ✅ pkill | ✅ taskkill |
| **Simplicidad** | ✅ Simple | ✅ Muy simple | ✅ Simple |

**Recomendación:** Usa **Opción 1 (Python)** si estás en Windows/Linux.

---

## Detalles Técnicos

### Bankroll por Liga

```python
LEAGUES = {
    "mex": 100,           # Liga Mexicana
    "laliga": 100,        # La Liga
    "pl": 100,            # Premier League
    "bundesliga": 100,    # Bundesliga
    "ligue1": 100,        # Ligue 1
    "brasil": 100,        # Brasileirão
    "seriea": 100,        # Serie A
    "mls": 100,           # MLS
    "superlig": 100,      # Süper Lig
    "libertadores": 100,  # Copa Libertadores
    "ucl": 100,           # Champions League
    "nfl": 75,            # NFL (más conservador)
}
```

Bankroll total: $1,175

### Logs

Todos los logs se guardan en `logs/bot_*.log`:
```
logs/
├── bot_mex.log          # Liga Mexicana
├── bot_laliga.log       # La Liga
├── bot_pl.log           # Premier League
├── bot_bundesliga.log   # Bundesliga
├── bot_ligue1.log       # Ligue 1
├── bot_brasil.log       # Brasileirão
├── bot_seriea.log       # Serie A
├── bot_mls.log          # MLS
├── bot_superlig.log     # Süper Lig
├── bot_libertadores.log # Copa Libertadores
├── bot_ucl.log          # Champions League
└── bot_nfl.log          # NFL
```

### Proceso de Cada Instancia

```
Instancia MEX
├── Carga Liga Mexicana (validada)
├── Obtiene fixtures (sintéticas)
├── Obtiene equipos y fortalezas
├── Ejecuta modelo predictor
├── Calcula edge
├── Genera trades (papel)
├── Log: logs/bot_mex.log

Instancia LALIGA (simultáneamente)
├── Carga La Liga (validada)
├── Obtiene fixtures (ESPN o sintéticas)
├── ... (mismo flujo)
└── Log: logs/bot_laliga.log

(Todas corriendo en paralelo)
```

---

## Monitoreo en Tiempo Real

### Con Python (Opción 1)

**En el menú, Opción 1:**
```
Procesos activos: 12/12

  mex          | Liga Mexicana               | PID:  5234 | EN EJECUCIÓN
  laliga       | La Liga                     | PID:  5235 | EN EJECUCIÓN
  pl           | Premier League              | PID:  5236 | EN EJECUCIÓN
  ...
```

### Con Linux/Mac (Opción 2)

```bash
# Ver procesos
ps aux | grep unified_bot.py

# Ver actividad en vivo
tail -f logs/bot_*.log

# Contar trades de Liga Mexicana
grep "Trade" logs/bot_mex.log | wc -l
```

### Con Windows (Opción 3)

```cmd
# Ver procesos
tasklist | findstr unified_bot

# Ver logs (PowerShell)
Get-Content logs/bot_mex.log -Wait
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'bot'"

**Causa:** No estás en el directorio correcto

**Solución:**
```bash
cd C:\Users\Pc Escritorio\Desktop\BotSport
python run_all_leagues.py
```

### Algunos logs están vacíos

**Es normal.** Espera 10-20 segundos para que el bot obtenga datos y empiece a generar trades.

### Quiero cambiar el bankroll

Edita el diccionario `LEAGUES` en `run_all_leagues.py`:
```python
LEAGUES = {
    "mex": {"bankroll": 200, ...},  # Cambiar de 100 a 200
}
```

### Quiero agregar/quitar ligas

En `run_all_leagues.py`:
```python
# Quitar una
LEAGUES = {
    # "nfl": ...,  # Comentado, no se ejecutará
    "pl": ...,
    ...
}

# Agregar una nueva
LEAGUES = {
    "pl": ...,
    "worldcup": {"bankroll": 50, "name": "FIFA World Cup"},  # Nueva
}
```

---

## Resumen

```bash
# Opción 1: Python (Recomendado)
python run_all_leagues.py
# Luego Ctrl+C para menú interactivo

# Opción 2: Bash
bash run_all_leagues_simple.sh
tail -f logs/bot_mex.log

# Opción 3: Batch (Windows)
run_all_leagues.bat
```

**Todas las 12 ligas corriendo simultáneamente con validación centralizada y sin riesgo de errores de datos.**
