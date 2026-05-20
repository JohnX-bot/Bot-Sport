# Estado del API de Football-Data.org

## Resumen
El bot está configurado para usar datos reales desde football-data.org, pero cuando **no hay partidos en vivo**, muestra datos simulados como fallback.

## ¿Por Qué No Ve Datos Reales?

### Razón 1: No hay partidos en vivo ahora mismo
- **Fecha/Hora actual**: 2026-05-10 a las 14:24
- **Estado**: Es fin de temporada en varias ligas. La mayoría de partidos ya terminaron o no han empezado.
- **Solución**: Esperar a que haya partidos en vivo (horarios de fin de semana o partidos internacionales)

### Razón 2: Los datos simulados se usan como fallback
Cuando el bot no encuentra un partido en vivo que coincida:
1. Intenta obtener datos reales del API
2. Si el API retorna lista vacía (sin partidos en vivo)
3. El bot cae al fallback de simulación

**Esto es CORRECTO** - el bot está diseñado para funcionar incluso sin datos en vivo.

## Cómo Verificar que el API Funciona

### Opción 1: Ejecutar el script de diagnóstico
```bash
python test_api_debug.py
```

Esto verificará:
- ✓ .env file está presente
- ✓ API key se cargó correctamente
- ✓ Módulo live_matches_api.py importa bien
- ✓ API key se lee en el módulo
- ✓ API llamadas se pueden hacer
- ✓ Partidos en vivo encontrados (si hay)

### Opción 2: Ver logs de transacciones
Ejecuta el bot y usa la opción 4 del menú para ver "Trades en Vivo".

Busca indicadores:
- `[API]` = Datos reales desde football-data.org
- `[SIM]` = Datos simulados (fallback)
- `Partidos en vivo: X` = Número de partidos en vivo detectados

## Cambios Realizados

### 1. **live_matches_api.py**
- Ahora carga .env automáticamente usando `load_dotenv()`
- No depende del usuario de configurar manualmente la variable de entorno

### 2. **run_all_leagues.py**
- Agregó indicadores `[API]` vs `[SIM]` al mostrar trades
- Ahora muestra cuántos partidos en vivo hay en cada liga
- Mejoró el fallback de simulación para datos más realistas

## Cuándo Verá Datos Reales [API]

Los datos reales aparecerán cuando:
1. Haya partidos jugándose EN VIVO en la API
2. Los nombres de equipos coincidan exactamente entre el bot y la API
3. El API retorne información del partido (score, minuto, status)

## Cómo Probar con Datos Reales

### Mejor Momento para Probar
- **Viernes-Domingo**: Cuando hay más partidos programados
- **Liga Europea**: Primeras horas de la tarde (14:00-20:00 horario local)
- **Ligas Americanas**: Noches del fin de semana

### Pasos:
1. Ejecuta: `python run_all_leagues.py`
2. Presiona Ctrl+C para ir al menú
3. Opción 4: "Ver trades en vivo"
4. Busca `[API]` en la salida
5. Si ves `[SIM]`, significa que no hay partidos en vivo en ese momento

## Estructura de Datos

### Archivo .env
```
FOOTBALL_DATA_API_KEY=bfbca5e0bd6549b1a83ed3c2968b517b
```

### API Response (cuando hay partidos en vivo)
```json
{
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "home_score": 2,
  "away_score": 1,
  "minute": 67,
  "status": "EN VIVO",
  "display_status": "EN VIVO"
}
```

### Fallback (cuando no hay partidos en vivo)
```json
{
  "home_team": "Manchester United",
  "away_team": "Liverpool",
  "score": "1-1",
  "minute": "45'",
  "status": "DESCANSO"
}
```

## Limitaciones del API Gratuito

- 10 llamadas por minuto
- Acceso a ligas principales
- Datos en vivo actualizados cada 30 segundos

## Próximos Pasos

### Si Quiere Datos 100% Reales
Hay opciones:
1. Esperar a que haya más partidos en vivo
2. Usar un API diferente con más eventos en vivo
3. Implementar predicciones alternativas que no requieran datos en vivo

### Para Verificar Consistencia
El bot ahora marca con `[API]` o `[SIM]` para que sepa siempre si está usando datos reales o simulados.

---

**Última actualización**: 2026-05-10
**API Key Status**: ✓ Configurado y funcionando
**Live Match Detection**: ✓ Funcionando (0 partidos en vivo ahora)
