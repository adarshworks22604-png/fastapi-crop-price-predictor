from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import MarketPrice, WeatherRecord
from app.processing.cleaner import DataCleaner
from app.processing.feature_engineering import FeatureEngineer


class DataProcessingPipeline:
    """Wires together DataCleaner + FeatureEngineer so callers (training
    script, prediction endpoint) get a single method that goes from raw
    DB rows straight to an ML-ready DataFrame."""

    def __init__(self):
        self.cleaner = DataCleaner()
        self.engineer = FeatureEngineer()

    def run(self, db: Session, commodity: Optional[str] = None) -> pd.DataFrame:
        price_query = db.query(MarketPrice)
        if commodity:
            price_query = price_query.filter(MarketPrice.commodity == commodity)

        prices_df = pd.read_sql(price_query.statement, db.bind)
        weather_df = pd.read_sql(db.query(WeatherRecord).statement, db.bind)

        prices_clean = self.cleaner.clean_market_prices(prices_df)
        weather_clean = self.cleaner.clean_weather(weather_df) if not weather_df.empty else weather_df

        return self.engineer.build_features(prices_clean, weather_clean)
