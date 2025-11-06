from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_host: str = Field(default="localhost")
    mongodb_port: int = Field(default=27017)
    mongodb_db_name: str = Field(default="notification")

    rabbit_host: str = Field(default="localhost")
    rabbit_port: int = Field(default=5672)
    rabbit_user: str = Field(default="admin")
    rabbit_password: str = Field(default="admin")

    email_queue: str = Field(default="email_notifications")

    smtp_server: str = Field(default="mailhog")
    smtp_port: int = Field(default=1025)
    smtp_user: str = Field(...)
    smtp_password: str = Field(...)
    use_tls: bool = Field(default=False)

    email_sender: str = Field(...)

    auth_host: str = Field('http://auth_service:8000', alias='AUTH_SERVICE_HOST')
    auth_api_base: str = Field('/api/v1/auth', alias='AUTH_API_BASE')

    auth_api_token: str = Field(...)

    @property
    def rabbitmq_url(self):
        return f"amqp://{self.rabbit_user}:{self.rabbit_password}@{self.rabbit_host}:{self.rabbit_port}/"

    @property
    def mongodb_url(self):
        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}"

    @property
    def auth_api_v1_url(self) -> str:
        return f"{self.auth_host}{self.auth_api_base}"

    @property
    def auth_users_list(self) -> str:
        return f"{self.auth_api_v1_url}/filter"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
