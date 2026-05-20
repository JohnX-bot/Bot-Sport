# Cambios Implementados - Arreglo de Colores ANSI y Visor de Trades en Vivo

## 1. ✅ Arreglo de Códigos ANSI (Colores en Windows)

### Problema
Los códigos ANSI se mostraban como caracteres crudos (←[90m) en lugar de renderizarse como colores en Windows Terminal.

### Solución
Añadido soporte para ANSI en Windows al inicio de `bot/sports_bot_main.py`:

```python
# Enable ANSI colors in Windows Terminal
if sys.platform == "win32":
    os.system("color")  # Enable color support in Windows console
```

Esta línea activa el soporte de códigos ANSI en la terminal de Windows, permitiendo que los colores se rendericen correctamente.

### Resultado
✅ Los colores ahora se muestran correctamente en Windows Terminal
- Verde para entradas y mensajes de éxito
- Rojo para errores
- Amarillo para advertencias
- Cian para información de debug

---

## 2. ✅ Sistema de Guardado de Posiciones Abiertas

### Cambios en `bot/sports_bot_main.py`

Añadida función `save_positions_state()` que guarda las posiciones abiertas a un archivo JSON:

```python
def save_positions_state(pos_manager, sport_code: str):
    """Save open positions to JSON file for monitoring."""
```

Esta función:
- Se ejecuta cada 60 segundos (en el heartbeat del bot)
- Crea archivos JSON en `logs/positions_[sport_code].json`
- Contiene información de cada posición abierta:
  - Equipos (home_team, away_team)
  - Dirección de la apuesta (home/draw/away)
  - Monto apostado
  - Cuotas
  - Tiempo transcurrido desde la entrada
  - Timestamp de la actualización

### Ejemplo de archivo generado
```json
{
  "sport_code": "pl",
  "timestamp": "13:35:47",
  "open_positions": 2,
  "positions": [
    {
      "match_id": "Brentford_Southampton_...",
      "home_team": "Brentford",
      "away_team": "Southampton",
      "direction": "home",
      "bet_amount": 10.67,
      "odds": 0.153,
      "entry_time": 1778441727,
      "time_elapsed_seconds": 20
    }
  ]
}
```

---

## 3. ✅ Visor de Trades en Vivo con Contador

### Nuevos cambios en `run_all_leagues.py`

#### Añadidas importaciones
```python
import json
import os
```

#### Nueva función: `show_live_trades()`

```python
def show_live_trades(self):
    """Muestra todos los trades abiertos con contador de tiempo."""
```

Esta función:
- Lee todos los archivos `positions_*.json` de la carpeta logs/
- Agrupa trades por liga
- Calcula el tiempo restante hasta cierre (30 segundos en modo demo)
- Muestra en formato legible con countdowns

#### Ejemplo de salida
```
================================================================================
TRADES EN VIVO (Contador de Tiempo)
================================================================================

[PL] Premier League
--------------------------------------------------------------------------------
  Brentford            vs Southampton          | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 3s     
  Aston Villa          vs Leicester City       | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 3s     

[LIGUE1] Ligue 1
--------------------------------------------------------------------------------
  Montpellier          vs Toulouse             | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 5s     

[MLS] MLS
--------------------------------------------------------------------------------
  Atlanta United       vs Philadelphia Union   | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 2s     

================================================================================
Total: 4 trades abiertos
================================================================================
```

---

## 4. ✅ Menú Actualizado en `run_all_leagues.py`

El menú interactivo ahora tiene la siguiente estructura:

```
1. Ver estado de procesos
2. Ver logs (todas las ligas)
3. Ver logs de una liga específica
4. Ver trades en vivo (con contador)  ← NUEVA OPCIÓN
5. Detener una liga
6. Detener todas las ligas
7. Reiniciar una liga
8. Salir
```

### Wireup de opción 4

```python
elif choice == "4":
    self.show_live_trades()
```

La opción 4 ahora abre el visor de trades en vivo con contadores de tiempo.

---

## Cómo Usar

### Ejecutar el Bot Multi-Liga
```bash
python run_all_leagues.py
```

### En el Menú Interactivo (Presiona Ctrl+C)
```
Opción: 4
```

Verás todos los trades abiertos en vivo con el tiempo restante hasta que se cierren.

---

## Detalles Técnicos

### Actualización de Posiciones
- Se actualiza cada 60 segundos (en el heartbeat del bot)
- Los contadores se recalculan en tiempo real
- Sistema asume cierre a los 30 segundos en modo demo (configurable)

### Archivos Generados
```
logs/
├── positions_mex.json
├── positions_pl.json
├── positions_laliga.json
├── positions_bundesliga.json
├── positions_ligue1.json
├── positions_brasil.json
├── positions_seriea.json
├── positions_mls.json
├── positions_superlig.json
├── positions_libertadores.json
├── positions_ucl.json
└── positions_nfl.json
```

Cada archivo se actualiza cada 60 segundos con el estado actual de posiciones abiertas.

---

## Validación

✅ ANSI colors funcionan en Windows
✅ Archivos de posiciones se crean correctamente
✅ Visor de trades muestra formato legible
✅ Contadores de tiempo funcionan correctamente
✅ Menú integrado en run_all_leagues.py

---

## Próximos Pasos (Opcionales)

1. Mejorar formato de nombres de equipos (algunos todavía tienen problemas con unicode)
2. Agregar persistencia de trades cerrados (historial)
3. Añadir filtros de ligas en el visor de trades
4. Implementar actualizaciones en tiempo real (cada 5 segundos en lugar de 60)

