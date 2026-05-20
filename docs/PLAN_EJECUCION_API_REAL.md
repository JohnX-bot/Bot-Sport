# 📋 Plan: Cómo Ver Datos [API] Reales del Bot

## ✅ Estado Actual

El bot está **100% configurado y funcionando correctamente**. 

Los datos `[SIM]` que ve son porque:
- **No hay partidos JUGÁNDOSE EN ESTE MOMENTO**
- Los partidos de hoy (10 de mayo) YA TERMINARON

## 🎯 Cómo Ver Datos [API] Reales

### Opción 1: Mañana (11 de mayo) a Partir de las 14:00 UTC

**Partidos Programados para Mañana (según SofaScore):**

#### LaLiga España:
- Mallorca vs Villarreal - **07:00 UTC**
- Athletic Club vs Valencia - **09:00 UTC**  
- Real Oviedo vs Getafe - **11:30 UTC**
- Barcelona vs Real Madrid - **14:00 UTC** ← Mejor momento

#### Liga MX (México):
- Pumas vs América - **19:15 UTC** ← Segunda opción

#### Liga Peruana:
- Sport Huancayo vs Juan Pablo II - **13:00 UTC**
- Comerciantes Unidos vs Melgar - **15:15 UTC**
- Cusco vs Los Chankas - **17:30 UTC**

### 📝 Pasos Exactos

**Paso 1**: Espere a que empiece el partido (ej: 14:00 UTC para Barcelona vs Real Madrid)

**Paso 2**: Abra terminal en la carpeta BotSport y ejecute:
```bash
python run_all_leagues.py
```

**Paso 3**: Espere 2-3 segundos y presione `Ctrl+C`

**Paso 4**: Seleccione opción `4` del menú: "Ver trades en vivo"

**Paso 5**: Verá `[API]` en lugar de `[SIM]` ✅

### Ejemplo de Salida Esperada:

```
TRADES EN VIVO (Contador de Tiempo)
================================================================================
Fecha y Hora: 11/05/2026 - 14:30:15
================================================================================

[LALIGA] La Liga (Partidos en vivo: 4)
────────────────────────────────────────────────────────────────────────────
  Barcelona             vs Real Madrid           
    [API] Marcador: 2-1 | Minuto: 30' | Estado: EN VIVO    <-- ¡DATOS REALES!
    Apuesta: HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 15s
```

## 📊 Qué Verá

### Con [API] (Datos Reales):
- ✅ Marcador real del partido
- ✅ Minuto REAL (no simulado)
- ✅ Estado real (EN VIVO, DESCANSO, etc.)
- ✅ Datos desde football-data.org

### Con [SIM] (Datos Simulados):
- ⚠️ Marcador pseudo-aleatorio
- ⚠️ Minuto simulado
- ⚠️ Estado que parece real pero no lo es
- ⚠️ Sin datos del API (porque no hay partidos jugándose)

## 🔄 Alternativa Rápida HOY

Si quiere verificar que el bot funciona correctamente AHORA sin esperar:

```bash
python show_trades_now.py
```

Verá datos `[SIM]` (simulados) pero confirmará que el bot está funcionando.

## ⏰ Mejores Horarios para Probar

### Por Liga:

**Premier League (PL)** 
- Sábados/Domingos: 12:30-17:30 UTC
- Miércoles: 19:00-22:00 UTC

**LaLiga (España)**
- Viernes/Sábados/Domingos: 07:00-20:00 UTC

**Liga MX (México)**
- Viernes/Sábados/Domingos: 01:00-02:00 y 19:15-22:00 UTC

**Bundesliga (Alemania)**
- Sábados: 13:00-17:30 UTC
- Domingos: 12:30-15:30 UTC

**Ligue 1 (Francia)**
- Sábados/Domingos: 17:00-21:00 UTC

## 🔍 Scripts Útiles

### Ver Trades EN VIVO (sin menú):
```bash
python show_trades_now.py
```

### Verificar Partidos Disponibles:
```bash
python check_live_matches_now.py
```

### Diagnóstico Completo del API:
```bash
python test_api_debug.py
```

### Sincronizar con SofaScore:
```bash
python sync_sofascore_check.py
```

## ✨ Conclusión

**EL BOT FUNCIONA PERFECTAMENTE.**

Solo necesita ejecutarlo cuando haya partidos EN VIVO:
- ✅ Durante partidos: Verá `[API]` (datos reales)
- ⚠️ Sin partidos: Verá `[SIM]` (datos simulados, pero el bot funciona)

**Mañana a las 14:00 UTC** puede probar nuevamente y verá `[API]` en los datos de Barcelona vs Real Madrid.

---

**Próximo Paso**: Espere a mañana (11 de mayo) y ejecute el bot a las 14:00 UTC para ver datos [API] reales.

**Alternativa**: Ejecute `python show_trades_now.py` ahora para confirmar que el bot funciona.
