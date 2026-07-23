from fastapi import APIRouter
from src.schemas.events import TrackingEvent
from src.services.broker import broker

router = APIRouter(prefix="/tracker", tags=["Tracker API"])


@router.post("/events", status_code=202)
async def track_event(event: TrackingEvent):
    await broker.publish(event)
    return {"status": "accepted"}
