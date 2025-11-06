from dataclasses import dataclass
import os
from typing import ClassVar, List
import pika
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

# Настройки Redis
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Настройки Elasticsearch
ELASTIC_SCHEME = os.getenv('ELASTIC_SCHEME', 'http')
ELASTIC_HOST = os.getenv('ELASTIC_HOST', '127.0.0.1')
ELASTIC_PORT = int(os.getenv('ELASTIC_PORT', 9200))

# Время жизни данных в кэше
CACHE_EXPIRE_IN_SECONDS = int(os.getenv('CACHE_EXPIRE_IN_SECONDS', 300))
CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'True').lower() == 'true'

# Время жизни данных в кэше
CACHE_EXPIRE_IN_SECONDS = int(os.getenv('CACHE_EXPIRE_IN_SECONDS', 300))
CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'True').lower() == 'true'


class JwtSettings(BaseSettings):
    """Конфигурация настройки JWT токена."""

    secret_key_header: str = Field(..., alias='JWT_SECRET_KEY_HEADER')
    alogrithm: str = Field(..., alias='JWT_ALGORITHM')
    secret_key_strength: int = Field(..., alias='JWT_SECRET_KEY_STRENGTH')

    access_token_lifetime_hours: int = Field(..., alias='JWT_ACCESS_TOKEN_LIFETIME_HOURS')
    refresh_token_lifetime_days: int = Field(..., alias='JWT_REFRESH_TOKEN_LIFETIME_DAYS')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)


@dataclass
class KafkaConfig:
    bootstrap_servers: List[str] = None

    def __post_init__(self):
        kafka_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', '')
        if not self.bootstrap_servers:
            if ',' in kafka_servers:
                self.bootstrap_servers = kafka_servers.split(',')
            else:
                self.bootstrap_servers = [kafka_servers] if kafka_servers else ['127.0.0.1:9094']


class KafkaSettings(BaseSettings):
    """Конфигурация для подключения к Kafka."""

    bootstrap_servers: str = Field(..., alias='KAFKA_BOOTSTRAP_SERVERS')
    topic: str = Field(..., alias='KAFKA_THEATRE_USERS_MOCK_TOPIC')
    theatre_users_test_topic: str = Field(..., alias='KAFKA_THEATRE_USERS_TEST_TOPIC')
    group_id: str = Field('ugc_etl_group', alias='KAFKA_GROUP_ID')
    auto_offset_reset: str = Field('earliest', alias='KAFKA_AUTO_OFFSET_RESET')
    consumer_timeout_ms: int = Field(10000, alias='KAFKA_CONSUMER_TIMEOUT_MS')
    auto_commit: bool = Field(False, alias='KAFKA_AUTO_COMMIT')
    theatre_users_msg_key: str = Field(..., alias='KAFKA_THEATRE_USERS_MSG_KEY')

    model_config = SettingsConfigDict(
        extra='allow',
        case_sensitive=True,
    )


class PgDbSettings(BaseSettings):
    """Конфигурация для подключения к реляционной БД аутентификации / авторизации."""

    provider_title: ClassVar[str] = 'PostgreSQL'
    user: str = Field(..., alias='POSTGRES_USER')
    password: str = Field(..., alias='POSTGRES_PASSWORD')
    host: str = Field(..., alias='POSTGRES_HOST')
    port: int = Field(..., alias='POSTGRES_PORT')
    database: str = Field(..., alias='POSTGRES_DB')
    content_schema: str = Field(..., alias='POSTGRES_SCHEMA')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)

    @computed_field(return_type=str)
    def dsn(self):
        return f'dbname={self.database} user={self.user} password={self.password} host={self.host} port={self.port}'

    @computed_field(return_type=str)
    def async_dsn(self):
        """
        Format for asyncpg
        """
        return f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'


class MongoDbSettings(BaseSettings):
    """Конфигурация для подключения к MongDB.
    Используем default= для отладки
    """

    provider_title: ClassVar[str] = 'Mongodb'
    host: str = Field(default='127.0.0.1', alias='MONGODB_HOST')
    port: int = Field(default=27017, alias='MONGODB_PORT')
    schema: str = Field(default='mongodb', alias='MONGODB_SCHEMA')

    social_activity_db: str = Field(default='sa', alias='MONGODB_SOCIAL_ACTIVITY_DB')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)

    @computed_field
    @property
    def conn_string(self) -> dict[str, str]:
        return f'{self.schema}://{self.host}:{self.port}'


