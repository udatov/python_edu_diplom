import logging

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from models.mongo import Notification, NotificationEvent

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient | None = None


async def connect_to_mongo():
    """Подключение к MongoDB"""
    logger.info("Подключение к MongoDB...")
    try:
        global client
        client = AsyncIOMotorClient(settings.mongodb_url)
        _db = client[settings.mongodb_db_name]

        await init_beanie(database=_db, document_models=[Notification, NotificationEvent])

        logger.info("Подключение к MongoDB успешно")
    except Exception as e:
        logger.error(f"Ошибка подключения к MongoDB: {str(e)}")
        raise


async def close_mongo_connection():
    """Закрытие подключения к MongoDB"""
    global client
    if client:
        logger.info("Закрытие подключения к MongoDB...")
        client.close()
        logger.info("Подключение к MongoDB закрыто")
