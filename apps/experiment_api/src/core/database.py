from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from src.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ExperimentModel(Base):
    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    variants: Mapped[dict] = mapped_column(JSONB, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    url: Mapped[str | None] = mapped_column(String(200), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose_db():
    await engine.dispose()

async def get_session():
    async with async_session() as session:
        yield session
