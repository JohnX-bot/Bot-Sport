#!/usr/bin/env python3
"""
Definición Centralizada de Ligas y Equipos

Estructura para validar que los datos sean correctos:
- Cada liga tiene un código único
- Cada liga especifica si es club o selección
- Los equipos están validados contra la liga
"""

from typing import Dict, List, Set


class LeagueDefinition:
    """Define una liga con sus equipos válidos."""

    def __init__(
        self,
        code: str,
        name: str,
        country: str,
        competition_type: str,  # "club" o "international"
        teams: List[str],
    ):
        self.code = code.lower()
        self.name = name
        self.country = country
        self.competition_type = competition_type
        self.teams = set(teams)

    def validate_team(self, team_name: str) -> bool:
        """Verificar si un equipo es válido para esta liga."""
        return team_name in self.teams

    def __repr__(self) -> str:
        return f"League({self.code}: {self.name} - {len(self.teams)} equipos)"


# ────────────────────────────── LIGAS DEFINIDAS ──────────────────────────────

LEAGUES = {
    # Liga Mexicana - CLUBS
    "mex": LeagueDefinition(
        code="mex",
        name="Liga Mexicana (MX1)",
        country="Mexico",
        competition_type="club",
        teams=[
            "Guadalajara",
            "Tigres",
            "Monterrey",
            "Pachuca",
            "Toluca",
            "Pumas",
            "Cruz Azul",
            "Santos",
            "Necaxa",
            "Atletico San Luis",
            "Queretaro",
            "FC Juarez",
            "Mazatlan",
            "Bravos",
            "Atlante",
            "Puebla",
            "Leon",
            "Morelia",
        ],
    ),

    # La Liga - CLUBS
    "laliga": LeagueDefinition(
        code="laliga",
        name="La Liga (España)",
        country="Spain",
        competition_type="club",
        teams=[
            "Real Madrid",
            "Barcelona",
            "Atletico Madrid",
            "Real Sociedad",
            "Villarreal",
            "Athletic Bilbao",
            "Valencia",
            "Sevilla",
            "Getafe",
            "Girona",
            "Osasuna",
            "Mallorca",
            "Real Betis",
            "Rayo Vallecano",
            "Celta",
            "Granada",
            "Cadiz",
            "Almeria",
            "Las Palmas",
            "Alaves",
        ],
    ),

    # Premier League - CLUBS
    "pl": LeagueDefinition(
        code="pl",
        name="Premier League (Inglaterra)",
        country="England",
        competition_type="club",
        teams=[
            "Arsenal",
            "Aston Villa",
            "Bournemouth",
            "Brentford",
            "Brighton",
            "Chelsea",
            "Crystal Palace",
            "Everton",
            "Fulham",
            "Ipswich Town",
            "Leicester City",
            "Liverpool",
            "Manchester City",
            "Manchester United",
            "Newcastle United",
            "Nottingham Forest",
            "Southampton",
            "Tottenham Hotspur",
            "West Ham United",
            "Wolverhampton Wanderers",
        ],
    ),

    # Serie A - CLUBS
    "seriea": LeagueDefinition(
        code="seriea",
        name="Serie A (Italia)",
        country="Italy",
        competition_type="club",
        teams=[
            "AC Milan",
            "Inter Milan",
            "Juventus",
            "Napoli",
            "AS Roma",
            "Lazio",
            "Atalanta",
            "Fiorentina",
            "Torino",
            "Sassuolo",
            "Empoli",
            "Bologna",
            "Monza",
            "Parma",
            "Como",
            "Verona",
            "Cagliari",
            "Lecce",
            "Frosinone",
            "Salernitana",
        ],
    ),

    # Bundesliga - CLUBS
    "bundesliga": LeagueDefinition(
        code="bundesliga",
        name="Bundesliga (Alemania)",
        country="Germany",
        competition_type="club",
        teams=[
            "Bayern Munich",
            "Borussia Dortmund",
            "RB Leipzig",
            "Bayer Leverkusen",
            "Stuttgart",
            "Schalke 04",
            "Eintracht Frankfurt",
            "Hoffenheim",
            "VfL Wolfsburg",
            "Borussia Monchengladbach",
            "Mainz",
            "Augsburg",
            "Cologne",
            "Union Berlin",
            "Werder Bremen",
            "Freiburg",
            "Bochum",
            "Heidenheim",
        ],
    ),

    # Ligue 1 - CLUBS
    "ligue1": LeagueDefinition(
        code="ligue1",
        name="Ligue 1 (Francia)",
        country="France",
        competition_type="club",
        teams=[
            "Paris Saint-Germain",
            "Olympique Marseille",
            "AS Monaco",
            "Olympique Lyonnais",
            "Stade Rennes",
            "Lens",
            "Nice",
            "Toulouse",
            "Strasbourg",
            "Lille",
            "Nantes",
            "Saint-Etienne",
            "Angers",
            "Montpellier",
            "Metz",
            "Reims",
            "Le Havre",
            "Lorient",
        ],
    ),

    # MLS - CLUBS
    "mls": LeagueDefinition(
        code="mls",
        name="Major League Soccer (USA/Canada)",
        country="USA",
        competition_type="club",
        teams=[
            "Atlanta United",
            "Austin FC",
            "Chicago Fire",
            "Colorado Rapids",
            "FC Cincinnati",
            "FC Dallas",
            "Houston Dynamo",
            "LA Galaxy",
            "Los Angeles FC",
            "Minnesota United",
            "Montreal Impact",
            "New England Revolution",
            "New York City FC",
            "New York Red Bulls",
            "Orlando City",
            "Philadelphia Union",
            "Portland Timbers",
            "Real Salt Lake",
            "San Jose Earthquakes",
            "Seattle Sounders",
            "Sporting Kansas City",
            "Toronto FC",
            "Vancouver Whitecaps",
        ],
    ),

    # Brasileiro - CLUBS
    "brasil": LeagueDefinition(
        code="brasil",
        name="Campeonato Brasileiro Serie A (Brasil)",
        country="Brazil",
        competition_type="club",
        teams=[
            "Palmeiras",
            "Botafogo",
            "Flamengo",
            "Atletico Mineiro",
            "Sao Paulo",
            "Santos",
            "Corinthians",
            "Internacional",
            "Gremio",
            "Vasco da Gama",
            "Fortaleza",
            "Cebolinha",
            "Cruzeiro",
            "Bahia",
            "Vitoria",
            "Goias",
            "Cuiaba",
            "RB Bragantino",
        ],
    ),

    # Süper Lig - CLUBS
    "superlig": LeagueDefinition(
        code="superlig",
        name="Süper Lig (Turquia)",
        country="Turkey",
        competition_type="club",
        teams=[
            "Galatasaray",
            "Fenerbahce",
            "Besiktas",
            "Trabzonspor",
            "Istanbul Basaksehir",
            "Kayserispor",
            "Sivasspor",
            "Gaziantep FK",
            "Konyaspor",
            "Kasimpasa",
            "Antalyaspor",
            "Altay",
            "Genclerbirligi",
            "Adana Demirspor",
            "Erzurumspor",
            "Alanyaspor",
            "Istanbulspor",
            "Samsunspor",
        ],
    ),

    # Copa Libertadores - CLUBS
    "libertadores": LeagueDefinition(
        code="libertadores",
        name="Copa Libertadores (America del Sur)",
        country="South America",
        competition_type="club",
        teams=[
            "Flamengo",
            "Palmeiras",
            "Botafogo",
            "Atletico Mineiro",
            "Internacional",
            "Gremio",
            "Boca Juniors",
            "River Plate",
            "Independiente",
            "Racing Club",
            "Estudiantes",
            "Velez Sarsfield",
            "Colo-Colo",
            "Universidad de Chile",
            "Universidad Catolica",
            "Pereira",
            "Millonarios",
            "Santa Fe",
            "Cerro Porteno",
            "Olimpia",
            "Alianza Lima",
            "Universitario",
        ],
    ),

    # Champions League - CLUBS (EUROPA)
    "ucl": LeagueDefinition(
        code="ucl",
        name="UEFA Champions League",
        country="Europe",
        competition_type="club",
        teams=[
            # Top clubs de varias ligas
            "Real Madrid",
            "Barcelona",
            "Bayern Munich",
            "Paris Saint-Germain",
            "Manchester City",
            "Manchester United",
            "Liverpool",
            "AC Milan",
            "Inter Milan",
            "Juventus",
            "Borussia Dortmund",
            "RB Leipzig",
            "Atletico Madrid",
            "Chelsea",
            "Arsenal",
        ],
    ),

    # FIFA World Cup - SELECCIONES
    "worldcup": LeagueDefinition(
        code="worldcup",
        name="FIFA World Cup",
        country="International",
        competition_type="international",
        teams=[
            "Argentina",
            "Brazil",
            "France",
            "Germany",
            "England",
            "Spain",
            "Italy",
            "Netherlands",
            "Belgium",
            "Portugal",
            "Mexico",
            "Uruguay",
            "Croatia",
            "Denmark",
            "Sweden",
            "Norway",
            "Russia",
            "Poland",
            "Japan",
            "South Korea",
            "Australia",
            "USA",
            "Canada",
            "Ecuador",
            "Colombia",
            "Peru",
            "Chile",
            "Venezuela",
            "Paraguay",
            "Bolivia",
            "Senegal",
            "Ghana",
        ],
    ),
}


