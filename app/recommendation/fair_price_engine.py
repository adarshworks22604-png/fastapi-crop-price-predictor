from dataclasses import dataclass
from typing import Optional


@dataclass
class FairPriceResult:
    predicted_market_price: float
    msp_floor: Optional[float]
    quality_adjustment: float
    logistics_cost: float
    recommended_farmer_price: float
    recommended_consumer_price: float
    margin_band: str


class FairPriceRecommender:
    """The 'Fair Price Recommendation' box. Takes a raw ML price
    prediction and turns it into two numbers that matter to real people:
    what the farmer should be paid, and what the consumer should pay —
    with MSP as a floor, a quality-grade adjustment, real logistics cost,
    and a capped platform margin so no intermediary can quietly take an
    outsized cut (the whole point of the project)."""

    QUALITY_MULTIPLIERS = {"A": 1.08, "FAQ": 1.0, "B": 0.93, "C": 0.85}

    def __init__(
        self,
        msp_lookup: Optional[dict] = None,
        base_logistics_cost_per_kg: float = 1.5,
        max_platform_margin_pct: float = 0.12,
    ):
        self.msp_lookup = msp_lookup or {}
        self.base_logistics_cost_per_kg = base_logistics_cost_per_kg
        self.max_platform_margin_pct = max_platform_margin_pct

    def recommend(
        self,
        commodity: str,
        predicted_price: float,
        grade: str = "FAQ",
        distance_km: float = 50,
    ) -> FairPriceResult:
        msp_floor = self.msp_lookup.get(commodity)

        quality_mult = self.QUALITY_MULTIPLIERS.get(grade, 1.0)
        quality_adjusted_price = predicted_price * quality_mult

        # Farmer is never paid below MSP when one exists for this crop.
        farmer_price = max(quality_adjusted_price, msp_floor) if msp_floor else quality_adjusted_price

        logistics_cost = self.base_logistics_cost_per_kg * (1 + distance_km / 200)

        margin = self.max_platform_margin_pct * farmer_price
        consumer_price = farmer_price + logistics_cost + margin

        margin_ratio = margin / farmer_price if farmer_price else 0
        margin_band = self._margin_band(margin_ratio)

        return FairPriceResult(
            predicted_market_price=round(predicted_price, 2),
            msp_floor=msp_floor,
            quality_adjustment=round(quality_adjusted_price - predicted_price, 2),
            logistics_cost=round(logistics_cost, 2),
            recommended_farmer_price=round(farmer_price, 2),
            recommended_consumer_price=round(consumer_price, 2),
            margin_band=margin_band,
        )

    @staticmethod
    def _margin_band(margin_ratio: float) -> str:
        if margin_ratio <= 0.05:
            return "low"
        if margin_ratio <= 0.10:
            return "moderate"
        return "high"
