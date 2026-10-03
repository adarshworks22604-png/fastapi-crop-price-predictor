from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    commodity: str
    market: str
    district: Optional[str] = None
    target_date: date


class PredictionResponse(BaseModel):
    commodity: str
    market: str
    predicted_date: date
    predicted_price: float
    model_version: str = "v1"


class FairPriceRequest(BaseModel):
    commodity: str
    market: str
    district: Optional[str] = None
    target_date: date
    grade: str = "FAQ"
    distance_km: float = 50


class FairPriceResponse(BaseModel):
    commodity: str
    market: str
    predicted_market_price: float
    msp_floor: Optional[float]
    quality_adjustment: float
    logistics_cost: float
    recommended_farmer_price: float
    recommended_consumer_price: float
    margin_band: str


class IngestionTriggerRequest(BaseModel):
    states: List[str]
    commodities: List[str]
