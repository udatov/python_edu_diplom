from typing import Optional
from fastapi_sso import OpenID
from fastapi_sso.sso.base import SSOLoginError
from httpx import AsyncClient
from common.src.theatre.core.sso.base_sso import AbstractOAuthSSO
import logging

logger = logging.getLogger(__name__)


class VKSSO(AbstractOAuthSSO):
    provider = "vk"
    scope = ["email"]
    base_url = "https://oauth.vk.com"
    access_token_url = "https://oauth.vk.com/access_token"
    userinfo_url = "https://api.vk.com/method/users.get"
    vk_api_version = "5.199"

    async def get_user_info(self, access_token: str, email: Optional[str] = None) -> OpenID:
        async with AsyncClient() as session:
            response = await session.get(
                self.userinfo_url,
                params={
                    "fields": "first_name,last_name,photo_200,screen_name",
                    "access_token": access_token,
                    "v": self.vk_api_version,
                },
            )
            data = response.json()
            if "error" in data:
                error_msg = f"Ошибка API ВКонтакте: {data['error']['error_msg']}"
                logger.error(error_msg)
                raise SSOLoginError(error_msg)

            user = data["response"][0]

            return OpenID(
                id=str(user["id"]),
                email=email,
                display_name=f"{user['first_name']} {user['last_name']}",
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                picture=user.get("photo_200"),
                provider=self.provider,
            )
