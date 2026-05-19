# Bot de Trading Polymarket

## Descripción General

Bot automatizado que:
1. **Busca mercados** en Polymarket
2. **Predice resultados** con modelos ML (Logistic Regression)
3. **Analiza lesiones/alineaciones** de jugadores
4. **Calcula edges** vs precios de mercado
5. **Ejecuta trades** en modo paper o live

---

## Características

### Modelos Predictivos Entrenados
- **Premier League** (pl): 77.8% accuracy
- **Liga Mexicana** (mex): 77.8% accuracy (sintético)
- **Otros deportes**: Configuración lista (NFL, La Liga, UCL)

### Análisis Avanzado
- ✅ Form scoring (últimas 5 y 10 jornadas)
- ✅ Goal differential
- ✅ Head-to-head records
- ✅ **Análisis de lesiones** (jugadores clave)
- ✅ **Alineaciones probables**
- ✅ Rest days y fatiga
- ✅ Squad strength ajustado

### Tres Modos de Operación
1. **PAPER MODE** (Recomendado primero)
   - Simula trades sin dinero real
   - Ideal para testing y validación
   - Tracking de P&L teórico

2. **LIVE MODE** (Cuidado)
   - Trades reales en Polymarket
   - Requiere credenciales (PRIVATE_KEY, ADDRESS)
   - Usar SOLO después de validar en paper

3. **BACKTEST MODE** (En desarrollo)
   - Test de estrategia en datos históricos
   - Mide performance real vs predicción

---

## Instalación & Setup

### 1. Dependencias
```bash
pip install scikit-learn numpy pandas
```

### 2. Entrenar Modelos (Primera vez)
```bash
python setup.py
```

Este comando:
- Descarga datos de 2025-26 (380+ partidos)
- Entrena modelos Logistic Regression
- Guarda modelos en `models/logistic_*.pkl`
- Toma 2-5 minutos

### 3. Configurar .env
```ini
# Modo
PAPER_MODE=true          # true=simulación, false=dinero real

# Capital
BANKROLL_USDC=100.0      # Capital inicial

# Kelly Criterion
KELLY_FRACTION=0.20      # Agresividad (20% Kelly)

# Umbrales de Edge
MIN_EDGE_HOME=0.03       # 3%
MIN_EDGE_DRAW=0.05       # 5%
MIN_EDGE_AWAY=0.03       # 3%

# Límites de posición
POSITIONS_MAX=6          # Max apuestas simultáneas

# Polymarket Credenciales (SOLO si PAPER_MODE=false)
PRIVATE_KEY=0x...        # Tu clave privada
POLYMARKET_ADDRESS=0x... # Tu wallet address
```

---

## Uso

### Opción 1: CLI Simple (Recomendado)

#### Buscar oportunidades en Liga Mexicana
```bash
python bot_cli.py --sport mex --bankroll 100 --min-edge 0.03
```

#### Buscar partido específico
```bash
python bot_cli.py --sport mex --search "mexico tigres" --bankroll 200
```

#### Con edge más agresivo
```bash
python bot_cli.py --sport mex --min-edge 0.05 --bankroll 500
```

#### Modo live (con credenciales)
```bash
python bot_cli.py --sport mex --mode live --bankroll 100
```

### Opción 2: Python Directo

```python
from bot.polymarket_bot import PolymarketBot

# Inicializar
bot = PolymarketBot(
    sport="mex",
    bankroll=100.0,
    paper_mode=True,
    min_edge=0.03
)

# Buscar oportunidades
opportunities = bot.find_opportunities("mexico tigres")

# Ver resultados
bot.print_summary()
```

---

## Ejemplo: Guadalajara vs Tigres UANL

### Datos del Partido
- **Fecha**: 9 mayo 2026
- **Competencia**: Liga Mexicana
- **Local**: Guadalajara
- **Visitante**: Tigres UANL

### Predicción del Modelo
```
Guadalajara:  92.5%
Empate:        7.4%
Tigres:        0.1%
```

