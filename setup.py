#!/usr/bin/env python3
"""
Setup Automático del Bot

Descarga datos, entrena modelos y prepara el bot para usar.
Ejecutar una sola vez al principio.
"""

import os
import sys

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.model_trainer import ModelTrainer


def create_directories():
    """Crear directorios necesarios."""
    dirs = [
        "data/historical",
        "data/live",
        "models",
        "logs",
    ]

    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[OK] Directorio: {dir_path}")


def main():
    """Ejecutar setup."""
    print("\n" + "="*70)
    print("SETUP AUTOMÁTICO - BOT DE APUESTAS DEPORTIVAS")
    print("="*70)

    # 1. Crear directorios
    print("\n[1] Creando directorios...")
    create_directories()

    # 2. Descargar y entrenar modelos
    print("\n[2] Descargando datos y entrenando modelos...")
    print("    (Esta operación puede tomar 2-5 minutos la primera vez)")

    trainer = ModelTrainer()

    # Entrenar Premier League 2023-24
    print("\n    Premier League 2023-24:")
    predictor, metrics = trainer.train_model("pl", "2023-24", save_model=True)

    if not predictor:
        print("[ERROR] No se pudo entrenar el modelo PL")
        return 1

    # Probar predicciones
    print("\n[3] Probando predicciones...")
    matches = trainer.download_and_parse_season("pl", "2023-24")
    if matches:
        trainer.test_model_predictions(predictor, matches, sample_size=3)

    # Resumen
    print("\n" + "="*70)
    print("SETUP COMPLETADO [OK]")
    print("="*70)
    print("""
Próximos pasos:

1. BACKTEST (pruebas históricas):
   python bot/unified_bot.py --mode backtest --sport pl \\
     --predictor logistic --start-date 2023-08-01 --end-date 2024-05-31

2. PAPER MODE (simulación en tiempo real):
   python bot/unified_bot.py --mode paper --sport pl \\
     --predictor logistic --bankroll 100

3. COMPARAR modelos:
   # Heurístico
   python bot/unified_bot.py --mode backtest --sport pl \\
     --predictor heuristic --start-date 2023-08-01 --end-date 2024-05-31

   # Logístico
   python bot/unified_bot.py --mode backtest --sport pl \\
     --predictor logistic --start-date 2023-08-01 --end-date 2024-05-31

Más información en README.md
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
