# db/postgres.py
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from auth_api.src.core.config import G_AUTH_DB_SETTINGS
from common.src.theatre.models.base import Base
from typing import Generator


# Создаём движок
# Настройки подключения к БД передаём из переменных окружения, которые заранее загружены в файл настроек
dsn = f'postgresql+asyncpg://{G_AUTH_DB_SETTINGS.user}:{G_AUTH_DB_SETTINGS.password}@{G_AUTH_DB_SETTINGS.host}:{G_AUTH_DB_SETTINGS.port}/{G_AUTH_DB_SETTINGS.database}'
engine = create_async_engine(
    dsn, echo=True, future=True, connect_args={'server_settings': {'search_path': G_AUTH_DB_SETTINGS.content_schema}}
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_database() -> None:
    # Импорт моделей необходим для их автоматического создания
    from auth_api.src.models.permission import Permission  # noqa: F401
    from auth_api.src.models.loginhistoryitem import LoginHistoryItem  # noqa: F401
    from auth_api.src.models.role import Role  # noqa: F401
    from auth_api.src.models.user import User  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_partition_tables() -> None:
    """
    Партиционные таблицы создаем из-под приложения мимо Alembic
    """
    from auth_api.src.db.partition import LoginHistoryItem  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


# Функция понадобится при внедрении зависимостей
# Dependency
async def get_session() -> Generator[AsyncSession, None, None]:  # type: ignore
    async with async_session() as session:
        yield session


async def purge_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
