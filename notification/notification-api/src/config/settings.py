from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    debug: bool = Field(default=False)
    app_title: str = Field(default="Сервис нотификации")
    app_description: str = Field(
        default="API для управления рассылками и уведомлениями")
    app_version: str = Field(default="1.0.0")
    notification_api_key: str = Field(..., description="Ключ для получения доступа к API")

    mongodb_host: str = Field(default="localhost")
    mongodb_port: int = Field(default=27017)
    mongodb_db_name: str = Field(default="notification")

    rabbit_host: str = Field(default="localhost")
    rabbit_port: int = Field(default=5672)
    rabbit_user: str = Field(default="admin")
    rabbit_password: str = Field(default="admin")

    rabbitmq_queue_ttl: int = Field(86400000)

    auth_public_key: str
    auth_algorithm: str = Field(default="HS256")

    @property
    def rabbitmq_url(self):
        return f"amqp://{self.rabbit_user}:{self.rabbit_password}@{self.rabbit_host}:{self.rabbit_port}/"

    @property
    def mongodb_url(self):
        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
