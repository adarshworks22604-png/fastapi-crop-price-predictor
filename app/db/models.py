from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class MarketPrice(Base):
    """Raw + cleaned mandi price records, sourced from Agmarknet/eNAM."""

    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, default="agmarknet")
    state = Column(String, index=True)
    district = Column(String, index=True)
    market = Column(String, index=True)
    commodity = Column(String, index=True)
    variety = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    arrival_date = Column(String)
    min_price = Column(Float)
    max_price = Column(Float)
    modal_price = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())


class WeatherRecord(Base):
    """Raw weather/forecast records, sourced from IMD Weather API."""

    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, default="imd_weather")
    district = Column(String, index=True)
    date = Column(String)
    rainfall_mm = Column(Float, nullable=True)
    max_temp_c = Column(Float, nullable=True)
    min_temp_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    ingested_at = Column(DateTime, server_default=func.now())


class PricePrediction(Base):
    """Every ML prediction the engine has ever produced, for audit/replay."""

    __tablename__ = "price_predictions"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String, index=True)
    market = Column(String, index=True)
    predicted_date = Column(String)
    predicted_price = Column(Float)
    model_version = Column(String)
    features_used = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class FairPriceRecommendation(Base):
    """Every fair-price recommendation served to farmers/consumers."""

    __tablename__ = "fair_price_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String, index=True)
    market = Column(String, index=True)
    predicted_price = Column(Float)
    msp_floor = Column(Float, nullable=True)
    quality_adjustment = Column(Float)
    logistics_cost = Column(Float)
    recommended_farmer_price = Column(Float)
    recommended_consumer_price = Column(Float)
    margin_band = Column(String)
    created_at = Column(DateTime, server_default=func.now())
