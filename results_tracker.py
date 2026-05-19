#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
results_tracker.py
Guarda las predicciones del bot y verifica los resultados reales
cuando los partidos terminan.

Uso:
  Importado por opportunity_finder.py automaticamente.
  También se puede correr directo:  python results_tracker.py
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "data", "predictions_history.json")
FD_BASE      = "https://api.football-data.org/v4"
ESPN_BASE    = "https://site.api.espn.com/apis/site/v2/sports"

os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)

# Ligas resolubles via football-data.org
FD_COMP_MAP = {
    "pl":           "PL",
    "laliga":       "PD",
    "bundesliga":   "BL1",
    "ligue1":       "FL1",
    "seriea":       "SA",
    "brasil":       "BSA",
    "ucl":          "CL",
    "libertadores": "CLI",
}

# Ligas resolubles via ESPN (no cubiertas por football-data)
ESPN_COMP_MAP = {
    "mls":          ("soccer", "usa.1"),
    "mex":          ("soccer", "mex.1"),
    "nfl":          ("football", "nfl"),
    "nba":          ("basketball", "nba"),
    # fallback para ligas FD también:
    "pl":           ("soccer", "eng.1"),
    "laliga":       ("soccer", "esp.1"),
    "bundesliga":   ("soccer", "ger.1"),
    "ligue1":       ("soccer", "fra.1"),
    "seriea":       ("soccer", "ita.1"),
    "ucl":          ("soccer", "uefa.champions"),
    "libertadores": ("soccer", "conmebol.libertadores"),
    "brasil":       ("soccer", "bra.1"),
}

