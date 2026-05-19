# Guía: Menú Interactivo del Bot Multi-Liga

## Cómo Ejecutar

### Paso 1: Inicia el bot
```bash
python run_all_leagues.py
```

Verás el mensaje:
```
[INFO] Abre logs/bot_*.log para ver el progreso
[INFO] Presiona Ctrl+C para entrar al menú interactivo
```

### Paso 2: Abre el menú
Presiona **Ctrl+C** para abrir el menú interactivo.

## Opciones del Menú

### 1. Ver estado de procesos
Muestra el PID y estado (EN EJECUCIÓN/DETENIDO) de cada liga.

**Ejemplo:**
```
[MONITOR] Chequeando estado de procesos...
────────────────────────────────────────────────────────────────────────────────
  mex          | Liga Mexicana                 | PID:  524 | EN EJECUCIÓN
  laliga       | La Liga                       | PID: 4776 | EN EJECUCIÓN
  pl           | Premier League                | PID: 8848 | EN EJECUCIÓN
  ...
────────────────────────────────────────────────────────────────────────────────
Procesos activos: 12/12
```

### 2. Ver logs (todas las ligas)
Muestra un resumen de todos los archivos de log y su tamaño.

**Ejemplo:**
```
[LOGS DISPONIBLES]
  brasil       :       1937 bytes
  bundesliga   :       2135 bytes
  laliga       :       1953 bytes
  ...
```

### 3. Ver logs de una liga específica
Te pide que selecciones una liga y muestra las últimas 20 líneas de su log.

**Uso:**
```
Opción: 3
Liga (mex, laliga, pl, ...): pl
```

Verás las últimas 20 líneas del log de Premier League.

### 4. Ver trades en vivo (con contador) ⭐ NUEVA OPCIÓN
**Esto es lo que solicitaste.** Muestra todos los trades abiertos con un contador de tiempo que cuenta hacia atrás.

**Ejemplo:**
```
================================================================================
TRADES EN VIVO (Contador de Tiempo)
================================================================================

[PL] Premier League
────────────────────────────────────────────────────────────────────────────────
  Brentford            vs Southampton          | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 3s
  Aston Villa          vs Leicester City       | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 3s

[LIGUE1] Ligue 1
────────────────────────────────────────────────────────────────────────────────
  Montpellier          vs Toulouse             | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 5s

[MLS] MLS
────────────────────────────────────────────────────────────────────────────────
  Atlanta United       vs Philadelphia Union   | HOME  | $ 10.67 @ 0.153 | Cierra en: 0m 2s

────────────────────────────────────────────────────────────────────────────────
Total: 3 trades abiertos
================================================================================
```

**Información mostrada:**
- Liga y código
- Equipo home vs Equipo away
- Dirección de la apuesta (HOME/AWAY/DRAW)
- Monto apostado ($)
- Cuotas (odds)
- ⏱️ **CONTADOR**: Tiempo restante hasta que se cierre el trade

### 5. Detener una liga
Te pide que selecciones una liga y la detiene.

**Uso:**
```
Opción: 5
Liga (mex, laliga, pl, ...): mex
```

### 6. Detener todas las ligas
Pide confirmación y detiene todos los bots.

**Uso:**
```
Opción: 6
¿Detener todas las ligas? (s/n): s
```

### 7. Reiniciar una liga
Te pide que selecciones una liga, la detiene y la reinicia.

**Uso:**
```
Opción: 7
Liga (mex, laliga, pl, ...): pl
```

### 8. Salir
Cierra el programa y detiene todas las ligas.

**Uso:**
```
Opción: 8
¿Salir? Esto detendrá todas las ligas (s/n): s
```

## Características Implementadas

### ✅ Colores ANSI Arreglados
Los colores ahora se muestran correctamente en Windows Terminal:
- 🟢 Verde: Éxito, OK, entries
- 🔴 Rojo: Errores
- 🟡 Amarillo: Advertencias
- 🔵 Cian: Información de debug
- ⚪ Blanco: Mensajes normales

### ✅ Visor de Trades en Vivo
- Actualización cada 60 segundos
- Contador de tiempo automático
- Agrupa por liga para fácil lectura
- Muestra: Home vs Away, dirección, monto, cuotas, tiempo restante

### ✅ Manejo Robusto de Errores
- Si presionas Ctrl+C en el menú, puedes continuar escribiendo tu opción
- Validación de opciones
- Validación de códigos de liga

## Notas Importantes

1. **Los trades se cierran cada 30 segundos** en modo demo (simulado)
2. **Las posiciones se actualizan cada 60 segundos**
3. **Cada liga tiene su propio bankroll** independiente
4. **Los logs se guardan en** `logs/bot_[liga].json`
5. **Las posiciones se guardan en** `logs/positions_[liga].json`

## Ejemplo de Sesión Completa

```bash
C:\BotSport> python run_all_leagues.py

[OK] Liga Mexicana                  PID: 524
[OK] La Liga                        PID: 4776
[OK] Premier League                 PID: 8848
...

[INFO] Presiona Ctrl+C para entrar al menú interactivo

# (Usuario presiona Ctrl+C)

Opción: 4

# (Ver trades en vivo)
[PL] Premier League
  Brentford vs Southampton | HOME | $10.67 | Cierra en: 0m 3s
  Aston Villa vs Leicester | HOME | $10.67 | Cierra en: 0m 3s

Total: 2 trades abiertos

# (Presiona Enter o escribe otra opción)

Opción: 1

# (Ver estado de procesos)
[MONITOR] Estado de procesos...
Procesos activos: 12/12

Opción: 8
¿Salir? (s/n): s

# Bot se detiene y termina
```

## Solución de Problemas

### P: No veo colores en el terminal
R: Los colores ANSI se activan automáticamente. Asegúrate de usar Windows Terminal o una terminal compatible.

### P: El menú dice "Opción inválida"
R: Debes escribir un número del 1 al 8 y presionar Enter.

### P: Los trades no aparecen en "Ver trades en vivo"
R: Los trades se muestran después de que los bots generen posiciones (puede tomar unos minutos). Espera y presiona "4" nuevamente.

### P: ¿Puedo dejar el bot corriendo sin el menú?
R: Sí. Solo no presiones Ctrl+C. El bot continuará ejecutándose indefinidamente.

---

**¡Listo! El bot multi-liga está completamente funcional con menú interactivo y visor de trades en vivo.** 🎯
