import logging
from logging import config as logging_config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi_limiter import FastAPILimiter
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from redis.asyncio import Redis
from starlette.middleware.cors import CORSMiddleware

from auth_api.src.api.v1.auth import auth_router, sso_router
from auth_api.src.api.v1.permissions import permission_router
from auth_api.src.api.v1.roles import role_router
from auth_api.src.core import config
from auth_api.src.core.middleware import RoleBasedAccessControlMiddleware
from auth_api.src.db import rdb
from auth_api.src.db.postgres import create_partition_tables, get_session
from auth_api.src.db.seed import seed_database
from common.src.theatre.core import redis as redis_module
from common.src.theatre.core import token
from common.src.theatre.core.config import REDIS_HOST, REDIS_PORT
from common.src.theatre.core.token import get_access_token_factory, get_refresh_token_factory
from common.src.theatre.db import base
from auth_api.src.core.logger import G_LOGGING

# Применяем настройки логирования
logging_config.dictConfig(G_LOGGING)

logger = logging.getLogger(__name__)


def configure_tracer() -> None:
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(
            JaegerExporter(
                agent_host_name='localhost',
                agent_port=6831,
            )
        )
    )
    # Чтобы видеть трейсы в консоли
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup events
    # configure_tracer()
    logger.info(f'Инициализация Redis с параметрами: host={REDIS_HOST}, port={REDIS_PORT}')
    try:
        redis: Redis = redis_module.get_new_redis()
        await redis.ping()
        logger.info('Успешное подключение к Redis')
        redis_module.redis = redis 
        redis_module.get_redis_cache_storage.cache_clear()

        await FastAPILimiter.init(redis)
    except Exception as e:
        logger.error(f'Ошибка при инициализации Redis: {str(e)}')
        raise

    async for session in get_session():
        base.db = rdb.UserDB(db_session=session)
        base.login_history_item_db = rdb.LoginHistoryItemDB(db_session=session)
        await seed_database(session)

    await create_partition_tables()

    token.access_token_factory = await get_access_token_factory(token_store=redis)
    token.refresh_token_factory = await get_refresh_token_factory(depends_on_factory=token.access_token_factory)

    # await FastAPILimiter.init(redis)

    yield
    # shutdown_events
    await redis.close()
    await session.aclose()


app = FastAPI(
    title=config.PROJECT_NAME,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    version='1.0.0',
    description='Сервис авторизации',
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:8000', 'http://127.0.0.1:8000', 'https://oauth.yandex.ru'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['*'],
)

# Остальные middleware
app.add_middleware(RoleBasedAccessControlMiddleware)

# FastAPIInstrumentor.instrument_app(app)
# SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

app.include_router(auth_router, prefix='/api/v1/auth', tags=['auth'])
app.include_router(role_router, prefix='/api/v1/auth', tags=['auth'])
app.include_router(permission_router, prefix='/api/v1/auth', tags=['auth'])
app.include_router(sso_router, prefix='/api/v1/auth', tags=['auth'])
