from contextlib import asynccontextmanager
import logging
from logging import config as logging_config
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from billing.payment_api.src.api.v1.payment import payment_api_router
from billing.payment_api.src.core.config import G_PAYMENT_SERVICE_SETTINGS
from billing.payment_api.src.core.logger import G_LOGGING
from common.src.theatre.db import base
from billing.payment_api.src.db import rdb
from common.src.theatre.db.postgres import create_async_session_maker, get_session
from common.src.theatre.core.config import G_PAYMENT_DB_SETTINGS

# Применяем настройки логирования
logging_config.dictConfig(G_LOGGING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup events

    async for session in get_session(
        async_session_maker=create_async_session_maker(
            dsn=G_PAYMENT_DB_SETTINGS.asyncpg_dsn, search_path=G_PAYMENT_DB_SETTINGS.content_schema
        )
    ):
        base.db = rdb.PaymentDB(db_session=session)

    logger.info("startup")
    yield
    # shutdown_events
    await session.aclose()


app = FastAPI(
    title='Payment API',
    docs_url='/api/openapi',
    openapi_url='/payment/api/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    version='1.0.0',
    description='API для проведения платежей через Yookassa',
)


app.include_router(payment_api_router, prefix=G_PAYMENT_SERVICE_SETTINGS.api_v1_prefix, tags=['payment_api'])
