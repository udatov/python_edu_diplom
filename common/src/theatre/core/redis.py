import json
from functools import lru_cache, wraps
from inspect import isawaitable
from typing import Any, Callable, Coroutine, Optional, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from redis import BusyLoadingError
from redis.asyncio import Redis

from common.src.theatre.core.config import CACHE_ENABLED, CACHE_EXPIRE_IN_SECONDS, REDIS_HOST, REDIS_PORT
from common.src.theatre.db.cache import RedisCacheStorage
from common.src.theatre.models.base import BaseDBModel
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

redis: Optional[Redis] = None

T = TypeVar('T', bound=BaseModel)
R = TypeVar('R')
AsyncPydanticMethod = Callable[..., Coroutine[Any, Any, R]]


def get_new_redis() -> Redis:
    return Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        retry=Retry(ExponentialBackoff(), 7),
        retry_on_error=[BusyLoadingError, ConnectionError, TimeoutError],
    )


@lru_cache()
def get_redis_cache_storage(redis: Redis) -> RedisCacheStorage:
    """Получение экземпляра RedisCacheStorage."""
    return RedisCacheStorage(redis)


def cache_with_storage(model: type[T]):
    """Универсальный декоратор для кеширования с абстракцией хранилища."""

    def wrapper(method: AsyncPydanticMethod[R]) -> AsyncPydanticMethod[R]:
        @wraps(method)
        async def wrapped(self, *args, **kwargs) -> R:
            if not CACHE_ENABLED:
                return await method(self, *args, **kwargs)
            if args:
                raise ValueError('Only kwargs are allowed here.')

            redis_cache_storage = get_redis_cache_storage(redis)

            prefix = get_storage_key_prefix(self, method)
            storage_key = get_storage_key(prefix, **kwargs)
            data = await redis_cache_storage.get(storage_key)
            if not data:
                result = await method(self, **kwargs)

                if isawaitable(result):
                    result = await result
                if isinstance(result, list):
                    dict_value = [jsonable_encoder(item) for item in result]
                else:
                    dict_value = jsonable_encoder(result)

                value = json.dumps(dict_value)
                await redis_cache_storage.set(storage_key, value, ex=CACHE_EXPIRE_IN_SECONDS)
                return result

            return BaseDBModel.create_model_with_validation(model=model, raw_data=data)

        return wrapped

    return wrapper


def get_storage_key_prefix(instance, method):
    class_name = type(instance).__name__
    method_name = method.__name__
    return f'{class_name}.{method_name}'


def get_storage_key(prefix, **kwargs):
    filtered_dict = {k: kwargs[k] for k in kwargs.keys() if kwargs[k] is not None}
    sorted_kwargs = ','.join([f'{k}={v}' for k, v in sorted(filtered_dict.items(), key=lambda x: x[0])])
    return f'{prefix}({sorted_kwargs})'
