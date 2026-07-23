from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.experiment import ExperimentConfigCreate
from src.core.database import get_session
from src.core.redis import redis_cache
from src.services.repository import ExperimentRepository
from src.core.config import settings

router = APIRouter(prefix='/experiments', tags=['Admin API'])
templates = Jinja2Templates(directory="src/templates")

async def verify_admin_key(x_admin_key: str = Header(...)):
    if not settings.ADMIN_API_KEY:
        return
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный API ключ")


@router.post("/", status_code=201, dependencies=[Depends(verify_admin_key)])
async def create_experiment(
    experiment: ExperimentConfigCreate,
    session: AsyncSession = Depends(get_session),
):
    repo = ExperimentRepository(session)
    if await repo.exists(experiment.name):
        raise HTTPException(
            status_code=400,
            detail=f"Эксперимент '{experiment.name}' уже существует!"
        )
    await repo.create(experiment)
    await redis_cache.save_experiment(experiment)
    return {"message": "Эксперимент успешно создан", "name": experiment.name}


@router.get("/", dependencies=[Depends(verify_admin_key)])
async def list_experiments(session: AsyncSession = Depends(get_session)):
    repo = ExperimentRepository(session)
    exps = await repo.list_all()
    return [
        {
            "name": e.name,
            "variants": e.variants,
            "config": e.config,
            "url": e.url,
            "is_active": e.is_active,
            "total_weight": sum(e.variants.values()),
        }
        for e in exps
    ]


@router.delete("/{name}", dependencies=[Depends(verify_admin_key)])
async def delete_experiment(
    name: str,
    session: AsyncSession = Depends(get_session),
):
    repo = ExperimentRepository(session)
    if not await repo.delete(name):
        raise HTTPException(status_code=404, detail="Эксперимент не найден")
    await redis_cache.delete_experiment(name)
    return {"message": f"Эксперимент '{name}' удалён"}