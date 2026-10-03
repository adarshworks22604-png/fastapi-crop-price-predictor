import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import FairPriceRecommendation
from app.db.session import get_db
from app.ml.model_registry import model_registry
from app.processing.pipeline import DataProcessingPipeline
from app.recommendation.fair_price_engine import FairPriceRecommender
from app.schemas.schemas import FairPriceRequest, FairPriceResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
pipeline = DataProcessingPipeline()


def _load_msp() -> dict:
    path = Path("app/data/msp_rates.json")
    if path.exists():
        return json.loads(path.read_text())
    return {}


recommender = FairPriceRecommender(msp_lookup=_load_msp())


@router.post("/", response_model=FairPriceResponse)
def recommend_price(req: FairPriceRequest, db: Session = Depends(get_db)):
    df = pipeline.run(db, commodity=req.commodity)
    latest_row = df[df["market"] == req.market].tail(1)

    model = model_registry.get(req.commodity)
    predicted_price = float(model.predict(latest_row)[0]) if not latest_row.empty else 0.0

    result = recommender.recommend(
        commodity=req.commodity,
        predicted_price=predicted_price,
        grade=req.grade,
        distance_km=req.distance_km,
    )

    db.add(
        FairPriceRecommendation(
            commodity=req.commodity,
            market=req.market,
            predicted_price=result.predicted_market_price,
            msp_floor=result.msp_floor,
            quality_adjustment=result.quality_adjustment,
            logistics_cost=result.logistics_cost,
            recommended_farmer_price=result.recommended_farmer_price,
            recommended_consumer_price=result.recommended_consumer_price,
            margin_band=result.margin_band,
        )
    )
    db.commit()

    return FairPriceResponse(
        commodity=req.commodity,
        market=req.market,
        predicted_market_price=result.predicted_market_price,
        msp_floor=result.msp_floor,
        quality_adjustment=result.quality_adjustment,
        logistics_cost=result.logistics_cost,
        recommended_farmer_price=result.recommended_farmer_price,
        recommended_consumer_price=result.recommended_consumer_price,
        margin_band=result.margin_band,
    )
