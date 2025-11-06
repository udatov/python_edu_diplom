from fastapi_sso import OpenID, SSOLoginError
from httpx import AsyncClient
from common.src.theatre.core.sso.base_sso import AbstractOAuthSSO


class YandexSSO(AbstractOAuthSSO):
    provider = "yandex"
    scope = ["login:email", "login:info"]
    base_url = "https://oauth.yandex.ru"
    access_token_url = "https://oauth.yandex.ru/token"
    userinfo_url = "https://login.yandex.ru/info"

    async def get_user_info(self, access_token: str, **kwargs) -> OpenID:
        async with AsyncClient() as session:
            response = await session.get(self.userinfo_url, headers={"Authorization": f"OAuth {access_token}"})
            if response.status_code != 200:
                raise SSOLoginError(f"Ошибка API Яндекса: {response.text}")

            data = response.json()
            return OpenID(
                id=str(data["id"]),
                email=data.get("default_email"),
                display_name=data.get("display_name"),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                provider=self.provider,
            )
