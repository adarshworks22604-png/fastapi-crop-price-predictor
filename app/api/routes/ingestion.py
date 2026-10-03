from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingestion.ingestion_service import DataIngestionService
from app.schemas.schemas import IngestionTriggerRequest

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
service = DataIngestionService()


@router.post("/trigger")
async def trigger_ingestion(
    req: IngestionTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    background_tasks.add_task(service.run_full_ingestion, db, req.commodities, req.states)
    return {"status": "ingestion started", "states": req.states, "commodities": req.commodities}
