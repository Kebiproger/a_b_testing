from src.services.cache import RedisCache
from src.core.config import settings

redis_cache = RedisCache(settings.REDIS_URL)
