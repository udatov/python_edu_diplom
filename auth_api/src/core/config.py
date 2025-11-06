import os
from pydantic import EmailStr, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from common.src.theatre.schemas.auth_schemas import UserCreate


# Название проекта. Используется в Swagger-документации
PROJECT_NAME = os.getenv('PROJECT_NAME', 'auth')

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AuthDbSettings(BaseSettings):
    """Конфигурация для подключения к реляционной БД аутентификации / авторизации."""

    user: str = Field(..., alias='AUTH_DB_USER')
    password: str = Field(..., alias='POSTGRES_PASSWORD')
    host: str = Field(..., alias='POSTGRES_HOST')
    port: int = Field(..., alias='POSTGRES_PORT')
    database: str = Field(..., alias='AUTH_DB')
    content_schema: str = Field(..., alias='AUTH_SCHEMA')
    auth_db_url: str = Field(..., alias='AUTH_DB_URL')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)


class AuthDefaultUserSettings(BaseSettings):
    """Свойства пользователя по уиолчанию - администратора"""

    login: str = Field(..., alias='AUTH_DEFAULTUSER_LOGIN')
    password: str = Field(..., alias='AUTH_DEFAULTUSER_PASSWORD')
    firstname: str = Field(..., alias='AUTH_DEFAULTUSER_FIRSTNAME')
    lastname: str = Field(..., alias='AUTH_DEFAULTUSER_LASTNAME')
    email: EmailStr = Field(..., alias='AUTH_DEFAULTUSER_EMAIL')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)

    @computed_field
    @property
    def build_user_create_dto(self) -> UserCreate:
        return UserCreate(
            login=self.login,
            email=self.email,
            password=self.password,
            first_name=self.firstname,
            last_name=self.lastname,
        )


class RateLimitSettings(BaseSettings):
    """Настройки ограничений запросов (rate limiting)"""

    enabled: bool = Field(True, alias='RATE_LIMIT_ENABLED')
    window: int = Field(60, alias='RATE_LIMIT_WINDOW')
    block_time: int = Field(300, alias='RATE_LIMIT_BLOCK_TIME')
    default: int = Field(100, alias='RATE_LIMIT_DEFAULT')

    registration: int = Field(5, alias='RATE_LIMIT_REGISTER')
    login: int = Field(5, alias='RATE_LIMIT_LOGIN')
    logout: int = Field(30, alias='RATE_LIMIT_LOGOUT')
    refresh: int = Field(10, alias='RATE_LIMIT_REFRESH')
    me: int = Field(60, alias='RATE_LIMIT_ME')
    history: int = Field(40, alias='RATE_LIMIT_HISTORY')

    role_read: int = Field(50, alias='RATE_LIMIT_ROLE_READ')
    role_write: int = Field(20, alias='RATE_LIMIT_ROLE_WRITE')
    user_role: int = Field(30, alias='RATE_LIMIT_USER_ROLE')

    permission_read: int = Field(50, alias='RATE_LIMIT_PERMISSION_READ')
    permission_write: int = Field(20, alias='RATE_LIMIT_PERMISSION_WRITE')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)


class YandexOAuthSettings(BaseSettings):
    """Настройки OAuth Яндекс"""

    client_id: str = Field(..., alias='YANDEX_CLIENT_ID')
    client_secret: str = Field(..., alias='YANDEX_CLIENT_SECRET')
    redirect_uri: str = Field('http://localhost:8000/api/v1/auth/callback/yandex', alias='YANDEX_REDIRECT_URI')
    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)


class VKOAuthSettings(BaseSettings):
    """Настройки OAuth ВКонтакте"""

    client_id: str = Field(..., alias='VK_CLIENT_ID')
    client_secret: str = Field(..., alias='VK_CLIENT_SECRET')
    redirect_uri: str = Field('http://localhost:8000/api/v1/auth/callback/vk', alias='VK_REDIRECT_URI')
    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)


G_AUTH_DB_SETTINGS = AuthDbSettings()
G_AUTH_DEFAULTUSER_SETTINGS = AuthDefaultUserSettings()
G_RATE_LIMIT_SETTINGS = RateLimitSettings()
G_YANDEX_OAUTH = YandexOAuthSettings()
G_VK_OAUTH = VKOAuthSettings()

SECRET_KEY = os.getenv('SECRET_KEY', 'secret_key')
