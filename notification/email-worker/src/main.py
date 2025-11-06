import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aio_pika
import aiosmtplib
import orjson
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from models import Notification, NotificationStatus, NotificationEvent
from settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(handler)


class EmailWorker:
    def __init__(self):
        self.rabbitmq_connection = None
        self.channel = None
        self.mongo_client = None
        self.email_queue = None
        self.is_running = False
        self.smtp_client = None
        self.scheduler_task = None

    async def connect(self):
        """Подключается к RabbitMQ и MongoDB"""
        try:
            logger.info("Connecting to RabbitMQ...")
            self.rabbitmq_connection = await aio_pika.connect_robust(url=settings.rabbitmq_url)
            self.channel = await self.rabbitmq_connection.channel()
            while not self.email_queue:
                try:
                    self.email_queue = await self.channel.get_queue(settings.email_queue)
                    logger.info(f"Connected to {settings.email_queue} queue")
                except Exception as e:
                    logger.error(f'Queue connection error: {e}.\n Retry after 5 seconds')
                    await asyncio.sleep(5)

            logger.info("Connecting to MongoDB...")
            self.mongo_client = AsyncIOMotorClient(settings.mongodb_url)
            db = self.mongo_client[settings.mongodb_db_name]
            await init_beanie(database=db, document_models=[Notification, NotificationEvent])
            logger.info("Connected to MongoDB")

            await self.smtp_connect()

            if settings.smtp_server == "mailhog":
                await self.test_mailhog_connection()

            return True
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    async def smtp_connect(self):
        """Подключение к SMTP"""
        logger.info("Connecting to SMTP...")
        self.smtp_client = aiosmtplib.SMTP(
            hostname=settings.smtp_server, port=settings.smtp_port, use_tls=settings.use_tls
        )
        await self.smtp_client.connect()
        if settings.smtp_server != "mailhog" and settings.smtp_user and settings.smtp_password:
            await self.smtp_client.login(settings.smtp_user, settings.smtp_password)
        logger.info("Connected to SMTP")

    async def test_mailhog_connection(self):
        """Тестирование подключения к MailHog"""
        if settings.smtp_server == "mailhog":
            logger.info("Testing MailHog connection...")
            test_email = MIMEMultipart()
            test_email["From"] = settings.email_sender
            test_email["To"] = "test@example.com"
            test_email["Subject"] = "MailHog Connection Test"
            test_email.attach(MIMEText("This is a test email to verify MailHog connection.", "plain"))

            try:
                await self.smtp_client.send_message(test_email)
                logger.info("✅  MailHog test successful! Check the MailHog UI at http://localhost:8025")
                return True
            except Exception as e:
                logger.error(f"❌ MailHog test failed: {str(e)}")
                return False
        return None

    async def process_message(self, message: aio_pika.IncomingMessage):
        """Обработка сообщения из очереди"""
        async with message.process():
            try:
                body = message.body.decode()
                data = orjson.loads(body)
                notification_id = message.message_id

                send_at = None
                if "send_at" in data:
                    try:
                        send_at = datetime.fromisoformat(data["send_at"])

                        if send_at.tzinfo is None:
                            send_at = send_at.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Incorrect send_at format of the notification {notification_id}: {e}."
                            f" Will send immediately."
                        )
                        send_at = None

                now = datetime.now(timezone.utc)
                if send_at and send_at > now:
                    await self._update_notifications_status(
                        notification_id=notification_id,
                        status=NotificationStatus.SCHEDULED
                    )
                    return

                content = data.get("content", {})
                email_content = content.get("email")

                if not email_content:
                    error_message = f"No email content found in message: {notification_id}"
                    logger.exception(error_message)
                    raise Exception(error_message)

                recipients = data.get("recipients", {})
                user_ids = recipients.get("user_ids", [])

                if not user_ids:
                    error_message = f"No recipients found for notification: {notification_id}"
                    logger.exception(error_message)
                    raise Exception(error_message)

                recipients_query = dict()
                if user_ids:
                    recipients_query["user_ids"] = [str(user_id) for user_id in user_ids]

                users = await self.list_users(**recipients_query)

                await self._update_notifications_status(
                    notification_id=notification_id,
                    status=NotificationStatus.PROCESSING
                )

                email_message = await self._make_email_message(email_content=email_content)

                for user in users:
                    await self._send_email(user=user, email_message=email_message, notification_id=notification_id)

            except Exception as e:
                error_message = str(e)
                logger.exception(f"Error processing notification {notification_id}: {error_message}")
                await self._update_notifications_status(
                    notification_id=notification_id,
                    status=NotificationStatus.FAILED,
                    error_message=error_message
                )

    @staticmethod
    async def _make_email_message(email_content: dict[str, Any], recipient: str | list = None) -> MIMEMultipart:
        """Создаёт письмо для отправки"""

        subject = email_content.get("subject", "")
        body = email_content.get("body", {})

        text = body.get("text", "")
        html = body.get("html", "")

        email_message = MIMEMultipart("alternative")
        email_message["From"] = settings.email_sender

        if recipient:
            if isinstance(recipient, list):
                email_message["To"] = ", ".join(recipient)
            else:
                email_message["To"] = recipient

        email_message["Subject"] = subject

        # Прикрепляем текстовую версию
        email_message.attach(MIMEText(text, "plain"))

        # Прикрепляем HTML-версию, если предоставлена
        if html:
            email_message.attach(MIMEText(html, "html"))

        return email_message

    @staticmethod
    async def _update_notifications_status(
            notification_id: str, status: NotificationStatus, error_message: str = None
    ) -> None:
        """Обновление статуса уведомлений"""
        try:

            await Notification.update_many_status(
                filter_query=dict(notification_id=notification_id),
                status=status,
                metadata=dict(error_message=error_message),
            )
        except Exception as e:
            logger.error(f"Failed to update notifications status: {str(e)}")

    @staticmethod
    async def _update_notification_status(
            notification_id: str, user_id: str, status: NotificationStatus, error_message: str = None
    ) -> None:
        """Обновление статуса уведомления для конкретного пользователя"""
        try:
            notification = await Notification.find_one(
                {"notification_id": notification_id, "user_id": user_id, "channel": "email"}
            )

            if notification:
                await notification.update_status(
                    status=status,
                    metadata={
                        "error_message": error_message
                    } if error_message else None
                )
            else:
                logger.warning(f"Notification not found: {notification_id} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update notification status: {str(e)}")

    async def _send_email(self, user: dict[str, Any], email_message: MIMEMultipart, notification_id: str) -> None:
        """Отправка письма конкретному пользователю"""
        try:
            email_message["To"] = user.get('email')
            num_tries = 0
            while num_tries < 2:
                try:
                    await self.smtp_client.send_message(email_message)
                    break
                except aiosmtplib.errors.SMTPServerDisconnected:
                    num_tries += 1
                    await self.smtp_connect()

            await self._update_notification_status(
                notification_id=notification_id,
                user_id=user.get("id"),
                status=NotificationStatus.DELIVERED
            )

        except Exception as e:
            logger.exception(f'Error sending email to user {user.get("id")}: {str(e)}')
            await self._update_notification_status(
                notification_id=notification_id,
                user_id=user.get("id"),
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )

    async def _process_scheduled_notification(self, notifications: list[Notification]):
        """Обработка запланированного уведомления"""
        notification_id = notifications[0].notification_id

        try:
            await self._update_notifications_status(
                notification_id=notification_id,
                status=NotificationStatus.PROCESSING
            )

            event = await NotificationEvent.find_one({"notification_id": notification_id})
            content = event.content
            email_content = content.get("email")

            if not email_content:
                error_message = f"No email content found in message: {notification_id}"
                logger.exception(error_message)
                raise Exception(error_message)

            recipients = event.recipients
            user_ids = recipients.get("user_ids", [])

            recipients_query = dict()
            if user_ids:
                recipients_query["user_ids"] = [str(user_id) for user_id in user_ids]

            users = await self.list_users(**recipients_query)

            if not user_ids:
                error_message = f"No recipients found for notification: {notification_id}"
                logger.exception(error_message)
                raise Exception(error_message)

            email_message = await self._make_email_message(
                email_content=email_content
            )
            for user in users:
                await self._send_email(user=user, email_message=email_message, notification_id=notification_id)

        except Exception as e:
            error_message = str(e)
            logger.exception(f"Error processing scheduled notification {notification_id}: {error_message}")
            await self._update_notifications_status(
                notification_id=notification_id,
                status=NotificationStatus.FAILED,
                error_message=error_message
            )

    async def list_users(self, user_ids: list[str] = None) -> list[dict[str, Any]]:
        """
        Получает список пользователей
        """
        import httpx
        params = {}

        if user_ids:
            params["user_ids"] = user_ids

        try:
            with httpx.AsyncClient(
                base_url=settings.auth_users_list,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.auth_api_token}"
                }
            ) as _client:
                response = await _client.get("/auth/list", params=params)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Request error: {str(e)}")

    async def scheduler(self):
        """Планировщик для отправки запланированных уведомлений"""
        logger.info("Email scheduler started")
        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                scheduled_notifications = await Notification.find(
                    {
                        "status": NotificationStatus.SCHEDULED,
                        "send_at": {"$lte": now},
                        "channel": "email"
                    }
                ).to_list()

                if scheduled_notifications:
                    notifications_by_notification_id = defaultdict(list)
                    for notification in scheduled_notifications:
                        if notification.status == NotificationStatus.SCHEDULED.value:
                            notifications_by_notification_id[notification.notification_id].append(notification)

                    for notifications in notifications_by_notification_id.values():
                        await self._process_scheduled_notification(notifications=notifications)

            except Exception as e:
                logger.exception(f"Error in scheduler: {str(e)}")

            await asyncio.sleep(60)

    async def run(self):
        """Запуск воркера, получение сообщений из очереди"""
        if not await self.connect():
            logger.error("Failed to connect. Exiting.")
            return

        self.is_running = True
        logger.info("Email worker started. Waiting for messages...")

        self.scheduler_task = asyncio.create_task(self.scheduler())

        try:
            async with self.email_queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await self.process_message(message)

                    if not self.is_running:
                        break

        except Exception as e:
            logger.exception(f"Error in message consumer: {str(e)}")
        finally:
            await self.close()

    async def close(self):
        """Close connections"""
        self.is_running = False

        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        if self.channel:
            await self.channel.close()

        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()

        if self.mongo_client:
            self.mongo_client.close()

        if self.smtp_client:
            await self.smtp_client.quit()

        logger.info("Email worker stopped")


async def main():
    worker = EmailWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
