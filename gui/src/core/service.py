from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict
import aiohttp

from gui.src.core.config import G_GUI_SERVICE_SETTINGS
from gui.src.core.storage import get_token


@asynccontextmanager
async def get_client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    try:
        session = aiohttp.ClientSession()
        yield session
    finally:
        await session.close()


async def make_auth_api_post_login(username: str, password: str) -> Dict[str, Any]:
    """
    Делаем запрос на /login Auth сервиса
    """
    async with get_client_session() as session:
        async with session.post(
            G_GUI_SERVICE_SETTINGS.auth_api_v1_login,
            data={'username': username, 'password': password},
            headers={'content-type': 'application/x-www-form-urlencoded'},
        ) as login_response:
            if login_response.status > 200:
                return {'status': login_response.status, 'json': None}
            return {'status': login_response.status, 'json': await login_response.json()}


async def make_payment_api_post_subscribe(months: int) -> Dict[str, Any]:
    """
    Делаем запрос на оплату подписки
    """
    async with get_client_session() as session:
        async with session.post(
            G_GUI_SERVICE_SETTINGS.payment_api_v1_subscribe,
            json={'subscribe_type': 'long_term', 'lifetime_months': months},
            headers={
                'content-type': 'application/json',
                'Authorization': f'Bearer {get_token()}',
            },
        ) as login_response:
            if login_response.status > 200:
                return {'status': login_response.status, 'json': None}
            return {'status': login_response.status, 'json': await login_response.json()}


async def make_payment_api_get_complete(yookassa_payment_id: str) -> Dict[str, Any]:
    """
    Делаем запрос на подтверждение оплаты
    """
    async with get_client_session() as session:
        async with session.get(
            f'{G_GUI_SERVICE_SETTINGS.payment_api_v1_complete}/{yookassa_payment_id}',
            headers={'content-type': 'application/json', 'Authorization': f'Bearer {get_token()}'},
        ) as login_response:
            if login_response.status > 200:
                return {'status': login_response.status, 'json': None}
            return {'status': login_response.status, 'json': await login_response.json()}
