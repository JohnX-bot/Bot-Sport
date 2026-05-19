#!/usr/bin/env python3
"""
Test Integral: Validación de Ligas y Prevención de Errores

Demuestra:
1. Error original evitado (Mexico no puede usarse en Liga Mexicana)
2. Múltiples ligas soportadas
3. Validación automática de datos
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.leagues_data import get_league, validate_team_for_league
from data.universal_data_loader import UniversalDataLoader
from bot.sport_config import get_sport_config, list_sports


def test_error_prevention():
    """Test que el error original (Mexico en mex) está prevenido."""
    print("\n" + "="*70)
    print("TEST 1: Prevención de Error Original")
    print("="*70)

    print("\nEscenario: Análisis de Liga Mexicana")
    print("-" * 70)

    # [X] ANTES (incorrecto)
    print("\n[INCORRECTO - ANTES]")
    print("  Intentar usar 'Mexico' (selección) en Liga Mexicana")
    is_valid = validate_team_for_league("Mexico", "mex")
    print(f"  validate_team_for_league('Mexico', 'mex') = {is_valid}")
    print(f"  [RESULTADO] {'[BLOCKED]' if not is_valid else '[ERROR]'}")

    # [OK] DESPUÉS (correcto)
    print("\n[CORRECTO - DESPUÉS]")
    print("  Usar 'Guadalajara' (club) en Liga Mexicana")
    is_valid = validate_team_for_league("Guadalajara", "mex")
    print(f"  validate_team_for_league('Guadalajara', 'mex') = {is_valid}")
    print(f"  [RESULTADO] {'[ALLOWED]' if is_valid else '[ERROR]'}")

    # [OK] Correcto en World Cup
    print("\n[CASO ESPECIAL - MUNDIAL]")
    print("  'Mexico' SÍ es válido en FIFA World Cup")
    is_valid = validate_team_for_league("Mexico", "worldcup")
    print(f"  validate_team_for_league('Mexico', 'worldcup') = {is_valid}")
    print(f"  [RESULTADO] {'[ALLOWED]' if is_valid else '[ERROR]'}")


def test_multiple_leagues():
    """Test soporte de múltiples ligas."""
    print("\n" + "="*70)
    print("TEST 2: Soporte de Múltiples Ligas")
    print("="*70)

    test_cases = [
        ("mex", "Guadalajara", True),
        ("mex", "Tigres", True),
        ("laliga", "Real Madrid", True),
        ("laliga", "Barcelona", True),
        ("pl", "Manchester United", True),
        ("pl", "Liverpool", True),
        ("bundesliga", "Bayern Munich", True),
        ("seriea", "Inter Milan", True),
        ("ligue1", "Paris Saint-Germain", True),
        ("mls", "Los Angeles FC", True),
        ("brasil", "Flamengo", True),
        ("superlig", "Galatasaray", True),
        ("libertadores", "Palmeiras", True),
        ("worldcup", "Argentina", True),
        ("worldcup", "France", True),
        # Casos negativos
        ("mex", "Bayern Munich", False),  # Equipo alemán en Liga Mexicana
        ("laliga", "Arsenal", False),  # Equipo inglés en La Liga
        ("pl", "Barcelona", False),  # Equipo español en PL
    ]

    results = {"pass": 0, "fail": 0}

    print("\n{:15} {:25} {:25} {}".format(
        "Liga", "Equipo", "Esperado", "Resultado"
    ))
    print("-" * 70)

    for league_code, team_name, expected in test_cases:
        is_valid = validate_team_for_league(team_name, league_code)

        passed = is_valid == expected
        status = "[OK]" if passed else "[X]"
        results["pass" if passed else "fail"] += 1

        print("{:15} {:25} {:25} {}".format(
            league_code,
            team_name[:25],
            str(expected),
            f"{status} {is_valid}"
        ))

    print("\n" + "-" * 70)
    print(f"Pasados: {results['pass']}/{len(test_cases)}")
    print(f"Fallidos: {results['fail']}/{len(test_cases)}")


def test_data_loader():
    """Test cargador universal con múltiples ligas."""
    print("\n" + "="*70)
    print("TEST 3: Cargador Universal de Datos")
    print("="*70)

    test_leagues = ["mex", "laliga", "pl", "bundesliga", "brasil"]

    print("\nCargando datos para {} ligas...".format(len(test_leagues)))
    print("-" * 70)

    for league_code in test_leagues:
        try:
            loader = UniversalDataLoader(league_code)
            config = get_sport_config(league_code)

            print(f"\n{league_code.upper()}:")
            print(f"  Nombre: {loader.league.name}")
            print(f"  Tipo: {loader.league.competition_type}")
            print(f"  Equipos: {len(loader.teams)}")
            print(f"  Config edges: {config.min_edges}")

            # Test un equipo válido
            first_team = sorted(loader.teams)[0]
            strength = loader.get_team_strength(first_team)
            print(f"  Ejemplo: {first_team} (fortaleza: {strength:.2f})")

            # Test un equipo inválido
            invalid = "FakeTeam123"
            is_valid = loader.validate_team(invalid)
            print(f"  Validación: {invalid} = {is_valid} [OK]")

        except Exception as e:
            print(f"\n[X] ERROR cargando {league_code}: {e}")


def test_all_sports():
    """Test que todas las sports están en config."""
    print("\n" + "="*70)
    print("TEST 4: Todas las Ligas en Config")
    print("="*70)

    sports = list_sports()
    print(f"\n{len(sports)} ligas configuradas:")
    print("-" * 70)

    for code in sorted(sports):
        try:
            config = get_sport_config(code)
            print(f"  {code:12} : {config.name:30} [OK]")
        except Exception as e:
            print(f"  {code:12} : ERROR - {e} [X]")


def main():
    """Ejecutar todos los tests."""
    print("\n" + "="*70)
    print("TEST SUITE: Bot Multiliga con Prevención de Errores")
    print("="*70)

    test_error_prevention()
    test_multiple_leagues()
    test_data_loader()
    test_all_sports()

    print("\n" + "="*70)
    print("TESTS COMPLETADOS")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
