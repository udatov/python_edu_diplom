import abc
from logging import getLogger
from typing import Callable, Tuple, Type
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import BasicProperties
from pika.spec import Basic
from pika import PlainCredentials, BlockingConnection, ConnectionParameters
from common.src.theatre.core.config import G_RABBITMQ_CONFIG, ThreadSignal
from threading import Thread
from common.src.theatre.core.helpers import logging_error

logger = getLogger(__name__)

"""
Тип функции, которая используется для обработки сообщений из очереди потребителем.
"""
ConsumerCallbackFuncType = Callable[[BlockingChannel, Basic.Deliver, BasicProperties, bytes], None]

"""
Тип функции, которая используется для старта потребителя в отдельном потоке.
"""
StartConsumerFuncType = Callable[[None], 'BaseConsumerHandler']


def create_consumer_handler_thread(target_func: StartConsumerFuncType) -> Thread:
    """
    Запускаем handler потребителя в отдельном потоке
    """
    return Thread(target=target_func)


def start_consumer_handler(consumer_cls: Type['BaseConsumerHandler']) -> None:
    """Создаем и запускаем handler потребителя для обработки нотификаций."""
    w = consumer_cls()
    try:
        print("start_consumer_handler: START HANLDER")
        w.run()
    except KeyboardInterrupt as keyboard_interr:
        print("start_consumer_handler: HANLDER INTERRUPTED")
        logging_error(logger=logger, error=keyboard_interr, prefix_msg='Notification Worker run in KeyboardInterrupted')
    except Exception as error:
        logging_error(logger=logger, error=error, prefix_msg='Notification Worker run exception')
    finally:
        print("start_consumer_handler: HANLDER FINALLY")
        w.close()


def create_queue_with_dlx_channel() -> BlockingChannel:
    """Регистрирует основную очередь и очередь DLX, связывет их и создает канал сообщения RabbitMQ для потребителя."""
    channel: BlockingChannel = None
    # Конфигурируем 2 exchange и 2 очереди (главную и DLX очередь)
    credentials = PlainCredentials(G_RABBITMQ_CONFIG.username, G_RABBITMQ_CONFIG.password)
    connection = BlockingConnection(ConnectionParameters(host=G_RABBITMQ_CONFIG.host, credentials=credentials))
    channel = connection.channel()
    # Set up DLX
    channel.exchange_declare(exchange=G_RABBITMQ_CONFIG.dlx_exchange_name, exchange_type='direct')
    channel.queue_declare(queue=G_RABBITMQ_CONFIG.dlx_queue_name, durable=True)
    channel.queue_bind(
        exchange=G_RABBITMQ_CONFIG.dlx_exchange_name,
        queue=G_RABBITMQ_CONFIG.dlx_queue_name,
        routing_key=G_RABBITMQ_CONFIG.dlx_routing_key,
    )

    # Main queue with DLX
    args = {
        'x-dead-letter-exchange': G_RABBITMQ_CONFIG.dlx_exchange_name,
        'x-dead-letter-routing-key': G_RABBITMQ_CONFIG.dlx_routing_key,
    }
    channel.queue_declare(queue=G_RABBITMQ_CONFIG.worker_queue, arguments=args, durable=True)
    channel.basic_qos(prefetch_count=1, global_qos=False)
    return channel, connection


def create_queue_channel(queue_name: str) -> BlockingChannel:
    """Создаем канал сообщения RabbitMQ для публикации."""
    channel: BlockingChannel = None
    # Конфигурируем 2 exchange и 2 очереди (главную и DLX очередь)
    credentials = PlainCredentials(G_RABBITMQ_CONFIG.username, G_RABBITMQ_CONFIG.password)
    connection = BlockingConnection(ConnectionParameters(host=G_RABBITMQ_CONFIG.host, credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1, global_qos=False)
    return channel, connection


def create_channel() -> BlockingChannel:
    """Создаем канал сообщения RabbitMQ для публикации."""
    channel: BlockingChannel = None
    # Конфигурируем 2 exchange и 2 очереди (главную и DLX очередь)
    credentials = PlainCredentials(G_RABBITMQ_CONFIG.username, G_RABBITMQ_CONFIG.password)
    connection = BlockingConnection(ConnectionParameters(host=G_RABBITMQ_CONFIG.host, credentials=credentials))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1, global_qos=False)
    return channel, connection


class BaseConsumerHandler(abc.ABC):
    """
    Базовый класс для handler потребителей очереди
    Handler "забирает" логику взаимодействия с очередью, а обработку сообщения отдает воркеру.
    """

    @staticmethod
    def is_stop_signal(body: bytes):
        print("Check if STOP signal")
        json_object: str = body.decode(G_RABBITMQ_CONFIG.content_encoding)
        try:
            signal_msg = ThreadSignal.model_validate_json(json_data=json_object)
            if signal_msg.signal == G_RABBITMQ_CONFIG.stop_signal.signal:
                print("Got STOP signal")
                return True
        except Exception as err:
            logging_error(logger=logger, error=err, prefix_msg='Not a stop signal. Continue consuming...')
            return False

    def __init__(self, queue_name: str):
        self._queue_name = queue_name
        channel, connection = self.create_channel()
        self._connection: BlockingConnection = connection
        self._channel: BlockingChannel = channel

    @abc.abstractmethod
    def get_process_callback(self) -> ConsumerCallbackFuncType:
        """
        Возвращает функцию-обработчик сообщения из очереди
        """
        pass

    def create_channel(self) -> Tuple:
        """
        Инициализация соединения и канала подключения к очереди
        """
        return create_channel()

    def run(self):
        self._channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=self.get_process_callback(),
            auto_ack=False,
        )
        self._channel.start_consuming()

    def close(self):
        self._channel.stop_consuming()
        self._channel.close()
        self._connection.close()
