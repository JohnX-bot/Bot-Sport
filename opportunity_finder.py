#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPPORTUNITY FINDER  -  BotSport
Analiza partidos proximos/en vivo, calcula probabilidades con modelo Poisson,
compara con precios de Polymarket y muestra oportunidades de valor (edge).

Modelo:
  - Poisson Dixon-Coles con fuerza de ataque/defensa de standings
  - Ajuste por forma reciente (ultimos 5 partidos)
  - Ajuste por alineacion (titulares vs suplentes desde ESPN)
  - Comparacion vs Polymarket (precio implicito)
  - Kelly criterion para tamano de apuesta

Uso:
  python opportunity_finder.py              # auto-refresca cada 5 min
  python opportunity_finder.py --once       # una vez y salir
  python opportunity_finder.py --min-edge 0.05  # solo mostrar edge > 5%
  python opportunity_finder.py --league brasil  # solo una liga
"""

import os
import sys
import time
import json
import argparse
import threading
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

try:
    from data.team_logos import get_local_logo
    _HAS_LOCAL_LOGOS = True
except ImportError:
    _HAS_LOCAL_LOGOS = False
    def get_local_logo(name, fallback=""): return fallback

os.system("")
GRN  = "\033[92m"; YLW  = "\033[93m"; RED  = "\033[91m"
CYN  = "\033[96m"; BOLD = "\033[1m";  DIM  = "\033[2m"
RST  = "\033[0m";  BLU  = "\033[94m"; MAG  = "\033[95m"
WHT  = "\033[97m"
def clr(t, c): return f"{c}{t}{RST}"

# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────
MIN_EDGE_DEFAULT  = 0.04   # 4% minimo para mostrar oportunidad
MIN_VOLUME        = 500    # volumen minimo Polymarket ($)
KELLY_FRACTION    = 0.25   # Quarter Kelly (conservador)
REFRESH_INTERVAL  = 300    # 5 minutos

LEAGUES = [
    # ── Ligas activas (las únicas que el bot analiza) ───────────────
    ("pl",           "Premier League",    "eng.1",                "PL"),
    ("laliga",       "La Liga",           "esp.1",                "PD"),
    ("bundesliga",   "Bundesliga",        "ger.1",                "BL1"),
    ("ligue1",       "Ligue 1",           "fra.1",                "FL1"),
    ("seriea",       "Serie A",           "ita.1",                "SA"),
    ("ucl",          "Champions League",  "uefa.champions",       "CL"),
    ("brasil",       "Brasileirao",       "bra.1",                "BSA"),
    ("mex",          "Liga MX",           "mex.1",                None),
    ("mls",          "MLS",               "usa.1",                None),
]

ESPN_BASE  = "https://site.api.espn.com/apis/site/v2/sports/soccer"
GAMMA_BASE = "https://gamma-api.polymarket.com"
FD_BASE    = "https://api.football-data.org/v4"
FD_KEY     = os.getenv("FOOTBALL_DATA_API_KEY", "")

POLY_TAGS = {
    "pl":           ["premier-league"],
    "laliga":       ["la-liga"],
    "bundesliga":   ["bundesliga"],
    "ligue1":       ["ligue-1"],
    "seriea":       ["sea"],            # Slug interno de Polymarket es 'sea', no 'serie-a'
    "ucl":          ["champions-league"],
    "brasil":       ["brazil-serie-a"],
    "mex":          ["mex"],
    "mls":          ["mls"],
}

# ─────────────────────────────────────────────────────────────────
# Importar modelo (con fallback si no existe aun)
# ─────────────────────────────────────────────────────────────────
try:
    from models.poisson_model import (
        calculate_match_probabilities,
        calculate_live_probabilities,
        apply_form_adjustment,
        apply_lineup_adjustment,
        calculate_edge,
        kelly_fraction,
        min_edge_threshold,
    )
    MODEL_OK = True
except ImportError:
    MODEL_OK = False
    def calculate_match_probabilities(ha, hd, aa, ad, **kw):
        h = ha / (ha + aa + 0.5); a = aa / (ha + aa + 0.5); d = 1 - h - a
        return {"home": round(h,4), "draw": round(max(d,0.15),4), "away": round(a,4)}
    def calculate_live_probabilities(lh, la, hg, ag, mp, **kw):
        return calculate_match_probabilities(1.0, 1.0, 1.0, 1.0)
    def apply_form_adjustment(p, hf, af): return p
    def apply_lineup_adjustment(p, hl, al): return p
    def calculate_edge(m, k): return round(m - k, 4)
    def kelly_fraction(m, k, fraction=0.25): return round(max(0, (m-k)/(1-k)) * fraction, 4)
    def min_edge_threshold(prob): return 0.05

# ─────────────────────────────────────────────────────────────────
# Results tracker (historial de predicciones)
# ─────────────────────────────────────────────────────────────────
try:
    import results_tracker as _tracker
    TRACKER_OK = True
except ImportError:
    _tracker = None
    TRACKER_OK = False

# ─────────────────────────────────────────────────────────────────
# Cache global
# ─────────────────────────────────────────────────────────────────
_standings_cache:  Dict[str, Tuple[Dict, float]] = {}   # code -> (data, ts)
_poly_cache:       Dict[str, Dict] = {}
_poly_ts:          float = 0.0
_opps_cache:       List[Dict] = []
_schedule_cache:   Dict[str, Tuple] = {}  # "{espn_id}_{team_id}" -> ([games], ts)
_stars_cache:      Dict[str, Tuple] = {}  # espn_id -> ({name: stars}, ts)
_data_lock = threading.Lock()

SCHEDULE_CACHE_TTL = 14400   # 4 horas
STARS_CACHE_TTL    = 7200    # 2 horas

# ─────────────────────────────────────────────────────────────────
# TEAM RATINGS: ⭐ Estrellas + Forma ajustada por calidad de rival
# ─────────────────────────────────────────────────────────────────

def compute_league_stars(standings: Dict, league_code: str = "") -> Dict[str, int]:
    """
    Sistema de estrellas multi-factor (1-5) normalizado DENTRO de la liga.

    ┌─────────────────────────────────────────────────────────────────┐
    │  RENDIMIENTO DEPORTIVO             40 %                         │
    │    PPG (puntos por partido)        20 %  – resultados           │
    │    Eficiencia ofensiva (GF/90)     10 %  – poder de ataque      │
    │    Solidez defensiva (GA/90 inv.)  10 %  – porterías a cero     │
    ├─────────────────────────────────────────────────────────────────┤
    │  CALIDAD DE PLANTILLA              25 %                         │
    │    Valor de mercado (Transfermarkt)25 %  – profundidad + talento│
    ├─────────────────────────────────────────────────────────────────┤
    │  DOMINIO DEL JUEGO – proxies       20 %                         │
    │    xG proxy: GD/90 (goles netos)  10 %  – dominancia real      │
    │    Forma reciente ponderada        10 %  – tendencia actual     │
    ├─────────────────────────────────────────────────────────────────┤
    │  PRESTIGIO HISTÓRICO               15 %                         │
    │    Score estático de reputación    15 %  – peso camiseta / UCL  │
    └─────────────────────────────────────────────────────────────────┘

    Proxies usados (datos gratuitos disponibles):
      - xG real → GD/90 (diferencia de goles neta por partido)
      - PPDA    → forma reciente vs calidad de rival (QoA)
      - Balón   → relación ataque/defensa (GF vs GA normalizado)
      - Portería a cero → GA/90 invertida (< 0.8 ga/game = elite)
    """
    try:
        from data.squad_values import get_squad_value
        _sv_ok = True
    except ImportError:
        _sv_ok = False

    # ── Prestigio histórico (reputación, pedigree UCL / internacional) ──
    # Score 0.0–1.0; equipos no listados → estimación por valor de plantilla
    _PRESTIGE: Dict[str, float] = {
        # Élite mundial (1.0)
        "real madrid": 1.00, "manchester united": 0.96,
        "liverpool": 0.94,   "fc barcelona": 0.94,  "barcelona": 0.94,
        "bayern munich": 0.93, "fc bayern": 0.93,
        "juventus": 0.90,    "ac milan": 0.89,
        "chelsea": 0.87,     "arsenal": 0.85,
        "inter milan": 0.85, "paris saint-germain": 0.83, "psg": 0.83,
        "manchester city": 0.82, "atletico madrid": 0.82,
        "atletico de madrid": 0.82,
        # Europa top (0.70–0.80)
        "tottenham": 0.72,   "borussia dortmund": 0.75,
        "ajax": 0.76,        "porto": 0.74,   "benfica": 0.72,
        "sporting cp": 0.68, "eintracht frankfurt": 0.65,
        "bayer leverkusen": 0.67, "rb leipzig": 0.65,
        "napoli": 0.68,      "roma": 0.66,    "lazio": 0.64,
        "sevilla": 0.68,     "real sociedad": 0.60,
        "villarreal": 0.62,  "athletic bilbao": 0.60, "athletic club": 0.60,
        "olympique de marseille": 0.65, "marseille": 0.65,
        "olympique lyonnais": 0.63,    "lyon": 0.63,
        "monaco": 0.60,      "lille": 0.58,
        "psv": 0.65,         "feyenoord": 0.63,
        # Américas (0.50–0.65)
        "flamengo": 0.63,    "palmeiras": 0.61, "atletico mineiro": 0.58,
        "river plate": 0.62, "boca juniors": 0.60,
        "club america": 0.58, "chivas": 0.55, "guadalajara": 0.55,
        "tigres": 0.52,      "santos laguna": 0.50,
        "inter miami": 0.52, "la galaxy": 0.50,
        # Resto → 0.40 por defecto (asignado dinámicamente abajo)
    }

    def _prestige_score(name: str, sv: float) -> float:
        """Busca el score de prestigio; si no está, lo estima por valor de plantilla."""
        name_low = name.lower().strip()
        for k, v in _PRESTIGE.items():
            if k in name_low or name_low in k:
                return v
        # Fallback: escalar valor de plantilla en rango 0.3–0.75
        return min(0.75, max(0.30, (sv / 1300.0) ** 0.45))

    # ── Filtrar equipos con datos suficientes ───────────────────────
    teams = {n: d for n, d in standings.items() if d.get("played", 0) >= 3}
    if len(teams) < 3:
        return {n: 3 for n in standings}

    avg_ppg = sum(d.get("ppg", 1.5) for d in teams.values()) / len(teams)

    # ── Función de normalización min-max 0→1 ────────────────────────
    def _norm(d: Dict) -> Dict:
        vals = list(d.values())
        mn, mx = min(vals), max(vals)
        rng = mx - mn
        if rng < 0.001:
            return {k: 0.5 for k in d}
        return {k: (v - mn) / rng for k, v in d.items()}

    # ── 1. Rendimiento deportivo ─────────────────────────────────────
    ppgs = {n: d.get("ppg", 0) for n, d in teams.items()}

    # Goles anotados por partido (ofensiva)
    gf_per90 = {
        n: d.get("goalsFor", 0) / max(d.get("played", 1), 1)
        for n, d in teams.items()
    }
    # Goles concedidos por partido INVERTIDOS (menor GA = mejor defensa)
    # Usamos max_ga como referencia para la inversión
    ga_raw = {
        n: d.get("goalsAgainst", 0) / max(d.get("played", 1), 1)
        for n, d in teams.items()
    }
    max_ga = max(ga_raw.values()) if ga_raw else 1.0
    ga_inv = {n: max_ga - v for n, v in ga_raw.items()}   # mayor = mejor defensa

    # ── 2. Calidad de plantilla ──────────────────────────────────────
    if _sv_ok:
        sq_vals = {
            n: get_squad_value(n, league_code, d.get("ppg", 1.5), avg_ppg)
            for n, d in teams.items()
        }
    else:
        sq_vals = {n: d.get("ppg", 1.5) * 100 for n, d in teams.items()}

    # ── 3. Dominio del juego (proxies) ───────────────────────────────
    # xG proxy: diferencia de goles por partido (GD/90)
    gd_per90 = {n: d.get("gd_per_game", 0) for n, d in teams.items()}
    # Forma reciente
    forms = {n: d.get("form_score", 0) for n, d in teams.items()}

    # ── 4. Prestigio histórico ───────────────────────────────────────
    prestige = {n: _prestige_score(n, sq_vals[n]) for n in teams}

    # ── Normalizar componentes dentro de la liga (min-max) ──────────
    n_ppg  = _norm(ppgs)
    n_gf   = _norm(gf_per90)
    n_ga   = _norm(ga_inv)
    n_sq   = _norm(sq_vals)
    n_gd   = _norm(gd_per90)
    n_form = _norm(forms)

    # Prestigio: escala GLOBAL fija (0.30=mínimo global, 1.0=élite mundial)
    # No se normaliza dentro de la liga para no inflar diferencias pequeñas.
    # Ejemplo: Athletic(0.60) vs Sevilla(0.68) → diferencia real ≈ 8 pts,
    # no amplificada a 0% vs 100% como haría min-max intra-liga.
    _PRESTIGE_MIN = 0.30
    _PRESTIGE_MAX = 1.00
    n_prestige = {
        n: (prestige[n] - _PRESTIGE_MIN) / (_PRESTIGE_MAX - _PRESTIGE_MIN)
        for n in teams
    }

    # ── Score final ponderado ─────────────────────────────────────────
    # Pesos siguiendo la propuesta del usuario:
    #   Rendimiento Deportivo  40% → PPG(20%) + GF(10%) + GA(10%)
    #   Calidad de Plantilla   20% → Valor de mercado
    #   Dominio del Juego      25% → GD/90-xG proxy(12%) + Forma(13%)
    #   Prestigio Histórico    15% → Reputación / historial internacional
    scores = {
        n: (
            n_ppg[n]       * 0.20 +   # Rendimiento: PPG
            n_gf[n]        * 0.10 +   # Rendimiento: ataque (GF/90)
            n_ga[n]        * 0.10 +   # Rendimiento: defensa (GA/90 inv.)
            n_sq[n]        * 0.20 +   # Calidad: valor plantilla
            n_gd[n]        * 0.12 +   # Dominio: xG proxy (GD neto)
            n_form[n]      * 0.13 +   # Dominio: forma reciente
            n_prestige[n]  * 0.15     # Prestigio: historial / UCL
        )
        for n in teams
    }

    # ── Asignar estrellas por quintiles ──────────────────────────────
    sorted_vals = sorted(scores.values())
    q = len(sorted_vals)
    thresholds = [
        sorted_vals[max(0, int(q * 0.20) - 1)],
        sorted_vals[max(0, int(q * 0.40) - 1)],
        sorted_vals[max(0, int(q * 0.60) - 1)],
        sorted_vals[max(0, int(q * 0.80) - 1)],
    ]

    stars_map: Dict[str, int] = {}
    for n, sc in scores.items():
        if sc < thresholds[0]:   stars_map[n] = 1
        elif sc < thresholds[1]: stars_map[n] = 2
        elif sc < thresholds[2]: stars_map[n] = 3
        elif sc < thresholds[3]: stars_map[n] = 4
        else:                    stars_map[n] = 5

    # Equipos sin datos suficientes → 3 estrellas (media)
    for n in standings:
        stars_map.setdefault(n, 3)

    return stars_map


def _fetch_team_schedule(espn_id: str, team_id: str) -> List[Dict]:
    """
    Últimos 8 partidos terminados de un equipo desde ESPN.
    Retorna lista de {opp_name, my_score, opp_score, result}.
    Cachea 4 horas.
    """
    if not team_id:
        return []
    key = f"{espn_id}_{team_id}"
    if key in _schedule_cache:
        data, ts = _schedule_cache[key]
        if time.time() - ts < SCHEDULE_CACHE_TTL:
            return data

    try:
        url = f"{ESPN_BASE}/{espn_id}/teams/{team_id}/schedule"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            # Cache corto si falla (30 min) para reintentar pronto
            _schedule_cache[key] = ([], time.time() - SCHEDULE_CACHE_TTL + 1800)
            return []

        events = r.json().get("events", [])
        finished = []
        for e in events:
            comp  = e.get("competitions", [{}])[0]
            state = comp.get("status", {}).get("type", {}).get("state", "")
            if state != "post":
                continue
            competitors = comp.get("competitors", [])
            home_c = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away_c = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home_c or not away_c:
                continue

            is_home  = str(home_c.get("team", {}).get("id", "")) == str(team_id)
            my_c     = home_c if is_home else away_c
            opp_c    = away_c if is_home else home_c
            opp_name = opp_c.get("team", {}).get("displayName", "")

            # Score puede ser dict {value, displayValue} o string
            def _score(comp_obj):
                s = comp_obj.get("score", 0)
                if isinstance(s, dict):
                    return int(float(s.get("value", 0) or s.get("displayValue", 0) or 0))
                try: return int(float(s or 0))
                except: return 0

            ms = _score(my_c)
            os = _score(opp_c)

            result = "W" if ms > os else ("D" if ms == os else "L")
            finished.append({"opp_name": opp_name, "my_score": ms,
                              "opp_score": os, "result": result})

        # ESPN devuelve eventos MÁS RECIENTE → MÁS VIEJO.
        # Tomamos los 8 PRIMEROS (= 8 más recientes) y los invertimos
        # para guardarlos cronológicamente (viejo → reciente).
        recent_first_oldest = list(reversed(finished[:8]))
        if recent_first_oldest:
            _schedule_cache[key] = (recent_first_oldest, time.time())
        else:
            # Si viene vacío, cache corto (30 min) para reintentar
            _schedule_cache[key] = ([], time.time() - SCHEDULE_CACHE_TTL + 1800)
        return recent_first_oldest
    except Exception:
        # En caso de error, cache corto (30 min)
        _schedule_cache[key] = ([], time.time() - SCHEDULE_CACHE_TTL + 1800)
        return []


def get_form5(games: List[Dict]) -> List[str]:
    """Retorna los últimos 5 resultados como lista ["W","D","L","W","W"]."""
    return [g["result"] for g in games[-5:]] if games else []


def quality_adjusted_form(
    games: List[Dict],
    stars_map: Dict[str, int],
) -> Dict:
    """
    Forma ponderada por calidad del rival (Quality of Opposition).

    Principio: ganar a equipos de 5⭐ vale mucho más que ganar a equipos de 1⭐.
    Perder contra 1⭐ es muy penalizante; perder contra 5⭐ es normal.

    Retorna {qa_form: -1..1, opp_avg_stars: 1-5, opp_quality: str}.
    """
    if not games:
        return {"qa_form": 0.0, "opp_avg_stars": 3.0, "opp_quality": "?"}

    weighted = []
    opp_stars_list = []

    for g in games:
        # Buscar estrellas del rival
        opp_name  = g.get("opp_name", "")
        opp_stars = 3
        for sname, st in stars_map.items():
            if _sim(opp_name, sname):
                opp_stars = st
                break
        opp_stars_list.append(opp_stars)

        result = g.get("result", "D")
        val    = {"W": 1.0, "D": 0.5, "L": 0.0}[result]

        # Pesos asimétricos: ganar a 5⭐ premia mucho, perder con 1⭐ castiga mucho
        if result == "W":
            weight = 0.4 + (opp_stars - 1) * 0.5   # 0.4 (1⭐) → 2.4 (5⭐)
        elif result == "L":
            weight = 1.8 - (opp_stars - 1) * 0.3   # 0.6 (5⭐) → 1.8 (1⭐)
        else:
            weight = 1.0 + (opp_stars - 3) * 0.1   # empate pesa igual ±ajuste

        weighted.append((val, weight))

    total_w = sum(w for _, w in weighted) or 1
    qa_raw  = sum(v * w for v, w in weighted) / total_w
    qa_form = round((qa_raw - 0.5) * 2, 3)   # 0..1 → -1..1

    avg_stars = round(sum(opp_stars_list) / len(opp_stars_list), 1)
    opp_quality = "Alta" if avg_stars >= 3.5 else ("Media" if avg_stars >= 2.5 else "Baja")

    return {
        "qa_form":       qa_form,
        "opp_avg_stars": avg_stars,
        "opp_quality":   opp_quality,
    }


# ─────────────────────────────────────────────────────────────────
# 1. STANDINGS / FUERZA DE EQUIPOS (football-data.org + ESPN fallback)
# ─────────────────────────────────────────────────────────────────
FD_COMP = {"pl":"PL","laliga":"PD","bundesliga":"BL1","ligue1":"FL1",
           "seriea":"SA","brasil":"BSA","ucl":"CL","libertadores":"CLI"}

# Ligas soportadas solo por ESPN (sin football-data.org)
ESPN_ONLY = {"mls","mex","superlig"}


def _espn_standings(espn_id: str) -> Dict:
    """
    Obtiene standings desde ESPN (gratis, sin API key).
    Combina todas las conferencias/grupos en un solo dict.
    Retorna {team_name: {goalsFor, goalsAgainst, played, won, draw, lost, form_score, team_id}}
    Incluye team_id para poder buscar el schedule individual de cada equipo.
    """
    try:
        url = f"https://site.api.espn.com/apis/v2/sports/soccer/{espn_id}/standings"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return {}
        data = r.json()
        result = {}
        children = data.get("children", [data])
        for child in children:
            entries = child.get("standings", {}).get("entries", [])
            for idx, entry in enumerate(entries, start=1):
                team_obj = entry.get("team", {})
                name    = team_obj.get("displayName", "")
                team_id = str(team_obj.get("id", ""))
                if not name:
                    continue
                stats = {s["name"]: s.get("displayValue", "0")
                         for s in entry.get("stats", [])}
                def _int(k):
                    try: return int(float(stats.get(k, 0)))
                    except: return 0
                # Posición en tabla: primero intentar campo "rank" de ESPN,
                # si no existe usar el índice del entry (ya viene ordenado)
                pos = _int("rank") or idx
                played = _int("gamesPlayed")
                won    = _int("wins")
                draw   = _int("ties")
                lost   = _int("losses")
                gf     = _int("pointsFor")
                ga     = _int("pointsAgainst")
                form_score = round((won - lost) / max(played, 1), 3)
                ppg        = round((won * 3 + draw) / max(played, 1), 3)
                gd_pg      = round((gf - ga) / max(played, 1), 3)
                result[name] = {
                    "team_id":      team_id,
                    "position":     pos,
                    "played":       max(played, 1),
                    "won":          won,
                    "draw":         draw,
                    "lost":         lost,
                    "goalsFor":     gf,
                    "goalsAgainst": ga,
                    "points":       won * 3 + draw,
                    "ppg":          ppg,
                    "gd_per_game":  gd_pg,
                    "form":         "",
                    "form_score":   form_score,
                }
        return result
    except Exception as e:
        print(f"[ESPN-Standings] error {espn_id}: {e}")
        return {}


def get_standings(league_code: str, espn_id: str = "") -> Dict:
    """
    Retorna {team_name: {goalsFor, goalsAgainst, played, won, draw, lost, form/form_score}}.
    Fuente: football-data.org para ligas europeas, ESPN para el resto.
    """
    cached, ts = _standings_cache.get(league_code, ({}, 0.0))
    if time.time() - ts < 3600 and cached:
        return cached

    comp = FD_COMP.get(league_code)

    # Intentar football-data.org para ligas europeas
    if comp and FD_KEY:
        try:
            r = requests.get(f"{FD_BASE}/competitions/{comp}/standings",
                headers={"X-Auth-Token": FD_KEY}, timeout=8)
            if r.status_code == 429:
                return cached
            if r.status_code == 200:
                table = r.json().get("standings", [{}])[0].get("table", [])
                result = {}
                for row in table:
                    name = row.get("team", {}).get("name", "")
                    if name:
                        form_str = row.get("form") or ""
                        result[name] = {
                            "id":           row.get("team", {}).get("id"),
                            "position":     row.get("position", 0),
                            "played":       row.get("playedGames", 1),
                            "won":          row.get("won", 0),
                            "draw":         row.get("draw", 0),
                            "lost":         row.get("lost", 0),
                            "goalsFor":     row.get("goalsFor", 0),
                            "goalsAgainst": row.get("goalsAgainst", 0),
                            "points":       row.get("points", 0),
                            "form":         form_str,
                        }
                if result:
                    _standings_cache[league_code] = (result, time.time())
                    return result
        except Exception as e:
            print(f"[FD] standings error {league_code}: {e}")

    # Fallback: ESPN standings (gratis)
    if espn_id:
        result = _espn_standings(espn_id)
        if result:
            _standings_cache[league_code] = (result, time.time())
            print(f"[ESPN-Standings] {league_code}: {len(result)} equipos cargados")
            return result

    return cached


def team_strengths(standings: Dict, home_team: str, away_team: str) -> Dict:
    """
    Calcula attack/defense strength relativo al promedio de la liga.
    Retorna valores neutrales (1.0) si no hay datos.
    """
    if not standings:
        return {"home_attack":1.0,"home_defense":1.0,"home_form":0.0,
                "away_attack":1.0,"away_defense":1.0,"away_form":0.0,
                "league_avg":2.6}

    # Promedio de la liga
    total_gf = total_gc = total_played = 0
    for s in standings.values():
        total_gf    += s.get("goalsFor", 0)
        total_gc    += s.get("goalsAgainst", 0)
        total_played += s.get("played", 1)

    teams = len(standings) or 1
    avg_scored    = total_gf / total_played if total_played else 1.3
    avg_conceded  = total_gc / total_played if total_played else 1.3
    league_avg    = avg_scored + avg_conceded   # total goals per game

    def find(name: str):
        n = name.lower()
        for k, v in standings.items():
            if k.lower() == n or n in k.lower() or k.lower() in n:
                return v
        return None

    def parse_form(form_str) -> float:
        """WWDLW -> score -1..+1, recientes pesan mas"""
        if not form_str:
            return 0.0
        weights = [0.35, 0.25, 0.20, 0.12, 0.08]
        chars = list(reversed(str(form_str).replace(",", "")))[:5]
        score = 0.0
        for i, c in enumerate(chars):
            w = weights[i] if i < len(weights) else 0.05
            if c == "W": score += w
            elif c == "L": score -= w
        return round(score, 3)

    def strengths(team_data):
        if not team_data:
            return 1.0, 1.0, 0.0
        played = max(team_data.get("played", 1), 1)
        att_raw = (team_data.get("goalsFor", 0) / played) / avg_scored if avg_scored else 1.0
        dfs_raw = (team_data.get("goalsAgainst", 0) / played) / avg_conceded if avg_conceded else 1.0
        # ── Regresión bayesiana a la media ──────────────────────────
        # Prior: 20 partidos "virtuales" al promedio de liga (1.0).
        # Con pocos partidos hay más incertidumbre → más regresión.
        # Evita que un equipo con 5 partidos perfectos domine el modelo.
        PRIOR = 20
        w = played / (played + PRIOR)           # peso de datos reales
        att = w * att_raw + (1 - w) * 1.0
        dfs = w * dfs_raw + (1 - w) * 1.0
        # Clamp extra: nunca más de ±50% del promedio (reduce extremos finales)
        att = max(0.50, min(att, 1.50))
        dfs = max(0.50, min(dfs, 1.50))
        # Usar form_score pre-calculado (ESPN) o parsear string de forma (FD)
        if "form_score" in team_data:
            form = team_data["form_score"]
        else:
            form = parse_form(team_data.get("form", ""))
        return round(att, 3), round(dfs, 3), form

    h_data = find(home_team)
    a_data = find(away_team)

    h_att, h_def, h_form = strengths(h_data)
    a_att, a_def, a_form = strengths(a_data)

    return {
        "home_attack":  h_att,
        "home_defense": h_def,
        "home_form":    h_form,
        "away_attack":  a_att,
        "away_defense": a_def,
        "away_form":    a_form,
        "league_avg":   round(league_avg, 2),
    }


# ─────────────────────────────────────────────────────────────────
# RELOJ EN VIVO (copiado de live_viewer.py)
# ─────────────────────────────────────────────────────────────────
_stable_clocks: Dict[str, tuple] = {}   # { "Home_Away": (base_secs, set_at_ts) }

def _update_stable_clock(key: str, new_secs: float) -> tuple:
    """Reloj monotónico por partido (nunca retrocede)."""
    now = time.time()
    if key not in _stable_clocks:
        _stable_clocks[key] = (new_secs, now)
        return new_secs, now
    base_secs, set_at = _stable_clocks[key]
    running = base_secs + (now - set_at)
    if new_secs >= running - 5:
        _stable_clocks[key] = (new_secs, now)
        return new_secs, now
    return base_secs, set_at

def _calc_minute(utc_str: str, status: str) -> Optional[int]:
    """Calcula el minuto actual desde la hora de inicio."""
    try:
        ko = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - ko).total_seconds() / 60
        if elapsed < 0:
            return None
        if status in ("PAUSED", "halftime"):
            return 45
        if elapsed <= 45:
            return int(elapsed)
        elif elapsed <= 60:
            return 45
        elif elapsed <= 115:
            return int(elapsed - 15)
        return 90
    except Exception:
        return None

def _live_minute_str(match_key: str, period: int, halftime: bool,
                     clock_secs: float = 0.0) -> str:
    """Devuelve string del minuto para incluir en el HTML como data attribute."""
    if halftime:
        return "HT"
    if match_key in _stable_clocks:
        base, set_at = _stable_clocks[match_key]
        mins = int((base + (time.time() - set_at)) // 60)
    else:
        mins = int(clock_secs // 60)
    if period == 1:
        return f"45+" + str(mins - 45) if mins >= 45 else str(mins)
    else:
        return f"90+" + str(mins - 90) if mins >= 90 else str(mins)


# ─────────────────────────────────────────────────────────────────
# 2. ESPN: partidos proximos + alineaciones
# ─────────────────────────────────────────────────────────────────
def get_fd_matches(comp_id: str, league_code: str, league_name: str) -> List[Dict]:
    """Obtiene matches de football-data.org (proximos 7 dias)."""
    if not FD_KEY:
        return []
    try:
        r = requests.get(f"{FD_BASE}/competitions/{comp_id}/matches",
            headers={"X-Auth-Token": FD_KEY},
            params={"status": "SCHEDULED,LIVE"},
            timeout=8)
        if r.status_code != 200:
            return []

        matches = []
        now = datetime.now(timezone.utc)
        limit_date = now + timedelta(days=7)

        for m in r.json().get("matches", []):
            date_str = m.get("utcDate", "")
            try:
                match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if match_date > limit_date:
                    continue
            except:
                continue

            home = m.get("homeTeam", {}).get("name", "?")
            away = m.get("awayTeam", {}).get("name", "?")
            status = m.get("status", "").lower()
            # FD usa: SCHEDULED, TIMED (programado con hora), IN_PLAY, PAUSED, FINISHED
            state = "pre" if status in ("scheduled", "timed") else "in"

            matches.append({
                "event_id":    m.get("id", ""),
                "league_code": league_code,
                "league_name": league_name,
                "home_team":   home,
                "away_team":   away,
                "home_score":  m.get("score", {}).get("fullTime", {}).get("home"),
                "away_score":  m.get("score", {}).get("fullTime", {}).get("away"),
                "status":      state,
                "date":        date_str,
                "source":      "fd",
            })

        return matches
    except Exception:
        return []


def find_espn_event_id(espn_id: str, home_team: str, away_team: str, date_str: str) -> str:
    """Busca el event_id de ESPN para un partido por equipos y fecha."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        date_param = dt.strftime("%Y%m%d")

        r = requests.get(f"{ESPN_BASE}/{espn_id}/scoreboard",
            params={"dates": date_param}, timeout=6)
        if r.status_code != 200:
            return ""

        # Palabras clave de cada equipo (ignorar palabras cortas)
        def keywords(name: str):
            return [w.lower() for w in name.split() if len(w) > 3]

        h_kw = keywords(home_team)
        a_kw = keywords(away_team)

        for evt in r.json().get("events", []):
            comp  = evt.get("competitions", [{}])[0]
            teams = comp.get("competitors", [])
            if len(teams) < 2:
                continue
            names = [t.get("team", {}).get("displayName", "").lower() for t in teams]
            names_str = " ".join(names)
            h_match = any(w in names_str for w in h_kw)
            a_match = any(w in names_str for w in a_kw)
            if h_match and a_match:
                return evt.get("id", "")
        return ""
    except Exception:
        return ""


