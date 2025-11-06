from datetime import datetime, timezone

from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from .common import Recipients, NotificationChannel, NotificationStatus
from .event_type import CustomEvent, NotificationContent, FixedEvent


class BaseRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseNotificationRequest(BaseRequest):
    """Базовый запрос для всех типов уведомлений"""
    recipients: Recipients
    channels: list[NotificationChannel]
    content: NotificationContent
    send_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator('send_at')
    @classmethod
    def validate_send_at_future(cls, v: datetime | None) -> datetime | None:
        if v and v < datetime.now(timezone.utc):
            raise ValueError("Время отправки должно быть в будущем")
        return v

    @field_validator('expires_at')
    @classmethod
    def validate_expires_after_send(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        send_at = info.data.get('send_at')
        if v and send_at and v <= send_at:
            raise ValueError("Срок действия должен быть после времени отправки")
        return v


class SendNotificationRequest(BaseNotificationRequest):
    """Запрос на отправку уведомления"""
    event: FixedEvent | CustomEvent


class GetUserNotificationsRequest(BaseRequest):
    """Запрос на получение истории уведомлений пользователя"""
    user_ids: list[str] | None = None
    notification_id: str | None = None
    channel: NotificationChannel | None = None
    status: NotificationStatus | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    sort_by: str | None = None
    limit: int | None = None
    offset: int | None = None
