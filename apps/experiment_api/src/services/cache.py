import redis.asyncio as aioredis
from typing import Optional
from src.schemas.experiment import ExperimentСonfigCreate

class RedisCache:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
    
    async def connect(self):
        self.redis = await aioredis.from_url(
            self.redis_url,
            decode_responses=True # Возвращает строку а не байт
        )
        print("Подключение успешна к Redis!")
    
    async def get_experiment(self, experiment_name: str) -> Optional[ExperimentСonfigCreate]:

        if not self.redis:
            raise RuntimeError("Redis не инициализирован")
        
        redis_key = f'experiment:{experiment_name}'

        raw_data = await self.redis.get(redis_key)

        if not raw_data:
            return None
        
        return ExperimentСonfigCreate.model_validate_json(raw_data)
    
    async def get_experiment_by_url(self, url: str) -> Optional[ExperimentСonfigCreate]:
        """Найти эксперимент по URL-паттерну (перебор всех экспериментов в Redis — для демо)"""
        if not self.redis:
            raise RuntimeError("Redis не инициализирован")
        keys = await self.redis.keys("experiment:*")
        for key in keys:
            raw = await self.redis.get(key)
            if not raw:
                continue
            exp = ExperimentСonfigCreate.model_validate_json(raw)
            if exp.url and url.startswith(exp.url):
                return exp
        return None
    
    async def save_experiment(self, experiment: ExperimentСonfigCreate):
        if not self.redis:
            raise RuntimeError("Redis не инициализирован")
        
        redis_key = f'experiment:{experiment.name}'

        json_data = experiment.model_dump_json() # Pydantic -> JSON

        await self.redis.set(redis_key, json_data)
        
    async def delete_experiment(self, experiment_name: str):
        if not self.redis:
            raise RuntimeError("Redis не инициализирован")
        redis_key = f"experiment:{experiment_name}"
        await self.redis.delete(redis_key)

    async def close(self):
        if self.redis:
            await self.redis.close()