def get_espn_matches(espn_id: str, league_code: str, league_name: str) -> List[Dict]:
    """
    Obtiene partidos de ESPN para los proximos 7 dias.
    Itera cada fecha individualmente (ESPN no acepta multiples fechas
    en el parametro dates= y sin fecha solo devuelve el dia actual).
    """
    now       = datetime.now(timezone.utc)
    matches   = []
    seen_ids  = set()

    # Logo del equipo — primero local (Escudos/), fallback ESPN CDN
    def _logo(team_obj):
        name = team_obj.get("displayName", "")
        # Intentar ESPN CDN como fallback
        logos = team_obj.get("logos", [])
        if logos:
            cdn_url = logos[0].get("href", "")
        else:
            tid = str(team_obj.get("id", ""))
            cdn_url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png" if tid else ""
        # Preferir logo local si existe
        return get_local_logo(name, cdn_url)

    def _parse_events(events: list) -> None:
        for evt in events:
            eid = evt.get("id", "")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)

            state = evt.get("status", {}).get("type", {}).get("state", "")
            if state not in ("in", "halftime", "pre", "post"):
                continue

            date_str_evt = evt.get("date", "")
            try:
                match_date = datetime.fromisoformat(date_str_evt.replace("Z", "+00:00"))
                if state == "post" and (now - match_date).days > 1:
                    continue   # terminados de mas de ayer: ignorar
            except Exception:
                pass

            comp  = evt.get("competitions", [{}])[0]
            teams = comp.get("competitors", [])
            if len(teams) < 2:
                continue
            home_t = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
            away_t = next((t for t in teams if t.get("homeAway") == "away"), teams[1])

            status_obj  = evt.get("status", {})
            clock_secs  = float(status_obj.get("clock", 0.0) or 0.0)
            period      = int(status_obj.get("period", 1) or 1)
            desc        = status_obj.get("type", {}).get("description", "")
            is_halftime = ("Halftime" in desc or state == "halftime")

            home_obj  = home_t.get("team", {})
            away_obj  = away_t.get("team", {})
            home_name = home_obj.get("displayName", "?")
            away_name = away_obj.get("displayName", "?")
            mkey = f"{home_name}_{away_name}"
            if state in ("in", "halftime"):
                _update_stable_clock(mkey, clock_secs)

            matches.append({
                "event_id":     eid,
                "league_code":  league_code,
                "league_name":  league_name,
                "home_team":    home_name,
                "away_team":    away_name,
                "home_score":   home_t.get("score", "0"),
                "away_score":   away_t.get("score", "0"),
                "home_logo":    _logo(home_obj),
                "away_logo":    _logo(away_obj),
                "home_team_id": str(home_obj.get("id", "")),
                "away_team_id": str(away_obj.get("id", "")),
                "status":       state,
                "date":         date_str_evt,
                "clock_secs":   clock_secs,
                "period":       period,
                "halftime":     is_halftime,
                "match_key":    mkey,
            })

    # ── 1. Llamada sin fecha → partidos en vivo / jornada actual ──
    try:
        r = requests.get(f"{ESPN_BASE}/{espn_id}/scoreboard", timeout=6)
        if r.status_code == 200:
            _parse_events(r.json().get("events", []))
    except Exception:
        pass

    # ── 2. Iterar los proximos 7 dias para no perder jornadas futuras ──
    for day_offset in range(0, 7):
        date_param = (now + timedelta(days=day_offset)).strftime("%Y%m%d")
        try:
            r = requests.get(
                f"{ESPN_BASE}/{espn_id}/scoreboard",
                params={"dates": date_param},
                timeout=6,
            )
            if r.status_code == 200:
                _parse_events(r.json().get("events", []))
        except Exception:
            pass

    return matches


