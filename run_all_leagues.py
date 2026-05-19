#!/usr/bin/env python3
"""
Ejecuta el bot para todas las ligas simultáneamente en modo paper.
Cada liga corre en su propio proceso con su propio bankroll.
"""

import subprocess
import sys
import time
import signal
import json
import os
from pathlib import Path
from typing import List, Dict

# Ligas a ejecutar
LEAGUES = {
    "mex": {"bankroll": 100, "name": "Liga Mexicana"},
    "laliga": {"bankroll": 100, "name": "La Liga"},
    "pl": {"bankroll": 100, "name": "Premier League"},
    "bundesliga": {"bankroll": 100, "name": "Bundesliga"},
    "ligue1": {"bankroll": 100, "name": "Ligue 1"},
    "brasil": {"bankroll": 100, "name": "Brasileirão"},
    "seriea": {"bankroll": 100, "name": "Serie A"},
    "mls": {"bankroll": 100, "name": "MLS"},
    "superlig": {"bankroll": 100, "name": "Süper Lig"},
    "libertadores": {"bankroll": 100, "name": "Copa Libertadores"},
    "ucl": {"bankroll": 100, "name": "Champions League"},
    "nfl": {"bankroll": 75, "name": "NFL"},  # NFL más conservador
}

class MultiLeagueBot:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.root_dir = Path(__file__).parent

    def start_league(self, league_code: str, config: dict) -> bool:
        """Inicia el bot para una liga específica."""
        try:
            bankroll = config["bankroll"]
            name = config["name"]

            # Comando para ejecutar el bot
            cmd = [
                sys.executable,
                str(self.root_dir / "bot" / "unified_bot.py"),
                "--mode", "paper",
                "--sport", league_code,
                "--bankroll", str(bankroll),
            ]

            print(f"[INICIANDO] {name:30} ({league_code}) - Bankroll: ${bankroll}")

            # Lanzar en background con output a archivo de log
            log_file = self.root_dir / "logs" / f"bot_{league_code}.log"
            log_file.parent.mkdir(exist_ok=True)

            with open(log_file, "w") as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.root_dir),
                )

            self.processes[league_code] = process
            print(f"[OK] {name:30} PID: {process.pid}")
            return True

        except Exception as e:
            print(f"[ERROR] {config['name']:30} - {e}")
            return False

    def start_all(self):
        """Inicia todas las ligas."""
        print("\n" + "="*80)
        print("INICIANDO BOT MULTI-LIGA (Modo Paper)")
        print("="*80 + "\n")

        started = 0
        failed = 0

        for league_code, config in LEAGUES.items():
            if self.start_league(league_code, config):
                started += 1
                time.sleep(0.5)  # Pequeño delay entre inicios
            else:
                failed += 1

        print("\n" + "="*80)
        print(f"RESUMEN: {started} ligas iniciadas, {failed} fallidas")
        print("="*80 + "\n")

        return started, failed

    def monitor(self):
        """Monitorea el estado de todos los procesos."""
        print("[MONITOR] Chequeando estado de procesos...")
        print("-" * 80)

        for league_code, process in list(self.processes.items()):
            status = "EN EJECUCIÓN" if process.poll() is None else "DETENIDO"
            name = LEAGUES[league_code]["name"]
            print(f"  {league_code:12} | {name:30} | PID: {process.pid:6} | {status}")

        print("-" * 80)
        alive = sum(1 for p in self.processes.values() if p.poll() is None)
        print(f"\nProcesos activos: {alive}/{len(self.processes)}\n")

    def show_logs(self, league_code: str = None):
        """Muestra los últimos logs de una liga o todas."""
        if league_code:
            log_file = self.root_dir / "logs" / f"bot_{league_code}.log"
            if log_file.exists():
                print(f"\n[LOGS] {LEAGUES[league_code]['name']}")
                print("-" * 80)
                # Mostrar últimas 20 líneas
                with open(log_file) as f:
                    lines = f.readlines()
                    for line in lines[-20:]:
                        print(line.rstrip())
        else:
            print(f"\n[LOGS DISPONIBLES]")
            logs_dir = self.root_dir / "logs"
            if logs_dir.exists():
                for log_file in sorted(logs_dir.glob("bot_*.log")):
                    league = log_file.stem.replace("bot_", "")
                    size = log_file.stat().st_size
                    print(f"  {league:12} : {size:10} bytes")

    def show_live_trades(self):
        """Muestra todos los trades abiertos con contador de tiempo."""
        from datetime import datetime
        import sys
        sys.path.insert(0, str(self.root_dir))

        try:
            from data.live_matches_api import get_all_live_matches
            # Pre-cargar TODOS los partidos en vivo de una sola vez (evita múltiples llamadas)
            all_live_matches = get_all_live_matches()   # dict: {league_code: [matches]}
            use_live_api = True
        except Exception:
            all_live_matches = {}
            use_live_api = False

        # Obtener hora y fecha actual
        now = datetime.now()
        fecha_hora = now.strftime("%d/%m/%Y - %H:%M:%S")

        print("\n" + "=" * 80)
        print("TRADES EN VIVO (Contador de Tiempo)")
        print("=" * 80)
        print(f"Fecha y Hora: {fecha_hora}")
        print("=" * 80)

        logs_dir = self.root_dir / "logs"
        if not logs_dir.exists():
            print("[INFO] Sin archivos de posiciones aún")
            return

        # Leer todos los archivos de posiciones
        all_positions = []
        now_timestamp = int(time.time())

        for positions_file in sorted(logs_dir.glob("positions_*.json")):
            try:
                with open(positions_file) as f:
                    data = json.load(f)
                    sport_code = data.get("sport_code", "unknown")
                    positions = data.get("positions", [])

                    for pos in positions:
                        # Calcular tiempo restante
                        entry_time = pos.get("entry_time", now_timestamp)
                        time_elapsed = now_timestamp - entry_time
                        demo_close_time = 120  # 2 minutos de ventana de visualización
                        time_remaining = max(0, demo_close_time - time_elapsed)

                        # Solo mostrar trades abiertos (menos de 2 minutos)
                        if time_elapsed <= demo_close_time:
                            all_positions.append({
                                "sport_code": sport_code,
                                "home_team": pos.get("home_team", ""),
                                "away_team": pos.get("away_team", ""),
                                "direction": pos.get("direction", ""),
                                "bet_amount": pos.get("bet_amount", 0),
                                "odds": pos.get("odds", 0),
                                "time_remaining": time_remaining,
                                "time_elapsed": time_elapsed,
                            })
            except Exception as e:
                pass  # Ignorar archivos corruptos

        if not all_positions:
            print("[INFO] No hay trades abiertos en este momento")
            print("-" * 80)
            return

        # Mostrar en orden de sport_code
        current_sport = None
        for pos in sorted(all_positions, key=lambda x: x["sport_code"]):
            if pos["sport_code"] != current_sport:
                current_sport = pos["sport_code"]
                league_name = LEAGUES.get(current_sport, {}).get("name", current_sport)

                live_count = len(all_live_matches.get(current_sport, []))
                status_str = f" ({live_count} en vivo)" if live_count > 0 else " (Sin partidos en vivo)"
                print(f"\n[{current_sport.upper()}] {league_name}{status_str}")
                print("-" * 80)

            # Buscar partido en el dict pre-cargado (sin llamadas extra al API)
            match_info = None
            if use_live_api:
                league_live = all_live_matches.get(pos["sport_code"], [])
                home_lower = pos["home_team"].lower().strip()
                away_lower = pos["away_team"].lower().strip()
                for m in league_live:
                    api_home = m["home_team"].lower()
                    api_away = m["away_team"].lower()
                    if ((home_lower in api_home or api_home in home_lower) and
                            (away_lower in api_away or api_away in away_lower)):
                        match_info = m
                        break

            # Si no hay datos reales, usar datos simulados
            if not match_info:
                import random
                # Usar el nombre de los equipos como seed para consistencia
                seed_str = f"{pos['home_team']}{pos['away_team']}"
                random.seed(hash(seed_str) % 2**32)

                # En demo, mostrar un minuto aleatorio pero realista
                # Considerar que algunos partidos pueden estar en descanso o finalizados
                match_minute = random.randint(10, 88)

                if match_minute >= 42 and match_minute <= 48:
                    status = "DESCANSO"
                    display_minute = "45'"
                else:
                    status = "EN VIVO"
                    display_minute = f"{match_minute}'"

                # Simular marcador realista
                home_goals = random.randint(0, 2)
                away_goals = random.randint(0, 2)
                score = f"{home_goals}-{away_goals}"

                # Marca que estos datos son simulados
                data_source = "[SIM]"
            else:
                # Usar datos reales de la API
                hs = match_info.get("home_score")
                as_ = match_info.get("away_score")
                score = f"{hs}-{as_}" if (hs is not None and as_ is not None) else "?-?"
                mn = match_info.get("minute")
                display_minute = f"{mn}'" if mn is not None else "?"
                status = match_info.get("display_status", match_info.get("status", "EN VIVO"))
                data_source = "[API]"

            # Formato del tiempo restante
            mins = int(pos["time_remaining"] // 60)
            secs = int(pos["time_remaining"] % 60)
            time_str = f"{mins}m {secs}s"

            # Mostrar posición con información del partido
            direction_upper = pos["direction"].upper()
            print(f"  {pos['home_team']:20} vs {pos['away_team']:20}")
            print(f"    {data_source} Marcador: {score} | Minuto: {display_minute} | Estado: {status}")
            print(f"    Apuesta: {direction_upper:5} | ${pos['bet_amount']:6.2f} @ {pos['odds']:.3f} | Cierra en: {time_str}")

        print("-" * 80)
        print(f"Total: {len(all_positions)} trades abiertos")
        print("Nota: [API] = Datos reales desde football-data.org | [SIM] = Datos simulados")
        print("=" * 80)

    def stop_league(self, league_code: str = None):
        """Detiene una liga o todas."""
        if league_code:
            if league_code in self.processes:
                process = self.processes[league_code]
                process.terminate()
                print(f"[DETENIDO] {LEAGUES[league_code]['name']} (PID: {process.pid})")
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        else:
            print("[DETENIENDO] Todos los procesos...")
            for league_code, process in self.processes.items():
                process.terminate()
                print(f"  {league_code:12} : Enviado SIGTERM")

            # Esperar a que se cierren
            time.sleep(2)
            for league_code, process in list(self.processes.items()):
                if process.poll() is None:
                    process.kill()
                    print(f"  {league_code:12} : Enviado SIGKILL")

    def interactive_menu(self):
        """Menú interactivo."""
        while True:
            try:
                print("\n" + "="*80)
                print("MULTI-LIGA BOT - MENÚ")
                print("="*80)
                print("1. Ver estado de procesos")
                print("2. Ver logs (todas las ligas)")
                print("3. Ver logs de una liga específica")
                print("4. Ver trades en vivo (con contador)")
                print("5. Detener una liga")
                print("6. Detener todas las ligas")
                print("7. Reiniciar una liga")
                print("8. Salir")
                print("="*80)
                print("[INFO] Los trades en vivo se actualizan cada 60 segundos")

                choice = input("\nOpción: ").strip()
            except KeyboardInterrupt:
                print("\n[WARN] Presionaste Ctrl+C. Escribe tu opción.")
                continue

            try:
                if choice == "1":
                    self.monitor()

                elif choice == "2":
                    self.show_logs()

                elif choice == "3":
                    league = input(f"Liga ({', '.join(LEAGUES.keys())}): ").strip()
                    if league in LEAGUES:
                        self.show_logs(league)
                    else:
                        print("[ERROR] Liga inválida")

                elif choice == "4":
                    self.show_live_trades()

                elif choice == "5":
                    league = input(f"Liga ({', '.join(LEAGUES.keys())}): ").strip()
                    if league in LEAGUES:
                        self.stop_league(league)
                    else:
                        print("[ERROR] Liga inválida")

                elif choice == "6":
                    confirm = input("¿Detener todas las ligas? (s/n): ").strip().lower()
                    if confirm == "s":
                        self.stop_league()

                elif choice == "7":
                    league = input(f"Liga ({', '.join(LEAGUES.keys())}): ").strip()
                    if league in LEAGUES:
                        self.stop_league(league)
                        time.sleep(1)
                        self.start_league(league, LEAGUES[league])
                    else:
                        print("[ERROR] Liga inválida")

                elif choice == "8":
                    confirm = input("¿Salir? Esto detendrá todas las ligas (s/n): ").strip().lower()
                    if confirm == "s":
                        self.stop_league()
                        break

                elif choice.strip() == "":
                    pass  # Ignorar entrada vacía

                else:
                    print("[ERROR] Opción inválida. Por favor, elige 1-8")

            except KeyboardInterrupt:
                print("\n[WARN] Operación cancelada por el usuario")
            except Exception as e:
                print(f"[ERROR] {e}")

            time.sleep(0.5)


def main():
    bot = MultiLeagueBot()

    # Iniciar todas las ligas
    started, failed = bot.start_all()

    if started > 0:
        print("[INFO] Abre logs/bot_*.log para ver el progreso")
        print("[INFO] Presiona Ctrl+C para entrar al menú interactivo\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[MENÚ ACTIVADO]")
            bot.interactive_menu()

    # Limpiar
    bot.stop_league()
    print("\n[EXIT] Todos los procesos detenidos")


if __name__ == "__main__":
    main()
