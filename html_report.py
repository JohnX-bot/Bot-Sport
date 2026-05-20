#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
html_report.py — Genera report.html con todas las oportunidades de apuesta.
Importado por opportunity_finder.py cuando se pasa --html.
"""

import os
import json
from datetime import datetime
from typing import List, Dict

REPORT_PATH = os.path.join(os.path.dirname(__file__), "report.html")


# ─────────────────────────────────────────────────────────────────
def _pct(v: float) -> str:
    return f"{v*100:.1f}%"

def _edge_str(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.1f}%"

def _edge_class(v: float) -> str:
    if v >= 0.10: return "edge-big"
    if v >= 0.05: return "edge-good"
    if v >  0:    return "edge-ok"
    return "edge-neg"

def _vol_class(v: float) -> str:
    if v > 10000: return "vol-high"
    if v > 1000:  return "vol-mid"
    return "vol-low"

def _fmt_date(raw: str) -> str:
    try:
        from datetime import timezone
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%d/%m/%Y &nbsp; %H:%M")
    except Exception:
        return raw[:16]

def _bar(model_p: float, poly_p: float, outcome: str, edge: float) -> str:
    m = round(model_p * 100, 1)
    p = round(poly_p * 100, 1)
    ec = _edge_class(edge)
    return f"""
    <div class="bar-group">
      <div class="bar-label">{outcome}</div>
      <div class="bar-track">
        <div class="bar-model" style="width:{m:.1f}%" title="Modelo {m:.1f}%"></div>
      </div>
      <div class="bar-track bar-track-poly">
        <div class="bar-poly" style="width:{p:.1f}%" title="Polymarket {p:.1f}%"></div>
      </div>
      <div class="bar-nums">
        <span class="bar-m">{m:.1f}%</span>
        <span class="bar-vs">vs</span>
        <span class="bar-p">{p:.1f}%</span>
        <span class="bar-edge {ec}">{_edge_str(edge)}</span>
      </div>
    </div>"""

def _h2h_table(h2h: List[Dict]) -> str:
    if not h2h:
        return ""
    rows = ""
    for g in h2h[:5]:
        rows += f"""
        <tr>
          <td class="h2h-team">{g.get('home','')[:20]}</td>
          <td class="h2h-score">{g.get('home_score','?')} - {g.get('away_score','?')}</td>
          <td class="h2h-team right">{g.get('away','')[:20]}</td>
        </tr>"""
    return f"""
    <div class="section-title">Historial H2H</div>
    <table class="h2h-table">
      <tbody>{rows}</tbody>
    </table>"""

def _lineup(starters: List[Dict], label: str) -> str:
    if not starters:
        return ""
    atk_pos = {"FW","CF","SS","LW","RW","WF","ST","AM","LF","RF","CAM"}
    mid_pos  = {"CM","CDM","DM","LM","RM","MF","DMF","CMF"}
    def_pos  = {"CB","LB","RB","LWB","RWB","SW","DF"}
    gk_pos   = {"GK"}

    groups = {"GK": [], "DEF": [], "MED": [], "ATA": [], "?": []}
    for p in starters:
        pos = p.get("position","").upper()
        if pos in gk_pos:  groups["GK"].append(p)
        elif pos in def_pos: groups["DEF"].append(p)
        elif pos in mid_pos: groups["MED"].append(p)
        elif pos in atk_pos: groups["ATA"].append(p)
        else: groups["?"].append(p)

    lines = []
    for grp, players in groups.items():
        if not players: continue
        names = "  ·  ".join(
            f'<span class="player">{p["name"][:16]}'
            f'<span class="pos-tag">{p.get("position","")}</span></span>'
            for p in players
        )
        lines.append(f'<div class="lineup-row"><span class="pos-label">{grp}</span>{names}</div>')

    return f"""
    <div class="section-title">{label}</div>
    <div class="lineup">{"".join(lines)}</div>"""


# ─────────────────────────────────────────────────────────────────
def _card(o: Dict, rank: int) -> str:
    ts   = o["team_strengths"]
    vol  = o.get("poly_volume", 0)
    live = o["status"] in ("in", "halftime")

    edges = {
        "HOME": o["edge_home"],
        "DRAW": o["edge_draw"],
        "AWAY": o["edge_away"],
    }
    kellys = {
        "HOME": o["kelly_home"],
        "DRAW": o["kelly_draw"],
        "AWAY": o["kelly_away"],
    }
    probs_map = {
        "HOME": o.get("model_home", 0),
        "DRAW": o.get("model_draw", 0),
        "AWAY": o.get("model_away", 0),
    }

    # ── Decisión basada en el MODELO (no en edge) ─────────────────────
    # El modelo incorpora: forma reciente, estadísticas, alineación,
    # fuerza ATK/DEF de cada equipo, ventaja local, Dixon-Coles, etc.
    # Edge y Kelly se muestran como INFO complementaria, no como
    # criterio de decisión. Esto evita el "underdog trap".
    sorted_probs = sorted(probs_map.items(), key=lambda x: x[1], reverse=True)
    primary,   primary_prob   = sorted_probs[0]   # outcome más probable
    secondary, secondary_prob = sorted_probs[1]   # segunda opción

    best       = primary           # usado para los cálculos y badges
    best_edge  = edges[primary]
    best_kelly = kellys[primary]

    # Nivel de riesgo según concentración de probabilidad
    if primary_prob >= 0.55:
        risk_label = "🟢 RIESGO BAJO"
        risk_cls   = "risk-low"
    elif primary_prob >= 0.40:
        risk_label = "🟡 RIESGO MEDIO"
        risk_cls   = "risk-mid"
    else:
        risk_label = "🔴 RIESGO ALTO"
        risk_cls   = "risk-high"

    no_bet = False

    # Datos en vivo
    live_minute   = o.get("live_minute", "")
    home_score    = o.get("home_score", None)
    away_score    = o.get("away_score", None)
    clock_secs    = float(o.get("clock_secs", 0) or 0)
    is_halftime   = o.get("halftime", False)
    period        = int(o.get("period", 1) or 1)
    live_adjusted = o.get("live_adjusted", False)
    mins_left     = o.get("mins_left", None)

    if live:
        min_label = "DESCANSO" if is_halftime else (f"{live_minute}'" if live_minute else "?'")
        # Badge ajustado muestra minutos restantes si disponible
        if live_adjusted and mins_left is not None:
            mins_left_label = f"~{int(mins_left)}' restantes"
            live_adj_badge = f'<span class="badge badge-adj" title="Modelo recalculado con marcador actual">&#9881; {mins_left_label}</span>'
        else:
            live_adj_badge = ''
        status_badge = (
            f'<span class="badge badge-live">&#9679; EN VIVO '
            f'<span class="live-clock" data-clock="{clock_secs:.0f}" '
            f'data-period="{period}" data-halftime="{1 if is_halftime else 0}">'
            f'{min_label}</span></span> {live_adj_badge}'
        )
    else:
        status_badge = '<span class="badge badge-pre">PROXIMO</span>'

    # Marcador en vivo
    if live and home_score is not None and away_score is not None:
        score_html = f'<div class="live-score"><span class="score-home">{home_score}</span><span class="score-sep">—</span><span class="score-away">{away_score}</span></div>'
    else:
        score_html = ""

    vol_badge = f'<span class="{_vol_class(vol)} vol-badge">Vol: ${vol:,.0f}</span>'
    date_str  = _fmt_date(o.get("date",""))
    hf = o.get("home_formation","") or ""
    af = o.get("away_formation","") or ""
    form_str  = f"<span class='formation'>{hf}</span>" if hf else ""
    form_str2 = f"<span class='formation'>{af}</span>" if af else ""
    home_logo = o.get("home_logo", "")
    away_logo = o.get("away_logo", "")

    rec_class = _edge_class(best_edge)
    live_note = ' &nbsp;<span class="live-adj-note">&#9881; Probs ajustadas al marcador</span>' if live_adjusted else ""

    # Edge label para cada outcome (info complementaria)
    edge_p = edges[primary]
    edge_s = edges[secondary]
    def _ec(v):
        if v >= 0.05: return "edge-pos"
        if v <= -0.05: return "edge-neg"
        return "edge-neu"

    rec_html  = f"""
    <div class="recommendation {rec_class}">
      <div class="rec-main">
        <div class="rec-primary">
          &#127919; <strong>Principal: {primary}</strong>
          <span class="rec-prob">({primary_prob*100:.1f}%)</span>
          <span class="rec-edge-info {_ec(edge_p)}">Edge {_edge_str(edge_p)}</span>
          {live_note}
        </div>
        <div class="rec-secondary">
          &#128737; Alternativa: <strong>{secondary}</strong>
          <span class="rec-prob">({secondary_prob*100:.1f}%)</span>
          <span class="rec-edge-info {_ec(edge_s)}">Edge {_edge_str(edge_s)}</span>
        </div>
      </div>
      <div class="rec-detail">
        <span class="{risk_cls}">{risk_label}</span>
        &nbsp;|&nbsp;
        Kelly: <strong>{best_kelly*100:.1f}%</strong> del bankroll
      </div>
    </div>"""

    # Tabla de probabilidades
    def row(label, cls, mh, md, ma, ph, pd, pa, eh, ed, ea, kh, kd, ka):
        return f"""
        <tr class="{cls}">
          <td class="tbl-label">{label}</td>
          <td class="{_edge_class(eh)}">{_pct(mh)}<br><small class="poly-val">{_pct(ph)}</small></td>
          <td class="{_edge_class(ed)}">{_pct(md)}<br><small class="poly-val">{_pct(pd)}</small></td>
          <td class="{_edge_class(ea)}">{_pct(ma)}<br><small class="poly-val">{_pct(pa)}</small></td>
        </tr>
        <tr class="edge-row">
          <td class="tbl-label edge-label">EDGE / Kelly</td>
          <td class="{_edge_class(eh)} edge-cell">
            {_edge_str(eh)}<br><small>{kh*100:.1f}%</small>
            {"&nbsp;&#9668;" if best=="HOME" and best_edge>=0.01 else ""}
          </td>
          <td class="{_edge_class(ed)} edge-cell">
            {_edge_str(ed)}<br><small>{kd*100:.1f}%</small>
            {"&nbsp;&#9668;" if best=="DRAW" and best_edge>=0.01 else ""}
          </td>
          <td class="{_edge_class(ea)} edge-cell">
            {_edge_str(ea)}<br><small>{ka*100:.1f}%</small>
            {"&nbsp;&#9668;" if best=="AWAY" and best_edge>=0.01 else ""}
          </td>
        </tr>"""

    prob_table = f"""
    <table class="prob-table">
      <thead>
        <tr>
          <th class="tbl-label"></th>
          <th>HOME</th><th>DRAW</th><th>AWAY</th>
        </tr>
      </thead>
      <tbody>
        {row("Modelo / Poly", "model-row",
             o['model_home'], o['model_draw'], o['model_away'],
             o['poly_home'],  o['poly_draw'],  o['poly_away'],
             o['edge_home'],  o['edge_draw'],  o['edge_away'],
             o['kelly_home'], o['kelly_draw'], o['kelly_away'])}
      </tbody>
    </table>"""

    # Barras visuales
    bars = (
        _bar(o['model_home'], o['poly_home'], "HOME", o['edge_home']) +
        _bar(o['model_draw'], o['poly_draw'], "DRAW", o['edge_draw']) +
        _bar(o['model_away'], o['poly_away'], "AWAY", o['edge_away'])
    )

    # Últimos 5 partidos
    def _form5_html(form5: list) -> str:
        if not form5:
            return ""
        pills = []
        for r in form5:
            cls  = {"W": "f5-win", "D": "f5-draw", "L": "f5-loss"}.get(r, "f5-draw")
            pills.append(f'<span class="f5-badge {cls}">{r}</span>')
        return '<span class="form5">' + "".join(pills) + '</span>'

    # Estrellas y QoA
    def _stars_html(n: int) -> str:
        filled = "&#9733;" * n
        empty  = "&#9734;" * (5 - n)
        cls = ("star-5" if n == 5 else "star-4" if n == 4 else
               "star-3" if n == 3 else "star-2" if n == 2 else "star-1")
        return f'<span class="stars {cls}">{filled}{empty}</span>'

    def _qoa_pill(qa_form: float, opp_quality: str, opp_stars: float) -> str:
        if opp_quality == "?":
            return ""
        # Color según calidad de los rivales
        if opp_quality == "Alta":
            oq_cls = "oq-high"
        elif opp_quality == "Media":
            oq_cls = "oq-mid"
        else:
            oq_cls = "oq-low"
        # Forma ajustada: color según resultado
        qa_cls = "form-pos" if qa_form >= 0.1 else ("form-neg" if qa_form <= -0.1 else "")
        qa_label = f"{qa_form:+.2f}"
        return (
            f'<span class="pill {oq_cls}" title="Calidad media de rivales recientes">'
            f'Rivales: {opp_quality} ({opp_stars:.1f}&#9733;)</span>'
            f'<span class="pill {qa_cls}" title="Forma ponderada por calidad de rival">'
            f'Forma QoA {qa_label}</span>'
        )

    h_stars      = o.get("home_stars", 3)
    a_stars      = o.get("away_stars", 3)
    h_qa_form    = o.get("home_qa_form", 0)
    a_qa_form    = o.get("away_qa_form", 0)
    h_opp_qual   = o.get("home_opp_quality", "?")
    a_opp_qual   = o.get("away_opp_quality", "?")
    h_opp_stars  = o.get("home_opp_stars", 3.0)
    a_opp_stars  = o.get("away_opp_stars", 3.0)

    # Stats de equipo
    lam_h = o.get("lambda_home", 0)
    lam_a = o.get("lambda_away", 0)
    stats_h = f"""
    <div class="team-stat-row">
      <div class="ts-name">{_stars_html(h_stars)} {o['home_team']}</div>
      <div class="ts-pills">
        <span class="pill atk">ATK {ts['home_attack']:.2f}</span>
        <span class="pill def">DEF {ts['home_defense']:.2f}</span>
        <span class="pill {'form-pos' if ts['home_form']>=0 else 'form-neg'}">
          Forma {ts['home_form']:+.2f}</span>
        <span class="pill gol">Goles esp: {lam_h:.2f}</span>
        {_qoa_pill(h_qa_form, h_opp_qual, h_opp_stars)}
      </div>
    </div>"""
    stats_a = f"""
    <div class="team-stat-row">
      <div class="ts-name">{_stars_html(a_stars)} {o['away_team']}</div>
      <div class="ts-pills">
        <span class="pill atk">ATK {ts['away_attack']:.2f}</span>
        <span class="pill def">DEF {ts['away_defense']:.2f}</span>
        <span class="pill {'form-pos' if ts['away_form']>=0 else 'form-neg'}">
          Forma {ts['away_form']:+.2f}</span>
        <span class="pill gol">Goles esp: {lam_a:.2f}</span>
        {_qoa_pill(a_qa_form, a_opp_qual, a_opp_stars)}
      </div>
    </div>"""

    h_form5_html = _form5_html(o.get("home_form5", []))
    a_form5_html = _form5_html(o.get("away_form5", []))

    # Escudo del equipo con posición en tabla
    def _crest(logo_url: str, alt: str, position: int = 0) -> str:
        letter = alt[:1].upper()
        # Badge de posición (color según ranking)
        pos_badge = ""
        if position and position > 0:
            if   position <= 4:   pcls = "pos-top"     # zona Champions
            elif position <= 6:   pcls = "pos-eur"     # zona europea
            elif position <= 12:  pcls = "pos-mid"     # mitad de tabla
            else:                  pcls = "pos-low"     # parte baja / descenso
            pos_badge = f'<span class="pos-badge {pcls}">{position}°</span>'
        if not logo_url:
            return (
                f'<div class="crest-wrap">'
                f'<div class="crest-placeholder">{letter}</div>'
                f'{pos_badge}</div>'
            )
        return (
            f'<div class="crest-wrap">'
            f'<img class="team-crest" src="{logo_url}" alt="{alt}" '
            f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
            f'<div class="crest-placeholder" style="display:none">{letter}</div>'
            f'{pos_badge}</div>'
        )

    h_crest = _crest(home_logo, o['home_team'], o.get('home_position', 0))
    a_crest = _crest(away_logo, o['away_team'], o.get('away_position', 0))

    h2h_html   = _h2h_table(o.get("h2h", []))
    lineup_h   = _lineup(o.get("home_starters", []), f"Alineacion {o['home_team']}")
    lineup_a   = _lineup(o.get("away_starters", []), f"Alineacion {o['away_team']}")

    card_border = {
        "edge-big":  "#3fb950",
        "edge-good": "#58d68d",
        "edge-ok":   "#f39c12",
    }.get(_edge_class(best_edge), "#30363d")

    # ISO date para data-date (YYYY-MM-DD)
    try:
        raw_d = o.get("date","")
        iso_date = datetime.fromisoformat(raw_d.replace("Z","+00:00")).astimezone().strftime("%Y-%m-%d")
    except Exception:
        iso_date = ""

    league_slug = o['league_name'].lower().replace(" ","_")

    return f"""
  <div class="card" style="border-left-color:{card_border}"
       data-league="{league_slug}"
       data-league-name="{league_slug}"
       data-date="{iso_date}"
       data-edge="{round(max(edges['HOME'], edges['DRAW'], edges['AWAY'])*100,1)}"
       data-live="{1 if live else 0}"
       data-clock-secs="{clock_secs:.0f}"
       data-period="{period}"
       data-halftime="{1 if is_halftime else 0}">
    <!-- Header -->
    <div class="card-header">
      <div class="card-header-left">
        <span class="rank">#{rank}</span>
        <span class="league">{o['league_name'].upper()}</span>
        {status_badge}
        <span class="match-date">{date_str}</span>
      </div>
      <div class="card-header-right">{vol_badge}</div>
    </div>

    <!-- Equipos + Marcador en vivo -->
    <div class="teams-row">
      <div class="team-block home-block">
        {h_crest}
        <div class="team-info home-info">
          <div class="team-name home-name">{o['home_team']} {form_str}</div>
          <div class="team-meta">
            {_stars_html(h_stars)}
            {h_form5_html}
          </div>
        </div>
      </div>
      {"<div class='live-score-wrap'>" + score_html + "</div>" if live and score_html else '<div class="vs-separator">VS</div>'}
      <div class="team-block away-block">
        <div class="team-info away-info">
          <div class="team-name away-name">{form_str2} {o['away_team']}</div>
          <div class="team-meta away-meta">
            {_stars_html(a_stars)}
            {a_form5_html}
          </div>
        </div>
        {a_crest}
      </div>
    </div>

    <!-- Recomendacion -->
    {rec_html}

    <!-- Tabla + Barras lado a lado -->
    <div class="data-cols">
      <div class="col-table">
        <div class="section-title">Probabilidades</div>
        {prob_table}
      </div>
      <div class="col-bars">
        <div class="section-title">
          <span class="legend-dot model-dot"></span>Modelo
          &nbsp;&nbsp;
          <span class="legend-dot poly-dot"></span>Polymarket
        </div>
        <div class="bars-wrap">{bars}</div>
      </div>
    </div>

    <!-- Stats equipos -->
    <div class="section-title">Forma & Fuerza</div>
    {stats_h}
    {stats_a}

    <!-- H2H y Alineaciones (colapsables) -->
    <div class="extras">
      {h2h_html}
      {lineup_h}
      {lineup_a}
    </div>
  </div>"""


# ─────────────────────────────────────────────────────────────────
CSS = """
:root {
  --bg:       #0d1117;
  --bg2:      #161b22;
  --bg3:      #21262d;
  --border:   #30363d;
  --text:     #e6edf3;
  --dim:      #8b949e;
  --cyan:     #58a6ff;
  --green:    #3fb950;
  --green2:   #2ea043;
  --yellow:   #d29922;
  --red:      #f85149;
  --purple:   #bc8cff;
  --orange:   #e3b341;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 14px;
  min-height: 100vh;
}
a { color: var(--cyan); text-decoration: none; }