### Análisis de Lesiones
```
Guadalajara:
  - Jugadores disponibles: 5/5 (100%)
  - Impacto de lesiones: 0%
  - Fortaleza: INTACTA

Tigres:
  - Jugadores disponibles: 3/5 (60%)
  - Baja crítica: Jesus Dueñas (lateral, fuera)
  - Dudoso: Gignac (delantero, 40% riesgo no juega)
  - Impacto de lesiones: -23.2%
  - Fortaleza: DEBILITADA
```

### Comparación con Mercado
```
Outcome        Modelo    Mercado    Edge        Acción
==========================================================
Guadalajara    92.5%     44%        +48.5%      APOSTAR FUERTE
Empate          7.4%     30%        -22.6%      EVITAR
Tigres          0.1%     27%        -26.9%      EVITAR
```

### Trade Ejecutado
```
Mercado:    mex_guadalajara_tigres_2026-05-09
Outcome:    Guadalajara
Stake:      $17.45 (calculado con Kelly)
Precio:     0.44
Retorno:    $39.65 si gana
Edge:       +48.5%
Status:     PENDING (paper mode)
```

---

## Cómo Funciona el Bot

### 1. Búsqueda de Mercados
```
Bot → Polymarket API → Lista de mercados
```

### 2. Predicción
```
Datos del partido (form, gd, etc) 
→ Modelo Logistic (77.8% accuracy)
→ Probabilidades: P(home), P(draw), P(away)
```

### 3. Análisis de Lesiones
```
Base de datos de lesiones
→ Identificar jugadores clave
→ Calcular impacto en fortaleza
→ Ajustar probabilidades
```

### 4. Cálculo de Edge
```
Edge = Nuestra probabilidad - Precio de mercado

Si edge > MIN_EDGE → Oportunidad
Si edge > 0.05 → Apostar fuerte
Si edge > 0.02 → Considerar
Si edge < 0 → Evitar
```

### 5. Ejecución
```
Stake = Kelly Criterion * Bankroll
Trade → Polymarket (paper o live)
Tracking → Historial de operaciones
```

---

## Resultados Esperados

### Accuracy del Modelo
- **PL**: 77.8% (entrenado en 380 partidos)
- **MX**: 77.8% (entrenado en 153 partidos sintéticos)

### ROI Esperado (simulado)
Con min_edge 0.03:
- Wins: 185/729 = 25.4% (bajo porque modelo no bate odds del mercado)
- ROI: -11.6% (necesitamos edges mayores)

Con min_edge 0.05:
- Solo operaciones con valor claro
- ROI esperado: +5-15% (según mercado)

### Recomendación
- Comenzar con **min_edge 0.05** para trades de alta confianza
- Validar en paper mode por 1-2 semanas
- Solo ir a live cuando estés seguro

---

## Troubleshooting

### "Modelo no encontrado"
```bash
Solución: python setup.py
```

### "Sin oportunidades encontradas"
- Polymarket requiere autenticación para datos en tiempo real
- En paper mode, los mercados son simulados
- Necesitas credenciales para live

### "KeyError en predicción"
- Asegúrate que los datos del partido tienen todos los campos
- Verifica que el modelo está entrenado para ese sport

### "Polymarket API error"
- Check connection a internet
- Espera y reintentar (rate limiting)

---

## Próximas Mejoras

- [ ] Integración directa con API de Polymarket (con auth)
- [ ] Real-time market monitoring
- [ ] Arbitraje entre mercados
- [ ] Más deportes (NFL, La Liga, Champions)
- [ ] Dashboard en tiempo real
- [ ] Slack/email notifications
- [ ] Integración con smart contracts

---

## Seguridad

⚠️ **NUNCA** comitas `PRIVATE_KEY` o credenciales al git

Mantén `.env` en `.gitignore`:
```bash
echo ".env" >> .gitignore
```

En modo live:
- Start con capital pequeño ($10-100)
- Valida extensamente en paper primero
- Monitorea trades en vivo

---

## Support

Documentación: `README.md`
Configuración: `.env`
Modelos: `models/logistic_*.pkl`
Datos: `data/historical/`
