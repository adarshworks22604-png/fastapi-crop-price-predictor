from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import MarketPrice
from app.db.session import get_db

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/")
def list_prices(
    commodity: Optional[str] = None,
    market: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(MarketPrice)
    if commodity:
        query = query.filter(MarketPrice.commodity == commodity)
    if market:
        query = query.filter(MarketPrice.market == market)
    return query.order_by(MarketPrice.ingested_at.desc()).limit(limit).all()
