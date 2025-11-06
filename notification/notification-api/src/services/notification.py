import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aio_pika
import orjson
from fastapi import BackgroundTasks
from models.mongo import Notification, NotificationEvent, NotificationStatus
from schemas.notification import (SendNotificationRequest, NotificationResponse)
from schemas.notification.push_notification import PushNotify, Recipients
from services.ws_connection_manager import WSConnectionManager

from broker.rabbitmq import get_rabbitmq_connection, PUSH_QUEUE

logger = logging.getLogger(__name__)


class NotificationServiceException(Exception):
    pass


class NotificationService:

    @staticmethod
    async def process_notification_request(
            request: SendNotificationRequest,
            background_tasks: BackgroundTasks,
    ) -> NotificationResponse:
        """
            Обрабатывает запрос на отправку уведомления.
        """
        response = NotificationResponse(
            notification_id=request.request_id,
            status=NotificationStatus.NEW.value,
            queued_at=datetime.now(timezone.utc),
            message="Notification queued for processing",
        )

        request_dict = request.model_dump()

        event_type = request.event.event_type.value

        event = NotificationEvent(
            notification_id=str(response.notification_id),
            event_type=event_type,
            recipients=request.recipients,
            created_at=request.timestamp,
            entity_id=getattr(request.event, "entity_id", None),
            content=request.content
        )

        await event.insert()

        await NotificationService._create_notification_records(
            request=request, notification_id=str(response.notification_id)
        )

        background_tasks.add_task(
            NotificationService.send_to_rabbitmq,
            message_data=request_dict,
            notification_id=str(response.notification_id),
            channels=[channel.value for channel in request.channels]
        )

        return response

    @staticmethod
    async def _create_notification_records(
            request: SendNotificationRequest,
            notification_id: str,
    ):
        """
        Создает записи уведомлений в MongoDB для каждого получателя и канала.
        """
        user_ids = request.recipients.user_ids

        notification_batch = []
        batch_size = 300

        for user_id in user_ids:
            if user_id:
                for channel in request.channels:
                    notification_batch.append(Notification(
                        notification_id=notification_id,
                        user_id=user_id,
                        channel=channel.value,
                        status=NotificationStatus.NEW,
                        created_at=datetime.now(timezone.utc),
                        send_at=request.send_at,
                        expires_at=request.expires_at,
                    ))

                    if len(notification_batch) >= batch_size:
                        await Notification.insert_many(notification_batch)
                        notification_batch.clear()

        if notification_batch:
            await Notification.insert_many(notification_batch)

    @staticmethod
    async def send_to_rabbitmq(
            message_data: dict[str, Any],
            notification_id: str,
            channels: list[str]
    ):
        """
        Отправляет сообщение в RabbitMQ.
        """
        try:
            from broker.rabbitmq import get_or_declare_exchange, CHANNEL_MAPPING, NOTIFICATION_EXCHANGE

            notifications_exchange = await get_or_declare_exchange(name=NOTIFICATION_EXCHANGE)

            message_data["sent_to_rabbitmq_at"] = datetime.now(timezone.utc).isoformat()
            message_body = orjson.dumps(message_data)

            await Notification.update_many_status(
                filter_query=dict(notification_id=notification_id),
                status=NotificationStatus.SENT_TO_QUEUE,
            )

            for notification_channel in channels:
                mapping = CHANNEL_MAPPING.get(notification_channel)
                if not mapping:
                    logger.warning(f"Unknown notification channel: {notification_channel}")
                    continue

                channel_message = aio_pika.Message(
                    body=message_body,
                    message_id=notification_id,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                )

                await notifications_exchange.publish(
                    message=channel_message,
                    routing_key=mapping["routing_key"]
                )

        except Exception as e:
            logger.exception(f"Error sending notification to RabbitMQ: {str(e)}")

            await Notification.update_many_status(
                filter_query=dict(notification_id=notification_id),
                status=NotificationStatus.FAILED,
                metadata=dict(error_message=str(e))
            )

    @staticmethod
    def build_push_notification(data: dict) -> PushNotify:
        push = data.get("content", {}).get("push", {})
        event = data.get("event", {})
        recipients_data = data.get("recipients", {})

        return PushNotify(
            title=push.get("title", ""),
            body=push.get("body", {}).get("text") or "",
            image_url=push.get("image_url"),
            action_url=push.get("action_url"),
            ttl=push.get("ttl"),
            event_type=event.get("event_type"),
            entity_id=event.get("entity_id"),
            subject=event.get("subject"),
            text=event.get("text"),
            send_at=data.get("send_at"),
            expires_at=data.get("expires_at"),
            recipients=Recipients(
                all_users=recipients_data.get("all_users", False),
                user_ids=recipients_data.get("user_ids"),
            )
        )


shutdown_event = asyncio.Event()


async def rabbit_queue_listener(manager: WSConnectionManager):
    connection = await get_rabbitmq_connection()
    channel = await connection.channel()
    queue = await channel.declare_queue(PUSH_QUEUE, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:

            if shutdown_event.is_set():
                break
            async with message.process():
                try:
                    data = orjson.loads(message.body.decode())
                    notification = NotificationService.build_push_notification(data)

                    msg = orjson.dumps(notification).decode()
                    if notification.recipients.all_users:
                        await manager.send_to_all_users(msg)
                    else:
                        for user_id in notification.recipients.user_ids or []:
                            await manager.send_to_user(user_id, msg)
                except Exception as e:
                    logger.exception(f"Failed to handle push message: {e}")
