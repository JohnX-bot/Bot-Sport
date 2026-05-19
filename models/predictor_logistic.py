#!/usr/bin/env python3
"""
Logistic Regression Match Predictor

ML-based predictor using scikit-learn Logistic Regression.
Trained on historical match data, returns calibrated probabilities.
"""

import json
import os
import pickle
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.feature_engineer import AdvancedFeatureEngineer


class LogisticMatchPredictor:
    """ML predictor using Logistic Regression."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize predictor.

        Args:
            model_path: Path to pre-trained model file. If None, uses default or random.
        """
        self.engineer = AdvancedFeatureEngineer()
        self.scaler = StandardScaler()
        self.model = None
        self.model_path = model_path or "models/logistic_model.pkl"
        self.scaler_path = model_path and model_path.replace(".pkl", "_scaler.pkl")
        self.is_trained = False

        # Try to load existing model
        if os.path.exists(self.model_path):
            self._load_model()

    def _load_model(self):
        """Load trained model from disk."""
        try:
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
            if self.scaler_path and os.path.exists(self.scaler_path):
                with open(self.scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
            self.is_trained = True
            print(f"[LOGISTIC] Loaded model from {self.model_path}")
        except Exception as e:
            print(f"[LOGISTIC] Could not load model: {e}")
            self._create_dummy_model()

    def _create_dummy_model(self):
        """Create untrained model for testing."""
        n_features = self.engineer.get_feature_count()
        self.model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )
        # Initialize with dummy data for shape
        dummy_X = np.random.randn(10, n_features)
        dummy_y = np.array([0, 1, 2] * 3 + [0, 1])  # 3-way classification
        self.scaler.fit(dummy_X)
        self.model.fit(self.scaler.transform(dummy_X), dummy_y)
        self.is_trained = False
        print(f"[LOGISTIC] Created untrained dummy model ({n_features} features)")

    def train(
        self,
        matches: List[Dict],
        save_model: bool = True,
    ) -> Dict:
        """
        Train model on historical match data.

        Args:
            matches: List of {home_stats, away_stats, h2h, result: "home"|"draw"|"away"}
            save_model: Whether to save trained model to disk

        Returns:
            Training metrics {accuracy, train_score, ...}
        """
        print(f"\n[LOGISTIC] Training on {len(matches)} matches...")

        # Extract features
        X_list = []
        y_list = []

        for match in matches:
            features = self.engineer.extract_features(match)
            feature_vector = [features[name] for name in self.engineer.feature_names]
            X_list.append(feature_vector)

            # Encode result: 0=home, 1=draw, 2=away
            result = match.get("result", "home")
            if result == "home":
                y_list.append(0)
            elif result == "draw":
                y_list.append(1)
            else:  # away
                y_list.append(2)

        X = np.array(X_list)
        y = np.array(y_list)

        # Fit scaler and transform
        X_scaled = self.scaler.fit_transform(X)

        # Train Logistic Regression
        self.model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver="lbfgs",
            random_state=42,
        )
        self.model.fit(X_scaled, y)
        self.is_trained = True

        # Evaluate
        train_score = self.model.score(X_scaled, y)
        print(f"[LOGISTIC] Training accuracy: {train_score:.1%}")

        # Save model
        if save_model:
            self._save_model()

        return {
            "accuracy": train_score,
            "n_matches": len(matches),
            "n_features": X.shape[1],
        }

    def _save_model(self):
        """Save trained model to disk."""
        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)
        with open(self.scaler_path or "models/logistic_scaler.pkl", "wb") as f:
            pickle.dump(self.scaler, f)
        print(f"[LOGISTIC] Saved model to {self.model_path}")

    def predict_match(
        self,
        match_data: Dict,
        verbose: bool = False,
    ) -> Tuple[float, float, float]:
        """
        Predict match probabilities.

        Args:
            match_data: {home_stats, away_stats, h2h, ...}
            verbose: Print debug info

        Returns:
            (p_home, p_draw, p_away) - calibrated probabilities summing to 1.0
        """
        if not self.is_trained:
            if verbose:
                print("[LOGISTIC] Model not trained, returning default probabilities")
            return (0.33, 0.33, 0.33)

        # Extract features
        features = self.engineer.extract_features(match_data)
        feature_vector = np.array([features[name] for name in self.engineer.feature_names])

        # Scale features
        feature_scaled = self.scaler.transform([feature_vector])[0]

        # Predict probabilities (Logistic Regression returns calibrated probs)
        probs = self.model.predict_proba([feature_scaled])[0]  # [p_home, p_draw, p_away]

        p_home = float(probs[0])
        p_draw = float(probs[1])
        p_away = float(probs[2])

        # Ensure valid probabilities
        total = p_home + p_draw + p_away
        if total > 0:
            p_home /= total
            p_draw /= total
            p_away /= total

        if verbose:
            print(f"[LOGISTIC] {match_data.get('home_team')} vs {match_data.get('away_team')}")
            print(f"  Home: {p_home:.3f}, Draw: {p_draw:.3f}, Away: {p_away:.3f}")

        return (p_home, p_draw, p_away)

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Get feature importances from model coefficients.
        Higher absolute coefficient = more important.
        """
        if not self.is_trained or self.model is None:
            return {}

        # Get coefficients (shape: [n_classes, n_features])
        # Average absolute coefficient across classes
        importances = {}
        coefs = np.abs(self.model.coef_)  # Shape: [3, n_features]
        avg_coefs = np.mean(coefs, axis=0)

        for i, name in enumerate(self.engineer.feature_names):
            importances[name] = float(avg_coefs[i])

        # Sort by importance
        return dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))


def main():
    """Test Logistic Regression predictor."""
    print("[TEST] Logistic Regression Predictor\n")

    # Create predictor
    predictor = LogisticMatchPredictor()

    # Generate mock training data
    print("[TEST] Generating mock training data...")
    training_matches = []
    np.random.seed(42)
    for i in range(50):
        match = {
            "home_team": f"Team_{i % 5}",
            "away_team": f"Team_{(i + 1) % 5}",
            "home_stats": {
                "form_5": 0.50 + np.random.randn() * 0.1,
                "form_10": 0.50 + np.random.randn() * 0.1,
                "gd": np.random.randn() * 0.1,
                "gd_home": np.random.randn() * 0.1,
                "strength": np.random.randn() * 0.05,
                "attack_strength": np.random.randn() * 0.05,
                "defense_strength": np.random.randn() * 0.05,
                "days_rest": np.random.randint(2, 8),
                "matches_last_7days": np.random.randint(1, 4),
            },
            "away_stats": {
                "form_5": 0.50 + np.random.randn() * 0.1,
                "form_10": 0.50 + np.random.randn() * 0.1,
                "gd": np.random.randn() * 0.1,
                "gd_away": np.random.randn() * 0.1,
                "strength": np.random.randn() * 0.05,
                "attack_strength": np.random.randn() * 0.05,
                "defense_strength": np.random.randn() * 0.05,
                "days_rest": np.random.randint(2, 8),
                "matches_last_7days": np.random.randint(1, 4),
            },
            "h2h": {
                "home_wins": np.random.randint(0, 5),
                "draws": np.random.randint(0, 3),
                "away_wins": np.random.randint(0, 5),
            },
            "result": np.random.choice(["home", "draw", "away"]),
        }
        training_matches.append(match)

    # Train
    print("[TEST] Training model...")
    metrics = predictor.train(training_matches, save_model=False)
    print(f"  Accuracy: {metrics['accuracy']:.1%}")

    # Predict on test match
    print("\n[TEST] Making predictions...")
    test_match = {
        "home_team": "Arsenal",
        "away_team": "Liverpool",
        "home_stats": {
            "form_5": 0.65,
            "form_10": 0.60,
            "gd": 0.12,
            "gd_home": 0.18,
            "strength": 0.08,
            "attack_strength": 0.10,
            "defense_strength": -0.02,
            "days_rest": 5,
            "matches_last_7days": 2,
        },
        "away_stats": {
            "form_5": 0.55,
            "form_10": 0.58,
            "gd": -0.08,
            "gd_away": -0.12,
            "strength": -0.03,
            "attack_strength": 0.06,
            "defense_strength": -0.06,
            "days_rest": 3,
            "matches_last_7days": 3,
        },
        "h2h": {
            "home_wins": 3,
            "draws": 2,
            "away_wins": 2,
        },
    }

    p_home, p_draw, p_away = predictor.predict_match(test_match, verbose=True)
    print(f"\n  Final probabilities: Home {p_home:.1%}, Draw {p_draw:.1%}, Away {p_away:.1%}")

    # Feature importances
    print("\n[TEST] Top 10 important features:")
    importances = predictor.get_feature_importances()
    for i, (name, importance) in enumerate(list(importances.items())[:10]):
        print(f"  {i+1:2d}. {name:35} : {importance:.4f}")


if __name__ == "__main__":
    main()
