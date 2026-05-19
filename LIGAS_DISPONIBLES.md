# ⚽ Ligas Disponibles en Football-Data.org

## ✅ Ligas CON Datos en Vivo (Cuando hay Partidos)

Las siguientes ligas están totalmente soportadas y mostrarán datos **[API]** cuando haya partidos EN VIVO:

### Europa

| Liga | País | Código | Estado |
|------|------|--------|--------|
| **Premier League** | Inglaterra | PL | ✅ Activa |
| **La Liga** | España | PD | ✅ Activa |
| **Bundesliga** | Alemania | BL1 | ✅ Activa |
| **Ligue 1** | Francia | FL1 | ✅ Activa |
| **Serie A** | Italia | SA | ✅ Activa |
| **Champions League** | Europa | CL | ✅ Activa |

### América

| Liga | País | Código | Estado |
|------|------|--------|--------|
| **Brasileirão** | Brasil | BSA | ✅ Activa |
| **Copa Libertadores** | América del Sur | CLI | ✅ Activa |

---

## ❌ Ligas SIN Soporte en Football-Data.org

Las siguientes ligas **NO están disponibles** en el API gratuito:

| Liga | País | Razón | Estado |
|------|------|-------|--------|
| Liga MX | México | No disponible en API gratuito | ❌ No soportada |
| MLS | USA/Canadá | Requiere acceso especial o plan premium | ❌ No soportada |
| Süper Lig | Turquía | No disponible en API gratuito | ❌ No soportada |
| NFL | USA | No es fútbol (American Football) | ❌ No soportada |

---

## 🎯 Horarios Recomendados para Probar

### Premier League
- **Sábados/Domingos**: 12:30-17:30 UTC
- **Miércoles**: 19:00-22:00 UTC (partidos de mitad de semana)

### La Liga
- **Viernes**: 19:00-21:00 UTC
- **Sábados**: 10:00-20:00 UTC
- **Domingos**: 16:00-21:00 UTC

### Bundesliga
- **Sábados**: 13:00-17:30 UTC
- **Domingos**: 14:30-17:00 UTC

### Ligue 1
- **Viernes/Sábados/Domingos**: 17:00-21:00 UTC

### Serie A
- **Sábados/Domingos**: 14:00-20:30 UTC

### Brasileirão
- **Lunes a Domingos**: 20:00-23:00 UTC (partidos principalmente nocturnos)

### Champions League
- **Martes/Miércoles**: 18:00-22:00 UTC

### Copa Libertadores
- **Martes/Miércoles/Jueves**: 19:00-22:00 UTC

---

## 📋 Cómo Verificar Partidos Disponibles

Para ver exactamente qué partidos están EN VIVO ahora:

```bash
python check_live_matches_now.py
```

Este script mostrará:
- Ligas con partidos EN VIVO
- Número de partidos por liga
- Equipos que están jugando
- Status de la competición

---

## 🔧 Configuración en live_matches_api.py

Los códigos de liga están definidos en `live_matches_api.py`:

```python
LEAGUE_MAPPING = {
    "pl": "PL",              # ✅ Funcionando
    "laliga": "PD",          # ✅ Funcionando
    "bundesliga": "BL1",     # ✅ Funcionando
    "ligue1": "FL1",         # ✅ Funcionando
    "seriea": "SA",          # ✅ Funcionando
    "brasil": "BSA",         # ✅ Funcionando
    "ucl": "CL",             # ✅ Funcionando
    "libertadores": "CLI",   # ✅ Funcionando
    "mex": None,             # ❌ No disponible
    "mls": None,             # ❌ No disponible
    "superlig": None,        # ❌ No disponible
    "nfl": None,             # ❌ No es fútbol
}
```

---

## ✨ Resumen

- **8 ligas completamente soportadas** con datos en vivo
- **4 ligas no disponibles** en football-data.org
- **API Gratuito**: Suficiente para las principales ligas europeas y sudamericanas
- **Datos**: Actualizados cada 30 segundos cuando hay partidos EN VIVO

**Próximo Paso**: Ejecute el bot durante horarios con partidos (ver tabla de horarios arriba) para ver datos **[API]** reales.

---

**Última actualización**: 2026-05-10
**Status del API**: ✅ Funcionando correctamente
