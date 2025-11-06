from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .common import NotificationChannel, NotificationStatus


class NotificationResponse(BaseModel):
    """Ответ на запрос отправки уведомления"""
    notification_id: UUID = Field(default_factory=uuid4)
    status: str = NotificationStatus.NEW.value
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    message: str | None = None


class NotificationHistoryItem(BaseModel):
    """Элемент истории уведомлений для просмотра в ЛК"""
    notification_id: str
    user_id: str
    created_at: datetime
    sent_at: datetime | None = None
    read_at: datetime | None = None
    channel: NotificationChannel
    status: NotificationStatus
    error_message: str | None = None


class GetUserNotificationsResponse(BaseModel):
    """Ответ с историей уведомлений пользователя"""
    notifications: list[NotificationHistoryItem]
    total: int
    limit: int | None = None
    offset: int | None = None
