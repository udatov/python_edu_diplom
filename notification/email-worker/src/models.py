from datetime import datetime, timezone
from enum import Enum
from typing import Any

from beanie import Document, Indexed


class NotificationStatus(str, Enum):
    """Статусы уведомления"""
    NEW = "new"  # Новая
    SENT_TO_QUEUE = "sent_to_queue"  # Отправлено в RabbitMQ
    PROCESSING = "processing"  # В процессе обработки
    DELIVERED = "delivered"  # Доставлено получателю
    FAILED = "failed"  # Ошибка при отправке
    READ = "read"  # Прочитано получателем
    EXPIRED = "expired"  # Срок действия истек
    CANCELLED = "cancelled"  # Отменено
    SCHEDULED = "scheduled"  # Запланировано


class NotificationEvent(Document):
    """Модель события уведомления в MongoDB"""
    notification_id: Indexed(str)
    event_type: str

    recipients: dict[str, Any]

    created_at: datetime
    stored_at: datetime
    entity_id: str | None = None  # ID связанной сущности (фильм, комментарий и т.д.)

    content: dict[str, Any]

    class Settings:
        name = "notification_events"
        use_state_management = True


class Notification(Document):
    """Модель уведомления в MongoDB"""
    notification_id: Indexed(str)
    user_id: Indexed(str)
    channel: str
    status: NotificationStatus

    created_at: datetime
    updated_at: datetime
    queued_at: datetime
    sent_at: datetime | None = None  # Отправлено в
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    send_at: datetime | None = None  # Для отложенной отправки
    expires_at: datetime | None = None  # Срок действия уведомления

    class Settings:
        name = "notifications"
        use_state_management = True

    async def update_status(
            self,
            status: NotificationStatus,
            metadata: dict[str, Any] | None = None
    ) -> "Notification":
        """
        Обновляет статус уведомления.

        Args:
            status: Новый статус
            metadata: Дополнительные данные для обновления

        Returns:
            Notification: Обновленное уведомление
        """
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

        match status:
            case NotificationStatus.SENT_TO_QUEUE:
                self.sent_at = datetime.now(timezone.utc)

            case NotificationStatus.DELIVERED:
                self.delivered_at = datetime.now(timezone.utc)

            case NotificationStatus.READ:
                self.read_at = datetime.now(timezone.utc)

            case NotificationStatus.FAILED:
                self.failed_at = datetime.now(timezone.utc)

        if metadata:
            if "error_message" in metadata:
                self.error_message = metadata["error_message"]

        await self.save()
        return self

    @classmethod
    async def update_many_status(
            cls,
            filter_query: dict,
            status: NotificationStatus,
            metadata: dict[str, Any] | None = None
    ) -> int:
        """
        Обновляет статус нескольких уведомлений, соответствующих фильтру.

        Args:
            filter_query: Словарь с условиями фильтрации
            status: Новый статус
            metadata: Дополнительные данные для обновления

        Returns:
            int: Количество обновленных документов
        """
        current_time = datetime.now(timezone.utc)

        filter_query.update(channel="email")

        update_data = {
            "$set": {
                "status": status,
                "updated_at": current_time
            }
        }

        if status == NotificationStatus.SENT_TO_QUEUE:
            update_data["$set"]["sent_at"] = current_time

        elif status == NotificationStatus.DELIVERED:
            update_data["$set"]["delivered_at"] = current_time

        elif status == NotificationStatus.READ:
            update_data["$set"]["read_at"] = current_time

        elif status == NotificationStatus.FAILED:
            update_data["$set"]["failed_at"] = current_time

        if metadata:
            if "error_message" in metadata:
                update_data["$set"]["error_message"] = metadata["error_message"]

        result = await cls.find(filter_query).update(update_data)
        return result.modified_count
