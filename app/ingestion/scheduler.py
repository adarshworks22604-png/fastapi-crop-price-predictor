from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.ingestion_service import DataIngestionService

DEFAULT_COMMODITIES = ["Onion", "Tomato", "Wheat", "Rice"]
DEFAULT_STATES = ["Uttar Pradesh", "Maharashtra", "Punjab"]


def start_scheduler() -> AsyncIOScheduler:
    """Runs DataIngestionService on a fixed interval so the pipeline stays
    fresh without anyone hitting the manual trigger endpoint."""
    settings = get_settings()
    scheduler = AsyncIOScheduler()
    service = DataIngestionService()

    async def job():
        db = SessionLocal()
        try:
            await service.run_full_ingestion(db, commodities=DEFAULT_COMMODITIES, states=DEFAULT_STATES)
        finally:
            db.close()

    scheduler.add_job(job, "interval", minutes=settings.ingestion_interval_minutes)
    scheduler.start()
    return scheduler
