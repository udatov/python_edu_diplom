from datetime import datetime, timezone
from typing import Any

from beanie import Document, Indexed
from beanie.odm.queries.find import FindMany
from pydantic import Field

from schemas.notification import NotificationContent
from schemas.notification.common import (Recipients, NotificationChannel, NotificationStatus)


class NotificationEvent(Document):
    """Модель события уведомления в MongoDB"""
    notification_id: Indexed(str)
    event_type: str = Field(...)

    recipients: Recipients

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stored_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entity_id: str | None = None  # ID связанной сущности (фильм, комментарий и т.д.)

    content: NotificationContent

    class Settings:
        name = "notification_events"
        use_state_management = True


class Notification(Document):
    """Модель уведомления в MongoDB"""
    notification_id: Indexed(str)
    user_id: Indexed(str)
    channel: NotificationChannel
    status: NotificationStatus = NotificationStatus.NEW

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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

    @classmethod
    async def get_notifications(
            cls,
            notification_id: str = None,
            user_ids: list[str] | None = None,
            channel: NotificationChannel | None = None,
            status: NotificationStatus | None = None,
            from_date: datetime | None = None,
            to_date: datetime | None = None,
            sort_by: str | None = None,
            limit: int | None = None,
            offset: int | None = None
    ) -> FindMany['Notification']:
        """
        Получает список уведомлений пользователя.

        Args:
            notification_id: Фильтр по идентификатору отправки
            user_ids: Фильтр по идентификаторам пользователей
            channel: Фильтр по каналу
            status: Фильтр по статусу
            from_date: Фильтр по дате (начало периода)
            to_date: Фильтр по дате (конец периода)
            sort_by: Сортировать по ("-created_at")
            limit: Максимальное количество результатов
            offset: Смещение для пагинации

        Returns:
            List[Notification]: Список уведомлений
        """
        query = cls.find()

        if notification_id:
            query = query.find({"notification_id": notification_id})

        if user_ids:
            query = query.find({"user_id": {"$in": user_ids}})

        if channel:
            query = query.find({"channel": channel})

        if status:
            query = query.find({"status": status})

        if from_date:
            if not to_date:
                to_date = datetime.now(timezone.utc)

            query = query.find({
                "created_at": {
                    "$gte": from_date,
                    "$lte": to_date
                }
            })

        if sort_by:
            query = query.sort(sort_by)

        if offset:
            query = query.skip(offset)

        if limit:
            query = query.limit(limit)

        return query

    @classmethod
    async def count_notifications(
            cls,
            notification_id: str = None,
            user_ids: list[str] | None = None,
            channel: NotificationChannel | None = None,
            status: NotificationStatus | None = None,
            from_date: datetime | None = None,
            to_date: datetime | None = None
    ) -> int:
        """
        Подсчитывает количество уведомлений пользователя.

        Args:
            notification_id: Фильтр по идентификатору отправки
            user_ids: Фильтр по идентификаторам пользователей
            channel: Фильтр по каналу
            status: Фильтр по статусу
            from_date: Фильтр по дате (начало периода)
            to_date: Фильтр по дате (конец периода)

        Returns:
            int: Количество уведомлений
        """
        query = await cls.get_notifications(
            notification_id=notification_id, user_ids=user_ids, channel=channel, status=status, from_date=from_date,
            to_date=to_date
        )

        return await query.count()

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

        update_data = {
            "$set": {
                "status": status,
                "updated_at": current_time
            }
        }

        match status:
            case NotificationStatus.SENT_TO_QUEUE:
                update_data["$set"]["sent_at"] = current_time

            case NotificationStatus.DELIVERED:
                update_data["$set"]["delivered_at"] = current_time

            case NotificationStatus.READ:
                update_data["$set"]["read_at"] = current_time

            case NotificationStatus.FAILED:
                update_data["$set"]["failed_at"] = current_time

        if metadata:
            if "error_message" in metadata:
                update_data["$set"]["error_message"] = metadata["error_message"]

        result = await cls.find(filter_query).update(update_data)
        return result.modified_count
