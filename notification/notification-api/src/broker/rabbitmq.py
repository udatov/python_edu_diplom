import logging

import aio_pika

from config import settings
from schemas.notification import NotificationChannel

logger = logging.getLogger(__name__)

_rabbitmq_connection: aio_pika.Connection | None = None

NOTIFICATION_EXCHANGE = "notifications"
DEAD_LETTER_EXCHANGE = "dead_letter"

EMAIL_QUEUE = 'email_notifications'
SMS_QUEUE = 'sms_notifications'
PUSH_QUEUE = 'push_notifications'

EMAIL_ROUTING_KEY = 'notification.email'
SMS_ROUTING_KEY = 'notification.sms'
PUSH_ROUTING_KEY = 'notification.push'

EXCHANGES: dict[str, aio_pika.abc.AbstractExchange] = {}

CHANNEL_MAPPING = {
    NotificationChannel.EMAIL.value: {
        "routing_key": EMAIL_ROUTING_KEY,
        "queue": EMAIL_QUEUE
    },
    NotificationChannel.SMS.value: {
        "routing_key": SMS_ROUTING_KEY,
        "queue": SMS_QUEUE
    },
    NotificationChannel.PUSH.value: {
        "routing_key": PUSH_ROUTING_KEY,
        "queue": PUSH_QUEUE
    }
}


async def open_rabbitmq_connection():
    """Подключение к RabbitMQ и установка exchanges и queues"""
    logger.info("RabbitMQ initialize connection and channels")

    global _rabbitmq_connection
    _rabbitmq_connection = await aio_pika.connect_robust(url=settings.rabbitmq_url)
    channel = await _rabbitmq_connection.channel()

    EXCHANGES[NOTIFICATION_EXCHANGE] = await channel.declare_exchange(
        NOTIFICATION_EXCHANGE, aio_pika.ExchangeType.TOPIC
    )

    await init_dead_letter(channel=channel)

    arguments = {
        "x-message-ttl": settings.rabbitmq_queue_ttl,
        "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
        "x-dead-letter-routing-key": f"dl.{EMAIL_ROUTING_KEY}"
    }
    email_queue = await channel.declare_queue(
        EMAIL_QUEUE, durable=True, arguments=arguments
    )

    arguments["x-dead-letter-routing-key"] = f"dl.{SMS_ROUTING_KEY}"
    sms_queue = await channel.declare_queue(
        SMS_QUEUE, durable=True, arguments=arguments
    )

    arguments["x-dead-letter-routing-key"] = f"dl.{PUSH_ROUTING_KEY}"
    push_queue = await channel.declare_queue(
        PUSH_QUEUE, durable=True, arguments=arguments
    )

    await email_queue.bind(EXCHANGES[NOTIFICATION_EXCHANGE], routing_key=EMAIL_ROUTING_KEY)
    await sms_queue.bind(EXCHANGES[NOTIFICATION_EXCHANGE], routing_key=SMS_ROUTING_KEY)
    await push_queue.bind(EXCHANGES[NOTIFICATION_EXCHANGE], routing_key=PUSH_ROUTING_KEY)


async def init_dead_letter(channel: aio_pika.abc.AbstractRobustChannel):
    """Инициализация Dead Letter Exchange"""
    EXCHANGES[DEAD_LETTER_EXCHANGE] = await channel.declare_exchange(
        DEAD_LETTER_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
    )

    dl_email_queue = await channel.declare_queue(
        f"dl_{EMAIL_QUEUE}", durable=True
    )
    dl_sms_queue = await channel.declare_queue(
        f"dl_{SMS_QUEUE}", durable=True
    )
    dl_push_queue = await channel.declare_queue(
        f"dl_{PUSH_QUEUE}", durable=True
    )

    await dl_email_queue.bind(EXCHANGES[DEAD_LETTER_EXCHANGE], routing_key=f"dl.{EMAIL_ROUTING_KEY}")
    await dl_sms_queue.bind(EXCHANGES[DEAD_LETTER_EXCHANGE], routing_key=f"dl.{SMS_ROUTING_KEY}")
    await dl_push_queue.bind(EXCHANGES[DEAD_LETTER_EXCHANGE], routing_key=f"dl.{PUSH_ROUTING_KEY}")


async def get_rabbitmq_connection() -> aio_pika.Connection:
    """Возвращает соединение с RabbitMQ."""
    global _rabbitmq_connection

    if _rabbitmq_connection is None or _rabbitmq_connection.is_closed:
        try:
            await open_rabbitmq_connection()
            logger.info("Reconnected to RabbitMQ")

        except Exception as e:
            logger.exception(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    return _rabbitmq_connection


async def close_rabbitmq_connection():
    """Закрывает соединение с RabbitMQ, если оно открыто."""
    global _rabbitmq_connection

    if _rabbitmq_connection:
        await _rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed")


async def get_or_declare_exchange(name: str) -> aio_pika.abc.AbstractExchange:
    """Возвращает или объявляет exchange"""
    if name in EXCHANGES:
        return EXCHANGES[name]

    connection = await get_rabbitmq_connection()
    _channel = await connection.channel()

    exchange = await _channel.declare_exchange(
        name, aio_pika.ExchangeType.TOPIC
    )
    EXCHANGES[name] = exchange
    return exchange
