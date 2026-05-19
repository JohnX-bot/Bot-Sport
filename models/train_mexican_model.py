#!/usr/bin/env python3
"""
Entrenador Específico para Liga Mexicana

Carga datos de Liga Mexicana, extrae features y entrena modelo Logistic.
"""

import json
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predictor_logistic import LogisticMatchPredictor
from models.feature_engineer import AdvancedFeatureEngineer


class MexicanModelTrainer:
    """Entrena modelo para Liga Mexicana."""

    def __init__(self):
        self.engineer = AdvancedFeatureEngineer()

    def load_mexican_data(self, filepath: str) -> List[Dict]:
        """Cargar datos de Liga Mexicana desde JSON."""
        with open(filepath, 'r') as f:
            matches = json.load(f)
        print(f"[OK] {len(matches)} partidos cargados desde {filepath}")
        return matches

    def train_mexican_model(self, filepath: str) -> tuple:
        """
        Entrenar modelo Logistic para Liga Mexicana.

        Returns:
            (predictor_entrenado, métricas)
        """
        print("\n" + "="*80)
        print("ENTRENANDO MODELO: LIGA MEXICANA 2025-26")
        print("="*80)

        # Cargar datos
        matches = self.load_mexican_data(filepath)

        # Crear predictor
        model_path = "models/logistic_mex_2025-26.pkl"
        predictor = LogisticMatchPredictor(model_path=model_path)

        # Entrenar
        print(f"\n[TRAIN] Entrenando Logistic Regression...")
        metrics = predictor.train(matches, save_model=True)

        # Features
        print(f"\n[FEATURES] Top 15 features importantes:")
        importances = predictor.get_feature_importances()
        for i, (name, imp) in enumerate(list(importances.items())[:15]):
            bar = "#" * int(imp * 50)
            print(f"  {i+1:2d}. {name:35} : {imp:.4f} {bar}")

        # Resumen
        print(f"\n[SUMMARY]")
        print(f"  Partidos de entrenamiento: {metrics.get('n_matches', 0)}")
        print(f"  Features: {metrics.get('n_features', 0)}")
        print(f"  Accuracy en entrenamiento: {metrics.get('accuracy', 0):.1%}")
        print(f"  Modelo guardado: {model_path}")

        return predictor, metrics

    def test_on_sample(self, predictor, matches: List[Dict]):
        """Probar predicciones en muestra."""
        print(f"\n[TEST] Predicciones en últimos 10 partidos:")
        print("-" * 110)
        print(f"{'Fecha':<12} {'Local':<18} {'Visitante':<18} {'P(H)':<7} {'P(D)':<7} {'P(A)':<7} {'Real':<8}")
        print("-" * 110)

        for match in matches[-10:]:
            try:
                p_h, p_d, p_a = predictor.predict_match(match)
                actual = match.get("result", "?")

                print(
                    f"{match['date']:<12} "
                    f"{match['home_team']:<18} "
                    f"{match['away_team']:<18} "
                    f"{p_h:<7.2f} "
                    f"{p_d:<7.2f} "
                    f"{p_a:<7.2f} "
                    f"{actual:<8}"
                )
            except Exception as e:
                print(f"[ERROR] No se pudo predecir para {match['date']}: {e}")


def main():
    """Entrenar modelo mexicano."""
    trainer = MexicanModelTrainer()

    # Entrenar
    predictor, metrics = trainer.train_mexican_model(
        "data/mexican_league_2025-26.json"
    )

    if not predictor:
        print("[ERROR] Fallo al entrenar")
        return 1

    # Cargar datos para test
    matches = trainer.load_mexican_data("data/mexican_league_2025-26.json")

    # Test
    trainer.test_on_sample(predictor, matches)

    print(f"\n{'='*80}")
    print("MODELO MEXICANO ENTRENADO EXITOSAMENTE")
    print(f"{'='*80}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
