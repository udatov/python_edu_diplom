import abc
from typing import Any, Dict
from redis.asyncio import Redis


class CacheStorage(abc.ABC):
    """Абстракция хранилища кеша."""

    @abc.abstractmethod
    async def get(self, key: str) -> str:
        """Получить данные по ключу из хранилища"""
        pass

    @abc.abstractmethod
    async def set(self, key: str, value: str, ex: int) -> None:
        """Сохранить данные по ключу в хранилище"""
        pass

    async def hset(self, entity_name: str, mapping: Dict[str, Any]):
        """Положить словарь данных"""
        pass

    async def hgetall(self, entity_name: str) -> Dict[str, Any]:
        """Получить словарь данных"""
        pass


class RedisCacheStorage(CacheStorage):
    """Хранилище кеша на основе Redis."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self, key: str) -> str:
        value = await self.redis.get(key)
        return value

    async def set(self, key: str, value: str, ex: int) -> None:
        await self.redis.set(key, value, ex=ex)

    async def hset(self, entity_name: str, mapping: Dict[str, Any]):
        await self.redis.hset(name=entity_name, mapping=mapping)

    async def hgetall(self, entity_name: str) -> Dict[str, Any]:
        return {k.decode(): v.decode() for k, v in await self.redis.hgetall(name=entity_name).items()}
