from typing import Optional
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import ExperimentModel
from src.schemas.experiment import ExperimentConfigCreate


class ExperimentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, name: str) -> Optional[ExperimentConfigCreate]:
        result = await self.session.get(ExperimentModel, name)
        if not result:
            return None
        return ExperimentConfigCreate(
            name=result.name,
            variants=result.variants,
            config=result.config,
            url=result.url,
            is_active=result.is_active,
        )

    async def create(self, experiment: ExperimentConfigCreate) -> None:
        model = ExperimentModel(
            name=experiment.name,
            variants=experiment.variants,
            config=experiment.config,
            url=experiment.url,
            is_active=experiment.is_active,
        )
        self.session.add(model)
        await self.session.commit()

    async def exists(self, name: str) -> bool:
        query = select(exists().where(ExperimentModel.name == name))
        result = await self.session.execute(query)
        return result.scalar()

    async def list_all(self) -> list[ExperimentConfigCreate]:
        result = await self.session.execute(select(ExperimentModel).order_by(ExperimentModel.created_at.desc()))
        rows = result.scalars().all()
        return [
            ExperimentConfigCreate(
                name=r.name, variants=r.variants,
                config=r.config, url=r.url, is_active=r.is_active,
            )
            for r in rows
        ]

    async def delete(self, name: str) -> bool:
        model = await self.session.get(ExperimentModel, name)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.commit()
        return True
