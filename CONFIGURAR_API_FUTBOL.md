# Configurar API de Fútbol en Vivo

## ¿Por qué necesitas una API Key?

Para ver **datos reales en vivo** de partidos (marcador, minuto, estado), necesitas registrarte en **football-data.org** y obtener una API key gratuita.

Sin la API key, el bot usará datos **simulados**.

---

## Paso 1: Registrarse en football-data.org

1. Abre: https://www.football-data.org/
2. Haz clic en **Sign Up** (arriba a la derecha)
3. Completa el formulario con:
   - Email
   - Nombre
   - Contraseña
4. Verifica tu email
5. Inicia sesión

---

## Paso 2: Obtener tu API Key

1. Inicia sesión en https://www.football-data.org/
2. Ve a **Profile** (esquina superior derecha)
3. Busca la sección **API Token**
4. Copia tu token (será una larga cadena de caracteres)

Ejemplo:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## Paso 3: Configurar la API Key en tu Sistema

### Opción A: Variable de Entorno (RECOMENDADO)

#### En Windows (PowerShell):
```powershell
$env:FOOTBALL_DATA_API_KEY = "tu_api_key_aqui"
python run_all_leagues.py
```

#### En Windows (CMD):
```cmd
set FOOTBALL_DATA_API_KEY=tu_api_key_aqui
python run_all_leagues.py
```

#### En Linux/Mac:
```bash
export FOOTBALL_DATA_API_KEY="tu_api_key_aqui"
python run_all_leagues.py
```

### Opción B: Archivo .env

1. Crea un archivo llamado `.env` en la carpeta BotSport
2. Añade esta línea:
```
FOOTBALL_DATA_API_KEY=tu_api_key_aqui
```

3. Guarda el archivo
4. Ejecuta el bot:
```bash
python run_all_leagues.py
```

---

## Paso 4: Verificar que Funciona

Ejecuta este comando para probar:

```bash
python data/live_matches_api.py
```

Si todo está bien, verás:
```
Probando API de fútbol en vivo...
Encontrados 5 partidos en vivo en Premier League
  Man City vs Liverpool: 2-1 (LIVE)
  Arsenal vs Chelsea: 1-0 (LIVE)
  ...
```

Si no funciona, verás:
```
[ERROR] No se pudo obtener datos de pl: 401 Client Error
```

---

## Ligas Soportadas por football-data.org

✅ **Premier League** (Inglaterra)
✅ **La Liga** (España)
✅ **Bundesliga** (Alemania)
✅ **Ligue 1** (Francia)
✅ **Serie A** (Italia)
✅ **Brasileirão** (Brasil)
✅ **Liga MX** (México)
✅ **MLS** (USA/Canada)
✅ **Champions League** (Europa)
✅ **Copa Libertadores** (América del Sur)
✅ **Süper Lig** (Turquía)

❌ **NFL** (No disponible en football-data.org)

---

## Plan Gratuito de football-data.org

- ✅ 10 llamadas por minuto
- ✅ Acceso a todas las ligas principales
- ✅ Datos en vivo actualizados
- ❌ Sin límite de llamadas diarias (solo el límite de 10/minuto)

**Esto es suficiente para el bot!**

---

## Datos que Obtendrás

Con la API configurada, verás en el visor:

```
================================================================================
TRADES EN VIVO (Contador de Tiempo)
================================================================================
Fecha y Hora: 10/05/2026 - 14:30:15
================================================================================

[PL] Premier League
────────────────────────────────────────────────────────────────────────────
  Manchester City vs Liverpool
    Marcador: 2-1 | Minuto: 67' | Estado: EN VIVO
    Apuesta: HOME | $10.67 @ 0.153 | Cierra en: 0m 8s

[LALIGA] La Liga
────────────────────────────────────────────────────────────────────────────
  Barcelona vs Real Madrid
    Marcador: 1-1 | Minuto: 45' | Estado: DESCANSO
    Apuesta: HOME | $10.67 @ 0.153 | Cierra en: 0m 12s

================================================================================
```

---

## Solución de Problemas

### "FOOTBALL_DATA_API_KEY no configurada"

**Solución**: 
- Verifica que estableciste correctamente la variable de entorno
- Reinicia la terminal/CMD después de establecer la variable
- Comprueba que copiaste correctamente tu API key

### "[ERROR] 401 Client Error"

**Solución**:
- Tu API key es incorrecta o expiró
- Ve a https://www.football-data.org/ y verifica tu token
- Actualiza la variable de entorno con el nuevo token

### "[ERROR] 429 Client Error (Too Many Requests)"

**Solución**:
- Excediste el límite de 10 llamadas/minuto
- El bot espera automáticamente antes de hacer más llamadas
- Esto se resuelve solo en pocos segundos

---

## Alternativas

Si no quieres configurar una API:
- El bot sigue funcionando con datos simulados
- Los contadores de tiempo seguirán siendo precisos
- Solo los marcadores, minutos y estados serán ficticios

---

## Preguntas Frecuentes

**P: ¿Mi API key es segura?**
R: Sí, es solo para lectura. No puede hacer cambios ni gastar dinero.

**P: ¿Puedo compartir mi API key?**
R: No recomendado, pero el riesgo es bajo. Si alguien la usa, solo puede leer datos.

**P: ¿Funciona con todas las ligas?**
R: Sí, con todas excepto NFL. NFL requeriría otra API diferente.

**P: ¿Qué pasa si me olvido de configurar la API?**
R: El bot seguirá funcionando con datos simulados. Verás un mensaje informativo.

---

## Soporte

Si tienes problemas:
1. Verifica que tu API key es correcta en https://www.football-data.org/
2. Asegúrate de que la variable de entorno está configurada correctamente
3. Reinicia la terminal y el bot
4. Intenta nuevamente

¡Listo! Con la API configurada, tendrás datos **reales en vivo** en tu visor de trades. 🎯
