from typing import Dict

from app.ml.price_predictor import PricePredictor as PricePredictionModel


class ModelRegistry:
    """Caches one loaded PricePredictionModel per commodity in memory,
    so a prediction request doesn't hit disk every time."""

    def __init__(self, registry_path: str = "app/ml/artifacts"):
        self.registry_path = registry_path
        self._models: Dict[str, PricePredictionModel] = {}

    def get(self, commodity: str) -> PricePredictionModel:
        if commodity not in self._models:
            model = PricePredictionModel(commodity, self.registry_path)
            model.load()
            self._models[commodity] = model
        return self._models[commodity]

    def refresh(self, commodity: str):
        """Call after retraining so the next request picks up the new weights."""
        self._models.pop(commodity, None)


model_registry = ModelRegistry()
