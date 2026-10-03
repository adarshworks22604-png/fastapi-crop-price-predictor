from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    state: str = Field(..., examples=["Uttar Pradesh"])
    commodity: str = Field(..., examples=["Potato"])
    market: Optional[str] = None
    target_date: date = Field(..., description="Date to predict price for")


class PredictionResponse(BaseModel):
    state: str
    commodity: str
    market: Optional[str]
    target_date: date
    predicted_price: float
    currency: str = "INR"
    unit: str = "quintal"
    model_version: str
    confidence_interval: Optional[tuple[float, float]] = None