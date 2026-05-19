# Cómo Usar El Bot (Después de la Implementación de Trading Logic)

**Cambio Principal:** El bot ahora **coloca apuestas reales** (en modo paper = simuladas) en lugar de solo predecir.

---

## Opción 1: Ver el Bot en Acción (2 minutos)

```bash
python demo_trading.py
```

**Qué hace:**
- Carga Liga Mexicana
- Obtiene 4 fixtures
- Predice resultados
- Busca matches con edge
- **COLOCA APUESTAS** (simuladas)
- Cierra posiciones después de 30 segundos
- Muestra P&L

**Salida esperada:**
```
[15:30:45] Fetching fixtures...
[15:30:46] Found 4 fixtures
[15:30:47] Tradeable matches: 2
[15:30:47]   Guadalajara vs Tigres | Edge: +4.2%
[15:30:47]   Monterrey vs Pachuca | Edge: +3.1%

[15:30:47] === Demo Trading Loop ===

[15:31:02] ✓ Placed 1 new entries
[15:31:02] ENTRY: Guadalajara vs Tigres | HOME | $4.50 @ 0.620 | Edge: +4.2%

[15:31:17] ✓ Placed 1 new entries
[15:31:17] ENTRY: Monterrey vs Pachuca | AWAY | $3.80 @ 0.350 | Edge: +3.1%

[15:31:32] ✓ Closed 1 positions
[15:31:32] WIN: Guadalajara vs Tigres | PnL: +$2.70

[15:31:47] ✓ Closed 1 positions
[15:31:47] LOSS: Monterrey vs Pachuca | PnL: -$3.80

[15:32:47] === Demo Complete ===
Results:
  Wins/Losses: 1W / 1L (50%)
  Starting Bankroll: $100.00
  Final Bankroll: $98.90
  Total P&L: -$1.10
  Return: -1.10%
```

---

## Opción 2: Ejecutar Una Liga

```bash
python bot/unified_bot.py --mode paper --sport mex --bankroll 100
```

**Qué hace:**
- Liga Mexicana en modo paper (trades simulados)
- Bankroll de $100
- Predictor heurístico
- Corre indefinidamente

**Salida:**
```
======================================================================
UNIFIED SPORTS BETTING BOT
======================================================================
Mode       : PAPER
Sport(s)   : mex
Predictor  : heuristic
Bankroll   : $100.00
======================================================================

============================================================
  SPORTS BOT v1  |  Liga Mexicana (MX1)  |  PAPER MODE  |  $100.00
============================================================
  Bankroll      : $100.00 USDC
  Bet range     : $1.00 – $15.00
  Kelly         : 20% (fractional)
  Min edges     : Home 3pp, Draw 5pp, Away 3pp
  Positions max : 6 parallel
  Matches/week  : 5 (top by edge)
============================================================

[15:32:14] Bot initialized
[15:32:14] Refreshing fixtures...
[15:32:15] Found 4 upcoming fixtures
[15:32:15] Tradeable: 1 matches with edge
[15:32:30] ✓ Placed 1 new entries
[15:32:30] ENTRY: Guadalajara vs Tigres | HOME | $4.50 @ 0.620 | Edge: +4.2%
[15:32:35] Status: Pos 1/6 | Exp $4.50 | Bank $95.50 | 0W/0L (0%)
...
```

**Parar:** Presiona Ctrl+C

---

## Opción 3: Ejecutar Todas las Ligas Simultáneamente

```bash
python run_all_leagues.py
```

**Qué hace:**
- 12 ligas corriendo en paralelo
- Cada una con su bankroll
- Cada una con su log

**Salida inicial:**
```
================================================================================
INICIANDO BOT MULTI-LIGA (Modo Paper)
================================================================================

[INICIANDO] Liga Mexicana                  (mex) - Bankroll: $100
[OK] Liga Mexicana                  PID: 14776
[INICIANDO] La Liga                        (laliga) - Bankroll: $100
[OK] La Liga                        PID: 9404
...

================================================================================
RESUMEN: 12 ligas iniciadas, 0 fallidas
================================================================================
```

**Menú interactivo (Ctrl+C):**
```
1. Ver estado de procesos
2. Ver logs (todas las ligas)
3. Ver logs de una liga específica
4. Detener una liga
5. Detener todas las ligas
6. Reiniciar una liga
7. Salir
```

---

## Logs y Monitoreo

### Ver logs en tiempo real

```bash
# Liga Mexicana
type logs/bot_mex.log

# La Liga
type logs/bot_laliga.log

# Cualquier liga
type logs/bot_*.log

# En Linux/Mac: tail -f logs/bot_mex.log
```

