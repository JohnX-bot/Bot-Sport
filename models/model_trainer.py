#!/usr/bin/env python3
"""
Model Trainer

Entrena automáticamente el modelo Logistic Regression con datos históricos.
"""

import json
import os
import sys
from typing import List, Dict, Optional, Tuple

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_downloader import FootballDataDownloader
from models.predictor_logistic import LogisticMatchPredictor
from models.feature_engineer import AdvancedFeatureEngineer


class ModelTrainer:
    """Entrena modelos predictivos con datos históricos."""

    def __init__(self):
        """Inicializar trainer."""
        self.downloader = FootballDataDownloader()
        self.engineer = AdvancedFeatureEngineer()

    def download_and_parse_season(
        self,
        sport: str,
        season: str,
    ) -> List[Dict]:
        """
        Descargar y parsear datos de una temporada.

        Args:
            sport: Código de deporte (pl, laliga, etc.)
            season: Año de temporada (ej: "2023-24")

        Returns:
            Lista de partidos enriquecidos
        """
        print(f"\n[DOWNLOAD] Descargando {sport.upper()} {season}...")

        # Descargar
        csv_path = self.downloader.download_season(sport, season)
        if not csv_path:
            return []

        # Parsear
        matches = self.downloader.parse_csv(csv_path)
        if not matches:
            return []

        # Enriquecer
        matches = self.downloader.enrich_matches(matches)

        print(f"[SUCCESS] Cargados {len(matches)} partidos")
        return matches

    def train_model(
        self,
        sport: str,
        season: str,
        save_model: bool = True,
    ) -> Tuple[Optional[LogisticMatchPredictor], Dict]:
        """
        Entrenar modelo para un deporte y temporada.

        Args:
            sport: Código de deporte
            season: Año de temporada
            save_model: Guardar modelo entrenado

        Returns:
            (modelo_entrenado, métricas)
        """
        print(f"\n{'='*70}")
        print(f"ENTRENANDO MODELO: {sport.upper()} {season}")
        print(f"{'='*70}")

        # Descargar datos
        matches = self.download_and_parse_season(sport, season)
        if not matches:
            print("[ERROR] No hay datos para entrenar")
            return None, {}

        # Crear predictor
        predictor = LogisticMatchPredictor(
            model_path=f"models/logistic_{sport}_{season}.pkl"
        )

        # Entrenar
        print(f"\n[TRAIN] Entrenando modelo Logistic Regression...")
        metrics = predictor.train(matches, save_model=save_model)

        # Feature importances
        print(f"\n[FEATURES] Top 10 features importantes:")
        importances = predictor.get_feature_importances()
        for i, (name, imp) in enumerate(list(importances.items())[:10]):
            print(f"  {i+1:2d}. {name:35} : {imp:.4f}")

        # Resumen
        print(f"\n[SUMMARY]")
        print(f"  Partidos de entrenamiento: {metrics.get('n_matches', 0)}")
        print(f"  Features: {metrics.get('n_features', 0)}")
        print(f"  Accuracy en entrenamiento: {metrics.get('accuracy', 0):.1%}")
        print(f"  Modelo guardado: {predictor.model_path}")

        return predictor, metrics

    def train_multiple_seasons(
        self,
        sport: str,
        seasons: List[str],
    ) -> Dict[str, Tuple[LogisticMatchPredictor, Dict]]:
        """
        Entrenar modelos para múltiples temporadas.

        Args:
            sport: Código de deporte
            seasons: Lista de temporadas (ej: ["2022-23", "2023-24"])

        Returns:
            Diccionario {season: (modelo, métricas)}
        """
        results = {}

        for season in seasons:
            predictor, metrics = self.train_model(sport, season, save_model=True)
            if predictor:
                results[season] = (predictor, metrics)

        return results

    def test_model_predictions(
        self,
        predictor: LogisticMatchPredictor,
        matches: List[Dict],
        sample_size: int = 5,
    ) -> None:
        """
        Probar predicciones del modelo en muestra de datos.

        Args:
            predictor: Modelo entrenado
            matches: Datos de prueba
            sample_size: Número de muestras a mostrar
        """
        if not matches:
            return

        print(f"\n[TEST] Predicciones en muestra de {sample_size} partidos:")
        print("-" * 90)

        for i, match in enumerate(matches[-sample_size:]):
            p_home, p_draw, p_away = predictor.predict_match(match)
            actual = match.get("result", "?")

            # Predicción (máxima probabilidad)
            pred_map = {"home": p_home, "draw": p_draw, "away": p_away}
            predicted = max(pred_map, key=pred_map.get)
            correct = "[OK]" if predicted == actual else "[XX]"

            print(
                f"{correct} {match['date']} | "
                f"{match['home_team']:20} vs {match['away_team']:20} | "
                f"P(H)={p_home:.2f} P(D)={p_draw:.2f} P(A)={p_away:.2f} | "
                f"Pred={predicted:6} Real={actual:6}"
            )


def main():
    """Entrenar modelo."""
    trainer = ModelTrainer()

    print("\n" + "="*70)
    print("MODEL TRAINER - ENTRENAMIENTO AUTOMÁTICO")
    print("="*70)

    # Entrenar PL 2023-24
    predictor, metrics = trainer.train_model("pl", "2023-24", save_model=True)

    if not predictor:
        print("[ERROR] No se pudo entrenar")
        return 1

    # Probar en muestra
    matches = trainer.download_and_parse_season("pl", "2023-24")
    if matches:
        trainer.test_model_predictions(predictor, matches, sample_size=5)

    print(f"\n{'='*70}")
    print("ENTRENAMIENTO COMPLETADO ✓")
    print(f"{'='*70}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
