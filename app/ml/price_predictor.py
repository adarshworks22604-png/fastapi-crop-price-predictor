import xgboost as xgb
import pandas as pd
from pathlib import Path
from functools import lru_cache

MODEL_PATH = Path(__file__).parent / "artifacts" / "price_model.json"


class PricePredictor:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model = xgb.XGBRegressor()
        self.model.load_model(str(model_path))
        self.version = model_path.stem

    def _build_features(self, row: dict, history_df: pd.DataFrame) -> pd.DataFrame:
        """
        row: {state, commodity, market, target_date}
        history_df: recent price history for that state+commodity+market,
                     pulled from your db (used for lag/rolling features).
        """
        target_date = pd.to_datetime(row["target_date"])
        feats = {
            "day_of_week": target_date.dayofweek,
            "day_of_month": target_date.day,
            "month": target_date.month,
            "state_enc": self._encode(row["state"], "state"),
            "commodity_enc": self._encode(row["commodity"], "commodity"),
        }
        if not history_df.empty:
            recent = history_df.sort_values("arrival_date").tail(30)
            feats["lag_1"] = recent["modal_price"].iloc[-1]
            feats["rolling_7_mean"] = recent["modal_price"].tail(7).mean()
            feats["rolling_30_mean"] = recent["modal_price"].mean()
            feats["rolling_7_std"] = recent["modal_price"].tail(7).std()
        else:
            feats.update({"lag_1": 0, "rolling_7_mean": 0,
                           "rolling_30_mean": 0, "rolling_7_std": 0})
        return pd.DataFrame([feats])

    def _encode(self, value: str, kind: str) -> int:
        # Replace with the same LabelEncoder/mapping used at training time
        # (load a saved encoder dict here rather than hashing ad hoc)
        return abs(hash(f"{kind}:{value}")) % 1000

    def predict(self, row: dict, history_df: pd.DataFrame) -> float:
        X = self._build_features(row, history_df)
        return float(self.model.predict(X)[0])


@lru_cache
def get_predictor() -> PricePredictor:
    return PricePredictor()