def get_espn_detail(espn_id: str, event_id: str) -> Dict:
    """
    Obtiene detalle del partido: formaciones, alineaciones, odds de DraftKings, H2H.
    """
    try:
        r = requests.get(f"{ESPN_BASE}/{espn_id}/summary?event={event_id}", timeout=8)
        if r.status_code != 200:
            return {}
        data = r.json()

        # Formaciones y alineaciones
        rosters = data.get("rosters", [])
        home_roster = next((x for x in rosters if x.get("homeAway") == "home"), {})
        away_roster = next((x for x in rosters if x.get("homeAway") == "away"), {})

        def parse_roster(ros):
            formation = ros.get("formation", "")
            starters  = []
            for p in ros.get("roster", []):
                if p.get("starter"):
                    athlete = p.get("athlete", {})
                    stats_list = p.get("stats", [])
                    stats = {s["abbreviation"]: s.get("value", 0)
                             for s in stats_list if "abbreviation" in s}
                    starters.append({
                        "name":     athlete.get("displayName", "?"),
                        "position": p.get("position", {}).get("abbreviation", "?"),
                        "jersey":   p.get("jersey", ""),
                        "goals":    stats.get("G", 0),
                        "assists":  stats.get("A", 0),
                        "shots":    stats.get("SH", 0),
                        "yellow":   stats.get("YC", 0),
                        "red":      stats.get("RC", 0),
                    })
            return formation, starters

        home_formation, home_starters = parse_roster(home_roster)
        away_formation, away_starters = parse_roster(away_roster)

        # Odds DraftKings (American moneyline -> implied prob)
        odds = data.get("odds", [])
        home_ml = away_ml = None
        home_impl = away_impl = draw_impl = None
        if odds:
            o = odds[0]
            home_ml = o.get("homeTeamOdds", {}).get("moneyLine")
            away_ml = o.get("awayTeamOdds", {}).get("moneyLine")
            if home_ml:
                home_impl = 100/(home_ml+100) if home_ml > 0 else abs(home_ml)/(abs(home_ml)+100)
            if away_ml:
                away_impl = 100/(away_ml+100) if away_ml > 0 else abs(away_ml)/(abs(away_ml)+100)
            if home_impl and away_impl:
                # Corregir sobreround
                total = home_impl + away_impl
                draw_impl  = round(max(0.05, 1 - home_impl - away_impl), 3)
                home_impl  = round(home_impl / (total + draw_impl * total), 3)
                away_impl  = round(away_impl / (total + draw_impl * total), 3)

        # H2H ultimos partidos
        h2h_raw  = data.get("headToHeadGames", [])
        h2h = []
        for g in h2h_raw[:5]:
            comp = g.get("competitions", [{}])[0] if g.get("competitions") else {}
            competitors = comp.get("competitors", [])
            if len(competitors) >= 2:
                h2h.append({
                    "home": competitors[0].get("team", {}).get("displayName", "?"),
                    "away": competitors[1].get("team", {}).get("displayName", "?"),
                    "home_score": competitors[0].get("score", "?"),
                    "away_score": competitors[1].get("score", "?"),
                })

        return {
            "home_formation": home_formation,
            "away_formation": away_formation,
            "home_starters":  home_starters,
            "away_starters":  away_starters,
            "home_ml":        home_ml,
            "away_ml":        away_ml,
            "home_implied":   home_impl,
            "away_implied":   away_impl,
            "draw_implied":   draw_impl,
            "h2h":            h2h,
        }
    except Exception as e:
        return {}


