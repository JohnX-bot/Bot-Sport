# BotSport — Setup para Desarrolladores

## Requisitos
- Python 3.10+
- pip

## Instalación

```bash
# 1. Clonar repo
git clone https://github.com/TU_USUARIO/BotSport.git
cd BotSport

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
# Copiar el archivo de ejemplo y llenar con tus claves
cp .env.example .env
# Editar .env con tu editor favorito
```

## Variables de entorno (.env)

```env
# API de fútbol (opcional - hay fallback a ESPN gratuito)
FOOTBALL_DATA_API_KEY=tu_clave_aqui

# Polymarket (solo necesario para modo live trading)
POLYMARKET_API_KEY=tu_clave_aqui
POLYMARKET_PRIVATE_KEY=tu_clave_aqui
```

> **Nota**: El bot funciona sin claves usando la ESPN API pública.
> Para predicciones de Polymarket solo se necesita la clave de FD.

## Ejecutar

```bash
# Modo normal (HTML report en el navegador)
python opportunity_finder.py --html --min-edge 0

# Una sola pasada (sin loop)
python opportunity_finder.py --html --min-edge 0 --once

# O usar el lanzador (Windows)
INICIAR.bat
```

## Estructura del proyecto

```
BotSport/
├── opportunity_finder.py   # Bot principal - loop de análisis
├── html_report.py          # Generador del reporte HTML
├── results_tracker.py      # Historial de predicciones
├── data/
│   ├── football_api.py     # ESPN + FD API wrappers
│   ├── team_logos.py       # Logos locales de equipos
│   ├── squad_values.py     # Valores de plantilla (rating estrellas)
│   └── predictions_history.json  # (generado automáticamente)
├── models/
│   └── poisson_model.py    # Modelo Poisson Dixon-Coles
├── Escudos/                # Imágenes PNG de escudos por liga
└── report.html             # (generado automáticamente)
```

## Ligas soportadas (9 activas)
- Premier League (pl)
- La Liga (laliga)
- Bundesliga (bundesliga)
- Ligue 1 (ligue1)
- Serie A (seriea)
- Champions League (ucl)
- Brasileirão (brasileirao)
- Liga MX (mex)
- MLS (mls)

## Modelo de predicción

**Poisson Dixon-Coles**:
- `home_advantage = 1.30` (~30% boost a local)
- `rho = -0.18` (corrección de empates)
- Regresión Bayesiana: prior = 20 partidos virtuales hacia la media
- Tamaño de apuesta: Kelly fraccionado × 0.25

**Decisión de apuesta**:
- Principal = outcome con mayor probabilidad según el modelo
- Alternativa = segundo outcome más probable
- Edge / Kelly = solo informativo (no determina la decisión)
