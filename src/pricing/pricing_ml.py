"""
Machine Learning model for price prediction and optimization.

Uses historical contract award data to predict optimal pricing
for new RFPs based on features like NAICS code, agency, and
requirement complexity.
"""

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


@dataclass
class PricePrediction:
    """Result of a price prediction."""

    predicted_price: float
    confidence_interval: Tuple[float, float]  # (lower, upper)
    feature_importance: Dict[str, float]
    model_confidence: float
    similar_awards: List[Dict]


class PricingMLModel:
    """Machine learning model for price prediction and optimization."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: List[str] = []
        self.model_path = model_path or Path("models/pricing_model.pkl")
        self._is_trained = False

        # Try to load existing model
        if self.model_path.exists():
            self._load_model()

    def train(self, historical_data: pd.DataFrame) -> Dict[str, float]:
        """
        Train the pricing model on historical award data.

        Args:
            historical_data: DataFrame with columns including award_amount,
                           naics_code, agency, description, etc.

        Returns:
            Dictionary with training metrics (R² scores, sample counts)
        """
        # Prepare features
        features = self._prepare_features(historical_data)
        target = historical_data["award_amount"].values

        # Remove rows with missing or invalid target
        valid_mask = ~np.isnan(target) & (target > 0) & (target < 1e9)  # Cap at $1B
        features = features[valid_mask]
        target = target[valid_mask]

        if len(features) < 100:
            raise ValueError(f"Insufficient training data: {len(features)} samples")

        # Log transform target for better distribution
        target_log = np.log1p(target)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, target_log, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train Gradient Boosting model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=10,
            min_samples_leaf=5,
            subsample=0.8,
            random_state=42,
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)

        # Calculate prediction errors for confidence estimation
        y_pred = self.model.predict(X_test_scaled)
        mape = np.mean(np.abs(np.expm1(y_pred) - np.expm1(y_test)) / np.expm1(y_test))

        self._is_trained = True

        # Save model
        self._save_model()

        return {
            "train_r2": train_score,
            "test_r2": test_score,
            "mape": mape,
            "samples_trained": len(X_train),
            "samples_tested": len(X_test),
        }

    def predict(
        self,
        naics_code: str,
        agency: str,
        description_length: int,
        requirement_count: int,
        contract_type: str = "FFP",
        set_aside: Optional[str] = None,
    ) -> PricePrediction:
        """
        Predict optimal price for an RFP.

        Args:
            naics_code: NAICS code for the work
            agency: Government agency
            description_length: Length of RFP description
            requirement_count: Number of requirements
            contract_type: Type of contract (FFP, T&M, etc.)
            set_aside: Set-aside type if any

        Returns:
            PricePrediction with price estimate and confidence
        """
        if not self._is_trained:
            raise ValueError("Model not trained. Call train() first or load a trained model.")

        # Prepare input features
        features = self._encode_features(
            {
                "naics_code": naics_code,
                "agency": agency,
                "description_length": description_length,
                "requirement_count": requirement_count,
                "contract_type": contract_type,
                "set_aside": set_aside or "None",
            }
        )

        # Scale and predict
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        prediction_log = self.model.predict(features_scaled)[0]
        prediction = np.expm1(prediction_log)  # Reverse log transform

        # Calculate confidence interval using tree predictions variance
        tree_predictions_log = np.array(
            [tree[0].predict(features_scaled)[0] for tree in self.model.estimators_]
        )
        tree_predictions = np.expm1(tree_predictions_log)
        std = tree_predictions.std()

        ci_lower = max(0, prediction - 1.96 * std)
        ci_upper = prediction + 1.96 * std

        # Calculate model confidence based on prediction spread
        cv = std / prediction if prediction > 0 else 1.0
        model_confidence = max(0.0, min(1.0, 1.0 - cv))

        # Get feature importance
        importance = dict(zip(self.feature_names, self.model.feature_importances_))

        return PricePrediction(
            predicted_price=float(prediction),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            feature_importance=importance,
            model_confidence=float(model_confidence),
            similar_awards=[],  # Could be populated from historical data
        )

    def optimize_price(
        self,
        base_cost: float,
        min_margin: float = 0.10,
        max_margin: float = 0.35,
        target_win_prob: float = 0.7,
        market_median: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Find optimal price balancing margin and win probability.

        Args:
            base_cost: Base cost of the work
            min_margin: Minimum acceptable margin (e.g., 0.10 = 10%)
            max_margin: Maximum margin to consider
            target_win_prob: Target win probability (0-1)
            market_median: Market median price for similar work

        Returns:
            Dictionary with optimal price, margin, win probability
        """
        from src.pricing.win_probability import WinProbabilityModel

        win_model = WinProbabilityModel()

        # If no market median, estimate from base cost
        if market_median is None:
            market_median = base_cost * 1.25

        best_score = -1
        best_price = base_cost * (1 + min_margin)
        best_margin = min_margin
        best_win_prob = 0.5

        # Grid search over possible margins
        for margin in np.arange(min_margin, max_margin + 0.01, 0.01):
            price = base_cost * (1 + margin)
            win_prob = win_model.predict(price, market_median)

            # Score: weighted combination prioritizing target win prob
            if win_prob >= target_win_prob:
                # Above target: maximize margin while maintaining win prob
                score = margin * 0.6 + win_prob * 0.4
            else:
                # Below target: maximize win prob
                score = win_prob

            if score > best_score:
                best_score = score
                best_price = price
                best_margin = margin
                best_win_prob = win_prob

        return {
            "optimal_price": float(best_price),
            "margin": float(best_margin),
            "win_probability": float(best_win_prob),
            "expected_profit": float(best_price - base_cost),
            "optimization_score": float(best_score),
        }

    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix from historical data."""
        feature_columns = [
            "naics_code",
            "agency",
            "description_length",
            "requirement_count",
            "contract_type",
            "set_aside",
        ]

        # Create derived features
        data = data.copy()

        # Description length
        if "description" in data.columns:
            data["description_length"] = data["description"].fillna("").str.len()
        if "description_length" not in data.columns:
            data["description_length"] = 500

        # Requirement count (estimate if not available)
        if "requirement_count" not in data.columns:
            data["requirement_count"] = 10

        # Contract type
        if "contract_type" not in data.columns:
            data["contract_type"] = "FFP"

        # Set aside
        if "set_aside" not in data.columns:
            data["set_aside"] = "None"

        # Encode categorical features
        features = []
        for col in feature_columns:
            if col in ["naics_code", "agency", "contract_type", "set_aside"]:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    values = data[col].fillna("Unknown").astype(str)
                    # Add 'Unknown' to handle new values during prediction
                    unique_values = list(values.unique()) + ["Unknown"]
                    self.label_encoders[col].fit(unique_values)

                encoded = self.label_encoders[col].transform(
                    data[col].fillna("Unknown").astype(str)
                )
                features.append(encoded)
            else:
                features.append(data[col].fillna(0).values)

        self.feature_names = feature_columns
        return np.column_stack(features)

    def _encode_features(self, data: Dict) -> np.ndarray:
        """Encode a single data point for prediction."""
        features = []
        for col in self.feature_names:
            if col in self.label_encoders:
                try:
                    encoded = self.label_encoders[col].transform(
                        [str(data.get(col, "Unknown"))]
                    )[0]
                except ValueError:
                    # Unknown value - use "Unknown" encoding
                    encoded = self.label_encoders[col].transform(["Unknown"])[0]
                features.append(encoded)
            else:
                features.append(data.get(col, 0))
        return np.array(features)

    def _save_model(self):
        """Save model to disk."""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "scaler": self.scaler,
                    "label_encoders": self.label_encoders,
                    "feature_names": self.feature_names,
                },
                f,
            )

    def _load_model(self):
        """Load model from disk."""
        try:
            with open(self.model_path, "rb") as f:
                data = pickle.load(f)
                self.model = data["model"]
                self.scaler = data["scaler"]
                self.label_encoders = data["label_encoders"]
                self.feature_names = data["feature_names"]
                self._is_trained = True
        except Exception as e:
            print(f"Warning: Could not load model from {self.model_path}: {e}")
            self._is_trained = False


# Singleton instance
_pricing_ml_model: Optional[PricingMLModel] = None


def get_pricing_ml_model() -> PricingMLModel:
    """Get the singleton pricing ML model instance."""
    global _pricing_ml_model
    if _pricing_ml_model is None:
        _pricing_ml_model = PricingMLModel()
    return _pricing_ml_model
