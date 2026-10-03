import logging
from typing import List

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import MarketPrice, WeatherRecord
from app.ingestion.agmarknet_client import AgmarknetClient
from app.ingestion.weather_client import IMDWeatherClient

logger = logging.getLogger(__name__)


class DataIngestionService:
    """The 'Data Ingestion' stage in the diagram. Coordinates every
    registered external client and persists normalized raw records into
    the data layer. Nothing here does cleaning or feature engineering —
    that's DataProcessingPipeline's job."""

    def __init__(self):
        settings = get_settings()
        self.agmarknet = AgmarknetClient(settings.agmarknet_base_url, settings.agmarknet_api_key)
        self.weather = IMDWeatherClient(settings.imd_weather_base_url, settings.imd_weather_api_key)

    async def ingest_market_prices(self, db: Session, **params) -> int:
        records = await self.agmarknet.fetch(**params)
        for r in records:
            db.add(MarketPrice(**r))
        db.commit()
        logger.info("Ingested %d market price records (%s)", len(records), params)
        return len(records)

    async def ingest_weather(self, db: Session, **params) -> int:
        records = await self.weather.fetch(**params)
        for r in records:
            db.add(WeatherRecord(**r))
        db.commit()
        logger.info("Ingested %d weather records (%s)", len(records), params)
        return len(records)

    async def run_full_ingestion(self, db: Session, commodities: List[str], states: List[str]):
        """Fan out across every state x commodity pair, then refresh weather
        once per run (district-wise rainfall covers the whole country in a
        single call, so it doesn't need to be repeated per state/commodity).
        Called by the scheduler and by the manual /ingestion trigger endpoint."""
        for state in states:
            for commodity in commodities:
                await self.ingest_market_prices(db, state=state, commodity=commodity)
        await self.ingest_weather(db)