### Estructura de logs

```
[15:32:14] Bot initialized
[15:32:14] Refreshing fixtures...
[15:32:15] Found 4 upcoming fixtures
[15:32:15] Tradeable: 1 matches with edge
[15:32:30] ✓ Placed 1 new entries
[15:32:30] ENTRY: Home vs Away | HOME | $4.50 @ 0.620 | Edge: +4.2%
[15:32:35] Status: Pos 1/6 | Exp $4.50 | Bank $95.50 | 0W/0L (0%)
[15:33:00] ✓ Closed 1 positions
[15:33:00] WIN: Home vs Away | PnL: +$2.70
[15:33:35] Status: Pos 0/6 | Exp $0.00 | Bank $98.20 | 1W/0L (100%)
```

---

## Parámetros Disponibles

### unified_bot.py

```bash
python bot/unified_bot.py \
  --mode paper|backtest|live \
  --sport mex|laliga|pl|bundesliga|ligue1|brasil|seriea|mls|superlig|libertadores|ucl|nfl|worldcup \
  --bankroll 100 \
  --predictor heuristic|logistic
```

**Ejemplos:**
```bash
# Liga Mexicana con $50
python bot/unified_bot.py --mode paper --sport mex --bankroll 50

# La Liga con $200
python bot/unified_bot.py --mode paper --sport laliga --bankroll 200

# Bundesliga con predictor logístico (cuando esté disponible)
python bot/unified_bot.py --mode paper --sport bundesliga --predictor logistic

# Backtest PL 2023-24 (cuando esté implementado)
python bot/unified_bot.py --mode backtest --sport pl \
  --start-date 2023-08-01 --end-date 2024-05-31
```

---

## Flujo Completo de Trading

### 1. Carga de Datos
```
Fixtures → Predictor → Scores → Filtro de Edge → Matches Tradeables
```

### 2. Entry (Entrada)
```
Para cada match tradeable:
  - Obtener odds (Polymarket o dummy)
  - Validar edge > threshold
  - Calcular tamaño con Kelly
  - Abrir posición
  - Log: ENTRY
```

### 3. Monitoring (Monitoreo)
```
Cada 5 segundos:
  - Chequear posiciones abiertas
  - Si pasó 30 segundos (demo) o 24h (real)
    - Simular/obtener resultado
    - Calcular P&L
    - Cerrar posición
    - Log: WIN/LOSS
```

### 4. Status
```
Cada 60 segundos:
  - Mostrar: Pos X/6 | Exp $Y | Bank $Z | WW/LL (%)
  - Guardar stats a archivo
```

---

## Benchmarking Esperado

### En Demo (2 minutos)

```
Trades: 4-6
Win rate: 45-55% (random)
P&L: -5% a +5% (simulado)
```

### En Paper (1-2 semanas)

```
Trades: 50-100+
Win rate: 50-55% (si edge es real)
Return: +2% a +10% (si predictor bueno)
```

---

## Troubleshooting

### "No se colocan apuestas"
- Verifica que haya fixtures
- Verifica que los matches tengan edge > threshold
- Mira los logs: `type logs/bot_mex.log`

### "Posiciones no se cierran"
- En demo: se cierran después de 30 segundos
- Espera 30+ segundos después de ENTRY

### "Bot se detiene"
- Presionaste Ctrl+C (intencional)
- Hubo error → mira logs
- Ejecuta de nuevo

---

## Siguiente Paso Recomendado

1. **Ahora:** Ejecuta demo para ver trading en acción
   ```bash
   python demo_trading.py
   ```

2. **Luego:** Una liga por 30 minutos
   ```bash
   python bot/unified_bot.py --mode paper --sport mex --bankroll 100
   ```

3. **Finalmente:** Todas las ligas simultáneamente
   ```bash
   python run_all_leagues.py
   ```

---

## Estados Posibles

✅ **ENTRY** - Bot colocó una apuesta
✅ **WIN** - Apuesta ganó
✅ **LOSS** - Apuesta perdió
⏸️ **Status** - Estado de posiciones abiertas

---

## Bankroll y P&L

```
Inicial: $100.00
Después de ENTRY 1 (-$5.00): $95.00 (en riesgo)
Después de WIN (+$3.00): $98.00
Después de ENTRY 2 (-$4.50): $93.50
Después de LOSS (-$4.50): $89.00
...
```

---

**¡Listo! El bot ahora está completo y funcional. Disfruta tradear múltiples ligas.** 🎯
