# Quick Start - Bot de Apuestas Deportivas

## Instalación Inicial (Primera vez)

```bash
# 1. Descargar datos e instalar dependencias
python setup.py

# Esto hace automáticamente:
# - Descarga 380 partidos PL 2023-24 desde football-data.co.uk
# - Entrena modelo Logistic Regression (55.5% accuracy)
# - Crea directorios necesarios
# - Guarda modelo entrenado para usar
```

**Tiempo estimado:** 2-5 minutos la primera vez

---

## Uso Diario

### 1. Backtest Rápido (probar estrategia en histórico)

```bash
# Heurístico (reglas)
python bot/unified_bot.py --mode backtest --sport pl \
  --predictor heuristic --start-date 2023-08-01 --end-date 2024-05-31

# Logístico (ML - RECOMENDADO)
python bot/unified_bot.py --mode backtest --sport pl \
  --predictor logistic --start-date 2023-08-01 --end-date 2024-05-31
```

**Salida:** Win rate, P&L, Brier score, Sharpe ratio

---

### 2. Paper Mode (Simulación en tiempo real)

```bash
# Simular apuestas en tiempo real (SIN dinero real)
python bot/unified_bot.py --mode paper --sport pl \
  --predictor logistic --bankroll 100

# Múltiples deportes
python bot/unified_bot.py --mode paper --sport pl,nfl \
  --predictor logistic --bankroll 200
```

**Requiere:** PAPER_MODE=true en .env (ya configurado)

---

### 3. Live Mode (SOLO cuando esté listo - DINERO REAL)

```bash
# CUIDADO: Esto ejecuta OPERACIONES REALES en Polymarket
python bot/unified_bot.py --mode live --sport pl \
  --predictor logistic --bankroll 100
```

**Requiere:**
- PAPER_MODE=false en .env
- PRIVATE_KEY y POLYMARKET_ADDRESS configurados
- Solo después de validar en backtest + paper

---

## Estructura del Proyecto

```
BotSport/
├── bot/
│   ├── unified_bot.py          # ENTRADA PRINCIPAL
│   ├── sport_config.py         # Configuración de deportes
│   ├── backtest_runner.py      # Motor de simulación
│   └── polymarket_adapter.py   # Integración Polymarket
├── modes/
│   ├── backtest_mode.py        # Modo backtest
│   ├── paper_mode.py           # Modo paper
│   └── live_mode.py            # Modo live
├── models/
│   ├── predictor_heuristic.py  # Predictor basado en reglas
│   ├── predictor_logistic.py   # Predictor ML (nuevo)
│   ├── feature_engineer.py     # 45+ features (nuevo)
│   ├── model_trainer.py        # Entrenador automático (nuevo)
│   └── logistic_pl_2023-24.pkl # Modelo entrenado
├── data/
│   ├── sports_data_loader.py   # Cargador de datos
│   ├── data_downloader.py      # Descargador automático (nuevo)
│   └── historical/
│       └── pl_2023-24.csv      # Datos descargados
├── setup.py                    # CORRER AL INICIO
├── .env                        # Configuración
└── README.md                   # Documentación completa
```

---

## Configuración (.env)

```ini
# Modo
PAPER_MODE=true          # true=simulación, false=dinero real

# Bankroll & Sizing
BANKROLL_USDC=100.0      # Capital inicial
KELLY_FRACTION=0.20      # Tamaño apuesta (20% Kelly)

# Umbrales de Edge
MIN_EDGE_HOME=0.04       # 4 puntos porcentuales
MIN_EDGE_DRAW=0.06       # 6 puntos porcentuales
MIN_EDGE_AWAY=0.04       # 4 puntos porcentuales

# Posiciones abiertas
POSITIONS_MAX=6          # Máximo de apuestas simultáneas
```

---

## Métricas Clave

### Win Rate
```
Target: 55%+ (baseline aleatorio = 33% para 3 outcomes)
Actual (Logistic en train): 55.5%
```

### Brier Score
```
Rango: 0.0 (perfecto) a 1.0 (peor)
Mide calibración de probabilidades
Más bajo = mejor
```

### Sharpe Ratio
```
Risk-adjusted return
Target: >0.5 en sports betting
```

---

## Comparativa Predictores

| Métrica | Heurístico | Logístico |
|---------|-----------|-----------|
| Tipo | Reglas | Machine Learning |
| Features | 14 | 45+ |
| Entrenamiento | Ninguno | 380 partidos |
| Interpretable | ✓ Muy | ~ Módulo |
| Adaptive | ✗ No | ✓ Sí |
| Tiempo | Rápido | Rápido |
| Accuracy | ~50% | 55.5% |

---

## Próximos Pasos

1. **Validar en Paper Mode**
   ```bash
   python bot/unified_bot.py --mode paper --sport pl --predictor logistic
   ```
   - Monitorear por 1-2 jornadas
   - Verificar que Brier score coincida con backtest

2. **Entrenar en más temporadas**
   ```bash
   # Modificar setup.py para incluir 2022-23, 2021-22, etc.
   seasons = ["2021-22", "2022-23", "2023-24"]
   ```

3. **Agregar más deportes**
   ```bash
   python bot/unified_bot.py --mode backtest --sport laliga \
     --predictor logistic --start-date 2023-08-01 --end-date 2024-05-31
   ```

4. **Fine-tuning de parámetros**
   - Ajustar MIN_EDGE thresholds
   - Optimizar KELLY_FRACTION
   - Test en diferentes bankrolls

---

## Solución de Problemas

### "No se puede descargar datos"
```
Causa: Problema de conexión a football-data.co.uk
Solución: 
1. Verificar conexión internet
2. Usar archivo CSV local
3. Ejecutar setup.py nuevamente
```

### "Modelo no entrenado"
```
Causa: No ejecutaste setup.py
Solución: python setup.py
```

### "UnicodeEncodeError en Windows"
```
Causa: Terminal no soporta UTF-8
Solución: Ya está arreglado (usando ASCII chars)
```

---

## Contacto & Más Info

Ver `README.md` para documentación completa.

**Estado actual:** Phase 4 (Integration Testing) 
- ✅ Backtest framework
- ✅ Unified bot
- ✅ Logistic Regression
- ✅ Auto-download & training
- 🔄 Paper mode validation (siguiente)