def get_league(league_code: str) -> LeagueDefinition:
    """Obtener definición de liga."""
    code = league_code.lower()
    if code not in LEAGUES:
        available = ", ".join(LEAGUES.keys())
        raise ValueError(f"Liga desconocida: {code}. Disponibles: {available}")
    return LEAGUES[code]


def validate_team_for_league(team_name: str, league_code: str) -> bool:
    """Validar que un equipo pertenece a una liga."""
    try:
        league = get_league(league_code)
        return league.validate_team(team_name)
    except ValueError:
        return False


def get_all_teams_for_league(league_code: str) -> Set[str]:
    """Obtener todos los equipos de una liga."""
    league = get_league(league_code)
    return league.teams


def main():
    """Test ligas."""
    print("\n[LIGAS DISPONIBLES]\n")
    for code, league in sorted(LEAGUES.items()):
        print(f"  {code:12} : {league.name} ({league.competition_type}) - {len(league.teams):2} equipos")

    # Test validación
    print("\n[VALIDACION DE EQUIPOS]\n")

    test_cases = [
        ("Guadalajara", "mex", True),
        ("Mexico", "mex", False),  # Selección, no equipo de club
        ("Real Madrid", "laliga", True),
        ("Manchester United", "pl", True),
        ("Bayern Munich", "bundesliga", True),
        ("France", "worldcup", True),
        ("France", "laliga", False),  # Selección en liga de clubs
    ]

    for team, league, expected in test_cases:
        result = validate_team_for_league(team, league)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} {team:20} en {league:12} -> {result}")

    print()


if __name__ == "__main__":
    main()
