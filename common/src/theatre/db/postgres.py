# db/postgres.py
from typing import TypeVar
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import Generator

AsyncPgSessionMakerType = TypeVar(name='AsyncPgSessionMakerType', bound=async_sessionmaker)


# Создаём движок
# Настройки подключения к БД передаём из переменных окружения, которые заранее загружены в файл настроек
def create_async_session_maker(dsn: str, search_path: str) -> AsyncPgSessionMakerType:
    engine = create_async_engine(
        dsn,
        echo=True,
        future=True,
        connect_args={'server_settings': {'search_path': search_path}},
    )
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Функция понадобится при внедрении зависимостей
# Dependency
async def get_session(async_session_maker: AsyncPgSessionMakerType) -> Generator[AsyncSession, None, None]:  # type: ignore
    async with async_session_maker() as session:
        yield session
