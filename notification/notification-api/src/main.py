import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from config import settings
from broker.rabbitmq import open_rabbitmq_connection, close_rabbitmq_connection
from database.mongo import connect_to_mongo, close_mongo_connection
from api import router as api_router
from services.notification import rabbit_queue_listener, shutdown_event
from services.ws_connection_manager import WSConnectionManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск сервиса нотификации")

    await open_rabbitmq_connection()
    await connect_to_mongo()

    shutdown_event.clear()
    manager = WSConnectionManager()
    app.state.manager = manager
    task = asyncio.create_task(rabbit_queue_listener(manager))

    yield

    logger.info("Завершение работы приложения Онлайн-кинотеатр API")
    shutdown_event.set()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("RabbitMQ listener task cancelled")

    await close_rabbitmq_connection()
    await close_mongo_connection()

app = FastAPI(
    lifespan=lifespan,
    description=settings.app_description,
    title=settings.app_title,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    root_path="/notification_api",
)


@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    from config import LOGGING

    uvicorn.run(
        app=app,
        host=settings.app_host,
        port=settings.app_port,
        log_config=LOGGING,
        log_level=logging.DEBUG,
    )
