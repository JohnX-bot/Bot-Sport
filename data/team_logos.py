#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
team_logos.py
Mapeo de nombres de equipo (ESPN) → ruta local del escudo.

Las rutas son relativas a report.html (raíz del proyecto),
usando la carpeta Escudos/ que contiene los PNG por liga.

Se usa una clave normalizada (sin tildes, sin espacios, sin "FC"/"CF"/etc.)
para hacer el match fuzzy con los nombres que devuelve ESPN.
"""

import unicodedata
import re
import os

# ── Ruta base de escudos (relativa al report.html) ──────────────────
ESCUDOS_BASE = "Escudos"

# ── Mapeo: clave normalizada → ruta relativa al report.html ─────────
# Clave = nombre del equipo sin tildes/espacios/palabras comunes
_RAW_MAP: dict = {

    # ── PREMIER LEAGUE ───────────────────────────────────────────────
    "arsenal":                  "Escudos/premier/arsenal.png",
    "astonvilla":               "Escudos/premier/astonvilla.png",
    "bournemouth":              "Escudos/premier/bournemouth.png",
    "brentford":                "Escudos/premier/brentford.png",
    "brighton":                 "Escudos/premier/brighton.png",
    "brightonhovealbion":       "Escudos/premier/brighton.png",
    "burnley":                  "Escudos/premier/burnley.png",
    "chelsea":                  "Escudos/premier/chelsea.png",
    "crystalpalace":            "Escudos/premier/crystalpalace.png",
    "everton":                  "Escudos/premier/everton.png",
    "fulham":                   "Escudos/premier/fulham.png",
    "leeds":                    "Escudos/premier/leeds.png",
    "leedsunited":              "Escudos/premier/leeds.png",
    "liverpool":                "Escudos/premier/liverpool.png",
    "manchestercity":           "Escudos/premier/manchestercity.png",
    "manchesterunited":         "Escudos/premier/manchesterunited.png",
    "newcastle":                "Escudos/premier/newcastle.png",
    "newcastleunited":          "Escudos/premier/newcastle.png",
    "nottinghamforest":         "Escudos/premier/nottingham_forest.png",
    "sunderland":               "Escudos/premier/sunderland.png",
    "tottenham":                "Escudos/premier/tottenham.png",
    "tottenhamphotspur":        "Escudos/premier/tottenham.png",
    "westham":                  "Escudos/premier/westham.png",
    "westhamunited":            "Escudos/premier/westham.png",
    "wolves":                   "Escudos/premier/wolves.png",
    "wolverhampton":            "Escudos/premier/wolves.png",
    "wolverhamptonwanderers":   "Escudos/premier/wolves.png",
    "ipswich":                  "",   # no está en carpeta
    "leicester":                "",
    "southampton":              "",

    # ── BUNDESLIGA ───────────────────────────────────────────────────
    "augsburg":                 "Escudos/bundesliga/augsburgo.png",
    "augsburgo":                "Escudos/bundesliga/augsburgo.png",
    "bayerleverkusen":          "Escudos/bundesliga/bayerleverkusen.png",
    "leverkusen":               "Escudos/bundesliga/bayerleverkusen.png",
    "bayernmunich":             "Escudos/bundesliga/bayernmunchen.png",
    "bayernmunchen":            "Escudos/bundesliga/bayernmunchen.png",
    "fcbayernmunchen":          "Escudos/bundesliga/bayernmunchen.png",
    "borussiamonchengladbach":  "Escudos/bundesliga/bmonchengladbach.png",
    "borussiadortmund":         "Escudos/bundesliga/borussiadortmund.png",
    "dortmund":                 "Escudos/bundesliga/borussiadortmund.png",
    "eintrachtfrankfurt":       "Escudos/bundesliga/eintrachtfrankfurt.png",
    "frankfurt":                "Escudos/bundesliga/eintrachtfrankfurt.png",
    "freiburg":                 "Escudos/bundesliga/freiburg.png",
    "scfreiburg":               "Escudos/bundesliga/freiburg.png",
    "hamburger":                "Escudos/bundesliga/hamburgo.png",
    "hamburgersv":              "Escudos/bundesliga/hamburgo.png",
    "heidenheim":               "Escudos/bundesliga/heidenheim.png",
    "hoffenheim":               "Escudos/bundesliga/hoffenheim.png",
    "tsghoffenheim":            "Escudos/bundesliga/hoffenheim.png",
    "koln":                     "Escudos/bundesliga/koln.png",
    "cologne":                  "Escudos/bundesliga/koln.png",
    "mainz":                    "Escudos/bundesliga/mainz05.png",
    "mainz05":                  "Escudos/bundesliga/mainz05.png",
    "rbleipzig":                "Escudos/bundesliga/rbleipzig.png",
    "leipzig":                  "Escudos/bundesliga/rbleipzig.png",
    "stpauli":                  "Escudos/bundesliga/st_pauli.png",
    "stuttgart":                "Escudos/bundesliga/stuttgart.png",
    "vfbstuttgart":             "Escudos/bundesliga/stuttgart.png",
    "unionberlin":              "Escudos/bundesliga/unionberlin.png",
    "werderbremen":             "Escudos/bundesliga/werderbremen.png",
    "bremen":                   "Escudos/bundesliga/werderbremen.png",
    "wolfsburg":                "Escudos/bundesliga/wolfsburg.png",
    "vflwolfsburg":             "Escudos/bundesliga/wolfsburg.png",
    "holsteinkiel":             "",
    "bochum":                   "",

    # ── LA LIGA ──────────────────────────────────────────────────────
    "alaves":                   "Escudos/laliga/alaves.png",
    "deportivoalaves":          "Escudos/laliga/alaves.png",
    "athletic":                 "Escudos/laliga/athletic.png",
    "athleticclub":             "Escudos/laliga/athletic.png",
    "athleticbilbao":           "Escudos/laliga/athletic.png",
    "atleticomadrid":           "Escudos/laliga/atlmadrid.png",
    "atleticodemadrid":         "Escudos/laliga/atlmadrid.png",
    "clubatleticodemadrid":     "Escudos/laliga/atlmadrid.png",
    "barcelona":                "Escudos/laliga/barcelona.png",
    "realbetis":                "Escudos/laliga/betis.png",
    "realbetisbalompie":        "Escudos/laliga/betis.png",
    "celtavigo":                "Escudos/laliga/celta.png",
    "rcceltavigo":              "Escudos/laliga/celta.png",
    "elche":                    "Escudos/laliga/elche.png",
    "espanyol":                 "Escudos/laliga/espanyol.png",
    "rcdespanyol":              "Escudos/laliga/espanyol.png",
    "getafe":                   "Escudos/laliga/getafe.png",
    "girona":                   "Escudos/laliga/girona.png",
    "levante":                  "Escudos/laliga/levante.png",
    "mallorca":                 "Escudos/laliga/mallorca.png",
    "rcdmallorca":              "Escudos/laliga/mallorca.png",
    "osasuna":                  "Escudos/laliga/osasuna.png",
    "caosasuna":                "Escudos/laliga/osasuna.png",
    "rayovallecano":            "Escudos/laliga/rayovallecano.png",
    "realmadrid":               "Escudos/laliga/realmadrid.png",
    "realmadridcf":             "Escudos/laliga/realmadrid.png",
    "realsociedad":             "Escudos/laliga/realsociedad.png",
    "sevilla":                  "Escudos/laliga/sevilla.png",
    "sevillafc":                "Escudos/laliga/sevilla.png",
    "valencia":                 "Escudos/laliga/valencia.png",
    "valenciacf":               "Escudos/laliga/valencia.png",
    "villarreal":               "Escudos/laliga/villarreal.png",
    "villarrealcf":             "Escudos/laliga/villarreal.png",
    "leganes":                  "",
    "laspalmas":                "",
    "valladolid":               "",

    # ── LIGUE 1 ──────────────────────────────────────────────────────
    "angers":                   "Escudos/ligue1/angers.png",
    "angersco":                 "Escudos/ligue1/angers.png",
    "auxerre":                  "Escudos/ligue1/auxerre.png",
    "ajauxerre":                "Escudos/ligue1/auxerre.png",
    "lehavre":                  "Escudos/ligue1/havre.png",
    "lehavreac":                "Escudos/ligue1/havre.png",
    "lille":                    "Escudos/ligue1/lille.png",
    "lilleosc":                 "Escudos/ligue1/lille.png",
    "lorient":                  "Escudos/ligue1/lorient.png",
    "metz":                     "Escudos/ligue1/metz.png",
    "fcmetz":                   "Escudos/ligue1/metz.png",
    "monaco":                   "Escudos/ligue1/monaco.png",
    "asmonaco":                 "Escudos/ligue1/monaco.png",
    "nantes":                   "Escudos/ligue1/nantes.png",
    "nice":                     "Escudos/ligue1/niza.png",
    "ogcnice":                  "Escudos/ligue1/niza.png",
    "olympiquedemarseille":     "Escudos/ligue1/olimpiquemarsella.png",
    "marseille":                "Escudos/ligue1/olimpiquemarsella.png",
    "olympiquelyonnais":        "Escudos/ligue1/olympiquelyon.png",
    "lyon":                     "Escudos/ligue1/olympiquelyon.png",
    "parisfc":                  "Escudos/ligue1/paris_fc.png",
    "parissaintgermain":        "Escudos/ligue1/psg.png",
    "psg":                      "Escudos/ligue1/psg.png",
    "rcstrasbourg":             "Escudos/ligue1/racingetrasburgo.png",
    "strasbourg":               "Escudos/ligue1/racingetrasburgo.png",
    "racingclubdelens":         "Escudos/ligue1/racinglens.png",
    "lens":                     "Escudos/ligue1/racinglens.png",
    "staderennais":             "Escudos/ligue1/rennais.png",
    "rennes":                   "Escudos/ligue1/rennais.png",
    "stadebrestois":            "Escudos/ligue1/stadebretois.png",
    "brest":                    "Escudos/ligue1/stadebretois.png",
    "toulouse":                 "Escudos/ligue1/toulouse.png",
    "toulousefc":               "Escudos/ligue1/toulouse.png",
    "reims":                    "",
    "montpellier":              "",
    "stetienne":                "",
    "nancylorraine":            "",

    # ── BRASILEIRÃO ──────────────────────────────────────────────────
    "atleticomineiro":              "Escudos/brasileirao/atlmineiro.png",
    "atleticogomg":                 "Escudos/brasileirao/atlmineiro.png",
    "athleticoparanaense":          "Escudos/brasileirao/atlparanaense.png",
    "clubathleticoparanaense":      "Escudos/brasileirao/atlparanaense.png",
    "bahia":                        "Escudos/brasileirao/bahia.png",
    "ecbahia":                      "Escudos/brasileirao/bahia.png",
    "botafogo":                     "Escudos/brasileirao/botafogo.png",
    "botafogorj":                   "Escudos/brasileirao/botafogo.png",
    "chapecoense":                  "Escudos/brasileirao/chapecoense.png",
    "corinthians":                  "Escudos/brasileirao/corinthians.png",
    "sportclupcorinthians":         "Escudos/brasileirao/corinthians.png",
    "coritiba":                     "Escudos/brasileirao/coritiba.png",
    "cruzeiro":                     "Escudos/brasileirao/cruzeiro.png",
    "flamengo":                     "Escudos/brasileirao/flamengo.png",
    "clubederegatasflamengo":       "Escudos/brasileirao/flamengo.png",
    "crflamengo":                   "Escudos/brasileirao/flamengo.png",
    "fluminense":                   "Escudos/brasileirao/fluminense.png",
    "fluminensefc":                 "Escudos/brasileirao/fluminense.png",
    "gremio":                       "Escudos/brasileirao/gremio.png",
    "gremio footbampoarte":         "Escudos/brasileirao/gremio.png",
    "internacional":                "Escudos/brasileirao/internacional.png",
    "scintermacional":              "Escudos/brasileirao/internacional.png",
    "mirassol":                     "Escudos/brasileirao/mirassol.png",
    "palmeiras":                    "Escudos/brasileirao/palmeiras.png",
    "sociedadeesportivapalmeiras":  "Escudos/brasileirao/palmeiras.png",
    "redbullbragantino":            "Escudos/brasileirao/rbbragantino.png",
    "bragantino":                   "Escudos/brasileirao/rbbragantino.png",
    "redbullbragantino":            "Escudos/brasileirao/rbbragantino.png",
    "santos":                       "Escudos/brasileirao/santos.png",
    "santosfc":                     "Escudos/brasileirao/santos.png",
    "saopaulo":                     "Escudos/brasileirao/saopaulo.png",
    "saopaulofc":                   "Escudos/brasileirao/saopaulo.png",
    "vascodagama":                  "Escudos/brasileirao/vasco.png",
    "crvascodeagama":               "Escudos/brasileirao/vasco.png",
    "vitoria":                      "Escudos/brasileirao/vitoria.png",
    "ecvitoria":                    "Escudos/brasileirao/vitoria.png",
    "fortaleza":                    "",
    "cuiaba":                       "",

    # ── LIGA MX ──────────────────────────────────────────────────────
    "clubamerica":              "Escudos/ligamx/america.png",
    "america":                  "Escudos/ligamx/america.png",
    "atlas":                    "Escudos/ligamx/atlas.png",
    "atleticosanluis":          "Escudos/ligamx/atleticosl.png",
    "cruzazul":                 "Escudos/ligamx/cruzazul.png",
    "guadalajara":              "Escudos/ligamx/guadalajara.png",
    "clubdeportivoguadalajara": "Escudos/ligamx/guadalajara.png",
    "juarez":                   "Escudos/ligamx/juarez.png",
    "fcjuarez":                 "Escudos/ligamx/juarez.png",
    "leon":                     "Escudos/ligamx/leon.png",
    "clubleon":                 "Escudos/ligamx/leon.png",
    "mazatlan":                 "Escudos/ligamx/mazatlan.png",
    "mazatlanfc":               "Escudos/ligamx/mazatlan.png",
    "monterrey":                "Escudos/ligamx/monterrey.png",
    "rayados":                  "Escudos/ligamx/monterrey.png",
    "cfmonterrey":              "Escudos/ligamx/monterrey.png",
    "necaxa":                   "Escudos/ligamx/necaxa.png",
    "pachuca":                  "Escudos/ligamx/pachuca.png",
    "clubpachuca":              "Escudos/ligamx/pachuca.png",
    "puebla":                   "Escudos/ligamx/puebla.png",
    "clubpuebla":               "Escudos/ligamx/puebla.png",
    "pumas":                    "Escudos/ligamx/pumas.png",
    "pumasonam":                "Escudos/ligamx/pumas.png",
    "universidadnacional":      "Escudos/ligamx/pumas.png",
    "queretaro":                "Escudos/ligamx/queretaro.png",
    "santoslaguna":             "Escudos/ligamx/santos.png",
    "tigres":                   "Escudos/ligamx/tigres.png",
    "tigresuanl":               "Escudos/ligamx/tigres.png",
    "tijuana":                  "Escudos/ligamx/tijuana.png",
    "clubtijuana":              "Escudos/ligamx/tijuana.png",
    "toluca":                   "Escudos/ligamx/toluca.png",
    "deportivotoluca":          "Escudos/ligamx/toluca.png",
    "sanluis":                  "",
    "bravos":                   "",

    # ── PRIMEIRA LIGA ────────────────────────────────────────────────
    "alverca":                  "Escudos/primeiraliga/alverca.png",
    "fcalverca":                "Escudos/primeiraliga/alverca.png",
    "arouca":                   "Escudos/primeiraliga/arouca.png",
    "fcarouca":                 "Escudos/primeiraliga/arouca.png",
    "avs":                      "Escudos/primeiraliga/avs.png",
    "benfica":                  "Escudos/primeiraliga/benfica.png",
    "slbenfica":                "Escudos/primeiraliga/benfica.png",
    "braga":                    "Escudos/primeiraliga/braga.png",
    "scbraga":                  "Escudos/primeiraliga/braga.png",
    "casapia":                  "Escudos/primeiraliga/casa_pia.png",
    "casapiaac":                "Escudos/primeiraliga/casa_pia.png",
    "estoril":                  "Escudos/primeiraliga/estoril.png",
    "estorilestrela":           "Escudos/primeiraliga/estoril.png",
    "estrela":                  "Escudos/primeiraliga/estrella.png",
    "cdestrelaamadora":         "Escudos/primeiraliga/estrella.png",
    "famalicao":                "Escudos/primeiraliga/famalicao.png",
    "fcfamalicao":              "Escudos/primeiraliga/famalicao.png",
    "gilvicente":               "Escudos/primeiraliga/gilvicente.png",
    "moreirense":               "Escudos/primeiraliga/moreirense.png",
    "nacional":                 "Escudos/primeiraliga/nacional.png",
    "porto":                    "Escudos/primeiraliga/porto.png",
    "fcporto":                  "Escudos/primeiraliga/porto.png",
    "rioave":                   "Escudos/primeiraliga/rioave.png",
    "rioavefc":                 "Escudos/primeiraliga/rioave.png",
    "santaclara":               "Escudos/primeiraliga/santaclara.png",
    "cfsantaclara":             "Escudos/primeiraliga/santaclara.png",
    "sportingcp":               "Escudos/primeiraliga/sporting.png",
    "sporting":                 "Escudos/primeiraliga/sporting.png",
    "tondela":                  "Escudos/primeiraliga/tondela.png",
    "vitoriaguimaraes":         "Escudos/primeiraliga/vitoria.png",
    "vitoriadesetubalsupport":  "Escudos/primeiraliga/vitoria.png",
    "vitorisc":                 "Escudos/primeiraliga/vitoria.png",

    # ── EREDIVISIE ───────────────────────────────────────────────────
    "ajax":                     "Escudos/eredivisie/ajax.png",
    "afcajax":                  "Escudos/eredivisie/ajax.png",
    "az":                       "Escudos/eredivisie/az.png",
    "azalkmaar":                "Escudos/eredivisie/az.png",
    "excelsior":                "Escudos/eredivisie/excelsior.png",
    "sbvexcelsior":             "Escudos/eredivisie/excelsior.png",
    "feyenoord":                "Escudos/eredivisie/feyenoord.png",
    "fortunasittard":           "Escudos/eredivisie/fortunasittard.png",
    "goadheagles":              "Escudos/eredivisie/go_ahead_eagles.png",
    "groningen":                "Escudos/eredivisie/gronningen.png",
    "fcgroningen":              "Escudos/eredivisie/gronningen.png",
    "heracles":                 "Escudos/eredivisie/heracles.png",
    "heraclesalmelo":           "Escudos/eredivisie/heracles.png",
    "nacbreda":                 "Escudos/eredivisie/nac_breda​.png",
    "nec":                      "Escudos/eredivisie/nec.png",
    "necnijmegen":              "Escudos/eredivisie/nec.png",
    "psv":                      "Escudos/eredivisie/psv.png",
    "psveindhoven":             "Escudos/eredivisie/psv.png",
    "heerenveen":               "Escudos/eredivisie/scheerenveen.png",
    "scheerenveen":             "Escudos/eredivisie/scheerenveen.png",
    "sparterotterdam":          "Escudos/eredivisie/sparta.png",
    "sparta":                   "Escudos/eredivisie/sparta.png",
    "telstar":                  "Escudos/eredivisie/telstar.png",
    "fctwente":                 "Escudos/eredivisie/twente.png",
    "twente":                   "Escudos/eredivisie/twente.png",
    "fcutrecht":                "Escudos/eredivisie/utrecht.png",
    "utrecht":                  "Escudos/eredivisie/utrecht.png",
    "volendam":                 "Escudos/eredivisie/volendam.png",
    "fcvolendam":               "Escudos/eredivisie/volendam.png",
    "zwolle":                   "Escudos/eredivisie/zwolle.png",
    "peczwolle":                "Escudos/eredivisie/zwolle.png",
}

# Eliminar entradas vacías del mapa
LOGO_MAP: dict = {k: v for k, v in _RAW_MAP.items() if v}


def _normalize(name: str) -> str:
    """
    Normaliza un nombre de equipo para matching:
    - Sin tildes/acentos
    - Minúsculas
    - Sin palabras genéricas (FC, CF, SC, AC, etc.)
    - Sin números aislados (años de fundación: "04", "1846", "05", etc.)
    - Sin puntuación ni espacios
    """
    # Eliminar tildes
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    # Minúsculas
    s = ascii_name.lower()
    # Quitar prefijos numéricos tipo "1." al inicio (ej. "1. FC Köln")
    s = re.sub(r'^\d+\.\s*', '', s)
    # Quitar palabras genéricas comunes
    stop = r"\b(fc|cf|sc|ac|rc|cd|sd|bk|if|fk|afc|rcd|slb|sl|ca|ssc|as|ss|us|ud|fsv|tsv|tsf|tsg|vfb|vfl|sv|bv|bvb|sp|ce|de|del|los|las|el|la)\b"
    s = re.sub(stop, " ", s)
    # Quitar números aislados (año de fundación: "04", "1846", "05", etc.)
    # Solo elimina números separados por espacios, no los pegados a letras
    s = re.sub(r'(?<![a-z])\d+(?![a-z])', ' ', s)
    # Quitar puntuación y espacios
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


# Caché de claves normalizadas del mapa
_NORM_MAP: dict = {_normalize(k): v for k, v in LOGO_MAP.items()}


def get_local_logo(team_name: str, fallback_url: str = "") -> str:
    """
    Retorna la ruta local del escudo si existe, o fallback_url si no.

    Args:
        team_name:    Nombre del equipo como lo devuelve ESPN (ej. "FC Bayern München")
        fallback_url: URL de ESPN CDN a usar si no hay logo local

    Returns:
        Ruta relativa tipo "Escudos/premier/arsenal.png"
        o fallback_url si no hay coincidencia local.
    """
    key = _normalize(team_name)
    local = _NORM_MAP.get(key, "")
    if local:
        return local
    # Intentar coincidencia parcial (el nombre normalizado contiene la clave)
    for k, v in _NORM_MAP.items():
        if k and (k in key or key in k) and len(k) >= 4:
            return v
    return fallback_url
