import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opportunity_finder import get_standings, fetch_poly_all, find_poly_market, team_strengths
from models.poisson_model import calculate_match_probabilities

standings = get_standings("wc2026", "fifa.world")
poly = fetch_poly_all()

wc_matches = [
    ("Mexico","South Africa"), ("South Korea","Czechia"),
    ("Canada","Bosnia-Herzegovina"), ("United States","Paraguay"),
    ("Qatar","Switzerland"), ("Brazil","Morocco"),
    ("Haiti","Scotland"), ("Germany","Curacao"),
    ("Netherlands","Japan"), ("Ivory Coast","Ecuador"),
    ("Spain","Cape Verde"), ("Iran","New Zealand"),
    ("France","Senegal"), ("Argentina","Algeria"), ("England","Croatia"),
]

hosts = {"mexico","united states","canada"}
print(f"{'Partido':<36} {'Modelo H/D/A':<16} {'Poly H/D/A':<16} {'Edge H/D/A'}")
print("-" * 85)
ok = 0
for home, away in wc_matches:
    pm = find_poly_market(home, away, poly)
    s = team_strengths(standings, home, away)
    hadv = 1.20 if home.lower() in hosts else 1.05
    probs = calculate_match_probabilities(
        s["home_attack"], s["home_defense"],
        s["away_attack"], s["away_defense"],
        league_avg_goals=s["league_avg"],
        home_advantage=hadv
    )
    mh = round(probs["home"]*100,1)
    md = round(probs["draw"]*100,1)
    ma = round(probs["away"]*100,1)
    label = (home + " vs " + away)[:35]
    if pm:
        ok += 1
        ph = round(float(pm.get("home_price",0))*100,1)
        pd = round(float(pm.get("draw_price",0) or 0)*100,1)
        pa = round(float(pm.get("away_price",0))*100,1)
        eh = round(mh-ph,1)
        ed = round(md-pd,1)
        ea = round(ma-pa,1)
        print(f"{label:<36}{mh}/{md}/{ma:<14} {ph}/{pd}/{pa:<14} {eh:+.1f}/{ed:+.1f}/{ea:+.1f}")
    else:
        print(f"{label:<36}{mh}/{md}/{ma:<14} -- SIN POLY --")

print(f"\nPolymarket encontrado: {ok}/{len(wc_matches)}")

