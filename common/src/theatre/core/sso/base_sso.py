from urllib.parse import urlencode
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
import secrets
from typing import Dict
from fastapi_sso import SSOBase, OpenID, SSOLoginError
from httpx import AsyncClient
from abc import ABC, abstractmethod
import logging
from common.src.theatre.core import redis

logger = logging.getLogger(__name__)


class AbstractOAuthSSO(SSOBase, ABC):
    """Абстрактный класс для OAuth авторизации через разные сервисы"""

    provider: str
    scope: list
    base_url: str
    access_token_url: str
    userinfo_url: str

    @abstractmethod
    async def get_user_info(self, access_token: str, **kwargs) -> OpenID:
        """Получение информации о пользователе (реализуется в подклассах)"""
        pass

    async def get_login_redirect(self, request: Request) -> RedirectResponse:
        """Создать URL для редиректа на OAuth"""
        state = secrets.token_urlsafe(16)
        # Сохраняем state в Redis с временем жизни 5 минут
        try:
            logger.info(f"Попытка сохранения state в Redis: {state}")
            # Проверяем подключение к Redis
            await redis.redis.ping()
            logger.info("Подключение к Redis успешно")

            # Сохраняем state
            await redis.redis.set(f"oauth_state:{state}", "1", ex=300)
            logger.info(f"State успешно сохранен в Redis: {state}")

            # Проверяем, что state действительно сохранился
            saved_state = await redis.redis.get(f"oauth_state:{state}")
            logger.info(f"Проверка сохранения state в Redis: {saved_state}")

            # Проверяем время жизни ключа
            ttl = await redis.redis.ttl(f"oauth_state:{state}")
            logger.info(f"Время жизни ключа state в Redis: {ttl} секунд")

            logger.info(f"Заголовки запроса: {dict(request.headers)}")
            logger.info(f"Origin: {request.headers.get('origin')}")
            logger.info(f"Redirect URI: {self.redirect_uri}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении state в Redis: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при сохранении state")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scope),
            "state": state,
        }
        authorize_url = f"{self.base_url}/authorize"
        return RedirectResponse(url=f"{authorize_url}?{urlencode(params)}")

    async def get_access_token(self, code: str) -> Dict:
        """Получение токена доступа"""
        async with AsyncClient() as session:
            response = await session.post(
                self.access_token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            data = response.json()
            if "error" in data:
                raise SSOLoginError(f"OAuth ошибка: {data.get('error_description', 'Неизвестная ошибка')}")
            return data

    async def verify_and_process(self, request: Request) -> OpenID:
        """Общий процесс верификации OAuth"""
        received_state = request.query_params.get("state")
        if not received_state:
            logger.error("State не получен в параметрах запроса")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="State не получен в параметрах запроса"
            )

        try:
            await redis.redis.ping()
            logger.info("Подключение к Redis успешно")

            state_exists = await redis.redis.get(f"oauth_state:{received_state}")
            logger.info(f"Проверка state в Redis: {state_exists}")

            if not state_exists:
                logger.error(f"State не найден в Redis: {received_state}")
                keys = await redis.redis.keys("oauth_state:*")
                logger.info(f"Все ключи state в Redis: {keys}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="State не найден или истек")

            await redis.redis.delete(f"oauth_state:{received_state}")
            logger.info(f"State успешно удален из Redis: {received_state}")
        except Exception as e:
            logger.error(f"Ошибка при проверке state в Redis: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при проверке state")

        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отсутствует код авторизации")

        token_data = await self.get_access_token(code)
        return await self.get_user_info(token_data["access_token"], email=token_data.get("email"))