# ─────────────────────────────────────────────────────────────────
def _load() -> List[Dict]:
    try:
        with open(RESULTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save(data: List[Dict]):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────────
def _normalize_team(name: str) -> str:
    """Normaliza nombre de equipo para deduplicación.
    Quita sufijos como 'FC', 'CF', 'SC', 'AFC', etc. y minimiza."""
    import re
    n = name.lower().strip()
    # Quitar sufijos comunes (FC al final, CF, SC, AC, AFC, etc.)
    n = re.sub(r'\s+(fc|cf|sc|ac|afc|sf|sk|bk|if|fk|cd|sd)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def save_prediction(opp: Dict):
    """
    Guarda una prediccion al historial si no existe ya.
    Guarda tanto partidos futuros (pre/timed) como en vivo (in/halftime).
    """
    if opp.get("status") not in ("pre", "timed", "in", "halftime", None):
        return  # Solo partidos activos, no finalizados

    history = _load()

    # Clave única normalizada (sin sufijos FC/CF/SC) para evitar duplicados
    # cuando ESPN dice "Aston Villa" y FD dice "Aston Villa FC"
    nh = _normalize_team(opp['home_team'])
    na = _normalize_team(opp['away_team'])
    date_d = opp.get('date','')[:10]
    match_key = f"{opp['league_code']}|{nh}|{na}|{date_d}"

    # Evitar duplicados (compara key normalizada contra existentes)
    for rec in history:
        rec_key = rec.get("match_key", "")
        # Comparación normalizada también para registros viejos
        rec_h = _normalize_team(rec.get("home_team",""))
        rec_a = _normalize_team(rec.get("away_team",""))
        rec_d = rec.get("date","")[:10]
        rec_norm = f"{rec.get('league_code','')}|{rec_h}|{rec_a}|{rec_d}"
        if rec_key == match_key or rec_norm == match_key:
            return

    history.append({
        "match_key":    match_key,
        "league_code":  opp.get("league_code", ""),
        "league_name":  opp.get("league_name", ""),
        "home_team":    opp.get("home_team", ""),
        "away_team":    opp.get("away_team", ""),
        "date":         opp.get("date", ""),
        "saved_at":     datetime.now(timezone.utc).isoformat(),
        # Prediccion del modelo
        "model_home":   round(opp.get("model_home", 0), 4),
        "model_draw":   round(opp.get("model_draw", 0), 4),
        "model_away":   round(opp.get("model_away", 0), 4),
        # Precios Polymarket al momento
        "poly_home":    opp.get("poly_home", 0),
        "poly_draw":    opp.get("poly_draw", 0),
        "poly_away":    opp.get("poly_away", 0),
        # Recomendación
        "edge_home":    round(opp.get("edge_home", 0), 4),
        "edge_draw":    round(opp.get("edge_draw", 0), 4),
        "edge_away":    round(opp.get("edge_away", 0), 4),
        "best_outcome": _best_outcome(opp),
        "best_edge":    _best_edge(opp),
        "kelly":        _best_kelly(opp),
        # Resultado real (se rellena después)
        "result":       None,   # "home" / "draw" / "away"
        "home_score":   None,
        "away_score":   None,
        "correct":      None,   # True / False
        "profit_pct":   None,   # ganancia/pérdida si se hubiera apostado Kelly
        "resolved_at":  None,
    })

    _save(history)

def _best_outcome(opp: Dict) -> str:
    """
    Selecciona el outcome con mayor PROBABILIDAD del modelo.
    El modelo ya incorpora forma, estadísticas, alineación, etc.
    Edge y Kelly se reportan como info pero NO deciden la apuesta.
    Esto evita el "underdog trap".
    """
    probs = {"home": opp.get("model_home",0),
             "draw": opp.get("model_draw",0),
             "away": opp.get("model_away",0)}
    return max(probs, key=probs.get)

def _best_edge(opp: Dict) -> float:
    """Edge del outcome seleccionado por EV."""
    best = _best_outcome(opp)
    return round(opp.get(f"edge_{best}", 0), 4)

def _best_kelly(opp: Dict) -> float:
    best = _best_outcome(opp)
    return round(opp.get(f"kelly_{best}", 0), 4)

# ─────────────────────────────────────────────────────────────────
def save_and_resolve(opp: Dict):
    """
    Guarda un partido YA TERMINADO como predicción y lo resuelve inmediatamente.
    Usa el marcador que viene en opp (home_score / away_score).
    """
    gh = opp.get("home_score")
    ga = opp.get("away_score")
    try:
        gh = int(float(str(gh))) if gh not in (None, "", "?") else None
        ga = int(float(str(ga))) if ga not in (None, "", "?") else None
    except Exception:
        gh, ga = None, None

    if gh is None or ga is None:
        return  # sin marcador, no podemos resolver

    # Guardar la predicción (force status pre para que pase el filtro)
    opp_copy = dict(opp)
    opp_copy["status"] = "pre"
    save_prediction(opp_copy)

    # Resolver inmediatamente
    history = _load()
    match_key = (
        f"{opp.get('league_code','')}|{opp.get('home_team','')}|"
        f"{opp.get('away_team','')}|{opp.get('date','')[:10]}"
    )
    now = datetime.now(timezone.utc)
    changed = False
    for rec in history:
        if rec.get("match_key") != match_key:
            continue
        if rec.get("result") is not None:
            break  # ya resuelto

        if gh > ga:
            actual = "home"
        elif ga > gh:
            actual = "away"
        else:
            actual = "draw"

        best       = rec.get("best_outcome", "home")
        kelly      = rec.get("kelly", 0.0)
        poly_price = rec.get(f"poly_{actual}", 0)

        if best == actual and poly_price and kelly:
            profit = kelly * ((1.0 / poly_price) - 1.0) if poly_price > 0 else 0
        else:
            profit = -kelly

        rec["result"]      = actual
        rec["home_score"]  = gh
        rec["away_score"]  = ga
        rec["correct"]     = (best == actual)
        rec["profit_pct"]  = round(profit * 100, 2)
        rec["resolved_at"] = now.isoformat()
        changed = True
        break

    if changed:
        _save(history)


# ─────────────────────────────────────────────────────────────────
def update_results(fd_key: str):
    """
    Busca partidos terminados en football-data.org y actualiza el historial.
    """
    if not fd_key:
        return

    history = _load()
    pending = [r for r in history if r.get("result") is None]
    if not pending:
        return

    # Agrupar pendientes por liga
    by_league: Dict[str, List] = {}
    for rec in pending:
        lc = rec.get("league_code", "")
        comp = FD_COMP_MAP.get(lc)
        if comp:
            by_league.setdefault(comp, []).append(rec)

    changed = False
    now = datetime.now(timezone.utc)

    for comp, records in by_league.items():
        try:
            r = requests.get(
                f"{FD_BASE}/competitions/{comp}/matches",
                headers={"X-Auth-Token": fd_key},
                params={"status": "FINISHED"},
                timeout=8,
            )
            if r.status_code != 200:
                continue

            for m in r.json().get("matches", []):
                match_date = m.get("utcDate", "")[:10]
                home_fd = m.get("homeTeam", {}).get("name", "")
                away_fd = m.get("awayTeam", {}).get("name", "")
                score   = m.get("score", {}).get("fullTime", {})
                gh      = score.get("home")
                ga      = score.get("away")
                if gh is None or ga is None:
                    continue

                # Determinar resultado real
                if gh > ga:
                    actual = "home"
                elif ga > gh:
                    actual = "away"
                else:
                    actual = "draw"

                # Buscar en pendientes
                for rec in records:
                    if rec.get("result") is not None:
                        continue
                    if rec.get("date", "")[:10] != match_date:
                        continue
                    if not (_sim(rec["home_team"], home_fd) and _sim(rec["away_team"], away_fd)):
                        continue

                    # Match encontrado → actualizar
                    best = rec.get("best_outcome", "home")
                    kelly = rec.get("kelly", 0.0)
                    poly_price = rec.get(f"poly_{actual}", 0)

                    # Ganancia/pérdida estimada sobre el bankroll
                    if best == actual and poly_price and kelly:
                        # Ganaste: stake * (1/poly - 1)
                        profit = kelly * ((1.0 / poly_price) - 1.0) if poly_price > 0 else 0
                    else:
                        profit = -kelly  # perdiste el stake

                    rec["result"]      = actual
                    rec["home_score"]  = gh
                    rec["away_score"]  = ga
                    rec["correct"]     = (best == actual)
                    rec["profit_pct"]  = round(profit * 100, 2)
                    rec["resolved_at"] = now.isoformat()
                    changed = True

        except Exception:
            continue

    # Resolver también via ESPN (MLS, Liga MX y otras no cubiertas por FD)
    pending_after_fd = [r for r in history if r.get("result") is None]
    if pending_after_fd:
        espn_changed = _resolve_via_espn(pending_after_fd)
        changed = changed or espn_changed

    if changed:
        _save(history)

def _sim(a: str, b: str) -> bool:
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return True
    stop = {"fc","sc","cf","ac","se","ca","club","real","sporting","atletico","united","city"}
    words = [w for w in a.split() if len(w) > 3 and w not in stop]
    return any(w in b for w in words)


# ─────────────────────────────────────────────────────────────────
def _resolve_via_espn(pending: List[Dict]) -> bool:
    """
    Resuelve partidos terminados usando ESPN API.
    Cubre MLS, Liga MX y cualquier liga de ESPN_COMP_MAP.
    Retorna True si hubo cambios.
    """
    changed = False
    now = datetime.now(timezone.utc)

    # Agrupar pendientes por liga+fecha
    by_key: Dict[str, List] = {}
    for rec in pending:
        lc = rec.get("league_code", "")
        if lc not in ESPN_COMP_MAP:
            continue
        date = rec.get("date", "")[:10]
        if not date:
            continue
        # Solo intentar resolver partidos cuya fecha ya pasó o es hoy
        try:
            match_dt = datetime.fromisoformat(date)
            if match_dt.date() > now.date():
                continue  # aún no ha jugado
        except Exception:
            pass
        key = (lc, date)
        by_key.setdefault(key, []).append(rec)

    for (lc, date), records in by_key.items():
        sport, league = ESPN_COMP_MAP[lc]
        date_param = date.replace("-", "")
        try:
            r = requests.get(
                f"{ESPN_BASE}/{sport}/{league}/scoreboard",
                params={"dates": date_param},
                timeout=8,
            )
            if r.status_code != 200:
                continue

            for evt in r.json().get("events", []):
                comp = evt.get("competitions", [{}])[0]
                status_name = comp.get("status", {}).get("type", {}).get("name", "")
                # Solo partidos terminados
                if status_name not in ("STATUS_FINAL", "STATUS_FULL_TIME",
                                       "STATUS_FINAL_PEN", "STATUS_FINAL_AET"):
                    continue

                competitors = comp.get("competitors", [])
                home_c = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away_c = next((c for c in competitors if c.get("homeAway") == "away"), None)
                if not home_c or not away_c:
                    continue

                home_name = home_c.get("team", {}).get("displayName", "")
                away_name = away_c.get("team", {}).get("displayName", "")
                try:
                    gh = int(float(home_c.get("score", 0) or 0))
                    ga = int(float(away_c.get("score", 0) or 0))
                except Exception:
                    continue

                if gh > ga:
                    actual = "home"
                elif ga > gh:
                    actual = "away"
                else:
                    actual = "draw"

                for rec in records:
                    if rec.get("result") is not None:
                        continue
                    if not (_sim(rec["home_team"], home_name) and
                            _sim(rec["away_team"], away_name)):
                        continue

                    best  = rec.get("best_outcome", "home")
                    kelly = rec.get("kelly", 0.0)
                    poly_price = rec.get(f"poly_{actual}", 0)

                    if best == actual and poly_price and kelly:
                        profit = kelly * ((1.0 / poly_price) - 1.0) if poly_price > 0 else 0
                    else:
                        profit = -kelly

                    rec["result"]      = actual
                    rec["home_score"]  = gh
                    rec["away_score"]  = ga
                    rec["correct"]     = (best == actual)
                    rec["profit_pct"]  = round(profit * 100, 2)
                    rec["resolved_at"] = now.isoformat()
                    changed = True

        except Exception:
            continue

    return changed

# ─────────────────────────────────────────────────────────────────
def get_recent_results(days: int = 14) -> List[Dict]:
    """Devuelve resultados recientes (con resultado conocido), ordenados por fecha desc."""
    history = _load()
    cutoff  = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    results = [r for r in history if r.get("result") is not None and r.get("date","") >= cutoff]
    return sorted(results, key=lambda x: x.get("date",""), reverse=True)

def get_pending() -> List[Dict]:
    """Devuelve predicciones sin resolver."""
    history = _load()
    return [r for r in history if r.get("result") is None]

def get_stats() -> Dict:
    """Calcula estadísticas globales del historial."""
    history = _load()
    resolved = [r for r in history if r.get("result") is not None]
    if not resolved:
        return {}

    wins    = sum(1 for r in resolved if r.get("correct"))
    losses  = len(resolved) - wins
    profits = [r.get("profit_pct", 0) or 0 for r in resolved]
    total_profit = sum(profits)
    brier_scores = []
    for r in resolved:
        actual = r.get("result")
        if actual:
            p = r.get(f"model_{actual}", 0)
            brier_scores.append((1 - p) ** 2)

    return {
        "total":         len(resolved),
        "wins":          wins,
        "losses":        losses,
        "win_rate":      round(wins / len(resolved) * 100, 1) if resolved else 0,
        "total_profit":  round(total_profit, 2),
        "avg_profit":    round(total_profit / len(resolved), 2) if resolved else 0,
        "brier_score":   round(sum(brier_scores) / len(brier_scores), 3) if brier_scores else 0,
        "pending":       len(get_pending()),
    }

# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from dotenv import load_dotenv
    load_dotenv()
    fd_key = os.getenv("FOOTBALL_DATA_API_KEY", "")

    print("Actualizando resultados...")
    update_results(fd_key)

    stats = get_stats()
    if stats:
        print(f"\n=== ESTADISTICAS ===")
        print(f"  Total:        {stats['total']}")
        print(f"  Aciertos:     {stats['wins']}  ({stats['win_rate']}%)")
        print(f"  Fallos:       {stats['losses']}")
        print(f"  P&L total:    {stats['total_profit']:+.2f}%")
        print(f"  P&L promedio: {stats['avg_profit']:+.2f}% por apuesta")
        print(f"  Brier score:  {stats['brier_score']}")
        print(f"  Pendientes:   {stats['pending']}")
    else:
        print("Sin historial aun.")

    recent = get_recent_results(14)
    if recent:
        print(f"\n=== ULTIMOS RESULTADOS ===")
        for r in recent[:15]:
            ok  = "✓" if r.get("correct") else "✗"
            pnl = f"{r.get('profit_pct',0):+.1f}%"
            print(f"  {ok} {r['date'][:10]}  {r['home_team'][:18]:18} {r.get('home_score','?')}-{r.get('away_score','?')}  {r['away_team'][:18]:18}  -> {r.get('best_outcome','?').upper()} {pnl}")