# ─────────────────────────────────────────────────────────────────
# 3. POLYMARKET: precios de cada partido
# ─────────────────────────────────────────────────────────────────
def fetch_poly_all() -> Dict[str, Dict]:
    global _poly_cache, _poly_ts
    if time.time() - _poly_ts < 90:
        return _poly_cache

    result: Dict[str, List[Dict]] = {}   # key → lista de variantes (puede haber varias por título)
    seen = set()
    for tags in POLY_TAGS.values():
        for tag in tags:
            if tag in seen: continue
            seen.add(tag)
            try:
                r = requests.get(f"{GAMMA_BASE}/events",
                    params={"active":"true","closed":"false","limit":50,"tag_slug":tag},
                    timeout=6)
                if r.status_code != 200: continue
                for evt in r.json() if isinstance(r.json(), list) else []:
                    title = evt.get("title", "")
                    # Saltar mercados especiales (Exact Score, Halftime, More Markets, etc.)
                    if any(x in title for x in (" - Exact Score", " - Halftime", " - More Markets", " - O/U", " - Spread")):
                        continue
                    if " vs." not in title and " vs " not in title: continue
                    norm = title.replace(" vs.", " vs ")
                    parts = norm.split(" vs ")
                    if len(parts) < 2: continue
                    ph, pa = parts[0].strip(), parts[1].strip()

                    # Fechas del evento (start/end)
                    start_date = evt.get("startDate", "") or ""
                    end_date   = evt.get("endDate", "") or ""

                    hp = dp = ap = None
                    vol = 0.0
                    for m in evt.get("markets", []):
                        if m.get("closed", True) or not m.get("active"): continue
                        q = m.get("question", "").lower()
                        pr = m.get("outcomePrices", "[]")
                        if isinstance(pr, str):
                            try: pr = json.loads(pr)
                            except: pr = []
                        if not pr: continue
                        try: p0 = round(float(pr[0]), 3)
                        except: continue
                        try: vol += float(m.get("volume") or 0)
                        except: pass

                        if "draw" in q:
                            dp = p0
                        elif "win" in q:
                            h_words = [w for w in ph.lower().split() if len(w) > 3]
                            a_words = [w for w in pa.lower().split() if len(w) > 3]
                            if any(w in q for w in h_words): hp = p0
                            elif any(w in q for w in a_words): ap = p0

                    if hp is not None or ap is not None:
                        # Filtro: mercado YA RESUELTO (un lado ~100%) → no usar
                        # En 3-way, si suman ~1.0 y el spread es >0.95, está cerrado
                        prices = [p for p in (hp, dp, ap) if isinstance(p, (int, float))]
                        if prices and max(prices) > 0.97:
                            continue  # mercado prácticamente resuelto

                        variant = {
                            "poly_home":  ph,
                            "poly_away":  pa,
                            "home_price": hp if hp is not None else "-",
                            "draw_price": dp if dp is not None else "-",
                            "away_price": ap if ap is not None else "-",
                            "volume":     vol,
                            "start_date": start_date,
                            "end_date":   end_date,
                        }
                        result.setdefault(norm, []).append(variant)
            except Exception:
                continue

    _poly_cache = result
    _poly_ts = time.time()
    return result


