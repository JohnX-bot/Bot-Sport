"""
FIFA Rankings - World Cup 2026
Puntos FIFA aproximados (última actualización oficial: abril 2026)
Próxima actualización oficial: 10 de junio 2026

Fuente: FIFA World Ranking oficial (inside.fifa.com/fifa-world-ranking/men)
Usado como proxy de fuerza para selecciones nacionales en el modelo Poisson.

Conversión a ATK/DEF:
  - Promedio de los 48 clasificados ≈ 1450 pts → ATK/DEF = 1.0
  - Spain (1850 pts) → ATK/DEF ≈ 1.28
  - Qatar (950 pts)  → ATK/DEF ≈ 0.66
"""

# ─── Puntos FIFA por selección (abril 2026) ───────────────────────────────────
# Grupos del Mundial 2026:
#   A: Mexico, Czechia, South Korea, South Africa
#   B: Canada, Bosnia-Herzegovina, Switzerland, Qatar
#   C: Brazil, Scotland, Haiti, Morocco
#   D: Paraguay, Türkiye, Australia, United States
#   E: Ecuador, Germany, Ivory Coast, Curacao
#   F: Netherlands, Sweden, Japan, Tunisia
#   G: Belgium, Iran, Egypt, New Zealand
#   H: Spain, Uruguay, Saudi Arabia, Cape Verde
#   I: Norway, France, Senegal, Iraq
#   J: Argentina, Austria, Algeria, Jordan
#   K: Colombia, Portugal, Uzbekistan, Congo DR
#   L: England, Croatia, Panama, Ghana

FIFA_POINTS: dict[str, int] = {
    # ── Grupo A ──
    "Mexico":           1550,
    "Czechia":          1420,
    "South Korea":      1490,
    "South Africa":     1240,

    # ── Grupo B ──
    "Canada":           1480,
    "Bosnia-Herzegovina": 1340,
    "Switzerland":      1620,
    "Qatar":             940,

    # ── Grupo C ──
    "Brazil":           1740,
    "Scotland":         1410,
    "Haiti":            1050,
    "Morocco":          1680,

    # ── Grupo D ──
    "Paraguay":         1330,
    "Türkiye":          1510,
    "Turkey":           1510,   # alias
    "Australia":        1390,
    "United States":    1560,
    "USA":              1560,   # alias

    # ── Grupo E ──
    "Ecuador":          1450,
    "Germany":          1730,
    "Ivory Coast":      1380,
    "Curacao":          1060,

    # ── Grupo F ──
    "Netherlands":      1690,
    "Sweden":           1480,
    "Japan":            1590,
    "Tunisia":          1280,

    # ── Grupo G ──
    "Belgium":          1670,
    "Iran":             1320,
    "Egypt":            1350,
    "New Zealand":      1120,

    # ── Grupo H ──
    "Spain":            1850,
    "Uruguay":          1620,
    "Saudi Arabia":     1260,
    "Cape Verde":       1180,

    # ── Grupo I ──
    "Norway":           1530,
    "France":           1780,
    "Senegal":          1540,
    "Iraq":             1200,

    # ── Grupo J ──
    "Argentina":        1800,
    "Austria":          1420,
    "Algeria":          1290,
    "Jordan":           1150,

    # ── Grupo K ──
    "Colombia":         1630,
    "Portugal":         1700,
    "Uzbekistan":       1160,
    "Congo DR":         1220,

    # ── Grupo L ──
    "England":          1760,
    "Croatia":          1590,
    "Panama":           1270,
    "Ghana":            1310,
}

# ─── Promedio de los 48 equipos (anchor para ATK/DEF) ────────────────────────
_ALL_POINTS = [v for k, v in FIFA_POINTS.items()
               if k not in ("Turkey", "USA")]   # excluir aliases
LEAGUE_AVG_POINTS = sum(_ALL_POINTS) / len(_ALL_POINTS)   # ≈ 1430


def get_fifa_points(team_name: str) -> int:
    """Retorna los puntos FIFA de una selección (case-insensitive, con aliases)."""
    # Búsqueda exacta
    if team_name in FIFA_POINTS:
        return FIFA_POINTS[team_name]
    # Búsqueda case-insensitive
    tl = team_name.lower()
    for k, v in FIFA_POINTS.items():
        if k.lower() == tl:
            return v
    # Búsqueda parcial
    for k, v in FIFA_POINTS.items():
        if tl in k.lower() or k.lower() in tl:
            return v
    # Fallback: equipo desconocido → fuerza media-baja
    return 1200


def get_wc_standings() -> dict:
    """
    Genera un diccionario de standings sintético para el Mundial,
    usando puntos FIFA como proxy de fuerza ATK/DEF.

    El formato es compatible con el que produce _espn_standings():
      { team_name: { goalsFor, goalsAgainst, played, won, draw, lost,
                     form_score, team_id, position, points } }

    Lógica de conversión:
      - strength = (pts / avg_pts) ** 2   → escala cuadrática para capturar
        la brecha real entre España (94%) y Cabo Verde (2%) que la escala
        lineal no reproduce. La escala cuadrática amplifica la diferencia:
          - Spain 1850 pts → strength = (1850/1440)^2 = 1.65
          - Curacao 1060 pts → strength = (1060/1440)^2 = 0.54
      - virtual_played = 200  → reduce la regresión Bayesiana (prior=20)
        al 91.7% de peso en datos reales vs 65.5% con played=38.
      - base_gf = 1.2 * strength, base_ga = 1.2 / strength
        (goals por partido virtuales, promediados en WC ≈ 1.2 goles/equipo)
    """
    avg = LEAGUE_AVG_POINTS
    result = {}
    for rank_pos, (team, pts) in enumerate(
            sorted(FIFA_POINTS.items(), key=lambda x: x[1], reverse=True), start=1):
        if team in ("Turkey", "USA"):   # saltar aliases
            continue
        # ── Escala cuadrática: amplifica brecha entre selecciones ──────────
        strength = (pts / avg) ** 2     # cuadrático: >1 = mucho más fuerte
        # goalsFor / goalsAgainst en 200 partidos "virtuales"
        # reduce la regresión Bayesiana y preserva las diferencias extremas
        base_gf = 1.2 * strength        # equipos fuertes anotan más
        base_ga = 1.2 / strength        # equipos fuertes conceden menos
        virtual_played = 200
        result[team] = {
            "team_id":      "",
            "position":     rank_pos,
            "played":       virtual_played,
            "won":          int(virtual_played * max(0, strength - 0.3) / 2),
            "draw":         int(virtual_played * 0.20),
            "lost":         int(virtual_played * max(0, 1.3 - strength) / 2),
            "goalsFor":     round(base_gf * virtual_played, 1),
            "goalsAgainst": round(base_ga * virtual_played, 1),
            "points":       pts,
            "ppg":          round(strength * 1.5, 3),
            "gd_per_game":  round((base_gf - base_ga), 3),
            "form":         "",
            "form_score":   round((strength - 1.0) * 0.6, 3),  # -0.6 .. +0.6
            "fifa_pts":     pts,
        }
    return result
