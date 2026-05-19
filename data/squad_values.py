#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
squad_values.py
Valores de plantilla aproximados en millones € (temporada 2024-25).
Fuente: estimaciones basadas en Transfermarkt / UEFA.
Se usan para enriquecer el sistema de estrellas con calidad real de jugadores.

Para equipos no listados se usa una estimación automática basada en
liga + posición en tabla.
"""

# Valor de plantilla en millones € por equipo
# Clave: nombre parcial del equipo (minúsculas) → valor en M€
SQUAD_VALUES: dict = {
    # ── PREMIER LEAGUE ────────────────────────────────────────────
    "manchester city":     1100,
    "arsenal":              980,
    "liverpool":            950,
    "chelsea":              850,
    "manchester united":    700,
    "tottenham":            620,
    "newcastle":            540,
    "aston villa":          490,
    "brighton":             410,
    "west ham":             370,
    "fulham":               290,
    "wolverhampton":        310,
    "brentford":            260,
    "crystal palace":       250,
    "everton":              260,
    "nottingham forest":    240,
    "bournemouth":          220,
    "leicester":            200,
    "southampton":          180,
    "ipswich":              150,

    # ── LA LIGA ───────────────────────────────────────────────────
    "real madrid":         1300,
    "barcelona":           1050,
    "atletico madrid":      780,
    "athletic bilbao":      340,
    "real betis":           290,
    "real sociedad":        270,
    "villarreal":           300,
    "sevilla":              260,
    "valencia":             230,
    "celta vigo":           200,
    "getafe":               120,
    "osasuna":              110,
    "rayo vallecano":       100,
    "girona":               220,
    "mallorca":             130,
    "alaves":               100,
    "espanyol":             130,
    "las palmas":            90,
    "leganes":               90,
    "valladolid":            80,

    # ── BUNDESLIGA ────────────────────────────────────────────────
    "bayer leverkusen":     550,
    "bayern munich":        900,
    "borussia dortmund":    480,
    "rb leipzig":           400,
    "eintracht frankfurt":  290,
    "vfb stuttgart":        280,
    "sc freiburg":          180,
    "borussia monchengladbach": 190,
    "hoffenheim":           160,
    "werder bremen":        160,
    "augsburg":             110,
    "heidenheim":            80,
    "mainz":                130,
    "wolfsburg":            200,
    "union berlin":         160,
    "bochum":                90,
    "holstein kiel":         70,
    "st. pauli":             80,

    # ── SERIE A ───────────────────────────────────────────────────
    "inter milan":          600,
    "juventus":             520,
    "ac milan":             480,
    "napoli":               400,
    "roma":                 380,
    "atalanta":             420,
    "lazio":                300,
    "fiorentina":           250,
    "torino":               160,
    "bologna":              210,
    "udinese":              110,
    "cagliari":             100,
    "genoa":                110,
    "lecce":                 90,
    "parma":                120,
    "verona":                90,
    "empoli":                90,
    "como":                 130,
    "venezia":               90,
    "monza":                150,

    # ── LIGUE 1 ───────────────────────────────────────────────────
    "paris saint-germain":  850,
    "monaco":               380,
    "marseille":            290,
    "lens":                 170,
    "nice":                 210,
    "rennes":               190,
    "lyon":                 250,
    "strasbourg":           130,
    "toulouse":             100,
    "brest":                110,
    "reims":                 90,
    "montpellier":           80,
    "st etienne":            80,
    "auxerre":               70,
    "angers":                70,
    "nantes":               100,
    "le havre":              70,
    "nancy":                 60,

    # ── BRASILEIRAO ───────────────────────────────────────────────
    "flamengo":             200,
    "palmeiras":            190,
    "atletico mineiro":     150,
    "sao paulo":            130,
    "fluminense":           120,
    "gremio":               110,
    "internacional":        100,
    "corinthians":          110,
    "atletico paranaense":   90,
    "cruzeiro":              90,
    "botafogo":             100,
    "bragantino":            80,
    "fortaleza":             70,
    "bahia":                 80,
    "vasco":                 80,
    "criciuma":              50,
    "juventude":             50,
    "vitoria":               50,
    "atletico goianiense":   60,
    "cuiaba":                50,

    # ── COPA LIBERTADORES ─────────────────────────────────────────
    "river plate":          170,
    "boca juniors":         130,
    "racing club":           90,
    "independiente":         70,
    "san lorenzo":           70,
    "estudiantes":           60,
    "club nacional":        100,
    "penarol":               80,
    "colo colo":             70,
    "universidad de chile":  60,
    "liga de quito":         50,
    "barcelon sc":           50,
    "olimpia":               40,
    "cerro porteno":         45,
    "libertad":              40,
    "club bolivar":          40,
    "universidad cesar vallejo": 45,
    "alianza lima":          45,
    "talleres":              70,
    "san pablo":             60,   # São Paulo alias

    # ── MLS ───────────────────────────────────────────────────────
    "inter miami":          160,
    "los angeles fc":        90,
    "la galaxy":             80,
    "seattle sounders":      75,
    "new york city fc":      80,
    "new york red bulls":    70,
    "columbus crew":         65,
    "philadelphia union":    65,
    "atlanta united":        80,
    "fc cincinnati":         70,
    "new england revolution": 60,
    "toronto fc":            60,
    "portland timbers":      60,
    "sporting kansas city":  55,
    "real salt lake":        50,
    "minnesota united":      50,
    "houston dynamo":        50,
    "d.c. united":           50,
    "nashville sc":          60,
    "chicago fire":          55,
    "orlando city":          60,
    "cf montreal":           50,
    "vancouver whitecaps":   55,
    "fc dallas":             50,
    "austin fc":             55,
    "san jose earthquakes":  45,
    "colorado rapids":       45,
    "red bull new york":     70,
    "st. louis city":        50,
    "san diego fc":          45,

    # ── LIGA MX ───────────────────────────────────────────────────
    "club america":         130,
    "guadalajara":           90,
    "cruz azul":             85,
    "tigres uanl":           90,
    "rayados monterrey":     95,
    "pumas unam":            70,
    "toluca":                65,
    "santos laguna":         60,
    "leon":                  65,
    "atlas":                 60,
    "necaxa":                50,
    "queretaro":             45,
    "juarez":                45,
    "mazatlan":              45,
    "puebla":                55,
    "pachuca":               80,
    "san luis":              55,
    "tijuana":               60,
    "veracruz":              45,
    "bravos":                45,

    # ── UCL HABITUALES ─────────────────────────────────────────────
    "celtic":               130,
    "rangers":              120,
    "porto":                230,
    "benfica":              280,
    "sporting cp":          220,
    "ajax":                 220,
    "psv":                  180,
    "feyenoord":            170,
    "club brugge":          140,
    "anderlecht":           100,
    "red bull salzburg":    110,
    "shakhtar donetsk":     150,
    "dinamo zagreb":         80,
    "galatasaray":          120,
    "fenerbahce":           110,
    "besiktas":              80,
    "olympiakos":            70,
    "panathinaikos":         65,
}


# Valor promedio por liga (en M€), para equipos no listados
LEAGUE_AVG_VALUE: dict = {
    "pl":           500,
    "ucl":          400,
    "laliga":       350,
    "bundesliga":   280,
    "seriea":       270,
    "ligue1":       230,
    "libertadores": 100,
    "brasil":        95,
    "superlig":      90,
    "mex":           70,
    "mls":           62,
}

# Rango máximo por liga (para normalizar posición → valor)
LEAGUE_MAX_VALUE: dict = {
    "pl":           1100,
    "ucl":           900,
    "laliga":       1300,
    "bundesliga":    900,
    "seriea":        600,
    "ligue1":        850,
    "libertadores":  200,
    "brasil":        200,
    "superlig":      130,
    "mex":           135,
    "mls":           160,
}


def get_squad_value(team_name: str, league_code: str = "",
                    ppg: float = 1.5, avg_ppg: float = 1.5) -> float:
    """
    Retorna el valor de plantilla estimado en M€.

    1. Si el equipo está en SQUAD_VALUES → valor directo
    2. Si no → estimación basada en liga + rendimiento (PPG relativo)
    """
    name_low = team_name.lower().strip()

    # Búsqueda directa o parcial
    for key, val in SQUAD_VALUES.items():
        if key in name_low or name_low in key:
            return float(val)

    # Búsqueda por palabras clave (ignorar FC, SC, etc.)
    skip_words = {"fc", "sc", "cf", "ac", "if", "bk", "sk", "hc",
                  "club", "the", "de", "del", "los", "las", "el", "la"}
    words = [w for w in name_low.split() if len(w) > 3 and w not in skip_words]
    for key, val in SQUAD_VALUES.items():
        if any(w in key for w in words):
            return float(val)

    # Fallback: estimación por liga + PPG relativo
    avg_val = LEAGUE_AVG_VALUE.get(league_code, 100)
    max_val = LEAGUE_MAX_VALUE.get(league_code, 300)
    ratio   = ppg / max(avg_ppg, 0.5)
    est     = avg_val * max(0.3, min(ratio, 2.5))
    return round(min(est, max_val), 1)