def _sim(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if a == b: return True
    stop = {"club","united","city","real","sporting","football","atletico","fc","sc","cf","ac","se","ca"}
    words = [w for w in a.split() if len(w) > 3 and w not in stop]
    return any(w in b for w in words)

def find_poly_market(home: str, away: str, poly: Dict,
                     match_date: str = "") -> Optional[Dict]:
    """
    Busca el mercado de Polymarket que mejor coincide con el partido.
    Si hay varios mercados con los mismos equipos, prefiere:
      1. El que tenga la fecha más cercana (start/end) a match_date
      2. El de mayor volumen como desempate
    """
    candidates: List[Tuple[Dict, bool]] = []  # (variant, reversed_flag)
    # `poly` ahora es Dict[str, List[Dict]]
    for variants in poly.values():
        # Compatibilidad: si todavía hay viejas entradas como dict simple
        if isinstance(variants, dict):
            variants = [variants]
        for data in variants:
            ph, pa = data["poly_home"], data["poly_away"]
            if _sim(home, ph) and _sim(away, pa):
                candidates.append((data, False))
            elif _sim(home, pa) and _sim(away, ph):
                candidates.append((data, True))

    if not candidates:
        return None

    # Si solo hay uno, devolver
    if len(candidates) == 1:
        data, rev = candidates[0]
        if rev:
            d = dict(data)
            d["home_price"], d["away_price"] = data["away_price"], data["home_price"]
            return d
        return data

    # Hay varios: rankear por proximidad de fecha y volumen
    def _score(item):
        data, rev = item
        end_d = data.get("end_date", "") or data.get("start_date", "")
        date_score = 999
        if match_date and end_d:
            try:
                from datetime import datetime
                md = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                ed = datetime.fromisoformat(end_d.replace("Z", "+00:00"))
                date_score = abs((ed - md).total_seconds()) / 86400  # días de diferencia
            except Exception:
                pass
        # Menor diferencia de fecha = mejor; más volumen = mejor (desempate)
        return (date_score, -data.get("volume", 0))

    candidates.sort(key=_score)
    data, rev = candidates[0]
    if rev:
        d = dict(data)
        d["home_price"], d["away_price"] = data["away_price"], data["home_price"]
        return d
    return data


# ─────────────────────────────────────────────────────────────────
# 4. ANALIZAR PARTIDO: modelo + edge
# ─────────────────────────────────────────────────────────────────
def analyze_match(match: Dict, detail: Dict, standings: Dict, poly: Dict) -> Optional[Dict]:
    """
    Combina standings + form + lineup + Polymarket para encontrar oportunidades.
    Retorna None si no hay mercado Polymarket o el edge es muy bajo.
    """
    home = match["home_team"]
    away = match["away_team"]
    match_date = match.get("date", "") or ""

    # Polymarket (pasamos la fecha del partido para elegir el mercado correcto)
    pm = find_poly_market(home, away, poly, match_date=match_date)
    if not pm:
        return None

    hp_raw = pm.get("home_price", "-")
    dp_raw = pm.get("draw_price", "-")
    ap_raw = pm.get("away_price", "-")
    volume = pm.get("volume", 0)

    try:
        hp = float(hp_raw)
        ap = float(ap_raw)
        dp = float(dp_raw) if dp_raw != "-" else max(0.05, 1 - hp - ap)
    except:
        return None

    if hp <= 0 or ap <= 0:
        return None

    # Fuerza de equipos desde standings
    str_data = team_strengths(standings, home, away)

    # ── Posición en tabla (buscar match parcial en nombres) ───────────
    def _find_pos(team_name: str) -> int:
        n = team_name.lower()
        for sname, sdata in standings.items():
            sl = sname.lower()
            if sl == n or n in sl or sl in n:
                return int(sdata.get("position", 0) or 0)
        return 0
    home_position = _find_pos(home)
    away_position = _find_pos(away)

    # ── Estrellas y forma ponderada por calidad de rival ──────────
    espn_id_league = match.get("_espn_id", "")
    stars_map = compute_league_stars(standings, match.get("league_code", ""))

    home_stars = stars_map.get(home, 3)
    away_stars = stars_map.get(away, 3)

    # Buscar por similitud si no hay match exacto
    if home not in stars_map:
        for sname, st in stars_map.items():
            if _sim(home, sname): home_stars = st; break
    if away not in stars_map:
        for sname, st in stars_map.items():
            if _sim(away, sname): away_stars = st; break

    # Schedule para QoA
    # Prioridad: team_id del scoreboard ESPN (siempre disponible, liga europea o no)
    # Fallback: team_id del standings dict (solo ligas ESPN como MLS/Liga MX)
    home_team_id = match.get("home_team_id", "")
    away_team_id = match.get("away_team_id", "")
    if not home_team_id or not away_team_id:
        for sname, sdata in standings.items():
            if not home_team_id and _sim(home, sname):
                home_team_id = str(sdata.get("team_id", ""))
            if not away_team_id and _sim(away, sname):
                away_team_id = str(sdata.get("team_id", ""))

    home_qa = {"qa_form": str_data.get("home_form", 0),
               "opp_avg_stars": 3.0, "opp_quality": "?"}
    away_qa = {"qa_form": str_data.get("away_form", 0),
               "opp_avg_stars": 3.0, "opp_quality": "?"}
    h_games, a_games = [], []

    if espn_id_league and home_team_id:
        h_games = _fetch_team_schedule(espn_id_league, home_team_id)
        if h_games:
            home_qa = quality_adjusted_form(h_games, stars_map)
    if espn_id_league and away_team_id:
        a_games = _fetch_team_schedule(espn_id_league, away_team_id)
        if a_games:
            away_qa = quality_adjusted_form(a_games, stars_map)

    home_form5 = get_form5(h_games)
    away_form5 = get_form5(a_games)

    # ── Calidad de datos: verificar si tenemos información real ──────
    # Un equipo tiene "datos" si aparece en standings con >= 5 partidos jugados.
    # Antes mirábamos ATK/DEF cerca de 1.0, pero la regresión bayesiana
    # comprime los valores al final de temporada y filtraba equipos válidos
    # (ej. Aston Villa con ATK=1.007 era falsamente "sin datos").
    def _team_played(name: str) -> int:
        n = name.lower()
        for k, v in standings.items():
            kl = k.lower()
            if kl == n or n in kl or kl in n:
                return int(v.get("played", 0) or 0)
        return 0
    home_has_data = _team_played(home) >= 5
    away_has_data = _team_played(away) >= 5

    # Si NINGÚN equipo tiene datos reales → descartar: el modelo es ciego
    if not home_has_data and not away_has_data:
        return None

    # Probabilidades base con modelo Poisson
    probs = calculate_match_probabilities(
        home_attack=str_data["home_attack"],
        home_defense=str_data["home_defense"],
        away_attack=str_data["away_attack"],
        away_defense=str_data["away_defense"],
        league_avg_goals=str_data["league_avg"],
        home_advantage=1.12,
    )

    # Ajuste por forma reciente
    probs = apply_form_adjustment(probs, str_data["home_form"], str_data["away_form"])

    # Ajuste por alineacion (si tenemos datos de ESPN)
    home_lineup_score = away_lineup_score = 0.0
    if detail.get("home_starters"):
        n_home = len(detail["home_starters"])
        home_lineup_score = 0.0 if n_home >= 10 else -0.3
    if detail.get("away_starters"):
        n_away = len(detail["away_starters"])
        away_lineup_score = 0.0 if n_away >= 10 else -0.3

    probs = apply_lineup_adjustment(probs, home_lineup_score, away_lineup_score)

    # ── Ajuste EN VIVO: recalcular con marcador + tiempo restante ──
    status = match.get("status", "pre")
    is_live = status in ("in", "halftime")
    live_adjusted = False
    if is_live:
        try:
            h_goals = int(float(match.get("home_score", 0) or 0))
            a_goals = int(float(match.get("away_score", 0) or 0))
            clock_secs = float(match.get("clock_secs", 0) or 0)
            period     = int(match.get("period", 1) or 1)
            is_ht      = match.get("halftime", False)

            # Minutos jugados
            if is_ht:
                mins_played = 45.0
            elif period == 1:
                mins_played = clock_secs / 60.0
            else:
                mins_played = 45.0 + clock_secs / 60.0

            lam_h = probs.get("lambda_home", 1.2)
            lam_a = probs.get("lambda_away", 1.0)

            live_p = calculate_live_probabilities(
                lambda_home_full=lam_h,
                lambda_away_full=lam_a,
                home_goals=h_goals,
                away_goals=a_goals,
                minutes_played=mins_played,
                is_halftime=is_ht,
            )
            probs = live_p
            live_adjusted = True
        except Exception:
            pass  # fallback a probs pre-partido

    # ── Edges ──
    edge_home = calculate_edge(probs["home"], hp)
    edge_draw = calculate_edge(probs["draw"], dp)
    edge_away = calculate_edge(probs["away"], ap)

    # ── Kelly ──
    k_home = kelly_fraction(probs["home"], hp,  KELLY_FRACTION)
    k_draw = kelly_fraction(probs["draw"], dp,  KELLY_FRACTION)
    k_away = kelly_fraction(probs["away"], ap,  KELLY_FRACTION)

    # ── Marcar si es una oportunidad accionable (alto edge) ───────────
    # Antes filtrábamos aquí, ahora dejamos pasar TODOS los matches con
    # Polymarket válido y el slider de edge en el HTML los filtra.
    if is_live:
        is_actionable = (
            (edge_home > 0.03 and probs["home"] > 0.15) or
            (edge_draw > 0.04 and probs["draw"] > 0.15) or
            (edge_away > 0.03 and probs["away"] > 0.15)
        )
    else:
        is_actionable = (
            edge_home >= min_edge_threshold(probs["home"]) or
            edge_draw >= min_edge_threshold(probs["draw"]) or
            edge_away >= min_edge_threshold(probs["away"])
        )

    # ── Filtro de datos parciales ─────────────────────────────────────
    # Si solo UN equipo tiene datos reales, el modelo es parcialmente ciego:
    # el equipo sin datos recibe probabilidades de equipo promedio (1.0/1.0),
    # lo que puede generar falsos edges contra el mercado.
    # Requerir edge mínimo mucho mayor (20%) para continuar.
    if (home_has_data ^ away_has_data):   # XOR: exactamente uno tiene datos
        best_edge_val = max(edge_home, edge_draw, edge_away)
        if best_edge_val < 0.20:
            return None

    return {
        "home_team":       home,
        "away_team":       away,
        "league_code":     match["league_code"],
        "league_name":     match["league_name"],
        "status":          match.get("status", "pre"),
        "date":            match.get("date", ""),
        # Datos EN VIVO
        "home_score":      match.get("home_score", None),
        "away_score":      match.get("away_score", None),
        "clock_secs":      match.get("clock_secs", 0.0),
        "period":          match.get("period", 1),
        "halftime":        match.get("halftime", False),
        "match_key":       match.get("match_key", f"{home}_{away}"),
        "live_minute":     _live_minute_str(
                               match.get("match_key", f"{home}_{away}"),
                               match.get("period", 1),
                               match.get("halftime", False),
                               match.get("clock_secs", 0.0),
                           ) if match.get("status") in ("in","halftime") else "",
        "home_formation":  detail.get("home_formation", ""),
        "away_formation":  detail.get("away_formation", ""),
        # Modelo
        "model_home":      probs["home"],
        "model_draw":      probs["draw"],
        "model_away":      probs["away"],
        "lambda_home":     probs.get("lambda_home", 0),
        "lambda_away":     probs.get("lambda_away", 0),
        "live_adjusted":   live_adjusted,   # True = probs ajustadas al marcador actual
        "mins_left":       probs.get("mins_left", None),
        # Polymarket
        "poly_home":       hp,
        "poly_draw":       dp,
        "poly_away":       ap,
        "poly_volume":     volume,
        # Edge y Kelly
        "edge_home":       edge_home,
        "edge_draw":       edge_draw,
        "edge_away":       edge_away,
        "kelly_home":      k_home,
        "kelly_draw":      k_draw,
        "kelly_away":      k_away,
        # Contexto
        "team_strengths":  str_data,
        "h2h":             detail.get("h2h", []),
        "home_starters":   detail.get("home_starters", []),
        "away_starters":   detail.get("away_starters", []),
        # Logos
        "home_logo":       match.get("home_logo", ""),
        "away_logo":       match.get("away_logo", ""),
        # Posiciones en la tabla de la liga
        "home_position":   home_position,
        "away_position":   away_position,
        # Flag de oportunidad accionable (alto edge)
        "is_actionable":   is_actionable,
        # Estrellas y forma ponderada
        "home_stars":      home_stars,
        "away_stars":      away_stars,
        "home_form5":      home_form5,
        "away_form5":      away_form5,
        "home_qa_form":    home_qa.get("qa_form", 0),
        "away_qa_form":    away_qa.get("qa_form", 0),
        "home_opp_quality":home_qa.get("opp_quality", "?"),
        "away_opp_quality":away_qa.get("opp_quality", "?"),
        "home_opp_stars":  home_qa.get("opp_avg_stars", 3.0),
        "away_opp_stars":  away_qa.get("opp_avg_stars", 3.0),
    }


# ─────────────────────────────────────────────────────────────────
# 5. RENDER
# ─────────────────────────────────────────────────────────────────
def edge_color(edge: float) -> str:
    if edge >= 0.10: return GRN + BOLD
    if edge >= 0.05: return GRN
    if edge > 0:     return YLW
    return RED + DIM

def format_prob(p: float) -> str:
    return f"{p*100:.1f}%"

def _fmt_date(raw_date: str) -> str:
    """Convierte ISO date a hora local legible."""
    try:
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%d/%m  %H:%M")
    except Exception:
        return raw_date[:16]


def _pct(v: float) -> str:
    """Porcentaje sin color, ancho fijo 6 chars: ' 12.6%'"""
    return f"{v*100:5.1f}%"


def _edge(v: float) -> str:
    """Edge con signo, ancho fijo 7 chars: '+20.9%'"""
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:5.1f}%"