class ThreadSignal(BaseModel):
    signal: str = 'FLUGGAENKOECHIEBOLSEN'


class RabbitMqSettings(BaseSettings):
    """Конфигурация RabbitMQ."""

    host: str = Field(..., alias='RABBITMQ_DEFAULT_HOST')
    username: str = Field(..., alias='RABBITMQ_DEFAULT_USER')
    password: str = Field(..., alias='RABBITMQ_DEFAULT_PASS')
    exchange_name: str = Field(..., alias='RABBITMQ_EXCHANGE_NAME')
    dlx_exchange_name: str = Field(..., alias='RABBITMQ_DLX_EXCHANGE_NAME')
    worker_queue: str = Field(..., alias='RABBITMQ_WORKER_QUEUE')
    publish_queue: str = Field(..., alias='RABBITMQ_PUBLISH_QUEUE')
    dlx_queue_name: str = Field(..., alias='RABBITMQ_DLX_QUEUE')
    routing_key: str = Field(..., alias='RABBITMQ_ROUTING_KEY')
    dlx_routing_key: str = Field(..., alias='RABBITMQ_DLX_ROUTING_KEY')

    retry_count: int = Field(..., alias='RABBITMQ_RETRY_COUNT')
    worker_thread_count: int = Field(..., alias='RABBITMQ_WORKER_THREAD_COUNT')
    content_encoding: str = Field(..., alias='RABBITMQ_CONTENT_ENCODING')
    content_type: str = Field(..., alias='RABBITMQ_MSG_CONTENT_TYPE')
    stop_signal: ThreadSignal = Field(default=ThreadSignal())

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)

    @computed_field
    @property
    def base_properties(self) -> dict[str, str]:
        return pika.BasicProperties(
            delivery_mode=2,
            content_encoding=G_RABBITMQ_CONFIG.content_encoding,
            content_type=G_RABBITMQ_CONFIG.content_type,
        )


class NotificationDbSettings(BaseSettings):
    """Конфигурация для подключения к реляционной БД уведомлений."""

    user: str = Field(..., alias='NOTIFICATION_DB_USER')
    password: str = Field(..., alias='POSTGRES_PASSWORD')
    host: str = Field(..., alias='POSTGRES_HOST')
    port: int = Field(..., alias='POSTGRES_PORT')
    database: str = Field(..., alias='NOTIFICATION_DB')
    content_schema: str = Field(..., alias='NOTIFICATION_SCHEMA')
    auth_db_url: str = Field(..., alias='NOTIFICATION_DB_URL')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)


class PaymentDbSettings(BaseSettings):
    """Конфигурация для подключения к реляционной БД оплаты подписки."""

    user: str = Field(..., alias='PAYMENT_DB_USER')
    password: str = Field(..., alias='POSTGRES_PASSWORD')
    host: str = Field(..., alias='POSTGRES_HOST')
    port: int = Field(..., alias='POSTGRES_PORT')
    database: str = Field(..., alias='PAYMENT_DB')
    content_schema: str = Field(..., alias='PAYMENT_SCHEMA')
    auth_db_url: str = Field(..., alias='PAYMENT_DB_URL')

    model_config = SettingsConfigDict(extra='allow', case_sensitive=True)

    @computed_field
    @property
    def asyncpg_dsn(self) -> str:
        return f'postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'


class ApiPathSettings(BaseSettings):
    auth_api_path: str = Field(default='http://localhost:8000', alias='AUTH_SERVICE_PATH')
    payment_api_path: str = Field(default='http://localhost:8007', alias='PAYMENT_SERVICE_PATH')
    gui_service_path: str = Field(default='http://localhost:8008', alias='GUI_SERVICE_PATH')


G_RABBITMQ_CONFIG = RabbitMqSettings()

G_KAFKA_SETTINGS = KafkaSettings()
G_JWT_SETTINGS = JwtSettings()
G_MONGODB_SETTINGS = MongoDbSettings()
G_PG_SETTINGS = PgDbSettings()

G_NOTIFICATION_DB_SETTINGS = NotificationDbSettings()
G_PAYMENT_DB_SETTINGS = PaymentDbSettings()
G_API_PATH_SETTINGS = ApiPathSettings()
