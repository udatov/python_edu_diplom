from logging import getLogger

from redis.asyncio import Redis
from common.src.theatre.core import redis as redis_module
from common.src.theatre.core.helpers import logging_error
from common.src.theatre.core.redis import get_redis_cache_storage
from common.src.theatre.core.token import JwtTokenCoder
from common.src.theatre.core.config import G_JWT_SETTINGS

import http
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = getLogger(__name__)
redis: Redis = redis_module.get_new_redis()


async def decode_token(access_token: str) -> Optional[Dict[Any, Any]]:
    global redis
    """
    Функция декодирует токен, используя секретный ключ, сохранённый в объекте settings в поле jwt_secret_key.
    Возвращает содержимое токена в виде словаря или None, если токен невалиден или при декодировании
    было выброшено исключение.
    """
    try:
        secret_key_header = G_JWT_SETTINGS.secret_key_header
        # keys = await redis.keys('*')  # for testing
        secret_key: str = await get_redis_cache_storage(redis=redis).get(key=secret_key_header)
        jwt_token_coder: JwtTokenCoder = JwtTokenCoder()

        return jwt_token_coder.decode(
            encode_token=access_token, secret_key=secret_key, algorithm=G_JWT_SETTINGS.alogrithm
        )
    except Exception as err:
        logging_error(logger=logger, error=err, prefix_msg='Decode auth token')
        return None
    finally:
        await redis.close()


class JWTBearer(HTTPBearer):
    """
    Класс - наследник fastapi.security.HTTPBearer. Рекомендуем исследовать этот класс.
    Метод `__call__` класса HTTPBearer возвращает объект HTTPAuthorizationCredentials из заголовка `Authorization`

    class HTTPAuthorizationCredentials(BaseModel):
        scheme: str #  'Bearer'
        credentials: str #  сам токен в кодировке Base64

    FastAPI при использовании класса HTTPBearer добавит всё необходимое для авторизации в Swagger документацию.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        """
        Переопределение метода родительского класса HTTPBearer.
        Логика проста: достаём токен из заголовка и декодируем его.
        В результате возвращаем словарь из payload токена или выбрасываем исключение.
        Так как далее объект этого класса будет использоваться как зависимость Depends(...),
        то при этом будет вызван метод `__call__`.
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid authorization code.')
        if not credentials.scheme == 'Bearer':
            raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail='Only Bearer token might be accepted')
        decoded_token = await self.parse_token(credentials.credentials)
        if not decoded_token:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Invalid or expired token.')
        return decoded_token

    @staticmethod
    async def parse_token(jwt_token: str) -> Optional[dict]:
        return await decode_token(jwt_token)


G_SECURITY_JWT = JWTBearer()