def render(opportunities: List[Dict], min_edge: float, total_analyzed: int):
    """Muestra resultados en pantalla. NO borra pantalla — eso lo hace main()."""
    W = 80   # ancho total de la tarjeta

    now_str = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
    header_title = "  OPPORTUNITY FINDER  -  BotSport"
    header_right = now_str

    # ── Cabecera global ───────────────────────────────────────────
    print(clr("=" * W, CYN + BOLD))
    print(clr(f"{header_title:<50}{header_right:>28}", BOLD + CYN))
    print(clr(f"  Modelo: Poisson Dixon-Coles  |  Min edge: {min_edge*100:.0f}%  |  {total_analyzed} partidos analizados", DIM))
    print(clr("=" * W, CYN + BOLD))

    # Filtrar y ordenar
    visible = [o for o in opportunities
               if max(o["edge_home"], o["edge_draw"], o["edge_away"]) >= min_edge]
    visible.sort(key=lambda x: max(x["edge_home"], x["edge_draw"], x["edge_away"]), reverse=True)

    if not visible:
        print()
        print(clr("  Sin oportunidades con edge minimo actual.", YLW))
        print(clr(f"  {len(opportunities)} partidos analizados con edge < {min_edge*100:.0f}%", DIM))
    else:
        for idx, o in enumerate(visible, 1):
            ts    = o["team_strengths"]
            vol   = o["poly_volume"]
            live  = o["status"] in ("in", "halftime")

            # Mejor outcome: piso de prob 30% + EV (edge × prob)
            # Si nada califica → marcar como NO-BET
            edges   = {"HOME": o["edge_home"], "DRAW": o["edge_draw"], "AWAY": o["edge_away"]}
            kellys  = {"HOME": o["kelly_home"], "DRAW": o["kelly_draw"], "AWAY": o["kelly_away"]}
            probs_m = {"HOME": o.get("model_home",0), "DRAW": o.get("model_draw",0), "AWAY": o.get("model_away",0)}
            safe    = {k: edges[k]*probs_m[k] for k in edges if edges[k] > 0 and probs_m[k] >= 0.30}
            if safe:
                best   = max(safe, key=safe.get)
                no_bet = False
            else:
                best   = max(edges, key=edges.get)
                no_bet = True
            best_e  = edges[best]
            best_k  = kellys[best] if not no_bet else 0.0

            # Colores de edge por columna
            def ec(v):
                if v >= 0.10: return GRN + BOLD
                if v >= 0.05: return GRN
                if v >  0:    return YLW
                return DIM

            # Fecha / hora
            date_str  = _fmt_date(o.get("date",""))
            status_lbl = "EN VIVO" if live else "PROXIMO"
            status_clr = GRN + BOLD if live else BLU

            # Formaciones
            hf = o.get("home_formation","") or ""
            af = o.get("away_formation","") or ""
            form_tag = f"  {hf} vs {af}" if (hf or af) else ""

            # Volumen color
            vcol = GRN if vol > 10000 else YLW if vol > 1000 else RED

            # ── Separador numerado ─────────────────────────────────
            print()
            print(clr(f"  {'─'*76}", DIM))

            # Linea 1: Liga · status · fecha · volumen
            vol_str = f"${vol:,.0f}"
            left1   = f"  {o['league_name'].upper()}  ·  {status_lbl}  ·  {date_str}"
            right1  = f"Vol: {vol_str}"
            gap     = W - len(left1) - len(right1) - 1
            print(clr(left1, BOLD + YLW)
                  + " " * max(gap, 1)
                  + clr(right1, vcol))

            # Linea 2: Equipos (+ formacion si hay)
            home_str = o["home_team"]
            away_str = o["away_team"]
            mid      = " vs "
            total_len = len(home_str) + len(mid) + len(away_str)
            pad_l    = max((W - total_len) // 2 - 2, 2)
            print(" " * pad_l
                  + clr(home_str, BOLD + WHT)
                  + clr(mid, DIM)
                  + clr(away_str, BOLD + WHT))

            if form_tag:
                print(clr(form_tag, DIM))

            # ── Tabla de probabilidades ────────────────────────────
            print()
            #   Header fila
            print(f"  {'':10}  {'HOME':>8}  {'DRAW':>8}  {'AWAY':>8}")
            print(clr(f"  {'─'*42}", DIM))

            # Fila Modelo
            mh = _pct(o['model_home']); md = _pct(o['model_draw']); ma = _pct(o['model_away'])
            print(f"  {clr('Modelo',CYN):<10}  {clr(mh,BOLD):>8}  {clr(md,BOLD):>8}  {clr(ma,BOLD):>8}")

            # Fila Polymarket
            ph = _pct(o['poly_home']); pd = _pct(o['poly_draw']); pa = _pct(o['poly_away'])
            print(f"  {clr('Poly',MAG):<10}  {clr(ph,MAG):>8}  {clr(pd,MAG):>8}  {clr(pa,MAG):>8}")

            print(clr(f"  {'─'*42}", DIM))

            # Fila Edge — marcar mejor con ◄
            eh = _edge(o['edge_home']); ed = _edge(o['edge_draw']); ea = _edge(o['edge_away'])
            markers = {k: (" ◄" if k == best and best_e >= min_edge else "  ")
                       for k in ("HOME","DRAW","AWAY")}
            print(f"  {clr('Edge',BOLD):<10}  "
                  f"{clr(eh, ec(o['edge_home'])):>8}{clr(markers['HOME'], GRN+BOLD)}  "
                  f"{clr(ed, ec(o['edge_draw'])):>8}{clr(markers['DRAW'], GRN+BOLD)}  "
                  f"{clr(ea, ec(o['edge_away'])):>8}{clr(markers['AWAY'], GRN+BOLD)}")

            # Fila Kelly
            kh = _pct(o['kelly_home']); kd = _pct(o['kelly_draw']); ka = _pct(o['kelly_away'])
            print(f"  {clr('Kelly',DIM):<10}  {clr(kh,DIM):>8}  {clr(kd,DIM):>8}  {clr(ka,DIM):>8}")

            # ── Recomendacion ──────────────────────────────────────
            print(clr(f"  {'─'*76}", DIM))
            if best_e >= min_edge:
                rec_color = (GRN + BOLD) if best_e >= 0.10 else GRN
                rec = (f"  >> APOSTAR {best:<5}  "
                       f"Edge: {_edge(best_e)}  "
                       f"Kelly: {best_k*100:.1f}% del bankroll")
                print(clr(rec, rec_color))
            else:
                print(clr("  -- Sin edge positivo suficiente", DIM))

            # ── Stats de equipos (1 linea cada uno) ───────────────
            h_lam = o.get("lambda_home", 0)
            a_lam = o.get("lambda_away", 0)
            h_abbr = o["home_team"][:14]
            a_abbr = o["away_team"][:14]
            sh = (f"  {h_abbr:<14}  "
                  f"ATK:{ts['home_attack']:.2f}  DEF:{ts['home_defense']:.2f}  "
                  f"F:{ts['home_form']:+.2f}  Goles esp:{h_lam:.2f}")
            sa = (f"  {a_abbr:<14}  "
                  f"ATK:{ts['away_attack']:.2f}  DEF:{ts['away_defense']:.2f}  "
                  f"F:{ts['away_form']:+.2f}  Goles esp:{a_lam:.2f}")
            print(clr(sh, DIM))
            print(clr(sa, DIM))

            # H2H
            if o.get("h2h"):
                parts = [f"{g['home'][:7]} {g['home_score']}-{g['away_score']} {g['away'][:7]}"
                         for g in o["h2h"][:3]]
                print(clr("  H2H: " + "  |  ".join(parts), DIM))

            # Atacantes titulares
            atk_pos = {"FW","CF","SS","LW","RW","WF","ST","AM","LF","RF"}
            h_atk = [p["name"][:13] for p in o.get("home_starters",[]) if p["position"] in atk_pos][:3]
            a_atk = [p["name"][:13] for p in o.get("away_starters",[]) if p["position"] in atk_pos][:3]
            if h_atk:
                print(clr(f"  Ataque {o['home_team'][:10]}: {', '.join(h_atk)}", DIM))
            if a_atk:
                print(clr(f"  Ataque {o['away_team'][:10]}: {', '.join(a_atk)}", DIM))

    # ── Footer ─────────────────────────────────────────────────────
    print()
    print(clr("=" * W, CYN + BOLD))
    print(clr(f"  {len(visible)} oportunidades  |  {total_analyzed} analizados  |  Ctrl+C para salir", DIM))
    print(clr("=" * W, CYN + BOLD))


# ─────────────────────────────────────────────────────────────────
# 6. CICLO PRINCIPAL
# ─────────────────────────────────────────────────────────────────
def run_analysis(league_filter: Optional[str] = None) -> Tuple[List[Dict], int]:
    """Ejecuta el analisis completo y retorna oportunidades."""
    opportunities = []
    total_analyzed = 0

    print(clr("  [1/4] Cargando precios Polymarket...", DIM), flush=True)
    poly = fetch_poly_all()
    print(clr(f"  [1/4] {len(poly)} mercados cargados", GRN), flush=True)

    leagues_to_run = [(c,n,e,f) for c,n,e,f in LEAGUES
                      if (not league_filter or c == league_filter)]

    from concurrent.futures import ThreadPoolExecutor

    for i, (code, name, espn_id, fd_id) in enumerate(leagues_to_run, 1):
        if not espn_id:
            continue

        print(clr(f"  [{i+1}/{len(leagues_to_run)+1}] Analizando {name}...", DIM), flush=True)

        # Standings: FD primero, ESPN como fallback
        standings = get_standings(code, espn_id)

        # Partidos: ESPN primero (trae team_ids para forma reciente),
        # FD como fallback si ESPN no devuelve nada
        matches = get_espn_matches(espn_id, code, name)
        if not matches and fd_id:
            matches = get_fd_matches(fd_id, code, name)
        if not matches:
            continue

        # ── PRE-FETCH PARALELO DE SCHEDULES ───────────────────────────
        # Recolectar todos los team_ids únicos y pre-cachear sus schedules
        # en paralelo (15 workers). Esto carga la forma de los últimos 5
        # partidos para TODOS los equipos antes de analizar matches.
        team_ids = set()
        for m in matches:
            if m.get("home_team_id"):
                team_ids.add(m["home_team_id"])
            if m.get("away_team_id"):
                team_ids.add(m["away_team_id"])
        # Fallback: team_ids desde standings (solo MLS/Liga MX tienen esto)
        for sdata in standings.values():
            tid = str(sdata.get("team_id", ""))
            if tid:
                team_ids.add(tid)

        if team_ids:
            with ThreadPoolExecutor(max_workers=15) as ex:
                list(ex.map(lambda tid: _fetch_team_schedule(espn_id, tid),
                            team_ids))

        # Analizar cada partido
        for match in matches:
            total_analyzed += 1
            # Inyectar espn_id en el match para que analyze_match pueda
            # buscar schedules individuales de equipos
            match["_espn_id"] = espn_id

            # Detalle ESPN (formacion, lineup, odds, H2H)
            espn_eid = match["event_id"]
            if match.get("source") == "fd":
                espn_eid = find_espn_event_id(
                    espn_id,
                    match["home_team"],
                    match["away_team"],
                    match["date"],
                )
            detail = get_espn_detail(espn_id, espn_eid) if espn_eid else {}

            result = analyze_match(match, detail, standings, poly)
            if result:
                if match.get("status") == "post":
                    # Partido terminado: solo tracking, no mostrar en HTML
                    if TRACKER_OK:
                        try:
                            _tracker.save_and_resolve(result)
                        except Exception:
                            pass
                else:
                    opportunities.append(result)
                    # Guardar prediccion en historial (futuros y en vivo)
                    if TRACKER_OK and result.get("status") in ("pre", "timed", "in", "halftime"):
                        try:
                            _tracker.save_prediction(result)
                        except Exception:
                            pass

    # Actualizar resultados de partidos terminados
    if TRACKER_OK:
        try:
            _tracker.update_results(FD_KEY)
        except Exception:
            pass

    return opportunities, total_analyzed


def main():
    global REFRESH_INTERVAL
    parser = argparse.ArgumentParser()
    parser.add_argument("--once",      action="store_true",
                        help="Analizar una vez y salir")
    parser.add_argument("--html",      action="store_true",
                        help="Generar report.html y abrir en navegador")
    parser.add_argument("--min-edge",  type=float, default=MIN_EDGE_DEFAULT)
    parser.add_argument("--league",    type=str,   default=None)
    parser.add_argument("--interval",  type=int,   default=REFRESH_INTERVAL)
    args = parser.parse_args()

    REFRESH_INTERVAL = args.interval

    # Importar generador HTML solo si se usa
    html_gen = None
    if args.html:
        try:
            import html_report as html_gen
        except ImportError:
            print("[ERROR] No se encontro html_report.py")
            args.html = False

    print(clr("=" * 82, CYN))
    print(clr("  OPPORTUNITY FINDER  -  BotSport  -  Iniciando...", BOLD + CYN))
    if args.html:
        print(clr("  Modo: HTML  (se abrira report.html en el navegador)", YLW))
    print(clr("=" * 82, CYN))

    def refresh_and_display(opps_prev, total_prev):
        opps, total = run_analysis(args.league)
        # ¿Hay partidos en vivo? → refresh más rápido
        has_live = any(o.get("status") in ("in","halftime") for o in opps)
        live_interval = 60 if has_live else args.interval
        # Terminal
        os.system("cls" if os.name == "nt" else "clear")
        render(opps, args.min_edge, total)
        # HTML
        if args.html and html_gen:
            path = html_gen.generate_report(opps, args.min_edge, total, live_interval)
            print(clr(f"  HTML guardado: {path}", DIM))
            if has_live:
                print(clr("  [EN VIVO] Refresh cada 60s", GRN + BOLD))
        return opps, total

    opps, total = refresh_and_display([], 0)

    # Abrir navegador la primera vez en modo HTML
    if args.html:
        import webbrowser, pathlib
        html_path = pathlib.Path(html_gen.REPORT_PATH).as_uri()
        webbrowser.open(html_path)
        print(clr(f"  Abriendo navegador: {html_path}", GRN))

    if args.once:
        return

    # Modo continuo
    fetch_ts = time.time()
    try:
        while True:
            elapsed = int(time.time() - fetch_ts)
            remaining = max(0, args.interval - elapsed)
            mins, secs = divmod(remaining, 60)
            countdown = f"  Proximo analisis en: {mins:02d}:{secs:02d}  (Ctrl+C para salir)"
            print(f"\r{clr(countdown, DIM)}", end="", flush=True)

            if elapsed >= args.interval:
                print()
                opps, total = refresh_and_display(opps, total)
                fetch_ts = time.time()

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nOpportunity Finder detenido.")


if __name__ == "__main__":
    main()
