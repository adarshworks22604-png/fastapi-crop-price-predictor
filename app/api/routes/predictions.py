from fastapi import APIRouter, Depends, HTTPException
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.ml.price_predictor import PricePredictor, get_predictor
from app.db.session import get_db  # adjust to your actual db module

router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post("/price", response_model=PredictionResponse)
async def predict_price(
    req: PredictionRequest,
    predictor: PricePredictor = Depends(get_predictor),
    db=Depends(get_db),
):
    history_df = await db.fetch_price_history(
        state=req.state, commodity=req.commodity, market=req.market
    )
    if history_df is None:
        raise HTTPException(404, "No historical data for this state/commodity")

    price = predictor.predict(req.model_dump(), history_df)

    return PredictionResponse(
        state=req.state,
        commodity=req.commodity,
        market=req.market,
        target_date=req.target_date,
        predicted_price=round(price, 2),
        model_version=predictor.version,
    )