/* ── HEADER ── */
.global-header {
  background: var(--bg2);
  border-bottom: 2px solid var(--cyan);
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}
.global-header h1 {
  font-size: 1.3rem;
  letter-spacing: 1px;
  color: var(--cyan);
}
.header-meta { color: var(--dim); font-size: 13px; text-align: right; line-height: 1.8; }
.header-meta strong { color: var(--text); }
#countdown { color: var(--orange); font-weight: bold; }

/* ── SUMMARY BAR ── */
.summary-bar {
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
  padding: 8px 24px;
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: var(--dim);
  flex-wrap: wrap;
}
.summary-bar span { display: flex; align-items: center; gap: 6px; }
.summary-bar strong { color: var(--text); }
/* Contador de predicciones en el summary bar */
.pred-counter {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(88,166,255,.08);
  border: 1px solid rgba(88,166,255,.25);
  border-radius: 20px;
  padding: 4px 14px;
  font-size: 13px;
}
.pred-label { color: var(--dim); font-size: 12px; }
.pred-score { font-size: 1.15rem; font-weight: 900; }
.pred-wr    { font-size: 12px; font-weight: bold; }
.pred-sep   { color: var(--border); }
.pred-pnl   { font-weight: bold; }
.pred-empty { color: var(--dim); font-size: 12px; }

