from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.core.config import settings
from src.services.broker import broker
from src.api.v1 import track


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker.amqp_url = settings.RABBITMQ_URL
    await broker.connect()
    yield
    await broker.close()


app = FastAPI(
    title="A/B Platform - Tracker API",
    description="Сервис приёма аналитических событий",
    lifespan=lifespan,
)

app.include_router(track.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy"}