/* ── Estrellas de equipo ── */
.stars       { font-size: 13px; letter-spacing: 1px; font-weight: 700;
               text-shadow: 0 0 6px currentColor; }
.star-5      { color: #FFD700; }   /* ★ Oro — elite mundial */
.star-4      { color: #3FB950; }   /* ★ Verde — muy bueno */
.star-3      { color: #58A6FF; }   /* ★ Azul — promedio */
.star-2      { color: #F0883E; }   /* ★ Naranja — bajo */
.star-1      { color: #F85149; }   /* ★ Rojo — muy bajo */
/* ── Calidad de rivales (QoA) ── */
.oq-high { background: rgba(63,185,80,.15); color: var(--green);  border: 1px solid rgba(63,185,80,.3); }
.oq-mid  { background: rgba(227,179,65,.10); color: var(--orange); border: 1px solid rgba(227,179,65,.3); }
.oq-low  { background: rgba(248,81,73,.08); color: #aaa;           border: 1px solid rgba(248,81,73,.2); }
/* ── Badge ajuste EN VIVO ── */
.badge-adj {
  background: rgba(188,140,255,.15);
  color: var(--purple);
  border: 1px solid rgba(188,140,255,.35);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: default;
}
/* ── Confianza del modelo ── */
.conf-high  { color: var(--green);  font-weight: bold; font-size: 12px; }
.conf-mid   { color: var(--orange); font-weight: bold; font-size: 12px; }
.conf-low   { color: var(--red);    font-weight: bold; font-size: 12px; }
.live-adj-note { color: var(--purple); font-size: 12px; font-weight: normal; }
/* ── FILTROS ── */
.filter-bar {
  background: var(--bg2);
  border-bottom: 2px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  position: sticky;
  top: 68px;
  z-index: 99;
}
.filter-section {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-label {
  font-size: 11px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: .8px;
  color: var(--dim);
  white-space: nowrap;
}
.filter-divider {
  width: 1px;
  height: 28px;
  background: var(--border);
}
/* Botones de liga */
.league-btn {
  padding: 4px 12px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--dim);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
}
.league-btn:hover { border-color: var(--cyan); color: var(--cyan); }
.league-btn.active {
  background: rgba(88,166,255,.15);
  border-color: var(--cyan);
  color: var(--cyan);
}
.league-btn.all-btn.active {
  background: rgba(63,185,80,.15);
  border-color: var(--green);
  color: var(--green);
}
/* Date picker */
.date-input {
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}
.date-input:focus { outline: none; border-color: var(--cyan); }
.date-clear {
  background: none;
  border: 1px solid var(--border);
  color: var(--dim);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
}
.date-clear:hover { color: var(--red); border-color: var(--red); }
/* Slider de edge */
.edge-slider { accent-color: var(--green); cursor: pointer; width: 100px; }
.edge-val { font-size: 12px; font-weight: bold; color: var(--green); min-width: 36px; }
/* Botón Live */
.live-btn {
  display: flex; align-items: center; gap: 5px;
  background: none;
  border: 1px solid var(--border);
  color: var(--dim);
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.live-btn:hover { border-color: var(--red); color: var(--red); }
.live-btn.active {
  background: rgba(220,50,50,0.15);
  border-color: var(--red);
  color: var(--red);
}
.live-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--red);
  display: inline-block;
}
.live-btn.active .live-dot { animation: pulse 1s infinite; }
@keyframes pulse {
  0%,100% { opacity: 1; }
  50%      { opacity: 0.3; }
}
/* Contador de resultados */
.filter-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--dim);
}
.filter-count strong { color: var(--text); }
/* Card oculta por filtro */
.card.hidden { display: none; }

/* ── LAYOUT BODY: sidebar izquierdo + contenido ── */
.layout-body {
  display: flex;
  align-items: flex-start;
  min-height: 80vh;
}
/* ── SIDEBAR ── */
.sidebar {
  width: 210px;
  flex-shrink: 0;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  position: sticky;
  top: 122px;
  height: calc(100vh - 122px);
  overflow-y: auto;
  align-self: flex-start;
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.sidebar-title {
  font-size: 10px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--dim);
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border);
}
.sidebar .league-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border-radius: 0;
  border: none;
  border-left: 3px solid transparent;
  padding: 8px 14px 8px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  background: transparent;
  color: var(--dim);
  cursor: pointer;
  transition: all .12s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sidebar .league-btn:hover {
  background: rgba(88,166,255,.07);
  border-left-color: var(--cyan);
  color: var(--text);
}
.sidebar .league-btn.active {
  background: rgba(88,166,255,.12);
  border-left-color: var(--cyan);
  color: var(--cyan);
}
.sidebar .all-btn.active {
  background: rgba(63,185,80,.12);
  border-left-color: var(--green);
  color: var(--green);
}
.sidebar .lg-empty { opacity: 0.38; }
.sidebar .lg-empty:hover { opacity: 0.65; }
.lgcount {
  background: var(--bg3);
  color: var(--dim);
  font-size: 10px;
  font-weight: 700;
  border-radius: 10px;
  padding: 1px 6px;
  min-width: 20px;
  text-align: center;
  flex-shrink: 0;
  margin-left: 4px;
}
.sidebar .league-btn.active .lgcount {
  background: rgba(88,166,255,.2);
  color: var(--cyan);
}
.sidebar .all-btn.active .lgcount {
  background: rgba(63,185,80,.2);
  color: var(--green);
}
/* ── MAIN CONTENT (a la derecha del sidebar) ── */
.main-content { flex: 1; min-width: 0; }
/* Conteo de ligas para la fecha seleccionada */
.league-date-count {
  background: var(--card);
  border-top: 1px solid var(--border);
  padding: 8px 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.league-date-count .ldc-label {
  font-size: 11px;
  color: var(--dim);
  margin-right: 4px;
}
.league-date-count .ldc-pill {
  font-size: 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 3px 10px;
  color: var(--text);
  white-space: nowrap;
}
.league-date-count .ldc-pill span {
  color: var(--cyan);
  font-weight: 700;
  margin-left: 4px;
}
/* Mensaje sin resultados */
#no-results {
  display: none;
  text-align: center;
  padding: 60px 40px;
  color: var(--dim);
  grid-column: 1/-1;
}
#no-results h3 { color: var(--orange); margin-bottom: 8px; }

/* ── MAIN GRID ── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(680px, 1fr));
  gap: 20px;
  padding: 20px 24px;
  max-width: 1600px;
  margin: 0 auto;
}

/* ── CARD ── */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-left: 4px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow .2s;
}
.card:hover { box-shadow: 0 4px 20px rgba(88,166,255,.12); }

/* Card header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
  gap: 6px;
}
.card-header-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rank { color: var(--dim); font-size: 12px; font-weight: bold; }
.league { font-weight: bold; color: var(--orange); font-size: 13px; letter-spacing: .5px; }
.match-date { color: var(--dim); font-size: 12px; }

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: bold;
  letter-spacing: .5px;
}
.badge-live { background: rgba(63,185,80,.2); color: var(--green); border: 1px solid var(--green2); animation: pulse-border 2s infinite; }
.badge-pre  { background: rgba(88,166,255,.15); color: var(--cyan); border: 1px solid #1f6feb; }
.vol-badge  { font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 12px; }
.vol-high   { color: var(--green); background: rgba(63,185,80,.1); }
.vol-mid    { color: var(--orange); background: rgba(210,153,34,.1); }
.vol-low    { color: var(--red); background: rgba(248,81,73,.1); }
/* Reloj en vivo dentro del badge */
.live-clock { font-weight: 900; margin-left: 4px; }
@keyframes pulse-border {
  0%,100% { box-shadow: 0 0 0 0 rgba(63,185,80,.4); }
  50%      { box-shadow: 0 0 0 4px rgba(63,185,80,0); }
}
/* Marcador en vivo */
.live-score-wrap {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.live-score {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(63,185,80,.12);
  border: 1px solid var(--green2);
  border-radius: 8px;
  padding: 6px 18px;
}
.score-home, .score-away {
  font-size: 1.8rem;
  font-weight: 900;
  color: var(--text);
  min-width: 28px;
  text-align: center;
}
.score-sep {
  color: var(--dim);
  font-size: 1.4rem;
  font-weight: bold;
  padding: 0 4px;
}
/* Card con borde pulsante si está en vivo */
.card[data-live="1"] {
  border-left-width: 4px;
  border-left-color: var(--green) !important;
}

/* Teams */
.teams-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  flex-wrap: wrap;
}
/* Bloque de equipo: escudo + info */
.team-block {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 160px;
}
/* Home: [crest LEFT][info expanding right] */
.home-block { flex-direction: row; }
/* Away: [info expanding left][crest RIGHT] */
.away-block { flex-direction: row; }
/* Info textual del equipo */
.team-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.home-info { align-items: flex-end; text-align: right; }
.away-info { align-items: flex-start; text-align: left; }
/* Meta: estrellas + forma */
.team-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.home-info .team-meta { justify-content: flex-end; }
/* Escudo del equipo */
.crest-wrap {
  position: relative;
  flex-shrink: 0;
  width: 52px;
  height: 52px;
}
.team-crest {
  width: 52px;
  height: 52px;
  object-fit: contain;
  border-radius: 4px;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,.4));
}
.crest-wrap .crest-placeholder {
  position: absolute;
  top: 0; left: 0;
}
.crest-placeholder {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--bg3);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: bold;
  color: var(--dim);
  flex-shrink: 0;
}
/* Badge de posición en tabla — esquina inferior-derecha del escudo */
.pos-badge {
  position: absolute;
  bottom: -4px;
  right: -4px;
  min-width: 22px;
  height: 20px;
  padding: 0 5px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px solid var(--bg);
  box-shadow: 0 2px 4px rgba(0,0,0,.5);
  z-index: 2;
}
.pos-top { background: #3fb950; color: #0d1117; }   /* 1-4: Champions */
.pos-eur { background: #58A6FF; color: #0d1117; }   /* 5-6: Europa */
.pos-mid { background: #8b949e; color: #0d1117; }   /* 7-12: mid-table */
.pos-low { background: #F85149; color: #fff;     }  /* 13+: descenso */
.team-name {
  font-size: 1.1rem;
  font-weight: bold;
  color: var(--text);
}
.home-name { text-align: right; }
.away-name { text-align: left; }
/* Badges últimos 5 partidos */
.form5 { display: inline-flex; gap: 3px; align-items: center; }
.f5-badge {
  display: inline-block;
  width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  font-size: 10px;
  font-weight: 800;
  border-radius: 3px;
}
.f5-win  { background: rgba(63,185,80,.25);  color: #3fb950; border: 1px solid rgba(63,185,80,.5); }
.f5-draw { background: rgba(227,179,65,.20); color: #e3b341; border: 1px solid rgba(227,179,65,.4); }
.f5-loss { background: rgba(248,81,73,.18);  color: #f85149; border: 1px solid rgba(248,81,73,.4); }
.vs-separator {
  color: var(--dim);
  font-size: 12px;
  font-weight: bold;
  letter-spacing: 2px;
  flex-shrink: 0;
}
.formation {
  display: inline-block;
  background: var(--bg3);
  color: var(--dim);
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 4px;
  font-weight: normal;
}

/* Recommendation */
.recommendation {
  margin: 0 16px 12px;
  padding: 10px 16px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
}
.edge-big  .recommendation,
.recommendation.edge-big  { background: rgba(63,185,80,.15); border: 1px solid rgba(63,185,80,.4); }
.recommendation.edge-good { background: rgba(63,185,80,.10); border: 1px solid rgba(63,185,80,.25); }
.recommendation.edge-ok   { background: rgba(210,153,34,.10); border: 1px solid rgba(210,153,34,.3); }
.recommendation.edge-neg  { background: var(--bg3); border: 1px solid var(--border); }
.recommendation.no-bet    {
  background: rgba(139,148,158,.10);
  border: 1px solid rgba(139,148,158,.4);
  border-left: 3px solid #8B949E;
}
.rec-arrow { font-size: 15px; font-weight: bold; letter-spacing: .5px; }
.edge-big  .rec-arrow,
.recommendation.edge-big  .rec-arrow { color: var(--green); }
.recommendation.edge-good .rec-arrow { color: var(--green); }
.recommendation.edge-ok   .rec-arrow { color: var(--orange); }
.recommendation.no-bet    .rec-arrow { color: #8B949E; }
.no-bet-reason { color: var(--dim); font-size: 12px; font-weight: 400; }
.rec-detail { color: var(--dim); font-size: 13px; }
.rec-detail strong { color: var(--text); }
/* Recomendación dual: Principal + Alternativa */
.rec-main { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.rec-primary { font-size: 15px; font-weight: 600; color: var(--green); }
.rec-secondary { font-size: 13px; color: var(--dim); }
.rec-secondary strong { color: var(--text); font-weight: 600; }
.rec-prob { font-weight: 700; margin-left: 2px; }
.rec-edge-info {
  font-size: 11px;
  margin-left: 8px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
}
.edge-pos { background: rgba(63,185,80,.18); color: #3FB950; }
.edge-neg { background: rgba(248,81,73,.18); color: #F85149; }
.edge-neu { background: rgba(139,148,158,.15); color: #8B949E; }
/* Niveles de riesgo */
.risk-low  { color: #3FB950; font-weight: 700; }
.risk-mid  { color: #F0883E; font-weight: 700; }
.risk-high { color: #F85149; font-weight: 700; }

/* Data columns */
.data-cols {
  display: flex;
  gap: 0;
  padding: 0 16px 12px;
  flex-wrap: wrap;
}
.col-table { flex: 1; min-width: 260px; }
.col-bars  { flex: 1; min-width: 240px; padding-left: 20px; }

/* Prob table */
.section-title {
  font-size: 11px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: .8px;
  color: var(--dim);
  margin-bottom: 6px;
  margin-top: 12px;
  padding: 0 0 4px;
  border-bottom: 1px solid var(--border);
}
.prob-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.prob-table th {
  text-align: center;
  color: var(--dim);
  font-weight: 600;
  padding: 4px 8px;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}
.prob-table td {
  text-align: center;
  padding: 6px 8px;
  border-bottom: 1px solid var(--bg3);
}
.tbl-label { text-align: left !important; color: var(--dim); font-size: 12px; }
.poly-val  { color: var(--purple); font-size: 11px; }
.model-row td { font-weight: bold; }
.edge-row  { background: var(--bg3); }
.edge-cell { font-weight: bold; font-size: 13px; }
.edge-label { color: var(--dim); font-style: italic; }

/* Edge colors */
.edge-big  { color: var(--green) !important; }
.edge-good { color: #58d68d !important; }
.edge-ok   { color: var(--orange) !important; }
.edge-neg  { color: var(--dim) !important; }

/* Bars */
.bars-wrap { margin-top: 4px; }
.bar-group { margin-bottom: 10px; }
.bar-label { font-size: 11px; font-weight: bold; color: var(--dim); margin-bottom: 3px; letter-spacing: .5px; }
.bar-track {
  width: 100%;
  height: 7px;
  background: var(--bg3);
  border-radius: 4px;
  margin-bottom: 2px;
  overflow: hidden;
}
.bar-model { height: 100%; background: var(--cyan); border-radius: 4px; transition: width .5s; }
.bar-poly  { height: 100%; background: var(--purple); border-radius: 4px; transition: width .5s; }
.bar-nums {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.bar-m   { color: var(--cyan); font-weight: bold; min-width: 40px; }
.bar-vs  { color: var(--dim); }
.bar-p   { color: var(--purple); font-weight: bold; min-width: 40px; }
.bar-edge { font-weight: bold; margin-left: auto; font-size: 13px; }
.legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.model-dot  { background: var(--cyan); }
.poly-dot   { background: var(--purple); }

/* Team stats */
.team-stat-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--bg3);
  flex-wrap: wrap;
}
.ts-name  { font-weight: bold; min-width: 160px; font-size: 13px; }
.ts-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}
.pill.atk      { background: rgba(88,166,255,.12); color: var(--cyan); }
.pill.def      { background: rgba(188,140,255,.12); color: var(--purple); }
.pill.form-pos { background: rgba(63,185,80,.12);  color: var(--green); }
.pill.form-neg { background: rgba(248,81,73,.10);  color: var(--red); }
.pill.gol      { background: rgba(227,179,65,.10); color: var(--orange); }

/* H2H */
.h2h-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-top: 4px;
}
.h2h-table td { padding: 4px 8px; border-bottom: 1px solid var(--bg3); }
.h2h-team  { color: var(--text); }
.h2h-score { text-align: center; font-weight: bold; color: var(--orange); width: 60px; }
.h2h-table .right { text-align: right; }
.extras { padding: 0 16px 16px; }

/* Lineup */
.lineup      { margin-top: 6px; }
.lineup-row  { display: flex; align-items: center; gap: 10px; padding: 4px 0; flex-wrap: wrap; border-bottom: 1px solid var(--bg3); }
.pos-label   { font-size: 10px; font-weight: bold; color: var(--dim); width: 32px; flex-shrink: 0; }
.player      { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text); }
.pos-tag     { font-size: 10px; color: var(--dim); background: var(--bg3); padding: 0 4px; border-radius: 3px; }

/* Empty state */
.empty-state {
  text-align: center;
  padding: 80px 40px;
  color: var(--dim);
}
.empty-state h2 { color: var(--orange); margin-bottom: 12px; }

/* Footer */
/* ── RESULTADOS ANTERIORES ── */
.results-section {
  max-width: 1400px;
  margin: 24px auto;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: var(--bg3);
  cursor: pointer;
  font-weight: bold;
  font-size: 14px;
  color: var(--cyan);
  letter-spacing: 1px;
  user-select: none;
}
.results-header:hover { background: rgba(88,166,255,.08); }
.results-toggle { font-size: 12px; color: var(--dim); transition: transform .2s; }
.results-toggle.open { transform: rotate(180deg); }
.results-body { overflow-x: auto; }
.res-stats {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}
.res-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-right: 1px solid var(--border);
  min-width: 80px;
}
.res-stat:last-child { border-right: none; }
.res-stat-val { font-size: 1.3rem; font-weight: 900; }
.res-stat-lbl { font-size: 10px; color: var(--dim); margin-top: 2px; text-transform: uppercase; }
.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.results-table thead tr {
  background: var(--bg3);
  color: var(--dim);
  font-size: 11px;
  text-transform: uppercase;
}
.results-table th, .results-table td { padding: 9px 12px; border-bottom: 1px solid var(--border); }
.results-table tbody tr:hover { background: rgba(255,255,255,.03); }
.res-win .res-ico { color: var(--green); font-weight: bold; }
.res-loss .res-ico { color: var(--red); font-weight: bold; }
.res-league { color: var(--orange); font-size: 11px; }
.res-teams { color: var(--text); }
.res-bet { color: var(--cyan); font-weight: bold; }
.res-result { color: var(--dim); }
.edge-neg { color: var(--red) !important; }

.footer {
  text-align: center;
  padding: 24px;
  color: var(--dim);
  font-size: 12px;
  border-top: 1px solid var(--border);
  margin-top: 20px;
}

@media (max-width: 900px) {
  .layout-body { flex-direction: column; }
  .sidebar {
    width: 100%;
    position: static;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    overflow-x: auto;
    overflow-y: visible;
  }
  .sidebar-title { width: 100%; }
  .sidebar .league-btn {
    width: auto;
    border-left: none;
    border-bottom: 3px solid transparent;
    padding: 8px 12px;
    white-space: nowrap;
  }
  .sidebar .league-btn.active {
    border-bottom-color: var(--cyan);
    border-left-color: transparent;
  }
  .sidebar .all-btn.active {
    border-bottom-color: var(--green);
    border-left-color: transparent;
  }
}
@media (max-width: 720px) {
  .cards-grid { grid-template-columns: 1fr; padding: 12px; }
  .data-cols  { flex-direction: column; }
  .col-bars   { padding-left: 0; }
  .teams-row  { flex-direction: column; gap: 8px; }
  .home-name, .away-name { text-align: center; }
}
"""

JS = """
/* ── Countdown ── */
let refreshSecs = REFRESH_SECS;
function tick() {
  refreshSecs--;
  const m = Math.floor(refreshSecs / 60);
  const s = String(refreshSecs % 60).padStart(2, '0');
  const el = document.getElementById('countdown');
  if (el) el.textContent = m + ':' + s;
  if (refreshSecs <= 0) {
    // Guardar estado de filtros antes de recargar
    localStorage.setItem('bs_leagues', JSON.stringify([...activeLeagues]));
    localStorage.setItem('bs_date',    activeDate);
    localStorage.setItem('bs_edge',    String(minEdgePct));
    location.reload();
  }
}
setInterval(tick, 1000);

/* ── Filtros ── */
let activeLeagues = new Set(['__all__']);
let activeDate    = '';
let minEdgePct    = -20;   // por defecto muestra TODOS los partidos
let onlyLive      = false;

function applyFilters() {
  const cards = document.querySelectorAll('.card');
  let visible = 0;

  cards.forEach(card => {
    const league = card.dataset.league;
    const date   = card.dataset.date;
    const edge   = parseFloat(card.dataset.edge || '0');
    const isLive = card.dataset.live === '1';

    const leagueOk = activeLeagues.has('__all__') || activeLeagues.has(league);
    const dateOk   = !activeDate || date === activeDate;
    const edgeOk   = edge >= minEdgePct;
    const liveOk   = !onlyLive || isLive;

    if (leagueOk && dateOk && edgeOk && liveOk) {
      card.classList.remove('hidden');
      visible++;
    } else {
      card.classList.add('hidden');
    }
  });

  const noRes = document.getElementById('no-results');
  if (noRes) noRes.style.display = visible === 0 ? 'block' : 'none';

  const countEl = document.getElementById('filter-count');
  if (countEl) countEl.innerHTML = `Mostrando <strong>${visible}</strong> de <strong>${cards.length}</strong>`;

  updateSidebarCounts();
}

/* ── Actualiza contadores del sidebar según fecha+edge activos ── */
function updateSidebarCounts() {
  const cards = document.querySelectorAll('.card');
  const counts = {};
  let totalVisible = 0;

  cards.forEach(card => {
    const date = card.dataset.date;
    const edge = parseFloat(card.dataset.edge || '0');
    const dateOk = !activeDate || date === activeDate;
    const edgeOk = edge >= minEdgePct;

    if (dateOk && edgeOk) {
      const lg = card.dataset.league || '';
      counts[lg] = (counts[lg] || 0) + 1;
      totalVisible++;
    }
  });

  document.querySelectorAll('.sidebar .league-btn[data-slug]').forEach(btn => {
    const slug = btn.dataset.slug;
    const count = slug === '__all__' ? totalVisible : (counts[slug] || 0);
    const countEl = btn.querySelector('.lgcount');
    if (countEl) countEl.textContent = count;
    if (slug !== '__all__') {
      btn.classList.toggle('lg-empty', count === 0);
    }
  });
}

function toggleLeague(slug) {
  if (slug === '__all__') {
    activeLeagues = new Set(['__all__']);
  } else {
    activeLeagues.delete('__all__');
    if (activeLeagues.has(slug)) {
      activeLeagues.delete(slug);
      if (activeLeagues.size === 0) activeLeagues = new Set(['__all__']);
    } else {
      activeLeagues.add(slug);
    }
  }
  // Actualizar clases de botones
  document.querySelectorAll('.league-btn').forEach(btn => {
    const s = btn.dataset.slug;
    btn.classList.toggle('active',
      s === '__all__' ? activeLeagues.has('__all__') : activeLeagues.has(s));
  });
  applyFilters();
}

function setDate(val) {
  activeDate = val;
  document.getElementById('date-clear').style.display = val ? 'inline-block' : 'none';
  // Marcar botón activo en azul
  document.querySelectorAll('.date-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.date === val);
  });
  // Sincronizar date-picker
  const picker = document.getElementById('date-picker');
  if (picker && val) picker.value = val;
  applyFilters();
  showLeagueDateCount(val);
}

function clearDate() {
  activeDate = '';
  document.getElementById('date-picker').value = '';
  document.getElementById('date-clear').style.display = 'none';
  // Quitar activo de todos los botones de fecha
  document.querySelectorAll('.date-btn').forEach(btn => btn.classList.remove('active'));
  applyFilters();
  showLeagueDateCount('');
}

function showLeagueDateCount(date) {
  const container = document.getElementById('league-date-count');
  if (!container) return;
  if (!date) { container.style.display = 'none'; return; }

  // Contar partidos por liga para esa fecha
  const counts = {};
  document.querySelectorAll('.card').forEach(card => {
    if (card.dataset.date === date) {
      const lg = card.dataset.leagueName || card.dataset.league || '';
      counts[lg] = (counts[lg] || 0) + 1;
    }
  });

  if (Object.keys(counts).length === 0) { container.style.display = 'none'; return; }

  let html = '<span class="ldc-label">📅 Partidos el ' + date.split('-').reverse().join('/') + ':</span>';
  Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .forEach(([lg, n]) => {
      const words = lg.replace(/_/g, ' ').split(' ');
      const display = words.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      html += `<span class="ldc-pill">${display}<span>${n}</span></span>`;
    });

  container.innerHTML = html;
  container.style.display = 'flex';
}

function setEdge(val) {
  minEdgePct = parseFloat(val);
  document.getElementById('edge-val').textContent = val + '%';
  applyFilters();
}

function toggleLive() {
  onlyLive = !onlyLive;
  const btn = document.getElementById('live-btn');
  if (btn) btn.classList.toggle('active', onlyLive);
  applyFilters();
}

// ── RESULTADOS ANTERIORES ─────────────────────────────────────────
let resultsOpen = true;
function toggleResults() {
  resultsOpen = !resultsOpen;
  const body   = document.getElementById('results-body');
  const toggle = document.getElementById('results-toggle');
  if (body)   body.style.display   = resultsOpen ? 'block' : 'none';
  if (toggle) toggle.classList.toggle('open', resultsOpen);
}

// ── RELOJ EN VIVO ─────────────────────────────────────────────────
// Actualiza el minuto de todos los partidos en vivo cada segundo
const PAGE_LOADED_TS = Date.now();  // ms cuando se cargó la página

function updateLiveClocks() {
  const clocks = document.querySelectorAll('.live-clock');
  const secondsElapsed = Math.floor((Date.now() - PAGE_LOADED_TS) / 1000);

  clocks.forEach(el => {
    const baseSecs  = parseFloat(el.dataset.clock || '0');
    const period    = parseInt(el.dataset.period || '1');
    const halftime  = el.dataset.halftime === '1';

    if (halftime) { el.textContent = 'DESCANSO'; return; }

    const totalSecs = baseSecs + secondsElapsed;
    const mins = Math.floor(totalSecs / 60);

    let label;
    if (period === 1) {
      label = mins >= 45 ? '45+' + (mins - 45) + "'" : mins + "'";
    } else {
      label = mins >= 90 ? '90+' + (mins - 90) + "'" : mins + "'";
    }
    el.textContent = label;
  });
}

// Inicializar al cargar
document.addEventListener('DOMContentLoaded', () => {
  // ── Restaurar filtros guardados antes del reload ──────────────
  const savedLeagues = localStorage.getItem('bs_leagues');
  const savedDate    = localStorage.getItem('bs_date');
  const savedEdge    = localStorage.getItem('bs_edge');
  localStorage.removeItem('bs_leagues');
  localStorage.removeItem('bs_date');
  localStorage.removeItem('bs_edge');

  if (savedLeagues) {
    try {
      activeLeagues = new Set(JSON.parse(savedLeagues));
    } catch(e) { activeLeagues = new Set(['__all__']); }
    document.querySelectorAll('.league-btn').forEach(btn => {
      const s = btn.dataset.slug;
      btn.classList.toggle('active',
        s === '__all__' ? activeLeagues.has('__all__') : activeLeagues.has(s));
    });
  }

  if (savedDate && savedDate !== '') {
    activeDate = savedDate;
    document.querySelectorAll('.date-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.date === savedDate);
    });
    const picker = document.getElementById('date-picker');
    if (picker) picker.value = savedDate;
    const clearBtn = document.getElementById('date-clear');
    if (clearBtn) clearBtn.style.display = 'inline-block';
    showLeagueDateCount(savedDate);
  }

  if (savedEdge !== null && savedEdge !== '') {
    minEdgePct = parseFloat(savedEdge);
    const slider = document.getElementById('edge-slider');
    if (slider) slider.value = minEdgePct;
    const valEl = document.getElementById('edge-val');
    if (valEl) valEl.textContent = minEdgePct + '%';
  }

  applyFilters();

  // Resaltar fecha de hoy en el picker
  const today = new Date().toISOString().slice(0,10);
  const picker = document.getElementById('date-picker');
  if (picker) picker.setAttribute('min', today);

  // Arrancar timer del reloj en vivo (cada segundo)
  if (document.querySelectorAll('.live-clock').length > 0) {
    setInterval(updateLiveClocks, 1000);
    updateLiveClocks();
  }
});
"""

# ─────────────────────────────────────────────────────────────────
def _results_section(results: List[Dict], stats: Dict) -> str:
    """Genera la sección HTML de resultados anteriores."""
    if not results and not stats:
        return ""

    # Stats bar
    if stats:
        wr   = stats.get("win_rate", 0)
        pnl  = stats.get("total_profit", 0)
        pnl_cls = "edge-big" if pnl > 0 else "edge-neg"
        brier = stats.get("brier_score", 0)
        stats_html = f"""
        <div class="res-stats">
          <div class="res-stat"><span class="res-stat-val">{stats.get('total',0)}</span><span class="res-stat-lbl">Predicciones</span></div>
          <div class="res-stat"><span class="res-stat-val" style="color:var(--green)">{stats.get('wins',0)}</span><span class="res-stat-lbl">Aciertos</span></div>
          <div class="res-stat"><span class="res-stat-val" style="color:var(--red)">{stats.get('losses',0)}</span><span class="res-stat-lbl">Fallos</span></div>
          <div class="res-stat"><span class="res-stat-val">{wr}%</span><span class="res-stat-lbl">% Acierto</span></div>
          <div class="res-stat"><span class="res-stat-val {pnl_cls}">{pnl:+.1f}%</span><span class="res-stat-lbl">P&L Total</span></div>
          <div class="res-stat"><span class="res-stat-val">{brier}</span><span class="res-stat-lbl">Brier Score</span></div>
          <div class="res-stat"><span class="res-stat-val" style="color:var(--dim)">{stats.get('pending',0)}</span><span class="res-stat-lbl">Pendientes</span></div>
        </div>"""
    else:
        stats_html = ""

    if not results:
        rows_html = '<tr><td colspan="8" style="text-align:center;color:var(--dim);padding:20px">Sin resultados aun</td></tr>'
    else:
        rows = []
        for r in results[:30]:
            ok  = r.get("correct")
            pnl = r.get("profit_pct", 0) or 0
            ico = "✓" if ok else "✗"
            row_cls = "res-win" if ok else "res-loss"
            date_lbl = r.get("date","")[:10]
            best = r.get("best_outcome","?").upper()
            actual = r.get("result","?").upper()
            score = f"{r.get('home_score','?')}–{r.get('away_score','?')}"
            edge_lbl = f"{r.get('best_edge',0)*100:+.1f}%"
            pnl_lbl  = f"{pnl:+.1f}%"
            pnl_cls  = "color:var(--green)" if pnl >= 0 else "color:var(--red)"
            rows.append(f"""
            <tr class="{row_cls}">
              <td class="res-ico">{ico}</td>
              <td>{date_lbl}</td>
              <td class="res-league">{r.get('league_name','')}</td>
              <td class="res-teams">{r.get('home_team','')[:18]} <strong>{score}</strong> {r.get('away_team','')[:18]}</td>
              <td class="res-bet">{best}</td>
              <td class="res-result">{actual}</td>
              <td>{edge_lbl}</td>
              <td style="{pnl_cls};font-weight:bold">{pnl_lbl}</td>
            </tr>""")
        rows_html = "\n".join(rows)

    return f"""
    <section class="results-section">
      <div class="results-header" onclick="toggleResults()">
        <span>&#128202; RESULTADOS ANTERIORES</span>
        <span class="results-toggle" id="results-toggle">&#9660;</span>
      </div>
      {stats_html}
      <div class="results-body" id="results-body">
        <table class="results-table">
          <thead>
            <tr>
              <th></th><th>Fecha</th><th>Liga</th><th>Partido</th>
              <th>Apuesta</th><th>Resultado</th><th>Edge</th><th>P&L</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </section>"""


def generate_report(
    opportunities: List[Dict],
    min_edge: float,
    total_analyzed: int,
    refresh_secs: int = 300,
    output_path: str = REPORT_PATH,
) -> str:
    """
    Genera report.html y retorna la ruta del archivo.
    """
    now_str = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")

    # Mostrar TODOS los partidos analizados (con Polymarket válido).
    # El slider de edge en el HTML hace el filtrado lado cliente.
    # Antes filtrábamos server-side por min_edge (4%) y desaparecían
    # partidos con poco edge → ahora aparecen todos.
    visible = list(opportunities)
    visible.sort(key=lambda x: (
        0 if x.get("status") in ("in", "halftime") else 1,
        -max(x["edge_home"], x["edge_draw"], x["edge_away"])
    ))

    all_visible = visible  # alias por compatibilidad
    leagues = sorted({o["league_name"] for o in visible})
    best_edge_overall = max(
        (max(o["edge_home"], o["edge_draw"], o["edge_away"]) for o in visible),
        default=0,
    )

    # Fechas: SIEMPRE mostrar hoy + 7 días, independiente de las oportunidades.
    # Esto da continuidad visual y el usuario puede confirmar que no faltan días.
    from datetime import timedelta as _td
    today = datetime.now().date()
    dates_sorted = [(today + _td(days=i)).strftime("%Y-%m-%d") for i in range(0, 8)]

    # Cards HTML
    if visible:
        cards_html = "\n".join(_card(o, i+1) for i, o in enumerate(visible))
        no_results = '<div id="no-results"><h3>Sin resultados</h3><p>Cambia los filtros para ver mas partidos.</p></div>'
        content = f'<div class="cards-grid">{cards_html}{no_results}</div>'
    else:
        content = f"""
        <div class="empty-state">
          <h2>Sin oportunidades</h2>
          <p>{total_analyzed} partidos analizados con edge &lt; {min_edge*100:.0f}%</p>
        </div>"""

    # Cargar stats del tracker ANTES del summary
    try:
        import results_tracker as _rt
        past_results = _rt.get_recent_results(30)
        result_stats = _rt.get_stats()
    except Exception:
        past_results = []
        result_stats = {}

    # Construir badge de predicciones
    if result_stats and result_stats.get("total", 0) > 0:
        wins  = result_stats["wins"]
        total = result_stats["total"]
        wr    = result_stats["win_rate"]
        pnl   = result_stats.get("total_profit", 0)
        pnl_s = f"{pnl:+.1f}%"
        # Color según win rate
        if wr >= 60:
            wr_col = "var(--green)"
        elif wr >= 45:
            wr_col = "var(--orange)"
        else:
            wr_col = "var(--red)"
        pnl_col = "var(--green)" if pnl >= 0 else "var(--red)"
        pred_badge = (
            f'<span class="pred-counter">'
            f'<span class="pred-label">&#127919; Predicciones</span>'
            f'<span class="pred-score" style="color:{wr_col}">{wins}/{total}</span>'
            f'<span class="pred-wr" style="color:{wr_col}">({wr}%)</span>'
            f'<span class="pred-sep">|</span>'
            f'<span class="pred-pnl" style="color:{pnl_col}">P&L {pnl_s}</span>'
            f'</span>'
        )
    else:
        pred_badge = '<span class="pred-counter pred-empty">&#127919; Sin historial aun</span>'

    # Summary bar
    summary = f"""
    <div class="summary-bar">
      <span>&#9650; <strong>{len(visible)}</strong> oportunidades</span>
      <span>&#9679; <strong>{total_analyzed}</strong> partidos analizados</span>
      <span>&#128200; Edge max: <strong>{_edge_str(best_edge_overall)}</strong></span>
      <span>&#127942; <strong>{len(leagues)}</strong> ligas</span>
      <span>&#128344; Min edge filtro: <strong>{min_edge*100:.0f}%</strong></span>
      {pred_badge}
    </div>"""

    # ── Sidebar: SOLO las ligas activas en LEAGUES ──────────────────
    ALL_LEAGUES = [
        ("premier_league",    "Premier League"),
        ("la_liga",           "La Liga"),
        ("bundesliga",        "Bundesliga"),
        ("ligue_1",           "Ligue 1"),
        ("serie_a",           "Serie A"),
        ("champions_league",  "Champions League"),
        ("brasileirao",       "Brasileirão"),
        ("liga_mx",           "Liga MX"),
        ("mls",               "MLS"),
        ("fifa_world_cup",    "Mundial 2026"),
    ]
    sidebar_btns = (
        '<button class="league-btn all-btn active" data-slug="__all__" '
        'onclick="toggleLeague(\'__all__\')">'
        '<span>&#9733; Todas</span><span class="lgcount">0</span></button>\n'
    )
    for slug, name in ALL_LEAGUES:
        sidebar_btns += (
            f'<button class="league-btn" data-slug="{slug}" '
            f'onclick="toggleLeague(\'{slug}\')">'
            f'<span>{name}</span><span class="lgcount">0</span></button>\n'
        )

    sidebar_html = f"""
    <aside class="sidebar">
      <div class="sidebar-title">&#9917; Ligas</div>
      {sidebar_btns}
    </aside>"""

    # Botones de fecha rápida (con data-date para JS)
    date_btns = ""
    for d in dates_sorted[:7]:  # max 7 días
        label = datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m")
        safe_id = f"date-btn-{d.replace('-','')}"
        date_btns += (
            f'<button class="league-btn date-btn" id="{safe_id}" data-date="{d}" '
            f'onclick="setDate(\'{d}\')">{label}</button>\n'
        )

    filter_bar = f"""
    <div class="filter-bar">
      <div class="filter-section">
        <span class="filter-label">&#128197; Fecha</span>
        {date_btns}
        <input type="date" id="date-picker" class="date-input"
               onchange="setDate(this.value)" title="Filtrar por fecha">
        <button class="date-clear" id="date-clear" onclick="clearDate()" style="display:none">&#10005; Limpiar</button>
      </div>
      <div class="filter-divider"></div>
      <div class="filter-section">
        <span class="filter-label">&#128200; Min Edge</span>
        <input type="range" class="edge-slider" id="edge-slider"
               min="-20" max="30" step="1" value="-20"
               oninput="setEdge(this.value)">
        <span class="edge-val" id="edge-val">-20%</span>
      </div>
      <div class="filter-divider"></div>
      <div class="filter-section">
        <button class="live-btn" id="live-btn" onclick="toggleLive()">
          <span class="live-dot"></span> EN VIVO
        </button>
      </div>
      <span class="filter-count" id="filter-count"></span>
    </div>
    <div class="league-date-count" id="league-date-count" style="display:none"></div>"""

    results_html = _results_section(past_results, result_stats)

    js_code = JS.replace("REFRESH_SECS", str(refresh_secs))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Opportunity Finder - BotSport</title>
  <style>{CSS}</style>
</head>
<body>

<header class="global-header">
  <h1>&#9889; OPPORTUNITY FINDER &mdash; BotSport</h1>
  <div class="header-meta">
    <div>Actualizado: <strong>{now_str}</strong></div>
    <div>Modelo: Poisson Dixon-Coles</div>
    <div>Refrescando en: <span id="countdown">{refresh_secs//60}:00</span></div>
  </div>
</header>

{summary}

{filter_bar}

<div class="layout-body">
{sidebar_html}
<div class="main-content">
{content}

{results_html}
</div>
</div>

<div class="footer">
  BotSport Opportunity Finder &mdash; Generado: {now_str} &mdash; {total_analyzed} partidos analizados
</div>

<script>{js_code}</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
